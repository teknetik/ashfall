# Karaveen artisan stall — empty Blender source

Created 10 September 2026 through the live Blender MCP connection in Blender 4.5.13 LTS.

[Open the Blender file](karaveen-artisan-stall-v01.blend). The active scene is `KA_Artisan_Stall_v01`.

The model includes the sloping canvas canopy, seams, repair patches, eyelets and lashings, four telescoping metal uprights with clamps and weighted feet, a two-cupboard service counter, an empty display shelf and an empty textile rail. Rugs, pottery, plants and all other merchandise are omitted. Nothing was imported into Unity.

## Controls

Select `KA_Artisan_Rig` and use its object custom properties:

| Control | Action |
| --- | --- |
| `left_door_open` | Left cupboard door, 0–105 degrees |
| `right_door_open` | Right cupboard door, 0–105 degrees |
| `canopy_billow` | Subtle pinned-edge fabric motion, 0–1 |
| `ROOT` bone in Pose Mode | Move or rotate the entire stall |

The doors use rigid bone parenting. Canvas patches and sewn details follow the same billow as the canopy. The file is saved with closed doors and zero billow. No animation is baked; controls can be keyframed in Blender.

All structural components remain separate and named. Canvas thickness, bevels and source topology remain editable. Materials are procedural PBR node graphs, so the file has no external texture dependency. The concept sheet is packed into the Blender file and can be selected in the Image Editor.

## Dimensions and review

Metres; X is width, Y is depth, Z is up. Customers approach from negative Y. Frame footprint is 3.00 × 2.40 m; canopy is approximately 3.30 × 2.70 m. Roof front is 2.30 m and rear is 2.65 m; the sewn front valance hangs to approximately 2.06 m. Counter top is 0.95 m high. Use the side elevation's single slope where the generated concept views disagree.

- [Hero render](artisan-stall-hero-v01.png)
- [Front](artisan-stall-front-v01.png), [right side](artisan-stall-right-v01.png), [back](artisan-stall-back-v01.png)
- [Canopy detail](artisan-stall-detail-v01.png)
- [Rig demonstration](artisan-stall-rig-preview-v01.png)
- [Numerical rig checks](rig-validation-v01.json)

Native Blender review uses Cycles with OptiX on the RTX 3060, 48 samples for overall views and 96 for the detail. The studio collection is separate from the asset. These renders review the Blender source, not in-game performance or materials.

Initial renders in `review-initial/` preserve the first observed defects: inner roof rails crossed the sagging canvas, shelf posts stopped above ground, and the horizontal reference cameras showed the studio plinth edge. The final source lowers those rails, adds grounded rubber shelf feet, hides the studio ground in elevation renders, and clarifies the woven canvas finish.

## Reproduction and provenance

The accepted scene concept and generated turnaround are in [the reference folder](../../refs/karaveen_market_20260910/modeling-v01/README.md), with generation prompts and construction decisions. Geometry and materials here are original authored source.

The live MCP transport, official Blender checksum, addon revision and dependency pins are recorded in [setup.json](setup.json) and [setup-requirements.txt](setup-requirements.txt). The temporary authoring environment can be restored from those records; it is not needed to open the finished `.blend`.

Authoring scripts are executed through `mcp_client.py --code-file PATH`. On a fresh Blender session the sequence is `author_artisan_stall.py`, `fix_render_findings.py`, then `finalize_source.py`. The final step adds matching cloth-detail drivers, verifies controls and schedules the review renders. Inspect the scene before repeating authoring; the initial authoring script refuses to overwrite its existing scene.
