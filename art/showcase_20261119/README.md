# Showcase programme, 19 November 2026

Carl's brief: go over the game, find the gaps in graphics, gameplay, environment and NPCs, and fix them, one Opus
agent per issue. This file is the programme record: the gap list, what was done about each gap, and what is still open.
Each package keeps its own README in a subfolder here; the night pass is in `art/night_readability_20261119/`.
The native test record is `unity/evidence/showcase/20261119/qa/README.md`.

**Nothing here is accepted by Carl yet, and nobody has listened to any of the new audio.**

## Build to play

`unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64` (18:50, same files as `Builds/batch-gates`: the 17:32 showcase
build, kept as `Builds/batch-showcase-qa`, plus the East Gate rename).
`unity/AthenHill/BUILDS-START-HERE.txt` opens with how to try each feature. New keys: **P** photo mode, **M** world map.

## Gap list and outcome

Source of the gaps: the last native captures (3 and 5 October builds), a grep of `Scripts/`, AGENTS.md open items and
Carl's save.

| # | Area | Gap | Outcome |
|---|---|---|---|
| 1 | Gameplay | No hit markers, kill confirmation, camera shake or weak points; enemy bolts were a thin pink line | **Done**: `combat_feel/`. Native check 23/23 |
| 2 | NPCs | Nobody spoke outside the dialogue window; Tamsin and Ossa's locker/range lines were unvoiced | **Done**: `npc_life/` (80 bark lines, greetings, remarks, reactions, captions; new takes). Native check 27/27 |
| 3 | Graphics | Conversations were framed by wherever the follow camera was; no photo mode | **Done**: `showcase_camera/` (over-the-shoulder conversation camera with depth of field, photo mode on P). Native check 99/99 after fixes |
| 4 | Environment | Static weather: constant wind, no dust fronts | **Done**: `weather/` (wind through the day, dust fronts, droid sight shortened in a front). Native check 13/13. The look values need Carl's eye |
| 5 | Graphics | Night close to black away from lamps; characters were silhouettes at 20:30 | **Done**: `art/night_readability_20261119/`. Faces 2.6–17 → 31–54 of 255; day unchanged. Mira is still darker than her lit floor |
| 6 | Environment | The 495 x 425 m Berms reads as flat, sparse sand between sites | **Not started** (needs Blender and a Unity pass) |
| 7 | NPCs | Nine actors in a whole city; streets are empty | **Not started** (Meshy has 126 credits, about three characters) |
| 8 | Gameplay | No world map for a 500 m play space | **Done**: `world_map/` (M; survey render, discovery, respawn ring, tracked mission). Native check 29/29 |
| 9 | Interface | Four corner panels plus radio banners cover much of a 1080p frame | **Done**: `interface/` (lower-third dialogue while the camera frames, optional Adaptive HUD; default stays Full). Native check 22/22 |
| 10 | Audio | The rifle reused the pistol's sound layers; droids shared voices | **Done**: `combat_audio/` (rifle layers, 35 droid clips, voice limiter). Native check 14/14 on what a machine can check |
| 11 | Characters | First-person rifle hands (shooting hand sits on the magazine well); NPC faces shade patchy in low sun | **Not started**. The night pass does not touch 17:00 |
| 12 | Rendering | OpenGL draws at most 32 lights per camera | **Decided 19 Nov** (left to the agent): a light-budget pass on OpenGL, not Vulkan. Not started |

Gaps seen in the final captures and not fixed:

- The colonist's flight suit and chest rig read as noisy, ragged patches from behind. The over-the-shoulder shot puts
  his back across a third of the frame in every conversation, so this is now the most visible character asset.
- Torr at the mission slab stands too close for a shoulder shot and gets the eye-line close-up.
- Linn's and Mira's faces are flat and grey in shade at 13:00.

## How it was run

- Seven feature agents wrote code and one idempotent Editor install method each, with no Unity running, compile-checked
  by `unity/tools/compile_check.py` (replays Unity's compiler response files with the Editor's Roslyn, about 5 s).
- Installs, Edit Mode tests, builds and native checks then ran one at a time through the wrappers in
  `~/.local/state/ward-programme/showcase-20261119/` (`seq.sh`, `build_to.sh`, `native_check.sh`, shared Unity lock,
  memory caps, watchdog).
- A night-readability agent and a native QA agent worked on the built game. The QA agent wrote the
  `unity/tools/check_showcase_*.py` checks, fixed the game defects it found and repaired four stale older checks.
