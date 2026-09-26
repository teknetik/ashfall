#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
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
    // Staged 10 September 2026. Copy into Assets/AthenHill/Editor when ready.
    // Every operation is explicit. This helper never opens/reconstructs the city.
    public static class GroundDetailPass
    {
        const string Date = "20260910";
        const string CandidateName = "Ground detail ";
        static readonly string[] Families = { "trash", "scrap", "crate" };
        static readonly Dictionary<string, Vector3> CanonicalSizes = new Dictionary<string, Vector3> {
            { "trash", new Vector3(1.4f, .38f, 1f) },
            { "scrap", new Vector3(1.8f, 1.25f, 1.1f) },
            { "crate", new Vector3(1.3f, 1.37f, 1.3f) }
        };
        static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source(string family) => Path.Combine(Repository, "meshy/ground-detail-" + Date, family);
        static string Folder(string family, string revision) => "Assets/AthenHill/Art/Imported/Meshy/GroundDetail/" + Date + "/" + family + "/" + revision;
        static string Prefab(string family, string revision) => Folder(family, revision) + "/" + family + ".prefab";
        static string Evidence => Path.Combine(Repository, "unity/evidence/reference-street/" + Date + "/ground-detail");
        sealed class SourceRecord
        {
            public int schema = 1;
            public string family, revision, sourceFolder;
            public Dictionary<string, string> sha256;
        }
        static readonly Dictionary<string, string> SourceFiles = new Dictionary<string, string> {
            { "model.fbx", "Source/model.fbx" },
            { "model_textures/base_color.png", "SourceTextures/base_color.png" },
            { "model_textures/normal.png", "SourceTextures/normal.png" },
            { "model_textures/metallic.png", "SourceTextures/metallic.png" },
            { "model_textures/roughness.png", "SourceTextures/roughness.png" }
        };
        static string SourceRecordPath(string family, string revision) => Folder(family, revision) + "/SourceContract.json";
        static string ResolveSource(string family, string sourceFolderOverride)
            => Path.GetFullPath(string.IsNullOrWhiteSpace(sourceFolderOverride) ? Source(family) : Path.IsPathRooted(sourceFolderOverride) ? sourceFolderOverride : Path.Combine(Repository, sourceFolderOverride));
        static string RecordedSource(SourceRecord record) => Path.GetFullPath(Path.IsPathRooted(record.sourceFolder) ? record.sourceFolder : Path.Combine(Repository, record.sourceFolder));
        static string[] RequestedFamilies(string[] families, string revision)
        {
            RequireEdit(null, revision);
            if (families == null || families.Length == 0 || families.Distinct(StringComparer.Ordinal).Count() != families.Length) throw new ArgumentException("Select at least one distinct ground family.");
            foreach (var family in families) RequireEdit(family, revision);
            if (families.Any(f => f == null)) throw new ArgumentException("A selected family cannot be null.");
            return Families.Where(families.Contains).ToArray();
        }
        static SourceRecord RecordSource(string family, string revision, string sourceFolderOverride, bool verifyImportedCopies)
        {
            string source = ResolveSource(family, sourceFolderOverride);
            var hashes = new Dictionary<string, string>();
            foreach (var pair in SourceFiles)
            {
                string input = Path.Combine(source, pair.Key);
                if (!File.Exists(input)) throw new FileNotFoundException("Revision source is incomplete.", input);
                hashes.Add(pair.Key, Hash(input));
                if (verifyImportedCopies && (!File.Exists(Folder(family, revision) + "/" + pair.Value) || Hash(Folder(family, revision) + "/" + pair.Value) != hashes[pair.Key]))
                    throw new InvalidOperationException("Existing imported data differs from the specified revision source: " + pair.Key);
            }
            var relative = Path.GetRelativePath(Repository, source);
            var record = new SourceRecord { family = family, revision = revision, sourceFolder = relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal) ? source : relative, sha256 = hashes };
            string path = SourceRecordPath(family, revision), serialized = JsonConvert.SerializeObject(record, Formatting.Indented);
            if (File.Exists(path))
            {
                if (File.ReadAllText(path) != serialized) throw new InvalidOperationException("This revision already names another immutable source contract. Prepare a new revision.");
            }
            else { Directory.CreateDirectory(Path.GetDirectoryName(path)); File.WriteAllText(path, serialized); }
            return record;
        }
        static SourceRecord ReadSource(string family, string revision)
        {
            string path = SourceRecordPath(family, revision);
            if (!File.Exists(path)) throw new InvalidOperationException("Missing revision-specific SourceContract.json. Explicitly bind and verify a legacy prepared candidate, or prepare a new revision.");
            var record = JsonConvert.DeserializeObject<SourceRecord>(File.ReadAllText(path));
            if (record == null || record.schema != 1 || record.family != family || record.revision != revision || string.IsNullOrWhiteSpace(record.sourceFolder) || record.sha256 == null || record.sha256.Count != SourceFiles.Count)
                throw new InvalidOperationException("Invalid revision source contract: " + path);
            foreach (var pair in SourceFiles)
            {
                if (!record.sha256.TryGetValue(pair.Key, out string expected) || Hash(Path.Combine(RecordedSource(record), pair.Key)) != expected || Hash(Folder(family, revision) + "/" + pair.Value) != expected)
                    throw new InvalidOperationException("Source or imported copy no longer matches this revision: " + pair.Key);
            }
            return record;
        }
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
        static string Hierarchy(Transform t) => t.parent ? Hierarchy(t.parent) + "/" + t.name : t.name;
        static bool Finite(float f) => !float.IsNaN(f) && !float.IsInfinity(f);
        static string Hash(string file) { using (var sha = SHA256.Create()) using (var stream = File.OpenRead(file)) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
        static void WriteNew(string name, object data)
        {
            Directory.CreateDirectory(Evidence);
            var path = Path.Combine(Evidence, name);
            if (File.Exists(path)) throw new IOException("Preserve previous evidence: " + path);
            File.WriteAllText(path, JsonConvert.SerializeObject(data, Formatting.Indented));
        }
        static void RequireEdit(string family = null, string revision = "v1")
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling) throw new InvalidOperationException("Finish Play and compilation first.");
            if (family != null && !Families.Contains(family)) throw new ArgumentException("Unknown ground family: " + family);
            if (string.IsNullOrWhiteSpace(revision) || revision.Any(c => !char.IsLetterOrDigit(c) && c != '-' && c != '_')) throw new ArgumentException("Revision must be a simple version name.");
        }
        static StaticRenderChunks RequireCity()
        {
            RequireEdit();
            if (SceneManager.GetActiveScene().path != ImportBaseline.ScenePath) throw new InvalidOperationException("Open the existing AthenHill scene. No scene will be loaded automatically.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var salvage = SceneManager.GetActiveScene().GetRootGameObjects().SingleOrDefault(g => g.name == "Post-war salvage");
            if (!chunks || !salvage || !chunks.sourceRoots.Contains(salvage.transform)) throw new InvalidOperationException("The existing registered salvage source root is missing.");
            return chunks;
        }
        static void CopyImmutable(string source, string destination)
        {
            if (!File.Exists(source)) throw new FileNotFoundException("Candidate source is incomplete.", source);
            if (File.Exists(destination))
            {
                if (Hash(source) != Hash(destination)) throw new IOException("Source changed. Prepare a new revision instead of replacing " + destination);
                return;
            }
            Directory.CreateDirectory(Path.GetDirectoryName(destination)); File.Copy(source, destination);
        }
        static Texture2D Texture(string path, bool srgb, bool normal = false, bool readable = false)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!importer) throw new InvalidOperationException("Texture did not import: " + path);
            importer.GetSourceTextureWidthAndHeight(out int width, out int height);
            importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(width, height));
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.flipGreenChannel = false;
            importer.alphaSource = TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = false; importer.mipmapEnabled = true; importer.streamingMipmaps = true;
            importer.anisoLevel = 8; importer.wrapMode = TextureWrapMode.Repeat;
            importer.isReadable = readable;
            importer.textureCompression = readable ? TextureImporterCompression.Uncompressed : TextureImporterCompression.CompressedHQ;
            importer.ClearPlatformTextureSettings("Standalone");
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
        static Material MakeMaterial(string folder, out object report)
        {
            var maps = folder + "/SourceTextures/";
            var albedo = Texture(maps + "base_color.png", true);
            var normal = Texture(maps + "normal.png", false, true);
            var metallic = Texture(maps + "metallic.png", false, false, true);
            var roughness = Texture(maps + "roughness.png", false, false, true);
            if (metallic.width != roughness.width || metallic.height != roughness.height) throw new InvalidOperationException("Metallic/roughness dimensions differ; author an explicit packing conversion first.");
            var metalPixels = metallic.GetPixels32(); var roughPixels = roughness.GetPixels32();
            int metalMin = 255, metalMax = 0, roughMin = 255, roughMax = 0;
            long metalSum = 0, roughSum = 0, saturatedMetal = 0;
            for (int n = 0; n < metalPixels.Length; n++)
            {
                int m = metalPixels[n].r, r = roughPixels[n].r;
                metalMin = Math.Min(metalMin, m); metalMax = Math.Max(metalMax, m); metalSum += m;
                roughMin = Math.Min(roughMin, r); roughMax = Math.Max(roughMax, r); roughSum += r;
                if (m > 230) saturatedMetal++;
                metalPixels[n] = new Color32((byte)m, 0, 0, (byte)(255 - r));
            }
            // URP Lit samples metallic in R and smoothness in A. Original masks stay intact.
            var packed = new Texture2D(metallic.width, metallic.height, TextureFormat.RGBA32, false, true);
            try { packed.SetPixels32(metalPixels); packed.Apply(); File.WriteAllBytes(folder + "/MetallicSmoothness.png", packed.EncodeToPNG()); }
            finally { Object.DestroyImmediate(packed); }
            report = new { metallicMin = metalMin / 255f, metallicMax = metalMax / 255f, metallicMean = metalSum / (255.0 * metalPixels.Length),
                roughnessMin = roughMin / 255f, roughnessMax = roughMax / 255f, roughnessMean = roughSum / (255.0 * roughPixels.Length),
                saturatedMetalFraction = saturatedMetal / (double)metalPixels.Length,
                packedChannels = "R = original metallic R; A = 1 - original roughness R; G/B unused",
                normalConvention = "Source tangent-space +Y; no green inversion. Confirm cavities/highlights in sun and shade before acceptance.",
                semanticMaskAcceptance = "Pending visual inspection of cloth, paper, dust and exposed metal regions; statistics alone cannot establish correctness.", emission = "Off; downloaded emission is retained only in external source records." };
            Texture(maps + "metallic.png", false); Texture(maps + "roughness.png", false);
            var shader = Shader.Find("Universal Render Pipeline/Lit"); if (!shader) throw new InvalidOperationException("Existing URP Lit shader is unavailable.");
            var material = new Material(shader) { name = "GroundDetail_" + Path.GetFileName(Path.GetDirectoryName(folder)) + "_" + Path.GetFileName(folder), enableInstancing = true };
            material.SetTexture("_BaseMap", albedo); material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BumpMap", normal); material.SetFloat("_BumpScale", 1f); material.EnableKeyword("_NORMALMAP");
            material.SetTexture("_MetallicGlossMap", Texture(folder + "/MetallicSmoothness.png", false));
            material.SetFloat("_Metallic", 1f); material.SetFloat("_Smoothness", 1f); material.SetFloat("_SmoothnessTextureChannel", 0f); material.EnableKeyword("_METALLICSPECGLOSSMAP");
            material.SetFloat("_Surface", 0f); material.SetFloat("_AlphaClip", 0f); material.SetFloat("_Cull", 2f);
            material.SetColor("_EmissionColor", Color.black); material.SetTexture("_EmissionMap", null); material.DisableKeyword("_EMISSION");
            material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack;
            AssetDatabase.CreateAsset(material, folder + "/Surface.mat"); return material;
        }
        static Bounds LocalBounds(Transform root, IEnumerable<MeshRenderer> renderers)
        {
            bool first = true; Bounds bounds = default;
            foreach (var renderer in renderers)
            {
                var filter = renderer.GetComponent<MeshFilter>(); if (!filter || !filter.sharedMesh) throw new InvalidOperationException("Missing static mesh: " + Hierarchy(renderer.transform));
                var matrix = root.worldToLocalMatrix * filter.transform.localToWorldMatrix;
                foreach (var vertex in filter.sharedMesh.vertices)
                {
                    var p = matrix.MultiplyPoint3x4(vertex);
                    if (!Finite(p.x) || !Finite(p.y) || !Finite(p.z)) throw new InvalidOperationException("Non-finite source vertex.");
                    if (first) { bounds = new Bounds(p, Vector3.zero); first = false; } else bounds.Encapsulate(p);
                }
            }
            if (first || bounds.size.x <= 0 || bounds.size.y <= 0 || bounds.size.z <= 0) throw new InvalidOperationException("Candidate has no valid three-dimensional bounds.");
            return bounds;
        }
        static object MeshReport(MeshFilter filter)
        {
            var mesh = filter.sharedMesh; if (!mesh) throw new InvalidOperationException("Missing imported mesh.");
            if (mesh.uv.Length != mesh.vertexCount || mesh.uv.Any(v => !Finite(v.x) || !Finite(v.y))) throw new InvalidOperationException("Invalid UV0: " + mesh.name);
            if (mesh.normals.Length != mesh.vertexCount || mesh.tangents.Length != mesh.vertexCount) throw new InvalidOperationException("Normals/tangents are incomplete: " + mesh.name);
            var renderer = filter.GetComponent<MeshRenderer>();
            if (!renderer || renderer.sharedMaterials.Length != mesh.subMeshCount) throw new InvalidOperationException("Material/submesh slots differ: " + mesh.name);
            long triangles = 0;
            for (int n = 0; n < mesh.subMeshCount; n++)
            {
                if (mesh.GetTopology(n) != MeshTopology.Triangles || mesh.GetIndexCount(n) % 3 != 0) throw new InvalidOperationException("Expected triangle mesh: " + mesh.name);
                triangles += (long)mesh.GetIndexCount(n) / 3;
            }
            return new { path = Hierarchy(filter.transform), source = AssetDatabase.GetAssetPath(mesh), mesh.name, vertices = mesh.vertexCount, triangles, submeshes = mesh.subMeshCount,
                uv0Count = mesh.uv.Length, uv0Min = new[] { mesh.uv.Min(v => v.x), mesh.uv.Min(v => v.y) }, uv0Max = new[] { mesh.uv.Max(v => v.x), mesh.uv.Max(v => v.y) },
                tangents = mesh.tangents.Length, localScale = V(filter.transform.localScale), lossyScale = V(filter.transform.lossyScale) };
        }
        public static void PrepareAll(string revision = "v1") { foreach (var family in Families) Prepare(family, revision); }
        public static void Prepare(string family, string revision = "v1", string sourceFolderOverride = null)
        {
            RequireEdit(family, revision);
            string folder = Folder(family, revision);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(family, revision)) || File.Exists(folder + "/Surface.mat")) throw new InvalidOperationException("Candidate already prepared. Preserve it and use a new revision.");
            var sourceRecord = RecordSource(family, revision, sourceFolderOverride, false);
            string source = RecordedSource(sourceRecord);
            foreach (var pair in SourceFiles) CopyImmutable(Path.Combine(source, pair.Key), folder + "/" + pair.Value);
            ReadSource(family, revision);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var modelPath = folder + "/Source/model.fbx";
            var importer = AssetImporter.GetAtPath(modelPath) as ModelImporter; if (!importer) throw new InvalidOperationException("FBX import failed.");
            importer.animationType = ModelImporterAnimationType.None; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.None; importer.importNormals = ModelImporterNormals.Import; importer.importTangents = ModelImporterTangents.CalculateMikk;
            importer.isReadable = true; importer.meshCompression = ModelImporterMeshCompression.Off;
            importer.SaveAndReimport();
            var material = MakeMaterial(folder, out var materialReport);
            var previewScene = EditorSceneManager.NewPreviewScene();
            try
            {
                var root = new GameObject("Ground detail " + family); SceneManager.MoveGameObjectToScene(root, previewScene);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
                var visual = (GameObject)PrefabUtility.InstantiatePrefab(model, previewScene); visual.name = "Intact Meshy near source"; visual.transform.SetParent(root.transform, false);
                if (visual.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length != 0 || visual.GetComponentsInChildren<Collider>(true).Length != 0) throw new InvalidOperationException("Static render-only candidates must not carry skins or colliders.");
                var renderers = visual.GetComponentsInChildren<MeshRenderer>(true);
                foreach (var renderer in renderers)
                {
                    var mesh = renderer.GetComponent<MeshFilter>().sharedMesh;
                    renderer.sharedMaterials = Enumerable.Repeat(material, mesh.subMeshCount).ToArray(); renderer.renderingLayerMask = 3;
                    renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true; renderer.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
                }
                var raw = LocalBounds(root.transform, renderers); var target = CanonicalSizes[family];
                float scale = Mathf.Min(target.x / raw.size.x, target.y / raw.size.y, target.z / raw.size.z);
                visual.transform.localScale *= scale;
                var fitted = LocalBounds(root.transform, renderers);
                visual.transform.localPosition -= new Vector3(fitted.center.x, fitted.min.y, fitted.center.z);
                fitted = LocalBounds(root.transform, renderers);
                var meshes = visual.GetComponentsInChildren<MeshFilter>(true).Select(MeshReport).ToArray();
                PrefabUtility.SaveAsPrefabAsset(root, Prefab(family, revision)); AssetDatabase.SaveAssets();
                WriteNew("prepared-" + family + "-" + revision + ".json", new { utc = DateTime.UtcNow, family, revision, prefab = Prefab(family, revision), modelSource = source + "/model.fbx", sourceSha256 = Hash(modelPath), sourceRecord,
                    rawSize = V(raw.size), canonicalEnvelope = V(target), size = V(fitted.size), uniformFitFactor = scale, meshes, material = materialReport,
                    maps = new[] { "base_color", "normal", "metallic", "roughness" }.Select(m => new { name = m, sourceSha256 = Hash(source + "/model_textures/" + m + ".png"), unitySha256 = Hash(folder + "/SourceTextures/" + m + ".png") }),
                    geometryPolicy = "All imported source triangles retained. No subdivision, simplification, district atlas or generated LOD. Original external FBX/GLB/pre-remesh preserved.",
                    status = "Prepared source-preserving candidate; geometry, normal direction and semantic masks still require native visual inspection." });
            }
            finally { EditorSceneManager.ClosePreviewScene(previewScene); }
        }
        public static void BindExistingSourceContract(string family, string revision, string sourceFolderOverride = null)
        {
            RequireEdit(family, revision);
            if (!AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(family, revision))) throw new InvalidOperationException("Only an already prepared candidate can be explicitly bound.");
            RecordSource(family, revision, sourceFolderOverride, true);
            AssetDatabase.ImportAsset(SourceRecordPath(family, revision), ImportAssetOptions.ForceSynchronousImport);
            ReadSource(family, revision);
        }
        static bool LogicalVisible(MeshRenderer renderer, StaticRenderChunks chunks)
        {
            int index = chunks.sources == null ? -1 : Array.IndexOf(chunks.sources, renderer);
            return renderer.gameObject.activeInHierarchy && (chunks.editingSources || index < 0 ? renderer.enabled : chunks.sourceVisibility[index]);
        }
        static MeshRenderer[] PreviousVisuals(Transform root)
        {
            return root.GetComponentsInChildren<MeshRenderer>(true).Where(r => {
                var filter = r.GetComponent<MeshFilter>(); if (!filter || !filter.sharedMesh) return false;
                var path = AssetDatabase.GetAssetPath(filter.sharedMesh);
                return path.StartsWith(ImportSalvageAssets.Folder + "/", StringComparison.Ordinal) || path.StartsWith(ImportDistrictAssets.Folder + "/Atlas/salvage_", StringComparison.Ordinal);
            }).ToArray();
        }
        static Transform[] ExistingRoots(string family, StaticRenderChunks chunks, bool includeReplaced = false)
        {
            var salvage = SceneManager.GetActiveScene().GetRootGameObjects().Single(g => g.name == "Post-war salvage");
            return salvage.transform.Cast<Transform>().Where(t => t.gameObject.activeInHierarchy && t.name.StartsWith(family + " ", StringComparison.Ordinal)
                && PreviousVisuals(t).Any(r => includeReplaced || LogicalVisible(r, chunks))).OrderBy(t => Hierarchy(t), StringComparer.Ordinal).ToArray();
        }
        static float StreetDistance(Transform root)
        {
            var p = root.position; p.y = 0;
            return Mathf.Min((p - new Vector3(16f, 0, -9f)).sqrMagnitude, (p - new Vector3(16f, 0, -18f)).sqrMagnitude);
        }
        static Bounds FitEnvelope(Transform root, MeshRenderer[] old)
        {
            var visual = LocalBounds(root, old);
            var boxes = root.GetComponents<BoxCollider>().Where(c => c.enabled && !c.isTrigger).ToArray();
            if (boxes.Length > 1) throw new InvalidOperationException("Inspect multiple collision envelopes: " + Hierarchy(root));
            if (boxes.Length == 0) return visual;
            var box = new Bounds(boxes[0].center, boxes[0].size);
            // Keep the candidate inside both the existing visual parcel and blocker.
            var min = Vector3.Max(visual.min, box.min); var max = Vector3.Min(visual.max, box.max);
            if (max.x <= min.x || max.y <= min.y || max.z <= min.z) throw new InvalidOperationException("Visual/collider bounds do not overlap: " + Hierarchy(root));
            return new Bounds((min + max) * .5f, max - min);
        }
        static object Plan(Transform root, string family, string revision)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(family, revision)); if (!prefab) throw new InvalidOperationException("Prepare " + family + " " + revision + " first.");
            var old = PreviousVisuals(root); var envelope = FitEnvelope(root, old);
            var source = LocalBounds(prefab.transform, prefab.GetComponentsInChildren<MeshRenderer>(true));
            float scale = Mathf.Min(envelope.size.x / source.size.x, envelope.size.y / source.size.y, envelope.size.z / source.size.z);
            return new { family, root = Hierarchy(root), rootId = GlobalObjectId.GetGlobalObjectIdSlow(root).ToString(), position = V(root.position), rotation = V(root.eulerAngles), rootScale = V(root.localScale),
                previousRenderers = old.Select(r => new { path = Hierarchy(r.transform), id = GlobalObjectId.GetGlobalObjectIdSlow(r).ToString(), localScale = V(r.transform.localScale) }),
                envelopeCenter = V(envelope.center), envelopeSize = V(envelope.size), candidateSize = V(source.size * scale), uniformScale = scale,
                candidateLocalPosition = V(new Vector3(envelope.center.x, envelope.min.y, envelope.center.z) - new Vector3(source.center.x, source.min.y, source.center.z) * scale),
                colliders = root.GetComponentsInChildren<Collider>(true).Select(c => new { path = Hierarchy(c.transform), id = GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(), type = c.GetType().Name }),
                geometryReview = "Numbers describe preserved source geometry; they do not establish visual quality." };
        }
        static object CandidateContract(string family, string revision)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(family, revision)); if (!prefab) throw new InvalidOperationException("Prepare " + family + " first.");
            string folder = Folder(family, revision), modelPath = folder + "/Source/model.fbx";
            var sourceRecord = ReadSource(family, revision);
            if (prefab.GetComponentsInChildren<Collider>(true).Length != 0 || prefab.GetComponentsInChildren<LODGroup>(true).Length != 0) throw new InvalidOperationException("This candidate contract is an intact render-only near mesh.");
            var filters = prefab.GetComponentsInChildren<MeshFilter>(true);
            var meshes = filters.Select(MeshReport).ToArray();
            if (filters.Any(f => AssetDatabase.GetAssetPath(f.sharedMesh) != modelPath)) throw new InvalidOperationException("Candidate references geometry outside its intact source FBX.");
            long triangles = filters.Sum(f => (long)f.sharedMesh.triangles.Length / 3);
            var material = AssetDatabase.LoadAssetAtPath<Material>(folder + "/Surface.mat");
            if (!material || material.shader.name != "Universal Render Pipeline/Lit" || material.IsKeywordEnabled("_EMISSION") || material.GetColor("_EmissionColor") != Color.black) throw new InvalidOperationException("Candidate must use non-emissive URP Lit PBR.");
            if (prefab.GetComponentsInChildren<MeshRenderer>(true).Any(r => r.sharedMaterials.Any(m => m != material))) throw new InvalidOperationException("Unexpected candidate material slot.");
            var textures = new List<object>();
            foreach (var binding in new[] { (property: "_BaseMap", file: "SourceTextures/base_color.png", srgb: true, normal: false),
                (property: "_BumpMap", file: "SourceTextures/normal.png", srgb: false, normal: true),
                (property: "_MetallicGlossMap", file: "MetallicSmoothness.png", srgb: false, normal: false) })
            {
                string path = folder + "/" + binding.file;
                var texture = material.GetTexture(binding.property) as Texture2D;
                var importer = AssetImporter.GetAtPath(path) as TextureImporter;
                if (!texture || !importer || AssetDatabase.GetAssetPath(texture) != path) throw new InvalidOperationException("Missing PBR texture binding: " + binding.property);
                importer.GetSourceTextureWidthAndHeight(out int width, out int height);
                if (texture.width != width || texture.height != height || importer.sRGBTexture != binding.srgb || importer.textureType != (binding.normal ? TextureImporterType.NormalMap : TextureImporterType.Default) || !importer.mipmapEnabled || importer.anisoLevel < 8)
                    throw new InvalidOperationException("Texture resolution/color-space/sampling contract failed: " + path);
                textures.Add(new { path, sourceWidth = width, sourceHeight = height, importedWidth = texture.width, importedHeight = texture.height,
                    importer.sRGBTexture, textureType = importer.textureType.ToString(), importer.streamingMipmaps, importer.anisoLevel, importer.flipGreenChannel });
            }
            return new { family, revision, sourceRecord, sourceContractSha256 = Hash(SourceRecordPath(family, revision)), triangles, meshes, textures, sourceSha256 = Hash(modelPath), prefabSha256 = Hash(Prefab(family, revision)),
                materialSha256 = Hash(folder + "/Surface.mat"), preservesAllImportedTriangles = true, originalUV0 = true,
                semanticMaskReview = "Required in native views; channel/type checks alone do not classify the surfaces." };
        }
        public static void DryRun(string revision = "v1", string reportName = "dry-run-v1.json") => DryRunSelected(Families, revision, reportName);
        public static void DryRunSelected(string[] families, string revision = "v1", string reportName = null)
        {
            var requested = RequestedFamilies(families, revision); var chunks = RequireCity();
            var candidates = requested.Select(f => CandidateContract(f, revision)).ToArray();
            var all = requested.SelectMany(f => ExistingRoots(f, chunks).Select(t => Plan(t, f, revision))).ToArray();
            var audition = requested.Select(f => { var roots = ExistingRoots(f, chunks); if (roots.Length == 0) throw new InvalidOperationException("No original active " + f + " instances."); return Plan(roots.OrderBy(StreetDistance).First(), f, revision); }).ToArray();
            WriteNew(reportName ?? "dry-run-" + revision + "-" + string.Join("-", requested) + ".json", new { utc = DateTime.UtcNow, requestedFamilies = requested, scene = SceneManager.GetActiveScene().path, savedSceneSha256 = Hash(ImportBaseline.ScenePath), chunksFresh = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks),
                candidates, audition, all, modifiesScene = false, preservesOriginalRootTransformsAndColliders = true, note = "Old renderer visibility, all collider data and all four ambient routes are guarded again during installation. Review fit and shadows in native views before rollout." });
        }
        static string PhysicsSignature()
        {
            return JsonConvert.SerializeObject(SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Collider>(true)).OrderBy(c => GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(), StringComparer.Ordinal)
                .Select(c => new { id = GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(), path = Hierarchy(c.transform), data = EditorJsonUtility.ToJson(c), active = c.gameObject.activeInHierarchy,
                    position = V(c.transform.position), rotation = new[] { c.transform.rotation.x, c.transform.rotation.y, c.transform.rotation.z, c.transform.rotation.w }, scale = V(c.transform.lossyScale) }));
        }
        static string ActorSignature()
        {
            return JsonConvert.SerializeObject(new { existingGameplay = DistrictCityPass.GameplaySignature(),
                allAmbientWalkers = SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<AmbientWalker>(true)).OrderBy(w => Hierarchy(w.transform), StringComparer.Ordinal).Select(w => new {
                    id = GlobalObjectId.GetGlobalObjectIdSlow(w).ToString(), path = Hierarchy(w.transform), data = EditorJsonUtility.ToJson(w), position = V(w.transform.position), rotation = V(w.transform.eulerAngles),
                    route = w.waypoints.Select(t => new { id = GlobalObjectId.GetGlobalObjectIdSlow(t).ToString(), position = V(t.position), rotation = V(t.eulerAngles) }) }) });
        }
        static void InstallOne(Transform root, string family, string revision)
        {
            if (root.Cast<Transform>().Any(t => t.name.StartsWith(CandidateName, StringComparison.Ordinal))) throw new InvalidOperationException("A ground candidate already exists at " + Hierarchy(root));
            var rootScale = root.lossyScale;
            if (Mathf.Abs(rootScale.x - rootScale.y) > .0001f || Mathf.Abs(rootScale.x - rootScale.z) > .0001f || rootScale.x <= 0) throw new InvalidOperationException("Root itself is nonuniform; inspect without changing collision: " + Hierarchy(root));
            var old = PreviousVisuals(root); var envelope = FitEnvelope(root, old);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(family, revision)); if (!prefab) throw new InvalidOperationException("Missing prepared candidate.");
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, root);
            Undo.RegisterCreatedObjectUndo(go, "Audition detailed " + family); go.name = CandidateName + revision;
            var source = LocalBounds(go.transform, go.GetComponentsInChildren<MeshRenderer>(true));
            float scale = Mathf.Min(envelope.size.x / source.size.x, envelope.size.y / source.size.y, envelope.size.z / source.size.z);
            go.transform.localRotation = Quaternion.identity; go.transform.localScale = Vector3.one * scale;
            go.transform.localPosition = new Vector3(envelope.center.x, envelope.min.y, envelope.center.z) - new Vector3(source.center.x, source.min.y, source.center.z) * scale;
            var actual = LocalBounds(root, go.GetComponentsInChildren<MeshRenderer>(true));
            if (Vector3.Distance(actual.size, source.size * scale) > .001f || actual.min.x < envelope.min.x - .001f || actual.max.x > envelope.max.x + .001f || actual.min.z < envelope.min.z - .001f || actual.max.z > envelope.max.z + .001f || actual.max.y > envelope.max.y + .001f) throw new InvalidOperationException("Uniform fit escaped the retained parcel.");
            if (go.GetComponentsInChildren<Collider>(true).Length != 0) throw new InvalidOperationException("Visual candidate unexpectedly contains colliders.");
            foreach (var renderer in old) { Undo.RecordObject(renderer, "Retain previous ground source"); renderer.enabled = false; PrefabUtility.RecordPrefabInstancePropertyModifications(renderer); }
            foreach (var renderer in go.GetComponentsInChildren<MeshRenderer>(true)) renderer.enabled = true;
        }
        static bool HasAudition(string family, string revision)
        {
            if (!Directory.Exists(Evidence)) return false;
            foreach (var path in Directory.GetFiles(Evidence, "audition-*.json"))
            {
                var data = JObject.Parse(File.ReadAllText(path));
                if ((string)data["revision"] == revision && data["instances"] is JArray instances && instances.Any(i => (string)i["family"] == family)) return true;
            }
            return false;
        }
        static void Install(string[] families, string revision, bool rollout, string reviewPath)
        {
            var requested = RequestedFamilies(families, revision); var chunks = RequireCity();
            if (rollout && (string.IsNullOrWhiteSpace(reviewPath) || !File.Exists(reviewPath))) throw new InvalidOperationException("Pass the actual independent native review file for the previously auditioned candidate.");
            if (rollout && requested.Any(f => !HasAudition(f, revision))) throw new InvalidOperationException("Audition each selected family at this revision in the saved street before rollout.");
            if (!rollout && requested.Any(f => HasAudition(f, revision))) throw new InvalidOperationException("A selected family already has an audition at this revision. Inspect its saved instance; use a new revision for another candidate.");
            var candidateContracts = requested.Select(f => CandidateContract(f, revision)).ToArray();
            // The caller must inspect the review's decision; file existence alone is never acceptance.
            var selected = requested.SelectMany(f => {
                var roots = ExistingRoots(f, chunks);
                if (rollout) return roots.Select(t => (family: f, root: t));
                if (roots.Length == 0) throw new InvalidOperationException("No original " + f + " instance remains for audition.");
                return roots.OrderBy(StreetDistance).Take(1).Select(t => (family: f, root: t));
            }).ToArray();
            if (selected.Length == 0) throw new InvalidOperationException("No remaining original visuals require replacement.");
            string operation = (rollout ? "rollout-" : "audition-") + revision + (requested.Length == Families.Length ? "" : "-" + string.Join("-", requested));
            Directory.CreateDirectory(Evidence); string backup = Path.Combine(Evidence, "before-" + operation + ".unity");
            if (File.Exists(backup)) throw new IOException("Preserve the previous attempt; inspect it before another revision.");
            var plans = selected.Select(v => Plan(v.root, v.family, revision)).ToArray();
            string physics = PhysicsSignature(), actors = ActorSignature();
            if (!EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), backup, true)) throw new IOException("Could not preserve the pre-operation scene.");
            Undo.IncrementCurrentGroup(); int undoGroup = Undo.GetCurrentGroup(); Undo.SetCurrentGroupName("Ground detail " + operation);
            bool wasEditing = chunks.editingSources;
            try
            {
                chunks.ShowSources(true);
                foreach (var target in selected) InstallOne(target.root, target.family, revision);
                if (PhysicsSignature() != physics || ActorSignature() != actors) throw new InvalidOperationException("Gameplay or collision changed; the operation must not be saved.");
            }
            catch
            {
                // Chunk assets have not been touched yet, so source edits can be undone safely.
                Undo.RevertAllDownToGroup(undoGroup); chunks.ShowSources(wasEditing); throw;
            }
            Undo.CollapseUndoOperations(undoGroup);
            // Rebuild owns disposable output assets and saves the scene. Do not pretend that
            // Undo can recover deleted chunk assets if this later operation fails: preserve
            // the source edits and recovery scene for a deliberate rebuild/recovery instead.
            StaticRenderChunksEditor.Rebuild(chunks); AssetDatabase.SaveAssets(); EditorSceneManager.SaveScene(SceneManager.GetActiveScene());
            if (PhysicsSignature() != physics || ActorSignature() != actors) throw new InvalidOperationException("Post-rebuild invariant mismatch. Restore the preserved scene before further work.");
            WriteNew(operation + ".json", new { utc = DateTime.UtcNow, revision, requestedFamilies = requested, candidateContracts, stage = rollout ? "Reviewed family rollout" : "One existing near-street instance per family", instances = plans,
                sceneSha256 = Hash(ImportBaseline.ScenePath), sourceFingerprint = chunks.sourceFingerprint,
                chunksFresh = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks), collisionPreserved = true, gameplayAndAllAmbientRoutesPreserved = true,
                review = reviewPath == null ? null : new { path = Path.GetFullPath(reviewPath), sha256 = Hash(reviewPath) },
                pending = "Native sun/shade, close-range/first-person, moving collision access and representative timing verification for this saved scene." });
        }
        public static void AuditionAll(string revision = "v1") => Install(Families, revision, false, null);
        public static void AuditionSelected(string[] families, string revision = "v1") => Install(families, revision, false, null);
        public static void RolloutReviewed(string revision, string independentNativeReviewPath) => Install(Families, revision, true, independentNativeReviewPath);
        public static void RolloutSelected(string[] families, string revision, string independentNativeReviewPath) => Install(families, revision, true, independentNativeReviewPath);
    }
}
#endif
