"""Fetch Sentinel-1 RTC (gamma0, 10 m, Planetary Computer) onto the study grid.

Relative orbit 110 (descending, ~06:02 UTC): same geometry for the baseline and the post-event
scene. Baseline = 8 and 20 Oct 2024 (dry, before the DANA). Post-event = 1 Nov (3 days after the
peak) and 13 Nov is not available, so 1 Nov is the main acquisition; 6 Nov (orbit 8) is a second look.
"""
import common as c
import numpy as np
import planetary_computer as pc
import pystac_client

cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                modifier=pc.sign_inplace)
bbox = list(c.BBOX_LL)

SETS = {
    "base_o110": ("2024-10-08/2024-10-20", 110),
    "post_20241101": ("2024-11-01/2024-11-01", 110),
    "post_20241106": ("2024-11-06/2024-11-06", 8),
    "base_o8": ("2024-10-13/2024-10-25", 8),
}

for name, (dates, orbit) in SETS.items():
    items = [i for i in cat.search(collections=["sentinel-1-rtc"], bbox=bbox, datetime=dates).item_collection()
             if i.properties.get("sat:relative_orbit") == orbit]
    print(name, len(items), "scenes")
    for pol in ("vv", "vh"):
        stack = []
        for it in items:
            stack.append(c.read_to_grid(it.assets[pol].href))
        arr = np.nanmean(np.stack(stack), axis=0) if len(stack) > 1 else stack[0]
        c.save(arr, f"s1_{name}_{pol}.tif")
        print("  ", pol, "valid %:", round(100 * np.isfinite(arr).mean(), 1))
