# The shared Blender kit (`kit/`)

Published 20 November 2026 by `model-pistol` for `model-servo` and `model-bench`. Blender 5.2.2, headless, metres, Z up.
Only `model-pistol` edits these files; changes are announced in `../PROGRESS.md`. If something is missing or wrong,
tell the orchestrator and work round it in your own folder (copy a function, do not patch the kit).

Method: `../ANYMACHINE.md`. Contract: `../CONTRACT.md` section A. The working example is `kit/example/` (a junction
box with a cover, two screws, a hinged latch, a sliding fuse, a wipe zone): read `example/build.py` first.

## Run it

```
SH=~/.local/state/ward-programme/steady-hands-20261120
$SH/blender.sh <family>/build.py -- --nobake            # geometry, parts.json, stats.json, source .blend (seconds)
$SH/blender.sh <family>/check.py                         # the machine checks -> export/check.json, exit 1 on failure
$SH/blender.sh kit/review.py -- --family <family> [--only six,bench,close,exploded] [--samples 40] [--hero node,node]
$SH/run.sh TAG $SH/blender.sh <family>/build.py -- --size 2048 --spp 24     # the bake (minutes): detached, then
$SH/wait.sh TAG                                                             # wait for it; one bake at a time
$SH/blender.sh kit/review.py -- --family <family> --glb  # what the exported GLB looks like in a plain viewer
```

The Blender slot is shared by every agent: keep `--nobake` builds and checks short, and never pipe a Blender command
through `grep`/`tail` in the foreground of a tool call (if it takes long you cannot see why, and it holds the slot).

## A family in 20 lines

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kit'))
from family import Family, G, MT, CT, RG          # geo, mats, contract, rig
import am_parts as AP
from mathutils import Vector
MM = 0.001; X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

F = Family('servo', __file__, budget=45000)        # empty scene; reads --nobake --size --spp --review
M = F.mats                                          # the shared palette; add yours with MT.make(...)
case = G.prism('case', G.rounded_rect(40 * MM, 20 * MM, 3 * MM), 30 * MM, (0, 0, 0), X, Y, Z, M['alloy_cast'], w0=0)
G.boolean(case, [AP.hole_cutter(3.2 * MM, 12 * MM, (15 * MM, 0, 30 * MM), Z)])
G.bevel(case, 0.4 * MM, 2)
CT.part(case, 'servo', 'case', 'Servo case', kind='part', material='alloy', mass='medium', loose=True, item='droid_servo_damaged')
scr = AP.screw('s', 3 * MM, 10 * MM, head='pan', drive='cross', mat=M['steel'], at=(15 * MM, 0, 30 * MM), axis=Z)
CT.fastener(scr, 'servo', 'screw_case_1', 'Case screw', bit='cross', turns=6, holds=['case'], shank_d=3 * MM,
            parent='case', steps=['s2.screws'])
