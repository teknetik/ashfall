#ifndef UNIVERSAL_FORWARD_LIT_PASS_INCLUDED
#define UNIVERSAL_FORWARD_LIT_PASS_INCLUDED

#include "MasonryLitInput.hlsl"
#define REQUIRES_WORLD_SPACE_POS_INTERPOLATOR
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

#if defined(LOD_FADE_CROSSFADE)
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/LODCrossFade.hlsl"
#endif

#if defined(_PARALLAXMAP)
#define REQUIRES_TANGENT_SPACE_VIEW_DIR_INTERPOLATOR
#endif

#if (defined(_NORMALMAP) || (defined(_PARALLAXMAP) && !defined(REQUIRES_TANGENT_SPACE_VIEW_DIR_INTERPOLATOR))) || defined(_DETAIL)
#define REQUIRES_WORLD_SPACE_TANGENT_INTERPOLATOR
#endif


// Original world-space scalar mask: broad accumulations stay independent of tile UVs.
float WardHash(float3 p) { p = frac(p * .1031); p += dot(p,p.yzx + 33.33); return frac((p.x+p.y)*p.z); }
float2 WardHash2(float2 p) { float3 p3 = frac(float3(p.xyx) * float3(.1031, .1030, .0973)); p3 += dot(p3, p3.yzx + 33.33); return frac((p3.xx + p3.yz) * p3.zy); }

// Voronoi cell: x = distance to the nearest feature point, y = that cell's random id, zw = offset to the point
float4 WardCells(float2 p)
{
    float2 i = floor(p), f = frac(p);
    float best = 8; float id = 0; float2 off = 0;
    [unroll] for (int y = -1; y <= 1; y++)
    [unroll] for (int x = -1; x <= 1; x++)
    {
        float2 g = float2(x, y); float2 r = WardHash2(i + g);
        float2 d = g + r - f; float dd = dot(d, d);
        if (dd < best) { best = dd; id = WardHash2(i + g + 17.3).x; off = d; }
    }
    return float4(sqrt(best), id, off);
}

// distance to the nearest Voronoi cell border (F2 - F1 style), for crack lines
float WardCellEdge(float2 p)
{
    float2 i = floor(p), f = frac(p);
    float2 mr = 0; float md = 8;
    [unroll] for (int y = -1; y <= 1; y++)
    [unroll] for (int x = -1; x <= 1; x++)
    { float2 g = float2(x, y); float2 r = g + WardHash2(i + g) - f; float d = dot(r, r); if (d < md) { md = d; mr = r; } }
    md = 8;
    [loop] for (int y2 = -1; y2 <= 1; y2++)
    [loop] for (int x2 = -1; x2 <= 1; x2++)
    {
        float2 g = float2(x2, y2); float2 r = g + WardHash2(i + g) - f;
        if (dot(mr - r, mr - r) > .00001) md = min(md, dot(.5 * (mr + r), normalize(r - mr)));
    }
    return md;
}

float WardNoise(float3 p)
{
    float3 a=floor(p), f=frac(p); f=f*f*(3-2*f);
    return lerp(lerp(lerp(WardHash(a),WardHash(a+float3(1,0,0)),f.x),lerp(WardHash(a+float3(0,1,0)),WardHash(a+float3(1,1,0)),f.x),f.y),
                lerp(lerp(WardHash(a+float3(0,0,1)),WardHash(a+float3(1,0,1)),f.x),lerp(WardHash(a+float3(0,1,1)),WardHash(a+1),f.x),f.y),f.z);
}

// keep this file in sync with LitGBufferPass.hlsl

