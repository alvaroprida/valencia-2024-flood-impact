"""Build, run (SFINCS in WSL1) and score a list of calibration variants, one after the other.

usage: python pipeline/26_run_variants.py name:cn_shift:rain_scale:manning_scale [...]
Calibration target: Algemesi (CEMS AOI04). Horta Sud (AOI03) is held out and only reported.
"""
import json
import subprocess
import sys
import time

PY = sys.executable
LOG = "data/processed/variants_log.txt"


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    print(msg, flush=True)


for spec in sys.argv[1:]:
    name, cn, rain, man = spec.split(":")
    t0 = time.time()
    log(f"== {name}: CN {cn} | rain x{rain} | Manning x{man}")
    subprocess.run([PY, "pipeline/19_build_sfincs.py", name, cn, rain, man, "lake"], check=True, capture_output=True)
    r = subprocess.run(["wsl", "-d", "sfincs", "--", "bash", "/mnt/c/Users/alvar/Documents/github/valencia-2024-flood-impact/tools/run_sfincs.sh", name],
                       capture_output=True)
    log(f"   run finished in {(time.time() - t0) / 60:.1f} min (exit {r.returncode})")
    p = subprocess.run([PY, "pipeline/22_flood_results.py", name], capture_output=True, text=True)
    v = json.load(open(f"data/processed/validation_sfincs_{name}.json"))
    for k in ("Algemesi (AOI04)", "Horta Sud (AOI03)"):
        m = v[k]
        log(f"   {k}: CSI {m['csi']} recall {m['recall']} precision {m['precision']} area ratio {m['area_ratio_model_to_obs']}")
    log(f"   water balance {v.get('water_balance')} | area>0.3m {v['flooded_km2_in_grid']} km2")
