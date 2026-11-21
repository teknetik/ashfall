# Tools and fixtures families: how they are built (model-bench)

Steady Hands bench programme, 20 November 2026. This file covers both of `model-bench`'s families; the breakdowns are
`tools/PARTS.md` and `fixtures/PARTS.md`, the bench layout is `fixtures/layout/` (`layout.json`, `layout_plan.png`).

## Run

`SH` is `~/.local/state/ward-programme/steady-hands-20261120`. Everything goes through the Blender slot.

```
python3 fixtures/src/gen_masks.py                          # mask images for the mats (ImageMagick, seconds)
$SH/blender.sh $PWD/fixtures/build.py -- --nobake          # geometry, parts.json, stats.json, export/fixtures.blend
$SH/blender.sh $PWD/tools/build.py -- --nobake
$SH/blender.sh $PWD/fixtures/check.py                      # machine checks -> export/check.json, exit 1 on failure
$SH/blender.sh $PWD/tools/check.py
$SH/run.sh mb-fx $SH/blender.sh $PWD/fixtures/build.py -- --size 2048 --spp 24 ; $SH/wait.sh mb-fx     # the bake
$SH/run.sh mb-tl $SH/blender.sh $PWD/tools/build.py -- --size 2048 --spp 24 ; $SH/wait.sh mb-tl
$SH/blender.sh $PWD/tools/src/review_mb.py -- --family fixtures [--only vise,dish] [--shots views,close,bench,lamp] [--quick] [--glb] [--warm]
bash tools/src/rebake_all.sh                               # both bakes, checks, publish and every review sheet, in three slot holds
python3 tools/src/publish.py fixtures tools                # copies a checked, baked family to Assets/AthenHill/Art/Bench/<Family>/
```

`rebake_all.sh` puts several Blender runs into one hold of the slot (`SH/slot.sh bash -c ...`), because on 20 Nov
each wait for the slot took 5 to 20 minutes with seven agents queuing; start it with `SH/run.sh`.

`--only a,b` builds a subset (fixtures only). `--size N` sets the atlas size of every set.

## Files

| File | What |
|---|---|
| `tools/src/mbk.py` | shared layer over the kit: `BenchFamily` (several rigs and several texture sets per family, hand-laid UV sets), placing from `layout.json`, helper empties in an object's own frame, seat marks, material layers (`Tap`), the skinned-rig and scale-rig helpers |
| `tools/src/tl_mats.py`, `tl_parts.py`, `tl_roll.py`, `tools/build.py` | the tools family |
| `fixtures/src/fx_mats.py`, `fx_parts.py`, `gen_masks.py`, `fixtures/build.py` | the fixtures family |
| `tools/src/check_mb.py`, `<family>/check.py` | the checks (kit `check.py` functions, ordered for several rigs and a skin) |
| `tools/src/review_mb.py` | review renders and the compare sheets |
| `fixtures/src/probe_bench.py` | the probe of the existing Meshy bench (read-only) |
| `tools/gen_sheet.py`, `gen_overall.sh`, `gen_close.sh` | reference sheets (OpenAI `gpt-image-2`) |

## What the kit did not cover, and how it is handled here (the kit is not edited)

- **Several rigs in one family.** The kit has one rig per family. Here every object with a mechanism has its own rig
  parented to its root node (`BenchFamily.new_rig` / `end_rig`), with parameters named `<object>_<param>`. The scene
  keeps the joints of every rig in `sh_rigs`; the check runs the kit's parameter sweep once per rig.
