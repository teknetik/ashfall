# Gemini merge, 21 November 2026

Gemini's branch `ward/phase4-canon-living-ward` (checkout `/home/teknetik/code/ao2-phase1-polish`, six commits on
`5b84b1f9` = our `6116cd6c`) merged into `merge/gemini-20261121`, cut from `ward/next-level` at `14440330` (Steady Hands
bench snapshot). Carl: "Take its work and merge it to yours. Discard bad code and work with what's good."

Gemini never opened Unity: nothing it wrote had been compiled by Unity, imported, installed or tested. Everything below
that says "verified" was run in this merge, with `-nographics` only. No player build and no native run was made here.

Where both sides changed a file, ours was kept and Gemini's change folded in on top. The Steady Hands bench, the bench
tutor, `CraftingState.benchFinished` and the no-Auto-assemble rule are untouched by the merge (no Gemini commit touched
`Scripts/Assembly`, `Scripts/BenchLook` or the bench routes; the conflicts in `CraftingModel`, `PlayerCombat`,
`FirstPersonViewModel`, `GameInput`, `FollowCamera` and `CityHud` were resolved in favour of the bench code).

## Commits on the branch

| Commit | Gemini source | What |
| --- | --- | --- |
| `918dbd5c` | 0772141b | phase 1 polish (part) |
| `40e1d441` | 68bf4506 | combat verbs, nano abilities, eye implant |
| `ebc86457` | dbadd6c8 | Living Ward pacing, canon UI, density installer v1 |
| `fef39b52` | 92840cfe | polish swarm (part) |
| `ff535d30` | 02cf44d8 | danger atmosphere, density v2 (look split out) |
| `98f35c68` | ab6df4ca + 02cf44d8 | **look unit**: every look change, revertable as one commit |
| `f38bb6b9` | — | Berms ground shaders did not parse; `Editor/ShaderCompileCheck.cs` |
| `3f47f65a` | — | Berms density installed in the saved scene; `.meta` files for the merged scripts |
| `4cef438d`, `98a1ad06` | — | Edit Mode failures fixed |
| (this commit) | — | this record and the Edit Mode results |

To take the look out again: `git checkout 14440330 -- <the 17 files of 98f35c68>` (the shader fix in `f38bb6b9` touches
two of them, so a plain `git revert 98f35c68` conflicts on one line each; resolve to the 14440330 version).

## 0772141b phase 1 polish

Kept
- Adaptive HUD as the default (`InterfaceOptions.mode` default, `CityHud.Mode` fallback, tests and the native check
  updated to match, DESIGN.md). Saves that stored `mode: 0` stay Full; only settings files without the key change.
  **Carl's call**: on 19 Nov he said the 6 s Adaptive quiet time "is a start to judge in play"; making it the default
  was Gemini's decision, not his.
- Enemy bar readability (wider bar, backed name label).
- Weak points larger (`RadiusFor` .15/.13/.17 -> .19/.16/.21 m, depth tolerance .35 -> .42) in code and on the six droid
  prefabs. Addresses the recorded open defect "the optic may be too small to hit (4 of 12 aimed shots)".
  `CombatFeelPass20261119 verify` still PASS with the same balance figures.

Dropped
- Player arm-corrector retune (`abductionTarget`/`abductionMin` raised in the scene and `characters.json`) and the pistol
  carry retune (`carryWristShare` 0.8 -> 0.9, `carryWristMax` 30 -> 48). These are values Carl reviewed in the game
  (character arms row, 20 Nov); Gemini gave no evidence and never looked at a frame. Default to ours.

## 68bf4506 combat verbs, nano abilities, Warden Optic Suite

Kept
- `CombatVerbs` (pure rules) and `DodgeState`; dodge in `PlayerMotor` (dash with 0.18 s i-frames, 1.4 s cooldown,
  12 nano when armed in the Berms), shove (`V`, 2.8 m cone, stagger, 12 damage), EMP Disruptor (`Q`, 30 nano, 7.5 m,
  1.8 s stun, 50 % armour strip for 8 s), Nano Overcharge (`X`, 25 nano, 6 s, fire interval x0.8, damage x1.2, +6
  armour penetration). `FeralDroid.ApplyShove/ApplyEmp`, EMP glow and bar label, verbs hint on the HUD.
- `optic_suite_mk1` (Warden Optic Suite Mk I) in `CityCatalog` (Field Supply, 65 cr) and `CharacterCatalog`
  (`implant_eye`, perception +3, accuracy +6, crit +0.03 like the other targeting implants, intellect 10). The eye slot
  now has one item; LoadoutFixPass verify reports it. With Overcharge it adds 2 s and widens the optic lock x1.2.
