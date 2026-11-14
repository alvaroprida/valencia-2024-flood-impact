"""Catchments and stream network from FABDEM (30 m, UTM 30N), for the maps and the basin rainfall check."""
import json

import common as c
import geopandas as gpd
import numpy as np
import rasterio
from pysheds.grid import Grid
from pysheds.sview import Raster, ViewFinder
from rasterio import features
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from shapely.geometry import Point, shape

RES = 30.0
# pour points: name -> (lon, lat) (SAIH gauge positions from the MITECO layer)
POINTS = {
    "Rambla del Poyo (A-3 gauge)": (-0.5818, 39.4754),
    "Magro at Forata dam": (-0.8647, 39.3412),
    "Magro at Guadassuar": (-0.4710, 39.2014),
    "Turia at Vilamarxant": (-0.6423, 39.5939),
}

# wide FABDEM -> UTM 30N @ 30 m
with rasterio.open(f"{c.RAW}/fabdem_wide.tif") as src:
    x0, y0, x1, y1 = rasterio.warp.transform_bounds("EPSG:4326", c.CRS, *src.bounds)
    x0, y0 = np.floor(x0 / RES) * RES, np.floor(y0 / RES) * RES
    w, h = int((x1 - x0) / RES), int((y1 - y0) / RES)
    tr = from_origin(x0, y0 + h * RES, RES, RES)
    dem = np.full((h, w), -9999, dtype="float32")
    reproject(rasterio.band(src, 1), dem, src_transform=src.transform, src_crs=src.crs, dst_transform=tr,
              dst_crs=c.CRS, resampling=Resampling.bilinear, src_nodata=-9999, dst_nodata=-9999)
print("dem 30 m", dem.shape)

vf = ViewFinder(affine=tr, shape=dem.shape, crs=c.CRS, nodata=np.float32(-9999))
raster = Raster(dem, vf)
grid = Grid.from_raster(raster)
dem_f = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(raster)))
fdir = grid.flowdir(dem_f)
acc = grid.accumulation(fdir)
np.save(f"{c.PROC}/acc30.npy", np.asarray(acc).astype("float32"))

from pyproj import Transformer
t = Transformer.from_crs("EPSG:4326", c.CRS, always_xy=True)
polys, info = [], []
for name, (lon, lat) in POINTS.items():
    x, y = t.transform(lon, lat)
    xs, ys = grid.snap_to_mask(acc > 20000, (x, y))  # snap to a main channel (>18 km2)
    catch = grid.catchment(x=xs, y=ys, fdir=fdir, xytype="coordinate")
    m = np.asarray(catch).astype("uint8")
    geom = [shape(g) for g, v in features.shapes(m, mask=m > 0, transform=tr) if v == 1]
    poly = max(geom, key=lambda g: g.area)
    polys.append(poly)
    info.append(dict(name=name, area_km2=round(poly.area / 1e6, 1), snapped_m=round(float(np.hypot(xs - x, ys - y)))))
    print(info[-1])
gdf = gpd.GeoDataFrame(info, geometry=polys, crs=c.CRS).to_crs(4326)
gdf.to_file(f"{c.PROC}/basins.geojson", driver="GeoJSON")

# streams: accumulation > 5 km2 (5.5k cells), vectorised with Strahler-like width from accumulation
st = grid.extract_river_network(fdir, acc > 5500)
rivers = gpd.GeoDataFrame(
    [dict(acc_km2=round(float(f["properties"].get("acc", 0)), 1)) for f in st["features"]],
    geometry=[shape(f["geometry"]) for f in st["features"]], crs=c.CRS).to_crs(4326)
rivers.to_file(f"{c.PROC}/streams.geojson", driver="GeoJSON")
print("stream segments:", len(rivers))
