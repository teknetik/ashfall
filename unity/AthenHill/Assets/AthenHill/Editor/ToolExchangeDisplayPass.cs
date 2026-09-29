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
    // One-time, recoverable operation for task t_3513ba55 (29 Sep 2026): installs the reviewed Tool Exchange display and
    // shutter-fittings package (t_3751e0fd) beside the accepted revision 04 shell. Editor-only; refuses to overwrite anything.
    // Scope: the street-facing recessed display and the rolling shutter only. Shell, door, sign, clerestory, colliders untouched.
    public static class ToolExchangeDisplayPass
    {
        public const string Folder = "Assets/AthenHill/Art/Phase1/ToolExchange/Display20260929";
        const string PrefabPath = Folder + "/ToolExchangeDisplay.prefab";
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string BuildingName = "tool_exchange";
        const string InstanceName = "Tool Exchange display and shutter";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/quality_20260929/tool-exchange-display");
        static string Evidence => Path.Combine(Repo, "unity/evidence/tool-exchange/20260929");
        // Revision 04 renderers superseded by the package: opaque near-black panes + dark recess, old guide rails, old lift handles. Disabled, never deleted.
        static readonly string[] RetiredPrefixes =
        {
            "tool_exchange Recessed tool display dark recess", "tool_exchange Recessed tool display glass",
            "tool_exchange Shutter guide rail", "tool_exchange Shutter lift handle"
        };
        // Parts that need no shadow casting: transparent film, and cm-scale parts whose shadow adds cost but no readable contact.
        static readonly HashSet<string> NoShadowCaster = new HashSet<string> { "TE_DisplayGlazing" };
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        static Vector3 V(JToken a) => new Vector3((float)a[0], (float)a[1], (float)a[2]);
        static void Write(string name, object data) { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented)); }
        static string Sha(string path) { using (var sha = System.Security.Cryptography.SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }

        static void OpenScene()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        static GameObject Building()
        {
            var b = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include).FirstOrDefault(t => t.name == BuildingName && t.GetComponentsInChildren<MeshRenderer>(true).Length > 100);
            if (!b) throw new InvalidOperationException("Revision 04 tool_exchange building instance not found.");
            return b.gameObject;
        }

        static IEnumerable<MeshRenderer> RetiredRenderers(GameObject building) =>
            building.GetComponentsInChildren<MeshRenderer>(true).Where(r => RetiredPrefixes.Any(p => r.name.StartsWith(p, StringComparison.Ordinal)));

        // Every collider that can affect the frontage: the building's own proxies and the world's shop_e_03 proxies.
        static object[] ColliderState(GameObject building)
        {
            var list = building.GetComponentsInChildren<Collider>(true).Concat(Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Where(c => c.name.StartsWith("COL_BLD_shop_e_03"))).Distinct();
            return list.OrderBy(c => c.transform.GetHierarchyPath(), StringComparer.Ordinal).Select(c => (object)new
            {
                path = c.transform.GetHierarchyPath(), type = c.GetType().Name, c.enabled, active = c.gameObject.activeInHierarchy,
                center = A(c.bounds.center), size = A(c.bounds.size)
            }).ToArray();
        }
        static string GetHierarchyPath(this Transform t) => t.parent ? t.parent.GetHierarchyPath() + "/" + t.name : t.name;

        public static void PrepareBatch() => Prepare();
        public static void InstallBatch() => Install();
        public static void VerifyBatch() => Verify();

        [MenuItem("Athen Hill/Phase 1/Prepare Tool Exchange display")]
        public static void Prepare()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            if (Directory.Exists(Folder)) throw new InvalidOperationException("Tool Exchange display assets already exist; review, never overwrite: " + Folder);
            var interchange = JObject.Parse(File.ReadAllText(Path.Combine(Source, "exports/interchange/te-meshes-v1.json")));
            var handoff = JObject.Parse(File.ReadAllText(Path.Combine(Source, "handoff.json")));
            var materialDoc = JObject.Parse(File.ReadAllText(Path.Combine(Source, "materials.json")));
            var parts = (JArray)interchange["parts"];
            var bySlot = ((JArray)materialDoc["materials"]).ToDictionary(m => (string)m["slot"]);
            var pivots = ((JArray)handoff["parts"]).ToDictionary(p => (string)p["part"], p => V(p["pivotUnityLocalToBuilding"]));
            foreach (var p in parts)
            {
                var v = (JArray)p["vertices"]; var n = (JArray)p["normals"]; var uv = (JArray)p["uv0"];
                if (v.Count == 0 || n.Count != v.Count || uv.Count != v.Count) throw new InvalidDataException("Invalid buffers: " + p["name"]);
                if (!pivots.ContainsKey((string)p["name"])) throw new InvalidDataException("No handoff pivot for " + p["name"]);
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
            foreach (var slot in parts.SelectMany(p => ((JArray)p["submeshes"]).Select(s => (string)s["material"])).Distinct().OrderBy(s => s)) materials[slot] = MakeMaterial(bySlot[slot], textureLog);
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
                foreach (var p in parts)
                {
                    string name = (string)p["name"];
                    var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                    go.transform.localPosition = pivots[name]; go.transform.localRotation = Quaternion.identity; go.transform.localScale = Vector3.one;
                    go.AddComponent<MeshFilter>().sharedMesh = meshes[name];
                    var r = go.AddComponent<MeshRenderer>();
                    r.sharedMaterials = ((JArray)p["submeshes"]).Select(s => materials[(string)s["material"]]).ToArray();
                    bool glazing = NoShadowCaster.Contains(name);
                    r.shadowCastingMode = glazing ? ShadowCastingMode.Off : ShadowCastingMode.On; r.receiveShadows = !glazing;
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally { Object.DestroyImmediate(root); }
            AssetDatabase.SaveAssets();
            Write("display-prepared.json", new
            {
                utc = DateTime.UtcNow, source = Source, prefab = PrefabPath, parts = parts.Count, materials = materials.Count,
                triangles = parts.Sum(p => ((JArray)p["submeshes"]).Sum(s => ((JArray)s["triangles"]).Count / 3)),
                textures = textureLog, conversion = "A-space X reflected, winding reversed, tangents regenerated from UV0 + normals; part pivots from handoff pivotUnityLocalToBuilding; scale 1",
                status = "Prepared assets only; not installed, not accepted"
            });
        }

        static Material MakeMaterial(JToken entry, List<object> log)
        {
            string name = (string)entry["unityMaterialName"], path = Folder + "/Materials/" + name + ".mat";
            bool glass = (string)entry["slot"] == "Glass";
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name, enableInstancing = true };
            m.SetFloat("_WorkflowMode", 1); m.SetFloat("_SmoothnessTextureChannel", 0);
            m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BaseMap", Tex((string)entry["baseMap"]["file"], true, false, glass, log));
            m.SetTexture("_BumpMap", Tex((string)entry["bumpMap"]["file"], false, true, false, log)); m.SetFloat("_BumpScale", 1); m.EnableKeyword("_NORMALMAP");
            // R = metallic, A = smoothness (already 1 - roughness). Scalars must be 1 when a map is bound.
            m.SetTexture("_MetallicGlossMap", Tex((string)entry["metallicGlossMap"]["file"], false, false, false, log)); m.SetFloat("_Metallic", 1); m.SetFloat("_Smoothness", 1); m.EnableKeyword("_METALLICSPECGLOSSMAP");
            if (glass)
            {
                // Transparent dust film: alpha blend, no depth write, queue after opaque, no shadow pass, no shadow reception.
                m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetFloat("_ZWrite", 0);
                m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ReceiveShadows", 0); m.SetFloat("_SpecularHighlights", 1); m.SetFloat("_EnvironmentReflections", 1);
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.EnableKeyword("_RECEIVE_SHADOWS_OFF"); m.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = (int)RenderQueue.Transparent;
                m.SetShaderPassEnabled("ShadowCaster", false); m.SetShaderPassEnabled("DepthOnly", false); m.SetShaderPassEnabled("DepthNormals", false);
            }
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static readonly Dictionary<string, Texture2D> Cache = new Dictionary<string, Texture2D>();
        static readonly HashSet<string> LoggedPaths = new HashSet<string>();
        static Texture2D Tex(string relative, bool srgb, bool normal, bool alphaIsTransparency, List<object> log)
        {
            string source = Path.Combine(Source, relative), path = Folder + "/Textures/" + Path.GetFileName(relative);
            string key = path + "|" + srgb + "|" + normal;
            if (Cache.TryGetValue(key, out var cached)) return cached;
            if (!File.Exists(source)) throw new FileNotFoundException(source);
            if (!File.Exists(path)) { File.Copy(source, path); AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport); }
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = alphaIsTransparency;
            importer.GetSourceTextureWidthAndHeight(out int w, out int h);
            importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(w, h));
            importer.npotScale = TextureImporterNPOTScale.None; importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
            importer.wrapMode = TextureWrapMode.Repeat; importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.crunchedCompression = false;
            importer.SaveAndReimport();
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!t) throw new InvalidOperationException("Texture failed to import: " + path);
            if (LoggedPaths.Add(path)) log.Add(new { path, source, width = w, height = h, srgb, normalMap = normal, alphaIsTransparency, format = importer.GetAutomaticFormat("Standalone").ToString() });
            Cache[key] = t; return t;
        }

        [MenuItem("Athen Hill/Phase 1/Install Tool Exchange display")]
        public static void Install()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current scene edits first.");
            if (GameObject.Find(InstanceName)) throw new InvalidOperationException("Tool Exchange display already installed; preserve edits.");
            var building = Building();
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath); if (!prefab) throw new InvalidOperationException("Run Prepare first.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); if (!chunks) throw new InvalidOperationException("Missing render-source controller.");
            var bt = building.transform;
            if (Vector3.Distance(bt.position, new Vector3(-20.6f, 0.5f, 9f)) > .01f || Mathf.Abs(Mathf.DeltaAngle(bt.eulerAngles.y, 90f)) > .01f || bt.lossyScale != Vector3.one)
                throw new InvalidOperationException("Revision 04 building is not at (-20.6, 0.5, 9) yaw 90 scale 1; the handoff pivots would not apply.");
            var collidersBefore = ColliderState(building);
            Write("colliders-before.json", collidersBefore);
            string backup = Path.Combine(Evidence, "rollback/before-tool-exchange-display-saved-by-install.unity");
            Directory.CreateDirectory(Path.GetDirectoryName(backup));
            if (File.Exists(backup) || !EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot create unique recovery scene copy.");
            chunks.ShowSources(true);
            var retired = RetiredRenderers(building).ToArray();
            if (retired.Length != 7) throw new InvalidOperationException("Expected 7 superseded renderers, found " + retired.Length + ": " + string.Join(", ", retired.Select(r => r.name)));
            foreach (var r in retired) { Undo.RecordObject(r, "Retain revision 04 display/shutter"); r.enabled = false; }
            // Scene-root sibling of the building, sharing its pose; live renderers, not a chunk source (glass must stay transparent and separate).
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            instance.name = InstanceName;
            instance.transform.SetPositionAndRotation(bt.position, bt.rotation); instance.transform.localScale = Vector3.one;
            Undo.RegisterCreatedObjectUndo(instance, "Install Tool Exchange display");
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene);
            StaticRenderChunksEditor.Rebuild(chunks); // saves the scene
            Write("display-installed.json", new
            {
                utc = DateTime.UtcNow, prefab = PrefabPath, buildingPosition = A(bt.position), buildingYaw = bt.eulerAngles.y,
                instanceWorldPosition = A(instance.transform.position), instanceYaw = instance.transform.eulerAngles.y, instanceScale = A(instance.transform.lossyScale),
                retiredRenderers = retired.Select(r => r.name).ToArray(), retiredTriangles = retired.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3),
                colliderCount = collidersBefore.Length, chunkFingerprint = chunks.sourceFingerprint,
                status = "Needs save/reopen verification, native capture, route and performance checks"
            });
        }

        [MenuItem("Athen Hill/Phase 1/Verify Tool Exchange display (reopens scene)")]
        public static void Verify()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); // reopen from disk
            var building = Building(); var instance = GameObject.Find(InstanceName);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var before = JArray.Parse(File.ReadAllText(Path.Combine(Evidence, "colliders-before.json")));
            var after = JArray.Parse(JsonConvert.SerializeObject(ColliderState(building)));
            bool collidersSame = before.Count == after.Count && before.Zip(after, (a, b) => JToken.DeepEquals(a, b)).All(x => x);
            var retired = RetiredRenderers(building).ToArray();
            var dressing = instance ? instance.GetComponentsInChildren<MeshRenderer>(true) : new MeshRenderer[0];
            var lossy = dressing.Select(r => r.transform.lossyScale).ToArray();
            var b = new Bounds(); bool first = true;
            foreach (var r in dressing) { if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
            var glass = dressing.FirstOrDefault(r => r.name == "TE_DisplayGlazing");
            var vex = Object.FindObjectsByType<NpcAgent>().Where(n => n.name == "npc_vex").Select(n => A(n.transform.position)).FirstOrDefault();
            var report = new
            {
                utc = DateTime.UtcNow, reopenedFromDisk = true, scenePath = UnityEngine.SceneManagement.SceneManager.GetActiveScene().path, dressingPresent = instance != null,
                dressingPrefab = instance ? (PrefabUtility.GetCorrespondingObjectFromSource(instance) ? AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(instance)) : "(unlinked)") : null,
                dressingRenderers = dressing.Length, dressingTriangles = dressing.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3),
                dressingScaleAllOne = lossy.All(s => Mathf.Abs(s.x - 1) < 1e-4f && Mathf.Abs(s.y - 1) < 1e-4f && Mathf.Abs(s.z - 1) < 1e-4f),
                dressingHasColliders = instance && instance.GetComponentsInChildren<Collider>(true).Length > 0,
                dressingBounds = new { min = A(b.min), max = A(b.max) },
                glazingMaterial = glass ? glass.sharedMaterial.name + " queue " + glass.sharedMaterial.renderQueue + " surface " + glass.sharedMaterial.GetFloat("_Surface") + " zwrite " + glass.sharedMaterial.GetFloat("_ZWrite") : null,
                retiredRenderers = retired.Length, retiredStillEnabled = retired.Count(r => r.enabled),
                collidersUnchanged = collidersSame, colliderStateCount = after.Count, sceneColliderCount = Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Length,
                chunkFingerprintMatches = chunks && !chunks.editingSources && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks), chunkSourcesShown = chunks ? chunks.editingSources : (bool?)null,
                actorAnimationCount = Object.FindObjectsByType<ActorAnimation>().Length, vexRoot = vex,
                sceneSha256 = Sha(Path.Combine(Repo, "unity/AthenHill/" + ScenePath))
            };
            Write("display-verify-saved-scene.json", report);
            Debug.Log("ToolExchangeDisplayPass.Verify " + JsonConvert.SerializeObject(report));
        }
    }
}
#endif
