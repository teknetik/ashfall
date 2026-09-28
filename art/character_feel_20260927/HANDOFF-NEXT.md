# Handover — character feel, next session (written 27 Sep 2026, after the first pass)

The original brief is `HANDOFF.md` in this folder; the running log is `PROGRESS.md`. This document is the state at the
end of the first pass and what to do next. The full report with numbers, before/after videos and captures is
`unity/evidence/character-feel/20260927/README.md`. Read that before changing anything.

Nothing is committed. The working tree also holds unrelated earlier work (render chunks, Ward/Berms passes). Keep it.

## Where things stand

All five areas from Carl's request are in and verified in the native build:

| Area | State | Main files |
| --- | --- | --- |
| Wardens "shifty" | Done. Six guard-model characters on calm per-character idles/talks, phase/speed jitter, head look-at | `Editor/CharacterFeelPass.cs`, `Scripts/ActorLookAt.cs`, `Scripts/ActorAnimation.cs`, `Art/CharacterMotion/Guard/idle_calm_*`, `talk_calm_*` |
| Player animation | Partly done. Breathing idle, two-handed pistol hold as an upper-body layer | `Art/CharacterMotion/Player/lib_*.anim`, `pistol_hold.anim`, `Scripts/Combat/PlayerWeaponPose.cs` |
| Footsteps | Done. Foot-contact trigger, 6 surfaces, Berms map, ElevenLabs sets, ~13 dB quieter | `Scripts/FootstepAudio.cs`, `unity/tools/generate_footstep_audio.py`, `Audio/ElevenLabs/Footsteps/` |
| First-person weapon | Done. Player forearms + pistol on an overlay camera, hip/ADS, sway, bob, recoil, flash | `Scripts/Combat/FirstPersonViewModel.cs`, `MuzzleFlash.cs`, `Editor/WeaponFeelPass.cs`, `Art/CharacterMotion/FirstPerson/` |
| Gunshots | Done. 3 layers × 6 variants, close/distant, foley, SFX group | `unity/tools/generate_pistol_audio.py`, `Audio/ElevenLabs/Combat/Pistol/`, `Scripts/Combat/PlayerCombat.cs` |

Paths under `Scripts/`, `Editor/`, `Art/` and `Audio/` are relative to `unity/AthenHill/Assets/AthenHill/`.

Last verified state:
- Edit Mode tests 65/65 (4 new in `Tests/Editor/CharacterFeelTests.cs`).
- Development and release builds 0 errors.
- Native checks all pass with the Editor closed: `check_character_feel.py`, `check_checkpoint.py` (10/10) and
  `check_depot.py` (7/7).
- Performance:
  - Checkpoint route: 212.8 fps, p99 17.42 ms (was 16.71–16.99).
  - Depot walk: p99 16.59 ms (was 16.00).
  - No hitches over 50 ms on either route.
  - Carl said to be lenient on frame rate for now.

## Decisions still with Carl

1. **Third-person aim framing.** From directly behind, the torso hides most of the raised pistol. Raising
   `FollowCamera.aimShoulder` from 0.55 to about 0.75 (and maybe `aimBoom` from 2.1 to 1.9) would show it, but changes
   camera feel. Ask before changing.
2. **Gunshot level.** The new shot is louder and fuller than the old one:
   - First-person segment: −16.6 LUFS (was −23.0).
   - Third-person segment: −19.2 LUFS (was −22.2).
   - If Carl finds it hot against music, trim `PlayerCombat.mechGain/bodyGain/tailGain`, keeping their ratio.
3. **Texture streaming** stays on, from the depot pass. The rollback copy is
   `unity/evidence/outer-berms-depot/20260927/QualitySettings-before-streaming.asset`.
4. **Frame-time target**: left for a dedicated pass, per Carl.

## Next work, in priority order

1. **Strafe and backpedal while aiming.** The legs play the forward walk while the body faces the camera, so the feet
   slide sideways.
   - Clips are already retargeted: `lib_left_528` (walk left with gun) and `lib_back_233` (walk back while shooting).
   - Plan: in `ActorAnimation.SetGroundMotion`, when `PlayerMotor.FaceView` is set, choose forward, back or left by the
     move direction relative to facing.
   - Right strafe needs a mirrored clip (legacy clips cannot mirror at runtime). Either request the Meshy library's
     right-strafe action on the player rig (`meshy/character-feel-20260927/rig_player.py <name>_<action_id>`), or mirror
     `lib_left_528` in the Editor by swapping Left/Right bone curves and negating the yaw/roll components.
   - Measure each clip's foot speed and set stride speeds so nothing slides.
2. **Turn-in-place.** `lib_turnl_576` and `lib_turnr_586` are retargeted but not wired. Trigger them when standing and the
   facing changes by more than about 60° (camera orbit while aiming, or `FaceView` catching up).