struct Attributes
{
    float4 positionOS   : POSITION;
    float3 normalOS     : NORMAL;
    float4 tangentOS    : TANGENT;
    float2 texcoord     : TEXCOORD0;
    float2 staticLightmapUV   : TEXCOORD1;
    float2 dynamicLightmapUV  : TEXCOORD2;
    half4 color               : COLOR;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct Varyings
{
    float2 uv                       : TEXCOORD0;

#if defined(REQUIRES_WORLD_SPACE_POS_INTERPOLATOR)
    float3 positionWS               : TEXCOORD1;
#endif

    float3 normalWS                 : TEXCOORD2;
#if defined(REQUIRES_WORLD_SPACE_TANGENT_INTERPOLATOR)
    half4 tangentWS                : TEXCOORD3;    // xyz: tangent, w: sign
#endif

#ifdef _ADDITIONAL_LIGHTS_VERTEX
    half4 fogFactorAndVertexLight   : TEXCOORD5; // x: fogFactor, yzw: vertex light
#else
    half  fogFactor                 : TEXCOORD5;
#endif

#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR)
    float4 shadowCoord              : TEXCOORD6;
#endif

#if defined(REQUIRES_TANGENT_SPACE_VIEW_DIR_INTERPOLATOR)
    half3 viewDirTS                : TEXCOORD7;
#endif

    DECLARE_LIGHTMAP_OR_SH(staticLightmapUV, vertexSH, 8);
#ifdef DYNAMICLIGHTMAP_ON
    float2  dynamicLightmapUV : TEXCOORD9; // Dynamic lightmap UVs
#endif

#ifdef USE_APV_PROBE_OCCLUSION
    float4 probeOcclusion : TEXCOORD10;
#endif

    half4 blockColor                : TEXCOORD11; // rgb per-block tint (0.5 neutral), a per-block occlusion
    half4 wearData                  : TEXCOORD12; // x runoff, y worn arris, z rust (mesh UV1.xy, UV2.x)

    float4 positionCS               : SV_POSITION;

    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

void InitializeInputData(Varyings input, half3 normalTS, out InputData inputData)
{
    inputData = (InputData)0;

#if defined(REQUIRES_WORLD_SPACE_POS_INTERPOLATOR)
    inputData.positionWS = input.positionWS;
#endif

#if defined(DEBUG_DISPLAY)
    inputData.positionCS = input.positionCS;
#endif

    half3 viewDirWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
#if defined(_NORMALMAP) || defined(_DETAIL)
    float sgn = input.tangentWS.w;      // should be either +1 or -1
    float3 bitangent = sgn * cross(input.normalWS.xyz, input.tangentWS.xyz);
    half3x3 tangentToWorld = half3x3(input.tangentWS.xyz, bitangent.xyz, input.normalWS.xyz);

    #if defined(_NORMALMAP)
    inputData.tangentToWorld = tangentToWorld;
    #endif
    inputData.normalWS = TransformTangentToWorld(normalTS, tangentToWorld);
#else
    inputData.normalWS = input.normalWS;
#endif

    inputData.normalWS = NormalizeNormalPerPixel(inputData.normalWS);
    inputData.viewDirectionWS = viewDirWS;

#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR)
    inputData.shadowCoord = input.shadowCoord;
#elif defined(MAIN_LIGHT_CALCULATE_SHADOWS)
    inputData.shadowCoord = TransformWorldToShadowCoord(inputData.positionWS);
#else
    inputData.shadowCoord = float4(0, 0, 0, 0);
#endif
#ifdef _ADDITIONAL_LIGHTS_VERTEX
    inputData.fogCoord = InitializeInputDataFog(float4(input.positionWS, 1.0), input.fogFactorAndVertexLight.x);
    inputData.vertexLighting = input.fogFactorAndVertexLight.yzw;
#else
    inputData.fogCoord = InitializeInputDataFog(float4(input.positionWS, 1.0), input.fogFactor);
#endif
                           
    inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);  

    #if defined(DEBUG_DISPLAY)
    #if defined(DYNAMICLIGHTMAP_ON)
    inputData.dynamicLightmapUV = input.dynamicLightmapUV;
    #endif
    #if defined(LIGHTMAP_ON)
    inputData.staticLightmapUV = input.staticLightmapUV;
    #else
    inputData.vertexSH = input.vertexSH;
    #endif
    #if defined(USE_APV_PROBE_OCCLUSION)
    inputData.probeOcclusion = input.probeOcclusion;
    #endif
    #endif
}

void InitializeBakedGIData(Varyings input, inout InputData inputData)
{
    #if defined(_SCREEN_SPACE_IRRADIANCE)
    inputData.bakedGI = SAMPLE_GI(_ScreenSpaceIrradiance, input.positionCS.xy, inputData.normalWS);
    #elif defined(DYNAMICLIGHTMAP_ON)
    inputData.bakedGI = SAMPLE_GI(input.staticLightmapUV, input.dynamicLightmapUV, input.vertexSH, inputData.normalWS);
    inputData.shadowMask = SAMPLE_SHADOWMASK(input.staticLightmapUV);
    #elif !defined(LIGHTMAP_ON) && (defined(PROBE_VOLUMES_L1) || defined(PROBE_VOLUMES_L2))
    inputData.bakedGI = SAMPLE_GI(input.vertexSH,
        GetAbsolutePositionWS(inputData.positionWS),
        inputData.normalWS,
        inputData.viewDirectionWS,
        input.positionCS.xy,
        input.probeOcclusion,
        inputData.shadowMask);
    #else
    inputData.bakedGI = SAMPLE_GI(input.staticLightmapUV, input.vertexSH, inputData.normalWS);
    inputData.shadowMask = SAMPLE_SHADOWMASK(input.staticLightmapUV);
    #endif
}

///////////////////////////////////////////////////////////////////////////////
//                  Vertex and Fragment functions                            //
///////////////////////////////////////////////////////////////////////////////

// Used in Standard (Physically Based) shader
Varyings LitPassVertex(Attributes input)
{
    Varyings output = (Varyings)0;

    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);

    VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS.xyz);

    // normalWS and tangentWS already normalize.
    // this is required to avoid skewing the direction during interpolation
    // also required for per-vertex lighting and SH evaluation
    VertexNormalInputs normalInput = GetVertexNormalInputs(input.normalOS, input.tangentOS);

    half3 vertexLight = VertexLighting(vertexInput.positionWS, normalInput.normalWS);

    half fogFactor = 0;
    #if !defined(_FOG_FRAGMENT)
        fogFactor = ComputeFogFactor(vertexInput.positionCS.z);
    #endif

    output.uv = TRANSFORM_TEX(input.texcoord, _BaseMap);
    output.blockColor = input.color;
    // Masonry wear channels ride in UV1/UV2 (the hall and Ward masonry buildings are probe-lit, never lightmapped)
#if defined(LIGHTMAP_ON) || defined(DYNAMICLIGHTMAP_ON)
    output.wearData = half4(0, 0, 0, 0);
#else
    output.wearData = half4(input.staticLightmapUV.x, input.staticLightmapUV.y, input.dynamicLightmapUV.x, input.dynamicLightmapUV.y);
#endif

    // already normalized from normal transform to WS.
    output.normalWS = normalInput.normalWS;
#if defined(REQUIRES_WORLD_SPACE_TANGENT_INTERPOLATOR) || defined(REQUIRES_TANGENT_SPACE_VIEW_DIR_INTERPOLATOR)
    real sign = input.tangentOS.w * GetOddNegativeScale();
    half4 tangentWS = half4(normalInput.tangentWS.xyz, sign);
#endif
#if defined(REQUIRES_WORLD_SPACE_TANGENT_INTERPOLATOR)
    output.tangentWS = tangentWS;
#endif

#if defined(REQUIRES_TANGENT_SPACE_VIEW_DIR_INTERPOLATOR)
    half3 viewDirWS = GetWorldSpaceNormalizeViewDir(vertexInput.positionWS);
    half3 viewDirTS = GetViewDirectionTangentSpace(tangentWS, output.normalWS, viewDirWS);
    output.viewDirTS = viewDirTS;
#endif

    OUTPUT_LIGHTMAP_UV(input.staticLightmapUV, unity_LightmapST, output.staticLightmapUV);
#ifdef DYNAMICLIGHTMAP_ON
    output.dynamicLightmapUV = input.dynamicLightmapUV.xy * unity_DynamicLightmapST.xy + unity_DynamicLightmapST.zw;
#endif
    OUTPUT_SH4(vertexInput.positionWS, output.normalWS.xyz, GetWorldSpaceNormalizeViewDir(vertexInput.positionWS), output.vertexSH, output.probeOcclusion);
#ifdef _ADDITIONAL_LIGHTS_VERTEX
    output.fogFactorAndVertexLight = half4(fogFactor, vertexLight);
#else
    output.fogFactor = fogFactor;
#endif

#if defined(REQUIRES_WORLD_SPACE_POS_INTERPOLATOR)
    output.positionWS = vertexInput.positionWS;
#endif

#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR)
    output.shadowCoord = GetShadowCoord(vertexInput);
#endif

    output.positionCS = vertexInput.positionCS;

    return output;
}

