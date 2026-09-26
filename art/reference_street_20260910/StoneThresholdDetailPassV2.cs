#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Staged only. Root copies this into Assets after reviewing the authored v2.
    public static class StoneThresholdDetailPassV2
    {
        const string Folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/ThresholdsV2";
        const string OldParent = "Reference street thresholds and detail/Stone threshold revision 20260910";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/reference_street_20260910");
        static string Evidence => Path.Combine(Repo, "unity/evidence/reference-street/20260910/threshold-install-v2");
        static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t, null);
        static string Sha(string path) { using (var h = SHA256.Create()) using (var f = File.OpenRead(path)) return BitConverter.ToString(h.ComputeHash(f)).Replace("-", "").ToLowerInvariant(); }
        static void Write(string name, object data) => File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented));
        static string Physics() => JsonConvert.SerializeObject(Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Where(c => c.gameObject.scene.IsValid()).OrderBy(c => PathOf(c.transform)).Select(c => new { path = PathOf(c.transform), active = c.gameObject.activeInHierarchy, transform = Enumerable.Range(0, 16).Select(i => c.transform.localToWorldMatrix[i]).ToArray(), component = EditorJsonUtility.ToJson(c) }));
        static string Actors()
        {
            var components = Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include).Where(c => c.gameObject.scene.IsValid() && new[] { "PlayerMotor", "ActorAnimation", "AmbientWalker", "GameSession", "NpcDefinition" }.Contains(c.GetType().Name)).OrderBy(c => PathOf(c.transform) + c.GetType().Name).Select(c => new { path = PathOf(c.transform), type = c.GetType().Name, data = EditorJsonUtility.ToJson(c), position = Enumerable.Range(0, 16).Select(i => c.transform.localToWorldMatrix[i]).ToArray() });
            var routes = Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include).Where(w => w.gameObject.scene.IsValid())
                .OrderBy(w => PathOf(w.transform)).Select(w => new { path = PathOf(w.transform), data = EditorJsonUtility.ToJson(w),
                    points = w.waypoints.Select(t => new { path = t ? PathOf(t) : null,
                        matrix = t ? Enumerable.Range(0, 16).Select(i => t.localToWorldMatrix[i]).ToArray() : null }).ToArray() }).ToArray();
            if (routes.Length != 4) throw new InvalidDataException("Expected all four current ambient routes.");
            return JsonConvert.SerializeObject(new { components, routes });
        }

        static int VerifyGeometry(string beforePath, string afterPath)
        {
            // Stream one part at a time instead of retaining two large JSON trees
            // while the Editor imports textures and meshes on the 32 GB host.
            var serializer = new JsonSerializer();
            using (var a = new JsonTextReader(File.OpenText(beforePath)))
            using (var b = new JsonTextReader(File.OpenText(afterPath)))
            {
                if (!a.Read() || a.TokenType != JsonToken.StartArray || !b.Read() || b.TokenType != JsonToken.StartArray) throw new InvalidDataException("Expected explicit mesh arrays.");
                int count = 0, changedNormals = 0; long triangles = 0;
                while (a.Read() && a.TokenType != JsonToken.EndArray)
                {
                    if (!b.Read() || b.TokenType != JsonToken.StartObject) throw new InvalidDataException("V2 part roster differs.");
                    var old = serializer.Deserialize<HeroStreetDetailPass.Part>(a);
                    var next = serializer.Deserialize<HeroStreetDetailPass.Part>(b);
                    if (old.name != next.name || old.sourcePath != next.sourcePath || old.material != next.material || old.castsShadow != next.castsShadow ||
                        !old.indices.SequenceEqual(next.indices) || old.positions.Length != next.positions.Length || old.normals.Length != next.normals.Length)
                        throw new InvalidDataException("Geometry or part identity changed: " + old.name);
                    for (int i = 0; i < old.positions.Length; i++)
                    {
                        if (!old.positions[i].SequenceEqual(next.positions[i])) throw new InvalidDataException("A threshold vertex moved: " + old.name + " " + i);
                        if (!old.normals[i].SequenceEqual(next.normals[i])) changedNormals++;
                    }
                    triangles += old.indices.Length / 3; count++;
                }
                if (!b.Read() || b.TokenType != JsonToken.EndArray || count != 36 || triangles != 235138) throw new InvalidDataException("Threshold geometry count changed.");
                return changedNormals;
            }
        }

        static Texture2D PackSourceRoughness(string sourcePath, out object audit)
        {
            string path = Folder + "/MetalSmooth.png";
            var source = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
            Texture2D packed = null, decoded = null;
            try
            {
                if (!source.LoadImage(File.ReadAllBytes(sourcePath), false)) throw new InvalidDataException("Cannot decode source roughness.");
                int width = source.width, height = source.height;
                var sourcePixels = source.GetPixels32(); var pixels = new Color32[sourcePixels.Length];
                int minimum = 255, maximum = 0; long sum = 0;
                for (int i = 0; i < pixels.Length; i++)
                {
                    byte rough = sourcePixels[i].r;
                    minimum = Math.Min(minimum, rough); maximum = Math.Max(maximum, rough); sum += rough;
                    pixels[i] = new Color32(0, 0, 0, (byte)(255 - rough));
                }
                // LoadImage(JPG) can change the source to RGB24. Never write the
                // required smoothness alpha back into that decoded RGB texture.
                packed = new Texture2D(width, height, TextureFormat.RGBA32, false, true);
                packed.SetPixels32(pixels); packed.Apply(false, false);
                byte[] bytes = packed.EncodeToPNG();
                if (bytes.Length < 26 || bytes[25] != 6) throw new InvalidDataException("Packed PNG must contain RGBA channels.");
                decoded = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                if (!decoded.LoadImage(bytes, false) || decoded.width != width || decoded.height != height) throw new InvalidDataException("Packing changed source dimensions.");
                var check = decoded.GetPixels32();
                if (check.Length != pixels.Length) throw new InvalidDataException("Packed pixel count changed.");
                for (int i = 0; i < check.Length; i++)
                    if (check[i].r != 0 || check[i].g != 0 || check[i].b != 0 || check[i].a != 255 - sourcePixels[i].r)
                        throw new InvalidDataException("Packed source channel mismatch at pixel " + i);
                File.WriteAllBytes(path, bytes);
                audit = new { source = sourcePath, sourceSha256 = Sha(sourcePath), sourceFormat = source.format.ToString(),
                    width, height, sourcePixels = sourcePixels.Length, roughnessMin = minimum / 255f, roughnessMax = maximum / 255f,
                    roughnessMean = sum / (255.0 * sourcePixels.Length), smoothnessMin = (255 - maximum) / 255f,
                    smoothnessMax = (255 - minimum) / 255f, packedPath = path, packedSha256 = Sha(path),
                    packedPngColorType = bytes[25], everyPixelVerified = true,
                    conversion = "New RGBA32 output; R/G/B=0, A=255-original roughness R; no resize or roughness remap." };
            }
            finally
            {
                Object.DestroyImmediate(source);
                if (packed) Object.DestroyImmediate(packed);
                if (decoded) Object.DestroyImmediate(decoded);
            }
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.GetSourceTextureWidthAndHeight(out int w, out int h);
            importer.ClearPlatformTextureSettings("Standalone");
            importer.textureType = TextureImporterType.Default; importer.sRGBTexture = false;
            importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = false;
            importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(w, h)); importer.npotScale = TextureImporterNPOTScale.None;
            importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
            importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.isReadable = false;
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        public static void Apply()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || scene.path != ImportBaseline.ScenePath || scene.isDirty || EditorSceneManager.sceneCount != 1)
                throw new InvalidOperationException("Open the single saved AthenHill scene in Edit mode, after compilation.");
            if (Directory.Exists(Folder) || Directory.Exists(Evidence)) throw new InvalidOperationException("Preserve prior v2 assets/evidence; inspect before retrying.");
            var manifest = JObject.Parse(File.ReadAllText(Path.Combine(Source, "stone-threshold-manifest-v2.json")));
            var contract = JObject.Parse(File.ReadAllText(Path.Combine(Source, "threshold-v2-install-contract.json")));
            string beforeFile = Path.Combine(Source, "stone-threshold-meshes-v1.json"), afterFile = Path.Combine(Source, "stone-threshold-meshes-v2.json");
            if ((string)manifest["revision"] != "stone-threshold-v2" || Sha(beforeFile) != (string)manifest["sourceSha256"] ||
                Sha(beforeFile) != (string)contract["sourceSha256"] || Sha(afterFile) != (string)manifest["meshFileSha256"])
                throw new InvalidDataException("Authored threshold source hash changed.");
            foreach (var file in ((JObject)contract["guardedFiles"]).Properties())
                if (Sha(Path.Combine(Repo, file.Name)) != (string)file.Value) throw new InvalidDataException("V1 installation/source changed: " + file.Name);
            int correctedNormals = VerifyGeometry(beforeFile, afterFile);
            if (correctedNormals != ((JArray)manifest["meshAudits"]).Sum(p => (int)p["correctedCornerNormals"])) throw new InvalidDataException("Corner-normal repair count differs.");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var root = GameObject.Find("Reference street thresholds and detail"); var oldParent = GameObject.Find(OldParent);
            if (!chunks || !root || !oldParent || !chunks.sourceRoots.Contains(root.transform) || chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Current registered source root and fresh v1 render chunks are required.");
            if (oldParent.GetComponentsInChildren<Collider>(true).Length != 0 || oldParent.GetComponentsInChildren<MeshRenderer>(true).Length != 32)
                throw new InvalidDataException("V1 addition roster or collider status changed.");
            var changes = (JArray)contract["installedMeshes"];
            foreach (var change in changes)
            {
                var target = GameObject.Find((string)change["path"]);
                if (!target || !target.GetComponent<MeshFilter>() || AssetDatabase.GetAssetPath(target.GetComponent<MeshFilter>().sharedMesh) != (string)change["newMesh"])
                    throw new InvalidDataException("Expected v1 source mesh changed: " + change["path"]);
            }
            var expected = changes.Where(p => (bool)p["replacement"]).ToDictionary(p => (string)p["path"], p => (string)p["newMesh"]);
            if (expected.Count != 4) throw new InvalidDataException("Four unchanged threshold roots are required.");
            string physics = Physics(), actors = Actors();
            Directory.CreateDirectory(Evidence); Directory.CreateDirectory(Folder);
            EditorSceneManager.SaveScene(scene, Path.Combine(Evidence, "before-scene.unity"), true);
            File.WriteAllText(Path.Combine(Evidence, "colliders-before.json"), physics);
            File.WriteAllText(Path.Combine(Evidence, "actors-before.json"), actors);
            try
            {
                string roughness = Path.Combine(Repo, (string)contract["roughnessSource"]);
                var packed = PackSourceRoughness(roughness, out var packingAudit);
                var materials = new Dictionary<string, Material>();
                foreach (var key in new[] { "ThresholdStone", "ThresholdMortar", "ThresholdGrit" })
                {
                    var original = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/ReferenceStreet/20260910/Thresholds/" + key + ".mat");
                    if (!original || original.shader.name != "Universal Render Pipeline/Lit") throw new InvalidDataException("Expected retained URP threshold material.");
                    var material = new Material(original) { name = key + " source roughness v2" };
                    material.SetTexture("_MetallicGlossMap", packed); material.SetFloat("_Smoothness", 1);
                    material.SetFloat("_Metallic", 0); material.SetFloat("_SmoothnessTextureChannel", 0);
                    material.EnableKeyword("_METALLICSPECGLOSSMAP"); material.DisableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A");
                    AssetDatabase.CreateAsset(material, Folder + "/" + key + ".mat"); materials.Add(key, material);
                }
                chunks.ShowSources(true);
                var parent = new GameObject("Stone threshold revision 20260910 v2"); parent.transform.SetParent(root.transform, false);
                var result = HeroStreetDetailPass.ImportParts(afterFile, Folder + "/Meshes", parent.transform, materials, expected);
                oldParent.SetActive(false); EditorUtility.SetDirty(oldParent); PrefabUtility.RecordPrefabInstancePropertyModifications(oldParent);
                if (Physics() != physics || Actors() != actors) throw new InvalidOperationException("Collision or actor state changed; do not save.");
                AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks);
                if (Physics() != physics || Actors() != actors || chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Post-rebuild preservation failed.");
                EditorSceneManager.SaveScene(scene);
                File.WriteAllText(Path.Combine(Evidence, "colliders-after.json"), Physics());
                File.WriteAllText(Path.Combine(Evidence, "actors-after.json"), Actors());
                Write("installation.json", new { utc = DateTime.UtcNow, result, correctedNormals, packingAudit,
                    previousParentDisabled = OldParent, previousAssetsRetained = true, positionsAndIndicesExactlyPreserved = true,
                    collidersPreserved = true, actorsPreserved = true, chunksFresh = true, savedSceneSha256 = Sha(scene.path),
                    authoredMeshSha256 = Sha(afterFile), nativeAccepted = false,
                    next = "Rebuild native Linux and inspect risers, crack variation, bevel/chip glare and dark cut recesses in sun/shade and motion; exercise both thresholds." });
            }
            catch (Exception exception)
            {
                Write("failure.json", new { utc = DateTime.UtcNow, exception = exception.ToString(), action = "Inspect retained before-scene and partial outputs; do not retry over them automatically." });
                throw;
            }
        }
    }
}
#endif
