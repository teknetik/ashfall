// Light budget pass (20 Nov 2026, art/light_budget_20261120/README.md): the pool of a demoted lamp.
// Drawn as a box round the lamp's range (back faces, depth test GEqual, additive). Each pixel reconstructs the opaque
// surface from the camera depth texture and adds the lamp's own Lambert term with URP's attenuation (distance window,
// spot cone, cookie) on an assumed albedo, so the pool sits on paving, steps, walls and under sails like the real light
// and cross-fades with it. No URP light slot is used.
Shader "Athen Hill/Lamp Pool"
{
    Properties
    {
        _LightPos("Light position (xyz), 1/range^2 (w)", Vector) = (0,0,0,1)
        _LightColor("Linear colour x intensity x pool weight (set as a vector, no gamma conversion)", Vector) = (0,0,0,0)
        _SpotDir("Spot direction", Vector) = (0,-1,0,0)
        _SpotParams("Spot a, b, isSpot", Vector) = (0,1,0,0)
        _CookieTex("Cookie", 2D) = "white" {}
        _CookieParams("Cookie on, tan(half angle), channel mode", Vector) = (0,1,0,0)
        _CookieRight("Light right", Vector) = (1,0,0,0)
        _CookieUp("Light up", Vector) = (0,1,0,0)
        _Albedo("Assumed albedo (linear, set as a vector)", Vector) = (.42,.36,.30,1)
        _PoolCut("Pool ends at this fraction of the range (soft over the last 0.15)", Float) = 1
    }
    SubShader
    {
        Tags { "Queue"="Transparent-120" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "IgnoreProjector"="True" }
        Pass
        {
            Name "LampPool"
            Tags { "LightMode"="UniversalForward" }
            Blend One One
            ZWrite Off
            ZTest GEqual
            Cull Front
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
            float4 _LightPos;
            float4 _LightColor;
            float4 _SpotDir;
            float4 _SpotParams;
            float4 _CookieParams;
            float4 _CookieRight;
            float4 _CookieUp;
            float4 _Albedo;
            float4 _CookieTex_ST;
            float _PoolCut;
            CBUFFER_END
            TEXTURE2D(_CookieTex); SAMPLER(sampler_CookieTex);

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; };

            Varyings Vert(Attributes i)
            {
                Varyings o;
                o.positionCS = TransformWorldToHClip(TransformObjectToWorld(i.positionOS.xyz));
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                float2 uv = i.positionCS.xy / _ScaledScreenParams.xy;
            #if UNITY_REVERSED_Z
                float depth = SampleSceneDepth(uv);
            #else
                float depth = lerp(UNITY_NEAR_CLIP_VALUE, 1, SampleSceneDepth(uv));
            #endif
                float3 wp = ComputeWorldSpacePosition(uv, depth, UNITY_MATRIX_I_VP);
                float3 toLight = _LightPos.xyz - wp;
                float distSq = max(dot(toLight, toLight), 1e-4);
                // URP's distance window: 1/d^2 * (1 - (d^2/r^2)^2)^2
                float f = distSq * _LightPos.w;
                float smooth = saturate(1 - f * f); smooth *= smooth;
                float atten = smooth / distSq;
                // the box is cut short of the range (cheaper); fade the last 15 % of what remains so the edge is soft
                atten *= saturate((_PoolCut - sqrt(f)) / .15);
                if (atten <= 0) discard;
                float3 L = toLight * rsqrt(distSq);
                if (_SpotParams.z > .5)
                {
                    float s = saturate(dot(_SpotDir.xyz, -L) * _SpotParams.x + _SpotParams.y);
                    atten *= s * s;
                }
                float3 cookie = 1;
                if (_CookieParams.x > .5)
                {
                    float3 d = -L; float z = dot(d, _SpotDir.xyz);
                    float2 c = float2(dot(d, _CookieRight.xyz), dot(d, _CookieUp.xyz)) / max(1e-3, z * _CookieParams.y);
                    float4 t = SAMPLE_TEXTURE2D_LOD(_CookieTex, sampler_CookieTex, c * .5 + .5, 0);
                    cookie = _CookieParams.z > 1.5 ? t.aaa : (_CookieParams.z > .5 ? t.rrr : t.rgb);
                    cookie *= z > 0 ? 1 : 0;
                }
                // surface normal from the depth buffer, facing the camera
                float3 n = normalize(cross(ddy(wp), ddx(wp)));
                if (dot(n, _WorldSpaceCameraPos - wp) < 0) n = -n;
                float ndotl = saturate(dot(n, L));
                float3 c = _LightColor.rgb * _Albedo.rgb * cookie * (atten * ndotl);
                float fog = ComputeFogFactor(TransformWorldToHClip(wp).z);
                c = MixFogColor(c, half3(0, 0, 0), fog);
                return half4(c, 0);
            }
            ENDHLSL
        }
    }
}
