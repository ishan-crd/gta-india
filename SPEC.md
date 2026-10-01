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

## World layout (UE cm) — matches the clip's cross-section
- River Ganga flows along X. Water surface Z = 0. Water from Y = -15000 to 0 (150 m), bed Z = -600.
- NEAR BANK (village side, Y > 0), everything on top at Z = 1200:
  - Ghat steps Y = 0 .. 4000 (X = -50000 .. 50000) rising from Z = -300 to +1200; bathers, washers,
    buffaloes in the shallows, garbage piled at the waterline.
  - Sandstone parapet with small domed kiosks at Y = 4150; busy littered strip Y = 4300 .. 5600.
  - Railway at Y = 5900 (rail top Z ~ 1215): the packed EMU (cab + 9 coaches) runs right along the ghats.
  - Dusty road Y = 7000 .. 7800 with autos/bikes; tin-shed stalls at Y = 7950; poles + wires at Y = 8250.
  - Village: three rows of low 1-2 storey houses (facades at Y = 8700, 11400, 14100) with galis behind,
    big shade trees, garbage heaps, then fields to Y ~ 30000.
- FAR BANK (old city, Y < -15000), X = -40000 .. 40000: ghat steps Y = -15000 .. -19000 rising to
  Z = 1200, riverfront houses / palaces facing the river at Y ~ -19500, a second row and temples behind.
  Named ghats there: Dashashwamedh (X = 0, the drop-off), Manikarnika, Darbhanga, Scindia, Assi.
- Driving along +X: village on the left, train and river on the right (as in the clip).

## Mission "Ganga Paar Delivery" (Hinglish)
1. Pick up the order at Sharma Bhojnalaya (village, by the road).
2. Ride the bike along the dusty road beside the train (or jump on the train roof).
3. Reach the ghats, cross the Ganga (swim; HP drains in water).
4. Deliver at Dashashwamedh Ghat on the far bank. Reward ₹ + time bonus.

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
