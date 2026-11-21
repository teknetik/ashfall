using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
    /// The bench's sound, driven by event ids (`asm.<group>.<name>`, DESIGN.md section 11). Its own pool of sources on
    /// the SFX mixer group with its own voice limit, loops whose pitch follows resistance, and seat sounds chosen by
    /// the two materials that meet. An event without a clip is logged and silent: the audio arrives after the system.
    public sealed class AssemblyAudio
    {
        readonly AssemblyBench bench;
        readonly AssemblySettings settings;
        readonly List<AudioSource> shots = new List<AudioSource>();
        readonly Dictionary<string, AudioSource> loops = new Dictionary<string, AudioSource>();
        readonly Dictionary<string, string> loopEvents = new Dictionary<string, string>();
        readonly Dictionary<string, float> lastStart = new Dictionary<string, float>();
        readonly Dictionary<string, int> lastVariant = new Dictionary<string, int>();
        readonly Dictionary<string, float> strokeAgain = new Dictionary<string, float>();
        readonly Dictionary<string, Vector2> strokeLevel = new Dictionary<string, Vector2>();
        GameObject host;
        /// Every event asked for, newest last (also when silent): QA and tests read this.
        public readonly List<string> Log = new List<string>();
        public int Played { get; private set; }
        public float effectsLevel = 1;
        public System.Func<float> Clock = () => Time.unscaledTime;

        public AssemblyAudio(AssemblyBench bench, AssemblySettings settings) { this.bench = bench; this.settings = settings; }

        /// Every event id asked for since the sitting began.
        public readonly HashSet<string> Heard = new HashSet<string>();
        void Note(string id) { Heard.Add(id); Log.Add(id); if (Log.Count > 64) Log.RemoveAt(0); }
        AudioSource NewSource(string name, bool loop)
        {
            if (!host) { host = new GameObject("Assembly audio") { hideFlags = HideFlags.DontSave }; host.transform.SetParent(bench.transform, false); }
            var go = new GameObject(name); go.transform.SetParent(host.transform, false);
            var s = go.AddComponent<AudioSource>();
            s.playOnAwake = false; s.loop = loop; s.spatialBlend = .55f; s.minDistance = .6f; s.maxDistance = 9; s.rolloffMode = AudioRolloffMode.Linear; s.priority = 96;
            s.outputAudioMixerGroup = bench.mixerGroup;
            return s;
        }
        AudioClip Variant(AssemblyAudioTable.Event e)
        {
            if (e == null || e.clips == null || e.clips.Length == 0) return null;
            lastVariant.TryGetValue(e.id, out int last);
            int i = e.clips.Length == 1 ? 0 : (last + 1 + Random.Range(0, e.clips.Length - 1)) % e.clips.Length;
            lastVariant[e.id] = i;
            return e.clips[i];
        }

        /// A one-shot at a point on the bench. `pitch01` (0 loose to 1 tight) picks the pitch inside the event's range;
        /// negative leaves it to a small random spread.
        public void Play(string id, Vector3 at, float volume = 1, float pitch01 = -1)
        {
            if (string.IsNullOrEmpty(id)) return;
            float now = Clock();
            if (lastStart.TryGetValue(id, out float t) && now - t < (settings ? settings.sameEventWindow : .04f) && now >= t) return;
            lastStart[id] = now; Note(id);
            var e = bench.audioTable ? bench.audioTable.Find(id) : null; var clip = Variant(e);
            if (!clip || !Application.isPlaying) return;
            AudioSource free = null;
            foreach (var s in shots) if (s && !s.isPlaying) { free = s; break; }
            if (!free) { if (shots.Count >= (settings ? settings.maxVoices : 8)) return; free = NewSource("shot " + shots.Count, false); shots.Add(free); }
            free.transform.position = at;
            free.pitch = pitch01 >= 0 ? Mathf.Lerp(e.pitchRange.x, e.pitchRange.y, Mathf.Clamp01(pitch01)) : Random.Range(.97f, 1.03f);
            free.volume = Mathf.Clamp01(e.volume * volume * (settings ? settings.volume : 1) * effectsLevel);
            free.clip = clip; free.Play(); Played++;
        }

        /// The contact of two materials, from the audio package's contact matrix (the part's material on the surface's).
        public void Contact(string a, string b, Vector3 at, float volume = 1)
        {
            a = string.IsNullOrEmpty(a) ? "steel" : a; b = string.IsNullOrEmpty(b) ? "rubber" : b;
            var table = bench.audioTable;
            string id = table ? table.ContactEvent(a, b) : null;
            if (string.IsNullOrEmpty(id)) id = "asm.seat." + a + "_" + b;
            Play(id, at, volume);
        }

        /// Starts (or keeps) a loop under a key; SetLoop moves its pitch and level while the verb works.
        /// An event the audio package did not make as a loop (a file stroke, a bite of the shears, a creak of the pliers) is
        /// never played as a looped clip: it is struck once, and again each time it has rung out while the hold lasts.
        public void Loop(string key, string id, Vector3 at, bool bed = false)
        {
            if (string.IsNullOrEmpty(id) || string.IsNullOrEmpty(key)) return;
            var e = bench.audioTable ? bench.audioTable.Find(id) : null;
            if (loopEvents.TryGetValue(key, out var running) && running == id)
            {
                if (loops.TryGetValue(key, out var live) && live)
                {
                    live.transform.position = at;
                    if (!live.loop && !live.isPlaying && strokeAgain.TryGetValue(key, out float again) && Clock() >= again) Strike(key, e, live);
                }
                return;
            }
            StopLoop(key);
            loopEvents[key] = id; Note(id);
            var clip = Variant(e);
            if (!clip || !Application.isPlaying) return;
            bool loop = e.loop || bed;
            var s = NewSource("loop " + key, loop); s.transform.position = at; loops[key] = s;
            if (!loop) { strokeLevel[key] = new Vector2(.5f, 1); s.clip = clip; Strike(key, e, s, false); return; }
            s.clip = clip; s.volume = 0; s.Play();
            // a bed (the shop from the bench) is not a point on the bench: flat, at its own level from the start
            if (bed) { s.spatialBlend = 0; s.priority = 140; s.pitch = 1; s.volume = Mathf.Clamp01(e.volume * (settings ? settings.volume : 1) * effectsLevel); }
        }
        /// True when an event would be struck again and again under a hold, not looped (it has clips and no loop flag).
        public bool IsStroke(string id) { var e = bench.audioTable ? bench.audioTable.Find(id) : null; return e != null && !e.loop; }
        public int Strokes { get; private set; }
        void Strike(string key, AssemblyAudioTable.Event e, AudioSource s, bool next = true)
        {
            if (e == null) return;
            if (next) { var clip = Variant(e); if (clip) s.clip = clip; }
            if (!s.clip) return;
            strokeLevel.TryGetValue(key, out var level);
            s.pitch = Mathf.Lerp(e.pitchRange.x, e.pitchRange.y, Mathf.Clamp01(level.x)) * Random.Range(.98f, 1.02f);
            s.volume = Mathf.Clamp01(e.volume * Mathf.Max(.35f, level.y) * (settings ? settings.volume : 1) * effectsLevel);
            s.Play(); Strokes++; Played++;
            strokeAgain[key] = Clock() + s.clip.length / Mathf.Max(.1f, s.pitch) + (settings ? settings.strokeGap : .1f);
        }
        public void SetLoop(string key, float pitch01, float volume)
        {
            if (!loops.TryGetValue(key ?? "", out var s) || !s || !loopEvents.TryGetValue(key, out var id)) return;
            var e = bench.audioTable ? bench.audioTable.Find(id) : null; if (e == null) return;
            // a stroke keeps the pitch and level it was struck with; the next one takes the new ones
            if (!s.loop) { strokeLevel[key] = new Vector2(pitch01, volume); return; }
            s.pitch = Mathf.Lerp(e.pitchRange.x, e.pitchRange.y, Mathf.Clamp01(pitch01));
            s.volume = Mathf.Clamp01(e.volume * volume * (settings ? settings.volume : 1) * effectsLevel);
        }
        public bool Looping(string key) => loopEvents.ContainsKey(key ?? "");
        public void StopLoop(string key)
        {
            if (string.IsNullOrEmpty(key)) return;
            loopEvents.Remove(key);
            strokeAgain.Remove(key); strokeLevel.Remove(key);
            if (loops.TryGetValue(key, out var s)) { loops.Remove(key); if (s) { if (Application.isPlaying) Object.Destroy(s.gameObject); else Object.DestroyImmediate(s.gameObject); } }
        }
        public void StopAll()
        {
            foreach (var key in new List<string>(loopEvents.Keys)) StopLoop(key);
            foreach (var s in shots) if (s) s.Stop();
        }
        public void Dispose()
        {
            StopAll(); shots.Clear();
            if (host) { if (Application.isPlaying) Object.Destroy(host); else Object.DestroyImmediate(host); }
        }
    }
}
