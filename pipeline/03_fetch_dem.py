"""Copernicus GLO-30 DEM onto the study grid, plus slope and HAND (height above nearest drainage)."""
import common as c
import numpy as np
import planetary_computer as pc
import pystac_client
from pysheds.grid import Grid
from pysheds.sview import Raster, ViewFinder
from scipy import ndimage as ndi

cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                modifier=pc.sign_inplace)
items = cat.search(collections=["cop-dem-glo-30"], bbox=list(c.BBOX_LL)).item_collection()
print(len(items), "DEM tiles")
parts = [c.read_to_grid(it.assets["data"].href) for it in items]
dem = np.nanmean(np.stack(parts), axis=0)
dem = np.where(np.isfinite(dem), dem, 0).astype("float32")
c.save(dem, "dem.tif")
print("dem range", float(dem.min()), float(dem.max()))

gy, gx = np.gradient(ndi.gaussian_filter(dem, 1.0), c.RES)
slope = np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")
c.save(slope, "slope.tif")

# HAND from a 30 m aggregate (pysheds on 10 m is slow and the source DEM is 30 m anyway)
f = 3
h, w = dem.shape[0] // f * f, dem.shape[1] // f * f
dem30 = dem[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))
aff = c.TRANSFORM * c.TRANSFORM.scale(f, f)
dem30 = dem30.astype("float32")
vf = ViewFinder(affine=aff, shape=dem30.shape, crs=c.CRS, nodata=np.float32(-9999))
dem_r = Raster(dem30, vf)
grid = Grid.from_raster(dem_r)
flooded = grid.fill_pits(dem_r)
flooded = grid.fill_depressions(flooded)
inflated = grid.resolve_flats(flooded)
fdir = grid.flowdir(inflated)
acc = grid.accumulation(fdir)
streams = acc > 800  # ~0.7 km2 contributing area at 30 m
hand30 = grid.compute_hand(fdir, inflated, streams)
hand30 = np.asarray(hand30, dtype="float32")
hand = np.kron(hand30, np.ones((f, f), dtype="float32"))
hand = np.pad(hand, ((0, dem.shape[0] - hand.shape[0]), (0, dem.shape[1] - hand.shape[1])), mode="edge")
c.save(np.where(np.isfinite(hand), hand, 99).astype("float32"), "hand.tif")
print("hand ok; share < 5 m:", round(float((hand < 5).mean()), 3))
