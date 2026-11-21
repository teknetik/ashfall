using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    /// <summary>
    /// Edit Mode tests for Outer Berms wasteland danger atmosphere math, Tier-3 territory warnings,
    /// Reduced Motion safety, and collision-checked placements/hazard FX data (21 Nov 2026).
    /// </summary>
    public class BermsDangerTests
    {
        [Test]
        public void DepthFactorIsZeroInsideWardAndRampsWestward()
        {
            Assert.That(BermsDangerMath.DepthFactor(-20f), Is.EqualTo(0f));
            Assert.That(BermsDangerMath.DepthFactor(-58.3f), Is.EqualTo(0f));
            float shallow = BermsDangerMath.DepthFactor(-140f);
            float mid = BermsDangerMath.DepthFactor(-260f);
            float deep = BermsDangerMath.DepthFactor(-460f);
            float beyond = BermsDangerMath.DepthFactor(-540f);

            Assert.That(shallow, Is.GreaterThan(0f).And.LessThan(mid));
            Assert.That(mid, Is.LessThan(deep));
            Assert.That(deep, Is.EqualTo(1f).Within(1e-4f));
            Assert.That(beyond, Is.EqualTo(1f).Within(1e-4f));
        }

        [Test]
        public void DroidProximityPressureScalesWithDistancePackAndDangerTier()
        {
            Assert.That(BermsDangerMath.DroidProximityPressure(80f, true, 3), Is.EqualTo(0f));
            Assert.That(BermsDangerMath.DroidProximityPressure(10f, false, 0), Is.EqualTo(0f));

            float farNormal = BermsDangerMath.DroidProximityPressure(45f, false, 1);
            float closeNormal = BermsDangerMath.DroidProximityPressure(12f, false, 1);
            float closePack = BermsDangerMath.DroidProximityPressure(12f, false, 4);
            float closeDanger = BermsDangerMath.DroidProximityPressure(12f, true, 4);

            Assert.That(farNormal, Is.GreaterThan(0f).And.LessThan(closeNormal));
            Assert.That(closePack, Is.GreaterThan(closeNormal));
            Assert.That(closeDanger, Is.GreaterThan(closePack).And.LessThanOrEqualTo(1f));
        }

        [Test]
        public void ThreatLevelCombinesDepthDroidsAndTier3Territory()
        {
            // Inside Ward is always 0 regardless of nearby droids
            Assert.That(BermsDangerMath.ThreatLevel(-40f, -58.3f, -460f, 5f, true, 3, true), Is.EqualTo(0f));

            float shallowQuiet = BermsDangerMath.ThreatLevel(-120f, -58.3f, -460f, float.PositiveInfinity, false, 0, false);
            float deepQuiet = BermsDangerMath.ThreatLevel(-420f, -58.3f, -460f, float.PositiveInfinity, false, 0, false);
            float deepTier3 = BermsDangerMath.ThreatLevel(-420f, -58.3f, -460f, float.PositiveInfinity, false, 0, true);
            float deepTier3Hostile = BermsDangerMath.ThreatLevel(-420f, -58.3f, -460f, 15f, true, 3, true);

            Assert.That(shallowQuiet, Is.GreaterThan(0f).And.LessThan(deepQuiet));
            Assert.That(deepTier3, Is.GreaterThan(deepQuiet));
            Assert.That(deepTier3Hostile, Is.GreaterThan(deepTier3).And.LessThanOrEqualTo(1f));
        }

        [Test]
        public void AshEmissionRateRespectsBermsBoundaryAndReducedMotion()
        {
            Assert.That(BermsDangerMath.AshEmissionRate(0.9f, false, false), Is.EqualTo(0f));
            Assert.That(BermsDangerMath.AshEmissionRate(0.01f, true, false), Is.EqualTo(0f));

            float normal = BermsDangerMath.AshEmissionRate(0.85f, true, false, 18f);
            float reduced = BermsDangerMath.AshEmissionRate(0.85f, true, true, 18f);

            Assert.That(normal, Is.GreaterThan(10f));
            Assert.That(reduced, Is.GreaterThan(0f).And.LessThanOrEqualTo(3f));
            Assert.That(reduced, Is.LessThan(normal * 0.35f));
        }

        [Test]
        public void CrackleIntervalShortensAsThreatRises()
        {
            float calm = BermsDangerMath.CrackleInterval(0f, 6f, 22f);
            float mid = BermsDangerMath.CrackleInterval(0.5f, 6f, 22f);
            float high = BermsDangerMath.CrackleInterval(1f, 6f, 22f);

            Assert.That(calm, Is.EqualTo(22f).Within(1e-4f));
            Assert.That(mid, Is.EqualTo(14f).Within(1e-4f));
            Assert.That(high, Is.EqualTo(6f).Within(1e-4f));
        }

        [Test]
        public void DangerZonesDetectTier3TerritoriesAndEnforceCooldown()
        {
            var zones = BermsDangerMath.DefaultTier3Zones();
            Assert.That(zones.Length, Is.GreaterThanOrEqualTo(3));

            int reaperIdx = BermsDangerMath.FindDangerZoneIndex(new Vector3(-240f, 0f, 140f), zones);
            int relayIdx = BermsDangerMath.FindDangerZoneIndex(new Vector3(-430f, 4f, 20f), zones);
            int fansIdx = BermsDangerMath.FindDangerZoneIndex(new Vector3(-490f, 5f, -105f), zones);
            int outsideIdx = BermsDangerMath.FindDangerZoneIndex(new Vector3(-120f, 0f, 0f), zones);

            Assert.That(reaperIdx, Is.GreaterThanOrEqualTo(0));
            Assert.That(zones[reaperIdx].id, Is.EqualTo("reaper_den"));
            Assert.That(relayIdx, Is.GreaterThanOrEqualTo(0));
            Assert.That(zones[relayIdx].id, Is.EqualTo("post_relay"));
            Assert.That(fansIdx, Is.GreaterThanOrEqualTo(0));
            Assert.That(zones[fansIdx].id, Is.EqualTo("fans_camp"));
            Assert.That(outsideIdx, Is.EqualTo(-1));

            // Entry triggers once, staying inside does not re-trigger, rapid re-entry respects cooldown
            Assert.That(BermsDangerMath.ShouldWarnZoneEntry(reaperIdx, -1, 100f, -9999f, 90f), Is.True);
            Assert.That(BermsDangerMath.ShouldWarnZoneEntry(reaperIdx, reaperIdx, 105f, 100f, 90f), Is.False);
            Assert.That(BermsDangerMath.ShouldWarnZoneEntry(reaperIdx, -1, 150f, 100f, 90f), Is.False);
            Assert.That(BermsDangerMath.ShouldWarnZoneEntry(reaperIdx, -1, 195f, 100f, 90f), Is.True);
        }

        [Test]
        public void PlacementsJsonHasValidPrefabsAndHazardTags()
        {
            string placementsPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../art/berms_density_20261121/placements.json"));
            Assert.That(File.Exists(placementsPath), Is.True, "placements.json missing at " + placementsPath);

            var doc = JObject.Parse(File.ReadAllText(placementsPath));
            var prefabs = (JArray)doc["prefabs"];
            Assert.That(prefabs, Is.Not.Null);
            Assert.That(prefabs.Count, Is.GreaterThanOrEqualTo(250), "expected expanded wasteland density placements");

            int arcCount = prefabs.Count(p => (string)p["hazard"] == "arc");
            int smokeCount = prefabs.Count(p => (string)p["hazard"] == "smoke");
            Assert.That(arcCount, Is.GreaterThanOrEqualTo(10), "expected tagged arc hazards");
            Assert.That(smokeCount, Is.GreaterThanOrEqualTo(10), "expected tagged smoke hazards");

            string prefabRoot = Path.Combine(Application.dataPath, "AthenHill/Prefabs");
            var missing = prefabs
                .Select(p => (string)p["prefab"])
                .Distinct()
                .Where(rel => !File.Exists(Path.Combine(prefabRoot, rel + ".prefab")))
                .ToArray();
            Assert.That(missing, Is.Empty, "Missing prefabs on disk: " + string.Join(", ", missing));
        }
    }
}
