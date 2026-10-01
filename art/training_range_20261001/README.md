# Warden training range — 1 October 2026

Carl: "the training robot section could use work." The Wardens' range in the Outer Berms (beyond the West Gate:
three Meshy steel knockdown plates in front of a bare mound, a firing bench and the range control, where the Berms
tutorial teaches recruits to shoot before they meet the machines on the service road) becomes a working, well-used
Warden range where recruits drill against steel plates and machines. Lore: the Wardens (lore.md) — a standing
militia that has fought rogue industrial droids and machine swarms at the outer berms for centuries; nothing new is
invented about them. Unity pass: `unity/AthenHill/Assets/AthenHill/Editor/TrainingRangePass.cs` (survey, build,
toggle, batch) and `TrainingRangeInstall.cs` (install, earth bank, retire, decals, lights, cameras, verify, capture).
Evidence: `unity/evidence/training-range/20261001/`.

## What is built (scene root `Outer Berms/Warden training range`)

| Group | Content |
| --- | --- |
| Firing point | Three timber bays at the tutorial's firing line (`checkpoint_firingline` is bay 1): bay dividers (plywood screens, foot sandbags, ear defenders on a hook), shooting benches with sandbag rests and a charge-cell case, lane boards 1–3, spent nano cells and brass on the ground, a painted firing line, a galvanised spent-cell bin, a waiting bench with a water can |
| Range officer | Trestle table (range log, radio, megaphone, binoculars), folding stool, nano-cell crates, water can; RANGE ORDERS board (original text) facing the path from the gate; a red range flag and a red "range live" lamp at the right end of the line; a timber flood pole |
| Distance posts | 5 / 10 / 15 M posts down the left edge, outside every line of fire |
| Backstop | A timber revetment (sleepers between buried posts, a level top, two courses of sandbags, shot-through sleepers behind each plate, lane numbers painted on the timber) in front of an earth bank built on the real ground (rises 3.15 m, buries the old mound), red flag on the crest, impact-scar decals where the tutorial's line of fire meets the wall, spare sleepers, spade, sand cart, sledgehammer, sacks |
| Machine lane (4) | Start frame with a MACHINE LANE 4 board, an agility run of tyres laid flat, two timber cover barricades, a steel tether gantry with a training drone hung from it, a stripped worker droid in a steel target frame with a painted hit ring |
| Service apron | Blast wall between the lane and the apron, a shade shelter over three drone charge docks (two training drones docked), repair bench (vice, test meter, toolbox, rag), welding cart, compressor, generator with cable runs to the docks and the bench, fuel can, tool trolley, caged work lamp, oil stains |
| Night lighting | Range flood (plates), range flood (machine lane), shelter work lamp, range officer's lamp — on the Ward light clock (practical + night only); the red range-live lamp burns day and night |
| Retired (inactive) | The old firing bench and its sandbags, the range flag that stood in front of the line, the floating unlit "PLATE 0n" TextMesh numbers on the plates, loose rocks/boulders/shrubs on the range floor (small stones stay where no shot passes and nothing is built) |

Gameplay objects are never moved: the three plates (health, collision, knock-down, tutorial callbacks), the range
reset station, the briefing board, Ossa and Rell, the arms locker, encounters, respawn and landmarks.

## Run order

`$O` is the programme wrapper folder `/home/teknetik/.local/state/ward-programme` (capped Unity/Blender/player/heavy
wrappers). `run/` holds this pass's capture scripts (native AFTER set, A/B toggle, tutorial check).

1. `layout.py` (plain Python: `uv run --with numpy --with matplotlib python layout.py --plot`) → `layout.json`,
   `review/layout-map.png`. Validates every collider-bearing piece against existing colliders, gameplay markers
   (landmarks, NPCs, interactables, spawns), the tutorial's lines of fire from the bays and the camera position to
   each plate's aim point, plate fall zones, the revetment line and the gate-to-firing-line walk. Ground from
   `survey.json` (`TrainingRangePass` survey step).
2. `$O/heavy.sh uv run --with pillow --with numpy python make_textures.py` (timber, sand, signs, numbers, decals).
3. `$O/blender.sh prepare_ph_props.py` (Poly Haven props, LOD0–2) then `prepare_prop_textures.py` (mask maps).
4. `$O/blender.sh author_range.py [-- TR_Name ...]` (Blender-authored kit → `Art/TrainingRange/Structures/*.glb`,
   `authored-assets.json`). Review: `review_kit.py`, `review_backstop.py`.
5. Unity (one step per run; `-nographics` for everything except captures):
   `$O/unity.sh <log> AthenHill.Editor.TrainingRangePass.RunBatch --steps build -nographics` (textures, materials,
   prefabs incl. the training drone and the baked worker-droid shell), then `--steps install -nographics`,
   `--steps verify -nographics`, and editor captures in batches of at most six cameras:
   `--steps capture:<dir>:cam_range_line+cam_range_bays+...` (graphics). Native evidence: `run/after.sh <tag>`,
   A/B: `run/ab2.sh` + `run/ab_city.sh`, tutorial: `run/tutorial.sh <out>`.

## Sources and licences

- Poly Haven (CC0): models bench_vice_01, Megaphone_01, retro_multimeter, old_military_compressor,
  portable_welding_cart, caged_hanging_light, rusted_spade_01, sledgehammer_01 (`polyhaven/manifest.json`, authors
  recorded); textures rough_wood (timber) and, from `art/west_gate_20260926/polyhaven`, dense_sand, plywood,
  metal_plate_02, rusty_painted_metal.
- Fonts (OFL, not redistributed; rasterised into the sign maps): Stardos Stencil, Allerta Stencil, Barlow Condensed
  from `art/west_gate_20260926/fonts`.
- Reused project assets: West Gate kit materials and prefabs (range flag, clipboard, radio, binoculars), street
  dressing prefabs (crates, jerrycans, tyres, stool, bench, bin, generator, tool cart, toolbox, rag, handcart, sacks),
  the accepted Meshy scrap drone and worker droid (`meshy/checkpoint-robots-20260926`, `art/outer_berms_20260926`) as
  static training pieces (no AI), the Berms Ground material for the earth bank, the weathering decal shader.
- Everything else is original Blender/Python authoring in this folder. No Meshy credits were used by this pass.
