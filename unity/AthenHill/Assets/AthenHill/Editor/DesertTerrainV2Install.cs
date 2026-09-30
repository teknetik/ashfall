using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// Installs Shaders/WardDesertTerrainV2 on the desert basin through a duplicate of SandstoneBasin.mat
    /// (SandstoneBasinV2.mat; the original stays for rollback), assigns the rock/scree/sand texture sets listed in
    /// WardDesertTerrainV2.README.md, points the 8 basin renderers at it and lets them cast shadows. Refuses to run twice.
    public static class DesertTerrainV2Install
    {
        const string Old = "Assets/AthenHill/Materials/Terrain/SandstoneBasin.mat";
        const string New = "Assets/AthenHill/Materials/Terrain/SandstoneBasinV2.mat";

        public static void InstallBatch()
        {
            int code = 0;
            try { Install(); } catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }

        [MenuItem("Athen Hill/Rendering/Install desert terrain v2")]
        public static void Install()
        {
            if (AssetDatabase.LoadAssetAtPath<Material>(New)) throw new InvalidOperationException("Terrain v2 is already installed: " + New);
            var shader = Shader.Find("Athen Hill/Ward Desert Terrain V2");
            if (!shader || !shader.isSupported) throw new InvalidOperationException("Ward Desert Terrain V2 shader is missing or failed to compile.");
            var old = AssetDatabase.LoadAssetAtPath<Material>(Old);
            if (!old) throw new InvalidOperationException("Missing " + Old);
            var mat = new Material(old) { name = "SandstoneBasinV2" }; mat.shader = shader;
            T<Texture2D>(mat, "_RockDetailAlbedo", "Assets/AthenHill/Art/Courtyard/Textures/sandstone_cracks_diff_2k.jpg");
            T<Texture2D>(mat, "_RockDetailNormal", "Assets/AthenHill/Art/Courtyard/Textures/sandstone_cracks_nor_gl_2k.jpg");
            T<Texture2DArray>(mat, "_GroundAH", "Assets/AthenHill/Art/WestGate/Ground/BermsGroundLayers_AH.png");
            T<Texture2DArray>(mat, "_GroundNRA", "Assets/AthenHill/Art/WestGate/Ground/BermsGroundLayers_NRA.png");
            AssetDatabase.CreateAsset(mat, New);

            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var root = GameObject.Find("Desert Landscape");
            if (!root) throw new InvalidOperationException("Desert Landscape root not found.");
            var changed = new System.Collections.Generic.List<string>();
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mats = r.sharedMaterials; bool hit = false;
                for (int i = 0; i < mats.Length; i++) if (mats[i] == old) { mats[i] = mat; hit = true; }
                if (!hit) continue;
                r.sharedMaterials = mats; r.shadowCastingMode = ShadowCastingMode.On;
                if (PrefabUtility.IsPartOfPrefabInstance(r)) PrefabUtility.RecordPrefabInstancePropertyModifications(r);
                EditorUtility.SetDirty(r); changed.Add(r.name);
            }
            if (changed.Count == 0) throw new InvalidOperationException("No basin renderer used " + Old);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            File.WriteAllText(Path.GetFullPath("../evidence/rendering/20260930/terrain-v2-install.json"),
                JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), material = New, previous = Old, renderers = changed, castShadows = true }, Formatting.Indented));
            Debug.Log("TERRAIN_V2 installed on " + changed.Count + " renderers");
        }

        static void T<TT>(Material m, string prop, string path) where TT : Texture
        {
            var tex = AssetDatabase.LoadAssetAtPath<TT>(path);
            if (!tex) throw new InvalidOperationException("Missing " + typeof(TT).Name + " " + path);
            m.SetTexture(prop, tex);
        }
    }
}
