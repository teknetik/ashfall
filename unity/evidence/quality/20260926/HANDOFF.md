# Ward / Athen Hill — AI handoff, 26 September 2026

## Stop state and authority

The user requested an ambitious AAA visual/gameplay improvement loop with parallel
specialists and harsh independent comparisons. They subsequently said **“stop”**,
then requested this handoff. Implementation is stopped and the explicit goal is
**paused**. This document does not authorize silently restarting the loop.

**The game does not meet the requested AAA standard.** Independent criticism still
prefers the official ARK references. Neither current gameplay nor performance is
fully qualified. Do not turn successful builds, unit tests, or internal A/B wins
into a claim of AAA quality or perfection.

Repository: `/home/teknetik/code/ao2`. Work only on the native Linux Unity game in
`unity/AthenHill`. Read the current `AGENTS.md`, `unity/EDITING.md`, relevant asset
records and `lore.md` before resuming. Preserve the later September street work,
orange tree, all nine actors, roles/routes, accepted gate/terminals and gameplay.
Do not revive the retired browser game, regenerate the city or enable rejected shops.

The working tree contained thousands of pre-existing staged/unstaged files before
this work. **Do not reset, clean, blanket-stage or commit the entire tree.** Existing
GameSession focus-loss changes and much of the scene diff predate this session.
No commit or PR was created for this work. Source originals and failed evidence
have been retained.

## What is actually implemented

Paths below are relative to `unity/AthenHill/Assets/AthenHill` unless stated otherwise.

| Area | Implemented change and limits |
| --- | --- |
| Player/camera presentation | New `Scripts/PlayerRenderPose.cs`; `PlayerMotor` interpolates the visual between fixed simulation poses, restores simulation before physics, resets interpolation on teleport, and exposes `RenderPosition`. `FollowCamera` follows that presentation position. Controller/collision roots remain in place. Motion still requires native visual/input acceptance. |
| Player shadow proxy | Existing proxy reparented under the existing interpolated visual while preserving its world pose. This is the only saved scene change made here. |
| Reduced Motion | `GameSettings` reads/saves the preference; `GameSession` initializes and persists it using the isolated QA preference namespace during tests. Relaunch behavior still needs real native verification. |
| Ground/grass shading | `Shaders/HillGround.shader` and `HillGrass.shader` corrected for installed URP lighting, shadows, AO and depth/normal passes. Grass no longer forces a 50% sunlight floor; alpha/wind behavior is aligned across passes. |
| Hero leaves | Original 4096² image retained. Derived `Art/Quality20260926/leaves-edge-padded-v1.png` preserves alpha and opaque RGB while extending leaf colour into pale partial-alpha edges. `Art/HeroTree/leaves.mat` references it. |
| Leaf lighting | WardTree shader includes a bounded opposite-hemisphere SH ambient-transmission approximation for the current Forward/legacy-probe path, with AO retained. Saved value is **0.15**, direct transmission remains **0.22**. Native .15 and .25 tied for a modest readability improvement over zero; neither fixed dense dark clusters. Other GI modes/deferred transmission are not implemented by this approximation. |
| Material Inspector | `Editor/WardTreeShaderGUI.cs` delegates the installed URP Lit inspector and exposes wind/flutter/direct/ambient controls. Compilation, GUI resolution, keyword preservation, multi-edit and Undo were checked. Manual pointer/layout review was not performed. |
| Development diagnostics | `NativeVisualReview`, `NativeTreeShadowReview` and `NativeQa` support reversible shadow distance/cascade and preserved LOD1 shadow-caster auditions. Visible tree geometry is unchanged. These are diagnostics, **not saved default optimizations**. Explicit `--athen-qa-background` permits static background rendering only in development QA. |
| Build/launcher | `Editor/LinuxBuild.cs` copies the existing UI font licence into both output types. `unity/tools/launch_phase1_qa.py` uses argparse, has a safe `--help`, accepts `--display`, and refuses to launch without an explicit/inherited X display. |

Tests added: seven interpolation checks, four Reduced Motion checks, four transient
tree-shadow helper checks, and a proxy hierarchy/collider contract in the existing
character suite. Unity-generated `.meta` files accompany new assets/scripts.

The full scoped source record is in [README.md](README.md),
[movement/README.md](movement/README.md) and the corresponding art manifests under
`art/quality_20260926/`.

## Saved scene and build identities

Current saved scene SHA-256:
`9094c6d14dc5c084519f149e3c99447bb29dc782746ed5f7b678179a42f94723`.
Pre-proxy scene SHA-256:
`497542b6541f392fd4a173f257e61b272fa40ebc33947ba9c501a2a246800cfb`.
`scene-change-scope.json` isolates the three hierarchy hunks from the much larger
pre-existing scene diff. **The planned ground cameras and paving material are not
installed.** `handoff-file-state.json` confirms this and records current hashes.

