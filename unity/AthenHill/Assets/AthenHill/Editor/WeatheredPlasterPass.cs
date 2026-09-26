#if UNITY_EDITOR
// Staged only. This one-shot installer must be invoked explicitly by the Editor operator.
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
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    public static class WeatheredPlasterPass
    {
        const string Folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/WeatheredPlasterV1";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ContractPath => Path.Combine(Repo, "art/reference_street_20260910/weathered-plaster-v1-contract.json");
        static string Evidence => Path.Combine(Repo, "unity/evidence/reference-street/20260910/weathered-plaster-v1-install");
        static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t, null);
        static string Sha(string path) { using (var h = SHA256.Create()) using (var f = File.OpenRead(path)) return BitConverter.ToString(h.ComputeHash(f)).Replace("-", "").ToLowerInvariant(); }
        static void Write(string name, object data) => File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented));
        static bool Finite(float f) => !float.IsNaN(f) && !float.IsInfinity(f);
        static string RepoFile(string relative)
        {
            string path = Path.GetFullPath(Path.Combine(Repo, relative));
            if (!path.StartsWith(Repo + Path.DirectorySeparatorChar, StringComparison.Ordinal) || !File.Exists(path))
                throw new InvalidDataException("Missing source inside repository: " + relative);
            return path;
        }
        static IEnumerable<T> Components<T>(Scene scene) where T : Component => scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<T>(true));
        static string Physics(Scene scene) => JsonConvert.SerializeObject(Components<Collider>(scene).OrderBy(c => PathOf(c.transform), StringComparer.Ordinal)
            .Select(c => new { path = PathOf(c.transform), active = c.gameObject.activeInHierarchy,
                matrix = Enumerable.Range(0, 16).Select(i => c.transform.localToWorldMatrix[i]).ToArray(), data = EditorJsonUtility.ToJson(c) }));
        static string Actors(Scene scene)
        {
            var actors = Components<ActorAnimation>(scene).OrderBy(c => PathOf(c.transform), StringComparer.Ordinal).ToArray();
            var walkers = Components<AmbientWalker>(scene).OrderBy(c => PathOf(c.transform), StringComparer.Ordinal).ToArray();
            if (actors.Length != 9 || walkers.Length != 4 || Components<PlayerMotor>(scene).Count() != 1)
                throw new InvalidDataException("Expected all nine actors, four ambient routes and one player.");
            return JsonConvert.SerializeObject(new {
                gameplay = DistrictCityPass.GameplaySignature(),
                actors = actors.Select(c => new { path = PathOf(c.transform), data = EditorJsonUtility.ToJson(c) }).ToArray(),
                walkers = walkers.Select(c => new { path = PathOf(c.transform), data = EditorJsonUtility.ToJson(c),
                    waypoints = c.waypoints.Select(t => new { path = t ? PathOf(t) : null,
                        matrix = t ? Enumerable.Range(0, 16).Select(i => t.localToWorldMatrix[i]).ToArray() : null }).ToArray() }).ToArray()
            });
        }
        static string Transforms(Scene scene, Transform generated) => JsonConvert.SerializeObject(Components<Transform>(scene)
            .Where(t => !generated || (t != generated && !t.IsChildOf(generated)))
            .OrderBy(PathOf, StringComparer.Ordinal).Select(t => new { path = PathOf(t), parent = t.parent ? PathOf(t.parent) : null,
                position = new[] { t.localPosition.x, t.localPosition.y, t.localPosition.z },
                rotation = new[] { t.localRotation.x, t.localRotation.y, t.localRotation.z, t.localRotation.w },
                scale = new[] { t.localScale.x, t.localScale.y, t.localScale.z }, active = t.gameObject.activeSelf, t.gameObject.layer, t.gameObject.tag }));

        static object CheckUv(MeshRenderer renderer, JObject expected)
        {
            var filter = renderer.GetComponent<MeshFilter>();
            if (!filter || !filter.sharedMesh || AssetDatabase.GetAssetPath(filter.sharedMesh) != (string)expected["meshPath"])
                throw new InvalidDataException("Saved source mesh changed: " + PathOf(renderer.transform));
            var mesh = filter.sharedMesh;
            if (Sha(AssetDatabase.GetAssetPath(mesh)) != (string)expected["meshSha256"] || mesh.subMeshCount != 1 ||
                mesh.vertexCount != (int)expected["vertices"] || mesh.GetIndexCount(0) / 3 != (uint)(int)expected["triangles"])
                throw new InvalidDataException("Saved source topology/hash changed: " + mesh.name);
            var p = mesh.vertices; var uv = mesh.uv; var normals = mesh.normals; var tangents = mesh.tangents; var triangles = mesh.triangles;
            if (uv.Length != p.Length || normals.Length != p.Length || tangents.Length != p.Length)
                throw new InvalidDataException("UV0, normals or tangents missing: " + mesh.name);
            float maximumDot = 0;
            for (int i = 0; i < p.Length; i++)
            {
                var t = new Vector3(tangents[i].x, tangents[i].y, tangents[i].z);
                if (!Finite(p[i].x) || !Finite(p[i].y) || !Finite(p[i].z) || !Finite(uv[i].x) || !Finite(uv[i].y) ||
                    !Finite(normals[i].sqrMagnitude) || !Finite(t.sqrMagnitude) || !Finite(tangents[i].w) ||
                    Mathf.Abs(normals[i].magnitude - 1) > 0.001f || Mathf.Abs(t.magnitude - 1) > 0.001f || Mathf.Abs(Mathf.Abs(tangents[i].w) - 1) > 0.001f)
                    throw new InvalidDataException("Invalid saved normal/tangent/UV: " + mesh.name + " vertex " + i);
                maximumDot = Mathf.Max(maximumDot, Mathf.Abs(Vector3.Dot(normals[i], t)));
            }
            if (maximumDot > 0.001f) throw new InvalidDataException("Saved tangents are not orthogonal: " + mesh.name);
            var matrix = renderer.transform.localToWorldMatrix;
            var tiles = new List<double>(); double area = 0, degenerateUvArea = 0, offMetricArea = 0;
            for (int i = 0; i < triangles.Length; i += 3)
            {
                int a = triangles[i], b = triangles[i + 1], c = triangles[i + 2];
                // Use double differences after the actual source transform: record tiny numerical slivers honestly.
                Vector3 va = matrix.MultiplyPoint3x4(p[a]), vb = matrix.MultiplyPoint3x4(p[b]), vc = matrix.MultiplyPoint3x4(p[c]);
                double ax = (double)vb.x - va.x, ay = (double)vb.y - va.y, az = (double)vb.z - va.z;
                double bx = (double)vc.x - va.x, by = (double)vc.y - va.y, bz = (double)vc.z - va.z;
                double cx = ay * bz - az * by, cy = az * bx - ax * bz, cz = ax * by - ay * bx;
                double faceArea = Math.Sqrt(cx * cx + cy * cy + cz * cz) / 2;
                double uvArea = Math.Abs(((double)uv[b].x - uv[a].x) * ((double)uv[c].y - uv[a].y) - ((double)uv[c].x - uv[a].x) * ((double)uv[b].y - uv[a].y)) / 2;
                area += faceArea;
                if (uvArea <= 1e-12) { degenerateUvArea += faceArea; continue; }
                double tile = Math.Sqrt(Math.Max(Math.Abs(cx), Math.Max(Math.Abs(cy), Math.Abs(cz))) / (2 * uvArea));
                if (double.IsNaN(tile) || double.IsInfinity(tile)) throw new InvalidDataException("Non-finite source UV metric: " + mesh.name);
                tiles.Add(tile);
                if (Math.Abs(tile - (double)expected["uv0TileMetres"]) > 0.02) offMetricArea += faceArea;
            }
            if (tiles.Count == 0) throw new InvalidDataException("No usable UV triangles: " + mesh.name);
            tiles.Sort(); double median = tiles[tiles.Count / 2];
            if (Math.Abs(median - (double)expected["uv0TileMetres"]) > 0.02)
                throw new InvalidDataException("Actual world UV scale changed: " + PathOf(renderer.transform) + " tile=" + median);
            return new { path = PathOf(renderer.transform), mesh = AssetDatabase.GetAssetPath(mesh), meshSha256 = (string)expected["meshSha256"],
                vertices = p.Length, triangles = triangles.Length / 3, tileMedianMetres = median, surfaceAreaM2 = area,
                offMetricAreaM2 = offMetricArea, degenerateUvAreaM2 = degenerateUvArea, maxAbsNormalTangentDot = maximumDot,
                normalsAndTangentsPreserved = true, sourcePhysicalTileMetres = 2, materialBaseMapScale = new[] { 2f, 2f } };
        }

        static Texture2D Import(string path, bool color, bool normal)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!importer) throw new InvalidDataException("Texture importer absent: " + path);
            importer.GetSourceTextureWidthAndHeight(out int width, out int height);
            if (width != 4096 || height != 4096) throw new InvalidDataException("Expected retained 4K photo input: " + path);
            importer.ClearPlatformTextureSettings("Standalone");
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = color; importer.convertToNormalmap = false; importer.flipGreenChannel = false;
            importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = false;
            importer.maxTextureSize = Math.Max(width, height); importer.npotScale = TextureImporterNPOTScale.None;
            importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
            importer.filterMode = FilterMode.Bilinear; importer.wrapMode = TextureWrapMode.Repeat;
            importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.compressionQuality = 100;
            importer.isReadable = false; importer.SaveAndReimport();
            var result = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!result || result.width != width || result.height != height) throw new InvalidDataException("Imported dimensions changed: " + path);
            return result;
        }

        static object Pack(string sourcePath, string destination)
        {
            Texture2D rough = null, packed = null, decoded = null;
            try
            {
                rough = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                if (!rough.LoadImage(File.ReadAllBytes(sourcePath), false) || rough.width != 4096 || rough.height != 4096)
                    throw new InvalidDataException("Roughness did not decode at full source resolution.");
                var src = rough.GetPixels32(); var dst = new Color32[src.Length]; int minimum = 255, maximum = 0; long sum = 0;
                for (int i = 0; i < src.Length; i++)
                {
                    minimum = Math.Min(minimum, src[i].r); maximum = Math.Max(maximum, src[i].r); sum += src[i].r;
                    dst[i] = new Color32(0, 0, 0, (byte)(255 - src[i].r));
                }
                // Keep alpha in a distinct RGBA output; LoadImage can change the decoded source format.
                packed = new Texture2D(rough.width, rough.height, TextureFormat.RGBA32, false, true);
                packed.SetPixels32(dst); packed.Apply(false, false); var bytes = packed.EncodeToPNG();
                if (bytes.Length < 26 || bytes[25] != 6) throw new InvalidDataException("Metal/smooth PNG must contain RGBA.");
                decoded = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                if (!decoded.LoadImage(bytes, false) || decoded.width != rough.width || decoded.height != rough.height)
                    throw new InvalidDataException("Packed output dimensions changed.");
                var check = decoded.GetPixels32();
                if (check.Length != src.Length) throw new InvalidDataException("Packed output pixel count changed.");
                for (int i = 0; i < check.Length; i++)
                    if (check[i].r != 0 || check[i].g != 0 || check[i].b != 0 || check[i].a != 255 - src[i].r)
                        throw new InvalidDataException("Packed PBR channel mismatch at pixel " + i);
                File.WriteAllBytes(destination, bytes);
                return new { source = sourcePath, sourceSha256 = Sha(sourcePath), sourceDecodedFormat = rough.format.ToString(),
                    width = rough.width, height = rough.height, pixelsVerified = check.Length, packedPngColorType = bytes[25],
                    roughnessMinimum = minimum / 255.0, roughnessMaximum = maximum / 255.0, roughnessMean = sum / (255.0 * src.Length),
                    conversion = "R/G/B=0; A=255-source roughness R. New RGBA32, no resize or scalar remap.", packedSha256 = Sha(destination) };
            }
            finally { if (rough) Object.DestroyImmediate(rough); if (packed) Object.DestroyImmediate(packed); if (decoded) Object.DestroyImmediate(decoded); }
        }

        public static void Apply()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorSceneManager.sceneCount != 1 ||
                scene.path != ImportBaseline.ScenePath || scene.isDirty || QualitySettings.globalTextureMipmapLimit != 0)
                throw new InvalidOperationException("Use the single saved AthenHill scene in Edit mode after compilation, with full texture quality.");
            if (Directory.Exists(Folder) || Directory.Exists(Evidence)) throw new InvalidOperationException("Prior material assets/evidence exist; retain them and inspect before a new revision.");
            var contract = JObject.Parse(File.ReadAllText(ContractPath));
            if ((string)contract["revision"] != "WeatheredPlasterV1" || (int)contract["sourceRosterCount"] != 35 ||
                (float)contract["uv0TileMetres"] != 4 || (float)contract["sourceTileMetres"] != 2 ||
                !contract["baseMapScale"].Values<float>().SequenceEqual(new[] { 2f, 2f }) || (float)contract["normalStrength"] != 1 ||
                (float)contract["metallic"] != 0 || (float)contract["smoothnessMultiplier"] != 1)
                throw new InvalidDataException("Reviewable material contract changed.");
            string oldPath = (string)contract["sourceMaterial"];
            var old = AssetDatabase.LoadAssetAtPath<Material>(oldPath);
            if (!old || old.shader.name != "Universal Render Pipeline/Lit" || AssetDatabase.AssetPathToGUID(oldPath) != (string)contract["sourceMaterialGuid"] || Sha(oldPath) != (string)contract["sourceMaterialSha256"])
                throw new InvalidDataException("Expected retained HeroLimePlaster changed.");
            if (Sha(RepoFile((string)contract["materialAudit"])) != (string)contract["materialAuditSha256"] ||
                Sha(RepoFile((string)contract["provenance"])) != (string)contract["provenanceSha256"])
                throw new InvalidDataException("Source audit or provenance changed.");
            var maps = (JObject)contract["maps"];
            foreach (var map in maps.Properties())
                if (Sha(RepoFile((string)map.Value["path"])) != (string)map.Value["sha256"])
                    throw new InvalidDataException("Retained source photo changed: " + map.Name);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!chunks || chunks.gameObject.scene != scene || chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Fresh rebuilt source chunks are required.");
            var expected = ((JArray)contract["sources"]).Cast<JObject>().ToDictionary(x => (string)x["path"], StringComparer.Ordinal);
            var targets = chunks.sources.OfType<MeshRenderer>().Where(r => r && r.sharedMaterials.Contains(old)).OrderBy(r => PathOf(r.transform), StringComparer.Ordinal).ToArray();
            if (expected.Count != 35 || targets.Length != 35 || targets.Select(r => PathOf(r.transform)).Distinct().Count() != 35 ||
                !targets.Select(r => PathOf(r.transform)).OrderBy(x => x, StringComparer.Ordinal).SequenceEqual(expected.Keys.OrderBy(x => x, StringComparer.Ordinal)))
                throw new InvalidDataException("Current HeroLimePlaster source roster differs from the 35-source contract.");
            var uvAudit = new List<object>();
            foreach (var target in targets)
            {
                if (target.sharedMaterials.Length != 1 || target.sharedMaterial != old || !target.gameObject.activeInHierarchy || !chunks.sourceVisibility[Array.IndexOf(chunks.sources, target)])
                    throw new InvalidDataException("Source material or intended visibility changed: " + PathOf(target.transform));
                uvAudit.Add(CheckUv(target, expected[PathOf(target.transform)]));
            }
            string physics = Physics(scene), actors = Actors(scene), transforms = Transforms(scene, chunks.generatedRoot);
            string contractSha = Sha(ContractPath);
            Directory.CreateDirectory(Evidence); Directory.CreateDirectory(Folder);
            File.Copy(ContractPath, Path.Combine(Evidence, "authored-contract.json"), false);
            EditorSceneManager.SaveScene(scene, Path.Combine(Evidence, "before-scene.unity"), true);
            File.WriteAllText(Path.Combine(Evidence, "colliders-before.json"), physics);
            File.WriteAllText(Path.Combine(Evidence, "actors-before.json"), actors);
            Write("source-uv-audit.json", uvAudit);
            try
            {
                File.Copy(RepoFile((string)maps["Diffuse"]["path"]), Folder + "/BaseColor.png", false);
                File.Copy(RepoFile((string)maps["nor_gl"]["path"]), Folder + "/Normal.png", false);
                var packing = Pack(RepoFile((string)maps["Rough"]["path"]), Folder + "/MetalSmooth.png");
                var color = Import(Folder + "/BaseColor.png", true, false); var normal = Import(Folder + "/Normal.png", false, true); var packed = Import(Folder + "/MetalSmooth.png", false, false);
                var material = new Material(old) { name = "Weathered plaster 20260910 v1" };
                var tint = contract["baseColorLinear"].Values<float>().ToArray();
                if (tint.Length != 4 || tint.Any(v => !Finite(v) || v < 0 || v > 1) || tint[3] != 1) throw new InvalidDataException("Invalid reviewed tint.");
                material.SetTexture("_BaseMap", color); material.SetTexture("_MainTex", color);
                material.SetColor("_BaseColor", new Color(tint[0], tint[1], tint[2], tint[3])); material.SetColor("_Color", material.GetColor("_BaseColor"));
                material.SetTextureScale("_BaseMap", new Vector2(2, 2)); material.SetTextureOffset("_BaseMap", Vector2.zero);
                material.SetTexture("_BumpMap", normal); material.SetFloat("_BumpScale", 1);
                material.SetTexture("_MetallicGlossMap", packed); material.SetFloat("_Metallic", 0); material.SetFloat("_Smoothness", 1); material.SetFloat("_SmoothnessTextureChannel", 0);
                material.EnableKeyword("_NORMALMAP"); material.EnableKeyword("_METALLICSPECGLOSSMAP"); material.DisableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A");
                string newPath = Folder + "/WeatheredPlaster.mat"; AssetDatabase.CreateAsset(material, newPath);
                chunks.ShowSources(true);
                foreach (var target in targets)
                {
                    target.sharedMaterial = material; EditorUtility.SetDirty(target); PrefabUtility.RecordPrefabInstancePropertyModifications(target);
                }
                if (Physics(scene) != physics || Actors(scene) != actors || Transforms(scene, chunks.generatedRoot) != transforms)
                    throw new InvalidOperationException("Source transforms, collisions or gameplay changed; do not save.");
                AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks);
                if (Physics(scene) != physics || Actors(scene) != actors || Transforms(scene, chunks.generatedRoot) != transforms ||
                    chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                    throw new InvalidOperationException("Post-rebuild preservation failed.");
                foreach (var target in targets)
                {
                    if (target.sharedMaterial != material) throw new InvalidDataException("Material assignment changed during rebuild.");
                    CheckUv(target, expected[PathOf(target.transform)]);
                }
                if (Sha(oldPath) != (string)contract["sourceMaterialSha256"] || Sha(ContractPath) != contractSha)
                    throw new InvalidDataException("Original material or reviewed contract was changed.");
                foreach (var map in maps.Properties()) if (Sha(RepoFile((string)map.Value["path"])) != (string)map.Value["sha256"])
                    throw new InvalidDataException("Original photo changed during installation.");
                EditorSceneManager.SaveScene(scene);
                File.WriteAllText(Path.Combine(Evidence, "colliders-after.json"), Physics(scene));
                File.WriteAllText(Path.Combine(Evidence, "actors-after.json"), Actors(scene));
                Write("installation.json", new { utc = DateTime.UtcNow, material = newPath, materialSha256 = Sha(newPath), contractSha256 = contractSha,
                    assignments = targets.Select(t => new { path = PathOf(t.transform), originalMaterial = oldPath, material = newPath }).ToArray(),
                    packing, copiedColorSha256 = Sha(Folder + "/BaseColor.png"), copiedNormalSha256 = Sha(Folder + "/Normal.png"),
                    sourceMeshesAndTangentsUnchanged = true, originalMaterialAndPhotoSourcesPreserved = true, allSourceTransformsPreserved = true,
                    allCollidersPreserved = true, allActorsAndRoutesPreserved = true, chunksFresh = true, savedSceneSha256 = Sha(scene.path),
                    nativeAccepted = false, next = "Matched native wide and pedestrian views at hour 12 and 16, followed by moving close inspection. Root owns localized weathering separately." });
            }
            catch (Exception exception)
            {
                Write("failure.json", new { utc = DateTime.UtcNow, exception = exception.ToString(), sceneDirty = scene.isDirty, chunks.editingSources,
                    action = "Preserve partial outputs and before-scene; inspect before any retry. No automatic deletion, asset overwrite or native acceptance." });
                throw;
            }
        }
    }
}
#endif
