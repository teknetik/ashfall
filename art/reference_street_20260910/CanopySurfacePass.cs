#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Staged material-only audition. Explicit Editor invocation follows actual
    // source review; this class does not imply that a source bake was accepted.
    public static class CanopySurfacePass
    {
        const string Folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/CanopySurfaceV1";
        const string GuardsHash = "971791ead4a82768b958e910aedc48087540a635d9536effe37d84e3ffeb5e43";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/reference_street_20260910/canopy-weathering-v1");
        static string Evidence => Path.Combine(Repo, "unity/evidence/reference-street/20260910/canopy-surface-v1-install");
        static string Guards => Path.Combine(Repo, "art/reference_street_20260910/canopy-surface-v1-guards.json");
        static string Hash(string path) { using var s = File.OpenRead(path); using var h = SHA256.Create(); return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant(); }
        static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t, null);
        static T[] Components<T>(Scene scene) where T : Component => scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<T>(true)).ToArray();
        static void Write(string name, object value) => File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(value, Formatting.Indented));
        static string PreservedScene(Scene scene, StaticRenderChunks chunks, HashSet<Renderer> targets)
        {
            bool SourceTransform(Transform t) => !chunks.generatedRoot || (t != chunks.generatedRoot && !t.IsChildOf(chunks.generatedRoot));
            return JsonConvert.SerializeObject(new {
                gameplay = DistrictCityPass.GameplaySignature(),
                transforms = Components<Transform>(scene).Where(SourceTransform).OrderBy(PathOf).Select(t => new { path = PathOf(t), data = EditorJsonUtility.ToJson(t), active = t.gameObject.activeSelf }).ToArray(),
                colliders = Components<Collider>(scene).OrderBy(c => PathOf(c.transform)).Select(c => new { path = PathOf(c.transform), data = EditorJsonUtility.ToJson(c) }).ToArray(),
                meshFilters = Components<MeshFilter>(scene).Where(c => SourceTransform(c.transform)).OrderBy(c => PathOf(c.transform)).Select(c => new { path = PathOf(c.transform), data = EditorJsonUtility.ToJson(c) }).ToArray(),
                otherRenderers = Components<Renderer>(scene).Where(c => SourceTransform(c.transform) && !targets.Contains(c)).OrderBy(c => PathOf(c.transform)).Select(c => new { path = PathOf(c.transform), data = EditorJsonUtility.ToJson(c) }).ToArray(),
                actors = Components<ActorAnimation>(scene).OrderBy(c => PathOf(c.transform)).Select(c => EditorJsonUtility.ToJson(c)).ToArray(),
                walkers = Components<AmbientWalker>(scene).OrderBy(c => PathOf(c.transform)).Select(c => EditorJsonUtility.ToJson(c)).ToArray()
            });
        }
        static void CheckOriginals(JObject guards)
        {
            foreach (var p in ((JObject)guards["preservedAssets"]).Properties())
                if (Hash(Path.Combine(Repo, p.Name)) != (string)p.Value) throw new InvalidDataException("Retained canopy asset changed: " + p.Name);
        }
        static string BakedMap(string family, string channel, JObject specs)
        {
            string path = Path.Combine(Source, family, channel + ".png");
            var proof = JObject.Parse(File.ReadAllText(Path.ChangeExtension(path, ".json")));
            if ((string)proof["family"] != family || (string)proof["channel"] != channel || (bool)proof["lightingBaked"] ||
                (string)proof["sha256"] != Hash(path) || !JToken.DeepEquals(proof["resolution"], specs[family]["resolution"]))
                throw new InvalidDataException("Unverified source bake: " + family + "/" + channel);
            return path;
        }
        static Texture2D Import(string path, bool srgb, bool normal, int width, int height, bool repeat)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!importer) throw new InvalidDataException("Missing texture importer " + path);
            importer.GetSourceTextureWidthAndHeight(out int w, out int h);
            if (w != width || h != height) throw new InvalidDataException("Source dimensions differ " + path);
            importer.ClearPlatformTextureSettings("Standalone");
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = srgb; importer.convertToNormalmap = false; importer.flipGreenChannel = false;
            importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = false;
            importer.maxTextureSize = Math.Max(w, h); importer.npotScale = TextureImporterNPOTScale.None;
            importer.mipmapEnabled = true; importer.streamingMipmaps = true; importer.anisoLevel = 8;
            importer.filterMode = FilterMode.Trilinear; importer.wrapMode = repeat ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
            importer.textureCompression = TextureImporterCompression.CompressedHQ; importer.compressionQuality = 100;
            importer.isReadable = false; importer.SaveAndReimport();
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!texture || texture.width != w || texture.height != h) throw new InvalidDataException("Runtime import resized " + path);
            return texture;
        }
        static object Pack(string source, string destination, int width, int height)
        {
            Texture2D rough = null, packed = null, check = null;
            try {
                rough = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                if (!rough.LoadImage(File.ReadAllBytes(source)) || rough.width != width || rough.height != height) throw new InvalidDataException("Roughness dimensions changed.");
                var a = rough.GetPixels32(); var b = new Color32[a.Length];
                for (int i = 0; i < a.Length; i++) b[i] = new Color32(0, 0, 0, (byte)(255 - a[i].r));
                packed = new Texture2D(width, height, TextureFormat.RGBA32, false, true);
                packed.SetPixels32(b); packed.Apply(false, false); var bytes = packed.EncodeToPNG();
                if (bytes[25] != 6) throw new InvalidDataException("Packed output must have true RGBA.");
                check = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                if (!check.LoadImage(bytes) || check.width != width || check.height != height) throw new InvalidDataException("Cannot verify packed output.");
                var c = check.GetPixels32();
                for (int i = 0; i < c.Length; i++) if (c[i].r != 0 || c[i].g != 0 || c[i].b != 0 || c[i].a != 255 - a[i].r) throw new InvalidDataException("Packed channel mismatch " + i);
                File.WriteAllBytes(destination, bytes);
                return new { source, sourceSha256 = Hash(source), destination, packedSha256 = Hash(destination), width, height, pixelsVerified = c.Length, conversion = "RGB=0; A=255-roughness.R, no resize or remap" };
            }
            finally { if (rough) Object.DestroyImmediate(rough); if (packed) Object.DestroyImmediate(packed); if (check) Object.DestroyImmediate(check); }
        }

        public static void Apply()
        {
            var scene = SceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating || SceneManager.sceneCount != 1 || scene.path != ImportBaseline.ScenePath || scene.isDirty)
                throw new InvalidOperationException("Use the saved native scene in settled Edit mode.");
            if (Directory.Exists(Folder) || Directory.Exists(Evidence)) throw new IOException("Preserve prior source audition; use a new version.");
            if (Hash(Guards) != GuardsHash) throw new InvalidDataException("Installed canopy guard changed.");
            var guards = JObject.Parse(File.ReadAllText(Guards)); CheckOriginals(guards);
            var contract = JObject.Parse(File.ReadAllText(Path.Combine(Source, "material-authoring-contract.json")));
            var specs = (JObject)contract["familyContracts"];
            float normalStrength = (float)contract["normalStrengthAudition"], albedoStrength = (float)contract["detailAlbedoStrengthAudition"];
            if (normalStrength < 0 || normalStrength > 1 || albedoStrength < 0 || albedoStrength > 1) throw new InvalidDataException("Unreviewable detail multiplier.");
            var chunks = Components<StaticRenderChunks>(scene).Single();
            if (chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Fresh source chunks required.");
            if (Components<ActorAnimation>(scene).Length != 9 || Components<AmbientWalker>(scene).Length != 4) throw new InvalidDataException("Current actor roster changed.");
            var pairs = ((JArray)guards["targets"]).Cast<JObject>().Select(g => {
                var r = Components<MeshRenderer>(scene).Single(c => PathOf(c.transform) == (string)g["path"]);
                var mesh = r.GetComponent<MeshFilter>().sharedMesh;
                int index = Array.IndexOf(chunks.sources, r);
                if (index < 0 || !chunks.sourceVisibility[index] || !r.gameObject.activeInHierarchy || r.sharedMaterials.Length != 1 ||
                    AssetDatabase.GetAssetPath(r.sharedMaterial) != (string)g["material"] || AssetDatabase.GetAssetPath(mesh) != (string)g["mesh"] ||
                    mesh.subMeshCount != 1 || mesh.GetIndexCount(0) / 3 != (uint)(int)g["triangles"] || mesh.uv.Length != mesh.vertexCount || mesh.tangents.Length != mesh.vertexCount)
                    throw new InvalidDataException("Installed canopy source changed: " + g["path"]);
                return (renderer: r, data: g);
            }).ToArray();
            if (pairs.Length != 6 || pairs.Select(p => p.renderer).Distinct().Count() != 6) throw new InvalidDataException("Expected six cloth sources.");
            foreach (string f in new[] { "Membrane", "Valance", "Seam", "Repair" }) foreach (string c in new[] { "BaseColor", "Roughness" }) BakedMap(f, c, specs);
            string detailFile = BakedMap("DetailFabric", "BaseColor", specs);
            var normalRow = ((JArray)contract["originalInputs"]["maps"]).Single(r => (string)r["channel"] == "nor_gl");
            string normalSource = Path.Combine(Repo, "refs/reference-street/20260910/cloth-candidates/book_pattern", (string)normalRow["file"]);
            if (Hash(normalSource) != (string)normalRow["sha256"]) throw new InvalidDataException("Original cloth normal changed.");
            var targets = new HashSet<Renderer>(pairs.Select(p => p.renderer));
            string preserved = PreservedScene(scene, chunks, targets);
            Directory.CreateDirectory(Evidence); Directory.CreateDirectory(Folder);
            EditorSceneManager.SaveScene(scene, Path.Combine(Evidence, "before-scene.unity"), true);
            File.Copy(Guards, Path.Combine(Evidence, "installed-source-guards.json"));
            File.Copy(Path.Combine(Source, "material-authoring-contract.json"), Path.Combine(Evidence, "material-contract.json"));
            try {
                File.Copy(detailFile, Folder + "/DetailAlbedo.png"); File.Copy(normalSource, Folder + "/DetailNormal.png");
                var detail = Import(Folder + "/DetailAlbedo.png", true, false, 4096, 4096, true);
                var normal = Import(Folder + "/DetailNormal.png", false, true, 4096, 4096, true);
                var materials = new Dictionary<string, Material>(); var packing = new List<object>();
                foreach (string f in new[] { "Membrane", "Valance", "Seam", "Repair" }) {
                    var spec = specs[f]; int w = (int)spec["resolution"][0], h = (int)spec["resolution"][1];
                    var metres = new Vector2((float)spec["metres"][0], (float)spec["metres"][1]);
                    string dir = Folder + "/" + f; Directory.CreateDirectory(dir);
                    File.Copy(BakedMap(f, "BaseColor", specs), dir + "/BaseColor.png");
                    packing.Add(Pack(BakedMap(f, "Roughness", specs), dir + "/MetalSmooth.png", w, h));
                    var baseMap = Import(dir + "/BaseColor.png", true, false, w, h, f == "Seam");
                    var mask = Import(dir + "/MetalSmooth.png", false, false, w, h, f == "Seam");
                    var old = pairs.First(p => (string)p.data["family"] == f).renderer.sharedMaterial;
                    var m = new Material(old) { name = "Finery weathered canvas " + f + " v1", enableInstancing = true };
                    m.SetColor("_BaseColor", Color.white); m.SetTexture("_BaseMap", baseMap);
                    m.SetTextureScale("_BaseMap", new Vector2(.4f / metres.x, .4f / metres.y)); m.SetTextureOffset("_BaseMap", Vector2.zero);
                    m.SetTexture("_BumpMap", null); m.SetTexture("_DetailNormalMap", normal); m.SetFloat("_DetailNormalMapScale", normalStrength);
                    m.SetTexture("_DetailAlbedoMap", detail); m.SetFloat("_DetailAlbedoMapScale", albedoStrength);
                    m.SetTextureScale("_DetailAlbedoMap", metres / .3f); m.SetTextureOffset("_DetailAlbedoMap", Vector2.zero);
                    m.SetTexture("_MetallicGlossMap", mask); m.SetFloat("_Metallic", 0); m.SetFloat("_Smoothness", 1); m.SetFloat("_SmoothnessTextureChannel", 0);
                    BaseShaderGUI.SetMaterialKeywords(m, UnityEditor.Rendering.Universal.ShaderGUI.LitGUI.SetMaterialKeywords, value => {
                        value.DisableKeyword("_DETAIL_MULX2"); value.EnableKeyword("_DETAIL_SCALED");
                    });
                    if (!m.IsKeywordEnabled("_DETAIL_SCALED") || !m.IsKeywordEnabled("_METALLICSPECGLOSSMAP") || m.IsKeywordEnabled("_NORMALMAP") || m.GetFloat("_Surface") != 0 || m.GetFloat("_AlphaClip") != 0)
                        throw new InvalidDataException("Unexpected canopy shader variant.");
                    AssetDatabase.CreateAsset(m, dir + "/Surface.mat"); materials.Add(f, m);
                }
                chunks.ShowSources(true);
                foreach (var p in pairs) { Undo.RecordObject(p.renderer, "Audition canopy surface"); p.renderer.sharedMaterial = materials[(string)p.data["family"]]; EditorUtility.SetDirty(p.renderer); }
                StaticRenderChunksEditor.Rebuild(chunks);
                if (preserved != PreservedScene(scene, chunks, targets)) throw new InvalidDataException("Unrelated scene content changed during material assignment.");
                CheckOriginals(guards);
                if (chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidDataException("Stale rebuilt chunks.");
                AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
                Write("installation.json", new { utc = DateTime.UtcNow.ToString("O"), scene = scene.path, sceneSha256 = Hash(scene.path),
                    assignments = pairs.Select(p => new { path = PathOf(p.renderer.transform), previousMaterial = (string)p.data["material"], material = AssetDatabase.GetAssetPath(p.renderer.sharedMaterial) }).ToArray(),
                    packing, normalSourceSha256 = Hash(normalSource), copiedNormalSha256 = Hash(Folder + "/DetailNormal.png"),
                    geometryUVsTangentsTransformsPhysicsActorsRoutesPreserved = true, chunksFresh = true, nativeAccepted = false, performanceQualified = false });
            }
            catch (Exception e) { File.WriteAllText(Path.Combine(Evidence, "failure.txt"), e.ToString()); throw; }
        }
    }
}
#endif
