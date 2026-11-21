# integration: the real models on the bench, their surfaces and the bench's light

Steady Hands bench programme, `integration` agent, 20 November 2026. Brief: `../briefs/integration.md`.
Part 1 (the bench with real art) installed; Part 2 (the rebuilt pistol in the hand) installed 21 Nov.

**Nobody has seen any of this in the game.** Graphics-mode Unity is not allowed on this machine; everything below was
made and checked with `-nographics` runs and by numbers. The look is a first setting to be corrected from native frames.

## State (21 Nov, 08:50)

- Run integ-n (08:44): grip republish (08:36) imported; `verify` PASS, `dryrun` PASS, bench `verify` PASS (81 steps,
  183 parts). Colour draws in the widest shot 116 of 120 (was 139): BenchLook does not draw the 23 servo parts no ray
  leaves while the case is closed (`enclosure.py` -> `enclosure.json`, list in `look.json` `enclosed`; drawn again as
  soon as any link is off its rest pose). Texture memory 169 MB at 2048; about 330 MB expected with the 4096 grants.
- 21 Nov 09:46: the bench GLBs import with glTFast `animationMethod` Legacy (sh-real1's player logged 10,025
  "Non-Legacy animations cannot be sampled" errors); `import` throws if a clip stays non-legacy, `verify` checks every
  `AssemblyParam` clip (15, all legacy). Bench selftest 17/17 on the six real families (run integ-q).
