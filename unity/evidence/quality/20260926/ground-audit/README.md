# West Gate paving and threshold: read-only technical audit

The strongest concrete material defect is that **the paving normal source is byte-for-byte the same colored image as the albedo**. Unity converts its luminance into height-derived normals, so mineral color variation becomes surface relief. This is consistent with the critic's coarse, uniform grain observation, though the final candidate still requires native image and motion comparison.

No asset, material, scene, collider or runtime source was changed by this audit. One read-only live Editor inspection completed with the saved AthenHill scene clean; subsequent geometry, material, importer and scene checks read saved files while root built the player. Raw results and source hashes accompany this report. The inspector name is not sufficient to identify a saved prefab child; the IDs and source indices below disambiguate the two gate instances.

## Actual saved surface and mapping

| Item | Saved finding |
| --- | --- |
| Editable main source | Root `Paving`, renderer fileID `1100300804`, chunk source index 1177, source visibility true; renderer disabled while chunks are shown |
| Geometry | Built-in Cube, 24 vertices/12 triangles, position `(0,-0.3,0)`, scale `(120,0.6,90)`, identity rotation |
| Surface bounds | X `[-60,60]`, Z `[-45,45]`, top Y `0`; slab lines and top bevels are texture shading on two planar triangles |
| Collision | Separate `COL_Ground`, enabled non-trigger BoxCollider fileID `1053946623`, size `(120,2,90)`, center `(0,-1,0)` under identity root; top Y `0` |
| Rendered output | `City Render Chunks/Generated material chunks/Chunk_11_Paving Local wear_0_0`, renderer fileID `1004867083`; same 24 vertices/12 triangles, receives shadows, casts Off |
| Material | `Assets/AthenHill/Art/Weathering/Paving Local wear.mat`, shader `WeatheredLit`, base and normal scale `(20,15)`, offset zero |
| UV0 mapping | The saved generated top triangles verify `u=(60-x)/120`, `v=(45-z)/90`; material repetition is exactly **6 m × 6 m** |
| Source density | Both source maps are **1254×1254**, approximately **209 source texels/metre** at this mapping; effective runtime mip resolution remains a separate measurement |
| Old paving strips | `Paving Joints/Paving joint` source objects are retained, but their saved source visibility is false; they do not supply active geometric grooves |

The top-triangle vertex/UV dump is in `topology-verification.json`; it prevents assuming a conventional Cube axis mapping from its overall 0..1 UV range alone. Main Paving has no local collider; the separate ground collider is the traversal contract to retain.

## Material inputs

`Art/Textures/AAA/Paving_Albedo.png` and `Paving_NormalSource.png` both hash to `9d8a4d78479096af5c1e33f98ccffbb5be8336cf232646a2cac25b022d22bc0c`, with 2,818,327 bytes each. This is an exact duplicate, not an independently authored height or tangent-space normal map.

The albedo importer is sRGB. The normal importer is NormalMap, sRGB off, `convertToNormalMap=1`, height scale `0.12`, normal filter `0`, green flip off. Its orientation is produced by Unity's conversion; this is not evidence of an externally authored DirectX/OpenGL normal mismatch. Both importers retain mipmaps and streaming, Repeat wrapping, bilinear filtering, anisotropy 8, maximum size 2048, and NPOT scale None. Actual imported compression/mip residency should be recorded in the next native snapshot rather than inferred from source dimensions.

The material enables `_NORMALMAP`, `_BumpScale=0.72`, metallic `0`, scalar smoothness `0.17`, white base tint. It has no metallic/smoothness, occlusion, detail-normal or parallax texture. There is no authored per-slab/dust roughness input. The weathering shader adds world-space noise: `_WearScale=0.24`, `_WearStrength=0.58`, `_BaseWear=0`, `_WearTint=(0.51,0.48,0.41)`. It darkens albedo and reduces smoothness by `1-wear*0.55`; it does not change the normal or place dust specifically at the gate piers. At these settings the theoretical smoothness range is approximately 0.116–0.17.

