# Worked materials: parts breakdown

Family `materials`. Written 20 November 2026 before any geometry, from `sheets/materials_stock.png`, the bench look
target `concept/bench_overview_fal.jpg` (alloy plates with flaking orange paint, the stoppered vial), `DESIGN.md`
stages 0, 3, 4, 5 and `CONTRACT.md` section A. Millimetres.

**No sheet exists for the side plates or the fused core.** The first materials prompt named them as parts of a pistol
grip and the image service refused it (`sheets/materials_overall_REFUSED.prompt.txt`, "violence"). It was not
reworded: the sheet that was made (`materials_stock.png`) shows only the stock that is not part of a weapon. The
plates and the core are modelled from `grip/INTERFACE.md` and `model-pistol`'s build, with no picture.

## Frames

- Blender, metres, Z up. Loose things lie as they lie on the bench, origin where they touch it, laid out in a row
  along X so one GLB holds them all.
- Everything that hangs on the gimbal (lead states, the damper loop) is modelled **in the gimbal cradle's own frame
  (the datum D of `grip/INTERFACE.md`: origin at the centre of the flange's outer face, +Z out of the cup) and
  exported with an identity transform at the GLB origin**: parent it to `servo_gimbal_cradle` at identity. The cradle
  stands on its bottom face there, so the bench is 20 mm below the flange face (z_D = -20).
- The raw core's flash and sprue are in the grip core's frame in the same way (parent `grip.core`).

## 1. Scrap Alloy (item `scrap_alloy`, two sheets)

Each sheet 120 x 90 x 2.0 (the interface's plates are 2.0 thick, so the sheets are; the brief said about 2.5), a panel offcut: Warden orange paint on one face (chipped, flaking to bare alloy, a
stencil fragment "7C", two old bolt holes), brushed bare metal on the other, one torn edge. Sheet A lies paint up,
sheet B bare side up (they are cut stacked, so the two plates come out as a mirrored pair).

| Part id (`materials.`) | What | Parent | Notes |
|---|---|---|---|
| `sheet_a` | What is left of sheet A after cutting: the largest offcut. Moves the whole sheet until it is cut. | - | item `scrap_alloy`; paths `scribe` and `cut` (the plate outline), `cut_strap` |
| `sheet_a_plate` | The left plate as cut and finished: the outline of `INTERFACE.md` section 4 (about 110 x 56) and its four holes. | `sheet_a` | marks `punch_1..4` = the interface's holes A, B (d 6.1), C, D (d 3.3) in that order; filed edge and drilled holes are the finished geometry |
| `sheet_a_margin` | The 0.6 mm sliver left outside the line by the snips. Hidden when filed. | `sheet_a_plate` | absent after s3.file |
| `sheet_a_plug_1..4` | The metal in each hole (1..4 = holes A, B, C, D). Hidden when drilled; carries the punch dimple in its normal map. | `sheet_a_plate` | absent after s3.drill |
| `sheet_a_strap` | The strap strip, flat, 17 wide and about 118 long (interface section 4), cut from the long edge. | `sheet_a` | marks `bend_1`, `bend_2` |
| `strap_bent` | The same strip after the two bends (shape from `INTERFACE.md`). Second state, same origin as the flat one. | `sheet_a` | absent at start |
| `sheet_a_offcut_1..2` | Small offcuts. They go in the press. | `sheet_a` | |
| `sheet_b`, `sheet_b_plate`, `sheet_b_margin`, `sheet_b_plug_1..4`, `sheet_b_strap` (the spare), `sheet_b_offcut_1..2` | Sheet B, the same breakdown; its plate is the right plate. | | |
| `sheet_a_scribe` | The scribed line as a bright 0.3 mm strip on the paint, for the game to reveal. | `sheet_a` | absent at start |
| `swarf_1..5` | Drill curls. | - | loose, absent at start |

## 2. Leads, resistor and the damper loop

Lead: 1.6 over insulation, 0.8 of stranded copper (interface section 2). The as-found leads in the servo are `servo.lead_*`; these are the
same leads once the gimbal is on the bench: they droop from the terminal tab to the bench and lie straight and
parallel. Arc length equals the servo's as-cut length (asserted, 2 mm).

| Part id | What | Notes |
|---|---|---|
| `lead_a`, `lead_b` | Coil lead from the tab to 8 mm short of the trim mark, insulated. | mark `trim`; state "as cut" is this plus its offcut, "trimmed" is this alone |
| `lead_a_offcut`, `lead_b_offcut` | From the trim mark to the as-cut end, with the marker band. | falls away at s3.trim |
| `lead_a_slug`, `lead_b_slug` | The last 8 mm of insulation. Slides off along the lead. | `__clear` 14 mm along the lead; s3.strip |
| `lead_a_strands`, `lead_b_strands` | 8 mm of twisted bare strands under the slug. | wipe `tin`: copper as stripped (loose PNGs), tinned bright in the GLB |
| `lead_sense` | The sense lead in the bench pose, whole. Cut off flush. | mark `flush`; s3.trim |
| `resistor` | The trim resistor as snipped from the board, lying on the bench: body with colour bands, two legs. | wipe `tin` on the legs |
| `sleeve_a`, `sleeve_b` | Heat-shrink sleeves before shrinking: 3.6 dia x 8, slid back on each lead (shrunk in the loop they are 2.9 dia x 7.0). | absent at start |
| `loop_lead_a`, `loop_lead_b`, `loop_resistor`, `loop_sleeve_a`, `loop_sleeve_b` | The finished damper loop as soldered on the bench: both leads curved round to the resistor, sleeves shrunk over the joints. | absent at start; marks `probe_a`, `probe_b` for the tester |
| `loop_tucked` | The same loop as it lies in the core's side channel: the interface's 14-point line in D at z_D = -1.7, resistor at (0, 21.8), sleeves at (+/-6.0, 21.8). One node. | absent at start; path `tuck` |

## 3. Nanites (item `nanite_residue`)

| Part id | What | Notes |
|---|---|---|
| `vial` | Glass vial 24 dia x 62 with a rolled lip, clear glass (its own material, one draw). | `__tip` at the lip, +Z out of the mouth; mark `level` |
| `vial_fluid` | Dull grey fluid, two thirds full, with a meniscus. Its own node so the level can fall. | |
| `vial_stopper` | Rubber stopper wired on with a twist of iron wire. | `__clear` 20 mm up |
| `vial_line` | The scratched level line: a thin opaque ring on the outside of the glass. | |

## 4. Copper Filament (item `copper_filament`)

| Part id | What | Notes |
|---|---|---|
| `bobbin` | Empty bobbin: wooden core 14 dia, two pressed-steel flanges 34 dia with a wire slot and a drive hole, 30 long. | stands on a flange |
| `bobbin_wire` | The wound copper, full. Its own node so it can grow. | absent at start |

## 5. The fused core as it leaves the press

| Part id | What | Notes |
|---|---|---|
| `core_raw` | The grip core straight out of the mould: the core's shape from `model-pistol` with an undersized pocket, a cast skin and heat tint. Swapped for `grip.core` once quenched and cleaned. | absent at start |
| `core_flash` | The thin ragged flash round the parting line. | parent `core_raw`; knocked off in s4.flash |
| `core_sprue` | The stubby sprue. | parent `core_raw` |

## From `grip/INTERFACE.md` (it exists since 15:41; ids above are unchanged by it)

Plate outline and holes: section 4. Strap: 17 x 2, developed length about 118, two bends. Loop: section 2. The core's
shape, its parting plane and pocket are not in the interface: `core_raw`, `core_flash` and `core_sprue` take them from
`grip/export` when `model-pistol` has built the core, and wait until then. Everything else is built without it.

## Budget

15,000 triangles. Planned: two sheets with plates, margins, plugs, straps and offcuts 4k; swarf 0.6k; leads, slugs,
strands, resistor, sleeves and loop 4k; vial 1.6k; bobbin and wire 2.4k; raw core, flash and sprue 2.4k. One 2048
set; the glass is a second, unbaked material.

## As built (20 November, `model-materials`): what differs from the tables above

No id above was renamed. `export/parts.json` is the authority; `README.md` has the reasons.

- **Frames.** `sheet_a_plate`, `sheet_b_plate` and `strap_bent` carry the node frames of `grip/interface.json`
  (SEAM.md section 9): seat them at `grip.core/seat_plate_l`, `seat_plate_r`, `seat_strap`. `sheet_a_strap`,
  `sheet_b_strap` and `strap_bent` share one node frame (the strip coincides with the bent strap along its back leg).
- **Extra part** `strap_bent_1`: the strip after the first (heel) bend. Absent at the start.
- **Absent at the start as well:** `lead_a`, `lead_b`, `lead_sense` with their pieces, and `resistor`.
- **Parents.** `lead_x_strands`, `lead_x_slug`, `lead_x_offcut`, `sleeve_x` are children of `lead_x`.
- **Wipes.** `tin` on `lead_x_strands` and `resistor`; `punch` on `sheet_a_plug_1..4` (the as-found set has no
  dimple). One as-found set for the family.
- **Marks and paths.** `probe_a`, `probe_b` are on `loop_resistor`; `tuck` is on `loop_tucked`; `bend_1`, `bend_2`
  on both flat straps; `punch_1..4` on both plates; `scribe`, `cut`, `cut_strap` on `sheet_a` only; `trim` on
  `lead_a`, `lead_b`; `flush` on `lead_sense`; `level` on `vial`; the helper `materials_vial__tip`.
- **Core.** `core_raw` and the charge are dropped (SEAM.md section 10). `core_flash`, `core_flash_2`, `core_flash_3`
  (path `file` on `core_flash`) and `core_sprue` (mark `snap`, a `__clear`) are in the frame of `grip.core`, parent
  `grip.core`, absent until the mould opens; the parting plane is P Y = 0.
- **Numbers.** Trim length 27.0 mm from the tab (19 insulated, 8 stripped). Bends at 45.3 mm (98 degrees) and
  102.2 mm (82 degrees) along the 118.2 mm strip, measured from the sheet's corner end. Sheets 120 x 90 x 2.0.
