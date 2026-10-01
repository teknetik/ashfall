// Ward city paving (1 Oct 2026): forward pass derived from WeatheredLit / URP LitForwardPass.hlsl (Unity Companion License, see Unity-LICENSE.md).
#ifndef UNIVERSAL_FORWARD_LIT_PASS_INCLUDED
#define UNIVERSAL_FORWARD_LIT_PASS_INCLUDED

#include "WardPavingInput.hlsl"
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

// ---------------------------------------------------------------------------------------------------------------
// Ward city paving (1 Oct 2026). The flag tile (4 x 4 m, 8 courses of 0.5 m running along world X) is mapped in world
// XZ. Every world course gets its own random shift along X and its own source course, so the 4 m tile never reads as
// a lattice; each flag instance (flag id x course x tile) gets its own tone/hue. Two world-space macro fields (~23 m and
// ~61 m) vary tint/value and lay dust patches that settle in the joints first; a 1 m grain normal adds close-range
// detail and fades out with distance. WeatheredLit's broad dust stains (_WearStrength/_WearScale/_WearTint) are kept.
struct PavingSample { half3 albedo; half3 normalWS; half smoothness; half occlusion; };

PavingSample SamplePaving(float3 positionWS, float3 vertexNormalWS)
{
    PavingSample o;
    // _CourseAxis 0: courses run east-west (u = +X, v = +Z); 1: courses run north-south (u = +Z, v = -X)
    float axis = step(.5, _CourseAxis);
    float2 xz = lerp(positionWS.xz, float2(positionWS.z, -positionWS.x), axis);
    float2 w = xz / _TileSize;                              // tile units
    float courseF = w.y * _CourseCount;
    float course = floor(courseF);
    float shift = WardHash(float3(course * .7131, 3.17 + _ShiftSeed, 9.71)) * _CourseShift;          // 0..1 tile (0..4 m)
    float srcCourse = lerp(fmod(fmod(course, _CourseCount) + _CourseCount, _CourseCount),
                           floor(WardHash(float3(course * 1.913, 7.31 + _ShiftSeed, 2.27)) * _CourseCount), _SourceShuffle);
    float2 uv = float2(w.x + shift, (srcCourse + frac(courseF)) / _CourseCount);
    float2 dx = ddx(w), dy = ddy(w);                        // continuous: no seams at course lines
    half4 base = SAMPLE_TEXTURE2D_GRAD(_BaseMap, sampler_BaseMap, uv, dx, dy);
    half4 mask = SAMPLE_TEXTURE2D_GRAD(_PavingMask, sampler_PavingMask, uv, dx, dy);   // r id, g cavity, b height, a smoothness
    half3 nTS = UnpackNormalScale(SAMPLE_TEXTURE2D_GRAD(_BumpMap, sampler_BumpMap, uv, dx, dy), _BumpScale);

    float dist = distance(positionWS, _WorldSpaceCameraPos);
    half flagW = smoothstep(.45h, .8h, mask.b);             // 1 on the flag face, 0 in the sanded joints
    half jointW = 1 - smoothstep(.12h, .5h, mask.b);

    // ---- per flag instance (id quantised to 1/32 in the bake; fades where mips mix several flags)
    float lod = log2(max(length(dx), length(dy)) * _BaseMap_TexelSize.z);
    half instW = flagW * (1 - smoothstep(4.5, 6.5, lod));
    float tileX = floor(uv.x);
    float idq = floor(mask.r * 32.0);
    float h1 = WardHash(float3(idq * 1.731 + .11, course * .913 + .37, tileX * 1.377 + .59));
    float h2 = WardHash(float3(idq * 2.113 + 3.1, course * 1.71 + .4, tileX * .711 + 9.2));
    half3 flagMul = (1 + (h1 - .5h) * 2 * _FlagValue) * lerp(half3(1, 1, 1), lerp(_FlagCool.rgb, _FlagWarm.rgb, h2), _FlagHue);
    half3 albedo = base.rgb * _BaseColor.rgb;
    albedo *= lerp(half3(1, 1, 1), flagMul, instW);
    albedo *= lerp(half3(1, 1, 1), _JointTint.rgb, jointW);
    // far away the 1-1.5 cm joints would read as a ruled grid: lift them towards the flag tone
    half farW = smoothstep(_JointFadeDist * .4, _JointFadeDist, dist);
    albedo *= lerp(1, _JointFarLift, saturate(1 - mask.b) * farW);
    half smoothness = mask.a * _SmoothnessScale * lerp(1, 1 + (h2 - .5h) * 2 * _FlagRough, instW);

    // ---- world-space macro variation and dust
    float2 p = positionWS.xz;
    float mA = WardNoise(float3(p / _MacroScaleA, .5));
    float mB = WardNoise(float3(p / _MacroScaleB + 17.1, 7.3));
    float mC = WardNoise(float3(p / 3.7, 2.2));
    half3 macro = lerp(_MacroCool.rgb, _MacroWarm.rgb, mA) * (1 + (mB - .5h) * 2 * _MacroValue);
    albedo *= lerp(half3(1, 1, 1), macro, _MacroStrength);
    half dustField = smoothstep(_DustThreshold, _DustThreshold + .3h, mB * .5h + mA * .25h + mC * .25h);
    half dust = saturate(dustField * _MacroDust * (0.55h + 0.9h * (1 - mask.b) + 0.25h * mC));
    albedo = lerp(albedo, _DustColor.rgb * (.92h + .16h * mC), dust * .75h);
    smoothness *= 1 - dust * .7h;
    // WeatheredLit broad stains (same parameters as before)
    float3 wardP = positionWS * _WearScale;
    float broad = WardNoise(wardP + float3(8.2, 1.1, 3.7));
    float broken = WardNoise(wardP * 3.17 + float3(1.2, 7.1, 2.3));
    float stain = smoothstep(.24, .78, broad * .74 + broken * .26) * _WearStrength;
    albedo *= lerp(half3(1, 1, 1), _WearTint.rgb, stain);
    smoothness *= 1 - stain * .55;

    // ---- close-range grain (1 m tile), fades out by _GrainFade metres; dust softens all relief
    half grainW = _GrainStrength * saturate(1 - dist / _GrainFade);
    half3 g = UnpackNormal(SAMPLE_TEXTURE2D(_GrainNormal, sampler_GrainNormal, positionWS.xz * _GrainScale));
    nTS = normalize(half3(nTS.xy * (1 - dust * .5h) + g.xy * grainW * (0.5h + 0.5h * flagW), nTS.z));

    // tangent frame of the world XZ mapping: T = +X, B = +Z, N = +Y (top face). Side faces keep the vertex normal.
    half top = smoothstep(.5h, .8h, vertexNormalWS.y);
    half3 T = lerp(half3(1, 0, 0), half3(0, 0, 1), axis), B = lerp(half3(0, 0, 1), half3(-1, 0, 0), axis);
    o.normalWS = normalize(lerp(vertexNormalWS, T * nTS.x + B * nTS.y + half3(0, 1, 0) * nTS.z, top));
    o.albedo = albedo;
    o.smoothness = saturate(smoothness);
    o.occlusion = lerp(1, mask.g, _MaskOcclusion);
    return o;
}

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

    PavingSample ps = SamplePaving(input.positionWS, normalize(input.normalWS));
    SurfaceData surfaceData = (SurfaceData)0;
    surfaceData.albedo = ps.albedo;
    surfaceData.alpha = 1;
    surfaceData.metallic = 0;
    surfaceData.specular = half3(0, 0, 0);
    surfaceData.smoothness = ps.smoothness;
    surfaceData.occlusion = ps.occlusion;
    surfaceData.normalTS = half3(0, 0, 1);

#ifdef LOD_FADE_CROSSFADE
    LODFadeCrossFade(input.positionCS);
#endif

    InputData inputData;
    InitializeInputData(input, half3(0, 0, 1), inputData);
    inputData.normalWS = NormalizeNormalPerPixel(ps.normalWS);   // world-mapped flag normal replaces the mesh frame
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
