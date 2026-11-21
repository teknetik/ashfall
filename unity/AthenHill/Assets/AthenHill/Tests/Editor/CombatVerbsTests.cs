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
    }
}
