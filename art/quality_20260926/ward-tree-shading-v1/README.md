# Ward tree shade-response audition, 26 September 2026

Status: the four hash-verified shader files are applied and imported. The first Editor shade-response audition completed with no ShaderUtil messages; source texture, ambient control and shadow settings were restored, and the scene remained clean. The first Editor shade batch is inconclusive: close views effectively tie, and the hill zero-control unexpectedly differs in a direction the additive ambient term cannot explain. A native per-frame comparison and qualification remain pending. Source backups and shader hashes remain in `before/` and `manifest.json`. Exact pre-import plans are preserved as `README.pre-import-proposal.md` and `manifest.pre-import-proposal.json`; the original96m/four-cascade plan was revised to48m/two cascades for this audition after full-source shadow profiles failed the native frame-time target.

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

## Completed Editor audition

The actual `editor-leaf-shade-v1` captures use the derived edge-padded leaves, main-light transmission0.22, **48m shadow distance and two cascades**, retaining the authored atlas and lighting. Indirect values0,0.15 and0.25 were captured from hill, hero, canopy-below and canopy-edge views (12 images). Corrected direct lighting with indirect zero is the control. The command changes only shadow distance/cascades, BaseMap and ambient control and restores them in `finally`.

Do not choose an ambient value from this batch. The critic found that hill indirect-zero appears bluer/brighter than positive values, while close triplets effectively tie. Adding the nonnegative ambient term cannot darken otherwise fixed shader inputs. Several Camera.Render calls in one Editor callback may observe different material/mip state; this is a diagnostic hypothesis, not an established renderer defect. Root will compare native frames using separate acknowledged ambient commands and settling intervals.

Evidence: `unity/evidence/quality/20260926/leaf-shade-audition-command.json`, `leaf-shade-audition-result.json` and `editor-leaf-shade-v1/`. PortDiagnostics renders a1920×1080 ARGB32 RenderTexture in Edit mode; these frames do not establish native gameplay MSAA or temporal stability.48m/two cascades is an audition condition, not a performance-qualified shipping profile.

Accept only if underside leaf/branch separation improves without flattening shadow contact, making the canopy self-lit, introducing halos, losing the olive leaf identity or damaging the sunlit crown. Compare the same variant in native OpenGL with real gameplay AA; static Editor captures cannot establish temporal stability. Native moving foliage/LOD/shadow-fade and performance evidence remains required.

## Validation status

All50 Unity EditMode cases passed (6.297s), including the four shadow-review tests, in `unity/evidence/quality/20260926/movement/proxy-reparent/editmode-results.json`. Two clone tests nevertheless logged warnings because DontSave flags were assigned to Transform before GameObject. Source ordering was corrected after that run; the focused test rerun is pending. The historical50/50 result is preserved with this warning caveat.

The original source image, padded candidate, material assignments and source backups remain recoverable. No shipping material value is chosen here.

## Native shade commands

`{"action":"reviewTree","ambientTransmission":0}` sets the corrected-shader control. Repeat with0.15 and0.25 after separate rendered-frame settling intervals. Read `visual-review-state.json` to verify the current/original ambient values. The new ambient field accepts0–0.5, preserves direct transmission unless that field is separately supplied, and restores independently through `reviewReset` or NativeQa teardown. The command does not change texture assignments.
