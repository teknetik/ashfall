// Ward Sky V2: procedural day/night skybox for Tir's oasis city.
//
// Drop-in replacement for "Athen Hill/Ward Reference Sky" (the scene's time-aware sky material,
// Art/ReferenceStreet/20260909/WardReferenceSky.mat), "Athen Hill/Ward Day Night Sky" and
// "Athen Hill/Desert Atmosphere". Every property those shaders declare is accepted here with the same
// meaning, so CityTimeOfDay keeps driving _Zenith/_Middle/_Horizon/_CloudLight/_CloudShade/_RidgeColor,
// _Exposure, _SunVisibility and _SunDirection each frame. See WardSkyV2.README.md.
//
// LUMINANCE SCALE (linear HDR, before post-exposure and ACES):
//   * A palette colour of 1.0 (after Unity's sRGB->linear conversion of Color properties) is sky
//     radiance 1.0 at _Exposure 1, exactly as in the previous Ward skies. The gradient, Rayleigh
//     phase term (mean 1 over the sphere) and horizon dust term (azimuthal mean 1) redistribute
//     that palette rather than adding energy, so the hemisphere-average sky luminance stays within
//     a few percent of the old shader for the same profile frame.
//   * The Mie aureole has a sphere-mean of 0.012 x _CloudLight; it only concentrates light near the sun.
//   * The sun disc's MEAN radiance is _SunIntensity x sun tint (default 8; 4 matches the old "disc*4"); limb
//     darkening makes the centre ~25% brighter and the limb darker. Sun, silver linings and the moon are
//     the only terms meant to exceed 1.0 (bloom sources).
//   * Stars peak around 0.04-1.6 x _StarBrightness; the night palette is ~0.001-0.01.
//
// Everything animated is driven by the global _AthenAtmosphereTime (CityAtmosphere). Reduced Motion
// stops that clock, which freezes cloud drift, cloud evolution and star twinkle. _CloudSpeed 0 also stops
// cloud motion. No keywords, no texture arrays, no loops; OpenGLCore via Unity's HLSL cross-compiler.
//
// COST (estimated, not yet measured natively): ~700-750 scalar ALU + 8 fetches of one 256^2 texture per
// clouded day pixel; night adds ~150-250 ALU + 4 explicit-LOD fetches (sun section skipped). Sun, night and
// ridge sections sit behind uniform branches. Roughly 0.25-0.35 ms for a full-screen 1080p sky on an RTX 3060.
Shader "Athen Hill/Ward Sky V2"
{
    Properties
    {
        [Header(Ward sky contract)]
        _Noise("Detail noise (AtmosphereNoise)", 2D) = "gray" {}
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
        _CloudSpeed("Cloud drift", Range(0,.02)) = .0007
        _SunSize("Sun radius", Range(.001,.04)) = .009
        _SunVisibility("Solar disc and halo", Range(0,1)) = 1
        _SunDirection("Direction toward sun", Vector) = (0,1,0,0)
        _RidgeColor("Distant desert ridges", Color) = (.61,.53,.42,1)
        _RidgeStrength("Horizon ridges", Range(0,1)) = .48

        [Header(Atmosphere)]
        _RayleighStrength("Rayleigh phase contrast", Range(0,1)) = .35
        _MieStrength("Mie aureole", Range(0,3)) = 1
        _MieG("Mie forward anisotropy", Range(.5,.95)) = .76
        _HorizonDustGlow("Sunward horizon dust glow at low sun", Range(0,1)) = .6
        _HorizonHaze("Horizon haze band", Range(0,1)) = .5
        _GroundDarkening("Below-horizon ground tint", Range(0,1)) = .35

        [Header(Sun)]
        _SunIntensity("Sun disc mean radiance", Range(0,32)) = 8
        _SunLimbDarkening("Sun limb darkening", Range(0,1)) = 1
        _SunCorona("Sun corona", Range(0,3)) = 1
        _SunTint("Sun tint multiplier", Color) = (1,1,1,1)

        [Header(Cumulus layer)]
        _CloudWind("Cloud travel direction (world XZ)", Vector) = (-1,0,0,0)
        _CloudEvolve("Cloud shape evolution", Range(0,2)) = .5
        _PlanetRadius("Layer curvature (planet radius in cloud heights)", Range(4,400)) = 50
        _CloudDetail("Billow edge detail", Range(0,1)) = .6
        _CloudAbsorption("Self-shadow absorption", Range(0,16)) = 6
        _CloudLightStep("Self-shadow march length", Range(0,1.5)) = .35
        _CloudSilver("Silver lining", Range(0,4)) = 1.2
        _CloudForward("Forward scattering g", Range(0,.9)) = .6
        _CloudBaseDarkening("Dark cloud bases", Range(0,1)) = .5
        _CloudHaze("Cloud aerial perspective", Range(0,.5)) = .15
        _CloudHorizonFade("Cloud horizon fade height", Range(.01,.3)) = .08

        [Header(Cirrus layer)]
        _CirrusCoverage("Cirrus coverage", Range(0,1)) = .5
        _CirrusScale("Cirrus scale", Range(.2,4)) = 1
        _CirrusOpacity("Cirrus opacity multiplier for Upper wisps", Range(0,8)) = 3
        _CirrusSpeed("Cirrus drift multiplier", Range(0,4)) = 1.6

        [Header(Night)]
        [Enum(KeyLight,0,OppositeSun,1,MoonDirection,2)] _MoonSource("Moon position", Float) = 0
        _MoonDirection("Direction toward moon (MoonDirection mode)", Vector) = (0,.5,-.85,0)
        _MoonSize("Moon radius", Range(.002,.05)) = .012
        _MoonColor("Moon colour", Color) = (.80,.86,1,1)
        _MoonIntensity("Moon disc radiance", Range(0,8)) = 1.2
        _MoonGlow("Moon glow", Range(0,3)) = 1
        _StarDensity("Star density", Range(0,1)) = .5
        _StarBrightness("Star brightness", Range(0,4)) = 1
        _StarTwinkle("Star twinkle", Range(0,1)) = .35
        _StarTwinkleSpeed("Star twinkle speed", Range(0,8)) = 3
        _GalaxyStrength("Galactic band", Range(0,2)) = .6
        _GalaxyPole("Galactic pole direction", Vector) = (.42,.62,-.66,0)
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
            #pragma target 3.0
            #include "UnityCG.cginc"

            sampler2D _Noise;
            float4 _Zenith, _Middle, _Horizon, _CloudLight, _CloudShade, _RidgeColor;
            float _Coverage, _CloudScale, _CloudEdge, _WispStrength, _CloudOpacity, _Exposure, _CloudSpeed;
            float _SunSize, _SunVisibility, _RidgeStrength;
            float4 _SunDirection;
            float _RayleighStrength, _MieStrength, _MieG, _HorizonDustGlow, _HorizonHaze, _GroundDarkening;
            float _SunIntensity, _SunLimbDarkening, _SunCorona;
            float4 _SunTint;
            float4 _CloudWind;
            float _CloudEvolve, _PlanetRadius, _CloudDetail, _CloudAbsorption, _CloudLightStep;
            float _CloudSilver, _CloudForward, _CloudBaseDarkening, _CloudHaze, _CloudHorizonFade;
            float _CirrusCoverage, _CirrusScale, _CirrusOpacity, _CirrusSpeed;
            float _MoonSource, _MoonSize, _MoonIntensity, _MoonGlow;
            float4 _MoonDirection, _MoonColor;
            float _StarDensity, _StarBrightness, _StarTwinkle, _StarTwinkleSpeed, _GalaxyStrength;
            float4 _GalaxyPole;
            // Set by CityAtmosphere and frozen under Reduced Motion; zero gives a static editor preview.
            float _AthenAtmosphereTime;

            // AtmosphereNoise channel statistics (RGB periodic Perlin with 16/42/91 cells per tile).
            #define NOISE_MEAN 0.466
            // Centre and spread of the cumulus shape match the previous texture FBM (mean 0.47, std 0.075,
            // measured), so _Coverage and _CloudEdge keep their tuned meaning: the same values give the same
            // sky fraction (0.53 -> ~49% covered, 0.3 -> clear, 0.7 -> ~99%).
            #define SHAPE_CENTER 0.47
            #define SHAPE_GAIN 0.75
            #define THICKNESS_SCALE 5.0
            #define STAR_GRID 150.0

            static const float2x2 kRotA = float2x2(0.80, -0.60, 0.60, 0.80);
            static const float2x2 kRotB = float2x2(-0.28, -0.96, 0.96, -0.28);
            static const float2x2 kRotC = float2x2(0.50, -0.866, 0.866, 0.50);

            struct Varyings { float4 position : SV_POSITION; float3 direction : TEXCOORD0; };

            Varyings Vert(float4 vertex : POSITION)
            {
                Varyings o;
                o.position = UnityObjectToClipPos(vertex);
                o.direction = vertex.xyz;
                return o;
            }

            // ---- Noise ------------------------------------------------------------------------
            // Sine-free hashes (Hoskins); stable on GL for the coordinate ranges used here (< ~1e3).
            float2 Hash22(float2 p)
            {
                float3 p3 = frac(p.xyx * float3(0.1031, 0.1030, 0.0973));
                p3 += dot(p3, p3.yzx + 33.33);
                return frac((p3.xx + p3.yz) * p3.zy);
            }
            float3 Hash33(float3 p3)
            {
                p3 = frac(p3 * float3(0.1031, 0.1030, 0.0973));
                p3 += dot(p3, p3.yxz + 33.33);
                return frac((p3.xxy + p3.yxx) * p3.zyx);
            }
            // Quintic gradient noise (~[-0.7,0.7], std ~0.19) with its analytic gradient in .yz (Quilez).
            // Unlike value noise it has no visible lattice blocks, and it never repeats.
            float3 GradientNoiseD(float2 p)
            {
                float2 i = floor(p), f = p - i;
                float2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
                float2 du = 30.0 * f * f * (f * (f - 2.0) + 1.0);
                float2 ga = Hash22(i) * 2.0 - 1.0;
                float2 gb = Hash22(i + float2(1, 0)) * 2.0 - 1.0;
                float2 gc = Hash22(i + float2(0, 1)) * 2.0 - 1.0;
                float2 gd = Hash22(i + 1.0) * 2.0 - 1.0;
                float va = dot(ga, f), vb = dot(gb, f - float2(1, 0)), vc = dot(gc, f - float2(0, 1)), vd = dot(gd, f - 1.0);
                float k = va - vb - vc + vd;
                float v = va + u.x * (vb - va) + u.y * (vc - va) + u.x * u.y * k;
                float2 g = ga + u.x * (gb - ga) + u.y * (gc - ga) + u.x * u.y * (ga - gb - gc + gd)
                    + du * (u.yx * k + float2(vb, vc) - va);
                return float3(v, g);
            }
            // AtmosphereNoise was made periodic by bilinearly blending four Perlin samples across each tile,
            // which halves its contrast toward the tile centre: a visible grid every 256 texels. Dividing the
            // deviation by that blend's standard-deviation factor restores uniform contrast (~8 ALU).
            float4 Destripe(float4 n, float2 uv)
            {
                float2 f = frac(uv);
                float2 w = f * f + (1.0 - f) * (1.0 - f);
                return NOISE_MEAN + (n - NOISE_MEAN) * rsqrt(w.x * w.y);
            }
            float4 NoiseTex(float2 uv) { return Destripe(tex2D(_Noise, uv), uv); }

            // Henyey-Greenstein without 1/(4 pi): its mean over the sphere is exactly 1 (energy neutral).
            float PhaseHG(float mu, float g)
            {
                float x = max(1.0 + g * g - 2.0 * g * mu, 1e-4);
                return (1.0 - g * g) / (x * sqrt(x));
            }

            // Distance from a viewer on the ground to a spherical shell `height` above a planet of radius R,
            // both in cumulus-base heights. Stable (no cancellation) form of -R mu + sqrt(R^2 mu^2 + 2Rh + h^2).
            float ShellDistance(float mu, float height, float R)
            {
                float b = R * mu, c = 2.0 * R * height + height * height;
                return c / (b + sqrt(b * b + c));
            }

            half4 Frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.direction);
                float h = max(d.y, 0.0);
                float pixelAngle = length(fwidth(d)) * 0.7;                   // radians per pixel

                float3 sunDir = normalize(_SunDirection.xyz + float3(0, 1e-5, 0));
                float sunVis = saturate(_SunVisibility);
                // KeyLight: the profile turns the key light into moonlight at night, so the moon sits where
                // the night key light comes from (matches shadows). The other modes are for other profiles.
                float3 moonDir = _MoonSource < 0.5 ? sunDir
                    : (_MoonSource < 1.5 ? -sunDir : normalize(_MoonDirection.xyz + float3(0, 1e-5, 0)));
                float moonVis = saturate(1.0 - sunVis * 2.5);                 // only once the sun has mostly faded
                // Light for clouds and Rayleigh: the sun by day, the moon by night, continuous in between.
                float3 L = normalize(sunDir * sunVis + moonDir * (1.0 - sunVis) + float3(0, 1e-4, 0));
                float muL = dot(d, L);
                float muS = dot(d, sunDir);
                float3 cl = max(_CloudLight.rgb, 1e-4);
                // Attenuated sunlight colour: the profile's sunlit-cloud colour, normalised to peak 1 and
                // desaturated 30% (a bright disc reads whiter than the light it casts, as a camera sees it).
                float3 sunTint = lerp(cl / max(max(cl.r, cl.g), cl.b), 1.0, 0.3) * _SunTint.rgb;

                // ---- Atmosphere --------------------------------------------------------------------
                // Profile palette, shaped like optical depth: the horizon colour decays exponentially with
                // elevation (no flat smoothstep band), then blends to the zenith exactly as before.
                float3 sky = lerp(_Horizon.rgb, _Middle.rgb, 1.0 - exp(-h * 7.0));
                sky = lerp(sky, _Zenith.rgb, pow(h, 0.65));
                // Rayleigh phase 3/4(1+mu^2): brighter toward/away from the light, darker 90 degrees off it.
                sky *= lerp(1.0, 0.75 * (1.0 + muL * muL), _RayleighStrength);
                // Warm dusty extinction: at low sun the sunward horizon brightens and the anti-solar side
                // cools. (az^2 - 0.375) has zero azimuthal mean, so this moves light without adding any.
                float2 dh = normalize(d.xz + float2(1e-5, 0));
                float2 sh = normalize(sunDir.xz + float2(1e-5, 0));
                float az = dot(dh, sh) * 0.5 + 0.5;
                float lowSun = 1.0 - smoothstep(0.05, 0.45, sunDir.y);
                sky *= 1.0 + _HorizonDustGlow * 0.8 * sunVis * lowSun * exp(-h * 5.0) * (az * az - 0.375);
                // Mie aureole: HG forward lobe of the attenuated sunlight, stronger through the dusty low sky.
                sky += _CloudLight.rgb * (PhaseHG(muS, _MieG) * 0.012 * _MieStrength * sunVis * (0.55 + 0.9 * exp(-h * 2.5)));
                // Thin bright haze straddling the horizon; continues below it for elevated cameras.
                sky = lerp(sky, _Horizon.rgb * 1.06, exp(-abs(d.y) * 38.0) * _HorizonHaze * 0.5);
                float skyLum = dot(sky, float3(0.2126, 0.7152, 0.0722));

                // ---- Sun ---------------------------------------------------------------------------
                float3 discs = 0;                                              // occluded by clouds
                float3 glow = 0;                                               // partly scatters through them
                UNITY_BRANCH
                if (sunVis > 0.001)
                {
                    float sunAngle = length(d - sunDir);                       // chord == angle near the sun
                    float sunR = sunAngle / _SunSize;
                    float sunEdge = saturate((1.0 - sunR) * _SunSize / max(pixelAngle, 1e-5) + 0.5);
                    // Limb darkening I(mu) = mu^alpha per channel (redder limb); divided by the disc mean
                    // 2/(alpha+2) so _SunIntensity stays the mean radiance.
                    float3 alpha = float3(0.397, 0.503, 0.652) * _SunLimbDarkening;
                    float3 limb = pow(max(sqrt(saturate(1.0 - sunR * sunR)), 1e-4), alpha) * (alpha + 2.0) * 0.5;
                    float extinction = lerp(0.35, 1.0, smoothstep(-0.01, 0.12, d.y));
                    discs += sunTint * (_SunIntensity * sunEdge * sunVis * extinction) * limb;
                    float outside = max(sunAngle - _SunSize, 0.0);
                    glow += sunTint * (_SunCorona * sunVis * (0.28 * exp(-sunAngle * 18.0)
                        + 1.5 * exp(-outside * 3.0 / _SunSize) * (1.0 - sunEdge)));
                }

                // ---- Night: stars, galactic band, moon ------------------------------------------------
                float3 space = 0;                                              // behind everything
                UNITY_BRANCH
                if (sunVis < 0.999)
                {
                    float night = 1.0 - sunVis;
                    // Stars fade as the local sky brightens (twilight glow, moon-lit horizon) and near the
                    // horizon where extinction and haze are strongest.
                    float nightVis = night * saturate(1.0 - skyLum * 30.0) * saturate(d.y * 6.0);

                    float3 gp = normalize(_GalaxyPole.xyz + float3(0, 1e-5, 0));
                    float gz = dot(d, gp);
                    float band = exp(-gz * gz * 28.0);
                    float3 gu = normalize(cross(gp, abs(gp.y) < 0.99 ? float3(0, 1, 0) : float3(1, 0, 0)));
                    float gx = dot(d, gu), gy = dot(d, cross(gp, gu));
                    // Two planar projections that both contain the pole, each weighted where it is not
                    // degenerate, so the texture is never smeared across the band. The sign offset de-mirrors
                    // the far side and flips exactly where that projection's weight is zero.
                    float4 gA = tex2Dlod(_Noise, float4(float2(gx, gz) * 1.2 + (gy > 0.0 ? 0.31 : 0.63), 0, 0));
                    float4 gB = tex2Dlod(_Noise, float4(float2(gy, gz) * 1.2 + (gx > 0.0 ? 0.17 : 0.49), 0, 0));
                    float4 gn = lerp(gB, gA, gy * gy / max(gx * gx + gy * gy, 1e-4));
                    float core = exp(-gz * gz * 140.0);
                    float clumps = saturate(0.4 + (gn.r - NOISE_MEAN) * 2.6 + (gn.g - NOISE_MEAN) * 1.6);
                    float lanes = 1.0 - 0.75 * core * saturate((gn.b - 0.42) * 3.5);
                    space += lerp(float3(0.55, 0.62, 0.85), float3(1.0, 0.9, 0.78), core)
                        * (band * clumps * lanes * 0.035 * _GalaxyStrength);

                    // Hashed stars on a 3D grid: one candidate per cell, accepted only if it projects back
                    // into its own cell (no clipping at cell faces). Gaussian footprint of at least ~0.8 px,
                    // energy-normalised so stars keep their brightness when minified (probes, low res).
                    float3 cell = floor(d * STAR_GRID);
                    float3 jitter = Hash33(cell);
                    float3 rnd = Hash33(cell + 71.13);
                    float3 starDir = normalize(cell + 0.25 + 0.5 * jitter);
                    float inCell = all(floor(starDir * STAR_GRID) == cell) ? 1.0 : 0.0;
                    float exists = step(rnd.x, _StarDensity * 0.09 * (1.0 + 2.5 * band)) * inCell;
                    float sigma = max(0.00045, pixelAngle * 0.55);
                    float sd = length(d - starDir);
                    float mag = rnd.y * rnd.y; mag *= mag;                     // many faint, few bright
                    float twinkle = 1.0 + _StarTwinkle * lerp(0.35, 1.0, 1.0 - h)
                        * sin(_AthenAtmosphereTime * _StarTwinkleSpeed * (0.6 + rnd.z) + rnd.z * 43.0);
                    float starI = _StarBrightness * (0.04 + 1.6 * mag) * twinkle * exists
                        * exp(-sd * sd / (2.0 * sigma * sigma)) * (0.00045 * 0.00045) / (sigma * sigma);
                    space += lerp(float3(0.72, 0.82, 1.0), float3(1.0, 0.86, 0.66), frac(rnd.z * 7.31)) * starI;
                    space *= nightVis;

                    // Moon: full disc with texture maria, almost no limb darkening, phase-independent glow.
                    float moonAngle = length(d - moonDir);
                    float mr = moonAngle / _MoonSize;
                    float moonEdge = saturate((1.0 - mr) * _MoonSize / max(pixelAngle, 1e-5) + 0.5);
                    float3 mRight = normalize(cross(float3(0, 1, 0), moonDir) + float3(1e-5, 0, 0));
                    float2 mUV = float2(dot(d, mRight), dot(d, cross(moonDir, mRight))) / _MoonSize;
                    float maria = tex2Dlod(_Noise, float4(mUV * 0.11 + float2(0.37, 0.61), 0, 1)).r;
                    float craters = tex2Dlod(_Noise, float4(mUV * 0.09 + float2(0.13, 0.29), 0, 1)).g;
                    float albedo = lerp(0.55, 1.0, smoothstep(0.38, 0.56, maria)) * lerp(0.85, 1.05, craters);
                    float moonLimb = pow(max(sqrt(saturate(1.0 - mr * mr)), 1e-3), 0.3);
                    discs += _MoonColor.rgb * (_MoonIntensity * albedo * moonLimb * moonEdge * moonVis);
                    glow += _MoonColor.rgb * (_MoonGlow * moonVis * (0.05 * exp(-moonAngle * 22.0) + 0.012 * exp(-moonAngle * 4.0)));
                }

                // ---- Cumulus layer on a curved shell ---------------------------------------------------
                // Below the horizon reuse the horizon hit (masked later) so derivatives stay finite.
                float muC = h;
                float tLow = ShellDistance(muC, 1.0, _PlanetRadius);            // 1 at zenith, ~10 at horizon (R 50)
                float2 windDir = normalize(_CloudWind.xz + float2(1e-5, 0));
                float drift = _AthenAtmosphereTime * _CloudSpeed;               // noise cells; 0 = frozen
                float evolve = drift * _CloudEvolve;
                // 0.85 keeps the zenith feature size of the previous shaders for the same _CloudScale.
                float2 uv = d.xz * (tLow * _CloudScale * 0.85) - windDir * drift;
                float2 duvx = ddx(uv), duvy = ddy(uv);
                float footprint = sqrt(max(dot(duvx, duvx), dot(duvy, duvy)));   // noise cells per pixel
                // Gentle domain warp from two destriped R lookups (16 texels per noise cell, so bilinear
                // magnification stays smooth; ~3-cell period, ~0.17-cell std): organic edges, no swirls.
                float2 warp = float2(
                    NoiseTex(uv * 0.021 + float2(0.43, 0.11) + evolve * float2(0.004, -0.003)).r,
                    NoiseTex(mul(kRotC, uv) * 0.021 + float2(0.77, 0.29) - evolve * float2(0.003, 0.004)).r) - NOISE_MEAN;
                float2 q = uv + warp;
                // FBM: an ALU gradient-noise base octave sets the cloud masses and never repeats; three
                // destriped, rotated texture octaves at non-commensurate scales (2.03, 4.3, 9.1 cells) add
                // the breakup. Texture mips band-limit them toward the horizon.
                float3 gn = GradientNoiseD(q);
                float o2 = NoiseTex(mul(kRotA, q) * 0.126875 + float2(0.21, 0.67)).r - NOISE_MEAN;
                float o3 = NoiseTex(mul(kRotB, q) * 0.1024 + float2(0.17, 0.53) + evolve * float2(0.012, -0.008)).g - NOISE_MEAN;
                float o4 = NoiseTex(mul(kRotC, q) * 0.1 + float2(0.71, 0.29) - evolve * float2(0.006, 0.011)).b - NOISE_MEAN;
                float detail = _CloudDetail * 1.6667;                           // 1.0 at the calibrated default
                float shape = SHAPE_CENTER + SHAPE_GAIN * (gn.x * 0.45 + o2 * 0.27 + (o3 * 0.14 + o4 * 0.07) * detail);
                float2 shapeGrad = gn.yz * (0.45 * SHAPE_GAIN);
                float thr = 1.0 - _Coverage;
                float density = shape - thr;                                    // > 0 inside the cloud
                float cloudA = smoothstep(-_CloudEdge, _CloudEdge, density);
                // When the base octave approaches Nyquist near the horizon, converge on the expected cover.
                float farBlend = saturate(footprint * 2.2 - 0.35);
                cloudA = lerp(cloudA, saturate(0.5 + (_Coverage - 0.53) * 5.3), farBlend);
                cloudA *= _CloudOpacity * smoothstep(0.0, _CloudHorizonFade, d.y);
                float thickness = saturate(density * THICKNESS_SCALE);

                // Self-shadowing toward the light, gradient-based: extrapolate the density 0.5 and 1.5 march
                // steps along the light's horizontal direction with the base octave's analytic gradient and
                // accumulate optical depth (Beer). In CPU tests this matched a real two-sample march closely
                // at a fraction of the cost (no extra noise evaluations or fetches). Low light = longer steps.
                float2 lDir = normalize(L.xz + float2(1e-5, 0));
                float slant = clamp(length(L.xz) / max(abs(L.y), 0.05), 0.3, 3.0);
                float slope = dot(shapeGrad, lDir) * (slant * _CloudLightStep);  // density change per step
                float opticalDepth = max(density, 0.0) * 0.5 + max(density + slope * 0.5, 0.0) * 0.6
                    + max(density + slope * 1.5, 0.0) * 0.5;
                float beer = exp(-opticalDepth * _CloudAbsorption);
                float thin = 1.0 - thickness;
                // Overhead we see flat, self-shadowed bases; toward the horizon, the lit flanks.
                float lit = beer * (1.0 - _CloudBaseDarkening * thickness * lerp(0.35, 1.0, saturate(h * 1.8)));
                lit *= lerp(1.1, 0.8, saturate(muL) * thickness);              // backlit cores are darker
                float3 cloudCol = lerp(_CloudShade.rgb, _CloudLight.rgb, saturate(lit));
                // Silver lining: thin edges forward-scatter toward the light (HDR near the sun, bloom source).
                cloudCol += _CloudLight.rgb * (_CloudSilver * 0.1 * PhaseHG(muL, _CloudForward) * thin * thin * beer);
                cloudCol = lerp(cloudCol, sky, 1.0 - exp(-max(tLow - 1.0, 0.0) * _CloudHaze));

                // ---- Cirrus: higher, thinner, less foreshortened, streaked along a veered wind ----------
                float tHigh = ShellDistance(muC, 4.0, _PlanetRadius) * 0.25;   // 1 at zenith, ~5 at horizon (R 50)
                float2 cWind = float2(windDir.x * 0.94 - windDir.y * 0.34, windDir.x * 0.34 + windDir.y * 0.94);
                float2 cpos = d.xz * (tHigh * _CirrusScale * 1.6) - cWind * (drift * _CirrusSpeed);
                float2 sf = float2(dot(cpos, cWind), dot(cpos, float2(-cWind.y, cWind.x)));   // along, across
                float patches = NoiseTex(sf * float2(0.012, 0.03) + float2(0.61, evolve * 0.004)).r - NOISE_MEAN;
                float2 sw = sf + float2(0.3, 2.2) * patches;                    // wavy fibres
                float f1 = NoiseTex(sw * float2(0.055, 0.328) + float2(0.07, 0.41)).r - NOISE_MEAN;
                float f2 = NoiseTex(mul(kRotC, sw * float2(0.35, 1.0)) * 0.11 + float2(0.83, 0.19)).b - NOISE_MEAN;
                float cirrus = saturate((0.5 + patches * 2.6 - (1.0 - _CirrusCoverage)) * 2.5)
                    * saturate((0.15 + f1 * 1.6 + f2 * 0.9) * 2.0);
                float cirrusA = saturate(cirrus * _WispStrength * _CirrusOpacity) * smoothstep(0.0, 0.2, d.y);
                float3 cirrusCol = lerp(sky, _CloudLight.rgb, 0.85)
                    + _CloudLight.rgb * (_CloudSilver * 0.05 * PhaseHG(muL, 0.75));
                cirrusCol = lerp(cirrusCol, sky, 1.0 - exp(-max(tHigh - 1.0, 0.0) * _CloudHaze * 1.5));

                // ---- Composite ---------------------------------------------------------------------
                // _CloudOpacity lets sky colour through cloud, but point sources should not shine through
                // thick cores: stars vanish and the sun/moon discs drop to a glow behind geometric cover.
                float cover = saturate(cloudA / max(_CloudOpacity, 1e-3));
                float3 col = sky + space * (1.0 - cover);
                col = lerp(col, cirrusCol, cirrusA);
                col += discs * ((1.0 - cirrusA * 0.5) * (1.0 - cover * 0.9));
                col = lerp(col, cloudCol, cloudA);
                col += glow * (1.0 - cloudA * 0.65);

                // Below the horizon: continuous haze first, then a subtle ground tint (elevated cameras,
                // reflection probes). Ordered smoothstep edges for GLSL portability.
                col = lerp(col, _Horizon.rgb, 1.0 - smoothstep(-0.035, 0.0, d.y));
                col = lerp(col, lerp(_Horizon.rgb, _RidgeColor.rgb, 0.55), (1.0 - smoothstep(-0.3, -0.02, d.y)) * _GroundDarkening);

                // ---- Optional distant ridges (disabled in the scene materials, which use ridge meshes) --
                UNITY_BRANCH
                if (_RidgeStrength > 0.001)
                {
                    float2 bearing = dh;
                    // Same silhouettes as the previous shaders (Noise(bearing*6.5+23), Noise(bearing*10.3-17)),
                    // plus crest detail; the far range hazes toward its base, the near one keeps colour and a
                    // sunward rim, so the two read as separate distances instead of one flat band.
                    float farN = saturate(tex2Dlod(_Noise, float4(bearing * 0.40625 + 1.4375, 0, 0)).r);
                    float nearN = tex2Dlod(_Noise, float4(bearing * 0.64375 - 1.0625, 0, 0)).r;
                    float4 crest = tex2Dlod(_Noise, float4(bearing * 0.9 + 0.3, 0, 0));
                    float farH = 0.008 + farN * farN * 0.11 + (crest.b - NOISE_MEAN) * 0.006;
                    float nearH = -0.015 + nearN * 0.055 + (crest.g - NOISE_MEAN) * 0.004;
                    float aa = max(pixelAngle, 0.0008);
                    float farM = 1.0 - smoothstep(farH - aa, farH + aa, d.y);
                    float nearM = 1.0 - smoothstep(nearH - aa, nearH + aa, d.y);
                    float sunSide = saturate(dot(bearing, sh)) * sunVis;
                    float3 farCol = lerp(_Horizon.rgb, _RidgeColor.rgb, 0.45 + 0.25 * saturate(d.y / max(farH, 1e-3)));
                    float3 nearCol = _RidgeColor.rgb * lerp(0.8, 1.0, saturate((d.y - nearH) / 0.01 + 1.0));
                    col = lerp(col, farCol * (1.0 + 0.12 * sunSide), farM * _RidgeStrength);
                    col = lerp(col, nearCol * (1.0 + 0.2 * sunSide), nearM * _RidgeStrength * 0.75);
                }

                return half4(col * _Exposure, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
