"""FABDEM V1-2 (30 m, forests and buildings removed; CC BY-NC-SA 4.0) from the University of Bristol.

1 deg tiles are read with HTTP range requests out of the 10 deg ZIP archives, so only the tiles that
the study area touches are downloaded.
"""
import math

import common as c
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import Resampling, reproject

BASE = "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn"
# Wider than the grid: the Poyo and Magro headwaters lie west of the flooded plain.
BBOX = (-1.45, 38.95, -0.15, 39.75)


def tile_url(lat, lon):
    z_lat, z_lon = math.floor(lat / 10) * 10, math.floor(lon / 10) * 10
    ns = lambda v: f"{'N' if v >= 0 else 'S'}{abs(v):02d}"
    ew = lambda v: f"{'E' if v >= 0 else 'W'}{abs(v):03d}"
    zip_name = f"{ns(z_lat)}{ew(z_lon)}-{ns(z_lat + 10)}{ew(z_lon + 10)}_FABDEM_V1-2.zip"
    tile = f"{ns(lat)}{ew(lon)}_FABDEM_V1-2.tif"
    return f"/vsizip//vsicurl/{BASE}/{zip_name}/{tile}"


tiles = [(la, lo) for la in range(math.floor(BBOX[1]), math.floor(BBOX[3]) + 1)
         for lo in range(math.floor(BBOX[0]), math.floor(BBOX[2]) + 1)]
print("tiles:", tiles)

with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".zip,.tif"):
    srcs = [rasterio.open(tile_url(la, lo)) for la, lo in tiles]
    mosaic, tr = merge(srcs, bounds=BBOX, nodata=-9999)
    profile = dict(driver="GTiff", dtype="float32", count=1, crs="EPSG:4326", transform=tr,
                   width=mosaic.shape[2], height=mosaic.shape[1], nodata=-9999, compress="deflate")
    with rasterio.open(f"{c.RAW}/fabdem_wide.tif", "w", **profile) as dst:
        dst.write(mosaic[0].astype("float32"), 1)
    print("wide fabdem", mosaic.shape, "range", float(mosaic[mosaic > -9000].min()), float(mosaic.max()))

    # same study grid as the satellite layers (10 m, UTM 30N), bilinear from 30 m
    out = np.full((c.H, c.W), np.nan, dtype="float32")
    with rasterio.open(f"{c.RAW}/fabdem_wide.tif") as src:
        reproject(rasterio.band(src, 1), out, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=c.TRANSFORM, dst_crs=c.CRS, resampling=Resampling.bilinear,
                  src_nodata=-9999, dst_nodata=np.nan)
    c.save(out, "fabdem.tif")
    old = c.load("dem.tif")
    ok = np.isfinite(out) & (old != 0)
    print("study grid: valid %", round(100 * float(np.isfinite(out).mean()), 1),
          "| mean(FABDEM - GLO30) m:", round(float((out - old)[ok].mean()), 2),
          "| rmsd m:", round(float(np.sqrt(np.mean((out - old)[ok] ** 2))), 2))
