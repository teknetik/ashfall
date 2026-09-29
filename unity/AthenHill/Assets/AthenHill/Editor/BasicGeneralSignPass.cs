#if UNITY_EDITOR
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
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // One-time, recoverable operation for task t_196932d9 (29 Sep 2026): installs the user-supplied Meshy "Neon Command Sign"
    // (as a low-poly front plate with baked 1.24M-triangle detail) over the Basic General frontage. Editor-only; refuses to overwrite.
    // Scope: the five superseded sign renderers only (enamel face, old lettering, OPEN housing/face/lettering). Frontage, counter,
    // colliders, Mira, interaction and trade data are untouched. Retired renderers are disabled, never deleted.
    public static class BasicGeneralSignPass
    {
        public const string Folder = "Assets/AthenHill/Art/Phase1/BasicGeneral/Sign20260929";
        const string PrefabPath = Folder + "/BasicGeneralNeonSign.prefab";
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string FrontageName = "Basic General authored frontage";
        const string InstanceName = "Basic General neon sign";
        // Uniform fit. Source is 1.90 x 0.614 x 0.121 m; x1.3 gives 2.47 x 0.80 x 0.16 m: it hangs between the 2.35 m headroom line and the awning front edge (3.13 m).
        const float Scale = 1.3f;
        // Back plane rests on the front face of Sign_backing_frame (z 16.862); centre 2.72 m: underside 2.32 m, top 3.12 m just under the awning edge.
        static readonly Vector3 Position = new Vector3(8.0f, 2.72f, 16.862f + 0.0612f * Scale);
        // Meshy's neon glow is restrained: linear HDR multiplier on the baked emission map (letters, OPEN plate, cyan traces).
        const float EmissionIntensity = 0.55f;
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "meshy/basic-general-sign-20260929");
        static string Evidence => Path.Combine(Repo, "unity/evidence/basic-general-sign/20260929");
        static readonly string[] Retired = { "BASIC_GENERAL_sign", "Sign_enamel_face", "Open_indicator_housing", "Open_indicator_face", "Open_lettering" };
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        static Vector3 V(JToken a) => new Vector3((float)a[0], (float)a[1], (float)a[2]);
        static void Write(string name, object data) { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented)); }
        static string Sha(string path) { using (var sha = System.Security.Cryptography.SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(); }

        static void OpenScene()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            if (EditorSceneManager.GetActiveScene().path != ScenePath) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        static IEnumerable<MeshRenderer> RetiredRenderers(GameObject frontage) =>
            frontage.GetComponentsInChildren<MeshRenderer>(true).Where(r => Retired.Contains(r.name));

        static object[] ColliderState(GameObject frontage) =>
            frontage.GetComponentsInChildren<Collider>(true).OrderBy(c => HPath(c.transform), StringComparer.Ordinal)
                .Select(c => (object)new { path = HPath(c.transform), type = c.GetType().Name, c.enabled, center = A(c.bounds.center), size = A(c.bounds.size) }).ToArray();
        static string HPath(Transform t) => t.parent ? HPath(t.parent) + "/" + t.name : t.name;

        public static void PrepareBatch() => Prepare();
        public static void InstallBatch() => Install();
        public static void VerifyBatch() => Verify();

        [MenuItem("Athen Hill/Phase 1/Prepare Basic General neon sign")]
        public static void Prepare()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            if (Directory.Exists(Folder)) throw new InvalidOperationException("Sign assets already exist; review, never overwrite: " + Folder);
            var doc = JObject.Parse(File.ReadAllText(Path_(Source, "baked/sign-mesh.json")));
            var v = (JArray)doc["vertices"]; var n = (JArray)doc["normals"]; var uv = (JArray)doc["uv0"]; var tri = (JArray)doc["triangles"];
            if (v.Count == 0 || n.Count != v.Count || uv.Count != v.Count || tri.Count % 3 != 0 || tri.Any(i => (int)i < 0 || (int)i >= v.Count)) throw new InvalidDataException("Invalid sign mesh buffers.");
            foreach (var d in new[] { "Meshes", "Materials", "Textures" }) Directory.CreateDirectory(Folder + "/" + d);
            AssetDatabase.Refresh();
            var log = new List<object>();
            var baseMap = Tex("sign_basecolor.png", true, false, log);
            var normalMap = Tex("sign_normal.png", false, true, log);
            var metalGloss = Tex("sign_metalgloss.png", false, false, log);
            var emission = Tex("sign_emission.png", true, false, log);

            var mesh = new Mesh { name = "BG_NeonSign", indexFormat = IndexFormat.UInt16 };
            // glTF (right handed, +Z front) -> Unity: reflect X, reverse winding.
            var verts = v.Select(a => new Vector3(-(float)a[0], (float)a[1], (float)a[2])).ToArray();
            var norms = n.Select(a => new Vector3(-(float)a[0], (float)a[1], (float)a[2]).normalized).ToArray();
            mesh.vertices = verts; mesh.normals = norms; mesh.uv = uv.Select(a => new Vector2((float)a[0], (float)a[1])).ToArray();
            var idx = tri.Select(x => (int)x).ToArray();
            for (int k = 0; k < idx.Length; k += 3) { int t = idx[k + 1]; idx[k + 1] = idx[k + 2]; idx[k + 2] = t; }
            mesh.SetTriangles(idx, 0);
            // Tangents by construction: the front plate has u along Unity -X and v along +Y; the side strips sample a flat texel.
            mesh.tangents = norms.Select(nn => Mathf.Abs(nn.z) > .99f ? new Vector4(-1, 0, 0, -1) : new Vector4(0, 0, nn.x > 0 || nn.y > 0 ? 1 : -1, 1)).ToArray();
            mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh, Folder + "/Meshes/BG_NeonSign.asset");

            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "BG_NeonSign", enableInstancing = true };
            m.SetFloat("_WorkflowMode", 1); m.SetFloat("_SmoothnessTextureChannel", 0);
            m.SetColor("_BaseColor", Color.white); m.SetTexture("_BaseMap", baseMap);
            m.SetTexture("_BumpMap", normalMap); m.SetFloat("_BumpScale", 1); m.EnableKeyword("_NORMALMAP");
            m.SetTexture("_MetallicGlossMap", metalGloss); m.SetFloat("_Metallic", 1); m.SetFloat("_Smoothness", 1); m.EnableKeyword("_METALLICSPECGLOSSMAP");
            m.SetTexture("_EmissionMap", emission); m.SetColor("_EmissionColor", Color.white * EmissionIntensity); m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
            AssetDatabase.CreateAsset(m, Folder + "/Materials/BG_NeonSign.mat");

            var root = new GameObject(InstanceName);
            try
            {
                var go = new GameObject("BG_NeonSign"); go.transform.SetParent(root.transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = m;
                r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true;
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally { Object.DestroyImmediate(root); }
            AssetDatabase.SaveAssets();
            Write("sign-prepared.json", new
            {
                utc = DateTime.UtcNow, prefab = PrefabPath, vertices = verts.Length, triangles = idx.Length / 3, bounds = new { center = A(mesh.bounds.center), size = A(mesh.bounds.size) },
                emissionIntensity = EmissionIntensity, textures = log,
                conversion = "glTF X reflected, winding reversed; tangents authored; front plate UV0 = orthographic front projection; source relief baked to normal/albedo/metal-gloss/emission",
                status = "Prepared assets only; not installed, not visually accepted"
            });
        }

        static string Path_(string a, string b) => System.IO.Path.Combine(a, b);

        static Texture2D Tex(string file, bool srgb, bool normal, List<object> log)
        {
            string source = Path_(Source, "baked/runtime/" + file), path = Folder + "/Textures/" + file;
            if (!File.Exists(source)) throw new FileNotFoundException(source);
            File.Copy(source, path);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = false;
            importer.GetSourceTextureWidthAndHeight(out int w, out int h);
            importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(w, h));
            importer.npotScale = TextureImporterNPOTScale.None; importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
            importer.wrapMode = TextureWrapMode.Clamp; importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.crunchedCompression = false;
            importer.SaveAndReimport();
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!t) throw new InvalidOperationException("Texture failed to import: " + path);
            log.Add(new { path, source, width = w, height = h, srgb, normalMap = normal, format = importer.GetAutomaticFormat("Standalone").ToString() });
            return t;
        }

        [MenuItem("Athen Hill/Phase 1/Install Basic General neon sign")]
        public static void Install()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current scene edits first.");
            if (GameObject.Find(InstanceName)) throw new InvalidOperationException("Sign already installed; preserve edits.");
            var frontage = GameObject.Find(FrontageName); if (!frontage) throw new InvalidOperationException("Authored frontage missing.");
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath); if (!prefab) throw new InvalidOperationException("Run Prepare first.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); if (!chunks) throw new InvalidOperationException("Missing render-source controller.");
            var collidersBefore = ColliderState(frontage);
            Write("colliders-before.json", collidersBefore);
            string backup = Path_(Evidence, "rollback/before-sign-saved-by-install.unity");
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
            if (File.Exists(backup) || !EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot create unique recovery scene copy.");
            chunks.ShowSources(true);
            var retired = RetiredRenderers(frontage).ToArray();
            if (retired.Length != Retired.Length) throw new InvalidOperationException("Expected " + Retired.Length + " superseded sign renderers, found " + retired.Length);
            foreach (var r in retired) { Undo.RecordObject(r, "Retain previous Basic General sign"); r.enabled = false; }
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            instance.name = InstanceName;
            instance.transform.SetPositionAndRotation(Position, Quaternion.identity); instance.transform.localScale = Vector3.one * Scale;
            Undo.RegisterCreatedObjectUndo(instance, "Install Basic General neon sign");
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene);
            StaticRenderChunksEditor.Rebuild(chunks); // saves the scene
            Write("sign-installed.json", new
            {
                utc = DateTime.UtcNow, prefab = PrefabPath, position = A(Position), uniformScale = Scale,
                retiredRenderers = retired.Select(r => r.name).ToArray(), retiredTriangles = retired.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3),
                colliderCount = collidersBefore.Length, chunkFingerprint = chunks.sourceFingerprint,
                status = "Needs save/reopen verification, native launch and visual review by Carl"
            });
        }

        [MenuItem("Athen Hill/Phase 1/Verify Basic General neon sign (reopens scene)")]
        public static void Verify()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); // reopen from disk
            var frontage = GameObject.Find(FrontageName); var instance = GameObject.Find(InstanceName);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var before = JArray.Parse(File.ReadAllText(Path_(Evidence, "colliders-before.json")));
            var after = JArray.Parse(JsonConvert.SerializeObject(ColliderState(frontage)));
            bool collidersSame = before.Count == after.Count && before.Zip(after, (a, b) => JToken.DeepEquals(a, b)).All(x => x);
            var frozen = JArray.Parse(File.ReadAllText(Path_(Repo, "art/quality_20260909/basic-general/preserved-colliders.json")));
            var frozenOk = frozen.Select(row => { var go = GameObject.Find((string)row["path"]); var c = go ? go.GetComponent<Collider>() : null; return c && c.enabled && Vector3.Distance(c.bounds.center, V(row["center"])) <= .002f && Vector3.Distance(c.bounds.size, V(row["size"])) <= .002f; }).ToArray();
            var retired = RetiredRenderers(frontage).ToArray();
            var rend = instance ? instance.GetComponentsInChildren<MeshRenderer>(true) : new MeshRenderer[0];
            var mat = rend.Length > 0 ? rend[0].sharedMaterial : null;
            var b = rend.Length > 0 ? rend[0].bounds : new Bounds();
            var mira = Object.FindObjectsByType<NpcAgent>().Select(n => new { n.name, position = A(n.transform.position) }).ToArray();
            var report = new
            {
                utc = DateTime.UtcNow, reopenedFromDisk = true, scenePath = UnityEngine.SceneManagement.SceneManager.GetActiveScene().path,
                signPresent = instance != null,
                signPrefab = instance ? (PrefabUtility.GetCorrespondingObjectFromSource(instance) ? AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(instance)) : "(unlinked)") : null,
                signLossyScale = instance ? A(instance.transform.lossyScale) : null,
                uniformScale = instance && Mathf.Approximately(instance.transform.lossyScale.x, instance.transform.lossyScale.y) && Mathf.Approximately(instance.transform.lossyScale.y, instance.transform.lossyScale.z),
                signBounds = new { min = A(b.min), max = A(b.max), size = A(b.size) }, signTriangles = rend.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3),
                signHasColliders = instance && instance.GetComponentsInChildren<Collider>(true).Length > 0,
                material = mat ? mat.name + " shader " + mat.shader.name + " emission " + mat.IsKeywordEnabled("_EMISSION") + " " + mat.GetColor("_EmissionColor") : null,
                retiredRenderers = retired.Length, retiredStillEnabled = retired.Count(r => r.enabled),
                frontageCollidersUnchanged = collidersSame, frontageColliderCount = after.Count, frozenGameplayColliders = frozen.Count, frozenGameplayCollidersOk = frozenOk.All(x => x),
                chunkFingerprintMatches = chunks && !chunks.editingSources && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks), chunkSourcesShown = chunks ? chunks.editingSources : (bool?)null,
                counterDressingStillPresent = GameObject.Find("Basic General counter dressing") != null, npcAgents = mira,
                sceneColliderCount = Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Length,
                sceneSha256 = Sha(Path_(Repo, "unity/AthenHill/" + ScenePath))
            };
            Write("sign-verify-saved-scene.json", report);
            Debug.Log("BasicGeneralSignPass.Verify " + JsonConvert.SerializeObject(report));
        }
    }
}
#endif
