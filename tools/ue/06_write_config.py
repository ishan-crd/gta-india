#!/usr/bin/env python3
"""Write the [/Script/GTAIndia.GIAssetSettings] section of Config/DefaultGame.ini from the assets
that actually exist in the project's Content folder. Plain Python (run on the Linux PC).

Usage: python3 06_write_config.py [--bike-yaw 180] [--train-yaw 0] [--box-bone Spine2]
"""
import argparse
import json
import os
import re

HOME = os.path.expanduser("~")
PROJECT = f"{HOME}/gta-india/GTAIndia"
CONTENT = f"{PROJECT}/Content"
INI = f"{PROJECT}/Config/DefaultGame.ini"
ASSETS = f"{HOME}/gta-india/assets"
SECTION = "[/Script/GTAIndia.GIAssetSettings]"


def exists(game_path):
    rel = game_path.replace("/Game/", "", 1)
    return os.path.exists(f"{CONTENT}/{rel}.uasset")


def obj(game_path):
    return f"{game_path}.{os.path.basename(game_path)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bike", default="BikePulsar150")
    ap.add_argument("--bike-yaw", type=float, default=180.0)  # Pulsar model front is on -X
    ap.add_argument("--bike-scale", type=float, default=1.0)
    ap.add_argument("--train", default="Train_EMU_Car")
    ap.add_argument("--train-engine", default="Train_EMU_Cab")
    ap.add_argument("--train-yaw", type=float, default=0.0)
    ap.add_argument("--box-bone", default="Spine2")
    ap.add_argument("--box-offset", default="(X=0.000000,Y=-6.000000,Z=124.000000)")
    ap.add_argument("--walk-speed", type=float, default=114.8)
    ap.add_argument("--run-speed", type=float, default=254.2)
    args = ap.parse_args()

    lines = [SECTION]
    player = "/Game/Characters/SK_Player/SK_Player"
    if exists(player):
        lines.append(f"PlayerMesh={obj(player)}")
    box = "/Game/Characters/DeliveryBox/SM_DeliveryBox"
    if exists(box):
        lines.append(f"DeliveryBoxMesh={obj(box)}")
    lines.append(f"DeliveryBoxBone={args.box_bone}")
    lines.append(f"DeliveryBoxOffset={args.box_offset}")

    clips = {"Idle": "A_Idle", "Walk": "A_Walk", "Run": "A_Run", "Jump": "A_Jump", "Fall": "A_Fall", "Land": "A_Land",
             "Swim": "A_Swim", "Sit": "A_SitIdle", "Death": "A_Death", "PickUp": "A_PickUp",
             "Tread": "A_Tread", "SitTalk": "A_SitTalk"}
    parts = []
    for field, name in clips.items():
        p = f"/Game/Characters/Anims/{name}"
        if exists(p):
            parts.append(f'{field}="{obj(p)}"')
    parts.append(f"WalkSpeed={args.walk_speed:.6f}")
    parts.append(f"RunSpeed={args.run_speed:.6f}")
    parts.append("WalkPlantPhase=0.065000")
    parts.append("RunPlantPhase=0.273000")
    lines.append("Anims=(" + ",".join(parts) + ")")

    chars_dir = f"{CONTENT}/Characters"
    try:
        variety = json.load(open(f"{ASSETS}/characters/variety.json"))
    except Exception:
        variety = {}
    manifest = {}
    try:
        manifest = {c["name"]: c for c in json.load(open(f"{ASSETS}/characters/manifest.json"))["characters"]}
    except Exception:
        pass
    if os.path.isdir(chars_dir):
        for d in sorted(os.listdir(chars_dir)):
            if not d.startswith("SK_") or d == "SK_Player":
                continue
            p = f"/Game/Characters/{d}/{d}"
            if exists(p):
                tag = manifest.get(d, {}).get("gender", "")
                weight = 0.6 if d in ("SK_OfficeWoman", "SK_Teen") else 1.0
                extra = ""
                v = variety.get(d, {})
                if v.get("tint_slots"):
                    extra += ",TintSlots=(" + ",".join(f'"{x}"' for x in v["tint_slots"]) + ")"
                if v.get("variants"):
                    extra += ",MaterialVariants=(" + ",".join(f'"{obj(x)}"' for x in v["variants"]) + ")"
                lines.append(f'+PedestrianLooks=(Mesh="{obj(p)}",Weight={weight:.6f},Tag="{tag}"{extra})')

    for name in ("Zebu",):
        p = f"/Game/GTAIndia/Props/{name}/SM_{name}"
        if exists(p):
            lines.append(f"CowMesh={obj(p)}")
    bike = f"/Game/GTAIndia/Props/{args.bike}/SM_{args.bike}"
    if exists(bike):
        lines.append(f"BikeMesh={obj(bike)}")
    lines.append(f"BikeMeshYaw={args.bike_yaw:.6f}")
    lines.append(f"BikeMeshScale={args.bike_scale:.6f}")
    def train_path(t):
        for cand in (f"/Game/GTAIndia/Kit/SM_{t}", f"/Game/GTAIndia/Props/{t}/SM_{t}"):
            if exists(cand):
                return cand
        return None
    for t in args.train.split(","):
        train = train_path(t)
        if train:
            lines.append(f"+TrainCarMeshes={obj(train)}")
    eng = train_path(args.train_engine) if args.train_engine else None
    if eng:
        lines.append(f"TrainEngineMesh={obj(eng)}")
    lines.append(f"TrainMeshYaw={args.train_yaw:.6f}")
    for key, p in (("MinimapMaterial", "/Game/GTAIndia/Materials/M_Minimap"), ("WaterMaterial", "/Game/GTAIndia/Materials/M_Water"),
                   ("MarkerMaterial", "/Game/GTAIndia/Materials/M_Marker"),
                   ("UnderwaterMaterial", "/Game/GTAIndia/Materials/M_Murk")):
        if exists(p):
            lines.append(f"{key}={obj(p)}")

    audio = {"AmbRiver": "A_AmbRiver", "AmbCity": "A_AmbCity", "TempleBells": "A_TempleBells", "TrainHorn": "S_TrainHorn",
             "TrainLoop": "A_TrainLoop", "BikeEngine": "A_BikeEngine", "BikeHorn": "S_BikeHorn", "Splash": "S_Splash",
             "SwimStroke": "S_SwimStroke", "Cash": "S_Cash"}
    for key, name in audio.items():
        p = f"/Game/GTAIndia/Audio/{name}"
        if exists(p):
            lines.append(f"{key}={obj(p)}")

    try:
        voices = json.load(open(f"{ASSETS}/audio/voice/voice_lines.json"))
    except Exception:
        voices = []
    for v in voices:
        p = f"/Game/GTAIndia/Audio/Voice/{v['name']}"
        if exists(p):
            text = v["text"].replace('"', "'")
            lines.append(f'+VoiceLines=(Sound="{obj(p)}",Category="{v["category"]}",Gender="{v["gender"]}",Text="{text}")')

    credits = []
    for f in (f"{ASSETS}/sketchfab/CREDITS.txt",):
        if os.path.exists(f):
            for line in open(f):
                line = line.strip()
                if line:
                    credits.append(line.split(": ", 1)[-1].replace('"', "'"))
    for c in credits:
        lines.append(f'+Credits="{c}"')
    lines.append('+Credits="Textures & HDRIs: Poly Haven (CC0) - polyhaven.com"')

    text = open(INI).read() if os.path.exists(INI) else ""
    text = re.sub(re.escape(SECTION) + r".*?(?=\n\[|\Z)", "", text, flags=re.S).rstrip() + "\n\n"
    text += "\n".join(lines) + "\n"
    open(INI, "w").write(text)
    print("\n".join(lines))


main()
