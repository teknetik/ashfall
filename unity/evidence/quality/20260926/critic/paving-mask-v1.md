# Paving joint-mask semantic review — 26 September 2026

**The main joint network is captured correctly, with no gross false classification of dark slab interiors. Refine the small holes and speckles within the joint corridors before treating the mask as a stable height-bake input.** This is a technical-map review only: no Unity/Blender operation or capture was performed and no in-game material/AAA acceptance follows.

Inspected original files in `art/quality_20260926/west-gate-paving-v1/refined-joints/`: `Albedo-preserved.png`, `Joint-review-overlay.png`, `Joint-classification.png`, `Roughness.png`, `Normal-OpenGL.png`. Coordinates below are approximate pixels in the 1254 × 1254 source, origin at top left.

| Priority | Region | Semantic finding / action |
| --- | --- | --- |
| First refinement | x930–1240, y154–178; x535–800, y734–751; x240–460, y1172–1197 | The mask has multiple dark holes/short gaps inside the otherwise correctly located joint bed. The corresponding albedo contains light granules inside the dark seam. Do not automatically promote those brighter granules to full slab-top height. Inspect/fill enclosed joint-bed holes for the semantic region, preserving any intended granular relief separately. The same small interruptions are visible in roughness/normal outputs. |
| Secondary cleanup | x430–455, y30–155; x794–814, y440–570; x94–114, y605–720 | Joint boundaries have small islands, hooks and abrupt width fluctuations. Many correspond to genuine chipped edges, so preserve larger albedo-supported chips. Remove only isolated threshold specks that do not represent a separate slab edge; avoid globally straightening the joints. |
| Retain | Central darker slab, approximately x548–790, y326–722; lower-left darker slab, x225–414, y946–1154 | Broad gray/brown mineral coloration remains excluded from the joint class. This is correct: it should not become a deep depression merely because it is darker. I see no large accidental interior joint island. |
| Retain as a separate feature class | Diagonal crack across lower-right slab, roughly (822,775) to (1174,908); upper-left hairline cracks | These cracks are excluded from the main slab-joint mask. That is semantically appropriate for a joint-depth/bevel bake. If wanted later, cracks need their own much smaller relief treatment; do not feed them into the same six-millimetre joint-depth class. |

I do not see a fully missed major slab boundary or an invented full-width joint through a slab. The narrow vertical seam near x652, y175–304 is captured; its thinness follows the source. The green overlay follows the principal horizontal joints near y166, y309, y594, y742, y927 and y1182, plus the visible vertical dividers. Masked coverage does not spread broadly into the large stone faces.

The magenta guard contains a few small boundary/continuation marks where no green class is present (for example near the top at x1180 and at the bottom continuation around x1180). These do not appear as white joint regions in `Joint-classification.png`; do not mistake the guard itself for a false classified seam.

At the supplied six-metre/1254-pixel scale, one pixel spans about 4.8 mm, so one-to-three-pixel binary flecks correspond to roughly 5–14 mm features. Their semantic treatment matters when assigned full joint depth, even if the technical maps look tidy at fit-to-screen scale. This calculation uses the author-provided physical scale; it does not verify its eventual Unity UV scale.

The author separately identified periodic edge-continuity weakness. That remains an unresolved bake/import prerequisite and was not accepted by this semantic review. The inspected normal/roughness maps show where the classification propagates, but cannot establish final depth, smoothness response, normal convention in Unity, tiling stability or visual quality under native lighting.

Disposition: **main mask semantics are usable as a refinement base; correct seam-interior holes/noise and periodic continuity before Unity audition.**
