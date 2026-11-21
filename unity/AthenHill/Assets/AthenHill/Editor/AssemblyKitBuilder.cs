using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>
    /// Turns object families into the bench the Steady Hands job is played on (20 Nov 2026, bench agent).
    /// A family is a node hierarchy plus its parts.json (CONTRACT.md section A): one node per part named
    /// &lt;family&gt;_&lt;part&gt;, and empties &lt;node&gt;__clear, __grab, __tip, __mark_&lt;id&gt;, __path_&lt;id&gt;_&lt;nn&gt;, __zone_&lt;id&gt;.
    /// The hierarchy comes from the family's GLB, or, for a greybox family, is generated here from the "grey" blocks of
    /// its parts.json (primitive meshes), so the whole job is playable before any art exists and the art drops in
    /// through the same path.
    ///
    /// THE SEAM FOR THE INTEGRATION PASS: <see cref="BindFamily"/> is the one method that binds a family (any source)
    /// to components. <see cref="BuildBench"/> takes, per family, either "greybox" or a GLB asset path; swapping a
    /// family for its real art is one entry in BenchSpec.sources, then the layout's places for that family's parts are
    /// bound to the art's own `__mark_seat_*` empties (SEAM.md section 2; data/layout.json names the mark and keeps the numbers as
    /// the greybox fallback). What a build could not resolve is in <see cref="LastReport"/>.
    /// </summary>
    public static class AssemblyKitBuilder
    {
        public const string DataDir = "Assets/AthenHill/Data/Assembly/";
        public const string GreyDir = DataDir + "Greybox/";
        public const string ArtDir = "Assets/AthenHill/Art/Bench/";
        public static readonly string[] Families = { "fixtures", "tools", "pistol", "grip", "servo", "materials" };

        public sealed class BenchSpec
        {
            /// family -> "greybox", or the asset path of its GLB (its parts.json is beside it as &lt;family&gt;.parts.json).
            public Dictionary<string, string> sources = new Dictionary<string, string>();
            public JObject layout;
            /// The families to build (null = all); `bindcheck` builds one.
            public string[] families;
            /// A trial build: nothing it makes is kept as an asset (re-bound clips stay in memory).
            public bool scratch;
            /// Fill what a real family's model lacks with the stand-in parts of the same id (on by default).
            public bool fill = true;
            public AssemblyRecipe recipe; public AssemblySettings settings; public AssemblyAudioTable audio;
            public UnityEngine.UIElements.StyleSheet hudStyle; public UnityEngine.Audio.AudioMixerGroup mixer;
            public List<string> log = new List<string>();
        }

        static Vector3 V(JToken t, int at = 0) => t == null ? Vector3.zero : new Vector3((float)t[at], (float)t[at + 1], (float)t[at + 2]);
        static string[] Strings(JToken t) => t is JArray a ? a.Select(x => (string)x).Where(x => x != null).ToArray() : new string[0];
        static Transform FindDeep(Transform root, string name)
        {
            if (root.name == name) return root;
            foreach (Transform c in root) { var f = FindDeep(c, name); if (f) return f; }
            return null;
        }
        public static string PartsPath(string family, string source) =>
            source == "greybox" ? GreyDir + family + ".parts.json" : Path.GetDirectoryName(source).Replace('\\', '/') + "/" + family + ".parts.json";

        // ------------------------------------------------------------------ greybox meshes and materials
        static void AddBox(List<CombineInstance> list, Mesh unit, float[] b) =>
            list.Add(new CombineInstance { mesh = unit, transform = Matrix4x4.TRS(new Vector3(b[0], b[1], b[2]), Quaternion.identity, new Vector3(b[3], b[4], b[5])) });
        static Mesh UnitBox()
        {
            var m = new Mesh { name = "unit box" }; var v = new List<Vector3>(); var n = new List<Vector3>(); var t = new List<int>();
            foreach (var d in new[] { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back })
            {
                var a = Mathf.Abs(d.y) > .5f ? Vector3.right : Vector3.up; var b = Vector3.Cross(d, a); a = Vector3.Cross(b, d); int i = v.Count;
                v.Add((d - a - b) * .5f); v.Add((d + a - b) * .5f); v.Add((d + a + b) * .5f); v.Add((d - a + b) * .5f);
                for (int k = 0; k < 4; k++) n.Add(d);
                t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
            }
            m.SetVertices(v); m.SetNormals(n); m.SetTriangles(t, 0); return m;
        }
        static Mesh UnitCylinder(int sides = 18)
        {
            // along Z, radius 1, length 1
            var m = new Mesh { name = "unit cylinder" }; var v = new List<Vector3>(); var n = new List<Vector3>(); var t = new List<int>();
            for (int i = 0; i <= sides; i++)
            {
                float a = i * Mathf.PI * 2 / sides; var r = new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0);
                v.Add(r + Vector3.back * .5f); v.Add(r + Vector3.forward * .5f); n.Add(r); n.Add(r);
                if (i < sides) { int k = i * 2; t.AddRange(new[] { k, k + 1, k + 3, k, k + 3, k + 2 }); }
            }
            foreach (float z in new[] { -.5f, .5f })
            {
                int c = v.Count; v.Add(new Vector3(0, 0, z)); n.Add(z < 0 ? Vector3.back : Vector3.forward);
                for (int i = 0; i <= sides; i++) { float a = i * Mathf.PI * 2 / sides; v.Add(new Vector3(Mathf.Cos(a), Mathf.Sin(a), z)); n.Add(z < 0 ? Vector3.back : Vector3.forward); }
                for (int i = 0; i < sides; i++) { if (z < 0) t.AddRange(new[] { c, c + 2 + i, c + 1 + i }); else t.AddRange(new[] { c, c + 1 + i, c + 2 + i }); }
            }
            m.SetVertices(v); m.SetNormals(n); m.SetTriangles(t, 0); return m;
        }

        /// One mesh per part, kept as sub-assets of one file per family so their ids survive a rebuild.
        sealed class MeshStore
        {
            readonly string path; readonly Dictionary<string, Mesh> meshes = new Dictionary<string, Mesh>(); readonly HashSet<string> used = new HashSet<string>(); Mesh main;
            public MeshStore(string path)
            {
                this.path = path; if (path == null) return;   // a scratch build keeps its meshes in memory
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                main = AssetDatabase.LoadMainAssetAtPath(path) as Mesh;
                if (!main) { main = new Mesh { name = Path.GetFileNameWithoutExtension(path) }; AssetDatabase.CreateAsset(main, path); }
                foreach (var o in AssetDatabase.LoadAllAssetsAtPath(path)) if (o is Mesh m && m != main) meshes[m.name] = m;
            }
            public Mesh Get(string name, List<CombineInstance> shapes)
            {
                if (!meshes.TryGetValue(name, out var m) || !m) { m = new Mesh { name = name }; if (path != null) AssetDatabase.AddObjectToAsset(m, path); meshes[name] = m; }
                m.Clear(); m.CombineMeshes(shapes.ToArray(), true, true); m.RecalculateBounds(); m.name = name; used.Add(name); if (path != null) EditorUtility.SetDirty(m);
                return m;
            }
            public void Finish() { if (path == null) return; foreach (var pair in meshes.ToArray()) if (!used.Contains(pair.Key) && pair.Value) { UnityEngine.Object.DestroyImmediate(pair.Value, true); meshes.Remove(pair.Key); } EditorUtility.SetDirty(main); }
        }

        static readonly Dictionary<string, Color> ClassColour = new Dictionary<string, Color>
        {
            { "steel", new Color(.42f, .44f, .46f) }, { "alloy", new Color(.60f, .60f, .56f) }, { "wood", new Color(.38f, .26f, .16f) }, { "rubber", new Color(.12f, .13f, .13f) },
            { "plastic", new Color(.62f, .60f, .34f) }, { "copper", new Color(.66f, .42f, .22f) }, { "glass", new Color(.50f, .66f, .70f) }, { "canvas", new Color(.44f, .39f, .27f) },
            { "paper", new Color(.84f, .82f, .74f) }, { "ceramic", new Color(.80f, .80f, .78f) },
        };
        static bool Metal(string c) => c == "steel" || c == "alloy" || c == "copper";
        public static Material GreyMaterial(string contact, Color? colour, bool emissive)
        {
            var c = colour ?? (ClassColour.TryGetValue(contact ?? "", out var k) ? k : Color.gray);
            string name = $"grey_{contact}_{ColorUtility.ToHtmlStringRGB(c)}" + (emissive ? "_e" : "");
            string path = GreyDir + "Materials/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { Directory.CreateDirectory(GreyDir + "Materials"); m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name }; AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", c); m.SetFloat("_Metallic", Metal(contact) ? .85f : 0); m.SetFloat("_Smoothness", Metal(contact) ? .42f : contact == "glass" ? .8f : .18f);
            // emission on (black) so the affordance rim, glints and lamps can be driven by a property block
            m.EnableKeyword("_EMISSION"); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; m.SetColor("_EmissionColor", Color.black);
            EditorUtility.SetDirty(m);
            return m;
        }
        public static Material UnlitMaterial(string name, Color c, bool transparent)
        {
            string path = DataDir + "Materials/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { Directory.CreateDirectory(DataDir + "Materials"); m = new Material(Shader.Find("Universal Render Pipeline/Unlit")) { name = name }; AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", c);
            if (transparent)
            {
                m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetFloat("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0); m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
                m.SetShaderPassEnabled("ShadowCaster", false); m.SetShaderPassEnabled("DepthOnly", false);
            }
            EditorUtility.SetDirty(m);
            return m;
        }

        // ------------------------------------------------------------------ greybox source: what a GLB would supply
        /// Builds one greybox family's node hierarchy (flat under the family root, as an export would be). `all` maps
        /// every greybox part id to its entry so a part seated on another family's part can be posed.
        static GameObject GreyboxSource(string family, JObject file, Dictionary<string, JObject> all, Mesh box, Mesh cylinder, string meshes = null)
        {
            var root = new GameObject(family);
            var store = new MeshStore(scratch ? null : GreyDir + "Meshes/" + (meshes ?? family) + ".asset");
            Matrix4x4 PoseOf(JObject e)
            {
                var g = (JObject)e["grey"]; var local = Matrix4x4.TRS(V(g["pos"]), Quaternion.Euler(V(g["rot"])), Vector3.one);
                string parent = (string)e["parent"];
                return !string.IsNullOrEmpty(parent) && all.TryGetValue(parent, out var pe) ? PoseOf(pe) * local : local;
            }
            foreach (JObject e in (JArray)file["parts"])
            {
                var g = (JObject)e["grey"]; string node = (string)e["node"];
                var go = new GameObject(node); go.transform.SetParent(root.transform, false);
                var pose = PoseOf(e); go.transform.SetPositionAndRotation(pose.GetColumn(3), pose.rotation);
                var shapes = new List<CombineInstance>();
                foreach (JObject s in (JArray)g["shapes"])
                {
                    if (s["box"] != null) AddBox(shapes, box, s["box"].Select(x => (float)x).ToArray());
                    else if (s["cyl"] != null)
                    {
                        var c = (JArray)s["cyl"]; string axis = (string)c[5]; float r = (float)c[3], len = (float)c[4];
                        var rot = axis == "x" ? Quaternion.Euler(0, 90, 0) : axis == "y" ? Quaternion.Euler(-90, 0, 0) : Quaternion.identity;
                        shapes.Add(new CombineInstance { mesh = cylinder, transform = Matrix4x4.TRS(V(c), rot, new Vector3(r, r, len)) });
                    }
                }
                go.AddComponent<MeshFilter>().sharedMesh = store.Get(node, shapes);
                Color? colour = g["color"] != null ? new Color((float)g["color"][0], (float)g["color"][1], (float)g["color"][2]) : (Color?)null;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = GreyMaterial((string)e["material"], colour, g["emissive"] != null && (bool)g["emissive"]);
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                Transform Empty(string name, Vector3 localPos, Quaternion localRot, Transform parent)
                {
                    var t = new GameObject(name).transform; t.SetParent(parent, false); t.localPosition = localPos; t.localRotation = localRot; return t;
                }
                // the clear pose is a sibling: the part's own pose moved by the offset given in its parent's space
                if (g["clear"] != null)
                {
                    string parent = (string)e["parent"];
                    var parentPose = !string.IsNullOrEmpty(parent) && all.TryGetValue(parent, out var pe) ? PoseOf(pe) : Matrix4x4.identity;
                    var t = Empty(node + "__clear", Vector3.zero, Quaternion.identity, root.transform);
                    t.SetPositionAndRotation((Vector3)pose.GetColumn(3) + parentPose.rotation * V(g["clear"]), pose.rotation);
                }
                if (g["grab"] != null) Empty(node + "__grab", V(g["grab"]), Quaternion.identity, go.transform);
                if (g["tip"] != null) { var d = V(g["tip"], 3); Empty(node + "__tip", V(g["tip"]), Quaternion.LookRotation(d, Mathf.Abs(d.y) > .9f ? Vector3.forward : Vector3.up), go.transform); }
                if (g["marks"] is JObject marks) foreach (var m in marks) { var d = V(m.Value, 3); var t = Empty(node + "__mark_" + m.Key, V(m.Value), Quaternion.LookRotation(d, Mathf.Abs(d.y) > .9f ? Vector3.forward : Vector3.up), go.transform); t.localScale = Vector3.one * (float)m.Value[6]; }
                if (g["paths"] is JObject paths) foreach (var p in paths) { int i = 0; foreach (var pt in (JArray)p.Value) Empty($"{node}__path_{p.Key}_{i++:00}", V(pt), Quaternion.identity, go.transform); }
                // a zone is a box empty whose scale is its half extents, as the kit exports it; the wipe is done across its thinnest axis
                if (g["zones"] is JObject zones) foreach (var z in zones) { var zr = g["zone_rot"]?[z.Key]; var t = Empty(node + "__zone_" + z.Key, V(z.Value), zr != null ? Quaternion.Euler(V(zr)) : Quaternion.identity, go.transform); t.localScale = V(z.Value, 3) * .5f; }
            }
            store.Finish();
            return root;
        }

        // ------------------------------------------------------------------ the seam: bind a family to components
        /// What a build found out about the families it bound (the integration pass and `bindcheck` read it).
        public sealed class BindReport
        {
            public List<string> problems = new List<string>(), notes = new List<string>();
            public List<string> boundPlaces = new List<string>(), posePlaces = new List<string>(), fallbackPlaces = new List<string>();
            public Dictionary<string, string> clips = new Dictionary<string, string>(), shots = new Dictionary<string, string>();
            /// Per real family: the ids its model does not have yet, filled with stand-ins.
            public Dictionary<string, string[]> standIns = new Dictionary<string, string[]>();
        }
        static BindReport report = new BindReport();
        public static BindReport LastReport => report;

        static bool Fixed(JObject e) => e["fixed"] != null && (bool)e["fixed"] || ((string)e["note"] ?? "").StartsWith("fixed sub-part");

        /// Adds AssemblyPart and AssemblyParam components to a family hierarchy from its parts.json. Works the same on an
        /// unpacked GLB instance (nested, with rigs) and on a greybox source (flat). Parts are registered in `parts`;
        /// parenting across families, rest poses and markers are done afterwards by <see cref="Settle"/>.
        public static void BindFamily(GameObject familyRoot, JObject file, Dictionary<string, AssemblyPart> parts, List<string> log)
        {
            string family = (string)file["family"];
            foreach (JObject e in (JArray)file["parts"])
            {
                string id = (string)e["id"], node = (string)e["node"];
                var t = FindDeep(familyRoot.transform, node);
                if (!t) { log.Add($"{family}: node {node} for part {id} not found"); report.problems.Add($"{id}: node {node} not found"); continue; }
                // a skinned part is drawn where its bones are, not where its node is: the part is the rig that holds both
                if (t.GetComponent<SkinnedMeshRenderer>() && t.parent && t.parent != familyRoot.transform && t.parent.name.EndsWith("_rig"))
                {
                    report.notes.Add($"{id}: {node} is skinned; the part is bound to its rig node {t.parent.name} so that moving the part moves the bones");
                    t = t.parent;
                }
                var p = t.gameObject.GetComponent<AssemblyPart>(); if (!p) p = t.gameObject.AddComponent<AssemblyPart>();
                p.id = id; p.label = (string)e["label"] ?? id; p.kind = (string)e["kind"] ?? "part"; p.material = (string)e["material"] ?? "steel"; p.mass = (string)e["mass"] ?? "light";
                if (p.kind == "part" && Fixed(e)) p.kind = "fixture";
                p.item = (string)e["item"] ?? ""; p.parentId = (string)e["parent"] ?? ""; p.heldBy = Strings(e["held_by"]);
                var seat = e["seat"] as JObject;
                if (seat != null) { p.symmetry = seat["symmetry"] != null ? (int)seat["symmetry"] : 1; p.tolMm = seat["tol_mm"] != null ? (float)seat["tol_mm"] : 5; p.tolDeg = seat["tol_deg"] != null ? (float)seat["tol_deg"] : 20; }
                if (e["fastener"] is JObject f) { p.bit = (string)f["bit"] ?? ""; p.turns = f["turns"] != null ? (float)f["turns"] : 6; p.holds = Strings(f["holds"]); }
                if (e["tool"] is JObject tool) { p.verbs = Strings(tool["verbs"]); p.tags = Strings(tool["tags"]); p.modes = Strings(tool["modes"]); }
                p.grab = FindDeep(familyRoot.transform, node + "__grab"); p.tip = FindDeep(familyRoot.transform, node + "__tip");
                parts[id] = p; nodeOf[id] = node;
            }
            foreach (var id in Strings(file["absent_at_start"])) if (parts.TryGetValue(id, out var ap)) ap.homePlace = "gone";
            foreach (JObject e in (JArray)(file["params"] ?? new JArray()))
            {
                string id = (string)e["id"];
                var go = new GameObject("param " + id); go.transform.SetParent(familyRoot.transform, false);
                var m = go.AddComponent<AssemblyParam>(); m.id = id;
                // SEAM.md section 7: a param starts at its rest, which is not always 0 (the gimbal's tilts rest at 0.5)
                var rest = e["rest"] ?? file["param_rest"]?[id]; if (rest != null && rest.Type != JTokenType.Null) m.asFound = Mathf.Clamp01((float)rest);
                string action = (string)e["action"];
                var clip = !string.IsNullOrEmpty(action) ? clips.FirstOrDefault(c => c && c.name == action) : null;
                if (clip)
                {
                    var rig = FindDeep(familyRoot.transform, (string)e["node"] ?? "");
                    var fitted = Retarget(clip, familyRoot.transform, rig ? rig : familyRoot.transform, family, out string how);
                    m.clip = fitted; m.clipRoot = (rig ? rig : familyRoot.transform).gameObject; report.clips[id] = how;
                    if (!fitted) report.problems.Add($"{id}: clip {action}: {how}");
                }
                else if (!string.IsNullOrEmpty(action) && e["grey"] == null) { report.problems.Add($"{id}: no clip named {action} in the model"); report.clips[id] = "missing"; }
                pendingParams.Add((m, e));
            }
        }
        static readonly List<(AssemblyParam param, JObject entry)> pendingParams = new List<(AssemblyParam, JObject)>();
        static readonly List<AnimationClip> clips = new List<AnimationClip>();
        static readonly Dictionary<string, string> nodeOf = new Dictionary<string, string>();
        static bool scratch;

        /// A family's `*_param` clip is bound from the model's root; parts are moved about the bench, so the clip is
        /// re-bound from its rig node, which travels with the part that owns it. The copy is kept as an asset.
        static AnimationClip Retarget(AnimationClip clip, Transform modelRoot, Transform rig, string family, out string how)
        {
            string prefix = rig == modelRoot ? "" : AnimationUtility.CalculateTransformPath(rig, modelRoot);
            var bindings = AnimationUtility.GetCurveBindings(clip);
            if (bindings.Length == 0) { how = "no curves"; return null; }
            AnimationClip copy;
            if (scratch) copy = new AnimationClip { name = clip.name };
            else
            {
                string dir = DataDir + "Clips"; Directory.CreateDirectory(dir);
                string path = $"{dir}/{family}__{clip.name}.anim";
                copy = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
                if (!copy) { copy = new AnimationClip { name = clip.name }; AssetDatabase.CreateAsset(copy, path); }
            }
            // legacy, whatever the import: AssemblyParam samples it with AnimationClip.SampleAnimation, which a player refuses for a
            // non-legacy clip without an Animator (21 Nov, sh-real1: 10,025 log errors)
            copy.ClearCurves(); copy.legacy = true; copy.frameRate = clip.frameRate;
            int resolved = 0, outside = 0;
            foreach (var b in bindings)
            {
                string rel;
                if (prefix == "") rel = b.path;
                else if (b.path == prefix) rel = "";
                else if (b.path.StartsWith(prefix + "/")) rel = b.path.Substring(prefix.Length + 1);
                else { outside++; continue; }
                if (rel == "" ? rig : rig.Find(rel)) resolved++;
                copy.SetCurve(rel, b.type, b.propertyName, AnimationUtility.GetEditorCurve(clip, b));
            }
            if (!scratch) EditorUtility.SetDirty(copy);
            how = $"{bindings.Length} curves, {resolved} resolve from {rig.name}" + (outside > 0 ? $", {outside} outside the rig (dropped)" : "") + (clip.legacy ? ", legacy" : "");
            return resolved > 0 ? copy : null;
        }

        static Bounds? MeshBounds(Renderer r)
        {
            if (r is SkinnedMeshRenderer sk) return sk.sharedMesh ? sk.localBounds : (Bounds?)null;
            var mf = r.GetComponent<MeshFilter>(); return mf && mf.sharedMesh ? mf.sharedMesh.bounds : (Bounds?)null;
        }

        /// After every family is bound: parts go under the part they are seated on (so they move with it) unless the
        /// model already has them there, their rest and clear poses are recorded, markers are made from the empties, and
        /// the mechanisms are wired. `placeMarks` are the marks the layout binds places to: they stay plain empties.
        static void Settle(Transform familiesRoot, Dictionary<string, AssemblyPart> parts, Dictionary<string, JObject> entries, HashSet<string> placeMarks, JObject layout, List<string> log)
        {
            // clear poses first, while the hierarchy is still as exported
            var clear = new Dictionary<string, Pose>();
            foreach (var pair in parts)
            {
                var e = entries[pair.Key]; string name = (string)(e["seat"]?["clear"]);
                if (string.IsNullOrEmpty(name)) continue;
                var t = FindDeep(familiesRoot, name);
                if (!t) { log.Add($"{pair.Key}: clear empty {name} not found"); report.problems.Add($"{pair.Key}: clear empty {name} not found"); continue; }
                clear[pair.Key] = new Pose(t.position, t.rotation);
            }
            int inParentFrame = 0;
            foreach (var pair in parts)
            {
                var p = pair.Value;
                if (string.IsNullOrEmpty(p.parentId)) continue;
                if (!parts.TryGetValue(p.parentId, out var parent)) { log.Add($"{p.id}: parent {p.parentId} is not a part of any family on the bench"); report.problems.Add($"{p.id}: parent {p.parentId} is not on the bench"); continue; }
                // a model that already nests it (directly, or on a bone of the parent's rig) is left as it is
                if (p.transform.IsChildOf(parent.transform)) continue;
                // a real part whose parent belongs to another family is modelled in that parent's own frame (the materials family's
                // leads "in the cradle frame D, identity transform", the core's flash "in the frame of grip.core"): where it stands in
                // its own family is where it stands on the parent. Kept in place instead, it was off by wherever the parent's node
                // stands in its family (21 Nov: the gimbal's leads 20 mm down through the work mat). Its own clear empty, a sibling
                // that stays behind in its family, is carried along with it.
                string fam = p.id.Contains(".") ? p.id.Substring(0, p.id.IndexOf('.')) : "", parentFam = parent.id.Contains(".") ? parent.id.Substring(0, parent.id.IndexOf('.')) : "";
                bool real = entries.TryGetValue(p.id, out var pe) && pe["grey"] == null;
                if (real && fam != parentFam)
                {
                    var root = p.transform; while (root.parent && root.parent != familiesRoot) root = root.parent;
                    var before = Matrix4x4.TRS(p.transform.position, p.transform.rotation, Vector3.one);
                    var lp = root.InverseTransformPoint(p.transform.position); var lr = Quaternion.Inverse(root.rotation) * p.transform.rotation;
                    p.transform.SetParent(parent.transform, false); p.transform.localPosition = lp; p.transform.localRotation = lr;
                    var moved = Matrix4x4.TRS(p.transform.position, p.transform.rotation, Vector3.one) * before.inverse;
                    if (clear.TryGetValue(p.id, out var cp)) clear[p.id] = new Pose(moved.MultiplyPoint3x4(cp.position), moved.rotation * cp.rotation);
                    // clear empties inside its own subtree moved with it: read them again
                    foreach (var sub in p.GetComponentsInChildren<AssemblyPart>(true))
                    {
                        if (sub == p) continue; string cn = (string)(entries.TryGetValue(sub.id, out var se) ? se["seat"]?["clear"] : null);
                        var ct = string.IsNullOrEmpty(cn) ? null : FindDeep(familiesRoot, cn);
                        if (ct && ct.IsChildOf(p.transform)) clear[sub.id] = new Pose(ct.position, ct.rotation);
                        else if (clear.TryGetValue(sub.id, out var sp)) clear[sub.id] = new Pose(moved.MultiplyPoint3x4(sp.position), moved.rotation * sp.rotation);
                    }
                    inParentFrame++;
                }
                else p.transform.SetParent(parent.transform, true);
            }
            if (inParentFrame > 0) report.notes.Add($"{inParentFrame} real parts whose parent is in another family were put in that parent's own frame");
            var all = familiesRoot.GetComponentsInChildren<Transform>(true);
            foreach (var pair in parts)
            {
                var p = pair.Value; var t = p.transform; string node = nodeOf.TryGetValue(p.id, out var nn) ? nn : t.name;
                p.restParent = t.parent; p.restPosition = t.localPosition; p.restRotation = t.localRotation; p.restScale = t.localScale;
                if (clear.TryGetValue(p.id, out var c)) { p.hasClear = true; p.clearPosition = p.restParent.InverseTransformPoint(c.position); p.clearRotation = Quaternion.Inverse(p.restParent.rotation) * c.rotation; }
                // own renderers: everything under the node that is not under a child part
                var own = t.GetComponentsInChildren<Renderer>(true).Where(r => r.GetComponentInParent<AssemblyPart>(true) == p && !r.name.StartsWith("decal_")).ToArray();
                p.renderers = own;
                bool any = false; var b = new Bounds();
                foreach (var r in own)
                {
                    var found = MeshBounds(r); if (!found.HasValue) continue;
                    var mb = found.Value; var m = t.worldToLocalMatrix * (r is SkinnedMeshRenderer sk && sk.rootBone ? sk.rootBone.localToWorldMatrix : r.transform.localToWorldMatrix);
                    for (int i = 0; i < 8; i++)
                    {
                        var corner = m.MultiplyPoint3x4(mb.center + Vector3.Scale(mb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1)));
                        if (!any) { b = new Bounds(corner, Vector3.zero); any = true; } else b.Encapsulate(corner);
                    }
                }
                p.localBounds = any ? b : new Bounds(Vector3.zero, Vector3.one * .02f);
                // a real shape is picked where it is, not where its box is (stand-ins are boxes already)
                p.surface = entries[p.id]["grey"] == null ? SurfacePoints(p, own, out p.surfaceRadius) : new Vector3[0]; p.hasHandle = false;
                if (p.surface.Length > 0)
                {
                    var centre = p.localBounds.center; p.handle = p.surface.OrderBy(q => (q - centre).sqrMagnitude).First();
                    p.hasHandle = (p.handle - centre).magnitude * Mathf.Abs(t.lossyScale.x) > .004f;
                }
                // marks, zones and paths from the empties under (or beside, or on a bone of) the node
                var paths = new SortedDictionary<string, SortedDictionary<string, Transform>>(StringComparer.Ordinal);
                foreach (var child in all)
                {
                    if (!child || !child.name.StartsWith(node + "__")) continue;
                    string rest = child.name.Substring(node.Length + 2);
                    if (rest.StartsWith("mark_") || rest.StartsWith("zone_"))
                    {
                        bool zone = rest.StartsWith("zone_"); string mid = rest.Substring(5);
                        // an empty on a bone stays there (the roll's pockets ride its segments); others ride the part
                        if (!child.IsChildOf(t)) child.SetParent(t, true);
                        var size = child.lossyScale; size = new Vector3(Mathf.Abs(size.x), Mathf.Abs(size.y), Mathf.Abs(size.z)); child.localScale = Vector3.one;   // (a mirrored empty has a negative scale)
                        // a mark a place is bound to, and every seat or slot, is where something rests: not a thing to click
                        if (!zone && (placeMarks.Contains(p.id + "/" + mid) || mid.StartsWith("seat_") || mid.StartsWith("slot_") || mid.StartsWith("clear_"))) continue;
                        var m = child.gameObject.GetComponent<AssemblyMarker>(); if (!m) m = child.gameObject.AddComponent<AssemblyMarker>();
                        m.kind = zone ? AssemblyMarkerKind.Zone : AssemblyMarkerKind.Mark; m.id = p.id + "/" + mid; m.ownerPart = p.id; m.frame = t;
                        // a zone empty's scale is the half extents of its box; a mark's is its pick radius where the family gives one
                        // (the kit's marks are unscaled: 6 mm then)
                        m.size = zone ? size * 2 : new Vector3(size.x > .2f ? .006f : Mathf.Clamp(size.x, .004f, .05f), .004f, .004f);
                    }
                    else if (rest.StartsWith("path_"))
                    {
                        string body = rest.Substring(5); int cut = body.LastIndexOf('_'); if (cut <= 0) continue;
                        if (!child.IsChildOf(t)) child.SetParent(t, true);
                        string pid = body.Substring(0, cut);
                        if (!paths.TryGetValue(pid, out var pts)) paths[pid] = pts = new SortedDictionary<string, Transform>(StringComparer.Ordinal);
                        pts[body.Substring(cut + 1)] = child;
                    }
                    else if ((rest == "grab" || rest == "tip") && !child.IsChildOf(t)) child.SetParent(t, true);
                }
                foreach (var path in paths)
                {
                    var go = new GameObject(node + "__path_" + path.Key); go.transform.SetParent(t, false);
                    var m = go.AddComponent<AssemblyMarker>(); m.kind = AssemblyMarkerKind.Path; m.id = p.id + "/" + path.Key; m.ownerPart = p.id; m.frame = t; m.points = path.Value.Values.ToArray();
                    if (m.points.Length > 0) go.transform.position = m.points[0].position;
                }
                // SEAM.md section 10: every wipe has a mask from the start. Where the art gives a wipe no zone of its own (the
                // punch dimple on a plug, the dust in a screw's recess) the wipe is the whole part: a zone over its box that no
                // hand works (an action's effect "~part/wipe" reveals it).
                foreach (var w in (entries[p.id]["wipes"] as JArray ?? new JArray()).OfType<JObject>())
                {
                    string wid = (string)w["id"], zoneNode = (string)w["zone"]; if (string.IsNullOrEmpty(wid)) continue;
                    if (!string.IsNullOrEmpty(zoneNode)) { if (!all.Any(x => x && x.name == zoneNode)) report.problems.Add($"{p.id}: wipe {wid}: zone empty {zoneNode} not found"); continue; }
                    if (t.GetComponentsInChildren<AssemblyMarker>(true).Any(x => x.id == p.id + "/" + wid)) continue;
                    var z = new GameObject(node + "__zone_" + wid).transform; z.SetParent(t, false); z.localPosition = p.localBounds.center;
                    var zm = z.gameObject.AddComponent<AssemblyMarker>(); zm.kind = AssemblyMarkerKind.Zone; zm.id = p.id + "/" + wid; zm.ownerPart = p.id; zm.frame = t;
                    zm.size = Vector3.Max(p.localBounds.size, Vector3.one * .001f); zm.passive = true;
                }
            }
            foreach (var (m, e) in pendingParams)
            {
                // what the bench layout says about a mechanism holds for any source; the grey block is the stand-in's own motion
                var l = layout?["params"]?[m.id] as JObject; var g = e["grey"] as JObject;
                foreach (var src in new[] { g, l })
                {
                    if (src == null) continue;
                    if (src["as_found"] != null) m.asFound = (float)src["as_found"];
                    if (src["switch_at"] != null) m.switchAt = (float)src["switch_at"];
                    if (src["show_high"] != null) m.shownHigh = m.shownHigh.Concat(Strings(src["show_high"]).Where(parts.ContainsKey).Select(id => parts[id].gameObject)).Distinct().ToArray();
                    if (src["show_low"] != null) m.shownLow = m.shownLow.Concat(Strings(src["show_low"]).Where(parts.ContainsKey).Select(id => parts[id].gameObject)).Distinct().ToArray();
                }
                // a continuous param of the art (no clip: the bench turns its bone; the drill's crank and its spindle at `ratio`)
                if (g == null && e["continuous"] != null && (bool)e["continuous"])
                {
                    var bone = FindDeep(familiesRoot, (string)e["bone"] ?? ""); var first = Strings(e["parts"]).Where(parts.ContainsKey).Select(id => parts[id]).FirstOrDefault();
                    if (!bone || !first) { report.problems.Add($"{m.id}: continuous param without its bone {(string)e["bone"]} or a part"); continue; }
                    m.continuous = true; m.spinBone = bone; m.spinBase = bone.localRotation; m.asFound = 0;
                    var tool = parts.TryGetValue(first.parentId ?? "", out var tp0) ? tp0 : null;
                    // the bone's own +Z is its axle (tools.glb of 21 Nov: drill_crank +Z along the wheel's axle, drill_spindle +Z along
                    // the bit, the same as the drill's __tip); checked against the tip where there is one
                    m.spinAxis = Vector3.forward;
                    // the art may say which bone axis it turns about ("positive turns about the bone +Y close the vise")
                    var axisNote = System.Text.RegularExpressions.Regex.Match((string)e["note"] ?? "", @"bone ([+-])([XYZ])\b");
                    if (axisNote.Success) { var v = axisNote.Groups[2].Value == "X" ? Vector3.right : axisNote.Groups[2].Value == "Y" ? Vector3.up : Vector3.forward; m.spinAxis = axisNote.Groups[1].Value == "-" ? -v : v; }
                    // the part riding it is turned through it (the vise screw turns about its own thread, not about its local up)
                    if (e["ratio"] == null && string.IsNullOrEmpty(first.spinParam)) first.spinParam = m.id;
                    // the spindle turns about the bit: the tool's length from where it is held to its tip (the art's __tip +Z points
                    // across it, 21 Nov), in the bone's own space
                    if (e["ratio"] != null && tool) { var len = AssemblyVerb.LengthAxis(tool); m.spinAxis = bone.InverseTransformDirection(len).normalized; report.notes.Add($"{m.id}: turns about the tool's length {m.spinAxis}"); }
                    report.notes.Add($"{m.id}: continuous, bone {bone.name}, axis {m.spinAxis}, {first.id} {(first.transform.IsChildOf(bone) ? "rides it" : "does NOT ride it")}");
                    continue;
                }
                if (g == null) continue;
                string target = (string)g["target"];
                if (!string.IsNullOrEmpty(target) && parts.TryGetValue(target, out var tp)) { m.target = tp.transform; m.basePosition = tp.transform.localPosition; m.baseEuler = tp.transform.localEulerAngles; m.move = V(g["move"]); m.turn = V(g["turn"]); }
                m.meshLow = Strings(g["mesh_low"]).Where(parts.ContainsKey).SelectMany(id => parts[id].renderers).ToArray();
                m.meshHigh = Strings(g["mesh_high"]).Where(parts.ContainsKey).SelectMany(id => parts[id].renderers).ToArray();
                string glow = (string)g["glow"];
                if (!string.IsNullOrEmpty(glow) && parts.TryGetValue(glow, out var gp) && gp.renderers.Length > 0) { m.glow = gp.renderers[0]; var c = g["glow_color"]; m.glowColor = c != null ? new Color((float)c[0], (float)c[1], (float)c[2]) : Color.white; }
            }
            // the spindle follows the crank of the same rig at its ratio, the opposite hand; the tool's work turns the crank
            foreach (var (m, e) in pendingParams)
            {
                if (!m.continuous || e["ratio"] == null) continue;
                var driver = pendingParams.FirstOrDefault(x => x.param != m && x.param.continuous && x.entry["ratio"] == null && (string)x.entry["node"] == (string)e["node"]).param;
                if (!driver) continue;
                driver.follower = m; driver.followRatio = -(float)e["ratio"];
                var wheel = Strings(driver_entry(pendingParams, driver)["parts"]).Where(parts.ContainsKey).Select(id => parts[id]).FirstOrDefault();
                if (wheel && parts.TryGetValue(wheel.parentId ?? "", out var tool)) tool.spinParam = driver.id;
            }
            pendingParams.Clear();
        }
        static JObject driver_entry(List<(AssemblyParam param, JObject entry)> list, AssemblyParam p) => list.First(x => x.param == p).entry;

        /// Every stand-in entry of every family, by id (their poses chain through stand-in parents).
        static Dictionary<string, JObject> GreyEntries()
        {
            var all = new Dictionary<string, JObject>();
            foreach (var family in Families) { string path = GreyDir + family + ".parts.json"; if (File.Exists(path)) foreach (JObject e in (JArray)JObject.Parse(File.ReadAllText(path))["parts"]) all[(string)e["id"]] = e; }
            return all;
        }

        static bool PoseMark(Dictionary<string, JObject> entries, string ownerId, string markId)
        {
            if (!entries.TryGetValue(ownerId, out var e) || !(e["marks"] is JArray marks)) return false;
            foreach (var m in marks) if (m is JObject o && (string)o["id"] == markId) return o["pose"] != null && o["pose"].Type == JTokenType.Boolean && (bool)o["pose"];
            return false;
        }

        // ------------------------------------------------------------------ the bench
        /// Builds the whole bench as one object (not yet in a scene): families bound and laid out, places, shots, the
        /// aim dot, and the AssemblyBench and AssemblySession components on the root.
        public static GameObject BuildBench(BenchSpec spec)
        {
            pendingParams.Clear(); clips.Clear(); nodeOf.Clear(); report = new BindReport(); scratch = spec.scratch;
            var root = new GameObject("Steady Hands bench");
            var bench = root.AddComponent<AssemblyBench>(); root.AddComponent<AssemblySession>().bench = bench;
            bench.recipe = spec.recipe; bench.settings = spec.settings; bench.audioTable = spec.audio; bench.hudStyle = spec.hudStyle; bench.mixerGroup = spec.mixer;
            bench.ghostMaterial = UnlitMaterial("AssemblyGhost", new Color(.45f, .92f, .95f, .30f), true);
            bench.lineMaterial = UnlitMaterial("AssemblyLine", new Color(.95f, .82f, .45f, .85f), true);
            var families = new GameObject("Families").transform; families.SetParent(root.transform, false);
            var files = new Dictionary<string, JObject>(); var entries = new Dictionary<string, JObject>();
            foreach (var family in spec.families ?? Families)
            {
                string source = spec.sources.TryGetValue(family, out var s) ? s : "greybox";
                string partsPath = PartsPath(family, source);
                if (!File.Exists(partsPath)) { spec.log.Add($"{family}: no parts file at {partsPath}"); report.problems.Add($"{family}: no parts file at {partsPath}"); continue; }
                files[family] = JObject.Parse(File.ReadAllText(partsPath));
                foreach (JObject e in (JArray)files[family]["parts"]) entries[(string)e["id"]] = e;
            }
            var box = UnitBox(); var cylinder = AssetCylinder();
            var parts = new Dictionary<string, AssemblyPart>();
            foreach (var family in spec.families ?? Families)
            {
                if (!files.TryGetValue(family, out var file)) continue;
                string source = spec.sources.TryGetValue(family, out var s) ? s : "greybox";
                GameObject fam; bool real = source != "greybox"; clips.Clear();
                if (!real) fam = GreyboxSource(family, file, entries, box, cylinder);
                else
                {
                    var asset = AssetDatabase.LoadAssetAtPath<GameObject>(source);
                    if (!asset) { spec.log.Add($"{family}: no model at {source}"); report.problems.Add($"{family}: no model at {source}"); continue; }
                    fam = (GameObject)PrefabUtility.InstantiatePrefab(asset); PrefabUtility.UnpackPrefabInstance(fam, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                    fam.name = family; clips.AddRange(AssetDatabase.LoadAllAssetsAtPath(source).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")));
                    foreach (var anim in fam.GetComponentsInChildren<Animation>(true)) UnityEngine.Object.DestroyImmediate(anim);
                    foreach (var anim in fam.GetComponentsInChildren<Animator>(true)) UnityEngine.Object.DestroyImmediate(anim);
                    report.notes.Add($"{family}: {clips.Count} clips in the model: {string.Join(", ", clips.Select(c => c.name))}");
                }
                fam.transform.SetParent(families, false);
                var place = spec.layout["families"]?[family]; if (real && place?["real"] != null) place = place["real"];
                if (place != null) { fam.transform.localPosition = V(place["pos"]); fam.transform.localRotation = Quaternion.Euler(V(place["rot"])); fam.transform.localScale = Vector3.one * (place["scale"] != null ? (float)place["scale"] : 1); }
                BindFamily(fam, file, parts, spec.log);
                spec.log.Add($"{family}: {source}, {((JArray)file["parts"]).Count} parts");
                // a family whose art is not complete yet: what its model lacks stays a stand-in, laid out in bench space as the
                // stand-in family is, so the job can be played on the art that has arrived (helpers of a stand-in whose own
                // parent is art are left out: the flat canvas of the stand-in roll)
                string greyPath = GreyDir + family + ".parts.json";
                if (real && spec.fill && File.Exists(greyPath))
                {
                    var grey = JObject.Parse(File.ReadAllText(greyPath));
                    var have = new HashSet<string>(((JArray)file["parts"]).Select(x => (string)x["id"]));
                    var haveParams = new HashSet<string>(((JArray)(file["params"] ?? new JArray())).Select(x => (string)x["id"]));
                    var extraParts = new JArray(((JArray)grey["parts"]).Where(x => !have.Contains((string)x["id"]) && !(x["grey"]?["helper"] != null && (bool)x["grey"]["helper"] && have.Contains((string)x["parent"] ?? ""))));
                    var extraParams = new JArray(((JArray)(grey["params"] ?? new JArray())).Where(x => !haveParams.Contains((string)x["id"])));
                    if (extraParts.Count > 0 || extraParams.Count > 0)
                    {
                        var sub = new JObject { ["family"] = family, ["parts"] = extraParts, ["params"] = extraParams };
                        var greyAll = GreyEntries();
                        var extra = GreyboxSource(family + " stand-ins", sub, greyAll, box, cylinder, family + "_standins");
                        extra.transform.SetParent(families, false);
                        foreach (JObject e in extraParts) entries[(string)e["id"]] = e;
                        clips.Clear(); BindFamily(extra, sub, parts, spec.log);
                        report.standIns[family] = extraParts.Select(x => (string)x["id"]).Concat(extraParams.Select(x => "param " + (string)x["id"])).ToArray();
                    }
                }
            }
            // where the layout knows better than a family's own file what a part sits on (the grip is exported in the pistol's frame with no parent)
            if (spec.layout["parents"] is JObject parents) foreach (var pr in parents) if (parts.TryGetValue(pr.Key, out var pp)) pp.parentId = (string)pr.Value ?? "";
            var placeMarks = new HashSet<string>();
            foreach (JObject pl in (JArray)spec.layout["places"]) { string mk = (string)pl["mark"]; if (!string.IsNullOrEmpty(mk)) placeMarks.Add(mk); }
            Settle(families, parts, entries, placeMarks, spec.layout, spec.log);
            UnityEngine.Object.DestroyImmediate(box);

            // interior lighting: lamps of the shop are on rendering layer 7
            foreach (var r in root.GetComponentsInChildren<Renderer>(true)) r.renderingLayerMask |= 1u << 7;

            var surface = new GameObject("Surface").transform; surface.SetParent(root.transform, false); surface.localPosition = V(spec.layout["surface"]["pos"]);
            bench.surface = surface; bench.reach = new Vector2((float)spec.layout["surface"]["reach"][0], (float)spec.layout["surface"]["reach"][1]);
            var loose = new GameObject("Loose").transform; loose.SetParent(root.transform, false); bench.loose = loose;
            var placesRoot = new GameObject("Places").transform; placesRoot.SetParent(root.transform, false);
            var basePos = new Dictionary<string, Vector3>();
            foreach (JObject pl in (JArray)spec.layout["places"]) { string id = (string)pl["id"]; if (!id.Contains("#")) basePos[id] = V(pl["pos"]); }
            foreach (JObject pl in (JArray)spec.layout["places"])
            {
                string id = (string)pl["id"], on = (string)pl["on"], mark = (string)pl["mark"] ?? "", restOf = (string)pl["rest_of"] ?? ""; Transform owner = placesRoot;
                if (!string.IsNullOrEmpty(on)) { if (!parts.TryGetValue(on, out var op)) { spec.log.Add($"place {id}: owner part {on} missing"); continue; } owner = op.transform; }
                var t = new GameObject(id).transform; t.SetParent(owner, false); t.localPosition = V(pl["pos"]); t.localRotation = Quaternion.Euler(V(pl["rot"])); bool restOn = false;
                // a place the art has no mark for, whose numbers were made for the stand-ins: `real` says where it is when a family is the
                // art's (`when`: the toolkit unless it says otherwise; the art's mats have the pistol's parts on the right and the servo's
                // on the left, the other way round from the stand-ins) and that a real part is set down on it, not put there by its origin
                if (pl["real"] is JObject alt)
                {
                    bool Real(string family) => spec.sources.TryGetValue(family, out var src) && src != "greybox";
                    string first = Strings(pl["accepts"]).FirstOrDefault(x => x != "*") ?? ""; bool partReal = first.Contains(".") && Real(first.Substring(0, first.IndexOf('.')));
                    if (Real((string)alt["when"] ?? "tools") && alt["pos"] != null) { t.localPosition = V(alt["pos"]); if (alt["rot"] != null) t.localRotation = Quaternion.Euler(V(alt["rot"])); }
                    if (partReal && alt["rest_on"] != null && (bool)alt["rest_on"])
                    {
                        restOn = true; var lp = t.localPosition; if (alt["surface"] != null) lp.y = (float)alt["surface"]; t.localPosition = lp;
                        if (alt["rest_rot"] != null) t.localRotation = Quaternion.Euler(V(alt["rest_rot"]));
                    }
                }
                if (restOf != "")
                {
                    // the part's own rest pose, whatever the family's source (a pocket, or where a loose tool lies)
                    if (parts.TryGetValue(restOf, out var rp)) { var rest = rp.RestWorld; t.SetPositionAndRotation(rest.position, rest.rotation); }
                    else spec.log.Add($"place {id}: rest_of part {restOf} missing");
                }
                else if (mark != "")
                {
                    int slash = mark.IndexOf('/'); string ownerId = mark.Substring(0, slash), markId = mark.Substring(slash + 1);
                    var markT = parts.ContainsKey(ownerId) && nodeOf.TryGetValue(ownerId, out var on2) ? FindDeep(families, on2 + "__mark_" + markId) : null;
                    if (markT)
                    {
                        // SEAM.md section 2: a point gives the position and the layout the rotation (in the owner's space); a pose mark gives both
                        var rotation = owner.rotation * Quaternion.Euler(V(pl["rot"])); markT.localScale = Vector3.one;
                        t.SetParent(markT, false); t.localPosition = Vector3.zero; t.localRotation = Quaternion.identity;
                        // a second pose at the same mark ("seat_work#core") is laid off from it by the layout's numbers; a '#' place that
                        // names a mark of its own ("seat_work#servo" on the art's seat_servo) is that mark
                        bool variant = id.Contains("#") && mark == id.Substring(0, id.IndexOf('#')), pose = PoseMark(entries, ownerId, markId);
                        if (variant) { t.position = markT.position + owner.TransformVector(V(pl["pos"]) - (basePos.TryGetValue(mark, out var bp) ? bp : V(pl["pos"]))); t.rotation = rotation; }
                        else if (!pose) t.rotation = rotation;
                        // `turn`: degrees about the owner's up laid on the art's pose (the pistol on the work mat lies with its cell to the
                        // back of the bench as modelled; asked of model-bench on 21 Nov; drop the turn when the mark is changed)
                        if (pose && !variant && pl["turn"] != null) { t.rotation = Quaternion.AngleAxis((float)pl["turn"], owner.up) * t.rotation; report.notes.Add($"place {id}: the art's pose turned {(float)pl["turn"]:0} degrees about the owner's up"); }
                        (pose && !variant ? report.posePlaces : report.boundPlaces).Add(id);
                        // a point on a real fixture is where a thing is set down, not where its origin goes (the layout's numbers were
                        // made for stand-ins whose origins are their middles)
                        restOn = !pose && ownerId.StartsWith("fixtures.") && entries.TryGetValue(ownerId, out var oe) && oe["grey"] == null;
                    }
                    else report.fallbackPlaces.Add(id);
                }
                var m = t.gameObject.AddComponent<AssemblyMarker>(); m.kind = AssemblyMarkerKind.Place; m.id = id; m.ownerPart = on ?? ""; m.frame = owner; m.accepts = Strings(pl["accepts"]); m.material = (string)pl["material"] ?? "rubber"; m.restOn = restOn;
                m.approach = V(pl["approach"]);
                // where the art gives the way in as well (a clear_<x> mark beside seat_<x>, as the grip core does for its plates, strap,
                // screws and the gimbal), the part comes in from there
                if (mark != "" && !id.Contains("#") && mark.Contains("/seat_") && nodeOf.TryGetValue(mark.Substring(0, mark.IndexOf('/')), out var ownerNode))
                {
                    var wayIn = FindDeep(families, ownerNode + "__mark_clear_" + mark.Substring(mark.IndexOf("/seat_") + 6));
                    if (wayIn && (wayIn.position - t.position).sqrMagnitude > 1e-8f) { m.approach = owner.InverseTransformDirection(wayIn.position - t.position); report.notes.Add($"place {id}: comes in from the art's clear mark"); }
                } m.tolMm = (float)(pl["tol_mm"] ?? 0); m.tolDeg = (float)(pl["tol_deg"] ?? 0); m.symmetry = (int)(pl["symmetry"] ?? -1); m.size = new Vector3((float)(pl["radius"] ?? .03f), .01f, .01f);
                m.heldBy = (string)pl["held_by"] ?? ""; m.holdAbove = pl["hold_above"] != null ? (float)pl["hold_above"] : .5f;
            }
            // a part the art gives no __tip of its own (the pistol's frame: its muzzle is a mark on the barrel): the layout names the
            // node the tip stands at and which way is out (+Z of the tip) and up, in the part's own space
            foreach (var tp in (spec.layout["tips"] as JObject ?? new JObject()))
            {
                if (!parts.TryGetValue(tp.Key, out var part) || part.tip) continue;
                var def = (JObject)tp.Value; var at = FindDeep(families, (string)def["node"] ?? "");
                if (!at) { report.problems.Add($"{tp.Key}: no node {(string)def["node"]} for its tip"); continue; }
                var tip = new GameObject((nodeOf.TryGetValue(tp.Key, out var tn) ? tn : part.name) + "__tip").transform; tip.SetParent(part.transform, false);
                tip.position = at.position; tip.localRotation = Quaternion.LookRotation(V(def["dir"]), V(def["up"])); part.tip = tip;
                var off = tip.localPosition - part.localBounds.center;
                if (Vector3.Dot(off, V(def["dir"])) <= 0 || Vector3.Dot(off, V(def["up"])) <= 0) report.problems.Add($"{tp.Key}: the tip at {(string)def["node"]} is not ahead of and above the middle of the part ({off * 1000:0} mm): the layout's dir or up is wrong for this model");
                else report.notes.Add($"{tp.Key}: tip made at {(string)def["node"]}, {off.magnitude * 1000:0} mm from the middle of the part");
            }
            // and where the hand takes a real part that has no __grab of its own (the vise screw is turned by its handle, which the
            // art marks on the jaw): the node the grab stands at
            foreach (var gp in (spec.layout["grabs"] as JObject ?? new JObject()))
            {
                if (!parts.TryGetValue(gp.Key, out var part) || part.grab || entries[gp.Key]["grey"] != null) continue;
                var grab = new GameObject((nodeOf.TryGetValue(gp.Key, out var gn) ? gn : part.name) + "__grab").transform; grab.SetParent(part.transform, false);
                if (gp.Value["local"] != null) grab.localPosition = V(gp.Value["local"]);   // in the part's own space
                else
                {
                    var at = FindDeep(families, (string)gp.Value["node"] ?? "");
                    if (!at) { UnityEngine.Object.DestroyImmediate(grab.gameObject); report.problems.Add($"{gp.Key}: no node {(string)gp.Value["node"]} for its grab"); continue; }
                    grab.position = at.position;
                }
                part.grab = grab; part.hasHandle = false; report.notes.Add($"{gp.Key}: held at {(gp.Value["local"] != null ? "its own " + gp.Value["local"].ToString(Newtonsoft.Json.Formatting.None) : (string)gp.Value["node"])}");
            }
            foreach (var h in (JObject)spec.layout["home"]) { if (parts.TryGetValue(h.Key, out var hp)) hp.homePlace = (string)h.Value; else spec.log.Add("home for unknown part " + h.Key); }
            var lamps = new List<AssemblyBench.Lamp>();
            foreach (JObject l in (JArray)(spec.layout["lamps"] ?? new JArray()))
            {
                string id = (string)l["part"]; if (!parts.ContainsKey(id)) { spec.log.Add("lamp on unknown part " + id); continue; }
                var c = l["color"]; lamps.Add(new AssemblyBench.Lamp { part = id, color = c != null ? new Color((float)c[0], (float)c[1], (float)c[2]) : Color.cyan, asFound = l["as_found"] != null ? (float)l["as_found"] : 0 });
            }
            bench.lamps = lamps.ToArray();
            // test cards: the holes are decals laid in the plane of the card's `centre` mark (+Z out of the card)
            var hole = UnlitMaterial("AssemblyHole", new Color(.03f, .03f, .03f), false);
            foreach (var id in Strings(spec.layout["cards"]))
            {
                if (!parts.TryGetValue(id, out var card)) continue;
                var centre = nodeOf.TryGetValue(id, out var cn) ? FindDeep(card.transform, cn + "__mark_centre") : null;
                if (!centre) { spec.log.Add($"card {id}: no centre mark"); report.problems.Add($"{id}: no centre mark for the holes"); continue; }
                // the card's face: its thinnest side (the art's centre mark has +Z in the card's plane, towards the clip; 21 Nov the
                // rings and the aim plane lay edge on as a streak). The mark is turned so +Z is the face normal and +Y the top (the clip)
                {
                    var sz = card.localBounds.size; var n = sz.x <= sz.y && sz.x <= sz.z ? Vector3.right : sz.y <= sz.z ? Vector3.up : Vector3.forward;
                    var clipMark = FindDeep(card.transform, cn + "__mark_clip");
                    var worldN = card.transform.TransformDirection(n).normalized;
                    // the face the player sees once the card is clipped to the board: the one towards the front of the bench there
                    var seatAt = root.GetComponentsInChildren<AssemblyMarker>(true).FirstOrDefault(mk => mk.kind == AssemblyMarkerKind.Place && mk.accepts != null && mk.accepts.Contains(id));
                    if (seatAt && Vector3.Dot(seatAt.transform.rotation * (Quaternion.Inverse(card.transform.rotation) * worldN), root.transform.forward) < 0) worldN = -worldN;
                    var top = clipMark ? Vector3.ProjectOnPlane(clipMark.position - centre.position, worldN) : Vector3.ProjectOnPlane(card.transform.up, worldN);
                    if (top.sqrMagnitude < 1e-10f) top = Vector3.ProjectOnPlane(Vector3.up, worldN);
                    centre.rotation = Quaternion.LookRotation(worldN, top.normalized);
                    report.notes.Add($"card {id}: centre mark turned to the card's face");
                }
                // printed target rings and a centre dot (21 Nov: a blank card gave nothing to aim at), under where the holes go
                var ink = UnlitMaterial("AssemblyCardInk", new Color(.06f, .055f, .05f), false); var paper = UnlitMaterial("AssemblyCardPaper", new Color(.86f, .83f, .76f), false);
                var rings = new[] { (.090f, ink), (.084f, paper), (.064f, ink), (.058f, paper), (.040f, ink), (.034f, paper), (.016f, ink) };
                // printed on the face the board shows (worked out above): the ink rings and the centre dot as ONE flat mesh in world
                // metres (21 Nov: seven discs a card were 14 draws in the wide shot); the paper is the card's own face
                {
                    var g = new GameObject("print_ring_set"); g.transform.SetParent(centre, false);
                    var ls = centre.lossyScale; g.transform.localScale = new Vector3(1 / Mathf.Max(1e-6f, Mathf.Abs(ls.x)), 1 / Mathf.Max(1e-6f, Mathf.Abs(ls.y)), 1 / Mathf.Max(1e-6f, Mathf.Abs(ls.z)));
                    g.transform.localPosition = new Vector3(0, 0, .00008f / Mathf.Max(1e-6f, Mathf.Abs(ls.z)));
                    g.AddComponent<MeshFilter>().sharedMesh = CardRings(); var gr = g.AddComponent<MeshRenderer>(); gr.sharedMaterial = ink;
                    gr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; gr.renderingLayerMask |= 1u << 7;
                    _ = paper; _ = rings;
                }
                for (int i = 0; i < 6; i++)
                {
                    var d = new GameObject("decal_" + i); d.transform.SetParent(centre, false); Disc(d.transform, .007f, .0016f, -.0002f);   // a 7 mm hole through the card, seen from either face
                    d.AddComponent<MeshFilter>().sharedMesh = cylinder; var dr = d.AddComponent<MeshRenderer>(); dr.sharedMaterial = hole;
                    dr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; dr.renderingLayerMask |= 1u << 7; d.SetActive(false);
                }
            }

            var cams = new GameObject("Steady Hands bench review cameras").transform; cams.SetParent(root.transform, false); bench.cameraRoot = cams;
            foreach (JObject sh in (JArray)spec.layout["shots"])
            {
                var t = new GameObject("cam_bench_" + (string)sh["id"]).transform; t.SetParent(cams, false);
                // a shot is what it frames (parts and marks by id), worked out from where those are on this bench, so it survives a
                // family being swapped for its art; the numbers in the layout are only the fallback when none of them is here
                if (FrameShot(sh, root.transform, bench, parts, out var framedAt, out var framedRot, out string framed)) { t.localPosition = framedAt; t.localRotation = framedRot; report.shots[(string)sh["id"]] = framed; }
                else { t.localPosition = V(sh["pos"]); t.localRotation = Quaternion.LookRotation(V(sh["look"]) - V(sh["pos"]), Vector3.up); report.shots[(string)sh["id"]] = "layout numbers" + (framed != null ? " (" + framed + ")" : ""); }
                var cam = t.gameObject.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = (float)sh["fov"]; cam.nearClipPlane = .03f;
            }
            var dot = new GameObject("Aim dot"); dot.transform.SetParent(root.transform, false); Disc(dot.transform, .011f, .0008f, 0);
            dot.AddComponent<MeshFilter>().sharedMesh = cylinder; var dotRenderer = dot.AddComponent<MeshRenderer>(); dotRenderer.sharedMaterial = UnlitMaterial("AssemblyAimDot", new Color(.25f, 1.8f, 1.9f), false);
            dotRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; dotRenderer.renderingLayerMask |= 1u << 7; dot.SetActive(false);

            bench.Index(true);
            bench.wipeIds = bench.Markers.Where(m => m.kind == AssemblyMarkerKind.Zone).Select(m => m.id).OrderBy(x => x, StringComparer.Ordinal).ToArray();
            bench.ResetAsFound();
            // a skinned part is picked by the shape it has as found (the rolled toolkit, not its unrolled bind pose)
            foreach (var p in parts.Values)
            {
                var skinned = p.renderers.OfType<SkinnedMeshRenderer>().Where(r => r.sharedMesh).ToArray(); if (skinned.Length == 0) continue;
                bool any = false; var b = new Bounds(); var baked = new Mesh();
                foreach (var sk in skinned)
                {
                    sk.BakeMesh(baked, true); var m = p.transform.worldToLocalMatrix * sk.transform.localToWorldMatrix;
                    foreach (var v in baked.vertices) { var q = m.MultiplyPoint3x4(v); if (!any) { b = new Bounds(q, Vector3.zero); any = true; } else b.Encapsulate(q); }
                }
                UnityEngine.Object.DestroyImmediate(baked);
                if (any) p.localBounds = b;
            }
            // where the hand takes hold of a real part that has no grab empty: the point of its surface nearest its middle that can
            // be seen from the front of the bench as the bench is found (the vise screw's handle, not the middle of its thread)
            var front = cams.Find("cam_bench_work"); int moved = 0;
            if (front && parts.Values.Any(p => p.surface.Length > 0))
            {
                var scene = AssemblySightCheck.Scene(bench, null); var eye = front.position;
                foreach (var p in parts.Values)
                {
                    if (p.surface.Length == 0 || p.grab) continue;
                    var centre = p.localBounds.center; int tried = 0;
                    // a part fitted on another (a screw, a pin, a gear on its post) is taken by the end it comes off by
                    if (p.hasClear && p.Travel > 1e-4f)
                    {
                        var off = p.LocalRemovalAxis; var outer = p.surface.OrderByDescending(x => Vector3.Dot(x - centre, off) - .5f * Vector3.ProjectOnPlane(x - centre, off).magnitude).First();
                        if ((outer - p.handle).sqrMagnitude > 1e-10f) moved++;
                        p.handle = outer; p.hasHandle = true; continue;
                    }
                    if (!p.gameObject.activeInHierarchy) continue;
                    foreach (var q in p.surface.OrderBy(x => (x - centre).sqrMagnitude))
                    {
                        if (++tried > 96) break;
                        var w = p.transform.TransformPoint(q); float far = Vector3.Distance(eye, w);
                        if (AssemblySightCheck.Blocked(scene, new Ray(eye, (w - eye) / far), far - .004f, new[] { p }, out _) != null) continue;
                        if ((q - p.handle).sqrMagnitude > 1e-10f) moved++;
                        p.handle = q; p.hasHandle = (q - centre).magnitude * Mathf.Abs(p.transform.lossyScale.x) > .004f; break;
                    }
                }
                report.notes.Add($"{moved} real parts are held at the end they come off by, or at a point that can be seen from the front, not at their middles");
            }
            return root;
        }

        /// Where a camera with the shot's lens, pitch and yaw stands to hold everything the shot frames (16:9), as near as it
        /// can. `anchor` bottom puts the nearest edge of what is framed at the bottom of the picture (the worktop's front edge),
        /// `headroom` adds metres above it for what will stand there, `margin` is the share of the picture kept clear all round.
        /// Bench-local. False when the shot names nothing, or nothing it names is on this bench.
        static bool FrameShot(JObject sh, Transform root, AssemblyBench bench, Dictionary<string, AssemblyPart> parts, out Vector3 position, out Quaternion rotation, out string how)
        {
            position = default; rotation = Quaternion.identity; how = null;
            var ids = Strings(sh["frames"]); if (ids.Length == 0) return false;
            var pts = new List<Vector3>(); var missing = new List<string>(); float headroom = sh["headroom"] != null ? (float)sh["headroom"] : 0;
            foreach (var id in ids)
            {
                if (id == "reach")
                {
                    var c = bench.surface.localPosition;
                    foreach (int sx in new[] { -1, 1 }) foreach (int sz in new[] { -1, 1 }) { var corner = c + new Vector3(sx * bench.reach.x, 0, sz * bench.reach.y); pts.Add(corner); if (headroom > 0) pts.Add(corner + Vector3.up * headroom); }
                }
                else if (parts.TryGetValue(id, out var p))
                {
                    var b = p.localBounds;
                    for (int i = 0; i < 8; i++)
                    {
                        var corner = root.InverseTransformPoint(p.transform.TransformPoint(b.center + Vector3.Scale(b.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1))));
                        pts.Add(corner); if (headroom > 0) pts.Add(corner + Vector3.up * headroom);
                    }
                }
                else { var m = bench.Marker(id); if (m) pts.Add(root.InverseTransformPoint(m.transform.position)); else missing.Add(id); }
            }
            if (pts.Count == 0) { how = "nothing to frame: " + string.Join(", ", missing); return false; }
            float pitch = sh["pitch"] != null ? (float)sh["pitch"] : 45, yaw = sh["yaw"] != null ? (float)sh["yaw"] : 0, fov = (float)sh["fov"], margin = sh["margin"] != null ? (float)sh["margin"] : .06f;
            string anchor = (string)sh["anchor"] ?? "centre";
            float full = Mathf.Tan(fov * .5f * Mathf.Deg2Rad), tv = full * (1 - margin), th = full * 16f / 9f * (1 - margin);
            Vector3 r = default, u = default, f = default; float cx = 0, cy = 0, ymin = 0, ymax = 0; var turn = Quaternion.identity;
            void Aim(float p) { turn = Quaternion.Euler(p, 180 + yaw, 0); r = turn * Vector3.right; u = turn * Vector3.up; f = turn * Vector3.forward; }   // yaw 0 stands on the player's side (+Z) and looks at -Z
            bool Fits(float cz)
            {
                float xmin = float.MinValue, xmax = float.MaxValue; ymin = float.MinValue; ymax = float.MaxValue;
                foreach (var p in pts)
                {
                    float z = Vector3.Dot(p, f) - cz; if (z <= .02f) return false; float x = Vector3.Dot(p, r), y = Vector3.Dot(p, u);
                    xmin = Mathf.Max(xmin, x - z * th); xmax = Mathf.Min(xmax, x + z * th); ymin = Mathf.Max(ymin, y - z * tv); ymax = Mathf.Min(ymax, y + z * tv);
                }
                if (xmin > xmax || ymin > ymax) return false;
                cx = (xmin + xmax) * .5f; cy = anchor == "bottom" ? ymax : anchor == "top" ? ymin : (ymin + ymax) * .5f;
                return true;
            }
            bool Nearest(out float cz)
            {
                float nearest = pts.Min(p => Vector3.Dot(p, f)), centre = pts.Average(p => Vector3.Dot(p, f));
                float hi = nearest - .03f, lo = nearest - 30; cz = lo;
                if (sh["min"] != null) hi = Mathf.Min(hi, centre - (float)sh["min"]);   // never nearer than this to the middle of what is framed
                if (!Fits(lo)) return false;
                if (!Fits(hi)) { for (int i = 0; i < 40; i++) { float mid = (lo + hi) * .5f; if (Fits(mid)) lo = mid; else hi = mid; } hi = lo; }
                cz = hi; return Fits(cz);
            }
            Aim(pitch); string extra = "";
            if (!Nearest(out float at)) { how = "does not fit the lens"; return false; }
            if (sh["avoid"] is JObject avoid && avoid["box"] is JArray ab && ab.Count == 6)
            {
                // something that must stay out of the way (the old bench's print head hangs over the middle of the worktop): it may
                // take no more than `max_top` of the picture's height, at the top. The eye goes steeper and further back until
                // that holds, and of the views that hold it the one in which what is framed stands tallest is taken.
                var c = new Vector3((float)ab[0], (float)ab[1], (float)ab[2]); var e = new Vector3((float)ab[3], (float)ab[4], (float)ab[5]) * .5f;
                float share = avoid["max_top"] != null ? (float)avoid["max_top"] : .1f, k = 1 - 2 * share, steepest = avoid["max_pitch"] != null ? (float)avoid["max_pitch"] : 78;
                float best = -1, bestPitch = pitch, bestAt = at, bestCy = cy, bestCx = cx;
                for (float p = pitch; p <= steepest + .01f; p += 1)
                {
                    Aim(p); if (!Nearest(out float near)) continue;
                    for (float back = 0; back <= 1.5f; back += .02f)
                    {
                        float cz = near - back; if (!Fits(cz)) continue;
                        float allowed = float.MaxValue;
                        for (int i = 0; i < 8; i++)
                        {
                            var q = c + Vector3.Scale(e, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                            float z = Vector3.Dot(q, f) - cz; if (z <= .02f) continue;
                            if (Mathf.Abs(Vector3.Dot(q, r) - cx) > z * full * 16f / 9f) continue;   // off to the side of the picture
                            allowed = Mathf.Min(allowed, Vector3.Dot(q, u) - k * z * full);
                        }
                        float y0 = Mathf.Min(cy, allowed); if (y0 < ymin) continue;
                        float low = float.MaxValue, high = float.MinValue;
                        foreach (var pt in pts) { float z = Vector3.Dot(pt, f) - cz, y = (Vector3.Dot(pt, u) - y0) / (z * full); low = Mathf.Min(low, y); high = Mathf.Max(high, y); }
                        float fill = (high - low) * .5f;
                        if (fill > best + 1e-4f) { best = fill; bestPitch = p; bestAt = cz; bestCy = y0; bestCx = cx; }
                    }
                }
                if (best < 0) { Aim(pitch); Nearest(out at); extra = $"; cannot keep the box at {c} in the top {share:P0}"; }
                else { Aim(bestPitch); at = bestAt; cx = bestCx; cy = bestCy; pitch = bestPitch; extra = $"; the box at {c} kept to the top {share:P0}, what is framed stands {best:P0} of the picture high"; }
            }
            position = r * cx + u * cy + f * at; rotation = turn;
            how = $"frames {string.Join(", ", ids.Except(missing))}" + (missing.Count > 0 ? $" (not on this bench: {string.Join(", ", missing)})" : "") + $", pitch {pitch:0}, {Vector3.Distance(position, pts.Aggregate(Vector3.zero, (a, b) => a + b) / pts.Count):0.00} m off" + extra;
            return true;
        }

        /// Points on a part's own surface, one to a cell of a grid in its local space, fine enough that a pointer over the
        /// part passes within `radius` of one: at most 512, the cell as small as 3 mm and never over 16 mm (a thing that
        /// would need coarser, and anything skinned, keeps its box: an empty list).
        static Vector3[] SurfacePoints(AssemblyPart p, Renderer[] own, out float radius)
        {
            radius = 0;
            if (own.Length == 0 || own.Any(r => r is SkinnedMeshRenderer)) return new Vector3[0];
            var t = p.transform; float scale = Mathf.Max(1e-6f, Mathf.Abs(t.lossyScale.x));
            var size = p.localBounds.size * scale; float spacing = Mathf.Max(.003f, Mathf.Max(size.x, Mathf.Max(size.y, size.z)) / 24);
            for (; spacing <= .016f; spacing *= 1.3f)
            {
                float cell = spacing / scale; var cells = new Dictionary<Vector3Int, Vector3>(); bool over = false;
                foreach (var r in own)
                {
                    var mf = r.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null; if (!mesh) continue;
                    var m = t.worldToLocalMatrix * r.transform.localToWorldMatrix; var v = mesh.vertices; var tri = mesh.triangles;
                    for (int i = 0; i + 2 < tri.Length && !over; i += 3)
                    {
                        Vector3 a = m.MultiplyPoint3x4(v[tri[i]]), b = m.MultiplyPoint3x4(v[tri[i + 1]]), c = m.MultiplyPoint3x4(v[tri[i + 2]]);
                        int n = Mathf.Clamp(Mathf.CeilToInt(Mathf.Max((b - a).magnitude, Mathf.Max((c - a).magnitude, (c - b).magnitude)) / cell), 1, 48);
                        for (int x = 0; x <= n && !over; x++) for (int y = 0; x + y <= n; y++)
                        {
                            var q = a + (b - a) * ((float)x / n) + (c - a) * ((float)y / n);
                            var key = new Vector3Int(Mathf.FloorToInt(q.x / cell), Mathf.FloorToInt(q.y / cell), Mathf.FloorToInt(q.z / cell));
                            if (cells.ContainsKey(key)) continue;
                            cells[key] = q; if (cells.Count > 512) { over = true; break; }
                        }
                    }
                    if (over) break;
                }
                if (!over && cells.Count > 0) { radius = cell; return cells.Values.ToArray(); }
                if (cells.Count == 0) break;
            }
            return new Vector3[0];
        }

        /// The unit cylinder as an asset (decals and the aim dot keep a reference to it in the prefab).
        /// A flat disc of the unit cylinder (radius 1, length 1, along Z) `diameter` metres across and `thick` metres deep, `z`
        /// metres out along its parent's +Z, whatever the parent's own scale.
        static void Disc(Transform t, float diameter, float thick, float z)
        {
            var ls = t.parent ? t.parent.lossyScale : Vector3.one; float sx = Mathf.Max(1e-6f, Mathf.Abs(ls.x)), sy = Mathf.Max(1e-6f, Mathf.Abs(ls.y)), sz = Mathf.Max(1e-6f, Mathf.Abs(ls.z));
            t.localScale = new Vector3(diameter * .5f / sx, diameter * .5f / sy, thick / sz); t.localPosition = new Vector3(0, 0, z / sz);
        }
        /// The printed target of a test card, in metres, flat in XY facing +Z: three ink rings (outer 90, 64, 40 mm) and an
        /// 8 mm dot. One mesh, kept as an asset so the prefab can hold it.
        static Mesh CardRings()
        {
            string path = GreyDir + "Meshes/card_rings.asset"; Directory.CreateDirectory(GreyDir + "Meshes");
            var v = new List<Vector3>(); var t = new List<int>(); const int sides = 48;
            void Annulus(float rOut, float rIn)
            {
                int b = v.Count;
                for (int i = 0; i <= sides; i++) { float a = i * Mathf.PI * 2 / sides; var d = new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0); v.Add(d * rOut); v.Add(d * rIn); }
                for (int i = 0; i < sides; i++) { int k = b + i * 2; t.AddRange(new[] { k, k + 2, k + 1, k + 1, k + 2, k + 3 }); t.AddRange(new[] { k, k + 1, k + 2, k + 1, k + 3, k + 2 }); }
            }
            Annulus(.045f, .042f); Annulus(.032f, .029f); Annulus(.020f, .017f); Annulus(.004f, 0);
            var fresh = new Mesh { name = "card rings" }; fresh.SetVertices(v); fresh.SetTriangles(t, 0); fresh.RecalculateNormals(); fresh.RecalculateBounds();
            var m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (!m) { AssetDatabase.CreateAsset(fresh, path); return fresh; }
            m.Clear(); m.SetVertices(fresh.vertices); m.SetTriangles(fresh.triangles, 0); m.RecalculateNormals(); m.RecalculateBounds(); EditorUtility.SetDirty(m);
            UnityEngine.Object.DestroyImmediate(fresh); return m;
        }
        static Mesh AssetCylinder()
        {
            string path = GreyDir + "Meshes/unit_cylinder.asset"; Directory.CreateDirectory(GreyDir + "Meshes");
            var m = AssetDatabase.LoadAssetAtPath<Mesh>(path); var fresh = UnitCylinder();
            if (!m) { AssetDatabase.CreateAsset(fresh, path); return fresh; }
            m.Clear(); m.SetVertices(fresh.vertices); m.SetNormals(fresh.normals); m.SetTriangles(fresh.triangles, 0); m.RecalculateBounds(); EditorUtility.SetDirty(m);
            UnityEngine.Object.DestroyImmediate(fresh);
            return m;
        }
    }
}
