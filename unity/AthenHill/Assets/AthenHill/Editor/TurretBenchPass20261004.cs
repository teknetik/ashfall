using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// Carl's Meshy turret and bench, 4 Oct 2026 (art/turret_bench_20261004/README.md).
    /// Sources: meshy/turret-bench-20261004/source (Meshy web exports) → art/turret_bench_20261004/prepare_meshy.py →
    /// Art/TurretBench/&lt;id&gt;/&lt;id&gt;_LOD0..2.glb + maps. Steps:
    ///   survey    — read-only list of turret/gun/bench objects in the saved scene (survey.txt)
    ///   assets    — texture importers, TB_* materials, Prefabs/TurretBench/TB_SentinelTurret and TB_CyberBench (LODs,
    ///               colliders, the bench's two NPC sit points)
    ///   bastions  — the gabion bastion models are re-authored without the round-two pintle gun (author_life.py,
    ///               GATE_GUN = False): their Metal/Hardware parts lost material slots, so every renderer of the
    ///               WL_GateBastionS/N prefabs is rebound by material name from its glb, and the turret is mounted on
    ///               the gun deck (the bastion json's "Sentinel turret" mount). Edited in place: scene links kept.
    ///   benches   — every active SD_bench_painted instance gets a TB_CyberBench sibling with the same transform and the
    ///               old one goes inactive; the four primitive AuthoredWorld PROP_bench_00–03 slabs (still drawn by the
    ///               render chunks) and their COL_bench boxes go inactive, two Meshy benches stand in each slab's place;
    ///               render chunks rebuilt
    ///   cameras   — cam_tb_* review cameras at player height
    ///   verify / others (the touched passes' own verify steps) / capture[:prefix] / rollback
    /// -executeMethod AthenHill.Editor.TurretBenchPass20261004.RunBatch --steps assets,bastions,benches,cameras,verify
    /// </summary>
    public static class TurretBenchPass20261004
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string ArtRoot = "Assets/AthenHill/Art/TurretBench/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/TurretBench/";
        const string TurretPrefab = PrefabDir + "TB_SentinelTurret.prefab";
        const string BenchPrefab = PrefabDir + "TB_CyberBench.prefab";
        const string OldBench = "Assets/AthenHill/Prefabs/StreetDressing/SD_bench_painted.prefab";
        const string Template = "Assets/AthenHill/Art/StreetDressing/Materials/SD_field_generator.mat";
        const string WLModels = "Assets/AthenHill/Art/WardLife/Models/";
        const string WLPrefabs = "Assets/AthenHill/Prefabs/WardLife/";
        const string BenchRootName = "Ward Meshy benches";
        const string CamRootName = "Turret and bench review cameras";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/turret_bench_20261004");
        static string Record => Path.Combine(ArtDir, "record.json");
        static string Evidence => Path.Combine(Repo, "unity/evidence/turret-bench/20261004");

        static IEnumerable<Transform> All() => EditorSceneManager.GetActiveScene().GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true));
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static string V(Vector3 v) => $"({v.x:0.##}, {v.y:0.##}, {v.z:0.##})";

        // ---- rollback record
        class Rec { public Dictionary<string, bool> active = new Dictionary<string, bool>(); public List<string> created = new List<string>(); public List<string> log = new List<string>(); }
        static Rec rec;
        static Rec Load() => File.Exists(Record) ? JsonConvert.DeserializeObject<Rec>(File.ReadAllText(Record)) : new Rec();
        static void Save() { Directory.CreateDirectory(ArtDir); File.WriteAllText(Record, JsonConvert.SerializeObject(rec, Formatting.Indented)); }
        static void SetActive(Transform t, bool on) { var p = PathOf(t); if (!rec.active.ContainsKey(p)) rec.active[p] = t.gameObject.activeSelf; t.gameObject.SetActive(on); }

        // ------------------------------------------------------------------ survey
        static string Survey()
        {
            var rx = new Regex("turret|gun|bench|pintle|sentinel", RegexOptions.IgnoreCase);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            var lines = new List<string>();
            foreach (var t in All())
            {
                var mf = t.GetComponent<MeshFilter>();
                var mesh = mf ? mf.sharedMesh : null;
                var src = PrefabUtility.GetCorrespondingObjectFromOriginalSource(t.gameObject);
                var srcPath = src ? AssetDatabase.GetAssetPath(src) : "";
                bool hit = rx.IsMatch(t.name) || (mesh && rx.IsMatch(mesh.name)) || (PrefabUtility.IsAnyPrefabInstanceRoot(t.gameObject) && rx.IsMatch(srcPath));
                if (!hit) continue;
                var r = t.GetComponent<Renderer>();
                string chunk = "";
                if (r && chunks && chunks.sources != null) { int i = Array.IndexOf(chunks.sources, r); if (i >= 0) chunk = " | chunked " + (chunks.sourceVisibility[i] ? "visible" : "hidden"); }
                lines.Add($"{(t.gameObject.activeInHierarchy ? "ON " : "off")} {PathOf(t)} | pos {V(t.position)} yaw {t.eulerAngles.y:0} | mesh {(mesh ? mesh.name + " " + mesh.triangles.Length / 3 + "t" : "-")} | bounds {(r ? V(r.bounds.size) : "-")} | src {srcPath}{chunk}");
            }
            File.WriteAllLines(Path.Combine(ArtDir, "survey.txt"), lines);
            return lines.Count + " matches -> survey.txt";
        }

        // ------------------------------------------------------------------ assets
        static void Tex(string path, bool normal, bool srgb)
        {
            var ti = (TextureImporter)AssetImporter.GetAtPath(path) ?? throw new Exception("No texture " + path);
            ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = srgb; ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.maxTextureSize = 2048;
            ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.anisoLevel = 4;
            ti.SaveAndReimport();
        }
        static string Find(string dir, string prefix) => Directory.GetFiles(dir, prefix + ".*").Where(f => !f.EndsWith(".meta")).Select(f => f.Replace('\\', '/')).FirstOrDefault() ?? throw new Exception("Missing " + dir + prefix);

        static Material BuildMaterial(string id)
        {
            var dir = ArtRoot + id + "/";
            string baseC = Find(dir, "source_BaseColor"), nrm = Find(dir, "source_Normal"), mask = dir + id + "_Mask.png";
            AssetDatabase.ImportAsset(mask, ImportAssetOptions.ForceUpdate);
            Tex(baseC, false, true); Tex(nrm, true, false); Tex(mask, false, false);
            Directory.CreateDirectory(ArtRoot + "Materials");
            var path = ArtRoot + "Materials/TB_" + id + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            var template = AssetDatabase.LoadAssetAtPath<Material>(Template) ?? throw new Exception("No template " + Template);
            if (!m) { m = new Material(template) { name = "TB_" + id }; AssetDatabase.CreateAsset(m, path); }
            else m.CopyPropertiesFromMaterial(template);
            var b = AssetDatabase.LoadAssetAtPath<Texture2D>(baseC); var n = AssetDatabase.LoadAssetAtPath<Texture2D>(nrm); var k = AssetDatabase.LoadAssetAtPath<Texture2D>(mask);
            m.SetTexture("_BaseMap", b); m.SetTexture("_MainTex", b); m.SetColor("_BaseColor", Color.white); m.SetColor("_Color", Color.white);
            m.SetTexture("_BumpMap", n); m.SetFloat("_BumpScale", 1f);
            m.SetTexture("_MetallicGlossMap", k); m.SetTexture("_OcclusionMap", k); m.SetFloat("_Metallic", 1f); m.SetFloat("_Smoothness", 1f);
            m.SetFloat("_OcclusionStrength", 1f);
            m.EnableKeyword("_NORMALMAP"); m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.EnableKeyword("_OCCLUSIONMAP");
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        static GameObject BuildPrefab(string id, string prefabPath, Material mat, float[] cuts, Action<GameObject, Mesh> extra)
        {
            Directory.CreateDirectory(PrefabDir);
            var root = new GameObject(Path.GetFileNameWithoutExtension(prefabPath));
            try
            {
                var levels = new List<LOD>(); Mesh lod0 = null;
                for (int i = 0; i < 3; i++)
                {
                    var glb = ArtRoot + id + "/" + id + "_LOD" + i + ".glb";
                    AssetDatabase.ImportAsset(glb, ImportAssetOptions.ForceUpdate);
                    var mesh = AssetDatabase.LoadAllAssetsAtPath(glb).OfType<Mesh>().FirstOrDefault() ?? throw new Exception("No mesh in " + glb);
                    if (i == 0) lod0 = mesh;
                    var go = new GameObject("LOD" + i); go.transform.SetParent(root.transform, false);
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = mat;
                    r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true;
                    r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                    r.receiveGI = ReceiveGI.LightProbes; r.lightProbeUsage = LightProbeUsage.BlendProbes;
                    levels.Add(new LOD(cuts[i], new Renderer[] { r }));
                }
                var g = root.AddComponent<LODGroup>(); g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                extra(root, lod0);
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                return PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        static Bounds MeshBand(Mesh m, float y0, float y1)
        {
            var vs = m.vertices.Where(v => v.y >= y0 && v.y <= y1).ToArray();
            var b = new Bounds(vs[0], Vector3.zero); foreach (var v in vs) b.Encapsulate(v); return b;
        }
        static void Box(GameObject root, string name, Bounds b)
        {
            var go = new GameObject(name); go.transform.SetParent(root.transform, false);
            var c = go.AddComponent<BoxCollider>(); c.center = b.center; c.size = b.size;
        }

        static string Assets()
        {
            var tm = BuildMaterial("sentinel_turret");
            var bm = BuildMaterial("cyber_bench");
            BuildPrefab("sentinel_turret", TurretPrefab, tm, new[] { .35f, .1f, .02f }, (root, m) =>
            {
                var cols = new GameObject("Colliders"); cols.transform.SetParent(root.transform, false);
                Box(cols, "COL base", MeshBand(m, 0f, .3f));
                var post = MeshBand(m, .3f, .78f); post.size = new Vector3(Mathf.Min(post.size.x, .3f), post.size.y, Mathf.Min(post.size.z, .3f));
                post.center = new Vector3(0, post.center.y, 0); Box(cols, "COL post", post);
                var head = MeshBand(m, .78f, 2f);                         // housing and rear pod; the barrel (z > 0.45) left out
                float z0 = head.min.z, z1 = Mathf.Min(head.max.z, .45f);
                head.center = new Vector3(head.center.x, head.center.y, (z0 + z1) * .5f); head.size = new Vector3(head.size.x, head.size.y, z1 - z0);
                Box(cols, "COL housing", head);
            });
            BuildPrefab("cyber_bench", BenchPrefab, bm, new[] { .3f, .08f, .02f }, (root, m) =>
            {
                var b = m.bounds; var c = root.AddComponent<BoxCollider>(); c.center = b.center; c.size = b.size;
                foreach (var x in new[] { .3f, -.3f })
                {
                    var sp = new GameObject("NPC sit point"); sp.transform.SetParent(root.transform, false);
                    sp.transform.localPosition = new Vector3(x, .45f, .05f);
                }
            });
            AssetDatabase.SaveAssets();
            string Info(string p) { var g = AssetDatabase.LoadAssetAtPath<GameObject>(p); var lg = g.GetComponent<LODGroup>().GetLODs();
                return Path.GetFileName(p) + " tris " + string.Join("/", lg.Select(l => l.renderers[0].GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3)) + " size " + V(lg[0].renderers[0].GetComponent<MeshFilter>().sharedMesh.bounds.size) + " colliders " + g.GetComponentsInChildren<Collider>().Length; }
            return Info(TurretPrefab) + "; " + Info(BenchPrefab);
        }

        // ------------------------------------------------------------------ bastions
        static Material FindMat(string name, Dictionary<string, Material> known)
        {
            name = name.Replace(" (Instance)", "");
            if (known.TryGetValue(name, out var m)) return m;
            foreach (var g in AssetDatabase.FindAssets(name + " t:Material", new[] { "Assets/AthenHill/Art" }))
            {
                var mm = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(g));
                if (mm && mm.name == name && !AssetDatabase.GetAssetPath(mm).EndsWith(".glb")) { known[name] = mm; return mm; }
            }
            return null;
        }

        /// Rebind every model renderer of a WardLife bastion prefab from its glb (material slots by name) and set the
        /// turret mount as given (withTurret false removes it). Returns a short report.
        static string EditBastion(string model, bool withTurret)
        {
            for (int i = 0; i < 3; i++) AssetDatabase.ImportAsset(WLModels + model + "_LOD" + i + ".glb", ImportAssetOptions.ForceUpdate);
            var path = WLPrefabs + model + ".prefab";
            var root = PrefabUtility.LoadPrefabContents(path);
            var log = new List<string>(); int rebound = 0;
            try
            {
                var known = new Dictionary<string, Material>();
                foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true)) foreach (var m in r.sharedMaterials) if (m) known[m.name] = m;
                for (int lod = 0; lod < 3; lod++)
                {
                    var holder = root.transform.Find("LOD" + lod); if (!holder) continue;
                    var src = AssetDatabase.LoadAssetAtPath<GameObject>(WLModels + model + "_LOD" + lod + ".glb");
                    var byName = src.GetComponentsInChildren<MeshRenderer>(true).ToDictionary(r => r.name);
                    foreach (var r in holder.GetComponentsInChildren<MeshRenderer>(true))
                    {
                        if (!byName.TryGetValue(r.name, out var sr)) throw new Exception(model + ": no glb renderer for " + r.name);
                        var mf = r.GetComponent<MeshFilter>(); var smesh = sr.GetComponent<MeshFilter>().sharedMesh;
                        mf.sharedMesh = smesh;
                        var slots = sr.sharedMaterials.Select(s => s ? FindMat(s.name, known) : null).ToArray();
                        if (slots.Any(s => !s)) throw new Exception(model + ": unmapped material on " + r.name + ": " + string.Join(",", sr.sharedMaterials.Select(s => s ? s.name : "null")));
                        if (slots.Length != smesh.subMeshCount) throw new Exception(model + ": " + r.name + " slots " + slots.Length + " vs submeshes " + smesh.subMeshCount);
                        if (!r.sharedMaterials.SequenceEqual(slots)) { r.sharedMaterials = slots; rebound++; log.Add(r.name + " " + slots.Length + " slots"); }
                    }
                }
                root.GetComponent<LODGroup>()?.RecalculateBounds();
                var fit = root.transform.Find("Fittings") ?? throw new Exception(model + ": no Fittings");
                var old = fit.Find("Sentinel turret");
                if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
                if (withTurret)
                {
                    var key = model.EndsWith("S") ? "bastion_s" : "bastion_n";
                    var json = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(WLModels + key + ".json"));
                    var mnt = json["mounts"].FirstOrDefault(m => (string)m["name"] == "Sentinel turret") ?? throw new Exception(key + ".json has no Sentinel turret mount (re-run author_life.py -- bastion)");
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(TurretPrefab));
                    go.name = "Sentinel turret"; go.transform.SetParent(fit, false);
                    go.transform.localPosition = new Vector3((float)mnt["pos"][0], (float)mnt["pos"][1], (float)mnt["pos"][2]);
                    go.transform.localRotation = Quaternion.Euler(0, (float)mnt["yaw"], 0);
                    // the bastion's own COL_GunPlatform box covers the deck (WardLifePass strips mount colliders the same way)
                    foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                    log.Add("turret at " + V(go.transform.localPosition) + " yaw " + (float)mnt["yaw"]);
                }
                PrefabUtility.SaveAsPrefabAsset(root, path);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            return model + ": " + rebound + " renderers rebound (" + string.Join("; ", log) + ")";
        }

        static string Bastions() => EditBastion("WL_GateBastionS", true) + " | " + EditBastion("WL_GateBastionN", true);

        // ------------------------------------------------------------------ benches
        static float Ground(float x, float z, float near)
        {
            Physics.SyncTransforms();
            var hits = Physics.RaycastAll(new Vector3(x, near + 1f, z), Vector3.down, 3f, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance).ToArray();
            return hits.Length > 0 ? hits[0].point.y : near;
        }

        static string Benches()
        {
            var scene = EditorSceneManager.GetActiveScene();
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(BenchPrefab) ?? throw new Exception("Run assets first");
            var oldPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(OldBench);
            var log = new List<string>();
            // 1. the street kit's Poly Haven bench, wherever a pass placed it
            var olds = All().Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject) && t.gameObject.activeInHierarchy
                                         && PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject) == oldPrefab).ToList();
            foreach (var o in olds)
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.name = "Meshy bench (" + o.name + ")";
                go.transform.SetParent(o.parent, false);
                go.transform.SetLocalPositionAndRotation(o.localPosition, o.localRotation); go.transform.localScale = Vector3.one;
                go.transform.SetSiblingIndex(o.GetSiblingIndex() + 1);
                SetActive(o, false); rec.created.Add(PathOf(go.transform));
                log.Add(PathOf(o) + " -> " + go.name);
            }
            // 2. the four primitive slabs in AuthoredWorld (2.8 x 0.9 m, drawn through the render chunks)
            var authored = All().First(t => t.name == "AuthoredWorld" && !t.parent);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>() ?? throw new Exception("No render chunks");
            var benchRoot = All().FirstOrDefault(t => t.name == BenchRootName && !t.parent);
            if (!benchRoot) { benchRoot = new GameObject(BenchRootName).transform; rec.created.Add(BenchRootName); }
            int slabs = 0;
            for (int i = 0; i < 4; i++)
            {
                var id = $"bench_{i:00}";
                var seat = authored.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "PROP_" + id + "_seat");
                if (!seat || !seat.gameObject.activeInHierarchy) { log.Add(id + " not present/active, skipped"); continue; }
                var parts = authored.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("PROP_" + id + "_") || t.name == "COL_" + id).ToList();
                var sb = seat.GetComponent<Renderer>().bounds;
                float footY = parts.Select(t => t.GetComponent<Renderer>()).Where(r => r).Min(r => r.bounds.min.y);
                bool alongX = sb.size.x >= sb.size.z;
                foreach (var p in parts) SetActive(p, false);
                // seats face the avenue axis (z = 0): the slabs stand on its north and south edges
                var c = sb.center; var yaw = alongX ? (c.z > 0 ? 180f : 0f) : (c.x > 0 ? 270f : 90f);
                var along = alongX ? Vector3.right : Vector3.forward;
                for (int k = -1; k <= 1; k += 2)
                {
                    var p = c + along * (k * .68f);
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                    go.name = $"Meshy bench ({id} {(k < 0 ? "a" : "b")})"; go.transform.SetParent(benchRoot, false);
                    go.transform.SetPositionAndRotation(new Vector3(p.x, 0, p.z), Quaternion.Euler(0, yaw, 0));
                    go.SetActive(false);                                     // keep the new bench out of its own ground ray
                    float gy = Ground(p.x, p.z, footY);
                    go.SetActive(true);
                    go.transform.position = new Vector3(p.x, gy, p.z);
                    rec.created.Add(PathOf(go.transform));
                }
                slabs++;
                log.Add($"{id} slab {V(c)} ({parts.Count} parts) -> two benches yaw {yaw}");
            }
            if (slabs > 0) StaticRenderChunksEditor.Rebuild(chunks);
            return olds.Count + " street-kit benches replaced, " + slabs + " primitive slabs replaced" + (slabs > 0 ? ", render chunks rebuilt" : "") + ": " + string.Join("; ", log);
        }

        // ------------------------------------------------------------------ cameras
        static readonly (string name, Vector3 pos, Vector3 target, float fov)[] Cams =
        {
            ("cam_tb_turret_s_street", new Vector3(39.3f, 1.65f, -7.0f), new Vector3(43.0f, 1.3f, -10.6f), 50),
            ("cam_tb_turret_s_close",  new Vector3(41.7f, 1.75f, -9.2f), new Vector3(43.6f, 1.35f, -10.9f), 45),
            ("cam_tb_turret_n_street", new Vector3(39.3f, 1.65f, 19.0f), new Vector3(43.0f, 1.3f, 22.6f), 50),
            ("cam_tb_bench_hill",      new Vector3(-11.2f, 1.6f, -0.4f), new Vector3(-7.4f, .45f, 0.1f), 55),
            ("cam_tb_bench_plaza",     new Vector3(10.6f, 1.6f, 2.4f), new Vector3(11.5f, .4f, 5.7f), 50),
            ("cam_tb_bench_avenue",    new Vector3(31.0f, 1.65f, -3.5f), new Vector3(31.0f, .4f, -8.0f), 55),
        };

        static string Cameras()
        {
            var scene = EditorSceneManager.GetActiveScene();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (!root) { root = new GameObject(CamRootName); rec.created.Add(CamRootName); }
            foreach (var (name, pos, target, fov) in Cams)
            {
                var t = root.transform.Find(name);
                if (!t) { t = new GameObject(name).transform; t.SetParent(root.transform, false); }
                t.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var cam = t.GetComponent<Camera>() ? t.GetComponent<Camera>() : t.gameObject.AddComponent<Camera>();
                cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f;
            }
            return Cams.Length + " cameras under " + CamRootName;
        }

        static string Capture(string filter)
        {
            var views = Cams.Where(c => string.IsNullOrEmpty(filter) || c.name.StartsWith(filter)).Take(6).ToList();
            return string.Join(",", StreetDressingPass.Capture(Path.Combine(Evidence, "editor"), views));
        }

        // ------------------------------------------------------------------ verify / rollback
        static string Verify()
        {
            var fails = new List<string>();
            foreach (var p in new[] { TurretPrefab, BenchPrefab })
            {
                var g = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                if (!g) { fails.Add("missing " + p); continue; }
                foreach (var r in g.GetComponentsInChildren<MeshRenderer>(true)) if (r.sharedMaterials.Any(m => !m)) fails.Add(p + " null material");
            }
            int turrets = 0;
            foreach (var model in new[] { "WL_GateBastionS", "WL_GateBastionN" })
            {
                var g = AssetDatabase.LoadAssetAtPath<GameObject>(WLPrefabs + model + ".prefab");
                foreach (var r in g.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var m = r.GetComponent<MeshFilter>().sharedMesh;
                    if (!m) fails.Add(model + "/" + r.name + " no mesh");
                    else if (r.sharedMaterials.Length != m.subMeshCount || r.sharedMaterials.Any(x => !x)) fails.Add(model + "/" + r.name + " material slots");
                }
                if (g.transform.Find("Fittings/Sentinel turret")) turrets++; else fails.Add(model + " has no turret");
            }
            var sceneTurrets = All().Count(t => t.name == "Sentinel turret" && t.gameObject.activeInHierarchy);
            var oldPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(OldBench); var newPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(BenchPrefab);
            var roots = All().Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject)).ToList();
            int oldOn = roots.Count(t => t.gameObject.activeInHierarchy && PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject) == oldPrefab);
            int newOn = roots.Count(t => t.gameObject.activeInHierarchy && PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject) == newPrefab);
            if (oldOn > 0) fails.Add(oldOn + " old benches still active");
            var slabOn = All().Count(t => t.name.StartsWith("PROP_bench_0") && t.gameObject.activeInHierarchy);
            if (slabOn > 0) fails.Add(slabOn + " slab parts active");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            bool fp = chunks && !chunks.editingSources && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            if (!fp) fails.Add("render chunk fingerprint stale");
            var missing = All().SelectMany(t => t.GetComponents<Component>()).Count(c => c == null);
            if (missing > 0) fails.Add(missing + " missing scripts");
            var sit = All().Count(t => t.name == "NPC sit point" && t.gameObject.activeInHierarchy);
            var result = $"verify {(fails.Count == 0 ? "PASS" : "FAIL " + string.Join(", ", fails))}; bastion prefabs with turret {turrets}, active turrets in scene {sceneTurrets}; Meshy benches active {newOn}, old benches active {oldOn}; active NPC sit points {sit}; chunks fingerprint {(fp ? "ok" : "STALE")}";
            if (fails.Count > 0) throw new Exception(result);
            return result;
        }

        /// The verify steps of the passes whose placements this one touched (read-only; each may open the scene itself).
        static string Others()
        {
            var outs = new List<string>();
            foreach (var (name, fn) in new (string, Func<string>)[] { ("WardLife", WardLifePass.Verify), ("StreetDressing", StreetDressingInstall.Verify),
                                                                       ("Hydroponics", HydroponicsPass.Verify), ("TrainingRange", TrainingRangeInstall.Verify) })
            {
                string r;
                try { r = fn(); } catch (Exception e) { r = "THREW " + e.Message; }
                outs.Add(name + ": " + (r.Length > 1500 ? r.Substring(0, 1500) + "…" : r));
                EditorSceneManager.OpenScene(ScenePath);
            }
            File.WriteAllText(Path.Combine(Evidence, "other-verifies.txt"), string.Join("\n\n", outs));
            return "other verifies -> other-verifies.txt";
        }

        static string Rollback()
        {
            var log = new List<string>();
            foreach (var p in Enumerable.Reverse(rec.created)) { var t = All().FirstOrDefault(x => PathOf(x) == p); if (t) { UnityEngine.Object.DestroyImmediate(t.gameObject); log.Add("removed " + p); } }
            foreach (var kv in rec.active) foreach (var t in All().Where(x => PathOf(x) == kv.Key).ToList()) t.gameObject.SetActive(kv.Value);   // sibling paths can repeat (two hill-foot benches)
            // the 3 Oct bastion models (with the pintle gun) back from art/turret_bench_20261004/previous
            var prev = Path.Combine(ArtDir, "previous");
            foreach (var f in Directory.GetFiles(prev, "WL_GateBastion*.glb").Concat(Directory.GetFiles(prev, "bastion_*.json")))
                File.Copy(f, Path.Combine(Repo, "unity/AthenHill", WLModels, Path.GetFileName(f)), true);
            AssetDatabase.Refresh();
            log.Add(EditBastion("WL_GateBastionS", false)); log.Add(EditBastion("WL_GateBastionN", false));
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            rec = new Rec();
            return "rolled back (set GATE_GUN = True in author_life.py to author the gun again): " + string.Join("; ", log);
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = (i >= 0 && i + 1 < args.Length ? args[i + 1] : "survey").Split(',');
            try
            {
                EditorSceneManager.OpenScene(ScenePath);
                rec = Load();
                bool dirty = false;
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string r = parts[0] switch
                    {
                        "survey" => Survey(), "assets" => Assets(), "bastions" => Bastions(), "benches" => Benches(),
                        "cameras" => Cameras(), "verify" => Verify(), "capture" => Capture(parts.Length > 1 ? parts[1] : ""),
                        "rollback" => Rollback(), "others" => Others(), _ => throw new Exception("unknown step " + st)
                    };
                    if (parts[0] == "benches" || parts[0] == "cameras" || parts[0] == "rollback") dirty = true;
                    rec.log.Add(DateTime.UtcNow.ToString("u") + " " + st + ": " + r);
                    Debug.Log("TurretBenchPass20261004 " + st + ": " + r);
                }
                if (dirty) { var scene = EditorSceneManager.GetActiveScene(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
                AssetDatabase.SaveAssets();
                Save();
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }   // scene not saved, record unchanged
        }
    }
}
