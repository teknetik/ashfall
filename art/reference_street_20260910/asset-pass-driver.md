# Diagnostic asset-camera pass supplement — 10 September 2026

Run `capture_asset_passes.py` after a successful `capture_native_iteration.py` in
the same fresh native folder. Root remains the only native Client/input operator.
The supplement verifies the base capture's build/source identity before recording;
it will not attach new footage to a changed build. It does not launch or close an
app, operate Unity, move the player, hide the HUD, or generate synthetic imagery.

Each of six saved cameras gets one continuous seven-second movement at authored
hour 12 and another at hour 16. `--seconds` permits 6–8 seconds. The recorder is
native X11 `ffmpeg` at 1920×1080/30 Hz with the actual game at render scale 1 and
the existing MSAA4/full-source texture settings. Start/end stills are taken outside
the recording so `ScreenCapture` does not add avoidable capture stalls inside the
camera movement. These recorded diagnostics make **no player-traversal or frame
time qualification claim**; keep the base driver's real-input walk separate.

## Proposed pass vectors

All coordinates are Unity metres. An offset is added to the saved camera origin;
the named target is held throughout a smooth interpolated straight camera path.
Root must inspect the final saved origins and collision clearance before running.
The script records those camera lens/transform sources and checks actual overlap
frames; the table is not an assertion that uncreated paths are safe.

| Saved camera | Current saved origin, if present | Target | Travel offset |
| --- | --- | --- | --- |
| `cam_ground_crate` | 12.7, 1.7, −19.8 | 15.65, 1.08, −20.7 | 0, +0.2, −1.1 |
| `cam_ground_trash` | 13.4, 1.55, −22.3 | 15.4, 0.64, −21.3 | 0, −0.1, +1.2 |
| `cam_ground_scrap` | 32.4, 1.65, −5.5 | 35, 0.6, −7 | 0, −0.25, −1.2 |
| `cam_ground_scrap_back` | Root to create/inspect | 35, 0.6, −7 | 0, −0.15, +1.1 |
| `cam_canopy_top` | Root to create/inspect | 14.6, 3.6, −18.5 | 0, 0, +1.3 |
| `cam_canopy_under` | Root to create/inspect | 14.6, 3.6, −18.5 | 0, 0, +1.1 |

`--plan-file` accepts a reviewed JSON list of the same six cameras with adjusted
`target`/`offset` vectors. It preserves that plan and its hash. Offsets must be
nonzero and no longer than 4 m. NativeAssetReview independently enforces its
saved-camera restriction, target proximity, and no crossing through the target.

## Commands and evidence

The actual saved code contract is:

```json
{"action":"reviewAssetPass","camera":"cam_ground_crate","target":[15.65,1.08,-20.7],"offset":[0,0.2,-1.1],"seconds":7}
```

`reviewAssetState` returns the camera name, active flag, duration, start/end/target,
sampled frames and overlapping frames in `asset-review-state.json`. The supplement
keeps start/middle/end snapshots per movie. It requires increasing positive frame
counts, an active middle, an inactive end, the camera at its requested endpoint,
and **zero overlapping frames**. NativeAssetReview checks a 0.08 m sphere on every
active frame. Ordinary snapshots also retain their separate 0.20 m overlap query;
these diagnostic-camera checks do not establish controller traversal clearance.

Time is reset, set explicitly and paused. Before each pass, the driver polls
`timeState` until no reflection capture is pending for at least 1.2 seconds with
zero failed captures. A changed hour also requires the completed-capture counter
to advance. It records every observed state, probe texture/intensity and the final
state. Current diagnostics do not expose each probe's captured hour, so the report
states that limit and does not invent a stronger per-probe freshness assertion.

Output is separate from the base report:

- `asset-passes-report.json`, with 12 pass records and explicit qualification limits.
- `asset-passes-identity-before.json` / `asset-passes-identity-after.json`.
- `asset-pass-CAMERA-hour-HOUR.mp4`, its ffmpeg log, and start/end PNGs.
- ffprobe dimensions/duration plus hashes, exact command states, Player.log error
  scan and any native `qa-error.json` retained inside the report.

All existing files are guarded against replacement. A failed or interrupted pass
stays incomplete with its partial footage. Use a new iteration folder for another
attempt. Cleanup explicitly sends `view` with `camera: "follow"` (which cancels
NativeAssetReview), then `timeReset`, and verifies motion is inactive. Resetting
the clock alone would not stop an active pass.

## Invocation

Offline inspection needs no X11 or live app and currently reports the three
uncreated cameras as missing:

```bash
python3 art/reference_street_20260910/capture_asset_passes.py --plan
```

After root builds/launches the final iteration, creates/inspects all six cameras
and completes the base driver, invoke on the host with the existing Pillow/Xlib
environment (`exec_command` with `sandbox_permissions: "require_escalated"`):

```bash
/home/teknetik/.cache/uv/archive-v0/C-D_s9RmoL-ZML5S/bin/python art/reference_street_20260910/capture_asset_passes.py unity/evidence/reference-street/20260910/iteration-N-native
```

Offline syntax and plan checks passed. No live camera or input call was made while
preparing this driver; its first native execution is still to be verified.
