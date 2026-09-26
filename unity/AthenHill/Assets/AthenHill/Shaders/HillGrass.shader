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
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        CBUFFER_START(UnityPerMaterial)
        float4 _Root,_Tip,_Dry; float _WindStrength;
        CBUFFER_END
        float _AthenAtmosphereTime;
        struct Attributes { float4 position:POSITION; float2 uv:TEXCOORD0; float4 color:COLOR; };
        struct Varyings { float4 position:SV_POSITION; float2 uv:TEXCOORD0; float3 world:TEXCOORD1; float4 color:COLOR; float fog:TEXCOORD2; half3 vertexLighting:TEXCOORD3; };
        Varyings Vert(Attributes i)
        {
            Varyings o; float3 p=TransformObjectToWorld(i.position.xyz);
            float phase=_AthenAtmosphereTime*1.5+p.x*.8+p.z*.6;
            float wind=sin(phase)+.35*sin(phase*2.3);
            p.xz+=float2(.8,.35)*wind*_WindStrength*i.uv.y*i.uv.y;
            o.world=p;o.position=TransformWorldToHClip(p);o.uv=i.uv;o.color=i.color;
            o.fog=ComputeFogFactor(o.position.z);
            o.vertexLighting=VertexLighting(p,half3(0,1,0));return o;
        }
        // The colour and depth passes use the same blade silhouette and the same
        // animated position. A whole uncut card must never occlude the ground.
        float3 Blade(float2 uv,float seed)
        {
            float lane=floor(uv.x*9);
            float random=frac(sin(lane*39.73+seed*93.1)*4375.53);
            float height=.32+random*.68;
            float y=uv.y/height;
            float bend=(random-.5)*y*y*1.65;
            float x=frac(uv.x*9)-.5+bend+(random-.5)*.23;
            float width=pow(saturate(1-y),.8)*(.20+random*.12);
            clip(min(width-abs(x),1-y));
            return float3(x,y,width);
        }
        half3 GrassLight(Light light)
        {
            // Preserve the authored broad blade response, but light reaching the
            // blades must still obey the same shadows as their surrounding soil.
            return light.color*(.45+.55*saturate(light.direction.y))*light.distanceAttenuation*light.shadowAttenuation;
        }
        ENDHLSL
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            half4 Frag(Varyings i):SV_Target
            {
                // Nine individually tapered blades per card; no large transparent billboard texture.
                float3 blade=Blade(i.uv,i.color.a);
                float x=blade.x,y=blade.y,width=blade.z;
                float3 tip=lerp(_Tip.rgb,_Dry.rgb,smoothstep(.55,.95,i.color.r));
                float3 albedo=lerp(_Root.rgb,tip,saturate(y*.85+.15))*(.62+i.color.g*.25);
                albedo*=lerp(.76,1.12,saturate(x/max(width,.001)*.5+.5));
                InputData inputData=(InputData)0;
                inputData.positionWS=i.world;
                inputData.normalizedScreenSpaceUV=GetNormalizedScreenSpaceUV(i.position);
                #if defined(_MAIN_LIGHT_SHADOWS_SCREEN)
                inputData.shadowCoord=float4(inputData.normalizedScreenSpaceUV,0,1);
                #else
                inputData.shadowCoord=TransformWorldToShadowCoord(i.world);
                #endif
                AmbientOcclusionFactor ao=GetScreenSpaceAmbientOcclusion(inputData.normalizedScreenSpaceUV);
                Light light=GetMainLight(inputData,half4(1,1,1,1),ao);
                float3 illumination=SampleSH(float3(0,1,0))*ao.indirectAmbientOcclusion+GrassLight(light);
                #if defined(_ADDITIONAL_LIGHTS)
                #if USE_CLUSTER_LIGHT_LOOP
                UNITY_LOOP for(uint lightIndex=0;lightIndex<min(URP_FP_DIRECTIONAL_LIGHTS_COUNT,MAX_VISIBLE_LIGHTS);++lightIndex)
                {
                    CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
                    illumination+=GrassLight(GetAdditionalLight(lightIndex,inputData,half4(1,1,1,1),ao));
                }
                #endif
                uint lightCount=GetAdditionalLightsCount();
                LIGHT_LOOP_BEGIN(lightCount)
                    illumination+=GrassLight(GetAdditionalLight(lightIndex,inputData,half4(1,1,1,1),ao));
                LIGHT_LOOP_END
                #elif defined(_ADDITIONAL_LIGHTS_VERTEX)
                illumination+=i.vertexLighting*ao.directAmbientOcclusion;
                #endif
                return half4(MixFog(albedo*illumination,i.fog),1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ColorMask R
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment DepthFrag
            half4 DepthFrag(Varyings i):SV_Target
            {
                Blade(i.uv,i.color.a);
                return i.position.z;
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment NormalFrag
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            half4 NormalFrag(Varyings i):SV_Target
            {
                Blade(i.uv,i.color.a);
                // The authored shading normal points up for the crossed blade cards.
                float3 normal=float3(0,1,0);
                #if defined(_GBUFFER_NORMALS_OCT)
                float2 octNormalWS=PackNormalOctQuadEncode(normal);
                return half4(PackFloat2To888(saturate(octNormalWS*.5+.5)),0);
                #else
                return half4(normal,0);
                #endif
            }
            ENDHLSL
        }
    }
}
