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
    /// <summary>Install the six reviewed store sources without replacing gameplay roots.</summary>
    public static class WardStoreRolloutPass
    {
        public static readonly string[] Stores = { "air_water", "field_supply", "repairs", "salvage", "thread_hide", "tool_exchange" };
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string RootName = "Ward shop architecture";
        const string AssetRoot = "Assets/AthenHill/Art/Quality/StoreArchitecture/Revision04";
        const string RelayMaterials = "Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02/Materials";
        static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repository, "art/quality_20260909/relay-family/store-variants-04");
        static string Evidence => Path.Combine(Repository, "unity/evidence/phase1/20260909-store-rollout");
        sealed class Part { public string name, family, group, material; public float[][] positions, normals, uv; public int[] indices; }
        sealed class Proxy { public string name, family; public float[] center, size; }
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_').ToArray());
        static string Folder(string id) => AssetRoot + "/" + id;
        static string PrefabPath(string id) => Folder(id) + "/" + id + ".prefab";
        static Vector3 Point(float[] v) => new Vector3(-v[0], v[1], v[2]);
        static Vector3 Vector(JToken v) => new Vector3((float)v[0], (float)v[1], (float)v[2]);
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        static string Hierarchy(Transform t) => t.parent ? Hierarchy(t.parent) + "/" + t.name : t.name;
        static int[] Winding(int[] source)
        {
            var result = (int[])source.Clone();
            for (int i = 0; i < result.Length; i += 3) { int b = result[i + 1]; result[i + 1] = result[i + 2]; result[i + 2] = b; }
            return result;
        }
        static void RequireEdit(string id)
        {
            if (!Stores.Contains(id)) throw new ArgumentException("Not one of the six remaining stores: " + id);
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorSceneManager.GetActiveScene().path != ScenePath) throw new InvalidOperationException("Open the saved city in Edit Mode.");
            if (EditorSceneManager.GetActiveScene().isDirty) throw new InvalidOperationException("Save existing scene edits before this operation.");
        }

        public static void Prepare(string id)
        {
            RequireEdit(id);
            if (Directory.Exists(Folder(id))) throw new InvalidOperationException("Keep existing or partial assets; inspect before resuming: " + id);
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, id, "meshes.json")));
            var manifest = JObject.Parse(File.ReadAllText(Path.Combine(Source, "manifest.json")));
            var row = manifest["families"].Single(v => (string)v["id"] == id);
            if (parts.Length != (int)row["parts"] || parts.Sum(p => p.indices.Length / 3) != (int)row["triangles"]) throw new InvalidDataException("Source manifest/count mismatch: " + id);
            if (parts.Any(p => p.family != id || p.positions.Length != p.normals.Length || p.positions.Length != p.uv.Length || p.indices.Length % 3 != 0 || p.indices.Any(n => n < 0 || n >= p.positions.Length))) throw new InvalidDataException("Invalid source buffers: " + id);
            if (parts.Select(p => p.name).Distinct().Count() != parts.Length) throw new InvalidDataException("Duplicate authored part names.");
            foreach (var p in parts)
                if (p.positions.Concat(p.normals).Any(v => v.Length != 3 || v.Any(x => float.IsNaN(x) || float.IsInfinity(x))) || p.uv.Any(v => v.Length != 2 || v.Any(x => float.IsNaN(x) || float.IsInfinity(x)))) throw new InvalidDataException("Non-finite source vectors: " + p.name);
            var proxies = JsonConvert.DeserializeObject<Proxy[]>(File.ReadAllText(Path.Combine(Source, id, "collider-proxies.json")));
            if (proxies.Length < 4 || proxies.Any(p => p.family != id || p.center.Length != 3 || p.size.Length != 3 || p.size.Any(v => v <= 0))) throw new InvalidDataException("Missing or invalid wall proxies.");
            Directory.CreateDirectory(Folder(id) + "/Meshes"); Directory.CreateDirectory(Folder(id) + "/Materials");
            var materials = new Dictionary<string, Material>();
            foreach (var slot in parts.Select(p => p.material).Distinct())
            {
                Material material;
                if (slot == "WardCloth_" + id)
                {
                    var original = AssetDatabase.LoadAssetAtPath<Material>(RelayMaterials + "/WardCloth.mat");
                    if (!original) throw new InvalidOperationException("Reviewed full-resolution cloth material missing.");
                    material = new Material(original) { name = slot };
                    var tint = manifest["clothTints"][id]; material.SetColor("_BaseColor", new Color((float)tint[0], (float)tint[1], (float)tint[2]));
                    AssetDatabase.CreateAsset(material, Folder(id) + "/Materials/" + slot + ".mat");
                }
                else
                {
                    string path = WardBuildingMaterials.Slots.Contains(slot) ? WardBuildingMaterials.Folder + "/" + slot + "/" + slot + ".mat" : RelayMaterials + "/" + slot + ".mat";
                    material = AssetDatabase.LoadAssetAtPath<Material>(path);
                }
                if (!material || material.shader.name != "Universal Render Pipeline/Lit") throw new InvalidDataException("Reviewed URP material missing: " + slot);
                materials.Add(slot, material);
            }
            var root = new GameObject("Authored " + id);
            try
            {
                var collision = new GameObject("Authored collision proxies").transform; collision.SetParent(root.transform, false);
                foreach (var p in parts)
                {
                    var mesh = new Mesh { name = p.name, indexFormat = IndexFormat.UInt32 };
                    mesh.vertices = p.positions.Select(Point).ToArray(); mesh.normals = p.normals.Select(Point).ToArray(); mesh.uv = p.uv.Select(v => new Vector2(v[0], v[1])).ToArray(); mesh.triangles = Winding(p.indices); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                    AssetDatabase.CreateAsset(mesh, Folder(id) + "/Meshes/" + Safe(p.name) + ".asset");
                    var group = root.transform.Find(p.group);
                    if (!group) { group = new GameObject(p.group).transform; group.SetParent(root.transform, false); }
                    var go = new GameObject(p.name); go.transform.SetParent(group, false); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[p.material]; renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true;
                    // Retain the actual roof slope for camera/physics contact; no detailed roof hardware colliders.
                    if (p.name.Contains("Roof sloped structural face"))
                    {
                        var roof = new GameObject(p.name + " collision"); roof.transform.SetParent(collision, false); roof.AddComponent<MeshCollider>().sharedMesh = mesh;
                    }
                    else if (p.name.EndsWith("Roof bearing slab", StringComparison.Ordinal))
                    {
                        var roof = new GameObject("Roof slab collision"); roof.transform.SetParent(collision, false); var box = roof.AddComponent<BoxCollider>(); box.center = mesh.bounds.center; box.size = mesh.bounds.size;
                    }
                }
                foreach (var p in proxies)
                {
                    var go = new GameObject(p.name); go.transform.SetParent(collision, false); var box = go.AddComponent<BoxCollider>(); box.center = Point(p.center); box.size = new Vector3(p.size[0], p.size[1], p.size[2]);
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(id));
                Directory.CreateDirectory(Evidence);
                File.WriteAllText(Path.Combine(Evidence, "prepared-" + id + ".json"), JsonConvert.SerializeObject(new { id, source = Path.Combine(Source, id), prefab = PrefabPath(id), parts = parts.Length, triangles = parts.Sum(p => p.indices.Length / 3), colliders = root.GetComponentsInChildren<Collider>().Length, materials = materials.Select(k => new { slot = k.Key, asset = AssetDatabase.GetAssetPath(k.Value) }), sourceMaps = "Full original shared maps retained; only individual cloth tints differ" }, Formatting.Indented));
            }
            finally { Object.DestroyImmediate(root); }
            AssetDatabase.SaveAssets();
        }

        public static void Install(string id)
        {
            RequireEdit(id);
            var scene = EditorSceneManager.GetActiveScene();
            var placement = JArray.Parse(File.ReadAllText(Path.Combine(Repository, "art/quality_20260909/relay-family/frozen-placements.json"))).Single(v => (string)v["id"] == id);
            var all = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true)).ToArray();
            var architecture = scene.GetRootGameObjects().Single(g => g.name == RootName);
            if (architecture.transform.Find(id)) throw new InvalidOperationException("Store already installed; preserve its edits: " + id);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(id)); if (!prefab) throw new InvalidOperationException("Prepare the reviewed source first.");
            string oldPath = (string)placement["primaryPath"];
            var old = all.Single(t => Hierarchy(t) == oldPath);
            var oldCollider = old.GetComponent<MeshCollider>(); var oldMesh = old.GetComponent<MeshFilter>().sharedMesh;
            if (!oldCollider || !oldCollider.enabled || oldMesh.triangles.Length / 3 != 6208) throw new InvalidOperationException("Old store inventory changed; inspect this placement.");
            var expected = Vector(placement["center"]);
            if (Vector3.Distance(oldCollider.bounds.center, expected) > .02f) throw new InvalidOperationException("Old parcel moved since the audit.");
            string key = oldPath.Split('/')[1].Replace(" repaired", "");
            var existingSteps = all.Where(t => t.name.StartsWith("COL_" + key + "_", StringComparison.Ordinal)).SelectMany(t => t.GetComponents<Collider>()).ToArray();
            if (!existingSteps.Any(c => c.name.EndsWith("_porch", StringComparison.Ordinal) && c.enabled && c.gameObject.activeInHierarchy)) throw new InvalidOperationException("Original porch collision is missing.");
            var renderers = placement["sourceInstances"].Where(v => ((string)v["path"]).StartsWith("Post-war salvage/", StringComparison.Ordinal)).Select(v => all.Single(t => Hierarchy(t) == (string)v["path"]).GetComponent<MeshRenderer>()).ToArray();
            if (renderers.Any(r => !r)) throw new InvalidOperationException("Original store visual is missing.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); if (!chunks || !chunks.sourceRoots.Contains(architecture.transform)) throw new InvalidOperationException("Editable architecture source root is not registered.");
            string backup = Path.Combine(Evidence, "before-" + id + ".unity"); if (File.Exists(backup)) throw new InvalidOperationException("Preserve existing recovery scene.");
            if (!EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Could not preserve the existing scene.");
            chunks.ShowSources(true);
            foreach (var r in renderers) { Undo.RecordObject(r, "Retain previous store visual"); r.enabled = false; }
            Undo.RecordObject(oldCollider, "Retain old shell collision asset"); oldCollider.enabled = false;
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab); instance.name = id; instance.transform.SetParent(architecture.transform, false);
            float floor = expected.y - (float)placement["size"][1] * .5f;
            instance.transform.SetPositionAndRotation(new Vector3(expected.x, floor, expected.z), Quaternion.LookRotation(Vector(placement["frontNormal"]), Vector3.up)); instance.transform.localScale = Vector3.one;
            Undo.RegisterCreatedObjectUndo(instance, "Replace " + id + " frontage");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.Combine(Evidence, "installed-" + id + ".json"), JsonConvert.SerializeObject(new { utc = DateTime.UtcNow, id, prefab = PrefabPath(id), position = A(instance.transform.position), rotation = A(instance.transform.eulerAngles), scale = A(instance.transform.localScale), retainedOldMesh = AssetDatabase.GetAssetPath(oldMesh), disabledOldVisuals = renderers.Select(r => Hierarchy(r.transform)), disabledShellCollider = GlobalObjectId.GetGlobalObjectIdSlow(oldCollider).ToString(), preservedSteps = existingSteps.Select(c => new { path = Hierarchy(c.transform), id = GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(), center = A(c.bounds.center), size = A(c.bounds.size) }), newColliders = instance.GetComponentsInChildren<Collider>().Select(c => new { path = Hierarchy(c.transform), type = c.GetType().Name, center = A(c.bounds.center), size = A(c.bounds.size) }), status = "Installed source; explicitly rebuild chunks and verify native before counting it as checked" }, Formatting.Indented));
        }
    }
}
#endif
