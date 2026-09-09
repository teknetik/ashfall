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
    // One-time, recoverable authoring operation. Never runs in the player.
    public static class BasicGeneralArchitecturePass
    {
        public const string Folder = "Assets/AthenHill/Art/Phase1/BasicGeneral/Revision03";
        const string Prefab = Folder + "/BasicGeneral.prefab";
        const string RootName = "Basic General authored frontage";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/quality_20260909/basic-general");
        static string Evidence => Path.Combine(Repo, "unity/evidence/phase1/20260909-buildings");
        static Vector3 V(JToken a) => new Vector3((float)a[0], (float)a[1], (float)a[2]);
        // The interchange stores Blender X/Z/-Y. Reflect X to preserve the view
        // from the front in Unity's left-handed camera basis; reverse winding too.
        static Vector3 UnityPoint(JToken a) => new Vector3(-(float)a[0], (float)a[1], (float)a[2]);
        static int[] UnityIndices(JToken row)
        {
            var indices = row.Select(i => (int)i).ToArray();
            for (int i = 0; i < indices.Length; i += 3) { int t = indices[i + 1]; indices[i + 1] = indices[i + 2]; indices[i + 2] = t; }
            return indices;
        }
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_').ToArray());
        static void RequireEdit()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorSceneManager.GetActiveScene().path != "Assets/AthenHill/Scenes/AthenHill.unity")
                throw new InvalidOperationException("Open the saved AthenHill scene in Edit Mode.");
        }
        static void Write(string name, object data) => File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented));

        [MenuItem("Athen Hill/Phase 1/Prepare Basic General authored frontage")]
        public static void Prepare()
        {
            RequireEdit();
            if (Directory.Exists(Folder)) throw new InvalidOperationException("Existing or partial frontage assets must be reviewed, never overwritten.");
            var document = JObject.Parse(File.ReadAllText(Path.Combine(Source, "basic-general-meshes-v3.json")));
            var parts = (JArray)document["parts"];
            var bindings = JArray.Parse(File.ReadAllText(Path.Combine(Source, "material-bindings-v3.json")));
            var names = new HashSet<string>();
            foreach (var p in parts)
            {
                var vertices = (JArray)p["vertices"]; var normals = (JArray)p["normals"]; var uv = (JArray)p["uv0"]; var indices = (JArray)p["triangles"];
                if (!names.Add(Safe((string)p["name"])) || vertices.Count == 0 || normals.Count != vertices.Count || uv.Count != vertices.Count || indices.Count % 3 != 0 || indices.Any(i => (int)i < 0 || (int)i >= vertices.Count))
                    throw new InvalidDataException("Invalid source buffers: " + p["name"]);
                foreach (var rows in new[] { vertices, normals, uv })
                    if (rows.Any(row => row.Any(v => float.IsNaN((float)v) || float.IsInfinity((float)v)))) throw new InvalidDataException("Non-finite source attributes.");
                if (!bindings.Any(b => (string)b["slot"] == (string)p["material"])) throw new InvalidDataException("Missing material binding: " + p["material"]);
            }
            Directory.CreateDirectory(Folder + "/Meshes"); Directory.CreateDirectory(Folder + "/Materials"); Directory.CreateDirectory(Folder + "/Textures"); Directory.CreateDirectory(Evidence);
            var materials = bindings.ToDictionary(b => (string)b["slot"], Material);
            var root = new GameObject(RootName);
            try
            {
                foreach (var p in parts)
                {
                    var mesh = new Mesh { name = (string)p["name"], indexFormat = IndexFormat.UInt32 };
                    mesh.vertices = p["vertices"].Select(UnityPoint).ToArray(); mesh.normals = p["normals"].Select(UnityPoint).ToArray();
                    mesh.uv = p["uv0"].Select(a => new Vector2((float)a[0], (float)a[1])).ToArray();
                    mesh.triangles = UnityIndices(p["triangles"]); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                    AssetDatabase.CreateAsset(mesh, Folder + "/Meshes/" + Safe(mesh.name) + ".asset");
                    string groupName = (string)p["group"]; var group = root.transform.Find(groupName);
                    if (!group) { group = new GameObject(groupName).transform; group.SetParent(root.transform, false); }
                    var go = new GameObject(mesh.name); go.transform.SetParent(group, false); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[(string)p["material"]];
                    renderer.shadowCastingMode = (string)p["material"] == "Collected sand" ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    renderer.receiveShadows = true;
                }
                PrefabUtility.SaveAsPrefabAsset(root, Prefab);
            }
            finally { Object.DestroyImmediate(root); }
            AssetDatabase.SaveAssets();
            Write("basic-general-prepared.json", new { utc = DateTime.UtcNow, source = Source, prefab = Prefab, parts = parts.Count, triangles = parts.Sum(p => p["triangles"].Count() / 3), winding = "Reflect interchange X and reverse triangle order to preserve front-view handedness", tangents = "Recalculated from retained UV0 and loop normals", status = "Prepared asset only; no native acceptance" });
        }

        [MenuItem("Athen Hill/Phase 1/Correct Basic General import handedness")]
        public static void CorrectHandedness()
        {
            RequireEdit();
            string record = Path.Combine(Evidence, "basic-general-coordinate-correction.json");
            if (File.Exists(record)) throw new InvalidOperationException("Correction already recorded; inspect rather than repeat.");
            var parts = JObject.Parse(File.ReadAllText(Path.Combine(Source, "basic-general-meshes-v3.json")))["parts"].ToArray();
            var meshes = parts.Select(p => AssetDatabase.LoadAssetAtPath<Mesh>(Folder + "/Meshes/" + Safe((string)p["name"]) + ".asset")).ToArray();
            for (int i = 0; i < parts.Length; i++)
                if (!meshes[i] || !meshes[i].vertices.SequenceEqual(parts[i]["vertices"].Select(V))) throw new InvalidOperationException("Mesh was edited or already converted: " + parts[i]["name"]);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); chunks.ShowSources(true);
            for (int i = 0; i < parts.Length; i++)
            {
                var mesh = meshes[i]; var p = parts[i]; Undo.RecordObject(mesh, "Correct frontage coordinate conversion");
                mesh.vertices = p["vertices"].Select(UnityPoint).ToArray(); mesh.normals = p["normals"].Select(UnityPoint).ToArray(); mesh.triangles = UnityIndices(p["triangles"]);
                mesh.RecalculateTangents(); mesh.RecalculateBounds(); EditorUtility.SetDirty(mesh);
            }
            AssetDatabase.SaveAssets();
            Write("basic-general-coordinate-correction.json", new { utc = DateTime.UtcNow, reason = "Native front view exposed mirrored lettering; a symmetric cube winding check had not tested handedness", conversion = "Blender (x,y,z) to Unity (-x,z,-y), reversed triangle order, regenerated tangents", preserved = "Mesh GUIDs, UV0, topology, material assignments, prefab root, dimensions and all gameplay colliders", parts = parts.Length, originalInterchange = Path.Combine(Source, "basic-general-meshes-v3.json") });
            StaticRenderChunksEditor.Rebuild(chunks);
        }

        static Material Material(JToken binding)
        {
            string slot = (string)binding["slot"], path = Folder + "/Materials/" + Safe(slot) + ".mat";
            Material m;
            if (WardBuildingMaterials.Slots.Contains(slot))
            {
                var original = AssetDatabase.LoadAssetAtPath<Material>(WardBuildingMaterials.Folder + "/" + slot + "/" + slot + ".mat");
                if (!original) throw new InvalidOperationException("Shared building material missing: " + slot);
                m = new Material(original);
            }
            else
            {
                m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                m.SetFloat("_WorkflowMode", 1); m.SetFloat("_Metallic", (float?)binding["metal"] ?? 0);
                m.SetFloat("_Smoothness", binding["roughness"]?.Type == JTokenType.Float || binding["roughness"]?.Type == JTokenType.Integer ? 1 - (float)binding["roughness"] : .3f);
                var albedo = Texture((string)binding["base"], true, false);
                var normal = Texture((string)binding["normal"], false, true);
                var packed = Texture((string)binding["metalSmooth"], false, false);
                if (albedo) m.SetTexture("_BaseMap", albedo);
                if (normal) { m.SetTexture("_BumpMap", normal); m.SetFloat("_BumpScale", 1); m.EnableKeyword("_NORMALMAP"); }
                if (packed) { m.SetTexture("_MetallicGlossMap", packed); m.SetFloat("_Metallic", 1); m.SetFloat("_Smoothness", 1); m.EnableKeyword("_METALLICSPECGLOSSMAP"); }
            }
            m.name = "BasicGeneral " + slot; m.enableInstancing = true;
            var tint = V(binding["tint"]); m.SetColor("_BaseColor", new Color(tint.x, tint.y, tint.z, 1));
            if ((bool?)binding["alpha"] == true)
            {
                m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha); m.SetFloat("_ZWrite", 0);
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = (int)RenderQueue.Transparent; m.SetShaderPassEnabled("ShadowCaster", false);
            }
            AssetDatabase.CreateAsset(m, path); return m;
        }

        static Texture2D Texture(string source, bool srgb, bool normal)
        {
            if (string.IsNullOrEmpty(source)) return null;
            string path;
            if (source.Contains("/art/quality_20260908/lamps/textures/"))
                path = "Assets/AthenHill/Art/Quality/Lamps/Textures/" + Path.GetFileName(source);
            else if (source.StartsWith(Application.dataPath + "/", StringComparison.Ordinal)) path = "Assets/" + source.Substring(Application.dataPath.Length + 1);
            else
            {
                path = Folder + "/Textures/" + Path.GetFileName(source);
                if (!File.Exists(path)) File.Copy(source, path);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var importer = (TextureImporter)AssetImporter.GetAtPath(path);
                importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default; importer.sRGBTexture = srgb;
                importer.GetSourceTextureWidthAndHeight(out int width, out int height); importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(width, height));
                importer.npotScale = TextureImporterNPOTScale.None; importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
                importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.SaveAndReimport();
            }
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!texture) throw new InvalidOperationException("Missing documented map: " + path);
            return texture;
        }

        [MenuItem("Athen Hill/Phase 1/Install reviewed Basic General frontage")]
        public static void Install()
        {
            RequireEdit(); var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Save current scene edits first.");
            if (GameObject.Find(RootName)) throw new InvalidOperationException("Frontage already installed; preserve edits.");
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab); if (!prefab) throw new InvalidOperationException("Prepare the inspected source first.");
            var old = GameObject.Find("Post-war salvage/Basic General repaired/Meshy visual");
            if (!old || old.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3 != 4277) throw new InvalidOperationException("Original visual changed; re-inspect this parcel.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); if (!chunks) throw new InvalidOperationException("Missing render-source controller.");
            var frozen = JArray.Parse(File.ReadAllText(Path.Combine(Source, "preserved-colliders.json")));
            var colliders = frozen.Select(row =>
            {
                var go = GameObject.Find((string)row["path"]); var c = go ? go.GetComponent<Collider>() : null;
                if (!c || !c.enabled || Vector3.Distance(c.bounds.center, V(row["center"])) > .002f || Vector3.Distance(c.bounds.size, V(row["size"])) > .002f) throw new InvalidOperationException("Frozen gameplay collider changed: " + row["path"]);
                return c;
            }).ToArray();
            var before = colliders.Select(c => new { id = GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(), c.name, center = A(c.bounds.center), size = A(c.bounds.size), c.enabled }).ToArray();
            Directory.CreateDirectory(Evidence); string backup = Path.Combine(Evidence, "before-basic-general-install.unity");
            if (File.Exists(backup) || !EditorSceneManager.SaveScene(scene, backup, true)) throw new IOException("Cannot create unique recovery scene.");
            chunks.ShowSources(true);
            string[] retire = { "Post-war salvage/Basic General repaired/Meshy visual", "AuthoredWorld/BLD_general_porch", "AuthoredWorld/BLD_general_first_step" };
            foreach (string path in retire)
            {
                var renderer = GameObject.Find(path).GetComponent<MeshRenderer>(); Undo.RecordObject(renderer, "Retain previous Basic General visual"); renderer.enabled = false;
            }
            var oldShell = old.GetComponent<MeshCollider>();
            if (oldShell) { Undo.RecordObject(oldShell, "Retain old visual collision"); oldShell.enabled = false; }
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab); instance.name = RootName; instance.transform.position = new Vector3(8, .5f, 15.1f); instance.transform.rotation = Quaternion.identity; instance.transform.localScale = Vector3.one;
            Undo.RegisterCreatedObjectUndo(instance, "Install reviewed Basic General frontage");
            chunks.sourceRoots = chunks.sourceRoots.Concat(new[] { instance.transform }).ToArray(); EditorUtility.SetDirty(chunks);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Write("basic-general-installation.json", new { utc = DateTime.UtcNow, prefab = Prefab, position = A(instance.transform.position), scale = A(instance.transform.localScale), retiredVisuals = retire, preservedColliders = before, oldMeshColliderRetained = oldShell != null, status = "Needs chunk rebuild, save/reopen, native review, trade/approach and frame-time checks" });
        }
    }
}
#endif