- **Part 2 installed (21 Nov 11:57, runs integ-u/v/w)**: numbers PASS on the 11:24 `pistol_hand.glb` (gyro grip 0.93 mm
  at worst); steps `hand`, `hand-rollback`, `handverify` (evidence `hand.json`, `hand-verify.json`, record
  `integration/hand-record.json`). The held and first-person pistols draw `Rebuilt pistol (Steady Hands)` (pistol_hand's
  five nodes) instead of the ScrapPistol mesh; the Stabilised grip mod draws `Real grip (Steady Hands)` (core, screws,
  seams, plates, bent strap, case screws at the core's seat marks) and hides the stock grip through `HideWhileActive`.
  Copies are named `pistol_hand*` and `real_grip_*` (a second `ScrapPistol` broke PlayerLocomotionTests, fixed 21 Nov).
  A second `hand` leaves the scene unchanged; rollback exercised and reinstalled. NPC pistols untouched. Not seen in
  the game yet.
- Earlier, **Part 2**: the numbers check (`hand_check.py`, evidence `hand_numbers.json`) failed on 20 Nov's `pistol_hand.glb`
  for one mod only: `grip_gyro_braced` stands off the new frame's left rear and backstrap by up to 2.8 mm. Ruling (a),
  08:36: model-pistol brings those within 1 mm in its 4096 republish; the check is re-run then. Bore, grip frame, rail
  left face and the other four mods pass. No `hand` step exists yet.

## State (20 Nov, 21:36)

- The bench in the saved scene is built from all six families as real art (`../data/sources.json`), with stand-ins of
  the same ids for what a model does not have yet (fixtures 24 parts, tools 11; materials none since its core_flash and
  core_sprue were published at 20:58).
- `SteadyHandsBenchInstall20261120 verify`: PASS (`unity/evidence/steady_hands/20261120/integration/verify.json`).
- The bench installer's own `verify`: PASS on the real-art bench (81 steps, 183 parts, 96 places; its run bench-f10 at
  21:37). Its `selftest` there was 14 of 17 (the bench agent's fix round).
- The bench installer's `selftest` on the real-art bench: **2 of 17** when I ran it (20:52) and 2 of 17 in the bench
  agent's own run of 21:17. Every failure is the bot failing to pick, hold or seat a real part (listed in
  `../PROGRESS.md` at 20:58 and answered by `bench` at 21:28: it is that agent's fix round); nothing fails to resolve
  in the bind. Copy of my result: `unity/evidence/steady_hands/20261120/integration/selftest-real-2052.json`. On the
  stand-ins the same selftest is 17 of 17 (the bench agent's `selftest-standins.json`).
- No player has been built with this pass: the first attempt (`sh-real0`, 21:22) was killed by the memory watchdog.

## What exists

| Piece | Where |
|---|---|
| Installer | `Editor/SteadyHandsBenchInstall20261120.cs`: `import`, `materials`, `bind`, `light`, `install`, `verify`, `rollback`, and `benchverify`, `benchselftest`, `benchbindcheck` (the bench installer's steps in the same Unity run) |
| Every number of the look | `integration/look.json` (import, surface, reveals, lamps, session, cameras, budgets) |
| Which families are real | `../data/sources.json` (flat: `"pistol": "real"`; read by both installers) |
| Runner | `integration/run.sh NAME STEPS` (one `-nographics` run on the shared Unity lock; `rollback` also rebuilds the bench from stand-ins) |
| Surface shader | `Shaders/BenchSurface.shader` (`Athen Hill/Bench Surface`), `Shaders/BenchSurface/BenchSurfaceInput.hlsl`, `BenchSurfaceForwardPass.hlsl` |
| Materials | `Art/Bench/<Family>/Materials/<GLB material name>.mat`, `...__wipe.mat` (as-found variant), `...__lamp.mat` |
| Runtime | `Scripts/BenchLook/BenchLook.cs` on the scene root **Steady Hands bench light** |
| Scene | roots **Steady Hands bench light** (`Bench work lamp`, `Cure lamp`, `BenchLook`) and **Steady Hands bench review cameras** (`cam_bench_close_*`), both at the bench root's transform |
| Checks without Unity | `integration/glb_report.py` (what is in each GLB), `integration/vise_check.py` (the pistol in the vise, by numbers), `integration/light_numbers.py` (what the lamps put on a white card across the bench), `integration/hand_check.py` (Part 2: pistol_hand.glb against ScrapPistol.glb), `integration/enclosure.py` (parts out of sight while assembled), shared reader `integration/glbgeom.py` |
| Evidence | `unity/evidence/steady_hands/20261120/integration/`: `import.json`, `materials.json`, `bind.json`, `light.json`, `verify.json`, `dryrun.json`, `vise_check.json`, `install-integ-*.log` one level up |

Paths without a prefix are under `unity/AthenHill/Assets/AthenHill/`.

## How it works

**Nothing is written into the bench's prefab.** `bind` runs the bench installer's own `prefab` and `scene` steps. The
real parts keep the glTF materials they were imported with in the prefab and the scene; `BenchLook` puts them on their
Bench Surface materials when the scene starts (by the glTF material's name) and again each time the bench is opened.
The bench installer can therefore rebuild its prefab at any time without losing the look, and `verify` here fails if
the bench was rebuilt from other sources than `sources.json` names.

**One shader, used only by materials under `Art/Bench`.** It is URP 17.6 Lit's passes and lighting (the project's own
copy for `Art/Weathering` was the template) with a surface for what the kit bakes:

- glTF-packed maps as they are: occlusion R, roughness G, metallic B in one linear map, RGB normals (+Y). Nothing is
  repacked, so a re-exported GLB needs only `materials` run again (textures are taken from the GLB's own imported
  material; they are bound by name).
- One inline sampler (trilinear, repeat, anisotropy 8) for every map: glTFast leaves embedded textures bilinear.
- `_BENCH_WIPE`: the family's as-found set (`tex/<family>__dirty_*.png`) on the same UVs, shown wherever the part is
  not yet clean. Clean is read per renderer from up to six wipe zones by **world position**: each zone's 16 x 16 mask
  (`AssemblyBench.Wipe`) is a slice of one texture array, and the zone's box is passed as a matrix. A part reads its
  own modelled zones; where the family gives none (`"zone": null`: a clip, a case screw, a punch mark) it reads the
  whole-part zone `part/<wipe id>` the bench makes, which an effect of the job reveals (`"~part/wipe"`). All 21
  as-found parts of the present bench are cleaned by something the job does (`verify.json`,
  `asFoundPartsTheJobNeverCleans` is empty). The wiped edge is broken up by the difference between the two sets
  (thick dust lets go last).
- The bench's feedback tint (`_EmissionColor` and `emissiveFactor` in a property block: affordance rim, glint, flash,
  refusal) is drawn as a **rim** (Fresnel, with a 22 % floor), not as a flood over the part. A part's own emission is a
  separate property (`_BenchEmission`), so hovering the glowing cell does not put it out. On a lamp (`__lamp`
  variant, for the parts in `layout.json` `lamps`) the tint lights the whole surface and the part has no emission of
  its own, so the bench's lamp level is all there is.
- Glass (`alphaMode: BLEND` in the GLB) is the same shader, transparent, premultiplied, two-sided, with no shadow or
  depth pass.

**A dry run of the runtime** (`dryrun`): `BenchLook.Start` and its frame step are run on the saved scene in the Editor
(no Play mode, nothing saved): 148 renderers go onto Bench Surface materials, none stays on a glTF material, 21 start
as found with their zones bound, the lamp is off away from the bench and on at it, 179 renderers cast shadows at the
bench and none after leaving.

**Reveals** (`look.json` `reveals`, SEAM.md section 10): a part that comes clean by the progress of an action, which
a mask cannot show. One today: the nanite seams follow the cure wait (`s5.cure:wait`) while it runs, with a glow that
peaks half way; the bench reveals the seam's mask at the end of the wait and the two agree (the larger wins).

**Light.** `Bench work lamp` is a warm spot (sRGB 1.0 / 0.80 / 0.60, about 3000 K) under the gantry's front edge,
behind and above the work surface, aimed at its middle: shadows fall toward the player. It is the one shadowed light in
the shop (soft, medium filter, a 4096 tile, URP's own bias: 1.08 mm; shadow texel 0.6 mm at the work mat). The work
surface, both mats and the tool roll never cast (`session.noShadowParts`): a big flat receiver in the shadow map
shades itself in bands at the edge of the pool, and what lies on them still casts onto them. It lights rendering layer 7 only (set on `UniversalAdditionalLightData`, where
this URP reads it), is saved switched off, and `BenchLook` brings it up over 0.6 s only while `AssemblySession` is
open, so nothing changes for a camera on the avenue. While the bench is in use `BenchLook` also takes the shop's own
lamps to 85 %, the old workbench's screen to 12 % and its cyan glow light to 4 %, and lets the bench's parts cast
shadows (away from the bench none do, like every prop in the shop, so they never enter a sun shadow pass). All of it
is put back on leaving. `Cure lamp` is a small cool spot that follows `fixtures.lamp_head` and is lit while the bench
has that lamp on.

What the lamps put on a white card (albedo 0.8) lying on the bench, by URP's formulas, red channel, no ambient
(`light_numbers.py`):

| Where | Today | At the bench with this pass |
|---|---|---|
| Work mat, middle | 0.61 red but 2.49 blue: the screen's "Fabricator glow" point light hangs 0.34 m over the mat | 1.32 (work lamp 1.00, shop 0.31, glow 0.01); blue 0.48 |
| Pad / parts mat / vise / dish | 0.42 to 0.70 | 1.19 / 1.00 / 0.93 / 0.89 |
| Work surface, front edge | 0.64 | 0.86 |
| Tester (left) | 0.35 | 0.64 |
| Where the pistol lies at the start (left front) | 0.39 | 0.48 |
| Tray (right rear) | 0.35 | 0.39 |
| Tool roll and servo at the start (far left) | 0.32 | 0.33 / 0.30 |
| Press (right rear) | 0.28 | 0.22 |

The worktop is 2.2 m wide and the lamp hangs 0.63 m over it (the gantry is in the way of anything higher), so it is
a pool over the 0.9 m work surface, as in the look target, and the ends of the worktop stay on the shop's lamps: the
press, the tray, the board and the things as found are about as bright as they are today, which next to a lit work
surface will read as dim. That is the first thing to judge from frames.

**Review cameras.** `cam_bench_close_<pistol|servo|grip|tools|fixtures|materials>` stand 0.3 m from the family's
main part (or its place) as the bench is found, 40 degrees down, 35 mm; `cam_bench_close_vise_work` looks at the
vise's work seat and `cam_bench_close_mat_low` across the work mat at 18 degrees. The bench's own ten shots are
untouched. They are disabled cameras on active objects, found by name like every other review camera.

## Running it

    SH=~/.local/state/ward-programme/steady-hands-20261120
    $SH/run.sh integ-x art/steady_hands_bench_20261120/integration/run.sh x install,verify,benchverify,benchselftest
    $SH/wait.sh integ-x
    python3 art/steady_hands_bench_20261120/integration/glb_report.py        # no Unity
    python3 art/steady_hands_bench_20261120/integration/vise_check.py        # no Unity

After a family is re-exported: `materials` (and `import` if a new file arrived), then `bind,light,verify`.
A second `install` leaves the scene file unchanged (checked: see "Results").

Development players, for A/B runs and stills: `ATHEN_BENCH_LOOK=off` (the bench as the bench installer made it: glTF
materials, no lamp), `always` (lit for work without opening the bench), `noshadow` (the work lamp without shadows),
`nodim` (the shop's lamps and the screen left alone). Comma separated. `BenchLook` writes one line to `Player.log` at
start: how many renderers it put on bench surfaces, how many as found, zones, whether it found the room and the screen.

Rollback: `integration/run.sh NAME rollback` removes the two scene roots, sets every family in `sources.json` to
`greybox` (the previous file is kept as `integration/sources-before-rollback.json`) and rebuilds the bench. Materials,
the shader and the import settings stay. Never exercised.

## Results

Numbers from `verify.json`, `import.json` and `materials.json` (run integ-c, 20:52, and later runs).

| Budget (DESIGN section 12, CONTRACT A) | Is | Verdict |
|---|---|---|
| Bench set in view under 250k triangles | 111.6k in the widest shot (`cam_bench_room`), 110.7k in `wide`, 61.5k in `work` | inside |
| Under 120 colour draws added in the bench camera | 139 (`room`), 137 (`wide`), 82 (`work`), 56 (`vise`) as found | **over in the two wide shots**: one draw per part; every bench renderer carries a property block (interior ambient, feedback), so the SRP batcher does not merge them. The work lamp's shadow pass draws about 134 casters more while the bench is in use |
| Triangles per family | pistol 31,775 / 45k; grip 7,820 / 25k; servo 41,468 / 45k; materials 14,238 / 15.7k; tools 17,306 (as imported) / 60k; fixtures 17,538 / 70k | inside |
| One 2048 texture set per family | pistol 21.3 MB (four maps: a 2048 emission map for the cell), grip 16 + 4 (as-found set kept at 1024), servo 16 + 16, materials 16 + 16, tools 32 (two sets), fixtures 32 (two sets): 169 MB in all against 96 | **over**: the as-found sets (36 MB), second atlases (32 MB) and the pistol's emission map (5 MB) |
| Lights: one bench lamp and the cure lamp, inside the light budget | 7 unbudgeted lights in view in the bench shots (the shop's five, the work lamp, the cure lamp), 11 in `room`; cap 28 | inside |
| Frame time no worse than the shop's walk-in view | not measured (needs the player) | open |

A second `install` left the scene file byte for byte unchanged (run integ-f, 21:02; not repeated after the later
changes to the lamp and the wipe zones, which use the same find-or-make code). Unity runs of this pass: integ-a to
integ-m, logs `unity/evidence/steady_hands/20261120/install-integ-*.log`.

Other checks: no colliders come from the imports; all six families bind with nothing unresolved; all sixteen
pass-and-keyword sets of the shader compile for OpenGL Core; chunk fingerprint unchanged; no missing scripts.
Meshes import readable (glTFast's importer has no switch for it): a few MB of CPU copies.

The vise (`vise_check.json`): with `pistol_frame` at `fixtures_vise__mark_seat_work` and the jaw at the family's
snug value 0.6022 the pads are 35.92 mm apart on a 35.62 mm frame. The pistol is held grip up: wrap, binding wires,
scales, both grip screws, housing, pin and plug are 26 to 139 mm above the jaw tops and none of them lies between
the pads. Only the cell and its latch are between the pads (10 to 14 mm clear of the faces), and the cell is out
before the first clamp. The mark is right.

## Not judged, because it needs a picture

Everything about how it looks: whether the work lamp's level (0.58), colour and angle give the look target's pool and
contact shadows; whether the ends of the worktop (tray, board, press, where things lie at the start) read as too dark
beside it; shadow acne on parts' own flat faces, or light leaking under thin parts (bias 1.08 mm, shadow texel 0.6 mm
at the work mat); the mats casting no shadow of their own (the work surface's 8 mm edge has none on the old worktop); whether the rim reads on flat parts seen from
above; the cell's glow (4.8, 60 % of the authored 8); the wiped edge; the seam's cure; glass; the dimmed screen;
whether the inline sampler is taken as trilinear with anisotropy on the OpenGL player; the close cameras' framing.

## Departures from the brief

1. **A runtime script** (`Scripts/BenchLook/BenchLook.cs`). The brief's ownership list has no runtime folder, but the
   wipe shader needs something to feed it the bench's masks, and the lamp and the screen need an enter and leave
   hook. It reads the bench (`AssemblyBench`, `AssemblySession.State`, `Job`, `Partial`) and edits none of its files.
2. **Materials are swapped at runtime, not in the bench's prefab** (see "How it works"). In the Editor, out of Play
   mode, the real parts show their glTF materials.
3. **One shader for every real part**, not URP Lit plus a wipe shader: URP Lit cannot read glTF's packed map without
   repacking every family's textures, and the bench's tint needed keeping apart from a part's own emission.
4. **The work lamp is on only while the bench is in use.** The brief wants nothing visible from the avenue to change;
   a lamp that burns all day in the back of the shop would.
5. **The shop's lamps and the screen are dimmed through their own components at runtime** (intensity, a property
   block), and restored on leaving. No scene object of the shop is edited.
6. **The cure lamp is a scene light that follows the bench's lamp part**, not a child of it (the part is in the bench's
   prefab). It reads the level the bench wrote into that part's property block.
7. **The work lamp's shadow tile is 4096**, the whole additional-light shadow atlas, which no other light in the shop
   uses (none casts). A lower bias on a 2048 tile was installed first (21:21) and withdrawn before any build: it was
   under what a flat face needs at the edge of the pool.

## Found on the way (not mine to change)

- **The shop's interior lamps are not held to rendering layer 7 in this URP.** `SalvageShopPass` and
  `InteriorLighting` set `Light.renderingLayerMask` to bit 7; URP 17.6 reads a light's layers from
  `UniversalAdditionalLightData.renderingLayers`, which is saved as bit 0 (Default) on those lamps
  (`ForwardLights.cs:699`). They light everything in range, not only the interior. Fixing it would change what is seen
  from the avenue, so it is left alone and reported.
- `AssemblyFeedback` writes the tint to `emissiveFactor` and `_EmissionColor` and leaves black behind: on a glTF
  material that puts out a part's own glow for good. Not a problem with the Bench Surface materials.
- `grip_seam_l__zone_seam` and `grip_seam_r__zone_seam` come in with negative scale (the zone reads -120 x -120 x -4
  mm); `AssemblyWipeMask.Axes` then takes x as the thin axis. `BenchLook` uses absolute sizes.
- The pistol's `KHR_materials_emissive_strength` is ignored by glTFast 6.20 (import report); the materials step reads
  the strength from the GLB itself.
