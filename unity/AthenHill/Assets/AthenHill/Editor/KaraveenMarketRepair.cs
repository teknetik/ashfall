using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>
    /// One-time, narrowly scoped repair for the two user-placed Karaveen market FBXs.
    /// It retains their world transforms, keeps the imported sources intact, and
    /// produces ordinary reusable prefabs with simple static collision proxies.
    /// The repair runs after Unity imports this editor script.
    /// </summary>
    [InitializeOnLoad]
    public static class KaraveenMarketRepair
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string TruckSource = "Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx";
        const string TruckSourceMaterial = "Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Material.001.mat";
        const string TruckMaterial = "Assets/AthenHill/Art/Imported/KaraveenMarket/Materials/KaraveenTruck.mat";
        const string TruckPrefab = "Assets/AthenHill/Prefabs/KaraveenTruck.prefab";
        const string StallSource = "Assets/Market/karaveen-artisan-stall-v01.fbx";
        const string StallPrefab = "Assets/AthenHill/Prefabs/KaraveenArtisanStall.prefab";
        const string Evidence = "../evidence/karaveen-market/20260911/repair.json";
        const string PlacementAudit = "../evidence/karaveen-market/20260911/placement-audit.json";

        static KaraveenMarketRepair()
        {
            // The user's Editor already owns the project lock, so perform the
            // authorized one-time repair there after this script compiles.
            if (!Application.isBatchMode) EditorApplication.delayCall += AutoApply;
        }

        static void AutoApply()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating)
            {
                EditorApplication.delayCall += AutoApply;
                return;
            }
            if (AssetDatabase.LoadAssetAtPath<GameObject>(TruckPrefab) || AssetDatabase.LoadAssetAtPath<GameObject>(StallPrefab)) return;
            try { Apply(); }
            catch (Exception exception) { Debug.LogException(exception); }
        }

        [MenuItem("Athen Hill/Karaveen/Repair imported market props")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play Mode before repairing market props.");
            if (AssetDatabase.LoadAssetAtPath<GameObject>(TruckPrefab) || AssetDatabase.LoadAssetAtPath<GameObject>(StallPrefab))
                throw new InvalidOperationException("Karaveen repair prefabs already exist. Edit the saved prefabs instead of rerunning this installer.");

            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var roots = scene.GetRootGameObjects();
            var truck = roots.SingleOrDefault(go => go.name == "Mudrunner Convoy")
                ?? throw new InvalidOperationException("Expected the user-placed root 'Mudrunner Convoy'.");
            var stall = roots.SingleOrDefault(go => go.name == "karaveen-artisan-stall-v01")
                ?? throw new InvalidOperationException("Expected the user-placed root 'karaveen-artisan-stall-v01'.");
            RequirePrefabSource(truck, TruckSource);
            RequirePrefabSource(stall, StallSource);

            var truckPosition = truck.transform.position;
            var truckRotation = truck.transform.rotation;
            var truckScale = truck.transform.localScale;
            if (!Uniform(truckScale) || truckScale.x < 10f)
                throw new InvalidOperationException($"Unexpected truck scale {truckScale}; refusing to reinterpret its units.");

            var importer = AssetImporter.GetAtPath(TruckSource) as ModelImporter
                ?? throw new InvalidOperationException("Truck ModelImporter is unavailable.");
            var oldImportScale = importer.globalScale;
            importer.globalScale = oldImportScale * truckScale.x;
            importer.importCameras = false;
            importer.importLights = false;
            importer.SaveAndReimport();

            ConfigurePropImporter(StallSource);

            // Re-resolve after FBX reimport, then put the corrected asset beneath a
            // metre-scale scene root while preserving the user's placement.
            truck = SceneManager.GetActiveScene().GetRootGameObjects().Single(go => go.name == "Mudrunner Convoy");
            var truckRoot = new GameObject("Karaveen truck");
            truckRoot.transform.SetPositionAndRotation(truckPosition, truckRotation);
            truckRoot.transform.localScale = Vector3.one;
            truck.transform.SetParent(truckRoot.transform, false);
            truck.transform.localPosition = Vector3.zero;
            truck.transform.localRotation = Quaternion.identity;
            truck.transform.localScale = Vector3.one;
            truck.name = "Visual";

            var truckRenderers = ValidRenderers(truckRoot);
            var truckMaterial = CreateTruckMaterial();
            foreach (var renderer in truckRenderers)
            {
                renderer.enabled = true;
                renderer.sharedMaterials = renderer.sharedMaterials.Select(_ => truckMaterial).ToArray();
            }
            var truckBounds = LocalBounds(truckRoot.transform, truckRenderers);
            var truckCollider = truckRoot.AddComponent<BoxCollider>();
            truckCollider.center = truckBounds.center;
            truckCollider.size = truckBounds.size;

            var stallPosition = stall.transform.position;
            var stallRotation = stall.transform.rotation;
            var stallScale = stall.transform.localScale;
            if (!Uniform(stallScale)) throw new InvalidOperationException($"Stall must retain uniform scale, found {stallScale}.");
            var stallRoot = new GameObject("Karaveen artisan stall");
            stallRoot.transform.SetPositionAndRotation(stallPosition, stallRotation);
            stallRoot.transform.localScale = stallScale;
            stall.transform.SetParent(stallRoot.transform, false);
            stall.transform.localPosition = Vector3.zero;
            stall.transform.localRotation = Quaternion.identity;
            stall.transform.localScale = Vector3.one;
            stall.name = "Visual";

            DisableImportedStage(stallRoot);
            var stallRenderers = RuntimeRenderers(stallRoot);
            foreach (var renderer in stallRenderers) renderer.enabled = true;
            var stallBounds = LocalBounds(stallRoot.transform, stallRenderers);
            AddStallPostColliders(stallRoot, stallBounds);
            var counterRenderers = stallRenderers.Where(r =>
            {
                var name = r.name.ToLowerInvariant();
                return name.Contains("cabinet") || name.Contains("cupboard") || name.Contains("counter") ||
                       name.Contains("drawer") || name.Contains("worktop");
            }).ToArray();
            if (counterRenderers.Length > 0) AddBox(stallRoot.transform, "Counter collision", LocalBounds(stallRoot.transform, counterRenderers));

            Directory.CreateDirectory(Path.GetDirectoryName(TruckPrefab));
            PrefabUtility.SaveAsPrefabAssetAndConnect(truckRoot, TruckPrefab, InteractionMode.AutomatedAction);
            PrefabUtility.SaveAsPrefabAssetAndConnect(stallRoot, StallPrefab, InteractionMode.AutomatedAction);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();

            var evidencePath = Path.GetFullPath(Evidence);
            Directory.CreateDirectory(Path.GetDirectoryName(evidencePath));
            File.WriteAllText(evidencePath, JsonConvert.SerializeObject(new
            {
                repairedUtc = DateTime.UtcNow.ToString("o"),
                scene = ScenePath,
                focusLoss = "Editor focus changes no longer pause gameplay; standalone focus-loss pause is retained.",
                truck = new
                {
                    source = TruckSource,
                    prefab = TruckPrefab,
                    material = TruckMaterial,
                    position = V(truckRoot.transform.position),
                    rotation = V(truckRoot.transform.eulerAngles),
                    originalSceneScale = V(truckScale),
                    oldImportScale,
                    newImportScale = importer.globalScale,
                    renderers = truckRenderers.Length,
                    meshes = truckRenderers.Select(r => MeshOf(r).name).Distinct().ToArray(),
                    colliderCenter = V(truckCollider.center),
                    colliderSize = V(truckCollider.size)
                },
                stall = new
                {
                    source = StallSource,
                    prefab = StallPrefab,
                    position = V(stallRoot.transform.position),
                    rotation = V(stallRoot.transform.eulerAngles),
                    scale = V(stallRoot.transform.localScale),
                    renderers = stallRenderers.Length,
                    collisionProxies = stallRoot.GetComponentsInChildren<BoxCollider>().Select(c => c.name).ToArray()
                }
            }, Formatting.Indented));
            Debug.Log($"Karaveen market repair complete: {truckRenderers.Length} truck renderers, {stallRenderers.Length} stall renderers.");
        }

        [MenuItem("Athen Hill/Karaveen/Refresh imported market collision")]
        public static void RefreshCollision()
        {
            var truckRoot = PrefabUtility.LoadPrefabContents(TruckPrefab);
            try
            {
                var renderers = ValidRenderers(truckRoot);
                foreach (var existingCollider in truckRoot.GetComponents<BoxCollider>()) UnityEngine.Object.DestroyImmediate(existingCollider);
                var bounds = LocalBounds(truckRoot.transform, renderers);
                var collider = truckRoot.AddComponent<BoxCollider>();
                collider.center = bounds.center;
                collider.size = bounds.size;
                PrefabUtility.SaveAsPrefabAsset(truckRoot, TruckPrefab);

                var evidencePath = Path.GetFullPath(Evidence);
                if (File.Exists(evidencePath))
                {
                    var evidence = JObject.Parse(File.ReadAllText(evidencePath));
                    evidence["truck"]["colliderCenter"] = new JArray(V(collider.center));
                    evidence["truck"]["colliderSize"] = new JArray(V(collider.size));
                    evidence["collisionRefreshedUtc"] = DateTime.UtcNow.ToString("o");
                    File.WriteAllText(evidencePath, evidence.ToString(Formatting.Indented));
                }
            }
            finally { PrefabUtility.UnloadPrefabContents(truckRoot); }

            var stallRoot = PrefabUtility.LoadPrefabContents(StallPrefab);
            try
            {
                foreach (var collider in stallRoot.GetComponentsInChildren<BoxCollider>(true))
                    UnityEngine.Object.DestroyImmediate(collider.gameObject);
                DisableImportedStage(stallRoot);
                var renderers = RuntimeRenderers(stallRoot);
                var bounds = LocalBounds(stallRoot.transform, renderers);
                AddStallPostColliders(stallRoot, bounds);
                var counterRenderers = renderers.Where(r =>
                {
                    var name = r.name.ToLowerInvariant();
                    return name.Contains("cabinet") || name.Contains("cupboard") || name.Contains("counter") ||
                           name.Contains("drawer") || name.Contains("worktop");
                }).ToArray();
                if (counterRenderers.Length > 0) AddBox(stallRoot.transform, "Counter collision", LocalBounds(stallRoot.transform, counterRenderers));
                PrefabUtility.SaveAsPrefabAsset(stallRoot, StallPrefab);
            }
            finally { PrefabUtility.UnloadPrefabContents(stallRoot); }

            AssetDatabase.SaveAssets();
            Debug.Log("Karaveen market collision refreshed from mesh-local bounds.");
        }

        [MenuItem("Athen Hill/Karaveen/Repair West Gate spawn view")]
        public static void RepairWestGateSpawnView()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play Mode before repairing the spawn view.");
            ConfigurePropImporter(TruckSource);
            ConfigurePropImporter(StallSource);

            var stallRoot = PrefabUtility.LoadPrefabContents(StallPrefab);
            Bounds stallBounds;
            int removedStageRenderers;
            try
            {
                removedStageRenderers = DisableImportedStage(stallRoot);
                foreach (var collider in stallRoot.GetComponentsInChildren<BoxCollider>(true))
                    UnityEngine.Object.DestroyImmediate(collider.gameObject);
                var renderers = RuntimeRenderers(stallRoot);
                stallBounds = LocalBounds(stallRoot.transform, renderers);
                AddStallPostColliders(stallRoot, stallBounds);
                var counterRenderers = renderers.Where(r =>
                {
                    var name = r.name.ToLowerInvariant();
                    return name.Contains("cabinet") || name.Contains("cupboard") || name.Contains("counter") ||
                           name.Contains("drawer") || name.Contains("worktop");
                }).ToArray();
                if (counterRenderers.Length > 0)
                    AddBox(stallRoot.transform, "Counter collision", LocalBounds(stallRoot.transform, counterRenderers));
                PrefabUtility.SaveAsPrefabAsset(stallRoot, StallPrefab);
            }
            finally { PrefabUtility.UnloadPrefabContents(stallRoot); }

            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var spawn = GameObject.Find("west_gate")?.transform
                ?? throw new InvalidOperationException("West Gate spawn is unavailable.");
            var player = GameObject.Find("Player")?.transform
                ?? throw new InvalidOperationException("Player root is unavailable.");
            player.position = spawn.position + Vector3.up * .015f;
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();

            var evidencePath = Path.GetFullPath(Evidence);
            var evidence = File.Exists(evidencePath) ? JObject.Parse(File.ReadAllText(evidencePath)) : new JObject();
            evidence["spawnViewRepair"] = JObject.FromObject(new
            {
                repairedUtc = DateTime.UtcNow.ToString("o"),
                spawn = V(spawn.position),
                player = V(player.position),
                removedImportedStageRenderers = removedStageRenderers,
                runtimeStallBoundsCenter = V(stallBounds.center),
                runtimeStallBoundsSize = V(stallBounds.size),
                importedCameras = false,
                importedLights = false
            });
            Directory.CreateDirectory(Path.GetDirectoryName(evidencePath));
            File.WriteAllText(evidencePath, evidence.ToString(Formatting.Indented));
            Debug.Log($"West Gate spawn view repaired; excluded {removedStageRenderers} studio renderer(s), runtime stall size {stallBounds.size}.");
        }

        [MenuItem("Athen Hill/Karaveen/Write placement audit")]
        public static void WritePlacementAudit()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var roots = scene.GetRootGameObjects();
            var truck = roots.Single(go => go.name == "Karaveen truck");
            var stall = roots.Single(go => go.name == "Karaveen artisan stall");
            var spawn = GameObject.Find("west_gate")?.transform
                ?? throw new InvalidOperationException("West Gate spawn is unavailable.");
            var truckRenderers = ValidRenderers(truck);
            var stallRenderers = ValidRenderers(stall);
            var path = Path.GetFullPath(PlacementAudit);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, JsonConvert.SerializeObject(new
            {
                auditedUtc = DateTime.UtcNow.ToString("o"),
                spawn = V(spawn.position),
                truck = PlacementRecord(truck, truckRenderers),
                stall = PlacementRecord(stall, stallRenderers),
                stallRenderers = stallRenderers.Select(renderer =>
                {
                    var bounds = LocalBounds(stall.transform, new[] { renderer });
                    var mesh = MeshOf(renderer);
                    return new
                    {
                        path = TransformPath(stall.transform, renderer.transform),
                        center = V(bounds.center),
                        size = V(bounds.size),
                        distanceFromRoot = bounds.center.magnitude,
                        vertices = mesh ? mesh.vertexCount : 0
                    };
                }).OrderByDescending(item => item.distanceFromRoot).ToArray()
            }, Formatting.Indented));
            Debug.Log($"Karaveen placement audit written to {path}.");
        }

        static object PlacementRecord(GameObject root, Renderer[] renderers)
        {
            var bounds = LocalBounds(root.transform, renderers);
            var worldCenter = root.transform.TransformPoint(bounds.center);
            return new
            {
                position = V(root.transform.position),
                localBoundsCenter = V(bounds.center),
                localBoundsSize = V(bounds.size),
                worldBoundsCenter = V(worldCenter),
                rendererCount = renderers.Length
            };
        }

        static string TransformPath(Transform root, Transform current)
        {
            var value = current.name;
            while (current.parent && current.parent != root)
            {
                current = current.parent;
                value = current.name + "/" + value;
            }
            return value;
        }

        static void RequirePrefabSource(GameObject instance, string expected)
        {
            var actual = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(instance);
            if (actual != expected) throw new InvalidOperationException($"'{instance.name}' comes from '{actual}', expected '{expected}'.");
        }

        static Material CreateTruckMaterial()
        {
            Directory.CreateDirectory(Path.GetDirectoryName(TruckMaterial));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            if (!AssetDatabase.CopyAsset(TruckSourceMaterial, TruckMaterial))
                throw new InvalidOperationException("Could not create the editable truck material variant.");
            AssetDatabase.ImportAsset(TruckMaterial, ImportAssetOptions.ForceSynchronousImport);
            var material = AssetDatabase.LoadAssetAtPath<Material>(TruckMaterial)
                ?? throw new InvalidOperationException("Truck material variant did not import.");
            material.SetFloat("_Metallic", .55f);
            material.SetFloat("_Smoothness", .32f);
            material.SetFloat("_GlossMapScale", .32f);
            material.SetColor("_BaseColor", Color.white);
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        static Renderer[] ValidRenderers(GameObject root)
        {
            var renderers = root.GetComponentsInChildren<Renderer>(true)
                .Where(renderer => renderer is MeshRenderer || renderer is SkinnedMeshRenderer).ToArray();
            if (renderers.Length == 0) throw new InvalidOperationException($"'{root.name}' contains no mesh renderer.");
            foreach (var renderer in renderers)
            {
                if (!MeshOf(renderer)) throw new InvalidOperationException($"Renderer '{renderer.name}' has no imported mesh.");
            }
            return renderers;
        }

        static Renderer[] RuntimeRenderers(GameObject root)
        {
            var renderers = ValidRenderers(root).Where(renderer => renderer.enabled && renderer.gameObject.activeInHierarchy).ToArray();
            if (renderers.Length == 0) throw new InvalidOperationException($"'{root.name}' contains no enabled runtime mesh renderer.");
            return renderers;
        }

        static int DisableImportedStage(GameObject root)
        {
            var stageObjects = root.GetComponentsInChildren<Transform>(true)
                .Where(transform => transform.name.StartsWith("KA_Studio_", StringComparison.OrdinalIgnoreCase)).ToArray();
            foreach (var stage in stageObjects) stage.gameObject.SetActive(false);
            return stageObjects.SelectMany(stage => stage.GetComponentsInChildren<Renderer>(true)).Distinct().Count();
        }

        static void ConfigurePropImporter(string assetPath)
        {
            var importer = AssetImporter.GetAtPath(assetPath) as ModelImporter
                ?? throw new InvalidOperationException($"ModelImporter is unavailable for '{assetPath}'.");
            if (!importer.importCameras && !importer.importLights) return;
            importer.importCameras = false;
            importer.importLights = false;
            importer.SaveAndReimport();
        }

        static Mesh MeshOf(Renderer renderer)
        {
            if (renderer is SkinnedMeshRenderer skinned) return skinned.sharedMesh;
            var filter = renderer.GetComponent<MeshFilter>();
            return filter ? filter.sharedMesh : null;
        }

        static Bounds LocalBounds(Transform root, Renderer[] renderers)
        {
            bool started = false;
            var result = new Bounds();
            foreach (var renderer in renderers)
            {
                var bounds = renderer is SkinnedMeshRenderer skinned ? skinned.localBounds : MeshOf(renderer).bounds;
                for (var x = -1; x <= 1; x += 2)
                for (var y = -1; y <= 1; y += 2)
                for (var z = -1; z <= 1; z += 2)
                {
                    var meshLocal = bounds.center + Vector3.Scale(bounds.extents, new Vector3(x, y, z));
                    var local = root.InverseTransformPoint(renderer.transform.TransformPoint(meshLocal));
                    if (!started) { result = new Bounds(local, Vector3.zero); started = true; }
                    else result.Encapsulate(local);
                }
            }
            if (!started || result.size.sqrMagnitude <= 0) throw new InvalidOperationException($"'{root.name}' has invalid renderer bounds.");
            return result;
        }

        static void AddStallPostColliders(GameObject root, Bounds bounds)
        {
            var width = Mathf.Min(.12f, bounds.size.x * .05f);
            var depth = Mathf.Min(.12f, bounds.size.z * .05f);
            var height = Mathf.Min(2.3f, bounds.size.y);
            var y = bounds.min.y + height * .5f;
            var xs = new[] { bounds.min.x + width * .5f, bounds.max.x - width * .5f };
            var zs = new[] { bounds.min.z + depth * .5f, bounds.max.z - depth * .5f };
            var index = 1;
            foreach (var x in xs)
            foreach (var z in zs)
                AddBox(root.transform, $"Post collision {index++}", new Bounds(new Vector3(x, y, z), new Vector3(width, height, depth)));
        }

        static BoxCollider AddBox(Transform parent, string name, Bounds bounds)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var collider = go.AddComponent<BoxCollider>();
            collider.center = bounds.center;
            collider.size = bounds.size;
            return collider;
        }

        static bool Uniform(Vector3 scale) => Mathf.Abs(scale.x - scale.y) < .0001f && Mathf.Abs(scale.x - scale.z) < .0001f;
        static float[] V(Vector3 value) => new[] { value.x, value.y, value.z };
    }
}
