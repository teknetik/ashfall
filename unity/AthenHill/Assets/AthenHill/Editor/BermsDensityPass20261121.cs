using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using AthenHill;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 21 November 2026 (Phase 4 / Outer Berms density & wasteland danger): additive worldbuilding pass that fills
    /// sparse corridors between Outer Berms POIs with collapsed conveyor spines, fallen Quantum Tube pylons, Warden
    /// sandbag cover posts, Karaveen skirmish wrecks, rusted perimeter hazard fencing, industrial ambush choke points,
    /// desert boulder/scrub clusters, lightweight zero-light arc/smoke hazard markers, and BermsDangerAtmosphere.
    /// Never moves or modifies existing sites, encounters, spawns, loot, colliders or ground tiles.
    ///
    /// Menu: Athen Hill -> Outer Berms -> Install / Verify / Rollback Berms Density (2026-11-21)
    /// Batch: -executeMethod AthenHill.Editor.BermsDensityPass20261121.RunBatch --steps install,verify
    /// </summary>
    public static class BermsDensityPass20261121
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string PlacementsPath = "../../art/berms_density_20261121/placements.json";
        const string PrefabRoot = "Assets/AthenHill/Prefabs/";
        const string RootName = "Berms density";
        const string HazardGroupName = "HazardFX";
        const string AtmosphereObjectName = "BermsDangerAtmosphere";
        const string TilesPath = "Outer Berms/Berms expanse/Ground";

        [MenuItem("Athen Hill/Outer Berms/Install Berms Density (2026-11-21)")]
        public static void MenuInstall() => Debug.Log(Install());

        [MenuItem("Athen Hill/Outer Berms/Verify Berms Density (2026-11-21)")]
        public static void MenuVerify() => Debug.Log(Verify());

        [MenuItem("Athen Hill/Outer Berms/Rollback Berms Density (2026-11-21)")]
        public static void MenuRollback() => Debug.Log(Rollback());

        /// Batch entry. The merge wrapper (SH/seq.sh -> unity.sh) runs -executeMethod without -quit, so this exits Unity
        /// itself: 0 when every step passed, 1 on the first failure (21 Nov 2026 merge review).
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string stepsArg = "verify";
            for (int i = 0; i < args.Length - 1; i++)
                if (args[i] == "--steps") stepsArg = args[i + 1];
            try
            {
                foreach (var raw in stepsArg.Split(','))
                {
                    var step = raw.Trim().ToLowerInvariant();
                    string result = step == "install" ? Install() : step == "verify" ? Verify() : step == "rollback" ? Rollback()
                        : throw new ArgumentException("Unknown BermsDensityPass step: " + step);
                    Debug.Log("BermsDensityPass20261121 " + step + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        static Scene OpenScene() => EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);

        static Transform Find(Scene s, string path)
        {
            var parts = path.Split('/');
            var r = s.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!r) return null;
            var t = r.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Find(parts[i]);
            return t;
        }

        public static string Install()
        {
            var scene = OpenScene();
            var berms = Find(scene, "Outer Berms");
            var tiles = Find(scene, TilesPath);
            if (!berms || !tiles) throw new Exception("Outer Berms or expanse ground not found");

            var old = berms.Find(RootName);
            if (old) Object.DestroyImmediate(old.gameObject);

            var root = new GameObject(RootName).transform;
            root.SetParent(berms, false);

            var groundGo = Find(scene, "Outer Berms/Berms ground");
            var varietyGo = Find(scene, "Outer Berms/Berms variety");
            var groundCols = tiles.GetComponentsInChildren<MeshCollider>(true).Cast<Collider>().ToList();
            if (groundGo && groundGo.GetComponent<MeshCollider>()) groundCols.Add(groundGo.GetComponent<MeshCollider>());
            if (varietyGo) groundCols.AddRange(varietyGo.GetComponentsInChildren<MeshCollider>(true));
            Physics.SyncTransforms();

            float GroundY(float x, float z)
            {
                var ray = new Ray(new Vector3(x, 300f, z), Vector3.down);
                float best = float.NegativeInfinity;
                foreach (var c in groundCols)
                    if (c && c.Raycast(ray, out var hit, 600f) && hit.point.y > best) best = hit.point.y;
                return best;
            }

            var session = Object.FindAnyObjectByType<GameSession>();
            var player = Object.FindAnyObjectByType<PlayerCombat>();
            var cityAudio = Object.FindAnyObjectByType<CityAudio>();
            var sfxGroup = cityAudio && cityAudio.confirmation ? cityAudio.confirmation.outputAudioMixerGroup : null;

            var sparkMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/OuterBerms/BermsSparks.mat")
                ?? AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/FX/Materials/FX_Spark.mat");
            var smokeMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/FX/Materials/FX_Smoke.mat")
                ?? AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Atmosphere/Dustbowl/CookfireSmoke.mat");
            var crackleClips = new[] { "arc-crackle-1", "arc-crackle-2" }
                .Select(n => AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/" + n + ".wav"))
                .Where(c => c)
                .ToArray();

            var doc = JObject.Parse(File.ReadAllText(PlacementsPath));
            var prefabs = (JArray)doc["prefabs"];
            var groups = new Dictionary<string, Transform>();
            var cache = new Dictionary<string, GameObject>();
            var missing = new List<string>();
            int placed = 0, skippedGround = 0, arcCount = 0, smokeCount = 0;

            Transform Group(string name)
            {
                if (!groups.TryGetValue(name, out var g))
                {
                    g = new GameObject(name).transform;
                    g.SetParent(root, false);
                    groups[name] = g;
                }
                return g;
            }

            var hazardFxRoot = Group(HazardGroupName);

            foreach (JObject p in prefabs)
            {
                var rel = (string)p["prefab"];
                if (!cache.TryGetValue(rel, out var asset))
                {
                    asset = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabRoot + rel + ".prefab");
                    cache[rel] = asset;
                }
                if (!asset) { if (!missing.Contains(rel)) missing.Add(rel); continue; }

                float x = (float)p["x"], z = (float)p["z"];
                float y = GroundY(x, z);
                if (float.IsNegativeInfinity(y)) { skippedGround++; continue; }

                float sink = p["sink"] != null ? (float)p["sink"] : 0.08f;
                float yaw = p["yaw"] != null ? (float)p["yaw"] : 0f;
                float scale = p["scale"] != null ? (float)p["scale"] : 1f;
                bool shadows = p["shadows"] == null || (bool)p["shadows"];
                string colMode = p["collider"] != null ? (string)p["collider"] : "keep";
                string group = p["group"] != null ? (string)p["group"] : "Props";
                string hazard = p["hazard"] != null ? (string)p["hazard"] : null;

                var inst = (GameObject)PrefabUtility.InstantiatePrefab(asset, scene);
                inst.name = $"{Path.GetFileNameWithoutExtension(rel)}_{placed + 1:000}";
                inst.transform.SetParent(Group(group), false);
                inst.transform.position = new Vector3(x, y - sink, z);
                inst.transform.rotation = Quaternion.Euler(0, yaw, 0);
                inst.transform.localScale = Vector3.one * scale;
                GameObjectUtility.SetStaticEditorFlags(inst, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);

                foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                {
                    r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    r.receiveShadows = true;
                }
                if (colMode == "remove")
                    foreach (var c in inst.GetComponentsInChildren<Collider>(true))
                        Object.DestroyImmediate(c);

                if (hazard == "arc")
                {
                    CreateArcHazard(hazardFxRoot, $"ArcHazard_{++arcCount:00}", new Vector3(x, y + 1.35f, z), session, sparkMat, crackleClips, sfxGroup);
                }
                else if (hazard == "smoke")
                {
                    CreateSmokeHazard(hazardFxRoot, $"SmokeHazard_{++smokeCount:00}", new Vector3(x, y + 0.85f, z), smokeMat);
                }

                placed++;
            }

            WireDangerAtmosphere(root, hazardFxRoot, session, player, smokeMat, crackleClips, sfxGroup);

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return $"BERMS_DENSITY install OK: placed={placed}, arcs={arcCount}, smoke={smokeCount}, skippedGround={skippedGround}, missingPrefabs={missing.Count} ({string.Join(", ", missing)})";
        }

        static void CreateArcHazard(
            Transform parent,
            string name,
            Vector3 worldPos,
            GameSession session,
            Material sparkMat,
            AudioClip[] clips,
            UnityEngine.Audio.AudioMixerGroup sfxGroup)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.position = worldPos;

            var arc = go.AddComponent<ElectricArc>();
            arc.session = session;
            arc.flash = null; // Strictly zero real-time lights
            arc.flashIntensity = 0f;
            arc.minInterval = 3.2f;
            arc.maxInterval = 8.5f;
            arc.burst = 14;
            arc.activeDistance = 42f;
            arc.sparks = CreateSparkSystem(go.transform, sparkMat);

            if (clips != null && clips.Length > 0)
            {
                var src = go.AddComponent<AudioSource>();
                src.playOnAwake = false;
                src.spatialBlend = 1f;
                src.rolloffMode = AudioRolloffMode.Linear;
                src.minDistance = 2.5f;
                src.maxDistance = 26f;
                src.volume = 0.55f;
                src.dopplerLevel = 0f;
                src.outputAudioMixerGroup = sfxGroup;
                arc.voice = src;
                arc.clips = clips;
            }
        }

        static ParticleSystem CreateSparkSystem(Transform parent, Material mat)
        {
            var go = new GameObject("Sparks", typeof(ParticleSystem));
            go.transform.SetParent(parent, false);
            var ps = go.GetComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);

            var main = ps.main;
            main.playOnAwake = false;
            main.loop = false;
            main.duration = 0.45f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.22f, 0.55f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(1.4f, 4.4f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.02f, 0.05f);
            main.gravityModifier = 1.25f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 40;
            main.startColor = new Color(0.82f, 0.94f, 1f, 1f);

            var em = ps.emission;
            em.enabled = false;

            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = 0.08f;

            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(new Color(0.85f, 0.97f, 1f), 0f), new GradientColorKey(new Color(1f, 0.62f, 0.22f), 0.55f), new GradientColorKey(new Color(0.9f, 0.3f, 0.1f), 1f) },
                new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0f, 1f) });
            col.color = g;

            var r = go.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.045f;
            r.lengthScale = 1f;
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            return ps;
        }

        static ParticleSystem CreateSmokeHazard(Transform parent, string name, Vector3 worldPos, Material smokeMat)
        {
            var go = new GameObject(name, typeof(ParticleSystem));
            go.transform.SetParent(parent, false);
            go.transform.position = worldPos;

            var ps = go.GetComponent<ParticleSystem>();
            var main = ps.main;
            main.playOnAwake = true;
            main.loop = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(3.5f, 6.0f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.35f, 0.75f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.55f, 1.35f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.gravityModifier = -0.02f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 24;
            main.startColor = new Color(0.28f, 0.26f, 0.24f, 0.24f);

            var em = ps.emission;
            em.rateOverTime = 2.4f;

            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 16f;
            shape.radius = 0.35f;

            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.45f), new Keyframe(1f, 1.55f)));

            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(new Color(0.32f, 0.27f, 0.22f), 0f), new GradientColorKey(new Color(0.22f, 0.21f, 0.20f), 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.26f, 0.22f), new GradientAlphaKey(0f, 1f) });
            col.color = g;

            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = smokeMat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            return ps;
        }

        internal static void WireDangerAtmosphere(
            Transform root,
            Transform hazardFxRoot,
            GameSession session,
            PlayerCombat player,
            Material smokeMat,
            AudioClip[] crackleClips,
            UnityEngine.Audio.AudioMixerGroup sfxGroup)
        {
            var go = new GameObject(AtmosphereObjectName);
            go.transform.SetParent(root, false);

            var atmo = go.AddComponent<BermsDangerAtmosphere>();
            atmo.session = session;
            atmo.player = player;
            atmo.hazardRoot = hazardFxRoot;
            atmo.dangerZones = BermsDangerMath.DefaultTier3Zones();
            atmo.crackleClips = crackleClips ?? Array.Empty<AudioClip>();
            if (player) atmo.cityEdgeX = player.cityEdgeX;

            var ashGo = new GameObject("AshWisps", typeof(ParticleSystem));
            ashGo.transform.SetParent(go.transform, false);
            var ash = ashGo.GetComponent<ParticleSystem>();
            ash.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ash.main;
            main.playOnAwake = false;
            main.loop = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(2.2f, 4.2f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.4f, 1.3f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.25f, 0.7f);
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 60;
            main.startColor = new Color(0.48f, 0.42f, 0.36f, 0.16f);

            var em = ash.emission;
            em.rateOverTime = 0f;

            var shape = ash.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(14f, 1.2f, 14f);

            var col = ash.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(new Color(0.55f, 0.47f, 0.39f), 0f), new GradientColorKey(new Color(0.35f, 0.32f, 0.28f), 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.18f, 0.3f), new GradientAlphaKey(0f, 1f) });
            col.color = g;

            var ashRenderer = ashGo.GetComponent<ParticleSystemRenderer>();
            ashRenderer.sharedMaterial = smokeMat;
            ashRenderer.shadowCastingMode = ShadowCastingMode.Off;
            ashRenderer.receiveShadows = false;
            atmo.ashWisps = ash;

            var src = go.AddComponent<AudioSource>();
            src.playOnAwake = false;
            src.spatialBlend = 0f;
            src.volume = 1f;
            src.dopplerLevel = 0f;
            src.outputAudioMixerGroup = sfxGroup;
            atmo.crackleSource = src;
        }

        const string Evidence = "../evidence/gemini_merge/20261121/berms_density/";
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        /// Checks the saved scene: renderers and materials, no lights, the hazard FX and the danger controller wired, and
        /// (added in the 21 Nov 2026 merge review) that no collider of this pass stands within reach of a gameplay
        /// point: droid spawns 3 m, salvage nodes, interactables and loot 2.5 m, waystations and the respawn 4 m
        /// (the same capsule test BermsVarietyPass20261120 uses). Writes verify.json; throws on any problem.
        public static string Verify()
        {
            var scene = OpenScene();
            Physics.SyncTransforms();
            var root = Find(scene, "Outer Berms/" + RootName);
            if (!root) throw new Exception("Berms density root not found");
            var problems = new List<string>();
            int renderers = root.GetComponentsInChildren<Renderer>(false).Length;
            int missingMats = root.GetComponentsInChildren<Renderer>(false)
                .Count(r => r.sharedMaterials == null || r.sharedMaterials.Any(m => !m));
            if (renderers == 0) problems.Add("0 active renderers");
            if (missingMats > 0) problems.Add($"{missingMats} renderers with missing materials");
            int lights = root.GetComponentsInChildren<Light>(true).Length;
            if (lights > 0) problems.Add($"must add 0 real-time lights, found {lights}");
            var atmo = root.GetComponentInChildren<BermsDangerAtmosphere>(true);
            if (!atmo) problems.Add("BermsDangerAtmosphere component not found");
            else if (!atmo.session || !atmo.player || !atmo.ashWisps) problems.Add("BermsDangerAtmosphere is missing scene references (session/player/ashWisps)");
            int arcs = root.GetComponentsInChildren<ElectricArc>(true).Length;
            var fx = root.Find(HazardGroupName);
            int smoke = fx ? fx.Cast<Transform>().Count(t => t.name.StartsWith("SmokeHazard_")) : 0;
            if (arcs == 0 || smoke == 0) problems.Add($"hazard FX missing: arcs={arcs}, smoke={smoke}");
            int expected = ((JArray)JObject.Parse(File.ReadAllText(PlacementsPath))["prefabs"]).Count;
            int props = root.Cast<Transform>().Where(g => g.name != HazardGroupName && g.name != AtmosphereObjectName).Sum(g => g.childCount);

            var mine = new HashSet<Collider>(root.GetComponentsInChildren<Collider>(true).Where(c => c.enabled && c.gameObject.activeInHierarchy));
            var crowded = new List<string>();
            int checkedPoints = 0;
            void Clear(string kind, Transform t, float clear)
            {
                if (!t || t.IsChildOf(root)) return;
                checkedPoints++;
                var near = Physics.OverlapCapsule(t.position + Vector3.up * (.3f + clear), t.position + Vector3.up * Mathf.Max(1.8f, .3f + clear), clear, ~0, QueryTriggerInteraction.Ignore);
                var hit = near.FirstOrDefault(c => mine.Contains(c));
                if (hit) crowded.Add($"{kind} {PathOf(t)} within {clear} m of {PathOf(hit.transform)}");
            }
            foreach (var e in Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (e.spawns != null) foreach (var sp in e.spawns) if (sp != null) Clear("spawn", sp.point, 3f);
            foreach (var n in Object.FindObjectsByType<SalvageNode>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Clear("salvage", n.transform, 2.5f);
            foreach (var w in Object.FindObjectsByType<WorldInteractable>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Clear("interactable", w.transform, 2.5f);
            foreach (var l in Object.FindObjectsByType<LootSource>(FindObjectsInactive.Include, FindObjectsSortMode.None)) if (!l.GetComponent<FeralDroid>()) Clear("loot", l.transform, 2.5f);
            foreach (var w in Object.FindObjectsByType<WardenWaystation>(FindObjectsInactive.Include, FindObjectsSortMode.None)) { Clear("waystation", w.transform, 4f); Clear("respawn", w.respawnPoint, 4f); }
            problems.AddRange(crowded);

            var report = new JObject
            {
                ["utc"] = DateTime.UtcNow.ToString("o"), ["pass"] = problems.Count == 0, ["problems"] = new JArray(problems),
                ["placementsInJson"] = expected, ["propsInScene"] = props, ["renderers"] = renderers, ["lights"] = lights,
                ["arcs"] = arcs, ["smoke"] = smoke, ["dangerZones"] = atmo && atmo.dangerZones != null ? atmo.dangerZones.Length : 0,
                ["gameplayPointsChecked"] = checkedPoints, ["colliders"] = mine.Count,
            };
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", report.ToString());
            if (problems.Count > 0) throw new Exception("BERMS_DENSITY verify FAIL: " + string.Join("; ", problems.Take(20)));
            return $"BERMS_DENSITY verify PASS: props={props}/{expected}, renderers={renderers}, lights=0, arcs={arcs}, smoke={smoke}, gameplay points checked={checkedPoints}, colliders={mine.Count}";
        }

        public static string Rollback()
        {
            var scene = OpenScene();
            var root = Find(scene, "Outer Berms/" + RootName);
            if (!root) return "BERMS_DENSITY rollback: root already absent";
            Object.DestroyImmediate(root.gameObject);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "BERMS_DENSITY rollback OK: removed " + RootName;
        }
    }
}
