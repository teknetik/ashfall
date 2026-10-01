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

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: basin mountains remesh and haze retune (art-direction review item 1). The backdrop ring
    /// "Desert Landscape/DesertBasin_00…07" (Art/Terrain/DesertBasin.glb, 640 triangles per chunk, straight faceted
    /// ridges, pale slope stripes, bleached at noon) is replaced by "Basin mountains": eight chunks of an eroded,
    /// adaptively meshed heightfield (Art/Terrain/BasinMountains/BasinMountains.glb, about 177k triangles) authored in
    /// art/basin_mountains_20261001 (numpy heightfield, stream-power erosion, RTIN mesh, Blender glb export). The chunks
    /// keep the original sector split, layout and shader inputs (Ward Desert Terrain V2: vertex colour R sun
    /// visibility, G sky access). Material Materials/Terrain/SandstoneBasinV3.mat is a copy of SandstoneBasinV2 with
    /// the new haze-shape controls (art/basin_mountains_20261001/material.json); V2 and the old chunks stay for rollback
    /// (old chunks inactive). The Outer Berms ground is not touched: the new surface equals the old one at its edge.
    ///
    /// Batch: -executeMethod AthenHill.Editor.BasinMountainsPass.RunBatch
    ///        --steps cameras|material|install|addcams|verify|previewbuild|abbuild:on|abbuild:off[,...]
    /// Menu:  Athen Hill → Basin mountains → …
    /// </summary>
    public static class BasinMountainsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/basin-mountains/20261001/";
        const string Glb = "Assets/AthenHill/Art/Terrain/BasinMountains/BasinMountains.glb";
        const string MatV2 = "Assets/AthenHill/Materials/Terrain/SandstoneBasinV2.mat";
        const string MatV3 = "Assets/AthenHill/Materials/Terrain/SandstoneBasinV3.mat";
        const string MaterialJson = "../../art/basin_mountains_20261001/material.json";
        public const string RootName = "Basin mountains";
        const string OldRootName = "Desert Landscape";
        const string AbOnCopy = "Assets/AthenHill/Scenes/__bm_ab_on.unity", AbOffCopy = "Assets/AthenHill/Scenes/__bm_ab_off.unity";
        const string PreviewCopy = "Assets/AthenHill/Scenes/__bm_preview.unity";
        const string CamRootName = "Basin mountains review cameras";
        const string CamJson = "../../art/basin_mountains_20261001/review_cameras.json";

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        // ------------------------------------------------------------------ cameras (read-only)
        /// World poses and lenses of every review camera (cam_*), for the source-side previews.
        public static string Cameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var rows = new List<object>();
            foreach (var root in scene.GetRootGameObjects())
            foreach (var cam in root.GetComponentsInChildren<Camera>(true))
            {
                if (!cam.name.StartsWith("cam_")) continue;
                var t = cam.transform;
                rows.Add(new
                {
                    name = cam.name, path = PathOf(t),
                    pos = new[] { t.position.x, t.position.y, t.position.z },
                    fwd = new[] { t.forward.x, t.forward.y, t.forward.z },
                    up = new[] { t.up.x, t.up.y, t.up.z },
                    euler = new[] { t.eulerAngles.x, t.eulerAngles.y, t.eulerAngles.z },
                    fov = cam.fieldOfView, near = cam.nearClipPlane, far = cam.farClipPlane,
                });
            }
            var key = RenderSettings.sun ? RenderSettings.sun.transform : null;
            var json = JsonConvert.SerializeObject(new
            {
                utc = DateTime.UtcNow.ToString("O"), cameras = rows,
                sun = key ? new { name = key.name, euler = new[] { key.eulerAngles.x, key.eulerAngles.y, key.eulerAngles.z }, fwd = new[] { key.forward.x, key.forward.y, key.forward.z } } : null,
                fog = new { RenderSettings.fogMode, start = RenderSettings.fogStartDistance, end = RenderSettings.fogEndDistance, color = new[] { RenderSettings.fogColor.r, RenderSettings.fogColor.g, RenderSettings.fogColor.b } },
            }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "cameras.json", json);
            return rows.Count + " cameras";
        }

        // ------------------------------------------------------------------ material
        /// Creates SandstoneBasinV3.mat (a copy of V2, same shader) or updates it, then applies material.json.
        [MenuItem("Athen Hill/Basin mountains/Create or update material V3")]
        public static string MaterialStep()
        {
            var v2 = AssetDatabase.LoadAssetAtPath<Material>(MatV2) ?? throw new Exception("Missing " + MatV2);
            var v3 = AssetDatabase.LoadAssetAtPath<Material>(MatV3);
            bool created = false;
            if (!v3)
            {
                v3 = new Material(v2) { name = "SandstoneBasinV3" };
                AssetDatabase.CreateAsset(v3, MatV3); created = true;
            }
            if (v3.shader != v2.shader) throw new Exception("V3 must use the V2 shader");
            var set = new List<string>();
            foreach (var p in JObject.Parse(File.ReadAllText(MaterialJson)).Properties())
            {
                if (p.Name.StartsWith("//")) continue;
                if (!v3.HasProperty(p.Name)) throw new Exception("Shader has no property " + p.Name + " (shader not reimported?)");
                if (p.Value.Type == JTokenType.Array)
                {
                    var a = p.Value.Select(x => (float)x).ToArray();
                    v3.SetVector(p.Name, new Vector4(a[0], a[1], a[2], a.Length > 3 ? a[3] : 0));
                }
                else v3.SetFloat(p.Name, (float)p.Value);
                set.Add(p.Name);
            }
            EditorUtility.SetDirty(v3); AssetDatabase.SaveAssets();
            return (created ? "created " : "updated ") + MatV3 + ": " + string.Join(", ", set);
        }

        // ------------------------------------------------------------------ apply / install
        static GameObject Apply(UnityEngine.SceneManagement.Scene scene, List<string> retired)
        {
            if (scene.GetRootGameObjects().Any(g => g.name == RootName)) throw new Exception(RootName + " is already in the scene");
            AssetDatabase.ImportAsset(Glb, ImportAssetOptions.ForceUpdate);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Glb) ?? throw new Exception("Missing " + Glb);
            var v3 = AssetDatabase.LoadAssetAtPath<Material>(MatV3) ?? throw new Exception("Run the material step first: " + MatV3);
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == OldRootName) ?? throw new Exception(OldRootName + " not found");
            var template = old.GetComponentsInChildren<MeshRenderer>(true).FirstOrDefault() ?? throw new Exception("No old basin renderer");
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
            go.name = RootName;
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity); go.transform.localScale = Vector3.one;
            int n = 0;
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                r.sharedMaterials = new[] { v3 };
                r.shadowCastingMode = ShadowCastingMode.On;            // the V2 basin cast shadows too (terrain v2 install)
                r.receiveShadows = template.receiveShadows;
                r.lightProbeUsage = template.lightProbeUsage;
                r.reflectionProbeUsage = template.reflectionProbeUsage;
                r.motionVectorGenerationMode = template.motionVectorGenerationMode;
                r.allowOcclusionWhenDynamic = template.allowOcclusionWhenDynamic;
                GameObjectUtility.SetStaticEditorFlags(r.gameObject, GameObjectUtility.GetStaticEditorFlags(template.gameObject));
                PrefabUtility.RecordPrefabInstancePropertyModifications(r);
                n++;
            }
            if (n != 8) throw new Exception("Expected 8 basin chunks, found " + n);
            foreach (var r in old.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (!r.gameObject.activeSelf) continue;
                r.gameObject.SetActive(false);
                PrefabUtility.RecordPrefabInstancePropertyModifications(r.gameObject);
                retired.Add(PathOf(r.transform));
            }
            return go;
        }

        [MenuItem("Athen Hill/Basin mountains/Install (one time)")]
        public static string Install()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (scene.GetRootGameObjects().Any(g => g.name == RootName)) throw new Exception("Basin mountains are already installed");
            Directory.CreateDirectory(Evidence + "rollback");
            File.Copy(ScenePath, Evidence + "rollback/AthenHill-before-basin-mountains.unity", true);
            var retired = new List<string>();
            var go = Apply(scene, retired);
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene)) throw new Exception("Scene save failed");
            var record = new
            {
                utc = DateTime.UtcNow.ToString("O"), root = RootName, model = Glb, material = MatV3, previousMaterial = MatV2,
                renderers = go.GetComponentsInChildren<MeshRenderer>(true).Select(r => new { path = PathOf(r.transform), mesh = r.GetComponent<MeshFilter>().sharedMesh.name, triangles = r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3, shadows = r.shadowCastingMode.ToString() }),
                retired, rollback = "rollback/AthenHill-before-basin-mountains.unity (scene file before the install); or: deactivate '" + RootName + "' and reactivate the eight 'Desert Landscape' children",
            };
            File.WriteAllText(Evidence + "install.json", JsonConvert.SerializeObject(record, Formatting.Indented));
            return "installed " + RootName + "; retired " + retired.Count;
        }

        // ------------------------------------------------------------------ review cameras
        /// Player-height review cameras (disabled Camera components) from review_cameras.json: eye = Berms ground collider
        /// + 1.7 m. Replaces this pass's own camera root only.
        [MenuItem("Athen Hill/Basin mountains/Add review cameras")]
        public static string AddCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var groundGo = GameObject.Find("Outer Berms/Berms ground");
            var ground = groundGo ? groundGo.GetComponent<MeshCollider>() : null;
            if (!ground) throw new Exception("Berms ground collider missing");
            Physics.SyncTransforms();
            var template = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).FirstOrDefault(c => c.name == "cam_berms_road");
            var root = new GameObject(CamRootName);
            var rows = new List<object>();
            foreach (var c in JObject.Parse(File.ReadAllText(CamJson))["cameras"])
            {
                float x = (float)c["x"], z = (float)c["z"];
                if (!ground.Raycast(new Ray(new Vector3(x, 80, z), Vector3.down), out var hit, 200)) throw new Exception("no Berms ground under " + c["name"]);
                var pos = new Vector3(x, hit.point.y + 1.7f, z);
                var look = new Vector3((float)c["look"][0], (float)c["look"][1], (float)c["look"][2]);
                var go = new GameObject((string)c["name"]); go.transform.SetParent(root.transform, false);
                var cam = go.AddComponent<Camera>();
                if (template) cam.CopyFrom(template);                     // CopyFrom also copies the transform: pose after it
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(look - pos, Vector3.up));
                cam.enabled = false; cam.fieldOfView = (float)c["fov"]; cam.nearClipPlane = .05f; cam.farClipPlane = 650; cam.targetTexture = null;
                rows.Add(new { name = go.name, pos = new[] { pos.x, pos.y, pos.z } });
            }
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene)) throw new Exception("Scene save failed");
            File.WriteAllText(Evidence + "review-cameras.json", JsonConvert.SerializeObject(rows, Formatting.Indented));
            return rows.Count + " review cameras under " + CamRootName;
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Basin mountains/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var problems = new List<string>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            var v3 = AssetDatabase.LoadAssetAtPath<Material>(MatV3);
            var rows = new List<object>(); long tris = 0;
            if (!root) problems.Add("root missing");
            else
            {
                if (!root.activeInHierarchy) problems.Add("root inactive");
                if (!PrefabUtility.IsPartOfPrefabInstance(root) || PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(root) != Glb) problems.Add("root is not a prefab instance of " + Glb);
                foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var mf = r.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null;
                    long t = mesh ? mesh.triangles.Length / 3 : 0; tris += t;
                    if (!mesh) problems.Add(PathOf(r.transform) + ": no mesh");
                    if (!r.gameObject.activeInHierarchy || !r.enabled) problems.Add(PathOf(r.transform) + ": inactive");
                    if (r.sharedMaterials.Length != 1 || r.sharedMaterial != v3) problems.Add(PathOf(r.transform) + ": material is not " + MatV3);
                    if (mesh && mesh.colors.Length != mesh.vertexCount) problems.Add(PathOf(r.transform) + ": vertex colours missing");
                    rows.Add(new { path = PathOf(r.transform), triangles = t, vertices = mesh ? mesh.vertexCount : 0, indexFormat = mesh ? mesh.indexFormat.ToString() : "", shadows = r.shadowCastingMode.ToString(), bounds = mesh ? new[] { r.bounds.min.x, r.bounds.min.y, r.bounds.min.z, r.bounds.max.x, r.bounds.max.y, r.bounds.max.z } : null });
                }
                if (rows.Count != 8) problems.Add("expected 8 chunks, found " + rows.Count);
            }
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == OldRootName);
            var stillActive = old ? old.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.gameObject.activeInHierarchy).Select(r => PathOf(r.transform)).ToList() : new List<string>();
            if (stillActive.Count > 0) problems.Add("old basin still active: " + string.Join(", ", stillActive));
            var berms = GameObject.Find("Outer Berms/Berms ground");
            if (!berms) problems.Add("Outer Berms/Berms ground missing");
            int missing = 0;
            if (root) foreach (var r in root.GetComponentsInChildren<Renderer>(true)) missing += r.sharedMaterials.Count(m => m == null);
            if (missing > 0) problems.Add(missing + " missing materials");
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            var reviewCams = camRoot ? camRoot.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            if (camRoot && camRoot.GetComponentsInChildren<Camera>(true).Any(c => c.enabled)) problems.Add("a review camera is enabled");
            var json = JsonConvert.SerializeObject(new
            {
                utc = DateTime.UtcNow.ToString("O"), ok = problems.Count == 0, problems, triangles = tris, chunks = rows,
                material = v3 ? new
                {
                    shader = v3.shader.name, hazeDensity = v3.GetFloat("_HazeDensity"), farStart = v3.GetFloat("_HazeFarStart"), farScale = v3.GetFloat("_HazeFarScale"),
                    heightFalloff = v3.GetFloat("_HazeHeightFalloff"), baseHeight = v3.GetFloat("_HazeBaseHeight"), noonTint = new[] { v3.GetVector("_HazeNoonTint").x, v3.GetVector("_HazeNoonTint").y, v3.GetVector("_HazeNoonTint").z }, rockSlope = v3.GetFloat("_RockSlope"),
                } : null,
                oldRootActive = old && old.activeInHierarchy, bermsGround = berms ? "present (untouched)" : "missing", reviewCameras = reviewCams,
            }, Formatting.Indented);
            File.WriteAllText(Evidence + "verify.json", json);
            if (problems.Count > 0) throw new Exception("verify failed: " + string.Join("; ", problems));
            return "verify ok: " + rows.Count + " chunks, " + tris + " triangles";
        }

        // ------------------------------------------------------------------ builds from temporary scene copies
        static string Build(string src, string folder)
        {
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneLinux64, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneLinux64, new[] { GraphicsDeviceType.OpenGLCore });
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { src }, locationPathName = "Builds/" + folder + "/AthenHill.x86_64",
                target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
            });
            if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("build failed: " + folder);
            return folder + " " + report.summary.totalTime.TotalSeconds.ToString("0") + " s";
        }

        /// Iteration build: the saved scene with the pass applied in memory (if not yet installed), written to a temporary
        /// copy, built to Builds/bm-preview, copy deleted. The shared saved scene is not changed.
        public static string PreviewBuild()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (!scene.GetRootGameObjects().Any(g => g.name == RootName)) Apply(scene, new List<string>());
            if (!EditorSceneManager.SaveScene(scene, PreviewCopy, true)) throw new Exception("could not write " + PreviewCopy);
            try { return Build(PreviewCopy, "bm-preview"); }
            finally { AssetDatabase.DeleteAsset(PreviewCopy); }
        }

        /// A/B timing builds (one per Editor run, memory caps). "on" snapshots the saved scene once into two copies (pass on,
        /// pass off = old basin active and the new root inactive) and builds the on copy; "off" builds the off copy and
        /// deletes both. The shared saved scene is never toggled.
        public static string AbBuild(string arm)
        {
            if (arm == "on")
            {
                var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
                var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName) ?? Apply(scene, new List<string>());
                var old = scene.GetRootGameObjects().First(g => g.name == OldRootName);
                var oldChunks = old.GetComponentsInChildren<MeshRenderer>(true).Select(r => r.gameObject).ToList();
                root.SetActive(true); foreach (var g in oldChunks) g.SetActive(false);
                if (!EditorSceneManager.SaveScene(scene, AbOnCopy, true)) throw new Exception("could not write " + AbOnCopy);
                root.SetActive(false); foreach (var g in oldChunks) g.SetActive(true);
                if (!EditorSceneManager.SaveScene(scene, AbOffCopy, true)) throw new Exception("could not write " + AbOffCopy);
                return Build(AbOnCopy, "bm-ab-on");
            }
            if (!File.Exists(AbOffCopy)) throw new Exception("Run abbuild:on first (it writes the scene snapshot for both arms).");
            try { return Build(AbOffCopy, "bm-ab-off"); }
            finally { AssetDatabase.DeleteAsset(AbOnCopy); AssetDatabase.DeleteAsset(AbOffCopy); }
        }

        // ================================================================== batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "cameras").Split(',');
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "cameras" => Cameras(),
                        "material" => MaterialStep(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "addcams" => AddCameras(),
                        "previewbuild" => PreviewBuild(),
                        "abbuild" => AbBuild(parts[1]),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("BasinMountainsPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
