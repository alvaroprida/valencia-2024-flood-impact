"""Optical flood extent (Sentinel-2, 31 Oct and 5 Nov) vs the clear 26 Oct baseline; scored against CEMS VHR."""
import importlib
import json

import common as c
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from skimage.morphology import remove_small_objects

s = importlib.import_module("04_sar_flood")
truth, foot = s.cems_truth()
hand, slope = c.load("hand.tif"), c.load("slope.tif")
base = c.load("mndwi_s2_20241026.tif")
exclude = (hand > 15) | (slope > 5)

res, figs = {}, []
for tag in ("20241031", "20241105"):
    post = c.load(f"mndwi_s2_{tag}.tif")
    clear = np.isfinite(post) & np.isfinite(base)
    # new water: wet now, not wet at baseline; permanent water excluded by the baseline
    water = (post > 0.0) & (base < -0.1) & clear & ~exclude
    water = remove_small_objects(water, 30)
    c.save(water.astype("float32"), f"flood_s2_{tag}.tif")
    mask = foot & clear
    res[tag] = dict(clear_share_of_footprint=round(float((foot & clear).sum() / foot.sum()), 3),
                    flooded_km2_study=round(float(water.sum()) * 1e-4, 1),
                    vs_cems_vhr_clear_pixels_only=s.metrics(water, truth, mask))
    print(tag, json.dumps(res[tag], indent=1))
    figs.append((tag, post, water, clear))

ext = [c.TRANSFORM.c, c.TRANSFORM.c + c.W * c.RES, c.TRANSFORM.f - c.H * c.RES, c.TRANSFORM.f]
fig, ax = plt.subplots(1, 3, figsize=(21, 8))
tag, post, water, clear = figs[0]
ax[0].imshow(post, extent=ext, cmap="BrBG", vmin=-0.6, vmax=0.6); ax[0].set_title(f"MNDWI {tag} (blank = cloud)")
rgb = np.zeros((c.H, c.W, 3)); rgb[..., 0] = water; rgb[..., 2] = truth; rgb[..., 1] = (~clear) * 0.35
ax[1].imshow(rgb, extent=ext); ax[1].set_title("red = S2 flood, blue = CEMS, green = cloud")
rgb2 = np.zeros((c.H, c.W, 3)); rgb2[..., 0] = water & truth; rgb2[..., 1] = truth & ~water; rgb2[..., 2] = water & ~truth
ax[2].imshow(rgb2, extent=ext); ax[2].set_title("yellow=hit, green=missed, blue=false alarm")
for a in ax:
    a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig("data/processed/qc_optical.png", dpi=70)
json.dump(res, open(f"{c.PROC}/validation_s2.json", "w"), indent=1)
