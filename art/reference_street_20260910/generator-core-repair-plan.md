# Generator source repair continuation — 10 September 2026

The service construction is frozen at the critic's 4/5. The generator as a whole remains on HOLD. The retained core has two distinct defects: the albedo contains a woven grid, and the geometry contains stepped/interrupted grille rails and an uneven protective net. No near mesh has been derived or installed from this source.

## Saved state and invariants

Load `meshy/ground-detail-20260910/generator-v3-source/generator-v3-source-handback.blend` only after the parent returns exclusive live Blender ownership. Scene: `Generator v3 side service authoring`. Original V2 review, FBX/GLB and PBR files remain untouched. The active source has 135 mesh objects, 2,025,574 triangles: the retained 1,927,842-triangle FBX core plus 97,732 authored service triangles. The separate GLB intrinsically has 1,945,352 triangles; the export discrepancy is already recorded.

Dimensions in Unity X/Y/Z are 1.574547 × 1.100000 × 0.887297 m. The authoring study intentionally preserves the core's original world transform for matched views. Before runtime fitting, translate the **complete assembly** in Blender by `(-0.154726565, 0, +0.000000019)` to place its bottom centre at the origin. This is a whole-assembly translation, followed by uniform fit if needed. Do not independently scale axes or change colliders. Keep the full authored service parts separate from the source core during any near derivation.

The original core has custom split normals, 226 boundary edges and 281 edges with more than two faces. It is not a closed Boolean operand. The 134 authored active service parts have positive signed surface volumes and no degenerate triangles. One converted coil has 48 indexed cap-seam boundary edges that close exactly under the recorded 10 μm coincident-seam audit; every other authored part is closed in indexed topology. Do not turn diagnostic welding into an unreviewed geometry edit.

## Service material V5 — staged only

`stage_generator_service_materials_v5.py` creates four separate material variants from the saved V4 contract, retaining all previous materials. It guards the V4 contract hash, active source roster/count and before/after vertex/index hashes. Geometry and the core material are unchanged.

The proposed change adds millimetre-scale roughness/grain to the tank, frame and steel straps/hardware, with physical bump distances of 18–55 μm. It removes broad color-noise modulation. Copper oxidation is localized to six of eight clamp contacts with unequal extent/intensity; two contacts stay unoxidized. The oxidation color is desaturated and the repeated turquoise bands from V4 are removed. This is an audition, not a claim that numerical grain settings meet the reference.

After executing in live Blender, use `render_generator_v3_source.py` for exactly three matched views with tag `materials-v5`: `front_oblique`, `right`, `connection_close`. Critic must judge paint/metal response and varied contact history. Preserve V3's excessive camouflage-like wear and V4's too-smooth/sparse result as prior evidence. Do not add broad cloudy color noise or repeat the core's woven pattern.

## Front grille: bounded selection and construction plan

The read-only source spatial audit exports world positions/triangles and a 192 × 160 front-ray depth map. `grille-spatial-audit/front-ray-depth.png` gives metric construction locations. Approximate horizontal rail centres are Blender Z 0.292, 0.340, 0.391, 0.443, 0.495, 0.542, 0.585 and 0.637 m, with vertical supports near X −0.310 and +0.085 m. The fan hub is near X −0.138/Z 0.468 m.

The **candidate diagnostic region**, not an approved deletion mask, is X [−0.444, +0.235], Z [0.251, 0.674] m, excluding a radius 0.073 m around the hub. Foremost source rail faces lie around Y −0.220 to −0.180 m. The nearby net extends towards Y −0.170 m and farther back. A front-Y threshold sweep selects 35,013 to 60,047 faces. These counts demonstrate that a blanket slab cut is too broad to apply unseen; it could trim rounded housing corners or the net.

The next live step should create a **selection preview only** on a duplicate source, using explicit rail bands and a connected-face growth bounded by the metric aperture. Render the selected faces in a flat diagnostic color from front and oblique angles. Review each rail root, hub attachment, housing corner and the rear wire net. Retain the complete original core hidden in the new source revision. Do not cut using a Boolean on the open core, and do not overlay new bars on visible malformed old bars.

After the selection is verified, deliberately replace only the exposed faulty rails with continuous metal sections and readable hub/root attachments. Preserve the fan opening and fan blades. Eight rows/two supports are measured source structure, not a required arbitrary count. The top rail and rails near the hub are the current conspicuous defects; broader replacement requires source evidence. If the uneven net remains a close-view blocker, isolate it as a separate subsequent repair rather than deleting it with the rail slab.

