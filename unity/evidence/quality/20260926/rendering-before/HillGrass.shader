Shader "Athen Hill/Wind Grass"
{
    Properties
    {
        _Root("Root shade", Color) = (.19,.24,.065,1)
        _Tip("Olive tips", Color) = (.48,.53,.23,1)
        _Dry("Dry tips", Color) = (.69,.59,.32,1)
        _WindStrength("Wind bend metres", Range(0,.25)) = .065
    }
    SubShader
    {
        Tags { "Queue"="AlphaTest" "RenderType"="TransparentCutout" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite On
        Pass
        {
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            CBUFFER_START(UnityPerMaterial)
            float4 _Root,_Tip,_Dry; float _WindStrength;
            CBUFFER_END
            float _AthenAtmosphereTime;
            struct Attributes { float4 position:POSITION; float2 uv:TEXCOORD0; float4 color:COLOR; };
            struct Varyings { float4 position:SV_POSITION; float2 uv:TEXCOORD0; float3 world:TEXCOORD1; float4 color:COLOR; float fog:TEXCOORD2; };
            Varyings Vert(Attributes i)
            {
                Varyings o; float3 p=TransformObjectToWorld(i.position.xyz);
                float phase=_AthenAtmosphereTime*1.5+p.x*.8+p.z*.6;
                float wind=sin(phase)+.35*sin(phase*2.3);
                p.xz+=float2(.8,.35)*wind*_WindStrength*i.uv.y*i.uv.y;
                o.world=p;o.position=TransformWorldToHClip(p);o.uv=i.uv;o.color=i.color;
                o.fog=ComputeFogFactor(o.position.z);return o;
            }
            half4 Frag(Varyings i):SV_Target
            {
                // Nine individually tapered blades per card; no large transparent billboard texture.
                float lane=floor(i.uv.x*9);
                float random=frac(sin(lane*39.73+i.color.a*93.1)*4375.53);
                float height=.32+random*.68;
                float y=i.uv.y/height;
                float bend=(random-.5)*y*y*1.65;
                float x=frac(i.uv.x*9)-.5+bend+(random-.5)*.23;
                float width=pow(saturate(1-y),.8)*(.20+random*.12);
                clip(min(width-abs(x),1-y));
                float3 tip=lerp(_Tip.rgb,_Dry.rgb,smoothstep(.55,.95,i.color.r));
                float3 albedo=lerp(_Root.rgb,tip,saturate(y*.85+.15))*(.62+i.color.g*.25);
                albedo*=lerp(.76,1.12,saturate(x/max(width,.001)*.5+.5));
                Light light=GetMainLight(TransformWorldToShadowCoord(i.world));
                float3 illumination=SampleSH(float3(0,1,0))+light.color*(.45+.55*saturate(light.direction.y))*lerp(.5,1,light.shadowAttenuation);
                return half4(MixFog(albedo*illumination,i.fog),1);
            }
            ENDHLSL
        }
    }
}
