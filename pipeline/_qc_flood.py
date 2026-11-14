import importlib
import sys

import common as c
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RUN = sys.argv[1] if len(sys.argv) > 1 else "base"
s = importlib.import_module("04_sar_flood")
d = c.load(f"sfincs_{RUN}_depth10.tif")
truth, foot = s.cems_truth()
v = d[np.isfinite(d) & (d >= 0.1)]
print("depth percentiles (m) of flooded pixels:", {p: round(float(np.percentile(v, p)), 2) for p in (10, 25, 50, 75, 90, 99, 99.9)}, "| >20 m:", int((v > 20).sum()))
fp = foot & (d >= 0.1) & ~truth
vv = d[fp]
print("false-alarm pixels inside the CEMS footprint: depth percentiles", {p: round(float(np.percentile(vv, p)), 2) for p in (25, 50, 75, 90)})
print("share of false alarms shallower than 0.3 m:", round(float((vv < 0.3).mean()), 2), "| than 0.5 m:", round(float((vv < 0.5).mean()), 2))
vt = d[truth & foot & np.isfinite(d)]
print("depth at observed-flooded pixels (model): median", round(float(np.median(np.nan_to_num(d[truth & foot]))), 2), "| share modelled >=0.1:", round(float((vt >= 0.1).mean()), 2))
ext = [c.TRANSFORM.c, c.TRANSFORM.c + c.W * c.RES, c.TRANSFORM.f - c.H * c.RES, c.TRANSFORM.f]
fig, ax = plt.subplots(1, 2, figsize=(20, 9))
im = ax[0].imshow(np.where(d >= 0.1, np.clip(d, 0, 4), np.nan), extent=ext, cmap="Blues", vmin=0, vmax=4)
ax[0].contour(np.flipud(truth.astype(float)), levels=[0.5], extent=ext, colors="red", linewidths=0.6)
ax[0].set_title("SFINCS max depth (m, clipped at 4) | red = CEMS observed"); plt.colorbar(im, ax=ax[0], shrink=0.6)
rgb = np.zeros((c.H, c.W, 3)); rgb[..., 0] = (d >= 0.1) & ~truth; rgb[..., 1] = truth & ~(d >= 0.1); rgb[..., 2] = (d >= 0.1) & truth
ax[1].imshow(np.where(foot[..., None], rgb, 0.12), extent=ext); ax[1].set_title("red = false alarm, green = missed, blue = hit (inside CEMS footprint)")
for a in ax:
    a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig(f"data/processed/qc_flood_{RUN}.png", dpi=60)
print("saved")
