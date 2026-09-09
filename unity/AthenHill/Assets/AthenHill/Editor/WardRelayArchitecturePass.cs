#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>Scoped authored shop replacement. Existing generated sources and collider IDs are retained.</summary>
    public static class WardRelayArchitecturePass
    {
        const string AssetRoot = "Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02";
        const string RootName = "Ward shop architecture";
        static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string RepresentativeSource => Path.Combine(Repository, "art/quality_20260909/relay-family/revision-02");
        static string Source => RepresentativeSource;
        static string Evidence => Path.Combine(Repository, "unity/evidence/phase1/20260909-buildings/relay-family");
        [Serializable] sealed class Part { public string name, family, group, material; public float[][] positions, normals, uv; public int[] indices; }
        [Serializable] sealed class Proxy { public string name, family; public float[] center, size; }
        static string Hierarchy(Transform t) => t.parent ? Hierarchy(t.parent) + "/" + t.name : t.name;
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_').ToArray());
        static Vector3 V(float[] v) => new Vector3(v[0], v[1], v[2]);
        static Vector3 V(JToken v) => new Vector3((float)v[0], (float)v[1], (float)v[2]);
        static Vector3 Point(float[] v) => new Vector3(-v[0], v[1], v[2]);
        static Vector3 Point(JToken v) => new Vector3(-(float)v[0], (float)v[1], (float)v[2]);
        static int[] Winding(int[] indices)
        {
            var result = (int[])indices.Clone();
            for (int i = 0; i < result.Length; i += 3) { int t = result[i + 1]; result[i + 1] = result[i + 2]; result[i + 2] = t; }
            return result;
        }
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        static void RequireEdit()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Prepare architecture in Edit Mode.");
            if (EditorSceneManager.GetActiveScene().path != "Assets/AthenHill/Scenes/AthenHill.unity") throw new InvalidOperationException("Open the saved AthenHill scene.");
        }
        static string PrefabPath(string id) => AssetRoot + "/" + id + ".prefab";
        static Part[] ReadParts()
        {
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, "relay-meshes.json")));
            if (parts == null || parts.Length == 0) throw new InvalidDataException("No authored source parts.");
            var names = new HashSet<string>();
            foreach (var part in parts)
            {
                if (!names.Add(part.name)) throw new InvalidDataException("Duplicate source part " + part.name);
                if (part.positions == null || part.normals == null || part.uv == null || part.indices == null || part.positions.Length != part.normals.Length || part.positions.Length != part.uv.Length || part.indices.Length % 3 != 0 || part.indices.Any(i => i < 0 || i >= part.positions.Length)) throw new InvalidDataException("Invalid buffers: " + part.name);
                if (part.positions.Any(v => v.Length != 3 || v.Any(f => float.IsNaN(f) || float.IsInfinity(f))) || part.normals.Any(v => v.Length != 3 || v.Any(f => float.IsNaN(f) || float.IsInfinity(f))) || part.uv.Any(v => v.Length != 2 || v.Any(f => float.IsNaN(f) || float.IsInfinity(f)))) throw new InvalidDataException("Non-finite or invalid vectors: " + part.name);
            }
            return parts;
        }

        [MenuItem("Athen Hill/Quality/Prepare authored Relay representative")]
        public static void PrepareAssets()
        {
            RequireEdit();
            var parts = ReadParts();
            var families = parts.Select(p => p.family).Distinct().ToArray();
            if (families.Any(id => AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(id)))) throw new InvalidOperationException("A source prefab already exists. Preserve edits and inspect it instead of overwriting the architecture.");
            if (Directory.Exists(AssetRoot)) throw new InvalidOperationException("Architecture output already exists; inspect partial or edited output before recovery.");
            // Shared library must be prepared by root first; do not overwrite its Inspector settings.
            var materials = new Dictionary<string, Material>();
            foreach (var name in WardBuildingMaterials.Slots)
            {
                var path = WardBuildingMaterials.Folder + "/" + name + "/" + name + ".mat";
                var material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!material) throw new InvalidOperationException("Prepare shared building material first: " + path);
                materials.Add(name, material);
            }
            var proxies = JsonConvert.DeserializeObject<Proxy[]>(File.ReadAllText(Path.Combine(Source, "collider-proxies.json")));
            if (proxies == null || proxies.Length == 0 || proxies.Any(p => p.center.Length != 3 || p.size.Length != 3 || p.size.Any(f => f <= 0 || float.IsNaN(f)))) throw new InvalidDataException("Invalid authored wall proxies.");
            Directory.CreateDirectory(AssetRoot + "/Meshes"); Directory.CreateDirectory(AssetRoot + "/Materials"); Directory.CreateDirectory(AssetRoot + "/Textures");
            foreach (var name in parts.Select(p => p.material).Distinct().Where(n => !materials.ContainsKey(n))) materials.Add(name, Supplemental(name));
            foreach (var family in families)
            {
                var root = new GameObject("Authored " + family);
                try
                {
                    foreach (var part in parts.Where(p => p.family == family))
                    {
                        var mesh = new Mesh { name = part.name, indexFormat = IndexFormat.UInt32 };
                        mesh.vertices = part.positions.Select(Point).ToArray(); mesh.normals = part.normals.Select(Point).ToArray(); mesh.uv = part.uv.Select(v => new Vector2(v[0], v[1])).ToArray(); mesh.triangles = Winding(part.indices); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                        AssetDatabase.CreateAsset(mesh, AssetRoot + "/Meshes/" + Safe(part.name) + ".asset");
                        var group = root.transform.Find(part.group);
                        if (!group) { group = new GameObject(part.group).transform; group.SetParent(root.transform, false); }
                        var go = new GameObject(part.name); go.transform.SetParent(group, false); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                        var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[part.material]; renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true;
                    }
                    var proxyRoot = new GameObject("Authored collision proxies"); proxyRoot.transform.SetParent(root.transform, false);
                    foreach (var proxy in proxies.Where(p => p.family == family))
                    {
                        var go = new GameObject(proxy.name); go.transform.SetParent(proxyRoot.transform, false); var box = go.AddComponent<BoxCollider>(); box.center = Point(proxy.center); box.size = V(proxy.size);
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(family));
                }
                finally { Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets(); Directory.CreateDirectory(Evidence);
            File.WriteAllText(Path.Combine(Evidence, "prepared-revision-02.json"), JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("o"), source = Source, families = families.Select(f => new { id = f, parts = parts.Count(p => p.family == f), triangles = parts.Where(p => p.family == f).Sum(p => p.indices.Length / 3), prefab = PrefabPath(f) }), coordinateConversion = "Reflect interchange X with reversed winding; physical dimensions, UVs and loop normals retained", tangents = "Reconstructed from source UV0 and supplied corner normals", nativeStatus = "No scene installation or visual acceptance" }, Formatting.Indented));
        }

        [MenuItem("Athen Hill/Quality/Install Relay Works representative only")]
        public static void InstallRepresentative() => Install("relay_works");

        [MenuItem("Athen Hill/Quality/Seal Relay closed door meeting")]
        public static void SealDoorMeeting()
        {
            RequireEdit();
            if (EditorSceneManager.GetActiveScene().isDirty) throw new InvalidOperationException("Preserve unsaved scene edits first.");
            var additions = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Repository, "art/quality_20260909/relay-family/door-meeting-additions.json"))).Where(p => p.family == "relay_works").ToArray();
            if (additions.Length != 2 || additions.Any(p => AssetDatabase.LoadAssetAtPath<Mesh>(AssetRoot + "/Meshes/" + Safe(p.name) + ".asset"))) throw new InvalidOperationException("Expected two new meeting parts; do not repeat an existing correction.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); chunks.ShowSources(true);
            var root = PrefabUtility.LoadPrefabContents(PrefabPath("relay_works"));
            try
            {
                foreach (var part in additions)
                {
                    var mesh = new Mesh { name = part.name, indexFormat = IndexFormat.UInt32 };
                    mesh.vertices = part.positions.Select(Point).ToArray(); mesh.normals = part.normals.Select(Point).ToArray(); mesh.uv = part.uv.Select(v => new Vector2(v[0], v[1])).ToArray(); mesh.triangles = Winding(part.indices); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                    AssetDatabase.CreateAsset(mesh, AssetRoot + "/Meshes/" + Safe(part.name) + ".asset");
                    var parent = root.transform.Find(part.group); if (!parent) throw new InvalidOperationException("Source entrance group missing.");
                    var go = new GameObject(part.name); go.transform.SetParent(parent, false); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(AssetRoot + "/Materials/" + part.material + ".mat");
                    if (!renderer.sharedMaterial) throw new InvalidOperationException("Existing door material missing.");
                    renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true;
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath("relay_works"));
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks);
            File.WriteAllText(Path.Combine(Evidence, "door-meeting-correction.json"), JsonConvert.SerializeObject(new { utc = DateTime.UtcNow, reason = "Native first-person view exposed daylight between closed leaves", source = "art/quality_20260909/relay-family/revision-03", parts = additions.Select(p => p.name), triangles = additions.Sum(p => p.indices.Length / 3), preserved = "Existing meshes, prefab GUID, materials, source placement and every collision proxy" }, Formatting.Indented));
        }

        [MenuItem("Athen Hill/Quality/Correct Relay door seal export positions")]
        public static void CorrectDoorSealExport()
        {
            RequireEdit();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Preserve unsaved scene edits first.");
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Repository, "art/quality_20260909/relay-family/door-meeting-additions-v4.json"))).Where(p => p.family == "relay_works").ToArray();
            if (parts.Length != 2 || parts.Any(p => p.positions.Min(v => v[1]) < 0 || p.positions.Max(v => v[2]) < 2)) throw new InvalidDataException("Expected two door seals exported at the doorway, above the floor.");
            var meshes = parts.Select(p => AssetDatabase.LoadAssetAtPath<Mesh>(AssetRoot + "/Meshes/" + Safe(p.name) + ".asset")).ToArray();
            if (meshes.Any(m => !m || m.bounds.center.z > 2)) throw new InvalidOperationException("Expected original misplaced seals; do not overwrite a corrected asset.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); chunks.ShowSources(true);
            for (int i = 0; i < parts.Length; i++)
            {
                var p = parts[i]; var mesh = meshes[i];
                mesh.vertices = p.positions.Select(Point).ToArray(); mesh.normals = p.normals.Select(Point).ToArray(); mesh.uv = p.uv.Select(v => new Vector2(v[0], v[1])).ToArray(); mesh.triangles = Winding(p.indices); mesh.RecalculateTangents(); mesh.RecalculateBounds(); EditorUtility.SetDirty(mesh);
            }
            AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks);
            File.WriteAllText(Path.Combine(Evidence, "door-export-position-correction.json"), JsonConvert.SerializeObject(new { utc = DateTime.UtcNow, source = "art/quality_20260909/relay-family/revision-04", reason = "Loaded Blender source transforms were unevaluated before deriving door bounds", parts = parts.Select(p => p.name), bounds = meshes.Select(m => new { center = A(m.bounds.center), size = A(m.bounds.size) }), preserved = "Mesh GUIDs, topology, UVs, prefab links, materials, actor transforms and all collider proxies", acceptance = "Requires first-person native verification" }, Formatting.Indented));
        }

        public static void Install(string id)
        {
            RequireEdit(); var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current work before recoverable architecture installation.");
            var placement = JArray.Parse(File.ReadAllText(Path.Combine(Repository, "art/quality_20260909/relay-family/frozen-placements.json"))).Single(b => (string)b["id"] == id);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(id));
            if (!prefab) throw new InvalidOperationException("Prepare reviewed authored prefab first: " + id);
            var all = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true)).ToArray();
            var roots = scene.GetRootGameObjects().Where(g => g.name == RootName).ToArray();
            if (roots.Length > 1 || (roots.Length == 1 && roots[0].transform.Find(id))) throw new InvalidOperationException("Existing architecture installation found; preserve it and review rather than reinstall.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); if (!chunks) throw new InvalidOperationException("Missing editable render-chunk source controller.");
            string primaryPath = (string)placement["primaryPath"];
            var oldMesh = all.Single(t => Hierarchy(t) == primaryPath);
            var filter = oldMesh.GetComponent<MeshFilter>(); var meshCollider = oldMesh.GetComponent<MeshCollider>();
            if (!filter || filter.sharedMesh.triangles.Length / 3 != 6208 || !meshCollider || !meshCollider.enabled) throw new InvalidOperationException("Frozen Relay source/collision inventory changed; inspect before replacing this parcel.");
            var oldRenderers = placement["sourceInstances"].Where(s => ((string)s["path"]).StartsWith("Post-war salvage/", StringComparison.Ordinal)).Select(s => all.Single(t => Hierarchy(t) == (string)s["path"]).GetComponent<MeshRenderer>()).ToArray();
            if (oldRenderers.Any(r => !r)) throw new InvalidOperationException("Expected retained Relay renderer missing.");
            string key = primaryPath.Split('/')[1].Replace(" repaired", "");
            var preservedColliders = all.Where(t => t.name.StartsWith("COL_" + key + "_", StringComparison.Ordinal)).SelectMany(t => t.GetComponents<Collider>()).ToArray();
            if (!preservedColliders.Any(c => c.gameObject.activeInHierarchy && c.enabled && c.name.EndsWith("_porch", StringComparison.Ordinal))) throw new InvalidOperationException("Original active porch collider missing.");
            var before = preservedColliders.Select(c => new { id = c.GetEntityId().ToString(), path = Hierarchy(c.transform), active = c.gameObject.activeSelf, c.enabled, position = A(c.transform.position), rotation = A(c.transform.eulerAngles), scale = A(c.transform.localScale) }).ToArray();
            Directory.CreateDirectory(Evidence); string backup = Path.Combine(Evidence, "before-" + id + "-architecture.unity");
            if (File.Exists(backup)) throw new InvalidOperationException("Existing recovery scene would be overwritten: " + backup);
            if (!EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot save recovery scene.");
            chunks.ShowSources(true);
            foreach (var r in oldRenderers) { Undo.RecordObject(r, "Retain previous Relay visual"); r.enabled = false; }
            Undo.RecordObject(meshCollider, "Retain previous Relay shell collision"); meshCollider.enabled = false;
            var architecture = roots.FirstOrDefault();
            if (!architecture) { architecture = new GameObject(RootName); Undo.RegisterCreatedObjectUndo(architecture, "Authored shop architecture"); }
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab); instance.name = id; Undo.RegisterCreatedObjectUndo(instance, "Install reviewed Relay architecture");
            instance.transform.SetParent(architecture.transform, false);
            var centre = V(placement["center"]); float floor = centre.y - (float)placement["size"][1] / 2f;
            instance.transform.SetPositionAndRotation(new Vector3(centre.x, floor, centre.z), Quaternion.LookRotation(V(placement["frontNormal"]), Vector3.up)); instance.transform.localScale = Vector3.one;
            chunks.sourceRoots = chunks.sourceRoots.Concat(new[] { architecture.transform }).Distinct().ToArray(); EditorUtility.SetDirty(chunks);
            PrepareCameras(instance.transform, id);
            // Sources remain editable; root explicitly rebuilds chunks after all focused installations.
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.Combine(Evidence, "installation-" + id + ".json"), JsonConvert.SerializeObject(new { installedUtc = DateTime.UtcNow.ToString("o"), id, source = Source, prefab = PrefabPath(id), position = A(instance.transform.position), rotation = A(instance.transform.eulerAngles), scale = A(instance.transform.localScale), retiredRenderers = oldRenderers.Select(r => Hierarchy(r.transform)), retainedOldMeshCollider = new { id = meshCollider.GetEntityId().ToString(), path = Hierarchy(meshCollider.transform), mesh = AssetDatabase.GetAssetPath(meshCollider.sharedMesh), meshCollider.enabled }, preservedGameplayColliders = before, newColliderProxies = instance.GetComponentsInChildren<Collider>().Select(c => new { path = Hierarchy(c.transform), type = c.GetType().Name, center = A(c.bounds.center), size = A(c.bounds.size) }), acceptance = "Unqualified installation: root must rebuild chunks, save/reopen, build native Linux, inspect sun/shade/footing/door/roof, exercise real-input approach and affected interactions, measure frame cost. No family rollout or AAA acceptance inferred." }, Formatting.Indented));
        }

        static void PrepareCameras(Transform instance, string id)
        {
            var rows = JArray.Parse(File.ReadAllText(Path.Combine(Source, "review-cameras.json")));
            var root = new GameObject("Review cameras " + id);
            foreach (var row in rows)
            {
                string name = "cam_" + id + "_authored_" + ((string)row["name"]).Replace('-', '_');
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                var camera = go.AddComponent<Camera>(); camera.enabled = false; camera.nearClipPlane = .06f; camera.farClipPlane = 300;
                camera.fieldOfView = 2 * Mathf.Atan(13.5f / (float)row["lens"]) * Mathf.Rad2Deg;
                go.transform.position = instance.TransformPoint(Point(row["position"])); go.transform.LookAt(instance.TransformPoint(Point(row["target"])), Vector3.up);
            }
        }
        static Material Supplemental(string name)
        {
            var material = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name, enableInstancing = true };
            material.SetFloat("_WorkflowMode", 1); material.SetColor("_BaseColor", Color.white); material.SetFloat("_Smoothness", .3f);
            var lamp = new Dictionary<string, string> { { "WardPaint", "Paint" }, { "WardSteel", "Steel" }, { "WardBrass", "Bronze" }, { "WardRubber", "Rubber" } };
            if (lamp.TryGetValue(name, out var oldName))
            {
                string prefix = "Assets/AthenHill/Art/Quality/Lamps/Textures/" + oldName;
                var albedo = AssetDatabase.LoadAssetAtPath<Texture2D>(prefix + "_BaseColor.png"); var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(prefix + "_Normal.png"); var packed = AssetDatabase.LoadAssetAtPath<Texture2D>(prefix + "_MetalSmooth.png");
                if (!albedo || !normal || !packed) throw new InvalidOperationException("Documented original lamp maps missing: " + oldName);
                material.SetTexture("_BaseMap", albedo); material.SetTexture("_BumpMap", normal); material.SetFloat("_BumpScale", 1); material.SetTexture("_MetallicGlossMap", packed); material.SetFloat("_Smoothness", 1); material.SetFloat("_Metallic", 1); material.EnableKeyword("_NORMALMAP"); material.EnableKeyword("_METALLICSPECGLOSSMAP");
            }
            else if (name == "WardCloth")
            {
                material.SetColor("_BaseColor", new Color(.26f, .066f, .034f)); material.SetFloat("_Metallic", 0); material.SetFloat("_Smoothness", 1);
                material.SetTexture("_BumpMap", ImportCloth("Normal.png", true)); material.SetFloat("_BumpScale", 1); material.EnableKeyword("_NORMALMAP");
                material.SetTexture("_MetallicGlossMap", ImportCloth("MetalSmooth.png", false)); material.EnableKeyword("_METALLICSPECGLOSSMAP");
            }
            else
            {
                Color color; float rough, metal;
                switch (name)
                {
                    case "WardGlass": color = new Color(.024f, .045f, .048f); rough = .28f; metal = 0; break;
                    case "WardLetter": color = new Color(.64f, .53f, .32f); rough = .65f; metal = .45f; break;
                    case "WardGasket": color = new Color(.017f, .014f, .011f); rough = .94f; metal = 0; break;
                    case "WardLampGlass": color = new Color(.78f, .47f, .14f); rough = .35f; metal = 0; material.EnableKeyword("_EMISSION"); material.SetColor("_EmissionColor", new Color(1, .56f, .2f) * .4f); break;
                    default: throw new InvalidDataException("Unknown original material slot: " + name);
                }
                material.SetColor("_BaseColor", color); material.SetFloat("_Smoothness", 1 - rough); material.SetFloat("_Metallic", metal);
            }
            AssetDatabase.CreateAsset(material, AssetRoot + "/Materials/" + name + ".mat"); return material;
        }
        static Texture2D ImportCloth(string name, bool normal)
        {
            var path = AssetRoot + "/Textures/Cloth" + name;
            File.Copy(Path.Combine(Source, "textures", "Cloth" + name), path, false); AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path); importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default; importer.sRGBTexture = false;
            importer.GetSourceTextureWidthAndHeight(out int w, out int h); importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(w, h)); importer.npotScale = TextureImporterNPOTScale.None; importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8; importer.wrapMode = TextureWrapMode.Repeat; importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.SaveAndReimport(); return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
    }
}
#endif
