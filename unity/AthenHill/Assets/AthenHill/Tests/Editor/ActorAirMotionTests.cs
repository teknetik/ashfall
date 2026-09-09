using NUnit.Framework;
namespace AthenHill.Tests
{
    public class ActorAirMotionTests
    {
        static ActorAirMotion Grounded()
        {
            var a=new ActorAirMotion();a.Step(true,false,-2,.02f);return a;
        }
        [Test] public void StandingAndRunningJumpsFollowActualAscentAndContact()
        {
            // Horizontal speed deliberately does not select the airborne state.
            var a=Grounded();a.Step(false,true,7.26f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Takeoff));
            for(int i=0;i<7;i++)a.Step(false,false,4,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Rising));
            a.Step(false,false,-.3f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Falling));
            a.Step(false,false,-6.8f,.02f);a.Step(true,false,-7.2f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Landing));
            Assert.That(a.ImpactSpeed,Is.EqualTo(6.8f).Within(.001));
            for(int i=0;i<13;i++)a.Step(true,false,-2,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Grounded));
        }
        [Test] public void WalkingOffEdgeDoesNotInventTakeoff()
        {
            var a=Grounded();
            for(int i=0;i<5;i++)a.Step(false,false,-2-i*.44f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Falling));
            a.Step(true,false,-4.2f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Landing));
        }
        [Test] public void OneTreadContactLossDoesNotTriggerJumpOrLanding()
        {
            var a=Grounded();a.Step(false,false,-2,.02f);a.Step(true,false,-2,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Grounded));
        }
        [Test] public void RepeatedAcceptedJumpInterruptsLandingWithoutWaiting()
        {
            var a=Grounded();a.Step(false,true,7.26f,.02f);a.Step(false,false,-7,.4f);a.Step(true,false,-7.1f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Landing));
            a.Step(false,true,7.26f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Takeoff));
            Assert.That(a.PhaseTime,Is.Zero);Assert.That(a.ImpactSpeed,Is.Zero);
        }
        [Test] public void GroundedBlockedInputCannotInventAnAcceptedJump()
        {
            var a=Grounded();for(int i=0;i<30;i++)a.Step(true,false,-2,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Grounded));
        }
        [Test] public void TeleportResetCannotReplayOldLanding()
        {
            var a=Grounded();a.Step(false,true,7.26f,.02f);a.Step(false,false,-10,.5f);a.Reset();
            a.Step(false,false,-.44f,.02f);a.Step(true,false,-.88f,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Grounded));
            Assert.That(a.AirTime,Is.Zero);Assert.That(a.ImpactSpeed,Is.Zero);
        }
        [Test] public void LowCeilingChangesTakeoffToFallInsteadOfHoldingRise()
        {
            var a=Grounded();a.Step(false,true,7.26f,.02f);a.Step(false,false,0,.02f);
            Assert.That(a.Phase,Is.EqualTo(ActorAirPhase.Falling));
        }
    }
}
