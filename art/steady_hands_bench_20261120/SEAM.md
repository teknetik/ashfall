# The seam between the interaction system and the real models

Orchestrator's decision, 20 November 2026, 17:35, after `bench` handed back its slice on greybox parts and the first
real families exported (`pistol`, `servo`, `tools`, `fixtures`). It settles what `CONTRACT.md` section A left open.
`bench`, the three modelling agents and `integration` all follow it.

## 1. The art's names are the names

Each family's `export/parts.json` (and its `PARTS.md` before it is built) is the authority for part ids, mark ids,
path ids, zone ids and param ids. The step table (`data/steps.json`), the layout (`data/layout.json`) and the
greybox use the same names. `bench` renames its side; the modellers do not rename anything for the bench.

Known differences on 20 November (greybox name to real name):

| Greybox | Real |
|---|---|
| `pistol.bind_wire_1`, `_2`, mark `cut` | `pistol.bind_wire_a`, `_b`, mark `snip` |
| `pistol.latch` (part) | no part; the latch is the param `pistol.cell_latch` |
| `pistol.spring` | `pistol.housing_spring` |
| `pistol.status` (param) | part `pistol.status_lamp` (the bench drives its emission) |
| `fixtures.work_surface`, `fixtures.parts_mat` | `fixtures.worksurface`, `fixtures.partsmat` (and `fixtures.workmat`, the black rubber mat) |
| `fixtures.vise_jaw`, `fixtures.vise_handle`, param `fixtures.vise.jaw` | `fixtures.vise_slide`, `fixtures.vise_screw`, params `fixtures.vise_jaw`, `fixtures.vise_handle` |
| `fixtures.card_board` | `fixtures.board` (clips `fixtures.board_clip_a`, `_b`) |
| `tools.dropper` | `tools.oil_dropper` (stands in `tools.oil_bottle`) |
| `tools.roll.unroll` (param) | `tools.roll_unroll` (and `tools.roll_strap`) |
| `servo.case` | `servo.case_body` with `servo.case_lid` and 31 more parts |
| `materials.alloy_a`, `_b`, `materials.vial` | see `materials/PARTS.md` (`sheet_a`, `sheet_b`, ...) |
| `grip.assembly`, `grip.screw_a`, `_b` | see `grip/INTERFACE.md` and `grip/PARTS.md` when written; until the grip family exports, the bench keeps a one-part stand-in named `grip.assembly` |

Param ids have one dot (`<family>.<name>`), as the art writes them.

## 2. Where things rest: marks named `seat_*`

A place where a part of one family rests on a part of another is a mark on the owner, named `seat_<what>`:
`fixtures.vise/seat_work`, `fixtures.cradle/seat_frame`, `fixtures.partsmat/seat_pistol_scale_l`,
`fixtures.dish/slot_00..11`, `fixtures.pad/seat_cell`, `fixtures.board/seat_card_before`, `tools.roll/seat_pliers`,
`fixtures.workmat/seat_pistol`. The modellers already do this.

- A place in `data/layout.json` names its mark (`"mark": "fixtures.vise/seat_work"`). With real art the pose is the
  mark empty's pose; the numbers in `layout.json` are only the greybox fallback.
- What a place accepts, its tolerances, its approach and what holds a part there (`held_by`) are interaction data and
  stay in `layout.json`.
- **A seat mark is either a point or a full pose, and says which.** The kit's `mark(o, id, point, normal)` gives a
  point with +Z along the normal and no defined heading: the bench then takes the position from the mark and the
  resting part's orientation from `layout.json` (in the owner's space). Where the orientation matters and the modeller
  knows it (frame in the vise, frame on the cradle, cell on the pad, cards on the board, the grip on the mat), the
  mark is a full pose: **the resting part's node takes the mark's world transform**, and the mark's entry in
  `parts.json` carries `"pose": true`. `model-pistol` adds a kit helper for this (`contract.seat_pose(owner, id,
  matrix, accepts=[part ids])`); a modeller places another family's GLB to find the matrix, as for a check render.
  Missing `pose` means a point.
- If the bench needs a place the art does not have, `bench` adds it to `layout.json` without a mark and lists it in
  its README under "Places with no mark" so the modeller can add the empty.

## 3. Tools with bits

The screwdriver's bits are real parts (`tools.bit_slot`, `tools.bit_cross`, tags `bit:slot`, `bit:cross`). The bit
seated at `tools.screwdriver/seat_bit` is the screwdriver's mode; the other one sits in `tools.bitblock`. The quick
swap (Flip with the screwdriver in hand) stays: it exchanges the two bits with a short collar move
(`tools.screwdriver_bit` 0 to 1 to 0). A fastener's `fastener.bit` says which bit fits it.

## 4. What the art tells the bench, and what it does not