- `CombatVerbsTests` (5 tests, real assertions).
- Key check: C, V, Q and X are unbound in the Gameplay map. Q and X are bound in the Bench map and C/Q in the Photo
  map, but those maps only run outside Play, and the verbs only read input in Play.

Changed
- Resolved against our `PlayerCombat` (Steady Hands heat, side kick, rattle/damper cues) and `GameInput` (Bench map).
- Dropped the Left Ctrl dodge binding: Ctrl-drag moves HUD windows. C stays. README updated.

Not checked: no real-input run; Item Lab export (`Data/Crafting/Export/ward-crafting.v1.json`) is still stale (it was
already) and now also lacks the optic.

## ab6df4ca night GPU, face fill, Berms relief, Vulkan harness

Kept, in the look unit (`98f35c68`)
- `PC_RPAsset`: additional-light shadow atlas 4096 -> 2048, high tier 1024 -> 512, soft shadow quality 3 -> 2, cookie
  atlas 2048 -> 1024. A performance trade that changes how shadows and cookies look; needs the native A/B.
- `NightActorLighting` conversation face fill (SH only, no lights). Risk to look for: it switches every actor within
  60 m from its baked probe to the sky probe x1.25 for the length of any conversation, by day too, so faces under
  awnings and in the walk-in shops may brighten and there may be a pop as the conversation starts.
- `BermsVarietyGround.mat` relief values.

Dropped
- `LightBudget` pool cap changes (`maxPools` 44 -> 28, `minPoolPixels` 6 -> 10, `poolMaxDistance` 120 -> 95, scene and
  code defaults). Unmeasured; they bring back distant lamps going dark, which the light-budget pass was built to remove.
  Candidate for the orchestrator's A/B if the night views still need frame time.
- `unity/tools/bench_vulkan_ab.py`. It cannot work: it writes `cmd.json` with a `cmd` key, but the QA bridge reads
  `command.json` with `action` and an `id`; `startGame`, `camera` and `sampleFrames` are not bridge commands; and the
  Linux player ships OpenGL Core only, so `-force-vulkan` has nothing to switch to. The graphics API is unchanged.

## dbadd6c8 Living Ward, canon UI, density v1

Kept
- `AmbientWalker` pacing (`reactToWeatherAndTime`): in a dust front walkers hurry (x1.25-1.4) and stay 1.5x longer at
  work stops without talking; at night they walk at x0.82 and stay 1.35x longer. Calm daylight is exactly as before.
  `LivingWardTests` (3). `WardResidentsInstall20261120 verify` still ok.
- HUD title "WARD / Oasis city · Tir" and modal footer "WARD / TIR" (was ATHEN HILL / FREE COLUMN). In line with the
  setting canon; Carl may want a say, since AGENTS.md asks for a deliberate content pass for player-facing names.

Changed
- A front is read from visibility only. Gemini's `windStrength > 1.8` clause also fired in clear gusting weather.
- `CityHud` writes the footer at runtime, so Gemini's uxml change never showed; the runtime string now says WARD / TIR.

## 92840cfe full-game polish swarm

Kept
- Combat feel for the verbs: camera trauma and synthesized fallback cues (`CameraImpulse`, `CombatAudio`), view-model
  verb poses and strafe roll (`ViewModelMotion`), bolts that respect dodge i-frames and check cover before the player's
  body, no splash on a direct hit, stunned/staggered droids do not fire, pack calls staggered by distance and line of
  sight (`DroidEncounter`).
- `FirstPersonViewModel` kicks on `ShotsFired` instead of `LastShotTime`: the verbs stamp `LastShotTime` to pause nano
  regeneration, so without this every dodge or EMP would kick the gun.
- Sprint and dodge FOV kick (`FollowCameraFeel`, off under Reduced Motion and while aiming).
- Music ducking with attack/release and equal-power crossfades; weather audio ducks in menus.
- Hardening: null and NaN guards across the character, crafting, orders, save, shop, stash, map, journal and settings
  code; skill-use progress cleared at the cap; capacity checked before a timed craft starts (it could fail after the
  timer); Repair job blocks a second job; FitMod orders count a mod fitted on any weapon; buying past a stack limit says
  so; keyboard navigation in the loadout, pack bar, journal and settings tabs; map wheel zoom proportional; HUD Adaptive
  keeps the identity panel up at low vitality, overclock or overcharge. Tests added in `CharacterModelTests`,
  `ShopModelTests`, `SaveGameTests`, `HudPanelsTests`, `InterfacePresentationTests`, `CombatVerbsTests`,
  `CraftingProgressionPolishTests`, `WorldAtmospherePolishTests`. `LoadoutFixTests` changed from "no eye implant
  exists" to "the optic fits the eye slot", which matches the new catalog (not a weakened test).

