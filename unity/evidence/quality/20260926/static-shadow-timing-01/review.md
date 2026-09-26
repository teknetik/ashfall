# Independent correctness review and static shadow timing

26 September 2026. Gameplay/physics agent review of the current working tree.
The parent owns Editor and build integration. This agent did not mutate the scene,
runtime source, materials or build during this review/timing run.

## Concrete remaining finding

The saved scene has an active `Player shadow proxy`, with its enabled renderer
set to `ShadowsOnly`, directly below the physics root. Its Transform is
1049059654, parent 175973427; the MeshyPlayer visual is sibling
2422505734151740906. See `AthenHill.unity` around line 95431.

`PlayerMotor.LateUpdate` interpolates only its MeshyPlayer visual. The shadow proxy
therefore remains at the latest physics pose, while the body and follow camera
use the interpolated pose. At 6 m/s and the authored 20 ms step, the proxy can be
up to 12 cm ahead and advances at 50 Hz. This is a presentation/grounding risk,
not a change to the collision root. The new tests model a single visual child and
do not catch this sibling-shadow topology. Fix by applying the same presentation
translation to that proxy, or deliberately place it below a suitable visual
wrapper through the Editor. Preserve its authored offset and shadow-only state.
No such change was made by this review. Stationary shadow timing is unaffected.

## Other reviewed paths

- `NativeVisualReview` validates finite distance and cascade counts 1/2/4,
  remembers original distance and cascade count on first use, and restores both.
  `GameSettings` owns a runtime clone of the URP asset; the native diagnostic
  changes that clone. No source asset or PlayerPrefs write occurs in the review.
  The development/explicit-QA gates remain in place.
- Do not edit video settings during an active audition: its restore values are
  captured before the audition and could overwrite a later video change.
  `reviewReset` also returns the camera to follow. These are operator lifecycle
  constraints, not new failures in the requested isolated comparison.
- Reduced Motion reads after `GameSettings.Awake`: its execution order is -100,
  so the QA prefix is initialized before the default-order `GameSession.Awake`.
  Adding a missing active settings component also runs its Awake before reading.
  The authored default remains in use when unset; toggle flushes immediately.
- The four persistence tests use real PlayerPrefs and unique private keys, but
  replacement components share the same process. They do not prove an OS-level
  relaunch or the real command-line-to-prefix path. Native toggle/relaunch QA
  remains required.
- Seven presentation tests cover cadence mathematics, stop clamping, yaw seams,
  teleport reset and actual Transform lifecycle methods. Reflection invocation in
  EditMode does not exercise natural PlayerLoop ordering, physics contacts,
  stairs, animation feet, camera wall proximity or pause/resume in the player.
  All 45 EditMode tests passed in the separately retained live Unity result.
- Existing camera sweep and input logic remain intact. Scaled render time stops
  presentation while paused. Rendering adds one physics step of presentation
  latency; no input/physics step is delayed.
- Runtime swapping of `visual` or `target` references would require refreshing
  the cached presentation/camera references. Current runtime source does not do
  this; existing assignments are serialized or Editor import operations.

## Exact timing protocol

The parent authorized sole command ownership of development player PID 1037608,
already writing `candidate-native-02`. The executable is not relaunched. The
runner checks actual snapshots for 1920×1080, Play state, zero player speed,
render scale 1, 4× MSAA, full textures, 4096 shadow resolution, VSync off, uncapped
frame rate, no settings preview and all nine actor components. It records the
executable and managed-assembly hashes, available environment, settings and actors.

The executable runner in this folder uses `unity/tools/native_client.py`:

```python
await client.command({"action": "timePause", "paused": True})
await client.command({"action": "timeSet", "hour": 12})
for camera in ["cam_hill", "cam_avenue", "cam_tree_canopy_below"]:
    await client.command({"action": "view", "camera": camera})
    for distance, cascades in [(18, 1), (96, 4), (96, 4), (18, 1)]:
        await client.command({"action": "reviewTree",
                              "shadowDistance": distance,
                              "shadowCascades": cascades})
        await asyncio.sleep(3)   # unmeasured settling
        await client.command({"action": "settingsSnapshot"})
        # Validate/retain actual settings and snapshot before each interval.
        await client.command({"action": "profileStart"})
        await asyncio.sleep(12)
        await client.command({"action": "profileStop"})
        # Immediately copy profile.json to a unique interval file.
        # Snapshot and memory collection occur outside the timed interval.
```

The client adds a unique ID, atomically renames `command.tmp` to `command.json`,
and waits for matching `ack.json` for up to 10 seconds. All writes are serial;
there must be exactly one writer. Failures write `qa-error.json` and do not ack.
The runner checks that error file after commands. Each profile start clears
in-memory samples; each stop replaces `profile.json`, so raw intervals are copied
before starting the next. Existing profile evidence is archived before the run.

The first frame remains in each raw file, but its summary excludes that one
sample because `profileStart` runs after the frame's delta began. Both raw count
and retained count are reported. No other hitches or samples are discarded.
All frame timing is uncapped and separate from screenshots/video. Afterward the
runner restores the original shadow values and clock values; camera returns to
follow, and player position stays unchanged.

## Counter limits

This is a short, stationary native cost comparison, **not real-input traversal,
functional acceptance, visual acceptance, or performance qualification**.
Background operation and the locked desktop are recorded; the Editor remains
alive/idle and can contend for resources. Day/night is fixed, but actor animation,
walkers, foliage, dust and audio remain active at differing phases. AB/BA order
reduces monotonic warmup/temperature bias without making those phases identical.

`dt` is frame wall time, and Main Thread includes waits. The installed run reports
an invalid Render Thread recorder. FrameTimingManager may supply no usable GPU
time; nonpositive CPU/GPU counters are null, never zero cost. Its latest timing is
asynchronous and this recorder has no frame timestamp, so repeated GPU samples
cannot be deduplicated or exactly aligned with `dt`. Counter-positive coverage
is recorded rather than implying full independent GPU frame coverage.

Draw calls, batches and SetPass are distinct. Submitted triangle totals include
shadow/depth/color passes and are not visible geometry. Memory snapshots separate
Unity allocation/texture estimates, OS RSS, and driver framebuffer memory; none
is substituted for another. The driver's per-PID memory may be unavailable.
Launch `environment.json` and saved Video dimensions can be stale after resize;
the live per-interval snapshots establish the actual resolution.

Three-second warmup and twelve-second samples provide an exploratory comparison.
They cannot establish sustained 60 FPS/p99 or loading, movement, shop and travel
behavior. Timing results belong only to the recorded executable/assets/profile.
