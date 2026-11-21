using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;
namespace AthenHill
{
    /// The seven input archetypes of the bench (DESIGN.md section 6). A step names one per action.
    public enum AssemblyVerbKind { Seat, Turn, Path, Window, Wipe, Point, Flick }
    /// Locked -> Available -> Active -> Done; a recovery step is Dormant until a fault calls for it.
    public enum AssemblyStepState { Locked, Available, Active, Done, Dormant }

    /// A mistake an action can report. `when`: "" = raised by the verb while working, "blocked" = raised when the player
    /// tries the action before the actions it waits for, "mode" = raised when the tool is set to the wrong mode (bit),
    /// "under" = a hold let go short of its window (a cold joint), "fast" = a turn driven too fast (the wire snaps, the drill binds),
    /// "misaligned" = a part offered to its seat the wrong way up, "poor:STEP" = raised in place of finishing when an earlier
    /// step was done badly (the rotor grinds if the race was not brushed clean), "wrong:PART" = the press landed on that part instead.
    [Serializable] public class AssemblyFaultDef
    {
        public string kind;
        public string when = "";
        [Tooltip("Taken off the job score each time.")] public float penalty = .02f;
        [Tooltip("The recovery step starts at this many faults of this kind on the step.")] public int after = 1;
        [Tooltip("Recovery step id made available (empty = try again in place).")] public string recovery;
        [Tooltip("What the mistake does to the bench when the recovery starts (the spring lands on the mat): same form as an action's effects.")] public string[] effects;
        [Tooltip("The action cannot be done again until the recovery step is finished (it grinds: brush it first, then spin it again).")] public bool blocks;
    }

    /// One thing the player does with their hands: a verb, what it is done to, with what, and its numbers.
    [Serializable] public class AssemblyActionDef
    {
        public string key;
        public AssemblyVerbKind verb;
        [Tooltip("Variant. Seat: inspect. Turn: stop, reveal. Window: hold, strike. Point: aim.")] public string mode = "";
        [Tooltip("The part handled: carried, turned, struck, shaken.")] public string part = "";
        [Tooltip("Tool id or tag that must be in the hand (empty = bare hand, * = whatever is in the hand).")] public string tool = "";
        [Tooltip("Tool setting needed, e.g. the screwdriver bit: slot or cross.")] public string toolMode = "";
        [Tooltip("Seat: a place id, or seat / start / clear. Point, Path, Wipe: a marker id.")] public string target = "";
        [Tooltip("Point: several marks, hit in any order.")] public string[] targets;
        [Tooltip("Repeats: strikes, shots, shakes.")] public int count = 1;
        [Tooltip("Turn: turns of the part (negative undoes).")] public float turns;
        [Tooltip("Turn: part turns per input turn. Lower is stiffer.")] public float gain = 1;
        [Tooltip("Window: the good band of the 0-1 value. Turn stop: extra turns allowed past `turns`. Path: pace band, m/s.")] public float lo, hi;
        [Tooltip("Window: rise of the value per second held. Flick: reversals per second needed.")] public float rate = 1;
        [Tooltip("Hold time: Flick keyboard form, cure waits.")] public float seconds;
        [Tooltip("Tolerance overrides (0 = the part's own).")] public float tolMm, tolDeg;
        [Tooltip("Path: a part that turns about the bench normal to keep the stretch of line being followed facing the eye (the vise on its swivel, for a wrap or a lead that runs round the back of the grip); it swings back when the line is done.")] public string swivel = "";
        [Tooltip("Path: how far along the line (m) the pointer may pick it up again ahead of where the work has got to (0 = 6 cm). Longer for a line that runs round the back of its part (the wrap), so the stretch out of sight is stepped over.")] public float ahead;
        [Tooltip("Parameter driven while working (vise jaw, latch), from `from` to `to`.")] public string drive = "";
        public float from, to = 1;
        [Tooltip("Seat: letting go before the part is clear is a fault (the spring).")] public bool keepHold;
        [Tooltip("Turn: the part does not spin with the hand; only the mechanism it drives moves (a latch thumbed back, a strap untied).")] public bool noSpin;
        [Tooltip("Camera shot while this action is the one in hand (empty = the stage's).")] public string shot = "";
        [Tooltip("Parts the work is done through or round (a scale laid on the sheet as a template): they are meant to be over the marks, so the sight check does not count them as in the way.")] public string[] through = new string[0];
        [Tooltip("What the action line on screen says while this is the next thing to do (for work a player cannot guess from the bench: the test card). Empty = no line.")] public string line = "";
        [Tooltip("Weight in the job's quality.")] public float weight = 1;
        [Tooltip("Action keys in this step that must be done first. Null = the action before this one; empty = none.")] public string[] after;
        [Tooltip("Applied when done: \"part>place\", \"part>seat\", \"part>gone\", \"param=0.5\".")] public string[] effects;
        public AssemblyFaultDef[] faults;
        [Tooltip("Audio event stem (asm.screw); the verb adds its own endings where it has them.")] public string audio = "";
        [Tooltip("Looping event while the verb works; pitch follows resistance.")] public string loop = "";
        [Tooltip("One-shot when the action is done.")] public string done = "";
    }

