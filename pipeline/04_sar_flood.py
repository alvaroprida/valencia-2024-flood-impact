"""Sentinel-1 flood extent by change detection, validated against CEMS EMSR773 (VHR optical)."""
import glob
import json

import common as c
import geopandas as gpd
import numpy as np
from rasterio import features
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu
from skimage.morphology import remove_small_objects


def db(a, k=5):
    """Boxcar speckle filter in linear power, then dB."""
    lin = ndi.uniform_filter(np.nan_to_num(a, nan=np.nanmedian(a)), k)
    return 10 * np.log10(np.maximum(lin, 1e-6))


def rasterize(gdf, value=1):
    g = gdf.to_crs(c.CRS)
    return features.rasterize(((geom, value) for geom in g.geometry if geom is not None),
                              out_shape=(c.H, c.W), transform=c.TRANSFORM, fill=0, dtype="uint8").astype(bool)


def cems_truth():
    """Flooded area (VHR optical, 31 Oct 10:22) and analysed footprint for AOI03 + AOI04."""
    flood, foot = np.zeros((c.H, c.W), bool), np.zeros((c.H, c.W), bool)
    for aoi in ("AOI03", "AOI04"):
        d = f"data/raw/cems/EMSR773_{aoi}_DEL_PRODUCT_v1/x/EMSR773_{aoi}_DEL_PRODUCT"
        ev = gpd.read_file(f"{d}_observedEventA_v1.shp")
        fp = gpd.read_file(f"{d}_imageFootprintA_v1.shp")
        flood |= rasterize(ev)
        foot |= rasterize(fp[fp.obj_type == "Image Footprint"])
    return flood, foot


def metrics(pred, truth, mask):
    p, t = pred[mask], truth[mask]
    tp, fp, fn = int((p & t).sum()), int((p & ~t).sum()), int((~p & t).sum())
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return dict(precision=round(prec, 3), recall=round(rec, 3),
                f1=round(2 * prec * rec / max(prec + rec, 1e-9), 3), csi=round(tp / max(tp + fp + fn, 1), 3),
                tp_km2=round(tp * 1e-4, 1), fp_km2=round(fp * 1e-4, 1), fn_km2=round(fn * 1e-4, 1))


if __name__ == "__main__":
    dem, slope, hand = c.load("dem.tif"), c.load("slope.tif"), c.load("hand.tif")
    exclude = (hand > 15) | (slope > 5)

    out = {}
    for tag, base_set in (("20241101", "base_o110"), ("20241106", "base_o8")):
        b = {p: db(c.load(f"s1_{base_set}_{p}.tif")) for p in ("vv", "vh")}
        e = {p: db(c.load(f"s1_post_{tag}_{p}.tif")) for p in ("vv", "vh")}
        valid = np.isfinite(c.load(f"s1_post_{tag}_vv.tif")) & np.isfinite(c.load(f"s1_{base_set}_vv.tif")) & ~exclude

        t_vv = threshold_otsu(e["vv"][valid & (e["vv"] > -30) & (e["vv"] < -3)])
        t_vv = float(np.clip(t_vv, -20, -14))
        dvv = e["vv"] - b["vv"]
        dvh = e["vh"] - b["vh"]
        water = (e["vv"] < t_vv) & ((dvv < -3) | (dvh < -3)) & (b["vv"] > t_vv) & valid
        water = remove_small_objects(water, 50)  # 0.5 ha
        water = ~remove_small_objects(~water, 20) | water  # fill small holes
        c.save(water.astype("float32"), f"flood_s1_{tag}.tif")
        c.save(dvv, f"dvv_{tag}.tif")

        truth, foot = cems_truth()
        m = metrics(water, truth, foot)
        out[tag] = dict(threshold_vv_db=round(t_vv, 2), flooded_km2_study=round(float(water.sum()) * 1e-4, 1),
                        validation_vs_cems_vhr=m)
        print(tag, json.dumps(out[tag], indent=1))

    json.dump(out, open(f"{c.PROC}/validation_s1.json", "w"), indent=1)