Changed
- Conflicts resolved in favour of the bench: `CityHud` (Assembly state keeps the HUD and drops the shade),
  `CraftingModel` (`on_bench` refusal and slot qualities on restore kept, Gemini's busy/null guards added),
  `FollowCamera` (bench camera branch kept), `FirstPersonViewModel` (handling sway, side kick and recovery overshoot
  kept; verb poses, strafe roll and the ShotsFired trigger added; the duplicate recoil decay Gemini added was removed).
- `FollowCamera`: Gemini cleared `lensTouched` on a fixed view. A fixed view entered while aiming or sprinting would then
  capture the zoomed or kicked FOV as the new base FOV. It now only zeroes the kick; the next normal frame restores.

Dropped
- `CraftingModel.SortedRecipes`, `CraftingModel.PlanIngredients`, `IngredientAllocation`, `CraftingText.ReserveUseNote`
  and their two tests: nothing in the game calls them (dead code reachable only from tests).

## 02cf44d8 wasteland realism, danger atmosphere, 271 placements

Kept, outside the look unit (`ff535d30`)
- `BermsDangerAtmosphere` (`BermsDangerMath` pure, `BermsDangerTests` 7): threat level from depth, droid proximity and
  four tier-3 zones (centres match the next-level encounters); radio warning on entering a zone (90 s cooldown), ash
  wisps that follow the player in the Berms (capped under Reduced Motion), distant crackles. No lights.
- `BermsDensityPass20261121` and `placements.json` v2: 271 props in seven groups (conveyor and Tube ruins, Warden cover
  posts, skirmish wrecks, hazard perimeters, ambush choke points, desert clusters), 22 spark arcs (no light), 14 smoke
  columns. Placements were generated clear of the Berms variety survey's markers and colliders.

Changed (installer)
- `RunBatch` exits Unity with 0/1. The batch wrapper runs `-executeMethod` without `-quit`; Gemini's version would have
  hung until the 90-minute timeout.
- `verify` now checks the saved scene: no collider of this pass within 3 m of a droid spawn, 2.5 m of a salvage node,
  interactable or loot source, 4 m of a waystation or the respawn (the BermsVarietyPass capsule test); counts props
  against the json; writes `unity/evidence/gemini_merge/20261121/berms_density/verify.json`; throws on any problem.
  `install` was already idempotent (it deletes and rebuilds its root) and `rollback` already existed.

Kept, in the look unit (`98f35c68`)
- `WardDustbowl` day/night profile (night ambient darker, day key 2.1 -> 2.35, cooler fill) and `WardDustbowlGrade`;
  `DefaultVolumeProfile` (tonemapping None -> ACES, contrast +12, saturation -4); `PC_Renderer` SSAO (intensity
  0.85 -> 1.15, direct 0.35 -> 0.48, radius 0.5 -> 0.42, falloff 60 -> 95); Berms ground V2/V3, Berms variety rock, sky
  and basin sandstone materials; the three terrain shaders (micro-grit, cavity occlusion, grazing dust sheen);
  `CityTimeOfDay` and `CityAtmosphere` Outer Berms blend (`WastelandAtmosphere`: exactly the old frame east of
  x = -58.3 m, bleaker ambient, denser fog, faster wind and more dust over 28 m west of the wall);
  `WastelandAtmosphereTests`.
- The night profile change works against the 19 Nov night-readability pass Carl reviewed (faces at 20:30). Check faces.

Fixed
- Both Berms ground shaders failed to parse (`[Header(Wasteland micro-detail and weathering)]`: a hyphen is not allowed
  in a ShaderLab attribute), which would have drawn the Outer Berms ground pink. Fixed by dropping the hyphen.
  `Editor/ShaderCompileCheck.cs` compiles every pass for Linux OpenGL Core without a graphics device: the old file fails
  it (negative control), the three changed terrain shaders and `LampPool` pass
  (`unity/evidence/gemini_merge/20261121/shader_check*.txt`). Only the no-keyword variant is compiled.

## Working-tree incident (not Gemini's)

Four Git LFS files were pointer stubs in the working tree when the merge started (mtime 21:42-21:43, after `14440330`
at 21:40): `Art/Imported/Meshy/colonist.glb` and `Art/Bench/{Fixtures/fixtures,Pistol/pistol,Tools/tools}.glb`. The
LFS objects were in `.git/lfs`; `git lfs checkout` restored them. With the stubs, the colonist failed to import (the
MeshyPlayer prefab lost its nested model) and the bench verify failed with "99 renderers lack a material". The first
density install saved the scene in that state and rewrote the player instance; that commit was replaced by a clean
reinstall (purely additive scene diff). Any Unity job, build or native run made in this checkout between 21:43 and
22:56 on 21 Nov ran without the player model and the bench art.

## Verification (this merge, -nographics)

- `compile_check.py` after every commit: OK.
- `BermsDensityPass20261121 install,verify`: PASS, 271/271 props, 0 lights, 22 arcs, 14 smoke, 151 gameplay points
  clear of 254 colliders.
- `AssemblyBenchInstall20261120 verify`: ok (81 steps, 201 parts, 97 places).
- `SteadyHandsBenchInstall20261120 verify,handverify`: ok (real fixtures/tools/pistol/grip/servo/materials; 2 pistols).
- `BenchTutorInstall20261121 verify`: pass (91 lines, 81 steps, 9 teach).
- `CombatFeelPass20261119 verify`: PASS (balance figures unchanged).
- `LoadoutFixPass20261120 verify`: ok (16 body-map slots, eye slot items: 1).
- `WardResidentsInstall20261120 verify`: ok.
- `BermsVarietyPass20261120 verify`: PASS; droid's-eye rays blocked by other geometry 1,499 -> 1,510 of 4,194 (the
  density pass adds cover on 11 rays).
