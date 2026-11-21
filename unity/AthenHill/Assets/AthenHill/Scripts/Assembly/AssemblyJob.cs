using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
    /// What completing an action changed.
    public struct AssemblyProgress
    {
        public bool ok, stepDone, stageDone, jobDone;
        public string stageId;
        /// Steps that became available because of it.
        public List<string> unlocked;
    }

    /// What a reported mistake led to.
    public struct AssemblyFaultResult
    {
        public bool ok;
        public AssemblyFaultDef def;
        /// Times this kind has now happened on the step, and whether it is the first of its kind in the job.
        public int count; public bool first;
        public float penalty;
        /// Recovery step made available by this fault (null when none, or already running).
        public string recoveryStarted;
    }

    /// A reference to one action of one step.
    public struct AssemblyActionRef
    {
        public AssemblyStepDef step; public AssemblyActionDef action;
        public string Id => step.id + ":" + action.key;
    }

    /// The state of one bench job (DESIGN.md section 9): which steps and actions are done, faults, precision, elapsed
    /// time, quality. Pure C#: no scene, no Unity objects, serialised to the opaque blob the crafting system saves
    /// (CraftingSession.AssemblyBlob -> WardSaveData.benchJob).
    public sealed class AssemblyJob
    {
        sealed class Run
        {
            public AssemblyStepDef def; public int stage; public AssemblyStepState state; public bool granted;
            public readonly Dictionary<string, float> done = new Dictionary<string, float>();
            public readonly HashSet<string> replaced = new HashSet<string>();
            public readonly Dictionary<string, int> faults = new Dictionary<string, int>();
        }

        public readonly AssemblyRecipeData Recipe;
        readonly List<Run> order = new List<Run>();
        readonly Dictionary<string, Run> runs = new Dictionary<string, Run>();
        readonly HashSet<string> faultKindsSeen = new HashSet<string>();
        /// Seconds worked at the bench (the session adds to it while the player is working).
        public float Seconds;
        /// Small things the bench wants kept with the job that are not steps (where the holes are in the test cards).
        public readonly Dictionary<string, string> Notes = new Dictionary<string, string>();
        /// Sum of fault penalties so far (before the cap).
        public float Penalty { get; private set; }
        public int Faults { get; private set; }

        public AssemblyJob(AssemblyRecipeData recipe)
        {
            Recipe = recipe ?? throw new ArgumentNullException(nameof(recipe));
            for (int i = 0; i < recipe.stages.Length; i++)
                foreach (var step in recipe.stages[i].steps)
                {
                    var run = new Run { def = step, stage = i, state = step.recovery ? AssemblyStepState.Dormant : AssemblyStepState.Locked };
                    order.Add(run); runs[step.id] = run;
                }
            Refresh();
        }

        // ------------------------------------------------------------------ reading
        public AssemblyStepState State(string stepId) => runs.TryGetValue(stepId ?? "", out var r) ? r.state : AssemblyStepState.Locked;
        public bool IsDone(string stepId) => State(stepId) == AssemblyStepState.Done;
        public bool ActionDone(string stepId, string key) => runs.TryGetValue(stepId ?? "", out var r) && r.done.ContainsKey(key ?? "");
        /// Done because a recovery step stood in for it: its own effects never happened.
        public bool ActionReplaced(string stepId, string key) => runs.TryGetValue(stepId ?? "", out var r) && r.replaced.Contains(key ?? "");
        public int FaultsOn(string stepId, string kind = null) => runs.TryGetValue(stepId ?? "", out var r) ? kind == null ? r.faults.Values.Sum() : r.faults.TryGetValue(kind, out int n) ? n : 0 : 0;
        public AssemblyStepDef Step(string stepId) => runs.TryGetValue(stepId ?? "", out var r) ? r.def : null;
        public AssemblyActionDef Action(string stepId, string key) { var s = Step(stepId); return s == null ? null : Array.Find(s.actions, a => a.key == key); }
        public int ActionsDone(string stepId) => runs.TryGetValue(stepId ?? "", out var r) ? r.done.Count : 0;
        /// How well a step was done: the mean precision of its finished actions (1 when it has none yet).
        public float StepPrecision(string stepId) => runs.TryGetValue(stepId ?? "", out var r) && r.done.Count > 0 ? r.done.Values.Average() : 1;

        static bool Needed(Run r) => !r.def.optional && r.state != AssemblyStepState.Dormant;
        /// Index of the stage being worked: the first with a needed step not done. Equals the stage count when complete.
        public int StageIndex
        {
            get
            {
                for (int i = 0; i < Recipe.stages.Length; i++)
                    foreach (var r in order) if (r.stage == i && Needed(r) && r.state != AssemblyStepState.Done) return i;
                return Recipe.stages.Length;
            }
        }
        public AssemblyStageDef Stage { get { int i = StageIndex; return i < Recipe.stages.Length ? Recipe.stages[i] : null; } }
        public bool Complete => StageIndex >= Recipe.stages.Length;

        public IEnumerable<AssemblyStepDef> StepsIn(AssemblyStepState state) => order.Where(r => r.state == state).Select(r => r.def);
        /// Steps that can be worked now (Available or Active), in table order.
        public IEnumerable<AssemblyStepDef> OpenSteps => order.Where(r => r.state == AssemblyStepState.Available || r.state == AssemblyStepState.Active).Select(r => r.def);

        /// Why an action cannot be done now: null when it can; otherwise done, locked, after:KEY or recovery:STEP.
        public string Blocked(string stepId, string key)
        {
            if (!runs.TryGetValue(stepId ?? "", out var r)) return "locked";
            var a = Array.Find(r.def.actions, x => x.key == key);
            if (a == null) return "locked";
            if (r.done.ContainsKey(key)) return "done";
            if (r.state != AssemblyStepState.Available && r.state != AssemblyStepState.Active) return "locked";
            foreach (var other in order)
                if (other.def.recovery && (other.state == AssemblyStepState.Available || other.state == AssemblyStepState.Active || other.state == AssemblyStepState.Locked) && other.def.replaces.Contains(stepId + ":" + key))
                    return "recovery:" + other.def.id;
            // a fault of its own that must be put right first (it grinds: brush the race again, then spin it)
            foreach (var fd in a.faults)
                if (fd.blocks && !string.IsNullOrEmpty(fd.recovery) && runs.TryGetValue(fd.recovery, out var rec) && (rec.state == AssemblyStepState.Available || rec.state == AssemblyStepState.Active || rec.state == AssemblyStepState.Locked))
                    return "recovery:" + fd.recovery;
            foreach (var k in a.after) if (!r.done.ContainsKey(k)) return "after:" + k;
            return null;
        }
        public bool CanDo(string stepId, string key) => Blocked(stepId, key) == null;

        /// Every action that can be done now, in table order.
        public IEnumerable<AssemblyActionRef> OpenActions
        {
            get
            {
                foreach (var r in order)
                {
                    if (r.state != AssemblyStepState.Available && r.state != AssemblyStepState.Active) continue;
                    foreach (var a in r.def.actions) if (Blocked(r.def.id, a.key) == null) yield return new AssemblyActionRef { step = r.def, action = a };
                }
            }
        }

        /// Every action done so far whose own effects happened, in table order (the bench replays them to rebuild the scene).
        public IEnumerable<AssemblyActionRef> DoneActions
        {
            get
            {
                foreach (var r in order)
                    foreach (var a in r.def.actions)
                        if (r.done.ContainsKey(a.key) && !r.replaced.Contains(a.key)) yield return new AssemblyActionRef { step = r.def, action = a };
            }
        }

        /// Recovery steps that a fault has called for and that are not finished, each with the fault that started it
        /// (the bench re-applies that fault's effects when it rebuilds the scene).
        public IEnumerable<(AssemblyStepDef recovery, AssemblyFaultDef fault)> PendingRecoveries
        {
            get
            {
                foreach (var r in order)
                {
                    if (!r.def.recovery || r.state == AssemblyStepState.Dormant || r.state == AssemblyStepState.Done) continue;
                    AssemblyFaultDef found = null;
                    foreach (var other in order) { foreach (var a in other.def.actions) { foreach (var fd in a.faults) if (fd.recovery == r.def.id) { found = fd; break; } if (found != null) break; } if (found != null) break; }
                    yield return (r.def, found);
                }
            }
        }

        // ------------------------------------------------------------------ working
        void Refresh(List<string> unlocked = null)
        {
            int stage = StageIndex;
            foreach (var r in order)
            {
                if (r.state == AssemblyStepState.Done || r.state == AssemblyStepState.Dormant || r.state == AssemblyStepState.Active) continue;
                // an optional step belongs to its own stage: once the stage is done it lapses (it never comes back as work)
                bool open = (r.def.optional ? r.stage == stage : r.stage <= stage) && r.def.requires.All(Satisfied);
                var next = open ? AssemblyStepState.Available : AssemblyStepState.Locked;
                if (next == AssemblyStepState.Available && r.state == AssemblyStepState.Locked) unlocked?.Add(r.def.id);
                r.state = next;
            }
        }
        bool Satisfied(string stepId) => !runs.TryGetValue(stepId, out var r) || r.state == AssemblyStepState.Done || r.state == AssemblyStepState.Dormant;

        /// Records an action as done with a precision of 0 to 1. Refused when the action is not open (unless forced).
        public AssemblyProgress CompleteAction(string stepId, string key, float precision, bool force = false)
        {
            var result = new AssemblyProgress { unlocked = new List<string>() };
            if (!runs.TryGetValue(stepId ?? "", out var r) || Array.FindIndex(r.def.actions, a => a.key == key) < 0) return result;
            if (!force && Blocked(stepId, key) != null) return result;
            if (r.state == AssemblyStepState.Done) return result;
            int stageBefore = StageIndex;
            if (r.state == AssemblyStepState.Dormant || r.state == AssemblyStepState.Locked) r.state = AssemblyStepState.Available;
            r.done[key] = Mathf.Clamp01(precision); r.replaced.Remove(key);
            result.ok = true;
            Settle(r, ref result);
            Refresh(result.unlocked);
            int stageAfter = StageIndex;
            if (stageAfter > stageBefore) { result.stageDone = true; result.stageId = Recipe.stages[stageBefore].id; }
            result.jobDone = Complete;
            return result;
        }

        void Settle(Run r, ref AssemblyProgress result)
        {
            if (r.done.Count < r.def.actions.Length) { if (r.state != AssemblyStepState.Done) r.state = AssemblyStepState.Active; return; }
            if (r.state == AssemblyStepState.Done) return;
            r.state = AssemblyStepState.Done; result.stepDone = true;
            // a finished recovery stands in for the actions it replaces
            foreach (var rep in r.def.replaces)
            {
                int colon = rep.IndexOf(':'); if (colon < 0) continue;
                if (!runs.TryGetValue(rep.Substring(0, colon), out var origin)) continue;
                string k = rep.Substring(colon + 1);
                if (origin.state == AssemblyStepState.Done || origin.done.ContainsKey(k) || Array.FindIndex(origin.def.actions, a => a.key == k) < 0) continue;
                origin.done[k] = Recipe.quality.replacedPrecision; origin.replaced.Add(k);
                if (origin.state == AssemblyStepState.Locked || origin.state == AssemblyStepState.Available) origin.state = AssemblyStepState.Active;
                var ignored = new AssemblyProgress(); Settle(origin, ref ignored);
            }
        }

        /// Marks a whole step done at one precision (QA, and steps with nothing to do).
        public AssemblyProgress CompleteStep(string stepId, float precision = 1, bool granted = false)
        {
            var last = new AssemblyProgress { unlocked = new List<string>() };
            if (!runs.TryGetValue(stepId ?? "", out var r) || r.state == AssemblyStepState.Done) return last;
            int stageBefore = StageIndex;
            foreach (var a in r.def.actions) if (!r.done.ContainsKey(a.key)) r.done[a.key] = Mathf.Clamp01(precision);
            r.granted |= granted;
            if (r.state == AssemblyStepState.Dormant || r.state == AssemblyStepState.Locked) r.state = AssemblyStepState.Available;
            last.ok = true; Settle(r, ref last);
            Refresh(last.unlocked);
            if (StageIndex > stageBefore) { last.stageDone = true; last.stageId = Recipe.stages[stageBefore].id; }
            last.jobDone = Complete;
            return last;
        }

        /// QA: every needed step of the named stages done at one precision (the slice's "grip given complete").
        public List<string> Grant(IEnumerable<string> stageIds, float precision = 1)
        {
            var granted = new List<string>(); var want = new HashSet<string>(stageIds ?? new string[0]);
            foreach (var r in order.ToArray())
            {
                if (!want.Contains(Recipe.stages[r.stage].id) || r.def.recovery || r.state == AssemblyStepState.Done) continue;
                CompleteStep(r.def.id, precision, true); granted.Add(r.def.id);
            }
            return granted;
        }

        /// A mistake on an action. Faults never end the job: they cost quality and may make a recovery step available.
        public AssemblyFaultResult Fault(string stepId, string key, string kind)
        {
            var result = new AssemblyFaultResult();
            if (!runs.TryGetValue(stepId ?? "", out var r) || string.IsNullOrEmpty(kind)) return result;
            var action = Array.Find(r.def.actions, a => a.key == key);
            result.def = action != null ? Array.Find(action.faults, f => f.kind == kind) : null;
            r.faults.TryGetValue(kind, out int n); r.faults[kind] = ++n;
            result.ok = true; result.count = n; result.first = faultKindsSeen.Add(kind);
            result.penalty = result.def != null ? result.def.penalty : Recipe.quality.faultPenalty;
            Penalty += Mathf.Max(0, result.penalty); Faults++;
            if (result.def != null && !string.IsNullOrEmpty(result.def.recovery) && n >= Mathf.Max(1, result.def.after) && runs.TryGetValue(result.def.recovery, out var rec) && rec.state == AssemblyStepState.Dormant)
            {
                rec.state = AssemblyStepState.Locked; result.recoveryStarted = rec.def.id;
                Refresh();
            }
            return result;
        }

        /// The player stepped back: a step in progress goes back to Available and its unfinished work is dropped. Faults
        /// stay, and so does whatever a finished recovery stood in for.
        public void Leave()
        {
            foreach (var r in order)
            {
                if (r.state != AssemblyStepState.Active) continue;
                foreach (var k in r.done.Keys.Where(k => !r.replaced.Contains(k)).ToArray()) r.done.Remove(k);
                r.state = AssemblyStepState.Available;
            }
            Refresh();
        }

        // ------------------------------------------------------------------ quality
        /// Weighted mean of precision over the actions done, less the fault penalties (capped). 0 to 1.
        public float Score
        {
            get
            {
                float weight = 0, sum = 0;
                foreach (var r in order)
                    foreach (var a in r.def.actions)
                        if (r.done.TryGetValue(a.key, out float p) && a.weight > 0) { weight += a.weight; sum += a.weight * p; }
                float mean = weight > 0 ? sum / weight : 1;
                return Mathf.Clamp01(mean - Mathf.Min(Recipe.quality.maxPenalty, Penalty));
            }
        }
        public CraftQuality Quality => QualityFor(Score, Recipe.quality);
        public static CraftQuality QualityFor(float score, AssemblyQualityRules rules) => score < rules.rough ? CraftQuality.Rough : score > rules.fine ? CraftQuality.Fine : CraftQuality.Standard;

        /// The one step left when it is a step that stepping back from the bench completes (holster and leave); else null.
        public AssemblyStepDef LeaveStep
        {
            get
            {
                AssemblyStepDef only = null;
                foreach (var r in order) { if (!Needed(r) || r.state == AssemblyStepState.Done) continue; if (only != null || !r.def.onLeave || r.state == AssemblyStepState.Locked) return null; only = r.def; }
                return only;
            }
        }

        /// Inventory items already cut, fused or otherwise used up: lost if the job is abandoned.
        public string[] SpentInputs() => order.Where(r => r.state == AssemblyStepState.Done).SelectMany(r => r.def.spends).Distinct().OrderBy(x => x, StringComparer.Ordinal).ToArray();

        // ------------------------------------------------------------------ the blob
        [Serializable] sealed class BlobStep
        {
            public string id; public int state; public bool granted;
            public List<string> done = new List<string>(); public List<float> precision = new List<float>();
            public List<string> replaced = new List<string>();
            public List<string> faultKinds = new List<string>(); public List<int> faultCounts = new List<int>();
        }
        [Serializable] sealed class Blob
        {
            public int v = Version; public string recipe; public float seconds, penalty; public int faults;
            public List<string> seen = new List<string>();
            public List<string> noteKeys = new List<string>(), noteValues = new List<string>();
            public List<BlobStep> steps = new List<BlobStep>();
            // layout 1 (never shipped, kept so an early save cannot break a load): finished step ids only
            public List<string> done = new List<string>();
        }
        public const int Version = 2;

        public string ToBlob()
        {
            var blob = new Blob { recipe = Recipe.id, seconds = Seconds, penalty = Penalty, faults = Faults, seen = faultKindsSeen.OrderBy(x => x, StringComparer.Ordinal).ToList() };
            foreach (var n in Notes.OrderBy(x => x.Key, StringComparer.Ordinal)) { blob.noteKeys.Add(n.Key); blob.noteValues.Add(n.Value ?? ""); }
            foreach (var r in order)
            {
                bool recoveryRunning = r.def.recovery && r.state != AssemblyStepState.Dormant;
                // (a finished step with nothing to do has no actions to list, but it is finished all the same)
                if (r.done.Count == 0 && r.faults.Count == 0 && !recoveryRunning && r.state != AssemblyStepState.Done) continue;
                var s = new BlobStep { id = r.def.id, state = (int)r.state, granted = r.granted };
                foreach (var a in r.def.actions) if (r.done.TryGetValue(a.key, out float p)) { s.done.Add(a.key); s.precision.Add(p); }
                s.replaced.AddRange(r.replaced.OrderBy(x => x, StringComparer.Ordinal));
                foreach (var f in r.faults.OrderBy(x => x.Key, StringComparer.Ordinal)) { s.faultKinds.Add(f.Key); s.faultCounts.Add(f.Value); }
                blob.steps.Add(s);
            }
            return JsonUtility.ToJson(blob);
        }

        /// Rebuilds a job from a saved blob. Anything unreadable, from another recipe or naming steps that no longer
        /// exist is dropped, so a save can never stop the bench from opening. A step that was in progress is reset
        /// (DESIGN.md rule 6), exactly as Leave does.
        public static AssemblyJob FromBlob(AssemblyRecipeData recipe, string json)
        {
            var job = new AssemblyJob(recipe);
            if (string.IsNullOrWhiteSpace(json)) return job;
            Blob blob;
            try { blob = JsonUtility.FromJson<Blob>(json); } catch (ArgumentException) { return job; }
            if (blob == null || (!string.IsNullOrEmpty(blob.recipe) && blob.recipe != recipe.id)) return job;
            job.Seconds = Mathf.Max(0, blob.seconds);
            if (blob.v < 2)
            {
                // layout 1: finished steps at an unknown, middling precision
                foreach (var id in blob.done ?? new List<string>()) if (job.runs.ContainsKey(id ?? "")) job.CompleteStep(id, .7f);
                job.Faults = Mathf.Max(0, blob.faults); job.Penalty = job.Faults * recipe.quality.faultPenalty;
                return job;
            }
            job.Penalty = Mathf.Max(0, blob.penalty); job.Faults = Mathf.Max(0, blob.faults);
            foreach (var k in blob.seen ?? new List<string>()) if (!string.IsNullOrEmpty(k)) job.faultKindsSeen.Add(k);
            for (int i = 0; i < (blob.noteKeys?.Count ?? 0); i++) if (!string.IsNullOrEmpty(blob.noteKeys[i])) job.Notes[blob.noteKeys[i]] = blob.noteValues != null && i < blob.noteValues.Count ? blob.noteValues[i] : "";
            foreach (var s in blob.steps ?? new List<BlobStep>())
            {
                if (s == null || !job.runs.TryGetValue(s.id ?? "", out var r)) continue;
                for (int i = 0; i < (s.done?.Count ?? 0); i++)
                    if (Array.FindIndex(r.def.actions, a => a.key == s.done[i]) >= 0)
                        r.done[s.done[i]] = Mathf.Clamp01(s.precision != null && i < s.precision.Count ? s.precision[i] : .7f);
                foreach (var k in s.replaced ?? new List<string>()) if (r.done.ContainsKey(k ?? "")) r.replaced.Add(k);
                for (int i = 0; i < (s.faultKinds?.Count ?? 0); i++)
                    if (!string.IsNullOrEmpty(s.faultKinds[i])) r.faults[s.faultKinds[i]] = Mathf.Max(1, s.faultCounts != null && i < s.faultCounts.Count ? s.faultCounts[i] : 1);
                r.granted = s.granted;
                bool all = r.done.Count >= r.def.actions.Length && (r.def.actions.Length > 0 || s.state == (int)AssemblyStepState.Done);
                if (all) r.state = AssemblyStepState.Done;
                else if (r.def.recovery) r.state = s.state == (int)AssemblyStepState.Dormant ? AssemblyStepState.Dormant : AssemblyStepState.Locked;
                else r.state = r.done.Count > 0 ? AssemblyStepState.Active : AssemblyStepState.Locked;
            }
            job.Leave();
            return job;
        }
    }
}
