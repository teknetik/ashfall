# Combined test, batch 1 (1 Oct 2026)

Batch 1 = perimeter walls, hydroponics, training range, night life, basin mountains, city paving (each installed in the
saved scene by its own pass; see each pass's README). First combined test under the batched-verification process
(AGENTS.md §7). Build: `Builds/batch-batch1` (development, -nographics build of the saved scene at 15:03). Baseline:
`Builds/base-3ebd801b`, built from a sparse worktree of commit 3ebd801b (the 30 Sep passes) with a reflinked Library.
Machine: RTX 3060 12 GB / i9-10850K, OpenGL, 1920×1080 window, High preset, render scale 100 %; desktop apps open
(~2.3 GB VRAM). PC texture streaming budget 5632 MB in batch 1 (paving pass; pending Carl's decision), 4096 in the baseline.

## Results
- Range tutorial check (`unity/tools/check_checkpoint.py`, real input): **PASS 10/10** (`tutorial/report.json`).
- City loop: **PASS** on retry (`cityloop/`, 15:35). First attempt was killed by the VRAM watchdog (old 11.7 GB line,
  `cityloop-killed-vram/`); second failed with an unacknowledged `cameraYaw` command on the walk to Linn with no
  exception in Player.log (`cityloop-fail-ack-linn/`) — treated as a transient stall; the retry passed.
- Lookbook: 80 cameras (10 standard + 70 review cameras from today's passes) × 13:00 / 20:30 = 160 captures, 0 errors,
  in five 16-camera chunks (`lookbook-p01…p05`, contact sheets `sheet-h13.00.jpg` / `sheet-h20.50.jpg`). The single
  80-camera run was VRAM-killed (`lookbook-killed-vram/`).
- Frame time, baseline → batch 1, alternating runs, 2 per arm, 8 s profiles (`ab-vs-base/ab-summary.json`):

| View | 13:00 | 20:30 |
|---|---|---|
| cam_hill | 66.1 → 64.2 fps, p50 +0.43 ms | 72.6 → 70.9 fps, p50 +0.31 ms |
| cam_avenue | p50 +0.05 ms; batch-1 runs hitch (p99 31 ms) | p50 −5.5 ms; baseline runs hitch (p99 38.5 ms) |
| cam_gate | 172.9 → 144.8 fps, p50 +1.31 ms | 176.7 → 143.9 fps, p50 +1.43 ms |

  Single-arm profiles in the same session: `profile-summary.json`. The avenue view's averages are dominated by hitches
  shortly after player load in both builds; judge it with a warmed walking traversal (planned for the final test).
  GPU time is unavailable in this player.

## Notes
- Native runs now use ~9.4–9.5 GB VRAM (streaming budget 5632 MB); with the desktop that sits at the watchdog line.
  A texture-memory pass (uncompressed glTF/Meshy textures, ~4.4 GB) is running in batch 2.
