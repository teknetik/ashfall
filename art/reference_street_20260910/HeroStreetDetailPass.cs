// Staged Editor-only authoring helper. Copy into Assets/AthenHill/Editor after review.
// It never executes on import or at runtime. Originals and gameplay roots stay intact.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    public static class HeroStreetDetailPass
    {
        public const string MasonryFolder = "Assets/AthenHill/Art/ReferenceStreet/20260910/HeroMasonry";
        const string ParentPath = "Reference street thresholds and detail";
        const string AdditionName = "Masonry revision 20260910";
        const string Revision = "hero-masonry-v1";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/reference_street_20260910");
        static string Evidence => Path.Combine(Repo, "unity/evidence/reference-street/20260910/hero-masonry-v1-install");

        [Serializable]
        public sealed class Part
        {
            public string name, sourcePath, family, material;
            public float[][] positions, normals, uv;
            public int[] indices;
            public bool castsShadow = true;
        }

        public sealed class ImportResult
        {
            public int replacements, additions;
            public long triangles;
            public List<object> changes = new List<object>();
        }

        sealed class ExistingTransform
        {
            public Transform transform;
            public string id, path, parentId;
            public Vector3 localPosition, localScale;
            public Quaternion localRotation;
            public bool activeSelf;
            public int layer;
            public string tag;
        }

        static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t, null);
        static string Id(Object o) => o ? GlobalObjectId.GetGlobalObjectIdSlow(o).ToString() : "null";
        static Vector3 V(float[] p) => new Vector3(p[0], p[1], p[2]);
        static float[] V(Vector3 p) => new[] { p.x, p.y, p.z };
        static string Safe(string text) => new string(text.Select(c => char.IsLetterOrDigit(c) || c == '_' ? c : '_').ToArray());
        static bool Finite(float n) => !float.IsNaN(n) && !float.IsInfinity(n);
        static string Sha(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        static void Write(string path, object value) => File.WriteAllText(path, JsonConvert.SerializeObject(value, Formatting.Indented));

        static string RepoFile(string path)
        {
            string result = Path.GetFullPath(Path.Combine(Repo, path));
            if (!result.StartsWith(Repo + Path.DirectorySeparatorChar, StringComparison.Ordinal) || !File.Exists(result))
                throw new InvalidDataException("Missing file or path outside repository: " + path);
            return result;
        }

        static IEnumerable<Transform> SceneTransforms(Scene scene) => scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true));

        static Transform ExactTransform(Scene scene, string path)
        {
            var matches = SceneTransforms(scene).Where(t => PathOf(t) == path).ToArray();
            if (matches.Length != 1) throw new InvalidDataException("Expected one scene transform: " + path + "; found " + matches.Length);
            return matches[0];
        }

        static void MeshGuard(Transform t, string expected)
        {
            var filter = t.GetComponent<MeshFilter>();
            var renderer = t.GetComponent<MeshRenderer>();
            if (!filter || !renderer || !filter.sharedMesh || string.IsNullOrEmpty(expected) || AssetDatabase.GetAssetPath(filter.sharedMesh) != expected)
                throw new InvalidDataException("Current source mesh changed: " + PathOf(t));
        }

        static string CollisionSignature(Scene scene)
        {
            var entries = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Collider>(true))
                .OrderBy(c => PathOf(c.transform), StringComparer.Ordinal).ThenBy(Id)
                .Select(c => new {
                    id = Id(c), path = PathOf(c.transform), type = c.GetType().FullName,
                    activeSelf = c.gameObject.activeSelf, activeInHierarchy = c.gameObject.activeInHierarchy,
                    c.enabled, c.isTrigger, layer = c.gameObject.layer,
                    matrix = Enumerable.Range(0, 16).Select(i => c.transform.localToWorldMatrix[i]).ToArray(),
                    serialized = EditorJsonUtility.ToJson(c)
                }).ToArray();
            return JsonConvert.SerializeObject(entries);
        }

        static string ActorSignature(Scene scene)
        {
            // Includes the fourth yard mechanic and every route reference; the legacy
            // DistrictCityPass signature alone intentionally omits that actor.
            var walkers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<AmbientWalker>(true))
                .OrderBy(w => PathOf(w.transform), StringComparer.Ordinal).Select(w => new {
                    id = Id(w), path = PathOf(w.transform), serialized = EditorJsonUtility.ToJson(w),
                    waypoints = w.waypoints.Select(t => new {
                        id = Id(t), path = t ? PathOf(t) : null,
                        position = t ? V(t.position) : null,
                        matrix = t ? Enumerable.Range(0, 16).Select(i => t.localToWorldMatrix[i]).ToArray() : null
                    }).ToArray()
                }).ToArray();
            var actors = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<ActorAnimation>(true))
                .OrderBy(a => PathOf(a.transform), StringComparer.Ordinal).Select(a => new {
                    id = Id(a), path = PathOf(a.transform), serialized = EditorJsonUtility.ToJson(a)
                }).ToArray();
            var players = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<PlayerMotor>(true))
                .OrderBy(p => PathOf(p.transform), StringComparer.Ordinal).Select(p => new {
                    id = Id(p), path = PathOf(p.transform), serialized = EditorJsonUtility.ToJson(p)
                }).ToArray();
            return JsonConvert.SerializeObject(new { legacy = DistrictCityPass.GameplaySignature(), walkers, actors, players });
        }

        static ExistingTransform[] CaptureTransforms(Scene scene, Transform generated)
        {
            return SceneTransforms(scene).Where(t => !generated || (t != generated && !t.IsChildOf(generated))).Select(t => new ExistingTransform {
                transform = t, id = Id(t), path = PathOf(t), parentId = Id(t.parent),
                localPosition = t.localPosition, localRotation = t.localRotation, localScale = t.localScale,
                activeSelf = t.gameObject.activeSelf, layer = t.gameObject.layer, tag = t.gameObject.tag
            }).ToArray();
        }

        static void VerifyTransforms(IEnumerable<ExistingTransform> before, HashSet<string> disabled)
        {
            foreach (var old in before)
            {
                var t = old.transform;
                if (!t || Id(t) != old.id || PathOf(t) != old.path || Id(t.parent) != old.parentId ||
                    t.localPosition != old.localPosition || t.localRotation != old.localRotation || t.localScale != old.localScale ||
                    t.gameObject.layer != old.layer || t.gameObject.tag != old.tag ||
                    t.gameObject.activeSelf != (disabled.Contains(old.path) ? false : old.activeSelf))
                    throw new InvalidOperationException("Existing source/actor transform changed: " + old.path);
            }
        }

        static Texture2D ImportMap(string path, bool color, bool normal)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!importer) throw new InvalidDataException("No texture importer: " + path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = color;
            importer.mipmapEnabled = true;
            importer.streamingMipmaps = true;
            importer.maxTextureSize = 4096;
            importer.anisoLevel = 8;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.compressionQuality = 100;
            importer.isReadable = false;
            importer.SaveAndReimport();
            var result = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!result || result.width != 4096 || result.height != 4096)
                throw new InvalidDataException("Expected retained full 4096 texture: " + path);
            return result;
        }

        static void PackRoughness(string roughnessSource, string destination)
        {
            Texture2D rough = null, packed = null;
            try
            {
                rough = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                if (!rough.LoadImage(File.ReadAllBytes(roughnessSource))) throw new InvalidDataException("Could not load roughness map");
                if (rough.width != 4096 || rough.height != 4096) throw new InvalidDataException("Roughness is not retained 4096 source");
                var pixels = rough.GetPixels32();
                for (int i = 0; i < pixels.Length; i++) pixels[i] = new Color32(0, 0, 0, (byte)(255 - pixels[i].r));
                packed = new Texture2D(rough.width, rough.height, TextureFormat.RGBA32, false, true);
                packed.SetPixels32(pixels); packed.Apply(false, false);
                File.WriteAllBytes(destination, packed.EncodeToPNG());
            }
            finally
            {
                if (rough) Object.DestroyImmediate(rough);
                if (packed) Object.DestroyImmediate(packed);
            }
        }

        static Dictionary<string, Material> PrepareMaterials(JObject specifications, List<object> audit)
        {
            var result = new Dictionary<string, Material>(StringComparer.Ordinal);
            var photos = new Dictionary<string, (Texture2D color, Texture2D normal, Texture2D packed)>(StringComparer.Ordinal);
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (!shader) throw new InvalidOperationException("Installed URP Lit shader unavailable");
            foreach (var property in specifications.Properties())
            {
                var spec = (JObject)property.Value;
                string photo = (string)spec["asset"];
                if (!photos.TryGetValue(photo, out var textures))
                {
                    string directory = MasonryFolder + "/Photos/" + Safe(photo);
                    Directory.CreateDirectory(directory);
                    string colorSource = RepoFile((string)spec["baseMap"]);
                    string normalSource = RepoFile((string)spec["normalMap"]);
                    string roughSource = RepoFile((string)spec["roughnessMap"]);
                    File.Copy(colorSource, directory + "/BaseColor.png", false);
                    File.Copy(normalSource, directory + "/Normal.png", false);
                    PackRoughness(roughSource, directory + "/MetalSmooth.png");
                    AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                    textures = (ImportMap(directory + "/BaseColor.png", true, false),
                                ImportMap(directory + "/Normal.png", false, true),
                                ImportMap(directory + "/MetalSmooth.png", false, false));
                    photos.Add(photo, textures);
                    audit.Add(new {
                        photo, sourceColorSha256 = Sha(colorSource), sourceNormalSha256 = Sha(normalSource),
                        sourceRoughnessSha256 = Sha(roughSource), importedColorSha256 = Sha(directory + "/BaseColor.png"),
                        importedNormalSha256 = Sha(directory + "/Normal.png"), packedSha256 = Sha(directory + "/MetalSmooth.png"),
                        provenance = (string)spec["sourceProvenance"], size = 4096, metallic = 0,
                        alpha = "1 - linear roughness", sourceMapsRetained = true
                    });
                }
                var material = new Material(shader) { name = property.Name + " 20260910", enableInstancing = true };
                var tint = spec["baseColor"].Values<float>().ToArray();
                var scale = spec["uvScale"].Values<float>().ToArray();
                material.SetTexture("_BaseMap", textures.color);
                material.SetColor("_BaseColor", new Color(tint[0], tint[1], tint[2], tint[3]));
                // Installed URP 17.6 Lit uses the same base transformed UV for all PBR maps.
                material.SetTextureScale("_BaseMap", new Vector2(scale[0], scale[1]));
                material.SetTexture("_BumpMap", textures.normal);
                material.SetFloat("_BumpScale", (float)spec["normalStrength"]);
                material.SetTexture("_MetallicGlossMap", textures.packed);
                material.SetFloat("_Metallic", 0);
                material.SetFloat("_Smoothness", 1);
                material.SetFloat("_SmoothnessTextureChannel", 0);
                material.SetFloat("_Surface", 0);
                material.EnableKeyword("_NORMALMAP");
                material.EnableKeyword("_METALLICSPECGLOSSMAP");
                AssetDatabase.CreateAsset(material, MasonryFolder + "/" + Safe(property.Name) + ".mat");
                result.Add(property.Name, material);
            }
            return result;
        }

        static Part[] ReadParts(string path)
        {
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(path));
            if (parts == null || parts.Length == 0) throw new InvalidDataException("No geometry parts: " + path);
            foreach (var p in parts)
            {
                if (string.IsNullOrWhiteSpace(p.name) || string.IsNullOrWhiteSpace(p.material) ||
                    p.positions == null || p.normals == null || p.uv == null || p.indices == null ||
                    p.positions.Length < 3 || p.positions.Length != p.normals.Length || p.positions.Length != p.uv.Length ||
                    p.indices.Length < 3 || p.indices.Length % 3 != 0 || p.indices.Any(i => i < 0 || i >= p.positions.Length) ||
                    p.positions.Any(v => v == null || v.Length != 3 || v.Any(n => !Finite(n))) ||
                    p.normals.Any(v => v == null || v.Length != 3 || v.Any(n => !Finite(n)) || V(v).sqrMagnitude < .5f) ||
                    p.uv.Any(v => v == null || v.Length != 2 || v.Any(n => !Finite(n))))
                    throw new InvalidDataException("Invalid geometry buffers: " + p.name);
            }
            return parts;
        }

        /// <summary>
        /// Explicit reusable world-Unity Part import. Caller owns scene snapshots,
        /// ShowSources, parent registration, final invariant checks, rebuild and save.
        /// No asset overwrites, implicit replacement guards or automatic execution.
        /// </summary>
        public static ImportResult ImportParts(string jsonPath, string meshFolder, Transform additionsParent,
            IReadOnlyDictionary<string, Material> materials, IReadOnlyDictionary<string, string> expectedReplacementMeshes)
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || !additionsParent || !additionsParent.gameObject.scene.IsValid())
                throw new InvalidOperationException("Import needs an existing scene parent in Edit mode");
            if (!meshFolder.StartsWith("Assets/AthenHill/Art/", StringComparison.Ordinal) || meshFolder.Contains(".."))
                throw new InvalidDataException("New mesh destination must be an AthenHill Art folder");
            var parts = ReadParts(jsonPath);
            var scene = additionsParent.gameObject.scene;
            var replacements = new Dictionary<string, Transform>(StringComparer.Ordinal);
            var additionNames = new HashSet<string>(StringComparer.Ordinal);
            string prefix = Safe(Path.GetFileNameWithoutExtension(jsonPath));
            for (int i = 0; i < parts.Length; i++)
            {
                var p = parts[i];
                if (!materials.TryGetValue(p.material, out var material) || !material)
                    throw new InvalidDataException("Missing reviewed material: " + p.material);
                string assetPath = meshFolder + "/" + prefix + "_" + i.ToString("D4") + "_" + Safe(p.name) + ".asset";
                if (File.Exists(assetPath) || AssetDatabase.LoadMainAssetAtPath(assetPath))
                    throw new InvalidOperationException("Preserve existing authored mesh: " + assetPath);
                if (!string.IsNullOrEmpty(p.sourcePath))
                {
                    if (expectedReplacementMeshes == null || !expectedReplacementMeshes.TryGetValue(p.sourcePath, out string expected))
                        throw new InvalidDataException("No exact current-mesh guard: " + p.sourcePath);
                    var t = ExactTransform(scene, p.sourcePath);
                    MeshGuard(t, expected);
                    replacements.Add(p.sourcePath, t);
                }
                else if (!additionNames.Add(p.name) || additionsParent.Find(p.name))
                    throw new InvalidDataException("Addition name already exists: " + p.name);
            }
            Directory.CreateDirectory(meshFolder);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var result = new ImportResult();
            for (int i = 0; i < parts.Length; i++)
            {
                var p = parts[i];
                bool replacement = !string.IsNullOrEmpty(p.sourcePath);
                Transform t;
                if (replacement) { t = replacements[p.sourcePath]; result.replacements++; }
                else
                {
                    var go = new GameObject(p.name);
                    t = go.transform; t.SetParent(additionsParent, false);
                    go.layer = additionsParent.gameObject.layer;
                    go.AddComponent<MeshFilter>(); go.AddComponent<MeshRenderer>();
                    result.additions++;
                }
                var filter = t.GetComponent<MeshFilter>();
                var renderer = t.GetComponent<MeshRenderer>();
                string originalMesh = AssetDatabase.GetAssetPath(filter.sharedMesh);
                string[] originalMaterials = renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath).ToArray();
                var mesh = new Mesh { name = p.name + " hero revision", indexFormat = IndexFormat.UInt32 };
                mesh.vertices = p.positions.Select(v => t.InverseTransformPoint(V(v))).ToArray();
                mesh.normals = p.normals.Select(v => t.localToWorldMatrix.transpose.MultiplyVector(V(v)).normalized).ToArray();
                mesh.uv = p.uv.Select(v => new Vector2(v[0], v[1])).ToArray();
                mesh.triangles = p.indices;
                mesh.RecalculateTangents(); mesh.RecalculateBounds();
                string asset = meshFolder + "/" + prefix + "_" + i.ToString("D4") + "_" + Safe(p.name) + ".asset";
                AssetDatabase.CreateAsset(mesh, asset);
                filter.sharedMesh = mesh;
                renderer.sharedMaterials = new[] { materials[p.material] };
                renderer.shadowCastingMode = p.castsShadow ? ShadowCastingMode.On : ShadowCastingMode.Off;
                renderer.receiveShadows = true;
                EditorUtility.SetDirty(filter); EditorUtility.SetDirty(renderer);
                PrefabUtility.RecordPrefabInstancePropertyModifications(filter);
                PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
                result.triangles += p.indices.Length / 3;
                result.changes.Add(new {
                    path = PathOf(t), replacement, originalMesh, newMesh = asset, originalMaterials,
                    material = AssetDatabase.GetAssetPath(materials[p.material]), triangles = p.indices.Length / 3,
                    p.castsShadow, colliderAdded = false, sourceTransformPreserved = replacement
                });
            }
            return result;
        }

        public static void RefineLitterContactV1()
        {
            var scene = EditorSceneManager.GetActiveScene();
            string evidence = Path.Combine(Repo, "unity/evidence/reference-street/20260910/litter-contact-v1-install");
            if (scene.path != ImportBaseline.ScenePath || scene.isDirty || EditorApplication.isPlayingOrWillChangePlaymode || Directory.Exists(evidence))
                throw new InvalidOperationException("Saved city and a new contact revision required");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!chunks || chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Fresh source chunks required");
            var candidate = ExactTransform(scene, "Post-war salvage/trash scatter 69/Ground detail v2");
            var growth = ExactTransform(scene, "Courtyard reference pass/Vegetation/Dry joint growth 17");
            if (candidate.GetComponentsInChildren<Collider>(true).Length != 0 || growth.GetComponentsInChildren<Collider>(true).Length != 0 ||
                growth.GetComponentsInChildren<MonoBehaviour>(true).Length != 0 || !growth.gameObject.activeSelf ||
                candidate.GetComponentsInChildren<MeshFilter>(true).Any(f => AssetDatabase.GetAssetPath(f.sharedMesh) !=
                    "Assets/AthenHill/Art/Imported/Meshy/GroundDetail/20260910/trash/v2/Source/model.fbx"))
                throw new InvalidDataException("The reviewed render-only litter or growth changed");
            MeshGuard(growth, "Assets/AthenHill/Art/Courtyard/Meshes/Dry_joint_growth_17.asset");
            var transforms = CaptureTransforms(scene, chunks.generatedRoot).Where(t => t.transform != candidate).ToArray();
            string collision = CollisionSignature(scene), actors = ActorSignature(scene);
            Vector3 oldLocal = candidate.localPosition, oldWorld = candidate.position;
            Directory.CreateDirectory(evidence); File.Copy(scene.path, Path.Combine(evidence, "before-scene.unity"), false);
            try
            {
                chunks.ShowSources(true);
                // Sink only the visual bed 18 mm into the stone; root/collider remain untouched.
                candidate.position = oldWorld + Vector3.down * .018f;
                growth.gameObject.SetActive(false); // This clump visibly crossed cans and sacks.
                PrefabUtility.RecordPrefabInstancePropertyModifications(candidate);
                EditorUtility.SetDirty(candidate); EditorUtility.SetDirty(growth.gameObject);
                var disabled = new HashSet<string> { PathOf(growth) };
                VerifyTransforms(transforms, disabled);
                if (collision != CollisionSignature(scene) || actors != ActorSignature(scene)) throw new InvalidOperationException("Contact edit changed gameplay");
                StaticRenderChunksEditor.Rebuild(chunks); VerifyTransforms(transforms, disabled);
                if (collision != CollisionSignature(scene) || actors != ActorSignature(scene) ||
                    chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Saved contact invariants failed");
                EditorSceneManager.SaveScene(scene);
                Write(Path.Combine(evidence, "installation.json"), new { utc = DateTime.UtcNow, savedSceneSha256 = Sha(scene.path),
                    candidate = PathOf(candidate), beforeLocal = V(oldLocal), afterLocal = V(candidate.localPosition),
                    worldEmbeddingMetres = .018f, deactivatedIntersectingClump = PathOf(growth),
                    allCollidersPreserved = true, allActorsAndRoutesPreserved = true, chunksFresh = true, nativeVisualAcceptance = false });
            }
            catch (Exception e) { Write(Path.Combine(evidence, "failure.json"), new { exception = e.ToString(), sceneDirty = scene.isDirty }); throw; }
        }

        [MenuItem("Athen Hill/Reference street/Repair hero masonry 20260910 v3")]
        public static void ApplyMasonryV3()
        {
            var scene = EditorSceneManager.GetActiveScene();
            const string revision = "hero-masonry-v3";
            const string folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/HeroMasonryV3";
            const string newName = "Masonry revision 20260910 v3";
            string evidence = Path.Combine(Repo, "unity/evidence/reference-street/20260910/hero-masonry-v3-install");
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || scene.isDirty ||
                scene.path != ImportBaseline.ScenePath || EditorSceneManager.sceneCount != 1)
                throw new InvalidOperationException("Open the saved clean city in Edit mode");
            if (Directory.Exists(folder) || Directory.Exists(evidence)) throw new InvalidOperationException("Preserve existing v3 attempt");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!chunks || chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Current source chunks required");
            var parent = ExactTransform(scene, ParentPath);
            var oldParent = ExactTransform(scene, ParentPath + "/" + AdditionName);
            if (!chunks.sourceRoots.Contains(parent) || !oldParent.gameObject.activeSelf || parent.Find(newName) ||
                oldParent.GetComponentsInChildren<Collider>(true).Length != 0 || oldParent.GetComponentsInChildren<MonoBehaviour>(true).Length != 0)
                throw new InvalidDataException("Expected the installed visual-only v1 masonry");
            var previous = JObject.Parse(File.ReadAllText(Path.Combine(Evidence, "installation.json")));
            var manifest = JObject.Parse(File.ReadAllText(Path.Combine(Source, revision + "-manifest.json")));
            string proofPath = Path.Combine(Source, revision + "-geometry-proof.json");
            var proof = JObject.Parse(File.ReadAllText(proofPath));
            if ((string)manifest["revision"] != revision || (int)manifest["replacementCount"] != 8 ||
                (int)manifest["additionCount"] != 386 || proof["allParts"].Count() != 394 || proof["cuts"].Count() != 22)
                throw new InvalidDataException("Unexpected closed-solid repair contract");
            foreach (var part in proof["allParts"])
                if ((int)part["boundaryEdges"] != 0 || (int)part["nonManifoldEdges"] != 0 ||
                    (int)part["nonContiguousEdges"] != 0 || (double)part["signedVolume"] <= 0)
                    throw new InvalidDataException("Unclosed or inverted source part: " + part["name"]);
            foreach (var cut in proof["cuts"])
            {
                if ((double)cut["after"]["signedVolume"] > (double)cut["before"]["signedVolume"] + .00001)
                    throw new InvalidDataException("Difference enlarged its source");
                for (int axis = 0; axis < 3; axis++)
                    if ((double)cut["after"]["min"][axis] < (double)cut["before"]["min"][axis] - .00001 ||
                        (double)cut["after"]["max"][axis] > (double)cut["before"]["max"][axis] + .00001)
                        throw new InvalidDataException("Difference exceeded its envelope");
            }
            var expected = previous["replaced"]["changes"].ToDictionary(p => (string)p["path"], p => (string)p["newMesh"], StringComparer.Ordinal);
            foreach (var pair in expected) MeshGuard(ExactTransform(scene, pair.Key), pair.Value);
            foreach (var old in previous["added"]["changes"])
                MeshGuard(ExactTransform(scene, (string)old["path"]), (string)old["newMesh"]);
            if (oldParent.childCount != 386) throw new InvalidDataException("V1 addition roster changed");
            var materials = ((JObject)manifest["materials"]).Properties().ToDictionary(p => p.Name,
                p => AssetDatabase.LoadAssetAtPath<Material>(MasonryFolder + "/" + p.Name + ".mat"));
            if (materials.Values.Any(m => !m)) throw new InvalidDataException("Retained masonry material missing");
            string replacements = Path.Combine(Source, revision + "-replacements.json"), additions = Path.Combine(Source, revision + "-additions.json");
            var parts = ReadParts(replacements).Concat(ReadParts(additions)).ToArray();
            if (parts.Length != 394 || parts.Sum(p => (long)p.indices.Length / 3) != (long)manifest["triangles"])
                throw new InvalidDataException("Repair geometry differs from manifest");
            Directory.CreateDirectory(evidence);
            File.Copy(scene.path, Path.Combine(evidence, "before-scene.unity"), false);
            File.Copy(proofPath, Path.Combine(evidence, "geometry-proof.json"), false);
            var transforms = CaptureTransforms(scene, chunks.generatedRoot);
            string collision = CollisionSignature(scene), actors = ActorSignature(scene);
            try
            {
                chunks.ShowSources(true);
                var newParent = new GameObject(newName).transform; newParent.SetParent(parent, false);
                var replaced = ImportParts(replacements, folder + "/Meshes", newParent, materials, expected);
                var added = ImportParts(additions, folder + "/Meshes", newParent, materials, expected);
                oldParent.gameObject.SetActive(false);
                var disabled = new HashSet<string> { PathOf(oldParent) };
                VerifyTransforms(transforms, disabled);
                if (collision != CollisionSignature(scene) || actors != ActorSignature(scene)) throw new InvalidOperationException("Gameplay invariants changed");
                AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks);
                VerifyTransforms(transforms, disabled);
                if (collision != CollisionSignature(scene) || actors != ActorSignature(scene) || chunks.editingSources ||
                    chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Saved repair invariants failed");
                EditorSceneManager.SaveScene(scene);
                Write(Path.Combine(evidence, "installation.json"), new { utc = DateTime.UtcNow, savedSceneSha256 = Sha(scene.path),
                    replaced, added, geometryProofSha256 = Sha(proofPath), sourceGeometryHashes = new[] { Sha(replacements), Sha(additions) },
                    originalSourceTransformsVerified = transforms.Length, allCollidersPreserved = true, allActorsAndRoutesPreserved = true,
                    chunksFresh = true, retainedRejectedParent = PathOf(oldParent), nativeVisualAcceptance = false });
            }
            catch (Exception e) { Write(Path.Combine(evidence, "failure.json"), new { exception = e.ToString(), sceneDirty = scene.isDirty }); throw; }
        }

        [MenuItem("Athen Hill/Reference street/Install hero masonry 20260910 v1")]
        public static void ApplyMasonryV1()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.path != ImportBaseline.ScenePath || scene.isDirty)
                throw new InvalidOperationException("Open the saved, clean AthenHill scene in Edit mode");
            if (EditorSceneManager.sceneCount != 1) throw new InvalidOperationException("Close unrelated scenes before the explicit saved-scene import");
            if (Directory.Exists(MasonryFolder)) throw new InvalidOperationException("Hero masonry destination already exists; preserve and review the installed revision");
            if (Directory.Exists(Evidence)) throw new InvalidOperationException("Installation evidence already exists; inspect the prior attempt instead of overwriting it");
            var manifest = JObject.Parse(File.ReadAllText(Path.Combine(Source, Revision + "-manifest.json")));
            if ((string)manifest["revision"] != Revision || (int)manifest["replacementCount"] != 8 ||
                manifest["regions"].Count() != 8 || manifest["quietPlasterMaterialTargets"].Count() != 35 ||
                manifest["disableOldSubstrates"].Count() != 14)
                throw new InvalidDataException("Unexpected reviewed masonry contract counts");
            if (Sha(Path.Combine(Source, "building-source.json")) != (string)manifest["currentSourceSha256"])
                throw new InvalidDataException("The authored Unity source export changed");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!chunks || chunks.gameObject.scene != scene || chunks.editingSources ||
                chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Saved render chunks must be current before this pass");
            var parent = ExactTransform(scene, ParentPath);
            if (!chunks.sourceRoots.Contains(parent)) throw new InvalidDataException("Existing reference-detail parent is not registered in render chunks");
            if (parent.Find(AdditionName)) throw new InvalidOperationException("Masonry addition child already exists");
            var expectedMeshes = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var region in manifest["regions"])
            {
                string path = (string)region["sourcePath"], expected = (string)region["expectedCurrentMeshPath"];
                MeshGuard(ExactTransform(scene, path), expected);
                expectedMeshes.Add(path, expected);
            }
            var quiet = new List<Transform>();
            foreach (var target in manifest["quietPlasterMaterialTargets"])
            {
                var t = ExactTransform(scene, (string)target["path"]);
                MeshGuard(t, (string)target["expectedMeshPath"]);
                var actual = t.GetComponent<Renderer>().sharedMaterials.Select(AssetDatabase.GetAssetPath);
                if (!actual.SequenceEqual(target["expectedMaterialPaths"].Values<string>()))
                    throw new InvalidDataException("Plaster material roster changed: " + PathOf(t));
                quiet.Add(t);
            }
            var disabled = new HashSet<string>(StringComparer.Ordinal);
            var substrates = new List<Transform>();
            foreach (var old in manifest["disableOldSubstrates"])
            {
                string path = (string)old["path"];
                var t = ExactTransform(scene, path); MeshGuard(t, (string)old["expectedMeshPath"]);
                if (!t.gameObject.activeInHierarchy || t.childCount != 0 || t.GetComponents<Collider>().Length != 0 || t.GetComponents<MonoBehaviour>().Length != 0)
                    throw new InvalidDataException("Old substrate is not an active visual-only leaf: " + path);
                disabled.Add(path); substrates.Add(t);
            }
            foreach (var spec in ((JObject)manifest["materials"]).Properties().Select(p => p.Value))
                foreach (var channel in new[] { "baseMap", "normalMap", "roughnessMap", "sourceProvenance" }) RepoFile((string)spec[channel]);
            string replacementsFile = RepoFile("art/reference_street_20260910/" + (string)manifest["replacementsFile"]);
            string additionsFile = RepoFile("art/reference_street_20260910/" + (string)manifest["additionsFile"]);
            var replacementParts = ReadParts(replacementsFile);
            var additionParts = ReadParts(additionsFile);
            if (replacementParts.Length != 8 || replacementParts.Any(p => string.IsNullOrEmpty(p.sourcePath)) ||
                !replacementParts.Select(p => p.sourcePath).OrderBy(p => p).SequenceEqual(expectedMeshes.Keys.OrderBy(p => p)) ||
                additionParts.Any(p => !string.IsNullOrEmpty(p.sourcePath)) || additionParts.Length != (int)manifest["additionCount"])
                throw new InvalidDataException("Geometry parts differ from the reviewed source replacement contract");
            var materialKeys = ((JObject)manifest["materials"]).Properties().Select(p => p.Name).ToHashSet();
            if (replacementParts.Concat(additionParts).Any(p => !materialKeys.Contains(p.material)))
                throw new InvalidDataException("A geometry material is missing from the contract");
            if (replacementParts.Concat(additionParts).Sum(p => (long)p.indices.Length / 3) != (long)manifest["triangles"])
                throw new InvalidDataException("Geometry triangle totals differ from manifest");

            // Every validation above is read-only. Only now make the reviewable change.
            Directory.CreateDirectory(Evidence);
            File.Copy(scene.path, Path.Combine(Evidence, "before-scene.unity"), false);
            File.Copy(Path.Combine(Source, Revision + "-manifest.json"), Path.Combine(Evidence, "authored-manifest.json"), false);
            var beforeTransforms = CaptureTransforms(scene, chunks.generatedRoot);
            string beforeCollision = CollisionSignature(scene), beforeActors = ActorSignature(scene);
            File.WriteAllText(Path.Combine(Evidence, "colliders-before.json"), beforeCollision);
            File.WriteAllText(Path.Combine(Evidence, "actors-before.json"), beforeActors);
            Write(Path.Combine(Evidence, "original-transforms.json"), beforeTransforms.Select(t => new {
                t.id, t.path, t.parentId, localPosition = V(t.localPosition),
                rotation = new[] { t.localRotation.x, t.localRotation.y, t.localRotation.z, t.localRotation.w },
                localScale = V(t.localScale), t.activeSelf, t.layer, t.tag
            }));
            var materialAudit = new List<object>();
            try
            {
                Directory.CreateDirectory(MasonryFolder);
                var materials = PrepareMaterials((JObject)manifest["materials"], materialAudit);
                chunks.ShowSources(true);
                var assignments = new List<object>();
                foreach (var t in quiet)
                {
                    var renderer = t.GetComponent<Renderer>();
                    assignments.Add(new { path = PathOf(t), oldMaterials = renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath).ToArray(),
                        newMaterial = AssetDatabase.GetAssetPath(materials["HeroLimePlaster"]) });
                    renderer.sharedMaterials = new[] { materials["HeroLimePlaster"] };
                    EditorUtility.SetDirty(renderer); PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
                }
                var newParent = new GameObject(AdditionName).transform;
                newParent.SetParent(parent, false);
                var replaced = ImportParts(replacementsFile, MasonryFolder + "/Meshes", newParent, materials, expectedMeshes);
                var added = ImportParts(additionsFile, MasonryFolder + "/Meshes", newParent, materials, expectedMeshes);
                foreach (var t in substrates)
                {
                    t.gameObject.SetActive(false); EditorUtility.SetDirty(t.gameObject);
                    PrefabUtility.RecordPrefabInstancePropertyModifications(t.gameObject);
                }
                VerifyTransforms(beforeTransforms, disabled);
                if (beforeCollision != CollisionSignature(scene) || beforeActors != ActorSignature(scene))
                    throw new InvalidOperationException("Collider or complete actor/route signature changed; do not save the scene");
                AssetDatabase.SaveAssets();
                StaticRenderChunksEditor.Rebuild(chunks); // Explicit source rebuild, including its ordinary saved-scene operation.
                VerifyTransforms(beforeTransforms, disabled);
                string afterCollision = CollisionSignature(scene), afterActors = ActorSignature(scene);
                if (beforeCollision != afterCollision || beforeActors != afterActors ||
                    chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                    throw new InvalidOperationException("Post-rebuild preservation or fresh-source guard failed; inspect retained before-scene");
                EditorSceneManager.SaveScene(scene);
                File.WriteAllText(Path.Combine(Evidence, "colliders-after.json"), afterCollision);
                File.WriteAllText(Path.Combine(Evidence, "actors-after.json"), afterActors);
                Write(Path.Combine(Evidence, "installation.json"), new {
                    utc = DateTime.UtcNow, scene = scene.path, savedSceneSha256 = Sha(scene.path),
                    geometryFiles = new[] { new { path = replacementsFile, sha256 = Sha(replacementsFile) }, new { path = additionsFile, sha256 = Sha(additionsFile) } },
                    replaced, added, assignments, disabledSubstratePaths = disabled.OrderBy(p => p).ToArray(), materialAudit,
                    originalSourceTransformsVerified = beforeTransforms.Length, allCollidersPreserved = true,
                    allActorsAndRoutesPreserved = true, chunksFresh = true, originalAssetsRetained = true,
                    nativeVisualAcceptance = false, next = "Build Linux and review matched native wide and player-height views."
                });
                Debug.Log("Hero masonry v1 saved: " + replaced.replacements + " replacements, " + added.additions + " additions; original colliders, actors, routes and source transforms preserved.");
            }
            catch (Exception exception)
            {
                Write(Path.Combine(Evidence, "failure.json"), new {
                    utc = DateTime.UtcNow, exception = exception.ToString(), sceneDirty = scene.isDirty,
                    action = "Inspect this attempt and retained before-scene. Do not retry or overwrite partial outputs automatically."
                });
                throw;
            }
        }
        // Authored projector positions follow selected coping joints and wall feet.
        // Projectors conform to the actual surface and add no collision or flat
        // cards across the repaired masonry recesses. Original maps are reused.
        public static void AddLocalizedWeatheringV1()
        {
            const string groupName = "Reference street localized sediment 20260910 v1";
            const string folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/LocalizedSedimentV1";
            var scene = SceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.isDirty || scene.path != ImportBaseline.ScenePath)
                throw new InvalidOperationException("Open the saved city in Edit mode.");
            if (SceneTransforms(scene).Any(t => t.name == groupName) || Directory.Exists(folder)) throw new InvalidOperationException("Preserve existing sediment revision.");
            var chunks = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<StaticRenderChunks>(true)).Single();
            if (chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Existing render sources are stale.");
            var rendererData = AssetDatabase.LoadAssetAtPath<UnityEngine.Rendering.Universal.UniversalRendererData>("Assets/Settings/PC_Renderer.asset");
            if (!rendererData || !rendererData.rendererFeatures.OfType<UnityEngine.Rendering.Universal.DecalRendererFeature>().Any(f => f.isActive))
                throw new InvalidOperationException("The existing accepted decal renderer feature must be active.");
            var template = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat");
            var runoff = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/AthenHill/Art/ReferenceStreet/20260909/MineralRunoff/BaseColor.png");
            if (!template || !template.shader.isSupported || !runoff || !template.HasProperty("Base_Map")) throw new InvalidDataException("Existing sediment shader/maps missing.");
            var deposits = new[] {
                ("Finery north coping west", new Vector3(19.35f,5.87f,-14.175f), .72f,1.65f,Vector3.back, false,.95f),
                ("Finery north coping east", new Vector3(23.12f,5.97f,-14.175f), .61f,1.45f,Vector3.back, false,.9f),
                ("Finery parapet seam west", new Vector3(16.69f,7.48f,-19.25f), .66f,.48f,Vector3.right, false,1f),
                ("Finery parapet seam east", new Vector3(16.69f,7.47f,-15.47f), .48f,.5f,Vector3.right, false,.95f),
                ("Finery upper pier joint west", new Vector3(16.775f,6.02f,-19.35f), .56f,1.14f,Vector3.right, false,.82f),
                ("Finery upper pier joint east", new Vector3(16.775f,6.12f,-16.62f), .48f,.94f,Vector3.right, false,.9f),
                ("Field gable rain trace", new Vector3(17.725f,5.13f,-7.82f), .63f,.46f,Vector3.right, false,.92f),
                ("Field gable outer joint", new Vector3(17.725f,4.96f,-11.63f), .48f,.25f,Vector3.right, false,.86f),
                ("Field poster pier footing", new Vector3(17.845f,.675f,-11.96f), .63f,.35f,Vector3.right, true,.34f),
                ("Field side sheltered foot", new Vector3(20.34f,.66f,-5.155f), 2.45f,.32f,Vector3.back, true,.3f),
                ("Finery north repair foot", new Vector3(20.24f,.685f,-14.175f), 1.82f,.37f,Vector3.back, true,.29f),
                ("Finery north corner foot", new Vector3(24.12f,.65f,-14.175f), 1.03f,.3f,Vector3.back, true,.34f)
            };
            string evidence = Path.Combine(Repo,"unity/evidence/reference-street/20260910/localized-sediment-v1-install");
            Directory.CreateDirectory(evidence);
            string backup = Path.Combine(evidence,"before.unity");
            if (File.Exists(backup)) throw new IOException("Preserve previous attempt.");
            File.Copy(scene.path,backup,false);
            var transforms = CaptureTransforms(scene,chunks.generatedRoot);
            var collision = CollisionSignature(scene); var actors = ActorSignature(scene);
            Directory.CreateDirectory(folder); AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var mineral = new Material(template) {name="Localized coping mineral sediment"};
            mineral.SetTexture("Base_Map",runoff); AssetDatabase.CreateAsset(mineral,folder+"/CopingMineral.mat");
            var foot = new Material(template) {name="Localized sheltered wall foot sediment"};
            AssetDatabase.CreateAsset(foot,folder+"/WallFoot.mat");
            var parent = new GameObject(groupName); Undo.RegisterCreatedObjectUndo(parent,"Add localized reference street sediment");
            foreach (var d in deposits)
            {
                var go = new GameObject(d.Item1); go.transform.SetParent(parent.transform,false); go.transform.position=d.Item2;
                go.transform.rotation=Quaternion.LookRotation(d.Item5,Vector3.up);
                var projector=go.AddComponent<UnityEngine.Rendering.Universal.DecalProjector>();
                projector.material=d.Item6?foot:mineral; projector.size=new Vector3(d.Item3,d.Item4,.12f); projector.pivot=Vector3.zero;
                projector.fadeFactor=d.Item7; projector.drawDistance=65; projector.fadeScale=.82f;
                projector.startAngleFade=45; projector.endAngleFade=70;
                if(d.Item6){projector.uvScale=new Vector2(.49f,.49f);projector.uvBias=new Vector2(.505f,.505f);}
            }
            VerifyTransforms(transforms,new HashSet<string>());
            if (CollisionSignature(scene)!=collision || ActorSignature(scene)!=actors || chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Unexpected geometry, collision, actor or route mutation.");
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Write(Path.Combine(evidence,"installation.json"),new {utc=DateTime.UtcNow,backup,sceneSha256=Sha(scene.path),
                projectors=parent.GetComponentsInChildren<UnityEngine.Rendering.Universal.DecalProjector>().Select(d=>new {d.name,position=V(d.transform.position),size=V(d.size),d.fadeFactor,material=AssetDatabase.GetAssetPath(d.material)}),
                checks=new {sourceGeometryAndTransformsPreserved=true,allCollidersAndActorsAndRoutesPreserved=true,chunksFresh=true},
                scope="Twelve localized coping/joint and wall-foot deposits. Existing source textures, materials and eight older runoff films retained. Native placement and appearance still require review."});
        }
        public static void RepairBannerPlacementV1()
        {
            const string bannerPath = "Courtyard reference pass/Wall graphics/Ward watch banner";
            const string folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/BannerPlacementV1";
            var scene=SceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode || scene.isDirty || scene.path!=ImportBaseline.ScenePath || Directory.Exists(folder)) throw new InvalidOperationException("Require clean saved city and unused banner revision.");
            var t=ExactTransform(scene,bannerPath); var r=t.GetComponent<MeshRenderer>();
            var chunks=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<StaticRenderChunks>(true)).Single();
            if(!r || r.bounds.min.x<17.30f || r.bounds.max.x>17.42f || Mathf.Abs(r.bounds.center.z+20.65f)>.01f || t.GetComponentsInChildren<Collider>().Length!=0 || r.sharedMaterial.shader.name!="Universal Render Pipeline/Lit") throw new InvalidOperationException("Original occluded banner contract changed.");
            if(Mathf.Abs(t.localScale.x-t.localScale.y)>.0001f || Mathf.Abs(t.localScale.x-t.localScale.z)>.0001f || chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Require uniform original banner and fresh render sources.");
            string evidence=Path.Combine(Repo,"unity/evidence/reference-street/20260910/banner-placement-v1-install"); Directory.CreateDirectory(evidence);
            string backup=Path.Combine(evidence,"before.unity"); if(File.Exists(backup))throw new IOException("Preserve previous banner attempt."); File.Copy(scene.path,backup,false);
            var before=new {position=V(t.position),scale=V(t.localScale),boundsMin=V(r.bounds.min),boundsMax=V(r.bounds.max),material=AssetDatabase.GetAssetPath(r.sharedMaterial),materialSha256=Sha(AssetDatabase.GetAssetPath(r.sharedMaterial))};
            string actors=ActorSignature(scene),collision=CollisionSignature(scene);
            var transforms=CaptureTransforms(scene,chunks.generatedRoot).Where(p=>p.transform!=t).ToArray();
            Directory.CreateDirectory(folder); AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var cloth=new Material(r.sharedMaterial){name="Ward banner fitted to lower masonry pier"};AssetDatabase.CreateAsset(cloth,folder+"/WardBanner.mat");
            chunks.ShowSources(true);Undo.RecordObject(t,"Fit banner uniformly on existing clear masonry pier");Undo.RecordObject(r,"Assign contained banner movement");
            t.localScale*=.78f; t.position=new Vector3(16.735f,1.92f,-19.31f);r.sharedMaterial=cloth;
            EditorUtility.SetDirty(t);EditorUtility.SetDirty(r);PrefabUtility.RecordPrefabInstancePropertyModifications(t);PrefabUtility.RecordPrefabInstancePropertyModifications(r);
            var b=r.bounds;
            if(b.max.x>=16.785f || b.min.z<=-19.57f || b.max.z>=-19.05f || b.min.y<1.07f || b.max.y>2.90f)throw new InvalidOperationException("Banner does not fit the clear lower pier at uniform scale.");
            VerifyTransforms(transforms,new HashSet<string>());
            if(ActorSignature(scene)!=actors || CollisionSignature(scene)!=collision)throw new InvalidOperationException("Banner changed gameplay or collision.");
            StaticRenderChunksEditor.Rebuild(chunks);AssetDatabase.SaveAssets();EditorSceneManager.SaveScene(scene);
            VerifyTransforms(transforms,new HashSet<string>());
            if(ActorSignature(scene)!=actors || CollisionSignature(scene)!=collision || chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks))throw new InvalidOperationException("Post-rebuild banner invariant failed.");
            Write(Path.Combine(evidence,"installation.json"),new{utc=DateTime.UtcNow,backup,before,after=new{position=V(t.position),scale=V(t.localScale),boundsMin=V(b.min),boundsMax=V(b.max),sourceShader="Universal Render Pipeline/Lit",staticAuthoredCloth=true},
                reasons="Original banner sat behind the window bay. Uniformly fit within existing clear lower masonry pier. Preserve the current static Lit cloth shader and all material properties.",allOtherSourceTransformsPreserved=true,allActorsRoutesAndCollidersPreserved=true,sourceMeshAndTexturePreserved=true,sceneSha256=Sha(scene.path),nativeAccepted=false});
        }
    }
}