    [Serializable] public class AssemblyStepDef
    {
        public string id, label = "";
        [Tooltip("Not needed to finish the stage.")] public bool optional;
        [Tooltip("Only needed after the fault that names it.")] public bool recovery;
        [Tooltip("Actions can be done in any order (screws, plates) unless they give `after`.")] public bool free;
        [Tooltip("Step ids that must be done first (a dormant recovery step counts as done).")] public string[] requires;
        [Tooltip("Recovery steps: \"step:key\" actions this stands in for.")] public string[] replaces;
        [Tooltip("Inventory item ids that are used up once this step is done (cut, fused): lost if the job is abandoned.")] public string[] spends;
        public string shot = "";
        [Tooltip("Applied when the whole step is done, after its actions' own effects.")] public string[] effects;
        [Tooltip("Stepping back from the bench (Esc) counts as doing this step when it is the only one left: holster and leave.")] public bool onLeave;
        public AssemblyActionDef[] actions;
    }

    [Serializable] public class AssemblyStageDef
    {
        public string id, label = "";
        [Tooltip("Default camera shot of the stage.")] public string shot = "work";
        public AssemblyStepDef[] steps;
    }

    [Serializable] public class AssemblyQualityRules
    {
        [Tooltip("Under this the job is Rough.")] public float rough = .55f;
        [Tooltip("Above this the job is Fine.")] public float fine = .85f;
        [Tooltip("Penalty of a fault that names none.")] public float faultPenalty = .02f;
        [Tooltip("Faults can never take more than this off the score.")] public float maxPenalty = .5f;
        [Tooltip("Precision recorded for an action a recovery step stood in for.")] public float replacedPrecision = .35f;
    }

