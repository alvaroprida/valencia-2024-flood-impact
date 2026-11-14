"""Shared study-area grid and helpers."""
import os

import _env  # noqa: F401  (must come before rasterio / pyproj)
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

CRS = "EPSG:32630"  # UTM 30N
RES = 10.0
# Horta Sud, Poyo / Magro / lower Turia, Albufera
BBOX_LL = (-0.65, 39.20, -0.25, 39.55)

PROC = "data/processed"
RAW = "data/raw"
os.makedirs(PROC, exist_ok=True)
os.makedirs(RAW, exist_ok=True)


def grid():
    t = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    x0, y0 = t.transform(BBOX_LL[0], BBOX_LL[1])
    x1, y1 = t.transform(BBOX_LL[2], BBOX_LL[3])
    x0, y0 = np.floor(x0 / RES) * RES, np.floor(y0 / RES) * RES
    x1, y1 = np.ceil(x1 / RES) * RES, np.ceil(y1 / RES) * RES
    w, h = int((x1 - x0) / RES), int((y1 - y0) / RES)
    return from_origin(x0, y1, RES, RES), w, h


TRANSFORM, W, H = grid()
PROFILE = dict(driver="GTiff", dtype="float32", count=1, crs=CRS, transform=TRANSFORM,
               width=W, height=H, nodata=np.nan, compress="deflate", tiled=True)


def read_to_grid(href, band=1, resampling=Resampling.bilinear):
    """Read any raster (local or HTTPS COG) resampled onto the study grid."""
    out = np.full((H, W), np.nan, dtype="float32")
    with rasterio.open(href) as src:
        reproject(rasterio.band(src, band), out, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=TRANSFORM, dst_crs=CRS, resampling=resampling,
                  src_nodata=src.nodata, dst_nodata=np.nan)
    return out


def save(arr, name, **kw):
    prof = {**PROFILE, **kw}
    with rasterio.open(f"{PROC}/{name}", "w", **prof) as dst:
        dst.write(arr.astype(prof["dtype"]), 1)


def load(name):
    with rasterio.open(f"{PROC}/{name}") as src:
        return src.read(1)
