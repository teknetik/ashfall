using System.IO;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    /// 19 Nov 2026 combat audio pass: per-weapon sound set choice (the pistol keeps its legacy arrays), droid clip
    /// overrides falling back to the shared clip, variation picking without immediate repeats, the droid voice budget,
    /// the desert rolloff curve and the Sentinel's roll mix. Nothing here needs the installer to have run.
    public class CombatAudioTests
    {
        static AudioClip Clip(string name) { var c = AudioClip.Create(name, 4410, 1, 44100, false); return c; }
        static WeaponSoundSet Set(string id, int bodies = 2) => new WeaponSoundSet { weaponId = id, body = Enumerable.Range(0, bodies).Select(i => Clip(id + "-body-" + i)).ToArray() };

        [TearDown]
        public void Clean()
        {
            foreach (var c in Object.FindObjectsByType<PlayerCombat>(FindObjectsInactive.Include)) Object.DestroyImmediate(c.gameObject);
            VoiceLimiter.Droids.Clear();
        }

        [Test]
        public void TheActiveWeaponPicksItsOwnSet()
        {
            var rifle = Set("weapon_field_rifle"); var other = Set("weapon_other");
            var sets = new[] { other, rifle };
            Assert.That(CombatAudio.SelectSet(sets, "weapon_field_rifle"), Is.SameAs(rifle));
            Assert.That(CombatAudio.SelectSet(sets, "weapon_other"), Is.SameAs(other));
            Assert.That(CombatAudio.SelectSet(sets, "weapon_scrap_pistol"), Is.Null, "no set: the pistol keeps PlayerCombat's own arrays");
            Assert.That(CombatAudio.SelectSet(sets, null), Is.Null);
            Assert.That(CombatAudio.SelectSet(sets, ""), Is.Null);
            Assert.That(CombatAudio.SelectSet(null, "weapon_field_rifle"), Is.Null);
            Assert.That(CombatAudio.SelectSet(new[] { Set("weapon_field_rifle", 0) }, "weapon_field_rifle"), Is.Null, "a set without a body layer is ignored");
            Assert.That(CombatAudio.SelectSet(new[] { new WeaponSoundSet { weaponId = "weapon_field_rifle", body = new AudioClip[] { null } } }, "weapon_field_rifle"), Is.Null);
        }

        [Test]
        public void PlayerCombatUsesTheBoundWeaponsSetAndLeavesThePistolAlone()
        {
            var go = new GameObject("combat"); var combat = go.AddComponent<PlayerCombat>();
            combat.shotBody = new[] { Clip("pistol-body") };
            var rifle = Set("weapon_field_rifle");
            combat.weaponSounds = new[] { rifle };
            Assert.That(combat.ActiveSoundSet, Is.Null, "no loadout bound");
            combat.BindLoadout(new WeaponLoadout(new CraftWeapon { id = "weapon_field_rifle", slots = new string[0] }, null));
            Assert.That(combat.ActiveSoundSet, Is.SameAs(rifle));
            combat.BindLoadout(new WeaponLoadout(new CraftWeapon { id = "weapon_scrap_pistol", slots = new string[0] }, null));
            Assert.That(combat.ActiveSoundSet, Is.Null, "pistol: legacy arrays");
            combat.weaponSounds = null;
            Assert.That(combat.ActiveSoundSet, Is.Null, "a scene saved before the pass has no sets");
        }

        [Test]
        public void PickingNeverRepeatsTheLastVariant()
        {
            for (int count = 2; count <= 8; count++)
            {
                int last = -1; var seen = new int[count];
                var rng = new System.Random(count);
                for (int n = 0; n < 2000; n++)
                {
                    int i = CombatAudio.PickIndex(count, last, (float)rng.NextDouble(), (float)rng.NextDouble());
                    Assert.That(i, Is.InRange(0, count - 1));
                    Assert.That(i, Is.Not.EqualTo(last), $"repeat with {count} variants");
                    seen[i]++; last = i;
                }
                Assert.That(seen.All(s => s > 2000 / count / 2), Is.True, $"every variant comes up with {count}: " + string.Join(",", seen));
            }
            Assert.That(CombatAudio.PickIndex(1, 0, .3f, .9f), Is.EqualTo(0), "a single clip may repeat");
            Assert.That(CombatAudio.PickIndex(0, -1, .3f, .9f), Is.EqualTo(-1));
            Assert.That(CombatAudio.PickIndex(3, 2, 1f, 1f), Is.InRange(0, 1), "edge randoms stay in range and avoid the last");
            Assert.That(CombatAudio.PickIndex(3, 0, 0f, 0f), Is.EqualTo(1));
        }

        [Test]
        public void ClipPickFromArraysAvoidsRepeats()
        {
            Random.InitState(42);
            var clips = new[] { Clip("a"), Clip("b"), Clip("c") };
            int last = -1; AudioClip prev = null;
            for (int n = 0; n < 300; n++) { var c = CombatAudio.Pick(clips, ref last); Assert.That(c, Is.Not.SameAs(prev)); prev = c; }
            Assert.That(CombatAudio.Pick(new AudioClip[0], ref last), Is.Null);
            Assert.That(CombatAudio.Pick(null, ref last), Is.Null);
        }

        [Test]
        public void DroidOverridesFallBackToTheSharedClip()
        {
            var shared = Clip("droid-alert"); var own = new[] { Clip("reaper-alert-1"), Clip("reaper-alert-2") };
            int last = -1;
            Assert.That(CombatAudio.Choose(new AudioClip[0], shared, ref last), Is.SameAs(shared), "empty override: today's shared clip");
            Assert.That(CombatAudio.Choose(null, shared, ref last), Is.SameAs(shared));
            Assert.That(CombatAudio.Choose(new AudioClip[] { null, null }, shared, ref last), Is.SameAs(shared), "only missing clips: shared");
            Assert.That(CombatAudio.Choose(new AudioClip[0], null, ref last), Is.Null, "nothing at all: silent, as before");
            Random.InitState(7);
            AudioClip prev = null;
            for (int n = 0; n < 50; n++) { var c = CombatAudio.Choose(own, shared, ref last); Assert.That(own, Does.Contain(c)); Assert.That(c, Is.Not.SameAs(prev)); prev = c; }
            var withHole = new[] { null, own[0] };
            for (int n = 0; n < 20; n++) Assert.That(CombatAudio.Choose(withHole, shared, ref last), Is.SameAs(own[0]), "a hole in the array is skipped");
        }

        [Test]
        public void NewDroidFieldsDefaultToTheSharedSet()
        {
            var go = new GameObject("droid"); var d = go.AddComponent<FeralDroid>();
            try
            {
                foreach (var a in new[] { d.alertVariants, d.windupVariants, d.strikeVariants, d.slamVariants, d.fireVariants, d.hitVariants, d.deathVariants, d.stepVariants })
                    Assert.That(a, Is.Empty);
                Assert.That(d.rollLoop, Is.Null);
                Assert.That(d.limitVoices, Is.True);
            }
            finally { Object.DestroyImmediate(go); }
        }

        [Test]
        public void VoiceBudgetKeepsEssentialCuesAndDropsTheRest()
        {
            var v = new VoiceLimiter(3, .07f);
            Assert.That(v.TryAcquire(0, 1, 1, false), Is.True);
            Assert.That(v.TryAcquire(0, 1, 1, false), Is.False, "same clip on the same frame");
            Assert.That(v.TryAcquire(0, 1, 1, true), Is.False, "same clip on the same frame, even essential");
            Assert.That(v.TryAcquire(.1f, 1, 1, false), Is.True, "same clip after the window");
            Assert.That(v.TryAcquire(.1f, 2, 1, false), Is.True);
            Assert.That(v.Playing(.1f), Is.EqualTo(3));
            Assert.That(v.TryAcquire(.2f, 3, 1, false), Is.False, "budget full: a footstep or clang drops");
            Assert.That(v.TryAcquire(.2f, 4, 1, true), Is.True, "an alert, tell, attack or death always plays");
            Assert.That(v.Playing(.2f), Is.EqualTo(4));
            Assert.That(v.TryAcquire(1.15f, 5, .5f, false), Is.True, "the first three sounds have ended");
            Assert.That(v.Playing(5), Is.EqualTo(0), "all expired");
            v.TryAcquire(5, 6, 10, false);
            Assert.That(v.Playing(1), Is.EqualTo(0), "time going backwards (a new play session) clears stale entries");
        }

        [Test]
        public void DesertRolloffFallsFromOneToSilenceAtMaxDistance()
        {
            foreach (var (min, max) in new[] { (3f, 70f), (3f, 90f), (12f, 120f), (1.5f, 50f) })
            {
                var c = CombatAudio.DesertRolloff(min, max);
                Assert.That(c.Evaluate(0), Is.EqualTo(1).Within(1e-4f));
                Assert.That(c.Evaluate(min / max * .5f), Is.EqualTo(1).Within(.02f), "full level inside Min Distance");
                Assert.That(c.Evaluate(1), Is.EqualTo(0).Within(1e-4f), "silent at Max Distance");
                float prev = 2;
                for (int i = 0; i <= 200; i++) { float g = CombatAudio.RolloffGain(i / 200f, min / max); Assert.That(g, Is.LessThanOrEqualTo(prev + 1e-5f)); prev = g; }
                // inverse distance in the useful range: twice Min Distance is about -6 dB
                Assert.That(CombatAudio.RolloffGain(2 * min / max, min / max), Is.EqualTo(.5f).Within(.03f));
            }
        }

        [Test]
        public void RollMixFollowsGroundSpeed()
        {
            var pitch = new Vector2(.75f, 1.2f);
            var idle = CombatAudio.RollMix(0, 5, .25f, pitch); var half = CombatAudio.RollMix(2.5f, 5, .25f, pitch); var full = CombatAudio.RollMix(9, 5, .25f, pitch);
            Assert.That(idle.x, Is.EqualTo(.25f).Within(1e-4f)); Assert.That(idle.y, Is.EqualTo(.75f).Within(1e-4f));
            Assert.That(half.x, Is.GreaterThan(idle.x).And.LessThan(1)); Assert.That(half.y, Is.EqualTo(.975f).Within(1e-3f));
            Assert.That(full.x, Is.EqualTo(1).Within(1e-4f)); Assert.That(full.y, Is.EqualTo(1.2f).Within(1e-4f));
        }

        [Test]
        public void GeneratedRifleSetHasEnoughVariationForABurst()
        {
            var dir = Path.Combine(Application.dataPath, "AthenHill/Audio/ElevenLabs/Combat/Rifle");
            Assume.That(Directory.Exists(dir), "rifle clips not generated (unity/tools/generate_combat_audio_20261119.py)");
            int Count(string layer) => Directory.GetFiles(dir, "rifle-" + layer + "-*.wav").Length;
            Assert.That(Count("mech"), Is.GreaterThanOrEqualTo(6));
            Assert.That(Count("body"), Is.GreaterThanOrEqualTo(8));
            Assert.That(Count("tail"), Is.GreaterThanOrEqualTo(6));
            Assert.That(Count("empty") * Count("draw") * Count("holster"), Is.GreaterThan(0));
        }
    }
}
