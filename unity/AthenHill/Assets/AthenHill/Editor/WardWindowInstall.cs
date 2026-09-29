using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// Turns the shop windows (WardGlass, shared by the render chunks) into interior-mapped glass with rooms that light
    /// up at night (Shaders/WardWindowInterior.shader), and puts the material on the lamp circuit so its emission
    /// follows the city clock. The original URP/Lit material is copied to WardGlass_URPLit_backup.mat first; restoring
    /// is copying that material's shader and values back (or reassigning it). Refuses to run twice.
    public static class WardWindowInstall
    {
        const string GlassPath = "Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02/Materials/WardGlass.mat";
        const string BackupPath = "Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02/Materials/WardGlass_URPLit_backup.mat";
        const string LogPath = "../evidence/rendering/20260929/window-install.json";

        [MenuItem("Athen Hill/Rendering/Install interior-mapped windows")]
        public static void Install()
        {
            var glass = AssetDatabase.LoadAssetAtPath<Material>(GlassPath);
            if (!glass) throw new InvalidOperationException("Missing " + GlassPath);
            var shader = Shader.Find("Athen Hill/Ward Window Interior");
            if (!shader || !shader.isSupported) throw new InvalidOperationException("Ward Window Interior shader is missing or failed to compile.");
            if (glass.shader == shader) throw new InvalidOperationException("Windows are already installed.");
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            if (!circuit) throw new InvalidOperationException("City light circuit is missing.");

            if (!AssetDatabase.LoadAssetAtPath<Material>(BackupPath)) AssetDatabase.CreateAsset(new Material(glass) { name = "WardGlass_URPLit_backup" }, BackupPath);
            var before = new { shader = glass.shader.name, smoothness = glass.HasProperty("_Smoothness") ? glass.GetFloat("_Smoothness") : -1, emission = glass.HasProperty("_EmissionColor") ? glass.GetColor("_EmissionColor").ToString() : "" };
            glass.shader = shader;
            glass.SetColor("_EmissionColor", new Color(3f, 3f, 3f));
            if (glass.HasProperty("_Smoothness")) glass.SetFloat("_Smoothness", .93f);
            EditorUtility.SetDirty(glass);

            bool added = false;
            if (!circuit.emissiveMaterials.Contains(glass)) { circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { glass }).ToArray(); added = true; EditorUtility.SetDirty(circuit); }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(LogPath)));
            File.WriteAllText(LogPath, JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), material = GlassPath, backup = BackupPath, before, after = new { shader = shader.name, smoothness = .93f, emission = "(3,3,3) HDR" }, addedToCircuit = added }, Formatting.Indented));
            Debug.Log("WINDOWS installed on " + GlassPath);
        }

        public static void InstallBatch() { Install(); EditorApplication.Exit(0); }
    }
}
