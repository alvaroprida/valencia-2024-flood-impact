"""Export the pipeline results as web layers (web/public/data): GeoJSON, map images and summary JSON.

usage: python pipeline/27_export_web.py [run_name]
Raster layers are reprojected to Web Mercator and written as coloured PNGs (draped on the map with their 4 corners).
"""
import json
import os
import sys

import common as c
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

RUN = sys.argv[1] if len(sys.argv) > 1 else "base"
OUT = "web/public/data"
os.makedirs(OUT, exist_ok=True)
sizes = {}


def write_geojson(gdf, name, keep, decimals=5, simplify=None):
    g = gdf[keep + ["geometry"]].copy()
    if simplify:  # tolerance in metres: simplify in the projected CRS, before going to degrees
        g = g.to_crs(c.CRS)
        g["geometry"] = g.geometry.simplify(simplify, preserve_topology=True)
    g = g.to_crs(4326)
    path = f"{OUT}/{name}"
    g.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=decimals)
    sizes[name] = round(os.path.getsize(path) / 1e6, 2)


HEX = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype="uint8")


def to_png(arr, src_transform, src_crs, name, colorize, res=15.0):
    """Reproject a raster to Web Mercator, colourise it (rgba uint8) and save a PNG; returns the image corners (lon, lat)."""
    h, w = arr.shape
    b = rasterio.transform.array_bounds(h, w, src_transform)
    dst_t, dw, dh = calculate_default_transform(src_crs, "EPSG:3857", w, h, *b, resolution=res * 1.2)
    dst = np.full((dh, dw), np.nan, dtype="float32")
    reproject(arr.astype("float32"), dst, src_transform=src_transform, src_crs=src_crs, dst_transform=dst_t, dst_crs="EPSG:3857",
              resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    rgba = colorize(dst)
    plt.imsave(f"{OUT}/{name}", rgba)
    sizes[name] = round(os.path.getsize(f"{OUT}/{name}") / 1e6, 2)
    x0, y1 = dst_t.c, dst_t.f
    x1, y0 = x0 + dw * dst_t.a, y1 + dh * dst_t.e
    t = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    tl, tr, br, bl = t.transform(x0, y1), t.transform(x1, y1), t.transform(x1, y0), t.transform(x0, y0)
    return [list(map(lambda v: round(v, 6), p)) for p in (tl, tr, br, bl)]


DEPTH_STOPS = [(0.3, "#cfe8f7"), (0.5, "#9ccdee"), (1.0, "#5aa7de"), (2.0, "#2a78d6"), (4.0, "#1d4f9e"), (99, "#13294f")]


def depth_rgba(a):
    out = np.zeros(a.shape + (4,), dtype="uint8")
    lo = 0.0
    for up, col in DEPTH_STOPS:
        m = np.isfinite(a) & (a >= max(lo, 0.3)) & (a < up)
        out[m, :3], out[m, 3] = HEX(col), 215
        lo = up
    return out


def mask_rgba(color, alpha=190):
    def f(a):
        out = np.zeros(a.shape + (4,), dtype="uint8")
        m = np.isfinite(a) & (a > 0)
        out[m, :3], out[m, 3] = HEX(color), alpha
        return out
    return f


images = {}
tr_g = c.TRANSFORM
images["flood_depth"] = to_png(c.load(f"sfincs_{RUN}_depth10.tif"), tr_g, c.CRS, "flood_depth.png", depth_rgba)
images["s1_flood"] = to_png(c.load("flood_s1_20241101.tif"), tr_g, c.CRS, "s1_flood_20241101.png", mask_rgba("#eb6834"), res=20)
images["s2_flood"] = to_png(c.load("flood_s2_20241031.tif"), tr_g, c.CRS, "s2_flood_20241031.png", mask_rgba("#1baf7a"), res=20)

# model rainfall total (0.01 deg, lat/lon image; the area is small enough to drape without reprojection)
rt = xr.open_dataarray("data/processed/rain_total.nc")
vals = np.flipud(rt.values)
cm = plt.get_cmap("YlGnBu")
norm = np.clip(vals / 700.0, 0, 1)
rgba = (cm(norm) * 255).astype("uint8")
rgba[..., 3] = np.where(vals > 5, 170, 0)
plt.imsave(f"{OUT}/rain_total.png", rgba)
sizes["rain_total.png"] = round(os.path.getsize(f"{OUT}/rain_total.png") / 1e6, 2)
lon0, lon1, lat0, lat1 = float(rt.lon.min()) - 0.005, float(rt.lon.max()) + 0.005, float(rt.lat.min()) - 0.005, float(rt.lat.max()) + 0.005
images["rain_total"] = [[lon0, lat1], [lon1, lat1], [lon1, lat0], [lon0, lat0]]

# ---------------------------------------------------------------- vectors
b = gpd.read_file("data/processed/basins.geojson")
rt_t = from_origin(float(rt.lon.min()) - 0.005, float(rt.lat.max()) + 0.005, 0.01, 0.01)
from rasterio import features
means = []
for g in b.geometry:
    m = features.rasterize([(g, 1)], out_shape=vals.shape, transform=rt_t, fill=0).astype(bool)
    means.append(round(float(vals[m].mean())))
b["mean_rain_mm"] = means
write_geojson(b.to_crs(c.CRS), "basins.geojson", ["name", "area_km2", "mean_rain_mm"], simplify=30)

st = gpd.read_file("data/processed/streams.geojson").to_crs(c.CRS)
st = st[st.acc_km2 >= 0] if "acc_km2" in st else st
write_geojson(st, "streams.geojson", ["acc_km2"] if "acc_km2" in st else [], decimals=4, simplify=25)

gau = gpd.read_file("data/processed/gauges.geojson").to_crs(c.CRS)
gau["event_mm"] = gau.event_mm.round(0)
cols = [k for k in ("kind", "name", "event_mm", "report_text", "coord_quality", "source", "peak_q", "peak_time") if k in gau]
write_geojson(gau, "gauges.geojson", cols, decimals=5)

alb = gpd.read_file("data/processed/albufera_lake.geojson").to_crs(c.CRS)
write_geojson(alb, "albufera.geojson", ["name"], simplify=30)

# CEMS reference (VHR 31 Oct) and analysed footprints
ev, fp = [], []
for aoi, label in (("AOI03", "Horta Sud"), ("AOI04", "Algemesí")):
    d = f"data/raw/cems/EMSR773_{aoi}_DEL_PRODUCT_v1/x/EMSR773_{aoi}_DEL_PRODUCT"
    e = gpd.read_file(f"{d}_observedEventA_v1.shp").to_crs(c.CRS)
    e["aoi"], e["kind"] = label, e["notation"]
    ev.append(e[["aoi", "kind", "geometry"]])
    f = gpd.read_file(f"{d}_imageFootprintA_v1.shp").to_crs(c.CRS)
    f = f[f.obj_type == "Image Footprint"]
    f["aoi"] = label
    fp.append(f[["aoi", "geometry"]].dissolve("aoi").reset_index())
write_geojson(pd.concat(ev).pipe(gpd.GeoDataFrame, crs=c.CRS), "cems_observed.geojson", ["aoi", "kind"], decimals=5, simplify=8)
write_geojson(pd.concat(fp).pipe(gpd.GeoDataFrame, crs=c.CRS), "cems_footprint.geojson", ["aoi"], simplify=30)

# buildings: flooded only, as points
bd = gpd.read_parquet(f"data/processed/impact_buildings_{RUN}.parquet")
bd = gpd.GeoDataFrame(bd.drop(columns="geometry"), geometry=bd.geometry.centroid, crs=c.CRS)
bd = bd[bd.flooded].copy()
OCC = ["residential", "commercial", "industrial", "public", "agricultural", "other"]
bd["o"] = bd.occ.map({k: i for i, k in enumerate(OCC)})
bd["d"], bd["r"], bd["p"], bd["f"] = bd.depth.round(1), bd.ratio.round(2), bd["pop"].round(1), bd.floors.astype(int)
bd["l"] = (bd.loss_eur / 1000).round(0)
write_geojson(bd, "buildings_flooded.geojson", ["o", "d", "r", "p", "f", "l"], decimals=5)

pc = gpd.read_parquet(f"data/processed/priority_cells_{RUN}.parquet").to_crs(c.CRS)
pc["people"], pc["people_sev"], pc["loss_k"] = pc.people_ground_exposed.round(0), pc.people_severity.round(0), (pc.loss_eur / 1000).round(0)
pc["score"], pc["road_cut"], pc["maxd"] = pc.score.round(1), pc.road_cut_share.round(2), pc.max_depth.round(1)
pc = pc.rename(columns={"facilities_flooded": "fac"})
write_geojson(pc, "priority_cells.geojson", ["rank", "tier", "score", "people", "people_sev", "loss_k", "maxd", "road_cut", "fac", "municipality", "buildings_flooded",
                                              "c_people", "c_loss", "c_facility", "c_access"], decimals=5)

# exposure grid (250 m): people and buildings over the study area
ba = gpd.read_parquet("data/processed/buildings.parquet")
cen = ba.geometry.centroid
ba["cx"], ba["cy"] = np.floor(cen.x / 250) * 250 + 125, np.floor(cen.y / 250) * 250 + 125
ba["res_pop"] = np.where(ba.occ == "residential", ba["pop"], 0.0)
eg = ba.groupby(["cx", "cy"]).agg(people=("pop", "sum"), buildings=("id", "size"), residential=("occ", lambda x: (x == "residential").mean()),
                                  industrial=("occ", lambda x: (x == "industrial").mean()), floors=("floors", "mean")).reset_index()
eg = eg[eg.people >= 5]
from shapely.geometry import box
eg["geometry"] = [box(x - 125, y - 125, x + 125, y + 125) for x, y in zip(eg.cx, eg.cy)]
eg = gpd.GeoDataFrame(eg, geometry="geometry", crs=c.CRS)
eg["people"], eg["residential"], eg["industrial"], eg["floors"] = eg.people.round(0), eg.residential.round(2), eg.industrial.round(2), eg.floors.round(1)
write_geojson(eg, "exposure_grid.geojson", ["people", "buildings", "residential", "industrial", "floors"], decimals=5)

# municipalities with impact and priority figures
mu = gpd.read_file("data/processed/municipalities.gpkg")
im = pd.read_csv(f"data/processed/impact_municipalities_{RUN}.csv")
pr = pd.read_csv(f"data/processed/priority_municipalities_{RUN}.csv")
mu = mu.merge(im, how="left", on="municipality").merge(pr[["municipality", "tier1_cells", "score", "people_severity", "facilities"]], how="left", on="municipality")
for k in mu.columns:
    if k not in ("municipality", "geometry"):
        mu[k] = pd.to_numeric(mu[k], errors="coerce")
mu = mu.round(2)
write_geojson(mu, "municipalities.geojson", [k for k in mu.columns if k != "geometry"], simplify=20)

cd = gpd.read_file("data/raw/cems/EMSR773_AOI03_GRA_PRODUCT_v2/x/EMSR773_AOI03_GRA_PRODUCT_builtUpP_v2.shp").to_crs(c.CRS)
cd["grade"] = cd.damage_gra
write_geojson(cd, "cems_damage_points.geojson", ["grade"], decimals=5)

fac = gpd.read_parquet(f"data/processed/impact_facilities_{RUN}.parquet").to_crs(c.CRS)
fac = fac[fac.flooded].copy()
fac["depth"] = fac.depth.round(1)
write_geojson(fac, "facilities_flooded.geojson", ["name", "facility", "depth"], decimals=5)

rd = gpd.read_parquet(f"data/processed/impact_roads_{RUN}.parquet")
rd = rd[rd.cut & rd["class"].isin(["motorway", "trunk", "primary", "secondary", "tertiary", "residential"])].copy()
rd["depth"] = rd.depth.round(1)
write_geojson(gpd.GeoDataFrame(rd, crs=c.CRS), "roads_cut.geojson", ["class", "depth"], decimals=4, simplify=5)

json.dump(images, open(f"{OUT}/images.json", "w"))
print("exported:", json.dumps(sizes, indent=1))
print("total MB:", round(sum(sizes.values()), 1))
