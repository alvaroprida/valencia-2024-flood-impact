"""Download the layers of the public Docker Hub image deltares/sfincs-cpu without Docker."""
import json
import os
import sys

import requests

REPO, TAG = "deltares/sfincs-cpu", sys.argv[1] if len(sys.argv) > 1 else "sfincs-v2.4.1"
OUT = "tools/sfincs_image"
os.makedirs(OUT, exist_ok=True)

tok = requests.get("https://auth.docker.io/token", params={
    "service": "registry.docker.io", "scope": f"repository:{REPO}:pull"}, timeout=30).json()["token"]
H = {"Authorization": f"Bearer {tok}"}
ACC = ",".join(["application/vnd.oci.image.index.v1+json", "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json", "application/vnd.docker.distribution.manifest.v2+json"])
reg = f"https://registry-1.docker.io/v2/{REPO}"

m = requests.get(f"{reg}/manifests/{TAG}", headers={**H, "Accept": ACC}, timeout=30).json()
if "manifests" in m:  # multi-arch index
    pick = next(x for x in m["manifests"] if x["platform"]["os"] == "linux" and x["platform"]["architecture"] == "amd64")
    m = requests.get(f"{reg}/manifests/{pick['digest']}", headers={**H, "Accept": ACC}, timeout=30).json()
json.dump(m, open(f"{OUT}/manifest.json", "w"), indent=1)

cfg = requests.get(f"{reg}/blobs/{m['config']['digest']}", headers=H, timeout=30).json()
print("entrypoint:", cfg["config"].get("Entrypoint"), "| cmd:", cfg["config"].get("Cmd"), "| workdir:", cfg["config"].get("WorkingDir"))
print("env:", cfg["config"].get("Env"))

for i, layer in enumerate(m["layers"]):
    path = f"{OUT}/layer{i:02d}.tar.gz"
    print(f"layer {i}: {layer['size'] / 1e6:.1f} MB {layer['mediaType'].split('.')[-1]}")
    with requests.get(f"{reg}/blobs/{layer['digest']}", headers=H, stream=True, timeout=300) as r, open(path, "wb") as f:
        r.raise_for_status()
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
print("done ->", OUT)
