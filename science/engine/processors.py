"""
TERRAVOX — Scientific Processing Engine (Pipelines A, B, UARI, and APOF)
Strictly preserves nodata masks, physical units, sign conventions, and uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from science.ingestion.nisar_reader import (
    GeocodedGridSubset,
    NISARProvenance,
    assert_compatible_pair,
)


@dataclass
class ScientificLayerOutput:
    measurement_type: str
    unit: str
    sign_convention: str
    measurement_grid: np.ndarray
    uncertainty_grid: np.ndarray
    quality_category_grid: np.ndarray  # 0=Invalid, 1=Low, 2=Moderate, 3=High
    valid_mask: np.ndarray
    disagreement_grid: Optional[np.ndarray]
    provenance_records: List[NISARProvenance]
    summary_stats: Dict[str, Optional[float]]
    limitations: List[str]


def process_gcov_backscatter_change(
    t1_subset: GeocodedGridSubset,
    t2_subset: GeocodedGridSubset,
    polarization_term: str = "HHHH",
    min_looks: float = 3.0,
    flood_threshold_db: float = -3.0,
    water_backscatter_ceiling_db: float = -15.0,
) -> ScientificLayerOutput:
    """
    Pipeline A + UARI + MECA Flood Inundation Classifier:
    1. Computes Delta gamma0_dB = 10*log10(gamma0_t2) - 10*log10(gamma0_t1).
    2. Identifies flood inundation where backscatter drops >= 3 dB and post-event power is specular.
    3. Calculates log-speckle UARI uncertainty from effective looks.
    """
    assert_compatible_pair(t1_subset.provenance, t2_subset.provenance)

    # Auto-detect available polarization term if HHHH is not present
    available_pols = [k for k in ("HHHH", "VVVV", "HVHV", "VHVH") if k in t1_subset.data and k in t2_subset.data]
    pol = polarization_term if polarization_term in t1_subset.data else available_pols[0]

    g1 = t1_subset.data[pol]
    g2 = t2_subset.data[pol]
    m1 = t1_subset.data.get("mask", np.zeros_like(g1, dtype=np.uint8))
    m2 = t2_subset.data.get("mask", np.zeros_like(g2, dtype=np.uint8))
    nl1 = t1_subset.data.get("numberOfLooks", np.full_like(g1, 16.0))
    nl2 = t2_subset.data.get("numberOfLooks", np.full_like(g2, 16.0))

    # Valid pixel: finite positive linear power, excluding shadow (bit 0 == 0)
    valid = (
        np.isfinite(g1)
        & np.isfinite(g2)
        & (g1 > 1e-7)
        & (g2 > 1e-7)
        & ((m1 & 1) == 0)
        & ((m2 & 1) == 0)
    )

    delta_db = np.full(g1.shape, np.nan, dtype=np.float32)
    uncertainty_db = np.full(g1.shape, np.nan, dtype=np.float32)
    flood_inundation_mask = np.zeros(g1.shape, dtype=np.uint8)  # 1 = Inundated
    quality_cat = np.zeros(g1.shape, dtype=np.uint8)  # 0=Invalid, 1=Low, 2=Moderate, 3=High

    # Compute logarithmic backscatter
    g1_db = np.full(g1.shape, np.nan, dtype=np.float32)
    g2_db = np.full(g2.shape, np.nan, dtype=np.float32)
    g1_db[valid] = 10.0 * np.log10(g1[valid])
    g2_db[valid] = 10.0 * np.log10(g2[valid])

    delta_db[valid] = g2_db[valid] - g1_db[valid]

    # UARI: First-order log-speckle uncertainty in dB: (10 / ln(10)) * sqrt(1/ENL_1 + 1/ENL_2)
    coeff = 10.0 / np.log(10.0)
    uncertainty_db[valid] = coeff * np.sqrt((1.0 / np.clip(nl1[valid], 1.0, 100.0)) + (1.0 / np.clip(nl2[valid], 1.0, 100.0)))

    # MECA Flood Classification: Significant drop + low absolute backscatter
    is_flooded = valid & (delta_db <= flood_threshold_db) & (g2_db <= water_backscatter_ceiling_db)
    flood_inundation_mask[is_flooded] = 1

    # Quality classification
    min_nl = np.minimum(nl1, nl2)
    quality_cat[valid & (min_nl < min_looks)] = 1  # Low
    quality_cat[valid & (min_nl >= min_looks) & (uncertainty_db > 1.2)] = 2  # Moderate
    quality_cat[valid & (min_nl >= min_looks) & (uncertainty_db <= 1.2)] = 3  # High

    valid_values = delta_db[valid]
    valid_unc = uncertainty_db[valid]
    flooded_count = int(np.count_nonzero(is_flooded))
    total_valid = int(np.count_nonzero(valid))

    stats = {
        "valid_pixel_fraction": float(np.mean(valid)),
        "total_valid_pixels": total_valid,
        "flooded_pixel_count": flooded_count,
        "flood_area_fraction": float(flooded_count / total_valid) if total_valid > 0 else 0.0,
        "mean_change_db": float(np.mean(valid_values)) if valid_values.size > 0 else None,
        "median_change_db": float(np.median(valid_values)) if valid_values.size > 0 else None,
        "p05_change_db": float(np.percentile(valid_values, 5)) if valid_values.size > 0 else None,
        "p95_change_db": float(np.percentile(valid_values, 95)) if valid_values.size > 0 else None,
        "mean_uncertainty_db": float(np.mean(valid_unc)) if valid_unc.size > 0 else None,
    }

    return ScientificLayerOutput(
        measurement_type=f"rtc_gamma0_backscatter_change_{pol}",
        unit="dB",
        sign_convention=(
            "Negative (-dB) indicates decreased radar backscatter (consistent with water specular reflection or drying); "
            "Positive (+dB) indicates increased radar backscatter (roughness or moisture)."
        ),
        measurement_grid=delta_db,
        uncertainty_grid=uncertainty_db,
        quality_category_grid=quality_cat,
        valid_mask=valid,
        disagreement_grid=flood_inundation_mask.astype(np.float32),  # Stored here for layer export
        provenance_records=[t1_subset.provenance, t2_subset.provenance],
        summary_stats=stats,
        limitations=[
            "Radar backscatter change (dB) detects surface roughness and dielectric property changes; it is NOT ground elevation change.",
            "Smooth water bodies reflect radar pulses away specularly; wind-roughened open water or flooded vegetation can produce complex backscatter variations.",
            "Radar shadow and layover zones are masked and never interpolated.",
        ],
    )


def process_gunw_deformation_and_apof(
    gunw_subset: GeocodedGridSubset,
    apply_ionosphere_correction: bool = True,
    coherence_threshold: float = 0.35,
    effective_looks: float = 36.0,
) -> ScientificLayerOutput:
    """
    Pipeline B + UARI + APOF:
    1. Masks invalid connectedComponents (0) and decorrelated pixels.
    2. Optionally subtracts ionospherePhaseScreen.
    3. Converts unwrapped phase (radians) to LOS displacement (mm):
       d_LOS = - (lambda / 4*pi) * delta_phi * 1000
    4. Computes UARI phase & ionospheric uncertainty in mm.
    5. Performs APOF (Adaptive Phase-Offset Fusion) where compatible slantRangeOffset (m) exists.
    """
    prov = gunw_subset.provenance
    wavelength_mm = prov.wavelength_m * 1000.0
    phase_to_mm = -wavelength_mm / (4.0 * np.pi)

    unw_phase = gunw_subset.data["unwrappedPhase"]
    coh = gunw_subset.data["coherenceMagnitude"]

    # Basic validity: finite phase, finite coherence, coherence > 0.05
    valid_phase = np.isfinite(unw_phase) & np.isfinite(coh) & (coh > 0.05) & (coh <= 1.0)

    # In NISAR, connectedComponents > 0 indicates valid unwrapped components
    if "connectedComponents" in gunw_subset.data:
        conn = gunw_subset.data["connectedComponents"]
        # If connected components are populated, filter by > 0; otherwise use finite phase
        if np.any(conn > 0):
            valid_phase &= (conn > 0)

    # In NISAR bitmask: 0 is valid ground; bits 0/1 are shadow/layover
    if "mask" in gunw_subset.data:
        m = gunw_subset.data["mask"]
        valid_phase &= ((m & 1) == 0)  # Exclude shadow (bit 0)

    corrected_phase = np.array(unw_phase, copy=True, dtype=np.float32)
    iono_unc_rad = np.zeros_like(unw_phase, dtype=np.float32)

    # Apply ionosphere phase screen where finite (do not invalidate phase if iono is NaN)
    if apply_ionosphere_correction and "ionospherePhaseScreen" in gunw_subset.data:
        iono = gunw_subset.data["ionospherePhaseScreen"]
        has_iono = np.isfinite(iono)
        corrected_phase[valid_phase & has_iono] -= iono[valid_phase & has_iono]
        if "ionospherePhaseScreenUncertainty" in gunw_subset.data:
            iono_u = gunw_subset.data["ionospherePhaseScreenUncertainty"]
            valid_iono_u = np.isfinite(iono_u)
            iono_unc_rad[valid_iono_u] = iono_u[valid_iono_u]

    # Phase-derived LOS displacement (mm)
    d_phase_mm = np.full_like(unw_phase, np.nan, dtype=np.float32)
    d_phase_mm[valid_phase] = corrected_phase[valid_phase] * phase_to_mm

    # UARI Phase Uncertainty: Cramér-Rao lower bound + ionospheric phase screen uncertainty
    coh_clipped = np.clip(coh, 0.05, 0.999)
    phase_var_rad2 = (1.0 - coh_clipped**2) / (2.0 * effective_looks * (coh_clipped**2))
    total_sigma_rad = np.sqrt(phase_var_rad2 + iono_unc_rad**2)
    sigma_phase_mm = np.full_like(unw_phase, np.nan, dtype=np.float32)
    sigma_phase_mm[valid_phase] = np.abs(phase_to_mm) * total_sigma_rad[valid_phase]

    # APOF: Check if compatible slantRangeOffset (meters) is present in the GUNW grid
    disagreement_mm = None
    measurement_type = "los_displacement_insar_phase"
    if "slantRangeOffset" in gunw_subset.data and "correlationSurfacePeak" in gunw_subset.data:
        sr_off_m = gunw_subset.data["slantRangeOffset"]
        corr_peak = gunw_subset.data["correlationSurfacePeak"]
        valid_off = np.isfinite(sr_off_m) & np.isfinite(corr_peak) & (corr_peak > 0.2)

        # Convert slantRangeOffset (m) to mm with matching sign convention (-1000 * sr_off_m)
        d_off_mm = np.full_like(unw_phase, np.nan, dtype=np.float32)
        d_off_mm[valid_off] = -1000.0 * sr_off_m[valid_off]
        sigma_off_mm = np.full_like(unw_phase, np.nan, dtype=np.float32)
        sigma_off_mm[valid_off] = 50.0 / np.clip(corr_peak[valid_off], 0.2, 1.0)

        both_valid = valid_phase & valid_off
        if np.any(both_valid):
            measurement_type = "los_displacement_apof_fused"
            disagreement_mm = np.full_like(unw_phase, np.nan, dtype=np.float32)
            disagreement_mm[both_valid] = np.abs(d_phase_mm[both_valid] - d_off_mm[both_valid])

            # Inverse-variance reliability weights gated by coherence
            w_p = (coh_clipped[both_valid] ** 2) / (sigma_phase_mm[both_valid] ** 2 + 1e-6)
            w_o = (corr_peak[both_valid] ** 2) / (sigma_off_mm[both_valid] ** 2 + 1e-6)

            d_phase_mm[both_valid] = (w_p * d_phase_mm[both_valid] + w_o * d_off_mm[both_valid]) / (
                w_p + w_o
            )
            sigma_phase_mm[both_valid] = np.sqrt(1.0 / (w_p + w_o))

    quality_cat = np.zeros(unw_phase.shape, dtype=np.uint8)
    quality_cat[valid_phase & (coh < coherence_threshold)] = 1  # Low reliability
    quality_cat[valid_phase & (coh >= coherence_threshold) & (coh < 0.65)] = 2  # Moderate
    quality_cat[valid_phase & (coh >= 0.65)] = 3  # High reliability

    valid_disp = d_phase_mm[valid_phase]
    valid_unc = sigma_phase_mm[valid_phase]

    stats = {
        "valid_pixel_fraction": float(np.mean(valid_phase)),
        "mean_los_displacement_mm": float(np.mean(valid_disp)) if valid_disp.size > 0 else None,
        "median_los_displacement_mm": float(np.median(valid_disp)) if valid_disp.size > 0 else None,
        "p05_los_displacement_mm": float(np.percentile(valid_disp, 5)) if valid_disp.size > 0 else None,
        "p95_los_displacement_mm": float(np.percentile(valid_disp, 95)) if valid_disp.size > 0 else None,
        "mean_uncertainty_mm": float(np.mean(valid_unc)) if valid_unc.size > 0 else None,
        "mean_coherence": float(np.mean(coh[valid_phase])) if valid_disp.size > 0 else None,
    }

    return ScientificLayerOutput(
        measurement_type=measurement_type,
        unit="mm",
        sign_convention=(
            "Line-of-Sight (LOS) displacement relative to radar sensor; "
            "requires single-geometry interpretation and is not 3D or purely vertical movement."
        ),
        measurement_grid=d_phase_mm,
        uncertainty_grid=sigma_phase_mm,
        quality_category_grid=quality_cat,
        valid_mask=valid_phase,
        disagreement_grid=disagreement_mm,
        provenance_records=[prov],
        summary_stats=stats,
        limitations=[
            "Single-geometry Line-of-Sight (LOS) displacement cannot separate vertical subsidence from horizontal fault motion without ascending + descending tracks.",
            "Unwrapped phase is relative to connected-component reference regions; phase jumps across disconnected components (connectedComponents IDs) may exist.",
            "Tropospheric delay variations may contribute residual phase signals if not independently corrected.",
        ],
    )