The differently scaled `PlazaPaving Local wear.mat` uses those same maps at `(3.3,1.4)`, normal strength 0.72 and smoothness 0.14. It belongs to three currently rendered plaza inset cubes near X −12.7..20.7, Z −11..15.2 in `Chunk_8_PlazaPaving Local wear_0_0`, **not the West Gate patch**. The north inset source is retained but its saved source visibility is false. The south source is 25×4.2 m, yielding approximately 7.58×3 m per image repeat; west/east sources are 4.2×22 m, yielding approximately 1.27×15.71 m per repeat with their unrotated Cube mapping. This separate inconsistent scale deserves its own later review, not a global change during the gate audition.

## Gate, wall and editable chunk relationships

The gate at Z 0 is saved prefab instance fileID `236671366`, renderer `236671369`, source index 1360. The second at Z 12 is instance `1314715881`, renderer `1314715884`, source index 1361. Both use `Prefabs/District/gate.prefab` GUID `c3bccef6eb046cf38875bb34a405f6a1`; source visibility is true. Their material is the existing District gate material and their mesh collider remains on the original mesh child. Both render into `Chunk_26_District_gate_0_0` (9,060 triangles combined). Preserve the accepted gate asset, transform and collider assignment.

Decoding that saved chunk's position stream gives gate 0 bounds X **46.3..49.7**, Y **0..8.8**, Z **−5.75..5.75**. The second copy has the same dimensions at Z 12. Gate 0 vertices below Y 0.2 have these two pier regions:

- Negative-Z pier: X 46.309..49.699, Z −5.750..−2.464, Y about 0..0.185.
- Positive-Z pier: X 46.312..49.690, Z 2.467..5.750, Y 0..0.199.

These are bounds of low rendered vertices, not a claim that the whole aperture is collision-free. Confirm clearance with the saved mesh collider and a real-input route. The `west_gate` landmark is `(43,0,0)`.

The neighboring authored west-wall sources are `AuthoredWorld/BLD_west_wall`, `.001`, `.002`, source indices 452–454, from `Art/Imported/world.glb`, using `MAT_stone Local wear.mat`. Their X bounds are 46.5..49.5 and Y 0..7.4; the three Z spans are −45..−3.7, 3.7..8.3, and 15.7..45. Their positive-X material/cell bucket is `Chunk_1_MAT_stone Local wear_0_0`; their independent `COL_BLD_west_wall*` objects preserve collision. Do not edit the generated chunk meshes directly.

Current `City Render Chunks` has 6,870 recorded sources, cell width 64, depth 128 and small-material threshold 5,000. Its source roots include Paving, AuthoredWorld and District rebuild. Rebuild keys use material, spatial cell, casting mode and receiving mode. Material reassignment or a source-mesh replacement requires the normal Show Sources → edit source → Rebuild workflow; the generated chunks are disposable output. Existing material GUIDs, source roots and colliders should remain stable.

## Safe bounded candidate

Use one patch at **X [42,50], Z [−6,6], top Y 0**: 8×12 m covers the inside approach, the existing gate threshold, both measured pier contacts and a short adjacent wall-foot region. This is a proposed authoring boundary, not an already accepted art result. It leaves the second gate outside the patch. Keep the flat collision and all gate/wall meshes untouched.

For an editable audition, split only the main Paving top into non-overlapping outside and patch geometry. Preserve the existing cube side/bottom faces, source transform, exact UV0 mapping, original mesh and material. Store the new mesh as an ordinary asset; use a separate candidate material slot for the patch. No lifted overlay is needed and no z-fighting should be introduced. The patch's UV rectangle is U `[0.0833333,0.15]`, V `[0.4333333,0.5666667]`; retaining scale `(20,15)` keeps the texture phase aligned with the existing district.

The first candidate should retain the albedo/layout as a control while giving joints and quieter stone tops an explicit physical height/normal interpretation plus an authored roughness response. Let localized dust collect near measured pier/wall feet and selected joints. Blend candidate normal/smoothness back to the original response at the patch boundary using a patch-only material mask, or demonstrate an equally clean physical boundary in the native view. A hard rectangle of changed shading is a rejection condition. Do not globally swap the shared district material or use a uniformly raised tile field that changes foot contact.

Before integration, inspect one player-height threshold view, a downward close-up and the shaded pier foot against matched baseline captures. After chunk rebuild, retain an actual gate walk/jump/camera test and moving surface review. This audit does not claim visual acceptance, collision qualification or a performance result for the proposed patch.
