using NUnit.Framework;

namespace AthenHill.Tests
{
    public sealed class LivingWardTests
    {
        [Test]
        public void CalmDaylightKeepsAuthoredWalkerPacing()
        {
            AmbientWalker.AmbientPacing(1f, 1f, 1f, out float speed, out float stop, out bool shelter);
            Assert.That(speed, Is.EqualTo(1f).Within(1e-4f));
            Assert.That(stop, Is.EqualTo(1f).Within(1e-4f));
            Assert.That(shelter, Is.False);
        }

        [Test]
        public void DustFrontMakesWalkersHurryAndShelterLonger()
        {
            AmbientWalker.AmbientPacing(2.4f, .45f, 1f, out float speed, out float stop, out bool shelter);
            Assert.That(speed, Is.GreaterThan(1.2f));
            Assert.That(stop, Is.GreaterThan(1.2f));
            Assert.That(shelter, Is.True);
        }

        [Test]
        public void NightSoftensWalkerSpeedAndExtendsStops()
        {
            AmbientWalker.AmbientPacing(1f, 1f, .05f, out float speed, out float stop, out bool shelter);
            Assert.That(speed, Is.LessThan(1f));
            Assert.That(stop, Is.GreaterThan(1f));
            Assert.That(shelter, Is.False);
        }
    }
}
