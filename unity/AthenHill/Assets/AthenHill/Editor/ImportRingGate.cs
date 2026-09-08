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
    // Editor-only installation. The saved prefab/scene is the shipped asset.
    public static class ImportRingGate
    {
        const string Folder = "Assets/AthenHill/Art/Imported/Meshy/RingGate";
        const string ModelPath = Folder + "/ring-gate.fbx";
        const string PrefabPath = "Assets/AthenHill/Prefabs/RingGate.prefab";
        const string RootName = "Meshy Ring Gate";
        const float TargetHeight = 6.7f;

        [MenuItem("Athen Hill/Props/Install Meshy ring gate")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play before installing the gate.");
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            if (GameObject.Find(RootName)) throw new Exception("Ring gate is already installed. Edit its prefab and scene instance normally.");
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            var authored = GameObject.Find("AuthoredWorld");
            if (!session || !session.ringPoint || !authored) throw new Exception("The saved city and Ring interaction marker are required.");
            var ringPosition = session.ringPoint.position;
            var actors = session.npcs.Select(n => n.transform.position).ToArray();

            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            importer.animationType = ModelImporterAnimationType.None;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.importNormals = ModelImporterNormals.Import;
            importer.importTangents = ModelImporterTangents.CalculateMikk;
            importer.isReadable = true; // Retain editable/cookable collision geometry.
            importer.SaveAndReimport();

            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (!model) throw new Exception("Ring gate FBX did not import.");
            var template = new GameObject("RingGate");
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(model);
            visual.name = "Meshy ring gate visual";
            visual.transform.SetParent(template.transform, false);
            // Meshy faces +Z; face the northward approach into the south court.
            visual.transform.localRotation = Quaternion.Euler(0, 180, 0);
            var sourceBounds = BoundsOf(template);
            if (sourceBounds.size.y <= .001f) throw new Exception("Empty gate geometry.");
            visual.transform.localScale *= TargetHeight / sourceBounds.size.y;
            var bounds = BoundsOf(template);
            visual.transform.localPosition -= new Vector3(bounds.center.x, bounds.min.y, bounds.center.z);
            var material = MakeMaterial();
            foreach (var renderer in template.GetComponentsInChildren<MeshRenderer>(true))
            {
                renderer.sharedMaterials = Enumerable.Repeat(material, renderer.sharedMaterials.Length).ToArray();
                renderer.shadowCastingMode = ShadowCastingMode.On;
                renderer.receiveShadows = true;
                renderer.renderingLayerMask = 3u;
                renderer.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
                // Concave static collision retains the open aperture, console and steps.
                var collision = renderer.gameObject.AddComponent<MeshCollider>();
                collision.sharedMesh = renderer.GetComponent<MeshFilter>().sharedMesh;
                collision.convex = false;
            }
            foreach (var t in template.GetComponentsInChildren<Transform>(true))
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
            var prefab = PrefabUtility.SaveAsPrefabAsset(template, PrefabPath);
            UnityEngine.Object.DestroyImmediate(template);
            if (!prefab) throw new Exception("Failed to save RingGate prefab.");

            var legacy = authored.GetComponentsInChildren<Transform>(true).Where(t => IsLegacy(t.name)).ToArray();
            if (!legacy.Any(t => t.name == "ENV_ring_pad")) throw new Exception("Original ring platform was not found.");
            foreach (var t in legacy) t.gameObject.SetActive(false);
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            instance.name = RootName;
            instance.transform.position = new Vector3(ringPosition.x, 0, ringPosition.z);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);

            ImportBaseline.Camera("cam_ring_front", new Vector3(0, 3.5f, 23.8f), new Vector3(0, 3.1f, ringPosition.z), 42);
            if (session.ringPoint.position != ringPosition || !actors.SequenceEqual(session.npcs.Select(n => n.transform.position)))
                throw new Exception("Gameplay markers or actors changed during visual replacement.");
            SaveReview();
        }

        static bool IsLegacy(string name) => name.StartsWith("ENV_ring_", StringComparison.Ordinal)
            || name.StartsWith("PROP_ring_", StringComparison.Ordinal)
            || name.StartsWith("COL_ENV_ring_", StringComparison.Ordinal)
            || name.StartsWith("COL_PROP_ring_", StringComparison.Ordinal)
            || name.StartsWith("COL_ring_", StringComparison.Ordinal);

        static Bounds BoundsOf(GameObject root)
        {
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) throw new Exception("Gate has no renderers.");
            var bounds = renderers[0].bounds;
            foreach (var r in renderers.Skip(1)) bounds.Encapsulate(r.bounds);
            return bounds;
        }

        static Texture2D Texture(string name, bool srgb, bool normal = false, bool readable = false)
        {
            var path = Directory.GetFiles(Folder, name + ".*").First(p => !p.EndsWith(".meta"));
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb;
            importer.maxTextureSize = 2048;
            importer.mipmapEnabled = true;
            importer.anisoLevel = 4;
            importer.isReadable = readable;
            importer.textureCompression = readable ? TextureImporterCompression.Uncompressed : TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static Material MakeMaterial()
        {
            var albedo = Texture("Albedo", true);
            var normal = Texture("Normal", false, normal: true);
            var mr = Texture("MetallicRoughness", false, readable: true);
            var pixels = mr.GetPixels32();
            for (int i = 0; i < pixels.Length; i++) pixels[i] = new Color32(pixels[i].b, 0, 0, (byte)(255 - pixels[i].g));
            WriteAtlas("MetallicSmoothness", mr.width, mr.height, pixels);
            var mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "RingGate", enableInstancing = true };
            mat.SetTexture("_BaseMap", albedo);
            mat.SetColor("_BaseColor", Color.white);
            mat.SetTexture("_BumpMap", normal);
            mat.SetFloat("_BumpScale", .65f);
            mat.EnableKeyword("_NORMALMAP");
            mat.SetTexture("_MetallicGlossMap", Texture("MetallicSmoothness", false));
            mat.SetFloat("_Metallic", 1);
            mat.SetFloat("_Smoothness", .6f);
            mat.EnableKeyword("_METALLICSPECGLOSSMAP");
            mat.SetTexture("_EmissionMap", Texture("Emission", true));
            mat.SetColor("_EmissionColor", Color.white * 1.5f);
            mat.EnableKeyword("_EMISSION");
            mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            AssetDatabase.CreateAsset(mat, Folder + "/RingGate.mat");
            return mat;
        }

        static void WriteAtlas(string name, int width, int height, Color32[] pixels)
        {
            var texture = new Texture2D(width, height, TextureFormat.RGBA32, false, true);
            texture.SetPixels32(pixels); texture.Apply();
            File.WriteAllBytes(Folder + "/" + name + ".png", texture.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(texture);
        }

        public static void SaveReview()
        {
            var gate = GameObject.Find(RootName);
            if (!gate) throw new Exception("Gate is missing.");
            var bounds = BoundsOf(gate);
            Physics.SyncTransforms();
            var center = new Vector3(bounds.center.x, 3.7f, bounds.center.z);
            bool apertureBlocked = Physics.RaycastAll(center - Vector3.forward * 4, Vector3.forward, 8)
                .Any(hit => hit.collider.transform.IsChildOf(gate.transform));
            if (apertureBlocked) throw new Exception("Generated ring aperture is blocked by collision.");
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(gate.scene);
            EditorSceneManager.SaveOpenScenes();
            foreach (string camera in new[] { "cam_whompah", "cam_ring_front", "cam_avenue", "cam_hill", "cam_gate" }) PortDiagnostics.Capture(camera);
            var filters = gate.GetComponentsInChildren<MeshFilter>();
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            File.WriteAllText("Captures/ring-gate-import.json", JsonConvert.SerializeObject(new
            {
                source = ModelPath, prefab = PrefabPath, targetHeightMeters = TargetHeight,
                position = new[] { gate.transform.position.x, gate.transform.position.y, gate.transform.position.z },
                bounds = new { center = new[] { bounds.center.x, bounds.center.y, bounds.center.z }, size = new[] { bounds.size.x, bounds.size.y, bounds.size.z } },
                triangles = filters.Sum(f => f.sharedMesh.triangles.Length / 3),
                vertices = filters.Sum(f => f.sharedMesh.vertexCount),
                tangentCounts = filters.Select(f => f.sharedMesh.tangents.Length),
                colliders = gate.GetComponentsInChildren<Collider>().Length,
                apertureBlocked,
                ringInteractionPosition = new[] { session.ringPoint.position.x, session.ringPoint.position.y, session.ringPoint.position.z },
                disabledLegacyParts = GameObject.Find("AuthoredWorld").GetComponentsInChildren<Transform>(true).Count(t => IsLegacy(t.name) && !t.gameObject.activeInHierarchy)
            }, Formatting.Indented));
        }

        public static void InstallAndBuild() { Install(); LinuxBuild.Development(); LinuxBuild.Release(); }
    }
}
