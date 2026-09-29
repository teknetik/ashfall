#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Task t_6f2addb6 (29 Sep 2026). Editor-only, recoverable. Inspect reports the current state without writing;
    // Apply does the two small changes described in unity/evidence/basic-general-face/20260929/README.md.
    public static class BasicGeneralFacePass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Evidence => Path.Combine(Repo, "unity/evidence/basic-general-face/20260929");
        static void Write(string name, object data) { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented)); }
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };

        static void OpenScene()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        public static void InspectBatch()
        {
            OpenScene();
            var frontage = GameObject.Find("Basic General authored frontage");
            var dress = GameObject.Find("Basic General counter dressing");
            var mira = GameObject.Find("Mira");
            var rear = new List<object>();
            if (frontage)
                foreach (var r in frontage.GetComponentsInChildren<Renderer>(true))
                {
                    string n = r.name;
                    if (!(n.StartsWith("Rear_wall") || n.StartsWith("Rear_recessed") || n.StartsWith("Front_reveal") || n.StartsWith("Threshold") || n.StartsWith("Structure"))) continue;
                    rear.Add(new { n, enabled = r.enabled, active = r.gameObject.activeInHierarchy, mats = r.sharedMaterials.Select(m => m ? m.name : null).ToArray(), center = A(r.bounds.center), size = A(r.bounds.size), tris = r.GetComponent<MeshFilter>() ? r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3 : 0 });
                }
            var lights = Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(l => Vector3.Distance(l.transform.position, new Vector3(8, 1.5f, 15.5f)) < 12f)
                .Select(l => new { path = PathOf(l.transform), type = l.type.ToString(), l.intensity, l.range, color = new[] { l.color.r, l.color.g, l.color.b }, shadows = l.shadows.ToString(), enabled = l.enabled, pos = A(l.transform.position), mode = l.lightmapBakeType.ToString() }).ToArray();
            var faceRenderers = dress ? dress.GetComponentsInChildren<Renderer>(true).Where(r => r.sharedMaterials.Any(m => m && m.name == "BGC_CounterFace")).Select(r => new { path = PathOf(r.transform), center = A(r.bounds.center), size = A(r.bounds.size), lodParent = r.GetComponentInParent<LODGroup>() != null }).ToArray() : null;
            var wholeDress = dress ? dress.GetComponentsInChildren<Renderer>(true).Select(r => new { path = PathOf(r.transform), mats = r.sharedMaterials.Select(m => m ? m.name : null).ToArray(), center = A(r.bounds.center), size = A(r.bounds.size) }).ToArray() : null;
            var dirLights = Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(l => l.type == LightType.Directional).Select(l => new { path = PathOf(l.transform), l.intensity, rot = A(l.transform.eulerAngles), shadows = l.shadows.ToString() }).ToArray();
            Write("inspect.json", new
            {
                utc = DateTime.UtcNow,
                frontagePos = frontage ? A(frontage.transform.position) : null,
                frontageYaw = frontage ? frontage.transform.eulerAngles.y : 0,
                dressPos = dress ? A(dress.transform.position) : null,
                miraPos = mira ? A(mira.transform.position) : null,
                rearRenderers = rear, lightsNearby = lights, faceRenderers, wholeDress, dirLights,
                ambient = new { mode = RenderSettings.ambientMode.ToString(), sky = new[] { RenderSettings.ambientSkyColor.r, RenderSettings.ambientSkyColor.g, RenderSettings.ambientSkyColor.b }, intensity = RenderSettings.ambientIntensity }
            });
        }

        public static void InspectLampsBatch()
        {
            OpenScene();
            var list = Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(r => Vector3.Distance(r.bounds.center, new Vector3(8, 2.5f, 14.5f)) < 9f && (r.name.StartsWith("Under-sign") || r.name.StartsWith("Rear_maint") || r.name.StartsWith("Stock_exact") || r.name.StartsWith("Lamp") || r.name.Contains("lamp") || r.name.Contains("Sign") || r.name.Contains("sign")))
                .Select(r => new { path = PathOf(r.transform), r.enabled, center = A(r.bounds.center), size = A(r.bounds.size) }).ToArray();
            Write("inspect-lamps.json", list);
        }

        // ---- Apply / Verify (task t_6f2addb6) ------------------------------------------------------------------------------
        const string Folder = "Assets/AthenHill/Art/Phase1/BasicGeneral/Counter20260929";
        const string PanelFolder = "Assets/AthenHill/Art/Phase1/BasicGeneral/BackPanel20260929";
        const string PanelInstance = "Basic General back panel";
        const string FaceMatPath = Folder + "/Materials/BGC_CounterFace.mat";

        static Texture2D ImportTex(string path, bool srgb, bool normal)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var imp = (TextureImporter)AssetImporter.GetAtPath(path);
            imp.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            imp.sRGBTexture = srgb; imp.alphaSource = TextureImporterAlphaSource.FromInput; imp.alphaIsTransparency = false;
            imp.GetSourceTextureWidthAndHeight(out int w, out int h);
            imp.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(w, h)); imp.npotScale = TextureImporterNPOTScale.None;
            imp.mipmapEnabled = true; imp.streamingMipmaps = true; imp.anisoLevel = 8; imp.wrapMode = TextureWrapMode.Clamp;
            imp.textureCompression = TextureImporterCompression.CompressedHQ; imp.crunchedCompression = false;
            imp.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        // Thin board, front face (+Z, towards the avenue) carries the whole texture; sides/back sample the frame colour.
        static Mesh BoardMesh(float w, float h, float d)
        {
            float x = w / 2, y = h / 2;
            var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 e, Vector3 nn, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ue)
            {
                int i = v.Count; v.AddRange(new[] { a, b, c, e }); n.AddRange(new[] { nn, nn, nn, nn }); uv.AddRange(new[] { ua, ub, uc, ue });
                if (Vector3.Dot(Vector3.Cross(b - a, c - a), nn) > 0) t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 }); else t.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 }); // Unity front faces are clockwise: cross(b-a,c-a) must face the normal
            }
            float zf = d / 2, zb = -d / 2; var edgeUv = new Vector2(0.01f, 0.5f);
            // Front (+Z, avenue side). A viewer at +Z looks along -Z, so +X is on their left: u = 0 at +X.
            Quad(new Vector3(x, -y, zf), new Vector3(x, y, zf), new Vector3(-x, y, zf), new Vector3(-x, -y, zf), Vector3.forward, new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0));
            Quad(new Vector3(x, -y, zb), new Vector3(x, y, zb), new Vector3(-x, y, zb), new Vector3(-x, -y, zb), Vector3.back, edgeUv, edgeUv, edgeUv, edgeUv);
            Quad(new Vector3(-x, -y, zb), new Vector3(-x, y, zb), new Vector3(-x, y, zf), new Vector3(-x, -y, zf), Vector3.left, edgeUv, edgeUv, edgeUv, edgeUv);
            Quad(new Vector3(x, -y, zf), new Vector3(x, y, zf), new Vector3(x, y, zb), new Vector3(x, -y, zb), Vector3.right, edgeUv, edgeUv, edgeUv, edgeUv);
            Quad(new Vector3(-x, y, zf), new Vector3(-x, y, zb), new Vector3(x, y, zb), new Vector3(x, y, zf), Vector3.up, edgeUv, edgeUv, edgeUv, edgeUv);
            Quad(new Vector3(-x, -y, zb), new Vector3(-x, -y, zf), new Vector3(x, -y, zf), new Vector3(x, -y, zb), Vector3.down, edgeUv, edgeUv, edgeUv, edgeUv);
            var m = new Mesh { name = "BGC_BackPanel" };
            m.SetVertices(v); m.SetNormals(n); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateTangents(); m.RecalculateBounds();
            return m;
        }

        // Installs the back panel (one new root object, no colliders, not a chunk source) and swaps the counter-face material textures
        // (already done on disk by the authoring script; this verifies the binding). Refuses to overwrite anything.
        public static void ApplyBatch()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current scene edits first.");
            if (GameObject.Find(PanelInstance)) throw new InvalidOperationException("Back panel already installed.");
            if (AssetDatabase.IsValidFolder(PanelFolder)) throw new InvalidOperationException("Back-panel assets already exist.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); if (!chunks) throw new InvalidOperationException("Missing render-source controller.");
            string backup = System.IO.Path.Combine(Evidence, "rollback/before-face-backpanel-saved-by-apply.unity");
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
            if (File.Exists(backup) || !EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot create unique recovery scene copy.");
            string fpBefore = chunks.sourceFingerprint;
            AssetDatabase.CreateFolder("Assets/AthenHill/Art/Phase1/BasicGeneral", "BackPanel20260929");
            foreach (var d in new[] { "Meshes", "Materials", "Textures" }) AssetDatabase.CreateFolder(PanelFolder, d);
            foreach (var k in new[] { "BaseColor", "MetalSmooth", "Normal" })
                AssetDatabase.MoveAsset(Folder + "/Textures/BGC_BackPanel_" + k + ".png", PanelFolder + "/Textures/BGC_BackPanel_" + k + ".png");
            var albedo = ImportTex(PanelFolder + "/Textures/BGC_BackPanel_BaseColor.png", true, false);
            var packed = ImportTex(PanelFolder + "/Textures/BGC_BackPanel_MetalSmooth.png", false, false);
            var normal = ImportTex(PanelFolder + "/Textures/BGC_BackPanel_Normal.png", false, true);
            var faceMat = AssetDatabase.LoadAssetAtPath<Material>(FaceMatPath);
            var mat = new Material(faceMat.shader) { name = "BGC_BackPanel", enableInstancing = true };
            mat.CopyPropertiesFromMaterial(faceMat);
            mat.SetTexture("_BaseMap", albedo); mat.SetTexture("_MainTex", albedo); mat.SetTexture("_BumpMap", normal); mat.SetTexture("_MetallicGlossMap", packed);
            AssetDatabase.CreateAsset(mat, PanelFolder + "/Materials/BGC_BackPanel.mat");
            var mesh = BoardMesh(0.86f, 1.00f, 0.03f);
            AssetDatabase.CreateAsset(mesh, PanelFolder + "/Meshes/BGC_BackPanel.asset");
            var go = new GameObject(PanelInstance);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On; r.receiveShadows = true;
            var prefab = PrefabUtility.SaveAsPrefabAsset(go, PanelFolder + "/BasicGeneralBackPanel.prefab");
            Object.DestroyImmediate(go);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            inst.name = PanelInstance;
            // Rear wall front face z 13.48 (Rear_wall_core bounds); service panels stand to 13.50; board 0.03 thick from 13.50 to 13.53.
            inst.transform.position = new Vector3(8.0f, 2.45f, 13.515f); inst.transform.rotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
            Undo.RegisterCreatedObjectUndo(inst, "Install Basic General back panel");
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Write("apply.json", new { utc = DateTime.UtcNow, prefab = PanelFolder + "/BasicGeneralBackPanel.prefab", position = A(inst.transform.position), fingerprintBefore = fpBefore, fingerprintAfter = chunks.sourceFingerprint,
                faceMaterialTextures = new[] { AssetDatabase.GetAssetPath(faceMat.GetTexture("_BaseMap")), AssetDatabase.GetAssetPath(faceMat.GetTexture("_MetallicGlossMap")), AssetDatabase.GetAssetPath(faceMat.GetTexture("_BumpMap")) } });
        }

        public static void VerifyBatch()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); // reopen from disk
            var inst = GameObject.Find(PanelInstance); var dress = GameObject.Find("Basic General counter dressing"); var frontage = GameObject.Find("Basic General authored frontage");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var frozen = Newtonsoft.Json.Linq.JArray.Parse(File.ReadAllText(System.IO.Path.Combine(Repo, "art/quality_20260909/basic-general/preserved-colliders.json")));
            var colliders = frozen.Select(row =>
            {
                var g = GameObject.Find((string)row["path"]); var c = g ? g.GetComponent<Collider>() : null;
                var ctr = row["center"]; var sz = row["size"];
                bool ok = c && c.enabled && Vector3.Distance(c.bounds.center, new Vector3((float)ctr[0], (float)ctr[1], (float)ctr[2])) <= .002f && Vector3.Distance(c.bounds.size, new Vector3((float)sz[0], (float)sz[1], (float)sz[2])) <= .002f;
                return new { path = (string)row["path"], ok };
            }).ToArray();
            var faceMat = AssetDatabase.LoadAssetAtPath<Material>(FaceMatPath);
            var faceRenderers = dress ? dress.GetComponentsInChildren<Renderer>(true).Where(x => x.sharedMaterials.Any(m => m == faceMat)).Select(x => x.name).ToArray() : null;
            var mira = Object.FindObjectsByType<NpcAgent>().Select(n => new { n.name, position = A(n.transform.position) }).ToArray();
            var rend = inst ? inst.GetComponent<MeshRenderer>() : null;
            var report = new
            {
                utc = DateTime.UtcNow, reopenedFromDisk = true,
                panelPresent = inst != null, panelPrefab = inst ? AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(inst)) : null,
                panelScale = inst ? A(inst.transform.lossyScale) : null, panelBounds = rend ? new { center = A(rend.bounds.center), size = A(rend.bounds.size) } : null,
                panelTriangles = inst ? inst.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3 : 0, panelHasColliders = inst && inst.GetComponentsInChildren<Collider>(true).Length > 0,
                dressingPresent = dress != null, faceMaterialUsers = faceRenderers,
                faceTextures = new[] { AssetDatabase.GetAssetPath(faceMat.GetTexture("_BaseMap")), AssetDatabase.GetAssetPath(faceMat.GetTexture("_MetallicGlossMap")), AssetDatabase.GetAssetPath(faceMat.GetTexture("_BumpMap")) },
                colliders, collidersAllPreserved = colliders.All(c => c.ok), colliderCount = Object.FindObjectsByType<Collider>().Length,
                chunkFingerprintMatches = chunks && !chunks.editingSources && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks),
                frontagePresent = frontage != null, npcAgents = mira,
                sceneSha256 = Sha(System.IO.Path.Combine(Repo, "unity/AthenHill/" + ScenePath))
            };
            Write("verify-saved-scene.json", report);
            Debug.Log("BasicGeneralFacePass.Verify " + JsonConvert.SerializeObject(report));
        }
        static string Sha(string p) { using (var sha = System.Security.Cryptography.SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(p))).Replace("-", "").ToLowerInvariant(); }

        // Correction after the first native capture: the interior wall face is z 14.00 (Rear_wall_core z 13.48..14.00); the board must stand on it.
        public static void MoveBatch()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current scene edits first.");
            var inst = GameObject.Find(PanelInstance); if (!inst) throw new InvalidOperationException("Back panel not installed.");
            string backup = System.IO.Path.Combine(Evidence, "rollback/before-panel-move-saved.unity");
            if (File.Exists(backup) || !EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot create unique recovery scene copy.");
            Undo.RecordObject(inst.transform, "Move Basic General back panel");
            inst.transform.position = new Vector3(8.0f, 2.32f, 14.015f);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Write("move.json", new { utc = DateTime.UtcNow, position = A(inst.transform.position) });
        }

        static string PathOf(Transform t) { var s = t.name; while (t.parent) { t = t.parent; s = t.name + "/" + s; } return s; }
    }
}
#endif
