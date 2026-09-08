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
        [MenuItem("Athen Hill/Weathering/Polish notice placement")]
        public static void PolishNotices()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            var scene=EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            var root=GameObject.Find("Ward surface wear");
            if(!root)throw new Exception("Install wear first.");
            var projectors=root.GetComponentsInChildren<UnityEngine.Rendering.Universal.DecalProjector>();
            foreach(var d in projectors)
            {
                if(d.name.EndsWith("embedded base dirt")){d.fadeFactor=.8f;EditorUtility.SetDirty(d);continue;}
                if(d.name.EndsWith("standing scuffs")){d.fadeFactor=.48f;EditorUtility.SetDirty(d);continue;}
                // Preserve the artwork's 4:3 aspect, with later paper above old paint.
                if(d.name=="Warden recruitment paper")d.size=new Vector3(.96f,.72f,.15f);
                else if(d.name=="Karaveen delivery notice")d.size=new Vector3(.8f,.6f,.15f);
                else if(d.name=="Aquifer maintenance notice")d.size=new Vector3(1.12f,.84f,.18f);
                else if(d.name=="Factory orders graffiti")
                {
                    d.transform.position=new Vector3(46.48f,.79f,-11.75f);
                    d.size=new Vector3(1.85f,.78f,.15f);
                }
                else continue;
                if(d.name!="Factory orders graffiti")d.material.SetFloat("_DrawOrder",20);
                EditorUtility.SetDirty(d);EditorUtility.SetDirty(d.material);
            }
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
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
