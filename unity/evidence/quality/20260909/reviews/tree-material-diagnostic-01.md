# Hero-tree leaves — readonly diagnostic note 01

9 September 2026. Reviewer: `visual_critic`. **No material edits and no established root cause.** The integration-01 canopy appears pale/silver in sun and insufficiently separated internally; see the [native static review](integration-01-static.md). The source albedo visibly contains olive green leaves. The observations below narrow controlled native comparisons, not acceptance.

Read the installed [leaf material](../../../../AthenHill/Assets/AthenHill/Art/HeroTree/leaves.mat), albedo and texture import metadata, [tree installer](../../../../AthenHill/Assets/AthenHill/Editor/HeroTreePass.cs), and custom tree shader input/forward/depth-normal code. Bindings connect the intended albedo, normal and metallic/smoothness textures. Albedo imports as sRGB; normal and packed map as non-sRGB. Normal type is enabled, green-channel flip is off. Material base tint is white, metallic scalar zero, no emission keyword, alpha clipping approximately 0.35 and culling off. There is no canopy occlusion map/keyword. Root independently reports fully rough source leaves and runtime packed smoothness alpha zero; that numerical source-map analysis is author evidence, not a separate measurement by this reviewer.

In [LitForwardPass.hlsl](../../../../AthenHill/Assets/AthenHill/Shaders/WardTree/LitForwardPass.hlsl), line 258 flips the normal for backfaces only when `_WardTranslucency > 0`. After baked GI and PBR evaluation, lines 268–272 add an albedo-tinted backside sun term with strength 0.22. [Depth normals](../../../../AthenHill/Assets/AthenHill/Shaders/WardTree/LitDepthNormalsPass.hlsl) use the same conditional normal flip. This term is not explicitly white. Its presence alone does not prove it creates the silver appearance.

The important experimental confound is that setting translucency to **zero also turns off the backface normal correction**. A zero-versus-0.22 comparison therefore changes two behaviors. To isolate transmission, preserve normal correction with a separately controlled diagnostic toggle or a near-zero positive value such as 0.0001. Do not compare a changed canopy material plus exposure, tint and shadow settings at the same time.

Suggested reversible comparisons, one variable at a time, same native camera/time/exposure/build profile:

1. Transmission 0.22 versus near-zero positive while retaining normal correction. Compare the same sun-facing, shaded and backlit clusters.
2. Existing 18 m shadow distance versus a longer diagnostic range, retaining material settings. The roughly 17 m tree and distant avenue camera make shadow coverage a plausible contributor to weak interior separation; this is a hypothesis, not a measured exclusion map.
3. Specular/environment reflection off as a diagnostic, with albedo and diffuse lighting unchanged. Fully rough material can still have broad reflection response; do not infer metallic behavior merely from brightness.
4. Normal-map bypass as a diagnostic if needed, preserving backface behavior, to test whether card normals or the normal map dominate cluster shading.

Capture actual native branch-interior and canopy close-ups as well as the matched avenue/hill hero views. Retain originals and restore diagnostic settings. A global saturation change would not establish correct material or lighting behavior. Native root re-review must use the rebuilt scene without the legacy horizontal hill shelf; its saved removal does not alter integration-01 evidence.
