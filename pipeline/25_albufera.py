"""Albufera lake outline from the 26 Oct Sentinel-2 water mask (pre-event, 10 m).

The lake is managed: sluices (golas) keep its level near the sea. FABDEM (30 m) cannot resolve the outlets, so in the model
the lake is held at sea level as a fixed-head boundary instead of filling up with runoff.
"""
import _env  # noqa: F401
import common as c
import geopandas as gpd
import numpy as np
from pyproj import Transformer
from rasterio import features
from scipy import ndimage as ndi
from shapely.geometry import shape
from skimage.morphology import remove_small_holes

w = np.nan_to_num(c.load("mndwi_s2_20241026.tif"), nan=-1) > 0.0
w = remove_small_holes(w, 5000)
lab, n = ndi.label(w, structure=np.ones((3, 3)))
t = Transformer.from_crs("EPSG:4326", c.CRS, always_xy=True)
col, row = ~c.TRANSFORM * t.transform(-0.355, 39.330)
comp = lab[int(row), int(col)]
lake = lab == comp
print("lake component pixels:", int(lake.sum()), "| area km2:", round(float(lake.sum()) * 1e-4, 1))
polys = [shape(g) for g, v in features.shapes(lake.astype("uint8"), mask=lake, transform=c.TRANSFORM) if v == 1]
poly = max(polys, key=lambda p: p.area).simplify(15)
gdf = gpd.GeoDataFrame({"name": ["Albufera lake"]}, geometry=[poly], crs=c.CRS).to_crs(4326)
gdf.to_file("data/processed/albufera_lake.geojson", driver="GeoJSON")
print("saved polygon, area km2 (UTM):", round(poly.area / 1e6, 1), "| bounds:", [round(v, 3) for v in gdf.total_bounds])
