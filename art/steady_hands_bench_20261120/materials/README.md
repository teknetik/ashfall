# Worked materials (family `materials`)

Built 20 November 2026 by `model-materials` (taking over from `model-servo`, who wrote `PARTS.md`) for the Steady
Hands bench programme. Method: `../ANYMACHINE.md`. Part ids are those of `PARTS.md`; none was renamed.

## Files

| File | What |
|---|---|
| `PARTS.md` | the breakdown (ids, states, marks, paths, wipes) |
| `build.py`, `mtl.py` | the build: `SH/blender.sh materials/build.py -- --nobake` (seconds), `-- --size 2048 --spp 16` to bake |
| `check.py` | the kit's checks plus this family's own (interface, unit, leads, rest, grip): writes `export/check.json` |
| `review.py` | staged review renders under the kit's neutral studio and a warm work lamp, sheets in `review/` |
| `run_all.sh` | build, check and review in one use of the shared Blender slot (`SH/run.sh TAG SH/slot.sh materials/run_all.sh ...`) |
| `src/stencil_7c.png`, `src/stencil_04b.png` | masks of the stencil fragments (ImageMagick, Liberation Mono Bold, SIL OFL) |
| `sheets/` | `materials_stock.png` and its prompt (made by `model-servo`); the refused prompt, kept as it was |
| `export/` | `materials.glb`, `materials.blend`, `parts.json`, `stats.json`, `check.json`, `tex/` |

## Provenance

Everything is original and procedural (this folder, `../kit`, layer helpers from `../servo/sv.py`). Corner easing of
the plate outline is `pistol/pgeom.py`'s `fillet`, the same function the grip core's recess is cut with. No Meshy
credits, no fal, Grok or OpenAI images were made by this agent; no third-party meshes or textures.

## What is in the GLB

- **Sheet A** (paint up) and **sheet B** (bare side up), 120 x 90 x 2.0, each as the pieces the snips leave, lying
  together as the uncut sheet with no gap: `sheet_x` (the largest offcut), `sheet_x_plate` with `sheet_x_margin` (the
  0.6 mm sliver) and `sheet_x_plug_1..4`, `sheet_x_strap`, `sheet_x_offcut_1..2`. `sheet_a_scribe`, `strap_bent`,
  `strap_bent_1` (extra, see Departures) and `swarf_1..5` are absent at the start.
- **In the cradle's frame D** (identity transforms, parent `servo.gimbal_cradle`; bench at z = -20 mm): `lead_a`,
  `lead_b` with their `_strands`, `_slug`, `_offcut` and `sleeve_a/b`, `lead_sense`, the loop as soldered
  (`loop_lead_a/b`, `loop_resistor`, `loop_sleeve_a/b`) and `loop_tucked`. All absent at the start.
- **Loose**: `resistor`, `vial` (+ `vial_fluid`, `vial_stopper`, `vial_line`), `bobbin` (+ `bobbin_wire`).
- **In the frame of `grip.core`** (identity transforms, parent `grip.core`, absent until the mould opens): the flash
  in three pieces, `core_flash` (it carries the path `file` round the whole parting line), `core_flash_2`,
  `core_flash_3`, and `core_sprue` (mark `snap`, `__clear` 18 mm out). The parting plane is the core's middle plane,
  P Y = 0; there is no fin across the tang slot's mouth. `core_raw` and `charge` are dropped (SEAM.md section 10).

## For the Unity side

- **Plates and strap are the grip's own** (SEAM.md section 9). `sheet_a_plate` is the left plate, `sheet_b_plate` the
  right; their node frames are `grip/interface.json` `plate.node_frames` (origin G on the inner face, +Y = S, +Z out
  of the grip, +X = -U left / +U right). Give the node the transform of `grip.core/seat_plate_l` or `_r` and it is
  seated. `strap_bent` has the grip frame G as node frame: seat it at `grip.core/seat_strap`.
- `sheet_a_strap`, `sheet_b_strap`, `strap_bent_1` and `strap_bent` share one node frame, so the states can be
  swapped in place: the strip coincides with the bent strap along its back leg (the first 36 mm from the sheet's
  corner), and each bend folds the rest toward the bare side. On the bench the bent strap rests on a long edge
  (rotate the node so its local Z is vertical). Marks `bend_1`, `bend_2` are on the flat strips.
- Plates, straps, the tucked loop and the bench leads have node origins away from their own bulk: each has a
  `__grab` empty at its middle.
- **The uncut sheet has no seams** because every piece of a sheet reads one pattern space (`sh_rest`, baked in) and
  the cut pieces carry no edge wear. The pieces tile with zero gap; `sheet_x_margin` wraps the plate's filed bevel,
  so the bevel shows only when the margin is hidden (`s3.file`), and the plugs fill the holes flush (`s3.drill`).
- **One as-found texture set** (`tex/materials__dirty_*.png`, same UVs): bare copper on `lead_x_strands`, dull legs
  on `resistor`, and unmarked paint on sheet A's plugs. The GLB's own set is the worked state: tinned, and punched
  (a centre-punch dimple on each plug of sheet A). Show the as-found set first and reveal the GLB's set inside each
  part's zone (strands, resistor) or over the whole plug.
