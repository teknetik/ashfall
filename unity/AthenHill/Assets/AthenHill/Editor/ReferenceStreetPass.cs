using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Explicit, recoverable authoring import. The player uses only saved assets.
    public static class ReferenceStreetPass
    {
        const string Folder = "Assets/AthenHill/Art/ReferenceStreet/20260909";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/reference_street_20260909");
        static string Evidence => Path.Combine(Repo, "unity/evidence/reference-street/20260909");
        sealed class Part
        {
            public string name, sourcePath, family, material;
            public float[][] positions, normals, uv;
            public int[] indices;
            public bool castsShadow = true;
        }
        static readonly List<object> Changes = new List<object>();
        static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t, null);
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '_' ? c : '_').ToArray());
        static Vector3 V(float[] v) => new Vector3(v[0], v[1], v[2]);
        static string Collision() => JsonConvert.SerializeObject(Object.FindObjectsByType<Collider>(FindObjectsInactive.Include)
            .Where(c => c.gameObject.scene.IsValid()).OrderBy(c => PathOf(c.transform)).Select(c => new {
                path = PathOf(c.transform), id = GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(),
                c.enabled, c.isTrigger, active = c.gameObject.activeInHierarchy,
                matrix = Enumerable.Range(0, 16).Select(i => c.transform.localToWorldMatrix[i]).ToArray(),
                boxCenter = c is BoxCollider b ? new[] { b.center.x, b.center.y, b.center.z } : null,
                boxSize = c is BoxCollider b2 ? new[] { b2.size.x, b2.size.y, b2.size.z } : null,
                mesh = c is MeshCollider m ? AssetDatabase.GetAssetPath(m.sharedMesh) : null
            }));

        static Texture2D ImportMap(string path, bool colour, bool normal)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var imp = (TextureImporter)AssetImporter.GetAtPath(path);
            imp.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            imp.sRGBTexture = colour; imp.mipmapEnabled = true; imp.streamingMipmaps = true;
            imp.maxTextureSize = 4096; imp.anisoLevel = 8; imp.npotScale = TextureImporterNPOTScale.None;
            imp.textureCompression = TextureImporterCompression.CompressedHQ; imp.isReadable = false;
            imp.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
        static Material PrepareMaterial(string family, string revision = null)
        {
            string dir = Folder + (revision == null ? "" : "/" + revision) + "/" + family;
            string src = Path.Combine(Source, revision == null ? "textures" : "textures-v3", family);
            Directory.CreateDirectory(dir);
            File.Copy(Path.Combine(src, "BaseColor.png"), dir + "/BaseColor.png", false);
            File.Copy(Path.Combine(src, "Normal.png"), dir + "/Normal.png", false);
            var rough = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
            var metal = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
            rough.LoadImage(File.ReadAllBytes(Path.Combine(src, "Roughness.png")));
            metal.LoadImage(File.ReadAllBytes(Path.Combine(src, "Metallic.png")));
            if (rough.width != metal.width || rough.height != metal.height) throw new InvalidDataException("Map size mismatch");
            var rr = rough.GetPixels32(); var mm = metal.GetPixels32();
            for (int i = 0; i < rr.Length; i++) rr[i] = new Color32(mm[i].r, 0, 0, (byte)(255 - rr[i].r));
            var packed = new Texture2D(rough.width, rough.height, TextureFormat.RGBA32, false, true);
            packed.SetPixels32(rr); packed.Apply(); File.WriteAllBytes(dir + "/MetalSmooth.png", packed.EncodeToPNG());
            Object.DestroyImmediate(rough); Object.DestroyImmediate(metal); Object.DestroyImmediate(packed);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "Reference " + family, enableInstancing = true };
            mat.SetTexture("_BaseMap", ImportMap(dir + "/BaseColor.png", true, false)); mat.SetColor("_BaseColor", Color.white);
            mat.SetTexture("_BumpMap", ImportMap(dir + "/Normal.png", false, true)); mat.SetFloat("_BumpScale", 1);
            mat.SetTexture("_MetallicGlossMap", ImportMap(dir + "/MetalSmooth.png", false, false));
            mat.SetFloat("_Metallic", 1); mat.SetFloat("_Smoothness", 1); mat.SetFloat("_SmoothnessTextureChannel", 0);
            mat.EnableKeyword("_NORMALMAP"); mat.EnableKeyword("_METALLICSPECGLOSSMAP");
            AssetDatabase.CreateAsset(mat, dir + "/" + family + ".mat");
            return mat;
        }

        [MenuItem("Athen Hill/Reference street/Install reviewed metal and brush v3")]
        public static void ApplyMetalV3()
        {
            var scene = EditorSceneManager.GetActiveScene();
            const string revision = "RevisionV3";
            string destination = Folder + "/" + revision;
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.path != ImportBaseline.ScenePath || scene.isDirty)
                throw new InvalidOperationException("Open the saved city in Edit mode.");
            if (Directory.Exists(destination)) throw new InvalidOperationException("Preserve the installed v3 revision.");
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).GroupBy(PathOf).ToDictionary(g => g.Key, g => g.First());
            var aged = JObject.Parse(File.ReadAllText(Path.Combine(Source, "aged-steel-assignment-contract.json")));
            var contract = JObject.Parse(File.ReadAllText(Path.Combine(Source, "metal-import-contract.json")));
            foreach (string family in new[] { "ShutterSteel", "AgedSteel" })
                foreach (string channel in new[] { "BaseColor", "Normal", "Roughness", "Metallic" })
                    if (!File.Exists(Path.Combine(Source, "textures-v3", family, channel + ".png"))) throw new FileNotFoundException("Missing v3 material bake");
            foreach (var target in aged["groups"].SelectMany(g => g["targets"]))
            {
                string path = (string)target["path"];
                if (!all.TryGetValue(path, out var t) || AssetDatabase.GetAssetPath(t.GetComponent<MeshFilter>().sharedMesh) != (string)target["expectedMeshPath"])
                    throw new InvalidDataException("Aged steel source mesh changed: " + path);
            }
            var brush = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, "brush-graffiti-meshes-v3.json")));
            if (brush.Length != 2 || brush.Any(p => string.IsNullOrEmpty(p.sourcePath) || !all.ContainsKey(p.sourcePath)))
                throw new InvalidDataException("V3 brush must replace the two existing meshes.");
            string gameplay = DistrictCityPass.GameplaySignature(), collision = Collision();
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); chunks.ShowSources(true);
            Changes.Clear();
            var shutter = PrepareMaterial("ShutterSteel", revision);
            foreach (string path in contract["ShutterSteel"]["replaceMaterialOnlyOn"].Values<string>()) Assign(all[path].GetComponent<Renderer>(), shutter);
            var coated = PrepareMaterial("AgedSteel", revision);
            foreach (var group in aged["groups"])
            {
                var variant = new Material(coated) { name = (string)group["materialVariant"] + " v3" };
                variant.SetTextureScale("_BaseMap", new Vector2((float)group["uvScale"][0], (float)group["uvScale"][1]));
                AssetDatabase.CreateAsset(variant, destination + "/" + variant.name + ".mat");
                foreach (string path in group["targetSourcePaths"].Values<string>()) Assign(all[path].GetComponent<Renderer>(), variant);
            }
            Geometry("brush-graffiti-meshes-v3.json", all,
                new Dictionary<string, Material> { ["BrushPaint"] = AssetDatabase.LoadAssetAtPath<Material>(Folder + "/BrushPaint.mat") },
                GameObject.Find("Reference street thresholds and detail").transform);
            if (gameplay != DistrictCityPass.GameplaySignature() || collision != Collision())
                throw new InvalidOperationException("Gameplay or collision signature changed unexpectedly");
            AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.Combine(Evidence, "metal-v3-installation.json"), JsonConvert.SerializeObject(new {
                utc = DateTime.UtcNow, changes = Changes, gameplayPreserved = true, collidersPreserved = true,
                reason = "Native audition showed overly clean coated metal and thin brush lettering; previous assets retained."
            }, Formatting.Indented));
        }
        static void Assign(Renderer renderer, Material material)
        {
            Changes.Add(new { path = PathOf(renderer.transform), originalMaterials = renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath).ToArray(), newMaterial = AssetDatabase.GetAssetPath(material) });
            renderer.sharedMaterials = new[] { material };
            EditorUtility.SetDirty(renderer); PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
        }
        static void Geometry(string file, Dictionary<string, Transform> all, Dictionary<string, Material> materials, Transform parent)
        {
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, file)));
            int index = 0;
            foreach (var part in parts)
            {
                if (part.positions.Length != part.normals.Length || part.positions.Length != part.uv.Length || part.indices.Any(i => i < 0 || i >= part.positions.Length)) throw new InvalidDataException("Invalid buffers: " + part.name);
                bool replacement = !string.IsNullOrEmpty(part.sourcePath);
                Transform t;
                if (replacement)
                {
                    if (!all.TryGetValue(part.sourcePath, out t) || !t.GetComponent<MeshFilter>()) throw new InvalidDataException("Missing replacement: " + part.sourcePath);
                }
                else { var go = new GameObject(part.name); t = go.transform; t.SetParent(parent, false); go.AddComponent<MeshFilter>(); go.AddComponent<MeshRenderer>(); }
                var filter = t.GetComponent<MeshFilter>(); var renderer = t.GetComponent<MeshRenderer>();
                string original = filter.sharedMesh ? AssetDatabase.GetAssetPath(filter.sharedMesh) : null;
                var mesh = new Mesh { name = part.name + " reference revision", indexFormat = IndexFormat.UInt32 };
                mesh.vertices = part.positions.Select(p => t.InverseTransformPoint(V(p))).ToArray();
                mesh.normals = part.normals.Select(p => t.localToWorldMatrix.transpose.MultiplyVector(V(p)).normalized).ToArray();
                mesh.uv = part.uv.Select(p => new Vector2(p[0], p[1])).ToArray(); mesh.triangles = part.indices;
                mesh.RecalculateTangents(); mesh.RecalculateBounds();
                string asset = Folder + "/Meshes/" + Safe(Path.GetFileNameWithoutExtension(file)) + "_" + (index++).ToString("D3") + "_" + Safe(part.name) + ".asset";
                AssetDatabase.CreateAsset(mesh, asset);
                Changes.Add(new { path = PathOf(t), originalMesh = original, newMesh = asset, addition = !replacement, triangles = part.indices.Length / 3 });
                filter.sharedMesh = mesh; EditorUtility.SetDirty(filter); PrefabUtility.RecordPrefabInstancePropertyModifications(filter);
                Assign(renderer, materials[part.material]);
                if (!part.castsShadow || part.material == "MineralRunoff") renderer.shadowCastingMode = ShadowCastingMode.Off;
            }
        }

        [MenuItem("Athen Hill/Reference street/Install reviewed street revision")]
        public static void Apply()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.path != ImportBaseline.ScenePath || scene.isDirty) throw new InvalidOperationException("Open the saved city in Edit mode.");
            if (Directory.Exists(Folder)) throw new InvalidOperationException("Preserve installed revision; use ordinary scoped edits after installation.");
            Changes.Clear();
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).GroupBy(PathOf).ToDictionary(g => g.Key, g => g.First());
            var aged = JObject.Parse(File.ReadAllText(Path.Combine(Source, "aged-steel-assignment-contract.json")));
            foreach (var target in aged["groups"].SelectMany(g => g["targets"]))
            {
                string path = (string)target["path"];
                if (!all.TryGetValue(path, out var t) || !t.GetComponent<MeshFilter>() || AssetDatabase.GetAssetPath(t.GetComponent<MeshFilter>().sharedMesh) != (string)target["expectedMeshPath"])
                    throw new InvalidDataException("Aged steel UV proof no longer matches source mesh: " + path);
            }
            foreach (string family in new[] { "ShutterSteel", "AgedSteel", "ReferencePlaster" })
                foreach (string channel in new[] { "BaseColor", "Normal", "Roughness", "Metallic" })
                    if (!File.Exists(Path.Combine(Source, "textures", family, channel + ".png"))) throw new FileNotFoundException("Missing reviewed material bake");
            foreach (string file in new[] { "threshold-replacements-v2.json", "threshold-additions-v2.json", "brush-graffiti-meshes-v1.json" })
                foreach (var part in JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, file))))
                    if (!string.IsNullOrEmpty(part.sourcePath) && (!all.ContainsKey(part.sourcePath) || !all[part.sourcePath].GetComponent<MeshFilter>())) throw new InvalidDataException("Missing geometry source: " + part.sourcePath);
            string gameplay = DistrictCityPass.GameplaySignature(), collision = Collision();
            File.WriteAllText(Path.Combine(Evidence, "gameplay-before.json"), gameplay);
            File.WriteAllText(Path.Combine(Evidence, "collision-before.json"), collision);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>(); chunks.ShowSources(true);
            Directory.CreateDirectory(Folder + "/Meshes"); AssetDatabase.Refresh();
            var materials = new Dictionary<string, Material>();
            materials["Stone"] = new Material(AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/FacadeMaterials/20260909/Stone/Stone.mat")) { name = "Reference threshold stone" };
            materials["Stone"].SetFloat("_BumpScale", .55f);
            AssetDatabase.CreateAsset(materials["Stone"], Folder + "/ThresholdStone.mat");
            materials["ShutterSteel"] = PrepareMaterial("ShutterSteel");
            var contract = JObject.Parse(File.ReadAllText(Path.Combine(Source, "metal-import-contract.json")));
            foreach (string path in contract["ShutterSteel"]["replaceMaterialOnlyOn"].Values<string>()) Assign(all[path].GetComponent<Renderer>(), materials["ShutterSteel"]);
            var coated = PrepareMaterial("AgedSteel");
            foreach (var group in aged["groups"])
            {
                var variant = new Material(coated) { name = (string)group["materialVariant"] };
                variant.SetTextureScale("_BaseMap", new Vector2((float)group["uvScale"][0], (float)group["uvScale"][1]));
                AssetDatabase.CreateAsset(variant, Folder + "/" + variant.name + ".mat");
                foreach (string path in group["targetSourcePaths"].Values<string>()) Assign(all[path].GetComponent<Renderer>(), variant);
            }
            var root = new GameObject("Reference street thresholds and detail").transform;
            chunks.sourceRoots = chunks.sourceRoots.Concat(new[] { root }).ToArray();
            Geometry("threshold-replacements-v2.json", all, materials, root);
            Geometry("threshold-additions-v2.json", all, materials, root);
            materials["BrushPaint"] = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "Reference brush paint", enableInstancing = true };
            materials["BrushPaint"].SetColor("_BaseColor", new Color(.73f, .66f, .53f));
            materials["BrushPaint"].SetFloat("_Metallic", 0); materials["BrushPaint"].SetFloat("_Smoothness", .08f);
            materials["BrushPaint"].SetFloat("_Cull", 0);
            AssetDatabase.CreateAsset(materials["BrushPaint"], Folder + "/BrushPaint.mat");
            var oldPaint = all.Where(p => p.Key.StartsWith("Field Supply and Finery weathering/field_supply/"))
                .Select(p => p.Value.GetComponent<MeshRenderer>()).Where(r => r && r.sharedMaterials.Any(m => m && m.name == "GraffitiSolid")).ToArray();
            if (oldPaint.Length == 0) throw new InvalidDataException("Expected old field shutter paint");
            foreach (var r in oldPaint) { Changes.Add(new { path = PathOf(r.transform), originalActive = r.gameObject.activeSelf, newActive = false }); r.gameObject.SetActive(false); PrefabUtility.RecordPrefabInstancePropertyModifications(r.gameObject); }
            Geometry("brush-graffiti-meshes-v1.json", all, materials, root);
            materials["ReferencePlaster"] = PrepareMaterial("ReferencePlaster");
            var plaster = JObject.Parse(File.ReadAllText(Path.Combine(Source, "plaster-manifest.json")));
            foreach (string path in plaster["targetSourcePaths"].Values<string>()) Assign(all[path].GetComponent<Renderer>(), materials["ReferencePlaster"]);
            InstallLighting();
            var review = new GameObject("cam_reference_street").AddComponent<Camera>();
            review.CopyFrom(GameObject.Find("cam_courtyard_facade").GetComponent<Camera>());
            var sourceCameraData = GameObject.Find("cam_courtyard_facade").GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
            if (sourceCameraData) EditorUtility.CopySerialized(sourceCameraData, review.gameObject.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>());
            review.enabled = false; review.fieldOfView = 52;
            review.transform.position = new Vector3(6.5f, 2.3f, -1.2f);
            review.transform.LookAt(new Vector3(18.5f, 3.2f, -12.8f));
            if (gameplay != DistrictCityPass.GameplaySignature() || collision != Collision()) throw new InvalidOperationException("Gameplay or collision signature changed unexpectedly");
            File.WriteAllText(Path.Combine(Evidence, "gameplay-after.json"), DistrictCityPass.GameplaySignature());
            File.WriteAllText(Path.Combine(Evidence, "collision-after.json"), Collision());
            AssetDatabase.SaveAssets(); StaticRenderChunksEditor.Rebuild(chunks); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.Combine(Evidence, "installation.json"), JsonConvert.SerializeObject(new { utc = DateTime.UtcNow, changes = Changes, gameplayPreserved = true, collidersPreserved = true, review = "Native review pending" }, Formatting.Indented));
        }
        static void InstallLighting()
        {
            var clock = Object.FindAnyObjectByType<CityTimeOfDay>();
            Changes.Add(new { originalProfile = AssetDatabase.GetAssetPath(clock.profile), originalSky = AssetDatabase.GetAssetPath(clock.timeAwareSky) });
            var profile = Object.Instantiate(clock.profile); profile.name = "Ward reference street daylight";
            var noon = profile.frames.Single(f => Mathf.Approximately(f.hour, 12));
            noon.keyEuler = new Vector3(38, 140, 0); noon.fillIntensity = .27f;
            noon.ambientSky = new Color(.43f, .51f, .62f); noon.ambientEquator = new Color(.46f, .43f, .37f); noon.ambientGround = new Color(.34f, .29f, .22f);
            noon.postExposure = -.18f;
            for (int i = 0; i < profile.frames.Length; i++) if (Mathf.Approximately(profile.frames[i].hour, 12)) profile.frames[i] = noon;
            if (!profile.IsValid(out string reason)) throw new InvalidDataException(reason);
            AssetDatabase.CreateAsset(profile, Folder + "/WardReferenceDaylight.asset");
            var sky = new Material(clock.timeAwareSky) { name = "Ward reference sky", shader = Shader.Find("Athen Hill/Ward Reference Sky") };
            sky.SetFloat("_CloudScale", 4.6f); sky.SetFloat("_CloudEdge", .055f); sky.SetFloat("_WispStrength", .035f); sky.SetFloat("_CloudOpacity", .88f);
            AssetDatabase.CreateAsset(sky, Folder + "/WardReferenceSky.mat");
            clock.profile = profile; clock.timeAwareSky = sky; EditorUtility.SetDirty(clock);
            // Keep the authored terrain-light orientation. Runtime clock suppresses its
            // baked directional terrain shadow weight when the reference sun turns.
        }

        [MenuItem("Athen Hill/Reference street/Audition localized mineral runoff")]
        public static void AddRunoff()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || scene.path != ImportBaseline.ScenePath || scene.isDirty) throw new InvalidOperationException("Open the saved city in Edit mode.");
            if (GameObject.Find("Reference street mineral runoff")) throw new InvalidOperationException("Keep existing film placements; do not duplicate them.");
            string dir = Folder + "/MineralRunoff"; Directory.CreateDirectory(dir);
            File.Copy(Path.Combine(Source, "textures/MineralRunoff/BaseColor.png"), dir + "/BaseColor.png", false);
            AssetDatabase.Refresh();
            var map = ImportMap(dir + "/BaseColor.png", true, false);
            var importer = (TextureImporter)AssetImporter.GetAtPath(dir + "/BaseColor.png");
            importer.wrapMode = TextureWrapMode.Clamp; importer.alphaSource = TextureImporterAlphaSource.FromInput; importer.alphaIsTransparency = true; importer.SaveAndReimport();
            var material = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "Reference mineral runoff", renderQueue = 3000 };
            material.SetTexture("_BaseMap", map); material.SetColor("_BaseColor", Color.white);
            material.SetFloat("_Surface", 1); material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            material.SetFloat("_ZWrite", 0); material.SetFloat("_Metallic", 0); material.SetFloat("_Smoothness", .03f);
            material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); material.SetOverrideTag("RenderType", "Transparent"); material.SetShaderPassEnabled("ShadowCaster", false);
            AssetDatabase.CreateAsset(material, dir + "/MineralRunoff.mat");
            var root = new GameObject("Reference street mineral runoff").transform;
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).GroupBy(PathOf).ToDictionary(g => g.Key, g => g.First());
            Changes.Clear(); Geometry("plaster-details.json", all, new Dictionary<string, Material> { ["MineralRunoff"] = material }, root);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.Combine(Evidence, "mineral-runoff-installation.json"), JsonConvert.SerializeObject(new { changes = Changes, separateTransparentRenderers = true, shadows = false, colliders = false, status = "Native audition pending" }, Formatting.Indented));
        }

        [MenuItem("Athen Hill/Reference street/Bake reviewed daylight reflections")]
        public static void BakeReflections()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Bake in Edit mode.");
            var clock = Object.FindAnyObjectByType<CityTimeOfDay>(); var frame = clock.profile.Evaluate(12);
            var keyRotation = clock.keyLight.transform.rotation; var keyColor = clock.keyLight.color; float keyIntensity = clock.keyLight.intensity;
            var fillColor = clock.skyFill.color; float fillIntensity = clock.skyFill.intensity;
            var sky = RenderSettings.skybox; var ambientMode = RenderSettings.ambientMode;
            var ambientSky = RenderSettings.ambientSkyColor; var equator = RenderSettings.ambientEquatorColor; var ground = RenderSettings.ambientGroundColor;
            var terrain = Shader.GetGlobalVector("_AthenTerrainTime");
            var results = new List<object>();
            try
            {
                clock.keyLight.transform.rotation = Quaternion.Euler(frame.keyEuler); clock.keyLight.color = frame.keyColor; clock.keyLight.intensity = frame.keyIntensity;
                clock.skyFill.color = frame.fillColor; clock.skyFill.intensity = frame.fillIntensity;
                RenderSettings.ambientMode = AmbientMode.Trilight; RenderSettings.ambientSkyColor = frame.ambientSky;
                RenderSettings.ambientEquatorColor = frame.ambientEquator; RenderSettings.ambientGroundColor = frame.ambientGround;
                var material = clock.timeAwareSky; RenderSettings.skybox = material;
                material.SetColor("_Zenith", frame.skyZenith); material.SetColor("_Middle", frame.skyMiddle); material.SetColor("_Horizon", frame.skyHorizon);
                material.SetColor("_CloudLight", frame.cloudLight); material.SetColor("_CloudShade", frame.cloudShade);
                material.SetFloat("_Exposure", frame.skyExposure); material.SetFloat("_SunVisibility", frame.sunVisibility);
                material.SetVector("_SunDirection", -clock.keyLight.transform.forward);
                Shader.SetGlobalVector("_AthenTerrainTime", new Vector4(1, 0, 0, 0));
                foreach (var binding in clock.reflections.probes)
                {
                    var probe = binding.probe;
                    string path = Folder + "/" + Safe(probe.name) + ".exr";
                    results.Add(new { probe.name, probe.resolution, originalMode = probe.mode.ToString(), originalCustom = AssetDatabase.GetAssetPath(probe.customBakedTexture), originalBaked = AssetDatabase.GetAssetPath(probe.bakedTexture), replacement = path });
                    if (!Lightmapping.BakeReflectionProbe(probe, path)) throw new InvalidOperationException("Reflection bake failed: " + probe.name);
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                    probe.customBakedTexture = AssetDatabase.LoadAssetAtPath<Cubemap>(path); probe.mode = ReflectionProbeMode.Custom;
                    if (!probe.customBakedTexture) throw new InvalidDataException("Missing saved cubemap: " + path);
                    if (binding.globalSky) { RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom; RenderSettings.customReflectionTexture = probe.customBakedTexture; }
                    EditorUtility.SetDirty(probe);
                }
                EditorUtility.SetDirty(material);
            }
            finally
            {
                clock.keyLight.transform.rotation = keyRotation; clock.keyLight.color = keyColor; clock.keyLight.intensity = keyIntensity;
                clock.skyFill.color = fillColor; clock.skyFill.intensity = fillIntensity;
                RenderSettings.skybox = sky; RenderSettings.ambientMode = ambientMode; RenderSettings.ambientSkyColor = ambientSky;
                RenderSettings.ambientEquatorColor = equator; RenderSettings.ambientGroundColor = ground;
                Shader.SetGlobalVector("_AthenTerrainTime", terrain);
            }
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene()); EditorSceneManager.SaveOpenScenes();
            File.WriteAllText(Path.Combine(Evidence, "reflection-bakes.json"), JsonConvert.SerializeObject(new { hour = 12, frame = JObject.Parse(JsonUtility.ToJson(frame)), probes = results }, Formatting.Indented));
        }
    }
}
