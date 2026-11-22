using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
    /// Everything a verb may read or touch while it works. The session fills it; tests fill it by hand.
    public sealed class AssemblyVerbContext
    {
        public AssemblyBench bench; public AssemblySettings settings; public AssemblyAudio audio; public AssemblyFeedback fx; public AssemblyCameraRig camera;
        public AssemblyStepDef step; public AssemblyActionDef action;
        /// The part handled, the tool in the hand (null = bare hand) and the action's marker when it has one.
        public AssemblyPart part, tool; public AssemblyMarker marker;
        /// Progress kept from an earlier go at the same action (a released screwdriver keeps the screw where it was).
        public float carried;
        public bool reducedMotion;
        /// Where the player's eye is (the camera position): what "facing you" means.
        public Vector3 eye;
        /// Where the keyboard focus ring wants the hand (the mouse form uses the frame's ray).
        public Vector3 focusPoint; public bool hasFocusPoint;
        public WeaponHandling handling;
        /// The session's vise: the crack step turns the same one, so the session sees how far it has gone round.
        public AssemblyViseSwivel vise;
        public float clock;
        public System.Random random = new System.Random(20261120);
    }

    public struct AssemblyVerbStatus
    {
        /// 0 to 1 of the action.
        public float progress;
        public bool done; public float precision;
        /// A fault kind raised this frame (null = none).
        public string fault;
        /// The verb has let go (released, struck, slipped): the hand is free again and `carry` is kept for the next go.
        public bool ended; public float carry;
        /// The verb is between goes (between two taps): the hand may leave for something else, or press again.
        public bool waiting;
        /// A live 0-1 reading: resistance for a turn, the value of a window, alignment of a seat.
        public float value;
        public int count;
    }

    /// One input archetype (DESIGN.md section 6). Each has a mouse form and a keyboard form in the same Tick, reads only
    /// the frame and the context, and reports progress, faults and a precision score.
    public abstract class AssemblyVerb
    {
        public AssemblyVerbContext c;
        public abstract AssemblyVerbKind Kind { get; }
        public virtual void Begin() { }
        public abstract AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f);
        /// Always called when the session drops the verb: stop loops, leave things where they should stay.
        public virtual void End() { }
        /// Where the player should point to do this (QA, hints, the focus ring).
        public virtual Vector3 ActPoint => c.marker ? c.marker.transform.position : c.part ? c.part.GrabPoint : Vector3.zero;

        public static AssemblyVerb Create(AssemblyVerbKind kind)
        {
            switch (kind)
            {
                case AssemblyVerbKind.Seat: return new SeatVerb();
                case AssemblyVerbKind.Turn: return new TurnVerb();
                case AssemblyVerbKind.Path: return new PathVerb();
                case AssemblyVerbKind.Window: return new WindowVerb();
                case AssemblyVerbKind.Wipe: return new WipeVerb();
                case AssemblyVerbKind.Point: return new PointVerb();
                default: return new FlickVerb();
            }
        }

        // ---- shared helpers
        /// How fast a quantity is changing, measured over a short stretch of time and never over one frame: a real pointer
        /// arrives in steps, and at a high frame rate one step in one 3 ms frame looked like a yank (20 Nov, the peel tore
        /// under a slow hand in the player). Push the running total each frame; the rate is per second.
        protected sealed class RateWindow
        {
            readonly Queue<(float time, float total)> samples = new Queue<(float, float)>(); float clock;
            public float Push(float dt, float total, float window = .25f)
            {
                clock += dt; samples.Enqueue((clock, total));
                while (samples.Count > 2 && clock - samples.Peek().time > window) samples.Dequeue();
                var first = samples.Peek(); float span = clock - first.time;
                return span >= window * .5f ? (total - first.total) / span : 0;
            }
        }
        protected string LoopKey => c.step != null && c.action != null ? c.step.id + ":" + c.action.key : "verb";
        protected string FaultKind(string when = "", int index = 0)
        {
            if (c.action == null) return null; int n = 0;
            foreach (var fd in c.action.faults) if ((fd.when ?? "") == when && n++ == index) return fd.kind;
            return null;
        }
        protected bool HasFault(string kind) { if (c.action == null) return false; foreach (var fd in c.action.faults) if (fd.kind == kind) return true; return false; }
        /// Puts a tool so that its tip is at a point and points along a direction.
        /// What turns when the bench swivels a part: the vise's swivel body where the art has one (`fixtures.vise_swivel`), else
        /// the part itself.
        public static AssemblyPart SwivelOf(AssemblyBench bench, AssemblyPart p) => p && p.id == "fixtures.vise" && bench.Part("fixtures.vise_swivel") ? bench.Part("fixtures.vise_swivel") : p;
        /// The vertical axis a swivel turns about: through the middle of the part's own shape (21 Nov, Carl: the vise turned
        /// about a corner, its origin at the front edge of its base), not through its origin.
        public static Vector3 SwivelPivot(AssemblyPart p)
        {
            // the art's split vise (fixtures 20:15: a still fixtures.vise_base, and fixtures.vise the body with its origin on the
            // swivel axis) turns about its own origin; an unsplit one about the middle of its shape
            var bench = p.GetComponentInParent<AssemblyBench>();
            return bench && p.id == "fixtures.vise" && bench.Part("fixtures.vise_base") ? p.transform.position : p.transform.TransformPoint(p.localBounds.center);
        }
        public static void Swivel(Transform t, Pose start, Vector3 pivot, Vector3 up, float degrees)
        {
            var r = Quaternion.AngleAxis(degrees, up); var flat = pivot - up * Vector3.Dot(pivot - start.position, up);   // the axis at the start's height
            t.SetPositionAndRotation(flat + r * (start.position - flat), r * start.rotation);
        }
        /// The way a turning tool works along: from where the hand holds it to its tip (21 Nov, Carl: the screwdriver swept round
        /// like a clock hand; the art's __tip +Z points down out of the blade, across the driver). Tools without both points, or
        /// whose tip +Z already runs along them, keep the tip's +Z.
        public static Vector3 LengthAxis(AssemblyPart tool)
        {
            var tip = tool.tip ? tool.tip : tool.transform;
            if (tool.grab && tool.tip) { var d = tool.tip.position - tool.grab.position; if (d.magnitude > .02f) return d.normalized; }
            return tip.forward;
        }
        /// Right and up as the eye sees them when it looks along `forward` with `worldUp` upright (Unity: right = up x forward).
        public static void ScreenAxes(Vector3 forward, Vector3 worldUp, out Vector3 right, out Vector3 up)
        {
            right = Vector3.Cross(worldUp, forward); if (right.sqrMagnitude < 1e-8f) right = Vector3.Cross(Vector3.forward, forward);
            right.Normalize(); up = Vector3.Cross(forward, right).normalized;
        }
        public static float DistanceToRay(Ray ray, Vector3 point, out Vector3 closest)
        {
            float t = Mathf.Max(0, Vector3.Dot(point - ray.origin, ray.direction)); closest = ray.origin + ray.direction * t;
            return Vector3.Distance(closest, point);
        }
        /// q = twist about `axis` after swing: returns the twist angle in degrees and the swing.
        public static float TwistAbout(Quaternion q, Vector3 axis, out Quaternion swing)
        {
            var inv = Quaternion.Inverse(q); var r = new Vector3(inv.x, inv.y, inv.z); var p = Vector3.Project(r, axis);
            var t = new Quaternion(p.x, p.y, p.z, inv.w);
            float m = Mathf.Sqrt(t.x * t.x + t.y * t.y + t.z * t.z + t.w * t.w);
            t = m < 1e-6f ? Quaternion.identity : new Quaternion(t.x / m, t.y / m, t.z / m, t.w / m);
            var s = inv * Quaternion.Inverse(t);
            var twist = Quaternion.Inverse(t); swing = Quaternion.Inverse(s);
            float angle = 2 * Mathf.Atan2(Vector3.Dot(new Vector3(twist.x, twist.y, twist.z), axis), twist.w) * Mathf.Rad2Deg;
            return Mathf.DeltaAngle(0, angle);
        }
    }

    // =====================================================================================================  Seat
    /// Carry a part, turn it to its key, bring it to its socket; it pulls in when close and aligned. Also every plain
    /// carry (no action): the part follows the hand on a critically damped spring whose stiffness is its mass class,
    /// leans into its motion, and is put down where the hand is. A part still on its parent first comes off along its
    /// own axis, and will not come at all while something holds it.
    public sealed class SeatVerb : AssemblyVerb
    {
        public override AssemblyVerbKind Kind => AssemblyVerbKind.Seat;
        enum Phase { Leaving, Free, PullIn, Done }
        Phase phase;
        Vector3 pos, vel, pressPoint; bool pressSet;
        Quaternion baseRotation, swing = Quaternion.identity; float keyYaw, yaw, yawTarget, slide, turned, misalignedFor, pullT, capturePrecision = 1, blockedNext;
        bool flipped, keyKnown; Pose pullFrom, approach, seated; string originPlace; Pose originPose; float speed;
        public bool Flipped => flipped;
        public float YawError { get; private set; }
        public float DistanceMm { get; private set; } = -1;
        public bool Carrying => phase == Phase.Free || phase == Phase.Leaving;
        public bool Leaving => phase == Phase.Leaving;
        public string OriginPlace => originPlace;
        public float HandSpeed => speed;
        /// On its way into its place: letting go now must not stop it.
        public bool Seating => phase == Phase.PullIn;
        bool canCapture, fromKnown; Vector3 handFrom; float approachFor;
        void PullIn(float precision)
        {
            capturePrecision = precision; pullFrom = new Pose(c.part.transform.position, c.part.transform.rotation);
            approachFor = Mathf.Clamp(Vector3.Distance(pullFrom.position, approach.position) / 1.5f, c.settings.approachSeconds, .22f);
            pullT = 0; phase = Phase.PullIn; misalignedFor = 0;
        }
        /// Let go on its socket while the part is still catching the pointer up: it goes in.
        /// Clicked onto its place with the part in the hand (the punch on the pin): it goes straight there.
        public void SeatNow()
        {
            if (phase != Phase.Free || !c.bench.TargetPose(c.part, Target, out _, out seated, out approach, out _)) return;
            speed = 0; PullIn(1);
        }
        public bool CaptureOnRelease()
        {
            if (phase != Phase.Free || !canCapture) return false;
            speed = 0; PullIn(Mathf.Clamp(1 - .35f * nearness, .4f, 1)); return true;
        }
        /// The target has moved (the vise was turned): find the key again.
        public void Rekey() { keyKnown = false; canCapture = false; }
        string Target => c.action != null && c.action.mode != "inspect" ? c.action.target : "";
        public override Vector3 ActPoint
        {
            get
            {
                if (phase == Phase.Leaving || !c.part) return c.part ? c.part.GrabPoint : Vector3.zero;
                return !string.IsNullOrEmpty(Target) && c.bench.TargetPose(c.part, Target, out _, out var s, out var a, out _) ? a.position : c.part.GrabPoint;
            }
        }

        public override void Begin()
        {
            var p = c.part; originPlace = p.place; originPose = new Pose(p.transform.position, p.transform.rotation);
            pos = p.GrabPoint; vel = Vector3.zero; baseRotation = p.transform.rotation; yaw = yawTarget = 0; flipped = false; keyKnown = false;
            c.fx?.Settle(p); fromKnown = false;
            if (p.place == "seat" && p.hasClear && p.Travel > 1e-4f) { phase = Phase.Leaving; slide = 0; pressSet = false; }
            else Free();
        }

        void Free()
        {
            var p = c.part; phase = Phase.Free;
            if (p.transform.parent != (c.bench.loose ? c.bench.loose : c.bench.transform)) p.transform.SetParent(c.bench.loose ? c.bench.loose : c.bench.transform, true);
            p.place = "held"; baseRotation = p.transform.rotation; pos = p.GrabPoint; yaw = yawTarget = 0; keyKnown = false; canCapture = false;
            // a keyed part on a lead hangs as it likes: it comes to the hand the wrong way up and has to be turned over
            if (c.action != null && c.action.mode == "keyed") flipped = true;
        }

        Vector3 GrabOffset(Quaternion rotation) => c.part.GrabOffsetAt(rotation);
        /// Degrees the part has been turned in the hand since it was picked up (looking it over).
        public float Turned => turned;
        float nearness = 1;

        public override AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var p = c.part; var s = c.settings; var bench = c.bench;
            if (phase == Phase.Done) { st.done = true; st.progress = 1; st.precision = capturePrecision; return st; }
            bool usePointer = f.pointer && !c.hasFocusPoint;

            if (phase == Phase.Leaving)
            {
                // off its parent along its own axis; any drag away from where it was taken pulls it
                if (usePointer && !fromKnown) { handFrom = bench.OnSurface(f.ray, s.carryLift); fromKnown = true; }
                var plane = usePointer ? bench.OnSurface(f.ray, bench.HeightAbove(p.RestWorld.position)) : c.focusPoint;
                if (!pressSet) { pressPoint = plane; pressSet = true; }
                float want = usePointer ? Mathf.Clamp01(Vector3.Distance(plane, pressPoint) / Mathf.Max(.035f, p.Travel)) : Mathf.Clamp01(slide + dt / .35f);
                slide = Mathf.MoveTowards(slide, want, dt * s.Spring(p.mass) * .35f);
                var rest = p.RestWorld; var clear = p.ClearWorld;
                p.transform.SetPositionAndRotation(Vector3.Lerp(rest.position, clear.position, slide), Quaternion.Slerp(rest.rotation, clear.rotation, slide));
                st.progress = slide * .5f; st.value = slide;
                bool letGo = c.action != null && c.action.keepHold && !f.primaryHeld;
                if (slide >= .999f)
                {
                    c.audio?.Contact(p.material, bench.ContactMaterial(p, "seat"), p.GrabPoint, .55f);
                    if (Target == "clear") { bench.Put(p, "clear"); phase = Phase.Done; capturePrecision = 1; st.done = true; st.progress = 1; st.precision = 1; return st; }
                    Free();
                }
                else if (letGo)
                {
                    bench.Put(p, "seat"); st.ended = true;
                    if (c.action != null && c.action.keepHold && slide > .15f) st.fault = FaultKind() ?? "flew_off";
                    return st;
                }
                return st;
            }

            if (phase == Phase.PullIn)
            {
                pullT += dt;
                float a = approachFor, b = s.pullInSeconds;
                if (pullT < a) { float k = pullT / a; k = k * k * (3 - 2 * k); p.transform.SetPositionAndRotation(Vector3.Lerp(pullFrom.position, approach.position, k), Quaternion.Slerp(pullFrom.rotation, approach.rotation, k)); }
                else if (pullT < a + b) { float k = (pullT - a) / b; k *= k; p.transform.SetPositionAndRotation(Vector3.Lerp(approach.position, seated.position, k), Quaternion.Slerp(approach.rotation, seated.rotation, k)); }
                else
                {
                    bench.Put(p, Target);
                    c.audio?.Contact(p.material, bench.ContactMaterial(p, Target), seated.position);
                    if (!string.IsNullOrEmpty(c.action.done)) c.audio?.Play(c.action.done, seated.position);
                    if (!c.reducedMotion) c.camera?.Nudge(seated.position - approach.position, s.cameraNudgeMm * .001f);
                    c.fx?.Flash(p, s.rimFlashSeconds);
                    phase = Phase.Done; st.done = true; st.precision = capturePrecision;
                    if (speed > s.fumbleSpeed && HasFault("rolled_off")) st.fault = "rolled_off";
                }
                st.progress = Mathf.Clamp01(.6f + .4f * pullT / (a + b)); st.value = 1;
                return st;
            }

            // ---- free carry
            if (f.flip) { flipped = !flipped; turned += 180; c.audio?.Play("asm.kit.tool", pos, .4f); }
            float dYaw = f.scroll * s.yawPerNotch + f.rotate * s.yawPerSecond * dt;
            yawTarget += dYaw; turned += Mathf.Abs(dYaw);
            var up = bench.Up;
            AssemblyMarker place = null;
            bool hasTarget = !string.IsNullOrEmpty(Target) && bench.TargetPose(p, Target, out _, out seated, out approach, out place);
            float w = 0, tolMm = 0, tolDeg = 0; int symmetry = 1; Vector3 handGrab;
            var planeGrab = usePointer ? bench.OnSurface(f.ray, s.carryLift) : bench.ClampToReach(c.focusPoint + up * (s.carryLift - bench.HeightAbove(c.focusPoint)));
            if (hasTarget)
            {
                tolMm = c.action.tolMm > 0 ? c.action.tolMm : place && place.tolMm > 0 ? place.tolMm : p.tolMm;
                tolDeg = c.action.tolDeg > 0 ? c.action.tolDeg : place && place.tolDeg > 0 ? place.tolDeg : p.tolDeg;
                symmetry = place && place.symmetry >= 0 ? place.symmetry : p.symmetry;
                if (usePointer && place && c.action.mode != "keyed")
                {
                    // over the mat, the pad or the tray it drops into place: no aiming, and it squares itself up (22 Nov, Carl)
                    var hand = bench.OnSurface(f.ray, s.carryLift);
                    if (!fromKnown) { handFrom = hand; fromKnown = true; }
                    if (Vector3.Distance(hand, handFrom) > s.snapAfterMove && bench.OverDropArea(place, f.ray, seated.position))
                    {
                        flipped = false; speed = 0; DistanceMm = 0; YawError = 0;
                        PullIn(1); st.value = 1; st.progress = .6f; return st;
                    }
                }
                if (!keyKnown) { keyYaw = TwistAbout(approach.rotation * Quaternion.Inverse(baseRotation), up, out swing); keyKnown = true; }
                // the socket draws the part in when the pointer is over it or over the way into it
                var approachGrab = approach.position + GrabOffset(approach.rotation); var seatedGrab = seated.position + GrabOffset(seated.rotation);
                float inner = Mathf.Max(.03f, tolMm * .001f), reach = Mathf.Max(.085f, tolMm * .004f), near = float.MaxValue;
                if (usePointer) for (int i = 0; i <= 4; i++) near = Mathf.Min(near, DistanceToRay(f.ray, Vector3.Lerp(approachGrab, seatedGrab, i / 4f), out _));
                else near = Vector3.Distance(c.focusPoint, seated.position) < .02f || Vector3.Distance(c.focusPoint, approach.position) < .02f ? 0 : Vector3.Distance(Vector3.ProjectOnPlane(c.focusPoint - approachGrab, up), Vector3.zero);
                float x = Mathf.InverseLerp(inner, reach, near); w = 1 - x * x * (3 - 2 * x); nearness = Mathf.Clamp01(near / inner);
                handGrab = Vector3.Lerp(planeGrab, approachGrab, w);
            }
            else handGrab = planeGrab;

            // the spring: critically damped, stiffness by mass class
            // (the exact step of a critically damped spring: it lags, it never overshoots, at any frame rate)
            float omega = s.Spring(p.mass), decay = Mathf.Exp(-omega * dt);
            var offset = pos - handGrab; var carryOn = (vel + offset * omega) * dt;
            vel = (vel - carryOn * omega) * decay; pos = handGrab + (offset + carryOn) * decay; speed = vel.magnitude;
            // the key: within reach of the socket a part that is nearly square finds its key
            float err = 0;
            if (hasTarget)
            {
                float period = symmetry <= 0 ? 0 : 360f / symmetry;
                err = symmetry <= 0 ? 0 : Mathf.DeltaAngle(0, yawTarget - keyYaw);
                if (period > 0 && period < 360) err = Mathf.Repeat(err + period * .5f, period) - period * .5f;
                if (symmetry <= 0) yawTarget = Mathf.LerpAngle(yawTarget, keyYaw, w);
                else if (w > .5f && Mathf.Abs(err) < Mathf.Max(9, tolDeg * .5f)) { yawTarget -= err * (1 - Mathf.Exp(-10 * dt)); }
            }
            yaw = Mathf.Lerp(yaw, yawTarget, 1 - Mathf.Exp(-s.yawFollow * dt));
            YawError = Mathf.Abs(err);
            var lean = Vector3.ProjectOnPlane(vel, up); float tilt = c.reducedMotion ? 0 : Mathf.Min(s.tiltMax, lean.magnitude * s.tiltPerSpeed) * (1 - w);
            var rotation = Quaternion.AngleAxis(yaw, up) * Quaternion.Slerp(Quaternion.identity, swing, hasTarget ? w : 0) * baseRotation;
            if (flipped) rotation = rotation * Quaternion.Euler(0, 0, 180);
            if (tilt > .01f) rotation = Quaternion.AngleAxis(tilt, Vector3.Cross(up, lean.normalized)) * rotation;
            p.transform.rotation = rotation; p.transform.position += pos - p.GrabPoint;

            if (!hasTarget) { DistanceMm = -1; return st; }
            // how far the hold point is from where it must be to go in (not origin to origin: a part that may go in either way
            // round, held off its middle, has its origin somewhere else when it is the other way round)
            float off = Vector3.Distance(pos, approach.position + GrabOffset(approach.rotation));
            DistanceMm = off * 1000; st.value = w; st.progress = .5f + .1f * w;
            bool square = Mathf.Abs(err) <= tolDeg && !flipped;
            canCapture = usePointer && square && w >= .95f;
            if (off <= tolMm * .001f && square)
            {
                PullIn(Mathf.Clamp(1 - .35f * nearness - .25f * (Mathf.Abs(err) / Mathf.Max(1, tolDeg)), .4f, 1));
            }
            else if (off <= tolMm * .003f && !square)
            {
                // close but not square, upside down or the wrong way round: it will not start
                misalignedFor += dt;
                if (misalignedFor > .5f && c.clock >= blockedNext)
                {
                    blockedNext = c.clock + 1.2f; misalignedFor = 0;
                    c.audio?.Play("asm.seat.blocked", approach.position, .7f); c.fx?.Shudder(p, s.shudderMm * .001f, s.shudderSeconds);
                    st.fault = FaultKind("misaligned") ?? (HasFault("misaligned") ? "misaligned" : null); Refusals++;
                }
            }
            else misalignedFor = 0;
            return st;
        }
        /// Times the part has refused to seat because it was not square (QA).
        public int Refusals { get; private set; }
        /// Puts the part down where the hand is (not seated). Back to where it came from when that is right under it.
        public void PutDown()
        {
            var p = c.part; var bench = c.bench;
            if (phase == Phase.Leaving) { bench.Put(p, "seat"); return; }
            if (phase != Phase.Free) return;
            if (!string.IsNullOrEmpty(originPlace) && originPlace != "held" && originPlace != "loose" && originPlace != "gone" && Vector3.Distance(Vector3.ProjectOnPlane(p.transform.position - originPose.position, bench.Up), Vector3.zero) < .05f)
            { bench.Put(p, originPlace); c.audio?.Contact(p.material, bench.ContactMaterial(p, originPlace), p.GrabPoint, .7f); return; }
            // lower it until it rests on whatever is under it, in sight
            var rot = Quaternion.AngleAxis(yaw, bench.Up) * baseRotation; if (flipped) rot = rot * Quaternion.Euler(0, 0, 180);
            p.transform.rotation = rot;
            bench.Support.Rest(p);
            bench.Drop(p, new Pose(p.transform.position, p.transform.rotation));
            c.audio?.Contact(p.material, "rubber", p.GrabPoint, .7f);
        }

        /// Back where it was picked up from (Esc, or a carry that cannot go on).
        public void Return()
        {
            var p = c.part; if (!p || phase == Phase.Done) return;
            if (originPlace == "seat" || originPlace == "clear" || c.bench.Marker(originPlace)) c.bench.Put(p, originPlace);
            else c.bench.Drop(p, originPose);
        }
    }

    // =====================================================================================================  Turn
    /// Hold on a target and turn against resistance: a circle round it with the mouse, the wheel, or a held key.
    /// Resistance is carried by how far the part moves per unit of input (the action's gain), the loop's pitch and the
    /// tool's vibration, never by a gauge.
    public sealed class TurnVerb : AssemblyVerb
    {
        public override AssemblyVerbKind Kind => AssemblyVerbKind.Turn;
        AssemblyViseSwivel swivel;
        float turned, lastAngle, settle, spin, handTurns, netTurns, wayRound; bool angleSet, over, slipped, onParent; readonly RateWindow hand = new RateWindow(); Quaternion startRotation; Vector3 pivot, axis, centre;
        float Need => Mathf.Max(.01f, Mathf.Abs(c.action.turns));
        float Sign => c.action.turns < 0 ? -1 : 1;
        public float Turned => turned;
        public override Vector3 ActPoint => c.part ? c.part.GrabPoint : base.ActPoint;

        public override void Begin()
        {
            turned = c.carried; angleSet = false; over = false; settle = 0; slipped = false; netTurns = wayRound = 0;
            var p = c.part; onParent = p.OnParent; pivot = centre = p.GrabPoint; axis = AssemblyToolPose.TurnAxis(p); startRotation = p.transform.localRotation;
            if (!string.IsNullOrEmpty(c.action.loop)) c.audio?.Loop(LoopKey, c.action.loop, pivot);
        }

        public override AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var a = c.action; var s = c.settings; var p = c.part;
            if (a.mode == "reveal") return Reveal(dt, f);
            float input = 0;
            if (f.pointer && !f.keyboard)
            {
                // a circle round where the turn began (the screw walks out along its thread; the hand's circle does not chase it),
                // measured in the plane that faces the eye
                var normal = (f.ray.origin - centre).normalized; var plane = new Plane(normal, centre);
                if (plane.Raycast(f.ray, out float t))
                {
                    var d = f.ray.GetPoint(t) - centre;
                    // the screen's own right and up at the pivot: the eye looks along -normal (20 Nov: this basis was mirrored,
                    // so a clockwise circle on the screen backed the turn off)
                    ScreenAxes(-normal, c.bench.Up, out var right, out var upv);
                    if (d.magnitude > s.circleMinRadiusMm * .001f)
                    {
                        float angle = Mathf.Atan2(Vector3.Dot(d, upv), Vector3.Dot(d, right)) * Mathf.Rad2Deg;
                        if (angleSet) input -= Mathf.DeltaAngle(lastAngle, angle) / 360f;   // clockwise as the player sees it is positive
                        lastAngle = angle; angleSet = true;
                    }
                    else angleSet = false;
                }
                input += f.scroll * s.turnsPerNotch * Sign;
            }
            else
            {
                float dir = Mathf.Abs(f.navigate.x) > .5f ? Mathf.Sign(f.navigate.x) : Sign;
                input = dir * s.keyTurnsPerSecond * dt;
            }
            handTurns += Mathf.Abs(input); float rate = Mathf.Abs(hand.Push(dt, handTurns));   // turns of the hand per second, over a quarter of a second
            float along = input * Sign * a.gain;
            if (a.mode != "stop" && (a.noSpin || !string.IsNullOrEmpty(a.drive) && a.turns < 0))
            {
                // a latch, a strap, a vise being opened: either way round works it (22 Nov: the wrong way silently did nothing)
                netTurns += input;
                if (wayRound != 0)
                {
                    along = input * wayRound * a.gain;
                    if (turned + along <= 0) { wayRound = netTurns = 0; }   // taken all the way back: either way starts it again
                }
                else if (Mathf.Abs(netTurns) > .03f) { wayRound = Mathf.Sign(netTurns); along = Mathf.Abs(netTurns) * a.gain; }
                else along = 0;
            }
            float before = turned, raw = Mathf.Max(0, turned + along);
            // a stop is a stop: turns past the band do not pile up out of sight (22 Nov: the step could then never finish)
            bool pastStop = a.mode == "stop" && raw > Need + a.hi + .12f;
            turned = a.mode == "stop" ? Mathf.Min(raw, Need + a.hi + .12f) : raw;
            float progress = Mathf.Clamp01(turned / Need);
            // resistance: stiff threads, and the load coming on at the end of a stop turn
            float resistance = Mathf.Clamp01(1 - a.gain);
            if (a.mode == "stop") resistance = Mathf.Clamp01(Mathf.Max(resistance, (turned - Need * .7f) / (Need * .3f + Mathf.Max(.01f, a.hi))));
            st.value = resistance; st.progress = progress; st.carry = turned;

            // the part: fasteners travel along their thread, everything else turns in place; a mechanism follows
            float deg = (turned - before) * Sign * 360f;
            spin += deg;
            if (p.IsFastener && p.hasClear && string.IsNullOrEmpty(a.drive) && onParent)
            {
                var rest = p.RestWorld; var clear = p.ClearWorld; float k = a.turns < 0 ? progress : 1 - progress;
                p.transform.SetPositionAndRotation(Vector3.Lerp(rest.position, clear.position, k), Quaternion.AngleAxis(spin, axis) * Quaternion.Slerp(rest.rotation, clear.rotation, k));
            }
            else if (!a.noSpin && !string.IsNullOrEmpty(p.spinParam) && c.bench.Param(p.spinParam) is AssemblyParam own && own.continuous)
            {
                // a part that rides a continuous param of its rig (the vise screw on its handle bone) turns through the param, about
                // the axis the art gives, so it stays on its thread; positive turns close (fixtures.vise_handle's note)
                if (turned != before) own.Set(own.Turns + (turned - before) * (a.turns < 0 ? -1 : 1) / Mathf.Max(.05f, Mathf.Abs(a.gain)));
            }
            else if (!a.noSpin) p.transform.localRotation = Quaternion.AngleAxis(spin, p.transform.parent ? p.transform.parent.InverseTransformDirection(axis) : axis) * startRotation;
            if (!string.IsNullOrEmpty(a.drive)) { var m = c.bench.Param(a.drive); if (m) m.Set(Mathf.Lerp(a.from, a.to, progress)); }
            // a tool with a crank of its own (the hand drill): the wheel turns with the hand, the spindle and bit with it at its ratio
            if (c.tool && !string.IsNullOrEmpty(c.tool.spinParam) && turned != before) { var sp = c.bench.Param(c.tool.spinParam); if (sp) sp.Set(sp.Turns + (turned - before) / Mathf.Max(.05f, Mathf.Abs(a.gain))); }
            pivot = p.GrabPoint;
            if (c.tool)
            {
                var buzz = c.reducedMotion ? Vector3.zero : UnityEngine.Random.insideUnitSphere * (s.buzzMm * .001f * resistance * Mathf.Clamp01(rate));
                // a screwdriver turns as a whole; a drill stands and turns its crank (its spinParam) instead
                AssemblyToolPose.Place(c.bench, c.tool, pivot + buzz, -axis, default, string.IsNullOrEmpty(c.tool.spinParam) ? spin : 0);
            }
            c.audio?.SetLoop(LoopKey, resistance, Mathf.Clamp01(rate * 1.2f));

            // a stiff screw turned too fast throws the bit out
            if (!f.keyboard && a.gain < .6f && rate > s.camOutSpeed && HasFault("camout") && !slipped)
            {
                slipped = true; turned = Mathf.Max(0, turned - .25f); st.carry = turned; st.fault = "camout"; st.ended = true; return st;
            }
            // driven too fast where the work will not take it (the copper snaps on the bobbin, the drill binds)
            if (!f.keyboard && rate > s.camOutSpeed && FaultKind("fast") != null && !slipped)
            {
                slipped = true; turned = Mathf.Max(0, turned - .5f); st.carry = turned; st.fault = FaultKind("fast"); st.ended = true; return st;
            }
            if (a.mode == "stop")
            {
                float lo = Need + a.lo, hi = Need + a.hi;
                if (pastStop)
                {
                    // too tight costs quality once, and it is tight: the action is over
                    over = true; turned = hi; st.carry = turned; st.fault = FaultKind() ?? "overtight";
                    st.done = true; st.precision = .55f; return st;
                }
                bool inBand = turned >= lo;
                settle = inBand && Mathf.Abs(along) < 1e-4f ? settle + dt : 0;
                if (inBand && (!f.primaryHeld || settle >= s.stopSettleSeconds))
                {
                    st.done = true; st.precision = over ? .55f : Mathf.Clamp(1 - .4f * (turned - lo) / Mathf.Max(.01f, hi - lo), .6f, 1);
                    return st;
                }
            }
            else if (turned >= Need) { st.done = true; st.precision = slipped ? .7f : 1; return st; }
            if (!f.primaryHeld) st.ended = true;
            return st;
        }

        /// Turning the vise to look for a mark: it follows the hand and stays where it is left. The session decides when the
        /// mark has been found (AssemblySession.WatchReveal), so turning it any other way counts as well.
        AssemblyVerbStatus Reveal(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus();
            if (swivel == null) { swivel = c.vise ?? new AssemblyViseSwivel(c.bench); swivel.Grab(f.ray); }
            if (!f.primaryHeld) { st.ended = true; return st; }
            if (f.pointer && !f.keyboard) swivel.Drag(f);
            else swivel.Turn(-(Mathf.Abs(f.navigate.x) > .5f ? Mathf.Sign(f.navigate.x) : 1) * 80 * dt);
            if (c.marker) st.value = Mathf.Clamp01((Vector3.Dot(c.bench.Out(c.marker.transform), (c.eye - c.marker.transform.position).normalized) + 1) * .5f);
            st.progress = st.value;
            return st;
        }
        public override void End() { c.audio?.StopLoop(LoopKey); swivel?.Release(); }
    }

    // =====================================================================================================  Window
    /// Hold or strike, and stop inside a window read from sound and position. Hold: a value rises while the button is
    /// down and the release is what counts (torque, pressure, heat). Strike: the tool rises while held and falls on
    /// release, the height being the force (taps on a punch).
    public sealed class WindowVerb : AssemblyVerb
    {
        public override AssemblyVerbKind Kind => AssemblyVerbKind.Window;
        float value, held, precisionSum, knit, total, outFor; int count, counted; bool wasHeld, mustRelease, everIn, voided; Vector3 strikePoint;
        /// Sustain: seconds spent inside the band so far.
        public float Knit => knit;
        public float Value => value;
        public override void Begin()
        {
            count = Mathf.RoundToInt(c.carried); value = 0; held = 0; wasHeld = false; mustRelease = false; counted = 0; precisionSum = 0; strikePoint = ActPoint;
            knit = c.action.mode == "sustain" ? c.carried : 0; total = knit; outFor = 0; everIn = knit > 0; voided = false;
            if (c.action.mode != "strike" && !string.IsNullOrEmpty(c.action.loop)) c.audio?.Loop(LoopKey, c.action.loop, strikePoint);
        }
        /// A strike lands on the tool standing on the part (the punch on the pin) when the action names one.
        public override Vector3 ActPoint { get { var t = c.bench.Part(c.action.target); if (t && !t.Gone) return t.GrabPoint; var m = !string.IsNullOrEmpty(c.action.target) ? c.bench.Marker(c.action.target) : null; return m ? m.transform.position : c.part ? c.part.GrabPoint : base.ActPoint; } }   // a strike lands on its mark where it names one (the pin's punch end)
        float Score(float v) { var a = c.action; return 1 - .5f * Mathf.Abs(v - (a.lo + a.hi) * .5f) / Mathf.Max(.01f, (a.hi - a.lo) * .5f); }

        public override AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var a = c.action; var s = c.settings; var p = c.part;
            st.count = count; st.carry = count; st.progress = (float)count / Mathf.Max(1, a.count);
            bool strike = a.mode == "strike";
            if (a.mode == "sustain") return Sustain(dt, f);
            if (mustRelease) { if (!f.primaryHeld) mustRelease = false; st.waiting = !f.primaryHeld; return st; }
            if (f.primaryHeld)
            {
                wasHeld = true; held += dt;
                value = strike ? Mathf.Clamp01(held / s.strikeRaiseSeconds) : Mathf.Clamp(value + a.rate * dt, 0, 1.2f);
                st.value = value;
                if (strike)
                {
                    if (c.tool)
                    {
                        var blow = AssemblyToolPose.Work(c.bench, a, p, c.marker, c.tool);
                        AssemblyToolPose.Place(c.bench, c.tool, blow.at, blow.into);
                        AssemblyToolPose.DrawBack(c.tool, blow.into, value, s.strikeLift);
                    }
                    return st;
                }
                if (!string.IsNullOrEmpty(a.drive)) { var m = c.bench.Param(a.drive); if (m) m.Set(Mathf.Lerp(a.from, a.to, Mathf.Clamp01(value / Mathf.Max(.01f, a.hi)))); }
                c.audio?.SetLoop(LoopKey, Mathf.InverseLerp(0, Mathf.Max(.01f, a.hi), value), .8f);
                if (c.tool)
                {
                    var work = AssemblyToolPose.Work(c.bench, a, p, c.marker, c.tool);
                    bool filing = c.tool.HasTag("tool:file") || c.tool.HasTag("tool:file_round"), driving = c.tool.HasTag("tool:screwdriver");
                    AssemblyToolPose.Place(c.bench, c.tool, work.at, work.into, default, driving ? 25 * held : 0);
                    if (filing && !c.reducedMotion) c.tool.transform.position += (c.tool.TipPoint - c.tool.GrabPoint).normalized * (Mathf.Sin(held * 10) * .015f);
                }
                st.progress = (count + Mathf.Clamp01(value / Mathf.Max(.01f, a.lo)) * .9f) / Mathf.Max(1, a.count);
                if (value > a.hi + s.overMargin) { st.fault = FaultKind() ?? "over"; value = 0; held = 0; wasHeld = false; mustRelease = true; c.audio?.SetLoop(LoopKey, 0, 0); }
                return st;
            }
            if (!wasHeld) { st.waiting = true; return st; }
            // released: the strike lands, or the hold is judged
            st.value = value; bool inWindow = value >= a.lo && value <= a.hi;
            if (strike)
            {
                var landed = AssemblyToolPose.Work(c.bench, a, p, c.marker, c.tool);
                if (c.tool) AssemblyToolPose.Place(c.bench, c.tool, landed.at, landed.into);
                if (value < a.lo) c.audio?.Play(a.audio + ".strike", strikePoint, .3f, 0);
                else
                {
                    count++; counted++; precisionSum += inWindow ? Score(value) : .35f;
                    c.audio?.Play(a.audio + ".strike", strikePoint, 1, value);
                    if (p && p.hasClear && p.OnParent) { float k = Mathf.Lerp(a.from, a.to, (float)count / Mathf.Max(1, a.count)); var rest = p.RestWorld; var clear = p.ClearWorld; p.transform.SetPositionAndRotation(Vector3.Lerp(rest.position, clear.position, k), Quaternion.Slerp(rest.rotation, clear.rotation, k)); }
                    if (!c.reducedMotion) c.camera?.Nudge(landed.into, s.cameraNudgeMm * .0006f);
                    if (value > a.hi) { st.fault = FaultKind() ?? "miss"; c.audio?.Play(a.audio + ".miss", strikePoint); }
                }
            }
            else if (inWindow) { count++; counted++; precisionSum += Score(value); if (!string.IsNullOrEmpty(a.audio)) c.audio?.Play(a.audio + ".seat", strikePoint); }
            else if (value > a.hi) st.fault = FaultKind() ?? "over";
            else if (value > .15f) st.fault = FaultKind("under");   // let go short of the window, where that is a mistake of its own (a cold joint)
            value = 0; held = 0; wasHeld = false;
            st.count = count; st.carry = count; st.progress = (float)count / Mathf.Max(1, a.count);
            if (count >= a.count) { st.done = true; st.precision = Mathf.Clamp((precisionSum + (count - counted) * .8f) / Mathf.Max(1, count), .3f, 1); }
            else st.waiting = true;
            return st;
        }
        /// Pump to the band and keep it there while the work goes on (the press while the nanites knit): the value rises
        /// while held and falls away when let go, time in the band is progress, and a long spell out of it leaves a void.
        AssemblyVerbStatus Sustain(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var a = c.action; var s = c.settings; float need = Mathf.Max(.5f, a.seconds);
            value = f.primaryHeld ? Mathf.Min(1.2f, value + a.rate * dt) : Mathf.Max(0, value - a.rate * s.sustainDrift * dt);
            bool inBand = value >= a.lo && value <= a.hi;
            if (inBand) { knit += dt; everIn = true; outFor = 0; }
            else if (everIn) { outFor += dt; if (outFor >= s.sustainVoidSeconds) { outFor = 0; voided = true; st.fault = FaultKind() ?? "void"; } }
            if (everIn) total += dt;
            if (!string.IsNullOrEmpty(a.drive)) c.bench.ApplyEffect(a.drive + "=" + (inBand ? 1f : Mathf.Clamp01(value) * .35f).ToString(System.Globalization.CultureInfo.InvariantCulture));
            c.audio?.SetLoop(LoopKey, Mathf.InverseLerp(0, Mathf.Max(.01f, a.hi), value), inBand ? 1 : .45f);
            st.value = value; st.progress = Mathf.Clamp01(knit / need); st.carry = knit; st.waiting = !f.primaryHeld;
            if (knit >= need) { st.done = true; st.waiting = false; st.precision = Mathf.Clamp((voided ? .7f : 1) * knit / Mathf.Max(knit, total), .3f, 1); }
            return st;
        }
        public override void End() { c.audio?.StopLoop(LoopKey); }
    }

    // =====================================================================================================  Point
    /// Aim at a small mark and click. Exact is good; a click beside the mark still does the job but badly, where the
    /// action says so. The aim form is the test card: the muzzle wanders by the weapon's handling and each click is a
    /// pulse through the card where the dot is.
    public sealed class PointVerb : AssemblyVerb
    {
        public override AssemblyVerbKind Kind => AssemblyVerbKind.Point;
        int count; float phase, kick, side; public Vector3 AimPoint { get; private set; }
        public readonly List<Vector3> Hits = new List<Vector3>();
        public override void Begin() { count = Mathf.RoundToInt(c.carried); phase = (float)c.random.NextDouble() * 6f; }

        public override AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var a = c.action; var s = c.settings;
            if (a.mode == "aim") return Aim(dt, f);
            // one click on one mark
            var mark = c.marker; st.carry = c.carried;
            if (!mark) { st.ended = true; return st; }
            float tol = (a.tolMm > 0 ? a.tolMm : s.pointTolMm) * .001f;
            float d = f.pointer && !f.keyboard ? DistanceToRay(f.ray, mark.transform.position, out _) : tol * .2f;
            if (c.tool) AssemblyToolPose.Place(c.bench, c.tool, mark.transform.position, -c.bench.Out(mark.transform));
            if (d > tol * 3) { st.ended = true; return st; }
            st.count = 1; st.done = true; st.progress = 1;
            st.precision = d <= tol ? 1 - .4f * d / tol : .4f;
            if (d > tol) st.fault = FaultKind();
            if (!string.IsNullOrEmpty(a.audio)) c.audio?.Play(a.audio, mark.transform.position);
            c.fx?.Flash(c.bench.Part(mark.ownerPart), .18f);
            return st;
        }

        AssemblyVerbStatus Aim(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var a = c.action; var s = c.settings; var card = c.marker;
            st.count = count; st.carry = count; st.progress = (float)count / Mathf.Max(1, a.count);
            if (!card) { st.ended = true; return st; }
            var plane = new Plane(card.transform.forward, card.transform.position);
            Vector3 centre = f.pointer && !f.keyboard && plane.Raycast(f.ray, out float t) ? f.ray.GetPoint(t) : card.transform.position;
            float distance = Mathf.Max(.2f, Vector3.Distance(c.eye, card.transform.position));
            // the wander: a slow figure of eight plus what is left of the last kick
            phase += dt * 2 * Mathf.PI / Mathf.Max(.2f, s.aimSwayPeriod);
            float sway = Mathf.Tan(Mathf.Max(0, c.handling.sway) * s.aimSwayScale * Mathf.Deg2Rad) * distance;
            float recover = Mathf.Max(.05f, c.handling.recovery);
            kick = Mathf.Lerp(kick, 0, 1 - Mathf.Exp(-dt * 3 / recover)); side = Mathf.Lerp(side, 0, 1 - Mathf.Exp(-dt * 3 / recover));
            var offset = card.transform.right * (Mathf.Sin(phase) * sway + side) + card.transform.up * (Mathf.Sin(phase * 2) * sway * .5f + kick);
            AimPoint = centre + offset;
            float half = Mathf.Max(.03f, card.size.x);
            bool onCard = Vector3.Distance(Vector3.ProjectOnPlane(AimPoint - card.transform.position, card.transform.forward), Vector3.zero) < half * 1.6f;
            st.value = onCard ? 1 : 0;
            if (f.primaryDown && onCard)
            {
                Hits.Add(AimPoint); count++;
                c.audio?.Play("asm.pulse.shot", c.part ? c.part.GrabPoint : AimPoint); c.audio?.Play("asm.pulse.hit", AimPoint, .8f);
                float k = Mathf.Tan(Mathf.Max(0, c.handling.kick) * Mathf.Deg2Rad) * distance, sd = Mathf.Tan(Mathf.Max(0, c.handling.sideStep) * Mathf.Deg2Rad) * distance;
                kick += k; side += sd * (c.random.NextDouble() < .5 ? -1 : 1);
                if (!c.reducedMotion) c.camera?.Nudge(c.bench.Up, s.cameraNudgeMm * .0008f);
                st.count = count; st.carry = count; st.progress = (float)count / Mathf.Max(1, a.count);
                if (count >= a.count) { st.done = true; st.precision = 1; }
            }
            else if (f.pointer && !onCard && f.primaryDown) st.ended = true;
            return st;
        }
    }

    // =====================================================================================================  Flick
    /// Throw the mouse, or shake a held object: the object answers with its state (the bare pistol rattles and keeps
    /// swaying, the finished one settles with one tick). The keyboard form is a held key.
    public sealed class FlickVerb : AssemblyVerb
    {
        public override AssemblyVerbKind Kind => AssemblyVerbKind.Flick;
        int reversals; float lastSign, window, held; Vector3 lastHand; bool handSet;
        public override AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var s = c.settings; var a = c.action;
            int need = a.count > 1 ? a.count : s.flickReversals;
            if (f.pointer && !f.keyboard)
            {
                var hand = c.bench.OnSurface(f.ray, s.carryLift);
                if (handSet && dt > 0)
                {
                    var v = (hand - lastHand) / dt; var flat = Vector3.ProjectOnPlane(v, c.bench.Up);
                    float along = Mathf.Abs(flat.x) >= Mathf.Abs(flat.z) ? flat.x : flat.z;
                    if (Mathf.Abs(along) >= s.flickSpeed)
                    {
                        float sign = Mathf.Sign(along);
                        if (lastSign != 0 && sign != lastSign) { reversals++; window = s.flickWindow; if (!string.IsNullOrEmpty(a.audio)) c.audio?.Play(a.audio, c.part ? c.part.GrabPoint : hand, .8f); }
                        lastSign = sign;
                    }
                }
                lastHand = hand; handSet = true;
                if (window > 0) { window -= dt; if (window <= 0) { reversals = 0; lastSign = 0; } }
                st.progress = Mathf.Clamp01((float)reversals / need);
            }
            else
            {
                held = f.primaryHeld ? held + dt : 0;
                float seconds = a.seconds > 0 ? a.seconds : s.flickHoldSeconds;
                if (f.primaryHeld && c.part && !c.reducedMotion) c.part.transform.position += c.bench.Up * (Mathf.Sin(c.clock * 38) * .0015f);
                if (f.primaryHeld && !string.IsNullOrEmpty(a.audio) && Mathf.FloorToInt(held * 5) != Mathf.FloorToInt((held - dt) * 5)) c.audio?.Play(a.audio, c.part ? c.part.GrabPoint : c.focusPoint, .8f);
                st.progress = Mathf.Clamp01(held / seconds);
                if (held >= seconds) reversals = need;
            }
            st.count = reversals;
            if (reversals >= need) { st.done = true; st.precision = 1; }
            return st;
        }
    }

    // =====================================================================================================  Path
    /// Follow a line at a steady pace. Wander is marked and costs quality; going too fast tears, where the action says
    /// so. Keyboard form: hold to move along at an even pace and keep the tip on the line with A / D as it drifts.
    public sealed class PathVerb : AssemblyVerb
    {
        public override AssemblyVerbKind Kind => AssemblyVerbKind.Path;
        float along, length, errorSum, errorTime, drift, paced, swivelYaw; bool swivelSet, swingingBack; Pose swivelStart; Vector3 swivelAt; AssemblyPart swivelPart; readonly List<Vector3> pts = new List<Vector3>(); readonly RateWindow travel = new RateWindow();
        public float Along => length > 0 ? along / length : 0;
        public override Vector3 ActPoint => PointAt(along);
        void Read()
        {
            pts.Clear(); length = 0;
            if (c.marker) foreach (var t in c.marker.points) if (t) pts.Add(t.position);
            for (int i = 1; i < pts.Count; i++) length += Vector3.Distance(pts[i - 1], pts[i]);
        }
        Vector3 PointAt(float s)
        {
            if (pts.Count == 0) Read();
            if (pts.Count == 0) return c.marker ? c.marker.transform.position : Vector3.zero;
            for (int i = 1; i < pts.Count; i++) { float d = Vector3.Distance(pts[i - 1], pts[i]); if (s <= d || i == pts.Count - 1) return Vector3.Lerp(pts[i - 1], pts[i], d > 0 ? Mathf.Clamp01(s / d) : 1); s -= d; }
            return pts[pts.Count - 1];
        }
        /// The angle (degrees about the bench normal) that would bring the line at `s` round to face the eye.
        public static float FacingTurn(AssemblyMarker line, Vector3 point, Vector3 eye, Vector3 up, AssemblyPart owner = null)
        {
            // round the middle of the part the line is on (the grip core for the lead's channel, the wrap round the grip), else
            // round the middle of the line itself
            var centre = Vector3.zero; int n = 0;
            if (owner) { centre = owner.transform.TransformPoint(owner.localBounds.center); n = 1; }
            else { foreach (var t in line.points) if (t) { centre += t.position; n++; } if (n == 0) return 0; centre /= n; }
            var d = Vector3.ProjectOnPlane(point - centre, up); var e = Vector3.ProjectOnPlane(eye - centre, up);
            return d.sqrMagnitude < 1e-8f || e.sqrMagnitude < 1e-8f ? 0 : Vector3.SignedAngle(d, e, up);
        }
        void TurnSwivel(float dt, bool back)
        {
            if (!swivelPart) return;
            var up = c.bench.Up;
            if (back) swivelYaw = Mathf.MoveTowards(swivelYaw, 0, 260 * dt);
            else
            {
                float want = FacingTurn(c.marker, PointAt(Mathf.Min(length, along + .012f)), c.eye, up, c.bench.Part(c.marker.ownerPart));
                if (Mathf.Abs(want) > 6) swivelYaw += Mathf.Clamp(want, -150 * dt, 150 * dt);
            }
            Swivel(swivelPart.transform, swivelStart, swivelAt, up, swivelYaw);
        }
        public override void Begin() { Read(); along = Mathf.Clamp01(c.carried) * length; swivelPart = !string.IsNullOrEmpty(c.action.swivel) ? SwivelOf(c.bench, c.bench.Part(c.action.swivel)) : null; if (swivelPart) { swivelStart = new Pose(swivelPart.transform.position, swivelPart.transform.rotation); swivelAt = SwivelPivot(swivelPart); swivelYaw = 0; swivelSet = true; } if (!string.IsNullOrEmpty(c.action.loop)) c.audio?.Loop(LoopKey, c.action.loop, PointAt(along)); }
        public override AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var a = c.action; var s = c.settings;
            Read();
            if (length <= 0) { st.done = true; st.precision = 1; return st; }
            // the work turned back square once the line is done (the vise swings back on its swivel)
            if (swingingBack) { TurnSwivel(dt, true); if (Mathf.Abs(swivelYaw) < .5f) { swivelPart.transform.SetPositionAndRotation(swivelStart.position, swivelStart.rotation); st.done = true; st.precision = finalPrecision; } else { st.progress = 1; } return st; }
            if (swivelPart) TurnSwivel(dt, false);
            float tol = (a.tolMm > 0 ? a.tolMm : s.pathTolMm) * .001f, before = along, error;
            if (a.mode == "drag" && f.pointer && !f.keyboard)
            {
                // (21 Nov, sh-real9: the peel by real mouse failed after five minutes: the line on the wrap could not be followed)
                // drag mode: any motion of the held pointer pulls the tape off; it cannot go back, cannot tear, and the work turns
                // on its swivel to show where the tape comes away. About 1400 px of hand motion for the whole line.
                error = 0;
                if (f.primaryHeld) along = Mathf.Min(length, along + f.delta.magnitude * length / 1400f);
            }
            else if (f.pointer && !f.keyboard)
            {
                // progress is the furthest point ahead on the line that the pointer is still on; the error is how far the pointer
                // is from the line itself (its nearest point there), which is what the line is judged by
                error = DistanceToRay(f.ray, PointAt(along), out _);
                // (the pointer trails the progress point by up to the tolerance, so the line is looked at a little way back too)
                float limit = Mathf.Min(length, along + (a.ahead > 0 ? a.ahead : .06f)), start = along;
                for (float ahead = Mathf.Max(0, start - tol * 1.5f); ahead < limit + .003f; ahead += .003f)
                {
                    float sample = Mathf.Min(ahead, limit), d = DistanceToRay(f.ray, PointAt(sample), out _);
                    if (sample >= start && d <= tol) along = sample;
                    if (d < error) error = d;
                }
            }
            else
            {
                // D moves the tip to the right as the eye sees it, whichever way the line runs
                var here = PointAt(along); var ahead = PointAt(Mathf.Min(length, along + .004f)) - here;
                float steer = 1;
                if (ahead.sqrMagnitude > 1e-10f) { ScreenAxes((here - c.eye).normalized, c.bench.Up, out var sr, out _); float side = Vector3.Dot(Vector3.Cross(c.bench.Up, ahead.normalized), sr); if (Mathf.Abs(side) > .2f) steer = Mathf.Sign(side); }
                drift += ((float)c.random.NextDouble() - .5f) * dt * .08f + f.navigate.x * steer * dt * .05f; drift = Mathf.Clamp(drift, -tol * 2, tol * 2);
                error = Mathf.Abs(drift);
                if (error <= tol) along = Mathf.Min(length, along + s.pathKeyPace * dt);
            }
            // a step over a stretch round the back is not speed: the pace counts at most 3 cm of line a frame
            paced += Mathf.Clamp(along - before, 0, .03f);
            float pace = Mathf.Max(0, travel.Push(dt, paced));   // metres of line per second, over a quarter of a second
            errorSum += Mathf.Clamp01(error / tol) * dt; errorTime += dt;
            st.progress = along / length; st.carry = st.progress; st.value = Mathf.Clamp01(error / tol);
            var at = PointAt(along);
            if (f.keyboard || !f.pointer) { var tangent = PointAt(Mathf.Min(length, along + .004f)) - at; if (tangent.sqrMagnitude > 1e-10f) at += Vector3.Cross(c.bench.Up, tangent.normalized) * drift; }
            if (c.tool)
            {
                var into = AssemblyToolPose.Work(c.bench, a, c.part, c.marker, c.tool).into;
                var run = PointAt(Mathf.Min(length, along + .006f)) - PointAt(Mathf.Max(0, along - .006f));
                AssemblyToolPose.Place(c.bench, c.tool, at, into, run);
            }
            c.audio?.SetLoop(LoopKey, a.hi > 0 ? Mathf.Clamp01(pace / a.hi) : .5f, pace > 0 ? .9f : .15f);
            if (a.mode != "drag" && a.hi > 0 && pace > a.hi && HasFault("tear")) { along = before; st.carry = along / length; st.fault = "tear"; st.ended = true; return st; }
            // the last 3 cm of a line that runs round the back (a swivel line) finish by themselves: the tape comes off, the lead drops in
            if (along >= length - (swivelPart ? .03f : .0015f))
            {
                finalPrecision = Mathf.Clamp(1 - .6f * (errorTime > 0 ? errorSum / errorTime : 0), .4f, 1);
                if (swivelPart && Mathf.Abs(swivelYaw) > .5f) { swingingBack = true; st.progress = 1; return st; }
                st.done = true; st.precision = finalPrecision; return st;
            }
            if (!f.primaryHeld) st.ended = true;
            return st;
        }
        float finalPrecision = 1;
        public override void End() { c.audio?.StopLoop(LoopKey); if (swivelPart && swivelSet) swivelPart.transform.SetPositionAndRotation(swivelStart.position, swivelStart.rotation); }
    }

    // =====================================================================================================  Wipe
    /// Rub a tool over a surface until it is clean. Coverage is kept by the bench as a mask per zone (AssemblyWipeMask,
    /// which the wipe shader reads); the verb only writes it. The wipe finishes by itself when the zone is all but clean;
    /// let go earlier with enough done and it counts, and what was missed shows later (the spin test).
    public sealed class WipeVerb : AssemblyVerb
    {
        public override AssemblyVerbKind Kind => AssemblyVerbKind.Wipe;
        AssemblyWipeMask mask; float sweep; int iu, iv, inn; Vector3 last;
        public float Coverage => mask != null ? mask.Coverage : 0;
        public override void Begin()
        {
            var zone = c.marker; mask = zone ? c.bench.Wipe(zone.id) : null;
            if (zone) AssemblyWipeMask.Axes(zone.size, out iu, out iv, out inn);
            last = ActPoint;
            if (!string.IsNullOrEmpty(c.action.loop)) c.audio?.Loop(LoopKey, c.action.loop, ActPoint);
        }
        public override AssemblyVerbStatus Tick(float dt, in AssemblyInputFrame f)
        {
            var st = new AssemblyVerbStatus(); var a = c.action; var s = c.settings; var zone = c.marker;
            if (!zone || mask == null) { st.done = true; st.precision = 1; return st; }
            var size = zone.size; float su = Mathf.Max(1e-4f, size[iu]), sv = Mathf.Max(1e-4f, size[iv]);
            var axis = Vector3.zero; axis[inn] = 1; var normal = zone.transform.TransformDirection(axis).normalized;
            if (Vector3.Dot(normal, c.eye - zone.transform.position) < 0) normal = -normal;
            float pu, pv; bool moving;
            if (f.pointer && !f.keyboard)
            {
                var plane = new Plane(normal, zone.transform.position);
                var local = plane.Raycast(f.ray, out float t) ? zone.transform.InverseTransformPoint(f.ray.GetPoint(t)) : new Vector3(99, 99, 99);
                pu = local[iu]; pv = local[iv]; moving = f.delta.sqrMagnitude > .5f || (f.ray.GetPoint(t) - last).sqrMagnitude > 1e-8f; last = f.ray.GetPoint(t);
            }
            else
            {
                sweep += dt * 1.4f; float row = Mathf.Floor(sweep), u = sweep - row; if (((int)row & 1) == 1) u = 1 - u;
                pu = (u - .5f) * su; pv = (Mathf.Repeat(row, 6) / 5f - .5f) * sv; moving = true;
            }
            // the brush covers at least a good share of a small zone (a trunnion is a few millimetres across)
            float scale = Mathf.Max(1e-6f, Mathf.Abs(zone.transform.lossyScale.x)), radius = Mathf.Max(s.wipeRadiusMm * .001f, .3f * Mathf.Min(su, sv)) / scale;
            if (f.primaryHeld && moving)
            {
                bool any = false; const int N = AssemblyWipeMask.N;
                for (int k = 0; k < N; k++) for (int i = 0; i < N; i++)
                {
                    float cu = ((i + .5f) / N - .5f) * su, cv = ((k + .5f) / N - .5f) * sv;
                    if ((cu - pu) * (cu - pu) + (cv - pv) * (cv - pv) <= radius * radius) any |= mask.Clean(i, k);
                }
                if (any) c.bench.NotifyWipe(mask);
            }
            if (c.tool)
            {
                var at = Vector3.zero; at[iu] = Mathf.Clamp(pu, -su * .5f, su * .5f); at[iv] = Mathf.Clamp(pv, -sv * .5f, sv * .5f);
                AssemblyToolPose.Place(c.bench, c.tool, zone.transform.TransformPoint(at) + normal * (size[inn] * .5f), -normal);
            }
            c.audio?.SetLoop(LoopKey, .5f, f.primaryHeld && moving ? .9f : 0);
            float cover = Coverage, need = a.lo > 0 ? a.lo : s.wipeDone;
            st.progress = Mathf.Clamp01(cover / Mathf.Max(.05f, need)); st.carry = cover; st.value = cover;
            if (cover >= Mathf.Max(need, s.wipeFull)) { st.done = true; st.precision = 1; return st; }
            if (!f.primaryHeld) { if (cover >= need) { st.done = true; st.precision = Mathf.Clamp01(cover); } else st.ended = true; }
            return st;
        }
        public override void End() { c.audio?.StopLoop(LoopKey); }
    }
}