Mesh reconstruction must carry every retained triangle's UV corners and **custom corner normal** unchanged. Preserve an original face/corner index mapping and assert unchanged vertex positions, UV values and corner normals outside the approved mask. BMesh conversion without explicit custom-normal restoration is unsuitable here. New bar bevels should be metric and surface-specific; verify closed, outward-facing sections. Re-render the same clay and PBR close-up before any reduction.

## Semantic panel degrid: measured preparation, no filter applied

`inspect_generator_uv_offline.py` reads the immutable binary FBX directly without launching an app. Its triangle array exactly equals the live Blender spatial audit, so UV corner correspondence is proven. `source-uv-corners.npz` retains all 5,783,526 UV corners. No source mesh or texture is modified.

The measured front-panel region is X [−0.440,+0.235], Z [0.693,0.812], Y < −0.200 m. It covers 972 source triangles and 115,239 atlas pixels, dispersed through the 4K map. The semantic mask is diagnostic, not yet a production mask; triangles crossing physical panel boundaries need review. A first strict Y < −0.220 threshold selected only 53 triangles/301 pixels and was rejected. Earlier failed/insufficient audit folders are preserved.

`audit_generator_panel_frequency.py` writes only source crops, masks and spectrum measurements. The V3 96-pixel patches still included white-letter edges and paint loss; they are not safe homogeneous filter regions. V4 protects bright and chromatic pixels with a three-pixel guard, yielding two fully interior 48-pixel dark-painted patches with low-frequency linear luminance standard deviations 0.00191 and 0.00206. Their dominant grid peaks occur at approximately 3.25–3.75 pixels per cycle and are 44–82 times their radial spectral median. The peak directions differ across patches, so a single global FFT notch or fixed blur is not justified.

Proposed next experiment:

1. Audit UV islands and separate painted background, white lettering interiors, red graphics, bare-metal edge wear and gutters. Preserve the existing glyph silhouettes and red graphic boundaries exactly. A protected 2–3 pixel edge band is distinct from the glyph interiors, which also contain the grid and may need a separate masked residual correction.
2. Measure local periodic peaks in each material/UV region. Use padded overlapping windows inside a single island, with DC and low-frequency color unchanged. Subtract only the measured periodic residual; do not convolve across unrelated island gutters. A semantic planar projection of the nearly flat front panel can simplify the coordinate problem, but its sampling and back-projection must first prove that glyph edge positions survive.
3. Make one small diagnostic patch on dark paint and one on a white glyph interior. Save source/candidate/residual as additive study outputs. Do not overwrite, import or bind a filtered map yet. Reject any operation that softens the letter boundary, loses thin nonperiodic scratches or bleeds red/white color into neighboring paint.
4. Measure DC/color drift, energy remaining at the identified paired peaks, difference outside the reviewed mask, and one-dimensional profiles across several letter and paint-chip edges. Expected outside-mask difference is exactly zero. Require unchanged edge positions and a critic comparison at the same sample density; no numerical threshold alone accepts the art.
5. Only after those patches pass, broaden to the remaining approved panel regions. Inspect true albedo-emission and opposed-light PBR views. Roughness/metallic are 2K while albedo/normal are 4K, so scalar-map frequency and masks must be measured independently. Normal-off evidence alone does not justify filtering all maps.

The existing albedo emission proves that the surface grid is in color/lettering. The flat-clay view removes that grid but keeps the bad rails. All original maps remain untouched. No texture filter has been applied by these preparation scripts.

## Derivation and acceptance gate

Get source acceptance after the grille, panel and service materials are repaired. Then derive the core near LOD against the full source while retaining the separately authored service geometry at its reviewed detail. Preserve all source texture resolutions. The earlier single-object V2 bake scripts must be adapted to the source's multiple materials and object material slots; do not simply reuse them on this multipart source.

Use a real selected-source-to-active bake if collapse changes UV mapping. Rebuild near UVs as needed and bake lighting-independent base color, metallic R, roughness R and OpenGL +Y tangent normal with explicit cage/ray bounds. Review matched source/near whole, oblique, grille, lettering, hose and clamp close-ups before FBX export. Unity installation, canonical pivot fitting, source rebuild, native sunlight/shade, collisions/routes and cost remain separate future work owned by the parent.
