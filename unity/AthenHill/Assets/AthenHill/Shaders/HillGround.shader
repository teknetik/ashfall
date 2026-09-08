Shader "Athen Hill/Hill Ground"
{
    Properties
    {
        _GroundTex("Soil gravel and ground cover", 2D) = "white" {}
        _Noise("Ground variation", 2D) = "gray" {}
        _Geology("Pebble and mineral detail", 2D) = "gray" {}
        _RockTex("Weathered stone", 2D) = "white" {}
        _Grass("Olive ground cover", Color) = (.28,.33,.12,1)
        _DryGrass("Dry grass", Color) = (.43,.40,.21,1)
        _Soil("Exposed soil", Color) = (.27,.21,.14,1)
        _Scale("Detail per metre", Range(.1,4)) = 1
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
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
            TEXTURE2D(_Noise); SAMPLER(sampler_Noise);
            TEXTURE2D(_GroundTex); SAMPLER(sampler_GroundTex);
            TEXTURE2D(_Geology); SAMPLER(sampler_Geology);
            TEXTURE2D(_RockTex); SAMPLER(sampler_RockTex);
            CBUFFER_START(UnityPerMaterial)
            float4 _Grass,_DryGrass,_Soil; float _Scale;
            CBUFFER_END
            struct Attributes { float4 position:POSITION; float3 normal:NORMAL; };
            struct Varyings { float4 position:SV_POSITION; float3 world:TEXCOORD0; float3 normal:TEXCOORD1; float fog:TEXCOORD2; };
            Varyings Vert(Attributes i)
            {
                Varyings o; o.world=TransformObjectToWorld(i.position.xyz);
                o.position=TransformWorldToHClip(o.world);o.normal=TransformObjectToWorldNormal(i.normal);
                o.fog=ComputeFogFactor(o.position.z); return o;
            }
            half4 Frag(Varyings i):SV_Target
            {
                float2 p=i.world.xz*_Scale;
                float broad=SAMPLE_TEXTURE2D(_Noise,sampler_Noise,p*.041).r;
                float detail=SAMPLE_TEXTURE2D(_Noise,sampler_Noise,p*.44).g;
                float4 geology=SAMPLE_TEXTURE2D(_Geology,sampler_Geology,p*.57);
                float3 rock=SAMPLE_TEXTURE2D(_RockTex,sampler_RockTex,p*.73).rgb;
                float3 normal=normalize(i.normal);
                float soil=smoothstep(.43,.62,broad+detail*.12);
                float stone=saturate((1-normal.y)*2+smoothstep(.6,.73,broad)*.75);
                float3 surface=SAMPLE_TEXTURE2D(_GroundTex,sampler_GroundTex,p*.42).rgb;
                float3 surfaceB=SAMPLE_TEXTURE2D(_GroundTex,sampler_GroundTex,p*.307+float2(.37,.13)).rgb;
                surface=lerp(surface,surfaceB,smoothstep(.35,.66,broad));
                float3 groundTint=lerp(_Grass.rgb*float3(3.1,2.75,6.5),_DryGrass.rgb*float3(2.2,2.3,4.0),soil);
                float3 albedo=surface*groundTint*(.84+detail*.28);
                // Exposed rock fades through gravel into the dry olive ground cover.
                albedo=lerp(albedo,rock*float3(.79,.76,.65),stone);
                float pebbles=smoothstep(.79,.91,geology.r)*soil;
                albedo=lerp(albedo,float3(.35,.31,.23),pebbles*.6);
                float height=lerp(dot(surface,float3(.21,.72,.07))*.018,dot(rock,float3(.21,.72,.07))*.08,stone);
                float3 dpdx=ddx(i.world),dpdy=ddy(i.world);
                float3 r1=cross(dpdy,normal),r2=cross(normal,dpdx);float det=dot(dpdx,r1);
                float3 grad=(ddx(height)*r1+ddy(height)*r2)*sign(det)/max(abs(det),.00001);
                normal=normalize(normal-clamp(grad,-.3,.3));
                Light light=GetMainLight(TransformWorldToShadowCoord(i.world));
                float3 illumination=SampleSH(normal)*(.83+.17*geology.b)+light.color*saturate(dot(normal,light.direction))*light.shadowAttenuation;
                return half4(MixFog(albedo*illumination,i.fog),1);
            }
            ENDHLSL
        }
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
    }
}
