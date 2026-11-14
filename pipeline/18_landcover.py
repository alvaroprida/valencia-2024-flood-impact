"""ESA WorldCover 2021 (10 m) -> 30 m UTM 30N rasters of Manning n and SCS curve number for the SFINCS domain.

Lookups are literature values (Manning: Deltares / Chow; CN: USDA TR-55 table, hydrologic soil group C assumed for
the whole domain - no soil map used), so they are uncertain and treated as calibration parameters.
"""
import _env  # noqa: F401
import numpy as np
import planetary_computer as pc
import pystac_client
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds

CRS, RES = "EPSG:32630", 30.0
BBOX_LL = (-1.45, 38.95, -0.15, 39.75)  # same window as the wide FABDEM
x0, y0, x1, y1 = transform_bounds("EPSG:4326", CRS, *BBOX_LL)
x0, y0 = np.floor(x0 / RES) * RES, np.floor(y0 / RES) * RES
W, H = int((x1 - x0) / RES), int((y1 - y0) / RES)
TR = from_origin(x0, y0 + H * RES, RES, RES)

cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
items = cat.search(collections=["esa-worldcover"], bbox=list(BBOX_LL), datetime="2021-01-01/2021-12-31").item_collection()
print("worldcover tiles:", len(items))
lc = np.zeros((H, W), dtype="uint8")
for it in items:
    with rasterio.open(it.assets["map"].href) as src:
        tmp = np.zeros((H, W), dtype="uint8")
        reproject(rasterio.band(src, 1), tmp, src_transform=src.transform, src_crs=src.crs, dst_transform=TR,
                  dst_crs=CRS, resampling=Resampling.mode)
        lc = np.where(tmp > 0, tmp, lc)

#            class: (manning n, CN)
LOOKUP = {10: (0.15, 70), 20: (0.10, 77), 30: (0.035, 74), 40: (0.05, 82), 50: (0.12, 90), 60: (0.03, 86),
          70: (0.03, 90), 80: (0.02, 100), 90: (0.07, 85), 95: (0.10, 80), 100: (0.05, 74)}
lc[lc == 0] = 80  # WorldCover leaves the sea unclassified: treat as water
man = np.full((H, W), 0.04, dtype="float32")
cn = np.full((H, W), 80, dtype="float32")
for k, (n, c) in LOOKUP.items():
    man[lc == k], cn[lc == k] = n, c
prof = dict(driver="GTiff", dtype="float32", count=1, crs=CRS, transform=TR, width=W, height=H, nodata=-9999, compress="deflate")
for name, arr in (("manning", man), ("cn", cn), ("landcover", lc.astype("float32"))):
    with rasterio.open(f"data/processed/sfincs_{name}.tif", "w", **prof) as dst:
        dst.write(arr, 1)
share = {k: round(float((lc == k).mean()) * 100, 1) for k in np.unique(lc) if (lc == k).mean() > 0.005}
print("grid", W, "x", H, "| class shares %:", share)