- `materials_vial__tip` (lip, +Z out of the mouth) is a helper of the vial; `parts.json` lists a `tip` only for
  tools, so find it by name. The vial's glass is its own unbaked material `vial_glass` (alpha blend, one draw); the
  wire round the neck is in the atlas (so the vial node has two primitives).
- `vial_fluid` has its origin on the inside of the bottom: scale its Y (Unity) to let the level fall.
- `sheet_a` carries the paths `scribe` (the plate's outline, 40 points, closed), `cut` (0.6 mm outside it) and
  `cut_strap`. Sheet B has none: the sheets are cut stacked.

## Departures (from PARTS.md, the brief, the contract or the kit)

1. **Plates and strap are the grip's** (SEAM.md section 9, after PARTS.md): node frames from `grip/interface.json`.
   The right plate is the left plate's mesh mirrored vertex for vertex. In the GLB `strap_bent` and `strap_bent_1`
   share the flat strip's node frame, so their legs hang below z = 0 there (they are absent at the start).
2. **`strap_bent_1`** is an extra part, not in PARTS.md: the strip after the heel bend only, so the first of the two
   bends of `s3.strap` has something to show. Drop it if it is not wanted (it is 0.4k triangles).
3. **Absent at the start, beyond PARTS.md's list:** the bench leads (`lead_a`, `lead_b`, `lead_sense` and their
   pieces) and the loose `resistor`. They are the servo's own leads and resistor once those are out of the servo;
   shown from the start they would double `servo.lead_coil_*` and `servo.trim_resistor`.
4. **Hierarchy of a lead.** `lead_x_strands`, `lead_x_slug`, `lead_x_offcut` and `sleeve_x` are children of `lead_x`
   (which is the child of `servo.gimbal_cradle`), not of the cradle directly. All transforms are identity either way.
5. **The leads do not lie on the bench as PARTS.md says.** Lead A is 36 mm as cut and stands off the flange in an
   arc, ending 3 to 4 mm above the bench; lead B (61 mm) and the sense lead (37 mm) reach it. Trim length is 27.0 mm
   from the tab (19 insulated, 8 stripped): that is what the interface's loop needs; PARTS.md gave no number. The
   stripped length is straight, so the slug slides off (swept by the check).
6. **The loop as soldered** is the tucked loop with everything past the flange rim hanging 22 degrees down; lengths are
   those of the interface line. `probe_a`, `probe_b` are on `loop_resistor` at the body's two ends: the interface's
   sleeves cover both joints up to the body, so there is no bare metal between them for a probe.
