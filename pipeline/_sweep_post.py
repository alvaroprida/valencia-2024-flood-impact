import importlib
import sys

import common as c
import geopandas as gpd
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import remove_small_objects

RUN = sys.argv[1] if len(sys.argv) > 1 else "base"
s = importlib.import_module("04_sar_flood")
d = np.nan_to_num(c.load(f"sfincs_{RUN}_depth10.tif"), nan=0.0)
alb = ndi.binary_dilation((c.load("flood_s1_20241101.tif") > 0) | (np.nan_to_num(c.load("mndwi_s2_20241026.tif"), nan=-1) > 0), iterations=15)
truth = {}
for aoi in ("AOI03", "AOI04"):
    p = f"data/raw/cems/EMSR773_{aoi}_DEL_PRODUCT_v1/x/EMSR773_{aoi}_DEL_PRODUCT"
    fp = gpd.read_file(f"{p}_imageFootprintA_v1.shp")
    truth[aoi] = (s.rasterize(gpd.read_file(f"{p}_observedEventA_v1.shp")), s.rasterize(fp[fp.obj_type == "Image Footprint"]))

print(f"{'hmin':>5} {'albufera mask':>14} {'min ha':>7} | {'AOI04 CSI':>9} {'rec':>5} {'prec':>5} {'area x':>6} | {'AOI03 CSI':>9} {'rec':>5} {'prec':>5} {'area x':>6}")
for hmin in (0.1, 0.3, 0.5):
    for mask_alb in (False, True):
        for minpx in (0, 100):
            f = d >= hmin
            if mask_alb:
                f &= ~alb
            if minpx:
                f = remove_small_objects(f, minpx)
            row = []
            for aoi in ("AOI04", "AOI03"):
                t, fp = truth[aoi]
                m = s.metrics(f, t, fp)
                row.append(f"{m['csi']:9.3f} {m['recall']:5.2f} {m['precision']:5.2f} {(m['tp_km2'] + m['fp_km2']) / max(m['tp_km2'] + m['fn_km2'], 1e-9):6.1f}")
            print(f"{hmin:5.1f} {str(mask_alb):>14} {minpx * 0.01:7.1f} | " + " | ".join(row))
