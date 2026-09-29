// Ward Window Interior: opaque URP 17.6 lit glass with world-space interior mapping.
//
// Replaces the flat near-black WardGlass. Everything is derived from world position and the geometric normal,
// so it survives StaticRenderChunks merging (chunk space, unreliable per-pane UVs). See
// WardWindowInterior.README.md for integration (switch WardGlass.mat's shader, set _EmissionColor, and add the
// material to CityLightCircuit.emissiveMaterials).
//
//   * Rooms: a world grid behind each facade (_RoomSize W x H x D metres, _RoomOffset = grid origin, with .y a
//     floor level). The view ray is intersected with the room box; walls, floor and ceiling are procedural, with
//     two parallax furniture planes, a lamp, and blinds/curtains just behind the glass. A per-room hash picks the
//     use (shop, workshop, dwelling, store), palette, furniture, blinds, whether it is lit and its light colour.
//   * Daylight inside = ambient SH seen by the facade x _InteriorDaylight (falling off with depth) + sun spill
//     through the window (main light, shadowed at the glass) + _InteriorFill.
//   * Night: room lamps use _EmissionColor (HDR). CityLightCircuit multiplies _EmissionColor by
//     lerp(daytimeStrength, 1, LampStrength) on its runtime clone, so every lamp, LED and lit blind follows the
//     city clock. Nothing else needs a script.
//   * Glass: Schlick Fresnel, GlossyEnvironmentReflection (probes/skybox, Forward+ probe atlas), shadowed main
//     light and additional-light specular, a world-space dust layer with grime driven by SSAO at sills, mullions
//     and reveals, slight tint, fog.
// Passes: UniversalForward, DepthOnly, DepthNormals (SSAO/decals). No ShadowCaster (windows do not cast) and no
// Meta pass. SRP Batcher compatible (single UnityPerMaterial CBUFFER shared by all passes).
Shader "Athen Hill/Ward Window Interior"
{
    Properties
    {
        [Header(Rooms behind the glass)]
        _RoomSize("Room size W H D (m)", Vector) = (9, 3.4, 4.0, 0)
        _RoomOffset("Room grid origin (world m; Y = a floor level)", Vector) = (4.5, 0.5, 4.5, 0)
        _RoomSeed("Variation seed", Float) = 0
        _WallTint("Wall tint", Color) = (1, 1, 1, 1)
        _FurnitureAmount("Furniture density", Range(0, 1)) = 0.85
        _BlindAmount("Blinds and curtains", Range(0, 1)) = 0.6

        [Header(Daylight inside)]
        _InteriorDaylight("Sky light entering rooms", Range(0, 2)) = 0.5
        _InteriorFill("Constant interior fill (linear)", Color) = (0.012, 0.011, 0.01, 1)
        _SunSpill("Sun spill through windows", Range(0, 1)) = 0.35

        [Header(Room lights at night)]
        [HDR] _EmissionColor("Room light intensity (CityLightCircuit scales this)", Color) = (3, 3, 3, 1)
        _LitFraction("Lit room fraction", Range(0, 1)) = 0.55
        _CoolFraction("Cool tech-light fraction", Range(0, 1)) = 0.3
        _WarmLight("Warm tungsten tint", Color) = (1, 0.62, 0.32, 1)
        _CoolLight("Cool tech tint", Color) = (0.55, 0.86, 1, 1)
        _LampRange("Lamp falloff radius (m)", Range(0.5, 5)) = 2.6

        [Header(Glass)]
        _GlassTint("Glass tint", Color) = (0.86, 0.94, 0.93, 1)
        _Smoothness("Glass smoothness", Range(0, 1)) = 0.93
        _ReflectionStrength("Reflection strength", Range(0, 2)) = 1
        _DirtColor("Dust colour", Color) = (0.42, 0.36, 0.28, 1)
        _DirtAmount("Dust amount", Range(0, 1)) = 0.45
        _DirtScale("Dust scale (1/m)", Range(0.2, 8)) = 1.6
        _EdgeGrime("Edge and corner grime (SSAO driven)", Range(0, 2)) = 1

        [Header(Optional room atlas)]
        [ToggleUI] _UseRoomAtlas("Use room atlas", Float) = 0
        [NoScaleOffset] _RoomAtlas("Room atlas (one-point perspective tiles)", 2D) = "black" {}
        _AtlasGrid("Atlas tiles per side (2 or 4)", Float) = 2
        _AtlasBackWallScale("Back wall size within a tile", Range(0.2, 0.9)) = 0.5
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "UniversalMaterialType"="Lit" "Queue"="Geometry" "IgnoreProjector"="True" }
        LOD 300

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        CBUFFER_START(UnityPerMaterial)
            float4 _RoomSize;
            float4 _RoomOffset;
            float _RoomSeed;
            half4 _WallTint;
            half _FurnitureAmount;
            half _BlindAmount;
            half _InteriorDaylight;
            half4 _InteriorFill;
            half _SunSpill;
            half4 _EmissionColor;
            half _LitFraction;
            half _CoolFraction;
            half4 _WarmLight;
            half4 _CoolLight;
            half _LampRange;
            half4 _GlassTint;
            half _Smoothness;
            half _ReflectionStrength;
            half4 _DirtColor;
            half _DirtAmount;
            half _DirtScale;
            half _EdgeGrime;
            half _UseRoomAtlas;
            half _AtlasGrid;
            half _AtlasBackWallScale;
        CBUFFER_END

        TEXTURE2D(_RoomAtlas);
        SAMPLER(sampler_RoomAtlas);
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            Cull Back
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex WindowVert
            #pragma fragment WindowFrag

            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BOX_PROJECTION
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_ATLAS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
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
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                half fogFactor : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings WindowVert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = vertexInput.positionCS;
                output.positionWS = vertexInput.positionWS;
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.fogFactor = ComputeFogFactor(vertexInput.positionCS.z);
                return output;
            }

            // ---- Small helpers ------------------------------------------------------------------
            // Sine-free hashes (Hoskins): stable across GPUs for the small coordinates used here.
            float Hash12(float2 p)
            {
                float3 p3 = frac(p.xyx * 0.1031);
                p3 += dot(p3, p3.yzx + 33.33);
                return frac((p3.x + p3.y) * p3.z);
            }
            float4 Hash43(float3 p)
            {
                float4 p4 = frac(p.xyzx * float4(0.1031, 0.1030, 0.0973, 0.1099));
                p4 += dot(p4, p4.wzxy + 33.33);
                return frac((p4.xxyz + p4.yzzw) * p4.zywx);
            }
            float ValueNoise(float2 p)
            {
                float2 i = floor(p), f = p - i;
                float2 u = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(Hash12(i), Hash12(i + float2(1, 0)), u.x), lerp(Hash12(i + float2(0, 1)), Hash12(i + 1.0), u.x), u.y);
            }
            // Antialiased axis-aligned rectangle; aa is the pixel footprint of p (from fwidth, taken outside branches).
            float Rect(float2 p, float2 lo, float2 hi, float2 aa)
            {
                float2 d = min(p - lo, hi - p) / aa;
                return saturate(min(d.x, d.y) + 0.5);
            }
            // Thin feature with coverage kept when narrower than a pixel (cords, grout, slat gaps).
            float Line1(float x, float centre, float halfWidth, float aa)
            {
                float w = max(halfWidth, aa * 0.5);
                return saturate((w - abs(x - centre)) / aa + 0.5) * (halfWidth / w);
            }

            static const float3 kWalls[6] = {
                float3(0.30, 0.25, 0.18),   // limewashed sand
                float3(0.28, 0.18, 0.10),   // ochre plaster
                float3(0.17, 0.20, 0.17),   // pale grey-green paint
                float3(0.40, 0.37, 0.31),   // whitewash
                float3(0.25, 0.12, 0.08),   // faded terracotta
                float3(0.16, 0.16, 0.15)    // bare concrete
            };
            static const float3 kCloth[5] = {
                float3(0.42, 0.37, 0.28),   // linen
                float3(0.34, 0.10, 0.06),   // faded red
                float3(0.42, 0.26, 0.09),   // ochre
                float3(0.12, 0.22, 0.22),   // teal-grey
                float3(0.30, 0.28, 0.26)    // undyed canvas
            };
            static const float3 kGoods[5] = {
                float3(0.30, 0.22, 0.12), float3(0.12, 0.16, 0.18), float3(0.36, 0.30, 0.20),
                float3(0.22, 0.09, 0.05), float3(0.10, 0.12, 0.08)
            };

            struct Facade
            {
                float3 N;       // outward, horizontal
                float3 T;       // along the facade, viewer's right
                float key;      // per-facade hash input
                float valid;    // 0 on top/bottom faces of the pane
            };

            Facade BuildFacade(float3 normalWS, float3 positionWS)
            {
                float2 h = normalWS.xz;
                float len = length(h);
                float2 n = len > 1e-4 ? h / len : float2(0, 1);
                // Axis-aligned buildings (the Ward shops) snap exactly to the world grid; any other horizontal
                // normal keeps its own frame, so rotated buildings still get coherent rooms.
                float2 a = abs(n);
                if (max(a.x, a.y) > 0.996) n = a.x > a.y ? float2(sign(n.x), 0) : float2(0, sign(n.y));
                Facade f;
                f.N = float3(n.x, 0, n.y);
                f.T = float3(-n.y, 0, n.x);
                f.key = floor(dot(positionWS, f.N) * 0.5 + 0.5) + dot(n, float2(17.0, 31.0));
                f.valid = smoothstep(0.35, 0.7, len);
                return f;
            }

            // Light reaching a point inside the room: daylight through the facade, sun spill, lamp, bounce.
            float3 RoomLight(float3 p, float3 n, float3 roomSize, float3 skyIn, float3 sunIn,
                             float3 lampPos, float3 lampCol, float tube)
            {
                float facing = 0.7 + 0.3 * saturate(-n.z) + 0.15 * saturate(n.y) - 0.15 * saturate(-n.y);
                float3 light = skyIn * (0.25 + 0.75 * exp(-p.z * 0.35)) * facing;
                light += sunIn * exp(-p.z * 1.3) * (0.25 + 0.75 * saturate(n.y)) * saturate(1.2 - p.y / roomSize.y);
                float3 dv = lampPos - p;
                float d2 = dot(dv, dv) + 0.01;
                float3 l = dv * rsqrt(d2);
                float cone = lerp(lerp(0.3, 0.55, tube), 1.0, smoothstep(0.1, 0.85, l.y));   // shaded pendant/tube
                float r2 = _LampRange * _LampRange;
                light += lampCol * (r2 / (d2 + r2) * cone * (saturate(dot(n, l)) * 0.8 + 0.2));
                light += lampCol * 0.06;                                        // room bounce
                return light + _InteriorFill.rgb;
            }

            float3 InteriorColor(float3 positionWS, Facade f, float3 skyIn, float3 sunIn, out float3 roomGlow)
            {
                float3 S = max(_RoomSize.xyz, float3(1.5, 2.2, 1.5));
                float3 rel = positionWS - _RoomOffset.xyz;
                float2 fc = float2(dot(rel, f.T), rel.y);                     // facade coordinates (m)
                float2 cell = floor(fc / S.xy);
                float3 o = float3(fc - cell * S.xy, 0.0);                       // entry point in room space
                float3 V = normalize(positionWS - GetCameraPositionWS());
                float3 rd = normalize(float3(dot(V, f.T), V.y, max(dot(V, -f.N), 0.02)));
                rd.x = abs(rd.x) < 1e-4 ? 1e-4 : rd.x;
                rd.y = abs(rd.y) < 1e-4 ? 1e-4 : rd.y;

                float3 seed = float3(cell, f.key) + _RoomSeed * 13.17;
                float4 h0 = Hash43(seed);
                float4 h1 = Hash43(seed + 71.7);
                float4 h2 = Hash43(seed + 143.3);
                float4 h3 = Hash43(seed + 211.9);

                // Room use: ground-floor rooms are shops/workshops, upper floors dwellings/workshops/stores.
                float upper = step(0.5, cell.y);
                float typeRnd = h0.x;
                float type = upper < 0.5 ? (typeRnd < 0.45 ? 0.0 : (typeRnd < 0.8 ? 1.0 : 3.0))
                                         : (typeRnd < 0.45 ? 2.0 : (typeRnd < 0.75 ? 1.0 : 3.0));
                float lit = step(h0.y, _LitFraction);
                float cool = step(h0.z, _CoolFraction * (type == 1.0 ? 1.8 : 0.6));
                float3 lampCol = _EmissionColor.rgb * lerp(_WarmLight.rgb, _CoolLight.rgb, cool) * (lit * lerp(0.6, 1.25, h0.w));
                float tube = cool;                                               // tech rooms: tube fittings

                float zA = clamp(S.z * (0.28 + 0.12 * h1.y), 0.8, S.z - 1.2);    // front furniture + lamp plane
                float zB = clamp(S.z * (0.62 + 0.15 * h1.z), zA + 0.6, S.z - 0.3); // back furniture plane
                float lx = S.x * (0.3 + 0.4 * h1.x);
                float ly = tube > 0.5 ? S.y - 0.25 : S.y - 0.75 - 0.35 * h1.w;
                float3 lampPos = float3(lx, ly - 0.05, zA);

                // ---- Room box ------------------------------------------------------------------
                float3 exitPlane = float3(rd.x > 0.0 ? S.x : 0.0, rd.y > 0.0 ? S.y : 0.0, S.z);
                float3 tt = (exitPlane - o) / rd;
                float t = min(tt.x, min(tt.y, tt.z));
                float3 p = o + rd * t;
                float face = tt.z <= min(tt.x, tt.y) ? 0.0 : (tt.x <= tt.y ? 1.0 : (rd.y < 0.0 ? 2.0 : 3.0));
                float3 nr = face == 0.0 ? float3(0, 0, -1) : (face == 1.0 ? float3(-sign(rd.x), 0, 0)
                          : (face == 2.0 ? float3(0, 1, 0) : float3(0, -1, 0)));
                float2 s = face == 0.0 ? p.xy : (face == 1.0 ? p.zy : p.xz);
                float2 sAA = max(fwidth(s), 1e-4);

                // Parallax planes (front furniture, back furniture, blinds) and their pixel footprints.
                float tA = zA / rd.z, tB = zB / rd.z, tBl = 0.04 / rd.z;
                float2 pA = o.xy + rd.xy * tA, pB = o.xy + rd.xy * tB, pBl = o.xy + rd.xy * tBl;
                float2 aaA = max(fwidth(pA), 1e-4), aaB = max(fwidth(pB), 1e-4), aaBl = max(fwidth(pBl), 1e-4);
                float inA = step(tA, t), inB = step(tB, t);

                // Optional atlas: tile coordinates are continuous inside a room, so gradients are safe.
                float nTiles = max(1.0, round(_AtlasGrid));
                float tile = floor(frac(h2.x * 7.31) * nTiles * nTiles);
                float2 tileXY = float2(fmod(tile, nTiles), floor(tile / nTiles));
                float bw = clamp(_AtlasBackWallScale, 0.05, 0.95);
                float fz = S.z * bw / (1.0 - bw);
                float2 tuv = 0.5 + 0.5 * ((p.xy / S.xy) * 2.0 - 1.0) / (1.0 + p.z / fz);
                float2 auv = (tileXY + saturate(tuv)) / nTiles;
                float2 auvDx = ddx(auv), auvDy = ddy(auv);

                // ---- Surfaces ----------------------------------------------------------------
                float3 wall = kWalls[(int)min(h3.x * 6.0, 5.0)] * _WallTint.rgb;
                float mottle = ValueNoise(s * 3.1 + h2.yz * 37.0);
                float3 albedo = wall * (0.85 + 0.3 * mottle);
                float3 emit = 0;
                if (face <= 1.0)
                {
                    float y = s.y;
                    albedo *= lerp(0.72, 1.0, smoothstep(0.0, 0.6, y));           // scuffed lower wall
                    float dado = step(0.5, h2.w) * Rect(float2(0.5, y), float2(0, -1), float2(1, 1.05), float2(1, sAA.y));
                    albedo = lerp(albedo, wall * 0.55 * float3(0.9, 0.95, 1.0), dado);
                    albedo *= 1.0 - 0.6 * Rect(float2(0.5, y), float2(0, -1), float2(1, 0.1), float2(1, sAA.y)); // skirting
                    albedo *= lerp(0.8, 1.0, smoothstep(S.y, S.y - 0.4, y));      // shadow under the ceiling
                    if (face == 0.0)
                    {
                        float bx = S.x * (0.12 + 0.5 * h2.x);
                        if (type == 0.0)       // doorway to a back store
                            albedo = lerp(albedo, float3(0.012, 0.011, 0.01), Rect(s, float2(bx, 0), float2(bx + 0.9, 2.1), sAA));
                        else if (type == 1.0)  // pegboard with hanging tools
                        {
                            float board = Rect(s, float2(bx, 0.95), float2(bx + 1.8, 1.95), sAA);
                            float col = floor((s.x - bx) / 0.22);
                            float hr = Hash12(float2(col, h0.w * 91.0));
                            float tool = Rect(s, float2(bx + col * 0.22 + 0.08, 1.85 - 0.2 - 0.35 * hr), float2(bx + col * 0.22 + 0.08 + 0.03 + 0.05 * hr, 1.85), sAA) * step(0.35, hr);
                            albedo = lerp(albedo, float3(0.2, 0.15, 0.09), board);
                            albedo = lerp(albedo, float3(0.05, 0.05, 0.055), tool * board);
                        }
                        else if (type == 2.0)  // hanging textile
                        {
                            float3 cloth = kCloth[(int)min(h2.z * 5.0, 4.0)];
                            float stripes = 0.8 + 0.2 * step(0.5, frac(s.y * 6.0));
                            albedo = lerp(albedo, cloth * stripes, Rect(s, float2(bx, 1.0), float2(bx + 1.2, 1.9), sAA));
                        }
                    }
                }
                else if (face == 2.0)
                {
                    float ft = frac(h2.y * 3.7);
                    float3 flr = ft < 0.4 ? float3(0.12, 0.11, 0.10) : (ft < 0.7 ? float3(0.20, 0.16, 0.12) : float3(0.14, 0.09, 0.05));
                    float grout = ft < 0.4 ? 0.0 : (ft < 0.7 ? max(Line1(frac(s.x / 0.4), 0.0, 0.01, sAA.x / 0.4), Line1(frac(s.y / 0.4), 0.0, 0.01, sAA.y / 0.4))
                                                             : Line1(frac(s.x / 0.18), 0.0, 0.012, sAA.x / 0.18));
                    albedo = flr * (0.8 + 0.4 * mottle) * (1.0 - 0.45 * grout);
                    if (type == 2.0)       // rug under the table
                    {
                        float rug = Rect(s, float2(lx - 1.0, zA - 0.9), float2(lx + 1.0, zA + 0.7), sAA);
                        float border = rug * (1.0 - Rect(s, float2(lx - 0.9, zA - 0.8), float2(lx + 0.9, zA + 0.6), sAA));
                        albedo = lerp(albedo, kCloth[(int)min(h1.w * 5.0, 4.0)] * (1.0 - 0.4 * border), rug);
                    }
                }
                else
                {
                    albedo = wall * 1.1 * (0.9 + 0.2 * mottle);
                    float beam = step(0.4, h2.w) * Line1(frac(s.y / 0.9), 0.5, 0.06, sAA.y / 0.9);
                    float conduit = Line1(s.x, lx, 0.018, sAA.x);
                    albedo = lerp(albedo, float3(0.07, 0.05, 0.035), beam);
                    albedo = lerp(albedo, float3(0.05, 0.05, 0.05), conduit);
                }
                float3 color = albedo * RoomLight(p, nr, S, skyIn, sunIn, lampPos, lampCol, tube);

                UNITY_BRANCH
                if (_UseRoomAtlas > 0.5)
                {
                    float3 atlas = SAMPLE_TEXTURE2D_GRAD(_RoomAtlas, sampler_RoomAtlas, auv, auvDx, auvDy).rgb;
                    color = atlas * RoomLight(p, nr, S, skyIn, sunIn, lampPos, lampCol, tube);
                    inA *= 0.0; inB *= 0.0;                                        // the atlas already has furniture
                }

                // ---- Back plane: shelving, fabricator cabinet, wardrobe, racks -------------------------
                float present = step(h2.x, _FurnitureAmount);
                float bx0 = S.x * (0.08 + 0.45 * h1.w);
                float maskB = 0, ledB = 0;
                float3 albB = float3(0.10, 0.075, 0.05);
                if (type == 0.0 || type == 3.0)
                {
                    float bay = type == 0.0 ? 1.0 : 1.3;
                    float u = pB.x - bx0;
                    float frame = max(max(Line1(u, 0.0, 0.025, aaB.x), Line1(u, bay, 0.025, aaB.x)), Line1(u, 2.0 * bay, 0.025, aaB.x));
                    frame *= Rect(pB, float2(bx0 - 0.03, 0.0), float2(bx0 + 2.0 * bay + 0.03, 2.1), aaB);
                    // Boards 3 cm thick every 0.45 m (tops at 0.115 + 0.45k); goods stand on each board.
                    float shelves = Line1(frac((pB.y - 0.099) / 0.45), 0.0, 0.035, aaB.y / 0.45)
                                  * Rect(pB, float2(bx0, 0.05), float2(bx0 + 2.0 * bay, 2.05), aaB);
                    float cw = type == 0.0 ? 0.17 : 0.45;
                    float2 ic = float2(floor(u / cw), floor((pB.y - 0.115) / 0.45));
                    float hr = Hash12(ic + h0.zw * 53.0);
                    float boardTop = ic.y * 0.45 + 0.115;
                    float itemTop = boardTop + (type == 0.0 ? 0.08 + 0.22 * hr : 0.25 + 0.14 * hr);
                    float item = step(0.3, hr) * Rect(float2(frac(u / cw) * cw, pB.y), float2(0.02, boardTop), float2(cw - 0.02, itemTop), aaB)
                               * Rect(pB, float2(bx0, 0.0), float2(bx0 + 2.0 * bay, 2.35), aaB);
                    maskB = saturate(frame + shelves + item);
                    albB = item > 0.5 ? kGoods[(int)min(hr * 5.0, 4.0)] : float3(0.10, 0.075, 0.05);
                }
                else if (type == 1.0)
                {
                    maskB = Rect(pB, float2(bx0, 0.0), float2(bx0 + 1.1, 1.9), aaB);
                    albB = float3(0.09, 0.10, 0.10) * (1.0 - 0.35 * Rect(pB, float2(bx0 + 0.08, 0.1), float2(bx0 + 1.02, 0.9), aaB));
                    float2 dotC = float2(frac((pB.x - bx0 - 0.1) / 0.09), pB.y - 1.72);
                    ledB = maskB * Rect(dotC, float2(0.35, -0.012), float2(0.65, 0.012), float2(aaB.x / 0.09, aaB.y))
                         * Rect(pB, float2(bx0 + 0.1, 1.6), float2(bx0 + 0.46, 1.8), aaB);
                    ledB += 0.25 * maskB * Rect(pB, float2(bx0 + 0.2, 1.05), float2(bx0 + 0.9, 1.45), aaB) * step(0.4, h2.w);
                }
                else
                {
                    maskB = Rect(pB, float2(bx0, 0.0), float2(bx0 + 0.9, 1.8), aaB);
                    albB = float3(0.14, 0.09, 0.05) * (1.0 - 0.5 * Line1(pB.x, bx0 + 0.45, 0.006, aaB.x));
                }
                maskB *= present * inB;
                float3 pBw = float3(pB, zB);
                float3 colB = albB * RoomLight(pBw, float3(0, 0, -1), S, skyIn, sunIn, lampPos, lampCol, tube)
                            + _EmissionColor.rgb * _CoolLight.rgb * ledB * 0.8;   // standby LEDs glow even unlit
                color = lerp(color, colB, maskB);
                emit += _EmissionColor.rgb * _CoolLight.rgb * ledB * 0.8 * maskB;

                // ---- Front plane: counter, workbench, table and chair, crates; plus the lamp -----------
                float c = S.x * (0.3 + 0.4 * h2.z);
                float maskA = 0, topA = 0;
                float3 albA = float3(0.10, 0.07, 0.045);
                if (type == 0.0)
                {
                    maskA = Rect(pA, float2(c - 1.2, 0.0), float2(c + 1.2, 0.95), aaA);
                    topA = Rect(pA, float2(c - 1.25, 0.92), float2(c + 1.25, 0.98), aaA);
                    float col = floor(pA.x / 0.25);
                    float hr = Hash12(float2(col, h1.x * 77.0));
                    float goods = step(0.55, hr) * Rect(pA, float2(col * 0.25 + 0.04, 0.98), float2(col * 0.25 + 0.21, 0.98 + 0.05 + 0.2 * hr), aaA)
                                * step(c - 1.1, pA.x) * step(pA.x, c + 1.1);
                    albA = goods > 0.5 ? kGoods[(int)min(hr * 5.0, 4.0)] : float3(0.13, 0.09, 0.055);
                    maskA = saturate(maskA + topA + goods);
                }
                else if (type == 1.0)
                {
                    topA = Rect(pA, float2(c - 1.0, 0.86), float2(c + 1.0, 0.92), aaA);
                    float legs = Rect(pA, float2(c - 0.95, 0.0), float2(c - 0.88, 0.86), aaA) + Rect(pA, float2(c + 0.88, 0.0), float2(c + 0.95, 0.86), aaA)
                               + Rect(pA, float2(c - 0.95, 0.18), float2(c + 0.95, 0.22), aaA);
                    float stool = Rect(pA, float2(c + 1.3, 0.62), float2(c + 1.62, 0.67), aaA) + Rect(pA, float2(c + 1.44, 0.0), float2(c + 1.48, 0.62), aaA);
                    float vise = Rect(pA, float2(c + 0.5, 0.92), float2(c + 0.7, 1.08), aaA);
                    maskA = saturate(topA + legs + stool + vise);
                    albA = float3(0.085, 0.08, 0.075);
                }
                else if (type == 2.0)
                {
                    topA = Rect(pA, float2(c - 0.6, 0.72), float2(c + 0.6, 0.76), aaA);
                    float legs = Rect(pA, float2(c - 0.55, 0.0), float2(c - 0.5, 0.72), aaA) + Rect(pA, float2(c + 0.5, 0.0), float2(c + 0.55, 0.72), aaA);
                    float chair = Rect(pA, float2(c + 0.8, 0.45), float2(c + 1.2, 0.49), aaA) + Rect(pA, float2(c + 1.15, 0.45), float2(c + 1.2, 0.95), aaA)
                                + Rect(pA, float2(c + 0.82, 0.0), float2(c + 0.85, 0.45), aaA) + Rect(pA, float2(c + 1.15, 0.0), float2(c + 1.18, 0.45), aaA);
                    // Potted plant from the hydroponics halls: pot plus a lobed leaf mass.
                    float px = c - 1.35;
                    float pot = Rect(pA, float2(px - 0.14, 0.0), float2(px + 0.14, 0.34), aaA);
                    float2 lp = (pA - float2(px, 0.72)) * float2(1.0, 1.25);
                    float ang = atan2(lp.y, lp.x);
                    float leaves = saturate((0.36 + 0.07 * sin(ang * 7.0 + h2.y * 6.0) - length(lp)) / max(aaA.x, 1e-3) + 0.5);
                    maskA = saturate(topA + legs + chair + pot + leaves);
                    albA = leaves > 0.5 && pot < 0.5 ? float3(0.05, 0.09, 0.035) : float3(0.12, 0.075, 0.045);
                }
                else
                {
                    float2 q = pA - float2(c - 0.9, 0.0);
                    float colI = floor(q.x / 0.62);
                    float hr = Hash12(float2(colI, h2.w * 61.0));
                    float stack = 1.0 + floor(hr * 3.0);
                    maskA = Rect(q, float2(0.0, 0.0), float2(3.0 * 0.62, 2.0), aaA) * saturate((stack * 0.55 - q.y) / aaA.y + 0.5)
                          * Rect(float2(frac(q.x / 0.62) * 0.62, 0.5), float2(0.03, 0.0), float2(0.59, 1.0), aaA);
                    maskA *= 1.0 - 0.8 * Line1(frac(q.y / 0.55), 0.0, 0.012, aaA.y / 0.55);
                    albA = float3(0.20, 0.15, 0.09);
                }
                maskA *= present * inA;

                // Lamp: pendant (shade, cord, bulb) or tube fitting, on the front plane.
                float lampShape, lampEmit;
                if (tube > 0.5)
                {
                    lampShape = Rect(pA, float2(lx - 0.65, S.y - 0.3), float2(lx + 0.65, S.y - 0.2), aaA);
                    lampEmit = Rect(pA, float2(lx - 0.6, S.y - 0.3), float2(lx + 0.6, S.y - 0.27), aaA);
                }
                else
                {
                    float yy = pA.y - ly;
                    float halfW = 0.2 - yy * 0.55;
                    lampShape = Rect(float2(abs(pA.x - lx) - halfW, yy), float2(-10.0, 0.0), float2(0.0, 0.22), aaA)
                              + Line1(pA.x, lx, 0.006, aaA.x) * step(ly + 0.2, pA.y) * step(pA.y, S.y);
                    float2 bd = (pA - float2(lx, ly - 0.01)) / 0.05;
                    lampEmit = saturate(1.0 - dot(bd, bd));
                }
                lampShape = saturate(lampShape) * inA;
                lampEmit *= inA;

                float3 pAw = float3(pA, zA);
                float3 litA = RoomLight(pAw, float3(0, 0, -1), S, skyIn, sunIn, lampPos, lampCol, tube);
                float3 litTop = RoomLight(pAw, float3(0, 1, 0), S, skyIn, sunIn, lampPos, lampCol, tube);
                float3 colA = albA * lerp(litA, litTop, saturate(topA));
                color = lerp(color, colA, maskA);
                color = lerp(color, float3(0.03, 0.028, 0.025) * litA, lampShape);
                float3 bulb = lampCol * 5.0 * lampEmit;
                color += bulb;
                emit += bulb;

                // ---- Blinds and curtains just behind the glass ------------------------------------
                float blindRnd = h3.y;
                float blindType = blindRnd < (1.0 - _BlindAmount) ? 0.0 : floor(frac(blindRnd * 5.3) * 3.0) + 1.0;
                float level = lerp(S.y * 0.4, S.y - 0.15, h3.z);
                float blind = 0.0, hem = 0.0, folds = 1.0;
                if (blindType == 1.0)
                {
                    blind = saturate((pBl.y - level) / aaBl.y + 0.5);
                    hem = Line1(pBl.y, level + 0.02, 0.02, aaBl.y);
                }
                else if (blindType == 2.0)
                {
                    float slat = 1.0 - Line1(frac(pBl.y / 0.05), 0.5, 0.008, aaBl.y / 0.05);
                    blind = saturate((pBl.y - level) / aaBl.y + 0.5) * slat;
                    folds = 0.85 + 0.15 * frac(pBl.y / 0.05);
                }
                else if (blindType == 3.0)
                {
                    float bay = 1.5;
                    float xb = frac(pBl.x / bay) * bay;
                    float open = bay * lerp(0.15, 0.85, frac(h3.z * 7.7));
                    blind = saturate((abs(xb - bay * 0.5) - open * 0.5) / aaBl.x + 0.5);
                    folds = 0.78 + 0.22 * sin(pBl.x * 57.0);
                }
                float3 cloth = kCloth[(int)min(h3.w * 5.0, 4.0)];
                float3 pBlw = float3(pBl, 0.04);
                float3 dvb = lampPos - pBlw;
                float r2 = _LampRange * _LampRange;
                float3 backlit = lampCol * (0.45 * r2 / (dot(dvb, dvb) + r2));    // lamp glowing through fabric
                float3 blindCol = cloth * folds * (skyIn * 1.2 + sunIn * 0.5 + _InteriorFill.rgb) + cloth * backlit * (1.0 - 0.7 * hem);
                blindCol *= 1.0 - 0.5 * hem;
                color = lerp(color, blindCol, blind);
                emit = emit * (1.0 - blind) + cloth * backlit * blind;

                // Partition ends and floor slabs where a room boundary crosses a pane.
                float edgeX = 1.0 - Rect(o.xy, float2(0.06, -1.0), float2(S.x - 0.06, S.y + 1.0), max(fwidth(o.xy), 1e-4));
                float edgeY = 1.0 - Rect(o.xy, float2(-1.0, 0.12), float2(S.x + 1.0, S.y - 0.15), max(fwidth(o.xy), 1e-4));
                float3 edgeLight = RoomLight(float3(o.xy, 0.0), float3(0, 0, -1), S, skyIn, sunIn, lampPos, lampCol, tube);
                color = lerp(color, wall * 0.8 * edgeLight, edgeX);
                color = lerp(color, float3(0.1, 0.095, 0.09) * edgeLight, edgeY);

                roomGlow = lampCol * 0.25 + emit * 0.1;
                return color;
            }

            float3 GlassSpecular(Light light, float3 N, float3 V, float roughness)
            {
                float3 H = SafeNormalize(light.direction + V);
                float NoH = saturate(dot(N, H)), LoH = saturate(dot(light.direction, H)), NoL = saturate(dot(N, light.direction));
                float r2 = roughness * roughness;
                float d = NoH * NoH * (r2 - 1.0) + 1.00001;
                float spec = r2 / (d * d * max(0.1, LoH * LoH) * (roughness * 4.0 + 2.0));
                return light.color * (min(spec, 100.0) * 0.04 * NoL * light.distanceAttenuation * light.shadowAttenuation);
            }

            void WindowFrag(Varyings input, out half4 outColor : SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                , out uint outRenderingLayers : SV_Target1
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);

                float3 positionWS = input.positionWS;
                float3 N = normalize(input.normalWS);
                float3 V = GetWorldSpaceNormalizeViewDir(positionWS);
                float2 screenUV = GetNormalizedScreenSpaceUV(input.positionCS);
                Facade f = BuildFacade(N, positionWS);

                InputData inputData = (InputData)0;
                inputData.positionWS = positionWS;
                inputData.normalWS = N;
                inputData.viewDirectionWS = V;
                inputData.normalizedScreenSpaceUV = screenUV;
                inputData.shadowCoord = TransformWorldToShadowCoord(positionWS);
                half4 shadowMask = half4(1, 1, 1, 1);
                AmbientOcclusionFactor ao = GetScreenSpaceAmbientOcclusion(screenUV);
                uint meshLayers = GetMeshRenderingLayer();

                Light mainLight = GetMainLight(inputData.shadowCoord, positionWS, shadowMask);
                #ifdef _LIGHT_LAYERS
                if (!IsMatchingLightLayer(mainLight.layerMask, meshLayers)) mainLight.color = 0;
                #endif

                // Light arriving at the window from outside, used to light the rooms behind it.
                float3 skyOut = max(SampleSH(f.N), 0.0);
                float3 skyIn = skyOut * _InteriorDaylight;
                float3 sunIn = mainLight.color * (saturate(dot(mainLight.direction, f.N)) * mainLight.shadowAttenuation * _SunSpill);

                float3 roomGlow;
                float3 interior = InteriorColor(positionWS, f, skyIn, sunIn, roomGlow) * f.valid;

                // Dust: world-space smudges and vertical drips on the facade plane, plus grime where SSAO finds the
                // sill, mullions and reveals (the pane edges); UVs are not used.
                float2 fp = float2(dot(positionWS - _RoomOffset.xyz, f.T), positionWS.y) * _DirtScale;
                float smudge = ValueNoise(fp) * 0.6 + ValueNoise(fp * 2.7 + 5.1) * 0.4;
                float drips = ValueNoise(float2(fp.x * 9.0, fp.y * 0.7 + 3.3));
                float edge = saturate((1.0 - ao.indirectAmbientOcclusion) * 2.5) * _EdgeGrime;
                // Soft haze everywhere, faint drip streaks, and heavier grime at the occluded pane edges.
                float dirt = _DirtAmount * (0.1 + 0.2 * smudge + 0.12 * drips * drips * drips) + edge * (0.35 + 0.4 * smudge);
                dirt = min(dirt, 0.8);

                // Old glass is slightly wavy; perturb the reflection normal a touch.
                float3 Nr = normalize(N + (f.T * (smudge - 0.5) + float3(0, 1, 0) * (drips - 0.5)) * 0.012);
                float perceptualRoughness = 1.0 - lerp(_Smoothness, 0.35, dirt);
                float roughness = max(perceptualRoughness * perceptualRoughness, 0.002);
                float NoV = saturate(dot(N, V));
                float fresnel = 0.04 + 0.96 * pow(1.0 - NoV, 5.0) * (1.0 - perceptualRoughness * 0.7);
                float3 reflection = GlossyEnvironmentReflection(reflect(-V, Nr), positionWS, perceptualRoughness, ao.indirectAmbientOcclusion, screenUV)
                                  * (fresnel * _ReflectionStrength);

                float3 specular = GlassSpecular(mainLight, Nr, V, roughness);
                #if defined(_ADDITIONAL_LIGHTS)
                uint pixelLightCount = GetAdditionalLightsCount();
                #if USE_CLUSTER_LIGHT_LOOP
                [loop] for (uint lightIndex = 0; lightIndex < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); lightIndex++)
                {
                    CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
                    Light light = GetAdditionalLight(lightIndex, positionWS, shadowMask);
                    #ifdef _LIGHT_LAYERS
                    if (IsMatchingLightLayer(light.layerMask, meshLayers))
                    #endif
                        specular += GlassSpecular(light, Nr, V, roughness);
                }
                #endif
                LIGHT_LOOP_BEGIN(pixelLightCount)
                    Light light = GetAdditionalLight(lightIndex, positionWS, shadowMask);
                    #ifdef _LIGHT_LAYERS
                    if (IsMatchingLightLayer(light.layerMask, meshLayers))
                    #endif
                        specular += GlassSpecular(light, Nr, V, roughness);
                LIGHT_LOOP_END
                #endif

                float3 dustLit = _DirtColor.rgb * (mainLight.color * (saturate(dot(N, mainLight.direction)) * mainLight.shadowAttenuation * ao.directAmbientOcclusion)
                                                 + skyOut * ao.indirectAmbientOcclusion);
                float3 color = interior * _GlassTint.rgb * (1.0 - fresnel) * (1.0 - dirt * 0.55)
                             + dirt * (dustLit + roomGlow * 0.3)
                             + reflection * (1.0 - dirt * 0.4)
                             + specular * (1.0 - dirt * 0.6);

                float fogCoord = InitializeInputDataFog(float4(positionWS, 1.0), input.fogFactor);
                color = MixFog(color, fogCoord);
                outColor = half4(color, 1.0);
                #ifdef _WRITE_RENDERING_LAYERS
                outRenderingLayers = EncodeMeshRenderingLayer();
                #endif
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
            #pragma multi_compile _ _WRITE_SMOOTHNESS
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
                    float2 remappedOctNormalWS = saturate(octNormalWS * 0.5 + 0.5);
                    outNormalWS = half4(PackFloat2To888(remappedOctNormalWS), 0.0);
                #else
                    outNormalWS = half4(NormalizeNormalPerPixel(input.normalWS), 0.0);
                #endif
                #if defined(_WRITE_SMOOTHNESS)
                    outNormalWS.a = _Smoothness;
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
