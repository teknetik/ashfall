# Stabilised Pistol Grip: the interface the servo parts must fit

Written by `model-pistol`, 20 November 2026, for `model-servo` (and for whoever builds the bench steps). **Nominal
values, held.** If one has to move, the change goes in `../PROGRESS.md` first. Revised twice (16:05, 16:15), the plate
outline only: its top edge moved up to where the existing grip panel ends (the plate is about 110 long), hole A moved
from S +25 to S +40, and a square bite was added in the rear edge for the housing pin. Nothing else changed, and the
outline is now final. The same numbers are in
[`interface.json`](interface.json) for a build script to read. Millimetres unless said.

## What the grip is

A fused alloy **core** that is the whole grip between two flat **side plates**. The core slides up onto the pistol's
short, cracked **tang** (a T-section dovetail), the housing pin and two brass grip screws lock it there, and an
orange **strap** runs down the back, round the heel and under the base. The servo's **gimbal damper unit** is pressed
into a pocket in the core's left side and the left plate closes over it; the **damper loop** lies in a channel beside
the pocket. From `model-servo` the grip needs four things: the unit, the loop, the four case screws, and (in the
materials family) the plates and strap as cut pieces.

## Frames

| Frame | What |
|---|---|
| **P** | Pistol metric frame: metres, muzzle −X, up +Z, the player's right +Y, origin = the origin of `ScrapPistol.glb`. `pistol.glb` and `grip.glb` are both in P, so the two family roots placed together are the fitted pistol. |
| **G** | Grip frame, for describing things: origin P (0.080, 0, −0.030); **+S** = P (−0.42038, 0, 0.90736), up the grip axis; **+U** = P (−0.90736, 0, −0.42038), toward the front strap; +Y as P. The grip runs about S −52 .. +59, U −31 .. +30, Y ±19.6. |
| **D** | Datum of the damper unit, and the origin of your cradle node: the **centre of the flange's outer face**. +Z_D out of the pocket (the pistol's left, P −Y), +X_D = +S (up the grip), +Y_D = +U (toward the front strap). Seated, D sits at G (U 0, S −26, Y −17.5) = P (0.090930, −0.017500, −0.053591). |

## 1. The gimbal damper unit (cradle, gimbal ring, rotor, coil)

Model it in D. Everything below is the unit at nominal; the pocket in the core is 0.05 mm bigger all round.

```
            +Y_D (front strap)
              ^        lead notches at +50 and -50 degrees from +Y_D
         . - -|- - .
       /   o  |  o   \        flange  d 30.0, from z = -2.0 to z = 0.0 (z = 0 ends flush with the core's left face)
      |       +------|-> +X_D (up the grip)
       \             /        body    d 26.0, from z = -20.0 to z = -2.0 (the bottom, z = -20.0, is the shoulder)
         ' - -[]- - '
              key lug at 180 degrees (-Y_D): 4.0 wide, out to r 14.5, z = -20.0 .. -2.0
```

| Feature | Value |
|---|---|
| Flange | d 30.0, 2.0 thick, outer face at z_D = 0 |
| Body (the press fit) | d 26.0, z_D −20.0 .. −2.0 |
| Key lug | at −Y_D, 4.0 wide, out to r 14.5, full body length. It fixes the turn: symmetry 1. This is the lug that cracks if the cradle is pressed past flush |
| Lead notches in the flange | two, at ±50° from +Y_D (toward ±X_D), 3.0 wide, cut in from the rim to r 11.0. The coil leads leave the unit here |
| Moving parts | gimbal ring, rotor, coil and the rotor's retaining ring stay inside r ≤ 11.0 and z_D −19.0 .. −0.3 at every value of every parameter. The left plate's inner face is at z_D = +0.05 |
| Axes (suggested, yours to decide) | `gimbal_pitch` about X_D ±12°, `gimbal_roll` about Y_D ±12°, `rotor` about Z_D continuous |

In `grip.glb` the unit's seat is two pose marks on the core: **`grip_core__mark_seat_gimbal`** (the pose of D when the
unit is home) and **`grip_core__mark_clear_gimbal`** (D lifted 40 mm along +Z_D). The grip family carries no rig and
no gimbal: the unit is `servo.gimbal_cradle` with what rides on it (SEAM.md section 7). As built it has two additions
that only remove material (a sense-lead notch at +Y_D, two trunnion-screw scallops at ±X_D in the flange rim); the
pocket does not rely on flange material there.

## 2. The damper loop (coil lead, trim resistor, coil lead)

