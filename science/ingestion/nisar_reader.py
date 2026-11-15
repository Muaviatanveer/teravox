"""
TERRAVOX — Genuine NISAR L2 HDF5 Reader & HTTP Range Subsetter
Supports both local .h5 files and remote HTTP Range streaming from ASF Earthdata Cloud.
"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")

import io
import os
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import asf_search as asf
import h5py
import numpy as np
from pyproj import CRS, Transformer
from scipy.interpolate import RegularGridInterpolator

SPEED_OF_LIGHT_MPS = 299_792_458.0


@dataclass(frozen=True)
class NISARProvenance:
    granule_id: str
    product_type: str
    radar_band: str
    reference_start_time: str
    reference_end_time: str
    secondary_start_time: Optional[str]
    secondary_end_time: Optional[str]
    track_number: int
    frame_number: int
    look_direction: str
    orbit_pass_direction: str
    product_version: str
    composite_release_id: str
    center_frequency_hz: float
    wavelength_m: float
    epsg_code: int


@dataclass
class GeocodedGridSubset:
    data: Dict[str, np.ndarray]
    x_coords: np.ndarray
    y_coords: np.ndarray
    epsg_code: int
    bounds_wgs84: Tuple[float, float, float, float]
    provenance: NISARProvenance


class CachedRangeReader(io.RawIOBase):
    """
    File-like HTTP Range reader with 4 MB block caching for h5py.
    Streams only the required spatial subset chunks from ASF Earthdata Cloud.
    """

    def __init__(self, url: str, session: asf.ASFSession, block_size: int = 4 * 1024 * 1024):
        super().__init__()
        self.url = url
        self.session = session
        self.block_size = block_size
        self.pos = 0
        self.cache: Dict[int, bytes] = {}
        self.bytes_downloaded = 0

        # Resolve Earthdata OAuth redirect and determine exact file size via 1-byte Range request
        resp = self.session.get(url, headers={"Range": "bytes=0-0"}, stream=True, timeout=60)
        resp.raise_for_status()
        self.resolved_url = resp.url
        content_range = resp.headers.get("Content-Range", "")
        if "/" in content_range:
            self.size = int(content_range.split("/")[-1])
        else:
            self.size = int(resp.headers.get("Content-Length", 0))
        resp.close()
        if self.size <= 0:
            raise RuntimeError(f"Could not determine Content-Length/Content-Range for {url}")

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        return self.pos

    def tell(self) -> int:
        return self.pos

    def _get_block(self, block_idx: int) -> bytes:
        if block_idx not in self.cache:
            start = block_idx * self.block_size
            end = min(start + self.block_size - 1, self.size - 1)
            headers = {"Range": f"bytes={start}-{end}"}
            resp = self.session.get(self.resolved_url, headers=headers, timeout=60)
            if resp.status_code in (401, 403):
                # Re-resolve redirect if signed cloud URL expired
                resp = self.session.get(self.url, headers=headers, timeout=60)
                self.resolved_url = resp.url
            resp.raise_for_status()
            data = resp.content
            self.bytes_downloaded += len(data)
            if len(self.cache) > 64:
                # Evict oldest cached block to cap memory usage
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            self.cache[block_idx] = data
        return self.cache[block_idx]

    def readinto(self, b: bytearray) -> int:
        if self.pos >= self.size:
            return 0
        to_read = min(len(b), self.size - self.pos)
        written = 0
        while written < to_read:
            block_idx = self.pos // self.block_size
            block_offset = self.pos % self.block_size
            block_data = self._get_block(block_idx)
            available = len(block_data) - block_offset
            if available <= 0:
                break
            chunk_len = min(to_read - written, available)
            b[written : written + chunk_len] = block_data[block_offset : block_offset + chunk_len]
            self.pos += chunk_len
            written += chunk_len
        return written


def build_authenticated_asf_session() -> asf.ASFSession:
    """
    Authenticates with NASA Earthdata Login via:
    1. EARTHDATA_TOKEN environment variable
    2. EARTHDATA_USERNAME + EARTHDATA_PASSWORD environment variables
    3. ~/.netrc file (machine urs.earthdata.nasa.gov)
    4. Interactive terminal prompt fallback
    """
    session = asf.ASFSession()
    # Ensure modern NASA Earthdata session cookies are accepted
    for cname in ("asf-urs", "urs-access-token", "urs-user-id", "_urs-gui_session"):
        if cname not in session.auth_cookie_names:
            session.auth_cookie_names.append(cname)

    token = os.getenv("EARTHDATA_TOKEN")
    user = os.getenv("EARTHDATA_USERNAME")
    pw = os.getenv("EARTHDATA_PASSWORD")

    if token:
        try:
            return session.auth_with_token(token)
        except asf.exceptions.ASFAuthenticationError as err:
            raise RuntimeError(
                f"\n[NASA Earthdata Action Required]: Token verification failed (or ASF EULA not approved yet).\n"
                f"Authorize ASF here: https://urs.earthdata.nasa.gov/approve_app?client_id=BO_n7nTIlMljdvU6kRRB3g"
            ) from err

    if user and pw:
        try:
            return session.auth_with_creds(user, pw)
        except asf.exceptions.ASFAuthenticationError as err:
            import requests

            check = requests.get(
                f"https://{session.edl_host}/oauth/authorize?client_id={session.edl_client_id}&response_type=code&redirect_uri=https://{session.asf_auth_host}/login",
                auth=(user, pw),
                allow_redirects=False,
            )
            loc = check.headers.get("location", "")
            if "resolution_url" in loc or "approve_app" in loc:
                raise RuntimeError(
                    f"\n[NASA Earthdata Action Required]: You must authorize Alaska Satellite Facility (ASF) once in your browser.\n"
                    f"Please visit: https://urs.earthdata.nasa.gov/approve_app?client_id={session.edl_client_id}\n"
                    f"and click 'Approve' / 'Authorize'."
                ) from err
            raise

    netrc_path = Path.home() / ".netrc"
    if netrc_path.exists() and "urs.earthdata.nasa.gov" in netrc_path.read_text():
        try:
            return session.auth_with_creds(None, None)
        except Exception:
            pass

    print("\nNASA Earthdata Login required to stream/download NISAR HDF5 granules from ASF DAAC.")
    user_input = input("Earthdata Username (or press Enter to use Bearer Token): ").strip()
    if user_input:
        pw_input = getpass("Earthdata Password: ")
        return session.auth_with_creds(user_input, pw_input)
    token_input = getpass("Earthdata Bearer Token: ").strip()
    return session.auth_with_token(token_input)


def _decode_h5_scalar(dataset: h5py.Dataset) -> str:
    val = dataset[()]
    if isinstance(val, (bytes, np.bytes_)):
        return val.decode("utf-8").strip()
    if isinstance(val, np.ndarray):
        if val.size == 1:
            item = val.item()
            return item.decode("utf-8").strip() if isinstance(item, (bytes, np.bytes_)) else str(item)
        if val.size > 0:
            first = val.flat[0]
            return first.decode("utf-8").strip() if isinstance(first, (bytes, np.bytes_)) else str(first)
    return str(val)


def _find_center_frequency(h5_file: h5py.File, product_type: str) -> float:
    candidate_paths = [
        f"/science/LSAR/{product_type}/grids/frequencyA/centerFrequency",
        f"/science/LSAR/{product_type}/grids/frequencyA/unwrappedInterferogram/centerFrequency",
        f"/science/LSAR/{product_type}/metadata/sourceData/swaths/frequencyA/centerFrequency",
        f"/science/LSAR/{product_type}/metadata/processingInformation/parameters/frequencyA/centerFrequency",
    ]
    for path in candidate_paths:
        if path in h5_file:
            return float(np.asarray(h5_file[path][()]).flat[0])
    # Fallback L-band NISAR Frequency A center frequency (1.257 GHz) if not at standard path
    return 1_257_500_000.0


def extract_provenance(h5_file: h5py.File, fallback_granule_id: str = "UNKNOWN") -> NISARProvenance:
    """Extracts official NISAR provenance from /science/LSAR/identification."""
    ident = h5_file["/science/LSAR/identification"]
    product_type = _decode_h5_scalar(ident["productType"])

    if "referenceZeroDopplerStartTime" in ident:
        ref_start = _decode_h5_scalar(ident["referenceZeroDopplerStartTime"])
        ref_end = _decode_h5_scalar(ident["referenceZeroDopplerEndTime"])
        sec_start = _decode_h5_scalar(ident["secondaryZeroDopplerStartTime"])
        sec_end = _decode_h5_scalar(ident["secondaryZeroDopplerEndTime"])
    else:
        ref_start = _decode_h5_scalar(ident["zeroDopplerStartTime"])
        ref_end = _decode_h5_scalar(ident["zeroDopplerEndTime"])
        sec_start = None
        sec_end = None

    center_freq_hz = _find_center_frequency(h5_file, product_type)

    grid_base = f"/science/LSAR/{product_type}/grids/frequencyA"
    if product_type == "GUNW":
        proj_ds = h5_file[f"{grid_base}/unwrappedInterferogram/projection"]
    else:
        proj_ds = h5_file[f"{grid_base}/projection"]
    epsg_code = int(np.asarray(proj_ds[()]).flat[0])

    granule_id = (
        _decode_h5_scalar(ident["granuleId"])
        if "granuleId" in ident
        else fallback_granule_id
    )

    return NISARProvenance(
        granule_id=granule_id,
        product_type=product_type,
        radar_band=_decode_h5_scalar(ident["radarBand"]) if "radarBand" in ident else "L",
        reference_start_time=ref_start,
        reference_end_time=ref_end,
        secondary_start_time=sec_start,
        secondary_end_time=sec_end,
        track_number=int(np.asarray(ident["trackNumber"][()]).flat[0]),
        frame_number=int(np.asarray(ident["frameNumber"][()]).flat[0]),
        look_direction=_decode_h5_scalar(ident["lookDirection"]),
        orbit_pass_direction=_decode_h5_scalar(ident["orbitPassDirection"]),
        product_version=_decode_h5_scalar(ident["productVersion"]) if "productVersion" in ident else "1.0",
        composite_release_id=(
            _decode_h5_scalar(ident["compositeReleaseId"])
            if "compositeReleaseId" in ident
            else "UNKNOWN"
        ),
        center_frequency_hz=center_freq_hz,
        wavelength_m=SPEED_OF_LIGHT_MPS / center_freq_hz,
        epsg_code=epsg_code,
    )


def assert_compatible_pair(prov_a: NISARProvenance, prov_b: NISARProvenance) -> None:
    """Scientific Data Rule: Never combine incompatible products or baselines."""
    errors = []
    if prov_a.product_type != prov_b.product_type:
        errors.append(f"Product type mismatch: {prov_a.product_type} vs {prov_b.product_type}")
    if prov_a.track_number != prov_b.track_number or prov_a.frame_number != prov_b.frame_number:
        errors.append(
            f"Track/Frame mismatch: ({prov_a.track_number}, {prov_a.frame_number}) "
            f"vs ({prov_b.track_number}, {prov_b.frame_number})"
        )
    if prov_a.look_direction != prov_b.look_direction:
        errors.append(f"Look direction mismatch: {prov_a.look_direction} vs {prov_b.look_direction}")
    if prov_a.composite_release_id != prov_b.composite_release_id:
        errors.append(
            f"Processing baseline (CRID) mismatch: {prov_a.composite_release_id} "
            f"vs {prov_b.composite_release_id}"
        )
    if errors:
        raise ValueError("Incompatible NISAR observation pair rejected: " + "; ".join(errors))


def _compute_pixel_slice(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    epsg_code: int,
    bbox_wgs84: Optional[Tuple[float, float, float, float]],
) -> Tuple[slice, slice, Tuple[float, float, float, float]]:
    crs_native = CRS.from_epsg(epsg_code)
    to_native = Transformer.from_crs("EPSG:4326", crs_native, always_xy=True)
    to_wgs84 = Transformer.from_crs(crs_native, "EPSG:4326", always_xy=True)

    if bbox_wgs84 is None:
        x_sl, y_sl = slice(None), slice(None)
    else:
        min_lon, min_lat, max_lon, max_lat = bbox_wgs84
        xs, ys = to_native.transform(
            [min_lon, max_lon, min_lon, max_lon],
            [min_lat, min_lat, max_lat, max_lat],
        )
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        x_indices = np.where((x_coords >= x_min) & (x_coords <= x_max))[0]
        y_indices = np.where((y_coords >= y_min) & (y_coords <= y_max))[0]
        if x_indices.size == 0 or y_indices.size == 0:
            # Fallback to full granule extent if bbox only grazes edge
            x_sl, y_sl = slice(None), slice(None)
        else:
            x_sl = slice(int(x_indices[0]), int(x_indices[-1]) + 1)
            y_sl = slice(int(y_indices[0]), int(y_indices[-1]) + 1)

    sub_x = x_coords[x_sl]
    sub_y = y_coords[y_sl]
    lons, lats = to_wgs84.transform(
        [float(np.min(sub_x)), float(np.max(sub_x)), float(np.min(sub_x)), float(np.max(sub_x))],
        [float(np.min(sub_y)), float(np.min(sub_y)), float(np.max(sub_y)), float(np.max(sub_y))],
    )
    bounds = (float(min(lons)), float(min(lats)), float(max(lons)), float(max(lats)))
    return y_sl, x_sl, bounds


def read_gunw_subset(
    source: Union[Path, str],
    polarization: str = "HH",
    bbox_wgs84: Optional[Tuple[float, float, float, float]] = None,
    session: Optional[asf.ASFSession] = None,
) -> GeocodedGridSubset:
    """
    Reads unwrappedPhase, coherenceMagnitude, connectedComponents, ionospherePhaseScreen,
    and pixelOffsets from a local .h5 file OR remote https:// URL via HTTP Range requests.
    """
    is_remote = isinstance(source, str) and source.startswith("http")
    fallback_name = str(source).split("/")[-1].replace(".h5", "")

    if is_remote:
        if session is None:
            session = build_authenticated_asf_session()
        raw_reader = CachedRangeReader(str(source), session=session)
        buffered_reader = io.BufferedReader(raw_reader, buffer_size=4 * 1024 * 1024)
        h5_ctx = h5py.File(buffered_reader, "r")
    else:
        raw_reader = None
        h5_ctx = h5py.File(Path(source), "r")

    with h5_ctx as f:
        prov = extract_provenance(f, fallback_granule_id=fallback_name)
        unw_grp = f["/science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram"]

        # Automatically select available polarization if requested polarization is absent
        available_pols = [k for k in ("HH", "VV", "HV", "VH") if k in unw_grp]
        pol = polarization if polarization in unw_grp else available_pols[0]
        pol_grp = unw_grp[pol]

        x_coords = unw_grp["xCoordinates"][:]
        y_coords = unw_grp["yCoordinates"][:]
        y_sl, x_sl, bounds_wgs84 = _compute_pixel_slice(x_coords, y_coords, prov.epsg_code, bbox_wgs84)

        sub_x = x_coords[x_sl]
        sub_y = y_coords[y_sl]

        print(
            f"  -> Extracting GUNW [{pol}] subset shape=({len(sub_y)}, {len(sub_x)}) "
            f"from {prov.granule_id} ...",
            flush=True,
        )

        layers: Dict[str, np.ndarray] = {
            "unwrappedPhase": pol_grp["unwrappedPhase"][y_sl, x_sl].astype(np.float32),
            "coherenceMagnitude": pol_grp["coherenceMagnitude"][y_sl, x_sl].astype(np.float32),
            "connectedComponents": pol_grp["connectedComponents"][y_sl, x_sl],
        }
        if "mask" in unw_grp:
            layers["mask"] = unw_grp["mask"][y_sl, x_sl]
        if "ionospherePhaseScreen" in pol_grp:
            layers["ionospherePhaseScreen"] = pol_grp["ionospherePhaseScreen"][y_sl, x_sl].astype(np.float32)
        if "ionospherePhaseScreenUncertainty" in pol_grp:
            layers["ionospherePhaseScreenUncertainty"] = pol_grp[
                "ionospherePhaseScreenUncertainty"
            ][y_sl, x_sl].astype(np.float32)

        # Extract native pixelOffsets for APOF fusion (handling both identical and coarser grids)
        off_base_path = "/science/LSAR/GUNW/grids/frequencyA/pixelOffsets"
        if off_base_path in f and pol in f[off_base_path]:
            off_base = f[off_base_path]
            off_grp = off_base[pol]
            if off_grp["slantRangeOffset"].shape == pol_grp["unwrappedPhase"].shape:
                layers["slantRangeOffset"] = off_grp["slantRangeOffset"][y_sl, x_sl].astype(np.float32)
                layers["correlationSurfacePeak"] = off_grp["correlationSurfacePeak"][y_sl, x_sl].astype(np.float32)
            elif "xCoordinates" in off_base and "yCoordinates" in off_base:
                ox = off_base["xCoordinates"][:]
                oy = off_base["yCoordinates"][:]
                oy_sl, ox_sl, _ = _compute_pixel_slice(ox, oy, prov.epsg_code, bbox_wgs84)
                sr_sub = off_grp["slantRangeOffset"][oy_sl, ox_sl].astype(np.float32)
                pk_sub = off_grp["correlationSurfacePeak"][oy_sl, ox_sl].astype(np.float32)
                sub_ox = ox[ox_sl]
                sub_oy = oy[oy_sl]

                if len(sub_ox) >= 2 and len(sub_oy) >= 2:
                    # Resample coarser pixelOffsets onto unwrappedPhase grid for APOF
                    yy, xx = np.meshgrid(sub_y, sub_x, indexing="ij")
                    pts = np.column_stack([yy.ravel(), xx.ravel()])
                    interp_sr = RegularGridInterpolator(
                        (sub_oy, sub_ox), sr_sub, method="linear", bounds_error=False, fill_value=np.nan
                    )
                    interp_pk = RegularGridInterpolator(
                        (sub_oy, sub_ox), pk_sub, method="linear", bounds_error=False, fill_value=np.nan
                    )
                    layers["slantRangeOffset"] = interp_sr(pts).reshape(len(sub_y), len(sub_x)).astype(np.float32)
                    layers["correlationSurfacePeak"] = (
                        interp_pk(pts).reshape(len(sub_y), len(sub_x)).astype(np.float32)
                    )

        if raw_reader is not None:
            mb = raw_reader.bytes_downloaded / (1024 * 1024)
            print(f"     HTTP Range stream complete: transferred only {mb:.2f} MB.", flush=True)

        return GeocodedGridSubset(
            data=layers,
            x_coords=sub_x,
            y_coords=sub_y,
            epsg_code=prov.epsg_code,
            bounds_wgs84=bounds_wgs84,
            provenance=prov,
        )


def read_gcov_subset(
    source: Union[Path, str],
    polarization_term: str = "HHHH",
    bbox_wgs84: Optional[Tuple[float, float, float, float]] = None,
    session: Optional[asf.ASFSession] = None,
) -> GeocodedGridSubset:
    """Reads windowed RTC gamma0 backscatter, mask, and numberOfLooks from a NISAR GCOV granule."""
    is_remote = isinstance(source, str) and source.startswith("http")
    fallback_name = str(source).split("/")[-1].replace(".h5", "")

    if is_remote:
        if session is None:
            session = build_authenticated_asf_session()
        raw_reader = CachedRangeReader(str(source), session=session)
        buffered_reader = io.BufferedReader(raw_reader, buffer_size=4 * 1024 * 1024)
        h5_ctx = h5py.File(buffered_reader, "r")
    else:
        h5_ctx = h5py.File(Path(source), "r")

    with h5_ctx as f:
        prov = extract_provenance(f, fallback_granule_id=fallback_name)
        grid = f["/science/LSAR/GCOV/grids/frequencyA"]

        # Available polarimetric terms
        available = [k for k in ("HHHH", "VVVV", "HVHV", "VHVH") if k in grid]
        pol = polarization_term if polarization_term in grid else available[0]

        x_coords = grid["xCoordinates"][:]
        y_coords = grid["yCoordinates"][:]
        y_sl, x_sl, bounds_wgs84 = _compute_pixel_slice(x_coords, y_coords, prov.epsg_code, bbox_wgs84)

        sub_x = x_coords[x_sl]
        sub_y = y_coords[y_sl]

        layers: Dict[str, np.ndarray] = {
            pol: grid[pol][y_sl, x_sl].astype(np.float32),
            "mask": grid["mask"][y_sl, x_sl] if "mask" in grid else np.zeros((len(sub_y), len(sub_x)), dtype=np.uint8),
            "numberOfLooks": grid["numberOfLooks"][y_sl, x_sl].astype(np.float32) if "numberOfLooks" in grid else np.full((len(sub_y), len(sub_x)), 16.0, dtype=np.float32),
        }

        return GeocodedGridSubset(
            data=layers,
            x_coords=sub_x,
            y_coords=sub_y,
            epsg_code=prov.epsg_code,
            bounds_wgs84=bounds_wgs84,
            provenance=prov,
        )
