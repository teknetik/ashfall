using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
    /// What the bench shows without any interface (DESIGN.md sections 6 and 8): the affordance rim under the pointer,
    /// the one-off glint of a hint, the rim flash on a seam, the shudder of a blocked part, the ghost of a part at its
    /// socket and a tool's path drawn for two seconds. The greybox form is an emission tint through a property block;
    /// the integration pass may replace Tint with a rim shader without touching the callers.
    public sealed class AssemblyFeedback
    {
        static readonly int Emission = Shader.PropertyToID("_EmissionColor"), EmissiveFactor = Shader.PropertyToID("emissiveFactor");
        public static Color RimColor = new Color(.22f, .62f, .64f), FlashColor = new Color(1.1f, .95f, .7f), GlintColor = new Color(1.3f, 1.1f, .6f), BlockColor = new Color(.9f, .25f, .12f);

        sealed class Tinted { public float rim, pulse, pulseLeft, pulseLength; public Color pulseColor; public Color applied = Color.clear; }
        // a shake is an offset added on top of wherever the part is (world space), so a part that is picked up, seated or
        // put under another parent while it shakes is never pulled back to where it was
        sealed class Shake { public Transform t; public Vector3 applied; public float left, length, metres; }
        sealed class GhostDraw { public AssemblyPart part; public Pose pose; public float left; }

        readonly Dictionary<AssemblyPart, Tinted> tints = new Dictionary<AssemblyPart, Tinted>();
        readonly List<Shake> shakes = new List<Shake>();
        readonly List<GhostDraw> ghosts = new List<GhostDraw>();
        readonly MaterialPropertyBlock block = new MaterialPropertyBlock();
        readonly AssemblyBench bench;
        LineRenderer line; float lineLeft;
        AssemblyPart hovered;
        /// What was last asked for, for QA and tests: "glint:id", "ghost:id", "path:id", "shudder:id", "flash:id".
        public readonly List<string> Log = new List<string>();
        public bool reducedMotion;

        public AssemblyFeedback(AssemblyBench bench) { this.bench = bench; }
        Tinted For(AssemblyPart p) { if (!tints.TryGetValue(p, out var t)) tints[p] = t = new Tinted(); return t; }
        void Note(string what) { Log.Add(what); if (Log.Count > 24) Log.RemoveAt(0); }

        /// The part under the pointer or focus ring that can be used now (null = none). Nothing else glows.
        public void Hover(AssemblyPart p) { hovered = p; }
        public void Glint(AssemblyPart p) { if (!p) return; Pulse(p, GlintColor, .7f); Note("glint:" + p.id); }
        public void Flash(AssemblyPart p, float seconds) { if (!p) return; Pulse(p, FlashColor, seconds); Note("flash:" + p.id); }
        void Pulse(AssemblyPart p, Color c, float seconds) { var t = For(p); t.pulseColor = c; t.pulseLeft = t.pulseLength = Mathf.Max(.05f, seconds); }

        /// A part that will not move: it shakes a little and glows warm for a moment.
        public void Shudder(AssemblyPart p, float metres, float seconds)
        {
            if (!p) return;
            Pulse(p, BlockColor, seconds); Note("shudder:" + p.id);
            if (reducedMotion) return;
            foreach (var s in shakes) if (s.t == p.transform) { s.left = s.length = seconds; return; }
            shakes.Add(new Shake { t = p.transform, left = seconds, length = seconds, metres = metres });
        }

        public void Ghost(AssemblyPart p, Pose pose, float seconds) { if (!p) return; ghosts.Add(new GhostDraw { part = p, pose = pose, left = seconds }); Note("ghost:" + p.id); }

        public void Path(IList<Vector3> points, float seconds, string id)
        {
            Note("path:" + id);
            if (points == null || points.Count < 2 || !bench.lineMaterial) return;
            if (!line)
            {
                var go = new GameObject("Assembly hint line") { hideFlags = HideFlags.DontSave };
                go.transform.SetParent(bench.transform, false);
                line = go.AddComponent<LineRenderer>(); line.sharedMaterial = bench.lineMaterial; line.useWorldSpace = true;
                line.widthMultiplier = .0035f; line.numCapVertices = 2; line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                line.renderingLayerMask |= 1u << 7;
            }
            line.positionCount = points.Count; for (int i = 0; i < points.Count; i++) line.SetPosition(i, points[i] + bench.Up * .002f);
            line.enabled = true; lineLeft = seconds;
        }

        /// Stops every shake where it stands (called before a part is moved by anything else).
        public void Settle(AssemblyPart p)
        {
            for (int i = shakes.Count - 1; i >= 0; i--) if (!p || shakes[i].t == p.transform) { if (shakes[i].t) shakes[i].t.position -= shakes[i].applied; shakes.RemoveAt(i); }
        }

        public void Tick(float dt)
        {
            for (int i = shakes.Count - 1; i >= 0; i--)
            {
                var s = shakes[i]; s.left -= dt;
                if (!s.t) { shakes.RemoveAt(i); continue; }
                if (s.left <= 0) { s.t.position -= s.applied; shakes.RemoveAt(i); continue; }
                var offset = new Vector3(Mathf.Sin(s.left * 95), 0, Mathf.Cos(s.left * 71)) * (s.metres * s.left / s.length);
                s.t.position += offset - s.applied; s.applied = offset;
            }
            foreach (var pair in tints)
            {
                var p = pair.Key; var t = pair.Value; if (!p) continue;
                t.rim = Mathf.MoveTowards(t.rim, p == hovered ? 1 : 0, dt * 9);
                if (t.pulseLeft > 0) t.pulseLeft -= dt;
                float pulse = t.pulseLeft > 0 ? Mathf.Sin(Mathf.Clamp01(t.pulseLeft / t.pulseLength) * Mathf.PI) : 0;
                var c = RimColor * (t.rim * .55f) + t.pulseColor * pulse;
                c.a = 1;
                if (c == t.applied) continue;
                t.applied = c;
                foreach (var r in p.renderers)
                {
                    if (!r) continue;
                    r.GetPropertyBlock(block); block.SetColor(Emission, c); block.SetColor(EmissiveFactor, c); r.SetPropertyBlock(block);
                }
            }
            if (hovered) For(hovered);
            if (bench.ghostMaterial)
                for (int i = ghosts.Count - 1; i >= 0; i--)
                {
                    var g = ghosts[i]; g.left -= dt;
                    if (g.left <= 0 || !g.part) { ghosts.RemoveAt(i); continue; }
                    var toPart = g.part.transform.worldToLocalMatrix; var at = Matrix4x4.TRS(g.pose.position, g.pose.rotation, g.part.transform.lossyScale);
                    foreach (var r in g.part.renderers)
                    {
                        var mf = r ? r.GetComponent<MeshFilter>() : null; if (!mf || !mf.sharedMesh) continue;
                        Graphics.DrawMesh(mf.sharedMesh, at * (toPart * r.transform.localToWorldMatrix), bench.ghostMaterial, r.gameObject.layer);
                    }
                }
            else ghosts.Clear();
            if (line && line.enabled) { lineLeft -= dt; if (lineLeft <= 0) line.enabled = false; }
        }

        public void Clear()
        {
            Settle(null); hovered = null; ghosts.Clear();
            foreach (var pair in tints) if (pair.Key) foreach (var r in pair.Key.renderers) if (r) { r.GetPropertyBlock(block); block.SetColor(Emission, Color.black); block.SetColor(EmissiveFactor, Color.black); r.SetPropertyBlock(block); }
            tints.Clear();
            if (line) { if (Application.isPlaying) Object.Destroy(line.gameObject); else Object.DestroyImmediate(line.gameObject); line = null; }
        }
    }
}
