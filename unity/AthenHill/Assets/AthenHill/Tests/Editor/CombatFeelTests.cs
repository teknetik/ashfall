using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Tests
{
    /// 19 Nov 2026 combat feel pass: weak-point ray maths and damage, the hit marker state, the camera impulse's trauma,
    /// the low-vitality warning, critical staggers and the weak-point balance rule against the saved prefabs.
    public class CombatFeelTests
    {
        [TearDown]
        public void Clean()
        {
            foreach (var h in Object.FindObjectsByType<Health>(FindObjectsInactive.Include)) Object.DestroyImmediate(h.gameObject);
            foreach (var w in Object.FindObjectsByType<DroidWeakPoint>(FindObjectsInactive.Include)) if (w) Object.DestroyImmediate(w.gameObject);
        }

        [Test]
        public void RayEntersSphereAtTheNearSurface()
        {
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward, new Vector3(0, 0, 10), .5f, 20, out float d), Is.True);
            Assert.That(d, Is.EqualTo(9.5f).Within(1e-4f));
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward * 7, new Vector3(0, 0, 10), .5f, 20, out d), Is.True, "direction need not be normalised");
            Assert.That(d, Is.EqualTo(9.5f).Within(1e-4f));
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward, new Vector3(.49f, 0, 10), .5f, 20, out _), Is.True, "grazing inside the radius");
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward, new Vector3(.51f, 0, 10), .5f, 20, out _), Is.False, "just outside the radius");
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward, new Vector3(0, 0, -10), .5f, 20, out _), Is.False, "behind the origin");
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward, new Vector3(0, 0, .2f), .5f, 20, out d), Is.True, "starting inside");
            Assert.That(d, Is.Zero);
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward, new Vector3(0, 0, 10), .5f, 9.4f, out _), Is.False, "beyond the reach");
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.forward, new Vector3(0, 0, 10), 0, 20, out _), Is.False);
            Assert.That(WeakPointMath.RayHitsSphere(Vector3.zero, Vector3.zero, new Vector3(0, 0, 10), .5f, 20, out _), Is.False);
        }

        [Test]
        public void WeakPointMultipliesWhatArmourLeaves()
        {
            Assert.That(WeakPointMath.AfterArmour(20, 1.25f), Is.EqualTo(25).Within(1e-4f));
            Assert.That(WeakPointMath.AfterArmour(20, .5f), Is.EqualTo(20), "never below 1×");
            Assert.That(WeakPointMath.AfterArmour(-3, 2), Is.Zero);
            Assert.That(WeakPointMath.ChargeDamage(11, 20, 1.25f, 0), Is.EqualTo(220).Within(1e-3f));
            Assert.That(WeakPointMath.ChargeDamage(11, 20, 1.25f, 1), Is.EqualTo(275).Within(1e-3f));
            Assert.That(WeakPointMath.ChargeDamage(11, 20, 1.25f, .25f), Is.EqualTo(233.75f).Within(1e-3f));
            Assert.That(WeakPointMath.ChargeDamage(11, 20, 1.25f, 4), Is.EqualTo(275).Within(1e-3f), "share clamps to 1");
        }

        [Test]
        public void HealthAppliesTheMultiplierAfterArmour()
        {
            var h = new GameObject("droid").AddComponent<Health>(); h.max = 400; h.Restore();
            // the Scrap Reaper's flat 14 armour with the 25 % floor, as FeralDroid installs it
            h.AdjustIncomingDamage = x => FeralDroid.MitigatedDamage(x, 14, 0, .25f);
            Assert.That(h.Damage(34, Vector3.zero, 1.25f), Is.True);
            Assert.That(h.Current, Is.EqualTo(400 - 25).Within(1e-3f), "(34 − 14) × 1.25");
            Assert.That(h.LastDamageDealt, Is.EqualTo(25).Within(1e-3f));
            Assert.That(h.Damage(34, Vector3.zero), Is.True);
            Assert.That(h.Current, Is.EqualTo(400 - 45).Within(1e-3f), "the old two-argument call is unchanged");
            h.AdjustIncomingDamage = _ => 0;
            float before = h.Current;
            Assert.That(h.Damage(34, Vector3.zero, 3), Is.True);
            Assert.That(h.Current, Is.EqualTo(before), "a weak point cannot multiply a hit armour absorbed");
            h.AdjustIncomingDamage = null;
            Assert.That(h.Damage(1000, Vector3.zero, 2), Is.True);
            Assert.That(h.Current, Is.Zero); Assert.That(h.LastDamageDealt, Is.EqualTo(before).Within(1e-3f), "dealt is capped at what was left");
        }

        [Test]
        public void WeakPointZoneFollowsItsAnchorAndTheRootScale()
        {
            var root = new GameObject("droid"); var head = new GameObject("head").transform; head.SetParent(root.transform, false);
            head.localPosition = new Vector3(0, 1.6f, .1f);
            var weak = root.AddComponent<DroidWeakPoint>(); weak.anchor = head; weak.offset = new Vector3(0, 0, .1f); weak.radius = .15f; weak.depthTolerance = .35f;
            Assert.That(Vector3.Distance(weak.Centre, new Vector3(0, 1.6f, .2f)), Is.LessThan(1e-4f));
            var origin = new Vector3(0, 1.6f, 10);
            Assert.That(weak.Test(origin, Vector3.back, 9.9f, out float d), Is.True, "struck the body just in front of the optic");
            Assert.That(d, Is.EqualTo(10 - .2f - .15f).Within(1e-3f));
            Assert.That(weak.Test(origin + Vector3.up * .3f, Vector3.back, 9.9f, out _), Is.False, "over the top of the optic");
            Assert.That(weak.Test(origin, Vector3.back, 9, out _), Is.False, "the shot stopped on cover well before the droid");
            // the 1.3× Foreman: offsets and radius grow with the root, not with bone scales
            root.transform.localScale = Vector3.one * 1.3f;
            Assert.That(weak.WorldRadius, Is.EqualTo(.195f).Within(1e-4f));
            Assert.That(Vector3.Distance(weak.Centre, head.position + new Vector3(0, 0, .13f)), Is.LessThan(1e-4f));
            head.localScale = Vector3.one * 100; // Meshy bones are often scaled
            Assert.That(weak.WorldRadius, Is.EqualTo(.195f).Within(1e-4f));
            Assert.That(Vector3.Distance(weak.Centre, head.position + new Vector3(0, 0, .13f)), Is.LessThan(1e-4f));
            Object.DestroyImmediate(root);
        }

        [Test]
        public void HitMarkerRanksKillOverCriticalOverHit()
        {
            var m = new HitMarkerState();
            Assert.That(m.Visible(0), Is.False); Assert.That(m.Opacity(0), Is.Zero);
            Assert.That(m.Register(false, false, 10), Is.EqualTo(HitMarkerKind.Hit));
            Assert.That(m.Visible(10 + m.hitSeconds * .5f), Is.True);
            Assert.That(m.Visible(10 + m.hitSeconds + .001f), Is.False);
            Assert.That(m.Register(true, false, 11), Is.EqualTo(HitMarkerKind.Critical));
            Assert.That(m.Register(false, false, 11.05f), Is.EqualTo(HitMarkerKind.Critical), "a hit cannot replace a showing critical");
            Assert.That(m.Until, Is.EqualTo(11 + m.criticalSeconds).Within(1e-4f), "…and only extends it when it would outlast it");
            Assert.That(m.Register(true, true, 11.1f), Is.EqualTo(HitMarkerKind.Kill), "a kill replaces a critical");
            Assert.That(m.Register(true, false, 11.15f), Is.EqualTo(HitMarkerKind.Kill));
            Assert.That(m.Until, Is.EqualTo(11.1f + m.killSeconds).Within(1e-4f));
            Assert.That(m.Register(false, false, 20), Is.EqualTo(HitMarkerKind.Hit), "after it fades a hit shows again");
            Assert.That(m.Hits, Is.EqualTo(3)); Assert.That(m.Criticals, Is.EqualTo(2)); Assert.That(m.Kills, Is.EqualTo(1));
            Assert.That(HitMarkerState.KindFor(false, true), Is.EqualTo(HitMarkerKind.Kill));
        }

        [Test]
        public void HitMarkerFadesAndPopsUnlessReducedMotion()
        {
            var m = new HitMarkerState();
            m.Register(true, true, 0);
            Assert.That(m.Opacity(.01f), Is.EqualTo(1));
            Assert.That(m.Opacity(m.killSeconds * .99f), Is.LessThan(.1f));
            Assert.That(m.Scale(0, false), Is.EqualTo(m.popScale).Within(1e-4f));
            Assert.That(m.Scale(.2f, false), Is.EqualTo(1).Within(1e-4f));
            Assert.That(m.Scale(0, true), Is.EqualTo(1), "Reduced Motion: no pop");
            m.Register(false, false, 5);
            Assert.That(m.Scale(5, false), Is.EqualTo(1), "plain hits never pop");
            m.Clear(); Assert.That(m.Visible(5), Is.False);
        }

        [Test]
        public void ImpulseTraumaClampsDecaysAndShakesQuadratically()
        {
            var s = new ImpulseState { decayPerSecond = 2 };
            s.Add(.5f); Assert.That(s.Trauma, Is.EqualTo(.5f)); Assert.That(s.Shake, Is.EqualTo(.25f).Within(1e-5f));
            s.Add(.8f); Assert.That(s.Trauma, Is.EqualTo(1));
            s.Add(-1); s.Add(float.NaN); Assert.That(s.Trauma, Is.EqualTo(1));
            s.Step(.25f); Assert.That(s.Trauma, Is.EqualTo(.5f).Within(1e-5f));
            s.Step(5); Assert.That(s.Trauma, Is.Zero);
            Assert.That(ImpulseState.Falloff(0, 16), Is.EqualTo(1));
            Assert.That(ImpulseState.Falloff(8, 16), Is.EqualTo(.25f).Within(1e-5f));
            Assert.That(ImpulseState.Falloff(20, 16), Is.Zero);
            Assert.That(ImpulseState.Falloff(1, 0), Is.Zero);
            Assert.That(ImpulseState.ForDamage(0, 100, .22f, 1.1f), Is.Zero);
            Assert.That(ImpulseState.ForDamage(14, 100, .22f, 1.1f), Is.EqualTo(.374f).Within(1e-4f));
            Assert.That(ImpulseState.ForDamage(500, 100, .22f, 1.1f), Is.EqualTo(1));
            Assert.That(ImpulseState.Amplitude(.5f, 1, true), Is.Zero, "Reduced Motion removes shake");
            Assert.That(ImpulseState.Amplitude(.5f, 0, false), Is.Zero, "the setting at 0 % removes shake");
            Assert.That(ImpulseState.Amplitude(.5f, .5f, false), Is.EqualTo(.25f).Within(1e-5f));
        }

        [Test]
        public void LowVitalityWarningDeepensAndHoldsStillUnderReducedMotion()
        {
            Assert.That(VitalityWarning.Intensity(.5f, .35f), Is.Zero);
            Assert.That(VitalityWarning.Intensity(.35f, .35f), Is.Zero);
            Assert.That(VitalityWarning.Intensity(.175f, .35f), Is.EqualTo(.5f).Within(1e-4f));
            Assert.That(VitalityWarning.Intensity(0, .35f), Is.EqualTo(1));
            Assert.That(VitalityWarning.Intensity(.1f, 0), Is.Zero);
            Assert.That(VitalityWarning.Pulse(0, 3, 1, false), Is.Zero);
            Assert.That(VitalityWarning.Pulse(1, 1.3f, 1.1f, true), Is.EqualTo(VitalityWarning.Pulse(1, 7.9f, 1.1f, true)), "steady under Reduced Motion");
            float lo = 1, hi = 0;
            for (float t = 0; t < 2; t += .01f) { float p = VitalityWarning.Pulse(1, t, 1, false); lo = Mathf.Min(lo, p); hi = Mathf.Max(hi, p); }
            Assert.That(lo, Is.EqualTo(.6f).Within(.01f)); Assert.That(hi, Is.EqualTo(1).Within(.01f));
        }

        [Test]
        public void CriticalHitsStaggerSoonerButNeverBeforeTheShorterImmunity()
        {
            Assert.That(FeralDroid.StaggerReady(10, 9.5f, 1.3f, .8f, false), Is.False);
            Assert.That(FeralDroid.StaggerReady(10, 9.1f, 1.3f, .8f, true), Is.True, "0.9 s after: a critical may stagger");
            Assert.That(FeralDroid.StaggerReady(10, 9.1f, 1.3f, .8f, false), Is.False, "an ordinary hit waits 1.3 s");
            Assert.That(FeralDroid.StaggerReady(10, 9.5f, 1.3f, .8f, true), Is.False);
            Assert.That(FeralDroid.StaggerReady(10, 9.5f, .4f, .8f, true), Is.True, "a droid with a shorter own immunity keeps it");
            Assert.That(FeralDroid.StaggerReady(0, -99, 1.3f, .8f, false), Is.True, "first hit");
        }

        [Test]
        public void WeatherNarrowsSightDownToTheFloorOnly()
        {
            Assert.That(FeralDroid.WeatherSightScale(1, .5f), Is.EqualTo(1), "clear air or no weather");
            Assert.That(FeralDroid.WeatherSightScale(.8f, .5f), Is.EqualTo(.8f).Within(1e-5f));
            Assert.That(FeralDroid.WeatherSightScale(.45f, .5f), Is.EqualTo(.5f), "a front's peak stops at the floor");
            Assert.That(FeralDroid.WeatherSightScale(0, .5f), Is.EqualTo(.5f));
            Assert.That(FeralDroid.WeatherSightScale(.3f, 0), Is.EqualTo(.3f).Within(1e-5f));
            Assert.That(FeralDroid.WeatherSightScale(.3f, 2), Is.EqualTo(1), "floor clamps to 1");
            Assert.That(FeralDroid.WeatherSightScale(1.5f, .5f), Is.EqualTo(1));
        }

        [Test]
        public void FxLightBudgetGivesTheNewestTheOldestSlot()
        {
            int cap = FxBurst.MaxLights;
            var made = new System.Collections.Generic.List<GameObject>();
            try
            {
                FxBurst.MaxLights = 2;
                FxBurst Make() { var go = new GameObject("fx"); made.Add(go); return go.AddComponent<FxBurst>(); }
                var a = Make(); var b = Make(); var c = Make();
                Assert.That(a.AcquireLight() && b.AcquireLight(), Is.True);
                Assert.That(FxBurst.LightsLit, Is.LessThanOrEqualTo(2));
                Assert.That(c.AcquireLight(), Is.True, "the newest takes a slot");
                Assert.That(a.HoldsLight, Is.False, "…from the oldest"); Assert.That(b.HoldsLight && c.HoldsLight, Is.True);
                Assert.That(a.AcquireLight(), Is.False, "an evicted burst stays dark for the rest of its play");
                c.ReleaseLight(); Assert.That(c.HoldsLight, Is.False);
                Object.DestroyImmediate(b.gameObject);
                Assert.That(FxBurst.LightsLit, Is.Zero, "destroyed bursts free their slot");
                FxBurst.MaxLights = 0; var d = Make();
                Assert.That(d.AcquireLight(), Is.False, "cap 0: no FX lights");
            }
            finally
            {
                foreach (var go in made) if (go) Object.DestroyImmediate(go);
                FxBurst.MaxLights = cap;
            }
        }

        [Test]
        public void ControlOptionsKeepDefaultsForOlderSavedSettings()
        {
            var old = JsonUtility.FromJson<ControlOptions>("{\"sensitivity\":140,\"invertY\":true}");
            Assert.That(old.sensitivity, Is.EqualTo(140)); Assert.That(old.cameraShake, Is.EqualTo(100)); Assert.That(old.hitMarkers, Is.True);
            Assert.That(new ControlOptions { cameraShake = 250 }.CameraShake, Is.EqualTo(1));
            Assert.That(new ControlOptions { cameraShake = 40 }.CameraShake, Is.EqualTo(.4f).Within(1e-4f));
        }

        /// The balance rule: weak points must not let the starter pistol take the level-3 droids. A full charge with a
        /// quarter of its hits on the optic stays under 60 % of their vitality (the next-level enemy test's bar), and
        /// even every hit on the optic stays under 100 %; the modded rifle still gets through faster than before.
        [Test]
        public void WeakPointsKeepTheStarterPistolOffTheLevelThreeDroids()
        {
            var catalog = AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
            var pistol = catalog.weapons.Single(w => w.id == "weapon_scrap_pistol").stats;
            var rifle = catalog.weapons.Single(w => w.id == "weapon_field_rifle").stats;
            float barrelPen = catalog.modifiers.Single(m => m.id == "mod_rifle_precision_barrel").effects.Single(e => e.stat == "armourPenetration").value;
            int shots = Mathf.FloorToInt(pistol.nanoMax / pistol.nanoPerShot);
            int checkedDroids = 0;
            foreach (var file in new[] { "FeralScrapReaper", "FeralPostSentinel", "FeralDepotForeman" })
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/" + file + ".prefab");
                if (!go) continue;
                var d = go.GetComponent<FeralDroid>(); var t = go.GetComponent<DroidThreat>(); var h = go.GetComponent<Health>();
                if (!t || t.level < 3) continue;
                var weak = go.GetComponent<DroidWeakPoint>();
                float multiplier = weak ? weak.damageMultiplier : DroidWeakPoint.MultiplierFor(t.level);
                Assert.That(multiplier, Is.LessThanOrEqualTo(DroidWeakPoint.Level3Multiplier + 1e-4f), file);
                float pistolHit = FeralDroid.MitigatedDamage(WeaponBallistics.ArmourReduced(pistol.damage, t.armour, pistol.armourPenetration), d.armour, pistol.armourPenetration, d.armourMinFraction);
                float expected = WeakPointMath.ChargeDamage(shots, pistolHit, multiplier, DroidWeakPoint.ExpectedWeakShare);
                float ceiling = WeakPointMath.ChargeDamage(shots, pistolHit, multiplier, 1);
                Assert.That(expected, Is.LessThan(h.max * .6f), $"{file}: expected pistol charge {expected:0} of {h.max}");
                Assert.That(ceiling, Is.LessThan(h.max), $"{file}: every pistol hit on the optic {ceiling:0} of {h.max}");
                float rifleHit = FeralDroid.MitigatedDamage(WeaponBallistics.ArmourReduced(rifle.damage * 1.05f, t.armour, rifle.armourPenetration + barrelPen), d.armour, rifle.armourPenetration + barrelPen, d.armourMinFraction);
                Assert.That(rifleHit * multiplier, Is.GreaterThan(rifleHit), file + ": the rifle gains from the optic");
                checkedDroids++;
            }
            Assert.That(checkedDroids, Is.GreaterThanOrEqualTo(2), "the Reaper and Sentinel prefabs exist");
            Assert.That(DroidWeakPoint.MultiplierFor(1), Is.EqualTo(DroidWeakPoint.DefaultMultiplier));
            Assert.That(DroidWeakPoint.MultiplierFor(3), Is.EqualTo(DroidWeakPoint.Level3Multiplier));
        }

        /// After the installer: every live droid prefab carries a weak point inside its own hierarchy, level 3 at the
        /// smaller multiplier.
        [Test]
        public void InstalledWeakPointsSitInsideTheirDroids()
        {
            var paths = AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/AthenHill/Prefabs/OuterBerms" }).Select(AssetDatabase.GUIDToAssetPath)
                .Where(p => System.IO.Path.GetDirectoryName(p).Replace('\\', '/') == "Assets/AthenHill/Prefabs/OuterBerms").ToArray();
            var droids = paths.Select(p => AssetDatabase.LoadAssetAtPath<GameObject>(p)).Where(g => g && g.GetComponent<FeralDroid>()).ToArray();
            if (!droids.Any(g => g.GetComponent<DroidWeakPoint>())) { Assert.Inconclusive("CombatFeelPass20261119 droids step not run yet"); return; }
            foreach (var g in droids)
            {
                var w = g.GetComponent<DroidWeakPoint>(); Assert.That(w, Is.Not.Null, g.name);
                if (w.anchor) Assert.That(w.anchor.IsChildOf(g.transform), g.name);
                Assert.That(w.radius, Is.InRange(.08f, .3f), g.name);
                var t = g.GetComponent<DroidThreat>();
                Assert.That(w.damageMultiplier, Is.EqualTo(DroidWeakPoint.MultiplierFor(t ? t.level : 1)).Within(1e-4f), g.name);
                // walkers and the wheeled Sentinel stand on their root; hover drones carry it at body height
                float rise = w.Centre.y - g.transform.position.y, reach = Vector3.Distance(w.Centre, g.transform.position);
                Assert.That(reach, Is.LessThan(4f), g.name + ": the zone sits on the droid");
                if (g.GetComponent<FeralDroid>().kind != DroidKind.Hover) Assert.That(rise, Is.GreaterThan(.5f), g.name + ": the zone is up at the optic, not at the feet");
            }
        }
    }
}
