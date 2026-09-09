# Platform terminals: integration handoff

This is a scoped visual replacement for three decorative hill-platform props. It does not change save data, inventory, respawn, travel, mission terminals, NPC identifiers or any interaction implementation.

## Root integration

1. Run `python art/quality_20260908/platform-terminals/stage_unity.py` from the repository. It validates that the source display repair completed and copies only this asset family's new files and Editor installer. It refuses to overwrite differing already-staged assets. The script does not operate Unity.
2. Through the live Unity MCP, refresh/compile and inspect the console. Then call `AthenHill.Editor.PlatformTerminalPass.PrepareAssets();`. This creates two ordinary saved prefabs with separate source mesh assets/tangents, URP PBR materials, measured LODGroup, exact-text display and hardware nameplate. It refuses to overwrite already-edited prefabs.
3. Inspect the prefabs. In the existing open saved city, call `AthenHill.Editor.PlatformTerminalPass.Install();`. This checks all 24 exact legacy source parts and all six existing collider components before mutation; it never opens or recreates the city. It installs the three new prefabs at the audited placements, hides only those retired renderers, refits the same collider components, rebuilds derived render chunks and saves. Repeating installation refuses to overwrite the installed root.
4. Reopen the saved scene, inspect shader/map bindings and confirm the three mission terminals remain untouched. Build the Linux player and capture the named views below. The new root stays independently instanced so the authored LODGroup is not collapsed into static render chunks.

## Review cameras and native route

- `cam_platform_terminals`: hill grouping; inspect all three placements in the tree's context.
- `cam_platform_save_front`, `cam_platform_save_side`, `cam_platform_save_back`: silhouette, full construction and grounding.
- `cam_platform_save_screen`: player-height controls, screen and hardware lettering.
- `cam_platform_reclaim_front`: alternate authored display and its approach.

These cameras are initial measured positions; any actual occlusion must be resolved in the saved scene and recorded rather than accepting an obscured capture. Add actual first-person approach, grazing left/right/top/bottom and a moving orbit with the normal gameplay camera. Check all three colliders, screen clearance, Linn's route, the hill stairs and tree access. The existing mission slab at x10/8/6, y.25, z-13.8 and both travel landmarks are excluded by exact path selection.

## Source and fidelity

- Original imagegen reference/prompt: `refs/quality_20260908/platform-terminals`.
- Meshy 7 ultra task `01a082f4-ec1a-7558-92e4-07c0a5b403cf`: 35 credits under the user's existing approval. Full 3,015,022 triangle source and all delivered PNG maps retained in `meshy/platform-terminals-20260908`.
- Uniform 1.65 m normalization, .74668 m width, .72002 m depth. No independent-axis fitting.
- Candidate LODs begin at 300k / 75k / 20k triangles before generated-glass replacement. `runtime-lod-measurements.json` records 32,000 deterministic bidirectional samples per LOD against the full source. LOD0 p99 displacement 0.068 mm / max 0.132 mm; LOD1 max 1.15 mm; LOD2 max 9.11 mm. These are sampled distances, not all-point Hausdorff certification or visual acceptance. The intentional display repair is documented separately in `display-repair.json`.
- Original 4K PNG albedo and 4K PNG normal are copied byte-for-byte; 2K original metallic/roughness PNGs are packed into Unity metallic R and inverse-roughness A. GLB's embedded JPEG versions also remain preserved for source comparison. Texture dimensions are retained, NPOT rescaling is disabled and normal/data color spaces are explicit.
- Runtime mesh tangent generation must leave positions, indices and UV0 unchanged. Source buffers and PBR regions are not collapsed into a district atlas.

## Final source repair, 9 September 2026

The rejected generated glass was removed from all three runtime derivatives, with original per-corner normals preserved. Final body counts are 295,588 / 74,238 / 19,794 triangles. A separately authored 288-triangle rounded rubber receiver, solid 4 mm display glass and exact-text `WARD // SR-08` nameplate replace the malformed screen region. The original detailed Meshy source remains untouched. The display, receiver and label are included at every LOD and share the body's distance culling.

The seven final source review images are `seated-v3-front.png`, `seated-v3-back.png`, `seated-v3-screen.png` and the four `seated-v3-grazing-*.png` views. [source-review-final.json](source-review-final.json) records their hashes and render settings. The editable source is [terminal-runtime-seated-v3.blend](terminal-runtime-seated-v3.blend). Earlier `runtime-*` and `seated-*` images remain as rejected/intermediate evidence, and the independent initial defect report is [terminal-source-01.md](../../../unity/evidence/quality/20260908/reviews/terminal-source-01.md).

[buffer-validation.json](buffer-validation.json) verifies finite positions/normals/UVs, index ranges and final export counts. It also confirms that runtime base color and normal PNGs are byte-identical to the delivered source and that metallic R / inverse-roughness A packing is exact. [compiler-check.json](compiler-check.json) records a successful non-mutating C# compile preflight against installed Unity 6000.6 assemblies. Actual Unity import and native player verification remain root integration work.

## Acceptance remains open

The independent critic inspected all seven final v3 source angles and cleared the prior screen geometry hold for a reversible native audition. No exposed generated triangles, open strip, floating insert or clipped graphic border remained in those views. Source construction was assessed around 4/5, materials 3/5, with native appearance unreviewed. The remaining source concerns are strong display washout at the left grazing angle, mirrored rear grime and bright continuous edge wear. Assess those under actual Ward sun and shade before deciding whether another material pass is needed.

The displays explicitly say `OFFLINE`. No save/reclaim verbs or IDs exist in the prior implementation. These models do not establish those systems. LOD thresholds (.16/.05/.005 of screen height) and dither transitions require native moving review and RTX 3060 measurement. Source studio images demonstrate construction and repairs only. The independent critic must assess the new native player views, real access and temporal stability before the TODO is marked complete.
