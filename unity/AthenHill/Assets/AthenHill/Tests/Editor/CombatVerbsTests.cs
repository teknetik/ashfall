using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    public sealed class CombatVerbsTests
    {
        [Test]
        public void DodgeDirectionUsesMoveInputOrDashesBackward()
        {
            var right = CombatVerbs.DodgeDirection(new Vector2(1, 0), Vector3.forward);
            Assert.That(Vector3.Distance(right, Vector3.right), Is.LessThan(1e-4f));
            var back = CombatVerbs.DodgeDirection(Vector2.zero, Vector3.forward);
            Assert.That(Vector3.Distance(back, Vector3.back), Is.LessThan(1e-4f));
        }

        [Test]
        public void DodgeStateTracksActiveInvulnerableAndCooldownWindows()
        {
            var dodge = new DodgeState();
            Assert.That(dodge.TryStart(10f, Vector3.right), Is.True);
            Assert.That(dodge.Active(10.1f), Is.True);
            Assert.That(dodge.Invulnerable(10.1f), Is.True);
            Assert.That(dodge.Invulnerable(10.2f), Is.False, "i-frames end slightly before the dash finishes");
            Assert.That(dodge.Active(10.25f), Is.False);
            Assert.That(dodge.TryStart(10.5f, Vector3.left), Is.False, "blocked during cooldown");
            Assert.That(dodge.CooldownRemaining(10.5f), Is.GreaterThan(0f));
            Assert.That(dodge.TryStart(11.5f, Vector3.left), Is.True, "ready once cooldown expires");
        }

        [Test]
        public void ShoveConeAcceptsCloseFrontTargetsAndRejectsBehindOrFar()
        {
            Assert.That(CombatVerbs.InShoveCone(Vector3.zero, Vector3.forward, new Vector3(0, 0, 2f)), Is.True);
            Assert.That(CombatVerbs.InShoveCone(Vector3.zero, Vector3.forward, new Vector3(1.2f, 0, 1.5f)), Is.True);
            Assert.That(CombatVerbs.InShoveCone(Vector3.zero, Vector3.forward, new Vector3(0, 0, 4f)), Is.False, "beyond range");
            Assert.That(CombatVerbs.InShoveCone(Vector3.zero, Vector3.forward, new Vector3(0, 0, -1.5f)), Is.False, "behind player");
        }

        [Test]
        public void EmpArmourStripReducesDroidMitigation()
        {
            float stripped = CombatVerbs.StrippedArmour(20f, CombatVerbs.EmpArmourStripFraction);
            Assert.That(stripped, Is.EqualTo(10f).Within(1e-4f));
            float normalHit = FeralDroid.MitigatedDamage(34f, 20f, 0f, .25f);
            float empHit = FeralDroid.MitigatedDamage(34f, stripped, 0f, .25f);
            Assert.That(empHit, Is.GreaterThan(normalHit));
            Assert.That(CombatVerbs.InEmpRadius(Vector3.zero, new Vector3(5f, 0, 5f)), Is.True);
            Assert.That(CombatVerbs.InEmpRadius(Vector3.zero, new Vector3(6f, 0, 6f)), Is.False);
        }

        [Test]
        public void EyeImplantExtendsOverchargeAndWeakPointForgiveness()
        {
            Assert.That(CombatVerbs.OverchargeSeconds(false), Is.EqualTo(CombatVerbs.OverchargeDuration));
            Assert.That(CombatVerbs.OverchargeSeconds(true), Is.EqualTo(CombatVerbs.OverchargeDuration + CombatVerbs.OverchargeEyeBonusSeconds));
            Assert.That(CombatVerbs.WeakPointRadiusScale(false, true), Is.EqualTo(1f));
            Assert.That(CombatVerbs.WeakPointRadiusScale(true, false), Is.EqualTo(1f));
            Assert.That(CombatVerbs.WeakPointRadiusScale(true, true), Is.EqualTo(CombatVerbs.EyeOverchargeWeakPointScale));
        }

        [Test]
        public void ImpulseForVerbSelectsClampedTraumaAndGuardsNaN()
        {
            Assert.That(ImpulseState.ForVerb(CombatVerbKind.Dodge, .14f, .28f, .42f, .22f), Is.EqualTo(.14f).Within(1e-5f));
            Assert.That(ImpulseState.ForVerb(CombatVerbKind.Shove, .14f, .28f, .42f, .22f), Is.EqualTo(.28f).Within(1e-5f));
            Assert.That(ImpulseState.ForVerb(CombatVerbKind.Emp, .14f, .28f, .42f, .22f), Is.EqualTo(.42f).Within(1e-5f));
            Assert.That(ImpulseState.ForVerb(CombatVerbKind.Overcharge, .14f, .28f, .42f, .22f), Is.EqualTo(.22f).Within(1e-5f));
            Assert.That(ImpulseState.ForVerb(CombatVerbKind.Emp, 0, 0, 2.5f, 0), Is.EqualTo(1f));
            Assert.That(ImpulseState.ForVerb(CombatVerbKind.Dodge, float.NaN, 0, 0, 0), Is.Zero);
            Assert.That(ImpulseState.ForDamage(float.NaN, 100, .2f, 1f), Is.Zero);
            Assert.That(VitalityWarning.Intensity(float.NaN, .35f), Is.Zero);
        }

        [Test]
        public void ViewModelMotionRespondsToStrafeAndVerbsAndRespectsReducedMotion()
        {
            float hipRoll = ViewModelMotion.StrafeRoll(6f, 6f, 1.6f, 0f, false);
            float adsRoll = ViewModelMotion.StrafeRoll(6f, 6f, 1.6f, 1f, false);
            Assert.That(hipRoll, Is.EqualTo(-1.6f).Within(1e-4f));
            Assert.That(Mathf.Abs(adsRoll), Is.LessThan(Mathf.Abs(hipRoll)));
            Assert.That(ViewModelMotion.StrafeRoll(6f, 6f, 1.6f, 0f, true), Is.Zero, "Reduced Motion removes strafe roll");

            ViewModelMotion.VerbPose(0f, 1f, 0f, 0f, false, 1f, 0f, false, out var shoveOff, out var shoveRot);
            Assert.That(shoveOff.z, Is.GreaterThan(.05f), "shove thrusts weapon forward");
            Assert.That(Mathf.Abs(shoveRot.z), Is.GreaterThan(1f));

            ViewModelMotion.VerbPose(1f, 0f, 0f, 0f, false, 1f, 0f, false, out var dodgeOff, out var dodgeRot);
            Assert.That(dodgeOff.y, Is.LessThan(0f), "dodge tucks weapon slightly down");
            Assert.That(dodgeRot.z, Is.LessThan(0f));

            ViewModelMotion.VerbPose(1f, 1f, 1f, 1f, true, 1.25f, 0f, true, out var rmOff, out var rmRot);
            Assert.That(rmRot, Is.EqualTo(Vector3.zero), "Reduced Motion removes verb rotation");
            Assert.That(rmOff.x, Is.Zero);
            Assert.That(rmOff.z, Is.Zero);
            Assert.That(rmOff.y, Is.GreaterThan(0f), "static overcharge readiness lift only");
        }

        [Test]
        public void CombatAudioSynthesizesBoundedClickFreeVerbCues()
        {
            foreach (var kind in new[] { CombatVerbKind.Dodge, CombatVerbKind.Shove, CombatVerbKind.Emp, CombatVerbKind.Overcharge })
            {
                var samples = CombatAudio.GenerateVerbSamples(kind, 22050);
                Assert.That(samples.Length, Is.GreaterThan(1000), kind.ToString());
                float peak = 0;
                for (int i = 0; i < samples.Length; i++)
                {
                    Assert.That(float.IsNaN(samples[i]) || float.IsInfinity(samples[i]), Is.False, kind.ToString());
                    peak = Mathf.Max(peak, Mathf.Abs(samples[i]));
                }
                Assert.That(peak, Is.GreaterThan(.05f).And.LessThanOrEqualTo(.85f + 1e-4f), kind.ToString());
                Assert.That(Mathf.Abs(samples[0]), Is.LessThan(.01f), "fade-in avoids start click");
                Assert.That(Mathf.Abs(samples[samples.Length - 1]), Is.LessThan(.01f), "fade-out avoids end click");
            }
            Assert.That(CombatAudio.PickIndex(3, 0, float.NaN, float.NaN), Is.InRange(0, 2));
        }

        [Test]
        public void DroidBoltBlocksStaleOwnersAndClampsSplashDamage()
        {
            Assert.That(DroidBolt.CanOwnerFire(false, false, false, DroidState.Dead), Is.True, "unowned bolts allowed");
            Assert.That(DroidBolt.CanOwnerFire(true, true, true, DroidState.Firing), Is.True);
            Assert.That(DroidBolt.CanOwnerFire(true, true, false, DroidState.Firing), Is.False, "dead health blocked");
            Assert.That(DroidBolt.CanOwnerFire(true, true, true, DroidState.Dead), Is.False, "dead state blocked");
            Assert.That(DroidBolt.CanOwnerFire(true, true, true, DroidState.Stagger), Is.False, "staggered / EMP-stunned blocked");
            Assert.That(DroidBolt.CanOwnerFire(true, false, true, DroidState.Firing), Is.False, "inactive / parked blocked");

            Assert.That(DroidBolt.SplashDamageAt(0f, 2.2f, 9f), Is.EqualTo(9f).Within(1e-4f));
            Assert.That(DroidBolt.SplashDamageAt(1.1f, 2.2f, 9f), Is.EqualTo(6.3f).Within(1e-4f));
            Assert.That(DroidBolt.SplashDamageAt(2.2f, 2.2f, 9f), Is.Zero);
            Assert.That(DroidBolt.SplashDamageAt(-1f, 2.2f, 9f), Is.Zero);
            Assert.That(DroidBolt.SplashDamageAt(float.NaN, 2.2f, 9f), Is.Zero);
        }

        [Test]
        public void DroidEncounterPackDelayScalesWithDistanceSightlineAndUnparkClampsHysteresis()
        {
            var range = new Vector2(.35f, 1.1f);
            float nearClear = DroidEncounter.PackCallDelay(2f, 16f, range, .5f, true);
            float farClear = DroidEncounter.PackCallDelay(15f, 16f, range, .5f, true);
            float farBlocked = DroidEncounter.PackCallDelay(15f, 16f, range, .5f, false);
            Assert.That(nearClear, Is.GreaterThanOrEqualTo(range.x).And.LessThan(farClear));
            Assert.That(farBlocked, Is.GreaterThan(farClear), "occluded packmates lag slightly");
            Assert.That(DroidEncounter.UnparkDistance(40f, 15f), Is.EqualTo(25f));
            Assert.That(DroidEncounter.UnparkDistance(10f, 15f), Is.Zero, "hysteresis never underflows negative");
        }

        [Test]
        public void WeaponBallisticsHandlesWideConesNegativeDamageAndNaN()
        {
            Assert.That(WeaponBallistics.HitChance(100f, 20f, .35f), Is.LessThan(.05f), "cones >= 90 deg must not wrap tan negative");
            Assert.That(WeaponBallistics.HitChance(5f, 20f, 0f), Is.Zero);
            Assert.That(WeaponBallistics.ArmourReduced(-10f, 5f, 0f), Is.Zero);
            Assert.That(WeaponBallistics.ArmourReduced(float.NaN, 5f, 0f), Is.Zero);
            Assert.That(WeaponBallistics.Falloff(float.NaN, 30f), Is.Zero);
            Assert.That(WeaponBallistics.SkillFor("weapon_heavyWeapons_cannon"), Is.EqualTo("heavyWeapons"));
            Assert.That(WeaponBallistics.SkillFor("weapon_energyWeapons_lance"), Is.EqualTo("energyWeapons"));
        }
    }
}
