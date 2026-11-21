using System;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
    /// Brann walks the player through the first hand-made job (tutor agent, 21 Nov 2026; Carl: "Maybe Brann walking you
    /// through the process as this will be a players first craft"). A separate component on its own scene root
    /// ("Steady Hands bench tutor", BenchTutorInstall20261121) that only listens to the bench session: its next useful action
    /// (HintAction), progress (Idle, ActionDone), mistakes (Faulted). It speaks through the bench's own voice
    /// (BenchVoice.SayLine: Brann at his counter, captions in the bark strip) only while Brann is silent with nothing of the
    /// bench's queued, shows a small prompt by the work the first time each kind of action comes up, and asks the session for
    /// the ghost at once. It changes nothing about the job and never takes the hand.
    ///
    /// On for the first hand-made job of the recipe (and for a detached QA job); off for later hand-made jobs and whenever the
    /// Settings switch "Brann's guidance" is off. What was said is kept in the job's notes (AssemblyJob.Notes["tutor"], saved
    /// inside the bench blob), so a resumed job does not repeat itself.
    [DisallowMultipleComponent]
    public class BenchTutor : MonoBehaviour
    {
        public const string EnabledKey = "AthenHill.Settings.v1.BenchGuidance";
        public const string NoteKey = "tutor";
        static int enabledCache = -1;
        /// Settings: "Brann's guidance" (default on), saved locally like the bark captions switch.
        public static bool Enabled
        {
            get { if (enabledCache < 0) enabledCache = PlayerPrefs.GetInt(EnabledKey, 1) != 0 ? 1 : 0; return enabledCache == 1; }
            set { enabledCache = value ? 1 : 0; PlayerPrefs.SetInt(EnabledKey, enabledCache); PlayerPrefs.Save(); }
        }
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)] static void ResetStatics() { enabledCache = -1; }

        public BenchTutorLines lines;
        [Tooltip("The prompt's look (Scripts/Assembly/Tutor/BenchTutor.uss).")] public StyleSheet style;
        public BenchTutorScript.Tuning tuning = new BenchTutorScript.Tuning();

        [Tooltip("Seconds a refusal, an H or a camera announcement stays as a caption.")] public float flashSeconds = 4;
        [Tooltip("The next target glints again this often while nothing is being worked (it glints at once when it changes).")] public float glintEvery = 4;
        [Tooltip("A refusal is voiced at most this often (the caption always shows).")] public float refusalVoiceEvery = 20;

        public BenchTutorScript Script { get; private set; }
        public string PromptKey => Script != null ? Script.Prompt : null;
        public bool Bound => bound != null;
        AssemblySession bound; AssemblyJob boundJob; BenchTutorPrompt prompt; BenchTutorNote note;
        string heldStep, heldText, flashText, lastShot, glintFor; float flashLeft, glintLeft, refusalVoiceLeft;
        BarkCaptionView caption; bool captionShown;
        Func<AssemblyActionRef, string> lineFor;
        /// The caption kept on screen after Brann's line for a step in tuning.holdCaptionSteps (the before card), until its first
        /// result is in the job notes ("card:STEP", one hole per pulse) or the step is done; null when none.
        public string CaptionHeld => heldText;
        /// A short caption: a refusal, an H, a camera move (null when none).
        public string CaptionFlash => flashLeft > 0 ? flashText : null;
        /// What Brann's caption band shows for the tutor: only his own held line (the before card). Flashes (camera, refusals, H)
        /// are not his words and go to the unlabelled note under the action line (native sh-real4b: they read as BRANN).
        public string CaptionText => heldText;

        void Update() => Drive(AssemblySession.Current, Time.deltaTime);
        void OnDisable() => Unbind();

        /// One frame (the player loop, or a test with a session opened by hand).
        public void Drive(AssemblySession s, float dt)
        {
            bool working = s && s.State == AssemblySession.Phase.Working && s.Job != null;
            if (!working) { if (bound) Unbind(); return; }
            if (s != bound || s.Job != boundJob) Bind(s);
            Script.SetEnabled(Enabled);
            // the same action the bench's instruction line shows (AssemblySession.Next: what is in the hand, else a step the player
            // has started, else the first open one), so Brann and the line never name different steps (native sh-real5, frame 28:
            // the line said the punch while Brann said the trigger lead) and both follow a player who starts another step. An
            // optional step counts only once the player has taken it up (the pistol in the hand with its shake open).
            var r = s.Next;
            if (r.HasValue && r.Value.step.optional && !(s.HeldPart && r.Value.action.part == s.HeldPart.id)) r = s.HintAction();
            Script.Observe(r.HasValue ? NextOf(s, r.Value) : default);
            Script.Idle(s.Idle);
            if (Script.TakeGhost()) s.Hint(3);
            if (Script.On && HintPressed(s)) { Script.Repeat(); Flash(r.HasValue ? LineFor(r.Value) : null); }
            refusalVoiceLeft -= dt; flashLeft -= dt;
            var voice = s.Voice;
            string want = Script.Candidate(dt, voice == null || voice.Busy);
            if (want != null && voice != null)
            {
                var line = lines ? lines.Find(want) : null;
                if (line == null) Script.Drop(want);
                else if (voice.SayLine(BenchTutorLines.ToVoice(line))) { Script.Spoken(want); Persist(); Hold(line); }
            }
            if (Script.On) { Highlight(s, r, dt); AnnounceShot(s); }
            UpdateCaption(s);
            if (Application.isPlaying) { UpdatePrompt(s, r); UpdateNote(); }
        }
        void UpdateNote()
        {
            string text = Script.On ? CaptionFlash : null;
            if (note == null)
            {
                if (text == null) return;
                var hud = FindAnyObjectByType<CityHud>(); var doc = hud ? hud.GetComponent<UIDocument>() : null;
                if (!doc || doc.rootVisualElement == null || doc.rootVisualElement.panel == null) return;
                note = new BenchTutorNote(doc.rootVisualElement, style);
            }
            note.Show(text);
        }

        void Bind(AssemblySession s)
        {
            Unbind();
            bound = s; boundJob = s.Job;
            Script = new BenchTutorScript(t => lines && lines.Has(t), tuning);
            boundJob.Notes.TryGetValue(NoteKey, out var note);
            bool resumed = !string.IsNullOrEmpty(note) || boundJob.Seconds > 2 || boundJob.StageIndex > 0;
            Script.Begin(FirstJob(s), note, resumed);
            Script.SetEnabled(Enabled);
            s.ActionDone += OnActionDone; s.Faulted += OnFaulted; s.Refused += Refusal;
            lineFor = LineFor; s.LineFor = lineFor;
            lastShot = s.ShotNow; glintFor = null; glintLeft = 0; flashLeft = 0; refusalVoiceLeft = 0;
        }
        void Unbind()
        {
            if (captionShown) caption?.Hide();
            captionShown = false; heldStep = null; heldText = null; flashLeft = 0;
            if (bound)
            {
                bound.ActionDone -= OnActionDone; bound.Faulted -= OnFaulted; bound.Refused -= Refusal;
                if (bound.LineFor == lineFor) bound.LineFor = null;
            }
            bound = null; boundJob = null; lineFor = null;
            prompt?.Dispose(); prompt = null; note?.Dispose(); note = null;
        }

        static bool HintPressed(AssemblySession s)
        {
            if (!Application.isPlaying || !s.session || !s.session.input) return false;
            var a = s.session.input.BenchAction("Hint"); return a != null && a.WasPressedThisFrame();
        }

        // ------------------------------------------------------------------ the instruction line (Carl, 21 Nov: "idiot proof")
        string T(string table, string key) => lines ? lines.Text(table, key) : null;
        string Name(string partId) => T("names", partId) ?? "it";
        string ToolName(string tag) => T("tools", tag) ?? "the right tool";
        string HeldToolName(AssemblyPart tool)
        {
            if (!tool) return "the tool";
            if (lines) foreach (var p in lines.tools) if (tool.HasTag(p.key)) return p.value;
            return "the tool";
        }
        static string Fill(string template, string slot, string value) => (template ?? "").Replace("{" + slot + "}", value ?? "");
        static string LowerFirst(string t) => string.IsNullOrEmpty(t) ? t : char.ToLowerInvariant(t[0]) + t.Substring(1);
        static bool IsLoose(AssemblyPart p) => p && !p.IsFixture;

        /// The action line for an action in a guided job: what to do now with its control, a prefix when the hand is not ready,
        /// and the camera move it will bring. Null (the line hides) when guidance is off. No taper: every stage.
        public string LineFor(AssemblyActionRef r)
        {
            var s = bound; if (!s || Script == null || !Script.On) return null;
            var a = r.action; string text = T("actions", r.step.id + ":" + a.key);
            if (string.IsNullOrEmpty(text)) return null;
            var held = s.HeldTool; var part = s.bench ? s.bench.Part(a.part) : null;
            bool needsTool = !string.IsNullOrEmpty(a.tool) && a.tool != "*";
            bool toolOk = needsTool ? held && held.HasTag(a.tool) : a.tool == "*" || !held;
            bool carried = a.verb == AssemblyVerbKind.Flick || a.verb == AssemblyVerbKind.Point && a.mode == "aim";
            if (!toolOk && held) text = Fill(T("prefix", "put_back"), "held", HeldToolName(held));
            else if (!toolOk) text = Fill(T("prefix", "take_tool"), "tool", ToolName(a.tool));
            else if (carried && IsLoose(part) && s.HeldPart != part) text = Fill(T("prefix", "pick_up"), "part", Name(a.part)) + ", then " + LowerFirst(text);
            // the camera move this will bring, said before it happens
            var toolPart = needsTool ? s.bench.Tool(a.tool) : held;
            var handPart = (a.verb == AssemblyVerbKind.Seat || carried) && IsLoose(part) ? part : s.HeldPart;
            string shot = s.ShotFor(r, toolPart, handPart);
            if (!string.IsNullOrEmpty(shot) && shot != s.ShotNow) { var where = T("shots", shot); if (where != null) text += "  ·  " + Fill(T("prefix", "view"), "shot", where); }
            return text;
        }

        // ------------------------------------------------------------------ highlight, refusals, camera, captions
        /// The next target glints as soon as the action changes, and again every few seconds while nothing is worked.
        void Highlight(AssemblySession s, AssemblyActionRef? r, float dt)
        {
            if (!r.HasValue || s.Fx == null) return;
            string id = r.Value.Id; glintLeft -= dt;
            if (id == glintFor && (glintLeft > 0 || s.VerbAction.HasValue)) return;
            glintFor = id; glintLeft = glintEvery;
            var a = r.Value.action; var b = s.bench;
            var tool = string.IsNullOrEmpty(a.tool) || a.tool == "*" ? null : b.Tool(a.tool); var part = b.Part(a.part);
            var target = tool && tool != s.HeldTool ? tool : part && part != s.HeldPart ? part : b.Marker(a.target) ? b.Part(b.Marker(a.target).ownerPart) : part;
            if (target) s.Fx.Glint(target);
        }
        /// The bench refused a press (AssemblySession.Refused): what is wrong, and what to do instead, as a caption; Brann says it
        /// too, at most every refusalVoiceEvery seconds.
        public void Refusal(string kind, AssemblyPart part, AssemblyPart other)
        {
            if (Script == null || !Script.On || !bound) return;
            string template = T("refused", kind) ?? T("refused", "not_yet");
            string otherName = other ? (other.IsTool ? HeldToolName(other) : Name(other.id)) : "something";
            string text = Fill(Fill(template, "part", part ? Name(part.id) : "that"), "other", otherName);
            var r = bound.HintAction(); var now = r.HasValue ? LineFor(r.Value) : null;
            Flash(string.IsNullOrEmpty(now) ? text : text + " " + now);
            if (refusalVoiceLeft > 0 || bound.Voice == null || bound.Voice.Busy) return;
            var line = lines ? lines.Find("tutor.refused:" + kind) : null;
            if (line != null && bound.Voice.SayLine(BenchTutorLines.ToVoice(line))) refusalVoiceLeft = refusalVoiceEvery;
        }
        /// Every camera change in a guided job is captioned when it happens (and the action line says it before, LineFor).
        void AnnounceShot(AssemblySession s)
        {
            string now = s.ShotNow; if (now == lastShot) return;
            string before = lastShot; lastShot = now;
            if (string.IsNullOrEmpty(before) || string.IsNullOrEmpty(now)) return;
            var where = T("shots", now); if (where == null) return;
            bool back = now == "work" || now == "wide";
            Flash(Fill(T("prefix", back ? "view_back" : "view_now"), "shot", where));
        }
        void Flash(string text) { if (string.IsNullOrEmpty(text)) return; flashText = text; flashLeft = flashSeconds; }

        void Hold(BenchTutorLines.Line line)
        {
            if (line.kind == "step" && Array.IndexOf(tuning.holdCaptionSteps ?? new string[0], line.step) >= 0) { heldStep = line.step; heldText = line.text; }
            else if (line.kind == "verb" && heldStep != null && bound && bound.Job != null && Script.Current.step == heldStep) heldText += " " + line.text;
        }
        void UpdateCaption(AssemblySession s)
        {
            if (heldStep != null)
            {
                s.Job.Notes.TryGetValue("card:" + heldStep, out var holes);
                if (!string.IsNullOrEmpty(holes) || s.Job.IsDone(heldStep) || !Script.On) { heldStep = null; heldText = null; }
            }
            if (!Script.On) flashLeft = 0;
            if (!Application.isPlaying) return;
            string text = CaptionText;
            bool want = text != null && BarkDirector.CaptionsEnabled && s.Voice != null && !s.Voice.Speaking;
            if (want && caption == null)
            {
                var hud = FindAnyObjectByType<CityHud>(); var doc = hud ? hud.GetComponent<UIDocument>() : null;
                if (doc && doc.rootVisualElement?.panel != null) caption = BarkCaptionView.Bind(doc.rootVisualElement);
            }
            if (caption == null) return;
            if (want && (!captionShown || caption.Text != text)) { caption.Show("Brann", text); captionShown = true; }
            else if (!want && captionShown) { if (s.Voice == null || !s.Voice.Speaking) caption.Hide(); captionShown = false; }
        }

        /// Guidance runs until the player has finished a job at the bench by hand (CraftingModel.FinishedAtBench, saved
        /// additively; coordinator, 21 Nov: an older save that made the grip on the timer, before the bench, has never finished
        /// one, so it is guided). "Build by hand again" after a finished job is not. A detached QA job is guided. Auto-assemble
        /// never opens the bench, so it never meets the tutor.
        static bool FirstJob(AssemblySession s)
        {
            var craft = s.Link != null ? s.Link.Craft : null;
            if (s.Detached || !craft || !s.bench || !s.bench.recipe) return true;
            return GuidedFor(craft.Model, s.bench.recipe.data.craftRecipeId);
        }
        public static bool GuidedFor(CraftingModel model, string recipeId) => model == null || !model.FinishedAtBench(recipeId);

        static BenchTutorScript.Next NextOf(AssemblySession s, AssemblyActionRef r) => new BenchTutorScript.Next
        {
            stage = s.Job.StageIndex, step = r.step.id, key = r.action.key, teach = BenchTutorScript.TeachKey(r.action),
            recovery = r.step.recovery, optional = r.step.optional,
        };

        void OnActionDone(string stepId, string key)
        {
            var step = bound && bound.Job != null ? bound.Job.Step(stepId) : null;
            var a = step != null ? step.actions.FirstOrDefault(x => x.key == key) : null;
            // an optional step done (the quick shake before) does not count as having learnt that kind of action: its how-line
            // still plays, and the prompt comes back at the next required one (native sh-real5: Flick was never taught)
            if (step != null && !step.optional) Script?.ActionDone(BenchTutorScript.TeachKey(a));
            Persist();
        }
        void OnFaulted(string stepId, string kind) { if (bound && bound.Job != null) Script?.Fault(stepId, bound.Job.StageIndex); }
        void Persist() { if (Script != null && boundJob != null && Script.Guided) boundJob.Notes[NoteKey] = Script.Save(); }

        // ------------------------------------------------------------------ the on-screen prompt
        void UpdatePrompt(AssemblySession s, AssemblyActionRef? r)
        {
            string key = Script.Prompt;
            var cam = s.Rig != null ? s.Rig.Lens : null;
            if (key == null || !r.HasValue || !cam || s.VerbAction.HasValue) { prompt?.Hide(); return; }
            if (prompt == null)
            {
                var hud = FindAnyObjectByType<CityHud>(); var doc = hud ? hud.GetComponent<UIDocument>() : null;
                if (!doc || doc.rootVisualElement == null || doc.rootVisualElement.panel == null) return;
                prompt = new BenchTutorPrompt(doc.rootVisualElement, style);
            }
            // the target's whole picture on screen (the part, where it goes, the mark or the path, where the hand works), so the
            // prompt sits beside it and never on it (native sh-real9: the box covered the wrap to be peeled); every frame, so it
            // follows the camera, the swivel and the part
            var root = prompt.Root; if (root.panel == null) return;
            bool any = false; Vector2 min = default, max = default;
            void Add(Vector3 world)
            {
                var sp = cam.WorldToScreenPoint(world); if (sp.z <= 0) return;
                var pp = RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(sp.x, Screen.height - sp.y));
                if (!any) { min = max = pp; any = true; } else { min = Vector2.Min(min, pp); max = Vector2.Max(max, pp); }
            }
            foreach (var w in TargetPoints(s, r.Value)) Add(w);
            if (!any) { prompt.Hide(); return; }
            prompt.ShowBeside(key, Rect.MinMaxRect(min.x, min.y, max.x, max.y));
        }
        /// World points that make up what the player works on for an action: the part's renderers (bounds corners), the place
        /// or marks it goes to, the path, and where the hand works.
        static System.Collections.Generic.IEnumerable<Vector3> TargetPoints(AssemblySession s, AssemblyActionRef r)
        {
            var a = r.action; var b = s.bench;
            yield return s.ActPoint(r);
            var part = b.Part(a.part);
            if (part && part.gameObject.activeInHierarchy && part.renderers != null)
                foreach (var rd in part.renderers)
                {
                    if (!rd || !rd.enabled || !rd.gameObject.activeInHierarchy) continue;
                    var bb = rd.bounds; var c = bb.center; var e = bb.extents;
                    for (int i = 0; i < 8; i++) yield return c + Vector3.Scale(e, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                }
            foreach (var id in a.targets.Length > 0 ? a.targets : new[] { a.target })
            {
                var m = b.Marker(id); if (!m || !m.gameObject.activeInHierarchy) continue;
                yield return m.transform.position;
                if (m.points != null) foreach (var t in m.points) if (t) yield return t.position;
            }
        }
    }

    /// The prompt by the work the first time each kind of action comes up (native sh-real4b: the first one was tiny grey text,
    /// unreadable at 1080p). Two rows on a dark plate with the bench's bronze edge: a MOUSE chip with the mouse form, a KEYS chip
    /// with the keyboard form; the control words are bold. It stays until the action is being worked (BenchTutor hides it then).
    public sealed class BenchTutorPrompt
    {
        readonly VisualElement root, box; readonly Label mouse, keys; string shownKey;
        public BenchTutorPrompt(VisualElement root, StyleSheet style)
        {
            this.root = root;
            if (style && !root.styleSheets.Contains(style)) root.styleSheets.Add(style);
            box = new VisualElement { name = "bench-tutor-prompt", pickingMode = PickingMode.Ignore }; box.AddToClassList("bench-tutor-prompt");
            box.style.position = Position.Absolute; box.style.display = DisplayStyle.None;
            mouse = Row("MOUSE", "bench-tutor-mouse"); keys = Row("KEYS", "bench-tutor-keys");
            root.Add(box);
        }
        Label Row(string chip, string cls)
        {
            var row = new VisualElement { pickingMode = PickingMode.Ignore }; row.AddToClassList("bench-tutor-row"); box.Add(row);
            var c = new Label(chip) { pickingMode = PickingMode.Ignore }; c.AddToClassList("bench-tutor-chip"); row.Add(c);
            var t = new Label { pickingMode = PickingMode.Ignore, enableRichText = true }; t.AddToClassList(cls); row.Add(t);
            return t;
        }
        public bool Visible => box.resolvedStyle.display == DisplayStyle.Flex;
        public string Key => shownKey;
        public VisualElement Root => root;
        /// Top of the area the prompt may use (below the stage and action lines, the tutor note and Brann's captions) and the
        /// margin above the bottom controls, in reference panel pixels.
        public const float SafeTop = 170, SafeBottom = 90, SafeSide = 16, Gap = 28;
        /// Shows the prompt beside a target rectangle (panel coordinates), never on it when there is room anywhere.
        public void ShowBeside(string key, Rect target)
        {
            if (key != shownKey) { var t = BenchTutorScript.PromptText(key); mouse.text = t.mouse ?? ""; keys.text = t.keys ?? ""; shownKey = key; }
            float w = root.layout.width > 0 ? root.layout.width : 1920, h = root.layout.height > 0 ? root.layout.height : 1080;
            var size = new Vector2(box.layout.width > 0 ? box.layout.width : 460, box.layout.height > 0 ? box.layout.height : 84);
            var at = Place(target, size, Rect.MinMaxRect(SafeSide, SafeTop, w - SafeSide, h - SafeBottom), Gap);
            box.style.left = at.x; box.style.top = at.y;
            box.style.display = DisplayStyle.Flex;
        }
        /// Where a box of `size` goes beside `target` inside `safe`: right, left, below or above it, the roomiest side first (the
        /// side away from the work), clamped into the safe area; the first that does not touch the target, else the one that
        /// covers least of it. Pure, so Edit Mode tests can hold it to "never on the target".
        public static Vector2 Place(Rect target, Vector2 size, Rect safe, float gap)
        {
            var cands = new (float room, Vector2 at)[]
            {
                (safe.xMax - target.xMax, new Vector2(target.xMax + gap, target.center.y - size.y * .5f)),
                (target.xMin - safe.xMin, new Vector2(target.xMin - gap - size.x, target.center.y - size.y * .5f)),
                (safe.yMax - target.yMax, new Vector2(target.center.x - size.x * .5f, target.yMax + gap)),
                (target.yMin - safe.yMin, new Vector2(target.center.x - size.x * .5f, target.yMin - gap - size.y)),
            };
            System.Array.Sort(cands, (p, q) => q.room.CompareTo(p.room));
            Vector2 best = default; float bestCover = float.MaxValue;
            foreach (var c in cands)
            {
                var at = new Vector2(Mathf.Clamp(c.at.x, safe.xMin, Mathf.Max(safe.xMin, safe.xMax - size.x)), Mathf.Clamp(c.at.y, safe.yMin, Mathf.Max(safe.yMin, safe.yMax - size.y)));
                float cover = Covered(new Rect(at, size), target);
                if (cover <= 0) return at;
                if (cover < bestCover) { bestCover = cover; best = at; }
            }
            return best;
        }
        public static float Covered(Rect a, Rect b) { float x = Mathf.Min(a.xMax, b.xMax) - Mathf.Max(a.xMin, b.xMin), y = Mathf.Min(a.yMax, b.yMax) - Mathf.Max(a.yMin, b.yMin); return x > 0 && y > 0 ? x * y : 0; }
        public void Hide() { box.style.display = DisplayStyle.None; }
        public void Dispose() { box.RemoveFromHierarchy(); }
    }

    /// The tutor's own note under the bench's action line: camera announcements, refusals and H flashes. No speaker label: these
    /// are the game talking, not Brann. It follows the action line ("assembly-action") when that is on screen.
    public sealed class BenchTutorNote
    {
        readonly VisualElement root; readonly Label label;
        public BenchTutorNote(VisualElement root, StyleSheet style)
        {
            this.root = root;
            if (style && !root.styleSheets.Contains(style)) root.styleSheets.Add(style);
            label = new Label { name = "bench-tutor-note", pickingMode = PickingMode.Ignore }; label.AddToClassList("bench-tutor-note");
            label.style.position = Position.Absolute; label.style.display = DisplayStyle.None;
            root.Add(label);
        }
        public string Text => label.resolvedStyle.display == DisplayStyle.Flex ? label.text : null;
        public void Show(string text)
        {
            if (string.IsNullOrEmpty(text)) { if (label.style.display != DisplayStyle.None) label.style.display = DisplayStyle.None; return; }
            if (label.text != text) label.text = text;
            var action = root.Q<VisualElement>("assembly-action");
            float top = action != null && action.resolvedStyle.display == DisplayStyle.Flex && action.layout.height > 0 ? action.worldBound.yMax - root.worldBound.yMin + 6 : 120;
            label.style.left = 28; label.style.top = top;
            label.style.display = DisplayStyle.Flex;
        }
        public void Dispose() { label.RemoveFromHierarchy(); }
    }
}
