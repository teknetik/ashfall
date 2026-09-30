using System;
using System.Globalization;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
    /// Batch material tuning for look-development loops:
    ///   -executeMethod AthenHill.Editor.MaterialTweak.SetBatch --mat Assets/.../X.mat --set "_Float=1.2;_Color=1,0.5,0.2,1;_Vec=1,2,3,0"
    /// Floats take one number; colours/vectors take four (colours may be HDR). Logs each before/after value.
    public static class MaterialTweak
    {
        public static void SetBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string n) { int i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : null; }
            var path = Arg("--mat"); var spec = Arg("--set");
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat || string.IsNullOrEmpty(spec)) throw new ArgumentException("Need --mat <existing material> and --set <assignments>.");
            foreach (var part in spec.Split(';').Where(p => p.Contains('=')))
            {
                var kv = part.Split('='); var name = kv[0].Trim();
                var nums = kv[1].Split(',').Select(s => float.Parse(s.Trim(), CultureInfo.InvariantCulture)).ToArray();
                if (!mat.HasProperty(name)) throw new ArgumentException(path + " has no property " + name);
                int idx = mat.shader.FindPropertyIndex(name); var type = mat.shader.GetPropertyType(idx);
                if (type == UnityEngine.Rendering.ShaderPropertyType.Color) { Debug.Log($"TWEAK {name}: {mat.GetColor(name)} -> {string.Join(",", nums)}"); mat.SetColor(name, new Color(nums[0], nums[1], nums[2], nums.Length > 3 ? nums[3] : 1)); }
                else if (type == UnityEngine.Rendering.ShaderPropertyType.Vector) { Debug.Log($"TWEAK {name}: {mat.GetVector(name)} -> {string.Join(",", nums)}"); mat.SetVector(name, new Vector4(nums[0], nums.Length > 1 ? nums[1] : 0, nums.Length > 2 ? nums[2] : 0, nums.Length > 3 ? nums[3] : 0)); }
                else { Debug.Log($"TWEAK {name}: {mat.GetFloat(name)} -> {nums[0]}"); mat.SetFloat(name, nums[0]); }
            }
            EditorUtility.SetDirty(mat); AssetDatabase.SaveAssets();
            EditorApplication.Exit(0);
        }

        /// Makes a URP Lit material emissive and puts it on the scene's lamp circuit, so its emission follows the clock
        /// (≈4 % by day, full at night):  -executeMethod AthenHill.Editor.MaterialTweak.LampLitBatch --mat PATH --emission r,g,b
        public static void LampLitBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string n) { int i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : null; }
            var path = Arg("--mat"); var e = Arg("--emission").Split(',').Select(x => float.Parse(x, CultureInfo.InvariantCulture)).ToArray();
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat || !mat.HasProperty("_EmissionColor")) throw new ArgumentException("Need an existing emissive-capable material: " + path);
            var scene = UnityEditor.SceneManagement.EditorSceneManager.OpenScene(ImportBaseline.ScenePath, UnityEditor.SceneManagement.OpenSceneMode.Single);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            if (!circuit) throw new InvalidOperationException("No lamp circuit in the scene.");
            Debug.Log($"TWEAK {path} _EmissionColor {mat.GetColor("_EmissionColor")} -> {string.Join(",", e)}");
            mat.EnableKeyword("_EMISSION"); mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            mat.SetColor("_EmissionColor", new Color(e[0], e[1], e[2]));
            EditorUtility.SetDirty(mat);
            if (!circuit.emissiveMaterials.Contains(mat)) { circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { mat }).ToArray(); EditorUtility.SetDirty(circuit); }
            UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene); UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets(); EditorApplication.Exit(0);
        }
    }
}
