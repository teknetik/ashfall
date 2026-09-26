# Trash cloth surface plan — 10 September 2026

The first candidate should use the existing URP Lit detail path, a reviewed sack-only mask and cotton detail tiling near **10.7–10.84**. New UVs or a new shader are optional fallbacks. Source maps, mesh geometry, UV0, macro folds and noncloth material values stay intact.

The geometry is one connected pile. The central sack’s seed UV region also includes cardboard, so linked selections cannot define cloth. `diagnostics/semantic-seeds.json` gives exact source triangle/UV references, Blender-coordinate starting points for both sacks and jug/can exclusions. They are starting points, not a completed mask. A live Blender face selection must be reviewed from front/back/top/side before rasterizing a DetailMask alpha. Check UV overlap and mip gutter bleed before accepting that mask.

The measured seed regions are incomplete; the central sample includes cardboard. At the prepared uniform scale, surface-area-weighted p5/median/p95 are:

| Region | Texels/metre at 4K | UV anisotropy |
| --- | --- | --- |
| Left seed | 1070 / 1290 / 1435 | 1.04 / 1.23 / 1.87 |
| Central seed | 1030 / 1267 / 1440 | 1.05 / 1.27 / 1.86 |

At detailST10.84, median principal source-tile extents become0.266×0.321m and0.265×0.335m, close enough to the retained Book Pattern0.3m tile for an initial source audition. Only3.04%/4.25% of the sampled surface area exceeds2:1 anisotropy. This does not prove full-sack mapping, but it does not justify requiring new UVs first.

Cross-region UV seams rotate the warp direction by a median47.6°/48.3° after normal parallel transport; continuous interior edges have median4.15°/3.80°. Some boundaries lead onto noncloth surfaces, so a completed mask is needed to identify visible cloth seams. Inspect that risk with restrained fine irregular weave rather than assuming every atlas seam will show at player distance.

Keep the original roughness and metallic for the first albedo/normal audition. URP Lit has no tiled detail-roughness input. Its detail albedo neutral is shader-linear0.5: a new derivative must respect that encoding, while retaining the sack’s original beige macro color and folds. The detail normal can use the existing valid UV0 tangent basis. The DetailMask coverage is alpha, not red. Verify URP keywords through material validation.

`segmentation-plan.json` records the complete proposed sequence, evidence hashes, source provenance, constraints and acceptance checks. `diagnostics/uv-anisotropy-audit.json` records both area-weighted and unweighted statistics, principal densities and seam measurements. The coloured diagnostic PNGs use centroid-sampled albedo and are not source beauty renders or native quality evidence. No Blender/Unity execution, semantic mask or material output has been produced in this preparation.
