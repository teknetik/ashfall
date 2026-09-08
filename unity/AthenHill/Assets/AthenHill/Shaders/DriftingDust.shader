Shader "Athen Hill/Drifting Dust"
{
    Properties { _Color("Dust tint", Color) = (.78,.66,.43,.12) }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Blend SrcAlpha OneMinusSrcAlpha
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
            float4 _Color;
            CBUFFER_END
            struct Attributes { float4 position:POSITION; float2 uv:TEXCOORD0; float4 color:COLOR; };
            struct Varyings { float4 position:SV_POSITION; float2 uv:TEXCOORD0; float4 color:COLOR; float distance:TEXCOORD1; };
            Varyings Vert(Attributes i)
            {
                Varyings o;float3 p=TransformObjectToWorld(i.position.xyz);
                o.position=TransformWorldToHClip(p);o.uv=i.uv;o.color=i.color;
                o.distance=distance(p,_WorldSpaceCameraPos);return o;
            }
            half4 Frag(Varyings i):SV_Target
            {
                float2 p=i.uv*2-1;
                float alpha=pow(saturate(1-dot(p,p)),3);
                alpha*=smoothstep(.5,2,i.distance)*(1-smoothstep(38,65,i.distance));
                return half4(_Color.rgb*i.color.rgb,alpha*_Color.a*i.color.a);
            }
            ENDHLSL
        }
    }
}
