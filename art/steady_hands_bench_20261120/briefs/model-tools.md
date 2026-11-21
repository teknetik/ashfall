# Brief: `model-tools` — the tools family, to hero quality and complete

Written 20 November 2026, 21:45. `model-bench` built the first set of tools (roll, screwdriver with two bits and bit
block, pliers, cutters, punch, mallet, oil bottle and dropper), checked and published. They work as parts but are not
at the bar: shapes are simple, the roll is a flat tan rectangle, texel density is 19 to 25 px/cm. Eleven more tools
are not built at all. You take over the whole `tools` family; `model-bench` keeps `fixtures`.

Tools are what the player holds for seventeen minutes, 0.3 m from the camera. They must look like one worn kit that a
salvager has carried for years, and like the reference sheets.

## Read first, in this order

1. `../AGENT-RULES.md` (binding: machine limits, wrappers, spending, reporting).
2. Pictures, opened yourself: the look target `../concept/bench_overview_fal.jpg` (the waxed canvas roll with re-taped
   tools, bottom right); the tool sheets in `../tools/sheets/`; the present state `../tools/review/glb_warm_*_compare.jpg`
   (sheet on the left, model on the right) and `../fixtures/review/glb_bench_lamp.png` (the bench they lie on).
3. `../tools/PARTS.md` and `../tools/README.md` (covers both families: rigs, the skinned roll, two texture sets, what
   differs from the sheets, kit work-rounds), `../tools/build.py`, `../tools/src/` (`mbk.py`, `tl_*.py`, `check_mb.py`,
   `review_mb.py`, `publish.py`, `rebake_all.sh`), `../tools/export/parts.json`, `check.json`, `stats.json`.
4. `../kit/READY.md` (the shared build kit; its review rig was fixed and calibrated at 19:46, exposure cards in frame).
5. `../SEAM.md` (names are fixed by the art; seat marks and pose marks; section 3, tools with bits; section 8, colours
   and the rule for review renders) and `../CONTRACT.md` section A.
6. `../DESIGN.md` section 4 (the Field Toolkit and Brann's bench tools) and section 7 for what each tool does.
7. `../bench/README.md` for how the interaction system binds a tool (tags, `__tip`, `__grab`, `__clear`, modes).

## What you own

`art/steady_hands_bench_20261120/tools/**` and `unity/AthenHill/Assets/AthenHill/Art/Bench/Tools/**`.
`tools/src/mbk.py` is also imported by `fixtures/`: do not change its behaviour; put new helpers in a new file. Not the
kit, not `fixtures/**`. You do not run Unity.

## Fixed, because the game logic is written against them

Every existing id, node name, parent, tag, param, clip, helper empty and seat mark in `tools/export/parts.json`
(`tools.roll` with params `tools.roll_unroll` and `tools.roll_strap`, `tools.screwdriver` with `screwdriver_collar`,
`bit_slot`, `bit_cross`, `bitblock`, `pliers` and `pliers_b`, `cutters` and `cutters_b`, `punch`, `mallet`,
`oil_bottle`, `oil_dropper` and its bulb). Parameter 0 is the as-found pose. `check.py` must pass on every publish.

New tools, with exactly these ids (the step table already uses them; say in PROGRESS.md at once if one must differ):

| Id (`tools.`) | Tag | What |
|---|---|---|
| `strippers` | `tool:strippers` | wire strippers with a stop screw; jaws param |
| `wirebrush` | `tool:brush` | long wooden-handled wire brush |
| `pick` | `tool:pick` | hooked pick |
| `scribe` | `tool:scribe` | scriber with a knurled grip |
| `file_flat` | `tool:file` | flat file with a wooden handle |
| `file_round` | `tool:file_round` | round file |
| `snips` | `tool:snips` | tin snips; jaws param |
| `drill` | `tool:drill` | eggbeater hand drill with `drill_bit`; params `crank` (continuous) and `chuck` |
| `iron` | `tool:solder` | soldering iron on a stand, with a coil of solder |
| `applicator` | `tool:applicator` | nanite applicator (a syringe-like bead gun) |
| `thirdhand` | `tool:thirdhand` | a weighted base with two clip arms |

The Field Toolkit tools have pockets in the roll (`tools.roll/seat_<tool>`); Brann's bench tools (mallet, files,
snips, drill, iron, oil, applicator, third hand) rest on the bench or its rack at marks `model-bench` owns: export
them at the origin with a sensible rest orientation and note in PROGRESS.md which fixture marks you need.

## What to do

1. **Judge what exists**, under the fixed rig's warm key at 0.3 m, beside the sheets. Write what you see in your first
   PROGRESS line.
2. **Rebuild or replace each tool to the sheet's form.** Forged, pitted, re-taped tools: knurled bands, a real pivot
   with a peened rivet, jaws with teeth, a turned wooden handle with scribed rings and a brass ferrule, black cloth
   tape on handles, worn red dip on the cutters. Different steels, not one grey.
   - **Rigged tools** (pliers, cutters, strippers, snips, drill, screwdriver with its collar and bits, third hand,
     the roll) are built in Blender with the kit: their parts move.
   - **Single-piece rigid tools** (punch, mallet, scribe, pick, files, wire brush, iron and stand, applicator, bit
     block, oil bottle) may be made with Meshy image-to-3D from crops of the sheets (the modelling tier and 4K PBR
     textures; record task ids and credits), cleaned in Blender, then given the contract's empties by measurement.
     Keep a Meshy piece only if it beats your Blender version side by side at 0.3 m and does not read as melted or
     carry baked lighting. Cap: 400 Meshy credits. All tools in the roll must still read as one kit.
3. **The roll** is the weakest piece. It needs cloth: waxed olive-brown canvas with creases and sag between pockets,
   stitched pocket seams with bulges where tools sit, a bound edge, a patch, a leather strap with a real buckle, and
   a rolled state whose end is a convincing spiral. It stays skinned on its rig with the same two params.
4. **Density.** A 4096 set is allowed for the hand tools and the roll (texture budget raised for this family and the
   pistol). Aim for 45 px/cm or better on anything carried to the work.
5. **Checks and publish** as now: `check.py` PASS on the baked export, `publish.py` to `Art/Bench/Tools/` keeping
   the existing `.meta` files. Publish in two steps so the others get parts early: first the eleven new tools at a
   quick bake with correct ids, empties and tags (PROGRESS line starting `model-tools: NEW TOOLS PUBLISHED`), then
   the quality pass.
6. **Review**: every tool at 0.3 m under the warm key beside its sheet, and the whole kit unrolled on the black rubber.
   Open every sheet yourself and say honestly where it still falls short.

## Spending

Meshy: 400 credits (single-piece tools only). fal `--tag model-tools`: $3 for extra reference sheets of tools not on
the existing sheets (drill, snips, iron, applicator, third hand): hand tools and workshop equipment only; if a service
refuses a prompt, stop and report, do not reword. Grok and OpenAI routes as in AGENT-RULES.

## Machine

One Blender slot is shared by several agents (waits of 5 to 20 minutes are normal this evening) and memory is short:
wrappers only, short geometry builds, group several jobs in one slot hold as `tools/src/rebake_all.sh` does, bake at
low resolution until the look is settled.

## Milestones and report

1. Verdict on what exists (PROGRESS line). 2. Eleven new tools published with correct ids (PROGRESS line as above).
3. Quality pass on all tools and the roll, 4096 bake, checks, publish, hand back.

Report as AGENT-RULES says: outcome first; what is on disk and published; check results; what you saw and where it
still differs from the sheets; triangles, density, texture sets; Meshy task ids and credits; open defects.
