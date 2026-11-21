# Scrap pistol, rebuilt to come apart (`pistol/`)

`model-pistol`, 20 November 2026. The in-game scrap pistol is one fused Meshy mesh (`Art/OuterBerms/ScrapPistol.glb`,
12,052 triangles). This family rebuilds it as 22 separate parts to the same outline, bore, rail and grip position, so
it can be stripped on Brann's bench and can replace the old mesh in the hand. Parts and mechanism: [PARTS.md](PARTS.md).
Kit: [../kit/READY.md](../kit/READY.md). Method: [../ANYMACHINE.md](../ANYMACHINE.md).

## Files

| Path | What |
|---|---|
| `measure.py`, `work/skin_measure.json`, `work/skin_mask_*.npy` | the Meshy pistol measured as a skin: bounds, bore, profiles, silhouette masks |
| `sheets/overall.png`, `sheets/look.png` (+ prompts) | the two reference sheets (fal Nano Banana Pro) |
| `PARTS.md` | parts breakdown, written before the build |
| `pgeom.py` | the grip's shared geometry (frames, plate outline, holes, the grip surface), also used by `../grip/` |
| `build.py` | builds every part, the rig, the sequence, the outline check, the bake and both exports |
| `outline_check.py` | the fixed numbers against the skin: `export/outline.json`, `review/outline_*.png` |
| `check.py` | the machine checks: `export/check.json` |
| `export/pistol.glb`, `parts.json`, `stats.json`, `check.json`, `outline.json`, `tex/` | the bench family (metres) |
| `export/pistol_hand.glb` | five merged nodes in `ScrapPistol.glb` units for the hand |
| `export/pistol.blend` | the source scene (procedural materials, rig still driven) |
| `review/` | compare renders and outline overlays |

Rebuild: `SH/blender.sh pistol/build.py -- --nobake` (10 s), `SH/blender.sh pistol/check.py` (6 s),
`SH/run.sh mp-bake SH/blender.sh pistol/build.py -- --size 4096 --spp 16` then `SH/wait.sh mp-bake`.

## Frames and units

