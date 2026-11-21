# Brief: `model-pistol-surface` — the rebuilt scrap pistol's surfaces and its 4096 bake

Written 20 November 2026, 18:05. `model-pistol` rebuilt the scrap pistol as 22 separable parts that pass every
machine check and match the old pistol's outline. Its geometry is accepted. Its surfaces are not at the bar: the
steel is pale, even and flat, the brass is clean yellow, the wood is light, and at 2048 the texel density is 34 px/cm
against a contract of 60. You do the surface pass and the final bake. `model-pistol` has moved on to the grip family.

The pistol is the object the player holds the camera on for seventeen minutes at 0.3 m, and then carries. It is the
hero prop of the whole programme.

## Read first, in this order

1. `../AGENT-RULES.md` (binding: machine limits, wrappers, spending, reporting).
2. Pictures, opened with your own eyes: the accepted look target `../concept/bench_overview_fal.jpg` (the pistol in
   the middle: dark, oily, worn steel under one warm lamp; Carl's reaction to this picture was "that image looks
   sick"), `../pistol/sheets/look.png`, `../pistol/sheets/overall.png`, `../pistol/sheets/exploded.png`. Then the
   present state: `../pistol/review/glb_close.png`, `glb_close_rear.png`, `glb_bench.png`, `glb_exploded.png`.
3. `../pistol/build.py` and whatever it imports, `../pistol/export/parts.json`, `outline.json`, `check.json`,
   `stats.json`, and the pistol's PARTS file.
4. `../kit/READY.md` (the build kit: geo, mats, bake, check, review, measure) and `../kit/mats.py`.
5. `../servo/sv.py` and `../servo/README.md`: how another family built its own paint, dust and wear layers in a
   local module without editing the kit. Do the same (`pistol/px.py` or similar).
6. `../SEAM.md` section 8 (shared colours; judge under a warm key) and `../CONTRACT.md` section A (budgets, texel
   density, the as-found texture set).

## What you own

`art/steady_hands_bench_20261120/pistol/**` and `unity/AthenHill/Assets/AthenHill/Art/Bench/Pistol/**`. Not the kit
(`kit/**` is `model-pistol`'s: if you need a kit change, work round it locally and say so; a kit defect that blocks
you goes in PROGRESS.md). You do not run Unity.

## What must not change

Node names, parents, part ids, marks, paths, params, clips, the helper empties, `parts.json` ids and structure, and
the outline: re-run the outline comparison and stay inside the numbers recorded in `export/outline.json` (bounds
within 0.6 mm, bore axis, mod rail face, hand points). The interaction system, the other five weapon mods and the
hand poses all hang on these. `check.py` must pass on the final baked export exactly as it does now.

## What to do

1. **Steel** (frame, receiver, cover plates, barrel collar, guard, trigger, sights, fasteners). The target is old
   blued or parkerised steel that has been carried for years: dark overall, worn to bright metal on edges, corners
   and where the hand and holster rub, brown rust in inside corners, under screw heads and along seams, grime and old
   oil in recesses, scratches and file marks that follow how each part was made, a few dings. Different parts are
   different steels (the receiver, the cover plates and the barrel collar should not be one grey). Roughness varies:
   oily and smoother where handled, dry and rough where rusted. No even procedural blotching.
2. **Form where it reads as cut-out plate.** The frame's flanks and the trigger guard look like flat sheet with razor
   edges. Give edges real bevels and the guard a stamped or forged section, within the outline tolerance and the
   triangle budget (31.8k of 45k used). Shade last, as the kit notes say.
3. **Wood** scales: darker, oiled, dirt in the grain and round the screw, the crack as a real dark split, worn pale
   only on the high edges.
4. **Leather, tape and wire** of the wrap: creased leather with darkened edges and stitch holes, cloth tape with a
   visible weave and frayed ends, copper wire dulled with a little green in the twists. The wrap should look tight
   and hand-done, not tidy.
5. **Brass** (cell caps, latch pawl, terminal plate, knurled nut): tarnished brown-gold with bright wear on the
   knurls and edges, not clean yellow.
6. **Cell and lamp**: dirty glass with a clean rubbed band, the cyan core as the one cool light on the bench (check
   the emissive value survives export; say what it is). Butt plate: the shared Warden orange of `SEAM.md` section 8,
   chipped in ragged patches.
7. **As-found set**: if the pistol has no `__dirty` texture set yet, it does not need one for the whole pistol (it
   is not brushed clean on the bench); say what exists.
8. **Density**: bake at 4096 for `pistol.glb`. Before baking, recover atlas space if it is cheap (the report says
   wires and straps are projected rings that waste the atlas). `pistol_hand.glb`, the copy the player carries,
   keeps a 2048 set made from the same bake.
9. **Review**: render at 0.3 m and at the 0.6 m bench camera, under a warm key (about 3000 K, one lamp above and in
   front, soft contact shadow on a black rubber mat) as well as the neutral rig, beside the look target and the
   sheets. The kit's `review.py --glb` frames a rigged GLB as a speck (a known kit defect, being fixed by
   `model-pistol`): frame on the mesh bounds yourself if the fix has not landed. Open every sheet yourself and say
   honestly where it still falls short of the target.
10. **Publish**: `check.py` PASS on the baked export, `outline.json` re-run, copy `pistol.glb`, `pistol_hand.glb`
    and `pistol.parts.json` to `Art/Bench/Pistol/`.

Work in small steps you can see: geometry builds with `--nobake` take seconds; a 4096 bake is about eleven minutes,
so bake once at 1024 or 2048 to judge the look and at 4096 only at the end.

## Spending

fal `--tag model-pistol-surface` (cap $3) for material close-up references if you need them (worn blued steel,
oiled walnut, tarnished brass): ask for surfaces and generic hardware, not for weapons; if a service refuses a
prompt, stop and report, do not reword. Grok and OpenAI routes as in AGENT-RULES. No Meshy.

## Machine

One Blender slot is shared by five agents this evening and about 13 GB of RAM is available. Keep slot uses short,
use `SH/run.sh` + `SH/wait.sh` for bakes, and never start Blender outside the wrappers.

## Milestones and report

1. Look settled at a low-resolution bake, review sheets under the warm key opened and compared. PROGRESS line.
2. 4096 bake, checks, publish. Hand back.

Report as AGENT-RULES says: outcome first; what changed and what did not; check and outline results; what you saw
and where it still differs from the target; triangles, texel density and atlas fill; open defects; spend.
