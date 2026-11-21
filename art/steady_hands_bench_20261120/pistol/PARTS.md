# Scrap pistol, rebuilt to come apart: parts breakdown

`model-pistol`, 20 November 2026. Written before the build script (`build.py`); the script's numbers are the authority
where they differ after the second pass, and the differences are listed in `README.md`.

## What it is held to

The in-game pistol, `Art/OuterBerms/ScrapPistol.glb` (Meshy, one fused mesh), imported at 0.13674 as a measuring skin
(`measure.py`, `work/skin_measure.json`). Fixed and asserted in the build:

| Number | Value (metric frame P: metres, muzzle −X, up +Z, right +Y) |
|---|---|
| Overall | 260.0 long (X −130.1 .. +129.9), 170.8 tall (Z −85.5 .. +85.3), 50.6 wide |
| Bore axis | Y +0.75 mm, Z +58.85 mm, mouth at X −130.1 mm, bore d 14 |
| Rail for the cell mods | left face of the dust cover (X −101 .. −58, Y −9.4 to −10.0 as on the skin) and of the frame behind it (Y −11.55), Z 24 .. 40 |
| Trigger and guard | blade X −1 .. +16, Z −10 .. +17; guard opening X −22 .. +27, guard bottom Z −18.6 (from the side silhouette) |
| Grip | centre G0 = (80, 0, −30) mm, axis raked 24.9° (S = (−0.42038, 0, 0.90736)), about 61 deep and 39 to 44 wide |
| Origin and axes | those of `ScrapPistol.glb` |

The outline is checked as silhouette masks in three views against the skin (`export/outline.json`).

The look comes from `sheets/overall.png` and `sheets/look.png` (bolted plates, slotted screws, brass-capped glass cell,
copper bus, leather, tape and twisted wire, orange butt plate) and from `../concept/bench_overview_fal.jpg`. The image
service drew its own outline both times, so the sheets fix the look and the skin fixes every dimension.

## Why it rattles (what the player finds)

1. The **tang** (the grip spine of the frame) broke off short years ago and the stub that is left is **cracked**. The
   two wooden scales hang below it with nothing between them.
2. So the scales are held on by two screws at the top, and by **tape, leather and two twists of wire** lower down.
3. The **backstrap housing** rides a T-rail on the tang stub and is kept there by one cross pin and a tired spring:
   it shifts in the hand.
4. The fasteners are whatever was to hand: one grip screw is bright, the other rusted in; the receiver has slotted
   screws and hex bolts mixed.

The Stabilised Pistol Grip replaces everything in the lower table with one fused core that takes the stub in a
dovetail (`../grip/INTERFACE.md`).

## Parts that stay on in this job

| Part (`pistol_…`) | Made of | Held by | Notes |
|---|---|---|---|
| `frame` | steel, with brass side plate (right) | (root) | lower frame, upper receiver with the cell bay, trigger guard, beavertail, sights base, **tang stub** (T-section: web 18 × 6.8, dovetailed head 6 × 12 up to S +40, from the frame down to S +2; clearance holes A (U −4, S +40) and B (U −4, S +8) d 4.3, pin hole (U −16, S +37) d 3.2; crack from the front edge at S +16; broken end), front cell clip, receiver bolts |
| `barrel` | dark steel | collar bolt | muzzle ring d 25, ribbed collar (six ribs), rear ring, front sight, emitter cup 33.5 deep |
| `dust_cover` | steel | two screws | under the barrel, with the round nose; its left face is the front of the mod rail |
| `trigger` | steel | pivot pin at (X 10.5, Z 22.3) | rig `trigger` (0 .. 12°) |
| `lead` | sleeved copper lead | fixed in the frame's rear face under the beavertail | flexible; down an open groove at the top of the housing, then inside it behind the T-rail to the plug |
| `cell_bus` | copper rod and strip, brass terminal plate (left), two ceramic stand-offs, cream socket block | rivets | from the rear cell clip along the left of the receiver to the terminal plate, then down the front edge of the tang to a keyed socket at its lower end |
| `cell_latch` | brass | pin across the bay floor | an upright pawl behind the cell with a thumb tab; its beak sits over the stud on the cell's rear cap. Rig `cell_latch` (0 .. 22° back) |
| `status_lamp` | glass lens | bezel | rear face of the receiver, toward the shooter; its own emissive material |

## Parts that come off (in this order)

| Step | Part | Made of | Held by | Comes off |
|---|---|---|---|---|
| s0.cell | `cell` (glass tube, two brass caps, retaining stud, fluid) | glass, brass | two saddle clips and the latch | latch back, then straight up; rig `cell_seat` (0 .. 16 mm) |
| s1.bind | `bind_wire_a`, `bind_wire_b` | copper wire d 1.2 | their own twist | snipped at the twist (mark `snip`), they spring open |
| s1.tape | `wrap` (three leather straps with two studs, two bands of cloth tape) | leather, tape | the wire twists, its own tack | peeled along `peel` |
| s1.screw_a | `screw_grip_a` (upper, bright) | steel, slotted | thread in the right scale's nut | 6 turns, out to the left |
| s1.screw_b | `screw_grip_b` (lower, rusted and seized) | steel, slotted | thread in the right scale's nut | oil mark `oil`, then 6 turns |
| s1.scales | `scale_l`, `scale_r` (cracked) | wood; the right one carries two brass nuts | the two screws, the wrap | lifted off sideways, left to −Y, right to +Y |
| s1.lead | `lead_plug` (keyed, cream) | plastic, two brass pins | its tab | pulled straight back out of the socket (−U) through a window in the housing's back wall |
| s1.pin | `housing_pin` d 3 × 30 | steel | friction, through the housing's two ears and the T-rail; the ears show in a square bite of each scale | driven out to the right (+Y) |
| s1.housing | `housing` (backstrap, heel and orange butt plate in one) | steel, orange paint | the pin, the T-rail | slides down the rail (−S) |
| s1.housing | `housing_spring` | spring steel | a blind hole in the back of the T-rail, pressed by the housing's back wall | jumps out backward (−U) once the housing is off |
| s6.plug, s6.pin, s6.cell | the plug, the pin and the cell go back | | | swept again in the grip family with the new grip on |

Loose: `card_a`, `card_b` (paper test cards, 148 × 105).

The four holes of each scale are the template for the new side plates: A and B (screws, d 6.1 with a counterbore on
the left scale), C (U +22, S −2) and D (U −22, S −44) (the wrap's two studs press into these, d 3.3).

## Rigs (`pistol_rig`)

| Parameter | Joint | Range | Moves |
|---|---|---|---|
| `cell_latch` | hinge about +Y through (X −28.3, Z 61.6) | 0 .. 22° | `cell_latch` |
| `cell_seat` | slide along +Z | 0 .. 16 mm, with `cell_latch` at 1 | `cell` |
| `trigger` | hinge about −Y through (X 10.5, Z 22.3) | 0 .. 12° | `trigger` |

## Budget

45,000 triangles; one 2048 atlas (4096 if the 0.3 m view needs it), plus one glass material and one lamp material.
