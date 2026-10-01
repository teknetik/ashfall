using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: West Gate arches (art-direction review item 4, "the arches are blind"). The two District gate
    /// arches at the +X spawn (the Meshy `District gate` instances, still chunk-rendered and untouched) get sealed
    /// working gates set 1.6 m back in the arch passage: steel-faced timber leaves (framed, ledged and braced on the city
    /// face, a wicket door in arch A's south leaf), strap hinges on pintles let into the jambs, a timber drop bar in steel
    /// stirrups with its ends in jamb pockets, a transom and a fixed head grille to the soffit, a worn steel threshold,
    /// guard stones (Ward masonry kit) and steel/rubber corner guards at the tunnel mouth, cart ruts, scuffs, sand and
    /// grime decals, and a caged bulkhead lamp on the Ward lighting clock.
    ///
    /// Sources: art/west_gate_arches_20261001 (author_gate_arches.py → Art/WestGateArches/Models/WGA_Gate{A,B}.glb with
    /// LOD0-2 per group, COL_ boxes and LIGHT_/AIM_ empties; layout.py → layout.json with placements, decals, light and
    /// review cameras; make_decals.py → the rut and jamb-scrape decal textures). Materials are shared: TR_Timber* (the
    /// training range's weathered timber), WG_* steel/rubber (the West Gate kit), VH_* masonry and lamp (Vanguard Hall).
    /// Menu: Athen Hill → West Gate arches → Build assets, Install (one time; rollback copy), Verify saved scene,
    /// Add review cameras. Batch: RunBatch --steps build,install,verify,capture[:filter] [--out dir].
    /// The leaves' collider seals each opening at the leaves (the city stays enclosed); the guard stones have their own.
    /// Nothing is retired and no render-chunk source changes (the Meshy arches keep their chunks).
    /// </summary>
    public static class WestGateArchesPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/WestGateArches/";
        const string ModelDir = Root + "Models/";
        const string TexDir = Root + "Textures/";
        const string MatDir = Root + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/WestGateArches/";
        const string TimberMats = "Assets/AthenHill/Art/TrainingRange/Materials/";
        const string WestGateMats = "Assets/AthenHill/Art/WestGate/Materials/";
        const string HallMats = "Assets/AthenHill/Art/VanguardHall/Materials/";
        const string DecalTemplate = "Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat";
        const string LayoutPath = "../../art/west_gate_arches_20261001/layout.json";
        const string Evidence = "../evidence/west-gate-arches/20261001/";
        public const string RootName = "Ward west gate arches";
        public const string CamRootName = "West gate arch review cameras";
        static readonly string[] Keys = { "A", "B" };

        // LOD switch distances (metres at 60° FOV, PC lodBias 2): bevelled + bolted LOD0 within ~15 m, LOD1 to ~45 m,
        // plain LOD2 beyond, culled past ~400 m. Converted per prefab with its LODGroup size (as the perimeter walls).
        const float Lod0Distance = 15f, Lod1Distance = 45f, CullDistance = 400f, LodBias = 2f;

        static JObject Layout() => JObject.Parse(File.ReadAllText(LayoutPath));
        static string PrefabPath(string key) => PrefabDir + "WGA_Gate" + key + ".prefab";
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);

        // ------------------------------------------------------------------ build assets
        [MenuItem("Athen Hill/West Gate arches/Build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            foreach (var k in Keys) AssetDatabase.ImportAsset(ModelDir + "WGA_Gate" + k + ".glb", ImportAssetOptions.ForceUpdate);
            ImportDecalTextures();
            var mats = BuildMaterials();
            Directory.CreateDirectory(PrefabDir);
            var layout = Layout();
            var missing = new HashSet<string>();
            var report = new Dictionary<string, object>();
            foreach (var k in Keys) report[k] = BuildPrefab(k, layout, mats, missing);
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(new { prefabs = report, unmapped = missing.OrderBy(x => x).ToArray() }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return "prefabs " + report.Count + ", unmapped: " + (missing.Count == 0 ? "none" : string.Join(", ", missing));
        }

        static void ImportDecalTextures()
        {
            foreach (var f in Directory.GetFiles(TexDir, "WGA_Decal*.png"))
            {
                var path = f.Replace('\\', '/');
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                if (!ti) continue;
                ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.alphaIsTransparency = true;
                ti.alphaSource = TextureImporterAlphaSource.FromInput; ti.wrapMode = TextureWrapMode.Clamp;
                ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.maxTextureSize = 2048; ti.anisoLevel = 4;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
        }

        static Material Load(string path)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) throw new Exception("Shared material missing: " + path);
            return m;
        }

        static Dictionary<string, Material> BuildMaterials()
        {
            var mats = new Dictionary<string, Material>();
            foreach (var n in new[] { "TR_Timber", "TR_TimberDark", "TR_TimberFresh" }) mats[n] = Load(TimberMats + n + ".mat");
            foreach (var n in new[] { "WG_RustSteel", "WG_PlateSteel", "WG_Rubber", "WG_Collider", "WG_DecalSandSpill", "WG_DecalGrime" })
                mats[n] = Load(WestGateMats + n + ".mat");
            foreach (var n in new[] { "VH_Ashlar", "VH_Dark", "VH_Steel", "VH_LampLens" }) mats[n] = Load(HallMats + n + ".mat");
            mats["Weathering"] = Load(DecalTemplate);
            // this pass's decals: copies of the accepted weathering decal material with our base maps
            var template = mats["Weathering"];
            if (!template.HasProperty("Base_Map")) throw new Exception("Decal template has no Base_Map: " + DecalTemplate);
            Directory.CreateDirectory(MatDir);
            foreach (var n in new[] { "WGA_DecalCartRuts", "WGA_DecalJambScrape", "WGA_DecalStencil" })
            {
                var path = MatDir + n + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) { m = new Material(template) { name = n }; AssetDatabase.CreateAsset(m, path); }
                else { m.shader = template.shader; m.CopyPropertiesFromMaterial(template); }
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + n + ".png");
                if (!tex) throw new Exception("Decal texture missing: " + TexDir + n + ".png");
                m.SetTexture("Base_Map", tex);
                if (m.HasProperty("Normal_Blend")) m.SetFloat("Normal_Blend", 0);
                EditorUtility.SetDirty(m);
                mats[n] = m;
            }
            return mats;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m) && m) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        static int Tris(Renderer r)
        {
            var mf = r ? r.GetComponent<MeshFilter>() : null;
            if (!mf || !mf.sharedMesh) return 0;
            int n = 0;
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) n += (int)mf.sharedMesh.GetIndexCount(s) / 3;
            return n;
        }

        // Leaves (timber, skin, transom, grille) and the guard stones cast; hardware, lamp and the stone bands never do
        static bool Casts(string node) => node.Contains("_Leaves_") || node.Contains("_Stone_LOD");

        static object BuildPrefab(string key, JObject layout, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var glb = ModelDir + "WGA_Gate" + key + ".glb";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
            if (!model) throw new Exception("Model not imported: " + glb);
            var nodes = model.GetComponentsInChildren<Transform>(true).ToDictionary(t => t.name, t => t);
            var root = new GameObject("WGA_Gate" + key);
            var rec = new Dictionary<string, object>();
            try
            {
                var levels = new List<LOD>();
                for (int lod = 0; lod < 3; lod++)
                {
                    var holder = new GameObject("LOD" + lod).transform; holder.SetParent(root.transform, false);
                    var rs = new List<Renderer>();
                    foreach (var part in new[] { "Leaves", "Iron", "Lamp", "Stone", "StoneBand" })
                    {
                        if (!nodes.TryGetValue($"WGA_Gate{key}_{part}_LOD{lod}", out var src)) continue;
                        var mf = src.GetComponent<MeshFilter>(); var mr = src.GetComponent<MeshRenderer>();
                        if (!mf || !mr) continue;
                        var go = new GameObject(src.name); go.transform.SetParent(holder, false);
                        go.transform.localPosition = model.transform.InverseTransformPoint(src.position);
                        go.transform.localRotation = Quaternion.Inverse(model.transform.rotation) * src.rotation;
                        go.AddComponent<MeshFilter>().sharedMesh = mf.sharedMesh;
                        var r = go.AddComponent<MeshRenderer>();
                        var slots = mr.sharedMaterials;
                        for (int i = 0; i < slots.Length; i++)
                        {
                            var m = slots[i] ? Lookup(mats, slots[i].name) : null;
                            if (m) slots[i] = m; else missing.Add(src.name + ":" + (slots[i] ? slots[i].name : "null"));
                        }
                        r.sharedMaterials = slots;
                        r.shadowCastingMode = Casts(src.name) ? ShadowCastingMode.On : ShadowCastingMode.Off;
                        r.receiveShadows = true;
                        r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                        r.receiveGI = ReceiveGI.LightProbes; r.lightProbeUsage = LightProbeUsage.BlendProbes;
                        rs.Add(r);
                    }
                    if (rs.Count == 0) throw new Exception($"No LOD{lod} meshes for gate {key}");
                    rec["LOD" + lod] = rs.Sum(Tris);
                    levels.Add(new LOD(new[] { .5f, .2f, .01f }[lod], rs.ToArray()));
                }
                var g = root.AddComponent<LODGroup>();
                g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                float H(float d) => Mathf.Clamp(g.size * LodBias / (2f * d * Mathf.Tan(30f * Mathf.Deg2Rad)), .004f, .98f);
                var cuts = new[] { H(Lod0Distance), H(Lod1Distance), H(CullDistance) };
                for (int i = 0; i < levels.Count; i++) levels[i] = new LOD(cuts[i], levels[i].renderers);
                g.SetLODs(levels.ToArray()); g.RecalculateBounds();
                rec["lodCuts"] = cuts.Select(c => Math.Round(c, 4)).ToArray();
                rec["size"] = Math.Round(g.size, 2);

                // colliders: COL_ boxes → BoxColliders (the leaves seal the opening; guard stones)
                var cols = new GameObject("Colliders").transform; cols.SetParent(root.transform, false);
                foreach (var t in nodes.Values.Where(t => t.name.StartsWith("COL_")).OrderBy(t => t.name))
                {
                    var mf = t.GetComponent<MeshFilter>();
                    if (!mf || !mf.sharedMesh) continue;
                    var go = new GameObject(t.name); go.transform.SetParent(cols, false);
                    var b = mf.sharedMesh.bounds;
                    var bc = go.AddComponent<BoxCollider>();
                    bc.center = model.transform.InverseTransformPoint(t.TransformPoint(b.center)); bc.size = b.size;
                }
                rec["colliders"] = cols.childCount;

                // bulkhead lamp (bound to the Ward lighting clock on install)
                var ls = layout["light"];
                if (nodes.TryGetValue($"LIGHT_WGA_Gate{key}_Bulkhead", out var lt) && nodes.TryGetValue($"AIM_WGA_Gate{key}_Bulkhead", out var aim))
                {
                    var lgo = new GameObject("Bulkhead light"); lgo.transform.SetParent(root.transform, false);
                    var p = model.transform.InverseTransformPoint(lt.position); var a = model.transform.InverseTransformPoint(aim.position);
                    lgo.transform.localPosition = p; lgo.transform.localRotation = Quaternion.LookRotation(a - p, Vector3.right);
                    var l = lgo.AddComponent<Light>();
                    l.type = LightType.Spot; l.lightmapBakeType = LightmapBakeType.Realtime;
                    var c = ls["color"]; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                    l.intensity = (float)ls["intensity"]; l.range = (float)ls["range"];
                    l.spotAngle = (float)ls["angle"]; l.innerSpotAngle = (float)ls["inner"];
                    l.shadows = LightShadows.None;
                    rec["light"] = new { pos = new[] { p.x, p.y, p.z }, intensity = l.intensity, range = l.range };
                }
                else missing.Add($"gate {key}: LIGHT_/AIM_ empties");

                // decals (URP projectors, local to the gate)
                var dRoot = new GameObject("Decals").transform; dRoot.SetParent(root.transform, false);
                int nd = 0;
                foreach (JObject d in layout["decals"])
                {
                    var only = d["gate"];
                    if (only != null && only.Type != JTokenType.Null && (string)only != key) continue;
                    var kind = (string)d["kind"];
                    Material m; Vector2 uvScale = Vector2.one, uvBias = Vector2.zero;
                    switch (kind)
                    {
                        case "ruts": m = mats["WGA_DecalCartRuts"]; break;
                        case "jamb": m = mats["WGA_DecalJambScrape"]; break;
                        case "sand": m = mats["WG_DecalSandSpill"]; break;
                        case "grime": m = mats["WG_DecalGrime"]; break;
                        case "scuffs": m = mats["Weathering"]; uvScale = new Vector2(.49f, .49f); uvBias = new Vector2(.005f, .005f); break;
                        case "stencil": m = mats["WGA_DecalStencil"]; break;
                        default: missing.Add("decal kind " + kind); continue;
                    }
                    var go = new GameObject("Decal " + kind + " " + (++nd)); go.transform.SetParent(dRoot, false);
                    var fwd = V3(d["fwd"]).normalized;
                    var size = V3(d["size"]);
                    var uv = d["uv"];
                    if (uv != null && uv.Type == JTokenType.Array) { uvScale = new Vector2((float)uv[0], (float)uv[1]); uvBias = new Vector2((float)uv[2], (float)uv[3]); }
                    var proj = go.AddComponent<DecalProjector>();
                    proj.material = m; proj.uvScale = uvScale; proj.uvBias = uvBias;
                    proj.fadeFactor = (float)d["opacity"]; proj.drawDistance = 40; proj.fadeScale = .7f;
                    var fade = d["angleFade"]; proj.startAngleFade = (float)fade[0]; proj.endAngleFade = (float)fade[1];
                    if (d["up"] == null || d["up"].Type == JTokenType.Null)
                    {
                        // ground decal: projected straight down from 0.25 m above the surface; texture V along fwd
                        var pos = V3(d["pos"]);
                        go.transform.localPosition = pos + Vector3.up * (size.z * .5f);
                        go.transform.localRotation = Quaternion.LookRotation(Vector3.down, fwd);
                        proj.size = size; proj.pivot = new Vector3(0, 0, size.z * .5f);
                    }
                    else
                    {
                        // wall decal: projected along fwd, texture V along `up`
                        go.transform.localPosition = V3(d["pos"]);
                        go.transform.localRotation = Quaternion.LookRotation(fwd, V3(d["up"]));
                        proj.size = size; proj.pivot = Vector3.zero;
                    }
                }
                rec["decals"] = nd;

                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    if (t.GetComponent<Light>() || t.GetComponent<DecalProjector>()) continue;
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(key));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            return rec;
        }

        // ------------------------------------------------------------------ scene helpers
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        static GameObject PlaceGates(UnityEngine.SceneManagement.Scene scene, JObject layout, out List<Light> lamps)
        {
            var root = new GameObject(RootName);
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            lamps = new List<Light>();
            foreach (var gate in layout["gates"])
            {
                var key = (string)gate["key"];
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(key));
                if (!prefab) throw new Exception("Prefab missing (build first): " + PrefabPath(key));
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(V3(gate["pos"]), Quaternion.identity);
                go.name = (string)gate["name"];
                lamps.AddRange(go.GetComponentsInChildren<Light>(true));
            }
            return root;
        }

        // ------------------------------------------------------------------ install
        [MenuItem("Athen Hill/West Gate arches/Install (one time)")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed root (the first rollback copy of the scene is kept).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (existing && !replace) throw new Exception("The West Gate arch fittings are already installed; edit them in place.");
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            if (existing)
            {
                var old = existing.GetComponentsInChildren<Light>(true);
                if (circuit)
                {
                    circuit.practicalLights = circuit.practicalLights.Where(l => l && !old.Contains(l)).ToArray();
                    circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !old.Contains(l)).ToArray();
                }
                UnityEngine.Object.DestroyImmediate(existing);
            }
            var layout = Layout();
            Directory.CreateDirectory(Evidence + "rollback");
            if (!replace) File.Copy(ScenePath, Evidence + "rollback/before-west-gate-arches.unity", true);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            string fpBefore = chunks ? chunks.sourceFingerprint : null;
            var record = new Dictionary<string, object>();
            var root = PlaceGates(scene, layout, out var lamps);
            if (circuit)
            {
                circuit.practicalLights = circuit.practicalLights.Where(l => l).Concat(lamps).Distinct().ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l).Concat(lamps).Distinct().ToArray();
                EditorUtility.SetDirty(circuit);
            }
            record["gates"] = root.transform.Cast<Transform>().Select(t => new { t.name, pos = new[] { t.position.x, t.position.y, t.position.z } }).ToArray();
            record["lights"] = lamps.Select(l => PathOf(l.transform)).ToArray();
            record["lightCircuitFound"] = circuit != null;
            record["retired"] = new string[0];
            AddCameras(scene, layout);
            record["reviewCameras"] = layout["cameras"].Count();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            if (chunks) record["chunkFingerprintUnchanged"] = chunks.sourceFingerprint == fpBefore && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + (replace ? "reinstall.json" : "install.json"), json);
            return json;
        }

        /// Measurement only (A/B frame time): switches the root off or on in the saved scene. Do not use on the shared
        /// scene while other passes build (the orchestrator builds A/B arms from scene snapshots).
        static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            root.SetActive(on);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return RootName + (on ? " on" : " off");
        }

        // ------------------------------------------------------------------ review cameras
        static void AddCameras(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (!root) { root = new GameObject(CamRootName); UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene); }
            foreach (var c in layout["cameras"])
            {
                var name = (string)c["name"];
                var t = root.transform.Find(name);
                if (!t) { t = new GameObject(name).transform; t.SetParent(root.transform, false); }
                var pos = V3(c["pos"]);
                t.SetPositionAndRotation(pos, Quaternion.LookRotation(V3(c["target"]) - pos, Vector3.up));
                var cam = t.GetComponent<Camera>();                  // Unity objects: no ?? (fake null)
                if (!cam) cam = t.gameObject.AddComponent<Camera>();
                cam.enabled = false; cam.fieldOfView = (float)c["fov"]; cam.nearClipPlane = .05f;
            }
        }

        [MenuItem("Athen Hill/West Gate arches/Add review cameras")]
        public static string ReviewCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            AddCameras(scene, layout);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "review cameras: " + layout["cameras"].Count();
        }

        /// Editor captures (MainCamera clone, post-processing on) of the review cameras; never saved. Before the install
        /// the gates and cameras are placed in memory only. filter: '+'-separated camera-name prefixes (≤ 6 per run).
        public static string CaptureViews(string outDir, string filter)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            if (!scene.GetRootGameObjects().Any(g => g.name == RootName)) PlaceGates(scene, layout, out _);
            AddCameras(scene, layout);
            var views = layout["cameras"]
                .Where(c => string.IsNullOrEmpty(filter) || filter.Split('+').Any(f => ((string)c["name"]).StartsWith(f)))
                .Select(c => ((string)c["name"], V3(c["pos"]), V3(c["target"]), (float)c["fov"])).Take(6).ToList();
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/West Gate arches/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (root)
            {
                r["active"] = root.activeSelf;
                var gates = root.GetComponentsInChildren<LODGroup>(true);
                r["gates"] = gates.Length;
                r["prefabLinked"] = gates.Count(m => PrefabUtility.IsPartOfPrefabInstance(m.gameObject));
                r["nonUniformScale"] = gates.Where(m => (m.transform.lossyScale - Vector3.one).sqrMagnitude > 1e-6).Select(m => PathOf(m.transform)).ToArray();
                var rends = root.GetComponentsInChildren<Renderer>(true);
                r["renderers"] = rends.Length;
                r["missingMaterials"] = rends.Count(x => x.sharedMaterials.Any(m => !m));
                r["materials"] = rends.SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => m.name + " (" + m.shader.name + ")").Distinct().OrderBy(x => x).ToArray();
                r["triangles"] = gates.ToDictionary(gg => gg.name, gg => gg.GetLODs().Select(l => l.renderers.Where(x => x).Sum(Tris)).ToArray());
                r["shadowCasters"] = rends.Where(x => x.shadowCastingMode != ShadowCastingMode.Off).Select(x => x.name).ToArray();
                var cols = root.GetComponentsInChildren<Collider>(true);
                r["colliders"] = cols.Select(c => new { c.name, c.enabled, active = c.gameObject.activeInHierarchy, center = new[] { c.bounds.center.x, c.bounds.center.y, c.bounds.center.z }, size = new[] { c.bounds.size.x, c.bounds.size.y, c.bounds.size.z } }).ToArray();
                r["decals"] = root.GetComponentsInChildren<DecalProjector>(true).Count(d => d.material);
                var lamps = root.GetComponentsInChildren<Light>(true);
                var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
                r["lights"] = lamps.Length;
                r["lightsOnCircuit"] = circuit ? lamps.Count(l => circuit.practicalLights.Contains(l) && circuit.nightOnlyLights.Contains(l)) : -1;
                // the spawn and Vex must be clear of every new collider (capsule r 0.35 + margin)
                var player = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Player");
                var vex = GameObject.Find("Colonists/npc_vex");
                float Clear(Vector3 p) => cols.Length == 0 ? 99f : cols.Min(c => Vector3.Distance(new Vector3(p.x, c.bounds.center.y, p.z), c.bounds.ClosestPoint(new Vector3(p.x, c.bounds.center.y, p.z))));
                r["spawnClearance"] = player ? Math.Round(Clear(player.transform.position), 2) : -1;
                r["vexClearance"] = vex ? Math.Round(Clear(vex.transform.position), 2) : -1;
            }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            var meshyGate = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "District rebuild");
            r["meshyArchesUntouched"] = meshyGate ? meshyGate.GetComponentsInChildren<Transform>(true).Count(t => t.name == "District gate" && t.gameObject.activeInHierarchy) : -1;
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            r["reviewCameras"] = cams ? cams.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            r["expectedCameras"] = layout["cameras"].Count();
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.WestGateArchesPass.RunBatch --steps build,install,verify,capture[:filter] [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "verify").Split(',');
            var outDir = Arg("--out", Evidence + "editor");
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "reinstall" => Reinstall(),
                        "cameras" => ReviewCameras(),
                        "toggle" => Toggle(parts[1] == "on"),
                        "capture" => CaptureViews(outDir, parts.Length > 1 ? parts[1] : ""),
                        "verify" => Verify(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("WestGateArchesPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