CT.clear_along(scr, 16 * MM)                        # '<node>__clear': backed out along the screw's own +Z
CT.sequence([{'op': 'remove', 'part': 'screw_case_1', 'step': 's2.screws'}])
F.finish()                                          # hierarchy, validate, UVs, bake, .blend, GLB, parts.json, stats.json
```

and `<family>/check.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kit'))
import check
check.main(os.path.dirname(os.path.abspath(__file__)))          # externals=[('../grip', None)] to add another family
```

## Rules the kit assumes

- **One mesh object per contract part**, registered with `CT.part` (or `CT.fastener`, `CT.tool`). Sub-shapes are made
  as objects and joined with `G.join` before registering. A node's scale must stay 1.
- **Closed solids** where you can (`G.solid_check(o)` returns `(0, 0)`): booleans, bevels and the fastener check's
  inside test need them. Open shells (a thread ridge, a canvas flap) are fine for looks and for the overlap sweep.
- **Model real clearances.** Parts that touch should be 0.05 to 0.1 mm apart, a screw in its hole 0.1 mm clear all
  round. The sweep shrinks the moving part by 0.03 mm, so exact contact passes, but anything deeper is an overlap.
- **Origins mean something**: the seat point of a part, the underside of a screw head (+Z out of the hole), the
  bench contact point of a loose thing. Set them with `origin=` in `CT.part` or `G.set_origin` **before** `F.finish()`:
  the materials are in object space.
- **Triangles are spent on silhouette at 0.3 m.** Detail under about 0.4 mm goes in the material (`bumps=`).
- `F.finish()` triangulates every part (the tangents of the normal map need it), so the counts in `stats.json` are
  what Unity gets.
- **Booleans are checked.** `G.boolean` compares each result's volume with what is possible and retries with the
  MANIFOLD and FLOAT solvers (the EXACT solver returned an intersection for a difference on a bevelled part, twice).
  It raises if none is possible: give it closed solids, and do not let a cutter's face lie in a face of the target.
- **Shade last.** `G.shade(o, angle, weighted=True)` drops custom normals and recomputes them; a boolean after a
  bevel or a weighted-normal pass leaves wrong normals on the new faces (it showed as crumpled flats).
- `MT.make(rust=(colour, amount, cavity weight, noise scale))`: the two extra numbers keep rust to recesses with a few
  broad blooms; the two-number form mottles every 11 mm and reads as camouflage on large flats.

## Files and functions

### `geo.py` (import as `G`): geometry, every builder returns a linked mesh object

| Function | What it makes |
|---|---|
| `lathe(name, loops, segs, origin, axis, ref, mat, phase, arc)` | revolve profiles `[(s, r)]` about an axis; open profiles ending at r = 0 are closed with a pole; `arc=(a0, a1)` for part of a turn |
| `prism(name, poly, depth, origin, u, v, w, mat, w0)` | extrude a 2D outline along `w` (from `w0`, default centred) |
| `box(name, center, size, rot, mat)`, `cyl(name, p0, p1, r, segs, mat, r1, chamfer)`, `pin(...)` | block, cylinder or cone between two points, chamfered cross pin |
| `plate(name, outline, thick, origin, u, v, w, holes, mat, w0, bevel_w, slots)` | flat plate with round holes `[(cu, cv, r)]` and slots cut through |
| `loft(name, sections, mat, caps, closed)` | skin rings of equal point count |
| `tube_path(name, pts, radius, segs, mat, closed)`, `band_path(name, pts, width, thick, normal_fn, mat, closed, offset)` | round wire or flat strap along a polyline |
| `ring(name, origin, axis, R, r, ...)` | torus (O-ring, wire loop), `arc=` for an open one |
| `rounded_rect(w, h, r)`, `stadium(length, width)`, `circle(r, seg)` | 2D outlines for `prism` and `plate` |
| `bezier(p0, p1, p2, p3, n)`, `chaikin(pts, it, closed)`, `resample(pts, n)`, `helix(origin, axis, ref, radius, pitch, turns)` | point lists for paths |
| `boolean(target, cutters, op)`, `bevel(o, width, segs, angle)`, `shade(o, angle)`, `subdivide(o, cuts)`, `displace(o, fn)` | cut, break edges, smooth-shade with sharp angles, dent or bend |
| `join(name, objs)`, `duplicate(o, name)`, `mirror(o, axis, about)` | assemble, copy, mirrored copy |
| `set_origin(o, point)`, `set_frame(o, M)`, `transform_obj(o, M)` | move the node origin or frame without moving the mesh; move the mesh |
| `tris(o)`, `solid_check(o)`, `clean(o)`, `fill_holes(o)`, `triangulate(o)` | counts and repairs |

### `am_parts.py` (import as `AP`): small mechanical parts, real geometry

Every part is built in its own frame (origin at the seat, +Z out of the hole or along the axis) and placed with
`at=`, `axis=`, `ref=`.

| Function | Notes |
|---|---|
| `screw(name, d, length, head, drive, head_d, head_h, mat, thread, thread_len, pitch, ...)` | heads `pan cheese dome hex csk socket none`; drives `slot cross hex none`; a real helical thread over `thread_len` |
| `rivet`, `washer`, `nut`, `tube` (bush, spacer), `circlip` (with plier holes), `solder_blob` | |
| `knurled_band(name, d, length, n, depth, ...)` | straight knurl as geometry, optional bore |
| `hinge(name, length, r_pin, r_knuckle, n, ...)` | returns `(knuckles_a, knuckles_b, pin)` on one axis; join a and b to their leaves, the pin is its own part |
| `spring(name, length, d_coil, d_wire, turns, ...)` | compression spring with closed ends |
| `wire(name, pts, d, mat)`, `lead(name, pts, d_sleeve, d_core, strip0, strip1, ...)` | round wire; sleeved lead returning `(sleeve, core)` with bare ends |
| `clip(name, width, t, r, ...)` | sheet spring clip for a round lead |
| `hole_cutter(d, depth, at, axis, csk)` | cutter for `G.boolean`: a screw hole opening at `at` |
| `frame_matrix(at, axis, ref)`, `place(o, at, axis, ref)` | frames |

### `mats.py` (import as `MT`): procedural authoring materials

`MT.library()` is the shared palette (`F.mats`): `steel steel_dark steel_blued steel_rusty steel_bright alloy
alloy_sheet alloy_cast anodized stainless brass brass_dull copper solder paint_orange paint_olive paint_bone paint_grey
rubber polymer plastic_cream wire_orange wire_black wire_red wood leather tape canvas paper ceramic glass_dark led_cyan
led_amber core_fluid`, and `glass` (a passthrough).

`MT.make(name, base, metal, rough, var, edge, dirt, rust, bumps, emit, tone2, wipe, ...)` makes your own: worn edges,
cavity grime, rust, bump patterns (`noise lathe stipple brushed grain weave pores knurl`), emission, and `wipe=` for a
surface that is cleaned on the bench (`dust`, `corrosion`, `film`, `all`). `MT.passthrough(name, color, alpha, ...)`
is a constant material that is not baked (glass); each one is a draw call. No baked light: base colour is albedo
only. Stone, cloth, rubber, wood and dust are not metallic.

### `contract.py` (import as `CT`): the contract in code

`part`, `fastener`, `tool`, `update`; helper empties `clear`, `clear_along`, `grab`, `tip`, `mark`, `seat_pose`,
`path` (8 to 40 points), `zone` (a box: the empty's scale holds the half sizes); `wipe`; `sequence` (the order things come off and go
on); `absent` (parts in the GLB that are not there at the start of the job); `build_hierarchy`, `validate`, `write`.
`parts.json` follows CONTRACT.md and adds, all optional for the reader: `unit_scale_m`, `sequence`,
`absent_at_start`, per part `flex` / `loose` / `rides` (the parameter a part moves with) / `note`, per parameter
`bone`, `parent_bone`, `requires`, `parts`.

**Seats for another family's part (SEAM.md section 2, added 20 Nov 17:45).** `CT.mark(o, 'seat_x', point, normal)` is
a point: +Z along the normal, no heading. Where the orientation matters and you know it, use
`CT.seat_pose(owner, 'x', matrix, accepts=['pistol.frame'])`: it writes `<node>__mark_seat_x` with a full world pose
(the resting part's node takes that transform) and `"pose": true` plus `accepts` on the mark's entry in `parts.json`.
To find the matrix, bring the other family in as for a check render (`check.load_external(blend)`), stand the part
where it should rest and read its `matrix_world`.

Empties: `<node>__clear` is a sibling of the node (same parent); every other helper is a child of the node. For a
part that rides a rig bone the `__clear` empty hangs on the part's contract parent, so it stays put when the
parameter moves.

### `rig.py` (import as `RG`): 0-1 parameters

`R = RG.Rig(family, parent=obj)`, `R.hinge(param, origin, axis, min_deg, max_deg, parts, parent=None, requires=None)`,
`R.slide(param, origin, axis, min_m, max_m, parts, ...)`, `R.continuous(param, origin, axis, parts, parent)`,
`R.finish()`. Set `F.rig = R`. The armature node is `<family>_rig`; bone +Y is the joint axis; parameter 0 is the
as-found pose. `F.finish()` bakes `<param>_param` (one second, linear, 24 fps) and strips every other bone from each
clip, so sampling one clip never resets another parameter. Continuous joints get a bone and extras, no clip.

### `bake.py` (import as `BK`): atlas and export

Called by `F.finish()`. `unwrap` (one atlas, `F.uv_weights = {'node_name': 1.4}` for more texels on a hero part),
`bake` (Cycles CPU; `color`, `normal` OpenGL +Y, `orm` glTF packing, `emit`), `assign_runtime` (`M_<family>` and
`M_<family>_emissive`), `export_glb`, `filter_animations`, `glb_summary`. Parts whose material has `wipe=` get a
second set on the same UVs in `export/tex/<family>__dirty_{color,normal,orm}.png` (one shared file per family, listed
under each part's `wipes`).

### `check.py`: the machine checks

Contract, parameter sweep (50 steps, overlaps against everything not on the bone, clamping), assembly path sweep
(every `sequence` event in 40 steps against what is there at that point), fastener holes and head contact, GLB
re-import (nodes, triangles, bounds, helpers, clips, end poses). `check.main(family_dir, externals=[(dir, ids[, 'absent'])])`.
A family is not copied to Unity with a failing `check.json`.

### `review.py` (import as `RV`): renders

`studio`, `six_views` (left, right, front, back, top orthographic at one scale, plus a three-quarter), `bench_cam`
(40 degrees down, 0.6 m, 35 mm), `close_cam` (0.3 m), `explode` (parts moved to and past their `__clear` poses),
`render_family`, `contact_sheet`, `beside(sheet, renders, out)`. As a script it writes `<family>/review/` and, when
`<family>/sheets/overall.png` exists, `review/compare_overall.png` with the sheet on the left.

### `measure.py` (import as `ME`): holding a build to a skin

`bounds`, `silhouette` (a mask of the projection in `side`, `top` or `front`), `compare_masks` (IoU, differing area,
largest deviation in mm), `save_mask_png`, `fit_circle`, `section_ring`.

## Changed on 20 November, 18:00 to 20:45 (read this before you rebuild)

Nothing here changes a family's geometry, node names or `parts.json` ids. A rebuild or rebake picks these up:

| Change | What you will notice |
|---|---|
| **Shared colours are constants** (SEAM.md section 8, corrected 19:20): `MT.WARDEN_ORANGE` = linear (0.60, 0.20, 0.076), `MT.BARE_ALLOY` = linear (0.30, 0.285, 0.265) with `MT.BARE_ALLOY_ROUGH` = 0.6; `MT.from_linear(c)` turns a linear albedo into the sRGB triple `MT.make` takes. The library's `paint_orange` reads them. (Between 19:10 and 19:45 the orange constant held an interim value; nothing should have been baked with it.) | Use the constants or the library `paint_orange`, never a typed triple. The bare alloy under the paint is now a dull dark grey-brown; the first value read as white paper. |
| **Flaked paint**: `MT.make(..., flake=(colour, metal, rough, coverage[, noise scale]))`: paint gone in large irregular patches with a ragged coast (0.3 to 0.5 for old Warden paint), more along worn edges, the bare patch a paint-thickness lower. `paint_orange` has it at 0.38. | Paint no longer wears only along edges. |
| **THE REVIEW RIG WAS ABOUT 1.4 TO 2.2 EV TOO BRIGHT, FIXED 19:45.** `review.studio()` now takes its energies from `review.RIG`, set with `kit/calibrate_rig.py` so that a white diffuse card (albedo 0.8) reads 0.83 to 0.90 in scene-linear whichever way it faces (it read 2.3 under the neutral rig and 4.0 under the warm one: `kit/rig_calibration_before.json`). Neutral: key 19.5 W, rim 10.5, fill 5, sky 0.43. Warm: key 16.6 W at 3000 K, rim 3, fill 3, and warm surroundings (1.0, 0.84, 0.66) at 0.336, a fifth of the light where they were 3 %. No exposure offset is used: leave `view_settings.exposure` at 0. | **Every colour judged on a render made before 19:45 is void: re-render.** Bright albedos keep their hue (the orange is orange, not salmon); metals read darker than before, because they were being judged on a blown-out frame. If you set an exposure of -1.6 or -2.2 as the interim rule said, take it out. |
| **Exposure cards in every frame**: `review.render()` puts a white (albedo 0.8) and a mid-grey (0.18) diffuse card in the bottom left corner, facing the camera. Each **stands on whatever is seen at its place in the frame** (a ray from the camera finds the ground, the bench or the part, and the card is set just clear of it), so nothing hides it and it is lit as the scene is there; where the ray meets nothing it floats at the subject's depth. They cast no shadow and are not in reflections. `review.CARDS = False` turns them off. (Until 20:40 they sat at the subject's depth and sank under a ground plane in oblique views.) | Read the exposure off any sheet: under AgX the white card is about sRGB (180, 165, 150) in a warm frame where it faces the lamp, and must never be flat white; the number that is calibrated is 0.9 in scene-linear. If you render with your own script, call `RV.render()` or `RV.cards(cam)` to get them. |
| **Warm key**: `review.py --warm` (and `build.py -- --review --warm`): the bench's one warm work lamp. Files get the prefix `warm_`. | Judge colours under this one; the neutral studio stays the default for comparing shapes with a sheet. |
| **`review.py --glb` frames on the family's parts only** (defect c): the importer's bone-shape meshes (a 1 m icosphere) were in the bounds, so the six views showed a speck. | Re-run `review.py --family X --glb` if your `glb_*` sheets were made before 17:57. |
| **A parameter may rest away from 0** (defect a, SEAM.md section 7): a joint whose range starts below 0 gets `rest` = where 0 degrees or 0 mm falls in 0..1; `Rig.finish()` puts every property at its rest before it parents parts to bones, and `rest` is written to the GLB extras and `parts.json` `params[]`. | A hinge from -12 to +12 degrees is modelled in its middle pose and reads `rest: 0.5`; no hand parenting needed. Ranges that start at 0 are unchanged. |
| **`check.py` holds the other parameters at their rest**, not at 0, while it sweeps one; and **resets the pose between clips** when it samples the re-imported GLB (defect b: a clip left its end pose behind for the next one). | Fewer false overlaps on a second rig; an export check that failed only on the second clip now passes. |
| **Atlas margin is capped** at 0.25 % of the atlas (defect d): 4 px at 2048, about 1.3 px at 512. | `--size 512` test builds with thousands of small islands no longer collapse. A 2048 or 4096 bake is unchanged. |
| **Pose marks**: `CT.pose_mark(owner, id, matrix, accepts=[...])` writes `<node>__mark_<id>` as a full pose (`"pose": true` in `parts.json`). `CT.seat_pose` is the same with the `seat_` prefix. | Use a pair (`seat_x`, `clear_x`) for a part of another family that seats on yours. |
| **Sweeping another family's part**: sequence events take `'seat'` and `'clear'` (two pose marks to sweep between; the part then rides the owner of the mark), `'unit': True` (its riders come with it), `'among': [families]` (only these are in the way) and `'expect': [ids]`. Externals take a third field: `externals=[('../servo', [ids], 'absent')]` = loaded, but not in place until your sequence inserts them. | See `grip/build.py` and `grip/check.py`: the servo's gimbal unit and case screws into the grip core. |
| **Stand-ins**: a mesh registered under another family's id (`CT.part(o, 'materials', 'sheet_a_plate', ...)`) stays in your `.blend` for sweeps and renders, is not exported, not baked and not in `parts.json`; the check treats it as that family's part, absent at the start. | For a part another family owns but has not built yet. |
| **`G.boolean` is stricter and says more**: a fallback solver that refuses the mesh (MANIFOLD on a target that is not closed) leaves it untouched, and that no-op used to pass the volume test: it is now rejected and the next solver is tried. After every cut that leaves the target open it prints `[geo.boolean] after DIFFERENCE of X the target Y is not a closed solid: n open edges ...`. | A build that silently skipped a cut now makes it or stops. A line like that followed by a clean `solid_check` at the end is fine (the final `heal` closed it); if the part ends open, the named cutter is where to look (coplanar faces are the usual cause: let the cutter overshoot). |
| **A loose part of another family is not in the way** of a sweep (a test card lying by the pistol stopped the grip's core). | Only matters for checks with `externals`. |
| **Triangulation cannot fold a face** (materials' defect 1): `G.triangulate` (called by `Family.finish()`) still uses BEAUTY, but first finds the faces BEAUTY would fold (a triangle facing against its face, seen as a hole from one side) and ear-clips those. It prints `[geo.triangulate] X: n face(s) ear-clipped ...` when it does. | Triangles are unchanged except on a face that was coming out wrong. A local `tri_safe` work-round can go. |
| **`G.bevel` says when the clamp will eat the bevel** (defect 2): with `clamp=True` (still the default, so built families do not change) Blender limits the bevel of the whole part so that no two bevels overlap, and one short edge at a bevelled corner shrinks it everywhere. `[geo.bevel] X: the shortest edge at a bevelled corner is 0.30 mm, under twice the bevel width ...` is printed when that is about to happen. | Pass `clamp=False` (keeps the width; check the corners) or weld the short edge. A plate outline with eased corners needs it. |
| **Kit modules load each other by file** (defect 3): `kit/kitload.py`, `kitload.load('check')`. A family's own `check.py`, `review.py` or `measure.py` ahead of `kit/` on `sys.path` was imported in place of the kit's (`import check` ran another family's script). `Family.finish()` now gets `review` and `review` gets `measure` through `kitload`. | In your own scripts: put `kit/` on the path, then `import kitload; check = kitload.load('check')` (same for `review`, `measure`). `import check` only works while nothing else named `check.py` is ahead on the path. `grip/check.py` and `kit/example/check.py` show it. |
| **The clamp test compares with the pose at 0** (servo's defect 6): it compared the pose at -0.5 with the rest pose, which failed any parameter resting at 0.5. | `servo/check.py`'s local fix can go. |
| **Islands can be turned square before packing**: `F.uv_align = True` (or `BK.unwrap(..., align=True)`) turns every UV island to its smallest bounding rectangle first. The packer packs boxes and only makes quarter turns, so a big face lying at an angle in its projection wastes half its box. Off by default. | Worth trying when `uv fill` is under 0.4 and the part has large slanted flats (the grip's side faces lie at 25 degrees). It moves the atlas, so rebake. |
| **`CT.zone` cannot export a mirrored box**: a `rot` whose axes are left-handed came out of the GLB as a negative scale (Unity read the grip's seam zones as -120 x -120 x -4 mm). The zone now turns its third axis round (the box is the same) and takes the half sizes as positive. | Rebuild a family whose zones were given a hand-typed `rot`; nothing else changes. |
| **`kit/publish.py` keeps the folder of extra files** (defect 4): `python3 kit/publish.py grip tex/grip__dirty_color.png ...` lands them in `Art/Bench/Grip/tex/`, the path `parts.json` gives under `wipes`. | Before, extras were copied flat. |
| `kit/selftest.sh`: the example family builds, bakes at 512 and passes its checks. `kit/calibrate_rig.py` (`SH/run.sh kit-cal bash kit/run_calibrate.sh`) measures the review rigs. | `SH/run.sh kit-selftest bash kit/selftest.sh` after any kit edit. |

## Not in the kit

LODs (the bench is LOD0 only), collision meshes, Unity materials. The Unity installer reads `parts.json`.