It leaves the unit through the +50° notch, runs round a U-shaped channel in the core's left face in front of the
pocket, and returns through the −50° notch. Centreline in D, all at z_D = −1.7:

```
(8.4, 7.1) (11.6, 9.7) (13.4, 14.0) (13.4, 18.0) (11.4, 20.8) (8.0, 21.8) (4.0, 21.8)
(-4.0, 21.8) (-8.0, 21.8) (-11.4, 20.8) (-13.4, 18.0) (-13.4, 14.0) (-11.6, 9.7) (-8.4, 7.1)
```

About 55.5 long between the notch ends. Lead: sleeve d 1.6 over a d 0.8 core. Trim resistor: body d 2.4 × 6.5,
centred at (0, 21.8) with its axis along X_D, legs d 0.6. Heat-shrink sleeves d 2.9 × 7.0 over the two joints,
centred at (±6.0, 21.8). The channel is 3.2 wide and 3.3 deep, the resistor bay 9.0 × 4.4. Two spring clips (mine,
fixed to the core) hold the leads at (±13.4, 14.0). The same line is in `grip.glb` as `grip_core__path_loop_00` ..
`_13`. If you model the loop as a part in its seated shape, model it on this line in D.

## 3. The four case screws, reused as plate screws

| | |
|---|---|
| Thread | d 3.0, 10.0 long under the head |
| Head | pan, d 5.6 × 2.2 high, **cross** drive (one is chewed: `s2.stripped`) |
| Use in the grip | two per plate, through a d 3.3 hole in the plate into the core (8.5 of thread) |
| Seats | **C** at G (U +22, S −2) and **D** at G (U −22, S −44); left plate heads at Y −19.55 facing P −Y, right plate heads at Y +19.55 facing P +Y |
| Seats in P (m) | left C (0.060879, −0.01955, −0.041063), left D (0.118459, −0.01955, −0.060675); right: Y +0.01955 |
| Empties in `grip.glb` | pose marks on the core: `grip_core__mark_seat_plate_screw_lc`, `_ld`, `_rc`, `_rd` (+Z out of the hole) and `clear_plate_screw_*` |

So the servo case must be one that four M3 × 10 pan-head cross screws hold shut.

## 4. The plates and the strap (materials family: the cut pieces)

Both plates are scribed round an **old grip scale** of the pistol (`pistol_scale_l`), so the scale, the scribed line
and the plate share one outline. Flat sheet, 2.0 thick. Outline in G as (U, S):

```
(27.4, 39.7) (28.2, 27.0) (26.5, 10.0) (26.0, -10.0) (25.0, -30.0) (24.2, -41.0) (21.5, -44.6) (-22.5, -50.8)
(-26.6, -47.5) (-27.8, -30.0) (-27.8, -6.0) (-26.0, 8.0) (-23.0, 21.0) (-24.2, 32.0) (-12.5, 32.0) (-12.5, 42.0)
(-20.0, 42.0) (-18.5, 44.5) (-18.0, 56.5) (-5.5, 54.7) (11.4, 58.7) (19.4, 50.9)
```

The square bite in the rear edge (U −24.2 .. −12.5, S 32 .. 42) is on purpose: it leaves the housing pin's ear
uncovered, so the pin can be driven with the plates on. Corners eased to r 2.

Four holes, punched through the scale's four holes: **A** (U −4, S +40) d 6.1 and **B** (U −4, S +8) d 6.1 (they drop
over the core's two locating pegs, and the grip screws pass through them later), **C** (U +22, S −2) d 3.3 and
**D** (U −22, S −44) d 3.3 (the plate screws). The right plate is the mirror image. Old Warden orange paint is on the
outer face, bare alloy inside. Seated, the left plate lies between Y −19.55 (outer) and −17.55.

Strap: a strip 17.0 wide and 2.0 thick, orange outward, bent twice. **Developed length 118** (confirmed 18:25 on the
built path: inner face 115.1, neutral axis 118.2; the 112 in my Milestone 2 report was a wrong estimate). It goes on
from below, so both legs are parallel to the grip axis: back leg 36.5 (inner face at U −28.4, S −7.5 .. −44), heel
bend about 98°, base 47.7 (2.0 above the base line S = −55.1 + 0.1354 (U + 27.4)), toe bend about 82°, toe lip 15.9
up the front (inner face at U +27.8, to S −30). The inner-face path is in `interface.json` (`strap.inner_face_path_G_us`).

### Node frames of the plates and the strap (SEAM.md section 9)

