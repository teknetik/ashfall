using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    public static class AtmospherePass
    {
        public const string Root = "Assets/AthenHill/Art/Atmosphere/";
        const string Materials = "Assets/AthenHill/Materials/Atmosphere/";

        [MenuItem("Athen Hill/Atmosphere/Add sky grass and dust")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            if (GameObject.Find("City Atmosphere"))
                throw new InvalidOperationException("Atmosphere already exists. Edit its materials and GrassPatch components in the Inspector.");
            var before = GameplayState();
            Directory.CreateDirectory(Root);
            Directory.CreateDirectory(Materials);
            AssetDatabase.Refresh();
            var noise = MakeNoise();
            ConfigureSky(noise);
            var ground = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/World/MAT_grass.mat");
            ground.shader = RequiredShader("Athen Hill/Hill Ground");
            ground.SetTexture("_Noise", noise);
            EditorUtility.SetDirty(ground);

            var root = new GameObject("City Atmosphere");
            var atmosphere = root.AddComponent<CityAtmosphere>();
            atmosphere.session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            AddGrass(root.transform);
            atmosphere.driftingDust = AddDust(root.transform);
            var after = GameplayState();
            if (before != after) throw new InvalidOperationException("Atmosphere changed gameplay geometry or actor placement.");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Existing render chunks are stale. Inspect their sources before rebuilding.");
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            Directory.CreateDirectory("Captures/Atmosphere");
            File.WriteAllText("Captures/Atmosphere/authoring.json", JsonConvert.SerializeObject(new
            {
                gameplayPreserved = before == after,
                grassTufts = root.GetComponentsInChildren<GrassPatch>().Sum(x => x.tuftCount),
                grassTriangles = root.GetComponentsInChildren<MeshFilter>().Sum(x => x.sharedMesh.triangles.Length / 3),
                maximumDustParticles = atmosphere.driftingDust.main.maxParticles,
                grassDraws = root.GetComponentsInChildren<MeshRenderer>().Length,
                chunksUnchanged = true,
                gameplay = JsonConvert.DeserializeObject(before)
            }, Formatting.Indented));
            Capture();
            Debug.Log("Atmosphere saved: sky, grass, and dust; gameplay and render chunks preserved.");
        }

        public static void ApplyAndBuild()
        {
            Apply();
            LinuxBuild.Development();
        }

        static Shader RequiredShader(string name)
        {
            var shader = Shader.Find(name);
            if (!shader || ShaderUtil.ShaderHasError(shader)) throw new InvalidOperationException("Invalid shader: " + name);
            return shader;
        }

        static Texture2D MakeNoise()
        {
            // Periodic scalar data, shared by clouds and ground; no image asset downloads.
            const int size = 256;
            var data = new Texture2D(size, size, TextureFormat.RGBA32, true, true) { name = "AtmosphereNoise" };
            var pixels = new Color[size * size];
            float Periodic(float x, float y, float scale, float offset)
            {
                float a = Mathf.PerlinNoise(x * scale + offset, y * scale + offset);
                float b = Mathf.PerlinNoise((x - 1) * scale + offset, y * scale + offset);
                float c = Mathf.PerlinNoise(x * scale + offset, (y - 1) * scale + offset);
                float d = Mathf.PerlinNoise((x - 1) * scale + offset, (y - 1) * scale + offset);
                return Mathf.Lerp(Mathf.Lerp(a, b, x), Mathf.Lerp(c, d, x), y);
            }
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float u = x / (float)size, v = y / (float)size;
                    pixels[y * size + x] = new Color(Periodic(u, v, 16, 37), Periodic(u, v, 42, 91), Periodic(u, v, 91, 153), 1);
                }
            data.SetPixels(pixels); data.Apply();
            data.wrapMode = TextureWrapMode.Repeat;
            data.filterMode = FilterMode.Trilinear;
            data.anisoLevel = 2;
            AssetDatabase.CreateAsset(data, Root + "AtmosphereNoise.asset");
            return data;
        }

        static void ConfigureSky(Texture2D noise)
        {
            var sky = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/DesertSky.mat");
            sky.shader = RequiredShader("Athen Hill/Desert Atmosphere");
            sky.shaderKeywords = Array.Empty<string>();
            sky.SetTexture("_Noise", noise);
            sky.SetFloat("_Exposure", 1f);
            sky.SetFloat("_SunSize", .009f);
            RenderSettings.skybox = sky;
            // Match the horizon to the fog; retain the recent surface lighting and sun direction.
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = new Color(.69f, .59f, .45f);
            RenderSettings.fogStartDistance = 32f;
            RenderSettings.fogEndDistance = 132f;
            EditorUtility.SetDirty(sky);
            BakeSkyReflection();
        }

        [MenuItem("Athen Hill/Atmosphere/Bake sky reflection")]
        public static void BakeSkyReflection()
        {
            var probe = GameObject.Find("City sky reflection")?.GetComponent<ReflectionProbe>();
            if (probe && SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null)
            {
                string path = Root + "AtmosphereReflection.exr";
                if (!Lightmapping.BakeReflectionProbe(probe, path)) throw new InvalidOperationException("Sky reflection bake failed.");
                AssetDatabase.ImportAsset(path);
                probe.bakedTexture = AssetDatabase.LoadAssetAtPath<Texture>(path);
                EditorSceneManager.MarkSceneDirty(probe.gameObject.scene);
            }
        }

        public static void RefreshAndBuild()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            foreach (var name in new[] { "Athen Hill/Desert Atmosphere", "Athen Hill/Hill Ground", "Athen Hill/Wind Grass", "Athen Hill/Drifting Dust" }) RequiredShader(name);
            BakeSkyReflection();
            EditorSceneManager.SaveOpenScenes();
            AssetDatabase.SaveAssets();
            Capture();
            LinuxBuild.Development();
            File.Copy("Captures/linux-build.json", "Captures/Atmosphere/development-build.json", true);
            LinuxBuild.Release();
            File.Copy("Captures/linux-build.json", "Captures/Atmosphere/release-build.json", true);
        }

        static void AddGrass(Transform parent)
        {
            var material = new Material(RequiredShader("Athen Hill/Wind Grass")) { name = "HillGrass" };
            AssetDatabase.CreateAsset(material, Materials + "HillGrass.mat");
            var sources = GameObject.Find("AuthoredWorld").GetComponentsInChildren<MeshFilter>(true);
            var surface = sources.Single(x => x.name == "ENV_hill_surface");
            var mound = sources.Single(x => x.name == "ENV_hill_mound");
            Bounds ground = surface.GetComponent<Renderer>().bounds;
            var blockers = sources.Where(x => x.name.StartsWith("ENV_hill_path") ||
                x.name.StartsWith("PROP_hill_market_") && x.name.EndsWith("_foot"))
                .Select(x => { var b = x.GetComponent<Renderer>().bounds; b.Expand(new Vector3(.65f, 1, .65f)); return b; }).ToList();
            foreach (var npc in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.None))
                if (Vector2.Distance(new Vector2(npc.transform.position.x, npc.transform.position.z), new Vector2(ground.center.x, ground.center.z)) < 8)
                    blockers.Add(new Bounds(npc.transform.position, new Vector3(1.3f, 5, 1.3f)));
            // Keep the exposed tree roots, stairs and terminal approach paths readable.
            blockers.Add(new Bounds(new Vector3(ground.center.x, 2, ground.center.z), new Vector3(2.7f, 6, 2.7f)));
            for (int z = 0; z < 2; z++)
                for (int x = 0; x < 2; x++)
                {
                    var go = new GameObject("Hill grass " + (z * 2 + x + 1));
                    go.transform.SetParent(parent, false);
                    var patch = go.AddComponent<GrassPatch>();
                    patch.seed = 731 + z * 29 + x * 13;
                    patch.minimum = new Vector2(x == 0 ? ground.min.x + .38f : ground.center.x, z == 0 ? ground.min.z + .38f : ground.center.z);
                    patch.maximum = new Vector2(x == 0 ? ground.center.x : ground.max.x - .38f, z == 0 ? ground.center.z : ground.max.z - .38f);
                    patch.groundSurface = surface; patch.moundSurface = mound; patch.exclusions = blockers.ToArray();
                    var renderer = go.GetComponent<MeshRenderer>();
                    renderer.sharedMaterial = material;
                    renderer.shadowCastingMode = ShadowCastingMode.Off;
                    renderer.receiveShadows = true;
                    renderer.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
                    GrassPatchEditor.Rebuild(patch);
                }
        }

        static ParticleSystem AddDust(Transform parent)
        {
            var go = new GameObject("Drifting plaza dust");
            go.transform.SetParent(parent, false); go.transform.position = new Vector3(4, 2.7f, 0);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            ps.useAutoRandomSeed = false; ps.randomSeed = 8401;
            var main = ps.main;
            main.loop = true; main.prewarm = true; main.duration = 20;
            main.startLifetime = new ParticleSystem.MinMaxCurve(14, 22);
            main.startSpeed = 0;
            main.startSize = new ParticleSystem.MinMaxCurve(.045f, .16f);
            main.startColor = new Color(1, .94f, .79f, .5f);
            main.maxParticles = 64; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var emission = ps.emission; emission.rateOverTime = 3;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Box; shape.scale = new Vector3(46, 4, 36);
            var velocity = ps.velocityOverLifetime; velocity.enabled = true; velocity.space = ParticleSystemSimulationSpace.World;
            velocity.x = new ParticleSystem.MinMaxCurve(.11f, .22f); velocity.y = new ParticleSystem.MinMaxCurve(-.025f, .035f); velocity.z = new ParticleSystem.MinMaxCurve(.035f, .085f);
            var color = ps.colorOverLifetime; color.enabled = true;
            var gradient = new Gradient();
            gradient.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, .2f), new GradientAlphaKey(1, .75f), new GradientAlphaKey(0, 1) });
            color.color = gradient;
            var renderer = go.GetComponent<ParticleSystemRenderer>();
            var material = new Material(RequiredShader("Athen Hill/Drifting Dust")) { name = "PlazaDust" };
            AssetDatabase.CreateAsset(material, Materials + "PlazaDust.mat");
            renderer.sharedMaterial = material; renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false; renderer.maxParticleSize = .025f;
            return ps;
        }

        static string GameplayState() => JsonConvert.SerializeObject(new
        {
            colliders = UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Include, FindObjectsSortMode.InstanceID)
                .Select(x => new { x.name, position = x.transform.position.ToString("R"), bounds = x.bounds.ToString("R"), x.enabled }).ToArray(),
            npcs = UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.InstanceID)
                .Select(x => new { x.name, position = x.transform.position.ToString("R") }).ToArray(),
            routes = UnityEngine.Object.FindObjectsByType<AmbientWalker>(FindObjectsSortMode.InstanceID)
                .Select(x => new { x.name, position = x.transform.position.ToString("R"), data = EditorJsonUtility.ToJson(x) }).ToArray()
        });

        [MenuItem("Athen Hill/Atmosphere/Capture review cameras")]
        public static void Capture()
        {
            if (SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null) return;
            PortDiagnostics.Capture("cam_hill"); // Warm URP's offscreen resources.
            foreach (var name in new[] { "cam_hill", "cam_avenue", "cam_gate", "cam_grid", "cam_whompah", "cam_hero" })
            {
                PortDiagnostics.Capture(name);
                Directory.CreateDirectory("Captures/Atmosphere");
                File.Copy("Captures/Fixed/" + name + ".png", "Captures/Atmosphere/" + name + ".png", true);
            }
        }
    }

    [CustomEditor(typeof(GrassPatch))]
    public class GrassPatchEditor : UnityEditor.Editor
    {
        public override void OnInspectorGUI()
        {
            DrawDefaultInspector();
            EditorGUILayout.HelpBox("Saved mesh, no runtime generation. Regenerate after changing placement or seed. Tuft limit preserves the city triangle budget.", MessageType.Info);
            if (GUILayout.Button("Rebuild this grass patch"))
            {
                Rebuild((GrassPatch)target);
                EditorSceneManager.MarkSceneDirty(((GrassPatch)target).gameObject.scene);
                AssetDatabase.SaveAssets();
            }
        }

        public static void Rebuild(GrassPatch patch)
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play mode before baking grass.");
            var random = new System.Random(patch.seed);
            float Between(float a, float b) => Mathf.Lerp(a, b, (float)random.NextDouble());
            var vertices = new List<Vector3>(); var uv = new List<Vector2>();
            var colors = new List<Color>(); var indices = new List<int>();
            var ground = patch.groundSurface.GetComponent<Renderer>().bounds;
            var moundMesh = patch.moundSurface.sharedMesh;
            var moundVertices = moundMesh.vertices.Select(patch.moundSurface.transform.TransformPoint).ToArray();
            var moundIndices = moundMesh.triangles;
            float GroundHeight(float x, float z)
            {
                float y = ground.max.y;
                for (int i = 0; i < moundIndices.Length; i += 3)
                {
                    var a = moundVertices[moundIndices[i]]; var b = moundVertices[moundIndices[i + 1]]; var c = moundVertices[moundIndices[i + 2]];
                    float det = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z);
                    if (Mathf.Abs(det) < .0001f) continue;
                    float u = ((b.z - c.z) * (x - c.x) + (c.x - b.x) * (z - c.z)) / det;
                    float v = ((c.z - a.z) * (x - c.x) + (a.x - c.x) * (z - c.z)) / det;
                    if (u >= 0 && v >= 0 && u + v <= 1) y = Mathf.Max(y, u * a.y + v * b.y + (1 - u - v) * c.y);
                }
                return y;
            }
            int placed = 0;
            int count = Mathf.Clamp(patch.tuftCount, 0, 85);
            for (int attempt = 0; attempt < count * 100 && placed < count; attempt++)
            {
                float x = Between(patch.minimum.x, patch.maximum.x), z = Between(patch.minimum.y, patch.maximum.y);
                if (patch.exclusions.Any(b => x > b.min.x && x < b.max.x && z > b.min.z && z < b.max.z)) continue;
                var center = new Vector3(x, GroundHeight(x, z) - .015f, z);
                float height = Between(patch.heightRange.x, patch.heightRange.y);
                float width = Between(patch.widthRange.x, patch.widthRange.y);
                float angle = Between(0, Mathf.PI * 2);
                var color = new Color(Between(0, 1), Between(0, 1), 0, Between(0, 1));
                for (int card = 0; card < 2; card++)
                {
                    float yaw = angle + card * Mathf.PI * .5f;
                    var right = new Vector3(Mathf.Cos(yaw), 0, Mathf.Sin(yaw)) * width * .5f;
                    int start = vertices.Count;
                    foreach (var v in new[] { center - right, center + right, center + right + Vector3.up * height, center - right + Vector3.up * height })
                    { vertices.Add(patch.transform.InverseTransformPoint(v)); colors.Add(color); }
                    uv.AddRange(new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up });
                    indices.AddRange(new[] { start, start + 2, start + 1, start, start + 3, start + 2 });
                }
                placed++;
            }
            if (placed != count) throw new InvalidOperationException("Could not place grass outside paths and roots.");
            var mesh = new Mesh { name = patch.name };
            mesh.SetVertices(vertices); mesh.SetUVs(0, uv); mesh.SetColors(colors); mesh.SetTriangles(indices, 0);
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            var bounds = mesh.bounds; bounds.Expand(.5f); mesh.bounds = bounds;
            string path = AtmospherePass.Root + patch.name.Replace(' ', '_') + ".asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing) { EditorUtility.CopySerialized(mesh, existing); UnityEngine.Object.DestroyImmediate(mesh); mesh = existing; }
            else AssetDatabase.CreateAsset(mesh, path);
            patch.GetComponent<MeshFilter>().sharedMesh = mesh;
            EditorUtility.SetDirty(patch);
        }
    }
}
