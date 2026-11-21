# Tools family: parts breakdown

`model-bench`, Steady Hands bench programme, 20 November 2026. Written before any geometry, from the reference sheets
in `sheets/` and the look target `../concept/bench_overview_fal.jpg`. The bench frame, the layout and the departures
shared with the fixtures are in `../fixtures/PARTS.md`; positions are in `../fixtures/layout/layout.json`.

## Frame, nodes, rigs

- Bench frame (Blender metres, Z up, origin on the worktop under the bench pivot, +X the player's right, -Y toward
  the player). `tools.glb` holds every tool at its place on the bench.
- One root node per tool, `tools_<name>`. A tool's own frame: origin where it touches what it lies on, local +Z up at
  rest, its long axis along local +Y with the working end at +Y. The rest tilt of a tool lying on a fat handle is in
  the mesh, so the node's rotation is a yaw only.
- A tool with a mechanism is a small rig of its own, `tools_<name>_rig`, parented to the tool's root mesh node, so the
  tool is one sub-tree. Its moving sub-parts are bone-parented meshes `tools_<name>_<sub>`. Parameters and bones are
  named `<name>_<param>` and clips `<name>_<param>_param` (1 s, linear in the parameter).
- **Parameter 0 is always the as-found pose** (the kit's rule: the modelled pose is 0). Hand-tool jaws are found
  closed, so `jaws` runs 0 = closed to 1 = open; the vise is found open, so its `jaw` runs 0 = open to 1 = closed.
- Every tool has `tools_<name>__tip` (local +Z out of the tool along the working direction) and `tools_<name>__grab`.
- Field Toolkit tools are exported **seated in their pockets on the unrolled roll**, with a sibling `__clear` empty
  (drawn 95 mm out of the pocket and 15 mm up). Each pocket also has `tools_roll__mark_seat_<tool>` on the roll's
  segment bone, so a tool parented to that mark rides the roll as it rolls up.
- Brann's tools lie at their rest places on the bench top; their slot is their rest transform.

## Look

Ward's tools are old, repaired and looked after. From the look target: re-taped in pale cloth tape gone grey-brown
with oil, steel dark with oxide and worn bright on jaws, tips, edges and where a thumb sits, wooden handles dark
and polished by hands, small owners' marks scratched in (three file nicks on Brann's, a punched triangle on the
player's). No uniform grunge and no cyan anywhere except the applicator's sight window.

## Field Toolkit (item `field_toolkit`, the player's)

| Node | Size (mm) | Parts and materials | Rig / empties | Slice |
|---|---|---|---|---|
| `tools_roll` | unrolled 560 x 300, rolled dia 85 x 300 | waxed olive-tan canvas 1.6 thick, oil-dark along folds; pocket layer with nine stitched pockets on the lower 135 mm, each bulged to its tool; top flap 110 deep; bound edges; a sewn patch on one corner; leather strap 25 x 380 with a steel roller buckle, riveted to the outer end | **skinned** on `tools_roll_rig`: 40 segment bones, 80 flap bones (two rows per segment), 15 strap bones. `roll_unroll` 0 = rolled bundle at the left end of the footprint, 0.8 = flat, 1 = flap folded open. `roll_strap` (added) 0 = buckled round the bundle, 0.6 = laid straight, 1 = swung to lie beside the roll, pointing away from the player. `__mark_seat_<tool>` on the segment bones, `__grab` on the bundle | yes |
| `tools_screwdriver` | 190 long, handle dia 28 | turned hardwood handle with two scribed rings, brass ferrule, steel shaft dia 6, **knurled locking collar** dia 11 x 18 with a 6.35 mm hex socket | rig: `screwdriver_bit` 0 = locked, 1 = collar drawn back 4 mm. `__mark_seat_bit`, `__tip` at the end of a seated bit | yes |
| `tools_bit_slot`, `tools_bit_cross` | 45 long, 6.35 hex | hex shank with a retaining groove, slotted 5 mm blade, cross point | part of the screwdriver's set; `__clear`, `__tip`. Slot bit seated in the driver, cross bit in the bit block | yes |
| `tools_bitblock` | 30 x 16 x 24 | hardwood block with two hex holes, in the narrow pocket | `__mark_seat_bit_a`, `__mark_seat_bit_b` | yes |
| `tools_pliers` | 165 long | combination pliers: serrated flat jaws, pipe grip, side cutter notch, dome pivot rivet, handles wrapped in pale cloth tape | rig: `pliers_jaws`, the second half turns about the pivot on a round lap joint (0 = closed, 1 = open 34 deg); nodes `tools_pliers` and `tools_pliers_b`; `__tip` between the jaw tips | yes |
| `tools_cutters` | 140 long | diagonal cutters: bevelled blades, lap joint with a rivet, dipped red rubber handles worn through to steel | rig: `cutters_jaws` (0 = closed, 1 = open 30 deg); nodes `tools_cutters` and `tools_cutters_b`; `__tip` at the middle of the blades | yes |
| `tools_punch` | 120 long, body 8 across flats | octagonal tool steel, 3 mm straight pin 26 long, a knurled band, mushroomed struck end | no rig; `__tip` at the pin end, `__mark_strike` on the head | yes |
| `tools_strippers` | 150 long | flat scissor-type strippers with a row of V notches, return spring, adjusting screw with a locknut | rig: `jaws` | M3 |
| `tools_wirebrush` | 200 long | curved wooden handle, three rows of brass bristle tufts (tufts as real clumps, fine bristle in the bake) | `__tip` on the bristle face, `__zone_face` | M3 |
| `tools_pick` | 150 long | slim knurled steel handle, hooked tip | `__tip` | M3 |
| `tools_scribe` | 150 long | knurled body, hardened needle point, pocket clip | `__tip` | M3 |

Pockets, left to right as the player sees the unrolled roll: screwdriver, bit block, pliers, cutters, strippers,
wire brush, pick, punch, scribe. The roll is mirrored from its sheet (strap and outer end on the left), so that the
bundle starts at the bench's left end and unrolls toward the work, and the unbuckled strap swings clear of the vise.

## Brann's bench tools (fixed to the station)

| Node | Size (mm) | Parts and materials | Rig / empties | Slice |
|---|---|---|---|---|
| `tools_mallet` | 280 long, head dia 38 x 80 | steel head barrel with two bands, one brass face, one rawhide face; hickory handle with a wedge, pale tape wrap on the grip | `__tip` on the brass face, `__grab` on the tape | yes |
| `tools_oil_dropper` in `tools_oil_bottle` | bottle dia 32 x 62, overall 100 | amber glass bottle (glass material), black rubber bulb, screw collar, glass pipette with oil in it | rig: `dropper_bulb` 0 = full, 1 = squeezed (the bulb's bone scales). Dropper seated in the bottle, `__clear` lifted 70 mm. `__tip` at the pipette's end, pointing down | yes |
| `tools_file_flat` | 250 blade, 345 overall | double-cut flat file, tang, brass ferrule, turned handle | `__tip`, `__zone_face` | M3 |
| `tools_file_round` | 220 blade, 310 overall | rat-tail file, handle | `__tip` | M3 |
| `tools_snips` | 250 long | straight tinner's snips, forged handles, pivot bolt and nut | rig: `jaws` | M3 |
| `tools_drill` | 300 long | eggbeater drill: wooden head handle and side knob, cast frame, spoked crank wheel dia 90 with real teeth, pinion, spindle, three-jaw chuck; `tools_drill_bit` 3 mm twist bit | rig: `crank` continuous (wheel, and the spindle at the gear ratio), `chuck` 0 = open, 1 = gripping | M3 |
| `tools_iron` on `tools_iron_stand`, `tools_solder_reel` | iron 220 | cork grip, copper tip, the cloth lead coiled and tied at the handle; bent-wire spring stand on a steel base; reel of solder with a free end | iron seated in the stand, `__clear`; `__tip` | M3 |
| `tools_thirdhand` | base dia 80, 120 tall | cast base, post, cross bar, two ball-jointed arms with crocodile clips | static; `__mark_seat_lead_l`, `__mark_seat_lead_r` | M3 |
| `tools_applicator` | 150 long | alloy barrel, ceramic nib, glass sight window with grey paste, thumb slider | `__tip` | M3 |
| `tools_rag` | 160 x 100 folded | oil-stained cotton | `__grab`, `__zone_face` | M3 |

## Triangles and textures (plan)

Budget 60k, 2k to 6k each. Toolkit: roll 6k, screwdriver 2.6k, bits 0.9k, block 0.3k, pliers 3.6k, cutters 3k,
punch 0.8k, strippers 3.5k, brush 3k, pick 1.2k, scribe 1.5k: about 26k. Brann's: mallet 2k, dropper and bottle 2k,
files 3k, snips 2.5k, drill 6k, iron, stand and reel 5k, third hand 4k, applicator 1.5k, rag 1.5k: about 28k.

Two 2048 sets: **T1** the Field Toolkit (roll and the nine tools), **T2** Brann's tools. The slice bakes what exists;
both sets are re-packed and re-baked when Milestone 3 adds the rest. Glass (oil bottle, pipette, applicator window)
uses the small shared glass material.

## Departures

- `strap` on the roll is added: `DESIGN.md` step `s0.roll` unties before it unrolls, and one `unroll` cannot show
  both.
- The roll is a skinned mesh (cloth cannot be rigid parts); everything else is rigid and bone-parented.
- The dropper's `bulb` is a bone scale, not a rigid motion.
- The roll is mirrored from its sheet (above).
- The third hand is listed with the tools here because the brief lists it there; it stands on the work surface.

## Model-tools, 21 Nov 2026

Built as above, with these changes: the tape on the pliers and the mallet is black cloth friction tape (the sheet; the
brief), not pale; the eleven M3 tools are built (README, "The eleven new tools"); the rag is not built (not in the
brief). Triangle budget 80k (orchestrator, 21 Nov). Texture sets a (carried tools) 4096, r (roll) 4096, b (bench-standing
things) 2048.
