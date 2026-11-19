using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// 19 November 2026, world map (art/showcase_20261119/world_map/README.md). The map itself needs no scene edit: the
    /// GameSession adds its WorldMap component at runtime, the HUD builds the window, and the panel draws a schematic.
    /// This pass only produces the optional survey asset, Assets/AthenHill/Resources/WorldMap/WorldMapSurvey.asset, which
    /// the map uses instead of its schematic base when present. It never saves the scene. Steps (re-runnable):
    ///  anchors   (-nographics is fine) reads the positions of a few named scene roots (Vanguard Hall, Nanofab 2, the
    ///            water point, ...) into the survey asset's anchors, replacing the recorded positions in the schematic.
    ///  survey    NEEDS GRAPHICS (do not pass -nographics): two orthographic top-down renders of the saved scene, the Outer
    ///            Berms overview (x -600..80, z -260..240 at 4 px/m, 2720 x 2000) and the city detail (x -64..64,
    ///            z -48..48 at 16 px/m, 2048 x 1536), each rendered at twice the size and halved for antialiasing, with
    ///            fog, sky and post-processing off, LODs forced to full detail, a fixed sun from the north-west (elevation
    ///            55°) and soft shadows, all restored afterwards. PNGs go to Assets/AthenHill/Art/WorldMap/ (BC7, mipmaps,
    ///            clamp); the asset records each layer's exact world rectangle (the world-to-map transform), also written
    ///            beside the PNGs as WorldMapSurvey.json and to the evidence folder.
    ///  verify    -> unity/evidence/world-map/20261119/verify.json: the asset (if any) loads with usable layers, the
    ///            panel style loads from Resources, Controls.inputactions has UI/Map on M and nothing else on M.
    ///  rollback  deletes the survey asset and the two textures: the map returns to its schematic.
    /// Batch: unity.sh LOG AthenHill.Editor.WorldMapInstall20261119.RunBatch --steps anchors,survey,verify   (graphics)
    ///        unity.sh LOG AthenHill.Editor.WorldMapInstall20261119.RunBatch --steps anchors,verify -nographics
    /// </summary>
    public static class WorldMapInstall20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string AssetDir = "Assets/AthenHill/Resources/WorldMap/";
        const string AssetPath = AssetDir + "WorldMapSurvey.asset";
        const string ArtDir = "Assets/AthenHill/Art/WorldMap/";
        const string InputPath = "Assets/AthenHill/Data/Controls.inputactions";
        const string Evidence = "../evidence/world-map/20261119/";
        const string ArtRecord = "../../art/showcase_20261119/world_map/";

        sealed class LayerSpec { public string id; public Rect world; public float ppm; public int order; }
        static readonly LayerSpec[] Layers =
        {
            new LayerSpec { id = "berms", world = Rect.MinMaxRect(-600, -260, 80, 240), ppm = 4, order = 0 },
            new LayerSpec { id = "city", world = Rect.MinMaxRect(-64, -48, 64, 48), ppm = 16, order = 1 },
        };
        /// City places read from the scene (map id -> scene object names to try, first active match wins).
        static readonly (string id, string[] names)[] AnchorNames =
        {
            ("city:vanguard_hall", new[] { "Vanguard Hall" }),
            ("city:nanofab", new[] { "Ward building: Nanofab 2" }),
            ("city:processing", new[] { "Ward building: Processing 11 ruin" }),
            ("city:aquifer", new[] { "Ward building: Aquifer 3" }),
            ("city:hydroponics", new[] { "Ward hydroponics" }),
            ("city:water_point", new[] { "Ward life: Lattice court water ration" }),
            ("city:goods_dock", new[] { "Ward life: Node 07 goods dock" }),
            ("city:salvage", new[] { "Salvage shop interior" }),
            ("city:field_supply", new[] { "Field Supply interior" }),
        };

        [MenuItem("Athen Hill/World map/Read anchors")] static void AnchorsMenu() => Debug.Log("WorldMap anchors: " + Anchors());
        [MenuItem("Athen Hill/World map/Render survey (graphics)")] static void SurveyMenu() => Debug.Log("WorldMap survey: " + Survey());
        [MenuItem("Athen Hill/World map/Verify")] static void VerifyMenu() => Debug.Log("WorldMap verify: " + Verify());
        [MenuItem("Athen Hill/World map/Rollback")] static void RollbackMenu() => Debug.Log("WorldMap rollback: " + Rollback());

        static WorldMapSurvey LoadOrCreate()
        {
            var s = AssetDatabase.LoadAssetAtPath<WorldMapSurvey>(AssetPath);
            if (s) return s;
            Directory.CreateDirectory(AssetDir);
            s = ScriptableObject.CreateInstance<WorldMapSurvey>();
            AssetDatabase.CreateAsset(s, AssetPath);
            return s;
        }

        static void OpenScene()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        static bool TryBounds(GameObject go, out Bounds b)
        {
            b = default; bool any = false;
            foreach (var r in go.GetComponentsInChildren<Renderer>(false))
            {
                if (!r.enabled || r is ParticleSystemRenderer) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            return any;
        }

        public static string Anchors()
        {
            OpenScene();
            var all = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            var found = new List<WorldMapSurvey.Anchor>(); var log = new List<string>();
            foreach (var (id, names) in AnchorNames)
            {
                Transform t = null;
                foreach (var n in names) { t = all.FirstOrDefault(x => x.name == n && x.gameObject.activeInHierarchy); if (t) break; }
                if (!t) { log.Add(id + ": not found"); continue; }
                var at = TryBounds(t.gameObject, out var b) ? b.center : t.position;
                // a place far from the city is a wrong match (another object with the same name): keep the recorded one
                if (!WorldMapMath.CityBounds.Contains(new Vector2(at.x, at.z))) { log.Add($"{id}: '{t.name}' outside the walls at {at}, skipped"); continue; }
                found.Add(new WorldMapSurvey.Anchor { id = id, position = at });
                log.Add($"{id}: {at.x:0.0},{at.z:0.0}");
            }
            var s = LoadOrCreate();
            s.anchors = found.ToArray(); s.scene = ScenePath;
            EditorUtility.SetDirty(s); AssetDatabase.SaveAssetIfDirty(s);
            return string.Join("; ", log);
        }

        public static string Survey()
        {
            if (Application.isBatchMode && SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null)
                throw new Exception("the survey step renders: run it without -nographics");
            OpenScene();
            Directory.CreateDirectory(ArtDir);
            var rendered = new List<(LayerSpec spec, string path, int w, int h)>();
            using (new SurveyLighting())
            {
                foreach (var l in Layers)
                {
                    int w = Mathf.RoundToInt(l.world.width * l.ppm / 4) * 4, h = Mathf.RoundToInt(l.world.height * l.ppm / 4) * 4;
                    var png = RenderTopDown(l.world, w, h);
                    var path = ArtDir + "WorldMap_" + l.id + ".png";
                    File.WriteAllBytes(path, png);
                    rendered.Add((l, path, w, h));
                }
            }
            var survey = LoadOrCreate();
            var layers = new List<WorldMapSurvey.Layer>();
            foreach (var (spec, path, w, h) in rendered)
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                var imp = (TextureImporter)AssetImporter.GetAtPath(path);
                imp.textureType = TextureImporterType.Default; imp.sRGBTexture = true; imp.alphaSource = TextureImporterAlphaSource.None;
                imp.npotScale = TextureImporterNPOTScale.None; imp.mipmapEnabled = true; imp.wrapMode = TextureWrapMode.Clamp;
                imp.filterMode = FilterMode.Trilinear; imp.anisoLevel = 2; imp.maxTextureSize = 4096; imp.isReadable = false;
                imp.textureCompression = TextureImporterCompression.CompressedHQ; imp.streamingMipmaps = false;
                var standalone = imp.GetPlatformTextureSettings("Standalone");
                standalone.overridden = true; standalone.maxTextureSize = 4096; standalone.format = TextureImporterFormat.BC7;
                imp.SetPlatformTextureSettings(standalone);
                imp.SaveAndReimport();
                layers.Add(new WorldMapSurvey.Layer { id = spec.id, texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path), worldRect = spec.world, pixelsPerMetre = w / spec.world.width, order = spec.order });
            }
            survey.layers = layers.ToArray(); survey.renderedUtc = DateTime.UtcNow.ToString("o"); survey.scene = ScenePath;
            survey.sunElevationBearing = new Vector2(SurveyLighting.Elevation, SurveyLighting.Bearing);
            EditorUtility.SetDirty(survey); AssetDatabase.SaveAssetIfDirty(survey);
            var record = new JObject
            {
                ["renderedUtc"] = survey.renderedUtc, ["scene"] = ScenePath,
                ["transform"] = "u = (x - xMin) / width, v = (z - zMin) / height; texture row 0 is the south edge, north is up",
                ["sun"] = new JObject { ["elevation"] = SurveyLighting.Elevation, ["bearingOfTravel"] = SurveyLighting.Bearing },
                ["layers"] = new JArray(rendered.Select(r => new JObject { ["id"] = r.spec.id, ["texture"] = r.path, ["width"] = r.w, ["height"] = r.h, ["xMin"] = r.spec.world.xMin, ["zMin"] = r.spec.world.yMin, ["width_m"] = r.spec.world.width, ["height_m"] = r.spec.world.height })),
            };
            File.WriteAllText(ArtDir + "WorldMapSurvey.json", record.ToString(Formatting.Indented));
            foreach (var dir in new[] { Evidence, ArtRecord }) { Directory.CreateDirectory(dir); File.WriteAllText(dir + "survey.json", record.ToString(Formatting.Indented)); }
            AssetDatabase.ImportAsset(ArtDir + "WorldMapSurvey.json");
            return string.Join("; ", rendered.Select(r => $"{r.spec.id} {r.w}x{r.h}"));
        }

        /// One top-down orthographic render (north up), at twice the size and halved by a bilinear blit for antialiasing.
        static byte[] RenderTopDown(Rect world, int w, int h)
        {
            var go = new GameObject("World map survey camera") { hideFlags = HideFlags.HideAndDontSave };
            RenderTexture big = null, small = null; Texture2D pixels = null; var active = RenderTexture.active;
            try
            {
                var cam = go.AddComponent<Camera>();
                cam.enabled = false; cam.orthographic = true; cam.orthographicSize = world.height * .5f; cam.aspect = world.width / world.height;
                // looking straight down with +Z (north) at the top of the picture and +X (east) to the right
                cam.transform.SetPositionAndRotation(new Vector3(world.center.x, 800, world.center.y), Quaternion.Euler(90, 0, 0));
                cam.nearClipPlane = 1; cam.farClipPlane = 1600;
                cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color32(0x10, 0x17, 0x17, 255);
                cam.cullingMask = ~((1 << 5) | (1 << 9) | (1 << 10)); // not UI, the first-person view model or the pack preview
                cam.allowHDR = false; cam.allowMSAA = false;
                var data = go.AddComponent<UniversalAdditionalCameraData>();
                data.renderPostProcessing = false; data.antialiasing = AntialiasingMode.None; data.renderShadows = true;
                big = new RenderTexture(new RenderTextureDescriptor(w * 2, h * 2, GraphicsFormat.R8G8B8A8_SRGB, 24) { msaaSamples = 1 }) { name = "World map survey 2x", filterMode = FilterMode.Bilinear };
                small = new RenderTexture(new RenderTextureDescriptor(w, h, GraphicsFormat.R8G8B8A8_SRGB, 0) { msaaSamples = 1 }) { name = "World map survey" };
                big.Create(); small.Create();
                cam.targetTexture = big;
                var request = new UnityEngine.Rendering.RenderPipeline.StandardRequest { destination = big };
                if (UnityEngine.Rendering.RenderPipeline.SupportsRenderRequest(cam, request)) UnityEngine.Rendering.RenderPipeline.SubmitRenderRequest(cam, request);
                else cam.Render();
                Graphics.Blit(big, small);
                RenderTexture.active = small;
                pixels = new Texture2D(w, h, TextureFormat.RGB24, false, false);
                pixels.ReadPixels(new Rect(0, 0, w, h), 0, 0, false); pixels.Apply(false);
                return pixels.EncodeToPNG();
            }
            finally
            {
                RenderTexture.active = active;
                if (pixels) UnityEngine.Object.DestroyImmediate(pixels);
                if (big) { big.Release(); UnityEngine.Object.DestroyImmediate(big); }
                if (small) { small.Release(); UnityEngine.Object.DestroyImmediate(small); }
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        /// Survey-sheet lighting for the duration of the renders, restored on Dispose: a copy of the URP asset with long
        /// soft shadows (the project asset is never edited), no fog, full-detail LODs and a fixed sun.
        sealed class SurveyLighting : IDisposable
        {
            public const float Elevation = 55, Bearing = 135; // the light travels toward the south-east: lit from the north-west
            readonly RenderPipelineAsset quality; readonly UniversalRenderPipelineAsset copy;
            readonly bool fog; readonly float lodBias; readonly int maxLod;
            readonly Light sun; readonly Quaternion sunRotation; readonly LightShadows sunShadows; readonly float sunStrength;
            public SurveyLighting()
            {
                quality = QualitySettings.renderPipeline;
                if (GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset source)
                {
                    copy = UnityEngine.Object.Instantiate(source); copy.name = source.name + " (world map survey)"; copy.hideFlags = HideFlags.HideAndDontSave;
                    copy.shadowDistance = 1400; copy.shadowCascadeCount = 1; copy.mainLightShadowmapResolution = 4096;
                    QualitySettings.renderPipeline = copy;
                }
                fog = RenderSettings.fog; RenderSettings.fog = false;
                lodBias = QualitySettings.lodBias; maxLod = QualitySettings.maximumLODLevel;
                QualitySettings.lodBias = 40; QualitySettings.maximumLODLevel = 0; // orthographic views pick LODs by size: keep the near ones
                sun = RenderSettings.sun ? RenderSettings.sun : UnityEngine.Object.FindObjectsByType<Light>(FindObjectsSortMode.None).Where(l => l.type == LightType.Directional && l.isActiveAndEnabled).OrderByDescending(l => l.intensity).FirstOrDefault();
                if (sun)
                {
                    sunRotation = sun.transform.rotation; sunShadows = sun.shadows; sunStrength = sun.shadowStrength;
                    sun.transform.rotation = Quaternion.Euler(Elevation, Bearing, 0); sun.shadows = LightShadows.Soft; sun.shadowStrength = .75f;
                }
            }
            public void Dispose()
            {
                if (sun) { sun.transform.rotation = sunRotation; sun.shadows = sunShadows; sun.shadowStrength = sunStrength; }
                QualitySettings.lodBias = lodBias; QualitySettings.maximumLODLevel = maxLod;
                RenderSettings.fog = fog;
                if (copy) { QualitySettings.renderPipeline = quality; UnityEngine.Object.DestroyImmediate(copy); }
            }
        }

        public static string Verify()
        {
            var problems = new List<string>(); var r = new JObject();
            var survey = AssetDatabase.LoadAssetAtPath<WorldMapSurvey>(AssetPath);
            r["surveyAsset"] = (bool)survey;
            if (survey)
            {
                if (Resources.Load<WorldMapSurvey>(WorldMapSurvey.ResourcePath) != survey) problems.Add("the survey asset does not load from Resources/" + WorldMapSurvey.ResourcePath);
                r["layers"] = new JArray((survey.layers ?? new WorldMapSurvey.Layer[0]).Select(l => new JObject { ["id"] = l?.id, ["usable"] = survey.Usable(l), ["texture"] = l?.texture ? AssetDatabase.GetAssetPath(l.texture) : null, ["width"] = l?.texture ? l.texture.width : 0, ["height"] = l?.texture ? l.texture.height : 0, ["world"] = l != null ? new JArray(l.worldRect.xMin, l.worldRect.yMin, l.worldRect.width, l.worldRect.height) : null }));
                foreach (var l in survey.layers ?? new WorldMapSurvey.Layer[0])
                {
                    if (!survey.Usable(l)) { problems.Add("layer " + l?.id + " is not usable"); continue; }
                    float aspectWorld = l.worldRect.width / l.worldRect.height, aspectTex = (float)l.texture.width / l.texture.height;
                    if (Mathf.Abs(aspectWorld - aspectTex) > .01f) problems.Add($"layer {l.id}: texture aspect {aspectTex:0.000} does not match its world rectangle {aspectWorld:0.000}");
                }
                r["anchors"] = new JArray((survey.anchors ?? new WorldMapSurvey.Anchor[0]).Select(a => new JObject { ["id"] = a.id, ["x"] = a.position.x, ["z"] = a.position.z }));
                var known = new HashSet<string>(WorldMapSchematic.CityPlaces().Select(p => p.id));
                foreach (var a in survey.anchors ?? new WorldMapSurvey.Anchor[0]) if (!known.Contains(a.id)) problems.Add("anchor for unknown place " + a.id);
            }
            if (!Resources.Load<UnityEngine.UIElements.StyleSheet>(WorldMapPanel.StylePath)) problems.Add("panel style does not load from Resources/" + WorldMapPanel.StylePath);
            var input = JObject.Parse(File.ReadAllText(InputPath));
            var maps = input["maps"].Children<JObject>().ToList();
            var onM = maps.SelectMany(m => m["bindings"].Children<JObject>().Where(b => (string)b["path"] == "<Keyboard>/m").Select(b => (string)m["name"] + "/" + (string)b["action"])).ToList();
            r["onM"] = new JArray(onM);
            if (onM.Count != 1 || onM[0] != "UI/Map") problems.Add("M is not bound to exactly UI/Map: " + string.Join(",", onM));
            var ids = maps.SelectMany(m => m["actions"].Children<JObject>()).Select(a => (string)a["id"]).ToList();
            if (ids.Count != ids.Distinct().Count()) problems.Add("duplicate action ids in Controls.inputactions");
            r["problems"] = new JArray(problems); r["pass"] = problems.Count == 0;
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", r.ToString(Formatting.Indented));
            if (problems.Count > 0) throw new Exception("verify failed: " + string.Join("; ", problems));
            return survey ? "PASS (survey present)" : "PASS (no survey: the map draws its schematic)";
        }

        public static string Rollback()
        {
            var log = new List<string>();
            foreach (var path in new[] { AssetPath }.Concat(Layers.Select(l => ArtDir + "WorldMap_" + l.id + ".png")).Append(ArtDir + "WorldMapSurvey.json"))
                if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path) && AssetDatabase.DeleteAsset(path)) log.Add("deleted " + path);
            return log.Count > 0 ? string.Join("; ", log) : "nothing to roll back";
        }

        /// -executeMethod AthenHill.Editor.WorldMapInstall20261119.RunBatch --steps anchors,survey,verify (or rollback)
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = (i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify").Split(',');
            try
            {
                foreach (var st in steps)
                {
                    string result = st switch
                    {
                        "anchors" => Anchors(),
                        "survey" => Survey(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("WorldMapInstall20261119 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
