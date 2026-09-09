Shader "Athen Hill/Courtyard Thin Surface"
{
    Properties
    {
        [MainColor] _BaseColor("Colour", Color)=(.64,.49,.26,1)
        [MainTexture] _BaseMap("Woven colour", 2D)="white"{}
        _WindStrength("Wind bend in metres", Range(0,.12))=.035
        _Transmission("Sun through thin material", Range(0,.5))=.22
        _RootShade("Root darkening", Range(0,.6))=.24
    }
    SubShader
    {
        Tags {"RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline"}
        Cull Off ZWrite On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        CBUFFER_START(UnityPerMaterial)
        half4 _BaseColor; float4 _BaseMap_ST;
        float _WindStrength, _Transmission, _RootShade;
        CBUFFER_END
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        float _AthenAtmosphereTime;
        struct Attributes {float4 position:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;float4 color:COLOR;};
        struct Varyings {float4 position:SV_POSITION;float3 world:TEXCOORD0;float3 normal:TEXCOORD1;float2 uv:TEXCOORD2;float2 shade:TEXCOORD3;};
        float3 WindPosition(Attributes a)
        {
            float3 p=TransformObjectToWorld(a.position.xyz);
            float phase=_AthenAtmosphereTime*1.5+p.x*.8+p.z*.6;
            p.xz+=float2(.8,.35)*(sin(phase)+.35*sin(phase*2.3))*_WindStrength*a.color.a*a.color.a;
            return p;
        }
        Varyings Vert(Attributes a)
        {
            Varyings o;o.world=WindPosition(a);o.position=TransformWorldToHClip(o.world);
            o.normal=TransformObjectToWorldNormal(a.normal);o.uv=TRANSFORM_TEX(a.uv,_BaseMap);
            o.shade=float2(ComputeFogFactor(o.position.z),a.color.a);return o;
        }
        ENDHLSL
        Pass
        {
            Name "ForwardLit" Tags {"LightMode"="UniversalForward"}
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            half4 Frag(Varyings i, FRONT_FACE_TYPE face:FRONT_FACE_SEMANTIC):SV_Target
            {
                half3 n=normalize(i.normal)*IS_FRONT_VFACE(face,1,-1);
                Light sun=GetMainLight(TransformWorldToShadowCoord(i.world));
                half facing=dot(n,sun.direction);
                half3 indirect=lerp(SampleSH(n),SampleSH(half3(0,1,0)),.40);
                half3 direct=sun.color*(saturate(facing)+_Transmission*saturate(-facing))*sun.shadowAttenuation;
                half3 colour=SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv).rgb*_BaseColor.rgb;
                colour*=1-_RootShade*(1-i.shade.y);
                return half4(MixFog(colour*(indirect+direct),i.shade.x),1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "ShadowCaster" Tags {"LightMode"="ShadowCaster"}
            ColorMask 0 ZTest LEqual
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex ShadowVert
            #pragma fragment ShadowFrag
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            float3 _LightDirection,_LightPosition;
            float4 ShadowVert(Attributes a):SV_POSITION
            {
                float3 p=WindPosition(a);float3 n=TransformObjectToWorldNormal(a.normal);
                #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 lightDirection=normalize(_LightPosition-p);
                #else
                float3 lightDirection=_LightDirection;
                #endif
                float4 h=TransformWorldToHClip(ApplyShadowBias(p,n,lightDirection));
                #if UNITY_REVERSED_Z
                h.z=min(h.z,UNITY_NEAR_CLIP_VALUE*h.w);
                #else
                h.z=max(h.z,UNITY_NEAR_CLIP_VALUE*h.w);
                #endif
                return h;
            }
            half4 ShadowFrag():SV_Target{return 0;}
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags {"LightMode"="DepthOnly"} ColorMask R
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment DepthFrag
            half4 DepthFrag(Varyings i):SV_Target{return i.position.z;}
            ENDHLSL
        }
        Pass
        {
            Name "DepthNormals" Tags {"LightMode"="DepthNormals"}
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment NormalFrag
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            half4 NormalFrag(Varyings i, FRONT_FACE_TYPE face:FRONT_FACE_SEMANTIC):SV_Target
            {
                float3 n=normalize(i.normal)*IS_FRONT_VFACE(face,1,-1);
                #if defined(_GBUFFER_NORMALS_OCT)
                float2 octNormalWS=PackNormalOctQuadEncode(n);
                return half4(PackFloat2To888(saturate(octNormalWS*.5+.5)),0);
                #else
                return half4(n,0);
                #endif
            }
            ENDHLSL
        }
    }
}
