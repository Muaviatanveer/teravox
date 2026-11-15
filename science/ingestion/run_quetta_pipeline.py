"""
TERRAVOX — Phase 2: High-Speed Quetta–Mastung GUNW Pipeline
Downloads granule directly with a live progress bar, then extracts the Quetta subset.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

import asf_search as asf
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.transform import from_bounds

from science.engine.processors import ScientificLayerOutput, process_gunw_deformation_and_apof
from science.ingestion.nisar_reader import (
    GeocodedGridSubset,
    build_authenticated_asf_session,
    read_gunw_subset,
)


def download_with_progress(url: str, dest_path: Path, session: asf.ASFSession) -> Path:
    """Fast stream-download with a live MB progress bar."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".downloading")

    print(f"\n[1/3] Downloading NISAR GUNW granule directly from NASA Earthdata Cloud...")
    print(f"      Destination: {dest_path.name}")

    resp = session.get(url, stream=True, timeout=90)
    resp.raise_for_status()

    total_bytes = int(resp.headers.get("Content-Length", 0))
    total_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0

    downloaded = 0
    chunk_size = 4 * 1024 * 1024  # 4 MB chunks for high throughput

    with open(temp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_mb > 0:
                    done_mb = downloaded / (1024 * 1024)
                    pct = (downloaded / total_bytes) * 100
                    bar = "=" * int(pct // 4) + "-" * (25 - int(pct // 4))
                    sys.stdout.write(f"\r      [{bar}] {pct:5.1f}%  ({done_mb:.1f} / {total_mb:.1f} MB)")
                    sys.stdout.flush()

    sys.stdout.write("\n")
    temp_path.rename(dest_path)
    print(f"      Download complete ({dest_path.stat().st_size / (1024*1024):.1f} MB saved to disk).\n")
    return dest_path


def save_geotiff(
    out_path: Path,
    array: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    epsg_code: int,
    nodata: float = np.nan,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    height, width = array.shape
    dx = abs(float(x_coords[1] - x_coords[0])) if len(x_coords) > 1 else 80.0
    dy = abs(float(y_coords[1] - y_coords[0])) if len(y_coords) > 1 else 80.0

    west = float(np.min(x_coords)) - dx / 2.0
    east = float(np.max(x_coords)) + dx / 2.0
    south = float(np.min(y_coords)) - dy / 2.0
    north = float(np.max(y_coords)) + dy / 2.0

    data_to_write = array if y_coords[0] > y_coords[-1] else np.flipud(array)
    transform = from_bounds(west, south, east, north, width, height)

    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data_to_write.dtype,
        crs=CRS.from_epsg(epsg_code),
        transform=transform,
        nodata=nodata,
        compress="deflate",
    ) as dst:
        dst.write(data_to_write, 1)


def extract_genuine_sample_points(
    subset: GeocodedGridSubset,
    output: ScientificLayerOutput,
    study_area_id: str,
    region_name: str,
    maturity: str,
) -> List[Dict]:
    to_wgs84 = Transformer.from_crs(CRS.from_epsg(subset.epsg_code), "EPSG:4326", always_xy=True)
    disp = output.measurement_grid
    unc = output.uncertainty_grid
    qcat = output.quality_category_grid
    coh = subset.data["coherenceMagnitude"]
    disagree = output.disagreement_grid

    prov = subset.provenance
    prov_record = {
        "granule_id": prov.granule_id,
        "product_type": "GUNW",
        "acquisition_start": prov.reference_start_time,
        "acquisition_end": prov.secondary_start_time or prov.reference_end_time,
        "track_number": prov.track_number,
        "frame_number": prov.frame_number,
        "look_direction": prov.look_direction,
        "orbit_pass_direction": prov.orbit_pass_direction,
        "composite_release_id": prov.composite_release_id,
        "maturity": maturity,
    }

    records: List[Dict] = []
    high_mask = qcat == 3
    mod_mask = qcat == 2
    low_mask = qcat == 1

    candidates: List[Tuple[str, Tuple[int, int]]] = []
    if np.any(high_mask):
        high_indices = np.argwhere(high_mask)
        high_vals = disp[high_mask]
        min_idx = high_indices[int(np.argmin(high_vals))]
        max_idx = high_indices[int(np.argmax(high_vals))]
        med_val = np.median(high_vals)
        med_idx = high_indices[int(np.argmin(np.abs(high_vals - med_val)))]
        candidates.append(("peak_negative_los", (int(min_idx[0]), int(min_idx[1]))))
        candidates.append(("peak_positive_los", (int(max_idx[0]), int(max_idx[1]))))
        candidates.append(("median_reference_los", (int(med_idx[0]), int(med_idx[1]))))

    if np.any(mod_mask):
        mod_indices = np.argwhere(mod_mask)
        mid = mod_indices[len(mod_indices) // 2]
        candidates.append(("moderate_quality_sample", (int(mid[0]), int(mid[1]))))

    if np.any(low_mask):
        low_indices = np.argwhere(low_mask)
        lid = low_indices[len(low_indices) // 2]
        candidates.append(("low_coherence_warning_sample", (int(lid[0]), int(lid[1]))))

    q_map = {0: "invalid", 1: "low", 2: "moderate", 3: "high"}

    for label, (r, c) in candidates:
        x_val = float(subset.x_coords[c])
        y_val = float(subset.y_coords[r])
        lon, lat = to_wgs84.transform(x_val, y_val)
        val = float(disp[r, c]) if np.isfinite(disp[r, c]) else None
        u_val = float(unc[r, c]) if np.isfinite(unc[r, c]) else None
        c_val = float(coh[r, c]) if np.isfinite(coh[r, c]) else None
        d_val = float(disagree[r, c]) if (disagree is not None and np.isfinite(disagree[r, c])) else None

        records.append(
            {
                "id": f"{study_area_id}_{label}",
                "study_area_id": study_area_id,
                "region_name": f"{region_name} ({label.replace('_', ' ').title()})",
                "coordinates_wgs84": [round(float(lon), 5), round(float(lat), 5)],
                "measurement_type": output.measurement_type,
                "value": round(val, 3) if val is not None else None,
                "unit": "mm",
                "uncertainty": round(u_val, 3) if u_val is not None else None,
                "quality_status": q_map.get(int(qcat[r, c]), "invalid"),
                "coherence_or_looks": round(c_val, 3) if c_val is not None else None,
                "apof_disagreement_mm": round(d_val, 3) if d_val is not None else None,
                "sign_convention": output.sign_convention,
                "source_observations": [prov_record],
                "supporting_context": {
                    "pixel_row_col": f"({r}, {c})",
                    "native_crs": f"EPSG:{subset.epsg_code}",
                    "wavelength_m": f"{prov.wavelength_m:.5f} m",
                },
                "limitations": output.limitations,
            }
        )

    return records


def run_locked_pipeline() -> None:
    gate_path = Path("data/metadata/study_area_gate_report.json")
    if not gate_path.exists():
        raise FileNotFoundError("Run verify_study_area.py first to generate study_area_gate_report.json")

    gate = json.loads(gate_path.read_text())
    lock = gate["recommended_lock"]
    region_id = lock["region_id"]
    region_info = gate["regions"][region_id]
    bbox = tuple(region_info["bbox_wgs84"])
    top_stack = lock["top_stack_summary"]
    url = top_stack["download_urls"][0]
    maturity = top_stack["maturity_tier"]

    filename = url.split("/")[-1]
    local_file = Path("data/samples") / filename

    print(f"=== TERRAVOX Phase 2: Processing Locked Study Area '{region_id}' ===")
    session = build_authenticated_asf_session()

    # Step 1: If not already downloaded, download directly with progress
    if not local_file.exists():
        download_with_progress(url, local_file, session)
    else:
        print(f"\n[1/3] Using already downloaded local granule: {local_file.name}")

    # Step 2: Read Quetta subset from the local HDF5 file (instant)
    print(f"[2/3] Extracting Quetta–Mastung spatial subset from local file...")
    subset = read_gunw_subset(source=local_file, polarization="HH", bbox_wgs84=bbox)

    # Step 3: Run InSAR LOS physics + UARI uncertainty + APOF fusion
    print(f"[3/3] Running GUNW LOS Displacement + UARI + APOF scientific processor...")
    output = process_gunw_deformation_and_apof(subset)

    # Export GeoTIFFs
    disp_tif = Path(f"outputs/rasters/{region_id}_los_displacement_mm.tif")
    unc_tif = Path(f"outputs/rasters/{region_id}_uari_uncertainty_mm.tif")
    qual_tif = Path(f"outputs/rasters/{region_id}_quality_category.tif")

    save_geotiff(disp_tif, output.measurement_grid, subset.x_coords, subset.y_coords, subset.epsg_code)
    save_geotiff(unc_tif, output.uncertainty_grid, subset.x_coords, subset.y_coords, subset.epsg_code)
    save_geotiff(
        qual_tif,
        output.quality_category_grid.astype(np.uint8),
        subset.x_coords,
        subset.y_coords,
        subset.epsg_code,
        nodata=0,
    )

    # Generate genuine ground measurement records
    samples = extract_genuine_sample_points(
        subset=subset,
        output=output,
        study_area_id=region_id,
        region_name="Quetta–Mastung Valley, Balochistan",
        maturity=maturity,
    )

    report_payload = {
        "study_area_id": region_id,
        "bounds_wgs84": subset.bounds_wgs84,
        "provenance": asdict(subset.provenance),
        "summary_stats": output.summary_stats,
        "rasters": {
            "los_displacement_mm": str(disp_tif),
            "uari_uncertainty_mm": str(unc_tif),
            "quality_category": str(qual_tif),
        },
        "sample_measurements": samples,
    }

    report_path = Path(f"outputs/reports/{region_id}_intelligence_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2))

    print("\n" + "=" * 50)
    print("=== PROCESSING COMPLETE (100% Genuine NISAR Data) ===")
    print("=" * 50)
    print("Summary Statistics:\n" + json.dumps(output.summary_stats, indent=2))
    print(f"\nSaved GeoTIFFs to: outputs/rasters/")
    print(f"Saved Intelligence Report ({len(samples)} genuine sample points) to:\n  -> {report_path}")


if __name__ == "__main__":
    run_locked_pipeline()