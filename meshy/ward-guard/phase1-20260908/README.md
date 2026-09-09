# Vex surface audit — 8 September 2026

The installed Vex uses the original Ward Guard identity and 38,071-triangle rig.
The full original PBR textures were recovered from Meshy task
`01a07c7c-4d44-7360-9cb7-656e79980f5c`; the current rig task remains
`01a07c81-2534-7259-af07-0a4df613e278`.

`original-unrigged.glb` and its full 2048px textures are retained. Exact original
and rigged UV coordinate matching was verified; the rig contains 23 additional
seam vertices. Unity's separate `WardGuardTangents.asset` preserves its original
positions, normals, UVs, indices, skin weights and bindposes, and adds tangents.
The original normal map and metallic/roughness maps are applied only to Vex.
Roughness is inverted into smoothness alpha; maps use correct colour spaces.
Albedo tint is white, normal strength 1, mipmaps/aniso enabled, source resolution
preserved. Vex casts and receives shadows. Other guard material assignments remain.

A generated texture audition used Meshy 7 retexture task
`01a08226-797a-71ff-adbc-ec534cfb333d`: original UVs, PBR, 4K requested,
lighting removal, GLB export. **10 Meshy credits** were consumed under the user's
existing approval. Its albedo is 4096px; supplied PBR maps are 2048px.
The request is in `retexture-request.json`, outputs in `retexture-4k.glb` and
`retexture-4k_textures`.

**Do not integrate the generated candidate.** It invents “NAR” chest lettering,
changes the cyan forehead insignia and alters visor paint. The candidate material
in `VexSurface/Candidate4K` is retained for review but is unassigned in the saved
scene. Correct those identity defects and review in native gameplay before any
future use. The original source remains soft in close-up, and this restoration
does not finish Vex's visual or animation work.

Before/after native and audition images, mesh validation and import settings:
`unity/evidence/phase1/20260908`.
