"""
TERRAVOX — Phase 1: Fast Study-Area Selection Gate & NISAR Coverage Verifier
Performs 1 batched ASF query per candidate region with live progress output
and parses official NISAR Level-2 granule naming conventions for Track/Frame/CRID.
"""

from __future__ import annotations

import warnings

# Silence macOS LibreSSL 2.8.3 warning from urllib3 v2 before importing asf_search
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import asf_search as asf
from shapely.geometry import box

# Candidate pilot regions (Bounding Boxes: [min_lon, min_lat, max_lon, max_lat])
CANDIDATE_REGIONS: Dict[str, Tuple[float, float, float, float]] = {
    "quetta_mastung_pk": (66.45, 29.65, 67.35, 30.45),
    "kacchi_indus_plains_pk": (67.40, 27.50, 68.60, 29.10),
    "central_valley_ca_calval": (-120.20, 35.80, -119.10, 36.80),
}

# Official NISAR L2 Granule Name Pattern:
# NISAR_IL_PT_PROD_CYL_REL_P_FRM_MODE_POLE_S_..._CRID_A_C_LOC_CTR
NISAR_NAME_REGEX = re.compile(
    r"^NISAR_(?P<level>L\d)_(?P<prod_config>[A-Z]{2})_(?P<product_type>[A-Z0-9]{4})_"
    r"(?P<cycle>\d{3})_(?P<track>\d{3})_(?P<pass_dir>[AD])_(?P<frame>\d{3})_"
    r"(?P<mode>\d{4})_(?P<pol>[A-Z0-9]{4})_[A-Z]_"
    r"(?P<timestamps>.+)_"
    r"(?P<crid>[A-Z]\d{5})_[A-Z]_[A-Z]_[A-Z]_\d{3}$"
)


@dataclass
class GranuleSummary:
    granule_id: str
    product_type: str
    maturity_tier: str
    crid: str
    acquisition_start: str
    acquisition_stop: str
    track: Optional[int]
    frame: Optional[int]
    flight_direction: Optional[str]
    polarization: Optional[str]
    bytes_size: Optional[int]
    download_url: str
    s3_urls: List[str] = field(default_factory=list)


@dataclass
class CompatibleStack:
    product_type: str
    maturity_tier: str
    crid_baseline: str
    track: Optional[int]
    frame: Optional[int]
    flight_direction: Optional[str]
    polarization: Optional[str]
    granule_count: int
    acquisition_dates: List[str]
    granules: List[GranuleSummary]


def parse_nisar_granule_id(granule_id: str) -> Dict[str, Optional[str]]:
    """
    Extracts product_type, track, pass_dir, frame, polarization, CRID, and inferred
    maturity tier directly from the official NISAR granule naming convention.
    """
    clean_id = granule_id.replace(".h5", "").replace(".nc", "").strip()
    match = NISAR_NAME_REGEX.match(clean_id)
    if not match:
        # Fallback token split if slightly non-standard
        parts = clean_id.split("_")
        if len(parts) >= 12 and parts[0] == "NISAR":
            crid = parts[-5] if len(parts) >= 16 else "UNKNOWN"
            return {
                "product_type": parts[3],
                "track": parts[5] if parts[5].isdigit() else None,
                "pass_dir": "ASCENDING" if parts[6] == "A" else ("DESCENDING" if parts[6] == "D" else None),
                "frame": parts[7] if parts[7].isdigit() else None,
                "pol": parts[9],
                "crid": crid,
                "maturity": _infer_maturity_from_crid(crid),
            }
        return {}

    gd = match.groupdict()
    crid = gd["crid"]
    return {
        "product_type": gd["product_type"],
        "track": gd["track"],
        "pass_dir": "ASCENDING" if gd["pass_dir"] == "A" else "DESCENDING",
        "frame": gd["frame"],
        "pol": gd["pol"],
        "crid": crid,
        "maturity": _infer_maturity_from_crid(crid),
    }


def _infer_maturity_from_crid(crid: str) -> str:
    """
    NISAR CRID prefix convention:
    - R***** : Validated / Release science baseline
    - P***** : Provisional baseline
    - T***** / X***** : Beta / Test / CalVal baseline
    """
    if not crid or crid == "UNKNOWN":
        return "UNKNOWN"
    prefix = crid[0].upper()
    if prefix == "R":
        return "VALIDATED"
    if prefix == "P":
        return "PROVISIONAL"
    if prefix in ("T", "X"):
        return "BETA"
    return "UNKNOWN"