    /// The whole job as plain data. `art/steady_hands_bench_20261120/data/steps.json` is the editable source; the
    /// AssemblyRecipe asset is generated from it (AssemblyBenchInstall20261120, step `recipe`).
    [Serializable] public class AssemblyRecipeData
    {
        public string id = "", craftRecipeId = "", modItemId = "", weaponId = "";
        public AssemblyStageDef[] stages;
        public AssemblyQualityRules quality = new AssemblyQualityRules();
        public ItemStack[] byproducts;

        public static AssemblyRecipeData FromJson(string json)
        {
            var data = JsonConvert.DeserializeObject<AssemblyRecipeData>(json);
            if (data == null) throw new ArgumentException("Empty assembly recipe JSON");
            data.Normalise();
            return data;
        }

        /// Fills what the JSON may leave out (null arrays, default `after` chains) so readers need no null checks.
        public void Normalise()
        {
            stages ??= new AssemblyStageDef[0];
            quality ??= new AssemblyQualityRules();
            byproducts ??= new ItemStack[0];
            foreach (var stage in stages)
            {
                stage.steps ??= new AssemblyStepDef[0];
                foreach (var step in stage.steps)
                {
                    step.requires ??= new string[0]; step.replaces ??= new string[0]; step.spends ??= new string[0]; step.effects ??= new string[0];
                    step.actions ??= new AssemblyActionDef[0];
                    for (int i = 0; i < step.actions.Length; i++)
                    {
                        var a = step.actions[i];
                        if (string.IsNullOrEmpty(a.key)) a.key = "a" + (i + 1);
                        if (a.after == null) a.after = step.free || i == 0 ? new string[0] : new[] { step.actions[i - 1].key };
                        a.targets ??= new string[0]; a.effects ??= new string[0]; a.faults ??= new AssemblyFaultDef[0];
                        foreach (var fd in a.faults) { fd.effects ??= new string[0]; fd.when ??= ""; fd.recovery ??= ""; }
                        a.mode ??= ""; a.part ??= ""; a.tool ??= ""; a.toolMode ??= ""; a.target ??= ""; a.drive ??= ""; a.shot ??= "";
                        a.audio ??= ""; a.loop ??= ""; a.done ??= "";
                        if (a.count < 1) a.count = 1;
                    }
                }
            }
        }

        public IEnumerable<AssemblyStepDef> Steps { get { foreach (var s in stages) foreach (var st in s.steps) yield return st; } }
        /// The wipes this job changes: those a Wipe action works over and those an effect reveals ("~part/wipe"), by mask id.
        /// Any other wipe on the bench stays as found from the first minute to the last.
        public HashSet<string> WipesDriven()
        {
            var ids = new HashSet<string>();
            foreach (var st in Steps)
            {
                foreach (var e in st.effects) Driven(e, ids);
                foreach (var a in st.actions)
                {
                    if (a.verb == AssemblyVerbKind.Wipe && !string.IsNullOrEmpty(a.target)) ids.Add(a.target);
                    foreach (var e in a.effects) Driven(e, ids);
                    foreach (var f in a.faults) foreach (var e in f.effects) Driven(e, ids);
                }
            }
            return ids;
        }
        static void Driven(string effect, HashSet<string> ids)
        {
            effect = AssemblyBench.EffectBody(effect); if (string.IsNullOrEmpty(effect) || !effect.StartsWith("~")) return;
            int eq = effect.IndexOf('='); ids.Add((eq > 0 ? effect.Substring(1, eq - 1) : effect.Substring(1)).Trim());
        }

        /// Problems in the table itself (duplicate ids, unknown references, cycles). Empty = sound.
        public List<string> Validate()
        {
            var problems = new List<string>(); var ids = new HashSet<string>(); var stageIds = new HashSet<string>();
            foreach (var stage in stages)
            {
                if (string.IsNullOrEmpty(stage.id) || !stageIds.Add(stage.id)) problems.Add("stage id missing or repeated: " + stage.id);
                foreach (var step in stage.steps)
                {
                    if (string.IsNullOrEmpty(step.id) || !ids.Add(step.id)) problems.Add("step id missing or repeated: " + step.id);
                    var keys = new HashSet<string>();
                    foreach (var a in step.actions) if (!keys.Add(a.key)) problems.Add(step.id + ": action key repeated: " + a.key);
                    foreach (var a in step.actions) foreach (var k in a.after) if (!keys.Contains(k)) problems.Add($"{step.id}:{a.key} waits for unknown action {k}");
                }
            }
            var stageOf = new Dictionary<string, int>(); var defs = new Dictionary<string, AssemblyStepDef>();
            for (int i = 0; i < stages.Length; i++) foreach (var step in stages[i].steps) { stageOf[step.id] = i; defs[step.id] = step; }
            foreach (var step in Steps)
            {
                foreach (var r in step.requires)
                {
                    if (!defs.ContainsKey(r)) { problems.Add(step.id + " requires unknown step " + r); continue; }
                    if (stageOf[r] > stageOf[step.id]) problems.Add(step.id + " requires " + r + ", which is in a later stage");
                }
                foreach (var a in step.actions) foreach (var f in a.faults)
                {
                    if (string.IsNullOrEmpty(f.kind)) problems.Add($"{step.id}:{a.key} has a fault without a kind");
                    if (string.IsNullOrEmpty(f.recovery)) continue;
                    if (!defs.TryGetValue(f.recovery, out var rec)) problems.Add($"{step.id}:{a.key} fault {f.kind} names unknown recovery {f.recovery}");
                    else if (!rec.recovery) problems.Add($"{step.id}:{a.key} fault {f.kind}: {f.recovery} is not marked recovery");
                    else if (stageOf[f.recovery] < stageOf[step.id]) problems.Add($"{f.recovery} recovers {step.id} but sits in an earlier stage");
                }
                foreach (var rep in step.replaces)
                {
                    int colon = rep.IndexOf(':');
                    string sid = colon < 0 ? rep : rep.Substring(0, colon), key = colon < 0 ? null : rep.Substring(colon + 1);
                    if (!defs.TryGetValue(sid, out var origin) || key == null || Array.FindIndex(origin.actions, x => x.key == key) < 0) problems.Add(step.id + " replaces unknown action " + rep);
                    else if (stageOf[sid] != stageOf[step.id]) problems.Add(step.id + " replaces " + rep + " from another stage (the stage could never finish)");
                }
                if (step.recovery && step.actions.Length == 0) problems.Add(step.id + " is a recovery step with nothing to do");
            }
            // cycles in the requirement graph
            var mark = new Dictionary<string, int>();
            bool Visit(string id)
            {
                if (!defs.ContainsKey(id)) return false;
                mark.TryGetValue(id, out int m); if (m == 2) return false; if (m == 1) return true;
                mark[id] = 1; foreach (var r in defs[id].requires) if (Visit(r)) return true; mark[id] = 2; return false;
            }
            foreach (var id in ids) if (Visit(id)) { problems.Add("requirement cycle through " + id); break; }
            return problems;
        }
    }

    /// The Steady Hands job as an asset (Data/Assembly/assembly_grip_stabilised_pistol.asset). Generated from steps.json:
    /// edit the JSON and run the installer's `recipe` step, not this asset.
    public class AssemblyRecipe : ScriptableObject
    {
        public AssemblyRecipeData data = new AssemblyRecipeData();
        [Tooltip("SHA-1 of the steps.json this was generated from (verify compares it).")] public string sourceHash = "";
        public string Id => data != null ? data.id : "";
    }
}
