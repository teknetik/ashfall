using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace AthenHill.Editor
{
    /// Can the player see what every action needs? (Fix round of 20 Nov 20:15: the peel of `s1.tape` failed by real mouse
    /// because the grip stood buried in the vise jaws, and nothing short of a player had looked.)
    ///
    /// The check walks the whole job on a copy of the bench, action by action, as the session will meet it: for each moment of
    /// an action (the hand goes for the tool, then for the part, then does the work) it asks the session which shot it will
    /// use (<see cref="AssemblySession.ShotFor"/>, the same question the camera asks) and tests every point the hand needs in
    /// that shot's 16:9 picture:
    ///   on screen      inside the picture with a little to spare;
    ///   not covered    not under the bench's own interface (<see cref="AssemblyHud.Covered"/>: stage line, Field Notes,
    ///                  Brann's captions, the way out, the pack-it-in control);
    ///   not hidden     nothing stands between the eye and the point (a ray against the triangles of everything on the bench,
    ///                  and against the boxes the layout says to keep clear of: the old bench's print head). A surface within
    ///                  8 mm of the point is the thing the point is on, not something in the way.
    /// Points: the tool where it rests, the part to pick up, where a carried part has to be brought, the mark or marks of a
    /// Point, every point of a Path, the middle and edges of a Wipe zone (which must also face the eye), the part or mark a
    /// Turn or Window works on, the card of a test, and the pistol held up to it (in the lower third, seen from behind).
    /// Mistakes with a way back are made on purpose so that the recovery steps are walked too. Nothing is saved.
    public static class AssemblySightCheck
    {
        const float Aspect = 16f / 9f, Tolerance = .008f, EdgeX = .96f, EdgeY = .94f;

        internal sealed class Occluder { public Transform frame; public Vector3[] vertices; public int[] triangles; public Bounds bounds; public string owner; public Transform part; public bool world; }

        public static JObject Run(AssemblyBench bench, JObject layout, string label)
        {
            var session = bench.GetComponent<AssemblySession>();
            var report = new JObject { ["bench"] = label };
            var failures = new JArray(); var used = new SortedDictionary<string, int>(StringComparer.Ordinal); var notes = new JArray();
            int actions = 0, points = 0;
            AssemblyCraftLink.ForgetDetached();
            if (!session || !session.Open(true)) { report["error"] = "the bench did not open"; return report; }
            try
            {
                var boxes = new List<Occluder>();
                foreach (JObject sh in (JArray)layout["shots"])
                    if (sh["avoid"]?["box"] is JArray ab && ab.Count == 6 && !boxes.Any(x => x.owner == "the old bench's print head"))
                        boxes.Add(Box(bench.transform, new Vector3((float)ab[0], (float)ab[1], (float)ab[2]), new Vector3((float)ab[3], (float)ab[4], (float)ab[5]), "the old bench's print head"));
                List<Occluder> scene = null;
                List<Occluder> Scene() => scene ?? (scene = AssemblySightCheck.Scene(bench, boxes));

                bool quiet = false; string lastWhy = null; JArray lastSeenFrom = null;
                var shotIds = ((JArray)layout["shots"]).Select(x => (string)x["id"]).Where(x => !string.IsNullOrEmpty(x)).ToArray();
                var paths = new JArray();
                void Fail(AssemblyActionRef r, string moment, string shot, string what, string why)
                {
                    lastWhy = why; if (quiet) { lastSeenFrom = null; return; }
                    var row = new JObject { ["action"] = r.Id, ["verb"] = r.action.verb.ToString() + (string.IsNullOrEmpty(r.action.mode) ? "" : " " + r.action.mode), ["moment"] = moment, ["shot"] = shot, ["what"] = what, ["why"] = why };
                    if (lastSeenFrom != null) row["seenFrom"] = lastSeenFrom;
                    lastSeenFrom = null; failures.Add(row);
                }
                // the shots in which a point would be in sight (on the picture, clear of the interface, nothing in the way): for
                // choosing a better shot for an action whose point is hidden in the one it has
                JArray SeenFrom(Vector3 world, AssemblyPart[] own)
                {
                    var ok = new JArray();
                    foreach (var id in shotIds)
                    {
                        var c = session.ShotCamera(id); if (!c) continue;
                        var l = c.transform.InverseTransformPoint(world); float tv = Mathf.Tan(c.fieldOfView * .5f * Mathf.Deg2Rad);
                        if (l.z < .05f) continue;
                        float x = l.x / (l.z * tv * Aspect), y = l.y / (l.z * tv);
                        if (Mathf.Abs(x) > EdgeX || Mathf.Abs(y) > EdgeY) continue;
                        if (AssemblyHud.CoveredBy(new Vector2((x * .5f + .5f) * AssemblyHud.Reference.x, (.5f - y * .5f) * AssemblyHud.Reference.y)) != null) continue;
                        var e = c.transform.position; float d = Vector3.Distance(e, world);
                        if (Blocked(Scene(), new Ray(e, (world - e) / d), d - Tolerance, own, out _) == null) ok.Add(id);
                    }
                    return ok;
                }
                // where the hand goes on a part: its grab point where the art gives one; for a part still fitted on another (a pin,
                // a gear on its post, a screw) the end it comes off by, not its middle, which is inside what holds it
                Vector3 Outer(AssemblyPart p)
                {
                    if (p.grab || !p.OnParent || !p.hasClear || p.Travel < 1e-4f) return p.GrabPoint;
                    var axis = p.RemovalAxis; var local = p.transform.InverseTransformDirection(axis); var e = Vector3.Scale(p.localBounds.extents, p.transform.lossyScale);
                    return p.transform.TransformPoint(p.localBounds.center) + axis * (Mathf.Abs(local.x) * e.x + Mathf.Abs(local.y) * e.y + Mathf.Abs(local.z) * e.z);
                }

                // one point from one shot; `own` is what the point belongs to (never in its own way), and what the action works
                // through (a template laid over the marks) is not in the way either
                bool Point(AssemblyActionRef r, string moment, string shot, string what, Vector3 world, params AssemblyPart[] own)
                {
                    points++;
                    if (r.action.through != null && r.action.through.Length > 0) own = (own ?? new AssemblyPart[0]).Concat(r.action.through.Select(id => bench.Part(id))).ToArray();
                    var cam = session.ShotCamera(shot);
                    if (!cam) { Fail(r, moment, shot, what, "the bench has no such shot"); return false; }
                    var l = cam.transform.InverseTransformPoint(world); float tv = Mathf.Tan(cam.fieldOfView * .5f * Mathf.Deg2Rad);
                    if (l.z < .05f) { Fail(r, moment, shot, what, "behind the eye"); return false; }
                    float x = l.x / (l.z * tv * Aspect), y = l.y / (l.z * tv);
                    if (Mathf.Abs(x) > EdgeX || Mathf.Abs(y) > EdgeY) { if (!quiet) lastSeenFrom = SeenFrom(world, own); Fail(r, moment, shot, what, $"off the picture ({(x * .5f + .5f) * 100:0} % across, {(.5f - y * .5f) * 100:0} % down)"); return false; }
                    var panel = new Vector2((x * .5f + .5f) * AssemblyHud.Reference.x, (.5f - y * .5f) * AssemblyHud.Reference.y);
                    string covered = AssemblyHud.CoveredBy(panel);
                    if (covered != null) { Fail(r, moment, shot, what, $"under {covered} ({panel.x:0}, {panel.y:0} of 1920 x 1080)"); return false; }
                    var eye = cam.transform.position; float far = Vector3.Distance(eye, world);
                    string behind = Blocked(Scene(), new Ray(eye, (world - eye) / far), far - Tolerance, own, out float at);
                    if (behind != null) { if (!quiet) lastSeenFrom = SeenFrom(world, own); Fail(r, moment, shot, what, $"hidden behind {behind} ({(far - at) * 1000:0} mm in front of it)"); return false; }
                    return true;
                }

                void Check(AssemblyActionRef r)
                {
                    actions++; scene = null;
                    var a = r.action; var part = bench.Part(a.part);
                    var tool = !string.IsNullOrEmpty(a.tool) && a.tool != "*" ? bench.Tool(a.tool) : null;
                    bool partIsTool = part && part.IsTool;
                    bool carried = part && !partIsTool && (a.verb == AssemblyVerbKind.Seat || a.verb == AssemblyVerbKind.Flick || a.mode == "aim");
                    void Count(string shot) { used.TryGetValue(shot, out int n); used[shot] = n + 1; }
                    // the hand goes for the tool
                    if (tool && tool.gameObject.activeInHierarchy)
                    {
                        string s0 = session.ShotFor(r, null, null); Count(s0);
                        // a tool in its pocket shows its handle, not its middle: it is in sight when any of three points along it is
                        var tb = tool.localBounds; int axis = tb.size.x >= tb.size.y && tb.size.x >= tb.size.z ? 0 : tb.size.y >= tb.size.z ? 1 : 2; var along = Vector3.zero; along[axis] = tb.extents[axis] * .7f;
                        quiet = true; bool any = false;
                        foreach (var at in new[] { tool.GrabPoint, tool.transform.TransformPoint(tb.center + along), tool.transform.TransformPoint(tb.center - along) }) if (Point(r, "take the tool", s0, tool.id, at, tool)) { any = true; break; }
                        quiet = false;
                        if (!any) Fail(r, "take the tool", s0, tool.id, "neither its middle nor either end is in sight: " + lastWhy);
                    }
                    else if (!string.IsNullOrEmpty(a.tool) && a.tool != "*" && !tool) Fail(r, "take the tool", "", a.tool, "no such tool on the bench");
                    // then for the part (a tool that is itself set somewhere is picked up like a part)
                    var held = partIsTool ? part : tool;
                    if ((carried || partIsTool) && part && !part.Gone && part.gameObject.activeInHierarchy)
                    {
                        string s1 = session.ShotFor(r, partIsTool ? null : tool, null); Count(s1);
                        Point(r, "pick it up", s1, part.id, Outer(part), part);
                    }
                    // then the work
                    var inHand = carried ? part : null;
                    string s2 = a.mode == "aim" && !string.IsNullOrEmpty(a.shot) ? a.shot : session.ShotFor(r, held, inHand); Count(s2);
                    var cam = session.ShotCamera(s2);
                    switch (a.verb)
                    {
                        case AssemblyVerbKind.Seat:
                            if (a.mode != "inspect") Point(r, "bring it in", s2, a.target, session.ActPointFor(r, held, inHand), part);
                            break;
                        case AssemblyVerbKind.Flick: break;   // in the hand
                        case AssemblyVerbKind.Point:
                            if (a.mode == "aim")
                            {
                                var card = bench.Marker(a.target);
                                if (!card) { Fail(r, "aim", s2, a.target, "no such mark"); break; }
                                Point(r, "aim", s2, a.target, card.transform.position, part);
                                if (part && cam)
                                {
                                    var pose = AssemblySession.AimPose(part, cam.transform.position, cam.transform.rotation, cam.fieldOfView, card.transform.position, bench.settings);
                                    var hold = pose.position + part.GrabOffsetAt(pose.rotation); var l = cam.transform.InverseTransformPoint(hold); float tv = Mathf.Tan(cam.fieldOfView * .5f * Mathf.Deg2Rad);
                                    float x = l.x / (l.z * tv * Aspect), y = l.y / (l.z * tv);
                                    var out0 = part.tip ? pose.rotation * (Quaternion.Inverse(part.transform.rotation) * part.tip.forward) : pose.rotation * Vector3.right;
                                    var top = part.tip ? pose.rotation * (Quaternion.Inverse(part.transform.rotation) * part.tip.up) : pose.rotation * Vector3.up;
                                    if (l.z < .1f || Mathf.Abs(x) > .9f || y > -1f / 3f || y < -1.05f) Fail(r, "aim", s2, part.id, $"the pistol held up to the card is not in the lower third of the picture ({(x * .5f + .5f) * 100:0} % across, {(.5f - y * .5f) * 100:0} % down)");
                                    else if (Vector3.Dot(out0, cam.transform.forward) < .8f) Fail(r, "aim", s2, part.id, $"the pistol held up to the card is not seen from behind (its muzzle is {Vector3.Angle(out0, cam.transform.forward):0} degrees off the view)");
                                    else if (Vector3.Dot(top, cam.transform.up) < .8f) Fail(r, "aim", s2, part.id, $"the pistol held up to the card is not top up (its top is {Vector3.Angle(top, cam.transform.up):0} degrees off the picture's up)");
                                    points++;
                                }
                                break;
                            }
                            foreach (var id in a.targets.Length > 0 ? a.targets : new[] { a.target })
                            {
                                var m = bench.Marker(id); var tp = m ? null : bench.Part(id);
                                if (m) Point(r, "the mark", s2, id, m.transform.position); else if (tp) Point(r, "the mark", s2, id, tp.GrabPoint, tp); else Fail(r, "the mark", s2, id, "no such mark");
                            }
                            break;
                        case AssemblyVerbKind.Path:
                        {
                            var m = bench.Marker(a.target);
                            if (!m || m.kind != AssemblyMarkerKind.Path) { Fail(r, "the line", s2, a.target, "no such path"); break; }
                            var inSight = new bool[m.points.Length]; var whyHidden = new string[m.points.Length];
                            quiet = true;
                            var sw = !string.IsNullOrEmpty(a.swivel) ? AssemblyVerb.SwivelOf(bench, bench.Part(a.swivel)) : null; var swStart = sw ? new Pose(sw.transform.position, sw.transform.rotation) : default; var swAt = sw ? AssemblyVerb.SwivelPivot(sw) : default;
                            var swCam = session.ShotCamera(s2);
                            for (int i = 0; i < m.points.Length; i++) if (m.points[i])
                            {
                                // a line on a swivel is seen with the work turned to face that stretch of it, as PathVerb turns it
                                if (sw && swCam)
                                {
                                    sw.transform.SetPositionAndRotation(swStart.position, swStart.rotation); var up = bench.Up;
                                    // (the turn is about the middle of the base, not round the line, so it is settled in three passes as the verb
                                    // settles it over frames)
                                    float yaw = 0;
                                    for (int pass = 0; pass < 3; pass++)
                                    {
                                        float want = PathVerb.FacingTurn(m, m.points[i].position, swCam.transform.position, up, bench.Part(m.ownerPart));
                                        if (Mathf.Abs(want) <= 6) break;
                                        yaw += want - Mathf.Sign(want) * 6; AssemblyVerb.Swivel(sw.transform, swStart, swAt, up, yaw);
                                    }
                                    scene = null;
                                }
                                inSight[i] = Point(r, "the line", s2, $"{a.target} point {i + 1} of {m.points.Length}", m.points[i].position);
                                if (!inSight[i]) whyHidden[i] = lastWhy;
                            }
                            if (sw) { sw.transform.SetPositionAndRotation(swStart.position, swStart.rotation); scene = null; }
                            quiet = false;
                            // how much of the line is out of sight at a stretch, measured along it (PathVerb looks 6 cm ahead on the line for
                            // the pointer, so a stretch round the back shorter than that can be stepped over from where the line shows again)
                            float Along(int from, int to) { float d = 0; for (int k = from + 1; k <= to; k++) if (m.points[k] && m.points[k - 1]) d += Vector3.Distance(m.points[k - 1].position, m.points[k].position); return d; }
                            float longest = 0; int hidden = 0, lastSeen = -1, n = m.points.Length;
                            for (int i = 0; i < n; i++)
                            {
                                if (!inSight[i]) { hidden++; continue; }
                                if (i - lastSeen > 1) longest = Mathf.Max(longest, Along(Mathf.Max(0, lastSeen), i));   // from the last point in sight to the next
                                lastSeen = i;
                            }
                            if (n > 0 && lastSeen < n - 1) longest = Mathf.Max(longest, Along(Mathf.Max(0, lastSeen), n - 1));
                            // the line can be followed by sight when it starts and ends in sight and every stretch out of sight is shorter than
                            // the verb's look-ahead (PathVerb: the pointer picks the line up again where it shows); otherwise the hidden points fail
                            float aheadM = a.ahead > 0 ? a.ahead : .06f;
                            // (a swivel line finishes by itself in its last 3 cm, PathVerb: its end need not be in sight within that)
                            bool endOk = n > 0 && (inSight[n - 1] || sw && lastSeen >= 0 && Along(lastSeen, n - 1) < .0295f);
                            // (likewise the start: the line is taken up anywhere within the look-ahead of its first point)
                            int firstSeen = Array.IndexOf(inSight, true);
                            bool startOk = n > 0 && (inSight[0] || firstSeen > 0 && Along(0, firstSeen) < aheadM * .9f);
                            bool followable = n > 0 && startOk && endOk && longest < aheadM * .9f;
                            if (!followable)
                            {
                                for (int k = 0; k < n; k++)
                                {
                                    if (!m.points[k] || inSight[k]) continue;
                                    if (sw) Fail(r, "the line", s2, $"{a.target} point {k + 1} of {n}", "with the work turned to face it on its swivel: " + whyHidden[k]);
                                    else Point(r, "the line", s2, $"{a.target} point {k + 1} of {n}", m.points[k].position);
                                }
                            }
                            paths.Add(new JObject { ["action"] = r.Id, ["shot"] = s2, ["points"] = m.points.Length, ["hidden"] = hidden, ["longestHiddenStretchMm"] = Math.Round(longest * 1000), ["aheadMm"] = Math.Round(aheadM * 1000), ["followable"] = followable, ["startInSight"] = inSight.Length > 0 && inSight[0], ["endInSight"] = inSight.Length > 0 && inSight[inSight.Length - 1] });
                            break;
                        }
                        case AssemblyVerbKind.Wipe:
                        {
                            var m = bench.Marker(a.target);
                            if (!m || m.kind != AssemblyMarkerKind.Zone) { Fail(r, "the area", s2, a.target, "no such zone"); break; }
                            AssemblyWipeMask.Axes(m.size, out int u, out int v, out int n);
                            Vector3 Axis(int i) => i == 0 ? m.transform.right : i == 1 ? m.transform.up : m.transform.forward;
                            var normal = Axis(n); var centre = m.transform.position;
                            if (cam && Vector3.Dot(normal, cam.transform.position - centre) < 0) normal = -normal;
                            float facing = cam ? Vector3.Dot(normal, (cam.transform.position - centre).normalized) : 1;
                            if (facing < .17f) { Fail(r, "the area", s2, a.target, $"the area is edge on or faces away from the eye ({Mathf.Acos(Mathf.Clamp(facing, -1, 1)) * Mathf.Rad2Deg:0} degrees off)"); break; }
                            var face = centre + normal * (m.size[n] * .5f);
                            // an area is worked over, not hit at a point: most of it has to be in sight (the middle of a bearing race is
                            // under its rotor, and that is how it is)
                            var spots = new List<(string name, Vector3 at)> { ("middle", face) };
                            foreach (var (du, dv) in new[] { (-.4f, 0f), (.4f, 0f), (0f, -.4f), (0f, .4f) }) spots.Add(($"edge ({du:0.#}, {dv:0.#})", face + Axis(u) * (m.size[u] * du) + Axis(v) * (m.size[v] * dv)));
                            var lost = new List<string>(); quiet = true;
                            foreach (var (name, at) in spots) if (!Point(r, "the area", s2, a.target + " " + name, at)) lost.Add($"{name}: {lastWhy}");
                            quiet = false;
                            if (lost.Count > 2) Fail(r, "the area", s2, a.target, $"hidden or off the picture at {lost.Count} of {spots.Count} places ({string.Join("; ", lost)})");
                            break;
                        }
                        default:   // Turn, Window: the mark where there is one, or the part itself
                        {
                            var m = bench.Marker(a.target);
                            var struck = !m && a.verb == AssemblyVerbKind.Window && !string.IsNullOrEmpty(a.target) ? bench.Part(a.target) : null;
                            // a strike lands on the target part where there is one (the punch head over the pin), as WindowVerb.ActPoint has it
                            if (struck && !struck.Gone) Point(r, "the work", s2, struck.id, struck.GrabPoint, struck, part);
                            else if (m) Point(r, "the work", s2, a.target, m.kind == AssemblyMarkerKind.Path && m.points.Length > 0 && m.points[0] ? m.points[0].position : m.transform.position, part);
                            else if (part && !part.Gone) Point(r, "the work", s2, part.id, Outer(part), part);
                            break;
                        }
                    }
                }

                var seen = new HashSet<string>(); var tried = new HashSet<string>(); var raised = new HashSet<string>(); int guard = 0; string stopped = null;
                while (session.State == AssemblySession.Phase.Working && session.Job != null && guard++ < 4000)
                {
                    // what may be done but need not (a shake, a look over) and the ways back from mistakes are walked while they are open
                    AssemblyActionRef? pick = null; bool side = false;
                    foreach (var r in session.Job.OpenActions)
                        if ((r.step.optional || r.step.recovery) && !tried.Contains(r.Id) && session.Job.Blocked(r.step.id, r.action.key) == null) { pick = r; side = true; break; }
                    if (!pick.HasValue) pick = session.Next;
                    if (!pick.HasValue) break;
                    var now = pick.Value;
                    if (seen.Add(now.Id)) Check(now);
                    if (side) tried.Add(now.Id);
                    // a mistake with a way back, made on purpose (once each): its recovery step opens now or when the step is done
                    foreach (var f in now.action.faults)
                    {
                        if (string.IsNullOrEmpty(f.recovery) || session.Job.Step(f.recovery) == null || session.Job.IsDone(f.recovery) || !raised.Add(now.Id + "/" + f.kind)) continue;
                        if (!session.DevFault(now.step.id, f.kind)) notes.Add($"{now.Id}: the mistake {f.kind} could not be made");
                    }
                    if (session.State != AssemblySession.Phase.Working) break;
                    if (session.Job.ActionDone(now.step.id, now.action.key)) continue;
                    if (session.DevComplete(now.step.id, now.action.key, 1)) continue;
                    if (side) continue;
                    // held up by its own mistake: the way back is open and the next turn of the loop takes it
                    if (session.Job.OpenActions.Any(r => r.step.recovery && !tried.Contains(r.Id) && session.Job.Blocked(r.step.id, r.action.key) == null)) continue;
                    stopped = $"{now.Id}: could not be completed ({session.Job.Blocked(now.step.id, now.action.key)})"; break;
                }
                if (stopped != null) report["stopped"] = stopped;
                var all = bench.recipe.data.Steps.SelectMany(st => st.actions.Select(a => st.id + ":" + a.key)).ToList();
                report["actionsInTheTable"] = all.Count; report["actionsChecked"] = actions; report["pointsChecked"] = points;
                report["notWalked"] = new JArray(all.Where(id => !seen.Contains(id)));
                report["shotsUsed"] = JObject.FromObject(used); report["paths"] = paths;
                report["failures"] = failures; report["failed"] = failures.Select(x => (string)x["action"]).Distinct().Count();
                report["byWhy"] = JObject.FromObject(failures.GroupBy(x => { string w = (string)x["why"]; return w.StartsWith("hidden") ? "hidden" : w.StartsWith("under") ? "under the interface" : w.StartsWith("off") ? "off the picture" : "other"; }).ToDictionary(g => g.Key, g => g.Count()));
                if (notes.Count > 0) report["notes"] = notes;
                report["ok"] = failures.Count == 0 && stopped == null;
            }
            catch (Exception e) { report["error"] = e.GetType().Name + ": " + e.Message + " @ " + (e.StackTrace ?? "").Split('\n').FirstOrDefault(); report["ok"] = false; }
            finally { session.Close(false); }
            return report;
        }

        static readonly Dictionary<Mesh, (Vector3[] v, int[] t, Bounds b)> meshes = new Dictionary<Mesh, (Vector3[] v, int[] t, Bounds b)>();
        /// Everything on the bench that can stand in the way, as it is now (plus the boxes given).
        internal static List<Occluder> Scene(AssemblyBench bench, List<Occluder> boxes)
        {
            var scene = new List<Occluder>(boxes ?? new List<Occluder>());
            foreach (var r in bench.GetComponentsInChildren<Renderer>(false))
            {
                if (!r.enabled || r.name.StartsWith("decal_") || r.name == "Aim dot" || r is LineRenderer) continue;
                var owner = r.GetComponentInParent<AssemblyPart>(true);
                // glass is seen through (the solvent jar: the gimbal in the bath, the core quenched in it)
                if (owner && owner.material == "glass" && owner.kind == "fixture") continue;
                if (r is SkinnedMeshRenderer sk)
                {
                    if (!sk.sharedMesh) continue;
                    var baked = new Mesh(); sk.BakeMesh(baked, true);
                    scene.Add(new Occluder { frame = sk.transform, vertices = baked.vertices, triangles = baked.triangles, bounds = baked.bounds, owner = owner ? owner.id : r.name, part = owner ? owner.transform : null });
                    UnityEngine.Object.DestroyImmediate(baked);
                    continue;
                }
                var mf = r.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null; if (!mesh) continue;
                if (!meshes.TryGetValue(mesh, out var data)) meshes[mesh] = data = (mesh.vertices, mesh.triangles, mesh.bounds);
                scene.Add(new Occluder { frame = r.transform, vertices = data.v, triangles = data.t, bounds = data.b, owner = owner ? owner.id : r.name, part = owner ? owner.transform : null });
            }
            return scene;
        }

        static Occluder Box(Transform frame, Vector3 centre, Vector3 size, string owner)
        {
            var e = size * .5f; var v = new Vector3[8];
            for (int i = 0; i < 8; i++) v[i] = frame.TransformPoint(centre + Vector3.Scale(e, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1)));
            var t = new[] { 0, 2, 1, 1, 2, 3, 4, 5, 6, 5, 7, 6, 0, 1, 4, 1, 5, 4, 2, 6, 3, 3, 6, 7, 0, 4, 2, 2, 4, 6, 1, 3, 5, 3, 7, 5 };
            var b = new Bounds(v[0], Vector3.zero); foreach (var p in v) b.Encapsulate(p);
            return new Occluder { vertices = v, triangles = t, bounds = b, owner = owner, world = true };
        }

        /// The id of the nearest thing a ray meets before `limit` metres, or null. Parts in `own`, and everything fitted on
        /// them, are never in the way.
        internal static string Blocked(List<Occluder> scene, Ray ray, float limit, AssemblyPart[] own, out float at)
        {
            at = limit; string who = null;
            foreach (var o in scene)
            {
                if (o.part && own != null && own.Any(p => p && o.part.IsChildOf(p.transform))) continue;
                Ray local = ray; float scale = 1;
                if (!o.world)
                {
                    var inv = o.frame.worldToLocalMatrix; var d = inv.MultiplyVector(ray.direction); scale = d.magnitude; if (scale < 1e-9f) continue;
                    local = new Ray(inv.MultiplyPoint3x4(ray.origin), d / scale);
                }
                var b = o.bounds; b.Expand(.0005f);
                if (!b.IntersectRay(local, out float enter) || enter / scale > at) continue;
                var v = o.vertices; var t = o.triangles; float best = at * scale;   // in the occluder's own units
                for (int i = 0; i + 2 < t.Length; i += 3)
                    if (Triangle(local, v[t[i]], v[t[i + 1]], v[t[i + 2]], out float hit) && hit < best) { best = hit; who = o.owner; }
                at = best / scale;
            }
            return who;
        }

        /// Moeller-Trumbore, both faces.
        static bool Triangle(Ray ray, Vector3 a, Vector3 b, Vector3 c, out float t)
        {
            t = 0; var e1 = b - a; var e2 = c - a; var p = Vector3.Cross(ray.direction, e2); float det = Vector3.Dot(e1, p);
            if (det > -1e-12f && det < 1e-12f) return false;
            float inv = 1 / det; var s = ray.origin - a; float u = Vector3.Dot(s, p) * inv; if (u < 0 || u > 1) return false;
            var q = Vector3.Cross(s, e1); float w = Vector3.Dot(ray.direction, q) * inv; if (w < 0 || u + w > 1) return false;
            t = Vector3.Dot(e2, q) * inv; return t > 1e-5f;
        }
    }
}
