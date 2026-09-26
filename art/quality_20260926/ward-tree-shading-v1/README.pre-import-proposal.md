# Ward tree shade-response audition, 26 September 2026

Status: staged outside Assets. No shader has been imported, compiled or visually accepted from this directory. Source backups and SHA256 hashes are in `before/` and `manifest.json`; `candidate.diff` is the proposed change. Root coordinates application after native timing finishes.

## Change

The existing tree shader adds transmission from the main directional light only. A leaf fully shadowed from that source receives no transmitted diffuse sky/probe light. The proposed `_WardIndirectTranslucency` property adds an albedo-filtered sample of legacy diffuse SH in the opposite normal direction, multiplied by the same indirect ambient occlusion used by URP Lit. This is a bounded thin-leaf approximation, not physically exact subsurface or multi-leaf scattering. There is no constant brightness floor, emission, exposure adjustment or albedo tint.

The new property defaults to zero, so existing materials gain no ambient transmission until explicitly authored. The existing direct term is independently corrected to use URP's full main-light lookup, with shadow fade/mixed shadow mask, cookies, SSAO, distance attenuation and rendering-layer membership. That API correction can change the existing direct transmission even at indirect zero; the audition must use the corrected indirect-zero image as its control.

For the current PC profile, SH Auto resolves to per-pixel evaluation and the renderer uses Forward with legacy probes. The new ambient term explicitly excludes lightmaps, APV and screen-space irradiance. Those modes need separate two-sided GI sampling and remain unchanged. The existing deferred GBuffer pass does not implement either custom transmission term; this candidate does not claim deferred support. The forward/depth-normal backside convention is retained, including when the ambient control alone is enabled. Geometry, alpha, normals, AO settings and materials are unchanged.

## Authoritative installed package evidence

- `com.unity.render-pipelines.universal@b9a66914c09e/Shaders/Nature/SpeedTree8Passes.hlsl:452–462` separates direct and indirect subsurface contributions. Its model differs from this opposite-hemisphere approximation.
- `Shaders/Nature/SpeedTree8.shader:21` has a separately controlled indirect subsurface parameter, default 0.25. This is implementation context, not evidence that 0.25 is correct for this tree.
- `ShaderLibrary/RealtimeLights.hlsl:141` provides the InputData/main-light overload used by current Lit.
- `ShaderLibrary/Lighting.hlsl:325–350` supplies the AO, shadow-mask and light-layer pattern.
- `ShaderLibrary/GlobalIllumination.hlsl:61–76` shows per-pixel SH sampling; `Runtime/UniversalRenderPipelineCore.cs:2033–2043` selects it for desktop Auto.
- `com.unity.render-pipelines.core@1691dee1b9ce/ShaderLibrary/AmbientProbe.hlsl:45–71` implements the legacy SH evaluation.

## Controlled audition

Use the derived edge-padded leaves, main-light transmission 0.22, 96 m shadow distance, four cascades and the existing 4096 atlas. Keep the authored noon, sky, exposure, AO, normal strength, camera, lens, resolution and root transforms identical. Capture indirect values 0, 0.15 and 0.25 in hill, hero, canopy-below and canopy-edge views. Zero after the direct-light correction is the control.

Accept only if underside leaf/branch separation improves without flattening shadow contact, making the canopy self-lit, introducing halos, losing the olive leaf identity or damaging the sunlit crown. Compare the same variant in native OpenGL with real gameplay AA; static Editor captures cannot establish temporal stability. Native moving foliage/LOD/shadow-fade and performance evidence remains required.

The original source image, padded candidate, material assignments and source backups remain recoverable. No shipping material value is chosen here.