- From `parts.json` the bench takes: nodes, parents, `seat` (clear pose, symmetry, tolerances), `held_by`,
  `fastener` (bit, turns, what it holds), marks, paths, zones, wipes (dirty and clean texture sets), params and their
  `*_param` clips, `absent_at_start`, mass class, item id.
- `sequence` in a family's `parts.json` is the modeller's proof that the family comes apart in order. It is not the
  step table. The step table stays `data/steps.json`, written by `bench` from `DESIGN.md` section 7.
- Each part's `steps` list says which design steps touch it; `bench` uses it as a cross-check (`verify` reports a
  step that refers to a part whose `steps` does not list it, as a warning).

## 5. The schematic and the test cards

- The schematic sheet (`fixtures_schematic`, seven regions with tick overlays) is `model-bench`'s Milestone 3. Until
  it exists the bench keeps its greybox schematic at `fixtures.board/seat_schematic`.
- Test cards are `pistol.card_a`, `pistol.card_b` (marks `centre`, `clip`); they clip at
  `fixtures.board/seat_card_before` and `seat_card_after`.

## 6. Order of work

1. `bench`, Milestone 2: rename to the real names (section 1), bind places to marks (section 2), and write stages 2 to
   5 against `servo/export/parts.json`, `materials/PARTS.md`, `grip/INTERFACE.md`, `tools/PARTS.md` and
   `fixtures/PARTS.md`. The greybox generator makes stand-ins with the real ids for anything not exported yet.
2. Modellers: nothing to rename. Add an empty when `bench` lists a place with no mark.
3. `integration`: runs `AssemblyBenchInstall20261120 --steps prefab --real <families>` and fixes what `BindFamily`
   finds; no renaming pass should be needed by then.

## 7. Rulings after the servo hand-back (20 Nov, 18:05)

- **One gimbal.** The gimbal unit is modelled once, in the servo family: `servo.gimbal_cradle` is its root and the
  ring, race, rotor, retaining ring, coil and grit ride on it. The grip family does not draw a second one. On the
  bench the unit is lifted out of the servo and seated in the grip core at `grip.core/seat_gimbal` (a pose mark, in
  the cradle's frame, datum D of `grip/INTERFACE.md`); in Unity the same nodes are reparented. `model-pistol` imports
  the unit from `servo/export/servo.glb` for its sweep and its renders.
- **The unit as built** adds two things to the interface, material removed only: a 1.7 mm notch at +Y_D for the sense
  lead, and two half-round scallops (r 1.45) in the flange rim at +X_D and -X_D for the trunnion screws. The core's
  pocket must not rely on flange material there.
- **Trunnion screws** have no place in the grip: they go to the dish and leave with the by-products.
- **A param's rest is not always 0.** `parts.json` gives `rest` per param (`param_rest` for the family); the gimbal's
  two tilts rest at 0.5 with the stops at 0 and 1. The bench starts every param at its `rest`.
- **A family may have more than one rig.** `params[].node` names the rig object a param lives on (servo: `servo_rig`
  for the clips, `servo_gimbal_rig` on the cradle so the unit moves as one).
- **One as-found texture set per family**, on the family's own UVs (`<family>__dirty_color/normal/orm.png` beside the
  GLB), not one per part as CONTRACT A says. Each part's `wipes` lists the zones that reveal the clean set.

## 8. Shared colours (corrected 20 Nov 19:20)

**History, so nobody repeats it.** At 18:05 I set the Warden orange to linear (0.60, 0.20, 0.076), worked back from
the look target. At 19:05 I withdrew it because the servo repainted with it rendered pale salmon. That withdrawal was
the mistake: `model-materials` showed that the kit's review rigs were about 1.6 EV too bright (a white card read 3 in
scene-linear under the neutral rig and 4.5 under the warm one), which washes any bright albedo to pastel under AgX.
At a correct exposure the same value renders as the look target's orange (measured on `materials/review/hero.png`:
sRGB about 180, 105, 60, hue 22 degrees; the look target is 220, 118, 60, hue 22). **The value stands.** Every colour
judgement made on a render before the rig is fixed is void, including "the pistol's steel is pale" and "the servo is
coral".

**Rule for review renders.** A white diffuse card (albedo 0.8) in the picture must not clip: it reads about 0.9 in
scene-linear, about sRGB 235 after the view transform. `model-pistol` fixes `kit/review.py` to that (both rigs) and
puts a white and a mid-grey card in every review frame's corner. Until the fix lands, set
`scene.view_settings.exposure = -1.6` (neutral) or `-2.2` (warm) after `studio()` and say so on the sheet.

**Colour values are linear albedo.** The kit's `make()` takes sRGB triples and converts them itself; use the kit's
constants (`mats.WARDEN_ORANGE`, `mats.BARE_ALLOY`, `from_linear`) and never type a triple twice.

