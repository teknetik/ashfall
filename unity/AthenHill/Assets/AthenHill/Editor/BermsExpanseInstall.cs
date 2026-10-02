using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
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
    /// 2 October 2026: installs the Outer Berms expansion into the saved scene from art/berms_expanse_20261002
    /// (footprint.json, sites.json, scatter.json, mesh.json and the two generated GLBs). Re-runnable: it first removes
    /// everything it made before (its roots, its extra spawns and landmarks) and re-applies the edits it makes to existing
    /// objects (those are recorded with their old values in the evidence on the first run).
    ///
    /// Scene result:
    /// * root **Basin expanse** (the mountain ring incl. the new western bowl; old **Basin mountains** inactive);
    /// * **Outer Berms/Berms expanse**: Ground (54 tiles, LOD0 collider), Boundary (box walls along the playable edge,
    ///   open at the West Gate), Scatter (rocks and scrub), Sites (props, encounters, salvage, the Warden waystation),
    ///   Trail cairns and the review cameras `cam_bx_*`; the old `Boundary colliders` are inactive;
    /// * first contact moved out past the depot rise as a pair of drones; the depot nest gains two droids;
    /// * new loot tables, tougher droid prefabs, ranged droid prefabs (when the Meshy visuals exist).
    /// </summary>
    public static class BermsExpanseInstall
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Src = BermsExpansePass.ArtSrc;
        const string Evidence = BermsExpansePass.Evidence;
        const string ArtDir = "Assets/AthenHill/Art/BermsExpanse/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/BermsExpanse/";
        const string OB = "Assets/AthenHill/Prefabs/OuterBerms/";
        const string GroundMat = "Assets/AthenHill/Art/BermsRoad/Ground/BermsGroundV2.mat";
        const string BasinMat = "Assets/AthenHill/Materials/Terrain/SandstoneBasinV3.mat";
        const string RootName = "Berms expanse", BasinRoot = "Basin expanse";
        const string Marker = " (expanse)";
        static string PathOf(Transform t) => BermsExpansePass.PathOf(t);
        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 2), (float)Math.Round(v.y, 2), (float)Math.Round(v.z, 2) };
        static JObject Json(string f) => JObject.Parse(File.ReadAllText(Src + f));

        // ------------------------------------------------------------------ loot tables (data)
        public static string Loot()
        {
            var cat = AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
            LootEntry E(string id, int lo, int hi, float chance, int pity = 0) => new LootEntry { itemId = id, minQuantity = lo, maxQuantity = hi, chance = chance, pityAfter = pity };
            var tables = new[]
            {
                new LootTable { id = "loot_feral_gunner", entries = new[] { E("droid_servo_damaged", 1, 1, 1), E("scrap_alloy", 2, 3, 1), E("nanite_residue", 2, 3, 1), E("copper_filament", 1, 2, .7f, 2), E("micro_capacitor", 1, 1, .55f, 2), E("actuator_intact", 1, 1, .14f, 5), E("lattice_shard", 1, 1, .08f) } },
                new LootTable { id = "loot_feral_lancer", entries = new[] { E("scrap_alloy", 1, 2, 1), E("nanite_residue", 2, 3, 1), E("micro_capacitor", 1, 1, .75f, 2), E("optic_lens_cracked", 1, 1, .55f, 2), E("copper_filament", 1, 1, .5f), E("lattice_shard", 1, 1, .16f, 6) } },
                new LootTable { id = "loot_berms_outer", entries = new[] { E("scrap_alloy", 2, 3, 1), E("nanite_residue", 1, 3, 1), E("copper_filament", 1, 2, .7f, 2), E("micro_capacitor", 1, 1, .45f, 3), E("optic_lens_cracked", 1, 1, .3f, 3), E("droid_servo_damaged", 1, 1, .3f), E("actuator_intact", 1, 1, .1f, 6), E("lattice_shard", 1, 1, .12f, 6) } },
                new LootTable { id = "loot_berms_outpost", entries = new[] { E("scrap_alloy", 2, 4, 1), E("nanite_residue", 2, 3, 1), E("micro_capacitor", 1, 2, .7f, 2), E("copper_filament", 1, 2, .7f), E("actuator_intact", 1, 1, .3f, 3), E("lattice_shard", 1, 1, .3f, 3), E("optic_lens_cracked", 1, 1, .35f) } },
            };
            var known = new HashSet<string>(AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset") is var city && city ? city.items.Select(i => i.id) : new string[0]);
            foreach (var t in tables) foreach (var e in t.entries) if (known.Count > 0 && !known.Contains(e.itemId)) throw new Exception("unknown item " + e.itemId);
            var list = cat.lootTables.Where(t => !tables.Any(n => n.id == t.id)).ToList();
            list.AddRange(tables);
            cat.lootTables = list.ToArray();
            EditorUtility.SetDirty(cat); AssetDatabase.SaveAssets();
            return "loot tables: " + string.Join(", ", tables.Select(t => t.id)) + $" ({cat.lootTables.Length} in all)";
        }

        // ------------------------------------------------------------------ droid prefabs
        /// Tougher melee droids (more vitality, quicker tells, a flank approach) and the two ranged droids, built from the
        /// visual prefabs of meshy/ranged-enemies-20261002 when they exist. Bolts are pooled prefabs (DroidBolt).
        public static string Droids()
        {
            var log = new List<string>();
            void Tune(string path, Action<FeralDroid, Health> f)
            {
                var root = PrefabUtility.LoadPrefabContents(path);
                try { f(root.GetComponent<FeralDroid>(), root.GetComponent<Health>()); PrefabUtility.SaveAsPrefabAsset(root, path); }
                finally { PrefabUtility.UnloadPrefabContents(root); }
                log.Add("tuned " + Path.GetFileNameWithoutExtension(path));
            }
            Tune(OB + "FeralWorkerDroid.prefab", (d, h) =>
            {
                h.max = 130; d.chaseSpeed = 3.6f; d.windupSeconds = .55f; d.recoverSeconds = .85f; d.strikeDamage = 18;
                d.aggroRadius = 18; d.leashRadius = 40; d.flank = .4f; d.idleThrottleDistance = Mathf.Max(d.idleThrottleDistance, 40);
            });
            Tune(OB + "FeralScrapDrone.prefab", (d, h) =>
            {
                h.max = 75; d.chaseSpeed = 4.8f; d.windupSeconds = .5f; d.strikeDamage = 11; d.aggroRadius = 20; d.leashRadius = 40; d.flank = .5f;
                d.idleThrottleDistance = Mathf.Max(d.idleThrottleDistance, 45);
            });
            // the Foreman keeps its 30 Sep elite tuning (1400 HP, a 20-40 s fight; GameplayV2FixesTests)
            Tune(OB + "FeralDepotForeman.prefab", (d, h) => { h.max = 1400; });
            log.Add(BuildBolts());
            log.Add(BuildRanged());
            AssetDatabase.SaveAssets();
            return string.Join("; ", log);
        }

        static Material EffectMat(string name, Color c)
        {
            var path = ArtDir + "Materials/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m) return m;
            Directory.CreateDirectory(ArtDir + "Materials");
            var src = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/OuterBerms/PistolTracer.mat");
            m = new Material(src) { name = name };
            foreach (var p in new[] { "_BaseColor", "_Color", "_TintColor" }) if (m.HasProperty(p)) m.SetColor(p, c);
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static string BuildBolts()
        {
            Directory.CreateDirectory(PrefabDir);
            var sparks = AssetDatabase.LoadAssetAtPath<GameObject>(OB + "FeralWorkerDroid.prefab").GetComponentsInChildren<ParticleSystem>(true).First(p => p.name.Contains("spark") || p.name.Contains("Spark"));
            var sfx = AssetDatabase.LoadAssetAtPath<GameObject>(OB + "FeralWorkerDroid.prefab").GetComponentInChildren<AudioSource>(true);
            AudioClip Clip(string n) => AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/" + n + ".wav");
            var made = new List<string>();
            foreach (var (name, color, core, trailW, trailT, speedTag, splashR, splashD) in new[]
            {
                ("DroidBolt_Gunner", new Color(1f, .55f, .18f, 1), new Vector3(.09f, .09f, .55f), .07f, .12f, "gunner", 0f, 0f),
                ("DroidBolt_Lancer", new Color(1f, .3f, .1f, 1), new Vector3(.18f, .18f, .9f), .16f, .2f, "lancer", 2.2f, 9f),
            })
            {
                var root = new GameObject(name);
                var bolt = root.AddComponent<DroidBolt>();
                var coreGo = GameObject.CreatePrimitive(PrimitiveType.Sphere); coreGo.name = "Core";
                Object.DestroyImmediate(coreGo.GetComponent<Collider>());
                coreGo.transform.SetParent(root.transform, false); coreGo.transform.localScale = core;
                var cr = coreGo.GetComponent<MeshRenderer>(); cr.sharedMaterial = EffectMat(name + "Core", color * 2.2f); cr.shadowCastingMode = ShadowCastingMode.Off; cr.receiveShadows = false;
                var trail = root.AddComponent<TrailRenderer>(); trail.time = trailT; trail.minVertexDistance = .2f; trail.sharedMaterial = EffectMat(name + "Trail", color);
                trail.widthCurve = new AnimationCurve(new Keyframe(0, trailW), new Keyframe(1, 0)); trail.shadowCastingMode = ShadowCastingMode.Off; trail.receiveShadows = false;
                trail.colorGradient = new Gradient { colorKeys = new[] { new GradientColorKey(color, 0), new GradientColorKey(color, 1) }, alphaKeys = new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) } };
                var imp = Object.Instantiate(sparks.gameObject, root.transform); imp.name = "Impact sparks"; imp.transform.localPosition = Vector3.zero;
                var ips = imp.GetComponent<ParticleSystem>(); var main = ips.main; main.playOnAwake = false; main.simulationSpace = ParticleSystemSimulationSpace.World;
                var audio = new GameObject("Impact audio", typeof(AudioSource)).GetComponent<AudioSource>(); audio.transform.SetParent(root.transform, false);
                audio.playOnAwake = false; audio.spatialBlend = 1; audio.rolloffMode = AudioRolloffMode.Linear; audio.minDistance = 2; audio.maxDistance = 40;
                if (sfx) audio.outputAudioMixerGroup = sfx.outputAudioMixerGroup;
                bolt.core = coreGo.transform; bolt.trail = trail; bolt.impact = ips; bolt.impactAudio = audio;
                bolt.impactClips = new[] { Clip("bolt-impact") }.Where(c => c).ToArray(); bolt.flybyClips = new[] { Clip("bolt-flyby") }.Where(c => c).ToArray();
                bolt.splashRadius = splashR; bolt.splashDamage = splashD; bolt.hitRadius = speedTag == "lancer" ? .4f : .3f;
                PrefabUtility.SaveAsPrefabAsset(root, PrefabDir + name + ".prefab");
                Object.DestroyImmediate(root);
                made.Add(name);
            }
            return "bolts: " + string.Join(", ", made);
        }

        /// The gameplay prefabs wrap the Meshy visual prefabs (Prefabs/OuterBerms/Visuals). Missing visuals: skipped.
        static string BuildRanged()
        {
            var made = new List<string>();
            var handoffPath = "../../meshy/ranged-enemies-20261002/handoff.json";
            JObject handoff = File.Exists(handoffPath) ? JObject.Parse(File.ReadAllText(handoffPath)) : null;
            var worker = AssetDatabase.LoadAssetAtPath<GameObject>(OB + "FeralWorkerDroid.prefab");
            var drone = AssetDatabase.LoadAssetAtPath<GameObject>(OB + "FeralScrapDrone.prefab");
            AudioClip Clip(string n) => AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/ElevenLabs/Combat/" + n + ".wav");
            var laserMat = EffectMat("DroidAimLaser", new Color(1f, .25f, .08f, .85f));
            foreach (var kind in new[] { "Gunner", "Lancer" })
            {
                var visualPath = OB + "Visuals/Feral" + kind + "Visual.prefab";
                var visual = AssetDatabase.LoadAssetAtPath<GameObject>(visualPath);
                if (!visual) { made.Add(kind + ": no visual yet"); continue; }
                bool hover = kind == "Lancer";
                var template = hover ? drone : worker;
                var root = new GameObject("Feral" + kind + (hover ? "Drone" : "Droid"));
                var vis = (GameObject)PrefabUtility.InstantiatePrefab(visual); vis.transform.SetParent(root.transform, false); vis.name = "Visual";
                var anim = vis.GetComponentInChildren<Animation>(true);
                var rs = vis.GetComponentsInChildren<Renderer>(true).Where(r => r is MeshRenderer || r is SkinnedMeshRenderer).ToArray();
                var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                // (skinned bounds are the whole-animation envelope, so heights come from the handoff: a 2.0 m gunner)
                float standing = hover ? 0 : 2.0f;
                var h = root.AddComponent<Health>(); h.max = hover ? 95 : 150; h.aimOffset = hover ? Vector3.zero : new Vector3(0, 1.25f, 0);
                var d = root.AddComponent<FeralDroid>();
                d.kind = hover ? DroidKind.Hover : DroidKind.Walker; d.attackMode = DroidAttack.Ranged;
                d.displayName = hover ? "Feral lancer drone" : "Feral gunner droid";
                d.boltPrefab = AssetDatabase.LoadAssetAtPath<DroidBolt>(PrefabDir + (hover ? "DroidBolt_Lancer" : "DroidBolt_Gunner") + ".prefab");
                d.muzzle = vis.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Muzzle");
                if (hover)
                {
                    d.wanderSpeed = 1.6f; d.chaseSpeed = 5.2f; d.strafeSpeed = 4.2f; d.hoverHeight = 3.4f; d.aggroRadius = 34; d.leashRadius = 60; d.fireRange = 34; d.preferredRange = 21; d.retreatRange = 9;
                    d.burstCount = 1; d.burstInterval = .2f; d.boltSpeed = 40; d.boltDamage = 20; d.aimSpread = .8f; d.leadFactor = .55f; d.windupSeconds = 1.25f; d.volleyPause = new Vector2(2.2f, 3.4f);
                    d.windupClip = Clip("lancer-charge"); d.fireClip = Clip("lancer-fire");
                    // diagonal pairs spin the same way (handoff: A, B, D, C so alternate indices counter-rotate)
                    var rotors = vis.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("Rotor ")).ToDictionary(t => t.name);
                    d.rotors = new[] { "Rotor A", "Rotor B", "Rotor D", "Rotor C" }.Where(rotors.ContainsKey).Select(n => rotors[n]).ToArray();
                    d.glowRenderers = vis.GetComponentsInChildren<Renderer>(true).Where(r => r.name.Contains("Lens")).ToArray();
                    var sphere = root.AddComponent<SphereCollider>(); sphere.radius = Mathf.Max(.6f, Mathf.Min(b.extents.x, b.extents.z) * .8f);
                    var rb = root.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false; rb.mass = 30; rb.angularDamping = .5f;
                }
                else
                {
                    d.wanderSpeed = 1.1f; d.chaseSpeed = 3.4f; d.strafeSpeed = 1.6f; d.walkStrideSpeed = 1.647f; d.runStrideSpeed = 5.847f; d.fireClipPerShot = true; d.aggroRadius = 30; d.leashRadius = 50; d.fireRange = 30; d.preferredRange = 17; d.retreatRange = 7;
                    d.burstCount = 3; d.burstInterval = .2f; d.boltSpeed = 32; d.boltDamage = 8; d.aimSpread = 1.6f; d.leadFactor = .4f; d.windupSeconds = .9f; d.volleyPause = new Vector2(1.4f, 2.6f);
                    d.windupClip = Clip("gunner-aim"); d.fireClip = Clip("gunner-fire");
                    if (anim)
                    {
                        anim.playAutomatically = false; d.animationSource = anim;
                        AnimationClip C(string n) => AnimationUtility.GetAnimationClips(anim.gameObject).FirstOrDefault(c => c && (c.name == n || c.name.EndsWith("_" + n)));
                        d.idle = C("idle"); d.walk = C("walk"); d.run = C("run"); d.attack = C("fire"); d.hit = C("hit"); d.death = C("death");
                        d.aim = C("aim"); d.strafeLeft = C("strafe_left"); d.strafeRight = C("strafe_right");
                    }
                    var smr = vis.GetComponentInChildren<SkinnedMeshRenderer>(true);
                    if (smr) { smr.updateWhenOffscreen = false; d.glowRenderers = new Renderer[] { smr }; }
                    d.feet = vis.GetComponentsInChildren<Transform>(true).Where(t => t.name.ToLower().Contains("toe")).Take(2).ToArray();
                    var cap = root.AddComponent<CapsuleCollider>(); cap.center = new Vector3(0, standing / 2, 0); cap.height = standing; cap.radius = .42f;
                    var rb = root.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false;
                }
                d.idleThrottleDistance = Mathf.Max(70, d.aggroRadius * 2.2f);
                // presentation copied from the melee template: voice, sparks, smoke, eye light, footstep clips, dust
                var t = template.GetComponent<FeralDroid>();
                d.alertClip = t.alertClip; d.strikeClip = t.strikeClip; d.hitClip = t.hitClip; d.deathClip = t.deathClip; d.footstepClips = t.footstepClips; d.footstepVolume = t.footstepVolume;
                d.glowCalm = t.glowCalm; d.glowHostile = t.glowHostile; d.glowWindup = t.glowWindup; d.motorLoop = null;
                Transform Copy(Component c) { if (!c) return null; var g = Object.Instantiate(c.gameObject, root.transform); g.name = c.gameObject.name; g.transform.localPosition = c.transform.localPosition; return g.transform; }
                var voice = Copy(t.voice); d.voice = voice ? voice.GetComponent<AudioSource>() : null;
                var sp = Copy(t.sparks); d.sparks = sp ? sp.GetComponent<ParticleSystem>() : null;
                var sm = Copy(t.smoke); d.smoke = sm ? sm.GetComponent<ParticleSystem>() : null;
                if (sm) sm.localPosition = new Vector3(0, hover ? 0 : 1.4f, 0);
                if (!hover && t.footDust) { var fd = Copy(t.footDust); d.footDust = fd.GetComponent<ParticleSystem>(); }
                if (hover && t.downwash) { var dw = Copy(t.downwash); d.downwash = dw.GetComponent<ParticleSystem>(); d.downwashRate = t.downwashRate; }
                if (hover && t.motorLoop) { var ml = Copy(t.motorLoop); d.motorLoop = ml.GetComponent<AudioSource>(); d.motorLoop.pitch = .8f; }
                var eye = t.eyeLight ? Object.Instantiate(t.eyeLight.gameObject, root.transform) : null;
                if (eye)
                {
                    eye.name = "Optic light"; d.eyeLight = eye.GetComponent<Light>();
                    var head = vis.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "Head" || x.name.ToLower() == "head");
                    if (head) { eye.transform.SetParent(head, true); eye.transform.position = head.position + root.transform.forward * .16f; }
                    else eye.transform.localPosition = hover ? new Vector3(0, .1f, .95f) : new Vector3(0, 1.8f, .18f);
                }
                // aiming laser (the tell)
                var laser = new GameObject("Aim laser", typeof(LineRenderer)).GetComponent<LineRenderer>(); laser.transform.SetParent(root.transform, false);
                laser.useWorldSpace = true; laser.positionCount = 2; laser.sharedMaterial = laserMat; laser.widthMultiplier = .02f; laser.numCapVertices = 2;
                laser.shadowCastingMode = ShadowCastingMode.Off; laser.receiveShadows = false; laser.enabled = false;
                laser.colorGradient = new Gradient { colorKeys = new[] { new GradientColorKey(new Color(1, .35f, .12f), 0), new GradientColorKey(new Color(1, .2f, .08f), 1) }, alphaKeys = new[] { new GradientAlphaKey(.9f, 0), new GradientAlphaKey(.35f, 1) } };
                d.aimLaser = laser;
                var loot = root.AddComponent<LootSource>(); loot.lootTableId = hover ? "loot_feral_lancer" : "loot_feral_gunner";
                var prefabName = root.name; var clipCount = anim ? AnimationUtility.GetAnimationClips(anim.gameObject).Length : 0;
                PrefabUtility.SaveAsPrefabAsset(root, OB + prefabName + ".prefab");
                Object.DestroyImmediate(root);
                made.Add(prefabName + (clipCount > 0 ? $" (clips: {clipCount})" : ""));
            }
            return "ranged: " + string.Join(", ", made);
        }

        // ------------------------------------------------------------------ install
        public static string Install()
        {
            AssetDatabase.Refresh();
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks && (chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks)))
                throw new Exception("Rebuild and save existing render-chunk source edits before the expansion install.");
            var rec = new Dictionary<string, object> { ["utc"] = DateTime.UtcNow.ToString("O") };
            Directory.CreateDirectory(Evidence);
            var firstRun = !File.Exists(Evidence + "rollback/before-berms-expanse.unity");
            if (firstRun) { Directory.CreateDirectory(Evidence + "rollback"); File.Copy(ScenePath, Evidence + "rollback/before-berms-expanse.unity", true); }
            var roots = scene.GetRootGameObjects();
            var berms = roots.First(g => g.name == "Outer Berms").transform;
            var session = Object.FindAnyObjectByType<GameSession>();
            var combat = Object.FindAnyObjectByType<PlayerCombat>();
            var crafting = Object.FindAnyObjectByType<CraftingSession>();
            var tutorial = berms.GetComponent<BermsTutorial>();
            // ---- remove what a previous run made
            foreach (var g in roots.Where(g => g.name == BasinRoot)) Object.DestroyImmediate(g);
            var old = berms.Find(RootName); if (old) Object.DestroyImmediate(old.gameObject);
            foreach (var e in new[] { tutorial.firstContact, tutorial.depot })
                foreach (Transform c in e.transform.Cast<Transform>().Where(c => c.name.EndsWith(Marker)).ToArray()) Object.DestroyImmediate(c.gameObject);
            var landmarks = roots.First(g => g.name == "Landmarks").transform;
            var sites = Json("sites.json");
            foreach (JObject s in sites["sites"]) { var l = landmarks.Find((string)s["landmark"] ?? "~"); if (l) Object.DestroyImmediate(l.gameObject); }
            foreach (var n in new[] { "berms_first_contact" }) { var l = landmarks.Find(n); if (l) Object.DestroyImmediate(l.gameObject); }
            var root = new GameObject(RootName).transform; root.SetParent(berms, false);

            // ---- ground tiles
            var groundMat = AssetDatabase.LoadAssetAtPath<Material>(GroundMat);
            var oldGround = berms.Find("Berms ground");
            var groundMeshes = AssetDatabase.LoadAllAssetsAtPath(ArtDir + "BermsExpanseGround.glb").OfType<Mesh>().ToDictionary(m => m.name);
            if (groundMeshes.Count == 0) throw new Exception("BermsExpanseGround.glb has no meshes (import failed?)");
            var gRoot = new GameObject("Ground").transform; gRoot.SetParent(root, false);
            var groundCols = new List<Collider> { oldGround.GetComponent<MeshCollider>() };
            int tiles = 0; long lod0 = 0, lod1 = 0;
            foreach (var name in groundMeshes.Keys.Where(k => k.EndsWith("_LOD0")).OrderBy(k => k))
            {
                var key = name.Substring(0, name.Length - 5); var m0 = groundMeshes[name]; groundMeshes.TryGetValue(key + "_LOD1", out var m1);
                var tile = new GameObject(key).transform; tile.SetParent(gRoot, false);
                Renderer Part(string n, Mesh m)
                {
                    var go = new GameObject(n, typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(tile, false);
                    go.GetComponent<MeshFilter>().sharedMesh = m; var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = groundMat;
                    r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = true;
                    GameObjectUtility.SetStaticEditorFlags(go, GameObjectUtility.GetStaticEditorFlags(oldGround.gameObject)); go.layer = oldGround.gameObject.layer;
                    return r;
                }
                var r0 = Part("LOD0", m0); var mc = r0.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = m0; groundCols.Add(mc);
                lod0 += m0.triangles.Length / 3;
                if (m1)
                {
                    var r1 = Part("LOD1", m1); lod1 += m1.triangles.Length / 3;
                    var lg = tile.gameObject.AddComponent<LODGroup>();
                    lg.SetLODs(new[] { new LOD(1f, new[] { r0 }), new LOD(0f, new[] { r1 }) });
                    lg.size = 64; lg.localReferencePoint = r0.bounds.center - tile.position;
                }
                GameObjectUtility.SetStaticEditorFlags(tile.gameObject, GameObjectUtility.GetStaticEditorFlags(oldGround.gameObject));
                tiles++;
            }
            rec["ground"] = new { tiles, lod0Triangles = lod0, lod1Triangles = lod1, material = GroundMat };
            Physics.SyncTransforms();

            // ---- basin
            var basinMat = AssetDatabase.LoadAssetAtPath<Material>(BasinMat);
            var oldBasin = roots.FirstOrDefault(g => g.name == "Basin mountains");
            var oldChunk = oldBasin ? oldBasin.GetComponentsInChildren<MeshRenderer>(true).FirstOrDefault() : null;
            var bRoot = new GameObject(BasinRoot).transform; SceneManager.MoveGameObjectToScene(bRoot.gameObject, scene);
            long basinTris = 0;
            foreach (var m in AssetDatabase.LoadAllAssetsAtPath(ArtDir + "BasinExpanse.glb").OfType<Mesh>().OrderBy(m => m.name))
            {
                var go = new GameObject(m.name, typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(bRoot, false);
                go.GetComponent<MeshFilter>().sharedMesh = m; var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = basinMat;
                if (oldChunk) { r.shadowCastingMode = oldChunk.shadowCastingMode; r.receiveShadows = oldChunk.receiveShadows; GameObjectUtility.SetStaticEditorFlags(go, GameObjectUtility.GetStaticEditorFlags(oldChunk.gameObject)); go.layer = oldChunk.gameObject.layer; }
                basinTris += m.triangles.Length / 3;
            }
            if (oldBasin) oldBasin.SetActive(false);
            rec["basin"] = new { chunks = bRoot.childCount, triangles = basinTris, oldRootInactive = oldBasin ? oldBasin.name : null };

            // ---- ground height (expanse tiles + old Berms ground only)
            float GroundY(float x, float z, float fallback = float.NaN)
            {
                var ray = new Ray(new Vector3(x, 300, z), Vector3.down); float best = float.NegativeInfinity;
                foreach (var c in groundCols) if (c && c.Raycast(ray, out var hit, 600) && hit.point.y > best) best = hit.point.y;
                return float.IsNegativeInfinity(best) ? fallback : best;
            }

            // ---- boundary: walls along the playable edge, open where the edge runs along the city wall (|z| < 44.5)
            var fp = Json("footprint.json");
            var poly = fp["playable"].Select(p => new Vector2((float)p[0], (float)p[1])).ToList();
            var oldBounds = berms.Find("Boundary colliders"); if (oldBounds) oldBounds.gameObject.SetActive(false);
            var walls = new GameObject("Boundary").transform; walls.SetParent(root, false);
            int boxes = 0;
            for (int i = 0; i < poly.Count; i++)
            {
                var a = poly[i]; var b2 = poly[(i + 1) % poly.Count];
                float len = Vector2.Distance(a, b2); int n = Mathf.Max(1, Mathf.CeilToInt(len));
                var run = new List<Vector2>();
                void Flush()
                {
                    if (run.Count >= 2)
                    {
                        var p0 = run[0]; var p1 = run[run.Count - 1]; var mid = (p0 + p1) / 2; var dir = p1 - p0;
                        float y = GroundY(mid.x, mid.y, 0);
                        var go = new GameObject("Edge wall " + boxes, typeof(BoxCollider)); go.transform.SetParent(walls, false);
                        go.transform.SetPositionAndRotation(new Vector3(mid.x, y + 9, mid.y), Quaternion.LookRotation(new Vector3(dir.x, 0, dir.y).normalized));
                        go.GetComponent<BoxCollider>().size = new Vector3(1.5f, 30, dir.magnitude + 1.5f); go.isStatic = true; boxes++;
                    }
                    run.Clear();
                }
                for (int k = 0; k <= n; k++)
                {
                    var p = Vector2.Lerp(a, b2, k / (float)n);
                    bool open = p.x > -61f && Mathf.Abs(p.y) < 44.5f;
                    if (open) Flush(); else run.Add(p);
                }
                Flush();
            }
            rec["boundary"] = new { walls = boxes, oldInactive = oldBounds ? PathOf(oldBounds) : null };

            // ---- scatter
            var sRoot = new GameObject("Scatter").transform; sRoot.SetParent(root, false);
            var groups = new Dictionary<string, Transform>();
            int scattered = 0, missing = 0;
            foreach (JObject it in Json("scatter.json")["items"])
            {
                var kind = (string)it["kind"];
                if (!groups.TryGetValue(kind, out var grp)) { grp = new GameObject(char.ToUpper(kind[0]) + kind.Substring(1)).transform; grp.SetParent(sRoot, false); groups[kind] = grp; }
                var go = Place((string)it["prefab"], grp, (float)it["x"], (float)it["z"], (float)it["yaw"], (float)it["scale"], GroundY, kind == "boulder" || kind == "rock" ? -.12f : -.03f);
                if (!go) { missing++; continue; }
                foreach (var r in go.GetComponentsInChildren<Renderer>()) if (kind != "boulder") r.shadowCastingMode = ShadowCastingMode.Off;
                if (kind == "deadwood" || kind == "stones" || kind == "scrub") foreach (var c in go.GetComponentsInChildren<Collider>()) c.enabled = false;
                scattered++;
            }
            rec["scatter"] = new { placed = scattered, missingPrefabs = missing };

            // ---- sites
            var siteRoot = new GameObject("Sites").transform; siteRoot.SetParent(root, false);
            var nodePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(OB + "SalvageHeapNode.prefab");
            var droidPrefabs = new Dictionary<string, FeralDroid>
            {
                ["worker"] = AssetDatabase.LoadAssetAtPath<FeralDroid>(OB + "FeralWorkerDroid.prefab"),
                ["drone"] = AssetDatabase.LoadAssetAtPath<FeralDroid>(OB + "FeralScrapDrone.prefab"),
                ["gunner"] = AssetDatabase.LoadAssetAtPath<FeralDroid>(OB + "FeralGunnerDroid.prefab"),
                ["lancer"] = AssetDatabase.LoadAssetAtPath<FeralDroid>(OB + "FeralLancerDrone.prefab"),
            };
            var siteRec = new List<object>(); var skippedSpawns = new List<string>(); var missingProps = new List<string>();
            int nodes = 0, spawns = 0, props = 0;
            foreach (JObject s in sites["sites"])
            {
                var c = s["centre"].Select(v => (float)v).ToArray();
                var site = new GameObject((string)s["name"]).transform; site.SetParent(siteRoot, false);
                site.position = new Vector3(c[0], GroundY(c[0], c[1], 0), c[1]);
                var propRoot = new GameObject("Props").transform; propRoot.SetParent(site, true);
                foreach (JObject p in s["props"])
                {
                    var w = p["world"].Select(v => (float)v).ToArray();
                    var go = Place((string)p["prefab"], propRoot, w[0], w[1], (float)p["yaw"], 1, GroundY, (bool?)p["main"] == true ? -.25f : -.04f);
                    if (!go) { missingProps.Add((string)p["prefab"]); continue; }
                    EnsureCollider(go); props++;
                }
                if (s["encounter"] is JObject enc && enc.HasValues)
                {
                    var eg = new GameObject("Encounter · " + (string)enc["name"]).transform; eg.SetParent(site, false); eg.position = site.position;
                    var e = eg.gameObject.AddComponent<DroidEncounter>();
                    e.displayName = (string)enc["name"]; e.player = combat; e.session = session;
                    int tier = (int)s["tier"];
                    e.activateWithin = 75; e.requirePistol = true; e.packRadius = 18; e.parkBeyond = 170;
                    e.respawnSeconds = 420; e.respawnClearance = 90; e.awaySeconds = 30;
                    var list = new List<DroidEncounter.Spawn>(); int k = 0;
                    foreach (JObject sp in enc["spawns"])
                    {
                        var kind = (string)sp["kind"];
                        if (!droidPrefabs.TryGetValue(kind, out var pf) || !pf) { skippedSpawns.Add((string)s["id"] + ":" + kind); continue; }
                        var w = sp["world"].Select(v => (float)v).ToArray();
                        var pt = new GameObject($"Spawn {++k} · {pf.name}").transform; pt.SetParent(eg, false);
                        var at = FreeSpot(new Vector2(w[0], w[1]), pf.kind == DroidKind.Walker, GroundY, site.position.y);
                        pt.SetPositionAndRotation(at, Quaternion.Euler(0, (float)sp["yaw"], 0));
                        list.Add(new DroidEncounter.Spawn { prefab = pf, point = pt }); spawns++;
                    }
                    e.spawns = list.ToArray();
                }
                foreach (JObject n in s["salvage"])
                {
                    var w = n["world"].Select(v => (float)v).ToArray();
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(nodePrefab, scene); go.name = "Salvage node · " + (string)n["name"];
                    go.transform.SetParent(site, true); go.transform.position = new Vector3(w[0], GroundY(w[0], w[1], site.position.y), w[1]);
                    var node = go.GetComponent<SalvageNode>(); node.crafting = crafting; node.lootTableId = (string)n["loot"]; node.displayName = (string)n["name"];
                    node.readyPrompt = (string)n["prompt"]; node.progressLabel = (string)n["progress"]; node.searchingPrompt = (string)n["progress"] + " hold still";
                    node.respawnSeconds = 420;
                    go.GetComponent<WorldInteractable>().range = (float)n["range"]; nodes++;
                }
                if ((bool?)s["waystation"] == true) Waystation(site, session, combat, GroundY);
                var cp = site.gameObject.AddComponent<BermsCompassPoint>(); cp.displayName = (string)s["name"];
                cp.kind = (bool?)s["waystation"] == true ? BermsCompassPoint.Kind.Waystation : BermsCompassPoint.Kind.Site;
                cp.encounter = site.GetComponentInChildren<DroidEncounter>(); cp.waystation = site.GetComponent<WardenWaystation>();
                if (s["landmark"] != null && s["landmark"].Type == JTokenType.String)
                {
                    // landmarks are approach points (QA teleports and guidance): 18 m from the centre toward the gate, on clear ground
                    var toGate = new Vector2(-58 - c[0], 0 - c[1]).normalized;
                    var ap = FreeSpot(new Vector2(c[0], c[1]) + toGate * 18, true, GroundY, site.position.y);
                    var l = new GameObject((string)s["landmark"]).transform; l.SetParent(landmarks, false); l.position = ap;
                }
                siteRec.Add(new { id = (string)s["id"], centre = V(site.position), props = propRoot.childCount, encounter = site.GetComponentInChildren<DroidEncounter>() ? site.GetComponentInChildren<DroidEncounter>().spawns.Length : 0 });
            }
            rec["sites"] = siteRec; rec["salvageNodes"] = nodes; rec["spawns"] = spawns; rec["props"] = props;
            rec["skippedSpawns"] = skippedSpawns; rec["missingProps"] = missingProps.Distinct().ToArray();

            // ---- trail cairns along the Warden routes
            var cairns = new GameObject("Trail cairns").transform; cairns.SetParent(root, false); int cairnCount = 0;
            var rng = new System.Random(20261002);
            foreach (var route in sites["routes"])
                foreach (var p in route)
                {
                    float x = (float)p[0], z = (float)p[1]; if (x > -106) continue;
                    var cg = new GameObject("Cairn " + cairnCount++).transform; cg.SetParent(cairns, false); cg.position = new Vector3(x, GroundY(x, z, 0), z);
                    string[] rocks = { "WestGate/PH_RockA", "WestGate/PH_RockB", "WestGate/PH_RockC" };
                    float y = 0;
                    for (int k = 0; k < 3; k++)
                    {
                        float sc = 1.1f - k * .3f;
                        var go = Place(rocks[rng.Next(3)], cg, x + (float)(rng.NextDouble() - .5) * .15f, z + (float)(rng.NextDouble() - .5) * .15f, rng.Next(360), sc, GroundY, -.05f);
                        if (!go) continue;
                        go.transform.position += Vector3.up * y;
                        var bb = Bounds(go); y += bb.size.y * .7f;
                        foreach (var r in go.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = ShadowCastingMode.Off;
                    }
                }
            rec["cairns"] = cairnCount;

            // ---- tutorial core: first contact moves out as a pair; the depot nest gains two droids
            var tut = Json("sites.json")["tutorial"];
            var fc = tutorial.firstContact; var fcList = fc.spawns.ToList();
            var fcWorld = tut["first_contact"].Select(t => t["world"].Select(v => (float)v).ToArray()).ToArray();
            if (firstRun) rec["firstContactWas"] = fcList.Select(s => V(s.point.position)).ToArray();
            var fc0 = new Vector3(fcWorld[0][0], GroundY(fcWorld[0][0], fcWorld[0][1], 0), fcWorld[0][1]);
            fc.transform.position = fc0;                         // the encounter root moves out with its first spawn
            fcList[0].point.position = fc0;
            fcList = fcList.Take(1).ToList();
            for (int k = 1; k < fcWorld.Length; k++)
            {
                var pt = new GameObject($"Spawn {k + 1} · FeralScrapDrone{Marker}").transform; pt.SetParent(fc.transform, false);
                pt.position = new Vector3(fcWorld[k][0], GroundY(fcWorld[k][0], fcWorld[k][1], 0), fcWorld[k][1]);
                fcList.Add(new DroidEncounter.Spawn { prefab = droidPrefabs["drone"], point = pt });
            }
            fc.spawns = fcList.ToArray(); fc.packRadius = 18;
            var depot = tutorial.depot; var dList = depot.spawns.Where(s => s.point && !s.point.name.EndsWith(Marker)).ToList();
            int di = dList.Count;
            foreach (var t in tut["depot_extra"])
            {
                var w = t["world"].Select(v => (float)v).ToArray(); var kind = (string)t["kind"]; var pf = droidPrefabs[kind];
                var pt = new GameObject($"Spawn {++di} · {pf.name}{Marker}").transform; pt.SetParent(depot.transform, false);
                pt.SetPositionAndRotation(new Vector3(w[0], GroundY(w[0], w[1], 0), w[1]), Quaternion.Euler(0, (float)(t["yaw"] ?? 0), 0));
                dList.Add(new DroidEncounter.Spawn { prefab = pf, point = pt });
            }
            depot.spawns = dList.ToArray(); depot.packRadius = 14;
            var foreman = Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include).FirstOrDefault(e => e.name.StartsWith("Depot Foreman"));
            if (foreman) foreman.packRadius = 16;
            if (firstRun) rec["tutorialLinesWas"] = new { tutorial.lineFirstContact, tutorial.lineDepot, tutorial.lineComplete };
            tutorial.lineFirstContact = "Movement past the depot rise, north of the service road. A pair of scrap drones have slipped their cluster. They back off before they dart in, so shoot on the tell, and don't let both get behind you.";
            tutorial.lineDepot = "The rest of the cluster is nested at the old machine depot, south along the road: five of them now, and they call each other in. Pull them a few at a time. Break contact if you're hurt; vitality comes back, and nano refills when you stop firing.";
            tutorial.lineComplete = "Clean work. Take that salvage to Brann at Salvage, on the north avenue inside the walls. His bench can turn a worker servo into a steadier grip for that pistol. When you're ready for more: the Berms run five hundred metres west now that the old slide's cleared. Gunner droids hold the relay knoll and lancers roost out by the Tube pylon. There's a Warden waystation past the north wash; check in there and we'll drag you back to it, not the gate.";
            var fcL = new GameObject("berms_first_contact").transform; fcL.SetParent(landmarks, false); fcL.position = fc.transform.position;
            // the way home on the compass
            var gate = new GameObject("West Gate (compass)").transform; gate.SetParent(root, false); gate.position = new Vector3(-58, 0, 1);
            var gp = gate.gameObject.AddComponent<BermsCompassPoint>(); gp.displayName = "West Gate"; gp.kind = BermsCompassPoint.Kind.Gate; gp.maxDistance = 1000;

            // ---- review cameras (player height)
            var cams = new GameObject("Berms expanse review cameras").transform; cams.SetParent(root, false);
            foreach (JObject cdef in JArray.Parse(File.ReadAllText(Src + "review_cameras.json")))
            {
                var p = cdef["pos"].Select(v => (float)v).ToArray(); var t = cdef["target"].Select(v => (float)v).ToArray();
                var pos = new Vector3(p[0], GroundY(p[0], p[2], 0) + p[1], p[2]); var tgt = new Vector3(t[0], GroundY(t[0], t[2], 0) + t[1], t[2]);
                var go = new GameObject((string)cdef["name"]); go.transform.SetParent(cams, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(tgt - pos, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = (float)(cdef["fov"] ?? 60); k.nearClipPlane = .05f; k.farClipPlane = 1600;
            }
            rec["cameras"] = cams.childCount;

            // ---- gameplay camera sees the far side of a 500 m bowl
            var view = session && session.follow ? session.follow.GetComponent<Camera>() : null;
            if (view) { if (firstRun) rec["farClipWas"] = view.farClipPlane; view.farClipPlane = Mathf.Max(view.farClipPlane, 1600); rec["farClip"] = view.farClipPlane; }

            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            var json = JsonConvert.SerializeObject(rec, Formatting.Indented);
            File.WriteAllText(Evidence + (firstRun ? "install.json" : "install-rerun.json"), json);
            return $"installed: {tiles} ground tiles, {bRoot.childCount} basin chunks, {boxes} edge walls, {scattered} scatter, {props} props, {spawns} spawns ({skippedSpawns.Count} skipped), {nodes} salvage nodes, {cairnCount} cairns";
        }

        /// A spawn point clear of props: walkers need a free standing capsule; searched in rings up to 5 m out.
        static Vector3 FreeSpot(Vector2 want, bool walker, Func<float, float, float, float> groundY, float fallback)
        {
            Physics.SyncTransforms();
            bool Free(Vector3 p) => !walker || !Physics.CheckCapsule(p + Vector3.up * .6f, p + Vector3.up * 1.7f, .45f, ~(1 << 8), QueryTriggerInteraction.Ignore);
            var first = new Vector3(want.x, groundY(want.x, want.y, fallback), want.y);
            if (Free(first)) return first;
            for (float r = .75f; r <= 5f; r += .75f)
                for (int a = 0; a < 12; a++)
                {
                    float ang = a * Mathf.PI / 6; float x = want.x + Mathf.Cos(ang) * r, z = want.y + Mathf.Sin(ang) * r;
                    var p = new Vector3(x, groundY(x, z, fallback), z);
                    if (Free(p)) return p;
                }
            return first;
        }

        static void Waystation(Transform site, GameSession session, PlayerCombat combat, Func<float, float, float, float> groundY)
        {
            var w = site.gameObject.AddComponent<WardenWaystation>();
            w.id = "berms_mid"; w.displayName = "Warden waystation"; w.session = session; w.player = combat; w.discoverRadius = 11;
            var rp = new GameObject("Respawn point").transform; rp.SetParent(site, false);
            var p = site.position + new Vector3(4, 0, -7);
            rp.SetPositionAndRotation(new Vector3(p.x, groundY(p.x, p.z, site.position.y), p.z), Quaternion.Euler(0, 90, 0));
            w.respawnPoint = rp;
            var lamp = new GameObject("Waystation lamp", typeof(Light)).GetComponent<Light>(); lamp.transform.SetParent(site, false);
            lamp.transform.position = site.position + new Vector3(0, 2.6f, 0); lamp.type = LightType.Point; lamp.range = 7; lamp.intensity = 2.2f;
            lamp.color = new Color(1f, .78f, .5f); lamp.shadows = LightShadows.None; lamp.enabled = false;
            w.foundLights = new[] { lamp };
        }

        static Bounds Bounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>().Where(r => r.enabled && !(r is ParticleSystemRenderer) && !(r is LineRenderer) && !(r is TrailRenderer)).ToArray();
            if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.one * .1f);
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); return b;
        }

        /// Prefab instance on the ground: yaw only, uniform scale, set down so no corner floats (big pieces sink a little more).
        static GameObject Place(string prefab, Transform parent, float x, float z, float yaw, float scale, Func<float, float, float, float> groundY, float sink)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/" + prefab + ".prefab");
            if (!asset) return null;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent.gameObject.scene);
            go.transform.SetParent(parent, false);
            go.transform.localScale = Vector3.one * scale;
            go.transform.SetPositionAndRotation(new Vector3(x, 0, z), Quaternion.Euler(0, yaw, 0));
            var b = Bounds(go);
            var ext = b.extents; float minY = float.PositiveInfinity, sumY = 0; int n = 0;
            foreach (var (dx, dz) in new[] { (0f, 0f), (-1f, -1f), (1f, -1f), (-1f, 1f), (1f, 1f) })
            {
                float y = groundY(b.center.x + dx * ext.x * .85f, b.center.z + dz * ext.z * .85f, float.NaN);
                if (float.IsNaN(y)) continue; minY = Mathf.Min(minY, y); sumY += y; n++;
            }
            if (n == 0) { Object.DestroyImmediate(go); return null; }
            float baseY = Mathf.Max(ext.x, ext.z) > 3 ? Mathf.Lerp(minY, sumY / n, .4f) : minY;
            float bottom = b.min.y - go.transform.position.y;
            go.transform.position = new Vector3(x, baseY - bottom + sink * Mathf.Max(1, scale), z);
            return go;
        }

        /// Big props without colliders get one box from their renderers, so they give cover and block droids.
        static void EnsureCollider(GameObject go)
        {
            if (go.GetComponentsInChildren<Collider>(true).Length > 0) return;
            var b = Bounds(go);
            if (Mathf.Max(b.size.x, b.size.z) < 1.2f || b.size.y < .8f) return;
            var box = go.AddComponent<BoxCollider>();
            var inv = go.transform.worldToLocalMatrix;
            var lc = inv.MultiplyPoint3x4(b.center);
            // renderer bounds are world AABBs; measure in local space for a snug box
            var locals = go.GetComponentsInChildren<MeshFilter>().Where(f => f.sharedMesh).SelectMany(f => { var m = inv * f.transform.localToWorldMatrix; var bb = f.sharedMesh.bounds; return new[] { m.MultiplyPoint3x4(bb.min), m.MultiplyPoint3x4(bb.max), m.MultiplyPoint3x4(new Vector3(bb.min.x, bb.min.y, bb.max.z)), m.MultiplyPoint3x4(new Vector3(bb.max.x, bb.min.y, bb.min.z)) }; }).ToArray();
            if (locals.Length > 0)
            {
                var lo = locals.Aggregate(Vector3.Min); var hi = locals.Aggregate(Vector3.Max);
                box.center = (lo + hi) / 2; box.size = (hi - lo) * .92f;
            }
            else { box.center = lc; box.size = b.size; }
        }

        // ------------------------------------------------------------------ A/B timing builds
        const string AbOn = "Assets/AthenHill/Scenes/__bx_ab_on.unity", AbOff = "Assets/AthenHill/Scenes/__bx_ab_off.unity";
        /// "on" snapshots the saved scene into two copies (expansion on; expansion off = old basin, old boundary walls,
        /// the expanse root inactive and the old 650 m far clip) and builds the on copy to Builds/bx-ab-on; "off" builds
        /// the off copy to Builds/bx-ab-off and deletes both copies. The shared saved scene is never toggled.
        public static string AbBuild(string arm)
        {
            if (arm == "on")
            {
                var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
                var roots = scene.GetRootGameObjects();
                var berms = roots.First(g => g.name == "Outer Berms").transform;
                var exp = berms.Find(RootName).gameObject; var basin = roots.First(g => g.name == BasinRoot);
                var oldBasin = roots.First(g => g.name == "Basin mountains"); var oldBounds = berms.Find("Boundary colliders").gameObject;
                var session = Object.FindAnyObjectByType<GameSession>(); var view = session.follow.GetComponent<Camera>(); float far = view.farClipPlane;
                if (!EditorSceneManager.SaveScene(scene, AbOn, true)) throw new Exception("could not write " + AbOn);
                exp.SetActive(false); basin.SetActive(false); oldBasin.SetActive(true); oldBounds.SetActive(true); view.farClipPlane = 650;
                if (!EditorSceneManager.SaveScene(scene, AbOff, true)) throw new Exception("could not write " + AbOff);
                return AbPlayer(AbOn, "bx-ab-on");
            }
            if (!File.Exists(AbOff)) throw new Exception("Run abbuild:on first (it writes both scene snapshots).");
            try { return AbPlayer(AbOff, "bx-ab-off"); }
            finally { AssetDatabase.DeleteAsset(AbOn); AssetDatabase.DeleteAsset(AbOff); }
        }
        static string AbPlayer(string src, string folder)
        {
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { src }, locationPathName = "Builds/" + folder + "/AthenHill.x86_64",
                target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
            });
            if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("build failed: " + folder);
            return folder + " " + report.summary.totalTime.TotalSeconds.ToString("0") + " s";
        }

        // ------------------------------------------------------------------ verify (saved scene)
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Physics.SyncTransforms();
            var r = new Dictionary<string, object>(); var problems = new List<string>();
            var roots = scene.GetRootGameObjects();
            var berms = roots.First(g => g.name == "Outer Berms").transform;
            var root = berms.Find(RootName); if (!root) throw new Exception("not installed");
            var basin = roots.FirstOrDefault(g => g.name == BasinRoot);
            r["basinActive"] = basin && basin.activeInHierarchy;
            r["oldBasinInactive"] = roots.Where(g => g.name == "Basin mountains").All(g => !g.activeSelf);
            var cols = root.Find("Ground").GetComponentsInChildren<MeshCollider>().Cast<Collider>().Append(berms.Find("Berms ground").GetComponent<MeshCollider>()).ToList();
            float G(Vector3 p) { var ray = new Ray(new Vector3(p.x, 300, p.z), Vector3.down); float best = float.NegativeInfinity; foreach (var c in cols) if (c.Raycast(ray, out var h, 600)) best = Mathf.Max(best, h.point.y); return best; }
            var all = root.GetComponentsInChildren<Transform>(true);
            var inst = all.Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject)).ToArray();
            r["prefabInstances"] = inst.Length;
            r["brokenPrefabLinks"] = inst.Count(t => !PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject));
            r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Concat(basin ? basin.GetComponentsInChildren<Renderer>(true) : new Renderer[0]).Count(x => x.sharedMaterials.Any(q => !q));
            var encs = root.GetComponentsInChildren<DroidEncounter>(true).Concat(new[] { berms.GetComponent<BermsTutorial>().firstContact, berms.GetComponent<BermsTutorial>().depot }).ToArray();
            int sp = 0;
            foreach (var e in encs)
                foreach (var s in e.spawns)
                {
                    sp++;
                    if (!s.prefab || !s.point) { problems.Add(e.name + ": empty spawn"); continue; }
                    float gy = G(s.point.position);
                    if (float.IsNegativeInfinity(gy)) problems.Add(PathOf(s.point) + ": no ground under spawn");
                    else if (Mathf.Abs(gy - s.point.position.y) > .6f) problems.Add(PathOf(s.point) + $": spawn {s.point.position.y:0.00} vs ground {gy:0.00}");
                    // walkers need head room (no prop over them)
                    if (s.prefab.kind == DroidKind.Walker && Physics.CheckCapsule(s.point.position + Vector3.up * .6f, s.point.position + Vector3.up * 1.7f, .35f, ~(1 << 8), QueryTriggerInteraction.Ignore))
                        problems.Add(PathOf(s.point) + ": walker spawn overlaps a collider");
                }
            r["spawns"] = sp;
            var nodes = root.GetComponentsInChildren<SalvageNode>(true);
            var cat = AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
            foreach (var n in nodes)
            {
                if (!cat.lootTables.Any(t => t.id == n.lootTableId)) problems.Add(n.name + ": unknown loot table " + n.lootTableId);
                if (float.IsNegativeInfinity(G(n.transform.position))) problems.Add(n.name + ": no ground");
            }
            r["salvageNodes"] = nodes.Length;
            r["waystation"] = root.GetComponentsInChildren<WardenWaystation>(true).Select(w => new { w.id, respawn = w.respawnPoint ? V(w.respawnPoint.position) : null }).ToArray();
            // a capsule can stand at every waystation respawn and every route cairn's foot
            foreach (var w in root.GetComponentsInChildren<WardenWaystation>(true))
                if (w.respawnPoint && Physics.CheckCapsule(w.respawnPoint.position + Vector3.up * .5f, w.respawnPoint.position + Vector3.up * 1.6f, .4f, ~(1 << 8), QueryTriggerInteraction.Ignore)) problems.Add("waystation respawn blocked");
            // the gate stays open
            var gateOpen = !Physics.CheckCapsule(new Vector3(-61, .6f, 1), new Vector3(-61, 1.6f, 1), .4f, ~(1 << 8), QueryTriggerInteraction.Ignore);
            r["gateOpen"] = gateOpen; if (!gateOpen) problems.Add("the West Gate opening is blocked");
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            r["chunksFresh"] = chunks && !chunks.editingSources && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            long tris0 = 0; foreach (var lg in root.GetComponentsInChildren<LODGroup>(true)) { var lods = lg.GetLODs(); if (lods.Length > 0) foreach (var rr in lods[0].renderers) if (rr && rr.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh) tris0 += mf.sharedMesh.triangles.Length / 3; }
            r["lod0TrianglesInExpanse"] = tris0;
            r["lights"] = root.GetComponentsInChildren<Light>(true).Length;
            r["problems"] = problems;
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(r, Formatting.Indented));
            return $"verify: {problems.Count} problems; " + string.Join(" | ", problems.Take(12));
        }
    }
}
