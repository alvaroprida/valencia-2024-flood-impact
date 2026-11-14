"""SFINCS maximum water level -> 30 m flood depth and extent; score against Copernicus EMS EMSR773.

usage: python pipeline/22_flood_results.py [run_name]
 - depth = max water level (90 m cells, subgrid-aware) downscaled onto FABDEM (30 m); depth >= 0.10 m = flooded
 - permanent water (sea, Albufera, reservoirs) removed with the 26 Oct Sentinel-2 water mask
 - validation on the CEMS very-high-resolution delineations: AOI03 Horta Sud and AOI04 Algemesi
"""
import importlib
import json
import shutil
import sys

import common as c
import geopandas as gpd
import numpy as np
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from hydromt_sfincs import SfincsModel
from hydromt_sfincs.utils import downscale_floodmap
from scipy import ndimage as ndi
from skimage.morphology import remove_small_objects

RUN = sys.argv[1] if len(sys.argv) > 1 else "base"
ROOT = f"models/{RUN}"
HMIN = 0.10
s = importlib.import_module("04_sar_flood")

shutil.copy(f"{ROOT}/out/sfincs_map.nc", f"{ROOT}/sfincs_map.nc")
mod = SfincsModel(root=ROOT, mode="r")
mod.read_results()
zsmax = mod.results["zsmax"].max("timemax") if "timemax" in mod.results["zsmax"].dims else mod.results["zsmax"]
print("zsmax dims", zsmax.dims, "| max", float(zsmax.max()))

dem = rioxarray.open_rasterio("data/raw/fabdem_wide.tif").squeeze(drop=True)
dem = dem.where(dem > -9000).rio.reproject("EPSG:32630", resolution=30.0, resampling=rasterio.enums.Resampling.bilinear)
depth = downscale_floodmap(zsmax=zsmax, dep=dem, hmin=HMIN, nrmax=2000)
depth.rio.to_raster(f"{c.PROC}/sfincs_{RUN}_depth30.tif", compress="deflate")
print("depth30 raster", depth.shape, "| max depth m", round(float(depth.max()), 1))

# onto the 10 m study grid (nearest) for scoring
d10 = c.read_to_grid(f"{c.PROC}/sfincs_{RUN}_depth30.tif", resampling=c.Resampling.nearest)
perm = np.nan_to_num(c.load("mndwi_s2_20241026.tif"), nan=-1) > 0.0
perm = ndi.binary_dilation(perm, iterations=2)
d10 = np.where(d10 > 30, np.nan, d10)  # a few reservoir / gorge cells; nothing physical above this
depth_grid = np.where(perm, np.nan, d10)
# one flood definition for mapping and for the impact step: depth >= 0.30 m and clusters >= 1 ha.
# (thin channel flow and sheet flow on slopes at 90 m cells are not floodplain inundation)
FLOOD_DEPTH, FLOOD_MIN_PX = 0.30, 100
flood = remove_small_objects(np.nan_to_num(depth_grid, nan=0) >= FLOOD_DEPTH, FLOOD_MIN_PX)
depth_final = np.where(flood, depth_grid, 0.0)
c.save(depth_final.astype("float32"), f"sfincs_{RUN}_depth10.tif")
c.save(flood.astype("float32"), f"flood_sfincs_{RUN}.tif")

out = dict(run=RUN, downscale_hmin_m=HMIN, flood_depth_threshold_m=FLOOD_DEPTH, min_cluster_ha=FLOOD_MIN_PX * 0.01,
           flooded_km2_in_grid=round(float(flood.sum()) * 1e-4, 1))
for name, aoi in (("Horta Sud (AOI03)", "AOI03"), ("Algemesi (AOI04)", "AOI04")):
    d = f"data/raw/cems/EMSR773_{aoi}_DEL_PRODUCT_v1/x/EMSR773_{aoi}_DEL_PRODUCT"
    truth = s.rasterize(gpd.read_file(f"{d}_observedEventA_v1.shp"))
    fp = gpd.read_file(f"{d}_imageFootprintA_v1.shp")
    foot = s.rasterize(fp[fp.obj_type == "Image Footprint"])
    m = s.metrics(flood, truth, foot)
    m["observed_km2"] = round(float((truth & foot).sum()) * 1e-4, 1)
    m["modelled_km2_in_footprint"] = round(float((flood & foot).sum()) * 1e-4, 1)
    m["area_ratio_model_to_obs"] = round(m["modelled_km2_in_footprint"] / max(m["observed_km2"], 1e-9), 2)
    out[name] = m
t, f = s.cems_truth()
out["both_aois"] = s.metrics(flood, t, f)
print(json.dumps(out, indent=1))
json.dump(out, open(f"{c.PROC}/validation_sfincs_{RUN}.json", "w"), indent=1)

# water balance and depth classes
ds = xr.open_dataset(f"{ROOT}/sfincs_map.nc", decode_times=False)
if "cumprcp" in ds and "cuminf" in ds:
    msk = ds["msk"].values > 0
    td = "timemax" if "timemax" in ds["cumprcp"].dims else "time"
    pr, inf = ds["cumprcp"].isel({td: -1}).values[msk], ds["cuminf"].isel({td: -1}).values[msk]
    out["water_balance"] = dict(mean_rain_mm=round(float(np.nanmean(pr))), mean_infiltration_mm=round(float(np.nanmean(inf))),
                                infiltrated_share=round(float(np.nanmean(inf) / np.nanmean(pr)), 2))
    print("water balance:", out["water_balance"])
out["area_km2_deeper_than"] = {str(lo): round(float(np.nansum(depth_final >= lo)) * 1e-4, 1) for lo in (0.3, 0.5, 1.0, 2.0)}
print("area by depth:", out["area_km2_deeper_than"])
json.dump(out, open(f"{c.PROC}/validation_sfincs_{RUN}.json", "w"), indent=1)
