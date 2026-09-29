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
    }
}
