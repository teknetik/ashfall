using System;
using System.Collections.Generic;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    public class ReducedMotionSettingsTests
    {
        string prefix;
        readonly List<GameObject> objects = new List<GameObject>();

        [SetUp]
        public void SetUp() => prefix = "AthenHill.Tests.ReducedMotion." + Guid.NewGuid().ToString("N") + ".";

        [TearDown]
        public void TearDown()
        {
            foreach (var item in objects) UnityEngine.Object.DestroyImmediate(item);
            objects.Clear();
            PlayerPrefs.DeleteKey(prefix + "ReducedMotion");
            PlayerPrefs.DeleteKey(prefix + "QA.ReducedMotion");
            PlayerPrefs.Save();
        }

        GameSettings Settings(bool qa = false)
        {
            var root = new GameObject("reduced motion settings test");
            root.SetActive(false);
            objects.Add(root);
            var settings = root.AddComponent<GameSettings>();
            typeof(GameSettings).GetField("prefix", BindingFlags.Instance | BindingFlags.NonPublic)
                .SetValue(settings, prefix + (qa ? "QA." : ""));
            return settings;
        }

        [Test]
        public void UnsetPreferenceUsesTheCurrentSceneDefaultWithoutSavingIt()
        {
            var settings = Settings();
            Assert.That(settings.ReadReducedMotion(false), Is.False);
            Assert.That(settings.ReadReducedMotion(true), Is.True);
            Assert.That(PlayerPrefs.HasKey(prefix + "ReducedMotion"), Is.False);
        }

        [Test]
        public void ExplicitOnAndOffSurviveAReplacementSettingsInstance()
        {
            Settings().SaveReducedMotion(true);
            Assert.That(Settings().ReadReducedMotion(false), Is.True);
            Settings().SaveReducedMotion(false);
            Assert.That(Settings().ReadReducedMotion(true), Is.False);
        }

        [Test]
        public void QaPreferenceCannotChangeTheNormalPlayerPreference()
        {
            Settings().SaveReducedMotion(true);
            Assert.That(Settings(true).ReadReducedMotion(false), Is.False);
            Settings(true).SaveReducedMotion(false);
            Assert.That(Settings().ReadReducedMotion(false), Is.True);
            Assert.That(Settings(true).ReadReducedMotion(true), Is.False);
        }

        [Test]
        public void SessionRestoresBeforeStartAndToggleSavesTheNextChoice()
        {
            var settings = Settings();
            settings.SaveReducedMotion(true);
            var session = settings.gameObject.AddComponent<GameSession>();
            session.reducedMotion = false;
            typeof(GameSession).GetMethod("Awake", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(session, null);
            Assert.That(session.reducedMotion, Is.True);
            int changes = 0;
            session.Changed += () => changes++;
            session.ToggleReducedMotion();
            Assert.That(session.reducedMotion, Is.False);
            Assert.That(Settings().ReadReducedMotion(true), Is.False);
            Assert.That(changes, Is.EqualTo(1));
        }
    }
}
