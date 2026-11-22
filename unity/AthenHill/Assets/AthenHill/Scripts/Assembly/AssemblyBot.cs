#if UNITY_EDITOR || DEBUG
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
    /// Plays the bench job through AssemblySession.Step with made-up input frames, in the mouse form (a pointer ray
    /// from where the bench camera stands) or the keyboard form (focus ring, held keys). It does what a player's hands
    /// would do, action by action: take the tool, set the bit, press, circle, hold, release, carry, turn to the key,
    /// bring to the socket. The Edit Mode tests and the installer's `selftest` step both use it, so the same run that
    /// proves the job can be finished by hand also proves it can be finished without a pointer.
    public sealed class AssemblyBot
    {
        readonly AssemblySession s; readonly AssemblyBench bench; readonly bool keyboard;
        public float dt = 1f / 60f;
        public int Frames { get; private set; }
        public readonly List<string> Log = new List<string>();
        public string Error { get; private set; }
        /// Presses that had to move off the part's hold point to find the part under the pointer (mouse form), by every bot
        /// since the list was last cleared (the selftest clears it per scenario and reports it).
        public static readonly List<string> Reaims = new List<string>();
        public AssemblyBot(AssemblySession session, bool keyboard) { s = session; bench = session.bench; this.keyboard = keyboard; }

        Vector3 Eye
        {
            get
            {
                var cam = bench.cameraRoot ? bench.cameraRoot.Find("cam_bench_" + s.WantedShotName) : null;
                if (!cam && bench.cameraRoot) cam = bench.cameraRoot.Find("cam_bench_wide");
                return cam ? cam.position : bench.SurfacePoint + bench.Up * .9f + (bench.surface ? bench.surface.forward : Vector3.forward) * .9f;
            }
        }
        AssemblyInputFrame At(Vector3 point)
        {
            var eye = Eye; var f = new AssemblyInputFrame { pointer = !keyboard, keyboard = keyboard };
            f.ray = keyboard ? new Ray(eye, (bench.SurfacePoint - eye).normalized) : new Ray(eye, (point - eye).normalized);
            f.screen = ToScreen(point);
            return f;
        }

        // ---- the screen, as the player has it: a 1920 x 1080 view through the camera of the shot in use. Circles and drags
        // are made in pixels and turned into rays here, so "clockwise" is clockwise on the screen whatever the game assumes.
        public const float ScreenW = 1920, ScreenH = 1080;
        Transform Cam
        {
            get
            {
                var cam = bench.cameraRoot ? bench.cameraRoot.Find("cam_bench_" + s.WantedShotName) : null;
                if (!cam && bench.cameraRoot) cam = bench.cameraRoot.Find("cam_bench_wide");
                return cam;
            }
        }
        float TanV { get { var c = Cam ? Cam.GetComponent<Camera>() : null; return Mathf.Tan((c ? c.fieldOfView : 55) * .5f * Mathf.Deg2Rad); } }
        /// Pixels from the bottom left of the screen.
        public Vector2 ToScreen(Vector3 world)
        {
            var cam = Cam; if (!cam) return default;
            var l = cam.InverseTransformPoint(world); if (l.z < 1e-4f) return new Vector2(-1, -1);
            float tv = TanV, th = tv * ScreenW / ScreenH;
            return new Vector2((l.x / (l.z * th) * .5f + .5f) * ScreenW, (l.y / (l.z * tv) * .5f + .5f) * ScreenH);
        }
        public Ray ScreenRay(Vector2 pixel)
        {
            var cam = Cam; float tv = TanV, th = tv * ScreenW / ScreenH;
            var d = new Vector3((pixel.x / ScreenW * 2 - 1) * th, (pixel.y / ScreenH * 2 - 1) * tv, 1);
            return new Ray(cam.position, cam.TransformDirection(d).normalized);
        }
        /// A held press at a screen pixel (mouse form).
        void HoldPixel(Vector2 pixel, Vector2 delta) { var f = new AssemblyInputFrame { pointer = true, ray = ScreenRay(pixel), screen = pixel, delta = delta, primaryHeld = true }; Tick(f); }
        void Tick(AssemblyInputFrame f, int frames = 1) { for (int i = 0; i < frames; i++) { s.Step(dt, f, Eye); Frames++; if (i == 0) { f.primaryDown = f.primaryUp = f.flip = f.putBack = f.next = f.previous = f.hint = false; f.scroll = 0; f.navStep = Vector2Int.zero; } } }
        bool redirected;
        bool Fail(string why) { Error = why + $" [held part {(s.HeldPart ? s.HeldPart.id : "-")}, tool {(s.HeldTool ? s.HeldTool.id : "-")}, focus {s.Focus.Id}, next {(s.Next.HasValue ? s.Next.Value.Id : "-")}]"; Log.Add("FAIL " + Error); return false; }

        // ---- the two ways of pointing and pressing
        bool FocusOn(string id, Vector3 point)
        {
            if (!keyboard) { Tick(At(point)); return true; }
            for (int i = 0; i < 80; i++) { if (s.Focus.Id == id) return true; var f = At(point); f.next = true; Tick(f); }
            return s.Focus.Id == id;
        }
        // a press and release at one world point is a tap, even when the shot changes under it (a real pointer does not move
        // when the camera does): the release is given the press's own pixel
        Vector3 downPoint; Vector2 downScreen;
        void Down(Vector3 point) { var f = At(point); f.primaryDown = f.primaryHeld = true; downPoint = point; downScreen = f.screen; Tick(f); }
        void Hold(Vector3 point, int frames = 1, float navigate = 0, Vector2 delta = default) { var f = At(point); f.primaryHeld = true; f.navigate = new Vector2(navigate, 0); f.delta = delta; Tick(f, frames); }
        void Up(Vector3 point) { var f = At(point); f.primaryUp = true; if ((point - downPoint).sqrMagnitude < 1e-8f) f.screen = downScreen; Tick(f); }
        void Click(Vector3 point) { Down(point); Up(point); }
        void Idle(Vector3 point, int frames = 1) { Tick(At(point), frames); }

        bool TakeTool(AssemblyActionDef a)
        {
            if (string.IsNullOrEmpty(a.tool) || a.tool == "*") return true;
            var tool = bench.Tool(a.tool); if (!tool) return Fail("no tool " + a.tool);
            if (s.HeldTool != tool)
            {
                if (s.HeldPart) { var f = At(s.HeldPart.GrabPoint); f.putBack = true; Tick(f); }
                if (!tool.gameObject.activeInHierarchy) return Fail(tool.id + " is not on the bench yet");
                if (!FocusOn(tool.id, tool.GrabPoint)) return Fail("cannot bring the focus to " + tool.id);
                Click(tool.GrabPoint);
                if (s.HeldTool != tool) return Fail("could not take " + tool.id);
            }
            for (int i = 0; i < 4 && !string.IsNullOrEmpty(a.toolMode) && tool.Mode != a.toolMode; i++) { var f = At(tool.GrabPoint); f.flip = true; Tick(f); }
            return string.IsNullOrEmpty(a.toolMode) || tool.Mode == a.toolMode || Fail(tool.id + " has no setting " + a.toolMode);
        }
        void FreeHand(AssemblyActionDef a)
        {
            if (s.HeldTool && string.IsNullOrEmpty(a.tool) && !(a.verb == AssemblyVerbKind.Seat && a.part == s.HeldTool.id)) { var f = At(s.HeldTool.GrabPoint); f.putBack = true; Tick(f); }
            if (s.HeldPart && s.HeldPart.id != a.part) { var f = At(s.HeldPart.GrabPoint); f.putBack = true; Tick(f); }
        }

        /// Does the next open action by hand. False (with Error) when it could not be done.
        public bool PlayNext()
        {
            var next = s.Next; if (!next.HasValue) return Fail("nothing is open");
            var r = next.Value; var a = r.action; var job = s.Job; string id = r.Id; int before = Frames;
            bool Done() => s.Job == null || s.State != AssemblySession.Phase.Working || s.Job != job || job.ActionDone(r.step.id, a.key);
            FreeHand(a);
            if (!TakeTool(a)) return false;
            var part = bench.Part(a.part);
            bool ok;
            switch (a.verb)
            {
                case AssemblyVerbKind.Seat: ok = Seat(r, part, Done); break;
                case AssemblyVerbKind.Turn: ok = Turn(r, part, Done); break;
                case AssemblyVerbKind.Window: ok = Window(r, part, Done); break;
                case AssemblyVerbKind.Point: ok = a.mode == "aim" ? Aim(r, part, Done) : Marks(r, Done); break;
                case AssemblyVerbKind.Flick: ok = Flick(r, part, Done); break;
                case AssemblyVerbKind.Path: ok = Path(r, Done); break;
                case AssemblyVerbKind.Wipe: ok = Wipe(r, Done); break;
                default: return Fail("the bot cannot do " + a.verb + " yet");
            }
            // the work showed up an earlier step done badly: it is put off until its recovery is done, which is what comes next
            if (!ok && s.State == AssemblySession.Phase.Working && s.Job == job && job.Blocked(r.step.id, a.key) is string why && why.StartsWith("recovery:"))
            { Log.Add($"{id} put off by its own fault: {why}"); Error = null; FreeHands(); return true; }
            if (ok) Log.Add($"{id} {a.verb} {(keyboard ? "keys" : "mouse")} {Frames - before} frames{(part ? ", " + part.id + " at " + part.place : "")}{(job.ActionDone(r.step.id, a.key) ? $", precision {job.StepPrecision(r.step.id):0.00} for the step" : "")}");
            return ok;
        }

        bool Carry(AssemblyPart part, bool hold, Func<bool> done = null)
        {
            if (s.HeldPart == part) return true;
            if (!part || part.Gone) return Fail("the part to carry is not on the bench");
            if (!FocusOn(part.id, part.GrabPoint)) return Fail("cannot bring the focus to " + part.id);
            var grab = part.GrabPoint; string before = s.Focus.Id;
            Down(grab);
            if (s.HeldPart && s.HeldPart != part && s.CarryAction.HasValue)
            {
                // it took the thing lying on top, which has work of its own: do that now (the job's next action follows the hand)
                Up(grab); redirected = true; Log.Add($"took {s.HeldPart.id} instead of {part.id}: it has its own place to go"); return false;
            }
            if (s.HeldPart != part)
            {
                string L(Vector3 v) => bench.transform.InverseTransformPoint(v).ToString("0.000");
                string why = $"could not pick up {part.id} at {part.place} (refusals {s.Refusals}): pointed at {L(grab)} from {L(Eye)} (shot {s.WantedShotName}), part origin {L(part.transform.position)}, focus before the press {before}" + (s.HeldPart ? $", took {s.HeldPart.id} whose origin is {L(s.HeldPart.transform.position)}" : "");
                Up(grab); return Fail(why);
            }
            // a tap leaves it in the hand; a part that must be held (the spring) keeps the button down until it is seated
            if (!hold) Up(grab);
            // off its parent: drag away from where it was taken (the keyboard form slides it by itself)
            for (int i = 1; i < 240 && s.CarryLeaving; i++) { if (hold) Hold(grab + bench.Up * (.003f * i)); else Idle(grab + bench.Up * (.003f * i)); }
            if (s.CarryLeaving) return Fail(part.id + " would not come off");
            if (s.HeldPart != part) return done != null && done() || Fail(part.id + " slipped back");
            return true;
        }

        bool Seat(AssemblyActionRef r, AssemblyPart part, Func<bool> done)
        {
            var a = r.action;
            if (part && part.IsTool && s.HeldPart != part)
            {
                // a tool stood on the work: take it as a tool, then press on the place it stands
                if (s.HeldTool != part) { if (!FocusOn(part.id, part.GrabPoint)) return Fail("cannot bring the focus to " + part.id); Click(part.GrabPoint); }
                if (s.HeldTool != part) return Fail("could not take " + part.id);
                var place = s.ActPoint(r);
                if (!FocusOn(a.target, place)) return Fail("cannot bring the focus to " + a.target);
                Click(place);
                if (s.HeldPart != part && !done()) return Fail(part.id + " was not stood on " + a.target);
            }
            else if (!done() && !Carry(part, a.keepHold, done)) { if (!redirected) return false; redirected = false; return true; }
            if (done()) return true;
            // a keyed part comes to the hand the wrong way up: turn it over
            if (a.mode == "keyed" && s.CarryFlipped) { var f = At(part.GrabPoint); f.flip = true; Tick(f); }
            if (a.mode == "inspect")
            {
                for (int i = 0; i < 400 && !done(); i++) { var f = At(part.GrabPoint); if (keyboard) f.rotate = 1; else if (i % 4 == 0) f.scroll = 1; Tick(f); }
                return done() || Fail("looking it over never finished");
            }
            var parent = bench.Part(part.parentId);
            string focusId = a.target == "seat" || a.target == "start" ? (parent ? parent.id : "") : a.target;
            float last = float.MaxValue; int dir = 1, since = 0;
            for (int i = 0; i < 900 && !done(); i++)
            {
                var goal = s.ActPoint(r);
                if (keyboard && s.Focus.Id != focusId && !FocusOn(focusId, goal)) return Fail("cannot bring the focus to " + focusId);
                var f = At(goal); f.primaryHeld = a.keepHold;
                // turn it to its key: a notch (or a held key) at a time, the other way when that made it worse
                float err = s.CarryYawError;
                if (i > 20 && err > 7)
                {
                    since++;
                    if (since % 8 == 0) { if (err > last + .5f) dir = -dir; last = err; if (!keyboard) f.scroll = dir; }
                    if (keyboard) f.rotate = dir * (err > 25 ? 1 : .35f);
                }
                Tick(f);
            }
            if (a.keepHold) Up(s.ActPoint(r));
            return done() || Fail($"{part.id} never seated at {a.target}: {s.CarryDistanceMm:0.0} mm off, {s.CarryYawError:0.0} degrees out");
        }

        bool Turn(AssemblyActionRef r, AssemblyPart part, Func<bool> done)
        {
            var a = r.action; var pivot = part.GrabPoint;
            if (!FocusOn(part.id, pivot)) return Fail("cannot bring the focus to " + part.id);
            if (a.mode == "reveal")
            {
                Down(pivot);
                if (!(s.Verb is TurnVerb)) { Up(pivot); return Fail("pressing on " + part.id + " did not start the turn"); }
                float best = 0; int engaged = 0; var mark = bench.Marker(a.target); string trail = "";
                for (int i = 0; i < 1500 && !done(); i++)
                {
                    Hold(pivot, 1, 1, new Vector2(5, 0)); best = Mathf.Max(best, s.VerbStatus.value); if (s.Verb != null) engaged++;
                    if (i == 100 && mark) { string path = ""; for (var t = mark.transform; t; t = t.parent) path = t.name + "/" + path; trail = $"at 100: part yaw {part.transform.localEulerAngles.y:0}, mark forward {mark.transform.forward.ToString("0.00")}, mark path {path}"; }
                }
                Up(pivot);
                for (int i = 0; i < 180 && s.Squaring; i++) Idle(pivot);   // it swings back square before anything else is pressed
                return done() || Fail($"the mark was never found (best facing {best:0.00}, engaged {engaged} frames, {trail}, eye {Eye.ToString("0.00")})");
            }
            Down(pivot);
            var verb = s.Verb as TurnVerb; if (verb == null) { Up(pivot); return Fail("pressing on " + part.id + " did not start a turn"); }
            float need = Mathf.Abs(a.turns), sign = a.turns < 0 ? -1 : 1, angle = 0; bool stop = a.mode == "stop";
            float target = stop ? need + a.lo + Mathf.Min(.12f, (a.hi - a.lo) * .4f) : need;
            // a circle round the pivot on the screen, in pixels: clockwise as the player sees it drives a right-hand thread in.
            // (Before 20 Nov the circle was made in world space with the verb's own basis, which hid a mirrored turn.)
            var centre = ToScreen(pivot); float radius = 70; Vector2 last = centre + new Vector2(radius, 0);
            Vector2 OnCircle() => centre + new Vector2(Mathf.Cos(angle * Mathf.Deg2Rad), Mathf.Sin(angle * Mathf.Deg2Rad)) * radius;
            for (int i = 0; i < 4000 && !done() && s.Verb == verb && verb.Turned < target; i++)
            {
                if (keyboard) { Hold(pivot); continue; }
                angle -= sign * 18;   // the angle falls: clockwise with x to the right and y up
                var at = OnCircle(); HoldPixel(at, at - last); last = at;
            }
            if (stop && !done())
            {
                if (keyboard) Up(pivot);
                else for (int i = 0; i < 60 && !done(); i++) HoldPixel(OnCircle(), Vector2.zero);
            }
            if (!done()) Up(pivot);
            return done() || Fail($"turning {part.id} never finished ({(verb != null ? verb.Turned : 0):0.00} of {need:0.00} turns)");
        }

        bool Window(AssemblyActionRef r, AssemblyPart part, Func<bool> done)
        {
            var a = r.action; var at = s.ActPoint(r); float mid = (a.lo + a.hi) * .5f;
            string focusId = bench.Part(a.target) ? a.target : a.part;
            if (a.mode == "wait")
            {
                // nothing to do but leave it alone
                FreeHands();
                for (int i = 0; i < Mathf.CeilToInt((a.seconds + 2) / dt) && !done(); i++) Idle(bench.SurfacePoint + bench.Up * .3f);
                return done() || Fail("the wait on " + a.part + " never ended");
            }
            if (a.mode == "sustain")
            {
                if (!FocusOn(focusId, at)) return Fail("cannot bring the focus to " + focusId);
                Down(at);
                var pump = s.Verb as WindowVerb; if (pump == null) { Up(at); return Fail("pressing on " + focusId + " did not start the work"); }
                // pump to the middle of the band, then feather it: down when it sags, off when it climbs
                for (int i = 0; i < Mathf.CeilToInt((a.seconds + 30) / dt) && !done() && s.Verb == pump; i++) { if (pump.Value < mid) Hold(at); else Idle(at); }
                return done() || Fail($"the press never knitted ({pump.Knit:0.0} of {a.seconds:0.0} s in the band)");
            }
            for (int n = 0; n < a.count + 4 && !done(); n++)
            {
                if (!FocusOn(focusId, at)) return Fail("cannot bring the focus to " + focusId);
                Down(at);
                var verb = s.Verb as WindowVerb; if (verb == null) { Up(at); return Fail("pressing on " + focusId + " did not start the work"); }
                for (int i = 0; i < 600 && verb.Value < mid && s.Verb == verb; i++) Hold(at);
                Up(at);
            }
            return done() || Fail("the window was never hit on " + a.part);
        }

        bool Wipe(AssemblyActionRef r, Func<bool> done)
        {
            var a = r.action; var zone = bench.Marker(a.target); if (!zone) return Fail("no zone " + a.target);
            AssemblyWipeMask.Axes(zone.size, out int iu, out int iv, out _);
            Vector3 P(float u, float v) { var l = Vector3.zero; l[iu] = (u - .5f) * zone.size[iu]; l[iv] = (v - .5f) * zone.size[iv]; return zone.transform.TransformPoint(l); }
            if (!FocusOn(zone.id, zone.transform.position)) return Fail("cannot bring the focus to " + zone.id);
            Down(P(.02f, .02f));
            if (done()) return true;   // it was clean already: one touch and it is done
            var verb = s.Verb as WipeVerb; if (verb == null) { Up(zone.transform.position); return Fail("pressing on " + zone.id + " did not start the wipe"); }
            if (keyboard) for (int i = 0; i < 3000 && !done() && s.Verb == verb; i++) Hold(zone.transform.position);
            else
                // back and forth across the zone, a row at a time
                for (int pass = 0; pass < 3 && !done() && s.Verb == verb; pass++)
                    for (int row = 0; row <= 10 && !done() && s.Verb == verb; row++)
                        for (int i = 0; i <= 14 && !done() && s.Verb == verb; i++) { float u = i / 14f; if ((row & 1) == 1) u = 1 - u; Hold(P(u, (row + (pass % 2) * .5f) / 10f)); }
            if (!done()) Up(zone.transform.position);
            return done() || Fail($"{zone.id} was never wiped clean ({(verb != null ? verb.Coverage : 0):0.00})");
        }

        bool Marks(AssemblyActionRef r, Func<bool> done)
        {
            var a = r.action;
            foreach (var id in a.targets.Length > 0 ? a.targets : new[] { a.target })
            {
                if (done()) break;
                var m = bench.Marker(id); if (!m) return Fail("no mark " + id);
                if (!m.gameObject.activeInHierarchy) continue;
                if (!FocusOn(id, m.transform.position)) return Fail("cannot bring the focus to " + id);
                Click(m.transform.position);
            }
            return done() || Fail("the marks were not all hit");
        }

        bool Aim(AssemblyActionRef r, AssemblyPart part, Func<bool> done)
        {
            if (!Carry(part, false)) return false;
            var card = bench.Marker(r.action.target); if (!card) return Fail("no card target");
            if (!FocusOn(card.id, card.transform.position)) return Fail("cannot bring the focus to " + card.id);
            Idle(card.transform.position, 20);
            if (!s.Aiming) return Fail("holding the pistol on the card did not start the aim");
            for (int n = 0; n < r.action.count + 3 && !done(); n++) { Click(card.transform.position); Idle(card.transform.position, 12); }
            return done() || Fail("the test pulses were not all fired");
        }

        bool Flick(AssemblyActionRef r, AssemblyPart part, Func<bool> done)
        {
            if (!Carry(part, false)) return false;
            var centre = bench.SurfacePoint; var side = bench.surface ? bench.surface.right : Vector3.right;
            if (keyboard) { Down(centre); for (int i = 0; i < 240 && !done(); i++) Hold(centre); Up(centre); }
            else for (int i = 0; i < 600 && !done(); i++) Idle(centre + side * (.07f * ((i / 5) % 2 == 0 ? 1 : -1)));
            return done() || Fail("the shake was never felt");
        }

        bool Path(AssemblyActionRef r, Func<bool> done)
        {
            var m = bench.Marker(r.action.target); if (!m || m.points.Length < 2) return Fail("no path " + r.action.target);
            var pts = m.points.Where(t => t).Select(t => t.position).ToList();
            if (!FocusOn(m.id, pts[0])) return Fail("cannot bring the focus to " + m.id);
            Down(pts[0]);
            var verb = s.Verb as PathVerb; if (verb == null) { Up(pts[0]); return Fail("pressing on the line did not start it"); }
            if (!keyboard && r.action.mode == "drag")
            {
                // drag mode, as a hand does it: small circles in screen pixels with the button held (real pointer deltas)
                var c0 = ToScreen(pts[0]);
                for (int i = 0; i < 3000 && !done() && s.Verb == verb; i++)
                {
                    float a0 = i * .25f, a1 = (i + 1) * .25f;
                    var p0 = c0 + new Vector2(Mathf.Cos(a0), Mathf.Sin(a0)) * 50; var p1 = c0 + new Vector2(Mathf.Cos(a1), Mathf.Sin(a1)) * 50;
                    HoldPixel(p1, p1 - p0);
                }
                for (int i = 0; i < 240 && !done(); i++) HoldPixel(c0, Vector2.zero);
                if (!done()) Up(pts[0]);
                return done() || Fail($"the line was never finished by dragging ({verb.Along:0.00})");
            }
            if (keyboard)
            {
                float nav = 0, last = 0;
                for (int i = 0; i < 6000 && !done() && s.Verb == verb; i++) { float v = s.VerbStatus.value; if (v > .5f && v > last) nav = nav >= 0 ? -1 : 1; else if (v < .25f) nav = 0; last = v; Hold(pts[0], 1, nav); }
            }
            else
                // the line is read where it is now at every step: the work may turn under it (the vise on its swivel)
                for (int k = 1; k < m.points.Length && !done(); k++)
                {
                    if (!m.points[k] || !m.points[k - 1]) continue;
                    int steps = Mathf.Max(1, Mathf.CeilToInt(Vector3.Distance(m.points[k - 1].position, m.points[k].position) / .0015f));
                    for (int i = 1; i <= steps && !done(); i++) Hold(Vector3.Lerp(m.points[k - 1].position, m.points[k].position, (float)i / steps));
                }
            var end = m.points[m.points.Length - 1] ? m.points[m.points.Length - 1] : null;
            for (int i = 0; i < 240 && !done(); i++) Hold(end ? end.position : pts[pts.Count - 1]);
            if (!done()) Up(end ? end.position : pts[pts.Count - 1]);
            return done() || Fail($"the line was never finished ({verb.Along:0.00})");
        }

        /// Takes a tool by hand (QA scenarios that then misuse it).
        public bool Take(string toolId)
        {
            var tool = bench.Tool(toolId); if (!tool) return Fail("no tool " + toolId);
            if (s.HeldTool == tool) return true;
            if (!FocusOn(tool.id, tool.GrabPoint)) return Fail("cannot bring the focus to " + tool.id);
            Click(tool.GrabPoint);
            return s.HeldTool == tool || Fail("could not take " + tool.id);
        }
        /// One press and release on a part or marker with whatever is in the hand.
        public bool Press(string id)
        {
            var part = bench.Part(id); var marker = bench.Marker(id);
            if (!part && !marker) return Fail("nothing called " + id);
            var at = part ? part.GrabPoint : marker.transform.position;
            if (!FocusOn(id, at)) return Fail("cannot bring the focus to " + id);
            // mouse: where its hold point is under something else (the lead behind the housing pin), the pointer is moved along the
            // part until the part itself is under it, as a hand would (the rim shows what is under the pointer); logged
            if (!keyboard && part && s.Focus.Id != id)
            {
                // on its surface where the part has surface points; else on its own lines and marks (a wire's route), else in its box
                var from = at; IEnumerable<Vector3> spots;
                if (part.surface != null && part.surface.Length > 0) spots = part.surface.Select(x => part.transform.TransformPoint(x));
                else
                {
                    var own = bench.Markers.Where(m => m && m.ownerPart == id && m.kind != AssemblyMarkerKind.Place).SelectMany(m => m.kind == AssemblyMarkerKind.Path ? m.points.Where(t => t).Select(t => t.position) : new[] { m.transform.position }).ToList();
                    var b = part.localBounds;
                    for (int ix = -1; ix <= 1; ix++) for (int iy = -1; iy <= 1; iy++) for (int iz = -1; iz <= 1; iz++) own.Add(part.transform.TransformPoint(b.center + Vector3.Scale(b.extents * .6f, new Vector3(ix, iy, iz))));
                    spots = own;
                }
                var seen = new Dictionary<string, int>();
                foreach (var q in spots.OrderBy(x => (x - from).sqrMagnitude).Take(160))
                {
                    Idle(q); if (s.Focus.Id != id) { seen.TryGetValue(s.Focus.Id ?? "", out int c); seen[s.Focus.Id ?? ""] = c + 1; continue; }
                    at = q; Log.Add($"re-aimed at {id}: {(q - from).magnitude * 1000:0} mm from its hold point"); Reaims.Add($"{id} {(q - from).magnitude * 1000:0} mm"); break;
                }
                if (s.Focus.Id != id) Reaims.Add($"{id} never under the pointer; found instead: {string.Join(", ", seen.Select(kv => (kv.Key == "" ? "nothing" : kv.Key) + " x" + kv.Value))}");
            }
            Click(at); return true;
        }
        /// Puts back whatever is in the hand (tool, then part).
        public void FreeHands()
        {
            for (int i = 0; i < 2 && (s.HeldPart || s.HeldTool); i++) { var f = At(bench.SurfacePoint); f.putBack = true; Tick(f); }
        }
        /// Takes hold of a seated part, pulls it part of the way off and lets go (the spring). The drag is made across the bench
        /// for `share` of the part's travel (the session reads a drag in the plane of the part's rest, whichever way it goes),
        /// so it is part of the way off on a real part with a long slide as on a stand-in.
        public bool PullAndLetGo(string partId, float share = .45f, int frames = 20)
        {
            FreeHands();
            var part = bench.Part(partId); if (!part) return Fail("no part " + partId);
            if (!FocusOn(part.id, part.GrabPoint)) return Fail("cannot bring the focus to " + partId);
            var grab = part.GrabPoint; Down(grab);
            if (s.HeldPart != part) return Fail("pressing on " + partId + " took " + (s.HeldPart ? s.HeldPart.id : "nothing") + " (focus " + s.Focus.Id + ")");
            var eye = Eye; var across = Vector3.ProjectOnPlane(grab - eye, bench.Up); across = across.sqrMagnitude > 1e-8f ? -across.normalized : bench.surface ? -bench.surface.forward : Vector3.back;
            float reach = share * Mathf.Max(.035f, part.Travel);
            Vector3 to = grab;
            for (int i = 1; i <= frames; i++) { to = grab + across * (reach * i / frames); Hold(to); }
            Hold(to, 6);
            Up(to); return true;
        }
        /// Holds whatever is in the hand at the place the next action wants it, without turning or flipping it (a part offered
        /// the wrong way up).
        public void Hover(float seconds)
        {
            var next = s.Next; if (!next.HasValue) return;
            for (int i = 0; i < Mathf.CeilToInt(seconds / dt) && s.Next.HasValue && s.Next.Value.Id == next.Value.Id; i++)
            {
                var goal = s.ActPoint(next.Value);
                if (keyboard) { var parent = s.HeldPart ? bench.Part(s.HeldPart.parentId) : null; string id = next.Value.action.target == "seat" || next.Value.action.target == "start" ? (parent ? parent.id : "") : next.Value.action.target; if (s.Focus.Id != id) FocusOn(id, goal); }
                Idle(goal);
            }
        }
        /// One press and release at a point on the bench (mouse form).
        public void PressAt(Vector3 world) { Tick(At(world)); Click(world); }
        public void Flip() { var f = At(bench.SurfacePoint); f.flip = true; Tick(f); }
        public void Wait(float seconds) { Tick(At(bench.SurfacePoint + bench.Up * .3f), Mathf.CeilToInt(seconds / dt)); }
        /// Plays until the named action is the next one (it is not done).
        public bool PlayUntil(string actionId, int maxActions = 600)
        {
            for (int n = 0; n < maxActions; n++)
            {
                var next = s.Next; if (!next.HasValue) return Fail("never reached " + actionId);
                if (next.Value.Id == actionId) return true;
                if (!PlayNext()) return false;
            }
            return Fail("never reached " + actionId);
        }

        /// The slice (Milestone 1): stages 0 and 1 by hand, stages 2 to 5 granted as the dev command does, then stages 6
        /// and 7 by hand to the end. True when the job finished; `session.LastResult` then holds the outcome.
        public bool PlaySlice(float grantPrecision = .9f)
        {
            if (!PlayThrough(1)) return false;
            if (s.State != AssemblySession.Phase.Working) return Fail("the job ended before the fit");
            int granted = s.DevGrant(new[] { "s2", "s3", "s4", "s5" }, grantPrecision);
            Log.Add("granted " + granted + " steps");
            if (!PlayThrough()) return false;
            return s.State == AssemblySession.Phase.Closed && s.LastResult != null || Fail("the job did not finish");
        }

        /// The whole job by hand, first action to last. True when it finished; `session.LastResult` holds the outcome.
        public bool PlayJob() => PlayThrough() && (s.State == AssemblySession.Phase.Closed && s.LastResult != null || Fail("the job did not finish"));

        /// Plays until the job is complete, the stage index passes `untilStage`, or an action cannot be done.
        public bool PlayThrough(int untilStage = int.MaxValue, int maxActions = 600)
        {
            for (int n = 0; n < maxActions; n++)
            {
                if (s.State != AssemblySession.Phase.Working || s.Job == null) return true;
                if (s.Job.Complete || s.Job.StageIndex > untilStage) return true;
                var next = s.Next; if (!next.HasValue) return Fail("the job is not complete and nothing is open");
                if (s.Job.Step(next.Value.step.id).actions.Length == 0) return Fail("step " + next.Value.step.id + " has nothing to do");
                if (!PlayNext()) return false;
            }
            return Fail("too many actions");
        }
    }
}
#endif
