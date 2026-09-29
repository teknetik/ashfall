using System;
using System.IO;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// Switches the scene clock's time-aware sky to Shaders/WardSkyV2 through a copy of the current sky material,
    /// so the original material and shader stay untouched for rollback (reassign CityTimeOfDay.timeAwareSky).
    public static class WardSkyV2Install
    {
        const string MaterialPath = "Assets/AthenHill/Materials/Sky/WardSkyV2.mat";
        const string LogPath = "../evidence/rendering/20260929/sky-v2-install.json";

        [MenuItem("Athen Hill/Rendering/Install sky v2")]
        public static void Install()
        {
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>();
            if (!clock || !clock.timeAwareSky) throw new InvalidOperationException("Scene clock or its sky material is missing.");
            if (AssetDatabase.LoadAssetAtPath<Material>(MaterialPath)) throw new InvalidOperationException("Sky v2 is already installed: " + MaterialPath);
            var shader = Shader.Find("Athen Hill/Ward Sky V2");
            if (!shader) shader = AssetDatabase.LoadAssetAtPath<Shader>("Assets/AthenHill/Shaders/WardSkyV2.shader");
            if (!shader || !shader.isSupported) throw new InvalidOperationException("WardSkyV2 shader is missing or failed to compile.");
            var old = clock.timeAwareSky; var oldPath = AssetDatabase.GetAssetPath(old);
            Directory.CreateDirectory(Path.GetDirectoryName(MaterialPath));
            var copy = new Material(old) { name = "WardSkyV2" };
            copy.shader = shader;
            AssetDatabase.CreateAsset(copy, MaterialPath);
            bool skyboxWasOld = RenderSettings.skybox == old;
            clock.timeAwareSky = copy; EditorUtility.SetDirty(clock);
            if (skyboxWasOld) RenderSettings.skybox = copy;
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));
            File.WriteAllText(LogPath, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), previous = oldPath, previousShader = old.shader.name, installed = MaterialPath, shader = shader.name, skyboxReplaced = skyboxWasOld }, Formatting.Indented));
            Debug.Log("SKY_V2 installed " + MaterialPath + " (was " + oldPath + ")");
        }

        public static void InstallBatch() { Install(); EditorApplication.Exit(0); }
    }
}
