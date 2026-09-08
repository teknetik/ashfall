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
    public static class ImportMissionTerminal
    {
        const string Folder = "Assets/AthenHill/Art/Imported/Meshy/MissionTerminal";
        const string ModelPath = Folder + "/mission-terminal.glb";
        const string MaterialPath = Folder + "/MissionTerminal.mat";
        const string AlbedoPath = Folder + "/Albedo.jpg";
        const string NormalPath = Folder + "/Normal.jpg";
        const string MetallicRoughnessPath = Folder + "/MetallicRoughness.jpg";
        const string MetallicSmoothnessPath = Folder + "/MetallicSmoothness.png";
        const string PrefabPath = "Assets/AthenHill/Prefabs/MissionTerminal.prefab";
        const string SceneRootName = "Mission Terminal Upgrade";
        const float TargetHeight = 1.95f;

        [MenuItem("Athen Hill/Props/Install Meshy mission terminals")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play before importing the mission terminal.");
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);

            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (!model) throw new Exception("Meshy mission terminal GLB did not import as a GameObject.");

            var template = new GameObject("MissionTerminal");
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(model);
            visual.name = "Meshy Mission Terminal";
            visual.transform.SetParent(template.transform, false);

            var sourceBounds = BoundsOf(template);
            if (sourceBounds.size.y <= .001f) throw new Exception("Meshy mission terminal has invalid bounds.");
            float scale = TargetHeight / sourceBounds.size.y;
            visual.transform.localScale = Vector3.one * scale;

            var scaledBounds = BoundsOf(template);
            visual.transform.localPosition += Vector3.up * -scaledBounds.min.y;
            var finalBounds = BoundsOf(template);
            if (Mathf.Abs(finalBounds.size.y - TargetHeight) > .01f || Mathf.Abs(finalBounds.min.y) > .01f)
                throw new Exception($"Mission terminal normalization failed: {finalBounds}");

            var gameMaterial = ImportMaterial();
            foreach (var renderer in template.GetComponentsInChildren<Renderer>(true))
            {
                renderer.sharedMaterials = Enumerable.Repeat(gameMaterial, renderer.sharedMaterials.Length).ToArray();
                renderer.shadowCastingMode = ShadowCastingMode.On;
                renderer.receiveShadows = true;
                renderer.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
                renderer.renderingLayerMask = 3u;
            }

            var collider = template.AddComponent<BoxCollider>();
            collider.center = finalBounds.center;
            collider.size = finalBounds.size;
            var prefab = PrefabUtility.SaveAsPrefabAsset(template, PrefabPath);
            UnityEngine.Object.DestroyImmediate(template);
            if (!prefab) throw new Exception("Could not create mission terminal prefab.");

            var authored = GameObject.Find("AuthoredWorld");
            if (!authored) throw new Exception("AuthoredWorld is missing.");
            var oldParts = authored.GetComponentsInChildren<Transform>(true)
                .Where(t => t.name.StartsWith("PROP_mission_", StringComparison.Ordinal)
                         || t.name.StartsWith("COL_PROP_mission_", StringComparison.Ordinal))
                .ToArray();
            if (!oldParts.Any(t => t.name == "PROP_mission_00_body")
                || !oldParts.Any(t => t.name == "PROP_mission_01_body")
                || !oldParts.Any(t => t.name == "PROP_mission_02_body"))
                throw new Exception("The three authored mission terminals were not found.");
            foreach (var part in oldParts) part.gameObject.SetActive(false);

            var previous = GameObject.Find(SceneRootName);
            if (previous) UnityEngine.Object.DestroyImmediate(previous);
            var root = new GameObject(SceneRootName);
            var sourcePositions = new[]
            {
                new Vector3(-10f, .25f, -13.8f),
                new Vector3(-8f, .25f, -13.8f),
                new Vector3(-6f, .25f, -13.8f),
            };
            var instances = sourcePositions.Select((position, index) =>
            {
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                instance.name = $"Mission Terminal {index + 1:00}";
                instance.transform.SetParent(root.transform);
                instance.transform.position = ImportBaseline.Convert(position.x, position.y, position.z);
                // Meshy's imported front already faces +Z toward Torr and the player approach.
                instance.transform.rotation = Quaternion.identity;
                SetStatic(instance);
                return instance;
            }).ToArray();

            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);

            var review = GameObject.Find("cam_terminal");
            if (review) UnityEngine.Object.DestroyImmediate(review);
            var camera = ImportBaseline.Camera(
                "cam_terminal",
                ImportBaseline.Convert(-8f, 2.35f, -7.6f),
                ImportBaseline.Convert(-8f, 1.05f, -13.8f),
                35f);
            camera.nearClipPlane = .05f;

            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(root.scene);
            EditorSceneManager.SaveOpenScenes();
            PortDiagnostics.Capture("cam_terminal");

            var meshes = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Mesh>().ToArray();
            var materials = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Material>().ToArray();
            long triangles = meshes.Sum(mesh => (long)mesh.triangles.Length / 3);
            var landmark = GameObject.Find("mission_slab");
            Directory.CreateDirectory("Captures");
            File.WriteAllText("Captures/mission-terminal-import.json", JsonConvert.SerializeObject(new
            {
                source = ModelPath,
                prefab = PrefabPath,
                targetHeightMeters = TargetHeight,
                sourceScale = scale,
                bounds = new
                {
                    center = new[] { finalBounds.center.x, finalBounds.center.y, finalBounds.center.z },
                    size = new[] { finalBounds.size.x, finalBounds.size.y, finalBounds.size.z }
                },
                meshes = meshes.Select(mesh => new { mesh.name, mesh.vertexCount, triangles = mesh.triangles.Length / 3 }),
                totalTriangles = triangles,
                materials = materials.Select(material => new { material.name, shader = material.shader ? material.shader.name : null }),
                gameMaterial = new
                {
                    gameMaterial.name,
                    shader = gameMaterial.shader.name,
                    baseMap = gameMaterial.GetTexture("_BaseMap") ? gameMaterial.GetTexture("_BaseMap").name : null,
                    normalMap = gameMaterial.GetTexture("_BumpMap") ? gameMaterial.GetTexture("_BumpMap").name : null,
                    note = "Meshy output has no tangent attribute, so the retained normal atlas is not enabled at runtime."
                },
                replacedInstances = instances.Select(instance => new
                {
                    instance.name,
                    position = new[] { instance.transform.position.x, instance.transform.position.y, instance.transform.position.z },
                    collider = instance.GetComponent<BoxCollider>() != null
                }),
                disabledLegacyParts = oldParts.Length,
                missionSlabLandmark = landmark ? new[] { landmark.transform.position.x, landmark.transform.position.y, landmark.transform.position.z } : null,
                reviewCapture = "Captures/Fixed/cam_terminal.png"
            }, Formatting.Indented));
        }

        public static void InstallAndBuild()
        {
            Install();
            LinuxBuild.Release();
        }

        static Bounds BoundsOf(GameObject root)
        {
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) throw new Exception("Meshy mission terminal has no renderers.");
            var bounds = renderers[0].bounds;
            foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
            return bounds;
        }

        static Material ImportMaterial()
        {
            ConfigureTexture(AlbedoPath, true, false, false);
            ConfigureTexture(NormalPath, false, true, false);
            ConfigureTexture(MetallicRoughnessPath, false, false, true);
            var metallicRoughness = AssetDatabase.LoadAssetAtPath<Texture2D>(MetallicRoughnessPath);
            var sourcePixels = metallicRoughness.GetPixels32();
            var packed = new Texture2D(metallicRoughness.width, metallicRoughness.height, TextureFormat.RGBA32, false, true);
            var packedPixels = new Color32[sourcePixels.Length];
            for (int i = 0; i < sourcePixels.Length; i++)
                packedPixels[i] = new Color32(sourcePixels[i].b, 0, 0, (byte)(255 - sourcePixels[i].g));
            packed.SetPixels32(packedPixels);
            packed.Apply();
            File.WriteAllBytes(MetallicSmoothnessPath, packed.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(packed);
            AssetDatabase.ImportAsset(MetallicSmoothnessPath, ImportAssetOptions.ForceSynchronousImport);
            ConfigureTexture(MetallicSmoothnessPath, false, false, false);

            var material = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            if (!material)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Unlit")) { name = "MissionTerminal" };
                AssetDatabase.CreateAsset(material, MaterialPath);
            }
            material.shader = Shader.Find("Universal Render Pipeline/Unlit");
            var baseMap = AssetDatabase.LoadAssetAtPath<Texture2D>(AlbedoPath);
            var normalMap = AssetDatabase.LoadAssetAtPath<Texture2D>(NormalPath);
            if (!baseMap || !normalMap) throw new Exception("Meshy GLB is missing its embedded albedo or normal atlas.");
            material.SetTexture("_BaseMap", baseMap);
            material.SetColor("_BaseColor", Color.white);
            // Meshy omitted tangents from this prop. Its albedo already contains
            // the authored wear and soft shading, which stays legible in this alcove.
            material.DisableKeyword("_NORMALMAP");
            material.DisableKeyword("_METALLICSPECGLOSSMAP");
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        static void ConfigureTexture(string path, bool srgb, bool normal, bool readable)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            if (!importer) throw new Exception("Texture is missing: " + path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb;
            importer.maxTextureSize = 2048;
            importer.mipmapEnabled = true;
            importer.anisoLevel = 4;
            importer.isReadable = readable;
            importer.textureCompression = readable ? TextureImporterCompression.Uncompressed : TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
        }

        static void SetStatic(GameObject root)
        {
            var flags = StaticEditorFlags.BatchingStatic
                      | StaticEditorFlags.OccluderStatic
                      | StaticEditorFlags.OccludeeStatic
                      | StaticEditorFlags.ReflectionProbeStatic;
            foreach (var transform in root.GetComponentsInChildren<Transform>(true))
                GameObjectUtility.SetStaticEditorFlags(transform.gameObject, flags);
        }
    }
}
