# GTA India — Varanasi

An Unreal Engine 5.8 open-world prototype inspired by the "GTA 6 India edition" clip: you are a
food-delivery rider in Varanasi. Pick up an order in town, race along the dusty road beside an
overcrowded train (or jump on its roof), reach Dashashwamedh Ghat and swim across the Ganga to
deliver at Ramnagar Ghat before the timer runs out. Swimming in the Ganga drains your HP.

## Layout

| Path | What |
|---|---|
| `GTAIndia/` | UE project (C++ module `GTAIndia`, configs). `Content/` is generated on the PC and not in git. |
| `GTAIndia/Source/GTAIndia` | Gameplay: player, swimming movement, code-driven animation, bike, train, crowd, mission, HUD/minimap, Slate menus + settings. |
| `tools/blender` | Procedural Varanasi building kit, character/animation retargeting, prop conversion. |
| `tools/ue` | Editor-Python pipeline: materials → meshes → characters → audio → level → config. |
| `tools/audio` | Procedural audio synthesis (ambience, horns, engine...). |
| `tools/pc` | Shell helpers run on the Linux build PC (`ssh linux`). |
| `tools/stream` | Headless X screen + browser streaming to play from the Mac. |
| `SPEC.md` | World layout, units, material slots. |

## Build pipeline (on the Linux PC)

```bash
tools/sync.sh                                   # Mac -> PC
ssh linux
cd ~/gta-india/repo
tools/pc/build_editor.sh                        # compile the game module
tools/pc/ue_python.sh tools/ue/01_materials.py
tools/pc/ue_python.sh tools/ue/02_import_meshes.py
tools/pc/ue_python.sh tools/ue/03_import_characters.py
tools/pc/ue_python.sh tools/ue/04_import_audio.py
tools/pc/ue_python_editor.sh tools/ue/05_build_level.py
python3 tools/ue/06_write_config.py
tools/pc/ue_python.sh tools/ue/07_material_usage.py      # usage flags (else default material in game)
tools/pc/ue_python_editor.sh tools/ue/08_char_lods.py    # crowd LODs
tools/pc/ue_python.sh tools/ue/09_detail.py              # debris, wires, grass, signboards
tools/pc/ue_python.sh tools/ue/10_variety.py             # outfit colours, saree variants, underwater murk
tools/pc/package.sh                             # Shipping build -> ~/gta-india/build
```

## Play it from the Mac

The game streams from the Linux PC to any browser (Chrome recommended), keyboard/mouse and gamepad:

1. Tunnel the stream (browsers only allow its input APIs on https or localhost):
   `ssh -f -N -L 8080:127.0.0.1:8080 linux`
2. Open **http://localhost:8080**. User `ishan`, password: `ssh linux cat .secrets/stream_pass`.
3. Click into the game once to lock the mouse (Esc releases it); plug in a controller any time.
   Mouse look also works without the lock: `tools/stream/patch_selkies.py` turns the browser's
   absolute cursor positions into relative motion while the game hides the cursor.
4. If the page is black: `ssh linux bash gta-india/repo/tools/stream/start_stream.sh`.
   Stop everything: `ssh linux bash gta-india/repo/tools/stream/stop_stream.sh`.

How it works: a private headless X screen `:5` on the RTX 3090 (never touches the PC's monitor or
the other users' consoles; no host input devices), Selkies 2.0 (NVENC H.264 over websockets) bound to
localhost and reached through an SSH tunnel, and the packaged Shipping build in a relaunch loop.

## Controls

| Action | Keyboard / mouse | Controller |
|---|---|---|
| Move / look | WASD / mouse | Left / right stick |
| Sprint (also swim faster) | Shift | L3 or RT |
| Jump | Space | A |
| Dive (while swimming) | C / Ctrl | B |
| Interact (climb onto train) | E | X |
| Get on / off bike | F | Y |
| Bike throttle / brake | W / S | RT / LT |
| Handbrake · Horn | Space · H | A · LB |
| Pause / settings | Esc | Start |

Settings: presets Low / Medium / High / Ultra plus auto-detect; resolution, window mode, VSync,
frame limit, resolution scale, AA/upscaler (TSR/TAA/FXAA), every scalability group, crowd density,
volumetric fog, motion blur, film grain, FOV, sensitivity, invert Y, FPS counter.

## Performance tips (also shown in-game under Settings)

Each setting shows its FPS cost (low / medium / high). Biggest wins, in order:
1. **Resolution Scale 70–80% + TSR**: nearly the same sharpness, +30–50% FPS (raise Sharpening a bit).
2. **Global Illumination (Lumen) Medium/Low** and **Shadows Medium** with **Shadow Distance 75%**.
3. **Crowd Density** and **Crowd Shadows** (the busy ghats and the packed train roof are the heaviest scenes).
4. **Draw Distance 80%**, **Volumetric Fog Off**. A **Frame Limit of 60** keeps the GPU cool.

Measured on the RTX 3090 (Shipping build, 1080p, Ultra): 60–100 fps; packed train roof ≈ 60 fps.
`-GIShots=<list>` writes `perf.csv` (fps, p99, game/render/GPU ms) next to the screenshots for profiling.

## Credits

Textures & HDRIs: Poly Haven (CC0). 3D models: Sketchfab creators listed in-game (Credits page) and
in `~/gta-india/assets/sketchfab/CREDITS.txt`. Characters are community models; see licences there.
