using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
    public static class WardBuildingMaterials
    {
        public const string Folder = "Assets/AthenHill/Art/BuildingMaterials";
        public static readonly string[] Slots = { "WardPlaster", "WardStone", "WardConcrete", "WardWornSteel" };

        [MenuItem("Athen Hill/Quality/Prepare shared building materials")]
        public static void Prepare()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play before material preparation.");
            var rows = Slots.Select(slot =>
            {
                var folder = Folder + "/" + slot;
                var path = folder + "/" + slot + ".mat";
                // Later Inspector tuning is authoritative; source staging never overwrites it.
                var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (existing) return new { slot, path, result = "existing material preserved" };
                var albedo = Import(folder + "/BaseColor.png", true, false);
                var normal = Import(folder + "/Normal.png", false, true);
                var packed = Import(folder + "/MetalSmooth.png", false, false);
                var material = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = slot, enableInstancing = true };
                material.SetTexture("_BaseMap", albedo); material.SetColor("_BaseColor", Color.white);
                material.SetTexture("_BumpMap", normal); material.SetFloat("_BumpScale", 1);
                material.SetTexture("_MetallicGlossMap", packed); material.SetFloat("_Metallic", 1); material.SetFloat("_Smoothness", 1);
                material.EnableKeyword("_NORMALMAP"); material.EnableKeyword("_METALLICSPECGLOSSMAP");
                material.SetFloat("_SmoothnessTextureChannel", 0); material.DisableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A");
                material.SetColor("_EmissionColor", Color.black); material.DisableKeyword("_EMISSION");
                AssetDatabase.CreateAsset(material, path);
                return new { slot, path, result = "created from full-resolution verified PBR sources" };
            }).ToArray();
            AssetDatabase.SaveAssets();
            var evidence = Path.GetFullPath(Path.Combine(Application.dataPath, "../../evidence/quality/20260909/building-materials"));
            Directory.CreateDirectory(evidence);
            File.WriteAllText(Path.Combine(evidence, "prepare.json"), JsonConvert.SerializeObject(new { utc = DateTime.UtcNow, rows, acceptance = "Source bindings prepared; no source render, scene, native visual or performance acceptance implied" }, Formatting.Indented));
        }

        static Texture2D Import(string path, bool srgb, bool normal)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!importer) throw new InvalidOperationException("Missing staged map: " + path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.npotScale = TextureImporterNPOTScale.None;
            importer.GetSourceTextureWidthAndHeight(out int width, out int height);
            importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(width, height));
            importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
            importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
    }
}
