# Static shadow timing results — 26 September 2026

Both requested runs completed. This is a short stationary frame-time comparison, not traversal, GPU-timestamp measurement, visual acceptance or performance qualification.

The 96 m/four-cascade and all tested 48/64/96 m/two-cascade settings miss the sampled 60 FPS/p99 ≤16.67 ms criterion in hill and avenue views. Do not promote them as 60 FPS defaults. This performance rejection is not an art-quality judgment. The existing setting also had one canopy p99 failure; no baseline qualification is claimed.

| Camera | Distance / cascades | Interval | Average FPS | p99 ms | Sample criterion |
| --- | --- | ---: | ---: | ---: | --- |
| cam_hill | 18 m / 1 | 1 | 74.49 | 14.55 | Met in interval |
| cam_hill | 96 m / 4 | 2 | 42.03 | 25.78 | Missed |
| cam_hill | 96 m / 4 | 3 | 41.89 | 25.48 | Missed |
| cam_hill | 18 m / 1 | 4 | 74.52 | 14.47 | Met in interval |
| cam_avenue | 18 m / 1 | 1 | 68.91 | 16.05 | Met in interval |
| cam_avenue | 96 m / 4 | 2 | 41.76 | 25.96 | Missed |
| cam_avenue | 96 m / 4 | 3 | 42.81 | 25.28 | Missed |
| cam_avenue | 18 m / 1 | 4 | 68.70 | 15.83 | Met in interval |
| cam_tree_canopy_below | 18 m / 1 | 1 | 86.99 | 12.45 | Met in interval |
| cam_tree_canopy_below | 96 m / 4 | 2 | 66.92 | 16.50 | Met in interval |
| cam_tree_canopy_below | 96 m / 4 | 3 | 66.78 | 16.37 | Met in interval |
| cam_tree_canopy_below | 18 m / 1 | 4 | 86.23 | 17.82 | Missed |
| cam_hill | 48 m / 2 | 1 | 59.74 | 18.10 | Missed |
| cam_hill | 64 m / 2 | 2 | 56.66 | 19.20 | Missed |
| cam_hill | 96 m / 2 | 3 | 52.93 | 20.40 | Missed |
| cam_avenue | 48 m / 2 | 1 | 56.87 | 18.96 | Missed |
| cam_avenue | 64 m / 2 | 2 | 52.32 | 20.87 | Missed |
| cam_avenue | 96 m / 2 | 3 | 51.66 | 20.73 | Missed |

Total retained summary data: 13,290 frames over 219.01 seconds. Every raw interval also retains its first pre-start-delta sample; only that one boundary sample is omitted from each summary.

Profiles: 1920×1080 actual live output, RTX 3060 12 GB / i9-10850K, NVIDIA610.57.04/OpenGL4.5, render scale1, 4×MSAA, 4096 shadow map, full textures, post-processing on, uncapped/VSync0. Time-of-day12 is paused; nine actors and normal HUD remain active. Editor is alive/idle and desktop locked; background diagnostics are explicitly enabled. Ambient animation/effects keep running, so scene phases differ.

GPU time is unavailable (`gpuMs=0` raw, null in summary). Render-thread, draw and batch counters are also unavailable even though draw recorder reports Valid. CPU/main-thread timing, triangle submissions and SetPass are recorded; CPU/main time includes waits and cannot identify an isolated GPU cost. Triangle totals include render passes.

Per-PID driver framebuffer allocation was3072MiB; OS RSS and Unity memory are recorded separately before/after intervals. Other applications contribute to total device usage. Player.log exception/shader/assertion marker search returned no matches.

Both runs restored18m/one cascade and original clock values and returned the camera to follow. No preferences, runtime source, assets, build or Editor scene were changed. The native player remains owned by root.

Evidence: [first-run report](../static-shadow-timing-01/report.json), [followup report](report.json), [machine-readable summary](comparison-summary.json), [review and exact protocol](../static-shadow-timing-01/review.md). Each report links unique raw frame files and metadata.
