# Meshy ring gate replacement — 8 September 2026

The south-court gate is replaced in the saved Unity scene and both native Linux
builds. The accepted Meshy 7 model follows the user's circular gunmetal ring,
sandstone clamps, cyan insets, control console and stone platform. It has 12,009
triangles and is normalized to 6.7 m tall. A reused 44-triangle city step provides
a tread wide enough for the player capsule. The complete editable prefab is
12,053 triangles with two colliders; its central aperture is unobstructed.

The 116 legacy gate/platform parts remain inactive under AuthoredWorld and are
excluded from rebuilt render chunks. Ring interaction position, offline message
and hum remain intact. The debug arrival marker now lands in front of the console.
Serialized player, NPC, animation, input, audio and session components are
unchanged (`gameplay-preservation.json`).

## Verification

- Final development player: real keyboard movement out of the platform and back
  up the steps, grounded throughout; return within 4 cm of the starting position,
  with no camera overlaps. E interaction and the automatic offline bark passed;
  Ring hum remained playing.
- Full native city loop passed: four conversations, modal movement blocking,
  buying a flask, selling scrap, Lattice travel, pause/settings, inventory/notes
  and reset. No runtime exceptions were logged.
- Final release launched, rendered, accepted keyboard movement/pause and ignored
  the development QA flag. See `release/report.json`.
- Both builds succeeded. Build logs retain licensing handshake/access-token
  messages and collision pre-bake warnings; these did not prevent building.
- Final screenshots: `editor/cam_whompah.png`, `editor/cam_ring_front.png` and the
  five native captures. `native-initial` records the rejected narrow-step check;
  `native-rejected-remesh` is not the accepted visual asset.

## Rendering

1080p, RTX 3060, i9-10850K, Linux/OpenGL; uncapped development player:

| View | Average FPS | p99 frame time | Verified GL draws | Submitted triangles |
|---|---:|---:|---:|---:|
| Existing gate camera | 535 | 2.43 ms | 40 | 130,894 |
| Front inspection | 612 | 2.21 ms | 37 | 129,650 |

FPS and GL tracing are separate runs. Unity's draw recorder returned zero, so
draw counts come from apitrace. Its sampled frames were aligned to Unity frame
numbers and cross-checked against triangle counts (`gl-trace/view-counts.json`).
Gate views meet the 80-draw/250k-submitted-triangle target. The wider city's
strict all-pass budget remains unqualified: follow peaked at 88 draws/311,285
submitted triangles, and hill at 81/~264,517. Hill counts were identical with
the 6k and 12k gate and the gate is outside that camera's frustum. These totals
include repeated render passes; the five fixed cameras contain at most 133,405
frustum-visible geometry triangles before repeated passes. This desktop run does
not qualify a medium laptop GPU.

## Meshy provenance

Generation `01a080b2-d7b6-7727-93b1-f10c1aa030a7`: 30 credits, accepted. Remesh
`01a080bc-e9d3-71b6-8a69-d87adc1df63e`: 5 credits, rejected because it damaged
the console, bollards and base. The clean original is the shipped model. Total:
35 credits. Source references, downloads, parameters and hashes are preserved in
`meshy/ring-gate-v1`. The user's standing Meshy cost approval is saved in AGENTS.md.

Re-run with `uv run --with python-xlib python unity/tools/check_ring_gate.py`.
The release check uses `ATHEN_RELEASE_EVIDENCE` with
`unity/tools/check_release_smoke.py`. Trace extra gate cameras using
`ATHEN_TRACE_VIEWS` with `unity/tools/trace_draws.py`.
