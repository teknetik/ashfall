using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Scoped tree replacement. Downloaded sources and the old authored tree are retained.
    public static class HeroTreePass
    {
        const string Folder = "Assets/AthenHill/Art/HeroTree";
        const string PrefabPath = Folder + "/WardOasisTree.prefab";
        const string Evidence = "../evidence/quality/20260908/tree";
        static readonly string[] Parts = { "trunk", "branches", "leaves" };

        static Texture2D ImportMap(string path, bool srgb, bool normal, bool alpha)
        {
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!importer) throw new FileNotFoundException("Prepare tree source maps first", path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb;
            importer.maxTextureSize = 4096;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.mipmapEnabled = true;
            importer.streamingMipmaps = true;
            importer.anisoLevel = 8;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.alphaIsTransparency = alpha;
            importer.mipMapsPreserveCoverage = alpha;
            importer.alphaTestReferenceValue = .35f;
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
        static Bounds BoundsOf(GameObject root)
        {
            var renderers = root.GetComponentsInChildren<MeshRenderer>(true);
            if (renderers.Length == 0) throw new InvalidOperationException("Tree model has no renderers.");
            var bounds = renderers[0].bounds;
            foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
            return bounds;
        }
        static Material PrepareMaterial(string part)
        {
            string path = Folder + "/" + part + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material) return material;
            var shader = Shader.Find("Athen Hill/Ward Tree");
            if (!shader || !shader.isSupported) throw new InvalidOperationException("The pinned Ward tree shader must compile on the current OpenGL renderer.");
            material = new Material(shader) { name = "Ward tree " + part, enableInstancing = true };
            bool leaves = part == "leaves";
            material.SetTexture("_BaseMap", ImportMap(Folder + "/" + part + "-albedo.png", true, false, leaves));
            material.SetTexture("_BumpMap", ImportMap(Folder + "/" + part + "-normal.png", false, true, false));
            material.SetTexture("_MetallicGlossMap", ImportMap(Folder + "/" + part + "-metallic-smoothness.png", false, false, false));
            material.SetColor("_BaseColor", Color.white);
            material.SetFloat("_BumpScale", 1);
            material.SetFloat("_Metallic", 0);
            material.SetFloat("_Smoothness", 1);
            material.SetFloat("_WorkflowMode", 1);
            material.SetFloat("_Surface", 0);
            material.SetFloat("_ZWrite", 1);
            material.SetFloat("_Cull", leaves ? 0 : 2);
            material.SetFloat("_AlphaClip", leaves ? 1 : 0);
            material.SetFloat("_AlphaToMask", leaves ? 1 : 0);
            material.SetFloat("_Cutoff", .35f);
            material.SetFloat("_WardWindStrength", .07f);
            material.SetFloat("_WardLeafFlutter", leaves ? .008f : 0);
            material.SetFloat("_WardTranslucency", leaves ? .22f : 0);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            CoreUtils.SetKeyword(material, "_ALPHATEST_ON", leaves);
            material.DisableKeyword("_EMISSION");
            material.SetOverrideTag("RenderType", leaves ? "TransparentCutout" : "Opaque");
            material.renderQueue = leaves ? 2450 : 2000;
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        [MenuItem("Athen Hill/Hero tree/Prepare full source tree candidate")]
        public static void Prepare()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Prepare the saved asset outside Play Mode.");
            Directory.CreateDirectory(Evidence);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath)) throw new InvalidOperationException("Tree candidate already prepared; edit its saved prefab and materials deliberately.");
            var materials = Parts.ToDictionary(p => p, PrepareMaterial);
            for (int lod = 0; lod < 2; lod++)
            {
                string path = Folder + "/WardTree_LOD" + lod + ".fbx";
                var importer = AssetImporter.GetAtPath(path) as ModelImporter;
                if (!importer) throw new FileNotFoundException("Prepare source FBX first", path);
                importer.meshCompression = ModelImporterMeshCompression.Off;
                importer.isReadable = true;
                importer.importAnimation = false;
                importer.importNormals = ModelImporterNormals.Import;
                importer.importTangents = ModelImporterTangents.Import;
                importer.materialImportMode = ModelImporterMaterialImportMode.None;
                importer.SaveAndReimport();
            }
            var root = new GameObject("Ward oasis tree");
            var reports = new List<object>();
            try
            {
                var lods = new List<LOD>();
                for (int lod = 0; lod < 2; lod++)
                {
                    string path = Folder + "/WardTree_LOD" + lod + ".fbx";
                    var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
                    model.name = "Source LOD " + lod;
                    model.transform.SetParent(root.transform, false);
                    var measured = BoundsOf(model);
                    var trunk = model.GetComponentsInChildren<MeshRenderer>().Single(r => r.name.EndsWith("_trunk"));
                    float trunkRatio = trunk.bounds.size.y / measured.size.y;
                    if (Mathf.Abs(trunkRatio - .5315f) > .03f) throw new InvalidOperationException("Tree is not upright after FBX import; inspect axes before installation.");
                    // Uniform conversion only, measured from the documented physical source height.
                    model.transform.localScale *= 19.468876f / measured.size.y;
                    var renderers = model.GetComponentsInChildren<MeshRenderer>();
                    long triangles = 0;
                    foreach (var renderer in renderers)
                    {
                        string part = Parts.Single(p => renderer.name.EndsWith("_" + p));
                        renderer.sharedMaterial = materials[part];
                        renderer.shadowCastingMode = part == "leaves" ? ShadowCastingMode.TwoSided : ShadowCastingMode.On;
                        renderer.receiveShadows = true;
                        renderer.motionVectorGenerationMode = MotionVectorGenerationMode.Object;
                        var mesh = renderer.GetComponent<MeshFilter>().sharedMesh;
                        if (mesh.tangents.Length != mesh.vertexCount) throw new InvalidOperationException("Missing imported tree tangents: " + renderer.name);
                        triangles += mesh.triangles.LongLength / 3;
                        GameObjectUtility.SetStaticEditorFlags(renderer.gameObject, 0);
                    }
                    long expected = lod == 0 ? 3748776L : 1845603L;
                    if (triangles != expected) throw new InvalidOperationException("Unexpected source triangle loss: " + triangles + " vs " + expected);
                    // A lower source trunk is a static, exact visual collision proxy. Leaves never collide.
                    if (lod == 1)
                    {
                        var collider = new GameObject("Trunk collision from source LOD1");
                        collider.transform.SetParent(root.transform, false);
                        collider.transform.position = trunk.transform.position;
                        collider.transform.rotation = trunk.transform.rotation;
                        collider.transform.localScale = trunk.transform.lossyScale;
                        collider.AddComponent<MeshCollider>().sharedMesh = trunk.GetComponent<MeshFilter>().sharedMesh;
                    }
                    lods.Add(new LOD(lod == 0 ? .50f : .015f, renderers) { fadeTransitionWidth = .12f });
                    measured = BoundsOf(model);
                    reports.Add(new { lod, triangles, vertices = renderers.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.vertexCount), size = new[] { measured.size.x, measured.size.y, measured.size.z }, source = path });
                }
                var group = root.AddComponent<LODGroup>();
                group.fadeMode = LODFadeMode.CrossFade;
                group.animateCrossFading = false;
                group.SetLODs(lods.ToArray());
                group.RecalculateBounds();
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                AssetDatabase.SaveAssets();
                File.WriteAllText(Evidence + "/prepared.json", JsonConvert.SerializeObject(new { preparedUtc = DateTime.UtcNow.ToString("o"), source = "Poly Haven Jacaranda Tree, CC0", lods = reports, reviewedDistanceTransitionsPending = true, sourceCopiesRetained = true }, Formatting.Indented));
            }
            finally { Object.DestroyImmediate(root); }
        }

        [MenuItem("Athen Hill/Hero tree/Install reviewed source audition")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Install outside Play Mode.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ImportBaseline.ScenePath) throw new InvalidOperationException("Open the existing saved AthenHill scene.");
            if (GameObject.Find("Ward oasis tree")) throw new InvalidOperationException("Tree already installed; edit its saved instance.");
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (!prefab) throw new InvalidOperationException("Prepare and inspect the candidate first.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            Directory.CreateDirectory(Evidence);
            EditorSceneManager.SaveScene(scene, Evidence + "/before-tree.unity", true);
            var old = GameObject.Find("AuthoredWorld").GetComponentsInChildren<MeshRenderer>(true)
                .Where(r => r.name.StartsWith("TREE_") || r.name.StartsWith("Tree ") && r.name.EndsWith("shadow proxy")).ToArray();
            var before = old.Select(r => new { r.name, r.enabled }).ToArray();
            foreach (var renderer in old) { Undo.RecordObject(renderer, "Retain old tree source"); renderer.enabled = false; }
            var roots = GameObject.Find("Phase 1 tree roots");
            if (roots) roots.SetActive(false);
            var core = GameObject.Find("AuthoredWorld/COL_tree_core");
            if (!core || !core.GetComponent<Collider>()) throw new InvalidOperationException("Expected old tree collision proxy for explicit replacement.");
            core.GetComponent<Collider>().enabled = false;
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            instance.name = "Ward oasis tree";
            instance.transform.position = new Vector3(0, 1.18f, 0);
            instance.transform.localScale = Vector3.one * .88f;
            PrefabUtility.RecordPrefabInstancePropertyModifications(instance.transform);
            // Keep the LOD-controlled tree outside disposable city chunks.
            var bounds = BoundsOf(instance);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene);
            File.WriteAllText(Evidence + "/installed.json", JsonConvert.SerializeObject(new { installedUtc = DateTime.UtcNow.ToString("o"), previousRenderers = before, priorRootPassRetained = roots != null, uniformScale = .88f, position = new[] { 0f, 1.18f, 0f }, boundsCenter = new[] { bounds.center.x, bounds.center.y, bounds.center.z }, boundsSize = new[] { bounds.size.x, bounds.size.y, bounds.size.z }, rootIntegration = "Raw scanned skirt sunk below existing hill soil at Y1.50; flare remains visible. Requires four-quadrant native review.", nativeReview = "Pending. Rebuild chunks, save/reopen, capture unchanged cameras, root circuit and canopy motion; qualify LOD and frame time." }, Formatting.Indented));
            Selection.activeGameObject = instance;
        }

        [MenuItem("Athen Hill/Hero tree/Retire rejected legacy mound and root stones")]
        public static void RetireLegacyGroundDecorations()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlaying || scene.path != ImportBaseline.ScenePath || !GameObject.Find("Ward oasis tree"))
                throw new InvalidOperationException("Open the saved tree audition outside Play Mode.");
            var authored = GameObject.Find("AuthoredWorld");
            var mound = authored.transform.Find("ENV_hill_mound");
            if (!mound) throw new InvalidOperationException("Expected legacy mound source is missing.");
            var stones = authored.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.name == "Hill root stone").ToArray();
            if (stones.Length != 6) throw new InvalidOperationException("Inspect changed legacy root-stone inventory before removal.");
            var rejected = stones.Concat(new[] { mound.GetComponent<MeshRenderer>() }).ToArray();
            if (rejected.Any(r => !r || r.GetComponents<Collider>().Any(c => c.enabled)))
                throw new InvalidOperationException("Unexpected collision on decorative source; inspect before removal.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            var before = rejected.Select(r => new { r.name, r.enabled, mesh = AssetDatabase.GetAssetPath(r.GetComponent<MeshFilter>().sharedMesh),
                center = new[] { r.bounds.center.x, r.bounds.center.y, r.bounds.center.z }, size = new[] { r.bounds.size.x, r.bounds.size.y, r.bounds.size.z } }).ToArray();
            foreach (var renderer in rejected)
            {
                Undo.RecordObject(renderer, "Retain rejected legacy tree decorations");
                renderer.enabled = false;
                EditorUtility.SetDirty(renderer);
            }
            File.WriteAllText(Evidence + "/legacy-ground-retirement.json", JsonConvert.SerializeObject(new
            {
                changedUtc = DateTime.UtcNow.ToString("o"), retainedSources = before,
                trigger = "Native integration-01 four-quadrant captures show ENV_hill_mound as a floating shelf cutting the trunk and six smooth flattened root stones as artificial discs.",
                collision = "All seven rejected decorations have no enabled attached collider. Hill surface, plinth, stairs and new trunk collision preserved.",
                review = "Rebuild chunks, save/reopen and recapture the same native root views. New tree placement remains unchanged for comparison."
            }, Formatting.Indented));
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
        }
    }
}
