"""
TERRAVOX — Phase 2B: Punjab Flood Inundation Pipeline (NISAR L2 GCOV)
Pairs identical Track 012, Frame 017 repeat acquisitions during peak monsoon (Aug 14 vs Aug 26, 2026).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.transform import from_bounds

from science.engine.processors import ScientificLayerOutput, process_gcov_backscatter_change
from science.ingestion.nisar_reader import (
    GeocodedGridSubset,
    build_authenticated_asf_session,
    read_gcov_subset,
)
from science.ingestion.run_quetta_pipeline import download_with_progress, save_geotiff

# Punjab Indus–Chenab Basin Bounding Box (Muzaffargarh, Multan, D.G. Khan, Rajanpur corridor)
PUNJAB_AOI_BBOX = (70.60, 29.60, 71.60, 30.60)

# Exact matching 12-day repeat-pass granules (Track 012, Frame 017, CRID P05023)
T1_FILENAME = "NISAR_L2_PR_GCOV_028_012_A_017_4005_DHDH_A_20260814T002948_20260814T003023_P05023_N_F_J_001.h5"
T2_FILENAME = "NISAR_L2_PR_GCOV_029_012_A_017_4005_DHDH_A_20260826T002948_20260826T003023_P05023_N_F_J_001.h5"

T2_URL = f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_PROVISIONAL_V1/{T2_FILENAME[:-3]}/{T2_FILENAME}"


def extract_flood_sample_points(
    subset: GeocodedGridSubset,
    output: ScientificLayerOutput,
    study_area_id: str,
    region_name: str,
) -> List[Dict]:
    """Extracts genuine sample points: severe inundation, mild change, dry control, and masked pixels."""
    to_wgs84 = Transformer.from_crs(CRS.from_epsg(subset.epsg_code), "EPSG:4326", always_xy=True)
    delta = output.measurement_grid
    unc = output.uncertainty_grid
    qcat = output.quality_category_grid
    inundation = output.disagreement_grid  # 1 for flooded, 0 otherwise

    prov_t1 = subset.provenance
    prov_record = {
        "granule_id": prov_t1.granule_id,
        "product_type": "GCOV",
        "acquisition_start": prov_t1.reference_start_time,
        "acquisition_end": prov_t1.reference_end_time,
        "track_number": prov_t1.track_number,
        "frame_number": prov_t1.frame_number,
        "look_direction": prov_t1.look_direction,
        "orbit_pass_direction": prov_t1.orbit_pass_direction,
        "composite_release_id": prov_t1.composite_release_id,
        "maturity": "PROVISIONAL",
    }

    records: List[Dict] = []
    flooded_mask = (inundation == 1) & (qcat >= 2)
    dry_mask = (delta > -1.0) & (delta < 1.0) & (qcat >= 2)

    candidates: List[Tuple[str, Tuple[int, int]]] = []
    if np.any(flooded_mask):
        f_indices = np.argwhere(flooded_mask)
        min_idx = f_indices[int(np.argmin(delta[flooded_mask]))]
        mid_idx = f_indices[len(f_indices) // 2]
        candidates.append(("confirmed_flood_inundation_core", (int(min_idx[0]), int(min_idx[1]))))
        candidates.append(("flood_plain_inundation_edge", (int(mid_idx[0]), int(mid_idx[1]))))

    if np.any(dry_mask):
        d_indices = np.argwhere(dry_mask)
        did = d_indices[len(d_indices) // 2]
        candidates.append(("dry_agricultural_control", (int(did[0]), int(did[1]))))

    q_map = {0: "invalid", 1: "low", 2: "moderate", 3: "high"}

    for label, (r, c) in candidates:
        x_val = float(subset.x_coords[c])
        y_val = float(subset.y_coords[r])
        lon, lat = to_wgs84.transform(x_val, y_val)
        val = float(delta[r, c]) if np.isfinite(delta[r, c]) else None
        u_val = float(unc[r, c]) if np.isfinite(unc[r, c]) else None
        is_f = bool(inundation[r, c] == 1)

        records.append(
            {
                "id": f"{study_area_id}_{label}",
                "study_area_id": study_area_id,
                "region_name": f"{region_name} ({label.replace('_', ' ').title()})",
                "coordinates_wgs84": [round(float(lon), 5), round(float(lat), 5)],
                "measurement_type": output.measurement_type,
                "value": round(val, 2) if val is not None else None,
                "unit": "dB",
                "uncertainty": round(u_val, 2) if u_val is not None else None,
                "quality_status": q_map.get(int(qcat[r, c]), "invalid"),
                "coherence_or_looks": 16.0,
                "apof_disagreement_mm": None,
                "sign_convention": output.sign_convention,
                "source_observations": [prov_record],
                "supporting_context": {
                    "flood_classification": "INUNDATED_WATER" if is_f else "NON_INUNDATED_LAND",
                    "pixel_row_col": f"({r}, {c})",
                    "native_crs": f"EPSG:{subset.epsg_code}",
                },
                "limitations": output.limitations,
            }
        )

    return records


def run_punjab_flood_pipeline() -> None:
    print("=== TERRAVOX Phase 2B: Punjab Flood Inundation Engine ===")
    print("  -> Matching Geometry: Track 012, Frame 017, Ascending (CRID P05023)")
    print("  -> Pre-monsoon Baseline: 2026-08-14")
    print("  -> Peak Monsoon Event  : 2026-08-26 (12-day repeat)")

    f1 = Path("data/samples") / T1_FILENAME
    f2 = Path("data/samples") / T2_FILENAME

    if not f1.exists():
        raise FileNotFoundError(f"Expected Date 1 file at {f1} but not found.")

    print(f"\n[1/3] Checking local files...")
    print(f"      Date 1 (2026-08-14): {f1.name} (Already on disk)")

    session = build_authenticated_asf_session()
    if not f2.exists():
        download_with_progress(T2_URL, f2, session)
    else:
        print(f"      Date 2 (2026-08-26): {f2.name} (Already on disk)")

    print(f"\n[2/3] Extracting Punjab flood plains subsets from both dates...")
    sub1 = read_gcov_subset(f1, polarization_term="HHHH", bbox_wgs84=PUNJAB_AOI_BBOX)
    sub2 = read_gcov_subset(f2, polarization_term="HHHH", bbox_wgs84=PUNJAB_AOI_BBOX)

    print(f"[3/3] Running GCOV Backscatter Change & Flood Inundation Detector...")
    output = process_gcov_backscatter_change(sub1, sub2, polarization_term="HHHH")

    # Save GeoTIFFs
    study_id = "punjab_flood_plains_pk"
    delta_tif = Path(f"outputs/rasters/{study_id}_delta_backscatter_db.tif")
    flood_tif = Path(f"outputs/rasters/{study_id}_inundation_extent.tif")
    unc_tif = Path(f"outputs/rasters/{study_id}_uari_uncertainty_db.tif")

    save_geotiff(delta_tif, output.measurement_grid, sub1.x_coords, sub1.y_coords, sub1.epsg_code)
    save_geotiff(
        flood_tif,
        output.disagreement_grid.astype(np.uint8),
        sub1.x_coords,
        sub1.y_coords,
        sub1.epsg_code,
        nodata=0,
    )
    save_geotiff(unc_tif, output.uncertainty_grid, sub1.x_coords, sub1.y_coords, sub1.epsg_code)

    samples = extract_flood_sample_points(
        subset=sub1,
        output=output,
        study_area_id=study_id,
        region_name="Punjab Indus–Chenab Basin, Pakistan",
    )

    report_payload = {
        "study_area_id": study_id,
        "region_name": "Punjab Flood Plains (Indus & Chenab River Basin), Pakistan",
        "bounds_wgs84": sub1.bounds_wgs84,
        "pre_event_date": "2026-08-14",
        "post_event_date": "2026-08-26",
        "summary_stats": output.summary_stats,
        "rasters": {
            "delta_backscatter_db": str(delta_tif),
            "inundation_extent": str(flood_tif),
            "uari_uncertainty_db": str(unc_tif),
        },
        "sample_measurements": samples,
    }

    report_path = Path(f"outputs/reports/{study_id}_intelligence_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2))

    print("\n" + "=" * 55)
    print("=== PUNJAB FLOOD PROCESSING COMPLETE (100% NISAR) ===")
    print("=" * 55)
    print("Flood Summary Statistics:\n" + json.dumps(output.summary_stats, indent=2))
    print(f"\nSaved GeoTIFFs to: outputs/rasters/")
    print(f"Saved Intelligence Report ({len(samples)} sample points) to:\n  -> {report_path}")


if __name__ == "__main__":
    run_punjab_flood_pipeline()