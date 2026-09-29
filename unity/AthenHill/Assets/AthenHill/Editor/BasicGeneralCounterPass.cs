#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // One-time, recoverable operation for task t_7f421ed1 (29 Sep 2026): installs the reviewed Basic General
    // counter/stock dressing beside the existing authored frontage. Editor-only; refuses to overwrite anything.
    public static class BasicGeneralCounterPass
    {
        public const string Folder = "Assets/AthenHill/Art/Phase1/BasicGeneral/Counter20260929";
        const string PrefabPath = Folder + "/BasicGeneralCounterDressing.prefab";
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string FrontageName = "Basic General authored frontage";
        const string InstanceName = "Basic General counter dressing";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/quality_20260929/basic-general-counter");
        static string Evidence => Path.Combine(Repo, "unity/evidence/basic-general/20260929");
        static readonly string[] RetiredPrefixes =
        {
            "Sealed goods tin", "Tin rolled lid", "Tin label", "Stock exact label", "Stock shelf", "Counter repair fascia",
            "Counter inset plate", "Counter plate rivet", "Service ledge", "Counter working lip", "Counter grip paint loss"
        };
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        static Vector3 V(JToken a) => new Vector3((float)a[0], (float)a[1], (float)a[2]);
        static string Norm(string s) => s.Replace(' ', '_');
        static void Write(string name, object data) { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented)); }

        static void OpenScene()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        // Mira's supplied root is also a landmark used by the route checks.
        static IEnumerable<Renderer> RetiredRenderers(GameObject frontage) =>
            frontage.GetComponentsInChildren<MeshRenderer>(true).Where(r => RetiredPrefixes.Any(p => r.name.StartsWith(Norm(p), StringComparison.Ordinal)));

        public static void PrepareBatch() => Prepare();
        public static void InstallBatch() => Install();
        public static void VerifyBatch() => Verify();

        // Recorded amendment: the first Install added the dressing to the chunk source roots, which baked LOD0+LOD1 together.
        [MenuItem("Athen Hill/Phase 1/Basic General counter: use live LOD renderers")]
        public static void SwitchToLiveLods()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current scene edits first.");
            var instance = GameObject.Find(InstanceName); var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!instance || !chunks) throw new InvalidOperationException("Install first.");
            if (!chunks.sourceRoots.Contains(instance.transform)) throw new InvalidOperationException("Already live.");
            string backup = Path.Combine(Evidence, "rollback/after-first-install-chunked-lods.unity");
            if (File.Exists(backup) || !EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot create unique recovery scene copy.");
            chunks.ShowSources(true);
            chunks.sourceRoots = chunks.sourceRoots.Where(t => t && t != instance.transform).ToArray(); EditorUtility.SetDirty(chunks);
            EditorSceneManager.MarkSceneDirty(scene);
            StaticRenderChunksEditor.Rebuild(chunks);
            Write("counter-live-lods.json", new { utc = DateTime.UtcNow, reason = "Chunk rebuild merged LOD0 and LOD1 and ignored the LODGroup", sourceRootsRemaining = chunks.sourceRoots.Length, chunkFingerprint = chunks.sourceFingerprint });
        }
        public static void SwitchToLiveLodsBatch() => SwitchToLiveLods();

        [MenuItem("Athen Hill/Phase 1/Prepare Basic General counter dressing")]
        public static void Prepare()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            if (Directory.Exists(Folder)) throw new InvalidOperationException("Counter dressing assets already exist; review, never overwrite: " + Folder);
            var interchange = JObject.Parse(File.ReadAllText(Path.Combine(Source, "exports/interchange/bgc-meshes-v1.json")));
            var handoff = JObject.Parse(File.ReadAllText(Path.Combine(Source, "handoff.json")));
            var materialDoc = JObject.Parse(File.ReadAllText(Path.Combine(Source, "materials.json")));
            var parts = (JArray)interchange["parts"];
            var bySlot = ((JArray)materialDoc["materials"]).ToDictionary(m => (string)m["slot"]);
            var pivots = ((JArray)handoff["parts"]).ToDictionary(p => (string)p["part"], p => V(p["pivotUnityLocalToBuilding"]));
            foreach (var p in parts)
            {
                var v = (JArray)p["vertices"]; var n = (JArray)p["normals"]; var uv = (JArray)p["uv0"];
                if (v.Count == 0 || n.Count != v.Count || uv.Count != v.Count) throw new InvalidDataException("Invalid buffers: " + p["name"]);
                foreach (var sub in (JArray)p["submeshes"])
                {
                    var t = (JArray)sub["triangles"];
                    if (t.Count % 3 != 0 || t.Any(i => (int)i < 0 || (int)i >= v.Count)) throw new InvalidDataException("Invalid indices: " + p["name"]);
                    if (!bySlot.ContainsKey((string)sub["material"])) throw new InvalidDataException("Missing material entry " + sub["material"]);
                }
            }
            foreach (var d in new[] { "Meshes", "Materials", "Textures" }) Directory.CreateDirectory(Folder + "/" + d);
            AssetDatabase.Refresh();
            var materials = new Dictionary<string, Material>();
            var textureLog = new List<object>();
            var usedSlots = parts.SelectMany(p => ((JArray)p["submeshes"]).Select(s => (string)s["material"])).Distinct().OrderBy(s => s).ToArray();
            foreach (var slot in usedSlots) materials[slot] = MakeMaterial(bySlot[slot], textureLog);
            var meshes = new Dictionary<string, Mesh>();
            foreach (var p in parts)
            {
                string name = (string)p["name"];
                var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
                // A-space -> Unity: reflect X and reverse winding (handoff coordinate convention).
                mesh.vertices = p["vertices"].Select(a => new Vector3(-(float)a[0], (float)a[1], (float)a[2])).ToArray();
                mesh.normals = p["normals"].Select(a => new Vector3(-(float)a[0], (float)a[1], (float)a[2])).ToArray();
                mesh.uv = p["uv0"].Select(a => new Vector2((float)a[0], (float)a[1])).ToArray();
                var subs = ((JArray)p["submeshes"]).ToArray();
                mesh.subMeshCount = subs.Length;
                for (int i = 0; i < subs.Length; i++)
                {
                    var idx = subs[i]["triangles"].Select(x => (int)x).ToArray();
                    for (int k = 0; k < idx.Length; k += 3) { int t = idx[k + 1]; idx[k + 1] = idx[k + 2]; idx[k + 2] = t; }
                    mesh.SetTriangles(idx, i);
                }
                mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, Folder + "/Meshes/" + name + ".asset"); meshes[name] = mesh;
            }
            var root = new GameObject(InstanceName);
            try
            {
                foreach (var baseName in new[] { "BGC_Counter", "BGC_ShelfBay_L", "BGC_ShelfBay_R", "BGC_HookRail_L", "BGC_HookRail_R", "BGC_CounterProps" })
                {
                    var pivot = pivots[baseName]; // building-local, already X-reflected by the handoff
                    var lod0 = Part(root.transform, baseName, meshes[baseName], parts, materials, pivot);
                    if (meshes.TryGetValue(baseName + "_LOD1", out var m1))
                    {
                        var lod1 = Part(root.transform, baseName + "_LOD1", m1, parts, materials, pivot);
                        var sub = new GameObject(baseName + " (LOD group)"); sub.transform.SetParent(root.transform, false);
                        lod0.transform.SetParent(sub.transform, false); lod1.transform.SetParent(sub.transform, false);
                        var group = sub.AddComponent<LODGroup>();
                        var size = Mathf.Max(lod0.GetComponent<MeshRenderer>().bounds.size.x, lod0.GetComponent<MeshRenderer>().bounds.size.y, lod0.GetComponent<MeshRenderer>().bounds.size.z);
                        // Relative screen height at a 50 degree vertical FOV: size / (2 d tan 25). LOD1 from ~5 m (props ~6 m), cull ~110 m.
                        float Height(float d) => size / (2 * d * Mathf.Tan(25 * Mathf.Deg2Rad));
                        float switchAt = baseName == "BGC_CounterProps" ? 6 : 5;
                        group.SetLODs(new[] { new LOD(Height(switchAt), new Renderer[] { lod0.GetComponent<MeshRenderer>() }), new LOD(Height(110), new Renderer[] { lod1.GetComponent<MeshRenderer>() }) });
                        group.fadeMode = LODFadeMode.None; group.RecalculateBounds();
                    }
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally { Object.DestroyImmediate(root); }
            AssetDatabase.SaveAssets();
            Write("counter-prepared.json", new
            {
                utc = DateTime.UtcNow, source = Source, prefab = PrefabPath, parts = parts.Count, materials = materials.Count,
                trianglesLod0 = parts.Where(p => !((string)p["name"]).EndsWith("_LOD1")).Sum(p => ((JArray)p["submeshes"]).Sum(s => ((JArray)s["triangles"]).Count / 3)),
                textures = textureLog, conversion = "A-space X reflected, winding reversed, tangents regenerated from UV0 + normals; part pivots from handoff pivotUnityLocalToBuilding; scale 1",
                status = "Prepared assets only; not installed, not accepted"
            });
        }

        static GameObject Part(Transform parent, string name, Mesh mesh, JArray parts, Dictionary<string, Material> materials, Vector3 pivot)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.localPosition = pivot; go.transform.localRotation = Quaternion.identity; go.transform.localScale = Vector3.one;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>();
            var subs = (JArray)parts.First(p => (string)p["name"] == name)["submeshes"];
            r.sharedMaterials = subs.Select(s => materials[(string)s["material"]]).ToArray();
            r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true;
            return go;
        }

        static Material MakeMaterial(JToken entry, List<object> log)
        {
            string name = (string)entry["unityMaterialName"], path = Folder + "/Materials/" + name + ".mat";
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name, enableInstancing = true };
            m.SetFloat("_WorkflowMode", 1); m.SetFloat("_SmoothnessTextureChannel", 0);
            m.SetColor("_BaseColor", Color.white);
            var albedo = Tex((string)entry["baseMap"]["file"], true, false, log);
            var normal = Tex((string)entry["bumpMap"]["file"], false, true, log);
            var packed = Tex((string)entry["metallicGlossMap"]["file"], false, false, log);
            m.SetTexture("_BaseMap", albedo);
            m.SetTexture("_BumpMap", normal); m.SetFloat("_BumpScale", 1); m.EnableKeyword("_NORMALMAP");
            // R = metallic, A = smoothness (already 1 - roughness). Scalars must be 1 when a map is bound.
            m.SetTexture("_MetallicGlossMap", packed); m.SetFloat("_Metallic", 1); m.SetFloat("_Smoothness", 1); m.EnableKeyword("_METALLICSPECGLOSSMAP");
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static readonly Dictionary<string, Texture2D> Cache = new Dictionary<string, Texture2D>();
        static readonly HashSet<string> LoggedPaths = new HashSet<string>();
        static Texture2D Tex(string relative, bool srgb, bool normal, List<object> log)
        {
            string source = Path.Combine(Source, relative), path = Folder + "/Textures/" + Path.GetFileName(relative);
            string key = path + "|" + srgb + "|" + normal;
            if (Cache.TryGetValue(key, out var cached)) return cached;
            if (!File.Exists(source)) throw new FileNotFoundException(source);
            if (!File.Exists(path)) { File.Copy(source, path); AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport); }
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = false;
            importer.GetSourceTextureWidthAndHeight(out int w, out int h);
            importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(w, h));
            importer.npotScale = TextureImporterNPOTScale.None; importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
            importer.wrapMode = TextureWrapMode.Repeat; importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.crunchedCompression = false;
            importer.SaveAndReimport();
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!t) throw new InvalidOperationException("Texture failed to import: " + path);
            if (LoggedPaths.Add(path)) log.Add(new { path, source, width = w, height = h, srgb, normalMap = normal, format = importer.GetAutomaticFormat("Standalone").ToString() });
            Cache[key] = t; return t;
        }

        [MenuItem("Athen Hill/Phase 1/Install Basic General counter dressing")]
        public static void Install()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current scene edits first.");
            if (GameObject.Find(InstanceName)) throw new InvalidOperationException("Counter dressing already installed; preserve edits.");
            var frontage = GameObject.Find(FrontageName); if (!frontage) throw new InvalidOperationException("Authored frontage missing.");
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath); if (!prefab) throw new InvalidOperationException("Run Prepare first.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); if (!chunks) throw new InvalidOperationException("Missing render-source controller.");
            var frozen = JArray.Parse(File.ReadAllText(Path.Combine(Repo, "art/quality_20260909/basic-general/preserved-colliders.json")));
            var colliders = frozen.Select(row =>
            {
                var go = GameObject.Find((string)row["path"]); var c = go ? go.GetComponent<Collider>() : null;
                if (!c || !c.enabled || Vector3.Distance(c.bounds.center, V(row["center"])) > .002f || Vector3.Distance(c.bounds.size, V(row["size"])) > .002f) throw new InvalidOperationException("Frozen gameplay collider changed: " + row["path"]);
                return c;
            }).ToArray();
            var before = colliders.Select(c => new { id = GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(), c.name, center = A(c.bounds.center), size = A(c.bounds.size), c.enabled }).ToArray();
            string backup = Path.Combine(Evidence, "rollback/before-basic-general-counter-saved-by-install.unity");
            Directory.CreateDirectory(Path.GetDirectoryName(backup));
            if (File.Exists(backup) || !EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot create unique recovery scene copy.");
            chunks.ShowSources(true);
            var retired = RetiredRenderers(frontage).ToArray();
            if (retired.Length != 90) throw new InvalidOperationException("Expected 90 superseded renderers, found " + retired.Length);
            foreach (var r in retired) { Undo.RecordObject(r, "Retain previous Basic General stock"); r.enabled = false; }
            // Scene-root sibling of the frontage (like the frontage itself), added to the render-source roots.
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            instance.name = InstanceName;
            instance.transform.position = frontage.transform.position; instance.transform.rotation = Quaternion.identity; instance.transform.localScale = Vector3.one;
            Undo.RegisterCreatedObjectUndo(instance, "Install Basic General counter dressing");
            // Amended 29 Sep 2026 after the first install: the dressing is NOT a chunk source. Chunking merges LOD0 and LOD1
            // into one mesh and drops the LODGroup, so the dressing stays as live LODGroup renderers (see SwitchToLiveLods).
            // Only the 90 retired renderers below change the chunk sources.
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene);
            StaticRenderChunksEditor.Rebuild(chunks); // saves the scene
            Write("counter-installed.json", new
            {
                utc = DateTime.UtcNow, prefab = PrefabPath, frontagePosition = A(frontage.transform.position), instanceParent = instance.transform.parent ? instance.transform.parent.name : "(scene root)",
                instanceWorldPosition = A(instance.transform.position), instanceScale = A(instance.transform.lossyScale),
                retiredRenderers = retired.Length, retiredTriangles = retired.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3),
                preservedColliders = before, chunkFingerprint = chunks.sourceFingerprint, status = "Needs save/reopen verification, native capture, route and performance checks"
            });
        }

        [MenuItem("Athen Hill/Phase 1/Verify Basic General counter dressing (reopens scene)")]
        public static void Verify()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); // reopen from disk
            var frontage = GameObject.Find(FrontageName); var instance = GameObject.Find(InstanceName);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var frozen = JArray.Parse(File.ReadAllText(Path.Combine(Repo, "art/quality_20260909/basic-general/preserved-colliders.json")));
            var colliderReport = frozen.Select(row =>
            {
                var go = GameObject.Find((string)row["path"]); var c = go ? go.GetComponent<Collider>() : null;
                bool ok = c && c.enabled && Vector3.Distance(c.bounds.center, V(row["center"])) <= .002f && Vector3.Distance(c.bounds.size, V(row["size"])) <= .002f;
                return new { path = (string)row["path"], ok };
            }).ToArray();
            var retired = frontage ? RetiredRenderers(frontage).ToArray() : new Renderer[0];
            var dressing = instance ? instance.GetComponentsInChildren<MeshRenderer>(true) : new MeshRenderer[0];
            var lossy = dressing.Select(r => r.transform.lossyScale).ToArray();
            var npcs = Object.FindObjectsByType<ActorAnimation>();
            var miraRoot = Object.FindObjectsByType<NpcAgent>().Select(n => new { n.name, position = A(n.transform.position) }).ToArray();
            var b = new Bounds(); bool first = true;
            foreach (var r in dressing) { if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
            var report = new
            {
                utc = DateTime.UtcNow, reopenedFromDisk = true, scenePath = SceneManager_Path(), frontagePresent = frontage != null, dressingPresent = instance != null,
                dressingPrefab = instance ? PrefabUtility.GetCorrespondingObjectFromSource(instance) ? AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(instance)) : "(unlinked)" : null,
                dressingRenderers = dressing.Length, dressingTriangles = dressing.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3),
                dressingLod0Triangles = dressing.Where(r => !r.name.EndsWith("_LOD1")).Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3),
                dressingScaleAllOne = lossy.All(s => Mathf.Abs(s.x - 1) < 1e-4f && Mathf.Abs(s.y - 1) < 1e-4f && Mathf.Abs(s.z - 1) < 1e-4f),
                dressingHasColliders = instance && instance.GetComponentsInChildren<Collider>(true).Length > 0,
                dressingBounds = new { min = A(b.min), max = A(b.max) },
                retiredRenderers = retired.Length, retiredStillEnabled = retired.Count(r => r.enabled),
                colliders = colliderReport, collidersAllPreserved = colliderReport.All(c => c.ok), colliderCount = Object.FindObjectsByType<Collider>().Length,
                chunkFingerprintMatches = chunks && !chunks.editingSources && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks), chunkSourcesShown = chunks ? chunks.editingSources : (bool?)null,
                actorAnimationCount = npcs.Length, npcAgents = miraRoot,
                sceneSha256 = Sha(Path.Combine(Repo, "unity/AthenHill/" + ScenePath))
            };
            Write("counter-verify-saved-scene.json", report);
            Debug.Log("BasicGeneralCounterPass.Verify " + JsonConvert.SerializeObject(report));
        }

        static string SceneManager_Path() => UnityEngine.SceneManagement.SceneManager.GetActiveScene().path;
        static string Sha(string path) { using (var sha = System.Security.Cryptography.SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }
    }
}
#endif
