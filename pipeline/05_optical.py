"""Optical flood detection: Sentinel-2 (31 Oct, 5 Nov) and Landsat 8/9 (30 Oct) vs a clear baseline.

Water index = MNDWI (green vs SWIR). Cloud, shadow and snow are masked with the scene classification
(S2 SCL) or QA_PIXEL (Landsat). Fixed, physically motivated thresholds - not tuned on the CEMS data.
"""
import common as c
import numpy as np
import planetary_computer as pc
import pystac_client

cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                modifier=pc.sign_inplace)
bbox = list(c.BBOX_LL)


def s2_scene(date):
    items = cat.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{date}/{date}").item_collection()
    mn, cl = [], []
    for it in items:
        g = c.read_to_grid(it.assets["B03"].href)
        s = c.read_to_grid(it.assets["B11"].href)
        scl = c.read_to_grid(it.assets["SCL"].href, resampling=c.Resampling.nearest)
        g, s = (g - 1000) / 10000, (s - 1000) / 10000  # post-2022 processing baseline offset
        m = (g - s) / np.maximum(g + s, 1e-6)
        bad = np.isin(scl, [0, 1, 3, 8, 9, 10, 11]) | ~np.isfinite(scl)
        m[bad] = np.nan
        mn.append(m)
        cl.append(bad)
    mndwi = np.nanmax(np.stack(mn), axis=0) if len(mn) > 1 else mn[0]  # tiles overlap little; keep clear value
    return mndwi


def landsat_scene(date):
    items = cat.search(collections=["landsat-c2-l2"], bbox=bbox, datetime=f"{date}/{date}",
                       query={"platform": {"in": ["landsat-8", "landsat-9"]}}).item_collection()
    outs = []
    for it in items:
        g = c.read_to_grid(it.assets["green"].href) * 2.75e-5 - 0.2
        s = c.read_to_grid(it.assets["swir16"].href) * 2.75e-5 - 0.2
        qa = c.read_to_grid(it.assets["qa_pixel"].href, resampling=c.Resampling.nearest)
        qa = np.nan_to_num(qa, nan=1).astype(np.uint16)
        bad = ((qa & 0b1111100) > 0) | ((qa & 1) > 0)  # fill, dilated cloud, cirrus, cloud, shadow, snow
        m = (g - s) / np.maximum(g + s, 1e-6)
        m[bad] = np.nan
        outs.append(m)
    print("  landsat scenes", len(outs))
    return np.nanmax(np.stack(outs), axis=0) if outs else None


for tag, fn, date in [("s2_20241021", s2_scene, "2024-10-21"), ("s2_20241026", s2_scene, "2024-10-26"),
                      ("s2_20241031", s2_scene, "2024-10-31"), ("s2_20241105", s2_scene, "2024-11-05"),
                      ("l8_20241030", landsat_scene, "2024-10-30")]:
    a = fn(date)
    if a is None:
        print(tag, "no scenes")
        continue
    c.save(a, f"mndwi_{tag}.tif")
    print(tag, "clear %:", round(100 * float(np.isfinite(a).mean()), 1),
          "| MNDWI>0 %:", round(100 * float(np.nanmean(a > 0)), 2))
