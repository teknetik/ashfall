Shader "Athen Hill/Desert Terrain"
{
    Properties
    {
        _RockTex("Sandstone albedo", 2D) = "white" {}
        _Geology("Geological detail (linear)", 2D) = "gray" {}
        _RockTint("Rock tint", Color) = (1,1,1,1)
        _Sand("Deposited sand", Color) = (.59,.46,.30,1)
        _Haze("Distance haze", Color) = (.62,.58,.51,1)
        _DetailScale("Rock repeats per metre", Range(.02,1)) = .073
        _Relief("Surface relief", Range(0,2)) = .14
        _HazeDensity("Atmospheric density", Range(0,.02)) = .0048
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
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            TEXTURE2D(_Geology); SAMPLER(sampler_Geology);
            TEXTURE2D(_RockTex); SAMPLER(sampler_RockTex);
            CBUFFER_START(UnityPerMaterial)
            float4 _RockTint,_Sand,_Haze;
            float _DetailScale,_Relief,_HazeDensity;
            CBUFFER_END
            // CityTimeOfDay owns these globals and restores them on teardown.
            // x: active clock, y: validity of the retained authored-direction shadow bake.
            float4 _AthenTerrainTime;
            float4 _AthenTerrainHazeScale;
            struct Attributes { float4 position:POSITION; float3 normal:NORMAL; float4 light:COLOR; };
            struct Varyings { float4 position:SV_POSITION; float3 world:TEXCOORD0; float3 normal:TEXCOORD1; float2 light:TEXCOORD2; };
            Varyings Vert(Attributes i)
            {
                Varyings o;o.world=TransformObjectToWorld(i.position.xyz);
                o.position=TransformWorldToHClip(o.world);o.normal=TransformObjectToWorldNormal(i.normal);o.light=i.light.rg;return o;
            }
            float4 Geology(float3 p,float3 weights,float scale)
            {
                return SAMPLE_TEXTURE2D(_Geology,sampler_Geology,p.zy*scale)*weights.x
                     + SAMPLE_TEXTURE2D(_Geology,sampler_Geology,p.xz*scale)*weights.y
                     + SAMPLE_TEXTURE2D(_Geology,sampler_Geology,p.xy*scale)*weights.z;
            }
            float3 Rock(float2 uv)
            {
                // Two differently scaled samples with a continuous blend avoid a repeated cliff stamp.
                float blend=SAMPLE_TEXTURE2D(_Geology,sampler_Geology,uv*.11+7.3).r;
                blend=smoothstep(.32,.67,blend);
                return lerp(SAMPLE_TEXTURE2D(_RockTex,sampler_RockTex,uv).rgb,
                    SAMPLE_TEXTURE2D(_RockTex,sampler_RockTex,uv*.731+float2(.37,.71)).rgb,blend);
            }
            half4 Frag(Varyings i):SV_Target
            {
                float3 n=normalize(i.normal);
                float3 weights=pow(abs(n),4);weights/=max(dot(weights,1),.0001);
                float4 macro=Geology(i.world,weights,.009);
                float3 p=i.world+float3(macro.r,0,macro.g)*2;
                float3 rock=(Rock(p.zy*_DetailScale)*weights.x+Rock(p.xz*_DetailScale)*weights.y+Rock(p.xy*_DetailScale)*weights.z)*_RockTint.rgb;
                float folded=i.world.y+macro.r*3+sin(i.world.x*.024+i.world.z*.018)*2;
                float beds=sin(folded*.72)*.5+.5;
                float3 albedo=rock*lerp(float3(.73,.65,.56),float3(1.13,1.03,.87),beds*.5+macro.r*.5);
                float sand=smoothstep(.70,.95,n.y)*smoothstep(.3,.7,macro.g);
                albedo=lerp(albedo,_Sand.rgb*(.70+macro.r*.28),sand*.7);
                float distanceToCamera=distance(_WorldSpaceCameraPos,i.world);
                float h=dot(rock,float3(.21,.72,.07))*_Relief*(1-sand)*saturate(1-distanceToCamera/210);
                float3 dpdx=ddx(i.world),dpdy=ddy(i.world);
                float3 r1=cross(dpdy,n),r2=cross(n,dpdx);
                float det=dot(dpdx,r1);
                float3 grad=(ddx(h)*r1+ddy(h)*r2)*sign(det)/max(abs(det),.00001);
                n=normalize(n-clamp(grad,-.4,.4));
                // This overload includes URP17.6 shadow-distance fade, including its
                // screen-space and cascade variants. No lightmap shadow mask is supplied.
                Light sun=GetMainLight(TransformWorldToShadowCoord(i.world),i.world,half4(1,1,1,1));
                float ndl=saturate(dot(n,sun.direction));
                float cavity=lerp(.78,1,macro.r);
                float clockActive=saturate(_AthenTerrainTime.x);
                float authoredShadowWeight=lerp(1,saturate(_AthenTerrainTime.y),clockActive);
                float authoredShadow=lerp(1,lerp(.25,1,i.light.x),authoredShadowWeight);
                // Keep the original noon view exactly, then replace its directional bake
                // with the live shadow as the sun moves. Beyond URP's shadow distance,
                // current normal lighting replaces the invalid noon-only cast shadow.
                float liveShadow=lerp(1,sun.shadowAttenuation,clockActive*(1-authoredShadowWeight));
                float3 lighting=SampleSH(n)*cavity*i.light.y+sun.color*ndl*authoredShadow*liveShadow;
                float3 color=albedo*lighting;
                float3 view=normalize(_WorldSpaceCameraPos-i.world);
                float3 halfDir=normalize(sun.direction+view);
                color+=sun.color*pow(saturate(dot(n,halfDir)),18)*.018*ndl*liveShadow;
                // Exponential depth retains relief nearby and separates the blue-grey rear ranges.
                float haze=1-exp(-max(0,distanceToCamera-38)*_HazeDensity);
                haze=saturate(haze+exp(-max(0,i.world.y)*.06)*.11);
                // Scale each material's existing haze relative to the captured default fog.
                // The multiplier is computed in the renderer's color space, avoiding a
                // self-lit beige horizon at night while retaining authored daytime tuning.
                float3 hazeColor=_Haze.rgb*lerp(float3(1,1,1),_AthenTerrainHazeScale.rgb,clockActive);
                return half4(lerp(color,hazeColor,haze),1);
            }
            ENDHLSL
        }
        // Distant backdrop writes depth in its forward pass. It does not need the
        // city SSAO prepass: this material supplies its own geological cavity shading.
    }
}
