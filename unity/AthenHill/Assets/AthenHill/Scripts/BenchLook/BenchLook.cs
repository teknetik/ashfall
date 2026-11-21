using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill
{
    /// <summary>
    /// The look of the Steady Hands bench with its real models (integration pass, 20 November 2026; record
    /// art/steady_hands_bench_20261120/integration/README.md). It sits on the scene root "Steady Hands bench light" and
    /// writes nothing into the bench's own prefab: the bench (AssemblyBench, AssemblySession) is found when the scene
    /// starts, so the bench's installer can rebuild its prefab at any time.
    ///
    /// What it does:
    ///  * puts the real parts on their Bench Surface materials (by the glTF material's name; stand-ins keep theirs), with
    ///    the as-found variant on the parts a family lists under `wipes` and the lamp variant on the bench's lamps;
    ///  * feeds the bench's wipe masks (AssemblyBench.Wipe, WipeChanged) to those parts' renderers, zone by zone;
    ///  * cures the nanite seam while the job waits under the cure lamp;
    ///  * while the bench is in use: brings the work lamp up (the one shadowed light of the shop), takes the shop's own
    ///    lamps down, dims the old workbench's screen, and lights the cure lamp when the bench switches its head on.
    ///    Everything is put back on leaving, so nothing changes for a camera anywhere else.
    /// Development players: ATHEN_BENCH_LOOK=off | always | noshadow | nodim (comma separated) for A/B runs and stills.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(1500)]   // after the session, the feedback and InteriorLighting; before LightBudget (2000) counts the lights
    public class BenchLook : MonoBehaviour
    {
        [Serializable] public class Surface
        {
            [Tooltip("Name of the material in the family's GLB (M_pistol, glass_cell, ...)")] public string source = "";
            public Material plain;
            [Tooltip("With the family's as-found set (parts listed under wipes); null = none")] public Material wipe;
            [Tooltip("For a part the bench drives as a lamp: no emission of its own, the tint lights the whole surface")] public Material lamp;
        }
        [Serializable] public class WipePart
        {
            public string part = "";
            [Tooltip("The wipe's id in the family (dust, corrosion, seam)")] public string group = "";
            [Tooltip("Zone marker ids (servo.case_lid/dust) whose masks clean this part")] public string[] zones = new string[0];
            [Tooltip("The zones are this part's own (its modelled zones, or the bench's whole-part zone for a wipe an effect reveals): nothing else cleans it. Off: it has none and comes clean as its group's zones are finished")] public bool ownZones = true;
        }

        [Header("Surfaces (written by SteadyHandsBenchInstall20261120)")]
        public Surface[] surfaces = new Surface[0];
        public WipePart[] wipeParts = new WipePart[0];
        [Tooltip("Metres past a zone's box over which its mask still cleans")] public float wipeReach = .012f;
        [Tooltip("Parts of the bench cast shadows while the bench is in use (stand-ins too). Away from the bench none do, as for every prop in the shop, so they never cost a sun shadow pass")] public bool partsCastShadows = true;

        /// A part that comes clean by something the job does, not by a wipe: the seam under the cure lamp, strands once
        /// tinned, a dimple once punched (SEAM.md section 10: as found is the starting state of every wipe).
        [Serializable] public class Reveal
        {
            public string[] parts = new string[0];
            public string step = "", action = "";
            [Tooltip("Follows the action's own progress while it runs (a wait), not only its end")] public bool progress;
            [ColorUsage(false, true)] public Color glow = Color.black;
            [Tooltip("Seconds from the action being done to fully clean")] public float settle = .5f;
        }
        [Tooltip("Parts that never cast: the flat mats everything lies on. A big flat receiver in the shadow map shades itself in bands (acne) at the edge of the lamp's pool; what lies on them still casts onto them")]
        public string[] noShadowParts = new string[0];

        /// A part no ray leaves while it and its shells sit as found (art/steady_hands_bench_20261120/integration/enclosure.py:
        /// the servo's insides under its lid). It is not drawn then (forceRenderingOff), which saves a draw per part in
        /// every shot; the moment it or any shell is off its seat, moved, reparented or gone, it is drawn again.
        [Serializable] public class Enclosed
        {
            public string part = "";
            [Tooltip("The parts the rays meet last on their way out (case body, lid, screws in the lid)")] public string[] shells = new string[0];
        }
        [Header("Not drawn while closed in")]
        public Enclosed[] enclosed = new Enclosed[0];
        [Tooltip("Metres a part may sit off its rest pose and still count as seated")] public float enclosedSlack = .001f;

        [Header("Clean by what the job does")]
        public Reveal[] reveals = new Reveal[0];

        [Header("Lamps")]
        [Tooltip("The bench work lamp: on only while the bench is in use")] public Light key;
        public float keyIntensity = .8f;
        [Tooltip("The cure lamp: follows the bench's lamp part and its level")] public Light cureLamp;
        public string cureLampPart = "fixtures.lamp_head";
        public float cureIntensity = .5f;
        public Vector3 cureLampOffset = new Vector3(0, -.02f, 0);
        [Tooltip("Seconds to bring the lamp up or down")] public float fadeSeconds = .6f;
        [Tooltip("The shop's own lamps while the bench is in use (1 = unchanged)")] [Range(0, 1)] public float roomDim = .4f;
        [Tooltip("The old workbench's screen while the bench is in use")] [Range(0, 1)] public float screenDim = .12f;
        [Tooltip("The screen's glow light while the bench is in use (it hangs 0.34 m over the work mat and out-shines the work lamp in blue)")] [Range(0, 1)] public float glowDim = .04f;
        [Tooltip("Material name of the old workbench's screen")] public string screenMaterial = "SS_FabScreen";
        [Tooltip("Shop lamps that follow the screen instead of the room")] public string screenLampName = "Fabricator glow";

        // ---- state, for QA and the Player.log line
        public int BoundRenderers { get; private set; }
        public int WipeRenderers { get; private set; }
        public int LampRenderers { get; private set; }
        public int UnknownMaterials { get; private set; }
        /// 0 = away from the bench, 1 = the bench is lit for work.
        public float Weight { get; private set; }
        public AssemblyBench Bench => bench;
        /// Renderers not drawn this frame because their part is closed in.
        public int HiddenRenderers { get; private set; }

        const int MaxZones = 6;
        static readonly int EmissionId = Shader.PropertyToID("_EmissionColor"), ToZoneId = Shader.PropertyToID("_BenchWipeToZone"), SizeId = Shader.PropertyToID("_BenchWipeSize"),
            StateId = Shader.PropertyToID("_BenchWipeState"), MasksId = Shader.PropertyToID("_BenchWipeMasks"), GlowId = Shader.PropertyToID("_BenchGlow");

        sealed class Zone { public string id; public AssemblyMarker marker; public int slice; public int version = -1; public bool wipedByJob; }
        sealed class Bound { public WipePart def; public AssemblyPart part; public Renderer[] renderers; public Zone[] zones; public Reveal reveal; public float shown; }

        AssemblyBench bench; AssemblySession session; InteriorLighting room;
        readonly Dictionary<string, Zone> zones = new Dictionary<string, Zone>();
        readonly List<Bound> bound = new List<Bound>();
        readonly Dictionary<string, Surface> byName = new Dictionary<string, Surface>();
        Texture2DArray masks; MaterialPropertyBlock block;
        readonly Matrix4x4[] toZone = new Matrix4x4[MaxZones]; readonly Vector4[] zoneSize = new Vector4[MaxZones];
        Renderer screen; Color screenBase; Light[] roomLamps = new Light[0]; float[] roomBase = new float[0];
        readonly List<Renderer> casters = new List<Renderer>();
        bool off, always, noShadow, noDim, wasWorking, dimmed, started, casting; float stepSeconds, enclosedClock;
        sealed class Closed { public Renderer[] renderers; public AssemblyPart[] links; }
        readonly List<Closed> closed = new List<Closed>();

        void Start()
        {
            block = new MaterialPropertyBlock();
#if UNITY_EDITOR || DEBUG
            var env = (Environment.GetEnvironmentVariable("ATHEN_BENCH_LOOK") ?? "").ToLowerInvariant();
            foreach (var word in env.Split(',')) { off |= word == "off"; always |= word == "always"; noShadow |= word == "noshadow"; noDim |= word == "nodim"; }
            if (env != "") Debug.Log("BenchLook: ATHEN_BENCH_LOOK=" + env);
#endif
            if (key) key.enabled = false;
            if (cureLamp) cureLamp.enabled = false;
            if (off) { enabled = false; return; }
            bench = FindAnyObjectByType<AssemblyBench>(FindObjectsInactive.Include);
            if (!bench) { Debug.LogWarning("BenchLook: no AssemblyBench in the scene"); enabled = false; return; }
            session = bench.GetComponent<AssemblySession>();
            foreach (var il in FindObjectsByType<InteriorLighting>(FindObjectsInactive.Include))
                if (Array.IndexOf(il.interiorRoots, bench.transform) >= 0) { room = il; break; }
            if (room)
            {
                roomLamps = Array.FindAll(room.lamps ?? new Light[0], l => l); roomBase = Array.ConvertAll(roomLamps, l => l.intensity);
                foreach (var r in room.GetComponentsInChildren<Renderer>(true))
                    if (r.sharedMaterial && r.sharedMaterial.name == screenMaterial) { screen = r; screenBase = r.sharedMaterial.HasProperty(EmissionId) ? r.sharedMaterial.GetColor(EmissionId) : Color.black; break; }
            }
            if (key && noShadow) key.shadows = LightShadows.None;
            Bind();
            bench.WipeChanged += OnWipe;
            started = true;
            Debug.Log($"BenchLook: {BoundRenderers} renderers on bench surfaces ({WipeRenderers} as found, {LampRenderers} lamps), {UnknownMaterials} real materials with no surface, {zones.Count} wipe zones, room {(room ? room.name : "none")}, screen {(screen ? "found" : "none")}, {roomLamps.Length} shop lamps");
        }

        void OnDestroy()
        {
            ShowEnclosed();
            if (bench) bench.WipeChanged -= OnWipe;
            Restore();
            if (masks) Destroy(masks);
        }
        void OnDisable() { if (started) Restore(); }

        // ------------------------------------------------------------------ surfaces
        /// Puts every real renderer of the bench on its surface and gathers the wipe zones. Safe to call again.
        public void Bind()
        {
            if (!bench) return;
            bench.Index(true);
            byName.Clear(); foreach (var s in surfaces) if (s != null && !string.IsNullOrEmpty(s.source)) byName[s.source] = s;
            var mine = new HashSet<Material>();
            foreach (var s in surfaces) { if (s == null) continue; if (s.plain) mine.Add(s.plain); if (s.wipe) mine.Add(s.wipe); if (s.lamp) mine.Add(s.lamp); }
            var wipeOf = new Dictionary<string, WipePart>(); foreach (var w in wipeParts) if (w != null && !string.IsNullOrEmpty(w.part)) wipeOf[w.part] = w;
            var lampParts = new HashSet<string>(); foreach (var l in bench.lamps) if (l != null) lampParts.Add(l.part);
            // the masks the job changes: by a wipe, or by an effect that reveals one (a punched dimple, tinned strands)
            var jobWipes = bench.recipe && bench.recipe.data != null ? bench.recipe.data.WipesDriven() : new HashSet<string>();

            BoundRenderers = WipeRenderers = LampRenderers = UnknownMaterials = 0; bound.Clear(); zones.Clear(); casters.Clear();
            var seen = new HashSet<Renderer>();
            foreach (var part in bench.Parts)
            {
                if (!part) continue;
                bool isLamp = lampParts.Contains(part.id); wipeOf.TryGetValue(part.id, out var wipe);
                var wiped = new List<Renderer>();
                foreach (var r in part.renderers)
                {
                    if (!r || !seen.Add(r)) continue;
                    var mats = r.sharedMaterials; bool changed = false, real = false, asFound = false;
                    for (int i = 0; i < mats.Length; i++)
                    {
                        var m = mats[i]; if (!m) continue;
                        if (mine.Contains(m)) { real = true; asFound |= wipe != null && m.IsKeywordEnabled("_BENCH_WIPE"); continue; }
                        if (!byName.TryGetValue(m.name, out var s)) { if (m.shader && m.shader.name.Contains("glTF")) UnknownMaterials++; continue; }
                        var to = isLamp && s.lamp ? s.lamp : wipe != null && s.wipe ? s.wipe : s.plain;
                        if (!to) continue;
                        mats[i] = to; changed = true; real = true; asFound |= to == s.wipe;
                    }
                    if (changed) r.sharedMaterials = mats;
                    if (!r.name.StartsWith("decal_") && Array.IndexOf(noShadowParts, part.id) < 0) casters.Add(r);
                    else if (r.shadowCastingMode != ShadowCastingMode.Off) r.shadowCastingMode = ShadowCastingMode.Off;
                    if (!real) continue;
                    BoundRenderers++; if (isLamp) LampRenderers++;
                    if (asFound) { wiped.Add(r); WipeRenderers++; }
                }
                if (wipe == null || wiped.Count == 0) continue;
                var list = new List<Zone>();
                foreach (var id in wipe.zones)
                {
                    if (list.Count >= MaxZones) break;
                    var marker = bench.Marker(id); if (!marker || marker.kind != AssemblyMarkerKind.Zone) continue;
                    if (!zones.TryGetValue(id, out var z)) zones[id] = z = new Zone { id = id, marker = marker, slice = zones.Count, wipedByJob = jobWipes.Contains(id) };
                    list.Add(z);
                }
                Reveal reveal = null; foreach (var rv in reveals) if (rv != null && Array.IndexOf(rv.parts, part.id) >= 0) { reveal = rv; break; }
                // (a reveal already done is shown as done: its glow is not played again each time the bench is opened)
                bound.Add(new Bound { def = wipe, part = part, renderers = wiped.ToArray(), zones = list.ToArray(), reveal = reveal, shown = reveal != null && Progress(reveal) >= 1 ? 1 : 0 });
            }
            // anything of a real family that is not a part's own renderer (none today) still gets its plain surface
            foreach (var r in bench.GetComponentsInChildren<Renderer>(true))
            {
                if (!seen.Add(r)) continue;
                var mats = r.sharedMaterials; bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                    if (mats[i] && !mine.Contains(mats[i]) && byName.TryGetValue(mats[i].name, out var s) && s.plain) { mats[i] = s.plain; changed = true; }
                if (changed) { r.sharedMaterials = mats; BoundRenderers++; }
            }
            ShowEnclosed(); closed.Clear();
            foreach (var e in enclosed)
            {
                if (e == null) continue;
                var links = Links(bench, e, enclosedSlack, out var part);
                if (links == null || !part) continue;
                closed.Add(new Closed { renderers = Array.FindAll(part.renderers, r => r), links = links.ToArray() });
            }
            UpdateEnclosed();
            if (masks && masks.depth != Mathf.Max(1, zones.Count)) { Destroy(masks); masks = null; }
            if (!masks && bound.Count > 0)
                masks = new Texture2DArray(AssemblyWipeMask.N, AssemblyWipeMask.N, Mathf.Max(1, zones.Count), TextureFormat.R8, false, true) { name = "Bench wipe masks", wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, hideFlags = HideFlags.DontSave };
            foreach (var z in zones.Values) z.version = -1;
            UploadMasks(); PushWipes();
            casting = !casting; Cast(!casting);
        }

        void Cast(bool on)
        {
            if (casting == on) return;
            casting = on;
            var mode = on && partsCastShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
            foreach (var r in casters) if (r && r.shadowCastingMode != mode) r.shadowCastingMode = mode;
        }

        void OnWipe(AssemblyWipeMask mask) { UploadMasks(); }

        void UploadMasks()
        {
            if (!masks) return;
            bool any = false;
            foreach (var z in zones.Values)
            {
                var m = bench.Wipe(z.id); if (m == null || m.Version == z.version) continue;
                masks.SetPixelData(m.cells, 0, z.slice); z.version = m.Version; any = true;
            }
            if (any) masks.Apply(false);
        }

        /// 0..1 of a reveal: 1 once its action is done; while it runs, the share of its wait (when it follows progress).
        float Progress(Reveal rv)
        {
            var job = session ? session.Job : null; if (job == null) return 0;
            if (string.IsNullOrEmpty(rv.action) ? job.IsDone(rv.step) : job.ActionDone(rv.step, rv.action)) return 1;
            if (!rv.progress || session.State == AssemblySession.Phase.Closed) return 0;
            float seconds = 10;
            foreach (var st in job.Recipe.Steps) if (st.id == rv.step) foreach (var a in st.actions) if (a.key == rv.action && a.seconds > 0) seconds = a.seconds;
            return Mathf.Clamp01(session.Partial(rv.step + ":" + rv.action) / seconds) * .92f;
        }

        void PushWipes()
        {
            if (bound.Count == 0 || !masks) return;
            foreach (var b in bound)
            {
                // (parts that are not on the bench yet are set too, so they are right in the frame they appear)
                if (!b.part) continue;
                int n = 0; float wiped = 0, any = 0; int wipedZones = 0;
                foreach (var z in b.zones)
                {
                    if (!z.marker) continue;
                    // (a zone empty may come in mirrored: its size is then negative on an axis)
                    var size = z.marker.size; size = new Vector3(Mathf.Abs(size.x), Mathf.Abs(size.y), Mathf.Abs(size.z));
                    AssemblyWipeMask.Axes(size, out int iu, out int iv, out int inn);
                    var a = Matrix4x4.zero; a[3, 3] = 1;
                    a[0, iu] = 1 / Mathf.Max(1e-5f, size[iu]); a[1, iv] = 1 / Mathf.Max(1e-5f, size[iv]); a[2, inn] = 1 / Mathf.Max(1e-5f, size[inn]);
                    toZone[n] = a * z.marker.transform.worldToLocalMatrix;
                    var scale = z.marker.transform.lossyScale;
                    zoneSize[n] = new Vector4(size[iu] * Mathf.Abs(scale[iu]), size[iv] * Mathf.Abs(scale[iv]), size[inn] * Mathf.Abs(scale[inn]), z.slice);
                    n++;
                    var mask = bench.Wipe(z.id); float cover = mask != null ? mask.Coverage : 0;
                    any += cover; if (z.wipedByJob) { wiped += cover; wipedZones++; }
                }
                for (int i = n; i < MaxZones; i++) { toZone[i] = Matrix4x4.identity; zoneSize[i] = Vector4.one; }
                float rest = 0; Color glow = Color.black;
                // a part with no zone of its own comes clean as the zones the job wipes are finished (all of them when the job wipes none)
                if (!b.def.ownZones && n > 0) rest = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.35f, .95f, wipedZones > 0 ? wiped / wipedZones : any / n));
                if (b.reveal != null)
                {
                    // it never snaps: the seam goes bright while it knits, then dull
                    float p = Progress(b.reveal);
                    b.shown = p >= 1 ? Mathf.MoveTowards(b.shown, 1, stepSeconds / Mathf.Max(.02f, b.reveal.settle)) : p;
                    rest = Mathf.Max(rest, Mathf.SmoothStep(0, 1, b.shown));
                    float heat = Mathf.Sin(Mathf.Clamp01(b.shown) * Mathf.PI); glow = b.reveal.glow * (heat * heat);
                }
                foreach (var r in b.renderers)
                {
                    if (!r) continue;
                    r.GetPropertyBlock(block);
                    block.SetTexture(MasksId, masks); block.SetMatrixArray(ToZoneId, toZone); block.SetVectorArray(SizeId, zoneSize);
                    block.SetVector(StateId, new Vector4(n, rest, Mathf.Max(1e-4f, wipeReach), 0)); block.SetVector(GlowId, glow);
                    r.SetPropertyBlock(block);
                }
            }
        }

        // ------------------------------------------------------------------ closed in
        /// The parts that must all sit as found for an enclosed part to be out of sight: the part and the shells, each with
        /// the parts it is seated on up to (not including) the family's root. Null when a part is missing.
        public static List<AssemblyPart> Links(AssemblyBench bench, Enclosed e, float slack, out AssemblyPart part)
        {
            part = bench ? bench.Part(e.part) : null; if (!part) return null;
            var links = new List<AssemblyPart>();
            foreach (var id in new[] { e.part }.Concat(e.shells))
            {
                var p = bench.Part(id); if (!p) return null;
                for (int guard = 0; p && !string.IsNullOrEmpty(p.parentId) && guard < 16; guard++) { if (!links.Contains(p)) links.Add(p); p = bench.Part(p.parentId); }
            }
            return links;
        }

        /// Each link on its rest parent at its rest pose, active and not gone.
        public static bool AsFound(IEnumerable<AssemblyPart> links, float slack)
        {
            foreach (var p in links)
            {
                if (!p || !p.gameObject.activeInHierarchy || p.Gone || p.place == "held" || p.place == "loose") return false;
                if (!p.restParent || p.transform.parent != p.restParent) return false;
                if ((p.transform.position - p.restParent.TransformPoint(p.restPosition)).sqrMagnitude > slack * slack) return false;
                if (Quaternion.Angle(p.transform.localRotation, p.restRotation) > 2f) return false;
            }
            return true;
        }

        void UpdateEnclosed()
        {
            int hidden = 0;
            foreach (var c in closed)
            {
                bool hide = AsFound(c.links, enclosedSlack);
                foreach (var r in c.renderers) { if (r.forceRenderingOff != hide) r.forceRenderingOff = hide; if (hide) hidden++; }
            }
            HiddenRenderers = hidden;
        }

        void ShowEnclosed()
        {
            foreach (var c in closed) foreach (var r in c.renderers) if (r && r.forceRenderingOff) r.forceRenderingOff = false;
            HiddenRenderers = 0;
        }

        // ------------------------------------------------------------------ lamps
        float LampLevel()
        {
            if (!bench || string.IsNullOrEmpty(cureLampPart)) return 0;
            var part = bench.Part(cureLampPart); if (!part || part.renderers.Length == 0 || !part.renderers[0] || !part.gameObject.activeInHierarchy) return 0;
            float full = 1; foreach (var l in bench.lamps) if (l != null && l.part == cureLampPart) full = Mathf.Max(.01f, l.color.maxColorComponent);
            part.renderers[0].GetPropertyBlock(block);
            return block.isEmpty ? 0 : Mathf.Clamp01(block.GetColor(EmissionId).maxColorComponent / full);
        }

        void Dim(float w)
        {
            if (noDim) return;
            dimmed = w > 0;
            for (int i = 0; i < roomLamps.Length; i++)
            {
                var l = roomLamps[i]; if (!l) continue;
                l.intensity = roomBase[i] * Mathf.Lerp(1, l.name.Contains(screenLampName) ? glowDim : roomDim, w);
            }
            if (screen)
            {
                screen.GetPropertyBlock(block); block.SetColor(EmissionId, screenBase * Mathf.Lerp(1, screenDim, w)); screen.SetPropertyBlock(block);
            }
        }

        void Restore()
        {
            if (key) key.enabled = false;
            if (cureLamp) cureLamp.enabled = false;
            if (dimmed) Dim(0);
            Cast(false);
            Weight = 0;
        }

        void LateUpdate() => Step(Time.unscaledDeltaTime);

        /// One frame of the look (LateUpdate; the installer's dry run calls it with a time step of its own).
        public void Step(float dt)
        {
            if (!bench) return;
            stepSeconds = dt;
            bool working = always || (session && session.State != AssemblySession.Phase.Closed);
            // a sitting may have rebuilt the bench (parts shown, hidden, swapped): make sure nothing fell back to a glTF material
            if (working && !wasWorking) Bind();
            wasWorking = working;
            float before = Weight;
            Weight = Mathf.MoveTowards(Weight, working ? 1 : 0, dt / Mathf.Max(.01f, fadeSeconds));
            float w = Mathf.SmoothStep(0, 1, Weight);
            if (key) { key.enabled = Weight > 0; key.intensity = keyIntensity * w; }
            Cast(Weight > 0);
            if (Weight != before || (Weight > 0 && Weight < 1)) Dim(w);
            if (cureLamp)
            {
                float level = Weight > 0 ? LampLevel() : 0;
                // the bench switches the head fully on or off; a hover tint on it is far below this
                cureLamp.enabled = level > .7f;
                if (cureLamp.enabled)
                {
                    cureLamp.intensity = cureIntensity * level * w;
                    var head = bench.Part(cureLampPart);
                    if (head) cureLamp.transform.SetPositionAndRotation(head.GrabPoint + bench.transform.TransformVector(cureLampOffset), Quaternion.LookRotation(-bench.Up, bench.transform.forward));
                }
            }
            enclosedClock += dt;
            if (enclosedClock >= .1f) { enclosedClock = 0; UpdateEnclosed(); }
            UploadMasks(); PushWipes();
        }
    }
}