| Build | Result | Identity/evidence |
| --- | --- | --- |
| Current development 04 | Succeeded, 53.46 s, 0 errors, 346 warnings | `development-build-04.json`, `candidate-build-04-identity.json` |
| Current release 01 | Succeeded, 153.38 s, 0 errors, 352 warnings | `release-build-01.json`, `release-build-01-identity.json` |
| Development 03 | Earlier shader/shadow diagnostics; leaf ambient stored zero, overridden explicitly for auditions | `candidate-build-03-identity.json` and build-03 evidence |

Current development `AthenHill.Runtime.dll` SHA-256:
`d52781641006b6e8a80aee3b42f542b64c4c83fb74c6ca60b640d3cfdd004f21`.
Current release runtime SHA-256:
`6d9437c43555cbeef94dad06d6d666bfd7c64b99abf75a467bf27bbd7dd6c6d6`.
There are both `AthenHill.Runtime.dll` and `Assembly-CSharp.dll`; record both when
identifying builds. Earlier tooling recorded only the latter in some reports.

Outputs remain in `unity/AthenHill/Builds/LinuxDevelopment` and `Builds/Linux`.
The original native build is recoverable under
`Builds/.archive-quality-20260926-original`. No pipeline/API/package migration was
made: Unity 6000.6.0f1, URP 17.6.0, normal NVIDIA OpenGL.

Most build warnings are pre-existing Sentis unsupported compute variants.
`release-build-warnings.json` exports all 352 release warnings. A point-shadow atlas
warning also reports reduction of twelve maps to fit a 2048 atlas; it remains a
lighting issue, not a new claimed fix.

## Verification, failures and limits

- **50 EditMode tests passed, 0 failed, 0 skipped** in 6.855 seconds. Raw result:
  `movement/proxy-reparent/final-editmode-results.json`. Later Inspector/build-copy
  changes were separately compiled/checked; no subsequent runtime logic change.
- Release negative-control gate passed: release ignored QA flags/commands and
  produced no development bridge files. `release-gate-01/report.json`.
- Visible release rendering passed: three owned-window XGetImage captures at
  1920×1080 on NVIDIA OpenGL 4.5, no detected runtime/shader/allocation errors,
  no focus or input manipulation. `release-static-01/report.json`.
- Current build-04 stills: twelve full 1920×1080 captures under
  `native-current-build04/`, including player portrait/body and guard. They are
  static visual evidence; this process was later found to run slowly.
- **No real native input tests began after the desktop unlocked.** The specialist
  had only read the harness files when the user stopped work. Controls, jumping,
  stairs, thresholds, camera collision/first-person zoom, modal input blocking,
  NPC branches, atomic trade, travel and Reduced Motion relaunch remain unverified
  on this build. Do not describe them as passed.
- Earlier private-display attempts were invalid for acceptance: llvmpipe ran at
  roughly 0.5 FPS; two Zink attempts emitted thousands of allocation errors, one
  with a black capture. Original failures are preserved in
  `headless-functional/ATTEMPTS.md`. Do not repeat those driver experiments as the
  default route; normal desktop NVIDIA OpenGL works.

### Performance

Host: RTX 3060 12 GB, i9-10850K, NVIDIA 610.57.04. Measurements used full 1920×1080,
render scale 1, MSAA 4, all nine actors, VSync off, uncapped timing. These were short
stationary controls, **not the required warmed moving traversal**. GPU time and
draw/batch counters were unavailable in these runs, not zero cost. Submitted
triangles include multiple rendering passes.

| Evidence | Important result |
| --- | --- |
| Build-03 hill, default 18 m/one cascade | 73.75 FPS average, p99 14.87 ms |
| 96 m/four cascades | About 42 FPS; visually stronger wide shadows but rejected for cost |
| Build-03 reduced shadow geometry, 48 m/two cascades | Hill 63.28 FPS/p99 17.08 ms; avenue 60.96 FPS/p99 17.67 ms. Both still fail p99. |
| Build-04 first coverage attempt | Aborted before intervals because actual viewport drifted to 2248×1290. |
| Build-04 coverage retry | Stopped after seven intervals when default hill control was about 10 FPS. Original cleanup failure and later successful restoration preserved. |
| Same slow process, ambient .15 versus zero | 10.08 versus 10.03 FPS. New ambient setting does not explain the slowdown in that run. `ambient-cost-04b/`. |
| Fresh build-04 process, final control | **69.03 FPS average; p50 14.05, p95 16.63, p99 31.51, max 44.64 ms; four hitches >33 ms** over 10.02 s/692 frames. Average cost recovered, p99 still fails. `fresh-control-04/report.json`. |