// Used in Standard (Physically Based) shader
void LitPassFragment(
    Varyings input
    , out half4 outColor : SV_Target0
#ifdef _WRITE_RENDERING_LAYERS
    , out uint outRenderingLayers : SV_Target1
#endif
)
{
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);

#if defined(_PARALLAXMAP)
#if defined(REQUIRES_TANGENT_SPACE_VIEW_DIR_INTERPOLATOR)
    half3 viewDirTS = input.viewDirTS;
#else
    half3 viewDirWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
    half3 viewDirTS = GetViewDirectionTangentSpace(input.tangentWS, input.normalWS, viewDirWS);
#endif
    ApplyPerPixelDisplacement(viewDirTS, input.uv);
#endif

    SurfaceData surfaceData;
    InitializeStandardLitSurfaceData(input.uv, surfaceData);
    float3 wardP = input.positionWS * _WearScale;
    float broad = WardNoise(wardP + float3(8.2,1.1,3.7));
    float broken = WardNoise(wardP*3.17 + float3(1.2,7.1,2.3));
    float stain = smoothstep(.24,.78,broad*.74+broken*.26)*_WearStrength;
    float baseDirt = (1-smoothstep(.08,2.3,input.positionWS.y)) * _BaseWear * smoothstep(.2,.65,broken);
    float wear = saturate(stain+baseDirt);
    surfaceData.albedo *= lerp(half3(1,1,1),_WearTint.rgb,wear);
    // Masonry: per-block tint from vertex RGB (0.5 = neutral) and per-block cavity/grime occlusion from vertex A.
    surfaceData.albedo *= lerp(half3(1,1,1), saturate(input.blockColor.rgb * 2.0h), _BlockTint);
    half blockAO = lerp(1.0h, input.blockColor.a, _BlockAO);
    surfaceData.occlusion *= blockAO;
    surfaceData.albedo *= lerp(1.0h, blockAO, _CavityAlbedo);
    surfaceData.smoothness *= 1-wear*.55;

    // ---- Ward masonry weathering (30 Sep 2026): runoff streaks under drip edges, rust trails under steel,
    // worn/chipped arrises and dust on upward faces. Weights are baked per vertex by art/ward_masonry_kit.
    float3 nW = normalize(input.normalWS);
    half vertical = saturate(1.0 - abs(nW.y) * 1.6);
    float along = input.positionWS.x * nW.z - input.positionWS.z * nW.x;
    float2 suv = float2(along * _StreakScale.x, -input.positionWS.y * _StreakScale.y);
    half3 streaks = SAMPLE_TEXTURE2D(_StreakMap, sampler_StreakMap, suv).rgb;
    half runoff = saturate(input.wearData.x * _StreakStrength) * vertical;
    half grime = saturate(runoff * (0.28h + 1.25h * streaks.r));
    half deposit = saturate(runoff * streaks.g * 1.4h) * (1 - grime);
    surfaceData.albedo *= lerp(half3(1,1,1), _StreakTint.rgb, grime);
    surfaceData.albedo *= lerp(half3(1,1,1), _DepositTint.rgb, deposit);
    surfaceData.smoothness *= 1 - grime * .3;
    half rust = saturate(input.wearData.z * _RustStrength) * vertical;
    half rustMask = saturate(rust * (0.2h + 1.6h * saturate(streaks.b + streaks.r * .35h)));
    surfaceData.albedo *= lerp(half3(1,1,1), _RustTint.rgb, rustMask);

    float3 eP = input.positionWS * _EdgeNoiseScale;
    half eN = WardNoise(eP) * .62 + WardNoise(eP * 2.7 + 5.3) * .38;
    half worn = saturate((input.wearData.y * _EdgeWear * 1.35h - eN - .25h) * 3.2h);
    half grit = saturate((input.wearData.y * _EdgeWear - .35h) * 2.5h) * saturate((eN - .62h) * 5);
    surfaceData.albedo *= lerp(half3(1,1,1), _EdgeTint.rgb, worn * (1 - grime * .7h));
    surfaceData.albedo *= 1 - grit * .38h;          // dirt caught in the broken edge
    surfaceData.smoothness *= 1 - worn * .5;

    // ---- battle scars (30 Sep, Carl: "this place saw a battle take place long ago"; West Gate reference):
    // old pitting everywhere, shrapnel scars in the baked impact clusters (UV2.y), grime packed on the arrises
    half damage = saturate(input.wearData.w * _BattleDamage);
    float2 wallUV = float2(along, input.positionWS.y);
    float4 pc = WardCells(wallUV * _PitScale);
    half pitOn = step(pc.y, _Pitting * .2h + damage * damage * .75h);   // sparse everywhere, dense in the impact clusters
    half pitR = .1h + .26h * frac(pc.y * 7.13h);
    half pit = pitOn * (1 - smoothstep(pitR * .45h, pitR, pc.x)) * vertical;
    half pitRim = pitOn * (1 - smoothstep(pitR, pitR * 1.6h, pc.x)) * (1 - pit) * vertical;
    float4 sc = WardCells(wallUV * _ScarScale + 3.7);
    half scarOn = step(sc.y, damage * .85h);
    half scarR = .3h + .25h * frac(sc.y * 5.31h);
    half scarCore = scarOn * (1 - smoothstep(scarR * .45h, scarR * .7h, sc.x));
    half scarRim = scarOn * (1 - smoothstep(scarR * .7h, scarR * 1.6h, sc.x)) * (1 - scarCore);
    half rays = saturate(WardNoise(float3(atan2(sc.w, sc.z) * 3.0h, sc.x * 9.0h, sc.y * 40.0h)) * 1.4h - .3h);
    surfaceData.albedo *= 1 - pit * .62h;
    surfaceData.albedo *= 1 + pitRim * .12h;                              // chipped, paler lip round each pit
    surfaceData.albedo = lerp(surfaceData.albedo, surfaceData.albedo * half3(1.22h, 1.18h, 1.1h), scarCore * .8h);
    surfaceData.albedo *= 1 - scarRim * (.25h + rays * .5h) * vertical;
    // hairline cracks through the damaged stone (Voronoi borders, broken up by noise)
    half crackE = WardCellEdge(wallUV * 1.35 + 11.3);
    half crackMask = saturate(damage * 1.6h - .35h) * saturate(WardNoise(float3(wallUV * 2.1, 3.3)) * 2.2h - .6h);
    half crack = (1 - smoothstep(.006h, .026h, crackE)) * crackMask * vertical;
    surfaceData.albedo *= 1 - crack * .7h;
    surfaceData.occlusion *= 1 - crack * .5h;
    surfaceData.smoothness *= 1 - (pit + scarCore) * .5h;
    // dents: tilt the normal towards the pit/scar centre (tangent frame follows the box-projected UVs)
    surfaceData.normalTS.xy += (pc.zw * pit * 2.2h + sc.zw * scarCore * 1.6h) * vertical;
    surfaceData.normalTS = normalize(surfaceData.normalTS);
    // arrises: mostly dark packed grime, with pale fresh chips only where the breakup noise is high
    half arris = saturate(input.wearData.y * 1.2h);
    surfaceData.albedo *= 1 - arris * _EdgeGrime * saturate(1.2h - eN * 1.3h) * .6h;

    half up = smoothstep(.45h, .92h, nW.y);
    half dustN = WardNoise(input.positionWS * 3.1 + 2.2);
    half dust = up * _TopDust * saturate(.45h + dustN * .9h);
    surfaceData.albedo = lerp(surfaceData.albedo, _DustTint.rgb * (0.85h + 0.3h * dustN), dust);
    surfaceData.smoothness *= 1 - dust * .6;

#ifdef LOD_FADE_CROSSFADE
    LODFadeCrossFade(input.positionCS);
#endif

    InputData inputData;
    InitializeInputData(input, surfaceData.normalTS, inputData);
    SETUP_DEBUG_TEXTURE_DATA(inputData, UNDO_TRANSFORM_TEX(input.uv, _BaseMap));

#if defined(_DBUFFER)
    ApplyDecalToSurfaceData(input.positionCS, surfaceData, inputData);
#endif

    InitializeBakedGIData(input, inputData);

    half4 color = UniversalFragmentPBR(inputData, surfaceData);
    color.rgb = MixFog(color.rgb, inputData.fogCoord);
    color.a = OutputAlpha(color.a, IsSurfaceTypeTransparent());

    outColor = color;

#ifdef _WRITE_RENDERING_LAYERS
    outRenderingLayers = EncodeMeshRenderingLayer();
#endif
}

#endif
