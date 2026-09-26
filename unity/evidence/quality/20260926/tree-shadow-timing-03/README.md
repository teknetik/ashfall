# Native tree-shadow caster comparison — build 03

The transient LOD1 caster candidate improves several sampled frame times, but **48 m/two cascades and 96 m/two cascades still miss the p99 ≤ 16.67 ms criterion in both hill and avenue views**. Neither profile should become the 60 FPS default based on this run. The candidate still needs matched native visual review; timing improvement does not establish acceptable shadow silhouettes.

All 18 intervals completed and were preserved. Original casters, 18 m/one cascade and the previous clock were restored, camera returned to follow, and mailbox ownership was released. No new exception/shader/assertion log markers appeared.

| View | Shadow profile | Original FPS | Reduced FPS | Original p99 ms | Reduced p99 ms | Reduced interval criterion |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| cam_hill | 18m / 1 | 73.75 | 74.27 | 14.87 | 14.70 | Met in interval |
| cam_hill | 48m / 2 | 60.33 | 63.28 | 17.70 | 17.08 | Missed |
| cam_hill | 96m / 2 | 52.53 | 55.60 | 20.79 | 19.70 | Missed |
| cam_avenue | 18m / 1 | 73.78 | 70.68 | 14.54 | 15.63 | Met in interval |
| cam_avenue | 48m / 2 | 58.27 | 60.96 | 18.72 | 17.67 | Missed |
| cam_avenue | 96m / 2 | 52.17 | 54.33 | 21.07 | 19.74 | Missed |
| cam_tree_canopy_below | 18m / 1 | 86.63 | 88.32 | 12.43 | 12.22 | Met in interval |
| cam_tree_canopy_below | 48m / 2 | 78.42 | 84.16 | 13.57 | 13.02 | Met in interval |
| cam_tree_canopy_below | 96m / 2 | 78.94 | 84.94 | 13.78 | 12.75 | Met in interval |

The summaries retain 15,038 frames over 216.31 s. Every raw file also preserves the first boundary frame omitted from its summary.

The candidate reports 1,845,603 shadow triangles per draw versus 3,748,776 in source LOD0, with three shadow-only renderers and all six original tree caster modes disabled during its interval. Visible source geometry/materials remain unchanged. For example, hill 48 m/two cascades submitted triangles across passes fell from about 26.3M to 22.6M. Those are submitted totals, not visible geometry.

The 18 m/one cascade avenue pair was slightly slower with the candidate, while other views improved. There is only one original/reduced pair at each camera/profile, so phase differences and drift remain possible. Do not infer a guaranteed improvement from these short samples.

Actual output 1920×1080, RTX 3060 12GB/i9-10850K, OpenGL 4.5/NVIDIA 610.57.04, render scale 1, 4× MSAA, full textures, 4096 shadow map, post-processing on, VSync 0 and uncapped. Nine actors, normal HUD, animation and effects remain active; daylight 12 is paused. The Editor stayed alive/frozen and no additional players launched during sampling. Native driver framebuffer allocation was recorded separately from Unity memory and OS RSS.

GPU timing was unavailable throughout. CPU/main-thread includes waits; draw and batch counters were unavailable as in the earlier build. No real-input traversal, functional acceptance, visual acceptance or performance qualification is claimed. Native movement and first-person checks remain separate.

See [full report](report.json), [paired data](paired-summary.json), individual raw/metadata files, and command receipts under `commands/`. Build identity is recorded in the report, including managed-assembly hash `59d2648df4ee430d39e42cc49003daf3b432ec1fed257f471f65f92a336e43fd`. Earlier build 02 performance is not attributed to build 03.