| Material | Albedo, linear RGB | Notes |
|---|---|---|
| Warden orange paint (servo case, alloy sheets, pistol butt plate, any Warden panel) | (0.60, 0.20, 0.076) | roughness 0.55 to 0.62; flakes off in **large irregular patches with a ragged coast**, 30 to 50 % bare on the alloy sheets (`materials/review/hero.png` is the reference for the character), far less on the servo can but in the same character: worn fields at ribs, edges, feet and where it was dragged, long scratches, clean fields between that still carry stains and grime. Not an even speckle, and no bare island in the middle of a panel |
| Bare alloy under the paint | (0.30, 0.285, 0.265), metallic 1 | old and oxidised, not polished: roughness 0.55 to 0.65, darker stains, brushed along the sheet's long edge. The first value (0.55, 0.53, 0.50) read as white paper under the lamp; the look target's bare metal is a dull dark grey-brown |
| Vise green | take from `fixtures` (model-bench says the value in its README) | |
| Press yellow | take from `fixtures` | |
## 9. The plates, the strap and the grip in the hand (ruling, 20 Nov 18:05)

Both `grip/PARTS.md` and `materials/PARTS.md` planned the side plates and the strap. They are modelled **once, in the
materials family**, because the player makes them from stock and must see the same piece, with the same paint, go
from the sheet onto the grip.

- `materials` owns the plates (`materials.sheet_a_plate` left, `materials.sheet_b_plate` right), the strap
  (`materials.sheet_a_strap` flat, `materials.strap_bent`), the damper loop and the leads, in every state.
- `grip` owns what is new when the grip exists: `grip.core` (finished), `grip.screw_a`, `grip.screw_b`, the seams
  (`grip.seam_l`, `grip.seam_r`), and the marks and paths on the core. It has **no** `plate_l`, `plate_r` or `strap`
  parts. The core carries pose marks `seat_plate_l`, `seat_plate_r`, `seat_strap`, `seat_gimbal` (each with its
  `clear` pose as a second pose mark `clear_plate_l`, ...), and the paths `loop` and `lead`.
- **Node frame of a plate** (so the two families agree without seeing each other's files): origin at the interface's
  grip-frame origin G projected onto the plate's inner (seat) face; +X = U, +Y = S of `grip/interface.json`; +Z out
  of the grip (away from the core). The same rule for the right plate, which is the mirror image as a shape. The
  bent strap's node frame is G itself. `materials` models the finished plate and bent strap at these frames (the
  node's transform then lays it on the sheet or the bench); `grip`'s seat marks are written for them.
- Each side checks by numbers when the other's export exists: seating the materials plate at the grip's mark puts
  every hole within 0.2 mm of its peg or screw hole, and the outline inside the recess with the interface's
  clearance. Until then each builds from `interface.json`.
- **The grip in the hand** is not a merged mesh from the modellers. `integration` builds the prefab the weapon shows
  for the mod (`grip_stabilised_pistol`) from the real bench parts in their seated poses (core, both plates, strap,
  screws; the gimbal inside is left out), so the grip in the hand is the one that was built. `grip_hand.glb` is not
  needed. `pistol_hand.glb` stays as it is; its `ScrapPistol_grip_stock` node is hidden when the grip is fitted.
- The raw core's flash and sprue (`materials.core_raw`, `core_flash`, `core_sprue`) stay in `materials`, in the
  core's frame, and wait for `grip/export/grip.glb`.

## 10. Rulings after the materials hand-back (20 Nov, 20:35)

- **No raw-core mesh.** The pressed core is `grip.core` itself from the moment the mould opens. What makes it raw is
  two small materials parts in the core's frame, `materials.core_flash` (the ragged fin along the parting line) and
  `materials.core_sprue` (the stub), which the player files and snaps off, plus the core's as-found texture set.
  `materials.core_raw` is dropped. The materials budget is 15k plus these two (about 700 triangles).
- **The charge belongs to the mould.** The heap of offcuts and grey paste in the cavity is `fixtures.mould_charge`, a
  sub-part of the tang mould (hidden at start), built by `model-bench` with the mould. `materials.charge` is dropped.
- **The tang mould is sized from the core**: `grip.core` is 93 x 39 x 115 mm; the 90 x 60 x 40 in `fixtures/PARTS.md`
  cannot hold it. The cavity is the core's outline plus flash clearance, parting line where `core_flash` sits.
- **As-found is the starting state of every wipe.** A part that lists `wipes` starts showing the family's as-found
  set in those zones; an action reveals the GLB's own set (brushing dust, tinning strands, punching a mark, curing a
  seam). So the alloy sheet's punch dimples are absent until `s3.punch`. `bench` initialises every wipe mask to
  as-found; `integration`'s shader reads it that way.
- `materials.strap_bent_1` (the strip after the first bend) stays: `s3.strap` shows it between the two bends.
- **The servo can's last surface pass is `model-materials`' job** (same paint, same hand as the alloy plates); it may
  edit `servo/**` for surfaces only, as `model-pistol-surface` does for the pistol.
