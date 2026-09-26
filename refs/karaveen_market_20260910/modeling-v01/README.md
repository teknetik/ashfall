# Karaveen stall modeling references — v01

Created: 2026-09-10. Generated with built-in image_gen from the user-liked [market concept](../karaveen-market-v01.png). These sheets extend that concept; they replace no earlier artwork or Unity assets.

## Sheets

Each PNG contains customer-facing front, right-side and rear views, with its exact generation prompt in the adjacent Markdown file.

- [Food and produce](01-food-produce-turnaround-v01.png)
- [Water and provisions](02-water-provisions-turnaround-v01.png)
- [Caravan repairs](03-caravan-repairs-turnaround-v01.png)
- [Travelling artisan](04-travelling-artisan-turnaround-v01.png)

## Proposed dimensions

The images are concept references, not measured drawings. Use these numeric design targets when reconciling views in Blender:

| Part | Target |
| --- | --- |
| Main frame footprint | 3.00 m wide × 2.40 m deep |
| Canopy including overhang | 3.30 m wide × 2.70 m deep |
| Low eave clearance | 2.30 m |
| Maximum roof height | 2.65 m |
| Front counter | 2.60 m wide × 0.65 m deep × 0.95 m high |
| Side vendor entry | At least 0.90 m clear |
| Rear shelves | At most 0.40 m deep |
| Clear vendor working depth | At least 1.00 m |

Food uses the final sheet's pyramidal/hipped canopy; provisions uses a shallow gabled roof. Repairs and artisan use roofs sloping from the higher rear to the lower front. Four primary corner posts, removable weighted feet, clamped crossbars, detachable canvas and separate counters form the shared construction. Merchandise, containers, tools and cloth displays should remain separately editable objects.

## Construction decisions after image review

- Food: the corrected sheet depicts a pyramidal/hipped roof, adopted for modeling instead of the initial prompt's gable. All four eaves stay at 2.30 m and the central apex reaches 2.65 m.
- Provisions: the side view understates the gable ridge height; model the ridge at 2.65 m and eaves at 2.30 m. Use a compact reservoir at the rear, approximately 0.80 m wide × 0.45 m deep × 0.85 m high, so it does not fill the working lane.
- Repairs: the full-width rear tool rack has a plain exterior back. Use the open side for vendor access. The revision fixes the initial half-width rear wall disagreement.
- Artisan: use the side elevation as roof authority: front low edge 2.30 m, rear high edge 2.65 m. The front/back canopy silhouettes are approximate.
- All rear views show the backs of the same front counters, not additional full-width rear counters. Preserve at least 1.00 m clear working depth and 0.90 m side access.

Initial prompts are stored beside each image. Targeted final edits are recorded in [revision-prompts.md](revision-prompts.md).

## Blender reference setup

Use metres, X for width, Y for depth and Z for up. Customer-facing front is toward negative Y. Front view looks along positive Y; right-side view looks along negative X; back view looks along negative Y. Align the ground to Z = 0 and frame centre to X = Y = 0. Use the known frame footprint and counter height to register the reference views.

Rear construction and hidden surfaces are proposed design extensions because they are not visible in the original scene. Generated views can disagree in small details; use the dimensional targets and a single coherent frame rather than tracing contradictions into the mesh. Check post positions, roof pitch, left/right reversal at the back, shelf backs and entry clearance while building.
