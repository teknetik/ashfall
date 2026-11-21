# Damaged Servo (family `servo`)

Built 20 November 2026 by `model-servo` for the Steady Hands bench programme. The method is AnyMachine's
(`../ANYMACHINE.md`): sheets, `PARTS.md`, one build script, compare renders, checks by machine, bake, export.

## Files

| File | What |
|---|---|
| `sheets/` | `servo_turn.png` (= `overall.png`), `servo_exploded.png`, `servo_close1.png`, each with its `*.prompt.txt`; `usage.json` |
| `PARTS.md` | the parts breakdown, written before any geometry and kept in step with the build |
| `build.py`, `gimbal.py`, `sv.py` | the build: `SH/blender.sh servo/build.py -- --nobake` (seconds), `-- --size 2048 --spp 24` to bake |
| `check.py` | the machine checks: `SH/blender.sh servo/check.py` writes `export/check.json` |
| `review.py` | the staged review renders and the sheets beside the references: `SH/blender.sh servo/review.py` |
| `src/stencil_8372.png` | mask for the stencilled serial on the lid (made with ImageMagick from Liberation Mono Bold, SIL OFL) |
| `export/` | `servo.glb`, `servo.blend` (source scene, rigs still driven), `parts.json`, `stats.json`, `check.json`, `tex/` |

## Provenance

Everything is original: geometry and materials are procedural (this folder and `../kit`). Reference sheets were made
with OpenAI `gpt-image-2` from written prompts; the overall sheet took the game's own inventory icon
(`UI/Art/servo.png`) as its input image, the exploded and close-up sheets took the overall sheet. No Meshy credits,
no fal images. No third-party meshes or textures.

## Departures (from the brief, the contract, the kit or the sheets)

1. **Two rigs in one family.** `servo_rig` (the three clips) hangs on the case body, `servo_gimbal_rig` (pitch, roll,
   rotor) hangs on the gimbal cradle, so that the unit moves as one when it is lifted out and can be put in the grip
   with its rig. The kit's `Family.finish()`, `rig.finish()` and `check.main()` assume one rig per family: `build.py`
   wraps the two behind the one-rig interface and `check.py` calls the kit's check functions once per rig. The kit is
   not edited. `parts.json` has the rig of every parameter in `params[].node` and the parents in `rigs`.
2. **Gimbal parameters rest at 0.5, not 0.** A gimbal swings both ways from level. `gimbal_pitch` and `gimbal_roll`
   run -12..+12 degrees with **0.5 = level = the as-found, modelled and GLB rest pose**; 0 and 1 are the two stops.
   (`parts.json`: `param_rest`, and `rest` on the two parameters.) The kit's own convention is 0 = as found.
3. **The gimbal's contract parents.** Ring, race, rotor, retaining ring and grit all have `parent: servo.gimbal_cradle`
   (their node sits under the cradle through the rig); `rides` says which parameter moves each.
4. **The cradle is modelled here.** `DESIGN.md` section 3 has the cradle coming out of the servo; `model-pistol`'s
   brief lists it as a grip part. There is one cradle, `servo_gimbal_cradle`, built to `grip/INTERFACE.md` with its
   node frame equal to the interface's datum D.
5. **Trunnion screws.** The interface's flange is a plain d 30 with no ears, so the two trunnion screws stand outside
   it, one beside each trunnion: shank in a half-round scallop of the rim, wide head clamping the flange, thread in
   the stator's blocks. The scallops and a small third notch (sense lead) are additions to the interface's unit that
   only remove material.
6. **The trim resistor is swept off the board while the board is still in the servo** (sequence order plug, resistor,
   board), because the kit's sweep drops a removed part's children. The geometry tested is the same.
7. **Flexible things are not swept**: circlip and retaining ring (sprung with pliers), the three leads and the stator
   winding (`flex` in `parts.json`). The plug with its lead ends is swept as a rigid part that tilts 100 degrees about
   the bands with a 0.14 mm kerf at the cut.