The old slow process had initially large/tall window dimensions and subsequent
resizes. A fresh process was 1920×1080 from observed frame 1. Process/window or host
state is implicated; the precise cause is **not proven**. Current-build stills were
already slow before the later observed user movement. Do not blame only that movement
or declare a fixed rendering regression based on the restart.

Potential next diagnostic: record actual RTHandle/render-texture allocation sizes
before/after a controlled window resize. Installed core APIs expose `RTHandles.maxWidth`,
`maxHeight` and `rtHandleProperties`; these were only read from package source,
**no diagnostic code was added**. First obtain repeatable fresh controls and keep
Editor/Blender builds/bakes separate from timing.

### Window/capture pitfalls

The tool shell does not inherit `DISPLAY`/`WAYLAND_DISPLAY`. Missing DISPLAY caused
an invalid offscreen build-04 capture, retained in `candidate-native-04/`.
Other early tiled windows produced black strips/clipped HUD while Unity reported
1920×1080. Validate PNG/backbuffer, live viewport and owned-window logical size.
On the observed 1.25-scale display, 1536×864 logical gave 1920×1080 native.

The scoped Hyprland resize must specify `relative=false`. Do not modify global
desktop configuration or assume the old Hyprland instance ID/window address still
exists. Read the Omarchy skill for any new window operation. Preserve unrelated
windows/focus and use fresh QA preferences. `--background` is a static diagnostic
option, not evidence of real keyboard input.

## Independent visual criticism

`critic/` preserves locked preferences, decoded mappings, source provenance and
rejections. Anonymous internal candidate labels were concealed until scores were
written. Game identities remain recognizable and ARK promotional settings are
unknown; **these are not scientifically blind or equal-hardware cross-game tests**.

- Leaf-edge repair preferred in all four Editor views, but fine-edge noise and dark
  clusters remained. Native ambient .15/.25 slightly preferred over zero in three
  close views; hill tied and no whole-point quality score increased.
- Original versus preserved LOD1 shadow casters tied in all five inspected native
  pairs. This is only a static lack of a visual veto; fine moving dapple is unqualified.
- Current player portrait: face **2/5**, solid hair/beard shells **1/5**, armour and
  hands **2/5**, overall silhouette about **3/5**. Guard material response about
  **2/5**. Static boot contact did not prove persistent floating. Motion unscored.
- Environment material detail/light/depth/density around **2/5**. Official ARK
  courtyard reference remains stronger. Gate pier texture is visibly soft at close
  range. `cam_fidelity_guard` is partly blocked by the player and needs a better
  review angle; do not mistake that composition problem for mesh intersection.

Read `critic/current-build04-character-review.md`, `critic/player-source-audit.md`,
`critic/native-motion-review-matrix.md` and `critic/next-ground-intervention.md`.
Player source/runtime metadata match: 17,522 vertices, 10,391 triangles, 24 joints,
no morph targets, 4096² texture. Current material is albedo-only URP, smoothness .25,
metallic zero; no authored normal/roughness/AO maps. There is no identified discarded
high-detail player mesh to recover. Head/hair/beard silhouette and semantic material
work must preserve supplied identity, skeleton and role.

`cross-game-comparison-02/pair.jpg` is a new randomized A/B side-by-side of current
hill and official ARK courtyard captures. Only uniform scaling/layout was used.
`mapping.json` records originals/hashes. **The fresh reviewer was never started**
because the user stopped immediately after the pair was created.

## Staged paving work — not installed

The active paving normal source is byte-identical to its colour texture. Grayscale
normal conversion turns mineral colour into relief. Ground audit:
`ground-audit/README.md`, source geometry/UV/collider records alongside it.

Rendering specialist authored physical joint height, tangent normal and roughness
through live Blender MCP. Current source candidate:
`art/quality_20260926/west-gate-paving-v1/periodic-v2/manifest.json`.
It retains original 1254² albedo bytes, 6 m repeat/209 source texels per metre, shallow
6 mm joints, eased edges and quiet independent slab-top relief. It includes full
maps, recipes, bake/validation records and a 62.55 MB editable packed `.blend`.
Earlier failed and overshooting versions are retained, not import candidates.

The critic permits a controlled native audition, **not acceptance**. Inspect the
small ribbed trace near tile x0–12/y390–485 at grazing light. Derivative error remains
localized near steep joints; compression, mip selection, tiling and actual relief
orientation must be checked in Unity/native views. See `critic/paving-mask-v2.md`.

