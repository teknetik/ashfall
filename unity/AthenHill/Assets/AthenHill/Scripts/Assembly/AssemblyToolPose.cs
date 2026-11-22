using UnityEngine;
namespace AthenHill
{
    /// How a tool is held for the work (22 Nov 2026, Carl: the mallet and the other tools stood at odd angles).
    ///
    /// The art's empties come from Blender, whose +Z reaches Unity as +Y: a real tool works along tip.up and a real mark
    /// faces out along its up. The stand-in bench was built the other way (+Z), so AssemblyBench.ArtAxes says which.
    /// `Work` says where an action is worked and which way it is driven; `Rotation` says how that kind of tool is held
    /// there. The handle is always on the player's side of the bench or above it, whatever the camera is doing.
    public static class AssemblyToolPose
    {
        public struct Job
        {
            public Vector3 at;
            /// The way the work is driven: into the surface, along the screw, the way the blow goes.
            public Vector3 into;
            /// The way a line runs where the tool is on it (zero for work that is not a line).
            public Vector3 along;
        }

        const float FileTilt = .12f, SnipsTilt = .35f, HandleBelow = .15f;

        static float Lean(AssemblyPart tool)
        {
            if (tool.HasTag("tool:solder")) return 50;
            if (tool.HasTag("tool:scribe") || tool.HasTag("tool:pick") || tool.HasTag("tool:applicator")) return 40;
            if (tool.HasTag("tool:cutters") || tool.HasTag("tool:strippers")) return 35;
            if (tool.HasTag("tool:oil")) return 15;
            return 0;   // screwdriver, drill, punch and pliers work square on
        }
        static bool SideOn(AssemblyPart tool) => tool.HasTag("tool:mallet") || tool.HasTag("tool:brush");
        static bool IsFile(AssemblyPart tool) => tool.HasTag("tool:file") || tool.HasTag("tool:file_round");

        /// The axis the tool works along, in the world, as the tool lies now.
        public static Vector3 WorkAxis(AssemblyBench bench, AssemblyPart tool)
        {
            var tip = tool.tip ? tool.tip : tool.transform;
            return bench.ArtAxes ? tip.up : tip.forward;
        }

        static Vector3 Across(Vector3 wanted, Vector3 axis, Vector3 fallback, Vector3 last)
        {
            foreach (var v in new[] { wanted, fallback, last })
            {
                var flat = Vector3.ProjectOnPlane(v, axis);
                if (flat.sqrMagnitude > .01f) return flat.normalized;
            }
            return Vector3.Cross(axis, Mathf.Abs(axis.y) < .9f ? Vector3.up : Vector3.right).normalized;
        }

        /// The world rotation of a tool working along `into`. It depends only on the tool's shape and the work, never on how
        /// the tool happened to lie before, so a tool cannot pick up a twist from the frame before.
        public static Quaternion Rotation(AssemblyBench bench, AssemblyPart tool, Vector3 into, Vector3 along = default)
        {
            var frame = bench.surface ? bench.surface : bench.transform;
            Vector3 up = bench.Up, toPlayer = frame.forward, right = -frame.right;   // the player's right: they face down the surface's -Z
            into = into.sqrMagnitude > 1e-8f ? into.normalized : -up;

            var tip = tool.tip ? tool.tip : tool.transform;
            var inverse = Quaternion.Inverse(tool.transform.rotation);
            Vector3 axis = inverse * WorkAxis(bench, tool);
            Vector3 side = inverse * (bench.ArtAxes ? tip.forward : tip.up);
            Vector3 direction = into, sideWanted;

            if (SideOn(tool))
            {
                // the face meets the work square; the handle lies across the blow, towards the hand
                side = inverse * (tool.GrabPoint - tool.TipPoint);
                // a blow from above has its handle to the hand, one along the bench has it off to the right hand
                sideWanted = Mathf.Abs(Vector3.Dot(into, up)) > .7f ? toPlayer + right * .6f : right + up * .25f;
            }
            else if (IsFile(tool))
            {
                // a file lies on the work and points away from the player
                var outward = -into;
                direction = (Across(-toPlayer, outward, right, up) + into * FileTilt).normalized;
                sideWanted = outward;
            }
            else if (tool.HasTag("tool:snips") && Vector3.ProjectOnPlane(along, into).sqrMagnitude > 1e-8f)
            {
                var run = Vector3.ProjectOnPlane(along, into).normalized;
                direction = (run + into * SnipsTilt).normalized;
                sideWanted = Vector3.Cross(into, run);
            }
            else
            {
                float lean = Lean(tool) * Mathf.Deg2Rad;
                if (lean > 0)
                {
                    // tipped so the handle comes back to the hand
                    direction = into * Mathf.Cos(lean) + Across(-toPlayer, into, -up, right) * Mathf.Sin(lean);
                    float rising = Vector3.Dot(direction, up);
                    if (rising > HandleBelow) direction -= up * rising;   // never with the handle down in the bench
                    direction.Normalize();
                }
                sideWanted = toPlayer + up * .5f;
            }

            var sideLocal = Across(side, axis, Vector3.up, Vector3.right);
            var sideWorld = Across(sideWanted, direction, up, right);
            return Quaternion.LookRotation(direction, sideWorld) * Quaternion.Inverse(Quaternion.LookRotation(axis, sideLocal));
        }

