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
    /// <summary>One-time, scoped installation of authored Blender fixture parts.</summary>
    public static class WardLampPass
    {
        const string AssetRoot = "Assets/AthenHill/Art/Quality/Lamps";
        const string RootName = "Ward utility lamps";
        static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repository, "art/quality_20260908/lamps");
        static string Evidence => Path.Combine(Repository, "unity/evidence/quality/20260908/lamps");

        [Serializable] sealed class Part
        {
            public string name, family, group, material;
            public float[][] positions, normals, uv;
            public int[] indices;
        }

        [MenuItem("Athen Hill/Quality/Install authored utility lamps")]
        public static void Install()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Install lamps in Edit Mode.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != "Assets/AthenHill/Scenes/AthenHill.unity") throw new InvalidOperationException("Open the saved AthenHill scene first.");
            if (scene.isDirty) throw new InvalidOperationException("Save current work before installing this recoverable lamp pass.");
            if (GameObject.Find(RootName)) throw new InvalidOperationException("The lamp family already exists. Edit its saved prefabs and placements rather than overwriting them.");
            if (Directory.Exists(AssetRoot)) throw new InvalidOperationException("Lamp output assets already exist. Inspect the existing installation before retrying.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var authored = GameObject.Find("AuthoredWorld");
            var finery = GameObject.Find("Phase 1 Finery frontage/Entrance light");
            if (!chunks || !authored || !finery) throw new InvalidOperationException("Expected editable sources and Finery lamp mounting root are missing.");
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, "lamp-meshes.json")));
            if (parts == null || !parts.Any(p => p.family == "Post") || !parts.Any(p => p.family == "Wall")) throw new InvalidDataException("Both complete lamp variants are required.");
            foreach (var part in parts)
            {
                if (part.positions.Length != part.normals.Length || part.positions.Length != part.uv.Length || part.indices.Length % 3 != 0 || part.indices.Any(i => i < 0 || i >= part.positions.Length))
                    throw new InvalidDataException("Invalid source buffer: " + part.name);
            }
            var allTransforms = authored.GetComponentsInChildren<Transform>(true);
            var oldSources = allTransforms.Where(t => t.name.StartsWith("PROP_avenue_lamp_", StringComparison.Ordinal)).Select(t => t.GetComponent<MeshRenderer>()).Where(r => r).ToArray();
            var oldColliders = allTransforms.Where(t => t.name.StartsWith("COL_PROP_avenue_lamp_", StringComparison.Ordinal)).Select(t => t.GetComponent<Collider>()).Where(c => c).ToArray();
            if (oldSources.Length != 30 || oldColliders.Length != 15) throw new InvalidOperationException("Lamp source/collider inventory changed; inspect placements before installation.");
            var positions = new Vector3[5];
            for (int i = 0; i < positions.Length; i++)
            {
                var foot = allTransforms.Single(t => t.name == "PROP_avenue_lamp_" + i.ToString("00") + "_foot").GetComponent<Renderer>().bounds;
                positions[i] = new Vector3(foot.center.x, foot.min.y, foot.center.z);
            }
            var previousWall = finery.GetComponentsInChildren<MeshRenderer>(true);
            if (previousWall.Length != 4) throw new InvalidOperationException("Finery wall fixture inventory changed; inspect the new content before replacement.");
            Directory.CreateDirectory(Evidence);
            EditorSceneManager.SaveScene(scene, Path.Combine(Evidence, "before-lamps.unity"), true);
            Directory.CreateDirectory(AssetRoot + "/Meshes"); Directory.CreateDirectory(AssetRoot + "/Materials"); Directory.CreateDirectory(AssetRoot + "/Textures");
            var materials = BuildMaterials(parts.Select(p => p.material).Distinct());
            var post = BuildPrefab("Post", parts, materials);
            var wall = BuildPrefab("Wall", parts, materials);
            chunks.ShowSources(true);
            foreach (var r in oldSources.Concat(previousWall)) { Undo.RecordObject(r, "Retain previous lamp source"); r.enabled = false; }
            // Preserve the original colliders and their enabled states, transforms and references.
            var group = new GameObject(RootName); Undo.RegisterCreatedObjectUndo(group, "Install authored Ward lamps");
            var lights = new List<Light>();
            for (int i = 0; i < positions.Length; i++)
            {
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(post); instance.name = "Avenue utility lamp " + i.ToString("00");
                instance.transform.SetParent(group.transform, false); instance.transform.position = positions[i];
                // Turn the high-mounted fixture towards its existing street, without relocating the base.
                var towardsStreet = new Vector3(-positions[i].x, 0, -positions[i].z);
                instance.transform.rotation = Quaternion.LookRotation(towardsStreet.normalized, Vector3.up);
                lights.Add(AddLight(instance.transform, new Vector3(0, 4.16f, .52f), "Lamp warm street light", 2.6f, 11.5f));
            }
            var wallInstance = (GameObject)PrefabUtility.InstantiatePrefab(wall); wallInstance.name = "Finery utility wall lamp";
            wallInstance.transform.SetParent(group.transform, false);
            // The feed plate extends 0.346m below the fixture origin. Keep it above the protruding lintel (top y=3.13).
            wallInstance.transform.SetPositionAndRotation(new Vector3(16.801f, 3.51f, -18), Quaternion.LookRotation(Vector3.left, Vector3.up));
            lights.Add(AddLight(wallInstance.transform, new Vector3(0, -.02f, .414f), "Lamp warm Finery entrance light", 1.65f, 6.5f));
            // A preceding entrance light may exist in a newer scene; replace only lights inside this exact old fixture root.
            foreach (var oldLight in finery.GetComponentsInChildren<Light>(true)) { Undo.RecordObject(oldLight, "Retain previous lamp light"); oldLight.enabled = false; }
            chunks.sourceRoots = chunks.sourceRoots.Concat(new[] { group.transform }).Distinct().ToArray();
            EditorUtility.SetDirty(chunks);
            BindClock(lights, materials["LampEmission"]);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene);
            File.WriteAllText(Path.Combine(Evidence, "installation.json"), JsonConvert.SerializeObject(new
            {
                installedUtc = DateTime.UtcNow.ToString("o"), scene = scene.path, source = "art/quality_20260908/lamps/lamp-family.blend",
                partCounts = parts.GroupBy(p => p.family).Select(g => new { family = g.Key, parts = g.Count(), triangles = g.Sum(p => p.indices.Length / 3) }),
                retainedOldRenderers = oldSources.Concat(previousWall).Select(r => Hierarchy(r.transform)).ToArray(),
                retainedColliders = oldColliders.Select(c => new { path = Hierarchy(c.transform), enabled = c.enabled, position = Array(c.transform.position), scale = Array(c.transform.lossyScale) }).ToArray(),
                lights = lights.Select(l => new { path = Hierarchy(l.transform), position = Array(l.transform.position), l.intensity, l.range, shadows = l.shadows.ToString(), color = new[] { l.color.r, l.color.g, l.color.b } }),
                reviewRequired = "Save assets; rebuild derived render chunks explicitly; save/reopen scene; build Linux; capture fixture base/head/wall at player height in noon, dusk and night; verify light pools, controller access, circuit switching and frame times. Source generation is not AAA acceptance."
            }, Formatting.Indented));
            Selection.activeGameObject = group;
            Debug.Log("Six authored fixtures installed with real practical lights. Original renderers and all lamp collider proxies retained. Rebuild chunks, save/reopen, and review native day/night views before acceptance.");
        }

        static Dictionary<string, Material> BuildMaterials(IEnumerable<string> names)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit"); if (!shader) throw new InvalidOperationException("URP Lit is unavailable.");
            var result = new Dictionary<string, Material>();
            foreach (var name in names)
            {
                var material = new Material(shader) { name = "WardLamp" + name, enableInstancing = true };
                material.SetFloat("_WorkflowMode", 1); material.SetColor("_BaseColor", Color.white);
                material.SetFloat("_Smoothness", .5f); material.SetFloat("_Metallic", 0);
                if (name == "LampEmission")
                {
                    material.SetColor("_BaseColor", new Color(.76f, .72f, .62f)); material.SetFloat("_Smoothness", .42f);
                    material.EnableKeyword("_EMISSION"); material.SetColor("_EmissionColor", new Color(1, .74f, .43f) * 3.2f);
                    material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                }
                else
                {
                    material.SetTexture("_BaseMap", ImportTexture(name + "_BaseColor.png", false, true));
                    material.SetTexture("_BumpMap", ImportTexture(name + "_Normal.png", true, false)); material.SetFloat("_BumpScale", .7f); material.EnableKeyword("_NORMALMAP");
                    material.SetTexture("_MetallicGlossMap", ImportTexture(name + "_MetalSmooth.png", false, false));
                    material.SetFloat("_Smoothness", 1); material.EnableKeyword("_METALLICSPECGLOSSMAP");
                    if (name == "Dust")
                    {
                        material.SetFloat("_Surface", 1); material.SetFloat("_Blend", 0); material.SetFloat("_ZWrite", 0);
                        material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                        material.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); material.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                        material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); material.SetOverrideTag("RenderType", "Transparent"); material.renderQueue = (int)RenderQueue.Transparent;
                        material.SetShaderPassEnabled("ShadowCaster", false);
                    }
                }
                AssetDatabase.CreateAsset(material, AssetRoot + "/Materials/" + material.name + ".mat"); result.Add(name, material);
            }
            return result;
        }

        static Texture2D ImportTexture(string name, bool normal, bool srgb)
        {
            var path = AssetRoot + "/Textures/" + name;
            File.Copy(Path.Combine(Source, "textures", name), path, false); AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.npotScale = TextureImporterNPOTScale.None; importer.maxTextureSize = 2048;
            importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8; importer.wrapMode = TextureWrapMode.Repeat;
            importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = name == "Dust_BaseColor.png";
            importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static GameObject BuildPrefab(string family, Part[] parts, Dictionary<string, Material> materials)
        {
            var root = new GameObject("Ward utility " + family.ToLowerInvariant() + " fixture");
            foreach (var part in parts.Where(p => p.family == family))
            {
                var mesh = new Mesh { name = part.name, indexFormat = IndexFormat.UInt32 };
                mesh.vertices = part.positions.Select(V3).ToArray(); mesh.normals = part.normals.Select(V3).ToArray();
                mesh.uv = part.uv.Select(v => new Vector2(v[0], v[1])).ToArray(); mesh.triangles = part.indices; mesh.RecalculateTangents(); mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, AssetRoot + "/Meshes/" + SafeName(part.name) + ".asset");
                var group = root.transform.Find(part.group);
                if (!group) { group = new GameObject(part.group).transform; group.SetParent(root.transform, false); }
                var go = new GameObject(part.name); go.transform.SetParent(group, false); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[part.material];
                renderer.shadowCastingMode = part.material == "LampEmission" || part.material == "Dust" ? ShadowCastingMode.Off : ShadowCastingMode.On;
                renderer.receiveShadows = true;
            }
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, AssetRoot + "/WardUtility" + family + ".prefab"); Object.DestroyImmediate(root); return prefab;
        }

        static Light AddLight(Transform parent, Vector3 local, string name, float intensity, float range)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.localPosition = local;
            var light = go.AddComponent<Light>(); light.type = LightType.Point; light.lightmapBakeType = LightmapBakeType.Realtime;
            light.color = new Color(1, .76f, .48f); light.intensity = intensity; light.range = range;
            light.shadows = LightShadows.Soft; light.shadowStrength = .82f; light.shadowBias = .03f; light.shadowNormalBias = .08f;
            light.shadowNearPlane = .05f; light.renderMode = LightRenderMode.Auto; light.enabled = true; return light;
        }

        static void BindClock(IEnumerable<Light> lights, Material emission)
        {
            var circuit = Object.FindAnyObjectByType<CityLightCircuit>(); if (!circuit) return;
            Undo.RecordObject(circuit, "Bind Ward lamp fixtures to clock");
            circuit.practicalLights = (circuit.practicalLights ?? System.Array.Empty<Light>()).Where(l => l && l.enabled).Concat(lights).Distinct().ToArray();
            circuit.emissiveMaterials = (circuit.emissiveMaterials ?? System.Array.Empty<Material>()).Where(m => m).Concat(new[] { emission }).Distinct().ToArray();
            EditorUtility.SetDirty(circuit);
        }
        static string SafeName(string name) => new string(name.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_').ToArray());
        static Vector3 V3(float[] v) => new Vector3(v[0], v[1], v[2]);
        static float[] Array(Vector3 v) => new[] { v.x, v.y, v.z };
        static string Hierarchy(Transform t) => t.parent ? Hierarchy(t.parent) + "/" + t.name : t.name;
    }
}
#endif
