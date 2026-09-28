// Outer Berms walkable ground (26 Sep 2026). Four height-blended PBR layers from Poly Haven CC0 scans,
// painted by a world-space splat (BermsGroundSplat.png): R compacted road gravel, G wind-deposited sand,
// B cracked crust; the remainder is dry pebbly ground. Full URP lighting: main + additional lights,
// SSAO, screen-space decals (depth/normals passes) and fog. Distance haze and the edge blend toward the
// Desert Terrain rock match the surrounding backdrop so the playable floor has no visible seam.
Shader "Athen Hill/Berms Ground"
{
    Properties
    {
        _Splat("Splat (R road, G sand, B crust, A 1-compaction)", 2D) = "black" {}
        _Compaction("Packed-ground darkening", Range(0, 1)) = .3
        _SplatRect("Splat rect (x0, z0, 1/width, 1/depth)", Vector) = (-104, -54, .0227, .0098)
        _AlbedoHeight("Layer albedo + height (array)", 2DArray) = "" {}
        _NormalRoughAO("Layer normal XY, roughness, AO (array)", 2DArray) = "" {}
        _LayerSize("Layer size in metres (base, sand, road, crust)", Vector) = (4, 1.8, 2.5, 4)
        _Tint0("Base tint", Color) = (1, 1, 1, 1)
        _Tint1("Sand tint", Color) = (1, 1, 1, 1)
        _Tint2("Road tint", Color) = (1, 1, 1, 1)
        _Tint3("Crust tint", Color) = (1, 1, 1, 1)
        _Saturation("Albedo saturation", Range(0, 1.5)) = .72
        _NormalStrength("Normal strength", Range(0, 2)) = 1
        _HeightBlend("Height blend depth", Range(.01, 1)) = .18
        _Geology("Macro variation (linear)", 2D) = "gray" {}
        _MacroScale("Macro variation repeats per metre", Range(.001, .2)) = .021
        _MacroStrength("Macro variation strength", Range(0, 1)) = .35
        _SkyOcclusion("Baked sky access strength", Range(0, 1)) = .5
        _RockTex("Backdrop rock albedo", 2D) = "white" {}
        _RockTint("Backdrop rock tint", Color) = (1, 1, 1, 1)
        _RockScale("Backdrop rock repeats per metre", Range(.02, 1)) = .073
        _EdgeBlend("Edge blend width (m)", Range(0, 20)) = 7
        _Haze("Distance haze", Color) = (.62, .58, .51, 1)
        _HazeDensity("Atmospheric density", Range(0, .02)) = .0048
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        TEXTURE2D(_Splat); SAMPLER(sampler_Splat);
        TEXTURE2D_ARRAY(_AlbedoHeight); SAMPLER(sampler_AlbedoHeight);
        TEXTURE2D_ARRAY(_NormalRoughAO); SAMPLER(sampler_NormalRoughAO);
        TEXTURE2D(_Geology); SAMPLER(sampler_Geology);
        TEXTURE2D(_RockTex); SAMPLER(sampler_RockTex);
        CBUFFER_START(UnityPerMaterial)
        float4 _SplatRect, _LayerSize, _Tint0, _Tint1, _Tint2, _Tint3, _RockTint, _Haze;
        float _Compaction, _Saturation, _NormalStrength, _HeightBlend, _MacroScale, _MacroStrength, _SkyOcclusion, _RockScale, _EdgeBlend, _HazeDensity;
        CBUFFER_END
        float4 _AthenTerrainTime;
        float4 _AthenTerrainHazeScale;

        struct GroundSample { float3 albedo; float3 normalTS; float roughness; float ao; };

        float4 Weights(float3 world, out float edge, out float packed)
        {
            float2 uv = (world.xz - _SplatRect.xy) * _SplatRect.zw;
            float4 s = SAMPLE_TEXTURE2D(_Splat, sampler_Splat, uv);
            packed = 1 - s.a;
            float2 dEdge = min(uv, 1 - uv) / _SplatRect.zw;
            edge = saturate(1 - min(dEdge.x, dEdge.y) / max(_EdgeBlend, .001));
            float base = saturate(1 - s.r - s.g - s.b);
            return float4(base, s.g, s.r, s.b); // layer order: base, sand, road, crust
        }

        GroundSample SampleGround(float3 world, float3 normalWS, out float edge)
        {
            float packed;
            float4 w = Weights(world, edge, packed);
            float macro = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, world.xz * _MacroScale).r;
            float macro2 = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, world.xz * _MacroScale * 3.7 + .31).g;
            float2 p = world.xz;
            // base layer at two scales/rotations to hide repetition
            float2 uvA = p / _LayerSize.x;
            float2 uvB = float2(p.x * .8 - p.y * .6, p.x * .6 + p.y * .8) / (_LayerSize.x * 2.3) + .37;
            float blendAB = smoothstep(.35, .65, macro2);
            float4 ah0 = lerp(SAMPLE_TEXTURE2D_ARRAY(_AlbedoHeight, sampler_AlbedoHeight, uvA, 0), SAMPLE_TEXTURE2D_ARRAY(_AlbedoHeight, sampler_AlbedoHeight, uvB, 0), blendAB);
            float4 nr0 = lerp(SAMPLE_TEXTURE2D_ARRAY(_NormalRoughAO, sampler_NormalRoughAO, uvA, 0), SAMPLE_TEXTURE2D_ARRAY(_NormalRoughAO, sampler_NormalRoughAO, uvB, 0), blendAB);
            float4 ah1 = SAMPLE_TEXTURE2D_ARRAY(_AlbedoHeight, sampler_AlbedoHeight, p / _LayerSize.y, 1);
            float4 nr1 = SAMPLE_TEXTURE2D_ARRAY(_NormalRoughAO, sampler_NormalRoughAO, p / _LayerSize.y, 1);
            float4 ah2 = SAMPLE_TEXTURE2D_ARRAY(_AlbedoHeight, sampler_AlbedoHeight, p / _LayerSize.z, 2);
            float4 nr2 = SAMPLE_TEXTURE2D_ARRAY(_NormalRoughAO, sampler_NormalRoughAO, p / _LayerSize.z, 2);
            float4 ah3 = SAMPLE_TEXTURE2D_ARRAY(_AlbedoHeight, sampler_AlbedoHeight, p / _LayerSize.w, 3);
            float4 nr3 = SAMPLE_TEXTURE2D_ARRAY(_NormalRoughAO, sampler_NormalRoughAO, p / _LayerSize.w, 3);
            // height blend: sand fills hollows (inverted height), others use their own relief
            float4 h = float4(ah0.a, 1 - ah1.a * .6, ah2.a, ah3.a) + w * 1.5;
            float hm = max(max(h.x, h.y), max(h.z, h.w)) - _HeightBlend;
            float4 b = max(h - hm, 0) * step(.001, w);
            b /= max(dot(b, 1), 1e-4);
            GroundSample g;
            g.albedo = ah0.rgb * _Tint0.rgb * b.x + ah1.rgb * _Tint1.rgb * b.y + ah2.rgb * _Tint2.rgb * b.z + ah3.rgb * _Tint3.rgb * b.w;
            g.albedo *= lerp(1, lerp(.82, 1.14, macro), _MacroStrength);
            // mid-frequency variation (1-10 m) breaks the flat look between texture detail and macro tint
            float mid = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, world.xz * .093 + .17).b;
            g.albedo *= lerp(.86, 1.1, mid);
            float luma = dot(g.albedo, float3(.3, .59, .11));
            g.albedo = lerp(luma.xxx, g.albedo, _Saturation);
            float4 nr = nr0 * b.x + nr1 * b.y + nr2 * b.z + nr3 * b.w;
            float2 nxy = (nr.rg * 2 - 1) * _NormalStrength;
            g.normalTS = normalize(float3(nxy, sqrt(saturate(1 - dot(nxy, nxy))) + 1e-4));
            g.roughness = nr.b * (1 - packed * .15); g.ao = nr.a;
            // packed ground (tyre ruts, trodden areas): darker, flatter relief
            g.albedo *= 1 - packed * _Compaction;
            g.normalTS = normalize(lerp(g.normalTS, float3(0, 0, 1), packed * .45));
            // blend toward the backdrop rock near the playable edge
            if (edge > 0)
            {
                float3 rock = SAMPLE_TEXTURE2D(_RockTex, sampler_RockTex, p * _RockScale).rgb * _RockTint.rgb;
                g.albedo = lerp(g.albedo, rock, edge * .85);
                g.normalTS = normalize(lerp(g.normalTS, float3(0, 0, 1), edge * .7));
            }
            return g;
        }

        float3 GroundNormalWS(float3 normalWS, float3 normalTS)
        {
            float3 n = normalize(normalWS);
            float3 t = normalize(float3(1, 0, 0) - n * n.x);
            float3 bt = cross(t, n);
            return normalize(t * normalTS.x + bt * normalTS.y + n * normalTS.z);
        }
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fragment _ _DBUFFER_MRT1 _DBUFFER_MRT2 _DBUFFER_MRT3
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile _ _LIGHT_LAYERS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile _ EVALUATE_SH_MIXED EVALUATE_SH_VERTEX
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DBuffer.hlsl"
            struct Attributes { float4 positionOS:POSITION; float3 normalOS:NORMAL; float4 color:COLOR; };
            struct Varyings { float4 positionCS:SV_POSITION; float3 positionWS:TEXCOORD0; float3 normalWS:TEXCOORD1; float2 baked:TEXCOORD2; float fog:TEXCOORD3; };
            Varyings Vert(Attributes i)
            {
                Varyings o; o.positionWS = TransformObjectToWorld(i.positionOS.xyz); o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS); o.baked = i.color.rg; o.fog = ComputeFogFactor(o.positionCS.z); return o;
            }
            half4 Frag(Varyings i) : SV_Target
            {
                float edge;
                GroundSample g = SampleGround(i.positionWS, i.normalWS, edge);
                float3 n = GroundNormalWS(i.normalWS, g.normalTS);
                InputData d = (InputData)0;
                d.positionWS = i.positionWS; d.normalWS = n; d.viewDirectionWS = GetWorldSpaceNormalizeViewDir(i.positionWS);
                d.shadowCoord = TransformWorldToShadowCoord(i.positionWS); d.fogCoord = i.fog;
                d.bakedGI = SampleSH(n); d.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS); d.shadowMask = half4(1, 1, 1, 1);
                SurfaceData s = (SurfaceData)0;
                s.albedo = g.albedo; s.metallic = 0; s.specular = 0; s.smoothness = saturate(1 - g.roughness) * .85; s.normalTS = g.normalTS;
                s.occlusion = g.ao * lerp(1, saturate(i.baked.g * 1.15), _SkyOcclusion); s.alpha = 1;
                #if defined(_DBUFFER)
                ApplyDecalToSurfaceData(i.positionCS, s, d);
                #endif
                half4 color = UniversalFragmentPBR(d, s);
                color.rgb = MixFog(color.rgb, d.fogCoord);
                // same distance haze model as Desert Terrain so the floor meets the backdrop cleanly
                float dist = distance(_WorldSpaceCameraPos, i.positionWS);
                float haze = 1 - exp(-max(0, dist - 38) * _HazeDensity);
                haze = saturate(haze + exp(-max(0, i.positionWS.y) * .06) * .11 * saturate((dist - 20) / 40));
                float clockActive = saturate(_AthenTerrainTime.x);
                float3 hazeColor = _Haze.rgb * lerp(float3(1, 1, 1), _AthenTerrainHazeScale.rgb, clockActive);
                color.rgb = lerp(color.rgb, hazeColor, haze);
                return half4(color.rgb, 1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma vertex V
            #pragma fragment F
            float4 V(float4 p:POSITION):SV_POSITION { return TransformObjectToHClip(p.xyz); }
            half F():SV_Target { return 0; }
            ENDHLSL
        }
        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            ZWrite On
            HLSLPROGRAM
            #pragma vertex V
            #pragma fragment F
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            struct A { float4 p:POSITION; float3 n:NORMAL; };
            struct VO { float4 p:SV_POSITION; float3 w:TEXCOORD0; float3 n:TEXCOORD1; };
            VO V(A i) { VO o; o.w = TransformObjectToWorld(i.p.xyz); o.p = TransformWorldToHClip(o.w); o.n = TransformObjectToWorldNormal(i.n); return o; }
            half4 F(VO i):SV_Target
            {
                float edge; GroundSample g = SampleGround(i.w, i.n, edge);
                float3 n = GroundNormalWS(i.n, g.normalTS);
                #if defined(_GBUFFER_NORMALS_OCT)
                float2 oct = PackNormalOctQuadEncode(n); return half4(PackFloat2To888(saturate(oct * .5 + .5)), 0);
                #else
                return half4(NormalizeNormalPerPixel(n), 0);
                #endif
            }
            ENDHLSL
        }
    }
}