- Shader compile check: PASS for BermsGroundV2, BermsGroundV3, WardDesertTerrainV2, LampPool.
- Edit Mode suite: first run 566/574 (8 failures), all traced and fixed except one that was already failing before the
  merge (below). Final run `editmode-gemini-merge-3`: 573/574, the one failure being that pre-existing bench test.
  Baseline: the suite on `14440330` alone (Assets checked out from that commit, `editmode-baseline-14440330`) is
  523/524; the one failure, `AssemblyBenchTests.APartHeldInPlaceWillNotComeAndShowsWhatHoldsIt` ("the scale shows what
  still holds it"), belongs to the bench work in progress and fails the same way after the merge.

Edit Mode failures found and fixed

| Test | Cause | Fix |
| --- | --- | --- |
| `AmbientWalkerStopsTests` x2 (existing) | Gemini added parameters to `UpdateWithStops`, which the tests call by reflection | signature restored, pacing scales moved to fields |
| `ShopSellTests.CatalogSellRulesFollowRarityAndKind` (existing) | the optic was Rare, and every Rare item must be untradeable | rarity Uncommon, like the Mk I implant sold beside it |
| `CharacterModelTests.SkillUseProgressClearsAtCapAndHandlesLargeAmounts` (Gemini) | expected 17 from a skill at 0 raised twice by 5 | cap 10, plus a check that progress stays below the cap |
| `CraftingProgressionPolishTests.ActiveRepairJob...` (Gemini) | instant-crafted the stabilised grip, which is hand-made at the bench every time (`hand_made_first`: the no-Auto-assemble rule held) | uses the wound coil schematic, which has no bench job |
| `HudPanelsTests.EyeImplant...` (Gemini) | expected a "sealed optic" line, but implant slots give three sockets; the equip was optional | dead branch removed in `CharacterLoadoutPanel`; equip asserted; checks "AUGMENTATION SLOTS 3" |
| `SaveGameTests.EyeImplantOpticSuite...` (Gemini) | ignored that accuracy and critical chance follow perception | floors after equipping, exact round trip after restore |

## For the native build

Not verified here: anything that needs a picture, a frame time or real input.

- Look unit (`98f35c68`), A/B against a build without it: Outer Berms ground close up and far (micro-grit, cavity
  darkening, grazing sheen, scorch contrast; `cam_bv_*`, `cam_nextlevel_*`), basin sandstone and sky (`cam_hill`,
  `cam_gate`), the Berms blend as the player walks out of the West Gate (fog, ambient, wind and dust change over 28 m),
  city grade and SSAO by day and at 20:30 (`cam_hill`, `cam_avenue`, `cam_gate`), night faces (`cam_night_*`; the
  profile darkens night ambient against the 19 Nov night-readability work), Mira under her lit floor in a
  conversation, shop interiors in conversation (face fill pop), lamp shadows and cookies (shadow atlas and cookie atlas
  halved). Frame time at the usual cameras, and in the Berms.
- Berms density: `cam_bv_*`, `cam_nextlevel_*`, the routes between sites; spark arcs and smoke columns; the tier-3 zone
  radio lines (Reaper den, Post relay, Fans camp, Southern cache); ash wisps near droids; frame time in the long Berms
  views (714 renderers, 254 colliders, mostly prefabs already used in the Berms). Gunner separation and next-level
  enemy checks, since cover changed on 11 of 4,194 droid's-eye rays.
- Real input: C dodge (and that it costs nano only armed in the Berms), V shove, Q EMP, X Overcharge with and without
  the optic; first-person view model while dodging and strafing; sprint FOV kick and its return; that aiming and
  conversations still set the lens correctly after a sprint or dodge; Field Supply sells the optic; eye slot equip; HUD
  Adaptive by default with a fresh settings file; HUD title and footer; world map wheel zoom; keyboard arrows in the
  loadout, pack bar, journal and settings tabs; walkers at night and in a dust front (speed, longer stops, no talk).
- Checks to re-run: interface (expects Adaptive default now), rifle quest, combat feel, combat audio (music ducking),
  NPC life, Berms expansion, gunner separation, next-level enemies, home/journal, Field Supply, loadout, city loop,
  range tutorial, and the bench checks.


## Fix round, 22 November 2026 (after native QA on `batch-sh-gemini1`)

### Vex's 23:00 greeting (check_showcase_npc_life 26/27, twice; 27/27 twice on `batch-sh-real12`)

Cause: the check's `barkReset` (`BarkDirector.QaReset`) set every speaker's approach gate to "outside". A walker
standing within his 3.2 m pass radius of the player at that moment was therefore "walked up to" by the reset itself
and spoke a Passing line on the next scan, inside the 0.3 s before the check reads its bark count. That bark took the
one-bark slot, so Vex's greeting edge (the player crossing 5.5 m on the walk-up) was used up with nothing said, and
the 7 s global gap outlasted the check's 6 s wait. The bark log left in the layout dump at the capture is Daro's in
both failing runs and Vex's in the passing one.
Why only on the merged build: Gemini's night pacing (`AmbientWalker`, x0.82 at night). Daro's lane runs past the
player's start point (16-38 m, z -3.5/-2.5, 0.95 m/s, loop 46 m). At full speed he passes the player at about t = 49 s
and is about 5 m away at the reset (t = 54 s); slowed from the 23:00 time set (t = 42.5 s) he is still about 3.1-3.6 m
away at the reset, on the edge of his pass radius.
Fix: `QaReset` re-arms each gate to where the player stands (inside if already within the speaker's radius), so a
reset no longer fabricates an approach. Gameplay barks are unchanged; the check is unchanged. Gemini's night pacing is
kept. Not verified natively here.

### Berms density props: discarded

The orchestrator judged the native before/after sheets (`native/look/cam_bv_long_gate-h13.00.jpg`,
`cam_nextlevel_post_relay-h13.00.jpg`): reused conveyor gantries, trusses on stilts and a tower dropped in the open
bowl outside the West Gate read as scatter, not purposeful sites (AGENTS.md section 4). `BermsDensityPass20261121
rollback` removed `Outer Berms/Berms density`; the saved scene now differs from `14440330` only by the serialized
defaults of the new fields (36 lines) plus the danger atmosphere below. The installer, `placements.json` and
`generate_placements.py` stay in the repository as an unaccepted pass that is **not installed**; do not run its
`install` without a new brief.

The danger atmosphere depended on it: Gemini's installer created `BermsDangerAtmosphere` under the density root, so the
rollback removed it too. New `Editor/BermsDangerInstall20261122.cs` (`install`, `verify`, `rollback`) puts back only
the controller under `Outer Berms/Berms danger atmosphere`: tier-3 zone radio warnings, ash wisps, distant crackles.
Without the density hazards there are no spark arcs, so a crackle is sound only. Verify PASS (one controller, four
zones, no lights, colliders or meshes, no density root).

### Fix-round verification (-nographics)

- `BermsDensityPass20261121 rollback`: removed; `BermsDangerInstall20261122 install,verify`: PASS.
- `BermsVarietyPass20261120 verify`: PASS (droid's-eye blocked-by-other back to 1,499, as before the density pass).
- `AssemblyBenchInstall20261120 verify` ok, `SteadyHandsBenchInstall20261120 verify,handverify` ok,
  `BenchTutorInstall20261121 verify` pass.
- Edit Mode `editmode-gemini-merge-fix1`: 573/574; the one failure is the pre-existing bench test
  (`AssemblyBenchTests.APartHeldInPlaceWillNotComeAndShowsWhatHoldsIt`, also failing on `14440330`).
- The earlier sections that describe the density install as installed are superseded by this round.