`pistol.glb` is in the pistol metric frame P: metres, the origin and axes of `ScrapPistol.glb` (glTF: muzzle −X, up
+Y, the player's right −Z). `grip.glb` is in the same frame, so the two family roots placed together are the fitted
pistol. `pistol_hand.glb` is the same geometry divided by 0.13674 (the ScrapPistol instance's scale), with identity
node transforms, so it stands where `ScrapPistol.glb` stands under the same instance and the five existing mods in
`PistolMods.glb` keep their places.

## Provenance

Original work, built procedurally in Blender 5.2.2 by the scripts here on the programme's kit. The Meshy pistol was
used only to measure from; none of its mesh or textures is in the export. Reference sheets: two images from fal
(Nano Banana Pro), $0.30, prompts beside the images. No Meshy credits.

## Departures (from the brief and the contract)

1. **Units of the bench GLB.** The brief asks for the pistol "in the same units, axes and origin as ScrapPistol.glb";
   the contract asks for metres. `pistol.glb` is in metres (same axes and origin), and `pistol_hand.glb` carries the
   ScrapPistol units for the hand, as the brief already asks of the grip. One GLB cannot be both, and a 22-node pistol
   in the hand would cost 22 draws twice over.
2. **The cell sits on top, not on the side.** The Meshy mesh has its glass cell in the top of the receiver (the
   prompt said "on the side"; the look sheet draws a side window). The outline is the fixed thing, so the cell stays
   on top, in an open bay, and shows from both sides above the low bay walls.
3. **The reference sheets do not hold the outline.** The image service drew its own boxier pistol both times, also
   with the grey renders of the skin as the first reference. The sheets are used for look only (materials, fasteners,
   the cell, the bus, the wrap); every dimension comes from the skin.
4. **`cell_latch` is an upright pawl, 0 to 22 degrees.** A hook that lies over the cap cannot clear a straight lift in
   22 degrees; a pawl standing behind the cell, with its beak over a stud on the rear cap, does (checked by the sweep).
5. **Extra fields in `parts.json`** (all optional for a reader): `fixed` (its own node, never comes off in this job),
   `flex`, `loose`, `rides`, `sequence`, `absent_at_start`, `unit_scale_m`.
6. **4096 atlas.** At 2048 the family gets 34 px/cm, under the contract's 60; at 4096 it is 68.

## Results (Milestone 2, 20 Nov 17:55; a 2048 bake)

| | |
|---|---|
| Parts | 22 nodes, 75 helper empties, rig `pistol_rig` with three clips of one second (`cell_latch_param`, `cell_seat_param`, `trigger_param`) |
| Triangles | 31,775 of 45,000: frame 8,206, wrap 3,560, scales 2,056 + 2,844, bus 2,402, two wire twists 1,648 each, barrel 1,540, housing about 1,700, cell 1,192; the rest under 800 each |
| Textures | one 2048 atlas (colour, normal OpenGL +Y, ORM, emission), fill 0.40, **34 px/cm**; materials `M_pistol`, `M_pistol_emissive`, `glass_cell` (blend), `lamp_pistol` (its own emissive) |
| `check.json` | PASS: contract; params (latch 0.11 mm clear, cell 0.15, trigger 0.5, all clamp); 13 sequence events (9 swept, 4 flexible parts not swept), no overlap, no unexpected contact; 3 fasteners in their holes with heads seated; GLB re-import (nodes, triangles, bounds 0.000 mm, helpers, clips end 0.000 mm from the driven rig) |
| `pistol_hand.glb` | `ScrapPistol` 13,428, `ScrapPistol_grip_stock` 15,403, `ScrapPistol_cell` 1,192, `ScrapPistol_trigger` 718, `ScrapPistol_lamp` 84 triangles |

Fixed numbers against the Meshy skin (`export/outline.json`):

| Number | Skin | Rebuilt | Error |
|---|---|---|---|
| Length (X) | −130.13 .. +129.88 | −130.10 .. +129.28 | +0.03 / −0.60 mm |
| Width (Y) | −25.16 .. +25.40 | −25.17 .. +25.17 | −0.01 / −0.23 mm |
| Height (Z) | −85.54 .. +85.29 | −85.70 .. +85.00 | −0.16 / −0.29 mm |
| Bore axis (Y, Z) | 0.713, 58.897 (circle fit); FACTS 0.75, 58.85 | 0.750, 58.850 | 0.06 mm |
| Bore mouth X | −130.13 | −130.10 | 0.03 mm |
| Rail, left face (10 samples) | Y −9.35 .. −11.70 | | at most 0.15 mm |
| Guard bottom at X −5 | −18.70 | −18.51 | 0.19 mm |
| Trigger blade | X −1 .. +16, Z from −10 | X −0.5 .. +16.5, Z from −10.4 | about 0.5 mm |
| Grip surface along the axis (20 samples) | | | mean 2.3 mm inside the skin; front strap up to 4 mm where only tape covers it; one ray reads 25.8 because it passes between the scales |
| Hand points (distance to the surface) | 27.43 / 23.29 mm | 27.28 / 22.93 mm | −0.15 / −0.36 mm |
| Silhouette, side / top / front | | IoU 0.949 / 0.935 / 0.928 | largest deviation 3.0 / 2.5 / 2.0 mm |

The five other mods against the new pistol (vertices deeper than 0.3 mm inside, deepest; skin in brackets): bored
alloy barrel 0 (6, 7.3 mm), lattice barrel 0 (65, 28 mm), overclocked cell 33, 1.0 mm (64, 1.3 mm), capacitor cell 57,
1.1 mm (117, 1.7 mm), gyro grip 75, 2.9 mm (65, 1.5 mm). The present Stabilised grip mod: 51, 2.6 mm (93, 1.7 mm).

## What still differs from the sheets

- **Outline** (on purpose): the sheets drew a boxier pistol; the model holds the skin.
- **Steel**: cleaner than `sheets/exploded.png`: less rust gathered in corners and round screws, no file marks or deep scratches, no stamped numbers.
- **Wrap**: tidier than the sheet: even bands, two loose tape ends; the sheet's is ragged, overlapping, with frayed cloth edges.
- **Cell**: on top in an open bay (sheet: side window with a domed steel end); latch is an upright pawl (sheet: a long leaf on top).
- **Bus**: a plain copper rod (the exploded sheet turned it into twisted wire).
- **No lanyard loop** on the butt, no leather-and-wire binding on the dust cover's nose (it is the mod rail).
- **Wood**: one crack and one chip a scale; the sheet's scales are more broken at the edges.

## Open

- The UVs of wires and straps are projected rings: they waste the atlas (fill 0.40). Strip UVs for tubes and bands
  in the kit would lift the density by about a quarter.
- 4096 bake not run (about 11 minutes by the 2048 timing).
- Not seen in Unity, in the hand or in a native capture. The glass is alpha-blended and the fluid inside it emissive:
  how that sorts and blooms in URP is unknown.
- `grip_gyro_braced` sits 1.4 mm deeper in the new butt plate than in the skin's.

## 21 November: surface pass finished, 4096 bake, gyro fit (`model-pistol`)

- **Surfaces** (`px.py`, by `model-pistol-surface` on 20 Nov, finished here): layered steels per part, rust and old oil in
  recesses, tarnished brass, copper, oiled walnut, stitched leather, woven tape, chipped Warden orange from
  `MT.WARDEN_ORANGE` / `MT.BARE_ALLOY`, dirty cell glass baked with its alpha. 21 Nov: rust colours a touch more orange,
  more of it on the receiver (`rust=1.35`), brass darker and more tarnished (`tarn=`), so the brass is not clean yellow.
- **Bake**: 4096, spp 12, atlas fill 0.594, 82.6 px/cm on frame, housing, scales and cell (contract 60), wrap 61.7.
  `pistol_hand.glb` carries a 2048 set made from the same bake (`tex/pistol_hand_*.png`).
- **Emissive**: glTFast here does not read `KHR_materials_emissive_strength`, so the cell's fluid stores colour x strength
  in the emission map at strength 1 (value at most 1.0). The cell blooms only if the Unity material multiplies it.
- **grip_gyro_braced fit** (orchestrator's ruling (a), 21 Nov 08:36, on integration's 08:28 numbers check): the frozen
  Mk II grip mod bears on the old Meshy surface at the frame's left rear and down the backstrap. Three changes bring the
  surface there back to within 1 mm of the skin: a welded **clip seat** on the frame's left rear (x 56.5..63.2,
  z 23.3..27.8, face at y -14.15); a folded **leather pad** on the backstrap between the two turns of binding wire A (part of
  `pistol.wrap`); the **heel** below grip level s -44 shifted 1.2 mm back (+x) by one smooth field applied to every part
  there (`gyro_heel` in `build.py`; housing and scales are sliced across the ramps first so they follow it together).
  strap3 is 1.4 thick (was 1.6). integration's `hand_check.py` on the new `pistol_hand.glb`: PASS, gyro max 0.93 mm.
- **Departure**: the rear bound now stands 0.60 mm behind the skin's (was 0.60 inside); the heel had to move back to meet
  the mod. Every other fixed number is unchanged. 42,318 triangles of 45,000. The two concave ledge corners under which grip.core seats are cut back to the sharp outline (a bevel had filled them by 0.34 mm; grip/check.py failed on it). bind_wire_b is now twisted on the left (bench's request).
