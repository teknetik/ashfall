using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// 22 Nov 2026: Idempotent Outer Berms progression pass.
    /// - Tunes Band 2/3 ranged droid prefabs: FeralGunnerDroid boltDamage=17, FeralLancerDrone boltDamage=30,
    ///   FeralPostSentinel boltDamage=24 (restored to 8/20/16 on rollback).
    /// - Wires LatticeTerminal onto the berms_mid WardenWaystation under Outer Berms/Berms progression.
    /// - Places initial FieldDataSlate, LockedSalvageCache (all 3 lock types), and SurveyCairn instances
    ///   under Outer Berms/Berms progression in AthenHill.unity.
    ///
    /// Batch: -executeMethod AthenHill.Editor.BermsProgressionPass20261122.RunBatch -nographics --steps install,verify|rollback
    public static class BermsProgressionPass20261122
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string RootName = "Berms progression";
        const string GunnerPrefab = "Assets/AthenHill/Prefabs/OuterBerms/FeralGunnerDroid.prefab";
        const string LancerPrefab = "Assets/AthenHill/Prefabs/OuterBerms/FeralLancerDrone.prefab";
        const string SentinelPrefab = "Assets/AthenHill/Prefabs/OuterBerms/FeralPostSentinel.prefab";

        static readonly (string path, float tuned, float baseline)[] DroidTuning =
        {
            (GunnerPrefab, 17f, 8f),
            (LancerPrefab, 30f, 20f),
            (SentinelPrefab, 24f, 16f),
        };

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 && i + 1 < args.Length ? args[i + 1].Split(',') : new[] { "verify" };
            try
            {
                foreach (var st in steps)
                {
                    string r = st == "install" ? Install()
                        : st == "verify" ? Verify()
                        : st == "rollback" ? Rollback()
                        : throw new Exception("unknown step " + st);
                    Debug.Log("BermsProgressionPass20261122 " + st + ": " + r);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                EditorApplication.Exit(1);
            }
        }

        static Transform Berms(UnityEngine.SceneManagement.Scene scene)
        {
            var b = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Outer Berms");
            if (!b) throw new Exception("Outer Berms root not found");
            return b.transform;
        }

        static float GroundY(float x, float z, float fallbackY)
        {
            if (Physics.Raycast(new Vector3(x, fallbackY + 40f, z), Vector3.down, out var hit, 120f))
                return hit.point.y;
            return fallbackY;
        }

        static void ApplyPrefabTuning(bool install)
        {
            foreach (var (path, tuned, baseline) in DroidTuning)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (!prefab) throw new Exception("Droid prefab missing: " + path);
                var droid = prefab.GetComponent<FeralDroid>();
                if (!droid) throw new Exception("FeralDroid component missing on: " + path);
                float target = install ? tuned : baseline;
                if (!Mathf.Approximately(droid.boltDamage, target))
                {
                    droid.boltDamage = target;
                    EditorUtility.SetDirty(droid);
                    PrefabUtility.SavePrefabAsset(prefab);
                }
            }
            AssetDatabase.SaveAssets();
        }

        public static string Install()
        {
            ApplyPrefabTuning(true);

            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var berms = Berms(scene);
            var old = berms.Find(RootName);
            if (old) Object.DestroyImmediate(old.gameObject);

            var root = new GameObject(RootName).transform;
            root.SetParent(berms, false);

            var session = Object.FindAnyObjectByType<GameSession>();
            var waystation = Object.FindObjectsByType<WardenWaystation>(FindObjectsInactive.Include)
                .FirstOrDefault(w => w.id == LatticeTerminalLogic.DefaultWaystationId);
            if (!waystation) throw new Exception("WardenWaystation berms_mid not found in scene");

            // 1. Wire LatticeTerminal onto berms_mid WardenWaystation
            var terminalGo = BuildLatticeTerminal(root, waystation, session);
            var terminal = terminalGo.GetComponent<LatticeTerminal>();
            waystation.terminal = terminal;
            EditorUtility.SetDirty(waystation);

            // 2. Place initial FieldDataSlate instances across Bands 1-3
            var slatesRoot = new GameObject("Field Data Slates").transform;
            slatesRoot.SetParent(root, false);
            var baseY = waystation.transform.position.y;
            (string id, Vector3 xz)[] slateSpecs =
            {
                ("slate_northgate_watch", new Vector3(-96f, baseY, 26f)),
                ("slate_karaveen_manifest", new Vector3(-135f, baseY, -28f)),
                ("slate_waystation_handoff", waystation.transform.position + new Vector3(-3.2f, 0f, 2.4f)),
                ("slate_tube_branch_09", new Vector3(-218f, baseY, 44f)),
                ("slate_relay_knoll_stand", new Vector3(-256f, baseY, -46f)),
                ("slate_orbital_silence", new Vector3(-345f, baseY, 18f)),
            };
            foreach (var (id, pos) in slateSpecs)
                BuildDataSlate(slatesRoot, id, pos);

            // 3. Place initial LockedSalvageCache instances (all 3 lock types)
            var cachesRoot = new GameObject("Locked Salvage Caches").transform;
            cachesRoot.SetParent(root, false);
            BuildLockedCache(cachesRoot, "cache_inner_padlock", "Padlocked Warden Crate", CacheLockType.Padlock,
                "loot_berms_outer", new Vector3(-124f, baseY, 18f), "", "");
            BuildLockedCache(cachesRoot, "cache_mid_junction", "Powered Salvage Locker", CacheLockType.JunctionBox,
                "loot_berms_outpost", new Vector3(-206f, baseY, -22f), "micro_capacitor", "");
            BuildLockedCache(cachesRoot, "cache_northgate_cipher", "Warden Cipher Crate", CacheLockType.CipherCrate,
                "loot_nextlevel_crate", new Vector3(-152f, baseY, 46f), "", "417");

            // 4. Place initial SurveyCairn vantage points across Bands 1-3
            var cairnsRoot = new GameObject("Survey Cairns").transform;
            cairnsRoot.SetParent(root, false);
            BuildSurveyCairn(cairnsRoot, "cairn_inner_ridge", "Inner Ridge Survey Cairn", new Vector3(-118f, baseY, -42f), 140f);
            BuildSurveyCairn(cairnsRoot, "cairn_mid_overlook", "Waystation Overlook Cairn", new Vector3(-228f, baseY, 64f), 140f);
            BuildSurveyCairn(cairnsRoot, "cairn_outer_rim", "Outer Rim Survey Cairn", new Vector3(-336f, baseY, -54f), 140f);

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);

            return $"installed under Outer Berms/{RootName} (1 LatticeTerminal, {slateSpecs.Length} slates, 3 locked caches, 3 survey cairns; prefabs tuned)";
        }

        static GameObject BuildLatticeTerminal(Transform parent, WardenWaystation waystation, GameSession session)
        {
            var go = new GameObject("Waystation Lattice Relay");
            go.transform.SetParent(parent, false);
            var wp = waystation.transform.position + new Vector3(2.4f, 0f, -2.2f);
            go.transform.position = new Vector3(wp.x, GroundY(wp.x, wp.z, waystation.transform.position.y), wp.z);

            // Simple kiosk plinth + beacon screen
            var plinth = GameObject.CreatePrimitive(PrimitiveType.Cube);
            plinth.name = "KioskBody";
            plinth.transform.SetParent(go.transform, false);
            plinth.transform.localPosition = new Vector3(0f, 0.85f, 0f);
            plinth.transform.localScale = new Vector3(0.65f, 1.7f, 0.45f);

            var screen = GameObject.CreatePrimitive(PrimitiveType.Cube);
            screen.name = "StatusScreen";
            screen.transform.SetParent(go.transform, false);
            screen.transform.localPosition = new Vector3(0f, 1.25f, 0.24f);
            screen.transform.localScale = new Vector3(0.46f, 0.42f, 0.04f);
            Object.DestroyImmediate(screen.GetComponent<Collider>());

            var lightGo = new GameObject("StatusLight", typeof(Light));
            lightGo.transform.SetParent(go.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 1.55f, 0.35f);
            var light = lightGo.GetComponent<Light>();
            light.type = LightType.Point;
            light.range = 4.5f;
            light.intensity = 1.4f;
            light.color = new Color(1f, 0.65f, 0.15f);

            var wi = go.AddComponent<WorldInteractable>();
            wi.prompt = LatticeTerminalLogic.PromptText(false, false, false, LatticeTerminalLogic.DefaultDisplayName);
            wi.range = 3.2f;

            var term = go.AddComponent<LatticeTerminal>();
            term.terminalId = LatticeTerminalLogic.DefaultWaystationId;
            term.displayName = LatticeTerminalLogic.DefaultDisplayName;
            term.requiredKeyId = LatticeTerminalLogic.DefaultKeyId;
            term.session = session;
            term.waystation = waystation;
            term.wakePoint = waystation.respawnPoint ? waystation.respawnPoint : waystation.transform;
            term.statusLights = new[] { light };
            term.statusRenderers = new[] { screen.GetComponent<Renderer>() };
            term.consumeKeyOnUnlock = false;

            return go;
        }

        static GameObject BuildDataSlate(Transform parent, string slateId, Vector3 pos)
        {
            var go = new GameObject("FieldSlate_" + slateId);
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(pos.x, GroundY(pos.x, pos.z, pos.y) + 0.08f, pos.z);

            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            body.name = "SlateMesh";
            body.transform.SetParent(go.transform, false);
            body.transform.localScale = new Vector3(0.32f, 0.04f, 0.22f);
            Object.DestroyImmediate(body.GetComponent<Collider>());

            var lightGo = new GameObject("SlateGlow", typeof(Light));
            lightGo.transform.SetParent(go.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 0.25f, 0f);
            var light = lightGo.GetComponent<Light>();
            light.type = LightType.Point;
            light.range = 2.5f;
            light.intensity = 0.8f;

            var wi = go.AddComponent<WorldInteractable>();
            wi.prompt = "E · Read field data slate";
            wi.range = 2.6f;

            var slate = go.AddComponent<FieldDataSlate>();
            slate.slateId = slateId;
            slate.statusLight = light;
            slate.screenRenderers = new[] { body.GetComponent<Renderer>() };
            return go;
        }

        static GameObject BuildLockedCache(Transform parent, string cacheId, string displayName, CacheLockType lockType,
            string lootTableId, Vector3 pos, string requiredItemId, string cipherCode)
        {
            var go = new GameObject("LockedCache_" + cacheId);
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(pos.x, GroundY(pos.x, pos.z, pos.y), pos.z);

            var crate = GameObject.CreatePrimitive(PrimitiveType.Cube);
            crate.name = "CrateBody";
            crate.transform.SetParent(go.transform, false);
            crate.transform.localPosition = new Vector3(0f, 0.4f, 0f);
            crate.transform.localScale = new Vector3(1.1f, 0.8f, 0.75f);

            var lockVis = GameObject.CreatePrimitive(PrimitiveType.Cube);
            lockVis.name = "LockVisual";
            lockVis.transform.SetParent(go.transform, false);
            lockVis.transform.localPosition = new Vector3(0f, 0.45f, 0.4f);
            lockVis.transform.localScale = new Vector3(0.18f, 0.22f, 0.08f);

            Health padlockHealth = null;
            if (lockType == CacheLockType.Padlock)
            {
                padlockHealth = lockVis.AddComponent<Health>();
                padlockHealth.max = 20f;
            }
            else
            {
                Object.DestroyImmediate(lockVis.GetComponent<Collider>());
            }

            var lightGo = new GameObject("CacheLight", typeof(Light));
            lightGo.transform.SetParent(go.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 0.95f, 0.25f);
            var light = lightGo.GetComponent<Light>();
            light.type = LightType.Point;
            light.range = 3.0f;
            light.intensity = 0.9f;

            var wi = go.AddComponent<WorldInteractable>();
            wi.prompt = "E · " + displayName;
            wi.range = 2.8f;

            var cache = go.AddComponent<LockedSalvageCache>();
            cache.cacheId = cacheId;
            cache.displayName = displayName;
            cache.lockType = lockType;
            cache.lootTableId = lootTableId;
            if (!string.IsNullOrEmpty(requiredItemId)) cache.requiredItemId = requiredItemId;
            if (!string.IsNullOrEmpty(cipherCode)) cache.requiredCipherCode = cipherCode;
            cache.padlockHealth = padlockHealth;
            cache.lockVisual = lockVis;
            cache.statusLight = light;
            return go;
        }

        static GameObject BuildSurveyCairn(Transform parent, string cairnId, string displayName, Vector3 pos, float radius)
        {
            var go = new GameObject("SurveyCairn_" + cairnId);
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(pos.x, GroundY(pos.x, pos.z, pos.y), pos.z);

            var pole = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            pole.name = "TripodMast";
            pole.transform.SetParent(go.transform, false);
            pole.transform.localPosition = new Vector3(0f, 1.1f, 0f);
            pole.transform.localScale = new Vector3(0.18f, 1.1f, 0.18f);

            var lightGo = new GameObject("BeaconLight", typeof(Light));
            lightGo.transform.SetParent(go.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 2.3f, 0f);
            var light = lightGo.GetComponent<Light>();
            light.type = LightType.Point;
            light.range = 4.0f;
            light.intensity = 1.1f;

            var wi = go.AddComponent<WorldInteractable>();
            wi.prompt = "E · Survey area (" + displayName + ")";
            wi.range = 3.0f;

            var cairn = go.AddComponent<SurveyCairn>();
            cairn.cairnId = cairnId;
            cairn.displayName = displayName;
            cairn.surveyRadius = radius;
            cairn.beaconLight = light;
            return go;
        }

        public static string Verify()
        {
            var problems = new List<string>();

            // 1. Check droid prefab boltDamage tuning
            foreach (var (path, tuned, _) in DroidTuning)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                var droid = prefab ? prefab.GetComponent<FeralDroid>() : null;
                if (!droid) problems.Add("missing FeralDroid on " + path);
                else if (!Mathf.Approximately(droid.boltDamage, tuned))
                    problems.Add($"{path} boltDamage={droid.boltDamage} (want {tuned})");
            }

            // 2. Check scene placement under Outer Berms/Berms progression
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = Berms(scene).Find(RootName);
            if (!root)
            {
                problems.Add("Outer Berms/" + RootName + " missing");
            }
            else
            {
                var term = root.GetComponentInChildren<LatticeTerminal>(true);
                if (!term) problems.Add("LatticeTerminal missing under " + RootName);
                else
                {
                    if (term.terminalId != LatticeTerminalLogic.DefaultWaystationId) problems.Add("LatticeTerminal terminalId != berms_mid");
                    if (term.requiredKeyId != LatticeTerminalLogic.DefaultKeyId) problems.Add("LatticeTerminal requiredKeyId != berms_relay_key");
                    if (!term.waystation || term.waystation.id != LatticeTerminalLogic.DefaultWaystationId) problems.Add("LatticeTerminal not wired to berms_mid waystation");
                    if (term.waystation && term.waystation.terminal != term) problems.Add("berms_mid waystation.terminal does not reference LatticeTerminal");
                    if (!term.session) problems.Add("LatticeTerminal session reference missing");
                }

                var slates = root.GetComponentsInChildren<FieldDataSlate>(true);
                if (slates.Length < 4) problems.Add($"expected >=4 FieldDataSlate, found {slates.Length}");
                foreach (var s in slates)
                    if (FieldSlateCatalog.Find(s.slateId) == null)
                        problems.Add("unknown slateId: " + s.slateId);

                var catalog = AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
                var caches = root.GetComponentsInChildren<LockedSalvageCache>(true);
                if (caches.Length < 3) problems.Add($"expected >=3 LockedSalvageCache, found {caches.Length}");
                foreach (var c in caches)
                {
                    if (catalog && !catalog.lootTables.Any(t => t.id == c.lootTableId))
                        problems.Add("unknown lootTableId on cache " + c.cacheId + ": " + c.lootTableId);
                    if (c.lockType == CacheLockType.Padlock && !c.padlockHealth)
                        problems.Add("padlock cache missing padlockHealth: " + c.cacheId);
                }

                var cairns = root.GetComponentsInChildren<SurveyCairn>(true);
                if (cairns.Length < 2) problems.Add($"expected >=2 SurveyCairn, found {cairns.Length}");
            }

            if (problems.Count > 0)
                throw new Exception("verify FAIL: " + string.Join("; ", problems));

            return "verify PASS";
        }

        public static string Rollback()
        {
            ApplyPrefabTuning(false);

            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var waystation = Object.FindObjectsByType<WardenWaystation>(FindObjectsInactive.Include)
                .FirstOrDefault(w => w.id == LatticeTerminalLogic.DefaultWaystationId);
            if (waystation && waystation.terminal)
            {
                waystation.terminal = null;
                EditorUtility.SetDirty(waystation);
            }

            var root = Berms(scene).Find(RootName);
            if (root) Object.DestroyImmediate(root.gameObject);

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "rolled back Outer Berms/" + RootName + " and restored droid prefab boltDamage";
        }
    }
}
