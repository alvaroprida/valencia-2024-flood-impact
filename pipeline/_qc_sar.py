"""Quick QC figure: SAR change, detection and CEMS truth on the study grid."""
import importlib

import common as c
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

s = importlib.import_module("04_sar_flood")
truth, foot = s.cems_truth()
dvv = c.load("dvv_20241101.tif")
water = c.load("flood_s1_20241101.tif") > 0
post = s.db(c.load("s1_post_20241101_vv.tif"))
ext = [c.TRANSFORM.c, c.TRANSFORM.c + c.W * c.RES, c.TRANSFORM.f - c.H * c.RES, c.TRANSFORM.f]

fig, ax = plt.subplots(1, 3, figsize=(21, 8))
ax[0].imshow(post, extent=ext, cmap="gray", vmin=-25, vmax=0); ax[0].set_title("S1 VV 1 Nov (dB)")
ax[1].imshow(dvv, extent=ext, cmap="RdBu", vmin=-8, vmax=8); ax[1].set_title("VV change vs baseline (dB)")
rgb = np.zeros((c.H, c.W, 3)); rgb[..., 0] = water; rgb[..., 2] = truth; rgb[..., 1] = foot * 0.25
ax[2].imshow(rgb, extent=ext); ax[2].set_title("red = S1 flood, blue = CEMS VHR, green tint = analysed footprint")
for a in ax:
    a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig("data/processed/qc_sar.png", dpi=70)
print("saved")
