using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// Non-destructive environment beauty pass. Gameplay collision, landmarks, NPC roots,
    /// and walker routes are deliberately untouched; all added geometry is render-only.
    /// </summary>
    public static class AAAEnvironmentPass
    {
        const string TextureRoot = "Assets/AthenHill/Art/Textures/AAA/";
        const string MaterialRoot = "Assets/AthenHill/Materials/AAA/";
        const string VolumePath = "Assets/AthenHill/Materials/AAA/AthenHillBeautyVolume.asset";
        static readonly Regex ShopPrefix = new Regex(@"^(BLD_shop_[ew]_\d\d)", RegexOptions.Compiled);

        [MenuItem("Athen Hill/Beauty/Apply AAA environment pass")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play Mode first.");
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            Directory.CreateDirectory(MaterialRoot);
            AssetDatabase.Refresh();

            PrepareTexture("Paving_Albedo.png", false, 8);
            PrepareTexture("WallStone_Albedo.png", false, 8);
            PrepareTexture("Gunmetal_Albedo.png", false, 8);
            PrepareTexture("Paving_NormalSource.png", true, 8, .12f);
            PrepareTexture("WallStone_NormalSource.png", true, 8, .09f);
            PrepareTexture("Gunmetal_NormalSource.png", true, 8, .07f);

            var paving = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/Paving.mat");
            ConfigureLit(paving, "Paving_Albedo.png", "Paving_NormalSource.png", new Vector2(20, 15), 0f, .17f);

            var stone = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/World/MAT_stone.mat");
            var metal = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/World/MAT_metal.mat");
            ConfigureGltf(stone, "WallStone_Albedo.png", "WallStone_NormalSource.png", 0f, .82f);
            ConfigureGltf(metal, "Gunmetal_Albedo.png", "Gunmetal_NormalSource.png", .28f, .68f);

            var plaza = CreateOrLoadLit("PlazaPaving", new Color(.78f, .70f, .59f), .12f);
            ConfigureLit(plaza, "Paving_Albedo.png", "Paving_NormalSource.png", new Vector2(3.3f, 1.4f), 0f, .14f);
            var trim = CreateOrLoadLit("ArchitecturalGunmetal", new Color(.31f, .33f, .34f), .34f);
            ConfigureLit(trim, "Gunmetal_Albedo.png", "Gunmetal_NormalSource.png", new Vector2(1.6f, 1.6f), .34f, .49f);
            ConfigureWardGuardMaterial();

            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (!chunks) throw new InvalidOperationException("City Render Chunks is missing.");
            // Local cells let the camera reject streets and facades behind the player.
            // The previous 64x128 m cells merged almost the whole city per material and
            // defeated otherwise-free frustum culling in the gate approach.
            chunks.cellSize = 64f;
            chunks.cellDepth = 128f;
            // Reveal sources before changing visibility; otherwise ShowSources(true) inside
            // Rebuild would restore the legacy grid from its previous visibility snapshot.
            chunks.ShowSources(true);
            CullSubpixelTreeGeometry();
            DisableLegacyJointGrid();
            RebuildDressing(stone, metal, plaza, trim);
            ConfigureShadowBudget(metal);
            ConfigureLightingAndPost();

            StaticRenderChunksEditor.Rebuild(chunks);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            // The SSAO feature allocates camera resources on its first offscreen render.
            // Warm the first camera so the saved review frame is representative.
            PortDiagnostics.Capture("cam_hill");
            PortDiagnostics.Capture("cam_hill");
            PortDiagnostics.Capture("cam_avenue");
            PortDiagnostics.Capture("cam_gate");
            PortDiagnostics.Snapshot();
            Debug.Log("AAA environment pass applied, chunks rebuilt, and hero cameras captured.");
        }

        static void PrepareTexture(string file, bool normal, int anisotropy, float bump = .1f)
        {
            var path = TextureRoot + file;
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (!importer) throw new FileNotFoundException("Missing beauty texture", path);
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.convertToNormalmap = normal;
            importer.heightmapScale = bump;
            importer.sRGBTexture = !normal;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.mipmapEnabled = true;
            importer.streamingMipmaps = true;
            importer.anisoLevel = anisotropy;
            importer.maxTextureSize = 2048;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
        }

        static Texture2D Texture(string file) => AssetDatabase.LoadAssetAtPath<Texture2D>(TextureRoot + file);

        static void ConfigureLit(Material material, string albedo, string normal, Vector2 tiling, float metallic, float smoothness)
        {
            if (!material) throw new InvalidOperationException("Required Lit material missing.");
            material.SetTexture("_BaseMap", Texture(albedo));
            material.SetTextureScale("_BaseMap", tiling);
            material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_BumpMap", Texture(normal));
            material.SetTextureScale("_BumpMap", tiling);
            material.EnableKeyword("_NORMALMAP");
            material.SetFloat("_BumpScale", .72f);
            material.SetFloat("_Metallic", metallic);
            material.SetFloat("_Smoothness", smoothness);
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
        }

        static void ConfigureGltf(Material material, string albedo, string normal, float metallic, float roughness)
        {
            if (!material) throw new InvalidOperationException("Required glTF material missing.");
            material.SetTexture("baseColorTexture", Texture(albedo));
            material.SetTexture("normalTexture", Texture(normal));
            material.SetColor("baseColorFactor", Color.white);
            material.SetFloat("normalTexture_scale", .62f);
            material.SetFloat("metallicFactor", metallic);
            material.SetFloat("roughnessFactor", roughness);
            material.EnableKeyword("_NORMALMAP");
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
        }

        static void ConfigureWardGuardMaterial()
        {
            const string modelPath = "Assets/AthenHill/Art/Imported/Meshy/ward-guard.glb";
            const string materialPath = "Assets/AthenHill/Materials/Actors/MAT_ward_guard.mat";
            var source = AssetDatabase.LoadAllAssetsAtPath(modelPath).OfType<Material>().FirstOrDefault();
            if (!source) return;
            var material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if (!material)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "MAT_ward_guard" };
                AssetDatabase.CreateAsset(material, materialPath);
            }
            var albedo = source.GetTexture("baseColorTexture") ?? source.GetTexture("_BaseMap") ?? source.mainTexture;
            var normal = source.GetTexture("normalTexture") ?? source.GetTexture("_BumpMap");
            material.SetTexture("_BaseMap", albedo);
            material.SetTexture("_BumpMap", normal);
            material.SetColor("_BaseColor", new Color(.62f, .66f, .59f, 1f));
            material.SetFloat("_Metallic", .08f);
            material.SetFloat("_Smoothness", .28f);
            if (normal) material.EnableKeyword("_NORMALMAP");
            EditorUtility.SetDirty(material);

            foreach (var npc in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.None))
                foreach (var renderer in npc.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (renderer.transform.root.name == npc.name || renderer.GetComponentInParent<ActorAnimation>()?.name == "WardGuard")
                        renderer.sharedMaterial = material;
        }

        static Material CreateOrLoadLit(string name, Color tint, float smoothness)
        {
            var path = MaterialRoot + name + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!material)
            {
                material = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name };
                AssetDatabase.CreateAsset(material, path);
            }
            material.SetColor("_BaseColor", tint);
            material.SetFloat("_Smoothness", smoothness);
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        static void DisableLegacyJointGrid()
        {
            var root = GameObject.Find("Paving Joints");
            if (!root) return;
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true)) renderer.enabled = false;
        }

        static void RebuildDressing(Material stone, Material metal, Material plaza, Material trim)
        {
            var world = GameObject.Find("AuthoredWorld");
            if (!world) throw new InvalidOperationException("AuthoredWorld is missing.");
            var old = world.transform.Find("AAA Environment Dressing");
            if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
            var root = new GameObject("AAA Environment Dressing");
            root.transform.SetParent(world.transform, false);

            // Ground zoning: a framed civic plaza and transverse service bands interrupt
            // the former full-screen graph while remaining millimetres above gameplay ground.
            Quad(root.transform, "Plaza inset north", new Vector3(4, .012f, -13.1f), new Vector3(25, .018f, 4.2f), plaza);
            Quad(root.transform, "Plaza inset south", new Vector3(4, .013f, 13.1f), new Vector3(25, .018f, 4.2f), plaza);
            Quad(root.transform, "Plaza inset west", new Vector3(-10.6f, .014f, 0), new Vector3(4.2f, .018f, 22), plaza);
            Quad(root.transform, "Plaza inset east", new Vector3(18.6f, .015f, 0), new Vector3(4.2f, .018f, 22), plaza);
            foreach (var z in new[] { -29f, -20f, 20f, 29f })
                Quad(root.transform, "Avenue service band", new Vector3(4, .019f, z), new Vector3(44, .024f, .22f), trim);

            // Each shop receives a different roof silhouette and human-scale facade rhythm.
            var sourceRenderers = world.GetComponentsInChildren<MeshRenderer>(true)
                .Where(r => !r.transform.IsChildOf(root.transform)).ToArray();
            var shops = sourceRenderers.Select(r => new { renderer = r, match = ShopPrefix.Match(r.name) })
                .Where(x => x.match.Success).GroupBy(x => x.match.Groups[1].Value).OrderBy(g => g.Key).ToArray();
            for (var index = 0; index < shops.Length; index++)
            {
                var renderers = shops[index].Select(x => x.renderer).ToArray();
                var roof = renderers.Where(r => r.name.Contains("_roof_cap")).Select(r => r.bounds).ToArray();
                var recess = renderers.Where(r => r.name.Contains("_dark_recess")).Select(r => r.bounds).ToArray();
                if (roof.Length == 0 || recess.Length == 0) continue;
                AddShopDetails(root.transform, shops[index].Key, Combine(roof), Combine(recess), index, metal, stone, trim);
            }

            AddHillGrounding(root.transform, stone, metal);
            AddStreetClusters(root.transform, metal, trim);
        }

        static Bounds Combine(IReadOnlyList<Bounds> bounds)
        {
            var combined = bounds[0];
            for (var i = 1; i < bounds.Count; i++) combined.Encapsulate(bounds[i]);
            return combined;
        }

        static void AddShopDetails(Transform root, string name, Bounds roof, Bounds recess, int index, Material metal, Material stone, Material trim)
        {
            var towardCentre = recess.center.x > 0 ? -1f : 1f;
            var faceX = recess.center.x + towardCentre * (recess.extents.x + .035f);
            var facadeHeight = Mathf.Min(2.8f, recess.size.y * .82f);
            for (var i = -1; i <= 1; i += 2)
                Quad(root, name + " facade rib", new Vector3(faceX, recess.center.y, recess.center.z + i * recess.extents.z * .82f), new Vector3(.16f, facadeHeight, .16f), trim);

            var roofY = roof.max.y + .08f;
            if (index % 3 == 0)
            {
                Quad(root, name + " roof service tower", new Vector3(roof.center.x, roofY + .43f, roof.center.z), new Vector3(1.45f, .86f, 1.25f), metal);
                Quad(root, name + " tower stone cap", new Vector3(roof.center.x, roofY + .9f, roof.center.z), new Vector3(1.72f, .11f, 1.5f), stone);
            }
            else if (index % 3 == 1)
            {
                Quad(root, name + " roof machinery", new Vector3(roof.center.x, roofY + .22f, roof.center.z - .45f), new Vector3(2.2f, .44f, .85f), metal);
                Quad(root, name + " exhaust", new Vector3(roof.center.x + .45f, roofY + .68f, roof.center.z + .35f), new Vector3(.26f, 1.15f, .26f), trim);
            }
            else
            {
                Quad(root, name + " asymmetric crown", new Vector3(roof.center.x + towardCentre * .28f, roofY + .34f, roof.center.z + .55f), new Vector3(1.05f, .68f, 1.65f), stone);
                Quad(root, name + " crown spine", new Vector3(roof.center.x, roofY + .79f, roof.center.z + .55f), new Vector3(.20f, 1.05f, .22f), trim);
            }
        }

        static void AddHillGrounding(Transform root, Material stone, Material metal)
        {
            // Low render-only stones visually knit the tree roots into the raised garden.
            var positions = new[]
            {
                new Vector3(.1f,1.54f,-2.9f), new Vector3(7.4f,1.54f,-3.4f),
                new Vector3(9.1f,1.54f,1.7f), new Vector3(6.8f,1.54f,5.1f),
                new Vector3(1.0f,1.54f,4.8f), new Vector3(-1.4f,1.54f,1.1f)
            };
            for (var i = 0; i < positions.Length; i++)
            {
                var rock = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                rock.name = "Hill root stone";
                rock.transform.SetParent(root, true);
                rock.transform.position = positions[i];
                rock.transform.localScale = new Vector3(.5f + (i % 3) * .14f, .18f + (i % 2) * .07f, .38f + ((i + 1) % 3) * .12f);
                rock.transform.rotation = Quaternion.Euler(0, i * 47f, 0);
                UnityEngine.Object.DestroyImmediate(rock.GetComponent<Collider>());
                rock.GetComponent<MeshRenderer>().sharedMaterial = stone;
            }
            // Four compact bench/utility clusters turn the plaza perimeter into a social place.
            foreach (var p in new[] { new Vector3(-3.4f,1.72f,-5.8f), new Vector3(11.5f,1.72f,5.7f) })
            {
                Quad(root, "Plaza bench seat", p, new Vector3(2.1f,.16f,.48f), metal);
                Quad(root, "Plaza bench leg", p + new Vector3(-.72f,-.25f,0), new Vector3(.18f,.5f,.4f), metal);
                Quad(root, "Plaza bench leg", p + new Vector3(.72f,-.25f,0), new Vector3(.18f,.5f,.4f), metal);
            }
        }

        static void AddStreetClusters(Transform root, Material metal, Material trim)
        {
            // Deliberately off the route centre lines: silhouettes and density without
            // introducing invisible collision or interfering with interaction approach.
            var anchors = new[]
            {
                new Vector3(-19.6f,.34f,-10.5f), new Vector3(-19.1f,.26f,8.8f),
                new Vector3(27.2f,.34f,-9.2f), new Vector3(26.7f,.26f,10.6f)
            };
            for (var i = 0; i < anchors.Length; i++)
            {
                Quad(root, "Street cargo crate", anchors[i], new Vector3(.85f,.68f,.75f), metal);
                Quad(root, "Street cargo crate small", anchors[i] + new Vector3(.55f,-.09f,.46f), new Vector3(.48f,.5f,.44f), trim);
                Quad(root, "Street bollard", anchors[i] + new Vector3(-.72f,.16f,-.38f), new Vector3(.16f,1f,.16f), trim);
            }
        }

        static GameObject Quad(Transform parent, string name, Vector3 worldPosition, Vector3 worldScale, Material material)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, true);
            go.transform.position = worldPosition;
            go.transform.localScale = worldScale;
            UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = ShadowCastingMode.On;
            renderer.receiveShadows = true;
            return go;
        }

        static void ConfigureShadowBudget(Material proxyMaterial)
        {
            // Animated NPC shadow passes were duplicating ~54k triangles in the wide
            // plaza views. SSAO/contact shading keeps them grounded; reserve authored
            // realtime shadows for the player and architectural silhouettes.
            foreach (var npc in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.None))
                foreach (var renderer in npc.GetComponentsInChildren<Renderer>(true))
                    renderer.shadowCastingMode = ShadowCastingMode.Off;
            foreach (var walker in UnityEngine.Object.FindObjectsByType<AmbientWalker>(FindObjectsSortMode.None))
                foreach (var renderer in walker.GetComponentsInChildren<Renderer>(true))
                    renderer.shadowCastingMode = ShadowCastingMode.Off;

            // The detailed player mesh is always close to the camera and was therefore
            // replayed into every cascade. A capsule preserves the readable grounding
            // shadow for a fraction of the triangle cost, while the visible mesh stays
            // completely unchanged.
            var player = UnityEngine.Object.FindAnyObjectByType<PlayerMotor>();
            if (player)
            {
                foreach (var old in player.GetComponentsInChildren<Renderer>(true))
                    old.shadowCastingMode = ShadowCastingMode.Off;
                var previous = player.transform.Find("Player shadow proxy");
                if (previous) UnityEngine.Object.DestroyImmediate(previous.gameObject);
                var proxy = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                proxy.name = "Player shadow proxy";
                proxy.transform.SetParent(player.transform, false);
                proxy.transform.localPosition = new Vector3(0f, .9f, 0f);
                proxy.transform.localScale = new Vector3(.42f, .9f, .42f);
                UnityEngine.Object.DestroyImmediate(proxy.GetComponent<Collider>());
                var proxyRenderer = proxy.GetComponent<MeshRenderer>();
                proxyRenderer.sharedMaterial = proxyMaterial;
                proxyRenderer.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                proxyRenderer.receiveShadows = false;
            }

            // Replace the thousands of architectural/tree shadow triangles with a small
            // authored proxy set. The visible meshes retain their full detail while the
            // sun sees only broad silhouette masses.
            var world = GameObject.Find("AuthoredWorld");
            if (world)
            {
                var dressing = world.transform.Find("AAA Environment Dressing");
                if (!dressing) return;
                foreach (var renderer in world.GetComponentsInChildren<MeshRenderer>(true))
                    renderer.shadowCastingMode = ShadowCastingMode.Off;

                var architectural = world.GetComponentsInChildren<MeshRenderer>(true)
                    .Where(r => !r.transform.IsChildOf(dressing) && !r.name.StartsWith("COL_")).ToArray();
                var shopGroups = architectural.Select(r => new { renderer = r, match = ShopPrefix.Match(r.name) })
                    .Where(x => x.match.Success && x.renderer.name.Contains("_rear_mass"))
                    .GroupBy(x => x.match.Groups[1].Value);
                foreach (var group in shopGroups)
                {
                    var bounds = Combine(group.Select(x => x.renderer.bounds).ToArray());
                    ShadowCube(dressing, "Shop shadow proxy", bounds.center, bounds.size * .94f, Quaternion.identity, proxyMaterial);
                }
                foreach (var renderer in architectural.Where(r => r.name.StartsWith("BLD_west_wall")))
                    ShadowCube(dressing, "Wall shadow proxy", renderer.bounds.center, renderer.bounds.size * .96f, Quaternion.identity, proxyMaterial);
                var hallParts = architectural.Where(r => r.name.IndexOf("vanguard", StringComparison.OrdinalIgnoreCase) >= 0).ToArray();
                if (hallParts.Length > 0)
                {
                    var hall = Combine(hallParts.Select(r => r.bounds).ToArray());
                    ShadowCube(dressing, "Hall shadow proxy", hall.center, hall.size * .88f, Quaternion.identity, proxyMaterial);
                }
                ShadowCylinder(dressing, "Tree trunk shadow proxy", new Vector3(4f, 6.2f, 0), new Vector3(1.45f, 5.8f, 1.45f), proxyMaterial);
                ShadowCube(dressing, "Tree branch shadow proxy", new Vector3(2.2f, 10.2f, 0), new Vector3(1.1f, 7.2f, 1.1f), Quaternion.Euler(0, 0, -38f), proxyMaterial);
                ShadowCube(dressing, "Tree branch shadow proxy", new Vector3(6.1f, 10.7f, .4f), new Vector3(1.05f, 7.6f, 1.05f), Quaternion.Euler(12f, 0, 34f), proxyMaterial);
            }
        }

        static void CullSubpixelTreeGeometry()
        {
            var world = GameObject.Find("AuthoredWorld");
            if (!world) return;
            foreach (var renderer in world.GetComponentsInChildren<MeshRenderer>(true))
            {
                // Preserve the trunk, roots, leaf sprays and the complete primary crown.
                // These tiny paired twigs are sub-pixel at the gameplay camera but cost
                // thousands of repeated triangles once lighting passes are included.
                if (renderer.name.StartsWith("TREE_twig", StringComparison.Ordinal) ||
                    (renderer.name.StartsWith("TREE_secondary", StringComparison.Ordinal) && renderer.name.EndsWith("_-1", StringComparison.Ordinal)) ||
                    (renderer.name.StartsWith("TREE_secondary_0", StringComparison.Ordinal) &&
                     (renderer.name.Contains("_04_") || renderer.name.Contains("_05_") || renderer.name.Contains("_06_"))) ||
                    renderer.name.StartsWith("TREE_dead_tip", StringComparison.Ordinal) ||
                    renderer.name == "TREE_scaffold_04" ||
                    renderer.name == "TREE_scaffold_05" || renderer.name == "TREE_scaffold_06")
                    renderer.enabled = false;
            }
        }

        static void ShadowCube(Transform parent, string name, Vector3 position, Vector3 scale, Quaternion rotation, Material material)
        {
            var go = Quad(parent, name, position, scale, material);
            go.transform.rotation = rotation;
            go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.ShadowsOnly;
        }

        static void ShadowCylinder(Transform parent, string name, Vector3 position, Vector3 scale, Material material)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            go.name = name;
            go.transform.SetParent(parent, true);
            go.transform.position = position;
            go.transform.localScale = scale;
            UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
            renderer.receiveShadows = false;
        }

        static void ConfigureLightingAndPost()
        {
            if (GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset pipeline)
            {
                pipeline.shadowDistance = 18f;
                EditorUtility.SetDirty(pipeline);
            }
            var sun = GameObject.Find("Sun")?.GetComponent<Light>();
            if (sun)
            {
                sun.intensity = 1.62f;
                sun.color = new Color(1f, .86f, .69f);
                sun.shadowStrength = .92f;
                sun.shadowBias = .035f;
                sun.shadowNormalBias = .28f;
            }
            var fill = GameObject.Find("Sky fill")?.GetComponent<Light>();
            if (fill) fill.intensity = .18f;
            RenderSettings.ambientSkyColor = new Color(.43f, .49f, .56f);
            RenderSettings.ambientEquatorColor = new Color(.48f, .39f, .29f);
            RenderSettings.ambientGroundColor = new Color(.20f, .17f, .14f);
            RenderSettings.reflectionIntensity = .82f;
            RenderSettings.fogColor = new Color(.69f, .55f, .39f);
            RenderSettings.fogStartDistance = 38f;
            RenderSettings.fogEndDistance = 145f;

            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(VolumePath);
            if (!profile)
            {
                profile = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profile, VolumePath);
            }
            foreach (var child in AssetDatabase.LoadAllAssetsAtPath(VolumePath).Where(o => o && o != profile).ToArray())
                UnityEngine.Object.DestroyImmediate(child, true);
            profile.components.Clear();
            var tone = AddPersistent<Tonemapping>(profile); tone.mode.Override(TonemappingMode.ACES);
            var color = AddPersistent<ColorAdjustments>(profile);
            color.postExposure.Override(-.38f); color.contrast.Override(18f); color.saturation.Override(-5f);
            color.colorFilter.Override(new Color(1f, .96f, .90f));
            var bloom = AddPersistent<Bloom>(profile);
            bloom.intensity.Override(.22f); bloom.threshold.Override(1.15f); bloom.scatter.Override(.58f);
            var vignette = AddPersistent<Vignette>(profile);
            vignette.intensity.Override(.13f); vignette.smoothness.Override(.72f);
            EditorUtility.SetDirty(profile);

            var volumeObject = GameObject.Find("AAA Global Volume") ?? new GameObject("AAA Global Volume");
            var volume = volumeObject.GetComponent<Volume>() ?? volumeObject.AddComponent<Volume>();
            volume.isGlobal = true; volume.priority = 20f; volume.sharedProfile = profile;
            foreach (var camera in UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                camera.farClipPlane = 100f;
                var data = camera.GetUniversalAdditionalCameraData();
                data.renderPostProcessing = true;
                data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
                data.antialiasingQuality = AntialiasingQuality.High;
            }

            var rendererData = AssetDatabase.LoadAssetAtPath<UniversalRendererData>("Assets/Settings/PC_Renderer.asset");
            if (rendererData)
            {
                var feature = AssetDatabase.LoadAllAssetsAtPath("Assets/Settings/PC_Renderer.asset")
                    .OfType<ScriptableRendererFeature>().FirstOrDefault(x => x.GetType().Name.Contains("ScreenSpaceAmbientOcclusion"));
                if (feature)
                {
                    feature.SetActive(true);
                    // Reconstruct normals from the depth texture instead of forcing URP's
                    // full-scene DepthNormals prepass. The latter nearly doubled the native
                    // triangle counter in the city-wide views for no visible quality gain.
                    var featureSettings = new SerializedObject(feature);
                    var source = featureSettings.FindProperty("m_Settings.Source");
                    if (source != null) source.enumValueIndex = 0;
                    var downsample = featureSettings.FindProperty("m_Settings.Downsample");
                    if (downsample != null) downsample.boolValue = false;
                    featureSettings.ApplyModifiedPropertiesWithoutUndo();
                    if (!rendererData.rendererFeatures.Contains(feature)) rendererData.rendererFeatures.Add(feature);
                    EditorUtility.SetDirty(feature);
                }
                EditorUtility.SetDirty(rendererData);
            }
        }

        static T AddPersistent<T>(VolumeProfile profile) where T : VolumeComponent
        {
            var component = ScriptableObject.CreateInstance<T>();
            component.name = typeof(T).Name;
            profile.components.Add(component);
            AssetDatabase.AddObjectToAsset(component, profile);
            EditorUtility.SetDirty(component);
            return component;
        }
    }
}
