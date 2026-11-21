using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Tests
{
    public class WastelandAtmosphereTests
    {
        [Test]
        public void BermsWeightIsZeroInsideWardAndSmoothlyRampsWestOfWall()
        {
            const float edge = WastelandAtmosphere.DefaultCityEdgeX;
            const float blend = WastelandAtmosphere.DefaultBlendMetres;

            // Anywhere inside Ward (at or east of the wall) must be exact 0.
            Assert.That(WastelandAtmosphere.BermsWeight(40f, edge, blend), Is.EqualTo(0f));
            Assert.That(WastelandAtmosphere.BermsWeight(0f, edge, blend), Is.EqualTo(0f));
            Assert.That(WastelandAtmosphere.BermsWeight(edge, edge, blend), Is.EqualTo(0f));

            // Smooth monotonic ramp west of the wall.
            float quarter = WastelandAtmosphere.BermsWeight(edge - blend * 0.25f, edge, blend);
            float half = WastelandAtmosphere.BermsWeight(edge - blend * 0.5f, edge, blend);
            float threeQuarter = WastelandAtmosphere.BermsWeight(edge - blend * 0.75f, edge, blend);
            float full = WastelandAtmosphere.BermsWeight(edge - blend, edge, blend);
            float far = WastelandAtmosphere.BermsWeight(edge - blend * 5f, edge, blend);

            Assert.That(quarter, Is.GreaterThan(0f).And.LessThan(half));
            Assert.That(half, Is.EqualTo(0.5f).Within(1e-4f));
            Assert.That(threeQuarter, Is.GreaterThan(half).And.LessThan(1f));
            Assert.That(full, Is.EqualTo(1f).Within(1e-5f));
            Assert.That(far, Is.EqualTo(1f));
        }

        [Test]
        public void BermsWeightHandlesEdgeAndNonFiniteInputsSafely()
        {
            Assert.That(WastelandAtmosphere.BermsWeight(float.NaN), Is.EqualTo(0f));
            Assert.That(WastelandAtmosphere.BermsWeight(float.PositiveInfinity), Is.EqualTo(0f));
            Assert.That(WastelandAtmosphere.BermsWeight(float.NegativeInfinity), Is.EqualTo(0f));
            Assert.That(WastelandAtmosphere.BermsWeight(-60f, float.NaN), Is.EqualTo(0f));

            // Zero or negative blendMetres degrades to a clean step at cityEdgeX.
            Assert.That(WastelandAtmosphere.BermsWeight(-58.3f, -58.3f, 0f), Is.EqualTo(0f));
            Assert.That(WastelandAtmosphere.BermsWeight(-58.31f, -58.3f, 0f), Is.EqualTo(1f));
            Assert.That(WastelandAtmosphere.BermsWeight(-60f, -58.3f, -5f), Is.EqualTo(1f));
        }

        [Test]
        public void ApplyToFrameLeavesWardAuthoredLightingUntouchedAtZeroWeight()
        {
            var authored = new DayNightFrame
            {
                hour = 17f,
                keyEuler = new Vector3(11f, 230f, 0f),
                keyColor = new Color(1f, 0.62f, 0.34f, 1f),
                keyIntensity = 1.65f,
                fillColor = new Color(0.52f, 0.66f, 0.94f, 1f),
                fillIntensity = 0.13f,
                ambientSky = new Color(0.21f, 0.28f, 0.43f, 1f),
                ambientEquator = new Color(0.24f, 0.19f, 0.15f, 1f),
                ambientGround = new Color(0.12f, 0.095f, 0.075f, 1f),
                skyHorizon = new Color(0.84f, 0.42f, 0.19f, 1f),
                skyMiddle = new Color(0.42f, 0.34f, 0.37f, 1f),
                fogColor = new Color(0.44f, 0.31f, 0.22f, 1f),
                sunVisibility = 1f,
                postExposure = -0.2f
            };

            var inWard = WastelandAtmosphere.ApplyToFrame(authored, 0f);
            Assert.That(inWard.keyIntensity, Is.EqualTo(authored.keyIntensity));
            Assert.That(inWard.fillIntensity, Is.EqualTo(authored.fillIntensity));
            Assert.That(inWard.ambientSky, Is.EqualTo(authored.ambientSky));
            Assert.That(inWard.ambientEquator, Is.EqualTo(authored.ambientEquator));
            Assert.That(inWard.ambientGround, Is.EqualTo(authored.ambientGround));
            Assert.That(inWard.fogColor, Is.EqualTo(authored.fogColor));
            Assert.That(inWard.postExposure, Is.EqualTo(authored.postExposure));

            var inBerms = WastelandAtmosphere.ApplyToFrame(authored, 1f);
            Assert.That(inBerms.keyIntensity, Is.GreaterThan(authored.keyIntensity));
            Assert.That(inBerms.fillIntensity, Is.LessThan(authored.fillIntensity));
            Assert.That(inBerms.ambientGround.r, Is.LessThan(authored.ambientGround.r));
            Assert.That(inBerms.postExposure, Is.LessThan(authored.postExposure));
            Assert.That(inBerms.ambientSky.r, Is.GreaterThanOrEqualTo(0f));
            Assert.That(inBerms.fogColor.b, Is.GreaterThanOrEqualTo(0f));
        }

        [Test]
        public void MultipliersAndEasingRespectReducedMotion()
        {
            Assert.That(WastelandAtmosphere.DustEmissionMultiplier(0f, false), Is.EqualTo(1f));
            Assert.That(WastelandAtmosphere.WindRateMultiplier(0f, false), Is.EqualTo(1f));
            Assert.That(WastelandAtmosphere.HazeMultiplier(0f), Is.EqualTo(1f));

            // Normal mode intensifies dust, wind, and haze in the Outer Berms.
            Assert.That(WastelandAtmosphere.DustEmissionMultiplier(1f, false), Is.GreaterThan(1.8f));
            Assert.That(WastelandAtmosphere.WindRateMultiplier(1f, false), Is.GreaterThan(1.2f));
            Assert.That(WastelandAtmosphere.HazeMultiplier(1f), Is.GreaterThan(1.3f));

            // Reduced Motion disables motion/particle intensification and eases transitions more slowly.
            Assert.That(WastelandAtmosphere.DustEmissionMultiplier(1f, true), Is.EqualTo(1f));
            Assert.That(WastelandAtmosphere.WindRateMultiplier(1f, true), Is.EqualTo(1f));
            float normalStep = WastelandAtmosphere.SmoothWeight(0f, 1f, 0.25f, false);
            float reducedStep = WastelandAtmosphere.SmoothWeight(0f, 1f, 0.25f, true);
            Assert.That(reducedStep, Is.GreaterThan(0f).And.LessThan(normalStep));
        }

        [Test]
        public void AtmosphereAssetsAreValidAndTunedForHighContrastWasteland()
        {
            var profile = AssetDatabase.LoadAssetAtPath<DayNightLightingProfile>(
                "Assets/AthenHill/Art/Atmosphere/Dustbowl/WardDustbowl.asset");
            Assert.That(profile, Is.Not.Null);
            Assert.That(profile.IsValid(out string reason), Is.True, reason);

            var noon = profile.Evaluate(12f);
            Assert.That(noon.keyIntensity, Is.GreaterThanOrEqualTo(2.2f));
            Assert.That(noon.fillColor.b, Is.GreaterThan(noon.fillColor.r), "cool shadow fill at noon");

            var golden = profile.Evaluate(17f);
            Assert.That(golden.keyColor.r, Is.GreaterThan(golden.keyColor.b), "warm sun key at golden hour");
            Assert.That(golden.fillColor.b, Is.GreaterThan(golden.fillColor.r), "cool shadow fill at golden hour");

            var grade = AssetDatabase.LoadAssetAtPath<VolumeProfile>(
                "Assets/AthenHill/Art/Atmosphere/Dustbowl/WardDustbowlGrade.asset");
            Assert.That(grade, Is.Not.Null);
            Assert.That(grade.TryGet(out Tonemapping tm), Is.True);
            Assert.That(tm.mode.value, Is.EqualTo(TonemappingMode.ACES));
            Assert.That(grade.TryGet(out ColorAdjustments ca), Is.True);
            Assert.That(ca.contrast.value, Is.GreaterThanOrEqualTo(20f));

            var sky = AssetDatabase.LoadAssetAtPath<Material>(
                "Assets/AthenHill/Materials/Sky/WardSkyV2.mat");
            Assert.That(sky, Is.Not.Null);
            Assert.That(sky.GetFloat("_RayleighStrength"), Is.InRange(0.4f, 0.8f));
            Assert.That(sky.GetFloat("_HorizonDustGlow"), Is.InRange(0.65f, 1f));
            Assert.That(sky.GetFloat("_HorizonHaze"), Is.InRange(0.55f, 0.9f));
        }
    }
}