- Edit Mode tests: 363/364 after the first installs, 390/390 at the end of the programme (run r6), 393/393 after the
  gate names pass.

Installers (all under `unity/AthenHill/Assets/AthenHill/Editor/`, each `RunBatch --steps ...`, each with a `verify` step):
`CombatFeelPass20261119`, `CombatAudioPass20261119`, `WeatherInstall20261119`, `NpcLifeInstall20261119`,
`ShowcaseCameraInstall20261119`, `WorldMapInstall20261119` (its `survey` step needs graphics),
`NightReadabilityPass20261119` (has `rollback`).

## Things that went wrong and what they cost

- `Library/` and `Builds/` had been deleted in the October/November disk cleanups: full reimport (12 min) and a first
  build of 52 min (cold shader cache; later builds 2–5 min).
- The last rebuild was stopped once by `ward-watchdog` (256 MB available, swap 27.3 GB) and succeeded on the retry;
  the baseline build needed a 19 GB cap after an out-of-memory kill at 17 GB. The desktop had less headroom by evening.
- The Unity licence had expired offline; starting Unity Hub renewed it from its saved session.
- The first reimport was killed by `ward-watchdog` after 47 s because desktop swap alone was over its 27 GB line.
  Nothing was raised; work continued without Unity until memory freed up.
- The first import emptied `Assets/Settings/UniversalRenderPipelineGlobalSettings.asset`; it was restored from HEAD
  (the emptied copy is kept beside the wrappers) and has not changed since.
- Unity bumped `com.unity.sdk.linux-x86_64` and `com.unity.toolchain.linux-x86_64-linux` 1.1.0 → 1.1.1 in
  `Packages/manifest.json` and `packages-lock.json`.

## Frame time

Before/after against a build of the last commit (`Builds/batch-baseline-head`, made from a copy-on-write copy of the
project by `~/.local/state/ward-programme/showcase-20261119/baseline.sh`), three alternating fresh runs of each build
(`unity/tools/check_showcase_ab.py`), 1920×1080 High with TAA, uncapped:

| View | Before (avg FPS, p50) | After (avg FPS, p50) | Change |
|---|---|---|---|
| cam_hill 13:00 | 59.4, 16.69 ms | 59.6, 16.67 ms | −0.02 ms |
| cam_avenue 13:00 | 56.0, 17.85 ms | 56.1, 17.84 ms | −0.01 ms |
| cam_gate 13:00 | 88.0, 11.46 ms | 88.0, 11.40 ms | −0.06 ms |
| cam_hill 20:30 | 58.8, 16.83 ms | 58.4, 16.96 ms | +0.13 ms |
| cam_avenue 20:30 | 58.7, 16.86 ms | 58.6, 16.93 ms | +0.07 ms |
| cam_gate 20:30 | 86.2, 11.72 ms | 87.0, 11.62 ms | −0.10 ms |

The programme costs nothing measurable at these views. The hill and avenue views are just under the 60 FPS target on
both builds, so that gap predates today. Dust-front, Berms and conversation numbers (showcase build only) are in the
QA README.

## Carl's answers (19 Nov 2026)

1. **Gate names.** Both gates had ended up called West Gate. The West Gate is the one near the market: the portal into
   the Berms. The spawn arches on the other side are now the East Gate (name picked by the agent; pass
   `art/gate_names_20261119`): plates over the baked plaques, menu and pause text, map label. Native on
   `Builds/batch-gates`: gate names 12/12, world map 29/29, interface 22/22, city loop PASS, range tutorial 10/10.
2. **Dust fronts** come only after Ossa's primer. No change.
3. **Lamps stay off in a dust front**: more interesting, and Ward saves power. No change.
4. **Adaptive HUD quiet time**: 6 s is a start; to be judged in play.
5. **Map discovery radius** 55 m: yes.
6. **32-light limit**: left to the agent. Decision: a light-budget pass on OpenGL, not Vulkan (reasons in AGENTS.md,
   Rendering baseline). Queued for the next round, after the playtest, because it changes night lighting again.

Still for Carl's eye: the dust front's look at its peak (haze 2.2, warmth 0.8, sky veil 0.7, sun dim 0.4) and the
1240 px dialogue panel width.

## Proposed next round

The light-budget pass (gap 12), Berms ground variety between sites (gap 6), three more residents with the remaining
Meshy credits (gap 7), the colonist's suit and rig seen from behind, first-person rifle hands (gap 11), Basic General's
counter lamps for Mira.
