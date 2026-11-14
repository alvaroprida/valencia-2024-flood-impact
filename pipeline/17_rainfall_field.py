"""Hourly rainfall field from gauge totals (SAIH episode totals + AEMET) with ERA5 hourly timing.

Two ways of combining them are compared by leave-one-out cross-validation:
  A  'ratio'  : ERA5 hourly x interpolated (gauge / ERA5) ratio      -> keeps ERA5's spatial pattern
  B  'direct' : IDW of the gauge totals, split in time with the local ERA5 hourly shape -> gauges set the pattern
SAIH totals cover 28 Oct - 5 Nov: 95 % is assumed to fall in the 28-30 Oct window (CHJ: Poyo 367 of 392 mm fell on
29 Oct = 94 %). Times are UTC; CHJ report times are local (CEST = UTC+2).
"""
import json

import _env  # noqa: F401
import geopandas as gpd
import numpy as np
import xarray as xr
from rasterio import features
from rasterio.transform import from_origin
from scipy.spatial import cKDTree

SHARE = 0.95
K, P = 8, 2.0
era = xr.open_dataset("data/raw/era5/era5_hourly.nc")
era_tot = era.precip.sum("time")

g = gpd.read_file("data/processed/gauges.geojson")
saih = g[(g.kind == "rain") & g.event_mm.notna()].copy()
saih["tot"] = saih.event_mm * SHARE
aemet = g[g.kind == "rain_aemet"].copy()
a3 = {}
for r in json.load(open("data/raw/aemet/daily_20241027_20241101.json", encoding="utf-8")):
    if r["fecha"] in ("2024-10-28", "2024-10-29", "2024-10-30") and r.get("prec") not in (None, "Ip"):
        a3[r["nombre"].title()] = a3.get(r["nombre"].title(), 0) + float(r["prec"].replace(",", "."))
aemet["tot"] = aemet.name.map(a3)
pts = gpd.GeoDataFrame(
    {"name": list(saih.name) + list(aemet.name), "tot": list(saih.tot) + list(aemet.tot),
     "q": list(saih.coord_quality) + list(aemet.coord_quality), "src": ["SAIH"] * len(saih) + ["AEMET"] * len(aemet)},
    geometry=list(saih.geometry) + list(aemet.geometry), crs=4326)
pts = pts[pts.tot.notna() & (pts.tot > 0)].reset_index(drop=True)
clip = lambda p: (float(np.clip(p.y, 38.75, 40.0)), float(np.clip(p.x, -1.5, 0.0)))
pts["era"] = [float(era_tot.interp(lat=clip(p)[0], lon=clip(p)[1])) for p in pts.geometry]
assert pts.era.notna().all()
print("gauges used:", len(pts), "| ERA5 / gauge total, median:", round(float((pts.era / pts.tot).median()), 2))

km = lambda lon, lat: np.c_[np.asarray(lon) * 85.0, np.asarray(lat) * 111.0]
xy = km(pts.geometry.x, pts.geometry.y)
tree = cKDTree(xy)
tot = pts.tot.values
lr = np.log(np.maximum(tot, 1) / np.maximum(pts.era.values, 5.0))
lr_med = float(np.median(lr))


def idw(qxy, vals, exclude_self=False):
    dist, idx = tree.query(qxy, k=K + (1 if exclude_self else 0))
    if exclude_self:
        dist, idx = dist[:, 1:], idx[:, 1:]
    w = 1.0 / np.maximum(dist, 1.0) ** P
    return (w * vals[idx]).sum(1) / w.sum(1), dist[:, 0]


# --- leave-one-out comparison
est_b, _ = idw(xy, tot, exclude_self=True)
est_lr, d0 = idw(xy, lr, exclude_self=True)
relax = np.exp(-d0 / 25.0)
est_a = np.maximum(pts.era.values, 5.0) * np.exp(relax * est_lr + (1 - relax) * lr_med)


def score(est, name):
    e = est - tot
    print(f"LOO {name}: bias {e.mean():6.1f} mm | RMSE {np.sqrt((e ** 2).mean()):5.1f} mm | R2 {1 - (e ** 2).sum() / ((tot - tot.mean()) ** 2).sum():5.2f}"
          f" | RMSE on gauges > 100 mm: {np.sqrt((e[tot > 100] ** 2).mean()):5.1f} mm")


score(est_a, "A ratio ")
score(est_b, "B direct")
pts.assign(loo_A=est_a, loo_B=est_b).drop(columns="geometry").to_csv("data/processed/rain_gauges_used.csv", index=False)

# --- field on a 0.01 deg grid, method B
lon = np.round(np.arange(-1.45, -0.149, 0.01), 3)
lat = np.round(np.arange(38.95, 39.751, 0.01), 3)
LO, LA = np.meshgrid(lon, lat)
T = idw(km(LO.ravel(), LA.ravel()), tot)[0].reshape(LO.shape)
hourly = era.precip.interp(lat=lat, lon=lon, method="linear").values        # (time, lat, lon)
local_tot = hourly.sum(0)
regional = era.precip.sel(lat=slice(39.0, 39.75), lon=slice(-1.25, -0.5)).mean(("lat", "lon")).values
shape = np.where(local_tot[None] > 15, hourly / np.maximum(local_tot[None], 1e-6), (regional / regional.sum())[:, None, None])
field = (shape * T[None]).astype("float32")
ds = xr.Dataset({"precip": (("time", "lat", "lon"), field)}, coords={"time": era.time.values, "lat": lat, "lon": lon})
ds.precip.attrs.update(units="mm/h", long_name="gauge-interpolated totals with ERA5 hourly timing (UTC)")
ds.to_netcdf("data/processed/rain_field.nc")
total = field.sum(0)
xr.DataArray(total, coords={"lat": lat, "lon": lon}, dims=("lat", "lon")).to_netcdf("data/processed/rain_total.nc")
print("field total range mm:", round(float(total.min())), "-", round(float(total.max())), "| peak hourly mm/h:", round(float(field.max()), 1))

b = gpd.read_file("data/processed/basins.geojson")
tr = from_origin(lon[0] - 0.005, lat[-1] + 0.005, 0.01, 0.01)
totf = np.flipud(total)
for _, row in b.iterrows():
    m = features.rasterize([(row.geometry, 1)], out_shape=total.shape, transform=tr, fill=0).astype(bool)
    print(f"{row['name']:32s} {row.area_km2:7.1f} km2  mean total {totf[m].mean():5.0f} mm")
print("CHJ report: Poyo basin 392 mm (whole episode; larger basin than the A-3 gauge catchment), Magro 306 mm")