- **A skinned mesh** (the roll) and **a scale joint** (the dropper's bulb): `mbk.new_armature`, `bake_pose_action`,
  `scale_rig`. Their clips are baked before the source `.blend` is saved, so review and check sample them.
- **Two texture sets per family**: `F.set_of[node] = 'a' | 'b'`. Fixtures set `a` (the mats) is laid out by hand
  (`fx_parts.uv_mats`); everything else is the kit's smart-project and pack. Textures: `export/tex/<family>_<set>_*.png`,
  runtime materials `M_<family>_<set>`.
- **Seat marks**: `<node>__mark_seat_<id>` are marks that carry a whole pose.

## Shared colours (SEAM.md section 8)

Linear albedo of the paints other families take from here. They are constants in `fixtures/src/fx_mats.py`
(`VISE_GREEN_LINEAR`, `PRESS_YELLOW_LINEAR`); `MT.make` takes sRGB triples, so pass `MT.from_linear(...)`.

| Material | Albedo, linear RGB | sRGB triple | Where | State |
|---|---|---|---|---|
| Vise green (cast-iron machine paint) | (0.020, 0.036, 0.018) | (0.152, 0.209, 0.143) | `vise_green`, `vise_green_slide`: roughness 0.48, stippled casting, chips to bare iron (sRGB 0.50, 0.48, 0.455, metal) with a rust-brown lip | built and baked on 20 Nov after the re-tune below |
| Press yellow | (0.36, 0.21, 0.040) | (0.64, 0.50, 0.22) | planned for `fixtures.press` (Milestone 3); worked back from the look target with the orange plates as the reference | **provisional**: nothing is built with it yet |

**Re-tune of 20 Nov, 19:40.** Every albedo of both families was first judged under the kit's review rig while it
was about 1.6 EV too bright, and was one to two stops too dark (tool steel at linear 0.045, canvas at 0.07, the vise
green at (0.0125, 0.0316, 0.0163)). All of them were raised and both families re-baked; the values now in
`fx_mats.py` and `tl_mats.py` were judged at a calibrated exposure against `concept/bench_overview_fal.jpg`.
The copies of the two files as they were are in the programme state folder (`model-bench-backup/*_1811.py`).

**Light of the review sheets.** `review_mb.py` measures a white card (albedo 0.8) beside the subject before each
rig is used and writes the numbers to `review/exposure.json`. Object sheets (`*_views.png`, `*_close*.png`,
`*_compare.jpg`): the kit's rig as re-lit at 19:46, neutral unless the file name has `warm_`, with the kit's white and
grey cards in the bottom left corner. Bench sheets: `glb_bench_studio.png`, `glb_bench_wide_studio.png` and
`glb_bench_plan.png` under the kit's neutral rig; `glb_bench_lamp.png` and `glb_bench_wide_lamp.png` under one 3000 K
pendant over the mat in a sandstone-coloured room, exposed so that a white card lying on the rubber reads 0.9
(largest channel). The two cards lie on the rubber between the vise and the work mat. Judge colour on the lamp
sheets and the `warm_` sheets. One exception: the four `tools/review/glb_warm_dropper_*` files are 1.04 EV brighter
than the rest (noted in `exposure.json`).

## Parameters at rest (SEAM.md section 7)

Every parameter of both families rests at 0, which is the as-found pose: vise open, tool jaws closed, bit collar
locked, dropper bulb full, roll rolled up and buckled. `parts.json` gives `rest` on every param. The roll's skin
is bound flat (`bind_pose_value`: unroll 1.0, strap 0.6), so a roll shown with no clip sampled is the unrolled
one: sample both clips at the param's value, 0 at the start.

There is no as-found (dirty) texture set for either family and no part has `wipes`: nothing here is cleaned in the job.

## Provenance

- Geometry: written here, on the programme kit (`../kit`, by `model-pistol`; parts of it follow AnyMachine, MIT, see
  the notice in `kit/am_parts.py`). AnyMachine itself was read, not run.
- Reference sheets: OpenAI `gpt-image-2`, prompts beside each image in `sheets/*.prompt.txt`, usage in
  `sheets/prompts.json`. 11 images on 20 Nov 2026 (8 overall sheets, 3 close-up sheets made from their overall sheet).
- Look target: `../concept/bench_overview_fal.jpg` (the orchestrator's).
- Existing bench: `unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Props/SS_Workbench/` is read for the probe and the
  layout renders and is not changed.
- No Meshy generation, no fal, no ElevenLabs. Meshy credits spent: 0 of the 240 allowed.

## model-tools, from 21 November 2026

`model-tools` took the tools family over from `model-bench` on 21 Nov (brief `../briefs/model-tools.md`). New files,
so `mbk.py`, `check_mb.py`, `review_mb.py` and `publish.py` (shared with the fixtures) keep their behaviour:

| File | What |
|---|---|
| `src/tl_kit.py` | helpers: lofts along a path (handles, shafts, tufts), lap-jointed scissor halves v2, face gear and pinion, crocodile clip, `frame_mat` (a tilted tool's materials read the modelling axes) |
| `src/tl_mats2.py` | materials of the new tools: forged black-oxide steel, bright ground steel, blued steel, nickel plate, cast iron, file steel with double-cut teeth, turned wood with scribed rings, cork, cloth lead, brass bristle, ceramic, nanite paste, cloth tape, red dip |
| `src/tl_new.py` | the eleven new tools (below) |
| `src/review_tl.py` | review renders per tool: top view as the sheet, two 0.3 m views, rigs posed, crop of the sheet beside (`review/mt/`) |

`build.py` takes `--size-a N --size-r N --size-b N` (one set's atlas) and `--reuse-sets r,b` (keep those sets' last
bake, so a long bake can be split over two slot holds).

**Texture sets from 21 Nov:** `a` = every carried hand tool (the toolkit's tools and Brann's mallet, files, snips, drill,
iron, applicator, dropper), `r` = the roll, `b` = what stands on the bench (oil bottle, iron stand, solder reel, third
hand). Runtime materials `M_tools_a`, `M_tools_r` (new), `M_tools_b`.

### The eleven new tools (ids and tags as the brief)

| Id | Tag | Built | Rig / helpers |
|---|---|---|---|
| `tools.strippers` (+ `strippers_b`) | `tool:strippers` | lap-jointed forged halves, five gauge notches, return spring, stop screw with locknut and knurled head, two lightening holes | `tools.strippers_jaws` 0 closed (as found) .. 1 open 28 deg; `__tip`, `__grab`, `__clear`; roll seat `seat_strippers` |
| `tools.wirebrush` | `tool:brush` | curved beech handle with hanging hole, head with 29 brass tufts in three rows; lies on its side in its pocket | `__tip` on the bristle face, +Z out of the bristles |
| `tools.pick` | `tool:pick` | nickel handle with diamond knurl, tapered shaft, hooked end | `__tip` at the hook |
| `tools.scribe` | `tool:scribe` | knurled nickel body, hardened needle, pocket clip with a ball end | `__tip` at the point |
| `tools.file_flat` | `tool:file` | 250 mm double-cut flat file, brass ferrule, turned handle with two scribed rings | `__tip` at the blade's end |
| `tools.file_round` | `tool:file_round` | 220 mm rat-tail file, same handle | `__tip` |
| `tools.snips` (+ `snips_b`) | `tool:snips` | forged blades, pivot bolt with a domed head and nut, one handle curled into a finger loop | `tools.snips_jaws` 0 closed .. 1 open 22 deg |
| `tools.drill` (+ `drill_wheel`, `drill_spindle`, `drill_chuck`, `drill_bit`) | `tool:drill` | eggbeater: mushroom knob and turned handle, cast frame with two rails and a bridge, 90 mm wheel with 60 face teeth and five curved spokes, crank and wooden knob, 12-tooth pinion, knurled chuck with three jaws, 3 mm twist bit | `tools.drill_crank` (continuous, wheel), `tools.drill_spindle` (continuous, spindle + pinion + chuck + bit, 5 turns per crank turn: param field `ratio`), `tools.drill_chuck` 0 tight (as found) .. 1 turned back 150 deg; `drill_bit` has `__clear` 45 mm out; mark `crank_knob` |
| `tools.iron` (+ `iron_stand`, `solder_reel`) | `tool:solder` | cork grip with grooves, heat guard, barrel and knurled nut, chisel copper tip tinned at the end, strain-relief spring, cloth lead coiled and tied under the butt; stand: cast plate with a tray, coil cone, V rest; reel with flanges and a free end | iron exported in its stand; stand mark `seat_iron` (pose) |
| `tools.applicator` | `tool:applicator` | alloy barrel, sight window with grey nanite paste (faint cyan crawl, the only cyan), ribbed thumb slider, brass collar, ceramic nib, pocket clip | `__tip` at the nib |
| `tools.thirdhand` | (kind fixture) | cast base, post with clamp block and thumb screw, cross bar, two ball-jointed arms with wing joints, two crocodile clips in front of the post | pose marks `seat_lead_l`, `seat_lead_r` (the clip mouths), `seat_resistor` (between them, 95 mm up, 32 mm in front of the post) |

### Departures (model-tools)

- Brann's new tools are exported at their places in `fixtures/layout/layout.json` (as the mallet and the oil bottle
  already were), not at the origin as the brief says: the bench's `place.rest.<tool>` takes the part's own pose in its
  model, so a tool at the origin would sit under the screen foot. No fixture mark is needed for them.
- The iron stand lies along Y (iron tip away from the player), not along X as its layout size suggests: along X its
  tip reaches the salvage tray (tip toward -X) or leaves the worktop (+X).
- The third hand's clips stand 32 mm in front of its post (else the post is where the resistor would be held); its
  `seat_resistor` mark is at (0, -32, 95) mm in the third hand's own frame, not the stand-in's (0, 0, 95).
- Extra ids beyond the brief's eleven: `drill_wheel`, `drill_spindle`, `drill_chuck`, `drill_bit`, `iron_stand`,
  `solder_reel`, `strippers_b`, `snips_b`, and the param `tools.drill_spindle`.

### Milestone 3: the hero rebuild (21 Nov)

`src/tl_hero.py` rebuilds model-bench's slice tools with the same working points (tip, bit socket, pivot at the
origin, `y_tip`), so `tl_parts.finish_*`, the rigs, the roll's seat marks and every helper empty land where they were:
- pliers: lofted forged handles under black cloth friction tape (wound ridges, palm wear, oil sheen), serrated jaws
  with pipe grip, the owner's punched triangle; cutters: lofted handles in red dip worn through to steel, bright blades;
- screwdriver: darker polished handle with two pairs of scribed rings, brass ferrule, bright shaft, nickel collar with
  a diamond knurl; bits forged with bright tips; bit block bevelled beech;
- punch: blued octagon with a knurled band, forged mushroomed head, bright pin;
- mallet: tapered hickory handle in black cloth tape (the old one pinched to a neck where tape met wood), cool steel
  barrel with two bands, brass and rawhide faces.

The roll (`src/tl_roll.py`): olive-brown waxed canvas (was orange-tan) with pale shiny wax patches, creases that run
along the roll's axis in the geometry, a raised bound edge with a darker binding, a larger sewn patch, a 3.4 mm strap
with five punched holes, a larger roller buckle. **The rig now has 80 segment bones (was 40)**, so the rolled end is a
smooth spiral; the bone names keep the pattern `roll_seg_NN` / `roll_flapa_NN` / `roll_flapb_NN`, the two params,
clips and every seat mark are unchanged (the marks hang on the segment bone under their pocket).

Steels (`src/tl_mats2.py`) are now distinct cool greys: forged black-oxide (handles, halves), bright ground (jaws,
tips, bits, shafts), blued (punch), nickel plate (pick, scribe, collar, chuck, third hand), cast iron (drill frame,
stands, bases), file steel.

**Hero publish, 21 Nov 11:44:** `Art/Bench/Tools/tools.glb` sha b8e062862ea03486, 136 MB (embedded PNGs), 74,044 tris of
80k, 34 parts, 11 params; sets a 4096 (fill 0.55, 60 to 84 px/cm), r 4096 (0.75, 44 px/cm), b 2048 (0.62, 36 to 59
px/cm), Cycles CPU bake at 16 spp, 24.5 min in one slot hold; `check.json` PASS. Meshy and fal: nothing spent (every
tool is built in Blender: slim forged tools, rigs and the bristles are where Meshy melts, so no trial was worth its
credits).

**Do not use `--reuse-sets` (21 Nov 12:00):** the UV packer is not reproducible from build to build (set a's fill came
out 0.539 against 0.546 for the same geometry), so a reused bake would sit on the wrong UVs. Bake every set together
(about 25 min at 4096 / 4096 / 2048, 16 spp).

**Roll fix round (21 Nov, after the orchestrator's review):** darker olive-brown canvas, coarser and deeper weave,
crease and sag displacement in the geometry (`crease`, `sag`, faded under the pocket strip by `bdef`), tool-shaped pocket
bulges with a crease across each, dark worn binding, khaki patch with a zig-zag stitch, hand grime at the pocket mouths and
the gripped end. Open: thin dark slits along the flap hinge (base and flap sag differently there).

**21 Nov 16:20:** emission map cut to 512 after the bake (`build.py`); the punch is 20 mm longer at the head end so it shows above its pocket (tip and seat unchanged).

**21 Nov 18:22:** pocket mouths lowered to y -0.045 (the bit block's to -0.100) so every tool shows above its pocket on the open roll; base crease and sag fade to flat under the seated tools. Check render: `review/mt/src_warm_kit_views.png`.
