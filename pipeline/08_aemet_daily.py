"""AEMET OpenData: station inventory and daily precipitation, 27 Oct - 1 Nov 2024, Valencia region."""
import json
import os
import time

import requests

KEY = next(l.split("=", 1)[1].strip() for l in open(".env") if l.startswith("AEMET_API_KEY="))
BASE = "https://opendata.aemet.es/opendata/api"
H = {"api_key": KEY, "Accept": "application/json"}
os.makedirs("data/raw/aemet", exist_ok=True)


def get(path):
    for _ in range(4):
        r = requests.get(BASE + path, headers=H, timeout=60)
        if r.status_code == 429:
            time.sleep(15)
            continue
        r.raise_for_status()
        meta = r.json()
        if meta.get("estado") != 200:
            raise RuntimeError(f"{path}: {meta}")
        d = requests.get(meta["datos"], timeout=120)
        d.encoding = "latin-1"
        return d.json()
    raise RuntimeError("rate limited")


inv = get("/valores/climatologicos/inventarioestaciones/todasestaciones")
json.dump(inv, open("data/raw/aemet/inventory.json", "w", encoding="utf-8"), ensure_ascii=False)
print("stations in inventory:", len(inv), "| keys:", list(inv[0].keys()))

daily = get("/valores/climatologicos/diarios/datos/fechaini/2024-10-27T00:00:00UTC/"
            "fechafin/2024-11-01T23:59:59UTC/todasestaciones")
json.dump(daily, open("data/raw/aemet/daily_20241027_20241101.json", "w", encoding="utf-8"), ensure_ascii=False)
print("daily records:", len(daily), "| keys:", list(daily[0].keys()))

vlc = [d for d in daily if d.get("provincia", "").upper() in ("VALENCIA", "VALENCIA/VALÈNCIA")]
print("Valencia-province records:", len(vlc))
top = sorted((d for d in vlc if d["fecha"] == "2024-10-29" and d.get("prec") not in (None, "Ip")),
             key=lambda d: -float(d["prec"].replace(",", ".")))[:12]
for d in top:
    print(d["fecha"], d["nombre"], d["prec"], "mm")
