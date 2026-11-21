# Stabilised Pistol Grip: parts breakdown

`model-pistol`, 20 November 2026; rewritten at 18:40 after `SEAM.md` sections 7 and 9. The grip the player builds at
the bench (`DESIGN.md` section 3). What other families must fit is in [INTERFACE.md](INTERFACE.md); this file is what
`grip.glb` holds.

## What this family is, and is not

`grip` owns what is **new when the grip exists**: the finished core, the two brass grip screws, the two seams, and the
marks and paths on the core. Five nodes.

| Not here | Where it is | How it meets the core |
|---|---|---|
| Gimbal damper unit (cradle, ring, race, rotor, retaining ring, coil, grit) | `servo.gimbal_cradle` and its riders | pose marks `seat_gimbal` / `clear_gimbal` (datum D) |
| Four plate screws | `servo.screw_case_a` .. `_d` | pose marks `seat_plate_screw_lc`, `_ld`, `_rc`, `_rd` / `clear_plate_screw_*` |
| Left and right side plates | `materials.sheet_a_plate`, `materials.sheet_b_plate` | pose marks `seat_plate_l`, `seat_plate_r` / `clear_plate_l`, `clear_plate_r` |
| Strap, bent | `materials.strap_bent` | pose marks `seat_strap` / `clear_strap` |
| Damper loop, tucked | `materials.loop_tucked` | path `loop` |
| Raw core, flash, sprue | `materials.core_raw`, `core_flash`, `core_sprue` | modelled in this core's frame from `export/grip.glb` |
| Trigger lead and its keyed plug, housing pin | `pistol.lead`, `pistol.lead_plug`, `pistol.housing_pin` | path `lead`; the plug and the pin go back in with the grip on |
| The grip in the hand | `integration` builds it from the seated bench parts | no `grip_hand.glb` |

`build.py` also makes the two plates and the strap from `interface.json` as **stand-ins**, registered under their
`materials` ids. They are in `export/grip.blend` for the sweeps and the review renders. They are not in `grip.glb`,
not baked and not in `parts.json`.

## Frame and seat

`grip.glb` is in the pistol's metric frame P (metres; origin and axes of `ScrapPistol.glb`), like `pistol.glb`. So:

- the grip's **seat on the pistol** is the rest pose of `grip_core` itself (place the grip family root on the pistol
  family root); `grip_core__clear` is the pose slid 75 mm down off the tang (−S);
- the whole family is `absent_at_start`: nothing of it exists when the job begins.

The grip frame G (S up the grip axis, U toward the front strap) and the unit datum D are defined in `INTERFACE.md`.

## Parts (`grip_…`)

| Part | Made from (bench step) | Made of | Held by | Goes on |
|---|---|---|---|---|
| `core` | alloy offcuts and 5 nanites, fused in the press (s4), flash knocked off, pocket eased | fused alloy: dark sintered skin, bright where a tool has been | on the pistol: the T-slot on the tang, the housing pin, the two grip screws | up the tang from below (+S), s6.slide |
| `screw_a`, `screw_b` | Brann's jar (s6.screws) | brass, M4 × 34, pan head, **cross** drive | through the left plate and the hollow peg, the core, the tang; thread in the core's right wall | from the left (−Y), 7 turns |
| `seam_l`, `seam_r` | nanite residue, traced and cured (s5.seam, s5.cure) | a fillet bead where each plate's edge meets the core | (a bead, not carried; `flex`) | shown as it is traced along path `seam_l` / `seam_r`; the as-found texture set is the uncured grey paste |

## The core, feature by feature

A flat-sided slab on the old grip's side outline: side faces at Y ∓17.5, corner radius 2.0, back and front on the
old grip's line. **The plates stand proud on the flat side faces** (2.0 thick, outer face Y ∓19.55); there is no
recess (the first plan had one: on the old rounded section its walls came to nothing at the edges, and a slab thick
enough to wall the plates in left lands 0.4 mm wide).

