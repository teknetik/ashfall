Shader "Athen Hill/Ward Reference Sky"
{
    Properties
    {
        _Noise("Cloud noise", 2D) = "gray" {}
        _Zenith("High sky", Color) = (.24,.39,.57,1)
        _Middle("Low sky", Color) = (.54,.64,.68,1)
        _Horizon("Dust horizon", Color) = (.83,.68,.47,1)
        _CloudLight("Sunlit cloud", Color) = (.96,.86,.68,1)
        _CloudShade("Cloud shade", Color) = (.48,.55,.60,1)
        _Coverage("Cloud coverage", Range(0,1)) = .48
        _CloudScale("Cloud layer scale", Range(1,10)) = 4.6
        _CloudEdge("Cloud edge softness", Range(.02,.2)) = .055
        _WispStrength("Upper wisps", Range(0,.3)) = .035
        _CloudOpacity("Cloud opacity", Range(0,1)) = .78
        _Exposure("Exposure", Range(.1,3)) = 1
        _CloudSpeed("Cloud drift", Range(0,.01)) = .0007
        _SunSize("Sun radius", Range(.001,.04)) = .009
        _SunVisibility("Solar disc and halo", Range(0,1)) = 1
        _SunDirection("Direction toward sun", Vector) = (0,1,0,0)
        _RidgeColor("Distant desert ridges", Color) = (.61,.53,.42,1)
        _RidgeStrength("Horizon ridges", Range(0,1)) = .48
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"
            sampler2D _Noise;
            float4 _Zenith, _Middle, _Horizon, _CloudLight, _CloudShade;
            float _Coverage, _CloudOpacity, _Exposure, _CloudSpeed, _SunSize, _SunVisibility;
            float4 _SunDirection;
            float _CloudScale, _CloudEdge, _WispStrength;
            float4 _RidgeColor; float _RidgeStrength;
            // Set by CityAtmosphere; zero also gives a valid static editor preview.
            float _AthenAtmosphereTime;
            struct Varyings { float4 position:SV_POSITION; float3 direction:TEXCOORD0; };
            Varyings Vert(float4 vertex:POSITION)
            {
                Varyings o; o.position=UnityObjectToClipPos(vertex);
                o.direction=vertex.xyz; return o;
            }
            float Noise(float2 p) { return tex2D(_Noise,p*.0625).r; }
            float Cloud(float2 p)
            {
                float2 warp=float2(Noise(p*.71),Noise(p*.71+7.1));
                p+=warp*.9;
                return Noise(p)*.49+Noise(p*2.13+3.7)*.27+Noise(p*4.37-5.2)*.15+Noise(p*8.91+2.4)*.065+Noise(p*17.7-8.1)*.025;
            }
            half4 Frag(Varyings i):SV_Target
            {
                float3 d=normalize(i.direction);
                float h=max(0,d.y);
                float3 sun=normalize(_SunDirection.xyz);
                float mu=saturate(dot(d,sun));
                float3 color=lerp(_Horizon.rgb,_Middle.rgb,smoothstep(0,.25,h));
                color=lerp(color,_Zenith.rgb,pow(saturate(h),.65));
                float warm=pow(mu,8)*_SunVisibility;
                color+=float3(.21,.11,.025)*warm*exp(-h*1.8);
                float2 wind=float2(_AthenAtmosphereTime*_CloudSpeed,0);
                float2 p=d.xz/(h+.16)*_CloudScale;
                p=p*float2(.95,1.05)+float2(4.2,-1.7)+wind;
                float n=Cloud(p);
                float cloud=smoothstep(1-_Coverage-_CloudEdge,1-_Coverage+_CloudEdge,n);
                cloud*=smoothstep(.005,.13,h)*_CloudOpacity;
                // A small offset toward the sun gives cloud lobes coherent lit rims.
                float densityTowardSun=Cloud(p+sun.xz*.24);
                float litRim=saturate(.62+(n-densityTowardSun)*3.8);
                float opticalDepth=saturate((n-(1-_Coverage))*3);
                float3 cloudColor=lerp(_CloudShade.rgb,_CloudLight.rgb,saturate(litRim-opticalDepth*.22+warm*.15));
                color=lerp(color,cloudColor,cloud);
                // Thin, stretched upper wisps sit behind the lower broken cloud layer.
                float wisps=smoothstep(.58,.77,Cloud(p*float2(.9,4.5)+11));
                color=lerp(color,_CloudLight.rgb,wisps*_WispStrength*smoothstep(.15,.5,h)*(1-cloud));
                float angle=acos(clamp(dot(d,sun),-.999999,.999999));
                float disc=1-smoothstep(_SunSize*.75,_SunSize,angle);
                float halo=exp(-angle*18)*.28;
                color+=float3(1,.72,.34)*(disc*4+halo)*(1-cloud*.82)*_SunVisibility;
                // The horizon remains continuous when an elevated review camera looks down.
                color=lerp(color,_Horizon.rgb,smoothstep(0,-.14,d.y));
                // A low atmospheric backdrop closes the empty horizon without extra scene geometry.
                // Circular coordinates avoid a longitude seam; authored canyon meshes remain in front.
                float2 bearing=normalize(d.xz+float2(.00001,0));
                float ridgeNoise=Noise(bearing*6.5+23);
                float ridgeHeight=.008+pow(saturate(ridgeNoise),2)*.11;
                float ridge=1-smoothstep(ridgeHeight-.0015,ridgeHeight+.0015,d.y);
                float nearHeight=-.015+Noise(bearing*10.3-17)*.055;
                float nearRidge=1-smoothstep(nearHeight-.001,nearHeight+.001,d.y);
                color=lerp(color,lerp(_Horizon.rgb,_RidgeColor.rgb,.65),ridge*_RidgeStrength);
                color=lerp(color,_RidgeColor.rgb,nearRidge*_RidgeStrength*.48);
                return half4(color*_Exposure,1);
            }
            ENDHLSL
        }
    }
}
