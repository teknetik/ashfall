# Executable generator source repair staging

No live Blender script here has been executed. Root owns the active Blender session. These are source auditions; they do not authorize runtime reduction or Unity installation.

## Operation A: core guard/rail repair

With `Generator v3 side service authoring` loaded, execute the full text of `art/reference_street_20260910/author_generator_core_repair.py` through the live Blender MCP. It verifies the immutable full-source geometry and the mask before any mutation, creates **a separate scene**, preserves the entire original core and the removed faces, and leaves the V3 scene unchanged.

New scene: `Generator v4 core repair audition`.
New source folder: `meshy/ground-detail-20260910/generator-v4-source`.

The 807,040 removed source faces are entirely inside the stated guard/rail bounds. The 1,120,802 retained triangles preserve exact original positions, index/UV correspondence and restored custom corner normals, with measured normal round-trip error. The source's enormous irregular net accounts for most of the removed count. Every face remains recoverable. There is no Boolean and no edit to service geometry.

The replacement has eight continuous front rails, two rigid mounting spines and a dished, regular welded diamond-wire guard. Four standoffs join the guard to those spines; the wires meet a rolled rim. It remains open so the fan body is visible. Existing cut-edge fragments or fan clipping remain a visual rejection condition; the stage is not accepted merely because its bounds and hashes pass.

Use `render_generator_core_repair.py` with `CORE_VIEW` (`front_oblique`, `grille_close`, `guard_oblique`) and `CORE_VARIANT` (`before`, `selection`, `after`). It writes immutable outputs and restores visibility. `selection` reconstructs the original using retained faces plus the removed orange patch, so the exact cut is reviewable. Start with selection and after grille/oblique views; add matched before views for critic comparison. The PBR panel remains unchanged in this operation.

## Operation B: protected painted-panel source candidate

Run `prepare_generator_panel_paint_candidate.py` using the bundled Python runtime, without any Blender/Unity application operation:

```bash
/home/teknetik/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /home/teknetik/code/ao2/art/reference_street_20260910/prepare_generator_panel_paint_candidate.py
```

This is an additive **local paint reauthoring study**, not a global blur/notch. It uses the proven FBX UV correspondence and pixel-centre barycentric world coordinates to constrain the panel region. Neighbors are restricted to the same detected paint/ink class and the same UV chart. It fits paint color only in safe interiors, preserves each class's mean linear color, and retains detected boundaries, salient narrow details, gutters, alpha and every outside-mask pixel exactly.

Output: `meshy/ground-detail-20260910/generator-v4-panel-study` with candidate 4K color, authored/protected/semantic masks, UV chart/class labels, magnified residual and quantitative checks. **Inspect the masks and residual**. Thin glyph strokes or scratches that cannot support safe interiors remain original and may retain grid; the script records this limitation. Automatic semantic masks can be wrong, so untouched detected boundaries do not establish that every real graphic boundary was correctly identified.

Then execute `author_generator_panel_material_candidate.py` in live Blender with the V4 core-repair scene loaded. It creates a separate `Generator v4 protected panel audition` scene and a separate material. Only the authored paint mask receives fine paint roughness/normal and metallic0; the original PBR remains outside it. Geometry, UVs and the prior scene/material/maps are retained.

Use `render_generator_panel_study.py` with `PANEL_VARIANT=before/after`, `PANEL_DIAGNOSTIC=pbr/albedo/mask`, and `PANEL_VIEW=grille_close/front_oblique`. Compare same-geometry before/after PBR, true albedo and a mask close-up. Reject damaged marks, removed nonperiodic wear, waxy paint or visible mask seams. If the conservative candidate leaves too much grid, refine the reviewed semantic masks; do not silently expand to a global blur.

## Checks already run offline

All six stage scripts parse. The actual local-fit functions passed a synthetic periodic-paint fixture: RMS periodic error fell from 0.02121 to 0.00101, while protected edge/scratch pixels remained exact and no cross-class color leak occurred. This validates bounded math, not source art quality. All selected source vertices are inside the strict spatial region, face sets are complementary, and authored wire endpoints meet the rim geometrically. `staging-checks.json` contains hashes and results.

Service geometry remains frozen at its critic score4. The full assembly's eventual Blender bottom-center translation remains X −0.154726565m, Y0, Z+0.000000019m before uniform runtime fit. Preserve authored service parts separately from the source core for any later LOD. Source critique and the protected core treatment must pass before near preparation or Unity work.
