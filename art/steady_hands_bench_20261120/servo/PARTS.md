# Damaged Servo: parts breakdown

Family `servo`, inventory item `droid_servo_damaged`. Written 20 November 2026 before any geometry, from
`sheets/servo_turn.png` (overall), `sheets/servo_exploded.png`, `sheets/servo_close1.png`, the inventory icon
(`UI/Art/servo.png`), `DESIGN.md` stage 2 and `CONTRACT.md` section A. Numbers are millimetres; the build asserts the
ones marked **fixed**.

## What it is

A joint servo torn out of a feral worker droid: a stubby orange motor can with cast-steel end bells, a pinion on the
output shaft at the front and torn leads at the back, as on the icon. The upper half of the can is a lid. Inside, a
ring stator lies flat in the body and the **gimbal** (the stabilising element Ossa means by "its gimbal is still
true": a deep cup with the gimbal inside it) sits in the stator's bore; a worm on the output shaft turns a three-gear stack; a control board lies over
everything and has burnt at its rear end.

## Axes, origin, size

- Blender, metres, Z up. X is the long axis; the output shaft and pinion point to **-X** (the kit's "front"). Y is
  the width. The servo lies on its mounting foot: **origin on the bench under the middle of the 95 mm length**.
- Overall **95 x 70 x 55** (fixed, error under 0.5): x -47.5..47.5, y -35..35 (across the four screw lugs),
  z 0..55. The torn outside leads hang about 25 mm beyond +X and are not counted.
- Can axis at y 0, z 29. Can outside radius 26, wall 2. Seam between body and lid at z 31.
- Along X: pinion -47.5..-38.5, boss to -29.5, front end bell to -22.5, can and interior -22.5..38.5, rear end bell
  to 44.5, grommet to 47.5.

## How it goes together (and which way everything comes off)

Everything inside lifts out **straight up (+Z)** through the opening the lid leaves (61 x 48). The lid is a half
shell on two flanges; four brass screws go down through its corner lugs into bosses on the body; three sprung strap
clips hinged under the body's flange hook over the lid's flange. The internal deck is at z 16.

| # | Part id (`servo.`) | What it is, material | Held by | Comes off | Step |
|---|---|---|---|---|---|
| 1 | `case_body` | Lower half can, both end bells, foot, flanges, four screw bosses, deck, gear post, shaft pedestal, idler post and pinion, board shelves, clip hinge pins, grommet and three torn outside leads (red, blue, yellow). Cast alloy painted orange, steel end bells. Dented. | - | never | s2.swap, s2.dust |
| 2 | `case_lid` | Upper half shell with flanges, four lugs, three ribs, riveted data plate; rear +Y corner scorched and blistered. Moulded cover (contact class plastic: the design's creak). | 4 case screws, 3 clips | +Z | s2.pry |
| 3-5 | `clip_1..3` | Spring-steel strap clips, 7 wide, hinged on a pin under the body flange, hooked over the lid flange, thumb tail below. Two on +Y (x -2, 19), one on -Y (x 8). | hinge pin | do not come off; rig `clip_1..3` springs them 40 degrees outward | s2.pry |
| 6-9 | `screw_case_a..d` | Brass M3 x 10 pan head, cross recess; `d` has a chewed, rounded recess. Reused as the grip's plate screws. | thread in body boss | +Z, 10 turns | s2.screws, s2.stripped (d), s5.start, s5.torque |
| 10 | `output_shaft` | Steel shaft on the can axis with the outside pinion (14 teeth, chewed), a worm inside, running in the front bell and a deck pedestal. | bearings | never | - |
| 11 | `board` | Control board 58 x 26 x 1.6 on two shelves with locating pins: 3-pin header (front), chip, capacitors, feedback pot and pinion under it, rear end charred with a bite out of the corner. | lid pressing on it, 2 pins | +Z | s2.board |
| 12 | `trim_resistor` | Axial resistor on the board, body 6.5 x 2.4, legs to two pads. Snipped at two marks; kept for the damper loop. | soldered legs (cut) | +Z after the two snips | s2.board, s3.tin, s3.loop |
| 13 | `lead_plug` | Black 3-way plug on the board's header with the three lead ends up to their marker bands. Origin at the bands, so it tilts off like a lead bending there. | header friction | tilts up 35 degrees about the bands, then away with the offcuts | s2.board (unplug), s2.leads (snipped off) |
| 14-15 | `lead_coil_a`, `lead_coil_b` | Coil leads, 1.6 over dark red insulation, pale marker band at the board end, soldered to the cradle's terminal tab. Ride with the gimbal. | solder at the tab | with the gimbal | s2.leads, s3.trim, s3.strip, s3.tin, s3.loop |
| 16 | `lead_sense` | Sense lead, bone insulation, yellow band, from the pickup pod on the cradle. | solder at the pod | with the gimbal; cut off flush in s3.trim | s2.leads, s3.trim |
| 18 | `circlip` | E-clip in the post's groove. | spring in the groove | sideways (+Y) 4 mm, then away | s2.circlip |
| 19 | `gear_top` | Small brass gear, 12 teeth, chewed; meshes the board's pot pinion. | circlip | +Z | s2.gears |
| 20 | `gear_mid` | Large dark steel gear, 28 teeth, a run of teeth stripped; meshes the idler pinion. | gear above | +Z | s2.gears |
| 21 | `gear_low` | Small brass worm wheel, 14 teeth; meshes the worm. | gear above | +Z | s2.gears |
| 22-23 | `screw_trunnion_a`, `_b` | Blued steel M2.5 x 10, wide cheese head, cross recess. One beside each trunnion: the shank passes a scallop in the flange rim and threads into a block on the stator, the head clamps the flange. | thread | +Z | s2.trunnion |
| 24 | `stator` | Laminated ring, 36.6 outside, 31 bore, 6 high, lying flat round the gimbal well on two cast blocks that carry the trunnion screws. Stays. | pressed in | never | s2.winding |
| 25 | `stator_winding` | The copper on the stator (toroidal turns in two sectors). Its own node so it can thin out as the bobbin fills. | wound on | unwound (mark at the wire end) | s2.winding |
| 26 | `gimbal_cradle` | Turned alloy cup to `grip/INTERFACE.md`: flange d 30 x 2 at the mouth, press-fit body d 26 down to the shoulder 20 below the flange face, key lug, two lead notches, a small sense notch with the pickup in it, two screw scallops, two trunnion studs in brass bushes pointing in, the coil's two tails fixed up the wall. Root of the unit; its node frame is the interface's datum D. | 2 trunnion screws | +Z with everything in it | s2.trunnion, s3.*, s4.flash, s4.pressfit |
| 27 | `gimbal_coil` | Ring coil of enamelled copper on the cup floor: the damping coil. | potted in the cup | never (child of cradle) | s3.test |
| 28 | `gimbal_ring` | Steel gimbal ring turning on the cradle's two trunnion studs. Rig `gimbal_pitch` (about X_D). | trunnion studs | never (rides the rig) | s3.brush, s3.oil |
| 29 | `gimbal_race` | Inner bearing race on two pins in the ring, three detent notches on its top land. Rig `gimbal_roll` (about Y_D). | pins | never (rides the rig) | s3.brush, s3.pick |
| 30 | `gimbal_rotor` | Heavy brass flywheel on a steel spindle with a hanging bob that swings inside the coil. Rig `rotor` (continuous, about Z_D). | retaining ring | +Z_D out of the race | s3.spin, s5.rotor |
| 31 | `gimbal_retainer` | Spring retaining ring in the race's bore above the flywheel. | spring in its groove | +Z_D | s5.rotor |
| 32-34 | `gimbal_grit_1..3` | Grit lumps in the three detents. | stuck | flicked out (hidden by the game) | s3.pick |

Ids, parents and the `held_by` lists go into `parts.json` from the build, not from this table.

## Removal order the path sweep must prove (DESIGN.md stage 2)

1. `screw_case_a..d` back out along +Z (any order).
2. `clip_1..3` to 1 (rig), then `case_lid` lifts +Z. With any clip at 0 the lid must be blocked.
3. `lead_plug` tilts off the header; `board` lifts +Z carrying `trim_resistor` and the pot.
4. `lead_plug` leaves (the three snips at the bands).
5. `circlip` slides off sideways; `gear_top`, `gear_mid`, `gear_low` lift +Z in that order (a lower gear lifted first
   must be blocked by the one above).
6. `screw_trunnion_a`, `_b` back out; `gimbal_cradle` lifts +Z with ring, race, rotor, retainer, coil, grit and the
   three leads.
7. `stator_winding` is unwound in place (no path).

Later, on the bench: `gimbal_retainer` and `gimbal_rotor` lift out of the race along the cradle's +Z and go back
(s5.rotor).

## Rigs

| Rig object | Parameter | Type | Axis and range |
|---|---|---|---|
| `servo_rig` (on the body) | `clip_1`, `clip_2`, `clip_3` | hinge | about X through each hinge pin, 0 closed to 40 degrees open |
| `servo_gimbal_rig` (on the cradle, so the unit moves as one) | `gimbal_pitch` | hinge | about X_D through the trunnion studs, -12..12 degrees, **0.5 = level = the as-found and modelled pose** |
| | `gimbal_roll` | hinge, child of pitch | about Y_D through the race's pins, -12..12 degrees, 0.5 = level |
| | `rotor` | continuous, child of roll | about the spindle (Z_D when level) |

## Surfaces that are cleaned, marks and zones

- Dust (wipe `dust`): `case_body`, `case_lid`, the clips and the case screw heads share the as-found set; zones
  `case_lid__zone_dust`, `case_body__zone_dust_l`, `_r`, `_front`, `_rear`.
- Corrosion (wipe `corrosion`): `gimbal_race`, `gimbal_ring`, the trunnion studs of `gimbal_cradle`; zones
  `gimbal_race__zone_race`, `gimbal_cradle__zone_trunnion_a`, `_b`.
- Marks: `case_body__mark_pry_1..3` (at each clip tail), `board__mark_snip_r1`, `_r2` (resistor legs),
  `lead_coil_a__mark_snip`, `lead_coil_b__mark_snip`, `lead_sense__mark_snip` (at the bands),
  `gimbal_cradle__mark_oil_a`, `_b` (trunnions), `gimbal_race__mark_detent_1..3`, `stator_winding__mark_end`,
  `gimbal_cradle__mark_probe_a`, `_b` (the two lead joints in the notches, for the tester).

## Where the sheets disagree, and which wins

- The overall sheet and the icon show a round can; the exploded sheet draws the open body as a square tub. The
  **outside is the round can**; the inside takes the exploded sheet's flat deck, flat stator and posts.
- The exploded sheet stacks the gears small-on-top; the close-up shows a second shaft with a pinion. A pyramid stack
  cannot lift past fixed mesh partners, so the stack is small, large, small: the worm drives the low gear, a fixed
  idler pinion meshes the large middle gear, and the top gear's partner is the pot pinion that leaves with the
  board. The mechanism wins over the picture.
- The sheets put the lid's screws on the lid's curved top; here they are on corner lugs of the seam flange, which is
  what makes the 70 mm width.
- Outside leads: the sheets draw them dark red and black; the bench look target
  (`concept/bench_overview_fal.jpg`) has red, blue and yellow. The look target wins for the outside leads.
- The gimbal on the sheets stands proud of its cup, with ears and a screw in each. `grip/INTERFACE.md` wants a plain
  d 30 flange with everything inside the cup and nothing above the flange face (the grip's plate closes over it).
  The interface wins: the gimbal sits inside the cup, and the two trunnion screws clamp the flange rim from outside
  it instead of passing through ears.

## Fit to `grip/INTERFACE.md` (measured by `check.py`, block `interface` in `check.json`)

Cradle node origin and axes are the datum D (centre of the flange's outer face, +Z out of the pocket). In the servo D
sits at (17.0, 0, 30.4) turned 180 degrees about Z, so both lead notches open to the -Y side. Flange d 30.0, z -2..0;
body d 26.0 to z -20.0; key lug 4.0 wide to r 14.5 at -Y_D; lead notches 3.0 wide at +/-50 degrees from +Y_D, cut
to r 11.0 and 2.7 deep so a 1.6 lead on the loop's line (z -1.7) lies in them. Ring, race, rotor, retaining ring,
coil and grit stay inside r 11.0 and z -19.0..-0.3 at all nine combinations of the two stops and level.
Added to the interface's unit, none of it outside its envelope: a 1.7 wide notch at +Y_D for the sense lead (cut off
flush before the unit goes in the grip) and two half-round scallops, r 1.45, in the flange rim at +/-X_D for the
trunnion screws. Open question for the orchestrator, unchanged: `model-pistol`'s brief lists "gimbal cradle" as a
grip part; it is modelled here, once, as `servo.gimbal_cradle`.

## Budget

45,000 triangles for the family. Planned: body 9k, lid 3k, clips 0.8k, screws 1.7k, shaft 1.5k, board, resistor and
plug 3.3k, leads 1.5k, post, circlip and gears 5k, stator and winding 5k, gimbal unit 7.5k (built: see `export/stats.json`). One 2048 set, with the
gimbal's islands scaled up to hold 60 px/cm and hidden inside faces scaled down.