Agreed next workflow: three matched native conditions on the existing single
`Paving Local wear` material: original, authored normal only, then normal plus packed
roughness. Preserve albedo/tint/UV/wear, every mesh and collider. A material-property
edit does not require rebuilding chunks; assigning different materials or changing
source geometry does. The earlier 8×12 m split-mesh/local shader proposal is deferred.

Three disabled camera positions are fully planned and read-only collision-probed
in `art/quality_20260926/ground-review-cameras/plan.json`: threshold, paving close-up
and shaded-facing pier. All 39 sampled camera positions cleared a 0.2 m sphere;
adjacent ground shade remains unverified. **No camera objects were created.**

Two unexecuted MCP batch requests are staged outside Assets:

- `ground-review-cameras/install-request.json`: add only those saved disabled
  cameras, preserve scene backup and chunk fingerprint. Local API probe found only
  obsolete-overload warnings. Recheck live scene/instance before use.
- `west-gate-paving-v1/normal-only-install-request.json`: guarded backup/import and
  normal-only assignment. **Known compile error, not ready to execute:**
  `Texture.activeTextureColorSpace` is inaccessible in installed Unity (CS0122).
  Replace that reporting access with a public importer property, then validate the
  request. `convertToNormalmap` spelling was confirmed correct. Probe records are
  in `west-gate-paving-v1/staging-review/`. Neither request was altered by the reviewer.

Build/capture the unchanged-paving baseline with saved cameras **before importing
and assigning the candidate**. Import normal as linear NormalMap, no grayscale
conversion/no green flip; preserve 1254 dimensions (NPOT None), normal strength 1.
Packed map is linear red=0/alpha=1−roughness, smoothness multiplier 1 for the second
candidate. The manifest records repeat/mip/aniso/compression settings. Keep originals
and restore the source material if independent native review rejects the candidate.

## Process/tool state at handoff

All agents have stopped implementation. Goal is paused. Native input ownership is
clear: no runner was started after fresh control, no held keys/buttons or changed
focus, no pending `command.json`, last acknowledgement successful. Clock and follow
camera were restored before shutdown.

Root closed only verified task-owned processes during wrap-up:

- Fresh development player PID1171527, stopped successfully.
- Recovered Blender PID1102568 on private display :93, stopped after author confirmed
  all authored work is in the complete `periodic-v2/Paving-authoring.blend` copy.
- Private Xvfb PID1071970, stopped after Blender. No system package was installed.

Previous Unity Editor PID987320 was also absent at the final read-only audit;
**root did not signal it**. No matching AthenHill project process was found. Rediscover
or open the Editor before resuming; do not assume the old MCP instance is live.
See `handoff-process-state.json` and `fresh-control-04/handoff-shutdown.json`.
No session lock was bypassed. Desktop was observed unlocked before stop; check again
when resuming. Do not restore old DPMS/window state over the user's current session.

Working Unity transport was `http://127.0.0.1:18081/mcp`, accessed by
`uv run --offline --with fastmcp python unity/tools/unity_client.py`.
Old instance was `AthenHill@7f7f353bae1a07d0`; inspect instances and scene state first.
Batch files contain `execute_code` with C#6 method bodies. A build menu request can
disconnect MCP while the build continues: watch `Captures/linux-build.json` and
Editor.log rather than firing a duplicate build. Native mailbox accepts only one
writer per folder. The live Blender MCP must be reconnected before future authoring.

## Suggested resumption order, when requested

1. Re-establish clean saved Editor/native state and fresh display-correct player.
   Run the outstanding real-input controls/city loop/traversal/Reduced Motion tests,
   record moving footage and logs. Use the staged runtime-bound hotbar-coordinate
   correction; the old hard-coded point lies above the current bar. Preserve failures.
2. Reproduce/diagnose the slow-process case and qualify a warmed representative
   native traversal. Targets remain average ≥60 FPS **and** p99 ≤16.67 ms. Do not
   promote longer shadows or LOD shadow substitutions on current failed evidence.
3. Finish the paving comparison described above, including native grazing views
   and independent anonymous preferences. Make the smallest accepted material edit.
4. Undertake a bounded player head/hair/beard/material pass from the source audit,
   then matched portrait/body sun/shade and moving rig review. Do not promise that
   adding texture resolution alone repairs anatomy or silhouette.
5. Continue the representative-street/landmark work from actual native weaknesses,
   with saved editable assets, original provenance and fresh evidence each iteration.

Do not re-run historical installers over edited content or treat this list as
approval to start every long-term gameplay system. The next AI should report the
remaining gap honestly and preserve the user's stop until they request continuation.