3. **Draw and holster body motion.** Today the aim layer blends in at 60 % for 0.35 s on draw, and the first-person view
   slides up from below. `lib_draw_222` is a draw from the back, so it doesn't fit a hip holster. Look in the library
   for a hip draw, or author a short one in Blender.
4. **First-person hands quality.** The arms are cut from the 20k-triangle colonist (1,373 triangles). The fingers are
   faceted and read slightly large at aim-down-sights.
   - A dedicated first-person arms mesh would fix it: Meshy, or Blender on the same armature.
   - Keep the bone names so `pistol_hold.anim` still drives it.
   - Re-run `WeaponFeelPass.Install()` afterwards.
5. **Reload and empty presentation.** There is an empty click but no animation. Library 170 "Standing Reload" is
   available.
6. **Worker droid clips.** Untouched this pass. The handover notes still apply: the idle is a combat stance, the punch is
   sped up, the hit sways about 0.5 m, and there is no turn-in-place.
7. **Small audio items.**
   - The metal landing set has only 2 variants; add takes via `EXTRA_TAKES` in the footstep script.
   - Optional NPC footsteps: same component, spatial, quieter.
8. **Frame time.** Budget work when Carl asks for it: profile the checkpoint route's slow east-facing frames.

## How to rebuild or re-run

**Editor-side installers.** All live in `Editor/`, are idempotent, and are also in the menus under Athen Hill →
Characters, Audio and Combat. Call them in this order after changing sources:
1. `CharacterFeelPass.ImportCalmIdles()`
2. `CharacterFeelPass.InstallCalmGuards()`
3. `CharacterFeelPass.RetargetPlayerClips()`
4. `CharacterFeelPass.InstallPlayerIdle()`
5. `CharacterFeelPass.InstallFootsteps()`
6. `WeaponFeelPass.Install()` — also regenerates `pistol_hold.anim`, re-mounts the pistol and rebuilds the view model

**Audio regeneration.** Run `python3 unity/tools/generate_footstep_audio.py` or `generate_pistol_audio.py`. Cached
sources are reused; pass `--generate` only for new takes. Sources, requests and manifests are in
`unity/staging/elevenlabs-audio/{footsteps,pistol}/`.

**Meshy.** The scripts are `meshy/character-feel-20260927/rig_guard.py` and `rig_player.py`. Pass `<name>_<action_id>`
arguments to add library clips. The catalogue is `animation-library.json` and previews are in `previews/`. Credits so
far: 70.

**Native check:**

```bash
DISPLAY=:0 ATHEN_FEEL_EVIDENCE=<dir> uv run --offline --with python-xlib python unity/tools/check_character_feel.py
```

Close the Editor first. It records video with audio and measures loudness per segment. It also runs against old
builds, which is how the `native-before/` baseline was made.

**Tests and builds.** Same as the depot pass. For tests, keep the job id that `run_tests` returns and poll
`get_test_job` with it. Builds go through `AthenHill.Editor.LinuxBuild.Development()` and `Release()` via
`EditorApplication.delayCall`.

## Pitfalls hit this pass (save yourself the time)

- **Launch the Editor detached**:
  `DISPLAY=:0 setsid -f /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -projectPath /home/teknetik/code/ao2/unity/AthenHill`.
  A plain `&` from a tool shell gets killed when the call ends.
- **Close the Editor before native runs** (VRAM). Wait for the process to exit, not just for the MCP call to return.
- **Stale skins in Editor renders.** Off-screen `Camera.Render()` of skinned characters shows a stale pose unless
  `SkinnedMeshRenderer.forceMatrixRecalculationPerRender = true` is set during the render.
- **glTFast armature root.** glTFast makes the armature the instance root, so clips bound to `Armature/Hips/...` miss.
  The first-person arms sit under a "Player forearms" root with the instance renamed "Armature".
- **Mismatched player skeletons.** The installed player skeleton and a fresh Meshy rig differ by about 110° at the hips
  and chest. Always use `CharacterFeelPass.Retarget` (bind-pose deltas), never copy rotations directly. The guard rigs
  match, so copying is fine there.
- **Library clips that turn the body.** For example 95 "Gun Hold Left Turn". Take hips and legs from idle before
  straightening the upper body, or the torso ends up twisted against the legs.
- **`??` on components.** `GetComponent<T>() ?? …` fails on Unity's fake null; write `if (!x)`.
- **Test asmdef.** It now references the URP runtime assemblies, which camera-stack tests need.
- **Native check input.** The check centres the mouse only once. A pointer warp while aiming counts as mouse look.

## Acceptance still open from the original brief

- **Wardens:** a 30 s continuous native video per Warden. The current evidence has about 20 s each, far and near.
- **Walk and run:** slow-motion capture of every transition, to check foot sliding. Strafe and backpedal will fail
  until item 1 is done.
- **Gunshots:** A/B inside the depot. The recordings so far are at the range only.
