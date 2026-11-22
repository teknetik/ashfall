using UnityEngine;
namespace AthenHill
{
    /// The vise on its swivel (22 Nov 2026, Carl: it should spin at all times). The body turns about the centre of its
    /// still base and takes whatever is clamped in it along. Where it is left is where it stays, until the bench is rebuilt.
    public sealed class AssemblyViseSwivel
    {
        const string BodyId = "fixtures.vise";
        const float DegreesPerPixel = .45f, DegreesPerNotch = 15, DegreesPerSecond = 90, AxisDeadZone = .025f, FarFromAxis = .6f, MostPerFrame = 30;

        readonly AssemblyBench bench;
        readonly AssemblyPart body;
        Plane grabPlane; Ray lastRay; Vector3 lastArm;
        bool grabbed, armKnown;

        /// Degrees turned either way since the last ResetTravel.
        public float Travel { get; private set; }
        public bool Grabbed => grabbed;

        public AssemblyViseSwivel(AssemblyBench bench)
        {
            this.bench = bench;
            body = AssemblyVerb.SwivelOf(bench, bench.Part(BodyId));
        }

        public void ResetTravel() => Travel = 0;

        /// How far round from square it stands, degrees.
        public float Yaw => body ? Vector3.SignedAngle(body.RestWorld.rotation * Vector3.forward, body.transform.forward, bench.Up) : 0;

        /// A step back towards square, where every shot and the work after the crack expect it. True once it is there.
        public bool StepSquare(float dt)
        {
            if (!body) return true;
            float yaw = Yaw, most = 220 * dt;
            if (Mathf.Abs(yaw) > most) { Turn(-Mathf.Sign(yaw) * most); return false; }
            var rest = body.RestWorld; body.transform.SetPositionAndRotation(rest.position, rest.rotation);
            return true;
        }

        /// The vise itself, or something held in it.
        public bool Carries(AssemblyPart p) => body && p && (p.id.StartsWith(BodyId) || p.transform.IsChildOf(body.transform));

        public void Turn(float degrees)
        {
            if (!body || Mathf.Abs(degrees) < 1e-4f) return;
            var t = body.transform;
            AssemblyVerb.Swivel(t, new Pose(t.position, t.rotation), AssemblyVerb.SwivelPivot(body), bench.Up, degrees);
            Travel += Mathf.Abs(degrees);
        }

        public void Grab(Ray ray)
        {
            if (!body) return;
            var hit = bench.Pick(ray, h => h.part && Carries(h.part));
            grabPlane = new Plane(bench.Up, hit.Valid ? hit.point : body.GrabPoint);
            grabbed = true; armKnown = false; lastRay = ray;
        }
        public void Release() { grabbed = false; armKnown = false; }

        /// Held by hand: what was taken hold of follows the pointer round the axis, so a sideways drag and a circle both
        /// work. Near the axis, or with the pointer stopped at the screen's edge, sideways motion turns it.
        public void Drag(in AssemblyInputFrame f)
        {
            if (!grabbed) return;
            bool still = (f.ray.direction - lastRay.direction).sqrMagnitude < 1e-12f;
            lastRay = f.ray;
            var arm = Vector3.zero;
            bool onPlane = grabPlane.Raycast(f.ray, out float t);
            if (onPlane) arm = Vector3.ProjectOnPlane(f.ray.GetPoint(t) - AssemblyVerb.SwivelPivot(body), bench.Up);
            bool usable = onPlane && arm.magnitude > AxisDeadZone && arm.magnitude < FarFromAxis;

            float degrees;
            if (still) degrees = -f.delta.x * DegreesPerPixel;
            else if (usable && armKnown) degrees = Vector3.SignedAngle(lastArm, arm, bench.Up);
            else if (!usable) degrees = -f.delta.x * DegreesPerPixel;
            else degrees = 0;
            Turn(Mathf.Clamp(degrees, -MostPerFrame, MostPerFrame));
            lastArm = arm; armKnown = usable;
        }

        /// V held: the mouse, the wheel, Q or the arrows turn it, whatever is in the hand.
        public void TurnByKey(float dt, in AssemblyInputFrame f)
        {
            float keys = Mathf.Clamp(f.rotate + f.navigate.x, -1, 1);
            Turn(-f.delta.x * DegreesPerPixel + f.scroll * DegreesPerNotch - keys * DegreesPerSecond * dt);
        }
    }
}
