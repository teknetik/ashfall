using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
    /// The bench for QA: the `assembly` block of snapshot.json (enough to drive a real-input check: where on the screen
    /// each open action is done, what is held, the verb in progress) and the dev.assembly.* bridge commands.
    public static class AssemblyQa
    {
        static float[] Screen(Camera cam, Vector3 world)
        {
            if (!cam) return null;
            var p = cam.WorldToScreenPoint(world);
            return new[] { Mathf.Round(p.x * 10) / 10, Mathf.Round(p.y * 10) / 10, p.z > 0 ? 1f : 0f };
        }

        /// The four corners of a wipe zone's surface on the screen (u then v across it), for a check that rubs it with the pointer.
        static float[][] ZoneCorners(Camera cam, AssemblyMarker zone)
        {
            if (!zone || !cam) return null;
            AssemblyWipeMask.Axes(zone.size, out int iu, out int iv, out _);
            float[] P(float u, float v) { var l = Vector3.zero; l[iu] = u * zone.size[iu]; l[iv] = v * zone.size[iv]; return Screen(cam, zone.transform.TransformPoint(l)); }
            return new[] { P(-.5f, -.5f), P(.5f, -.5f), P(.5f, .5f), P(-.5f, .5f) };
        }

        /// The snapshot block, or the error in its place: a fault here must never take the rest of snapshot.json with it.
        public static object SafeSnapshot()
        {
            try { return Snapshot(); }
            catch (System.Exception e) { return new { available = false, error = e.GetType().Name + ": " + e.Message }; }
        }

        /// State for snapshot.json. Screen positions are pixels from the bottom-left; the third number is 1 when the point
        /// is in front of the camera.
        public static object Snapshot()
        {
            var s = AssemblySession.Current;
            if (!s || !s.bench) return new { available = false };
            var bench = s.bench; var job = s.Job;
            if (s.State == AssemblySession.Phase.Closed || job == null)
                return new { available = true, open = false, cameraBlendingBack = AssemblyCameraBlendOut.Running, recipe = bench.recipe ? bench.recipe.Id : null, station = bench.stationId, lastNotice = s.LastNotice,
                    lastResult = s.LastResult != null ? new { quality = s.LastResult.quality.ToString(), s.LastResult.score, s.LastResult.faults, s.LastResult.seconds } : null };
            var cam = s.Rig != null && s.Rig.Lens ? s.Rig.Lens : Camera.main;
            var stage = job.Stage; var next = s.Next;
            object Describe(AssemblyActionRef r)
            {
                var a = r.action; var tool = string.IsNullOrEmpty(a.tool) ? null : bench.Tool(a.tool); var part = bench.Part(a.part);
                return new
                {
                    step = r.step.id, key = a.key, id = r.Id, verb = a.verb.ToString(), a.mode, a.part, a.tool, a.toolMode, a.target, targets = a.targets, a.count, a.turns, a.lo, a.hi,
                    optional = r.step.optional, recovery = r.step.recovery, partial = s.Partial(r.Id),
                    at = Screen(cam, s.ActPoint(r)),
                    partAt = part && !part.Gone ? Screen(cam, part.GrabPoint) : null, partPlace = part ? part.place : null,
                    toolAt = tool ? Screen(cam, tool.GrabPoint) : null, toolInHand = tool && tool == s.HeldTool, toolModeNow = tool ? tool.Mode : null,
                    marks = a.targets.Select(id => bench.Marker(id)).Where(m => m).Select(m => new { m.id, at = Screen(cam, m.transform.position), shown = m.gameObject.activeInHierarchy }).ToArray(),
                    path = bench.Marker(a.target) && bench.Marker(a.target).kind == AssemblyMarkerKind.Path ? bench.Marker(a.target).points.Where(t => t).Select(t => Screen(cam, t.position)).ToArray() : null,
                    zone = a.verb == AssemblyVerbKind.Wipe ? ZoneCorners(cam, bench.Marker(a.target)) : null, coverage = a.verb == AssemblyVerbKind.Wipe ? bench.Wipe(a.target)?.Coverage : null,
                    a.seconds, a.shot
                };
            }
            var verb = s.Verb; var verbRef = s.VerbAction; var carry = s.CarryAction;
            return new
            {
                available = true, open = true, phase = s.State.ToString(), detached = s.Detached, recipe = job.Recipe.id, station = bench.stationId,
                stage = stage != null ? new { stage.id, stage.label, index = job.StageIndex, of = job.Recipe.stages.Length } : null,
                complete = job.Complete, seconds = job.Seconds, score = job.Score, quality = job.Quality.ToString(), faults = job.Faults, penalty = job.Penalty,
                steps = job.Recipe.Steps.Select(st => new { st.id, state = job.State(st.id).ToString(), done = job.ActionsDone(st.id), of = st.actions.Length, faults = job.FaultsOn(st.id), st.optional, st.recovery }).ToArray(),
                actions = job.OpenActions.Select(Describe).ToArray(),
                next = next.HasValue ? next.Value.Id : null,
                held = new
                {
                    part = s.HeldPart ? s.HeldPart.id : null, partAt = s.HeldPart ? Screen(cam, s.HeldPart.GrabPoint) : null,
                    tool = s.HeldTool ? s.HeldTool.id : null, toolMode = s.HeldTool ? s.HeldTool.Mode : null, toolAt = s.HeldTool ? Screen(cam, s.HeldTool.TipPoint) : null,
                    action = carry.HasValue ? carry.Value.Id : null, leaving = s.CarryLeaving, distanceMm = s.CarryDistanceMm, yawError = s.CarryYawError, aiming = s.Aiming, flipped = s.CarryFlipped
                },
                focus = s.Focus.Valid ? new { id = s.Focus.Id, kind = s.Focus.part ? "part" : s.Focus.marker.kind.ToString(), at = Screen(cam, s.Focus.Position) } : null,
                verb = verb != null && verbRef.HasValue ? new { id = verbRef.Value.Id, kind = verb.Kind.ToString(), s.VerbStatus.progress, s.VerbStatus.value, s.VerbStatus.count, s.VerbStatus.waiting, at = Screen(cam, verb.ActPoint) } : null,
                camera = s.Rig != null ? new { shot = s.ShotNow, pinned = s.PinnedShot, shots = s.ShotNames.ToArray(), zoom = s.Rig.Zoom, side = s.Rig.Side, squaring = s.Squaring, viseYaw = s.Vise != null ? s.Vise.Yaw : 0, yaw = s.Rig.Yaw, pitch = s.Rig.Pitch, blending = s.Rig.Blending, active = s.Rig.Active } : null,
                wipes = bench.Wipes.OrderBy(w => w.zone).Select(w => new { w.zone, coverage = w.Coverage }).ToArray(),
                hint = new { level = s.HintLevel, idle = s.Idle },
                refusals = s.Refusals,
                audio = s.Audio != null ? new { events = s.Audio.Log.Skip(Mathf.Max(0, s.Audio.Log.Count - 16)).ToArray(), played = s.Audio.Played } : null,
                voice = s.Voice != null ? new { line = s.Voice.LineId, caption = s.Voice.Caption, triggers = s.Voice.Log.Skip(Mathf.Max(0, s.Voice.Log.Count - 8)).ToArray(), spoken = s.Voice.Spoken.Skip(Mathf.Max(0, s.Voice.Spoken.Count - 8)).ToArray() } : null,
                feedback = s.Fx != null ? s.Fx.Log.Skip(Mathf.Max(0, s.Fx.Log.Count - 8)).ToArray() : null,
                hud = s.Hud != null ? new { legend = s.Hud.LegendShown, stage = s.Hud.StageText, action = s.Hud.ActionText } : null, actionLine = s.ActionLine,
                parts = bench.Parts.Where(p => p && !p.IsFixture).OrderBy(p => p.id).Select(p => new { p.id, p.place, at = p.Gone ? null : Screen(cam, p.GrabPoint) }).ToArray(),
                blobLength = (s.Link?.Blob ?? "").Length, lastNotice = s.LastNotice
            };
        }

#if UNITY_EDITOR || DEBUG
        /// dev.assembly.open {force?} | close | complete {step, key?, precision?} | fault {step, kind} | grant {stages[], precision?}
        /// | finish {score? | quality?} | abandon | shot {shot} | hint {level?} | reset
        public static DevBridgeCommands.Result Execute(Newtonsoft.Json.Linq.JObject command, GameSession session)
        {
            string action = (string)command["action"];
            var s = AssemblySession.Current;
            if (!s || !s.bench) return DevBridgeCommands.Result.Fail("unavailable", "No assembly bench in this scene.");
            string Text(string key) => command[key]?.Type == Newtonsoft.Json.Linq.JTokenType.String ? (string)command[key] : null;
            float Number(string key, float fallback) { var t = command[key]; return t != null && (t.Type == Newtonsoft.Json.Linq.JTokenType.Float || t.Type == Newtonsoft.Json.Linq.JTokenType.Integer) ? Mathf.Clamp01((float)t) : fallback; }
            bool working = s.State == AssemblySession.Phase.Working;
            switch (action)
            {
                case "dev.assembly.state": return DevBridgeCommands.Result.Ok();
                case "dev.assembly.open":
                {
                    if (s.State != AssemblySession.Phase.Closed) return DevBridgeCommands.Result.Fail("invalid_state", "The bench is already open.");
                    if (session.State != CityState.Play) return DevBridgeCommands.Result.Fail("invalid_state", "Opening the bench needs Play.");
                    var station = Object.FindObjectsByType<CraftingStationMarker>(FindObjectsSortMode.None).FirstOrDefault(m => m.stationId == s.bench.stationId);
                    if (!station) return DevBridgeCommands.Result.Fail("unavailable", "No workbench with station " + s.bench.stationId + ".");
                    if (command["fresh"]?.Type == Newtonsoft.Json.Linq.JTokenType.Boolean && (bool)command["fresh"]) AssemblyCraftLink.ForgetDetached();
                    AssemblySession.AllowDetached = command["force"]?.Type == Newtonsoft.Json.Linq.JTokenType.Boolean && (bool)command["force"];
                    session.OpenAssembly(station, s.bench.recipe.data.craftRecipeId);
                    return session.State == CityState.Assembly ? DevBridgeCommands.Result.Ok() : DevBridgeCommands.Result.Fail("refused", "The session did not enter the bench state.");
                }
                case "dev.assembly.close":
                    if (session.State != CityState.Assembly) return DevBridgeCommands.Result.Fail("invalid_state", "The bench is not open.");
                    session.Close(); return DevBridgeCommands.Result.Ok();
            }
            if (!working) return DevBridgeCommands.Result.Fail("invalid_state", "Open the bench first (dev.assembly.open).");
            switch (action)
            {
                case "dev.assembly.complete":
                    return s.DevComplete(Text("step"), Text("key"), Number("precision", 1)) ? DevBridgeCommands.Result.Ok() : DevBridgeCommands.Result.Fail("not_open", "That step or action is not open now.");
                case "dev.assembly.fault":
                    return Text("kind") != null && s.DevFault(Text("step"), Text("kind")) ? DevBridgeCommands.Result.Ok() : DevBridgeCommands.Result.Fail("invalid_argument", "Give step and kind.");
                case "dev.assembly.grant":
                {
                    var stages = command["stages"] is Newtonsoft.Json.Linq.JArray arr ? arr.Select(x => (string)x).ToArray() : null;
                    if (stages == null || stages.Length == 0) return DevBridgeCommands.Result.Fail("invalid_argument", "Give stages: [\"s2\", ...].");
                    return s.DevGrant(stages, Number("precision", 1)) > 0 ? DevBridgeCommands.Result.Ok() : DevBridgeCommands.Result.Fail("nothing", "No step of those stages was left to grant.");
                }
                case "dev.assembly.finish":
                {
                    float score = Number("score", -1);
                    if (score < 0) { var q = Text("quality"); var rules = s.bench.recipe.data.quality; score = q == "Rough" ? rules.rough - .15f : q == "Fine" ? Mathf.Min(1, rules.fine + .1f) : (rules.rough + rules.fine) * .5f; }
                    return s.DevFinish(score) ? DevBridgeCommands.Result.Ok() : DevBridgeCommands.Result.Fail("refused", "The job could not be finished.");
                }
                case "dev.assembly.abandon": s.Abandon(); return DevBridgeCommands.Result.Ok();
                // shot: a cam_bench_ name holds that shot until an action is finished; "auto" (or none) lets the job choose again
                case "dev.assembly.shot": return s.DevShot(Text("shot")) ? DevBridgeCommands.Result.Ok() : DevBridgeCommands.Result.Fail("unknown_shot", "No cam_bench_ camera of that name.");
                case "dev.assembly.hint": s.Hint(Mathf.Clamp(Mathf.RoundToInt(command["level"] != null ? (float)command["level"] : 3), 1, 3)); return DevBridgeCommands.Result.Ok();
            }
            return DevBridgeCommands.Result.Fail("unknown_action", "Unknown assembly operation.");
        }
#endif
    }
}