8. **Sheets.** The outside follows the overall sheet (round can); the inside takes the exploded sheet's flat deck and
   flat stator; the gear stack is small, large, small; the lid's screws sit on seam-flange lugs; the gimbal is inside
   its cup. Reasons in `PARTS.md`, "Where the sheets disagree".
9. **Size.** 95.0 x 70.0 x 55.4 without the torn outside leads, which hang 17 mm past the rear.

## For the Unity side

- The servo lies on its foot, origin on the bench under the middle of its length, output shaft toward -X (Blender).
  Everything inside lifts out along the servo's +Z; clamp it in the vise lid up.
- `servo_lead_plug` has its origin at the lead bands, so moving it to its `__clear` pose reads as the leads bending
  there. `servo_gimbal_cradle` carries `servo_gimbal_rig` and the three leads.
- As-found textures: one shared set `tex/servo__dirty_{color,normal,orm}.png` on the same UVs (dust on the case,
  lid, clips and case screws; corrosion on cradle, ring and race). Blend with a mask inside each part's zones.
- `servo_stator_winding` and the three `servo_gimbal_grit_*` are nodes of their own so they can be thinned or hidden.

## State on 20 November, 17:55 (Milestone 2)

Built to `grip/INTERFACE.md`, baked at 2048 (16 samples, 8.5 minutes on the CPU), `export/check.json` passes
(contract, parameters, sequence, fasteners, order tests, interface, export), copied to
`unity/AthenHill/Assets/AthenHill/Art/Bench/Servo/` (`servo.glb`, `servo.parts.json`, `tex/servo__dirty_*.png`).
41,324 triangles of 45,000; one material `M_servo`; texel density 67 to 71 px/cm on the gimbal, 38 to 56 elsewhere;
the atlas is only 38 % filled (the kit packs by bounding box and the family has thousands of small islands).

Review sheets (`review/`): `compare_overall.png` (sheet beside six views, clean set), `states.png` (as found at the
bench camera and at 0.3 m, dusted, lid off, board off, gears off, gimbal out), `compare_close.png` (the close-up
sheet beside six matching views), `compare_exploded.png`, `gimbal.png` and `g6_apart.png` (the unit alone, as found,
cleaned, side, top, at both stops, taken apart), `glb_views.png` (the exported, baked GLB re-imported).

What still differs from the sheets (seen in those renders):

- The orange is redder and cleaner than the sheet's brown-orange; the as-found dust is lighter than "caked".
- End bells and clips are plainer: dark even steel, flat bent straps; the sheet's are rough rusty castings and
  shaped latches. The scorch is a compact black patch, the sheet's is a soot gradient over the rear third.
- The board has about a third of the sheet's component density, and its charred end is a few lumps.
- The gimbal is a bright turned-alloy cup with everything inside it (the interface); the sheet's is dark cast steel
  standing proud with ears.
- No clip comes off (they are hinged to the body and rigged); the sheet shows them loose.

Kit notes for `model-pistol`: `rig.finish()` parents parts while the parameter is 0, so a joint with a non-zero
minimum rests wrongly in the GLB unless the parts are parented at the rest value (done by hand here);
`check_export` samples clips one after another without resetting the pose, which fails for a child joint; and
`review.py --glb` frames on the importer's bone-shape meshes, so a rigged family comes out as a speck
(`src/glb_view.py` is the framed version).

## Surface fix round, 20 November 18:15 to 19:00 (orchestrator's list of 7; geometry, ids, parents, params unchanged)

