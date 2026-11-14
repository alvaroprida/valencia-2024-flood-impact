"""Parse the CHJ event report (Annex II) into a rain-gauge table and locate each gauge by municipality.

Coordinates are the municipality centre (Nominatim / OpenStreetMap), NOT the gauge itself: approximate to a
few km. AEMET stations keep their exact coordinates (08_aemet_daily.py).
"""
import json
import os
import re
import time

import requests

TXT = "data/raw/chj/informe_episodio_chj.txt"
OUT = "data/processed/chj_rain_gauges.json"
CACHE = "data/raw/chj/geocode_cache.json"
UA = {"User-Agent": "valencia-2024-flood-impact/0.1 (https://github.com/alvaroprida/valencia-2024-flood-impact)"}

pat = re.compile(r"^(?P<txt>.+?)\s+\((?P<prov>V|CS|TE|CU|AB|A)\)\s+(?P<mm>\d+(?:[.,]\d+)?)\s*$")
rows, seen, basin = [], set(), None
for line in open(TXT, encoding="utf-8"):
    line = line.strip()
    if line.startswith("* CUENCA"):
        basin = line[2:].strip().title()
        continue
    m = pat.match(line)
    if not m or m["prov"] != "V":
        continue
    key = (m["txt"], float(m["mm"].replace(",", ".")))
    if key in seen:
        continue
    seen.add(key)
    rows.append(dict(text=m["txt"], mm=float(m["mm"].replace(",", ".")), basin=basin))
print("valencia-province gauges:", len(rows))

cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}


def geocode(q):
    if q in cache:
        return cache[q]
    time.sleep(1.1)  # Nominatim usage policy: max 1 request/second
    r = requests.get("https://nominatim.openstreetmap.org/search", headers=UA, timeout=30, params={
        "q": f"{q}, Valencia, Spain", "format": "json", "limit": 3, "countrycodes": "es", "addressdetails": 1})
    res = [x for x in r.json() if x.get("addresstype") in ("village", "town", "city", "municipality", "hamlet",
                                                            "suburb", "administrative", "county")
           and "València" in x.get("display_name", "") + x.get("display_name", "").replace("Valencia", "València")]
    cache[q] = dict(lat=float(res[0]["lat"]), lon=float(res[0]["lon"]), name=res[0]["display_name"].split(",")[0]) if res else None
    return cache[q]


for r in rows:
    words = r["text"].replace("'", "’").split()
    r["lat"] = r["lon"] = r["municipality"] = None
    for n in (3, 2, 1):  # longest trailing word group that resolves to a place in Valencia province
        if len(words) <= n:
            continue
        g = geocode(" ".join(words[-n:]))
        if g:
            r.update(lat=g["lat"], lon=g["lon"], municipality=g["name"], matched=" ".join(words[-n:]))
            break
json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
ok = [r for r in rows if r["lat"] is not None]
print("located:", len(ok), "of", len(rows))
os.makedirs("data/processed", exist_ok=True)
json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in sorted(ok, key=lambda r: -r["mm"])[:14]:
    print(f'{r["mm"]:6.1f}  {r["text"][:45]:45s} -> {r["municipality"]} ({r["lat"]:.3f}, {r["lon"]:.3f})')
print("unlocated:", [r["text"] for r in rows if r["lat"] is None][:10])
