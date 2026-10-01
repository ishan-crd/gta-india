# GTA India — Varanasi slice (UE 5.8.3, C++)

Reference: AI video "GTA 6 India edition" — delivery guy (yellow shirt, yellow food box on back),
dusty road next to an overcrowded train, train roof, ghats of Varanasi at golden hour, swimming across
the murky Ganga (HP drains), climbing out on the far bank's steps. HUD: mission box top-left,
health bar + ₹ money top-right, circular minimap bottom-left.

## Machines
- Mac (this repo) = source of truth for code/scripts. Synced to the Linux PC with `tools/sync.sh`.
- Linux PC (`ssh linux`, user ishan): engine at ~/UnrealEngine (5.8.3 source build),
  project at ~/gta-india/GTAIndia, raw assets at ~/gta-india/assets, logs at ~/gta-india/logs.

## Units / axes
UE: centimetres, Z up. Blender kit is authored in METRES, Z up, +X forward, exported to FBX so that
1 Blender m = 100 UE cm. Mesh origins at bottom-centre unless noted in the kit manifest.

## World layout (UE cm)
- River Ganga flows along X. Water surface Z = 0. River spans Y = -15000 .. 0 (150 m wide), bed Z = -600.
- WEST BANK (city, Y > 0), X = -40000 .. 40000:
  - Ghat steps Y = 0 .. 4000 rising from Z = -300 (underwater) to Z = +1200. Steps ~30 cm rise, ~60 cm
    tread, landings every ~10 steps. Named ghats: Dashashwamedh (X=0), Manikarnika (X=-25000),
    Assi (X=+30000). Chhatri umbrellas, small shrines, boats tied at the water line.
  - Riverfront buildings Y = 4000 .. 9000 on top of the ghats (Z = 1200): 3–7 storey palaces, houses,
    temples; narrow stair-gullies between them down to the ghats.
  - Railway embankment along X at Y = 10500, rail top at Z = 1500. Dusty road at Y = 12500, Z = 1200.
  - Town blocks Y = 14000 .. 30000 with lanes.
- EAST BANK (Y < -15000): wide sand bank Z ~ 0..150, Ramnagar-style fort ghat around X = 0
  (steps Y = -15000 .. -19000 rising to Z = 1000, sandstone fort wall behind). Delivery drop-off there.

## Mission "Ganga Paar Delivery" (Hinglish)
1. Pick up the order at Sharma Bhojnalaya (town, near the road).
2. Ride the bike along the dusty road beside the train (or jump on the train roof).
3. Reach Dashashwamedh Ghat, cross the Ganga (swim; HP drains in water).
4. Deliver at Ramnagar Ghat on the far bank. Reward ₹ + time bonus.

## Materials (slot names used by all kit meshes; built in UE from Poly Haven 2k sets)
| Slot | Poly Haven set |
|---|---|
| M_Sandstone | large_sandstone_blocks |
| M_SandstoneRed | red_sandstone_wall |
| M_SandstoneSteps | sandstone_blocks_05 |
| M_SandstoneOld | old_sandstone_02 |
| M_Pavement | red_sandstone_pavement |
| M_PlasterYellow | yellow_plaster |
| M_PlasterOchre | yellow_plaster_02 |
| M_PlasterRed | red_plaster_weathered |
| M_PlasterBlue | blue_plaster_weathered |
| M_PlasterPeeling | peeling_painted_wall |
| M_PlasterMossy | worn_mossy_plasterwall |
| M_PlasterDamaged | damaged_plaster |
| M_PlasterWhite | white_plaster_rough_01 |
| M_PlasterPainted | painted_plaster_wall |
| M_PlasterWorn | worn_plaster_wall |
| M_ClayPlaster | patterned_clay_plaster |
| M_BrickPlaster | red_brick_plaster_patch_02 |
| M_BrickWhite | whitewashed_brick |
| M_Mud | brown_mud |
| M_MudDry | brown_mud_dry |
| M_Dirt | dirt |
| M_DryGround | dry_ground_01 |
| M_Trail | rocky_trail |
| M_Riverbed | mud_cracked_dry_riverbed_002 |
| M_RiverPebbles | ganges_river_pebbles |
| M_RoadDamaged | road_damaged |
| M_Asphalt | worn_asphalt |
| M_CorrugatedRust | rusty_corrugated_iron |
| M_Shutter | rusty_metal_shutter |
| M_WoodShutter | wood_shutter |
| M_WoodPlanks | weathered_planks |
| M_RoofTiles | clay_roof_tiles |
| M_Cloth | crepe_satin (tintable) |
| M_MetalRust | rusty_metal_02 |
| M_Concrete | concrete_floor_worn_001 |
| M_Thatch | reed_roof_04 |
| M_Ballast | gravel_floor_02 |
| M_Steel | rusty_metal |

Solid colour slots: M_WindowDark (near-black interior), M_Saffron (temple paint/flags), M_Gold (metal
kalash), M_Whitewash (plain off-white paint).

UV rule: world-scale UVs, 1 UV unit = 2 m (cube projection is fine) so tiling matches everywhere.

## Kit output
- `~/gta-india/assets/kit/<Name>.fbx`
- `~/gta-india/assets/kit/previews/<Name>.png`
- `~/gta-india/assets/kit/kit_manifest.json` — `[{name, file, bounds_m:[x,y,z], pivot, category, notes}]`
