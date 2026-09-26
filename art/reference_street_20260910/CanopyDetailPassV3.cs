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
    // One explicit saved-scene source import. No runtime authoring or collider
    // changes. Keep this helper and the previous source assets for recovery.
    public static class CanopyDetailPassV3
    {
        const string Folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/CanopyV3";
        const string ParentPath = "Reference street thresholds and detail";
        const string AdditionName = "Canopy revision 20260910 v3";
        const string RetiredName = "Canopy revision 20260910";
        const string InstalledGuardsHash = "f0ee513cb962b14b8aa1334bf70752fef4ef9ca1b387ad40b6976c7967c55f2f";
        const string Template = "Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02/Materials/WardCloth.mat";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Source => Path.Combine(Repo, "art/reference_street_20260910/canopy-v3");
        static string Evidence => Path.Combine(Repo, "unity/evidence/reference-street/20260910/canopy-v3");
        sealed class Part
        {
            public string name, sourcePath, family, material;
            public float[][] positions, normals, uv;
            public int[] indices;
            public bool castsShadow = true;
        }
        static readonly List<object> Changes = new List<object>();
        static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t, null);
        static string Id(Object o) => o ? GlobalObjectId.GetGlobalObjectIdSlow(o).ToString() : null;
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
        static float[] Q(Quaternion q) => new[] { q.x, q.y, q.z, q.w };
        static Vector3 V(float[] v) => new Vector3(v[0], v[1], v[2]);
        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '_' ? c : '_').ToArray());
        static string Disk(string asset) => Path.GetFullPath(Path.Combine(Application.dataPath, "..", asset));
        static string Hash(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        static void WriteNew(string name, object data)
        {
            Directory.CreateDirectory(Evidence);
            string path = Path.Combine(Evidence, name);
            if (File.Exists(path)) throw new IOException("Preserve the prior canopy operation: " + path);
            File.WriteAllText(path, JsonConvert.SerializeObject(data, Formatting.Indented));
        }
        static IEnumerable<T> SceneComponents<T>() where T : Component =>
            SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<T>(true));
        static Dictionary<string, Transform> ScenePaths()
        {
            var groups = SceneComponents<Transform>().GroupBy(PathOf).ToArray();
            // Duplicate paths elsewhere in the city are tolerated, but every path
            // used by this import is resolved uniquely below.
            return groups.Where(g => g.Count() == 1).ToDictionary(g => g.Key, g => g.Single(), StringComparer.Ordinal);
        }
        static bool SourceVisible(StaticRenderChunks chunks, Renderer r)
        {
            int index = chunks.sources == null ? -1 : Array.IndexOf(chunks.sources, r);
            return chunks.editingSources || index < 0 ? r.enabled : chunks.sourceVisibility[index];
        }
        static object TransformData(Transform t, Transform retire = null)
        {
            if (!t) throw new InvalidOperationException("An existing transform was destroyed during canopy authoring.");
            return new { id = Id(t), parent = Id(t.parent), path = PathOf(t), t.name,
                activeSelf = t != retire && t.gameObject.activeSelf, activeInHierarchy = (!retire || (t != retire && !t.IsChildOf(retire))) && t.gameObject.activeInHierarchy,
                localPosition = V(t.localPosition), localRotation = Q(t.localRotation), localScale = V(t.localScale),
                worldMatrix = Enumerable.Range(0, 16).Select(i => t.localToWorldMatrix[i]).ToArray() };
        }
        static string TransformSignature(Transform[] preserved) => JsonConvert.SerializeObject(preserved.Select(t => TransformData(t)));
        static string PhysicsSignature() => JsonConvert.SerializeObject(SceneComponents<Collider>()
            .OrderBy(c => Id(c), StringComparer.Ordinal).Select(c => new { id = Id(c), path = PathOf(c.transform), type = c.GetType().FullName,
                data = EditorJsonUtility.ToJson(c), transform = TransformData(c.transform) }));
        static string ActorSignature()
        {
            var session = SceneComponents<GameSession>().Single();
            var walkers = SceneComponents<AmbientWalker>().OrderBy(w => PathOf(w.transform), StringComparer.Ordinal).ToArray();
            if (!session.player || session.npcs == null || session.npcs.Length != 4 || session.npcs.Any(n => !n) || walkers.Length != 4)
                throw new InvalidOperationException("Expected the existing one player, four talking actors and all four ambient walkers.");
            var roots = new[] { session.player.transform }.Concat(session.npcs.Select(n => n.transform)).Concat(walkers.Select(w => w.transform)).Distinct().OrderBy(PathOf, StringComparer.Ordinal).ToArray();
            return JsonConvert.SerializeObject(new {
                session = EditorJsonUtility.ToJson(session), existingGameplay = DistrictCityPass.GameplaySignature(),
                actors = roots.Select(root => new { root = PathOf(root), id = Id(root),
                    transforms = root.GetComponentsInChildren<Transform>(true).OrderBy(PathOf, StringComparer.Ordinal).Select(t => TransformData(t)).ToArray(),
                    components = root.GetComponentsInChildren<Component>(true).Where(c => c && !(c is Transform)).OrderBy(c => Id(c), StringComparer.Ordinal)
                        .Select(c => new { id = Id(c), type = c.GetType().FullName, data = EditorJsonUtility.ToJson(c) }).ToArray() }).ToArray(),
                allAmbientRoutes = walkers.Select(w => new { id = Id(w), path = PathOf(w.transform), data = EditorJsonUtility.ToJson(w),
                    actor = Id(w.actor), route = w.waypoints.Select(t => new { id = Id(t), transform = TransformData(t) }).ToArray() }).ToArray()
            });
        }
        static object RendererData(Renderer r, StaticRenderChunks chunks) => new {
            path = PathOf(r.transform), id = Id(r), sourceVisible = SourceVisible(chunks, r),
            active = r.gameObject.activeInHierarchy, meshPath = AssetDatabase.GetAssetPath(r.GetComponent<MeshFilter>().sharedMesh),
            meshGuid = AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(r.GetComponent<MeshFilter>().sharedMesh)),
            materials = r.sharedMaterials.Select(m => new { path = AssetDatabase.GetAssetPath(m), guid = AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(m)) }).ToArray(),
            shadowCasting = r.shadowCastingMode.ToString(), r.receiveShadows
        };
        static string SupportSignature(Dictionary<string, Transform> all, string[] paths, StaticRenderChunks chunks) =>
            JsonConvert.SerializeObject(paths.Select(p => RendererData(all[p].GetComponent<MeshRenderer>(), chunks)));
        static void RequireSavedCity()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating)
                throw new InvalidOperationException("Wait for the saved city to be ready in Edit mode.");
            var scene = SceneManager.GetActiveScene();
            if (scene.path != ImportBaseline.ScenePath || scene.isDirty)
                throw new InvalidOperationException("Open and save the authored Athen Hill scene before canopy installation.");
            for (int i = 0; i < SceneManager.sceneCount; i++)
                if (SceneManager.GetSceneAt(i).isDirty) throw new InvalidOperationException("Save unrelated scene work before the chunk rebuild's SaveOpenScenes operation.");
            if (Directory.Exists(Disk(Folder)) || SceneComponents<Transform>().Any(t => PathOf(t) == ParentPath + "/" + AdditionName))
                throw new InvalidOperationException("This canopy revision already exists. Preserve it and create a new revision instead of reapplying.");
        }
        static void ValidatePart(Part p)
        {
            if (p.positions == null || p.normals == null || p.uv == null || p.indices == null || p.positions.Length == 0 ||
                p.positions.Length != p.normals.Length || p.positions.Length != p.uv.Length || p.indices.Length % 3 != 0)
                throw new InvalidDataException("Invalid canopy buffers: " + p.name);
            bool Bad(float f) => float.IsNaN(f) || float.IsInfinity(f);
            if (p.positions.Any(v => v.Length != 3 || v.Any(Bad)) || p.normals.Any(v => v.Length != 3 || v.Any(Bad) || V(v).sqrMagnitude < .5f) ||
                p.uv.Any(v => v.Length != 2 || v.Any(Bad)) || p.indices.Any(i => i < 0 || i >= p.positions.Length))
                throw new InvalidDataException("Nonfinite or out-of-range canopy buffer: " + p.name);
            if (p.positions.Min(v => v[1]) <= 3.1f) throw new InvalidDataException("Canopy geometry violates the 3.1 m clearance guard.");
        }
        static Texture2D ExistingTexture(string path, bool normal)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!texture || importer == null || importer.textureType != (normal ? TextureImporterType.NormalMap : TextureImporterType.Default) || importer.sRGBTexture == normal)
                throw new InvalidDataException("Existing fabric texture import is not the expected colour/normal type: " + path);
            return texture;
        }
        static Dictionary<string, Material> CreateMaterials(JObject contract)
        {
            var template = AssetDatabase.LoadAssetAtPath<Material>(Template);
            if (!template || template.shader.name != "Universal Render Pipeline/Lit") throw new InvalidOperationException("Missing unchanged URP Lit cloth template.");
            var materials = new Dictionary<string, Material>(StringComparer.Ordinal);
            foreach (var property in ((JObject)contract["materials"]).Properties())
            {
                var item = (JObject)property.Value;
                if ((string)item["shader"] != "Universal Render Pipeline/Lit") throw new InvalidDataException("Unexpected canopy shader.");
                var m = new Material(template) { name = "Finery " + property.Name + " 20260910 v3", enableInstancing = true };
                m.shaderKeywords = Array.Empty<string>();
                foreach (string key in new[] { "_BaseMap", "_BumpMap", "_MetallicGlossMap", "_OcclusionMap", "_DetailNormalMap", "_DetailAlbedoMap", "_DetailMask", "_EmissionMap", "_ParallaxMap", "_SpecGlossMap" })
                    if (m.HasProperty(key)) m.SetTexture(key, null);
                var colour = item["baseColor"].Values<float>().ToArray();
                if (colour.Length != 4) throw new InvalidDataException("Invalid material colour.");
                m.SetColor("_BaseColor", new Color(colour[0], colour[1], colour[2], colour[3]));
                var baseMap = ExistingTexture((string)item["baseMap"], false);
                var normalMap = ExistingTexture((string)item["normalMap"], true);
                m.SetTexture("_BaseMap", baseMap); m.SetTextureScale("_BaseMap", baseMap ? Vector2.one / 7 : Vector2.one); m.SetTextureOffset("_BaseMap", Vector2.zero);
                m.SetTexture("_BumpMap", null); m.SetFloat("_BumpScale", 1);
                m.SetTexture("_DetailNormalMap", normalMap); m.SetFloat("_DetailNormalMapScale", (float?)item["normalScale"] ?? 1);
                m.SetFloat("_DetailAlbedoMapScale", 0); m.SetTextureScale("_DetailAlbedoMap", Vector2.one * 7); m.SetTextureOffset("_DetailAlbedoMap", Vector2.zero);
                m.SetFloat("_Metallic", (float)item["metallic"]); m.SetFloat("_Smoothness", (float)item["smoothness"]);
                m.SetFloat("_SmoothnessTextureChannel", 0); m.SetFloat("_Cull", (int)item["cull"]);
                m.SetFloat("_Surface", 0); m.SetFloat("_AlphaClip", 0); m.SetFloat("_ZWrite", 1);
                m.SetFloat("_SrcBlend", (float)BlendMode.One); m.SetFloat("_DstBlend", (float)BlendMode.Zero);
                m.SetColor("_EmissionColor", Color.black); m.SetOverrideTag("RenderType", "Opaque"); m.renderQueue = -1;
                // Match URP Lit's public validation. LitDetailGUI is internal, so its two
                // detail keyword rules are supplied explicitly after base/Lit validation.
                BaseShaderGUI.SetMaterialKeywords(m, UnityEditor.Rendering.Universal.ShaderGUI.LitGUI.SetMaterialKeywords, mat => {
                    mat.DisableKeyword("_DETAIL_MULX2");
                    CoreUtils.SetKeyword(mat, "_DETAIL_SCALED", mat.GetTexture("_DetailNormalMap") != null);
                });
                ValidateMaterial(m, item);
                AssetDatabase.CreateAsset(m, Folder + "/Materials/" + property.Name + ".mat");
                materials.Add(property.Name, m);
            }
            return materials;
        }
        static void InstallPart(Part p, int index, Dictionary<string, Transform> all, Transform addition, Dictionary<string, Material> materials, StaticRenderChunks chunks)
        {
            bool replacement = !string.IsNullOrEmpty(p.sourcePath);
            Transform t;
            object previous = null;
            if (replacement)
            {
                t = all[p.sourcePath]; previous = RendererData(t.GetComponent<MeshRenderer>(), chunks);
                Undo.RecordObjects(new Object[] { t.GetComponent<MeshFilter>(), t.GetComponent<MeshRenderer>() }, "Replace authored canopy visual");
            }
            else
            {
                var go = new GameObject(p.name); t = go.transform; t.SetParent(addition, false);
                go.AddComponent<MeshFilter>(); go.AddComponent<MeshRenderer>(); Undo.RegisterCreatedObjectUndo(go, "Add canopy construction detail");
            }
            var mesh = new Mesh { name = p.name + " source", indexFormat = IndexFormat.UInt32 };
            mesh.vertices = p.positions.Select(v => t.InverseTransformPoint(V(v))).ToArray();
            mesh.normals = p.normals.Select(n => t.localToWorldMatrix.transpose.MultiplyVector(V(n)).normalized).ToArray();
            mesh.uv = p.uv.Select(v => new Vector2(v[0], v[1])).ToArray(); mesh.triangles = p.indices;
            mesh.RecalculateTangents(); mesh.RecalculateBounds();
            string path = Folder + "/Meshes/" + index.ToString("D2") + "_" + Safe(p.name) + ".asset";
            AssetDatabase.CreateAsset(mesh, path);
            var filter = t.GetComponent<MeshFilter>(); var renderer = t.GetComponent<MeshRenderer>();
            filter.sharedMesh = mesh; renderer.sharedMaterials = new[] { materials[p.material] };
            renderer.enabled = true; renderer.shadowCastingMode = p.castsShadow ? ShadowCastingMode.On : ShadowCastingMode.Off; renderer.receiveShadows = true;
            EditorUtility.SetDirty(filter); EditorUtility.SetDirty(renderer);
            PrefabUtility.RecordPrefabInstancePropertyModifications(filter); PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
            Changes.Add(new { action = replacement ? "Replace mesh and material on retained source" : "Add visual-only detail", path = PathOf(t), previous,
                mesh = path, triangles = p.indices.Length / 3, material = AssetDatabase.GetAssetPath(materials[p.material]) });
        }

        static void ValidateMaterial(Material m, JToken item)
        {
            bool fabric = !string.IsNullOrEmpty((string)item["normalMap"]);
            if (m.shader.name != "Universal Render Pipeline/Lit" || m.GetTexture("_BumpMap") || m.IsKeywordEnabled("_NORMALMAP") ||
                m.GetTexture("_DetailAlbedoMap") || m.GetFloat("_DetailAlbedoMapScale") != 0 || m.IsKeywordEnabled("_DETAIL_MULX2") ||
                m.IsKeywordEnabled("_DETAIL_SCALED") != fabric || m.GetTextureScale("_DetailAlbedoMap") != Vector2.one * 7 ||
                m.GetTextureOffset("_DetailAlbedoMap") != Vector2.zero || m.GetTextureOffset("_BaseMap") != Vector2.zero)
                throw new InvalidDataException("Canopy material detail-only configuration did not survive validation: " + m.name);
            if (fabric && (AssetDatabase.GetAssetPath(m.GetTexture("_DetailNormalMap")) != (string)item["normalMap"] ||
                AssetDatabase.GetAssetPath(m.GetTexture("_BaseMap")) != (string)item["baseMap"] ||
                m.GetTextureScale("_BaseMap") != Vector2.one / 7 || Mathf.Abs(m.GetFloat("_DetailNormalMapScale") - (float)item["normalScale"]) > .00001f))
                throw new InvalidDataException("Canopy fabric texture scale or normal strength changed: " + m.name);
        }
        static void ValidateContract(JObject contract)
        {
            var colourScale = contract["textureScale"].Values<float>().ToArray();
            var detailScale = contract["detailScale"].Values<float>().ToArray();
            if (colourScale.Length != 2 || colourScale.Any(f => Mathf.Abs(f - 1f / 7) > .000001f) ||
                detailScale.Length != 2 || detailScale.Any(f => f != 7) || (float)contract["detailAlbedoScale"] != 0)
                throw new InvalidDataException("Expected 2.8 m colour tiles and 0.4 m detail weave contract.");
            foreach (var item in new[] { ("CanopyRed", .23f), ("CanopySeam", .21f), ("CanopyRepair", .19f) })
                if (Mathf.Abs((float)contract["materials"][item.Item1]["normalScale"] - item.Item2) > .00001f)
                    throw new InvalidDataException("Unexpected source fabric normal strength: " + item.Item1);
        }
        static void ValidateAssets(JObject guards)
        {
            foreach (var asset in ((JObject)guards["assets"]).Properties())
                if (Hash(Disk(asset.Name)) != (string)asset.Value["sha256"] || Hash(Disk(asset.Name) + ".meta") != (string)asset.Value["metaSha256"] ||
                    AssetDatabase.AssetPathToGUID(asset.Name) != (string)asset.Value["guid"])
                    throw new InvalidDataException("Retained V1/shared asset or importer changed: " + asset.Name);
        }
        static void ValidateWorldMatrix(Transform t, JToken expected)
        {
            var values = expected.Values<float>().ToArray();
            if (values.Length != 16 || Enumerable.Range(0, 16).Any(i => Mathf.Abs(t.localToWorldMatrix[i] - values[i]) > .00005f))
                throw new InvalidDataException("Installed canopy transform changed: " + PathOf(t));
        }
        static void ValidateInstalledV1(JObject guards, Dictionary<string, Transform> all, StaticRenderChunks chunks)
        {
            foreach (var file in ((JObject)guards["priorEvidence"]).Properties())
                if (Hash(Path.Combine(Repo, file.Name)) != (string)file.Value) throw new InvalidDataException("Retained V1 evidence changed: " + file.Name);
            ValidateAssets(guards);
            var sources = guards["sources"].ToArray();
            foreach (var role in ((JObject)guards["expectedRoles"]).Properties())
                if (sources.Count(g => (string)g["role"] == role.Name) != (int)role.Value) throw new InvalidDataException("Wrong V1 guard scope.");
            if (sources.Length != 38 || sources.Select(g => (string)g["path"]).Distinct().Count() != 38) throw new InvalidDataException("Expected 38 unique canopy source guards.");
            foreach (var guard in sources)
            {
                string path = (string)guard["path"];
                if (!all.TryGetValue(path, out var t) || !t.GetComponent<MeshFilter>() || !t.GetComponent<MeshRenderer>())
                    throw new InvalidDataException("Missing or ambiguous installed V1 source: " + path);
                var r = t.GetComponent<MeshRenderer>();
                if (AssetDatabase.GetAssetPath(t.GetComponent<MeshFilter>().sharedMesh) != (string)guard["meshPath"] ||
                    !r.sharedMaterials.Select(AssetDatabase.GetAssetPath).SequenceEqual(guard["materials"].Values<string>()) ||
                    (!string.IsNullOrEmpty((string)guard["rendererId"]) && Id(r) != (string)guard["rendererId"]))
                    throw new InvalidDataException("Expected installed V1 mesh/material/renderer identity: " + path);
                if (!t.gameObject.activeInHierarchy || SourceVisible(chunks, r) != (bool)guard["sourceVisible"])
                    throw new InvalidDataException("Expected V1 visibility including 24 already hidden originals: " + path);
                ValidateWorldMatrix(t, guard["worldMatrix"]);
                if ((r.bounds.min - V(guard["boundsMin"].Values<float>().ToArray())).magnitude > .003f ||
                    (r.bounds.max - V(guard["boundsMax"].Values<float>().ToArray())).magnitude > .003f)
                    throw new InvalidDataException("Installed V1 source bounds changed by more than 3 mm: " + path);
            }
        }
        static object MaterialEvidence(Material m) => new { path = AssetDatabase.GetAssetPath(m), shader = m.shader.name,
            keywords = m.shaderKeywords, baseMap = AssetDatabase.GetAssetPath(m.GetTexture("_BaseMap")),
            baseScale = new[] { m.GetTextureScale("_BaseMap").x, m.GetTextureScale("_BaseMap").y },
            bumpMap = AssetDatabase.GetAssetPath(m.GetTexture("_BumpMap")), detailNormal = AssetDatabase.GetAssetPath(m.GetTexture("_DetailNormalMap")),
            detailNormalScale = m.GetFloat("_DetailNormalMapScale"), detailAlbedoScale = m.GetFloat("_DetailAlbedoMapScale"),
            detailScale = new[] { m.GetTextureScale("_DetailAlbedoMap").x, m.GetTextureScale("_DetailAlbedoMap").y } };

        [MenuItem("Athen Hill/Reference street/Install Finery canopy V3 20260910")]
        public static void Apply()
        {
            RequireSavedCity();
            var scene = SceneManager.GetActiveScene();
            var chunks = SceneComponents<StaticRenderChunks>().Single();
            if (chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Rebuild and save existing source edits before this narrowly scoped pass.");
            var all = ScenePaths();
            if (!all.TryGetValue(ParentPath, out var parent) || !chunks.sourceRoots.Any(t => t && parent.IsChildOf(t)))
                throw new InvalidOperationException("The existing addition parent must already belong to a registered render source root.");
            string guardPath = Path.Combine(Source, "canopy-installed-v1-guards.json");
            if (Hash(guardPath) != InstalledGuardsHash) throw new InvalidDataException("Installed V1 guard record changed.");
            var guards = JObject.Parse(File.ReadAllText(guardPath));
            ValidateInstalledV1(guards, all, chunks);
            if (!all.TryGetValue(ParentPath + "/" + RetiredName, out var retired) || !retired.gameObject.activeSelf || retired.parent != parent ||
                retired.GetComponentsInChildren<Transform>(true).Length != 7 || retired.GetComponentsInChildren<MeshRenderer>(true).Length != 6 ||
                retired.GetComponentsInChildren<Collider>(true).Length != 0 || retired.GetComponentsInChildren<MonoBehaviour>(true).Length != 0)
                throw new InvalidDataException("Expected the intact active V1 visual-only addition parent and six details.");
            ValidateWorldMatrix(retired, guards["retiredParentWorldMatrix"]);
            var contract = JObject.Parse(File.ReadAllText(Path.Combine(Source, "canopy-material-contract-v3.json")));
            var authored = JObject.Parse(File.ReadAllText(Path.Combine(Source, "canopy-authoring-manifest-v3.json")));
            foreach (string name in new[] { "canopy-parts-v3.json", "canopy-material-contract-v3.json" })
                if (Hash(Path.Combine(Source, name)) != (string)authored["files"][name]) throw new InvalidDataException("Authored V3 canopy source changed: " + name);
            ValidateContract(contract);
            var parts = JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source, "canopy-parts-v3.json")));
            if (parts.Length != 9 || parts.Count(p => !string.IsNullOrEmpty(p.sourcePath)) != 3 || parts.Sum(p => p.indices.Length / 3) != (int)authored["geometry"]["triangles"])
                throw new InvalidDataException("Expected nine canopy parts and exactly three V1 source replacements with the authored triangle count.");
            foreach (var p in parts) ValidatePart(p);
            var obsolete = contract["disableObsoleteSourcePaths"].Values<string>().ToArray();
            var preserve = contract["preserveSourcePaths"].Values<string>().ToArray();
            bool MatchesRole(IEnumerable<string> paths, string role) => paths.OrderBy(p => p, StringComparer.Ordinal).SequenceEqual(
                guards["sources"].Where(g => (string)g["role"] == role).Select(g => (string)g["path"]).OrderBy(p => p, StringComparer.Ordinal));
            if (!MatchesRole(parts.Where(p => !string.IsNullOrEmpty(p.sourcePath)).Select(p => p.sourcePath), "replacement") ||
                !MatchesRole(obsolete, "obsolete") || !MatchesRole(preserve, "support")) throw new InvalidDataException("V3 scope diverges from installed V1 source guards.");
            foreach (var prop in ((JObject)contract["materials"]).Properties())
            {
                ExistingTexture((string)prop.Value["baseMap"], false); ExistingTexture((string)prop.Value["normalMap"], true);
            }
            if (parts.Any(p => contract["materials"][p.material] == null)) throw new InvalidDataException("Missing authored material recipe.");
            var preservedTransforms = SceneComponents<Transform>().Where(t => !chunks.generatedRoot || !t.IsChildOf(chunks.generatedRoot)).OrderBy(t => Id(t), StringComparer.Ordinal).ToArray();
            string beforeTransforms = TransformSignature(preservedTransforms);
            // Exactly one existing activeSelf change is authorized. Its six descendants
            // necessarily become inactiveInHierarchy, but their own activeSelf is preserved.
            string expectedTransforms = JsonConvert.SerializeObject(preservedTransforms.Select(t => TransformData(t, retired)));
            string physics = PhysicsSignature(), actors = ActorSignature(), supports = SupportSignature(all, preserve, chunks);
            string obsoleteState = SupportSignature(all, obsolete, chunks);
            Directory.CreateDirectory(Evidence);
            string backup = Path.Combine(Evidence, "before-canopy-v3.unity");
            if (File.Exists(backup)) throw new IOException("Preserve the earlier canopy attempt before preparing another revision.");
            File.Copy(Disk(scene.path), backup, false);
            WriteNew("before-canopy-v3.json", new { utc = DateTime.UtcNow, scene = scene.path, savedSceneSha256 = Hash(backup),
                sourceGuardsSha256 = Hash(guardPath), authoringManifestSha256 = Hash(Path.Combine(Source, "canopy-authoring-manifest-v3.json")),
                transforms = JToken.Parse(beforeTransforms), expectedTransforms = JToken.Parse(expectedTransforms), physics = JToken.Parse(physics),
                actors = JToken.Parse(actors), supports = JToken.Parse(supports), obsolete = JToken.Parse(obsoleteState), retainedAssets = guards["assets"] });
            Directory.CreateDirectory(Disk(Folder + "/Meshes")); Directory.CreateDirectory(Disk(Folder + "/Materials"));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var materials = CreateMaterials(contract);
            Changes.Clear(); Undo.IncrementCurrentGroup(); int undoGroup = Undo.GetCurrentGroup(); Undo.SetCurrentGroupName("Finery canopy V3 20260910");
            bool wasEditing = chunks.editingSources;
            try
            {
                chunks.ShowSources(true);
                Undo.RecordObject(retired.gameObject, "Retain V1 canopy additions inactive"); retired.gameObject.SetActive(false); EditorUtility.SetDirty(retired.gameObject);
                Changes.Add(new { action = "Deactivate V1 addition parent; retain all six source meshes/materials", path = PathOf(retired), previousActiveSelf = true, activeSelf = false });
                var addition = new GameObject(AdditionName); addition.transform.SetParent(parent, false); Undo.RegisterCreatedObjectUndo(addition, "Create V3 canopy detail group");
                for (int i = 0; i < parts.Length; i++) InstallPart(parts[i], i, all, addition.transform, materials, chunks);
                if (TransformSignature(preservedTransforms) != expectedTransforms || PhysicsSignature() != physics || ActorSignature() != actors ||
                    SupportSignature(all, preserve, chunks) != supports || SupportSignature(all, obsolete, chunks) != obsoleteState)
                    throw new InvalidOperationException("Canopy V3 altered an existing transform beyond retiring V1 additions, collider, actor, route, hidden original or retained support; do not save.");
                ValidateAssets(guards);
                foreach (var material in materials) ValidateMaterial(material.Value, contract["materials"][material.Key]);
            }
            catch (Exception e)
            {
                Undo.RevertAllDownToGroup(undoGroup); chunks.ShowSources(wasEditing);
                WriteNew("installation-source-failure.json", new { utc = DateTime.UtcNow, error = e.ToString(), backup,
                    recovery = "Source Undo was attempted before chunk mutation. Newly prepared assets are intentionally retained; inspect the current scene and use a new revision for another attempt." });
                throw;
            }
            Undo.CollapseUndoOperations(undoGroup);
            // Chunk outputs are disposable and not covered by source Undo. The exact
            // saved pre-pass scene and all V1 source assets remain available for recovery.
            StaticRenderChunksEditor.Rebuild(chunks); AssetDatabase.SaveAssets(); EditorSceneManager.SaveScene(scene);
            bool transformsOk = TransformSignature(preservedTransforms) == expectedTransforms, physicsOk = PhysicsSignature() == physics,
                actorsOk = ActorSignature() == actors, supportsOk = SupportSignature(all, preserve, chunks) == supports,
                obsoleteOk = SupportSignature(all, obsolete, chunks) == obsoleteState, retiredOk = !retired.gameObject.activeSelf,
                fresh = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            ValidateAssets(guards);
            foreach (var material in materials) ValidateMaterial(material.Value, contract["materials"][material.Key]);
            WriteNew("installation-v3.json", new { utc = DateTime.UtcNow, scene = scene.path, sceneSha256 = Hash(Disk(scene.path)),
                changes = Changes, triangles = parts.Sum(p => p.indices.Length / 3), sourceParts = parts.Length, materials = materials.Values.Select(MaterialEvidence).ToArray(),
                checks = new { existingTransformsPreservedExceptV1AdditionActiveState = transformsOk, allColliderSerializedDataPreserved = physicsOk,
                    playerFourNpcAndFourWalkersPreserved = actorsOk, allFiveSupportsPreserved = supportsOk, all24ObsoleteOriginalsRemainHidden = obsoleteOk,
                    oldAdditionParentRetainedInactive = retiredOk, all49RetainedAssetsAndImportersPreserved = true, detailMaterialContractVerified = true, chunksFresh = fresh },
                sourceFingerprint = chunks.sourceFingerprint, backup, runtimeMotion = (string)contract["runtimeMotion"],
                pending = "Native matched top/underside/hem views, sun/shade, weave/moire, attachment contact, real-input access, temporal stability, performance and independent critic acceptance remain unverified." });
            if (!transformsOk || !physicsOk || !actorsOk || !supportsOk || !obsoleteOk || !retiredOk || !fresh)
                throw new InvalidOperationException("Post-rebuild invariant mismatch. Inspect the report and preserved scene before further work; this pass is not accepted.");
        }
    }
}
#endif