7. **Punch marks** use the wipe mechanism (`wipes: punch` on sheet A's four plugs): PARTS.md asked for the dimple in
   the plug's normal map, and a dimple in the only set would show before the punch.
8. **Sheet B has no paths and no scribed line**; the two sheets are cut stacked along sheet A's.
9. **The vial's neck wire stays on the vial**; the bail over the stopper belongs to `vial_stopper` and lifts off
   with it (a ring under the rolled lip cannot come off as a rigid part).
10. **`item` on `bobbin`** (`copper_filament`): the wound bobbin is the item; `bobbin_wire` is its growing part.
11. **Kit work-rounds, in this folder only.** (a) `mtl.tri_safe`: the kit triangulates n-gons with BEAUTY, which
    left a flipped sliver in a plate face; plates and offcuts are ear-clipped before `Family.finish()`. (b) The
    bevel is unclamped on the plates: clamped, it shrank to nothing round the whole outline because one edge between
    two eased corners is 0.3 mm long (the grip family's former plates had the same). (c) `servo/` and `pistol/` have
    their own `check.py`, `review.py` and `measure.py`: with those folders ahead of `kit/` on `sys.path`,
    `import check` ran another family's script. The kit goes first here and `check.py` / `review.py` load the kit's
    modules by path. (d) `review.py` renders the kit's neutral rig at -1.6 EV and uses its own warm lamp (2.4 W at
    0.47 m, white = 0.9): at EV 0 both kit rigs put a white diffuse at 3 to 4.5, and anything brighter than about
    0.25 albedo burns out (`review/exposure_ab.png`).
12. **Colours.** Warden orange and bare alloy are read from `kit/mats.py` (`WARDEN_ORANGE`, `BARE_ALLOY`) at build
    time; `stats.json` `notes.colours` records what a build used. Wire and resistor colours are the servo's.

## Budget and textures (the baked export of 20 November, 20:03)

13,692 triangles of 15,000, 52 parts, 144 helper empties, two materials (`M_materials`, `vial_glass`), GLB 10.6 MB.

| Where | Triangles |
|---|---|
| The two plates (the eased outline, four holes, a real 0.3 mm filed bevel on both rims) | 2,456 |
| Margins and plugs (they wrap the plates' bevels so the uncut sheet is flat) | 1,282 |
| Remainders, offcuts and flat straps of both sheets | 1,296 |
| Bent strap and the strip after the first bend | 856 |
| Scribed line, five swarf curls | 524 |
| Leads, strands, slugs, offcuts, unshrunk sleeves, sense lead | 1,916 |
| Loop as soldered (five nodes) | 1,200 |
| Loop tucked (one node) | 928 |
| Resistor | 304 |
| Vial (glass 720, wire, residue, stopper and bail, level line) | 1,744 |
| Bobbin and its copper | 1,186 |

One 2048 set, baked at 16 samples in 280 s (atlas 43 % filled), and the as-found set on the same UVs for seven
parts. Texel density: plates and bent strap 70 px/cm, leads and loop 44 to 48, small things 37, the rest of the
sheets and the flat straps 33, the strip after the first bend 22, the wound copper 30.

**The raw core does not fit the budget.** `grip.core` is 5,458 triangles (pocket, T-slot, channels, pegs, strap bed).
A raw core that keeps its pocket and slot needs about 2,000, with flash, sprue and the poured charge about 2,500:
16.2k for the family against 15k. The 15k was written when the plates and the strap (3.3k with their bent state)
were still the grip family's; the grip is now at 8.2k of its 25k. This needs a ruling (see the hand-back): raise this
family's budget by about 1.5k, or accept a 900-triangle raw core whose pocket is a rough dent.

## Review sheets (`review/`)

`sheets.png` (as found, neutral and warm; scribed line), `states.png` (cut with the pieces apart; filed, drilled and
bent), `hero.png` (the two plates and the strap in its three states at 0.3 m), `leads.png` (as cut, stripped, tinned,
loop soldered, loop tucked, with the servo's unit), `small.png` (vial, bobbin empty and wound, resistor, swarf), each
also as `glb_*.png` from the exported, baked GLB. "Neutral" is the kit's rig as re-lit at 19:46 (EV 0); "warm" is
this family's own lamp (2.4 W area light, 0.47 m above and behind the work, 3000 K, white = 0.9). The source sheets
of 19:50 were rendered while the kit's rig was being changed: their neutral tiles are at -1.6 EV on the old rig.
`exposure_ab.png` is the old rig at EV 0 against -1.6 EV (historical).

Against `sheets/materials_stock.png` and the look target, seen in those renders:

- The sheets match the look target's plates in character (large ragged flakes, orange on dull metal). They are
  cleaner than the stock sheet's: no dents, no bent corner, and the torn corner is a wavy cut, not ripped metal.
- The stencil reads "7" with a broken "C"; on the stock sheet it is larger and whole.
- The stock sheet's strap has two holes and a rounded U bend; ours is the interface's plain strip with two tight
  bends (98 and 82 degrees).
- Leads are a redder, cleaner insulation than the stock sheet's dusty maroon; the strands are a plain 6-sided core
  with the twist only in the normal map (it bakes as a dotted glint at 48 px/cm).
- The vial: under the warm lamp the residue is a dark grey with a visible level line; under bright neutral light it
  turns pale silver (it is 0.85 metallic). The settled darker layer at the bottom does not show through the glass.
  The stock sheet's wire is a proper twisted tie; ours is a two-turn ring, a short pigtail and a bail.
- The bobbin's turns are in the normal map only; the flanges are plain pressed discs with one slot and one hole.
- Swarf curls are thin two-sided ribbons, bright; fine at the bench camera, flat when seen at 5 cm.

`compare_stock_hero.png`, `compare_stock_leads.png` (the stock sheet beside the baked GLB) and `compare_target.png`
(the look target's plates and vial beside the baked plates and small parts under the warm lamp) are tiled from
those renders.

## State on 20 November, 20:27 (Milestone 2)

Baked at 2048, `export/check.json` passes on the baked export (the kit's contract, sequence and GLB re-import; this
family's interface, cover, unit, leads and rest blocks; the grip's marks, advisory), copied to
`unity/AthenHill/Assets/AthenHill/Art/Bench/Materials/` (`materials.glb`, `materials.parts.json`,
`tex/materials__dirty_{color,normal,orm}.png`). Not in it: `core_raw`, `core_flash`, `core_sprue`, `charge`.

Seen in `compare_target.png`: the look target's plates are a deeper, redder orange with fewer and darker bare
patches, a brown tinge in the metal and dark burnt edges, and they look about 3 mm thick; ours are a lighter orange
on a mid grey (the shared values), 2.0 thick (the interface), with clean filed edges.

## Flash and sprue (added 20 November, about 21:00, after SEAM.md section 10)

`core_flash`, `core_flash_2`, `core_flash_3` (426 triangles) and `core_sprue` (120) are built from
`grip/export/grip.blend` (the core generated 20:26): the fin follows the core's outline on its middle plane P Y = 0
(the grip family names no parting line; the tang mould's parting line should be this plane), 0.5 mm thick at the
root, 0.5 to 3.5 mm ragged, missing across the tang slot's mouth. The sprue is a necked stub under the middle of the
base. If the core's outline changes, rebuild this family (seconds) and re-bake. The sections above describe the
export before these four parts; triangles are now 14,238 of 15,700.
