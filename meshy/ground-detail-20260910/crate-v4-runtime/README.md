# Crate v4 runtime mapping repair

The full retained `../crate-v3/model.fbx` has 1,953,204 triangles. The initial 100,000-triangle derivative preserved shape but displaced painted marks into triangular zigzags. V4 retains that same 100,000-triangle geometry and gives it a new non-overlapping UV layout.

Live Blender/Cycles selected-to-active projection transfers the original full source's albedo, metallic, roughness and tangent normals to the final runtime UVs. Albedo and scalar channels use emission-only bakes without lighting. The normal bake combines the high source surface and its normal texture in the final target tangent basis, using OpenGL +Y. All derivative maps are 4096². Original albedo/normal are 4096²; original scalar maps are 2048², so larger scalar outputs are resampling rather than new source detail.

The authoring `.blend`, bake settings/timings, hashes, paired renders and four single-object matched-camera renders are retained here. Source originals are untouched. The independent critic accepted this version for native audition after checking stencil marks, the handle-side label, lid shading and side relief. Native scale, contact, normal import, mips and moving-view quality remain to be checked.
