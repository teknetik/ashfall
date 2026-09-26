using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>
    /// 26 September 2026 "dust-bowl" pass: a grittier post-apocalyptic frontier grade and
    /// the Blender-built Karaveen caravan market (art/karaveen_market_20260926).
    /// Market: one saved glTF prefab instance at the scene origin. COL_* nodes become box
    /// colliders, LIGHT_/SMOKE_ markers receive lanterns, fire and smoke, "* Goods" nodes
    /// get distance culling. The three earlier placeholder stalls are kept but disabled.
    /// Atmosphere: new lighting/grade assets are created beside the originals, which are
    /// retained unchanged for rollback (see evidence/dustbowl-market/20260926/pass.json).
    /// </summary>
    public static class DustbowlMarketPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string MarketGlb = "Assets/AthenHill/Art/KaraveenMarket/KaraveenMarket.glb";
        const string MarketRootName = "Karaveen caravan market";
        const string Dir = "Assets/AthenHill/Art/Atmosphere/Dustbowl/";
        const string DayNightPath = Dir + "WardDustbowl.asset";
        const string GradePath = Dir + "WardDustbowlGrade.asset";
        const string SkyPath = "Assets/AthenHill/Art/ReferenceStreet/20260909/WardReferenceSky.mat";
        const string Evidence = "../evidence/dustbowl-market/20260926/";
        static readonly string[] OldStalls = { "Karaveen artisan stall", "Karaveen artisan stall (1)", "Karaveen artisan stall (2)" };
        static readonly Dictionary<string, object> Record = new Dictionary<string, object>();

        [MenuItem("Athen Hill/Karaveen/Install caravan market")]
        public static void InstallMarketMenu()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (scene.GetRootGameObjects().Any(g => g.name == MarketRootName))
                throw new InvalidOperationException("The caravan market is already installed. Edit its prefab instance instead of reinstalling.");
            InstallMarket(scene); Save(scene);
        }

        [MenuItem("Athen Hill/Atmosphere/Apply dust-bowl grade")]
        public static void ApplyAtmosphereMenu()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            ApplyAtmosphere(scene); Save(scene);
        }

        /// Batch entry point used during authoring; replaces an earlier install of this pass only.
        public static void RunAll()
        {
            AssetDatabase.Refresh();
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == MarketRootName || g.name == "Windborne dust" || g.name == ReviewCameras).ToArray())
                UnityEngine.Object.DestroyImmediate(old);
            InstallMarket(scene);
            ApplyAtmosphere(scene);
            AddReviewCameras(scene);
            Save(scene);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "pass.json", JsonConvert.SerializeObject(Record, Formatting.Indented));
        }

        const string ReviewCameras = "Karaveen market review cameras";

        /// Disabled cameras for the development View command (same convention as cam_gate etc.).
        static void AddReviewCameras(Scene scene)
        {
            var root = new GameObject(ReviewCameras);
            SceneManager.MoveGameObjectToScene(root, scene);
            foreach (var (name, eye, target) in new[]
            {
                ("cam_market", new Vector3(-27f, 5.5f, 3f), new Vector3(-39f, .8f, 0f)),
                ("cam_market_lane", new Vector3(-31.5f, 1.7f, -13f), new Vector3(-37f, 1.2f, 6f)),
                ("cam_market_produce", new Vector3(-36.4f, 1.65f, 12.4f), new Vector3(-40f, 1.05f, 12f)),
                ("cam_market_cookfire", new Vector3(-31.6f, 1.8f, -1.2f), new Vector3(-35f, .7f, -3f)),
            })
            {
                var go = new GameObject(name);
                go.transform.SetParent(root.transform, false);
                go.transform.position = eye; go.transform.LookAt(target);
                var cam = go.AddComponent<Camera>(); cam.fieldOfView = 58; cam.enabled = false;
            }
        }

        static void Save(Scene scene)
        {
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
        }

        // ------------------------------------------------------------------ market
        static void InstallMarket(Scene scene)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(MarketGlb)
                ?? throw new InvalidOperationException("Import " + MarketGlb + " first (art/karaveen_market_20260926/build_market.py).");
            var root = (GameObject)PrefabUtility.InstantiatePrefab(asset, scene);
            root.name = MarketRootName;
            root.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

            var session = UnityEngine.Object.FindFirstObjectByType<GameSession>();
            var circuit = UnityEngine.Object.FindFirstObjectByType<CityLightCircuit>();
            var lanterns = new List<Light>();
            int colliders = 0, goods = 0;
            var all = root.GetComponentsInChildren<Transform>(true);
            foreach (var t in all)
            {
                if (t.name.StartsWith("COL_"))
                {
                    var filter = t.GetComponent<MeshFilter>();
                    if (filter && filter.sharedMesh)
                    {
                        var box = t.gameObject.AddComponent<BoxCollider>();
                        box.center = filter.sharedMesh.bounds.center; box.size = filter.sharedMesh.bounds.size;
                        colliders++;
                    }
                    var r = t.GetComponent<Renderer>(); if (r) r.enabled = false;
                }
                else if (t.name.EndsWith(" Goods"))
                {
                    var renderers = t.GetComponents<Renderer>();
                    if (renderers.Length == 0) continue;
                    var lod = t.gameObject.AddComponent<LODGroup>();
                    lod.SetLODs(new[] { new LOD(.045f, renderers) });
                    lod.fadeMode = LODFadeMode.None;
                    lod.RecalculateBounds();
                    goods++;
                }
                else if (t.name.StartsWith("LIGHT_"))
                {
                    bool fire = t.name == "LIGHT_fire";
                    var go = new GameObject(fire ? "Cookfire light" : "Lantern light");
                    go.transform.SetParent(t, false);
                    var light = go.AddComponent<Light>();
                    light.type = LightType.Point;
                    light.color = fire ? new Color(1f, .52f, .24f) : new Color(1f, .7f, .42f);
                    light.intensity = fire ? 1.8f : 1.4f;
                    light.range = fire ? 6.5f : 4.5f;
                    light.shadows = LightShadows.None;
                    if (fire)
                    {
                        var flicker = go.AddComponent<FireFlicker>();
                        flicker.session = session; flicker.baseIntensity = light.intensity;
                    }
                    else lanterns.Add(light);
                }
                else if (t.name.StartsWith("SMOKE_")) BuildCookfireEffects(t, session);
            }
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (!r.enabled) continue;
                r.shadowCastingMode = r.name.EndsWith(" Goods") && r.name.StartsWith("Bunting") ? ShadowCastingMode.Off : ShadowCastingMode.On;
                r.receiveShadows = true;
            }
            if (circuit)
            {   // lanterns follow the existing day/night lamp circuit and distance culling
                var so = new SerializedObject(circuit);
                var list = so.FindProperty("practicalLights");
                for (int i = list.arraySize - 1; i >= 0; i--)   // drop references to lights from a replaced install
                    if (!list.GetArrayElementAtIndex(i).objectReferenceValue) list.DeleteArrayElementAtIndex(i);
                foreach (var light in lanterns)
                {
                    list.arraySize++;
                    list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = light;
                }
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            var disabled = new List<string>();
            foreach (var go in scene.GetRootGameObjects().Where(g => OldStalls.Contains(g.name)))
            {
                go.SetActive(false); disabled.Add(go.name);
            }
            Record["market"] = new
            {
                prefab = MarketGlb, colliders, goodsLodGroups = goods, lanterns = lanterns.Count, circuit = circuit ? circuit.name : null,
                disabledPlaceholderStalls = disabled,
                triangles = root.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh && !f.name.StartsWith("COL_")).Sum(f => (long)f.sharedMesh.triangles.Length / 3)
            };
        }

        static void BuildCookfireEffects(Transform anchor, GameSession session)
        {
            var puff = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + "SoftPuff.png");
            var smokeMat = ParticleMaterial("CookfireSmoke", true, false, puff, new Color(.46f, .42f, .38f, 1f));
            var flameMat = ParticleMaterial("CookfireFlame", false, true, puff, new Color(1f, .62f, .28f, 1f));
            var effects = new List<ParticleSystem>();

            var smoke = NewSystem("Cookfire smoke", anchor, Vector3.zero, smokeMat, out var main);
            main.startLifetime = new ParticleSystem.MinMaxCurve(6, 9); main.startSpeed = new ParticleSystem.MinMaxCurve(.25f, .5f);
            main.startSize = new ParticleSystem.MinMaxCurve(.6f, 1.05f); main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
            main.startColor = new Color(.36f, .33f, .3f, .95f); main.maxParticles = 110;
            var em = smoke.emission; em.rateOverTime = 9;
            var shape = smoke.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 8; shape.radius = .12f;
            shape.rotation = new Vector3(-90, 0, 0);
            var vel = smoke.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(.25f, .55f); vel.y = new ParticleSystem.MinMaxCurve(.35f, .6f); vel.z = new ParticleSystem.MinMaxCurve(.05f, .2f);
            var size = smoke.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .6f, 1, 3.4f));
            var col = smoke.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(.42f, .38f, .34f), new Color(.6f, .56f, .52f), .8f, .08f);
            var rot = smoke.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-.35f, .35f);
            effects.Add(smoke);

            var flame = NewSystem("Cookfire flames", anchor, new Vector3(0, -.14f, 0), flameMat, out main);
            main.startLifetime = new ParticleSystem.MinMaxCurve(.35f, .6f); main.startSpeed = new ParticleSystem.MinMaxCurve(.3f, .7f);
            main.startSize = new ParticleSystem.MinMaxCurve(.16f, .32f); main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
            main.startColor = new Color(1f, .6f, .25f, .9f); main.maxParticles = 40;
            em = flame.emission; em.rateOverTime = 24;
            shape = flame.shape; shape.shapeType = ParticleSystemShapeType.Circle; shape.radius = .17f; shape.rotation = new Vector3(-90, 0, 0);
            size = flame.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, 1, 1, .2f));
            col = flame.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(1f, .78f, .4f), new Color(1f, .3f, .08f), 1f, .1f);
            effects.Add(flame);

            var embers = NewSystem("Cookfire embers", anchor, new Vector3(0, -.1f, 0), flameMat, out main);
            main.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 2.4f); main.startSpeed = new ParticleSystem.MinMaxCurve(.7f, 1.5f);
            main.startSize = new ParticleSystem.MinMaxCurve(.012f, .03f); main.startColor = new Color(1f, .55f, .2f, 1f); main.maxParticles = 30;
            em = embers.emission; em.rateOverTime = 5;
            shape = embers.shape; shape.shapeType = ParticleSystemShapeType.Circle; shape.radius = .15f; shape.rotation = new Vector3(-90, 0, 0);
            var noise = embers.noise; noise.enabled = true; noise.strength = .6f; noise.frequency = 1.2f;
            col = embers.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(1f, .7f, .3f), new Color(1f, .25f, .05f), 1f, .05f);
            effects.Add(embers);

            var holder = anchor.gameObject.AddComponent<WindborneDust>();
            holder.session = session; holder.viewer = null; holder.systems = effects.ToArray();
            holder.height = anchor.position.y;
            holder.enabled = true;
            // WindborneDust only follows a viewer when one is assigned; here it just handles Reduced Motion.
        }

        static ParticleSystem NewSystem(string name, Transform parent, Vector3 local, Material mat, out ParticleSystem.MainModule main)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false); go.transform.localPosition = local;
            var ps = go.AddComponent<ParticleSystem>();
            main = ps.main;
            main.loop = true; main.prewarm = true; main.duration = 10; main.playOnAwake = true;
            main.simulationSpace = ParticleSystemSimulationSpace.World; main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            var renderer = go.GetComponent<ParticleSystemRenderer>();
            renderer.sharedMaterial = mat; renderer.shadowCastingMode = ShadowCastingMode.Off; renderer.receiveShadows = false;
            renderer.sortMode = ParticleSystemSortMode.Distance;
            return ps;
        }

        static ParticleSystem.MinMaxGradient Fade(Color a, Color b, float peak, float fadeIn)
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(a, 0), new GradientColorKey(b, 1) },
                      new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(peak, fadeIn), new GradientAlphaKey(peak * .6f, .6f), new GradientAlphaKey(0, 1) });
            return new ParticleSystem.MinMaxGradient(g);
        }

        static Material ParticleMaterial(string name, bool lit, bool additive, Texture texture, Color color)
        {
            var path = Dir + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            var shader = Shader.Find(lit ? "Universal Render Pipeline/Particles/Simple Lit" : "Universal Render Pipeline/Particles/Unlit");
            if (!mat) { mat = new Material(shader) { name = name }; AssetDatabase.CreateAsset(mat, path); }
            mat.shader = shader;
            mat.SetTexture("_BaseMap", texture); mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", additive ? 2 : 0);
            mat.SetFloat("_SoftParticlesEnabled", 1); mat.SetFloat("_SoftParticlesNearFadeDistance", 0); mat.SetFloat("_SoftParticlesFarFadeDistance", 1.2f);
            mat.SetFloat("_CameraFadingEnabled", 1); mat.SetFloat("_CameraNearFadeDistance", .4f); mat.SetFloat("_CameraFarFadeDistance", 2.2f);
            BaseShaderGUI.SetMaterialKeywords(mat, null, ParticleGUI.SetMaterialKeywords);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // ------------------------------------------------------------------ atmosphere
        static void ApplyAtmosphere(Scene scene)
        {
            Directory.CreateDirectory(Dir);
            var clock = UnityEngine.Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include)
                ?? throw new InvalidOperationException("Ward lighting clock not found.");
            // Values before this pass, for rollback (the original assets are left unchanged).
            Record["originals"] = new
            {
                dayNightProfile = "Assets/AthenHill/Art/ReferenceStreet/20260910/ShadeBalanceV1/WardAfternoonShade.asset",
                gradeProfile = "Assets/AthenHill/Materials/AAA/AthenHillBeautyVolume.asset",
                fog = new[] { 32f, 132f },
                sky = new { material = SkyPath, coverage = .48f, wispStrength = .035f, cloudOpacity = .88f, atmosphereThickness = 1.35f, skyTint = new[] { .58f, .53f, .46f } },
                sandstoneBasin = new { hazeDensity = .0048f, haze = new[] { .62f, .58f, .51f } }
            };

            // Day/night: dustier noon and a low, warm late-afternoon default.
            var source = clock.profile;
            var profile = AssetDatabase.LoadAssetAtPath<DayNightLightingProfile>(DayNightPath);
            if (!profile)
            {
                var basePath = AssetDatabase.GetAssetPath(source).Contains("Dustbowl") ? "Assets/AthenHill/Art/ReferenceStreet/20260910/ShadeBalanceV1/WardAfternoonShade.asset" : AssetDatabase.GetAssetPath(source);
                AssetDatabase.CopyAsset(basePath, DayNightPath);
                profile = AssetDatabase.LoadAssetAtPath<DayNightLightingProfile>(DayNightPath);
            }
            var frames = profile.frames.Where(f => Mathf.Abs(f.hour - 16f) > .01f).ToList();
            int noon = frames.FindIndex(f => Mathf.Abs(f.hour - 12f) < .01f);
            var n = frames[noon];
            n.keyColor = new Color(1f, .86f, .68f); n.keyIntensity = 1.55f;
            n.fillColor = new Color(.66f, .7f, .8f); n.fillIntensity = .16f;
            n.ambientSky = new Color(.3f, .32f, .35f); n.ambientEquator = new Color(.36f, .3f, .23f); n.ambientGround = new Color(.2f, .16f, .11f);
            n.skyZenith = new Color(.33f, .4f, .47f); n.skyMiddle = new Color(.62f, .6f, .52f); n.skyHorizon = new Color(.82f, .66f, .45f);
            n.cloudLight = new Color(.93f, .82f, .64f); n.cloudShade = new Color(.5f, .47f, .44f); n.ridgeColor = new Color(.58f, .47f, .34f);
            n.fogColor = new Color(.66f, .53f, .37f); n.postExposure = -.32f; n.skyExposure = .95f;
            frames[noon] = n;
            var late = n;
            late.hour = 16f; late.keyEuler = new Vector3(24f, 168f, 0f);
            late.keyColor = new Color(1f, .72f, .46f); late.keyIntensity = 1.38f;
            late.fillColor = new Color(.6f, .66f, .8f); late.fillIntensity = .12f;
            late.ambientSky = new Color(.24f, .26f, .3f); late.ambientEquator = new Color(.33f, .26f, .19f); late.ambientGround = new Color(.17f, .13f, .09f);
            late.skyZenith = new Color(.2f, .3f, .44f); late.skyMiddle = new Color(.6f, .52f, .42f); late.skyHorizon = new Color(.86f, .58f, .33f);
            late.cloudLight = new Color(1f, .74f, .48f); late.cloudShade = new Color(.46f, .38f, .36f); late.ridgeColor = new Color(.55f, .4f, .28f);
            late.fogColor = new Color(.64f, .47f, .31f); late.sunVisibility = 1; late.lampStrength = .1f;
            late.postExposure = -.3f; late.skyExposure = .95f; late.reflectionStrength = .9f;
            frames.Insert(noon + 1, late);
            profile.frames = frames.ToArray();
            profile.defaultHour = 16f;
            if (!profile.IsValid(out var reason)) throw new InvalidOperationException(reason);
            EditorUtility.SetDirty(profile);
            clock.profile = profile; EditorUtility.SetDirty(clock);

            // Grade: warm, dusty, higher-contrast frontier look with grain and a heavier vignette.
            var grade = AssetDatabase.LoadAssetAtPath<VolumeProfile>(GradePath);
            if (!grade) { grade = ScriptableObject.CreateInstance<VolumeProfile>(); AssetDatabase.CreateAsset(grade, GradePath); }
            foreach (var child in AssetDatabase.LoadAllAssetsAtPath(GradePath).Where(o => o && o != grade).ToArray()) UnityEngine.Object.DestroyImmediate(child, true);
            grade.components.Clear();
            Add<Tonemapping>(grade).mode.Override(TonemappingMode.ACES);
            var color = Add<ColorAdjustments>(grade);
            color.postExposure.Override(-.3f); color.contrast.Override(22f); color.saturation.Override(-7f); color.colorFilter.Override(new Color(1f, .965f, .9f));
            var wb = Add<WhiteBalance>(grade); wb.temperature.Override(6f); wb.tint.Override(2f);
            var smh = Add<ShadowsMidtonesHighlights>(grade);
            smh.shadows.Override(new Vector4(.93f, .96f, 1.04f, -.05f)); smh.midtones.Override(new Vector4(1.02f, 1f, .95f, 0f)); smh.highlights.Override(new Vector4(1.04f, 1f, .92f, 0f));
            var lgg = Add<LiftGammaGain>(grade);
            lgg.lift.Override(new Vector4(1f, .98f, .95f, -.02f)); lgg.gamma.Override(new Vector4(1f, .98f, .94f, -.03f)); lgg.gain.Override(new Vector4(1.03f, 1f, .93f, 0f));
            var bloom = Add<Bloom>(grade); bloom.intensity.Override(.32f); bloom.threshold.Override(1.05f); bloom.scatter.Override(.65f); bloom.tint.Override(new Color(1f, .86f, .7f));
            var vignette = Add<Vignette>(grade); vignette.intensity.Override(.3f); vignette.smoothness.Override(.48f); vignette.color.Override(new Color(.12f, .08f, .05f));
            var grain = Add<FilmGrain>(grade); grain.type.Override(FilmGrainLookup.Medium3); grain.intensity.Override(.2f); grain.response.Override(.75f);
            var ca = Add<ChromaticAberration>(grade); ca.intensity.Override(.05f);
            EditorUtility.SetDirty(grade);
            if (clock.gradingVolume) { clock.gradingVolume.sharedProfile = grade; EditorUtility.SetDirty(clock.gradingVolume); }

            // Static fallbacks match the default frame; the clock drives them in Play Mode.
            RenderSettings.fogStartDistance = 12f; RenderSettings.fogEndDistance = 118f;
            RenderSettings.fogColor = late.fogColor;

            var sky = AssetDatabase.LoadAssetAtPath<Material>(SkyPath);
            if (sky)
            {
                sky.SetFloat("_Coverage", .53f); sky.SetFloat("_WispStrength", .07f); sky.SetFloat("_CloudOpacity", .8f);
                sky.SetFloat("_AtmosphereThickness", 1.7f); sky.SetColor("_SkyTint", new Color(.66f, .55f, .43f));
                EditorUtility.SetDirty(sky);
            }
            var basin = AssetDatabase.FindAssets("SandstoneBasin t:Material").Select(AssetDatabase.GUIDToAssetPath).Select(AssetDatabase.LoadAssetAtPath<Material>).FirstOrDefault();
            if (basin && basin.HasProperty("_HazeDensity"))
            {
                basin.SetFloat("_HazeDensity", .0068f); basin.SetColor("_Haze", new Color(.66f, .54f, .4f));
                EditorUtility.SetDirty(basin);
            }

            BuildWindborneDust(scene);
            Record["atmosphere"] = new { dayNight = DayNightPath, grade = GradePath, defaultHour = profile.defaultHour, fog = new[] { 12f, 118f } };
        }

        static void BuildWindborneDust(Scene scene)
        {
            var root = new GameObject("Windborne dust");
            SceneManager.MoveGameObjectToScene(root, scene);
            var puff = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + "SoftPuff.png");
            var streak = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + "GritStreak.png");
            var sheetMat = ParticleMaterial("DustSheet", true, false, puff, new Color(.8f, .68f, .52f, 1f));
            var gritMat = ParticleMaterial("BlowingGrit", true, false, streak, new Color(.82f, .72f, .56f, 1f));

            var sheets = NewSystem("Dust sheets", root.transform, new Vector3(0, 1.1f, 0), sheetMat, out var main);
            main.startLifetime = new ParticleSystem.MinMaxCurve(9, 14); main.startSpeed = 0;
            main.startSize = new ParticleSystem.MinMaxCurve(3.5f, 8f); main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
            main.startColor = new Color(.8f, .68f, .52f, .16f); main.maxParticles = 110;
            var em = sheets.emission; em.rateOverTime = 9;
            var shape = sheets.shape; shape.shapeType = ParticleSystemShapeType.Box; shape.scale = new Vector3(70, 1.4f, 70);
            var vel = sheets.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(1.3f, 2.6f); vel.y = new ParticleSystem.MinMaxCurve(-.05f, .12f); vel.z = new ParticleSystem.MinMaxCurve(.35f, 1f);
            var size = sheets.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .7f, 1, 1.25f));
            var col = sheets.colorOverLifetime; col.enabled = true; col.color = Fade(Color.white, Color.white, 1f, .25f);
            var rot = sheets.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-.08f, .08f);

            var grit = NewSystem("Blowing grit", root.transform, new Vector3(0, .5f, 0), gritMat, out main);
            main.startLifetime = new ParticleSystem.MinMaxCurve(.8f, 1.6f); main.startSpeed = 0;
            main.startSize = new ParticleSystem.MinMaxCurve(.02f, .045f); main.startColor = new Color(.84f, .74f, .58f, .55f); main.maxParticles = 260;
            em = grit.emission; em.rateOverTime = 75;
            shape = grit.shape; shape.shapeType = ParticleSystemShapeType.Box; shape.scale = new Vector3(30, 1f, 30);
            vel = grit.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(4f, 7.5f); vel.y = new ParticleSystem.MinMaxCurve(-.25f, .45f); vel.z = new ParticleSystem.MinMaxCurve(1f, 2.4f);
            col = grit.colorOverLifetime; col.enabled = true; col.color = Fade(Color.white, Color.white, 1f, .15f);
            var gr = grit.GetComponent<ParticleSystemRenderer>();
            gr.renderMode = ParticleSystemRenderMode.Stretch; gr.velocityScale = .1f; gr.lengthScale = 1.5f;

            var dust = root.AddComponent<WindborneDust>();
            dust.session = UnityEngine.Object.FindFirstObjectByType<GameSession>();
            var cam = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "MainCamera");
            dust.viewer = cam ? cam.transform : null;
            dust.systems = new[] { sheets, grit };
        }

        /// Review stills rendered in the Editor with the clock's default frame applied
        /// (the scene is not saved afterwards). Native build captures remain the acceptance evidence.
        public static void Capture()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var clock = UnityEngine.Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            float hour = clock.profile.defaultHour;
            var args = Environment.GetCommandLineArgs();
            int hi = Array.IndexOf(args, "-athenHour"); if (hi >= 0) hour = float.Parse(args[hi + 1], System.Globalization.CultureInfo.InvariantCulture);
            var f = clock.profile.Evaluate(hour);
            clock.keyLight.transform.rotation = Quaternion.Euler(f.keyEuler); clock.keyLight.color = f.keyColor; clock.keyLight.intensity = f.keyIntensity;
            if (clock.skyFill) { clock.skyFill.color = f.fillColor; clock.skyFill.intensity = f.fillIntensity; }
            RenderSettings.ambientMode = AmbientMode.Trilight; RenderSettings.ambientSkyColor = f.ambientSky;
            RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
            var sky = new Material(clock.timeAwareSky);
            sky.SetColor("_Zenith", f.skyZenith); sky.SetColor("_Middle", f.skyMiddle); sky.SetColor("_Horizon", f.skyHorizon);
            sky.SetColor("_CloudLight", f.cloudLight); sky.SetColor("_CloudShade", f.cloudShade); sky.SetFloat("_Exposure", f.skyExposure);
            sky.SetFloat("_SunVisibility", f.sunVisibility); sky.SetVector("_SunDirection", -clock.keyLight.transform.forward);
            RenderSettings.skybox = sky; RenderSettings.sun = clock.keyLight;
            if (clock.gradingVolume && clock.gradingVolume.sharedProfile.TryGet<ColorAdjustments>(out var ca)) ca.postExposure.value = f.postExposure;
            string tag = hi >= 0 ? "-h" + hour.ToString("0", System.Globalization.CultureInfo.InvariantCulture) : "";
            var outDir = Evidence + "captures/"; Directory.CreateDirectory(outDir);
            var shots = new (string name, Vector3 eye, Vector3 target, float fov)[]
            {
                ("market-overview", new Vector3(-27f, 5.5f, 3f), new Vector3(-39f, .8f, 0f), 60),
                ("market-lane", new Vector3(-31.5f, 1.7f, -13f), new Vector3(-37f, 1.2f, 6f), 60),
                ("stall-produce", new Vector3(-36.4f, 1.65f, 12.4f), new Vector3(-40f, 1.05f, 12f), 55),
                ("stall-pottery", new Vector3(-36.3f, 1.65f, 4.4f), new Vector3(-39.7f, 1.05f, 5.2f), 55),
                ("stall-tools", new Vector3(-36.4f, 1.65f, -10.2f), new Vector3(-39.8f, 1.2f, -10.8f), 55),
                ("stall-cloth", new Vector3(-34.6f, 1.65f, 13f), new Vector3(-34f, 1.2f, 16.6f), 55),
                ("stall-rations", new Vector3(-33.4f, 1.65f, -12.6f), new Vector3(-34f, 1.1f, -16.2f), 55),
                ("cookfire", new Vector3(-31.6f, 1.8f, -1.2f), new Vector3(-35f, .7f, -3f), 55),
            };
            var list = shots.ToList();
            foreach (var name in new[] { "cam_avenue", "cam_gate", "cam_hero", "cam_hill", "cam_grid" })
            {
                var c = scene.GetRootGameObjects().FirstOrDefault(g => g.name == name);
                if (c) list.Add((name, c.transform.position, c.transform.position + c.transform.forward * 10, c.GetComponent<Camera>() ? c.GetComponent<Camera>().fieldOfView : 60));
            }
            foreach (var s in list)
            {
                var go = new GameObject("capture");
                var cam = go.AddComponent<Camera>();
                go.transform.position = s.eye; go.transform.LookAt(s.target);
                cam.fieldOfView = s.fov; cam.nearClipPlane = .1f; cam.farClipPlane = 650;
                var data = go.AddComponent<UniversalAdditionalCameraData>();
                data.renderPostProcessing = true; data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
                data.volumeLayerMask = ~0; data.volumeTrigger = go.transform;
                var rt = new RenderTexture(1600, 900, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 };
                cam.targetTexture = rt;
                for (int i = 0; i < 3; i++) cam.Render();   // settle volumes/exposure
                RenderTexture.active = rt;
                var tex = new Texture2D(1600, 900, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, 1600, 900), 0, 0); tex.Apply();
                File.WriteAllBytes(outDir + s.name + tag + ".png", tex.EncodeToPNG());
                RenderTexture.active = null; cam.targetTexture = null; rt.Release();
                UnityEngine.Object.DestroyImmediate(go); UnityEngine.Object.DestroyImmediate(tex);
            }
        }

        static T Add<T>(VolumeProfile profile) where T : VolumeComponent
        {
            var component = ScriptableObject.CreateInstance<T>();
            component.name = typeof(T).Name;
            profile.components.Add(component);
            AssetDatabase.AddObjectToAsset(component, profile);
            return component;
        }
    }
}
