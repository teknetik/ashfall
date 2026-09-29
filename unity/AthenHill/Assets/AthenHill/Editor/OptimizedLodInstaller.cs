using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>
    /// 29 September 2026 rendering pass: installs the optimized Karaveen truck LOD chain and the
    /// Ward oasis tree shadow proxy + LOD2 (sources and review: art/optimization_20260929/README.md).
    ///
    /// One-time and narrowly scoped. It refuses to run over unsaved scene edits or over an existing
    /// install, never deletes anything (the original 3.09M-triangle truck renderer is disabled, the
    /// tree's visible LOD0/LOD1 meshes are kept and only stop casting shadows), keeps every existing
    /// transform, and writes ../evidence/rendering/20260929/lod-install.json.
    ///
    /// Copy this file to Assets/AthenHill/Editor/ and the meshes/textures to
    /// Assets/AthenHill/Art/Optimized/20260929/{Truck,Tree}/ before running it.
    /// </summary>
    public static class OptimizedLodInstaller
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/Optimized/20260929";
        const string TruckDir = Root + "/Truck";
        const string TreeDir = Root + "/Tree";
        const string Marker = "Optimized LODs 20260929";

        const string TruckRootName = "Karaveen truck";
        const string TruckVisualName = "Visual";
        const string TruckSourceFbx = "Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx";
        const string TruckMaterialPath = "Assets/AthenHill/Art/Imported/KaraveenMarket/Materials/KaraveenTruck.mat";
        const string TruckLod0 = TruckDir + "/KaraveenTruck_LOD0_exact.fbx";
        const string TruckLod1 = TruckDir + "/KaraveenTruck_LOD1.fbx";
        const string TruckLod2 = TruckDir + "/KaraveenTruck_LOD2.fbx";
        const string TruckShadowNear = TruckDir + "/KaraveenTruck_ShadowNear.fbx";
        const string TruckShadowProxy = TruckDir + "/KaraveenTruck_ShadowProxy.fbx";

        const string TreeRootName = "Ward oasis tree";
        const string TreeSourceFbx = "Assets/AthenHill/Art/HeroTree/WardTree_LOD0.fbx";
        const string TreeShadowFbx = TreeDir + "/WardTree_ShadowProxy.fbx";
        const string TreeLod2Fbx = TreeDir + "/WardTree_LOD2.fbx";
        static readonly string[] TreeParts = { "leaves", "branches", "trunk" };

        // Target switch distances in metres for the scene's player camera. They are converted to
        // screen-relative heights with the camera FOV and QualitySettings.lodBias at install time.
        // With the PC quality level's lodBias of 2, a switch for these sizes cannot happen closer
        // than size*bias/(2*tan(fov/2)) (height clamped below 1); the log records the effective distances.
        static readonly float[] TruckSwitchMetres = { 15f, 40f, 800f };   // LOD0->1, LOD1->2, cull
        static readonly float[] TreeSwitchMetres = { 25f, 45f };          // LOD0->1, LOD1->2 (cull kept)
        const float MaxRelativeHeight = 0.98f;
        const float MinLevelRatio = 0.75f;                                 // next level <= 75% of previous
        const string Evidence = "../../evidence/rendering/20260929/lod-install.json"; // from Assets/

        [MenuItem("Athen Hill/Rendering/Install truck and tree LODs")]
        public static void InstallFromMenu()
        {
            try
            {
                Install();
                EditorUtility.DisplayDialog("Optimized LODs", "Truck and tree LODs installed. See evidence/rendering/20260929/lod-install.json.", "OK");
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorUtility.DisplayDialog("Optimized LODs", exception.Message, "OK");
            }
        }

        /// <summary>Batch entry: Unity -batchmode -quit -executeMethod AthenHill.Editor.OptimizedLodInstaller.InstallBatch</summary>
        public static void InstallBatch()
        {
            try
            {
                Install();
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        public static void Install()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play Mode before installing LODs.");
            for (var i = 0; i < SceneManager.sceneCount; i++)
            {
                var open = SceneManager.GetSceneAt(i);
                if (open.isDirty) throw new InvalidOperationException($"Scene '{open.path}' has unsaved edits; save or revert them first.");
            }
            foreach (var path in new[] { TruckLod0, TruckLod1, TruckLod2, TruckShadowNear, TruckShadowProxy, TreeShadowFbx, TreeLod2Fbx })
                if (AssetDatabase.LoadMainAssetAtPath(path) == null || AssetDatabase.LoadAllAssetsAtPath(path).OfType<Mesh>().FirstOrDefault() == null)
                    throw new InvalidOperationException($"Optimized asset '{path}' is missing or failed to import (check the Console for FBX importer errors). Copy the art/optimization_20260929 files first.");

            // Open and validate the scene before touching any importer so a refused run changes nothing.
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var roots = scene.GetRootGameObjects();
            var truck = SingleRoot(roots, TruckRootName);
            var tree = SingleRoot(roots, TreeRootName);
            if (truck.transform.Find(Marker) != null || tree.transform.Find(Marker) != null || tree.transform.Find("Shadow proxy") != null)
                throw new InvalidOperationException("Optimized LODs are already installed; edit the saved scene objects instead of rerunning.");
            if (truck.GetComponent<LODGroup>() != null) throw new InvalidOperationException($"'{TruckRootName}' already has a LODGroup; refusing to replace it.");
            RequireUniform(truck.transform);
            RequireUniform(tree.transform);

            var log = new Dictionary<string, object>
            {
                ["installedUtc"] = DateTime.UtcNow.ToString("o"),
                ["unity"] = Application.unityVersion,
                ["scene"] = ScenePath,
                ["source"] = "art/optimization_20260929"
            };

            var importers = new List<object>();
            var truckSourceImporter = AssetImporter.GetAtPath(TruckSourceFbx) as ModelImporter;
            if (truckSourceImporter == null) throw new InvalidOperationException("Truck source ModelImporter is unavailable.");
            foreach (var path in new[] { TruckLod0, TruckLod1, TruckLod2, TruckShadowNear, TruckShadowProxy })
                importers.Add(ConfigureModel(path, truckSourceImporter));
            var treeSourceImporter = AssetImporter.GetAtPath(TreeSourceFbx) as ModelImporter;
            if (treeSourceImporter == null) throw new InvalidOperationException("Tree source ModelImporter is unavailable.");
            foreach (var path in new[] { TreeShadowFbx, TreeLod2Fbx })
                importers.Add(ConfigureModel(path, treeSourceImporter));
            var textures = new List<object>();
            foreach (var lod in new[] { "LOD1", "LOD2" })
            {
                var size = lod == "LOD1" ? 2048 : 1024;
                textures.Add(ConfigureTexture($"{TruckDir}/Textures/KaraveenTruck_{lod}_BaseColor.png", TextureImporterType.Default, true, size));
                textures.Add(ConfigureTexture($"{TruckDir}/Textures/KaraveenTruck_{lod}_Normal.png", TextureImporterType.NormalMap, false, size));
                textures.Add(ConfigureTexture($"{TruckDir}/Textures/KaraveenTruck_{lod}_MetallicSmoothness.png", TextureImporterType.Default, false, size));
            }
            log["importers"] = importers;
            log["textures"] = textures;
            AssetDatabase.SaveAssets();

            var camera = PlayerCamera();
            var fov = camera != null ? camera.fieldOfView : 60f;
            log["lodCamera"] = new
            {
                camera = camera != null ? camera.name : "(none found, 60 deg assumed)",
                verticalFov = fov,
                qualityLevel = QualitySettings.names[QualitySettings.GetQualityLevel()],
                lodBias = QualitySettings.lodBias
            };

            log["truck"] = InstallTruck(truck, fov);
            log["tree"] = InstallTree(tree, fov);

            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene)) throw new InvalidOperationException("Scene save failed.");
            AssetDatabase.SaveAssets();
            log["sceneSaved"] = true;

            var evidence = Path.GetFullPath(Path.Combine(Application.dataPath, Evidence));
            Directory.CreateDirectory(Path.GetDirectoryName(evidence));
            File.WriteAllText(evidence, JsonConvert.SerializeObject(log, Formatting.Indented,
                new JsonSerializerSettings { ReferenceLoopHandling = ReferenceLoopHandling.Ignore }));
            Debug.Log($"Optimized truck/tree LODs installed; evidence written to {evidence}.");
        }

        // ------------------------------------------------------------------ truck

        static object InstallTruck(GameObject truck, float fov)
        {
            var visual = truck.transform.Find(TruckVisualName);
            if (visual == null) throw new InvalidOperationException($"'{TruckRootName}/{TruckVisualName}' is missing.");
            var original = visual.GetComponent<MeshRenderer>();
            var originalFilter = visual.GetComponent<MeshFilter>();
            if (original == null || originalFilter == null || originalFilter.sharedMesh == null)
                throw new InvalidOperationException("The truck Visual has no MeshRenderer/MeshFilter with a mesh.");
            var material = AssetDatabase.LoadAssetAtPath<Material>(TruckMaterialPath);
            if (material == null) throw new InvalidOperationException($"Missing '{TruckMaterialPath}'.");
            var sceneMaterial = original.sharedMaterial;
            var lod1Material = BakedTruckMaterial(material, "LOD1");
            var lod2Material = BakedTruckMaterial(material, "LOD2");

            var container = new GameObject(Marker);
            container.transform.SetParent(truck.transform, false);
            container.layer = visual.gameObject.layer;

            var lod0 = AddMeshChild(container.transform, "LOD0 (592k, UV-exact)", SingleMesh(TruckLod0), visual, original, material, ShadowCastingMode.Off);
            var near = AddMeshChild(container.transform, "Shadow near (LOD0 range)", SingleMesh(TruckShadowNear), visual, original, material, ShadowCastingMode.ShadowsOnly);
            var lod1 = AddMeshChild(container.transform, "LOD1 (40k, baked 2k)", SingleMesh(TruckLod1), visual, original, lod1Material, ShadowCastingMode.Off);
            var proxy1 = AddMeshChild(container.transform, "Shadow proxy (LOD1 range)", SingleMesh(TruckShadowProxy), visual, original, material, ShadowCastingMode.ShadowsOnly);
            var lod2 = AddMeshChild(container.transform, "LOD2 (10k, baked 1k)", SingleMesh(TruckLod2), visual, original, lod2Material, ShadowCastingMode.Off);
            var proxy2 = AddMeshChild(container.transform, "Shadow proxy (LOD2 range)", SingleMesh(TruckShadowProxy), visual, original, material, ShadowCastingMode.ShadowsOnly);

            var boundsCheck = CompareBounds(originalFilter.sharedMesh, lod0.GetComponent<MeshFilter>().sharedMesh, 0.02f, "truck LOD0");
            CompareBounds(originalFilter.sharedMesh, lod1.GetComponent<MeshFilter>().sharedMesh, 0.03f, "truck LOD1");
            CompareBounds(originalFilter.sharedMesh, lod2.GetComponent<MeshFilter>().sharedMesh, 0.03f, "truck LOD2");
            CompareBounds(originalFilter.sharedMesh, near.GetComponent<MeshFilter>().sharedMesh, 0.03f, "truck ShadowNear");

            var originalWasEnabled = original.enabled;
            var originalShadows = original.shadowCastingMode.ToString();
            original.enabled = false; // kept for provenance / rollback, not deleted

            var group = truck.AddComponent<LODGroup>();
            group.fadeMode = LODFadeMode.CrossFade;
            group.animateCrossFading = false;
            group.SetLODs(new[]
            {
                new LOD(1f, new Renderer[] { lod0.GetComponent<Renderer>(), near.GetComponent<Renderer>() }),
                new LOD(0.5f, new Renderer[] { lod1.GetComponent<Renderer>(), proxy1.GetComponent<Renderer>() }),
                new LOD(0.1f, new Renderer[] { lod2.GetComponent<Renderer>(), proxy2.GetComponent<Renderer>() })
            });
            group.RecalculateBounds();
            var worldSize = group.size * MaxAbs(truck.transform.lossyScale);
            var heights = HeightsFor(TruckSwitchMetres, worldSize, fov);
            var lods = group.GetLODs();
            for (var i = 0; i < lods.Length; i++)
            {
                lods[i].screenRelativeTransitionHeight = heights[i];
                lods[i].fadeTransitionWidth = 0.12f;
            }
            group.SetLODs(lods);

            return new
            {
                root = TruckRootName,
                container = Marker,
                originalRenderer = new { path = $"{TruckRootName}/{TruckVisualName}", wasEnabled = originalWasEnabled, nowEnabled = original.enabled, shadowCastingMode = originalShadows, mesh = originalFilter.sharedMesh.name, triangles = Triangles(originalFilter.sharedMesh) },
                material = TruckMaterialPath,
                sceneRendererMaterial = sceneMaterial != null ? AssetDatabase.GetAssetPath(sceneMaterial) : "(none)",
                materialMatchesScene = sceneMaterial == material,
                lodMaterials = new[] { AssetDatabase.GetAssetPath(lod1Material), AssetDatabase.GetAssetPath(lod2Material) },
                levels = LevelRecords(group, worldSize, fov),
                lodGroupSize = group.size,
                lodGroupWorldSize = worldSize,
                targetSwitchMetres = TruckSwitchMetres,
                transformCopiedFrom = $"{TruckRootName}/{TruckVisualName}",
                localPosition = V(visual.localPosition),
                localRotation = V(visual.localEulerAngles),
                localScale = V(visual.localScale),
                bounds = boundsCheck
            };
        }

        static Material BakedTruckMaterial(Material template, string lod)
        {
            var path = $"{TruckDir}/KaraveenTruck_{lod}.mat";
            var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (existing != null) return existing;
            if (!AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(template), path))
                throw new InvalidOperationException($"Could not create '{path}'.");
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null) throw new InvalidOperationException($"'{path}' did not import.");
            var baseMap = LoadTexture($"{TruckDir}/Textures/KaraveenTruck_{lod}_BaseColor.png");
            var normal = LoadTexture($"{TruckDir}/Textures/KaraveenTruck_{lod}_Normal.png");
            var metallic = LoadTexture($"{TruckDir}/Textures/KaraveenTruck_{lod}_MetallicSmoothness.png");
            // Same shader and scalar values as KaraveenTruck.mat; only the maps change (new UV0).
            if (material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap", baseMap);
            if (material.HasProperty("_MainTex")) material.SetTexture("_MainTex", baseMap);
            if (material.HasProperty("_BumpMap")) material.SetTexture("_BumpMap", normal);
            if (material.HasProperty("_MetallicGlossMap")) material.SetTexture("_MetallicGlossMap", metallic);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            EditorUtility.SetDirty(material);
            return material;
        }

        // ------------------------------------------------------------------- tree

        static object InstallTree(GameObject tree, float fov)
        {
            var group = tree.GetComponent<LODGroup>();
            if (group == null) throw new InvalidOperationException($"'{TreeRootName}' has no LODGroup.");
            var src0 = tree.transform.Find("Source LOD 0");
            var src1 = tree.transform.Find("Source LOD 1");
            if (src0 == null || src1 == null) throw new InvalidOperationException("Expected 'Source LOD 0' and 'Source LOD 1' under the tree.");
            var before = group.GetLODs();
            if (before.Length != 2) throw new InvalidOperationException($"Expected the tree's two-level LODGroup, found {before.Length} levels.");
            var beforeRecord = before.Select((l, i) => new
            {
                level = i,
                screenRelativeHeight = l.screenRelativeTransitionHeight,
                renderers = l.renderers.Where(r => r != null).Select(r => new { name = r.name, shadowCastingMode = r.shadowCastingMode.ToString() }).ToArray()
            }).ToArray();
            var worldSize = group.size * MaxAbs(tree.transform.lossyScale);

            // Materials and casting modes by part name, from the visible LOD0 renderers.
            var partMaterial = new Dictionary<string, Material>();
            var partRenderer = new Dictionary<string, Renderer>();
            var partCasting = new Dictionary<string, ShadowCastingMode>();
            foreach (var renderer in src0.GetComponentsInChildren<Renderer>(true))
            {
                var part = PartOf(renderer.name);
                if (part == null) continue;
                partMaterial[part] = renderer.sharedMaterial;
                partRenderer[part] = renderer;
                partCasting[part] = renderer.shadowCastingMode;
            }
            foreach (var part in TreeParts)
                if (!partMaterial.ContainsKey(part) || partMaterial[part] == null) throw new InvalidOperationException($"No LOD0 '{part}' renderer/material found under Source LOD 0.");

            // Visible LOD0/LOD1 meshes stop casting; nothing is removed.
            var shadowChanges = new List<object>();
            foreach (var renderer in before.SelectMany(l => l.renderers).Where(r => r != null).Distinct())
            {
                shadowChanges.Add(new { renderer = renderer.name, before = renderer.shadowCastingMode.ToString(), after = ShadowCastingMode.Off.ToString() });
                renderer.shadowCastingMode = ShadowCastingMode.Off;
            }

            var shadowModel = AssetDatabase.LoadAssetAtPath<GameObject>(TreeShadowFbx);
            var lod2Model = AssetDatabase.LoadAssetAtPath<GameObject>(TreeLod2Fbx);
            var marker = new GameObject(Marker);
            marker.transform.SetParent(tree.transform, false);
            var shadowRoot = CopyLocal("Shadow proxy", tree.transform, src0);
            var shadowNear = CopyLocal("LOD0 range", shadowRoot.transform, null);
            var shadowMid = CopyLocal("LOD1 range", shadowRoot.transform, null);
            var lod2Root = CopyLocal("Source LOD 2", tree.transform, src0);

            var transformChecks = new List<object>();
            var nearRenderers = AddTreeParts(shadowModel, shadowNear.transform, partMaterial, partRenderer, _ => ShadowCastingMode.ShadowsOnly, transformChecks, "shadow LOD0 range");
            var midRenderers = AddTreeParts(shadowModel, shadowMid.transform, partMaterial, partRenderer, _ => ShadowCastingMode.ShadowsOnly, transformChecks, "shadow LOD1 range");
            // LOD2 is cheap (~0.29M) and is the only geometry beyond the LOD1 switch, so it casts itself
            // with the casting mode the source part had (leaves two-sided).
            var lod2Renderers = AddTreeParts(lod2Model, lod2Root.transform, partMaterial, partRenderer, part => partCasting[part] == ShadowCastingMode.Off ? ShadowCastingMode.On : partCasting[part], transformChecks, "LOD2");

            var heights = HeightsFor(TreeSwitchMetres, worldSize, fov);
            var cull = Mathf.Min(before[1].screenRelativeTransitionHeight, heights[1] * MinLevelRatio);
            var after = new[]
            {
                new LOD(heights[0], before[0].renderers.Concat(nearRenderers).ToArray()) { fadeTransitionWidth = before[0].fadeTransitionWidth },
                new LOD(heights[1], before[1].renderers.Concat(midRenderers).ToArray()) { fadeTransitionWidth = before[1].fadeTransitionWidth },
                new LOD(cull, lod2Renderers.ToArray()) { fadeTransitionWidth = before[1].fadeTransitionWidth }
            };
            group.SetLODs(after);

            return new
            {
                root = TreeRootName,
                lodGroupSize = group.size,
                lodGroupWorldSize = worldSize,
                targetSwitchMetres = TreeSwitchMetres,
                before = new { levels = beforeRecord, effectiveMetres = before.Select(l => DistanceFor(l.screenRelativeTransitionHeight, worldSize, fov)).ToArray() },
                after = LevelRecords(group, worldSize, fov),
                shadowCastingChanges = shadowChanges,
                shadowProxy = new { path = $"{TreeRootName}/Shadow proxy", source = TreeShadowFbx, triangles = nearRenderers.Sum(r => Triangles(r.GetComponent<MeshFilter>().sharedMesh)) },
                lod2 = new { path = $"{TreeRootName}/Source LOD 2", source = TreeLod2Fbx, triangles = lod2Renderers.Sum(r => Triangles(r.GetComponent<MeshFilter>().sharedMesh)) },
                transformChecks,
                materials = partMaterial.ToDictionary(p => p.Key, p => AssetDatabase.GetAssetPath(p.Value))
            };
        }

        static List<Renderer> AddTreeParts(GameObject model, Transform parent, Dictionary<string, Material> materials,
            Dictionary<string, Renderer> sourceRenderers, Func<string, ShadowCastingMode> casting, List<object> checks, string label)
        {
            if (model == null) throw new InvalidOperationException($"{label}: model asset did not load.");
            var result = new List<Renderer>();
            foreach (var part in TreeParts)
            {
                var filter = model.GetComponentsInChildren<MeshFilter>(true).SingleOrDefault(f => PartOf(f.name) == part);
                if (filter == null || filter.sharedMesh == null) throw new InvalidOperationException($"{label}: no '{part}' mesh in {AssetDatabase.GetAssetPath(model)}.");
                var source = sourceRenderers[part].transform;
                var go = new GameObject($"{filter.name}");
                go.transform.SetParent(parent, false);
                // Same node transform as the matching source part (identical FBX Model node values).
                go.transform.localPosition = source.localPosition;
                go.transform.localRotation = source.localRotation;
                go.transform.localScale = source.localScale;
                checks.Add(new
                {
                    label,
                    part,
                    modelLocalPosition = V(filter.transform.localPosition),
                    sourceLocalPosition = V(source.localPosition),
                    modelLocalRotation = V(filter.transform.localEulerAngles),
                    sourceLocalRotation = V(source.localEulerAngles),
                    modelLocalScale = V(filter.transform.localScale),
                    sourceLocalScale = V(source.localScale),
                    match = Approximately(filter.transform.localPosition, source.localPosition) &&
                            Quaternion.Angle(filter.transform.localRotation, source.localRotation) < 0.01f &&
                            Approximately(filter.transform.localScale, source.localScale)
                });
                go.layer = source.gameObject.layer;
                GameObjectUtility.SetStaticEditorFlags(go, GameObjectUtility.GetStaticEditorFlags(source.gameObject));
                go.AddComponent<MeshFilter>().sharedMesh = filter.sharedMesh;
                var renderer = go.AddComponent<MeshRenderer>();
                CopyRendererSettings(sourceRenderers[part], renderer);
                renderer.sharedMaterial = materials[part];
                renderer.shadowCastingMode = casting(part);
                CompareBounds(sourceRenderers[part].GetComponent<MeshFilter>().sharedMesh, filter.sharedMesh, part == "leaves" ? 0.08f : 0.05f, $"tree {label} {part}");
                result.Add(renderer);
            }
            return result;
        }

        static GameObject CopyLocal(string name, Transform parent, Transform copyFrom)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            if (copyFrom != null)
            {
                go.transform.localPosition = copyFrom.localPosition;
                go.transform.localRotation = copyFrom.localRotation;
                go.transform.localScale = copyFrom.localScale;
                go.layer = copyFrom.gameObject.layer;
            }
            return go;
        }

        // ---------------------------------------------------------------- helpers

        static GameObject AddMeshChild(Transform parent, string name, Mesh mesh, Transform copyTransform, MeshRenderer template,
            Material material, ShadowCastingMode casting)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = copyTransform.localPosition;
            go.transform.localRotation = copyTransform.localRotation;
            go.transform.localScale = copyTransform.localScale;
            go.layer = copyTransform.gameObject.layer;
            GameObjectUtility.SetStaticEditorFlags(go, GameObjectUtility.GetStaticEditorFlags(copyTransform.gameObject));
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.AddComponent<MeshRenderer>();
            CopyRendererSettings(template, renderer);
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = casting;
            return go;
        }

        static void CopyRendererSettings(Renderer from, Renderer to)
        {
            to.receiveShadows = from.receiveShadows;
            to.lightProbeUsage = from.lightProbeUsage;
            to.reflectionProbeUsage = from.reflectionProbeUsage;
            to.probeAnchor = from.probeAnchor;
            to.motionVectorGenerationMode = from.motionVectorGenerationMode;
            to.allowOcclusionWhenDynamic = from.allowOcclusionWhenDynamic;
            to.renderingLayerMask = from.renderingLayerMask;
            to.staticShadowCaster = false;
            to.enabled = true;
        }

        static object ConfigureModel(string path, ModelImporter source)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) throw new InvalidOperationException($"'{path}' is not a model asset.");
            // Same unit/axis handling as the source FBX so the meshes land at the identical transform.
            importer.globalScale = source.globalScale;
            importer.useFileScale = source.useFileScale;
            importer.useFileUnits = source.useFileUnits;
            importer.bakeAxisConversion = source.bakeAxisConversion;
            importer.importNormals = ModelImporterNormals.Import;
            importer.importTangents = ModelImporterTangents.CalculateMikk;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.importCameras = false;
            importer.importLights = false;
            importer.importVisibility = true;
            importer.importBlendShapes = false;
            importer.importAnimation = false;
            importer.animationType = ModelImporterAnimationType.None;
            importer.isReadable = false;
            importer.meshCompression = ModelImporterMeshCompression.Off;
            importer.weldVertices = true;
            importer.indexFormat = ModelImporterIndexFormat.Auto;
            importer.generateSecondaryUV = false;
            importer.addCollider = false;
            importer.SaveAndReimport();
            return new { path, globalScale = importer.globalScale, useFileScale = importer.useFileScale, bakeAxisConversion = importer.bakeAxisConversion, copiedFrom = AssetDatabase.GetAssetPath(source) };
        }

        static object ConfigureTexture(string path, TextureImporterType type, bool srgb, int maxSize)
        {
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null) throw new InvalidOperationException($"Missing texture '{path}'.");
            importer.textureType = type;
            importer.sRGBTexture = srgb;
            importer.alphaSource = TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = false;
            importer.mipmapEnabled = true;
            importer.streamingMipmaps = true;
            importer.maxTextureSize = maxSize;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.anisoLevel = 4;
            importer.SaveAndReimport();
            return new { path, type = type.ToString(), srgb, maxSize };
        }

        static Texture2D LoadTexture(string path)
        {
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null) throw new InvalidOperationException($"Missing texture '{path}'.");
            return texture;
        }

        static Mesh SingleMesh(string path)
        {
            var meshes = AssetDatabase.LoadAllAssetsAtPath(path).OfType<Mesh>().ToArray();
            if (meshes.Length != 1) throw new InvalidOperationException($"'{path}' should contain exactly one mesh, found {meshes.Length}.");
            return meshes[0];
        }

        static GameObject SingleRoot(GameObject[] roots, string name)
        {
            var matches = roots.Where(r => r.name == name).ToArray();
            if (matches.Length != 1) throw new InvalidOperationException($"Expected one scene root '{name}', found {matches.Length}.");
            return matches[0];
        }

        static Camera PlayerCamera()
        {
            var cameras = UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include);
            // The follow camera is the gameplay view; fall back to the MainCamera tag.
            foreach (var camera in cameras)
                if (camera.GetComponents<MonoBehaviour>().Any(b => b != null && b.GetType().Name == "FollowCamera")) return camera;
            foreach (var camera in cameras)
                if (camera.CompareTag("MainCamera")) return camera;
            return null;
        }

        static float[] HeightsFor(float[] metres, float worldSize, float fov)
        {
            var heights = new float[metres.Length];
            var previous = MaxRelativeHeight / MinLevelRatio;
            for (var i = 0; i < metres.Length; i++)
            {
                var h = worldSize * QualitySettings.lodBias / (2f * metres[i] * Mathf.Tan(0.5f * fov * Mathf.Deg2Rad));
                h = Mathf.Min(h, MaxRelativeHeight, previous * MinLevelRatio);
                heights[i] = Mathf.Max(h, 0.001f);
                previous = heights[i];
            }
            return heights;
        }

        static float DistanceFor(float height, float worldSize, float fov) =>
            worldSize * QualitySettings.lodBias / (2f * Mathf.Max(height, 1e-5f) * Mathf.Tan(0.5f * fov * Mathf.Deg2Rad));

        static object[] LevelRecords(LODGroup group, float worldSize, float fov) =>
            group.GetLODs().Select((l, i) => (object)new
            {
                level = i,
                screenRelativeHeight = l.screenRelativeTransitionHeight,
                switchesAtMetres = DistanceFor(l.screenRelativeTransitionHeight, worldSize, fov),
                fadeTransitionWidth = l.fadeTransitionWidth,
                renderers = l.renderers.Where(r => r != null).Select(r => new
                {
                    name = r.name,
                    shadowCastingMode = r.shadowCastingMode.ToString(),
                    triangles = r.GetComponent<MeshFilter>() != null ? Triangles(r.GetComponent<MeshFilter>().sharedMesh) : 0
                }).ToArray()
            }).ToArray();

        static object CompareBounds(Mesh reference, Mesh candidate, float tolerance, string label)
        {
            if (reference == null || candidate == null) throw new InvalidOperationException($"{label}: missing mesh for bounds check.");
            var a = reference.bounds;
            var b = candidate.bounds;
            var size = Mathf.Max(a.size.x, Mathf.Max(a.size.y, a.size.z));
            var delta = Mathf.Max((a.min - b.min).magnitude, (a.max - b.max).magnitude) / Mathf.Max(size, 1e-6f);
            if (delta > tolerance)
                throw new InvalidOperationException($"{label}: bounds differ by {delta:P1} of the source size (min {a.min} vs {b.min}, max {a.max} vs {b.max}); check the importer scale.");
            return new { label, sourceMin = V(a.min), sourceMax = V(a.max), candidateMin = V(b.min), candidateMax = V(b.max), relativeDelta = delta };
        }

        static string PartOf(string name)
        {
            var lower = name.ToLowerInvariant();
            foreach (var part in TreeParts)
                if (lower.EndsWith(part)) return part;
            return null;
        }

        static void RequireUniform(Transform t)
        {
            var s = t.lossyScale;
            if (Mathf.Abs(Mathf.Abs(s.x) - Mathf.Abs(s.y)) > 1e-4f || Mathf.Abs(Mathf.Abs(s.x) - Mathf.Abs(s.z)) > 1e-4f)
                throw new InvalidOperationException($"'{t.name}' must have uniform scale, found {s}.");
        }

        static int Triangles(Mesh mesh)
        {
            if (mesh == null) return 0;
            long total = 0;
            for (var i = 0; i < mesh.subMeshCount; i++) total += mesh.GetIndexCount(i) / 3;
            return (int)total;
        }

        static bool Approximately(Vector3 a, Vector3 b) => (a - b).sqrMagnitude < 1e-6f * Mathf.Max(1f, a.sqrMagnitude);
        static float MaxAbs(Vector3 v) => Mathf.Max(Mathf.Abs(v.x), Mathf.Max(Mathf.Abs(v.y), Mathf.Abs(v.z)));
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
    }
}
