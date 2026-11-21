# Brief: `integration` — the real models on the bench, its light, and the rebuilt pistol in the hand

Draft of 20 November 2026, 17:45. The orchestrator fills in the "State when you start" section before this is used.

You turn the greybox bench into the real one: the modellers' families bound into the interaction system, lit and
shaded to the look target, measured, and then the rebuilt scrap pistol put in the player's hand in place of the fused
Meshy one. You do not change how the job plays (that is `bench`) or what it grants (that is `craft`).

Read first: `../AGENT-RULES.md`, `../DESIGN.md` sections 4, 8, 10 and 12, `../CONTRACT.md` (ownership table and A),
`../SEAM.md` (binding: names, places, pose marks), `../bench/README.md` ("The seam for the integration pass", "Running
it"), each family's `README.md`, `PARTS.md` and `export/parts.json`, `../kit/READY.md`, and `AGENTS.md` section 3
rows **Salvage shop (walk-in)**, **Light budget**, **Player: hero base**, **First-person rifle hands** and
**Character arms and pistol hold**. Look at `../concept/bench_overview_fal.jpg`: Carl accepted it as the look to reach.

## What you own

`Editor/SteadyHandsBenchInstall20261120.cs` (steps `import`, `materials`, `bind`, `light`, `install`, `verify`,
`rollback`, and later `hand`, `hand-rollback`), `Prefabs/Bench/**`, `Shaders/Bench*`, `Art/Bench/**` import settings
and material assets (the GLBs and `*.parts.json` there belong to the modellers: report defects, do not edit them),
and scene objects under the roots **Steady Hands bench light** and **Steady Hands bench review cameras**. The root
**Steady Hands bench** itself is made by `bench`'s installer; you run its `prefab --real <families>` and `scene`
steps, you do not write into its prefab by hand.

## Part 1: the bench with real art (do this first, report, then go on)

1. **Import.** Every family in `Assets/AthenHill/Art/Bench/<Family>/`: glTFast import with the project's texture
   compression add-on, correct normal and packed-map handling (AGENTS.md section 6, Material import), readable
   meshes off, no colliders from the import. Record triangles, materials and texture memory per family against
   `DESIGN.md` section 12.
2. **Materials.** URP Lit unless a part needs more. Two small shaders at most, each written and checked in the player:
   a wipe shader (blend from the family's `__dirty` set to its clean set through a mask the `WipeVerb` paints) and,
   if `bench` asks for it, an emissive ramp for the nanite cure. No shader may add a pass to the whole scene.
3. **Bind.** Run `AssemblyBenchInstall20261120 --steps prefab --real <families>` and fix what `BindFamily` reports
   on your side (import names, missing empties are the modellers' to fix: list them precisely). Greybox stays for any
   family that is not ready. `verify` and `selftest` must pass with the real families bound, and a second install
   must leave the scene unchanged.
4. **Light.** One bench work lamp (warm, about 3000 K, the shadowed key of the look target) and the cure lamp, both on
   rendering layer 7 with the shop's interior lamps and counted by `LightBudget`. The shop's lamps cast no shadows
   today; one shadowed spot here is the single exception and its cost is measured. Contact matters more than
   brightness: parts must sit on the mat, not float. Nothing visible from the avenue may change (the room's portal
   test stays as it is).
5. **Review cameras** `cam_bench_*` (the six shots `bench` defined stay; add close ones for each family at 0.3 m).
6. **Verify** (`-nographics`): bound part count per family, no missing materials or scripts, every step's references
   resolve on real parts, light count in the bench shots inside the budget, chunk fingerprint unchanged.

You cannot see it: graphics-mode Unity is not allowed on this machine. The orchestrator builds, captures every
`cam_bench_*` at the bench hours and sends frames back. Expect two or three fix rounds on light and materials.

## Part 2: the rebuilt pistol in the hand (only after part 1 is accepted by the orchestrator)

`model-pistol` exports `pistol_hand.glb` (the pistol as one merged object in `ScrapPistol.glb` units) for this. The
held pistol, its holstered copy, the first-person view model and the other five mods (`art/pistol_mods_20260930`,
`WeaponModVisuals` shows the child named after the mod's item id) must still fit: same outline, bore, rail and grip
position are the modeller's promise, and you check it by numbers before anything is swapped (muzzle point, grip
frame, mod mount points within 1 mm of the old ones).

- A separate step with its own rollback (`hand`, `hand-rollback`), keeping `ScrapPistol.glb` and its GUID untouched.
- The Stabilised Pistol Grip shown on the held pistol becomes the real grip (`grip` family, merged for the hand).
- Do not re-run `MainCharacterInstall`, `TutorialSetInstall`, `RifleHandsPass20261120 install` or the hero base
  chain. If finger contact needs re-solving on the new grip shape, use the existing passes' narrowest step and say
  which; if that is not possible without the chain, stop and report instead.
- `check_rifle_quest.py`, the range tutorial and the city loop are run by the orchestrator afterwards.

## Limits

- One Unity job at a time through `SH/seq.sh`, `-nographics` only; batch your runs. Memory is tight
  (`gpu-job-limits.md`): check `free -g` before a run, and never retry a killed job more than once.
- No building the player, no native runs, no commits.
- Budgets: `DESIGN.md` section 12. Say where you are against each.

## State when you start (20 November, 20:20)

**Families in `Assets/AthenHill/Art/Bench/`** (GLB, `<family>.parts.json`, as-found PNGs in `tex/` where a family has
wipes). No `.meta` files were written by the modellers: Unity makes them on first import.

| Family | State | Notes |
|---|---|---|
| `Pistol` | 22 parts, 31.8k triangles, 2048 bake, checks pass; `pistol_hand.glb` beside it | a surface pass and a 4096 bake are in progress (`model-pistol-surface`); ids, nodes, marks, params and outline will not change, the textures will |
| `Servo` | 33 parts, 41.5k triangles, 2048 bake, checks pass, two rigs, params rest at 0.5 for the gimbal | one more surface pass to come; ids fixed |
| `Grip` | core, two cross screws, two seams; 7.8k triangles, 2048 bake, checks pass | plates and strap are materials parts seated on the core's pose marks (`SEAM.md` section 9) |
| `Tools` | slice set: roll (skinned, on `tools_roll_rig`), screwdriver with two bits and bit block, pliers, cutters, punch, mallet, oil bottle and dropper | the rest is `model-bench`'s Milestone 3: stand-ins fill the gaps |
| `Fixtures` | slice set: work surface, work mat, parts mat, vise (slide, screw, pads), cradle, dish, pad, board with clips | tray, bin, jar, press, lamp, tester, schematic, holster are Milestone 3: stand-ins fill the gaps |
| `Materials` | not published yet (geometry built, 52 parts; bake pending) | stand-ins until it lands |

**The interaction system** (`bench`, Milestone 2 handed back 20:05): 81 steps, 208 actions, all eight stages; the bot
plays the whole job by mouse and by keyboard; Edit Mode 504/504. `AssemblyBenchInstall20261120` has the steps
`recipe, audio, settings, prefab, scene, install, verify, bindcheck, selftest, rollback`. `bindcheck` binds one real
family at a time on a scratch object and reports what does not resolve: all four families that existed then resolve
(`unity/evidence/steady_hands/20261120/bench/bind-*.json`). A family's gaps are filled with stand-ins carrying the
real ids ("mixed families"). **A whole bench built from the real families has never been made or played. That is
your first result.** Read `bench/README.md` from "The seam for the integration pass" on.

**Which families are real is one file**: `art/steady_hands_bench_20261120/data/sources.json`, read by `bench`'s
installer (it is adding the reader now; look for its PROGRESS line). You own the file's contents. Until the reader
exists, work on import, materials, light and cameras, which do not touch the bench prefab.

**What the native runs showed** (stand-ins, real mouse, build `batch-sh-slice2`): the bench opens, the camera takes
over, stage 0 and half of stage 1 play. Frames in `unity/evidence/steady_hands/20261120/bench/native-mouse/run/`:
open `shot-work.png` (the working view, and the look target's composition), `shot-wide.png`, `18-s1_tape_peel.png`.
Things that are yours:

- The old Meshy workbench's own cyan screen is the brightest thing in every shot, and its lamp head hangs into the
  wide view. While the bench is in use, dim the screen's emission (a material property block or a swapped material on
  that renderer for the session, restored on leaving; ask `bench` for an enter/leave hook if there is none) so the
  warm lamp and the pistol's cell carry the picture.
- The bench is lit by flat room ambient: no key, no contact shadows. This is the largest gap to the look target.
- In the stand-ins the clamped pistol sits inside the vise jaws. With the real vise the pose comes from
  `fixtures.vise/seat_work`: check by numbers that the grip and its wrap are clear of the jaws and reachable from
  the `vise` shot, and report to `model-bench` (PROGRESS line `integration -> model-bench:`) if the mark is wrong.

**Review renders.** The modellers' kit rig was about 1.6 EV too bright until 19:46 (`SEAM.md` section 8): colours in
sheets rendered before that are washed out. You judge nothing from Blender anyway: the orchestrator sends native
frames.

**Shared colours** for anything you light or tint: `SEAM.md` section 8.

**Talking to the others.** You cannot message other agents. Write a PROGRESS.md line starting
`integration -> bench:` (or `-> model-bench:`, `-> model-pistol:`, `-> model-materials:`) with the file and node
names; they read the file. Do not edit their files.

**Asking for a build.** When part 1 is installed and `verify` and `selftest` pass on the real-art bench, write a
PROGRESS line containing `READY FOR BUILD real1` and carry on with what does not need a picture. The orchestrator
builds when memory allows (it is tight: builds have been killed twice today) and sends frames back.

## Report

After part 1 and after part 2: what is installed, `verify` and `selftest` results, the numbers against the budgets,
what you could not judge without a picture, defects that belong to another agent (with the file and node names).
