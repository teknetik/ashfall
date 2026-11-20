// Outer Berms walkable ground, V3 (20 Nov 2026, Berms ground variety pass; art/berms_variety_20261120).
// V2 below plus a bowl-wide region mask over the expansion ground tiles and the variety pass's earthworks and craters
// (_VarSplatA/_VarSplatB over _VarRect, 0.25 m per texel): clay pans and hardpan (crust / packed gravel layers),
// wind-laid sand in the lee of ridges, gravel fans with a desert-varnish share, dry wash beds, wheel and track marks
// (packed, with ruts in the relief channel), scorched and glassed ground and crater bowls (relief). Every region uses
// the V2 texture layers, recoloured, so the basin toe and the old Berms ground still match; outside the rect, near the
// old ground and at the playable edge the masks are zero and V3 equals V2. _VarStrength 0 turns the regions off.
// ---- V2 header follows ----
// Outer Berms walkable ground, V2 (1 Oct 2026, Berms road ground pass; art/berms_road_20261001).
// Replaces "Athen Hill/Berms Ground" on `Outer Berms/Berms ground` (the old shader and material stay for rollback and
// for the training range's earth bank). The floor now uses the basin's Ward Desert Terrain V2 ground model, so the
// playable floor, its slopes and the basin toe read as one surface:
//   * natural ground (V2): cliff rock on slopes (Sandstone + Poly Haven "Sandstone Cracks", strata, triplanar),
//     scree (dry_ground_rocks) and sand (dense_sand, wind ripples) by slope, sky access and noise; masks use a
//     smoothed slope baked into the splat (the mesh is a 1 m resample of a faceted surface, so per-pixel normals would
//     turn the masks into straight-edged bands);
//   * painted features from two splats (world XZ, _SplatRect):
//       _Splat   R compacted road gravel (gravel_ground_01), G wind-deposited sand, B cracked crust, A 1 - compaction
//                (same channel meaning as the West Gate splat, which the footstep map reads);
//       _Splat2  R loose gravel (floor_pebbles_01: road crown, shoulder windrows and desert-pavement lag), G relief height
//                (0.5 = flat; ruts, windrows, potholes -> normals), B the varnished-lag share of R, A smoothed slope;
//   * every layer is index-bombed (Quilez) against tiling, height-blended, and fades to its mean colour with distance.
// Inside _EdgeBlend metres of the splat border the painted features and URP fog fade out and the haze takes the basin
// V3 shape, so the outer band equals the basin material. Lighting: URP PBR (UniversalFragmentPBR) with live shadows,
// SSAO, Forward+ lights and screen-space (DBuffer) decals, as the old shader. No shadow caster (as before).
Shader "Athen Hill/Berms Ground V3"
{
    Properties
    {
        [Header(Splats)]
        _Splat("Splat (R road, G sand, B crust, A 1-compaction)", 2D) = "black" {}
        _Splat2("Splat 2 (R loose gravel, G relief, B lag share, A smoothed slope x2)", 2D) = "black" {}
        _SplatRect("Splat rect (x0, z0, 1/width, 1/depth)", Vector) = (-104, -54, .0227, .0098)
        _EdgeBlend("Edge blend width (m)", Range(0, 20)) = 7
        _Compaction("Packed-ground darkening", Range(0, 1)) = .22
        _ReliefDepth("Relief height range of splat 2 G (m)", Range(0, .5)) = .2
        _ReliefStrength("Relief normal strength", Range(0, 3)) = 1

        [Header(Layer arrays)]
        _AlbedoHeight("Layer albedo + height (array)", 2DArray) = "" {}
        _NormalRoughAO("Layer normal XY, roughness, AO (array)", 2DArray) = "" {}
        _LayerSize("Tile size m (scree, sand, road, crust)", Vector) = (4, 1.8, 3, 4)
        _LooseSize("Loose gravel tile size (m)", Range(.5, 12)) = 3
        _GroundNormalStrength("Ground normal strength", Range(0, 2)) = 1.2
        _HeightBlend("Height blend depth", Range(.01, 1)) = .18
        _Saturation("Albedo saturation", Range(0, 1.5)) = 1

        [Header(Natural ground colours (V2 model))]
        _GravelColor("Scree colour", Color) = (.55, .44, .31, 1)
        _GravelMean("Scree texture mean (linear RGB)", Vector) = (.324, .19, .086, 0)
        _Sand("Sand colour", Color) = (.59, .46, .30, 1)
        _SandMean("Sand texture mean (linear RGB)", Vector) = (.299, .222, .127, 0)

        [Header(Painted layer colours)]
        _RoadColor("Road gravel colour", Color) = (.5, .42, .31, 1)
        _RoadMean("Road texture mean (linear RGB)", Vector) = (.307, .245, .157, 0)
        _RoadContrast("Road texture contrast", Range(0, 1.5)) = .9
        _CrustColor("Crust colour", Color) = (.5, .42, .32, 1)
        _CrustMean("Crust texture mean (linear RGB)", Vector) = (.247, .206, .151, 0)
        _LooseColor("Loose gravel colour (road)", Color) = (.52, .43, .32, 1)
        _LagColor("Gravel lag colour (open ground)", Color) = (.36, .27, .19, 1)
        _LooseMean("Loose gravel texture mean (linear RGB)", Vector) = (.321, .26, .166, 0)
        _LooseContrast("Loose gravel texture contrast", Range(0, 1.5)) = .75
        _DriftColor("Drifted sand colour (painted sand on and by the road)", Color) = (.62, .53, .40, 1)

        [Header(Natural layer masks)]
        _RockSlope("Rock from slope (1 - normal.y)", Range(0, .6)) = .06
        _SlopeBlend("Slope transition width", Range(.005, .2)) = .035
        _SandAmount("Sand in flats and hollows", Range(0, 1)) = .5
        _InnerSand("Natural sand inside the playable floor", Range(0, 1)) = .35
        _RockSlopeInner("Rock from slope inside the floor (edge band blends to _RockSlope)", Range(0, .6)) = .18

        [Header(Rock (V2))]
        _RockTex("Sandstone albedo (mid scale)", 2D) = "white" {}
        _RockTint("Rock tint", Color) = (1, 1, 1, 1)
        _DetailScale("Rock repeats per metre", Range(.02, 1)) = .073
        _Relief("Rock surface relief", Range(0, 2)) = .14
        _RockDetailAlbedo("Rock detail albedo (sandstone_cracks)", 2D) = "white" {}
        [Normal] _RockDetailNormal("Rock detail normal", 2D) = "bump" {}
        _RockDetailMean("Rock detail mean albedo (linear RGB)", Vector) = (.641, .359, .177, 0)
        _RockDetailSize("Rock detail tile size (m)", Range(.5, 12)) = 3.2
        _RockDetailStrength("Rock detail albedo strength", Range(0, 1)) = .6
        _RockSmoothness("Rock smoothness", Range(0, 1)) = .12
        _StrataThickness("Bed thickness (m)", Range(.3, 8)) = 1.7
        _StrataStrength("Strata contrast", Range(0, 2)) = 1
        _StrataDark("Dark bed multiplier (linear)", Vector) = (.73, .65, .56, 0)
        _StrataLight("Light bed multiplier (linear)", Vector) = (1.13, 1.03, .87, 0)

        [Header(Macro variation)]
        _Geology("Geological detail (linear)", 2D) = "gray" {}
        _MacroScale("Macro repeats per metre", Range(.001, .05)) = .009
        _MacroStrength("Macro variation strength", Range(0, 1)) = .35

        [Header(Sand ripples)]
        _WindDirection("Wind direction (world XZ)", Vector) = (-1, 0, .35, 0)
        _RippleWavelength("Ripple wavelength (m)", Range(.04, .5)) = .2
        _RippleStrength("Ripple strength", Range(0, 2)) = 1

        [Header(Region mask (variety pass))]
        _VarSplatA("Regions A (R clay pan, G hardpan, B wind sand, A gravel fan)", 2D) = "black" {}
        _VarSplatB("Regions B (R varnish, G relief 0.5 flat, B scorch, A wheel track)", 2D) = "black" {}
        _VarRect("Region rect (x0, z0, 1/width, 1/depth)", Vector) = (-572, -256, .001953125, .001953125)
        _VarStrength("Region strength (0 = V2)", Range(0, 1)) = 1
        _ClayColor("Clay pan colour", Color) = (.66, .58, .48, 1)
        _HardpanColor("Hardpan colour", Color) = (.50, .40, .30, 1)
        _WindSandColor("Wind sand colour", Color) = (.68, .55, .38, 1)
        _FanColor("Fresh fan gravel colour", Color) = (.56, .46, .34, 1)
        _VarnishColor("Varnished stone colour", Color) = (.25, .18, .13, 1)
        _TrackColor("Wheel track colour", Color) = (.53, .45, .35, 1)
        _ScorchColor("Scorch multiplier", Color) = (.30, .26, .23, 1)
        _GlassColor("Glassed ground colour", Color) = (.12, .11, .10, 1)
        _GlassSmoothness("Glass smoothness", Range(0, 1)) = .72
        _VarnishRock("Varnish on rock and scree", Range(0, 1)) = .55
        _TrackCompaction("Track compaction", Range(0, 1)) = .8
        _VarReliefDepth("Region relief height range (m)", Range(0, 2)) = .8
        _VarReliefStrength("Region relief normal strength", Range(0, 3)) = 1
        _WindSandRipples("Ripple boost in wind sand", Range(0, 3)) = 1.6

        [Header(Distance and lighting)]
        _DetailFadeStart("Detail fade start (m)", Range(5, 300)) = 40
        _DetailFadeEnd("Detail fade end (m)", Range(10, 500)) = 140
        _SkyOcclusion("Baked sky access strength", Range(0, 1)) = .5
        _FogBlend("URP fog blend inside the floor", Range(0, 1)) = 1
        _EdgeFogBlend("URP fog blend at the border (basin value)", Range(0, 1)) = 0

        [Header(Distance haze (basin V3 model))]
        _Haze("Distance haze", Color) = (.66, .54, .40, 1)
        _HazeDensity("Atmospheric density", Range(0, .02)) = .0068
        _HazeFarStart("Far haze starts (m beyond 38 m)", Range(0, 1000)) = 100
        _HazeFarScale("Density beyond the far start", Range(0, 1)) = .28
        _HazeHeightFalloff("Haze height falloff (m, 0 = off)", Range(0, 300)) = 32
        _HazeBaseHeight("Height falloff base (m)", Range(-5, 40)) = 6
        _HazeNoonTint("High-sun haze tint (linear multiplier)", Vector) = (.88, .93, 1.03, 0)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        TEXTURE2D(_Splat); SAMPLER(sampler_Splat);
        TEXTURE2D(_Splat2); SAMPLER(sampler_Splat2);
        TEXTURE2D_ARRAY(_AlbedoHeight); SAMPLER(sampler_AlbedoHeight);
        TEXTURE2D_ARRAY(_NormalRoughAO); SAMPLER(sampler_NormalRoughAO);
        TEXTURE2D(_Geology); SAMPLER(sampler_Geology);
        TEXTURE2D(_RockTex); SAMPLER(sampler_RockTex);
        TEXTURE2D(_RockDetailAlbedo); SAMPLER(sampler_RockDetailAlbedo);
        TEXTURE2D(_RockDetailNormal); SAMPLER(sampler_RockDetailNormal);
        TEXTURE2D(_VarSplatA); SAMPLER(sampler_VarSplatA);
        TEXTURE2D(_VarSplatB); SAMPLER(sampler_VarSplatB);
        CBUFFER_START(UnityPerMaterial)
        float4 _Splat2_TexelSize;
        float4 _SplatRect, _LayerSize;
        float _EdgeBlend, _Compaction, _ReliefDepth, _ReliefStrength, _LooseSize, _GroundNormalStrength, _HeightBlend, _Saturation;
        float4 _GravelColor, _GravelMean, _Sand, _SandMean;
        float4 _RoadColor, _RoadMean, _CrustColor, _CrustMean, _LooseColor, _LagColor, _LooseMean, _DriftColor;
        float _RoadContrast, _LooseContrast;
        float _RockSlope, _SlopeBlend, _SandAmount, _InnerSand, _RockSlopeInner;
        float4 _RockTint, _RockDetailMean, _StrataDark, _StrataLight;
        float _DetailScale, _Relief, _RockDetailSize, _RockDetailStrength, _RockSmoothness, _StrataThickness, _StrataStrength;
        float _MacroScale, _MacroStrength;
        float4 _WindDirection;
        float _RippleWavelength, _RippleStrength;
        float _DetailFadeStart, _DetailFadeEnd, _SkyOcclusion, _FogBlend, _EdgeFogBlend;
        float4 _Haze, _HazeNoonTint;
        float _HazeDensity, _HazeFarStart, _HazeFarScale, _HazeHeightFalloff, _HazeBaseHeight;
        float4 _VarSplatB_TexelSize, _VarRect;
        float4 _ClayColor, _HardpanColor, _WindSandColor, _FanColor, _VarnishColor, _TrackColor, _ScorchColor, _GlassColor;
        float _VarStrength, _GlassSmoothness, _VarnishRock, _TrackCompaction, _VarReliefDepth, _VarReliefStrength, _WindSandRipples;
        CBUFFER_END
        float4 _AthenTerrainTime;
        float4 _AthenTerrainHazeScale;
        float _AthenWeatherHaze; // weather (Scripts/Weather): extra haze density, 0 when unset = authored haze

        float Hash11(float p) { p = frac(p * 0.1031); p *= p + 33.33; p *= p + p; return frac(p); }
        float2 Hash12(float n)
        {
            float3 p3 = frac(float3(n, n, n) * float3(0.1031, 0.1030, 0.0973));
            p3 += dot(p3, p3.yzx + 33.33);
            return frac((p3.xx + p3.yz) * p3.zy);
        }
        float3 TangentToWorldUp(float3 n, float3 ts)
        {
            float3 t = normalize(float3(1, 0, 0) - n * n.x);
            float3 bt = cross(t, n);
            return normalize(t * ts.x + bt * ts.y + n * ts.z);
        }

        float2 SplatUV(float3 P) { return (P.xz - _SplatRect.xy) * _SplatRect.zw; }
        // 1 at the splat border, 0 deeper than _EdgeBlend metres inside
        float EdgeFactor(float2 uv)
        {
            float2 d = min(uv, 1 - uv) / _SplatRect.zw;
            return saturate(1 - min(d.x, d.y) / max(_EdgeBlend, .001));
        }

        // Relief normal from splat 2 G (world-space height in metres): finite differences one texel (or one pixel
        // footprint, whichever is larger) apart, sampled with the pixel's own gradients so distant relief is filtered.
        float3 ReliefNormal(float3 Ng, float2 uv, float strength)
        {
            float2 dx = ddx(uv), dy = ddy(uv);
            float2 stp = max(_Splat2_TexelSize.xy, max(abs(dx), abs(dy)));
            float h0 = SAMPLE_TEXTURE2D_GRAD(_Splat2, sampler_Splat2, uv, dx, dy).g;
            float hx = SAMPLE_TEXTURE2D_GRAD(_Splat2, sampler_Splat2, uv + float2(stp.x, 0), dx, dy).g;
            float hz = SAMPLE_TEXTURE2D_GRAD(_Splat2, sampler_Splat2, uv + float2(0, stp.y), dx, dy).g;
            float2 metres = stp / _SplatRect.zw;
            float2 grad = float2(hx - h0, hz - h0) * _ReliefDepth / metres * strength;
            return normalize(Ng - float3(grad.x, 0, grad.y));
        }

        float2 VarUV(float3 P) { return (P.xz - _VarRect.xy) * _VarRect.zw; }
        float VarInside(float2 uv) { return step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0) * _VarStrength; }
        // Region relief (splat B G, 0.5 = flat): wheel ruts, crater bowls, wash bars.
        float3 VarReliefNormal(float3 N, float2 uv, float strength)
        {
            UNITY_BRANCH
            if (strength <= 0.0) return N;
            float2 dx = ddx(uv), dy = ddy(uv);
            float2 stp = max(_VarSplatB_TexelSize.xy, max(abs(dx), abs(dy)));
            float h0 = SAMPLE_TEXTURE2D_GRAD(_VarSplatB, sampler_VarSplatB, uv, dx, dy).g;
            float hx = SAMPLE_TEXTURE2D_GRAD(_VarSplatB, sampler_VarSplatB, uv + float2(stp.x, 0), dx, dy).g;
            float hz = SAMPLE_TEXTURE2D_GRAD(_VarSplatB, sampler_VarSplatB, uv + float2(0, stp.y), dx, dy).g;
            float2 metres = stp / _VarRect.zw;
            float2 grad = float2(hx - h0, hz - h0) * _VarReliefDepth / metres * strength;
            return normalize(N - float3(grad.x, 0, grad.y));
        }

        struct GroundTap { float4 ah; float4 nra; };

        // Index bombing (as Ward Desert Terrain V2): an ~11 m noise picks one of eight offsets; neighbours cross-fade
        // along the texture's own height. Only taps with non-zero weight are fetched (explicit gradients).
        GroundTap SampleLayer(float2 uv, float2 dx, float2 dy, float layer, float k)
        {
            float i = floor(k), f = frac(k);
            float2 offA = Hash12(i + layer * 17.0) * 11.3;
            float2 offB = Hash12(i + 1.0 + layer * 17.0) * 11.3;
            GroundTap a = (GroundTap)0, b = (GroundTap)0;
            float blend = smoothstep(0.35, 0.65, f);
            UNITY_BRANCH
            if (blend < 0.999)
            {
                a.ah = SAMPLE_TEXTURE2D_ARRAY_GRAD(_AlbedoHeight, sampler_AlbedoHeight, uv + offA, layer, dx, dy);
                a.nra = SAMPLE_TEXTURE2D_ARRAY_GRAD(_NormalRoughAO, sampler_NormalRoughAO, uv + offA, layer, dx, dy);
            }
            UNITY_BRANCH
            if (blend > 0.001)
            {
                b.ah = SAMPLE_TEXTURE2D_ARRAY_GRAD(_AlbedoHeight, sampler_AlbedoHeight, uv + offB, layer, dx, dy);
                b.nra = SAMPLE_TEXTURE2D_ARRAY_GRAD(_NormalRoughAO, sampler_NormalRoughAO, uv + offB, layer, dx, dy);
            }
            blend = saturate(blend + (b.ah.a - a.ah.a) * 0.35 * step(0.001, blend) * step(blend, 0.999));
            GroundTap o;
            o.ah = lerp(a.ah, b.ah, blend);
            o.nra = lerp(a.nra, b.nra, blend);
            return o;
        }

        GroundTap LayerOrMean(float w, float detailFade, float size, float layer, float k, float3 P, float3 dPdx, float3 dPdy, float3 meanLin, float rough)
        {
            GroundTap t;
            t.ah = float4(meanLin, 0.5); t.nra = float4(0.5, 0.5, rough, 1.0);
            UNITY_BRANCH
            if (w > 0.001 && detailFade > 0.001)
            {
                float s = 1.0 / size;
                t = SampleLayer(P.xz * s, dPdx.xz * s, dPdy.xz * s, layer, k);
            }
            return t;
        }

        void SampleRockProjection(float2 uv, float2 dx, float2 dy, float midBlend, float detailOn, out float3 mid, out float3 detail, out float3 detailTS)
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

        struct GroundSurface { float3 albedo; float3 normalWS; float smoothness; float ao; float fogBlend; float edge; };

        GroundSurface ShadeGround(float3 P, float3 normalWS, float skyAccess)
        {
            float3 Ng = normalize(normalWS);
            float dist = distance(GetCameraPositionWS(), P);
            float detailFade = 1.0 - smoothstep(_DetailFadeStart, max(_DetailFadeEnd, _DetailFadeStart + 1.0), dist);
            float3 dPdx = ddx(P), dPdy = ddy(P);

            // ---- splats -------------------------------------------------------------------------------
            float2 uv = SplatUV(P);
            float4 s1 = SAMPLE_TEXTURE2D(_Splat, sampler_Splat, uv);
            float4 s2 = SAMPLE_TEXTURE2D(_Splat2, sampler_Splat2, uv);
            float edge = EdgeFactor(uv);
            float inner = 1.0 - edge;
            float packed = (1.0 - s1.a) * inner;
            // smoothed slope for the masks (baked x2 into splat 2 A); outside the splat use the geometric slope
            float inside = step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0);
            float slope = lerp(1.0 - saturate(Ng.y), s2.a * 0.5, inside);
            // ---- region mask (variety pass) -------------------------------------------------------------
            float2 vuv = VarUV(P);
            float vIn = VarInside(vuv);
            float4 vA = 0, vB = float4(0, 0.5, 0, 0);
            UNITY_BRANCH
            if (vIn > 0.0)
            {
                vA = SAMPLE_TEXTURE2D(_VarSplatA, sampler_VarSplatA, vuv) * vIn;
                vB = SAMPLE_TEXTURE2D(_VarSplatB, sampler_VarSplatB, vuv);
                vB.rba *= vIn;
            }
            float rClay = vA.r, rHard = vA.g, rWind = vA.b, rFan = vA.a, rTrack = vB.a, rVarnish = vB.r, rScorch = vB.b;
            float rSum = rClay + rHard + rWind + rFan + rTrack;
            float rNorm = rSum > 1.0 ? 1.0 / rSum : 1.0;
            rClay *= rNorm; rHard *= rNorm; rWind *= rNorm; rFan *= rNorm; rTrack *= rNorm;
            float rKeep = 1.0 - min(rSum, 1.0);
            packed = saturate(packed + rTrack * _TrackCompaction + rHard * 0.45);

            // ---- macro variation (V2: 111 m and ~410 m octaves, ~11 m mid noise) -----------------------
            float4 macro = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, P.xz * _MacroScale);
            float2 rotXZ = float2(P.x * 0.8 - P.z * 0.6, P.x * 0.6 + P.z * 0.8);
            float4 macro2 = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, rotXZ * (_MacroScale * 0.27) + 0.31);
            float4 mid = SAMPLE_TEXTURE2D(_Geology, sampler_Geology, P.xz * 0.093 + 0.17);

            // ---- natural masks (V2) ---------------------------------------------------------------------
            float rockNoise = (macro.r - 0.5) * 0.25 + (mid.r - 0.5) * 0.1 + (macro2.g - 0.5) * 0.1;
            float rockSlope = lerp(_RockSlopeInner, _RockSlope, edge);           // the floor's gentle mounds stay scree; the border matches the basin
            float wRockN = smoothstep(rockSlope - _SlopeBlend, rockSlope + _SlopeBlend, slope + rockNoise);
            float hollow = (1.0 - skyAccess) * 1.5 + (1.0 - smoothstep(0.0, 4.0, P.y)) * 0.25;
            float sandNoise = 0.5 + (macro.g - 0.505) * 2.0 + (mid.a - 0.49) * 1.0;
            float sandMask = (1.0 - smoothstep(0.015, 0.06, slope))
                           * smoothstep(0.35, 0.65, sandNoise + (_SandAmount - 0.5) * 0.6 + hollow * 0.4) * lerp(_InnerSand, 1.0, edge);
            float wSandN = (1.0 - wRockN) * saturate(sandMask);
            float wScreeN = saturate(1.0 - wRockN - wSandN);

            // ---- painted features (fade out over the border band) ---------------------------------------
            float road = s1.r * inner, sandP = s1.g * inner, crust = s1.b * inner, loose = s2.r * inner;
            float painted = road + sandP + crust;
            float norm = painted > 1.0 ? 1.0 / painted : 1.0;
            road *= norm; sandP *= norm; crust *= norm;
            float natural = saturate(1.0 - road - sandP - crust) * (1.0 - loose);
            // weights: rock, scree, sand, road, crust, loose
            float wRock = wRockN * natural;
            float wScree = wScreeN * natural;
            float wSand = wSandN * natural + sandP * (1.0 - loose);
            float wRoad = road * (1.0 - loose);
            float wCrust = crust * (1.0 - loose);
            float wLoose = loose;
            // regions replace part of the natural/painted mix (V2 is unchanged where the masks are zero)
            float wHardR = rHard + rTrack;
            wRock *= rKeep; wScree *= rKeep; wSand = wSand * rKeep + rWind;
            wRoad = wRoad * rKeep + wHardR; wCrust = wCrust * rKeep + rClay; wLoose = wLoose * rKeep + rFan;

            // ---- rock (V2, triplanar with whiteout normals) ----------------------------------------------
            float3 rockMid = 0, rockDetail = _RockDetailMean.rgb, rockN = Ng;
            float midBlend = smoothstep(0.32, 0.67, mid.g * 0.5 + macro.r * 0.5);
            float2 warp = (macro.rg - 0.5) * 2.0;
            float3 axisSign = Ng < 0 ? -1.0 : 1.0;
            float3 an = abs(Ng);
            float3 tw = pow(saturate(an - 0.3), 3.0);
            tw /= max(dot(tw, 1.0), 1e-5);
            tw *= step(0.02, tw);
            tw /= max(dot(tw, 1.0), 1e-5);
            UNITY_BRANCH
            if (wRock > 0.001)
            {
                float3 mX = 0, mY = 0, mZ = 0, dX = 0, dY = 0, dZ = 0;
                float3 tsX = float3(0, 0, 1), tsY = float3(0, 0, 1), tsZ = float3(0, 0, 1);
                UNITY_BRANCH
                if (tw.y > 0.0)
                    SampleRockProjection(float2(P.x * axisSign.y, P.z) + warp, float2(dPdx.x * axisSign.y, dPdx.z), float2(dPdy.x * axisSign.y, dPdy.z), midBlend, detailFade, mY, dY, tsY);
                UNITY_BRANCH
                if (tw.x > 0.0)
                    SampleRockProjection(float2(P.z * axisSign.x, P.y) + float2(warp.y, 0), float2(dPdx.z * axisSign.x, dPdx.y), float2(dPdy.z * axisSign.x, dPdy.y), midBlend, detailFade, mX, dX, tsX);
                UNITY_BRANCH
                if (tw.z > 0.0)
                    SampleRockProjection(float2(-P.x * axisSign.z, P.y) + float2(warp.x, 0), float2(-dPdx.x * axisSign.z, dPdx.y), float2(-dPdy.x * axisSign.z, dPdy.y), midBlend, detailFade, mZ, dZ, tsZ);
                rockMid = mX * tw.x + mY * tw.y + mZ * tw.z;
                rockDetail = dX * tw.x + dY * tw.y + dZ * tw.z;
                tsX.x *= axisSign.x; tsY.x *= axisSign.y; tsZ.x *= -axisSign.z;
                tsX = float3(tsX.xy + Ng.zy, tsX.z * an.x);
                tsY = float3(tsY.xy + Ng.xz, tsY.z * an.y);
                tsZ = float3(tsZ.xy + Ng.xy, tsZ.z * an.z);
                rockN = normalize(tsX.zyx * tw.x + tsY.xzy * tw.y + tsZ.xyz * tw.z);
            }
            // strata (V2 beds on faces; antialiased by their own footprint)
            float warpY = P.y + (macro.r - 0.5) * 6.0 + sin(P.x * 0.024 + P.z * 0.018) * 2.0;
            float strataCoord = warpY / _StrataThickness;
            float bandId = floor(strataCoord), bandF = frac(strataCoord);
            float bandAA = max(fwidth(strataCoord), 1e-4);
            float bandRnd = lerp(Hash11(bandId - 1.0 + 17.0), Hash11(bandId + 17.0), saturate(bandF / (bandAA * 1.5)));
            float strataAmt = _StrataStrength * smoothstep(0.1, 0.45, slope);
            float3 strataTint = lerp(float3(1, 1, 1), lerp(_StrataDark.rgb, _StrataLight.rgb, saturate(bandRnd * 0.5 + macro.r * 0.5)), strataAmt);
            float3 rockAlbedo = rockMid * _RockTint.rgb * strataTint * lerp(1.0, rockDetail / max(_RockDetailMean.rgb, 1e-3), _RockDetailStrength * detailFade);
            float rockDetailLuma = dot(rockDetail / max(_RockDetailMean.rgb, 1e-3), float3(0.2126, 0.7152, 0.0722));

            // ---- ground layers --------------------------------------------------------------------------
            float k = mid.r * 8.0;
            GroundTap scree = LayerOrMean(wScree, detailFade, _LayerSize.x, 0, k, P, dPdx, dPdy, _GravelMean.rgb, .85);
            GroundTap sand = LayerOrMean(wSand, detailFade, _LayerSize.y, 1, k + 3.7, P, dPdx, dPdy, _SandMean.rgb, .9);
            GroundTap roadT = LayerOrMean(wRoad, detailFade, _LayerSize.z, 2, k + 1.9, P, dPdx, dPdy, _RoadMean.rgb, .87);
            GroundTap crustT = LayerOrMean(wCrust, detailFade, _LayerSize.w, 3, k + 5.3, P, dPdx, dPdy, _CrustMean.rgb, .83);
            GroundTap looseT = LayerOrMean(wLoose, detailFade, _LooseSize, 4, k + 2.6, P, dPdx, dPdy, _LooseMean.rgb, .9);

            float3 screeAlb = _GravelColor.rgb * lerp(1.0, min(scree.ah.rgb / max(_GravelMean.rgb, 1e-3), 1.8), 0.75 * detailFade);
            float3 sandAlb = _Sand.rgb * (0.70 + macro.r * 0.28) * lerp(1.0, min(sand.ah.rgb / max(_SandMean.rgb, 1e-3), 1.8), detailFade);
            float3 roadAlb = _RoadColor.rgb * lerp(1.0, min(roadT.ah.rgb / max(_RoadMean.rgb, 1e-3), 1.8), _RoadContrast * detailFade);
            float3 crustAlb = _CrustColor.rgb * lerp(1.0, min(crustT.ah.rgb / max(_CrustMean.rgb, 1e-3), 1.8), detailFade);
            float lagness = saturate(s2.b / max(s2.r, 1e-3));            // varnished desert-pavement lag vs fresh road gravel
            float3 looseAlb = lerp(_LooseColor.rgb, _LagColor.rgb, lagness) * lerp(1.0, min(looseT.ah.rgb / max(_LooseMean.rgb, 1e-3), 1.8), _LooseContrast * detailFade);
            float3 driftAlb = _DriftColor.rgb * lerp(1.0, min(sand.ah.rgb / max(_SandMean.rgb, 1e-3), 1.8), detailFade);
            sandAlb = lerp(sandAlb, driftAlb, saturate(sandP * (1.0 - loose) / max(wSand, 1e-4)));   // drifted sand on and by the road reads paler
            // region colours: each region recolours the layer it borrows (texture detail kept, as the painted layers)
            float3 windAlb = _WindSandColor.rgb * lerp(1.0, min(sand.ah.rgb / max(_SandMean.rgb, 1e-3), 1.8), detailFade);
            sandAlb = lerp(sandAlb, windAlb, saturate(rWind / max(wSand, 1e-4)));
            float3 hardTex = lerp(1.0, min(roadT.ah.rgb / max(_RoadMean.rgb, 1e-3), 1.8), _RoadContrast * detailFade);
            float3 hardAlb = lerp(_HardpanColor.rgb, _TrackColor.rgb, saturate(rTrack / max(wHardR, 1e-4))) * hardTex;
            roadAlb = lerp(roadAlb, hardAlb, saturate(wHardR / max(wRoad, 1e-4)));
            float3 clayAlb = _ClayColor.rgb * lerp(1.0, min(crustT.ah.rgb / max(_CrustMean.rgb, 1e-3), 1.8), detailFade);
            crustAlb = lerp(crustAlb, clayAlb, saturate(rClay / max(wCrust, 1e-4)));
            float3 fanAlb = lerp(_FanColor.rgb, _VarnishColor.rgb, saturate(rVarnish)) * lerp(1.0, min(looseT.ah.rgb / max(_LooseMean.rgb, 1e-3), 1.8), _LooseContrast * detailFade);
            looseAlb = lerp(looseAlb, fanAlb, saturate(rFan / max(wLoose, 1e-4)));
            // desert varnish darkens the natural scree and rock where the mask says the surface is old and stable
            float varnishNat = saturate(rVarnish) * _VarnishRock;
            screeAlb *= lerp(float3(1, 1, 1), _VarnishColor.rgb / max(_GravelColor.rgb, 1e-3), varnishNat);
            rockAlbedo *= lerp(float3(1, 1, 1), lerp(float3(1, 1, 1), _VarnishColor.rgb * 2.2, 0.6), varnishNat);

            // ---- height blend: sand fills hollows, stony layers keep their relief ---------------------------
            float3 wA = float3(wRock, wScree, wSand), wB = float3(wRoad, wCrust, wLoose);
            float3 hA = float3(lerp(0.5, saturate(rockDetailLuma * 0.5), detailFade), scree.ah.a, 1.0 - sand.ah.a * 0.6) + wA * 1.5;
            float3 hB = float3(roadT.ah.a, crustT.ah.a, looseT.ah.a * 1.1) + wB * 1.5;
            float depth = lerp(1.5, _HeightBlend, detailFade);
            float hm = max(max(hA.x, max(hA.y, hA.z)), max(hB.x, max(hB.y, hB.z))) - depth;
            float3 bA = max(hA - hm, 0.0) * step(0.001, wA), bB = max(hB - hm, 0.0) * step(0.001, wB);
            float bSum = max(dot(bA, 1.0) + dot(bB, 1.0), 1e-4);
            bA /= bSum; bB /= bSum;

            // ---- sand ripples (V3, fix round 20 Nov): direction, wavelength and amplitude vary with low-frequency noise,
            // the crest warp adds forks and dislocations, fine ripples (6-20 cm) only in the near field, large ripples
            // (1.2-3 m) only in patches of wind-laid sand; both fade out over hardpan, gravel and tracks (packed, bA.z)
            float2 wind0 = normalize(_WindDirection.xz + float2(1e-5, 0));
            float ang = (macro.g - 0.5) * 1.3 + (mid.b - 0.5) * 0.6;
            float ca = cos(ang), sa = sin(ang);
            float2 wind = float2(wind0.x * ca - wind0.y * sa, wind0.x * sa + wind0.y * ca);
            float along = dot(P.xz, wind), across = dot(P.xz, float2(-wind.y, wind.x));
            float sandOnly = 1.0 - packed;
            float flatOnly = 1.0 - smoothstep(0.02, 0.1, slope);
            float lambda = max(_RippleWavelength, 0.02) * lerp(0.55, 1.05, macro2.g);
            float crestWarp = 0.35 * sin(across * 0.9 + sin(along * 0.37) * 1.5) + (mid.g - 0.5) * 2.4 + (mid.r - 0.5) * 1.8;
            float phase = (along + crestWarp * lambda * 3.0) / lambda * 6.2831853;
            float fineFade = saturate(1.0 - smoothstep(4.0, 35.0, dist)) * saturate(1.5 - fwidth(along) / lambda * 3.0) * flatOnly
                           * _RippleStrength * lerp(0.5, 1.0, mid.a) * sandOnly;
            float rippleSlope = 0.011 * (6.2831853 / lambda) * (cos(phase) + 0.5 * cos(2.0 * phase)) * fineFade;
            float windShare = saturate(rWind / max(wSand, 1e-4));
            float patchN = smoothstep(0.45, 0.7, macro.b * 0.6 + mid.b * 0.4);
            float lambda2 = lerp(1.2, 3.0, macro2.g);
            float phase2 = (along * (1.0 + (mid.r - 0.5) * 0.15) + crestWarp * lambda2 * 0.9) / lambda2 * 6.2831853;
            float bigFade = saturate(1.0 - smoothstep(_DetailFadeStart, _DetailFadeEnd * 0.8, dist)) * saturate(1.5 - fwidth(along) / lambda2 * 3.0)
                          * flatOnly * _RippleStrength * sandOnly * windShare * patchN * _WindSandRipples * lerp(0.4, 1.0, mid.a);
            rippleSlope += 0.035 * (6.2831853 / lambda2) * (cos(phase2) + 0.4 * cos(2.0 * phase2 + 0.7)) * bigFade;
            sandAlb *= 1.0 + 0.05 * sin(phase) * fineFade + 0.035 * sin(phase2) * bigFade;

            // ---- combine ------------------------------------------------------------------------------------
            float3 albedo = rockAlbedo * bA.x + screeAlb * bA.y + sandAlb * bA.z + roadAlb * bB.x + crustAlb * bB.y + looseAlb * bB.z;
            albedo *= lerp(1.0, lerp(0.82, 1.14, macro2.r), _MacroStrength);
            albedo *= lerp(0.88, 1.1, mid.a);
            float luma = dot(albedo, float3(0.2126, 0.7152, 0.0722));
            albedo = lerp(luma.xxx, albedo, _Saturation);
            albedo *= 1.0 - packed * _Compaction;
            float glass = smoothstep(0.62, 0.8, rScorch);
            albedo *= lerp(float3(1, 1, 1), _ScorchColor.rgb, saturate(rScorch * 1.4));
            albedo = lerp(albedo, _GlassColor.rgb * lerp(0.8, 1.25, mid.a), glass);

            // relief from splat 2 (ruts, windrows, potholes) under the layer detail
            float3 Nr = ReliefNormal(Ng, uv, _ReliefStrength * inner);
            Nr = VarReliefNormal(Nr, vuv, _VarReliefStrength * step(0.001, vIn));
            float gs = _GroundNormalStrength * detailFade;
            float2 nScree = (scree.nra.rg * 2.0 - 1.0) * gs, nSand = (sand.nra.rg * 2.0 - 1.0) * gs, nRoad = (roadT.nra.rg * 2.0 - 1.0) * gs;
            float2 nCrust = (crustT.nra.rg * 2.0 - 1.0) * gs, nLoose = (looseT.nra.rg * 2.0 - 1.0) * gs;
            float2 nxy = nScree * bA.y + nSand * bA.z + nRoad * bB.x + nCrust * bB.y + nLoose * bB.z;
            nxy *= 1.0 - packed * 0.45;                                    // packed ground: flatter
            nxy *= 1.0 - glass * 0.8;                                      // glassed ground: fused, smooth
            float groundShare = 1.0 - bA.x;
            float3 groundN = TangentToWorldUp(Nr, float3(nxy / max(groundShare, 1e-3), 1.0));
            groundN = normalize(groundN - float3(wind.x, 0.0, wind.y) * rippleSlope * bA.z / max(groundShare, 1e-3));
            float3 N = normalize(rockN * bA.x + groundN * groundShare);
            // rock mid-scale relief (V2 _Relief bump), screen-space height derivatives, fades out by 210 m
            float hRock = dot(rockMid, float3(0.21, 0.72, 0.07)) * _Relief * bA.x * saturate(1.0 - dist / 210.0);
            float3 r1 = cross(dPdy, N), r2 = cross(N, dPdx);
            float det = dot(dPdx, r1);
            float3 grad = (ddx(hRock) * r1 + ddy(hRock) * r2) * sign(det) / max(abs(det), 1e-5);
            N = normalize(N - clamp(grad, -0.4, 0.4));

            float rough = scree.nra.b * bA.y + sand.nra.b * bA.z + roadT.nra.b * bB.x + crustT.nra.b * bB.y + looseT.nra.b * bB.z;
            float smoothV = _RockSmoothness * bA.x + saturate(1.0 - rough * (1.0 - packed * 0.15)) * 0.85 * groundShare;
            float ao = lerp(1.0, lerp(0.72, 1.0, saturate(rockDetailLuma)), detailFade) * bA.x
                     + scree.nra.a * bA.y + sand.nra.a * bA.z + roadT.nra.a * bB.x + crustT.nra.a * bB.y + looseT.nra.a * bB.z;
            ao *= lerp(0.8, 1.0, macro.r);
            smoothV = lerp(smoothV, _GlassSmoothness * lerp(0.7, 1.0, mid.g), glass);

            GroundSurface o;
            o.albedo = albedo; o.normalWS = N; o.smoothness = smoothV; o.ao = ao; o.edge = edge;
            o.fogBlend = lerp(_FogBlend, _EdgeFogBlend, edge);
            return o;
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
                float sky = saturate(i.baked.g);
                GroundSurface g = ShadeGround(i.positionWS, i.normalWS, sky);
                InputData d = (InputData)0;
                d.positionWS = i.positionWS; d.normalWS = g.normalWS; d.viewDirectionWS = GetWorldSpaceNormalizeViewDir(i.positionWS);
                d.shadowCoord = TransformWorldToShadowCoord(i.positionWS); d.fogCoord = i.fog;
                d.bakedGI = SampleSH(g.normalWS); d.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS); d.shadowMask = half4(1, 1, 1, 1);
                SurfaceData s = (SurfaceData)0;
                s.albedo = g.albedo; s.metallic = 0; s.specular = 0; s.smoothness = g.smoothness; s.normalTS = float3(0, 0, 1);
                s.occlusion = g.ao * lerp(1, saturate(i.baked.g * 1.15), _SkyOcclusion); s.alpha = 1;
                #if defined(_DBUFFER)
                ApplyDecalToSurfaceData(i.positionCS, s, d);
                #endif
                half4 color = UniversalFragmentPBR(d, s);
                color.rgb = lerp(color.rgb, MixFog(color.rgb, d.fogCoord), g.fogBlend);
                // basin V3 haze (Ward Desert Terrain V2 model). The low-altitude term is gated by distance inside the
                // floor (the old Berms behaviour, keeps the near ground crisp) and ungated at the border (basin behaviour).
                float3 P = i.positionWS;
                float dist = distance(_WorldSpaceCameraPos, P);
                float hazeDist = max(0.0, dist - 38.0);
                hazeDist = min(hazeDist, _HazeFarStart) + max(hazeDist - _HazeFarStart, 0.0) * _HazeFarScale;
                float opticalDepth = hazeDist * _HazeDensity;
                UNITY_BRANCH
                if (_HazeHeightFalloff > 0.0)
                {
                    float h0 = max(_WorldSpaceCameraPos.y - _HazeBaseHeight, 0.0) / _HazeHeightFalloff;
                    float h1 = max(P.y - _HazeBaseHeight, 0.0) / _HazeHeightFalloff;
                    float dh = h1 - h0;
                    opticalDepth *= abs(dh) > 1e-3 ? (exp(-h0) - exp(-h1)) / dh : exp(-h0);
                }
                float haze = 1.0 - exp(-opticalDepth * (1.0 + max(_AthenWeatherHaze, 0.0)));
                haze = saturate(haze + exp(-max(0.0, P.y) * 0.06) * 0.11 * lerp(saturate((dist - 20.0) / 40.0), 1.0, g.edge));
                float clockActive = saturate(_AthenTerrainTime.x);
                float3 hazeColor = _Haze.rgb * lerp(float3(1, 1, 1), _AthenTerrainHazeScale.rgb, clockActive);
                float highSun = smoothstep(0.3, 0.6, _MainLightPosition.y) * smoothstep(0.8, 1.5, dot(_MainLightColor.rgb, float3(0.2126, 0.7152, 0.0722)));
                hazeColor *= lerp(float3(1, 1, 1), _HazeNoonTint.rgb, highSun);
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
            // geometric normal plus the splat relief (ruts, windrows) only: the layered shading would double the cost
            half4 F(VO i):SV_Target
            {
                float2 uv = SplatUV(i.w);
                float3 n = ReliefNormal(normalize(i.n), uv, _ReliefStrength * (1.0 - EdgeFactor(uv)));
                float2 vuv = VarUV(i.w);
                n = VarReliefNormal(n, vuv, _VarReliefStrength * step(0.001, VarInside(vuv)));
                #if defined(_GBUFFER_NORMALS_OCT)
                float2 oct = PackNormalOctQuadEncode(n); return half4(PackFloat2To888(saturate(oct * .5 + .5)), 0);
                #else
                return half4(NormalizeNormalPerPixel(n), 0);
                #endif
            }
            ENDHLSL
        }
    }
    FallBack Off
}
