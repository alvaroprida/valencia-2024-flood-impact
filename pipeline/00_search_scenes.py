"""List Sentinel-1 RTC and Sentinel-2 L2A scenes over Valencia around the 29 Oct 2024 DANA."""
import planetary_computer as pc
import pystac_client

BBOX = [-0.75, 39.20, -0.25, 39.60]  # Horta Sud, Poyo, Magro and lower Turia
cat = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace
)

for coll, dates in [
    ("sentinel-1-rtc", "2024-10-01/2024-11-20"),
    ("sentinel-2-l2a", "2024-10-20/2024-11-12"),
]:
    items = cat.search(collections=[coll], bbox=BBOX, datetime=dates).item_collection()
    print(f"\n== {coll}: {len(items)} items")
    for it in sorted(items, key=lambda i: i.datetime):
        p = it.properties
        extra = (
            f"orbit={p.get('sat:orbit_state')} rel={p.get('sat:relative_orbit')}"
            if coll.startswith("sentinel-1")
            else f"cloud={p.get('eo:cloud_cover'):.0f}%"
        )
        print(it.datetime.strftime("%Y-%m-%d %H:%M"), it.id[:60], extra)