        /// A tool's pose with its working point on `at`.
        public static Pose At(AssemblyBench bench, AssemblyPart tool, Vector3 at, Vector3 into, Vector3 along = default, float spin = 0)
        {
            var t = tool.transform; var rotation = Rotation(bench, tool, into, along);
            if (spin != 0) rotation = Quaternion.AngleAxis(spin, into.normalized) * rotation;
            var tipLocal = Quaternion.Inverse(t.rotation) * (tool.TipPoint - t.position);
            return new Pose(at - rotation * tipLocal, rotation);
        }

        public static void Place(AssemblyBench bench, AssemblyPart tool, Vector3 at, Vector3 into, Vector3 along = default, float spin = 0)
        {
            if (!tool) return;
            var pose = At(bench, tool, at, into, along, spin);
            tool.transform.SetPositionAndRotation(pose.position, pose.rotation);
        }

        /// A blow drawn back by `raised` (0 to 1): the head rises against the blow, swinging about the hand.
        public static void DrawBack(AssemblyPart tool, Vector3 into, float raised, float lift)
        {
            if (!tool || raised <= 0) return;
            var reach = tool.TipPoint - tool.GrabPoint; var hinge = Vector3.Cross(reach, -into);
            // a blow along the bench has less room to draw back in than one from above
            float swing = Mathf.Abs(into.normalized.y) > .7f ? 38 : 20;
            if (hinge.magnitude > .4f * reach.magnitude) tool.transform.RotateAround(tool.GrabPoint, hinge.normalized, swing * raised);
            tool.transform.position -= into.normalized * (lift * .35f * raised);
        }

        static float HalfLength(AssemblyPart p, Vector3 axis)
        {
            var local = p.transform.InverseTransformDirection(axis); var e = Vector3.Scale(p.localBounds.extents, p.transform.lossyScale);
            return Mathf.Abs(local.x * e.x) + Mathf.Abs(local.y * e.y) + Mathf.Abs(local.z * e.z);
        }

        /// The axis a turned part turns about, pointing out of what it is in.
        public static Vector3 TurnAxis(AssemblyPart p) =>
            !p.hasClear ? p.transform.up : p.OnParent ? p.RemovalAxis : p.transform.rotation * p.LocalRemovalAxis;

        /// Where and which way an action is worked. The verbs and the tool hovering over the work both ask this, so a tool
        /// does not jump to another angle when the button goes down.
        public static Job Work(AssemblyBench bench, AssemblyActionDef a, AssemblyPart p, AssemblyMarker mark, AssemblyPart tool)
        {
            var down = -bench.Up;
            var job = new Job { at = p ? p.GrabPoint : mark ? mark.transform.position : bench.SurfacePoint, into = down };
            if (a == null) return job;
            switch (a.verb)
            {
                case AssemblyVerbKind.Turn:
                    if (p) job.into = -TurnAxis(p);
                    break;
                case AssemblyVerbKind.Point:
                    if (mark) { job.at = mark.transform.position; job.into = -bench.Out(mark.transform); }
                    break;
                case AssemblyVerbKind.Path:
                    if (!mark) break;
                    var outward = bench.Out(mark.transform);
                    var frame = bench.surface ? bench.surface : bench.transform;
                    if (Vector3.Dot(outward, frame.forward + bench.Up) < 0) outward = -outward;   // worked on the face the hand can reach
                    job.into = -outward;
                    if (mark.points.Length > 0 && mark.points[0]) job.at = mark.points[0].position;
                    if (mark.points.Length > 1 && mark.points[0] && mark.points[1]) job.along = mark.points[1].position - mark.points[0].position;
                    break;
                case AssemblyVerbKind.Wipe:
                    if (mark) job.at = mark.transform.position;
                    break;
                case AssemblyVerbKind.Window:
                    if (mark && mark.kind == AssemblyMarkerKind.Mark) { job.at = mark.transform.position; job.into = -bench.Out(mark.transform); break; }
                    if (!p) break;
                    if (a.mode == "strike")
                    {
                        var struck = bench.Part(a.target);
                        if (struck && struck.IsTool)
                        {
                            // the mallet hits the end of the punch, along the punch
                            job.into = WorkAxis(bench, struck);
                            var end = bench.Marker(struck.id + "/strike");
                            job.at = end ? end.transform.position : struck.GrabPoint - job.into * HalfLength(struck, job.into);
                            break;
                        }
                        // still in its hole: along it, the way it has to go. Lying on the anvil: straight down on it
                        if (p.hasClear && p.OnParent) job.into = a.to > a.from ? p.RemovalAxis : -p.RemovalAxis;
                        job.at = p.GrabPoint - job.into * HalfLength(p, job.into);
                        break;
                    }
                    if (tool && IsFile(tool)) job.at = p.GrabPoint + bench.Up * HalfLength(p, bench.Up);
                    else if (p.hasClear && !(tool && (tool.HasTag("tool:strippers") || tool.HasTag("tool:solder")))) job.into = -p.RemovalAxis;
                    break;
            }
            return job;
        }
    }
}