1. **Paint colour**: both paints take the shared Warden orange of `SEAM.md` section 8, linear albedo (0.60, 0.20, 0.076)
   (`sv.lin()` turns it into the sRGB triple the kit's `make()` expects); bare alloy under it linear (0.55, 0.53, 0.50),
   metallic, roughness 0.5.
2. **Paint wear**: the even speckle is gone. `sv.add_wear` lays a dozen fields per paint where the thing was handled
   (foot corners and bolt slots, clip seats, screw bosses and lid lugs, two rib crests, a length of flange edge, one
   two-lobed field on the lid's shoulder, one long dragged field on the -Y side), each with a noise-broken coast and
   a thin primer rim; `sv.add_scratches` adds thin scratches along the axis; one rare stray flake layer; handling
   stains as the second tone.
3. **End bells**: mottled cast surface (two noise scales and a stipple), brown rust in recesses and round the bolt
   heads (`sv.add_cavity`), a rubbed lighter rim (wider edge wear).
4. **Scorch**: a wide soft field of heat-darkened, blistered paint with soot thickening to black inside it, carried
   onto the body below the lid corner and onto the rear bell.
5. **As-found dust**: almost no veil on the sides; weighted to upward faces and recesses.
6. **Outside leads**: their own dull, dusty materials (`xwire_*`).
7. **Clips**: a formed latch: a bow in the upright, the flat that bears on the lid flange, a rolled finger lip. Same
   hinge, same 0 to 40 degrees; the parameter sweep and the lid's blocked/free tests pass unchanged.

Review light: the kit's studio is neutral and its AgX view washes a bright orange toward pink; `review.py` and
`src/glb_view.py` gained a warm key (about 3000 K, sky turned down) and each sheet's labels say which light a panel
used. `check.py` now redoes the kit's clamp test against the pose at 0: since its 18:01 update the kit compares the
pose at -0.5 with the rest pose, which fails for a parameter that rests at 0.5.

## Last surface pass, 21 November (`model-servo-surface`; geometry, ids, parents, params, rigs, zones unchanged)

The 18:48 bake had three faults on the calibrated rig (`review/surface/before_glb.png`): bare islands brighter than the
white card (the old bright alloy through `sv.lin()`), one flat orange between them, and an even pale line on every
rib and flange edge (the kit's `edge` wear). What changed, all in the paint block of `build.py` and in `sv.py`:

- **Shared constants only**: paint `MT.from_linear(MT.WARDEN_ORANGE)`, bare metal `MT.BARE_ALLOY` / `BARE_ALLOY_ROUGH`;
  every other tone (oil, soak, chalk, rub, oxide, fresh scratch) is one of them times a factor (`tone()`).
- **No kit edge line** (`edge=None`): edges lose paint through `sv.add_flakes(edge_gain=...)`, in runs.
- **Flakes in the plates' character** (`materials/mtl.py flakes()`: patch, coast and crumb octaves, primer rim, pits,
  oxide stains on the bare metal) only inside handled fields (`WEAR`: foot corners and front edge, round the bolt
  slots, clip seats, screw bosses and lid lugs, rib crests, lengths of flange edge) and along outside edges. Two new
  arguments made it work on a can: `plateau` (the field pushes across its width, not only at its centre) and `mix`
  (more coast and crumb: the fields are 5 to 12 mm, smaller than the 16 mm patch octave, so with the plates' weights
  most fields landed on a low patch and showed nothing; that was trial t1).
- **One long dragged field** on the -Y flank it lay on: flakes drawn out along X (`stretch`), dull axial scratches.
- **Clean fields are not flat**: handling stains gathered where it is held (`HELD`), one soaked spill, light chalking
  on upward faces, burnished rubs along the axis, short bright and dull scratches along the axis (finite length: a
  stretch of 7 per metre had made continuous stripes, trial t2), and a grime **tide mark** toward the foot
  (`sv.add_grime(tide=...)`: a wandering top edge with a darker dried line, thicker below).
- Kept as they were: end bells, scorch and soot, as-found dust, outside leads, clips, everything inside.

Review: `src/surface_view.py` (warm, neutral and the materials lamp; closed, open, as found, beside the plates; GLB or
source). Its `w_plates` shot parsed as the clean state until 21 Nov, so no earlier sheet has the plates in frame.
`review.py` (states.png) and `src/glb_view.py` (glb_views.png) now use the kit's calibrated warm rig instead of the
neutral rig recoloured by hand. Trials build to `export_wip/` (`build.py -- --out export_wip`); the previous published
build is `export_prev_1848/`, its paint block `src/paint_block_1900.py.txt`.

Departures: (10) `review.py`/`glb_view.py` warm panels changed rig (above); (11) the brief's "old bright alloy through
`sv.lin()`" was already replaced in `build.py` by the previous agent before the stop; the fault was in the bake only.
