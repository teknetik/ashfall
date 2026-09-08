using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    public static partial class WardWeatheringPass
    {
        const string Evidence = "../evidence/weathering/20260908";
        const string Root = "Assets/AthenHill/Art/Weathering";
        static float[] V(Vector3 p) => new[] { p.x, p.y, p.z };
        static Transform[] All() => UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include);
        static readonly string[] Views = { "cam_hill", "cam_avenue", "cam_gate", "cam_grid", "cam_whompah", "cam_hero", "cam_terminal", "cam_wear_terminal", "cam_wear_steps", "cam_wear_wall" };

        [MenuItem("Athen Hill/Weathering/Survey and capture before")]
        public static void Survey()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            Directory.CreateDirectory(Evidence);
            // Recoverable copy before this pass; subsequent calls must not overwrite it.
            if (!File.Exists(Evidence + "/before-scene.unity")) File.Copy(ImportBaseline.ScenePath, Evidence + "/before-scene.unity");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            try
            {
                var renderers = UnityEngine.Object.FindObjectsByType<MeshRenderer>();
                File.WriteAllText(Evidence + "/survey.json", JsonConvert.SerializeObject(new {
                    renderers = renderers.Where(r => !r.transform.IsChildOf(chunks.transform)).Select(r => new { r.name, parent = r.transform.parent ? r.transform.parent.name : null, root = r.transform.root.name, min = V(r.bounds.min), max = V(r.bounds.max), position = V(r.transform.position), rotation = V(r.transform.eulerAngles), enabled = r.enabled, materials = r.sharedMaterials.Select(AssetDatabase.GetAssetPath) }),
                    colliders = UnityEngine.Object.FindObjectsByType<Collider>().Select(c => new { c.name, min = V(c.bounds.min), max = V(c.bounds.max) })
                }, Formatting.Indented));
            }
            finally { chunks.ShowSources(false); }
            DistrictCityPass.Camera("cam_wear_terminal", new Vector3(11.5f, 1.75f, -10.5f), new Vector3(8f, .65f, -13.6f), 60);
            DistrictCityPass.Camera("cam_wear_steps", new Vector3(12.5f, 1.7f, 5.5f), new Vector3(7.6f, .7f, .2f), 58);
            DistrictCityPass.Camera("cam_wear_wall", new Vector3(41.8f,1.7f,-10.6f), new Vector3(46.3f,1.55f,-10.3f), 65);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Capture("before-editor");
        }
        static void Capture(string folder)
        {
            ShaderUtil.allowAsyncCompilation = false;
            Directory.CreateDirectory(Evidence + "/" + folder);
            foreach (var view in Views)
            {
                PortDiagnostics.Capture(view); PortDiagnostics.Capture(view);
                File.Copy("Captures/Fixed/" + view + ".png", Evidence + "/" + folder + "/" + view + ".png", true);
            }
        }
        [MenuItem("Athen Hill/Weathering/Refresh and capture installed wear")]
        public static void Review()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            EnableDecals();
            Capture("after-editor");
        }
        [MenuItem("Athen Hill/Weathering/Build current Linux players")]
        public static void Build()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            Directory.CreateDirectory(Evidence);
            LinuxBuild.Development(); File.Copy("Captures/linux-build.json", Evidence + "/development-build.json", true);
            LinuxBuild.Release(); File.Copy("Captures/linux-build.json", Evidence + "/release-build.json", true);
        }
    }
}
