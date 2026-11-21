# Brief: `model-servo` — the Damaged Servo, everything inside it, and the worked materials

You model what the player salvages and processes: the servo that comes apart into the grip's damper, and the alloy,
leads and nanites in every state the job puts them through.

Read first: `../AGENT-RULES.md`, `../ANYMACHINE.md` (all), `../CONTRACT.md` section A (binding), `../DESIGN.md`
sections 1 to 4 and 7 (stages 0, 2, 3, 4, 5), `../FACTS.md` (items without models, the worker droid). Then AnyMachine
as reading only: `/home/teknetik/code/vendor/anymachine/PIPELINE.md` part 2, `hardsurface/NOTES.md`,
`hardsurface/rig2_blender/kit/README.md`, `laptop/NOTES.md`.

The kit is `art/steady_hands_bench_20261120/kit/`, published by `model-pistol` (look for `kit/READY.md`). Do your
sheets and `PARTS.md` first; if the kit is not ready when you need it, copy `pm_geo.py` and `pm_mats.py` from
`art/pistol_mods_20260930/src` into your folder, go on, and switch when it lands. Do not edit the kit.
The grip's interface (bearing pocket, gimbal outside diameter, plate screw size and positions, loop channel) is
`grip/INTERFACE.md`, written by `model-pistol`; your gimbal, rotor, loop and screws must fit it. If it is not there
yet, model the servo's outside and its other parts first.

## 1. The Damaged Servo (`servo/`)

A joint servo from a feral worker droid (the droids have heavy hydraulic forearms, exposed pistons and cable bundles;
take colour and wear from `U/Art/OuterBerms/Textures/WorkerDroid_*`). About 95 x 70 x 55 mm, heavy, dented, caked in
Berms dust, one corner scorched where the board burnt. It must read as the thing on the inventory icon
(`U/UI/Art/servo.png`) made real. Inventory item `droid_servo_damaged`.

Parts, at least (write `PARTS.md` first): case body and case lid with three spring clips and a seam, four brass
cross-head case screws (one chewed), output shaft and boss, burnt control board with its connector and a trim
resistor that is snipped off, three leads with bands (two coil, one sense), gear post with circlip and three stacked
gears (chewed teeth), stator with its copper winding, two trunnion screws, and the **gimbal assembly**: gimbal ring on
two trunnions, rotor (the swinging mass), damping coil, retaining ring. Rigs: `clip_1..3`, `gimbal_pitch`,
`gimbal_roll`, `rotor` (continuous). Dirty and clean sets for the case (dust) and the gimbal (corrosion on the race
and trunnions, grit in three detents), with zones and marks per `CONTRACT.md`. The order things come out in is
`DESIGN.md` stage 2; your assembly path sweep must prove it.

## 2. Worked materials (`materials/`)

Each as the finished pieces lying together as the uncut whole, with the cut lines as paths:

- **Scrap Alloy** (item `scrap_alloy`, two sheets, about 120 x 90 x 2.5 mm): salvaged panel offcuts with old Warden
  orange paint on one face, stencil fragments, bolt holes, a torn edge. Cut into: left plate, right plate, the strap
  strip (flat, and bent in two places as a second state), and offcuts (which go in the press). Scribed-line state,
  four punched and drilled holes per plate, filed edges, swarf curls.
- **Leads** in each state: as cut, trimmed, stripped with twisted strands, tinned; the **trim resistor**; the finished
  **damper loop** (two leads across the resistor, two shrunk sleeves); heat-shrink sleeves before shrinking.
- **Nanites** (item `nanite_residue`, tier one): a stoppered glass vial of grey fluid with a level line; the pour
  stream and the fluid level in the mould are Unity effects, give the vial a `__tip` at its lip.
- **Copper Filament** (item `copper_filament`): bobbin, empty and wound.
- The **fused grip core as it leaves the press**: hot, with flash and a sprue (the cleaned core is `model-pistol`'s;
  take its shape from `grip/INTERFACE.md`).

## Method and gate

Reference sheets first (`gen_concept.py`, OpenAI `gpt-image-2`; `FACTS.md` Tooling): overall, exploded and close-up
sheets for the servo, one sheet for the materials. Then `PARTS.md`, `build.py`, compare renders beside the sheets,
a planned second pass, the checks in `ANYMACHINE.md` section 3, bake, export, copy to `U/Art/Bench/Servo/` and
`U/Art/Bench/Materials/`. Budgets: servo 45k triangles, materials 15k; 2048 per family. Meshy allowance: 90 credits
(nothing here needs it unless a soft part does). No Unity runs.

## Report

Milestone 1: sheets and both `PARTS.md` (append to `PROGRESS.md`, keep going). Milestone 2: servo passing its checks
with compare renders. Milestone 3: materials. Final report: triangles and textures per family, `check.json` results,
the path of every review sheet, how the gimbal fits `INTERFACE.md` (measured), and one line per family on what still
differs from its sheets. Look at your renders before you report; say what you saw.