def search_nisar_for_bbox(
    region_id: str,
    bbox: Tuple[float, float, float, float],
    product_types: List[str] = ["GUNW", "GOFF", "GCOV", "SME2"],
    max_results: int = 500,
) -> List[CompatibleStack]:
    """
    Performs a single batched ASF Search API call for the region and groups results
    into strictly compatible stacks (matching Product, Maturity, CRID, Track, Frame, Pass, Pol).
    """
    wkt_aoi = box(*bbox).wkt
    print(f"  -> Querying ASF DAAC for '{region_id}' {bbox} ...", flush=True)

    results = asf.search(
        dataset=asf.DATASET.NISAR,
        processingLevel=product_types,
        intersectsWith=wkt_aoi,
        maxResults=max_results,
    )
    print(f"     Retrieved {len(results)} raw NISAR granule(s) for '{region_id}'.", flush=True)

    grouped: Dict[Tuple, List[GranuleSummary]] = defaultdict(list)

    for item in results:
        props = item.properties
        granule_id = str(props.get("sceneName") or props.get("fileID") or "UNKNOWN")
        parsed = parse_nisar_granule_id(granule_id)

        prod_type = parsed.get("product_type") or str(props.get("processingLevel") or "UNKNOWN")
        track_str = parsed.get("track") or props.get("pathNumber")
        frame_str = parsed.get("frame") or props.get("frameNumber")
        track = int(track_str) if track_str is not None and str(track_str).isdigit() else None
        frame = int(frame_str) if frame_str is not None and str(frame_str).isdigit() else None
        direction = parsed.get("pass_dir") or props.get("flightDirection")
        pol = parsed.get("pol") or str(props.get("polarization") or "")
        crid = parsed.get("crid") or "UNKNOWN"
        maturity = str(props.get("dataMaturity") or parsed.get("maturity") or "UNKNOWN")

        summary = GranuleSummary(
            granule_id=granule_id,
            product_type=prod_type,
            maturity_tier=maturity,
            crid=crid,
            acquisition_start=str(props.get("startTime", "")),
            acquisition_stop=str(props.get("stopTime", "")),
            track=track,
            frame=frame,
            flight_direction=direction,
            polarization=pol,
            bytes_size=props.get("bytes"),
            download_url=str(props.get("url", "")),
            s3_urls=props.get("s3Urls", []) if isinstance(props.get("s3Urls"), list) else [],
        )

        # Strict scientific compatibility key: never mix product types, maturity, CRID, track, frame, or direction
        stack_key = (
            summary.product_type,
            summary.maturity_tier,
            summary.crid,
            summary.track,
            summary.frame,
            summary.flight_direction,
            summary.polarization,
        )
        grouped[stack_key].append(summary)

    stacks: List[CompatibleStack] = []
    for (ptype, mat, crid, trk, frm, fdir, pol), items in grouped.items():
        # Deduplicate by granule_id and sort chronologically
        unique_items = {g.granule_id: g for g in items}
        sorted_items = sorted(unique_items.values(), key=lambda g: g.acquisition_start)
        stacks.append(
            CompatibleStack(
                product_type=ptype,
                maturity_tier=mat,
                crid_baseline=crid,
                track=trk,
                frame=frm,
                flight_direction=fdir,
                polarization=pol,
                granule_count=len(sorted_items),
                acquisition_dates=[g.acquisition_start for g in sorted_items],
                granules=sorted_items,
            )
        )

    # Sort stacks: prefer VALIDATED > PROVISIONAL > BETA, and larger granule_count first
    maturity_rank = {"VALIDATED": 3, "PROVISIONAL": 2, "BETA": 1, "UNKNOWN": 0}
    stacks.sort(
        key=lambda s: (maturity_rank.get(s.maturity_tier, 0), s.granule_count),
        reverse=True,
    )
    return stacks


def evaluate_study_area_gate(output_path: Path) -> Dict:
    print("=== TERRAVOX Phase 1: Study-Area Selection Gate ===", flush=True)
    report: Dict = {"regions": {}, "recommended_lock": None}

    for region_id, bbox in CANDIDATE_REGIONS.items():
        stacks = search_nisar_for_bbox(region_id, bbox)
        gunw_stacks = [s for s in stacks if s.product_type == "GUNW" and s.granule_count >= 1]
        gcov_pairs = [s for s in stacks if s.product_type == "GCOV" and s.granule_count >= 2]
        gcov_single = [s for s in stacks if s.product_type == "GCOV" and s.granule_count == 1]

        decision = "INSUFFICIENT_COMPATIBLE_DATA"
        primary_pipeline = None
        selected_stack = None

        if gunw_stacks:
            decision = "LOCK_OPTION_A_DEFORMATION_GUNW"
            primary_pipeline = "GUNW_DEFORMATION_AND_APOF"
            selected_stack = asdict(gunw_stacks[0])
        elif gcov_pairs:
            decision = "LOCK_OPTION_B_BACKSCATTER_GCOV"
            primary_pipeline = "GCOV_BACKSCATTER_CHANGE"
            selected_stack = asdict(gcov_pairs[0])

        print(
            f"     [{region_id}] GUNW stacks: {len(gunw_stacks)} | "
            f"GCOV repeat stacks (>=2 dates): {len(gcov_pairs)} | "
            f"GCOV single scenes: {len(gcov_single)} -> Decision: {decision}",
            flush=True,
        )

        report["regions"][region_id] = {
            "bbox_wgs84": bbox,
            "decision": decision,
            "primary_pipeline": primary_pipeline,
            "compatible_gunw_stacks": len(gunw_stacks),
            "compatible_gcov_repeat_stacks": len(gcov_pairs),
            "top_recommended_stack": selected_stack,
            "stacks": [asdict(s) for s in stacks],
        }

        if report["recommended_lock"] is None and primary_pipeline is not None:
            report["recommended_lock"] = {
                "region_id": region_id,
                "decision": decision,
                "primary_pipeline": primary_pipeline,
                "top_stack_summary": {
                    "product_type": selected_stack["product_type"],
                    "maturity_tier": selected_stack["maturity_tier"],
                    "crid_baseline": selected_stack["crid_baseline"],
                    "track": selected_stack["track"],
                    "frame": selected_stack["frame"],
                    "flight_direction": selected_stack["flight_direction"],
                    "granule_count": selected_stack["granule_count"],
                    "acquisition_dates": selected_stack["acquisition_dates"],
                    "download_urls": [g["download_url"] for g in selected_stack["granules"][:2]],
                },
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    gate_file = Path("data/metadata/study_area_gate_report.json")
    result = evaluate_study_area_gate(gate_file)
    print(f"\nGate report saved to: {gate_file}", flush=True)
    print("Recommended Lock:\n" + json.dumps(result["recommended_lock"], indent=2), flush=True)
