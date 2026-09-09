#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    public static class WardBenchPass
    {
        const string AssetRoot = "Assets/AthenHill/Art/Quality/Benches";
        const string RootName = "Ward plaza benches";
        static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repository, "art/quality_20260908/benches");
        static string Evidence => Path.Combine(Repository, "unity/evidence/quality/20260908/benches");
        [Serializable] sealed class Part { public string name, group, material; public float[][] positions, normals, uv; public int[] indices; }

        [MenuItem("Athen Hill/Quality/Install authored plaza benches")]
        public static void Install()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Install benches in Edit Mode.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != "Assets/AthenHill/Scenes/AthenHill.unity" || scene.isDirty) throw new InvalidOperationException("Save and open the authored AthenHill scene before installing.");
            if (GameObject.Find(RootName) || Directory.Exists(AssetRoot)) throw new InvalidOperationException("Bench installation or assets already exist. Inspect and edit that content rather than overwrite it.");
            var dressing = GameObject.Find("AuthoredWorld/AAA Environment Dressing"); var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!dressing || !chunks) throw new InvalidOperationException("Expected source roots are missing.");
            var previous = dressing.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.name == "Plaza bench seat" || r.name == "Plaza bench leg").ToArray();
            var seats = previous.Where(r => r.name == "Plaza bench seat").OrderBy(r => r.bounds.center.x).ToArray();
            if (previous.Length != 6 || seats.Length != 2 || previous.Any(r => r.GetComponent<Collider>())) throw new InvalidOperationException("The two plaza bench inventories changed; inspect before replacement.");
            var positions = seats.Select(r => r.bounds.center - new Vector3(0, .495f, 0)).ToArray();
            if (Vector3.Distance(positions[0], new Vector3(-3.4f, 1.5f, -5.8f)) > .025f || Vector3.Distance(positions[1], new Vector3(11.5f, 0, 5.7f)) > .025f)
                throw new InvalidOperationException("Bench placements changed since source fit. Inspect new floor heights and paths first.");
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, "bench-meshes.json")));
            if (parts == null || parts.Length < 20) throw new InvalidDataException("The complete authored bench source is required.");
            foreach (var p in parts)
                if (p.positions.Length != p.normals.Length || p.positions.Length != p.uv.Length || p.indices.Length % 3 != 0 || p.indices.Any(i => i < 0 || i >= p.positions.Length))
                    throw new InvalidDataException("Invalid bench buffer: " + p.name);
            Directory.CreateDirectory(Evidence); EditorSceneManager.SaveScene(scene, Path.Combine(Evidence, "before-benches.unity"), true);
            foreach (var child in new[] { "Meshes", "Materials", "Textures" }) Directory.CreateDirectory(AssetRoot + "/" + child);
            var materials = BuildMaterials(parts.Select(p => p.material).Distinct());
            var prefab = BuildPrefab(parts, materials);
            chunks.ShowSources(true);
            foreach (var r in previous) { Undo.RecordObject(r, "Retain primitive bench sources"); r.enabled = false; }
            var root = new GameObject(RootName); Undo.RegisterCreatedObjectUndo(root, "Install Ward plaza benches");
            var instances = new List<GameObject>();
            for (int i = 0; i < positions.Length; i++)
            {
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab); instance.name = i == 0 ? "Hill plaza bench" : "Avenue plaza bench";
                instance.transform.SetParent(root.transform, false); instance.transform.position = positions[i];
                // Existing long axis and centre are preserved; +Z remains the seat approach.
                instance.transform.rotation = Quaternion.identity; instances.Add(instance);
            }
            chunks.sourceRoots = chunks.sourceRoots.Concat(new[] { root.transform }).Distinct().ToArray(); EditorUtility.SetDirty(chunks);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene);
            File.WriteAllText(Path.Combine(Evidence, "installation.json"), JsonConvert.SerializeObject(new
            {
                installedUtc = DateTime.UtcNow.ToString("o"), scene = scene.path, source = "art/quality_20260908/benches/bench-family.blend",
                parts = parts.Length, trianglesPerBench = parts.Sum(p => p.indices.Length / 3),
                retiredPrimitiveRenderers = previous.Select(r => new { path = Hierarchy(r.transform), position = V(r.transform.position) }),
                instances = instances.Select(g => new { g.name, position = V(g.transform.position), colliders = g.GetComponentsInChildren<Collider>().Length }),
                preserved = "Four separate PROP_bench_00–03 groups and COL_bench_00–03 are unchanged; this pass replaces only the two plaza bench sets.",
                reviewRequired = "Save assets, rebuild chunks, save/reopen, native close front/side/rear/underseat views and real-input walk around each end. Check exact floor contact, seat height, material scale, shadows and collision. No sitting system is added and no AAA acceptance is asserted."
            }, Formatting.Indented));
            Selection.activeGameObject = root;
            Debug.Log("Two authored plaza benches installed. Six original primitive renderers retained disabled. Rebuild chunks, save/reopen and review native construction and routes.");
        }

        static Dictionary<string, Material> BuildMaterials(IEnumerable<string> regions)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit"); if (!shader) throw new InvalidOperationException("URP Lit required.");
            var result = new Dictionary<string, Material>();
            foreach (var region in regions)
            {
                var material = new Material(shader) { name = "WardBench" + region, enableInstancing = true };
                material.SetFloat("_WorkflowMode", 1); material.SetFloat("_Smoothness", 1); material.SetFloat("_Metallic", 0);
                material.SetColor("_BaseColor", region == "Wood" ? new Color(1.03f, .94f, .79f) : region == "EndGrain" ? new Color(1, .85f, .70f) : Color.white);
                material.SetTexture("_BaseMap", ImportTexture(region + "_BaseColor.png", false, true, region));
                material.SetTexture("_BumpMap", ImportTexture(region + "_Normal.png", true, false, region)); material.SetFloat("_BumpScale", region == "Wood" ? .42f : .7f); material.EnableKeyword("_NORMALMAP");
                material.SetTexture("_MetallicGlossMap", ImportTexture(region + "_MetalSmooth.png", false, false, region)); material.EnableKeyword("_METALLICSPECGLOSSMAP");
                if (region == "Dust")
                {
                    material.SetFloat("_Surface", 1); material.SetFloat("_Blend", 0); material.SetFloat("_ZWrite", 0);
                    material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                    material.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); material.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                    material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); material.SetOverrideTag("RenderType", "Transparent"); material.renderQueue = (int)RenderQueue.Transparent;
                    material.SetShaderPassEnabled("ShadowCaster", false);
                }
                AssetDatabase.CreateAsset(material, AssetRoot + "/Materials/" + material.name + ".mat"); result.Add(region, material);
            }
            return result;
        }
        static Texture2D ImportTexture(string name, bool normal, bool srgb, string region)
        {
            var path = AssetRoot + "/Textures/" + name; File.Copy(Path.Combine(Source, "textures", name), path, false); AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path); importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.npotScale = TextureImporterNPOTScale.None; importer.maxTextureSize = region == "Wood" ? 4096 : region == "EndGrain" ? 1024 : 2048;
            importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8; importer.wrapMode = TextureWrapMode.Repeat;
            importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = name == "Dust_BaseColor.png"; importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport(); return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
        static GameObject BuildPrefab(Part[] parts, Dictionary<string, Material> materials)
        {
            var root = new GameObject("Ward reclaimed timber bench");
            foreach (var p in parts)
            {
                var mesh = new Mesh { name = p.name, indexFormat = IndexFormat.UInt32 };
                mesh.vertices = p.positions.Select(a => new Vector3(a[0], a[1], a[2])).ToArray(); mesh.normals = p.normals.Select(a => new Vector3(a[0], a[1], a[2])).ToArray();
                mesh.uv = p.uv.Select(a => new Vector2(a[0], a[1])).ToArray(); mesh.triangles = p.indices; mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, AssetRoot + "/Meshes/" + Safe(p.name) + ".asset");
                var group = root.transform.Find(p.group); if (!group) { group = new GameObject(p.group).transform; group.SetParent(root.transform, false); }
                var go = new GameObject(p.name); go.transform.SetParent(group, false); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[p.material]; renderer.shadowCastingMode = p.material == "Dust" ? ShadowCastingMode.Off : ShadowCastingMode.On; renderer.receiveShadows = true;
            }
            var proxies = new GameObject("Visible mass collision proxies").transform; proxies.SetParent(root.transform, false);
            Box(proxies, "Slatted seat", new Vector3(0, .430f, 0), new Vector3(2.08f, .045f, .474f));
            var back = Box(proxies, "Reclined back", new Vector3(0, .725f, -.243f), new Vector3(2.04f, .405f, .040f)); back.transform.localRotation = Quaternion.Euler(-13.88f, 0, 0);
            foreach (float x in new[] { -.77f, .77f })
            {
                var upright = Box(proxies, "Back upright " + x, new Vector3(x, .6465f, -.2625f), new Vector3(.041f, .602f, .047f));
                upright.transform.localRotation = Quaternion.Euler(-13.88f, 0, 0);
            }
            foreach (float x in new[] { -.948f, .948f }) Box(proxies, "Timber arm " + x, new Vector3(x, .665f, -.008f), new Vector3(.077f, .047f, .404f));
            foreach (float x in new[] { -.77f, .77f }) foreach (float z in new[] { -.195f, .195f })
            {
                Box(proxies, "Steel leg " + x + " " + z, new Vector3(x, .206f, z * .915f), new Vector3(.049f, .380f, .070f));
                Box(proxies, "Ground shoe " + x + " " + z, new Vector3(x, .008f, z), new Vector3(.115f, .016f, .10f));
            }
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, AssetRoot + "/WardPlazaBench.prefab"); Object.DestroyImmediate(root); return prefab;
        }
        static BoxCollider Box(Transform parent, string name, Vector3 centre, Vector3 size)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.localPosition = centre; var collider = go.AddComponent<BoxCollider>(); collider.size = size; return collider;
        }
        static string Safe(string value) => new string(value.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_').ToArray());
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
        static string Hierarchy(Transform t) => t.parent ? Hierarchy(t.parent) + "/" + t.name : t.name;
    }
}
#endif
