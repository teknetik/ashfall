// Ward Desert Terrain V2: layered PBR desert for the basin backdrop and its cliffs (DesertBasin.glb,
// "Desert Landscape"). Drop-in replacement for "Athen Hill/Desert Terrain": every old property keeps its meaning,
// the vertex colours keep theirs (R = authored noon shadow, G = baked sky access) and the CityTimeOfDay globals
// (_AthenTerrainTime, _AthenTerrainHazeScale) drive the same shadow handover and haze as before.
//
// Layers, blended by slope + macro noise + baked sky access, then by per-layer height:
//   * cliff rock:  the existing SandstoneAlbedo (_RockTex, _DetailScale) at mid scale, Poly Haven "Sandstone
//                  Cracks" close-up detail (albedo + normal), world-Y sedimentary strata with ledges and
//                  desert-varnish streaks. Side projections are only sampled where the slope needs them.
//   * scree:       Berms ground array layer (default 0, dry_ground_rocks) on mid slopes and bare flats.
//   * sand:        Berms ground array layer (default 1, dense_sand) on flats and in hollows, with procedural
//                  ripples aligned to _WindDirection that fade with distance.
// Anti-tiling: two-sample index bombing for the ground layers, two-scale mid rock, UV warps and two macro octaves
// of the geology map; texture detail fades to the layer mean colour between _DetailFadeStart and _DetailFadeEnd,
// where the far basin also stops sampling detail textures.
// Lighting: URP PBR (InitializeBRDFData / GlobalIllumination / LightingPhysicallyBased, the body of
// UniversalFragmentPBR) so the authored noon shadow can join the main light's shadow term; cascaded + soft
// shadows, Forward+ lights, SSAO, probes, SH. Then the Desert Terrain distance haze (optional far/height thinning and
// high-sun tint since 1 Oct 2026; the defaults reproduce the original haze).
// Passes: UniversalForward, ShadowCaster, DepthOnly, DepthNormals. SRP Batcher compatible.
Shader "Athen Hill/Ward Desert Terrain V2"
{
    Properties
    {
        [Header(Desert Terrain contract)]
        _RockTex("Sandstone albedo (mid scale)", 2D) = "white" {}
        _Geology("Geological detail (linear)", 2D) = "gray" {}
        _RockTint("Rock tint", Color) = (1, 1, 1, 1)
        _Sand("Deposited sand", Color) = (.59, .46, .30, 1)
        _Haze("Distance haze", Color) = (.62, .58, .51, 1)
        _DetailScale("Rock repeats per metre", Range(.02, 1)) = .073
        _Relief("Surface relief", Range(0, 2)) = .14
        _HazeDensity("Atmospheric density", Range(0, .02)) = .0048

        [Header(Macro variation)]
        _MacroScale("Macro repeats per metre", Range(.001, .05)) = .009
        _MacroStrength("Macro variation strength", Range(0, 1)) = .35

        [Header(Cliff rock detail)]
        _RockDetailAlbedo("Rock detail albedo (sandstone_cracks)", 2D) = "white" {}
        [Normal] _RockDetailNormal("Rock detail normal", 2D) = "bump" {}
        _RockDetailMean("Rock detail mean albedo (linear RGB)", Vector) = (.641, .359, .177, 0)
        _RockDetailSize("Rock detail tile size (m)", Range(.5, 12)) = 3.2
        _RockDetailStrength("Rock detail albedo strength", Range(0, 1)) = .6
        _RockSmoothness("Rock smoothness", Range(0, 1)) = .12

        [Header(Sedimentary strata)]
        _StrataThickness("Bed thickness (m)", Range(.3, 8)) = 1.7
        _StrataStrength("Strata contrast", Range(0, 2)) = 1
        _StrataDark("Dark bed multiplier (linear)", Vector) = (.73, .65, .56, 0)
        _StrataLight("Light bed multiplier (linear)", Vector) = (1.13, 1.03, .87, 0)
        _StrataRelief("Bed ledge relief", Range(0, 2)) = .35
        _StreakStrength("Desert varnish streaks", Range(0, 1)) = .3

        [Header(Scree and sand from the Berms ground arrays)]
        _GroundAH("Ground layers albedo + height (array)", 2DArray) = "" {}
        _GroundNRA("Ground layers normal XY, roughness, AO (array)", 2DArray) = "" {}
        _GravelLayer("Scree layer index", Float) = 0
        _SandLayer("Sand layer index", Float) = 1
        _GravelSize("Scree tile size (m)", Range(.5, 12)) = 4
        _SandSize("Sand tile size (m)", Range(.5, 12)) = 1.8
        _GravelColor("Scree colour", Color) = (.55, .44, .31, 1)
        _GravelMean("Scree texture mean (linear RGB)", Vector) = (.312, .182, .084, 0)
        _SandMean("Sand texture mean (linear RGB)", Vector) = (.293, .218, .127, 0)
        _GroundNormalStrength("Scree and sand normal strength", Range(0, 2)) = 1.2

        [Header(Layer blending)]
        _RockSlope("Rock from slope (1 - normal.y)", Range(0, .6)) = .075
        _SlopeBlend("Slope transition width", Range(.005, .2)) = .035
        _SandAmount("Sand in flats and hollows", Range(0, 1)) = .5
        _HeightBlend("Height blend depth", Range(.01, 1)) = .18

        [Header(Sand ripples)]
        _WindDirection("Wind direction (world XZ)", Vector) = (-1, 0, .35, 0)
        _RippleWavelength("Ripple wavelength (m)", Range(.04, .5)) = .2
        _RippleStrength("Ripple strength", Range(0, 2)) = 1

        [Header(Distance and lighting)]
        _DetailFadeStart("Detail fade start (m)", Range(5, 300)) = 40
        _DetailFadeEnd("Detail fade end (m)", Range(10, 500)) = 140
        _SkyOcclusion("Baked sky access strength", Range(0, 1)) = 1
        _FogBlend("URP fog blend (0 = previous look)", Range(0, 1)) = 0

        [Header(Distance haze shape (defaults keep the original haze))]
        _HazeFarStart("Far haze starts (m beyond 38 m)", Range(0, 1000)) = 1000
        _HazeFarScale("Density beyond the far start", Range(0, 1)) = 1
        _HazeHeightFalloff("Haze height falloff (m, 0 = off)", Range(0, 300)) = 0
        _HazeBaseHeight("Height falloff base (m)", Range(-5, 40)) = 6
        _HazeNoonTint("High-sun haze tint (linear multiplier)", Vector) = (1, 1, 1, 0)
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "UniversalMaterialType"="Lit" "Queue"="Geometry" }
        LOD 300

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        CBUFFER_START(UnityPerMaterial)
            float4 _RockTint, _Sand, _Haze;
            float _DetailScale, _Relief, _HazeDensity;
            float _MacroScale, _MacroStrength;
            float4 _RockDetailMean;
            float _RockDetailSize, _RockDetailStrength, _RockSmoothness;
            float _StrataThickness, _StrataStrength;
            float4 _StrataDark, _StrataLight;
            float _StrataRelief, _StreakStrength;
            float _GravelLayer, _SandLayer, _GravelSize, _SandSize;
            float4 _GravelColor, _GravelMean, _SandMean;
            float _GroundNormalStrength;
            float _RockSlope, _SlopeBlend, _SandAmount, _HeightBlend;
            float4 _WindDirection;
            float _RippleWavelength, _RippleStrength;
            float _DetailFadeStart, _DetailFadeEnd, _SkyOcclusion, _FogBlend;
            float _HazeFarStart, _HazeFarScale, _HazeHeightFalloff, _HazeBaseHeight;
            float4 _HazeNoonTint;
        CBUFFER_END

        TEXTURE2D(_RockTex); SAMPLER(sampler_RockTex);
        TEXTURE2D(_Geology); SAMPLER(sampler_Geology);
        TEXTURE2D(_RockDetailAlbedo); SAMPLER(sampler_RockDetailAlbedo);
        TEXTURE2D(_RockDetailNormal); SAMPLER(sampler_RockDetailNormal);
        TEXTURE2D_ARRAY(_GroundAH); SAMPLER(sampler_GroundAH);
        TEXTURE2D_ARRAY(_GroundNRA); SAMPLER(sampler_GroundNRA);

        // CityTimeOfDay owns these globals and restores them on teardown (unchanged from Desert Terrain).
        // x: active clock, y: validity of the retained authored-direction shadow bake.
        float4 _AthenTerrainTime;
        float4 _AthenTerrainHazeScale;
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            Cull Back
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex TerrainVert
            #pragma fragment TerrainFrag

            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BOX_PROJECTION
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_ATLAS
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #pragma multi_compile _ _LIGHT_LAYERS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/RenderingLayers.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float2 baked : TEXCOORD2;          // R authored noon shadow, G baked sky access
                half fogFactor : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings TerrainVert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                output.positionWS = TransformObjectToWorld(input.positionOS.xyz);
                output.positionCS = TransformWorldToHClip(output.positionWS);
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.baked = input.color.rg;
                output.fogFactor = ComputeFogFactor(output.positionCS.z);
                return output;
            }

            // ---- Helpers ----------------------------------------------------------------------
            float Hash11(float p)
            {
                p = frac(p * 0.1031);
                p *= p + 33.33;
                p *= p + p;
                return frac(p);
            }
            float2 Hash12(float n)
            {
                float3 p3 = frac(float3(n, n, n) * float3(0.1031, 0.1030, 0.0973));
                p3 += dot(p3, p3.yzx + 33.33);
                return frac((p3.xx + p3.yz) * p3.zy);
            }
            float3 GroundNormalWS(float3 n, float3 normalTS)
            {
                float3 t = normalize(float3(1, 0, 0) - n * n.x);
                float3 bt = cross(t, n);
                return normalize(t * normalTS.x + bt * normalTS.y + n * normalTS.z);
            }

            struct GroundTap { float4 ah; float4 nra; };

            // Index bombing (Quilez): a mid-frequency noise picks one of eight random offsets; neighbouring
            // indices are cross-faded along the texture's own height, so no tile repeats and no seam is straight.
            // Only the samples with non-zero weight are fetched (explicit gradients keep branching legal).
            GroundTap SampleGround(float2 uv, float2 dx, float2 dy, float layer, float k, float bombing)
            {
                float i = floor(k), f = frac(k);
                float2 offA = Hash12(i + layer * 17.0) * 11.3;
                float2 offB = Hash12(i + 1.0 + layer * 17.0) * 11.3;
                GroundTap a = (GroundTap)0, b = (GroundTap)0;
                float blend = smoothstep(0.35, 0.65, f) * bombing;
                UNITY_BRANCH
                if (blend < 0.999)
                {
                    a.ah = SAMPLE_TEXTURE2D_ARRAY_GRAD(_GroundAH, sampler_GroundAH, uv + offA, layer, dx, dy);
                    a.nra = SAMPLE_TEXTURE2D_ARRAY_GRAD(_GroundNRA, sampler_GroundNRA, uv + offA, layer, dx, dy);
                }
                UNITY_BRANCH
                if (blend > 0.001)
                {
                    b.ah = SAMPLE_TEXTURE2D_ARRAY_GRAD(_GroundAH, sampler_GroundAH, uv + offB, layer, dx, dy);
                    b.nra = SAMPLE_TEXTURE2D_ARRAY_GRAD(_GroundNRA, sampler_GroundNRA, uv + offB, layer, dx, dy);
                }
                blend = saturate(blend + (b.ah.a - a.ah.a) * 0.35 * step(0.001, blend) * step(blend, 0.999));
                GroundTap o;
                o.ah = lerp(a.ah, b.ah, blend);
                o.nra = lerp(a.nra, b.nra, blend);
                return o;
            }

            // One rock projection: two-scale mid sandstone (continuous blend), optional close-up detail.
            void SampleRockProjection(float2 uv, float2 dx, float2 dy, float midBlend, float detailOn,
                                      out float3 mid, out float3 detail, out float3 detailTS)
            {
                float s = _DetailScale;
                float3 m1 = SAMPLE_TEXTURE2D_GRAD(_RockTex, sampler_RockTex, uv * s, dx * s, dy * s).rgb;
                float3 m2 = SAMPLE_TEXTURE2D_GRAD(_RockTex, sampler_RockTex, uv * (s * 0.731) + float2(0.37, 0.71), dx * (s * 0.731), dy * (s * 0.731)).rgb;
                mid = lerp(m1, m2, midBlend);
                detail = _RockDetailMean.rgb;
                detailTS = float3(0, 0, 1);
                UNITY_BRANCH
                if (detailOn > 0.001)
                {
                    float d = 1.0 / _RockDetailSize;
                    detail = SAMPLE_TEXTURE2D_GRAD(_RockDetailAlbedo, sampler_RockDetailAlbedo, uv * d, dx * d, dy * d).rgb;
                    float4 packedN = SAMPLE_TEXTURE2D_GRAD(_RockDetailNormal, sampler_RockDetailNormal, uv * d, dx * d, dy * d);
                    detailTS = UnpackNormalScale(packedN, detailOn * _Relief / 0.14);
                }
            }

            // URP PBR (the body of UniversalFragmentPBR) with the Desert Terrain noon-shadow handover merged into
            // the main light's shadow term.
            half3 TerrainLighting(InputData inputData, SurfaceData surfaceData, float authoredShadowBake)
            {
                BRDFData brdfData;
                InitializeBRDFData(surfaceData, brdfData);
                BRDFData noClearCoat = (BRDFData)0;
                half4 shadowMask = CalculateShadowMask(inputData);
                AmbientOcclusionFactor aoFactor = CreateAmbientOcclusionFactor(inputData, surfaceData);
                uint meshRenderingLayers = GetMeshRenderingLayer();
                Light mainLight = GetMainLight(inputData, shadowMask, aoFactor);

                // Identical to Desert Terrain: keep the authored noon view, then hand over to live shadows as the
                // sun moves; beyond the shadow distance live lighting replaces the noon-only bake.
                float clockActive = saturate(_AthenTerrainTime.x);
                float authoredWeight = lerp(1.0, saturate(_AthenTerrainTime.y), clockActive);
                float authoredShadow = lerp(1.0, lerp(0.25, 1.0, authoredShadowBake), authoredWeight);
                float liveShadow = lerp(1.0, mainLight.shadowAttenuation, clockActive * (1.0 - authoredWeight));
                mainLight.shadowAttenuation = authoredShadow * liveShadow;

                MixRealtimeAndBakedGI(mainLight, inputData.normalWS, inputData.bakedGI);
                LightingData lightingData = CreateLightingData(inputData, surfaceData);
                lightingData.giColor = GlobalIllumination(brdfData, noClearCoat, 0.0, inputData.bakedGI, aoFactor.indirectAmbientOcclusion,
                                                          inputData.positionWS, inputData.normalWS, inputData.viewDirectionWS, inputData.normalizedScreenSpaceUV);
                #ifdef _LIGHT_LAYERS
                if (IsMatchingLightLayer(mainLight.layerMask, meshRenderingLayers))
                #endif
                    lightingData.mainLightColor = LightingPhysicallyBased(brdfData, noClearCoat, mainLight, inputData.normalWS, inputData.viewDirectionWS, 0.0, false);

                #if defined(_ADDITIONAL_LIGHTS)
                uint pixelLightCount = GetAdditionalLightsCount();
                #if USE_CLUSTER_LIGHT_LOOP
                [loop] for (uint lightIndex = 0; lightIndex < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); lightIndex++)
                {
                    CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
                    Light light = GetAdditionalLight(lightIndex, inputData, shadowMask, aoFactor);
                    #ifdef _LIGHT_LAYERS
                    if (IsMatchingLightLayer(light.layerMask, meshRenderingLayers))
                    #endif
                        lightingData.additionalLightsColor += LightingPhysicallyBased(brdfData, noClearCoat, light, inputData.normalWS, inputData.viewDirectionWS, 0.0, false);
                }
                #endif
                LIGHT_LOOP_BEGIN(pixelLightCount)
                    Light light = GetAdditionalLight(lightIndex, inputData, shadowMask, aoFactor);
                    #ifdef _LIGHT_LAYERS
                    if (IsMatchingLightLayer(light.layerMask, meshRenderingLayers))
                    #endif
                        lightingData.additionalLightsColor += LightingPhysicallyBased(brdfData, noClearCoat, light, inputData.normalWS, inputData.viewDirectionWS, 0.0, false);
                LIGHT_LOOP_END
                #endif

                return CalculateFinalColor(lightingData, 1.0).rgb;
            }

            void TerrainFrag(Varyings input, out half4 outColor : SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                , out uint outRenderingLayers : SV_Target1
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);

                float3 P = input.positionWS;
                float3 Ng = normalize(input.normalWS);
                float dist = distance(GetCameraPositionWS(), P);
                float detailFade = 1.0 - smoothstep(_DetailFadeStart, max(_DetailFadeEnd, _DetailFadeStart + 1.0), dist);
                float slope = 1.0 - saturate(Ng.y);
                float3 dPdx = ddx(P), dPdy = ddy(P);                          // for explicit-gradient sampling

                // ---- Macro variation: two octaves of the geology map (111 m and ~410 m periods) ------------
                float4 macro = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, P.xz * _MacroScale);
                float2 rotXZ = float2(P.x * 0.8 - P.z * 0.6, P.x * 0.6 + P.z * 0.8);
                float4 macro2 = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, rotXZ * (_MacroScale * 0.27) + 0.31);
                // Mid-frequency (~11 m) noise: bombing index, mid rock blend and ripple warp.
                float4 mid = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, P.xz * 0.093 + 0.17);

                // ---- Layer masks: slope for rock, flats and hollows for sand, scree between ----------------
                float skyAccess = saturate(input.baked.g);
                float rockNoise = (macro.r - 0.5) * 0.25 + (mid.r - 0.5) * 0.1 + (macro2.g - 0.5) * 0.1;
                float wRock = smoothstep(_RockSlope - _SlopeBlend, _RockSlope + _SlopeBlend, slope + rockNoise);
                float hollow = (1.0 - skyAccess) * 1.5 + (1.0 - smoothstep(0.0, 4.0, P.y)) * 0.25;
                // Geology G alone varies too little (std 0.07); mixing in A gives patches tens of metres wide.
                float sandNoise = 0.5 + (macro.g - 0.505) * 2.0 + (mid.a - 0.49) * 1.0;
                float sandMask = (1.0 - smoothstep(0.015, 0.06, slope))
                               * smoothstep(0.35, 0.65, sandNoise + (_SandAmount - 0.5) * 0.6 + hollow * 0.4);
                float wSand = (1.0 - wRock) * saturate(sandMask);
                float wGravel = saturate(1.0 - wRock - wSand);

                // ---- Cliff rock -------------------------------------------------------------------------
                float3 rockMid = 0, rockDetail = _RockDetailMean.rgb;
                float3 rockN = Ng;
                float streak = 0;
                float midBlend = smoothstep(0.32, 0.67, mid.g * 0.5 + macro.r * 0.5);
                float2 warp = (macro.rg - 0.5) * 2.0;                            // old shader's domain warp (m)
                float3 axisSign = Ng < 0 ? -1.0 : 1.0;
                float3 an = abs(Ng);
                float3 tw = pow(saturate(an - 0.3), 3.0);
                tw /= max(dot(tw, 1.0), 1e-5);
                tw *= step(0.02, tw);                                            // skip negligible projections
                tw /= max(dot(tw, 1.0), 1e-5);
                UNITY_BRANCH
                if (wRock > 0.001)
                {
                    float3 mX = 0, mY = 0, mZ = 0, dX = 0, dY = 0, dZ = 0;
                    float3 tsX = float3(0, 0, 1), tsY = float3(0, 0, 1), tsZ = float3(0, 0, 1);
                    // Y projection (plan view): covers every rock slope below about 45 degrees.
                    UNITY_BRANCH
                    if (tw.y > 0.0)
                        SampleRockProjection(float2(P.x * axisSign.y, P.z) + warp, float2(dPdx.x * axisSign.y, dPdx.z), float2(dPdy.x * axisSign.y, dPdy.z),
                                             midBlend, detailFade, mY, dY, tsY);
                    // Side projections only where the face is steep enough to need them.
                    UNITY_BRANCH
                    if (tw.x > 0.0)
                    {
                        SampleRockProjection(float2(P.z * axisSign.x, P.y) + float2(warp.y, 0), float2(dPdx.z * axisSign.x, dPdx.y), float2(dPdy.z * axisSign.x, dPdy.y),
                                             midBlend, detailFade, mX, dX, tsX);
                        streak += tw.x * SAMPLE_TEXTURE2D_GRAD(_Geology, sampler_Geology, float2(P.z * 0.35, P.y * 0.018),
                                                               float2(dPdx.z * 0.35, dPdx.y * 0.018), float2(dPdy.z * 0.35, dPdy.y * 0.018)).r;
                    }
                    UNITY_BRANCH
                    if (tw.z > 0.0)
                    {
                        SampleRockProjection(float2(-P.x * axisSign.z, P.y) + float2(warp.x, 0), float2(-dPdx.x * axisSign.z, dPdx.y), float2(-dPdy.x * axisSign.z, dPdy.y),
                                             midBlend, detailFade, mZ, dZ, tsZ);
                        streak += tw.z * SAMPLE_TEXTURE2D_GRAD(_Geology, sampler_Geology, float2(P.x * 0.35 + 3.1, P.y * 0.018),
                                                               float2(dPdx.x * 0.35, dPdx.y * 0.018), float2(dPdy.x * 0.35, dPdy.y * 0.018)).r;
                    }
                    rockMid = mX * tw.x + mY * tw.y + mZ * tw.z;
                    rockDetail = dX * tw.x + dY * tw.y + dZ * tw.z;
                    // Whiteout triplanar normal blend (Golus), with the UV flips above mirrored into the normals.
                    tsX.x *= axisSign.x; tsY.x *= axisSign.y; tsZ.x *= -axisSign.z;
                    tsX = float3(tsX.xy + Ng.zy, tsX.z * an.x);
                    tsY = float3(tsY.xy + Ng.xz, tsY.z * an.y);
                    tsZ = float3(tsZ.xy + Ng.xy, tsZ.z * an.z);
                    rockN = normalize(tsX.zyx * tw.x + tsY.xzy * tw.y + tsZ.xyz * tw.z);
                    streak = streak / max(tw.x + tw.z, 1e-4);
                }

                // Sedimentary strata: gently folded horizontal beds (world Y) with finer laminations, antialiased
                // by their own footprint so distant bands do not shimmer.
                float warpY = P.y + (macro.r - 0.5) * 6.0 + sin(P.x * 0.024 + P.z * 0.018) * 2.0;
                float strataCoord = warpY / _StrataThickness;
                float bandId = floor(strataCoord), bandF = frac(strataCoord);
                float bandAA = max(fwidth(strataCoord), 1e-4);
                float bandRnd = lerp(Hash11(bandId - 1.0 + 17.0), Hash11(bandId + 17.0), saturate(bandF / (bandAA * 1.5)));
                float fineCoord = strataCoord * 4.3;
                float fineRnd = Hash11(floor(fineCoord) + 3.1);
                float fineFade = saturate(1.0 - fwidth(fineCoord) * 1.5);
                float strataAmt = _StrataStrength * smoothstep(0.1, 0.45, slope);      // beds read on faces, not as contour rings on gentle slopes
                float3 strataTint = lerp(_StrataDark.rgb, _StrataLight.rgb, saturate(bandRnd * 0.5 + macro.r * 0.5));
                strataTint = lerp(float3(1, 1, 1), strataTint * lerp(1.0, lerp(0.96, 1.04, fineRnd), fineFade), strataAmt);
                // Desert varnish: dark streaks hanging from each ledge on steep faces.
                float varnish = smoothstep(0.45, 0.8, streak) * smoothstep(0.2, 1.0, bandF) * smoothstep(0.15, 0.4, slope) * _StreakStrength;

                float3 rockAlbedo = rockMid * _RockTint.rgb * strataTint
                                  * lerp(1.0, rockDetail / max(_RockDetailMean.rgb, 1e-3), _RockDetailStrength * detailFade)
                                  * (1.0 - varnish * float3(0.55, 0.6, 0.65));
                float rockDetailLuma = dot(rockDetail / max(_RockDetailMean.rgb, 1e-3), float3(0.2126, 0.7152, 0.0722));

                // ---- Scree and sand from the ground arrays ------------------------------------------------
                float k = mid.r * 8.0;
                float2 dXZx = dPdx.xz, dXZy = dPdy.xz;
                GroundTap gravel = (GroundTap)0;
                gravel.ah = float4(_GravelMean.rgb, 0.5); gravel.nra = float4(0.5, 0.5, 0.85, 1.0);
                UNITY_BRANCH
                if (wGravel > 0.001 && detailFade > 0.001)
                {
                    float s = 1.0 / _GravelSize;
                    gravel = SampleGround(P.xz * s, dXZx * s, dXZy * s, _GravelLayer, k, 1.0);
                }
                GroundTap sand = (GroundTap)0;
                sand.ah = float4(_SandMean.rgb, 0.5); sand.nra = float4(0.5, 0.5, 0.9, 1.0);
                UNITY_BRANCH
                if (wSand > 0.001 && detailFade > 0.001)
                {
                    float s = 1.0 / _SandSize;
                    sand = SampleGround(P.xz * s, dXZx * s, dXZy * s, _SandLayer, k + 3.7, 1.0);
                }
                // Texture/mean ratios are clamped so bright pebbles do not turn into white specks under the tint.
                float3 gravelAlbedo = _GravelColor.rgb * lerp(1.0, min(gravel.ah.rgb / max(_GravelMean.rgb, 1e-3), 1.8), 0.75 * detailFade);
                float3 sandAlbedo = _Sand.rgb * (0.70 + macro.r * 0.28) * lerp(1.0, min(sand.ah.rgb / max(_SandMean.rgb, 1e-3), 1.8), detailFade);

                // ---- Height blend (Berms style): sand fills hollows, rock and scree keep their relief ----------
                float3 w = float3(wRock, wGravel, wSand);
                float3 hl = float3(lerp(0.5, saturate(rockDetailLuma * 0.5), detailFade), gravel.ah.a, 1.0 - sand.ah.a * 0.6) + w * 1.5;
                float depth = lerp(1.5, _HeightBlend, detailFade);
                float hm = max(hl.x, max(hl.y, hl.z)) - depth;
                float3 bw = max(hl - hm, 0.0) * step(0.001, w);
                bw /= max(dot(bw, 1.0), 1e-4);

                // ---- Sand ripples: skewed sine crests across the wind, wavy, fading with distance ---------
                float2 wind = normalize(_WindDirection.xz + float2(1e-5, 0));
                float along = dot(P.xz, wind), across = dot(P.xz, float2(-wind.y, wind.x));
                float lambda = max(_RippleWavelength, 0.02);
                float crestWarp = 0.35 * sin(across * 0.9 + sin(along * 0.37) * 1.5) + (mid.g - 0.5) * 1.6;
                float phase = (along + crestWarp * lambda * 3.0) / lambda * 6.2831853;
                float rippleFade = detailFade * saturate(1.5 - fwidth(along) / lambda * 3.0)
                                 * (1.0 - smoothstep(0.02, 0.1, slope)) * _RippleStrength * lerp(0.4, 1.0, macro2.r);
                float rippleSlope = 0.008 * (6.2831853 / lambda) * (cos(phase) + 0.5 * cos(2.0 * phase)) * rippleFade;
                // Megaripples / wind streaks at 9x the wavelength keep the wind direction readable to ~50 m.
                float lambda2 = lambda * 9.0;
                float phase2 = (along + crestWarp * lambda2 * 0.8) / lambda2 * 6.2831853;
                float rippleFade2 = saturate(1.0 - smoothstep(_DetailFadeStart, _DetailFadeEnd * 0.7, dist)) * saturate(1.5 - fwidth(along) / lambda2 * 3.0)
                                  * (1.0 - smoothstep(0.02, 0.1, slope)) * _RippleStrength;
                rippleSlope += 0.05 * (6.2831853 / lambda2) * (cos(phase2) + 0.5 * cos(2.0 * phase2)) * rippleFade2;
                sandAlbedo *= 1.0 + 0.06 * sin(phase) * rippleFade + 0.04 * sin(phase2) * rippleFade2;

                // ---- Combine ------------------------------------------------------------------------------
                float groundStrength = _GroundNormalStrength * detailFade;
                float2 gXY = (gravel.nra.rg * 2.0 - 1.0) * groundStrength;
                float2 sXY = (sand.nra.rg * 2.0 - 1.0) * groundStrength;
                float3 gravelN = GroundNormalWS(Ng, float3(gXY, sqrt(saturate(1.0 - dot(gXY, gXY))) + 1e-4));
                float3 sandN = GroundNormalWS(Ng, float3(sXY, sqrt(saturate(1.0 - dot(sXY, sXY))) + 1e-4));
                sandN = normalize(sandN - float3(wind.x, 0.0, wind.y) * rippleSlope);

                float3 albedo = rockAlbedo * bw.x + gravelAlbedo * bw.y + sandAlbedo * bw.z;
                albedo *= lerp(1.0, lerp(0.82, 1.14, macro2.r), _MacroStrength);
                albedo *= lerp(0.88, 1.1, mid.a);                                  // ~11 m variation that survives the detail fade
                float3 N = normalize(rockN * bw.x + gravelN * bw.y + sandN * bw.z);
                float smoothness = _RockSmoothness * bw.x + saturate(1.0 - gravel.nra.b) * 0.85 * bw.y + saturate(1.0 - sand.nra.b) * 0.85 * bw.z;
                float ao = lerp(1.0, lerp(0.72, 1.0, saturate(rockDetailLuma)), detailFade) * bw.x + gravel.nra.a * bw.y + sand.nra.a * bw.z;
                ao *= lerp(0.8, 1.0, macro.r);                                    // old macro cavity

                // Mid-scale relief (the old _Relief bump from the sandstone luminance) plus bed ledges, via
                // screen-space height derivatives; fades out by 210 m exactly as before.
                float ledge = _StrataRelief * 0.3 * bandF * bandF * strataAmt * saturate(1.0 - bandAA * 4.0);
                float h = (dot(rockMid, float3(0.21, 0.72, 0.07)) * _Relief + ledge) * bw.x * saturate(1.0 - dist / 210.0);
                float3 r1 = cross(dPdy, N), r2 = cross(N, dPdx);
                float det = dot(dPdx, r1);
                float3 grad = (ddx(h) * r1 + ddy(h) * r2) * sign(det) / max(abs(det), 1e-5);
                N = normalize(N - clamp(grad, -0.4, 0.4));

                // ---- Lighting -----------------------------------------------------------------------------
                InputData inputData = (InputData)0;
                inputData.positionWS = P;
                inputData.normalWS = N;
                inputData.viewDirectionWS = GetWorldSpaceNormalizeViewDir(P);
                inputData.shadowCoord = TransformWorldToShadowCoord(P);
                inputData.fogCoord = InitializeInputDataFog(float4(P, 1.0), input.fogFactor);
                inputData.bakedGI = SampleSH(N);
                inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
                inputData.shadowMask = half4(1, 1, 1, 1);

                SurfaceData surfaceData = (SurfaceData)0;
                surfaceData.albedo = albedo;
                surfaceData.metallic = 0;
                surfaceData.specular = 0;
                surfaceData.smoothness = smoothness;
                surfaceData.normalTS = float3(0, 0, 1);
                surfaceData.occlusion = ao * lerp(1.0, skyAccess, _SkyOcclusion);
                surfaceData.alpha = 1;

                float3 color = TerrainLighting(inputData, surfaceData, input.baked.r);
                color = lerp(color, MixFog(color, inputData.fogCoord), _FogBlend);

                // ---- Desert Terrain distance haze --------------------------------------------------------
                // Same model and same values up to _HazeFarStart (the Berms ground toe uses this haze too), then
                // optionally thinner with distance and with height (optical depth averaged along the ray through an
                // exponential layer above _HazeBaseHeight), so far ridge tops keep their form under a high sun.
                float hazeDist = max(0.0, dist - 38.0);
                hazeDist = min(hazeDist, _HazeFarStart) + max(hazeDist - _HazeFarStart, 0.0) * _HazeFarScale;
                float opticalDepth = hazeDist * _HazeDensity;
                UNITY_BRANCH
                if (_HazeHeightFalloff > 0.0)
                {
                    float h0 = max(GetCameraPositionWS().y - _HazeBaseHeight, 0.0) / _HazeHeightFalloff;
                    float h1 = max(P.y - _HazeBaseHeight, 0.0) / _HazeHeightFalloff;
                    float dh = h1 - h0;
                    opticalDepth *= abs(dh) > 1e-3 ? (exp(-h0) - exp(-h1)) / dh : exp(-h0);
                }
                float haze = 1.0 - exp(-opticalDepth);
                haze = saturate(haze + exp(-max(0.0, P.y) * 0.06) * 0.11);
                float clockActive = saturate(_AthenTerrainTime.x);
                float3 hazeColor = _Haze.rgb * lerp(float3(1, 1, 1), _AthenTerrainHazeScale.rgb, clockActive);
                // high, strong sun (noon, not the evening sun or the night key): optional cooler, lighter haze
                float highSun = smoothstep(0.3, 0.6, _MainLightPosition.y) * smoothstep(0.8, 1.5, dot(_MainLightColor.rgb, float3(0.2126, 0.7152, 0.0722)));
                hazeColor *= lerp(float3(1, 1, 1), _HazeNoonTint.rgb, highSun);
                color = lerp(color, hazeColor, haze);

                outColor = half4(color, 1.0);
                #ifdef _WRITE_RENDERING_LAYERS
                outRenderingLayers = EncodeMeshRenderingLayer();
                #endif
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex ShadowVert
            #pragma fragment ShadowFrag
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

            float3 _LightDirection;
            float3 _LightPosition;

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };

            Varyings ShadowVert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
                #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 lightDirectionWS = normalize(_LightPosition - positionWS);
                #else
                float3 lightDirectionWS = _LightDirection;
                #endif
                output.positionCS = ApplyShadowClamping(TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS)));
                return output;
            }
            half4 ShadowFrag(Varyings input) : SV_TARGET
            {
                UNITY_SETUP_INSTANCE_ID(input);
                return 0;
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ZWrite On
            ColorMask R
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DepthVert
            #pragma fragment DepthFrag
            #pragma multi_compile_instancing

            struct Attributes { float4 positionOS : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID UNITY_VERTEX_OUTPUT_STEREO };

            Varyings DepthVert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                return output;
            }
            half DepthFrag(Varyings input) : SV_TARGET
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                return input.positionCS.z;
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            ZWrite On
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DepthNormalsVert
            #pragma fragment DepthNormalsFrag
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/RenderingLayers.hlsl"
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            #pragma multi_compile_instancing

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID UNITY_VERTEX_OUTPUT_STEREO };

            Varyings DepthNormalsVert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                return output;
            }
            // Geometric normals only: SSAO in PC_Renderer reconstructs from depth, and screen-space decals need
            // a stable base normal rather than the full layered shading (which would double the terrain cost).
            void DepthNormalsFrag(Varyings input, out half4 outNormalWS : SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                , out uint outRenderingLayers : SV_Target1
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                #if defined(_GBUFFER_NORMALS_OCT)
                    float3 normalWS = normalize(input.normalWS);
                    float2 octNormalWS = PackNormalOctQuadEncode(normalWS);
                    outNormalWS = half4(PackFloat2To888(saturate(octNormalWS * 0.5 + 0.5)), 0.0);
                #else
                    outNormalWS = half4(NormalizeNormalPerPixel(input.normalWS), 0.0);
                #endif
                #ifdef _WRITE_RENDERING_LAYERS
                    outRenderingLayers = EncodeMeshRenderingLayer();
                #endif
            }
            ENDHLSL
        }
    }
    FallBack Off
}
