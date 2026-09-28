Shader "Athen Hill/Checkpoint Lettering"
{
 Properties { _MainTex("Font atlas",2D)="white"{} _Color("Colour",Color)=(1,1,1,1) }
 SubShader {
  Tags { "Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" }
  Pass {
   Tags { "LightMode"="SRPDefaultUnlit" }
   Blend SrcAlpha OneMinusSrcAlpha
   ZTest LEqual ZWrite Off Cull Back
   HLSLPROGRAM
   #pragma vertex Vert
   #pragma fragment Frag
   #pragma multi_compile_fog
   #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
   TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);
   CBUFFER_START(UnityPerMaterial)
   float4 _MainTex_ST; half4 _Color;
   CBUFFER_END
   struct Attributes { float4 position:POSITION;float2 uv:TEXCOORD0;half4 color:COLOR; };
   struct Varyings { float4 position:SV_POSITION;float2 uv:TEXCOORD0;half4 color:COLOR;float fog:TEXCOORD1; };
   Varyings Vert(Attributes i){Varyings o;o.position=TransformObjectToHClip(i.position.xyz);o.uv=TRANSFORM_TEX(i.uv,_MainTex);o.color=i.color*_Color;o.fog=ComputeFogFactor(o.position.z);return o;}
   half4 Frag(Varyings i):SV_Target{half4 c=i.color;c.a*=SAMPLE_TEXTURE2D(_MainTex,sampler_MainTex,i.uv).a;clip(c.a-.01);c.rgb=MixFog(c.rgb,i.fog);return c;}
   ENDHLSL
  }
 }
}
