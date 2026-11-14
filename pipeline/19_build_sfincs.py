"""Build the SFINCS rain-on-grid model of the Poyo + Magro + Horta Sud area (29 Oct 2024 DANA).

Run from the repository root:  python pipeline/19_build_sfincs.py [run_name] [cn_shift]
 - 90 m regular grid, 45 m subgrid pixels from FABDEM (30 m), rain on grid from the gauge-scaled ERA5 field, SCS-CN infiltration,
   sea level boundary on the eastern (Mediterranean) edge. No dams / canals / sewers are represented.
"""
import logging
import os
import sys

import _env  # noqa: F401
import geopandas as gpd
import pandas as pd
import xarray as xr
import yaml
from hydromt import DataCatalog
from hydromt_sfincs import SfincsModel
from shapely.geometry import Point, box

RUN = sys.argv[1] if len(sys.argv) > 1 else "base"
CN_SHIFT = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0      # added to the SCS curve number (negative = more infiltration)
RAIN_SCALE = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0    # multiplier on the rainfall field
MAN_SCALE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0     # multiplier on Manning's n
LAKE = (sys.argv[5] if len(sys.argv) > 5 else "lake") == "lake"  # hold the Albufera at sea level (managed lake)
ROOT = os.path.abspath(f"models/{RUN}")
ABS = os.path.abspath

import numpy as np  # noqa: E402
import rasterio  # noqa: E402


def variant(src, dst, fn):
    with rasterio.open(src) as r:
        a, p = r.read(1), r.profile
    with rasterio.open(dst, "w", **p) as w:
        w.write(fn(a).astype(p["dtype"]), 1)


variant("data/processed/sfincs_cn.tif", f"data/processed/sfincs_cn_{RUN}.tif",
        lambda a: np.where((a > 0) & (a < 100), np.clip(a + CN_SHIFT, 30, 99), a))
variant("data/processed/sfincs_manning.tif", f"data/processed/sfincs_manning_{RUN}.tif", lambda a: a * MAN_SCALE)

import rioxarray  # noqa: F401  (adds .rio, used to stamp the CRS on the rainfall grid)
_r = xr.open_dataset("data/processed/rain_field.nc").rename({"lat": "y", "lon": "x"})
_r["precip"] = _r["precip"] * RAIN_SCALE
_r.rio.write_crs("EPSG:4326").to_netcdf(f"data/processed/rain_field_{RUN}.nc")

cat = {
    "fabdem": dict(data_type="RasterDataset", path=ABS("data/raw/fabdem_wide.tif"), driver="raster", crs=4326, nodata=-9999),
    "manning": dict(data_type="RasterDataset", path=ABS(f"data/processed/sfincs_manning_{RUN}.tif"), driver="raster", crs=32630, nodata=-9999),
    "cn": dict(data_type="RasterDataset", path=ABS(f"data/processed/sfincs_cn_{RUN}.tif"), driver="raster", crs=32630, nodata=-9999),
    "precip": dict(data_type="RasterDataset", path=ABS(f"data/processed/rain_field_{RUN}.nc"), driver="netcdf", crs=4326),
}
os.makedirs("models", exist_ok=True)
yaml.safe_dump(cat, open(f"models/catalog_{RUN}.yml", "w"))

logger = logging.getLogger("sfincs")
logging.basicConfig(level=logging.INFO)
sf = SfincsModel(root=ROOT, mode="w+", data_libs=[f"models/catalog_{RUN}.yml"], logger=logger)
print(f"run {RUN}: CN shift {CN_SHIFT:+.0f} | rain x{RAIN_SCALE} | Manning x{MAN_SCALE} | Albufera held at sea level: {LAKE}")

# --- grid: region polygon = Magro + Poyo catchments + Horta Sud plain + coastal strip
basins = gpd.read_file("data/processed/basins.geojson")
keep = basins[basins.name.isin(["Rambla del Poyo (A-3 gauge)", "Magro at Guadassuar"])].geometry.tolist()
plain = box(-0.70, 39.16, -0.27, 39.50)
region = gpd.GeoDataFrame(geometry=[pd.concat([gpd.GeoSeries(keep), gpd.GeoSeries([plain])]).union_all()], crs=4326)
sf.setup_grid_from_region(region={"geom": region}, res=90, crs=32630, rotated=False, align=True)

sf.setup_config(tref="20241028 000000", tstart="20241028 120000", tstop="20241030 120000",
                dtmapout=3600, dthisout=600, dtmaxout=172800, storemaxwaterlevel=1, dtrstout=0, utmzone="30N")

sf.setup_dep(datasets_dep=[{"elevtn": "fabdem"}])
sf.setup_mask_active(mask=region, zmin=-5.0, reset_mask=True, fill_area=10.0)
east = gpd.GeoDataFrame(geometry=[box(-0.325, 39.12, -0.27, 39.52)], crs=4326)
sf.setup_mask_bounds(btype="waterlevel", include_mask=east, zmax=0.05, reset_bounds=True)

if LAKE:
    # the Albufera is a managed lake (sluices keep it near sea level): hold it as a fixed-head (water level) boundary
    from rasterio import features
    lake = gpd.read_file("data/processed/albufera_lake.geojson").to_crs(sf.crs)
    inside = features.rasterize([(g, 1) for g in lake.geometry], out_shape=sf.grid["msk"].shape,
                                transform=sf.grid["msk"].raster.transform, fill=0).astype(bool)
    msk = sf.grid["msk"].copy()
    new = msk.values.copy()
    new[inside & (new == 1)] = 2
    msk.values = new
    sf.set_grid(msk, name="msk")
    print("Albufera boundary cells:", int((inside & (msk.values == 2)).sum()))

sf.setup_manning_roughness(datasets_rgh=[{"manning": "manning"}], manning_land=0.04, manning_sea=0.02)
sf.setup_cn_infiltration(cn="cn", antecedent_moisture="avg")

sf.setup_subgrid(datasets_dep=[{"elevtn": "fabdem"}], datasets_rgh=[{"manning": "manning"}], nr_subgrid_pixels=2,
                 manning_land=0.04, manning_sea=0.02, write_dep_tif=False, write_man_tif=False)

# rainfall: mm/h, hourly, timestamps = end of the hour (Open-Meteo/ERA5 convention)
sf.setup_precip_forcing_from_grid(precip="precip", cumulative_input=False, time_label="right", aggregate=False)

# sea level on the boundary: constant 0.3 m (mean Mediterranean sea level + small surge; no tide to speak of)
t = pd.date_range("2024-10-28 00:00", "2024-10-31 00:00", freq="1h")
ts = pd.DataFrame({1: 0.30}, index=t)
loc = gpd.GeoDataFrame({"index": [1]}, geometry=[Point(-0.29, 39.30)], crs=4326).set_index("index").to_crs(32630)
sf.setup_waterlevel_forcing(timeseries=ts, locations=loc, buffer=100000)

sf.write()
print("\nmodel written:", ROOT)
print("grid:", sf.grid.sizes if hasattr(sf.grid, "sizes") else "", "| active cells:", int((sf.grid["msk"] > 0).sum()))
print(open(f"{ROOT}/sfincs.inp").read())
