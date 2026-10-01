#!/usr/bin/env python3
"""Download Sketchfab models (glTF) by uid. Usage: sfdl.py name:uid ..."""
import json, os, sys, urllib.request, zipfile, io
TOKEN = open(os.path.expanduser("~/.secrets/sketchfab")).read().strip()
OUT = os.path.expanduser("~/gta-india/assets/sketchfab")
H = {"Authorization": f"Token {TOKEN}"}
def get(url, auth=True):
    req = urllib.request.Request(url, headers=H if auth else {})
    return urllib.request.urlopen(req, timeout=300).read()
credits = os.path.join(OUT, "CREDITS.txt")
for arg in sys.argv[1:]:
    name, uid = arg.split(":")
    dest = os.path.join(OUT, name)
    if os.path.isdir(dest):
        print("skip", name); continue
    try:
        meta = json.loads(get(f"https://api.sketchfab.com/v3/models/{uid}"))
        dl = json.loads(get(f"https://api.sketchfab.com/v3/models/{uid}/download"))
        zipfile.ZipFile(io.BytesIO(get(dl["gltf"]["url"], auth=False))).extractall(dest)
        with open(credits, "a") as f:
            f.write(f'{name}: "{meta["name"]}" by {meta["user"]["displayName"]} ({meta["license"]["label"]}) https://sketchfab.com/3d-models/{uid}\n')
        print("ok", name)
    except Exception as e:
        print("FAIL", name, e)
