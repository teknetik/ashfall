using UnityEngine;

namespace AthenHill
{
    public enum ActorAirPhase { Grounded, Takeoff, Rising, Falling, Landing }

    // Presentation only: the CharacterController remains the authority for movement.
    // Keeping this small state machine independent makes edge/fall/re-jump behavior testable.
    public sealed class ActorAirMotion
    {
        public ActorAirPhase Phase { get; private set; }
        public float PhaseTime { get; private set; }
        public float AirTime { get; private set; }
        public float ImpactSpeed { get; private set; }
        bool initialized, wasGrounded, jumped;
        float lastVertical;

        public void Reset()
        {
            Phase = ActorAirPhase.Grounded;
            PhaseTime = AirTime = ImpactSpeed = lastVertical = 0;
            initialized = wasGrounded = jumped = false;
        }

        public void Step(bool grounded, bool jumpAccepted, float verticalSpeed, float dt,
            float takeoffSeconds = .12f, float landingSeconds = .24f)
        {
            dt = Mathf.Max(0, dt);
            PhaseTime += dt;
            if (!initialized)
            {
                initialized = true;
                wasGrounded = grounded;
            }
            if (jumpAccepted)
            {
                // A second accepted jump interrupts recovery immediately, without delaying input.
                jumped = true;
                AirTime = ImpactSpeed = 0;
                Change(ActorAirPhase.Takeoff, true);
            }
            else if (grounded)
            {
                if (!wasGrounded && (jumped || AirTime >= .08f) && lastVertical < -2.1f)
                {
                    ImpactSpeed = -lastVertical;
                    Change(ActorAirPhase.Landing);
                }
                else if (Phase != ActorAirPhase.Landing || PhaseTime >= landingSeconds)
                    Change(ActorAirPhase.Grounded);
                AirTime = 0;
                jumped = false;
            }
            else
            {
                AirTime += dt;
                if (Phase == ActorAirPhase.Takeoff && PhaseTime < takeoffSeconds && verticalSpeed > 0) { }
                else if (verticalSpeed > .1f) Change(ActorAirPhase.Rising);
                // Brief contact losses over treads remain locomotion rather than stamping every step.
                else if (jumped || AirTime >= .06f) Change(ActorAirPhase.Falling);
            }
            wasGrounded = grounded;
            lastVertical = verticalSpeed;
        }

        void Change(ActorAirPhase next, bool restart = false)
        {
            if (Phase == next && !restart) return;
            Phase = next;
            PhaseTime = 0;
        }
    }
}
