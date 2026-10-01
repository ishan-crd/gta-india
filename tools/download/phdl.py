#!/usr/bin/env python3
"""Download Poly Haven assets. Usage: phdl.py textures|models|hdris id ..."""
import json, os, sys, urllib.request
UA = {"User-Agent": "gta-india-build/1.0"}
ROOT = os.path.expanduser("~/gta-india/assets/polyhaven")
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=300).read()
def save(url, path):
    if os.path.exists(path): return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = get(url); open(path, "wb").write(data)
kind, ids = sys.argv[1], sys.argv[2:]
for aid in ids:
    try:
        f = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
        d = os.path.join(ROOT, kind, aid)
        if kind == "textures":
            maps = {"Diffuse": "diff", "nor_gl": "nor", "arm": "arm", "Displacement": "disp"}
            for k, short in maps.items():
                if k in f:
                    e = f[k]["2k"]["jpg" if "jpg" in f[k]["2k"] else "png"]
                    ext = e["url"].rsplit(".", 1)[1]
                    save(e["url"], f"{d}/{aid}_{short}.{ext}")
        elif kind == "hdris":
            save(f["hdri"]["4k"]["hdr"]["url"], f"{d}/{aid}_4k.hdr")
        elif kind == "models":
            g = f["gltf"]["2k"]["gltf"]
            save(g["url"], f"{d}/{aid}.gltf")
            for rel, inc in g.get("include", {}).items():
                save(inc["url"], f"{d}/{rel}")
        print("ok", aid)
    except Exception as ex:
        print("FAIL", aid, ex)
