# Player motion presentation — 26 September 2026

Status: implemented, compiled, and passed the Unity EditMode suite (initially
45/45; the later shadow-hierarchy integration passed the expanded 50/50 suite).
Rebuilt native motion review is still required. This is a focused temporal-stability fix, not AAA
animation or physics acceptance.

## Evidenced defect and change

The saved `ProjectSettings/TimeManager.asset` runs physics at 0.02 seconds (50 Hz).
`PlayerMotor` previously moved its CharacterController and visible actor only in
`FixedUpdate`; `FollowCamera.LateUpdate` read the unsmoothed controller position.
Consequently the tracked actor/camera positions repeated between fixed steps and
jumped on the next one, even at the target 60 Hz and higher rendering rates.
This is a source-level timing finding; no before/after native video is claimed here.

`PlayerRenderPose` retains the last two completed controller positions and visual
headings. `PlayerMotor.LateUpdate` interpolates the existing visual child, and
`FollowCamera` independently reads the same interpolated position before running
its existing collision sweep. No script execution order change is needed.

Collision, interaction distances, movement speeds, jump integration, animation
state selection and QA physics traces still use the real controller transform.
The simulation-facing visual pose is restored before every fixed step, avoiding
feedback of interpolated rotation into turning. Authored local position offsets
are retained. Teleport resets both samples immediately; disable restores the
visual's simulation pose. Teleport also resets the formerly stale speed value.

Interpolation deliberately introduces one physics step (20 ms at this project's
settings) of presentation delay, without delaying input consumption or collision.
It clamps to completed poses rather than predicting movement through obstacles.
Mouse orbit remains responsive at rendering cadence. Pause uses scaled time, so
presentation does not drift while the game is paused. Existing first-person
shadow visibility, camera boom sweep and zoom remain in place.

## Validation so far

- Offline C# compilation passed with the installed Unity 6000.6.0f1 Editor,
  development-player and release-player response files, without warnings.
- The complete EditMode suite passed in the live Unity 6000.6.0f1 Editor:
  **45 passed, 0 failed, 0 skipped**, 0.214 seconds. The suite includes seven
  `PlayerRenderPoseTests` cases and four accessibility-persistence cases.
  [Raw final result](editmode-final-results.json), job
  `3de124bf22344066a25a4a5b4ef4e71f`.
- New tests exercise constant-speed motion at 30/60/144 Hz, collision-stop bounds,
  yaw wrapping, teleport reset, preservation of the collision root, and restoration
  of authored visual offsets after disable. The integration test uses actual
  Unity Transforms and the existing CharacterController component.
- `git diff --check` passed for modified tracked scripts.
- [compile-report.json](compile-report.json) records source hashes, profiles and
  log files. Compiled assemblies live only in a temporary directory. This check
  does not replace an Editor import, Unity test run or native build.

The first live run exposed two test-harness defects; its failure evidence remains
at [the original run](../editmode-tests.json). The 144 Hz delta assertion sampled
the initial partial interval before a full physics sample existed; the absolute
position-versus-time assertion passed. The lifecycle test used Unity's runtime
`SendMessage` dispatcher in EditMode, causing `ShouldRunBehaviour()` assertions.
The corrected tests use the actual full-interval boundary and direct reflection
calls for the lifecycle methods, without ignoring logs or changing runtime logic.
One intermediate rerun was orphaned by a pending domain reload; its records and
the supported clear-orphan operation are retained in this folder.

## Reduced-motion preference

The same review exposed that Reduced Motion reset on every launch. `GameSettings`
now saves it under the existing settings prefix, and `GameSession.Awake` restores
it before atmosphere and HUD startup. Unset preferences use the serialized scene
default. Toggle flushes the choice immediately, and opted-in development QA uses
the existing `QA.` prefix. The prior GameSession focus-loss fix is preserved.

Four real-PlayerPrefs EditMode tests passed: unset default/no implicit write,
explicit on/off across replacement settings instances, normal/QA isolation, and
early session restoration followed by toggle persistence. Tests use unique
temporary preference namespaces and delete their own keys afterward. Native
toggle/relaunch verification is still required; tests do not claim it occurred.

## Integration and review

Run the project's EditMode tests, build through the existing native workflow, and
capture a matched real-input walking/running route at native 1080p. Compare stable
world edges during translation in both follow and first-person cameras, especially
with a 60 FPS cap. Exercise reversals, stairs, a jump/landing, camera collision,
pause/resume and Return to West Gate. Reject trails after teleport, collision-root
changes, new clipping, unstable feet or remaining camera stutter.

The existing `unity/evidence/quality/20260908/movement/check_character_motion.py`
provides a real-input jump/modal/stairs/first-person regression route; its dated
source can be run against a newly identified build and a fresh evidence directory.
Its physical checks alone cannot establish temporal or animation quality.

The initial code pass changed no scene or asset. A subsequent topology review
found that the retained shadow-only capsule was a sibling of the interpolated
MeshyPlayer visual. It would still advance at the physics cadence. The guarded
live-Editor followup reparented that existing object under MeshyPlayer, preserving
world pose, identity, material, mesh, renderer flags and the collision root.
[Before/after evidence and exact scene diff](proxy-reparent/verification.json)
show only the parent and its corresponding child/prefab-override records changed.
The actual 10,391-triangle player skin already casts shadows; the retained
832-triangle capsule was not substituted for it by this pass.

A saved-scene preview test now checks that enabled shadow-only proxies are within
the presentation hierarchy, have no colliders and retain the supplied player
prefab. The expanded full suite passed 50/50 after shader import, with the active
scene still clean; [raw result](proxy-reparent/editmode-results.json).
Actor roles, routes, gameplay data, dependencies, graphics API and prior
uncommitted work are preserved.

Unity 6.6 documentation consulted:
[interpolation](https://docs.unity3d.com/6000.6/Documentation/Manual/rigidbody-interpolation.html),
[render time](https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Time-timeAsDouble.html),
[fixed time](https://docs.unity3d.com/6000.6/Documentation/ScriptReference/Time-fixedTimeAsDouble.html).
The Rigidbody documentation explains the timing tradeoff; this project's
CharacterController requires its own presentation interpolation.