| Part | Origin (P, m) | +X | +Y | +Z |
|---|---|---|---|---|
| right plate (`materials.sheet_b_plate`) | (0.080, +0.01755, −0.030): G on its inner face | +U | +S | P +Y, out of the grip |
| left plate (`materials.sheet_a_plate`) | (0.080, −0.01755, −0.030) | **−U** | +S | P −Y, out of the grip |
| bent strap (`materials.strap_bent`) | G (0.080, 0, −0.030) | +U | +S | P +Y |

The ruling says "+X = U, +Y = S, +Z out of the grip" for both plates. On the left that would be a mirrored frame, which
a node cannot have, so the left plate keeps +Y = S and +Z outward and its **+X is −U**. In its own frame the left
plate's outline is then (x, y) = (−U, S) and the right plate's (x, y) = (U, S): mirror images, as two sheets cut
stacked are. Both plates occupy z 0 .. 2.0 of their frame.

### Marks on the core

Pose marks (`"pose": true` in `parts.json`: the incoming node takes the mark's world transform), each seat with its
clear pose: `seat_gimbal` / `clear_gimbal` (datum D), `seat_plate_l` / `clear_plate_l`, `seat_plate_r` /
`clear_plate_r` (the plate frames above), `seat_strap` / `clear_strap` (G; clear is 65 mm down the axis),
`seat_plate_screw_lc`, `_ld`, `_rc`, `_rd` / `clear_plate_screw_*` (the four case screws: origin under the head, +Z
out of the hole). Paths: `loop`, `lead`, `seam_l`, `seam_r`.

## 5. Mine, for reference

Two brass grip screws (`grip.screw_a`, `grip.screw_b`: M4, 34 under a cross-drive pan head d 8.6 × 2.6, `bit: cross`) through A
and B and the tang; the housing pin
(d 3.0 × 30, along Y) at G (U −16, S +37), in the bite of the plates; the trigger lead in an open channel down the back of the core (path
`grip.core/lead`) to a keyed plug on the cell bus at the lower end of the tang. The grip's seat on the pistol is the
core's own rest pose (`grip.glb` is in the pistol's frame) with `grip_core__clear` as the slid-off pose.

## What I need back

Tell me (through the orchestrator) if the unit cannot be made to fit d 26 × 20 with a d 30 × 2 flange, or if M3 × 10
case screws do not suit your case: I would rather move a number now than find out at the sweep. When `servo/export/`
exists, `grip/check.py` loads the unit as an external family and sweeps it into the pocket.

## As built (20 Nov, 18:55)

`grip/export/check.json` passes with the stripped pistol, the servo family's gimbal unit and four case screws, and
stand-in plates and strap made from this file's numbers. No dimension above changed. What the build settled:

- **The plates stand proud** on flat seat faces at Y ∓17.5 (inner face |Y| 17.55, outer 19.55). There is no recess.
  A land of 1.7 to 3.9 mm of core shows round each plate at the front, base and back; along the top the plate's edge
  is the core's own edge.
- **The strap lies in an open channel** 17.3 wide: flush with the core on the back leg and the toe lip, 0.4 to 0.6 mm
  below the core's surface along the base and up to 1.1 mm below it round the heel.
- **The unit fits the pocket**: `servo.gimbal_cradle` and what rides on it, swept 40 mm from `clear_gimbal` to
  `seat_gimbal`, no overlap, 0.02 mm from the bore wall at the tightest facet. The pocket is a full circle and does
  not use the flange where the servo family notched it.
- **The case screws fit holes C and D** through the plates at the four `seat_plate_screw_*` marks.
- **The seam** is an open line per plate (front edge, base, back edge, round the bite): paths `seam_l`, `seam_r`.
- **The real plates and strap fit** (20:37): `grip/check.py` sweeps `materials.sheet_a_plate`, `sheet_b_plate` and
  `strap_bent` from `materials/export/materials.blend` in place of the stand-ins: no overlap, plates 0.05 mm off the
  seat faces, strap 0.14 mm off its bed. `grip/crosscheck_materials.py` reads the same parts from `materials.glb`:
  punch marks 1 to 4 are 0.00 mm off holes A to D in both plates.
- **The core is the pressed core** (`SEAM.md` section 10). The mould parts on the mid-plane Y = 0; path `parting` on
  `grip_core` (up to 40 points on the surface: front strap, toe, base, heel, back strap) is where
  `materials.core_flash` stands. The as-found texture set is the core fresh from the mould; wipes `skin`, `flash`,
  `pocket` (PARTS.md).
