using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// Replaces the placeholder salvage cache visual (scaled scrap pile + beacon cylinder) in Prefabs/OuterBerms/
    /// SalvageCache.prefab with the authored hero prop from art/salvage_cache_20260930 (droid-housing tray with parts and
    /// a nanite canister whose glass core carries the rarity glow). Configures importers and URP materials, keeps the
    /// glow light and motes, and points SalvageCache.glowRenderers at the core LODs. Refuses to run twice.
    public static class SalvageCacheArtInstall
    {
        const string Dir = "Assets/AthenHill/Art/Loot/SalvageCache";
        const string ModelPath = Dir + "/SalvageCache.fbx";
        const string PrefabPath = "Assets/AthenHill/Prefabs/OuterBerms/SalvageCache.prefab";

        [MenuItem("Athen Hill/Loot/Install salvage cache art")]
        public static void Install()
        {
            // Importers: colour maps sRGB, normals as normal maps, packed masks linear; model without colliders.
            foreach (var png in Directory.GetFiles(Dir, "*.png"))
            {
                var imp = (TextureImporter)AssetImporter.GetAtPath(png.Replace('\\', '/'));
                bool normal = png.Contains("_Normal"), mask = png.Contains("_MaskMap"), emission = png.Contains("_Emission");
                imp.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                imp.sRGBTexture = !(normal || mask); imp.mipmapEnabled = true; imp.streamingMipmaps = true; imp.anisoLevel = 8;
                imp.maxTextureSize = 2048; imp.textureCompression = TextureImporterCompression.CompressedHQ;
                if (emission) imp.sRGBTexture = true;
                imp.SaveAndReimport();
            }
            var model = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            model.addCollider = false; model.importNormals = ModelImporterNormals.Import; model.importTangents = ModelImporterTangents.Import;
            model.meshCompression = ModelImporterMeshCompression.Off; model.isReadable = false; model.materialImportMode = ModelImporterMaterialImportMode.None;
            model.importAnimation = false; model.importCameras = false; model.importLights = false;
            model.SaveAndReimport();

            Texture2D T(string n) => AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + "/" + n);
            var body = Lit("MI_SalvageCache_Body", T("SalvageCache_Body_BaseColor.png"), T("SalvageCache_Body_Normal.png"), T("SalvageCache_Body_MaskMap.png"), null);
            var vial = Lit("MI_SalvageCache_Vial", T("SalvageCacheVial_BaseColor.png"), T("SalvageCacheVial_Normal.png"), T("SalvageCacheVial_MaskMap.png"), null);
            var core = Lit("MI_SalvageCache_Core", T("SalvageCacheVial_BaseColor.png"), T("SalvageCacheVial_Normal.png"), T("SalvageCacheVial_MaskMap.png"), T("SalvageCacheVial_Emission.png"));

            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                if (root.transform.Find("Salvage bundle/SalvageCache_Core_LOD0")) throw new InvalidOperationException("Salvage cache art is already installed.");
                foreach (var name in new[] { "Salvage bundle", "Salvage beacon" }) { var old = root.transform.Find(name); if (old) UnityEngine.Object.DestroyImmediate(old.gameObject); }
                var art = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath), root.transform);
                art.name = "Salvage bundle"; art.transform.localPosition = Vector3.zero; art.transform.localRotation = Quaternion.identity; art.transform.localScale = Vector3.one;
                var glow = new System.Collections.Generic.List<Renderer>();
                foreach (var r in art.GetComponentsInChildren<MeshRenderer>(true))
                {
                    bool isCore = r.name.StartsWith("SalvageCache_Core");
                    r.sharedMaterials = isCore ? new[] { core } : r.sharedMaterials.Length > 1 ? new[] { body, vial } : new[] { body };
                    r.shadowCastingMode = isCore ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    if (isCore) glow.Add(r);
                }
                var lod = art.GetComponent<LODGroup>();
                if (lod)
                {
                    var lods = lod.GetLODs();
                    float[] h = { .08f, .03f, .004f };
                    for (int i = 0; i < lods.Length && i < h.Length; i++) lods[i].screenRelativeTransitionHeight = h[i];
                    lod.SetLODs(lods); lod.fadeMode = LODFadeMode.None; lod.RecalculateBounds();
                }
                var cache = root.GetComponent<SalvageCache>();
                cache.glowRenderers = glow.OrderBy(r => r.name).ToArray();
                if (root.GetComponentsInChildren<Collider>(true).Any(c => c.transform.IsChildOf(art.transform))) throw new InvalidOperationException("The cache art must not add colliders.");
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                Debug.Log("SALVAGE_CACHE_ART installed: glow renderers " + string.Join(", ", cache.glowRenderers.Select(r => r.name)) + (lod ? ", LODs " + lod.lodCount : ", no LODGroup"));
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            AssetDatabase.SaveAssets();
        }

        public static void InstallBatch() { try { Install(); EditorApplication.Exit(0); } catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); } }

        static Material Lit(string name, Texture2D baseMap, Texture2D normal, Texture2D mask, Texture2D emission)
        {
            string path = Dir + "/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name }; AssetDatabase.CreateAsset(mat, path); }
            mat.SetTexture("_BaseMap", baseMap); mat.SetColor("_BaseColor", Color.white);
            mat.SetTexture("_BumpMap", normal); mat.SetFloat("_BumpScale", 1); mat.EnableKeyword("_NORMALMAP");
            // Packed mask (R metallic, G occlusion, A smoothness): URP Lit reads metallic/smoothness from _MetallicGlossMap
            // and occlusion from the G channel of _OcclusionMap.
            mat.SetTexture("_MetallicGlossMap", mask); mat.SetFloat("_Metallic", 1); mat.SetFloat("_Smoothness", 1); mat.SetFloat("_SmoothnessTextureChannel", 0); mat.EnableKeyword("_METALLICSPECGLOSSMAP");
            mat.SetTexture("_OcclusionMap", mask); mat.SetFloat("_OcclusionStrength", 1); mat.EnableKeyword("_OCCLUSIONMAP");
            if (emission)
            {   // SalvageCache.Refresh writes the rarity colour into _EmissionColor per renderer; the map confines it to the core.
                mat.SetTexture("_EmissionMap", emission); mat.SetColor("_EmissionColor", new Color(1.5f, 1.35f, 1.1f)); mat.EnableKeyword("_EMISSION");
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            EditorUtility.SetDirty(mat); return mat;
        }
    }
}