| Feature | Where (G, mm) | For |
|---|---|---|
| Seat faces | Y −17.5 (left; also z = 0 of datum D) and Y +17.5 | the plates; a land of 1.7 to 3.9 mm shows round each plate at the front, base and back |
| T-slot, open at the top | web U −13 .. +5, head U −19 .. −13, from S −6.4 up; 0.15 clear | the tang; widened in front (U to 6.75) for the bus strip, and down to S −6.4 for the socket block under the tang's end |
| Pegs at A and B | d 5.9 × 1.8 on both seat faces; the left pair is bored d 4.3 | locate the plates; the grip screws pass through the left pair |
| Pocket | at D: counterbore d 30.2 × 2.1, bore d 26.1 × 20.1, keyway at −Y_D | the gimbal damper unit, pressed to the flush line. Full circle: it does not rely on the unit's flange where the servo family notched it |
| Loop channel and resistor bay, two spring clips | left face, in front of the pocket | the damper loop (path `loop`) |
| Holes C and D | d 3.2 × 8.7, both seat faces | the four plate screws |
| Pin hole | d 3.2 at (U −16, S 37), in the bite of the plates (S 32 .. 42) | the housing pin, driven with the plates on |
| Lead channel | open groove in the back, Y +2.5 .. +5.5, from the top down to the window | the trigger lead (path `lead`) |
| Plug window | through the back wall at S −6.2 .. +1.0, 7.5 wide | the keyed plug goes straight in to the bus socket (+U) |
| Strap bed | 17.3 wide, 2.15 deep, down the back from S −7.5, round the heel, along the base, up the toe to S −30 | the strap, flush with the core |
| Lightening pockets | three, cast in, under the right plate (6, 6 and 4 deep), a rib between the lower two | what a moulded part has; seen on the bench before the right plate goes on |
| Ejector witness marks | six discs d 4.8, 0.2 deep, three a side | the same |

## As found: the core fresh from the mould (`SEAM.md` section 10)

There is no raw-core mesh. `grip.core` is the pressed core from the moment the mould opens; what makes it raw is the
materials family's `core_flash` and `core_sprue`, which stand on it, and this family's as-found texture set
(`tex/grip__dirty_*.png`, the whole atlas): a dull grey skin under release powder, the pocket and the holes as cast,
and a dark witness line where the mould parts.

- **The mould parts on the grip's mid-plane, Y = 0.** A band 1.6 mm wide round the outside of the core there is its
  own surface: filed bright in the clean set (where the flash was knocked off), the dark witness line as found. Path
  `parting` (up to 40 points on the surface: front strap, toe, base, heel, back strap; not across the top, where the
  T-slot opens, nor across the plug window) is the line for the flash and the file.
- **Three wipes on the core**, each a box wiped across its thin side:

| Wipe | Zone | Reveals | Step |
|---|---|---|---|
| `skin` | the whole core (65 x 119 x 43) | the fused alloy under the powder | quench and brush, s4.open |
| `flash` | the slab round the parting plane (5 thick) | the filed strip | s4.flash |
| `pocket` | a box round the pocket (33 x 33 x 22) | the bore eased bright | s4.flash |

The zones overlap. A texel should show the clean set only when **every** zone that holds it has been wiped, so the
pocket and the parting line stay as cast until `s4.flash` even if the skin is cleaned first.

The two spring clips in the loop channel are part of the core mesh and are there in both sets.

## Marks and paths on `grip_core`

Pose marks (`"pose": true`; the incoming node takes the mark's world transform), each seat with its clear pose:
`seat_gimbal`, `seat_plate_l`, `seat_plate_r`, `seat_strap`, `seat_plate_screw_lc`, `_ld`, `_rc`, `_rd`, and
`clear_…` for each. Point mark `pocket_shoulder`. Paths: `loop` (14), `lead` (14), `parting` (up to 40), `seam_l`, `seam_r` (40 each; the
seam runs down the plate's front edge, along the base, up the back and round the bite; along the top the plate's edge
is the core's own edge and there is nothing to trace).

## Sequence proved by `check.py`

Loaded with it: the stripped pistol (as its own sequence leaves it), the servo family's gimbal unit and four case
screws, and the stand-in plates and strap.

1. the bare core up the tang (a fit check, not a bench step);
2. on the bench (the pistol is not in the way): the gimbal unit into the pocket (s4.pressfit), the strap up the spine
   (s5.strap), both plates onto their pegs (s5.plates), the four case screws (s5.torque), the seams;
3. the assembled grip off the tang and on again (s6.slide as the player does it);
4. the pistol's plug back into its socket through the window (s6.plug), the housing pin (s6.pin), the two grip screws
   (s6.screws).

## Budget

25,000 triangles, one 2048 atlas.
