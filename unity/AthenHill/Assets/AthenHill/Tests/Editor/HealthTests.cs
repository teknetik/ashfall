using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
 public class HealthTests
 {
  Health Make(float max){var go=new GameObject("health");var h=go.AddComponent<Health>();h.max=max;h.Restore();return h;}
  [TearDown]public void Clean(){foreach(var h in Object.FindObjectsByType<Health>(FindObjectsInactive.Include))Object.DestroyImmediate(h.gameObject);}
  [Test]public void DamageClampsAtZeroAndDiesOnce(){var h=Make(30);int died=0;h.Died+=()=>died++;Assert.That(h.Damage(20,Vector3.zero));Assert.That(h.Current,Is.EqualTo(10));Assert.That(h.Damage(25,Vector3.zero));Assert.That(h.Current,Is.Zero);Assert.That(h.Alive,Is.False);Assert.That(h.Damage(5,Vector3.zero),Is.False);Assert.That(died,Is.EqualTo(1));}
  [Test]public void ZeroOrNegativeDamageIsIgnored(){var h=Make(10);int hits=0;h.Damaged+=(_,__)=>hits++;Assert.That(h.Damage(0,Vector3.zero),Is.False);Assert.That(h.Damage(-3,Vector3.zero),Is.False);Assert.That(h.Current,Is.EqualTo(10));Assert.That(hits,Is.Zero);}
  [Test]public void HealNeverExceedsMaxOrRevives(){var h=Make(50);h.Damage(20,Vector3.zero);h.Heal(100);Assert.That(h.Current,Is.EqualTo(50));h.Damage(60,Vector3.zero);h.Heal(10);Assert.That(h.Alive,Is.False);h.Restore();Assert.That(h.Current,Is.EqualTo(50));}
 }
}
