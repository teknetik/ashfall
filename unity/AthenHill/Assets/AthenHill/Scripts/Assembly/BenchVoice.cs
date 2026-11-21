using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
    /// Brann's lines at the bench. He stays behind his counter (DESIGN.md decision 15), so a line is his voice from where
    /// he stands, his talk clip (NpcAgent.barking) and a caption in the bark strip. Lines are looked up by trigger
    /// (audio/lines.json: stage.start:1, fault.first:camout, step.done:s1.inspect, hint.idle25:a ...). A trigger without
    /// a line says nothing; a line without a take is caption only.
    public sealed class BenchVoice
    {
        readonly AssemblyBench bench;
        readonly GameSession session;
        NpcAgent speaker; BarkCaptionView caption; DialogueNode node = new DialogueNode();
        AssemblyAudioTable.Line active; float left; bool shown;
        readonly Queue<string> waiting = new Queue<string>();
        /// Triggers asked for, newest last (also those without a line), and lines actually spoken.
        public readonly List<string> Log = new List<string>(), Spoken = new List<string>();
        public readonly HashSet<string> Asked = new HashSet<string>();
        public string Caption => active != null ? active.text : null;
        public string LineId => active?.id;
        public bool Speaking => active != null;
        /// Brann is speaking or has a line of the bench's queued (21 Nov, for the tutor: it speaks only when this is false).
        public bool Busy => active != null || waiting.Count > 0;
        /// Speaks a line from another table (the tutor's) when Brann is silent and nothing of the bench's is queued; the bench's own
        /// fault and stage lines always win. False when busy or no line.
        public bool SayLine(AssemblyAudioTable.Line line)
        {
            if (line == null || Busy) return false;
            Asked.Add("line:" + line.id); Log.Add("line:" + line.id); if (Log.Count > 48) Log.RemoveAt(0);
            Start(line); return true;
        }

        public BenchVoice(AssemblyBench bench, GameSession session) { this.bench = bench; this.session = session; }

        NpcAgent Speaker(string id)
        {
            if (speaker && speaker.definition && speaker.definition.id == id) return speaker;
            speaker = session && session.npcs != null ? session.npcs.FirstOrDefault(n => n && n.definition && n.definition.id == id) : null;
            if (!speaker) speaker = Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.None).FirstOrDefault(n => n && n.definition && n.definition.id == id);
            return speaker;
        }

        /// True when a line exists for the trigger (it is spoken now, or after the line in progress).
        public bool Say(string trigger, bool interrupt = false)
        {
            if (string.IsNullOrEmpty(trigger)) return false;
            Asked.Add(trigger); Log.Add(trigger); if (Log.Count > 48) Log.RemoveAt(0);
            var line = bench.audioTable ? bench.audioTable.FindLine(trigger) : null;
            if (line == null) return false;
            if (active != null && !interrupt) { if (!waiting.Contains(trigger) && waiting.Count < 3) waiting.Enqueue(trigger); return true; }
            Start(line);
            return true;
        }

        void Start(AssemblyAudioTable.Line line)
        {
            Stop(false);
            active = line; shown = false; Spoken.Add(line.id); if (Spoken.Count > 48) Spoken.RemoveAt(0);
            var who = Speaker(string.IsNullOrEmpty(line.speaker) ? "npc_brann" : line.speaker);
            left = BarkRules.CaptionSeconds(line.text, line.clip ? line.clip.length : 0);
            if (who && Application.isPlaying)
            {
                if (line.clip) { node.voice = line.clip; node.text = line.text; who.Speak(node, session ? session.Settings : null, Object.FindAnyObjectByType<CityAudio>()?.steps); }
                who.barking = true;
            }
        }

        public void Tick(float dt)
        {
            if (active == null) { if (waiting.Count > 0) { var next = bench.audioTable ? bench.audioTable.FindLine(waiting.Dequeue()) : null; if (next != null) Start(next); } return; }
            left -= dt;
            if (left <= 0) { Stop(false); return; }
            if (!Application.isPlaying) return;
            if (caption == null)
            {
                var hud = Object.FindAnyObjectByType<CityHud>(); var doc = hud ? hud.GetComponent<UIDocument>() : null;
                if (doc && doc.rootVisualElement?.panel != null) caption = BarkCaptionView.Bind(doc.rootVisualElement);
            }
            if (caption == null) return;
            bool want = BarkDirector.CaptionsEnabled;
            if (want && (!shown || caption.Text != active.text)) { caption.Show(speaker && speaker.definition ? speaker.definition.displayName : "Brann", active.text); shown = true; }
            else if (!want && shown) { caption.Hide(); shown = false; }
        }

        public void Stop(bool clearQueue = true)
        {
            if (clearQueue) waiting.Clear();
            if (active == null) return;
            if (speaker) { speaker.barking = false; if (Application.isPlaying && active.clip) speaker.StopSpeaking(); }
            if (shown) caption?.Hide();
            active = null; shown = false;
        }
    }
}
