using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace AthenHill.Editor
{
    /// <summary>
    /// 26 September 2026: Outer Berms combat primer beyond the market gate (west wall, behind the Karaveen truck).
    /// Opens a 7 m gap in the west boundary wall (original wall kept inactive for rollback; the two new
    /// segments are clipped copies of its mesh and join the render chunks), lays a walkable ground mesh over
    /// the basin floor using the basin's own material and vertex lighting, and places the Warden post, range,
    /// service road and machine depot. Enemy/target/pistol prefabs are built from the Meshy sources in
    /// meshy/outer-berms-20260926. Gameplay is serialized on the "Outer Berms" root (BermsTutorial,
    /// DroidEncounter spawn points) and on Player (Health, PlayerCombat). No other scene object moves.
    /// </summary>
    public static class OuterBermsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Art = "Assets/AthenHill/Art/OuterBerms/";
        const string Prefabs = "Assets/AthenHill/Prefabs/OuterBerms/";
        const string Audio = "Assets/AthenHill/Audio/ElevenLabs/Combat/";
        const string RootName = "Outer Berms";
        const string CamerasName = "Outer Berms review cameras";
        const string WallName = "AuthoredWorld/BLD_boundary_side.001";
        const string WallCollider = "AuthoredWorld/COL_BLD_boundary_side.001";
        const string SegmentPrefix = "BLD_berms_gate_wall_";
        const string Evidence = "../evidence/outer-berms/20260926/";
        const float GapSouth = -2.5f, GapNorth = 4.5f;
        const float X0 = -104, X1 = -60, Z0 = -54, Z1 = 48;
        static readonly Vector2[] Road = { new(-58, .5f), new(-66, .5f), new(-75, -2.5f), new(-82, -10), new(-85, -21), new(-83, -31), new(-80, -37) };
        const float RoadHalf = 2.6f;
        static readonly Vector2 DepotCenter = new(-80, -41);
        const float DepotRadius = 8.5f;
        // mounds: centre x/z, radii x/z, height
        static readonly (float x, float z, float rx, float rz, float h)[] Mounds =
        {
            (-85, 16, 3.5f, 9, 2.4f),      // range backstop
            (-71, -9, 2.5f, 3.5f, 1.0f), (-91, -14, 3, 4, 1.3f), (-72, -27, 3, 3, 1.1f), (-93, -30, 3.5f, 5, 1.6f),
            (-70, 34, 6, 4, 1.8f), (-90, 37, 7, 5, 2.2f), (-66, 22, 3, 5, 1.2f), (-70, -50, 8, 3, 1.6f), (-95, 6, 4, 6, 1.8f),
        };
        static readonly Dictionary<string, object> Record = new();

        [MenuItem("Athen Hill/Outer Berms/Install combat primer")]
        public static void InstallMenu()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (scene.GetRootGameObjects().Any(g => g.name == RootName))
                throw new InvalidOperationException("The Outer Berms primer is already installed. Edit its scene objects and prefabs instead.");
            Install(scene);
        }

        /// Authoring entry point: removes only this pass's own objects (and restores the original wall) before reinstalling.
        public static void RunAll()
        {
            AssetDatabase.Refresh();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            CheckChunks();
            var roots = scene.GetRootGameObjects();
            foreach (var old in roots.Where(g => g.name == RootName || g.name == CamerasName).ToArray()) UnityEngine.Object.DestroyImmediate(old);
            var world = roots.First(g => g.name == "AuthoredWorld").transform;
            foreach (Transform t in world.Cast<Transform>().Where(t => t.name.StartsWith(SegmentPrefix) || t.name.StartsWith("COL_" + SegmentPrefix)).ToArray())
                UnityEngine.Object.DestroyImmediate(t.gameObject);
            Find(scene, WallName).gameObject.SetActive(true); Find(scene, WallCollider).gameObject.SetActive(true);
            var player = roots.First(g => g.name == "Player");
            foreach (var c in player.GetComponents<PlayerCombat>()) UnityEngine.Object.DestroyImmediate(c);
            foreach (var c in player.GetComponents<Health>()) UnityEngine.Object.DestroyImmediate(c);
            foreach (Transform t in player.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("Berms ")).ToArray()) if (t) UnityEngine.Object.DestroyImmediate(t.gameObject);
            var hud = roots.First(g => g.name == "City HUD");
            foreach (var c in hud.GetComponents<CombatHud>()) UnityEngine.Object.DestroyImmediate(c);
            Install(scene, false);
        }

        static StaticRenderChunks CheckChunks()
        {
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Rebuild and save existing source edits before the Outer Berms pass.");
            return chunks;
        }

        static void Install(Scene scene, bool check = true)
        {
            Record.Clear();
            var chunks = check ? CheckChunks() : UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            Directory.CreateDirectory(Prefabs);
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            var cityAudio = UnityEngine.Object.FindAnyObjectByType<CityAudio>();
            var sfxGroup = cityAudio && cityAudio.confirmation ? cityAudio.confirmation.outputAudioMixerGroup : null;

            var sparksMat = CopyMaterial("Assets/AthenHill/Art/Atmosphere/Dustbowl/CookfireFlame.mat", Art + "BermsSparks.mat", new Color(1f, .62f, .24f));
            var tracerMat = CopyMaterial("Assets/AthenHill/Art/Atmosphere/Dustbowl/CookfireFlame.mat", Art + "PistolTracer.mat", new Color(.35f, .84f, .86f));
            var smokeMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Atmosphere/Dustbowl/CookfireSmoke.mat");

            var worker = BuildWorkerDroid(sfxGroup, sparksMat, smokeMat);
            var drone = BuildScrapDrone(sfxGroup, sparksMat, smokeMat);
            var target = BuildRangeTarget(sfxGroup, sparksMat);

            SplitWall(scene);
            var root = new GameObject(RootName); SceneManager.MoveGameObjectToScene(root, scene);
            var ground = BuildGround(root.transform);
            BuildRoad(root.transform, ground);
            Physics.SyncTransforms();
            float Y(float x, float z) => GroundY(ground, x, z);
            Vector3 At(float x, float z, float up = 0) => new Vector3(x, Y(x, z) + up, z);

            // Boundary: invisible walls where the basin floor meets the escarpment and side slopes.
            var bounds = Child(root.transform, "Boundary colliders");
            Box(bounds, "Boundary west", new Vector3(-101, 3, -3), new Vector3(1, 12, 104));
            Box(bounds, "Boundary north", new Vector3(-80.5f, 3, 47), new Vector3(42, 12, 1));
            Box(bounds, "Boundary south", new Vector3(-80.5f, 3, -53), new Vector3(42, 12, 1));

            // Warden post just outside the gate
            var post = Child(root.transform, "Warden post");
            var gateMarker = Child(post, "Gate marker"); gateMarker.position = new Vector3(-57, 0, 1);
            var respawn = Child(post, "Respawn point"); respawn.SetPositionAndRotation(At(-64, 4.5f), Quaternion.Euler(0, -90, 0));
            var guard = Place("Assets/AthenHill/Prefabs/WardGuard.prefab", post, "Warden Ossa", At(-63.4f, 2.6f), Quaternion.Euler(0, 250, 0));
            var locker = Place("Assets/AthenHill/Prefabs/Salvage/crate.prefab", post, "Warden arms locker", At(-64.6f, 9.4f), Quaternion.Euler(0, 12, 0));
            AddBoxFromRenderers(locker);
            var use = locker.AddComponent<WorldInteractable>(); use.prompt = "E · Take the scrap pistol"; use.range = 2.6f;
            var lamp = new GameObject("Locker lamp", typeof(Light)).GetComponent<Light>();
            lamp.transform.SetParent(locker.transform, false); lamp.transform.localPosition = new Vector3(0, 1.9f, 0);
            lamp.type = LightType.Point; lamp.color = new Color(.35f, .84f, .86f); lamp.intensity = 1.4f; lamp.range = 3.2f; lamp.shadows = LightShadows.None;
            AddBoxFromRenderers(Place("Assets/AthenHill/Prefabs/Salvage/generator.prefab", post, "Post generator", At(-66.9f, 10.6f), Quaternion.Euler(0, 80, 0)));
            Place("Assets/AthenHill/Prefabs/Salvage/trash.prefab", post, "Post litter", At(-62.6f, 10.2f), Quaternion.Euler(0, 30, 0));
            AddBoxFromRenderers(Place("Assets/AthenHill/Prefabs/Salvage/crate.prefab", post, "Post crate", At(-65.9f, 8.3f), Quaternion.Euler(0, -20, 0)));

            // Range: three plates in front of the backstop berm, facing the firing line at the post
            var range = Child(root.transform, "Warden range");
            var firingLine = new Vector3(-66, 0, 8);
            var targets = new List<RangeTarget>();
            foreach (var (x, z, i) in new[] { (-78f, 11f, 1), (-80.5f, 15.5f, 2), (-77.5f, 20f, 3) })
            {
                var p = At(x, z);
                var face = firingLine - p; face.y = 0;
                var t = (GameObject)PrefabUtility.InstantiatePrefab(target, scene);
                t.name = "Range plate " + i; t.transform.SetParent(range, true);
                t.transform.SetPositionAndRotation(p, Quaternion.LookRotation(face.normalized));
                targets.Add(t.GetComponent<RangeTarget>());
            }

            // Machine depot: cracked foundation, broken walls, the power source the cluster guards, a stripped carcass
            var depotRoot = Child(root.transform, "Machine depot");
            var concrete = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/BuildingMaterials/WardConcrete/WardConcrete.mat");
            float padY = Y(DepotCenter.x, DepotCenter.y);
            Slab(depotRoot, "Depot foundation", new Vector3(DepotCenter.x, padY - .12f, DepotCenter.y), new Vector3(15, .4f, 11), 8, concrete, false);
            foreach (var (x, z, len, h, yaw) in new[] { (-86.8f, -40f, 9f, 2.2f, 90f), (-83.5f, -46f, 6f, 1.4f, 0f), (-75.5f, -45.8f, 4f, .9f, 4f), (-87f, -34.8f, 3f, 1.1f, 80f), (-74f, -36.5f, 2.5f, .7f, 95f) })
                Slab(depotRoot, "Depot wall", new Vector3(x, Y(x, z) - .1f + h / 2, z), new Vector3(len, h, .45f), yaw, concrete, true);
            AddBoxFromRenderers(Place("Assets/AthenHill/Prefabs/Salvage/generator.prefab", depotRoot, "Depot generator", At(-82.5f, -43.8f), Quaternion.Euler(0, 5, 0)));
            AddBoxFromRenderers(Place("Assets/AthenHill/Prefabs/Salvage/generator.prefab", depotRoot, "Depot generator", At(-80.6f, -44.1f), Quaternion.Euler(0, -8, 0)));
            foreach (var (x, z, yaw) in new[] { (-85.3f, -37f, 30f), (-76.2f, -39.5f, 140f), (-78f, -34.5f, 75f) })
                AddBoxFromRenderers(Place("Assets/AthenHill/Prefabs/Salvage/scrap.prefab", depotRoot, "Stripped scrap", At(x, z), Quaternion.Euler(0, yaw, 0)));
            foreach (var (x, z, yaw) in new[] { (-73.8f, -42.5f, 20f), (-86f, -44.4f, -10f) })
                AddBoxFromRenderers(Place("Assets/AthenHill/Prefabs/Salvage/crate.prefab", depotRoot, "Depot crate", At(x, z), Quaternion.Euler(0, yaw, 0)));
            foreach (var (x, z) in new[] { (-79f, -38f), (-83.5f, -39.5f), (-71f, -20f) })
                Place("Assets/AthenHill/Prefabs/Salvage/trash.prefab", depotRoot, "Depot litter", At(x, z), Quaternion.Euler(0, x * 37 % 360, 0));
            Carcass(depotRoot, At(-86.4f, -43.2f, -.35f));

            // Encounters
            var enc = Child(root.transform, "Encounters");
            var first = Encounter(enc, "First contact · service road", session, new[] { (drone, At(-83, -13)) }, 0);
            var depot = Encounter(enc, "Machine depot nest", session, new[] { (worker, At(-81, -40.5f)), (worker, At(-77, -37)), (drone, At(-84, -36)) }, 0);

            // Player combat
            var playerGo = scene.GetRootGameObjects().First(g => g.name == "Player");
            var motor = playerGo.GetComponent<PlayerMotor>();
            var health = playerGo.AddComponent<Health>(); health.max = 100; health.regenPerSecond = 8; health.regenDelay = 4; health.aimTarget = false; health.aimOffset = new Vector3(0, 1.2f, 0);
            var combat = playerGo.AddComponent<PlayerCombat>();
            combat.session = session; combat.input = session.input; combat.motor = motor; combat.follow = session.follow; combat.view = session.follow.GetComponent<Camera>();
            combat.respawnPoint = respawn;
            var voice = new GameObject("Berms pistol audio", typeof(AudioSource)).GetComponent<AudioSource>();
            voice.transform.SetParent(playerGo.transform, false); voice.spatialBlend = 0; voice.playOnAwake = false; voice.outputAudioMixerGroup = sfxGroup;
            combat.audioSource = voice;
            combat.shotClip = Clip("scrap-pistol-shot"); combat.emptyClip = Clip("scrap-pistol-empty"); combat.drawClip = Clip("scrap-pistol-draw"); combat.hurtClip = Clip("player-hurt");
            var tracer = new GameObject("Berms pistol tracer", typeof(LineRenderer)).GetComponent<LineRenderer>();
            tracer.transform.SetParent(playerGo.transform, false); tracer.useWorldSpace = true; tracer.positionCount = 2;
            tracer.widthCurve = new AnimationCurve(new Keyframe(0, .035f), new Keyframe(1, .012f)); tracer.sharedMaterial = tracerMat;
            tracer.shadowCastingMode = ShadowCastingMode.Off; tracer.receiveShadows = false; tracer.numCapVertices = 2;
            combat.tracer = tracer;
            var flash = new GameObject("Berms muzzle flash", typeof(Light)).GetComponent<Light>();
            flash.transform.SetParent(playerGo.transform, false); flash.type = LightType.Point; flash.color = new Color(.45f, .9f, .92f); flash.intensity = 3; flash.range = 4; flash.shadows = LightShadows.None;
            combat.muzzleLight = flash;
            combat.impactSparks = Sparks(playerGo.transform, "Berms impact sparks", sparksMat);
            AttachPistol(combat, motor);

            // HUD
            var hudGo = scene.GetRootGameObjects().First(g => g.name == "City HUD");
            var combatHud = hudGo.AddComponent<CombatHud>();
            combatHud.session = session; combatHud.combat = combat; combatHud.worldCamera = session.follow.GetComponent<Camera>();

            // Tutorial
            foreach (var e in new[] { first, depot }) e.player = combat;
            var tutorial = root.AddComponent<BermsTutorial>();
            tutorial.session = session; tutorial.combat = combat; tutorial.locker = use; tutorial.targets = targets.ToArray();
            tutorial.firstContact = first; tutorial.depot = depot; tutorial.gateMarker = gateMarker;
            combatHud.tutorial = tutorial;

            Cameras(scene);
            StaticRenderChunksEditor.Rebuild(chunks);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();

            Record["guard"] = guard.name;
            Record["groundTriangles"] = ground.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3;
            Record["targets"] = targets.Select(t => V(t.transform.position));
            Record["encounters"] = new[] { first, depot }.Select(e => new { e.displayName, spawns = e.spawns.Select(s => new { prefab = s.prefab.name, pos = V(s.point.position) }) });
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "pass.json", JsonConvert.SerializeObject(Record, Formatting.Indented));
            Debug.Log("Outer Berms installed: " + JsonConvert.SerializeObject(Record));
        }

        // ---------- wall gap ----------
        static void SplitWall(Scene scene)
        {
            var wall = Find(scene, WallName); var col = Find(scene, WallCollider);
            var mesh = wall.GetComponent<MeshFilter>().sharedMesh; var mat = wall.GetComponent<MeshRenderer>().sharedMaterials;
            var b = mesh.bounds; float zMin = b.min.z + wall.position.z, zMax = b.max.z + wall.position.z;
            foreach (var (name, lo, hi) in new[] { ("south", zMin, GapSouth), ("north", GapNorth, zMax) })
            {
                var m = ClipZ(mesh, lo - wall.position.z, hi - wall.position.z, b.min.z, b.max.z);
                m.name = "Berms gate wall " + name;
                AssetDatabase.CreateAsset(m, Art + "BermsGateWall_" + name + ".asset");
                var seg = new GameObject(SegmentPrefix + name, typeof(MeshFilter), typeof(MeshRenderer));
                seg.transform.SetParent(wall.parent, false); seg.transform.SetPositionAndRotation(wall.position, wall.rotation);
                seg.GetComponent<MeshFilter>().sharedMesh = m;
                var r = seg.GetComponent<MeshRenderer>(); r.sharedMaterials = mat;
                var src = wall.GetComponent<MeshRenderer>(); r.shadowCastingMode = src.shadowCastingMode; r.receiveShadows = src.receiveShadows;
                seg.isStatic = wall.gameObject.isStatic; seg.layer = wall.gameObject.layer;
                var c = new GameObject("COL_" + SegmentPrefix + name, typeof(BoxCollider));
                c.transform.SetParent(col.parent, false); c.layer = col.gameObject.layer; c.isStatic = col.gameObject.isStatic;
                var box = c.GetComponent<BoxCollider>(); var cb = col.GetComponent<Collider>().bounds;
                box.center = new Vector3(cb.center.x, cb.center.y, (lo + hi) / 2); box.size = new Vector3(cb.size.x, cb.size.y, hi - lo);
            }
            wall.gameObject.SetActive(false); col.gameObject.SetActive(false);
            Record["wallGap"] = new[] { GapSouth, GapNorth };
        }

        /// Clips a mesh to lo..hi along local Z (attributes interpolated, so tiling UVs continue) and caps each cut
        /// with a copy of the original end face moved to the cut.
        static Mesh ClipZ(Mesh src, float lo, float hi, float srcMin, float srcMax)
        {
            var pos = src.vertices; var nrm = src.normals; var uv = src.uv; var tan = src.tangents;
            bool hasTan = tan.Length == pos.Length;
            var P = new List<Vector3>(); var N = new List<Vector3>(); var U = new List<Vector2>(); var T = new List<Vector4>(); var I = new List<int>();
            int Add(Vector3 p, Vector3 n, Vector2 u, Vector4 t) { P.Add(p); N.Add(n); U.Add(u); T.Add(t); return P.Count - 1; }
            var tris = src.triangles;
            for (int k = 0; k < tris.Length; k += 3)
            {
                var poly = new List<(Vector3 p, Vector3 n, Vector2 u, Vector4 t)>();
                for (int j = 0; j < 3; j++) { int v = tris[k + j]; poly.Add((pos[v], nrm[v], uv[v], hasTan ? tan[v] : Vector4.zero)); }
                bool endMax = poly.All(v => v.p.z > srcMax - .06f), endMin = poly.All(v => v.p.z < srcMin + .06f);
                // End faces: keep only at an original end, and copy to each cut below
                if (endMax || endMin)
                {
                    if (endMax && hi >= srcMax - .01f || endMin && lo <= srcMin + .01f) Emit(poly);
                    continue;
                }
                poly = Clip(poly, lo, true); poly = Clip(poly, hi, false);
                Emit(poly);
            }
            void Emit(List<(Vector3 p, Vector3 n, Vector2 u, Vector4 t)> poly)
            {
                if (poly.Count < 3) return;
                int a = Add(poly[0].p, poly[0].n, poly[0].u, poly[0].t);
                for (int j = 1; j + 1 < poly.Count; j++) { I.Add(a); I.Add(Add(poly[j].p, poly[j].n, poly[j].u, poly[j].t)); I.Add(Add(poly[j + 1].p, poly[j + 1].n, poly[j + 1].u, poly[j + 1].t)); }
            }
            // caps
            for (int k = 0; k < tris.Length; k += 3)
            {
                var v3 = new[] { tris[k], tris[k + 1], tris[k + 2] };
                if (hi < srcMax - .01f && v3.All(v => pos[v].z > srcMax - .06f))
                    foreach (var v in v3) I.Add(Add(pos[v] + Vector3.forward * (hi - srcMax), nrm[v], uv[v], hasTan ? tan[v] : Vector4.zero));
                if (lo > srcMin + .01f && v3.All(v => pos[v].z < srcMin + .06f))
                    foreach (var v in v3) I.Add(Add(pos[v] + Vector3.forward * (lo - srcMin), nrm[v], uv[v], hasTan ? tan[v] : Vector4.zero));
            }
            var m = new Mesh { indexFormat = IndexFormat.UInt32 };
            m.SetVertices(P); m.SetNormals(N); m.SetUVs(0, U); if (hasTan) m.SetTangents(T); m.SetTriangles(I, 0);
            m.RecalculateBounds(); if (!hasTan) m.RecalculateTangents();
            return m;
        }
        static List<(Vector3 p, Vector3 n, Vector2 u, Vector4 t)> Clip(List<(Vector3 p, Vector3 n, Vector2 u, Vector4 t)> poly, float plane, bool keepAbove)
        {
            var o = new List<(Vector3 p, Vector3 n, Vector2 u, Vector4 t)>();
            bool Inside(Vector3 p) => keepAbove ? p.z >= plane : p.z <= plane;
            for (int i = 0; i < poly.Count; i++)
            {
                var a = poly[i]; var b = poly[(i + 1) % poly.Count];
                bool ia = Inside(a.p), ib = Inside(b.p);
                if (ia) o.Add(a);
                if (ia != ib)
                {
                    float t = (plane - a.p.z) / (b.p.z - a.p.z);
                    o.Add((Vector3.Lerp(a.p, b.p, t), Vector3.Lerp(a.n, b.n, t).normalized, Vector2.Lerp(a.u, b.u, t), Vector4.Lerp(a.t, b.t, t)));
                }
            }
            return o;
        }

        // ---------- ground ----------
        static GameObject BuildGround(Transform parent)
        {
            // Basin surface (height + baked vertex lighting) via temporary colliders on its meshes
            var basin = GameObject.Find("Desert Landscape");
            var temp = new List<(GameObject go, Mesh mesh)>();
            foreach (var r in basin.GetComponentsInChildren<MeshRenderer>())
            {
                var f = r.GetComponent<MeshFilter>(); var probe = new GameObject("basin probe") { layer = 31, hideFlags = HideFlags.DontSave };
                probe.transform.SetPositionAndRotation(r.transform.position, r.transform.rotation); probe.transform.localScale = r.transform.lossyScale;
                probe.AddComponent<MeshCollider>().sharedMesh = f.sharedMesh; temp.Add((probe, f.sharedMesh));
            }
            Physics.SyncTransforms();
            var cache = new Dictionary<Mesh, (Color[] colors, int[] tris)>();
            (float h, Color c, bool ok) Basin(float x, float z)
            {
                if (!Physics.Raycast(new Vector3(x, 120, z), Vector3.down, out var hit, 300, 1 << 31)) return (-1.4f, Color.white, false);
                var mesh = temp.First(t => t.go == hit.collider.gameObject).mesh;
                if (!cache.TryGetValue(mesh, out var data)) cache[mesh] = data = (mesh.colors, mesh.triangles);
                var (cols, tri) = data; var bc = hit.barycentricCoordinate; int i = hit.triangleIndex * 3;
                var c = cols.Length > 0 ? cols[tri[i]] * bc.x + cols[tri[i + 1]] * bc.y + cols[tri[i + 2]] * bc.z : Color.white;
                return (hit.point.y, c, true);
            }
            int nx = (int)(X1 - X0) + 1, nz = (int)(Z1 - Z0) + 1;
            var height = new float[nx, nz]; var color = new Color[nx, nz];
            Color fallback = Color.white; bool haveFallback = false;
            for (int i = nx - 1; i >= 0; i--) for (int j = 0; j < nz; j++)
            {
                float x = X0 + i, z = Z0 + j; var s = Basin(x, z);
                if (s.ok && !haveFallback) { fallback = s.c; haveFallback = true; }
                height[i, j] = s.ok ? s.h : -1.4f; color[i, j] = s.ok ? s.c : fallback;
            }
            // road centreline height, following the natural surface incl. the gate ramp
            float Natural(int i, int j) { float x = X0 + i; float apron = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(-60, -67, x)); return Mathf.Max(height[i, j] + .04f, Mathf.Lerp(0, height[i, j] + .04f, apron)); }
            float roadY(float s) { var p = PointAt(s); int i = Mathf.Clamp(Mathf.RoundToInt(p.x - X0), 0, nx - 1), j = Mathf.Clamp(Mathf.RoundToInt(p.y - Z0), 0, nz - 1); return Natural(i, j); }
            float padY = 0; { int i = Mathf.RoundToInt(DepotCenter.x - X0), j = Mathf.RoundToInt(DepotCenter.y - Z0); padY = Natural(i, j); }
            var verts = new Vector3[nx * nz]; var colors = new Color[nx * nz];
            for (int i = 0; i < nx; i++) for (int j = 0; j < nz; j++)
            {
                float x = X0 + i, z = Z0 + j; float h = Natural(i, j);
                float d = DistanceToRoad(new Vector2(x, z), out float s);
                float road = 1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(RoadHalf, RoadHalf + 2.5f, d));
                float ry = RoadSmooth(roadY, s);
                h = Mathf.Lerp(h, ry, road);
                float pad = 1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(DepotRadius, DepotRadius + 3, Vector2.Distance(new Vector2(x, z), DepotCenter)));
                h = Mathf.Lerp(h, padY, pad);
                float edge = Mathf.Min(Mathf.Min(x - X0, X1 - x), Mathf.Min(z - Z0, Z1 - z));
                float keep = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(0, 4, edge)) * (1 - road) * (1 - pad);
                foreach (var m in Mounds)
                {
                    float u = (x - m.x) / m.rx, v = (z - m.z) / m.rz, d2 = u * u + v * v;
                    if (d2 < 1) h += m.h * Mathf.Pow(Mathf.Cos(Mathf.Sqrt(d2) * Mathf.PI / 2), 2) * keep;
                }
                verts[j * nx + i] = new Vector3(x, h, z);
                var c = color[i, j]; float wallShade = Mathf.InverseLerp(-63, -60, x); c.r = Mathf.Lerp(c.r, c.r * .75f, wallShade); colors[j * nx + i] = c;
            }
            foreach (var t in temp) UnityEngine.Object.DestroyImmediate(t.go);
            var tris = new List<int>();
            for (int i = 0; i < nx - 1; i++) for (int j = 0; j < nz - 1; j++)
            {
                int a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
                tris.AddRange(new[] { a, c, b, b, c, d });
            }
            var mesh = new Mesh { name = "Outer Berms ground", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(verts); mesh.SetColors(colors); mesh.SetTriangles(tris, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh, Art + "BermsGround.asset");
            var go = new GameObject("Berms ground", typeof(MeshFilter), typeof(MeshRenderer), typeof(MeshCollider));
            go.transform.SetParent(parent, false); go.isStatic = true;
            go.GetComponent<MeshFilter>().sharedMesh = mesh; go.GetComponent<MeshCollider>().sharedMesh = mesh;
            var r2 = go.GetComponent<MeshRenderer>(); r2.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/Terrain/SandstoneBasin.mat");
            r2.shadowCastingMode = ShadowCastingMode.Off;
            return go;
        }
        static float RoadSmooth(Func<float, float> f, float s) { float sum = 0; int n = 0; for (float k = -3; k <= 3; k += 1) { sum += f(Mathf.Clamp(s + k, 0, RoadLength)); n++; } return sum / n; }
        static float RoadLength { get { float l = 0; for (int i = 1; i < Road.Length; i++) l += Vector2.Distance(Road[i - 1], Road[i]); return l; } }
        static Vector2 PointAt(float s)
        {
            for (int i = 1; i < Road.Length; i++) { float l = Vector2.Distance(Road[i - 1], Road[i]); if (s <= l) return Vector2.Lerp(Road[i - 1], Road[i], s / l); s -= l; }
            return Road[^1];
        }
        static float DistanceToRoad(Vector2 p, out float along)
        {
            float best = float.MaxValue, acc = 0; along = 0;
            for (int i = 1; i < Road.Length; i++)
            {
                var a = Road[i - 1]; var b = Road[i]; var ab = b - a; float l = ab.magnitude;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / (l * l)); float d = Vector2.Distance(p, a + ab * t);
                if (d < best) { best = d; along = acc + t * l; }
                acc += l;
            }
            return best;
        }
        static float GroundY(GameObject ground, float x, float z)
        {
            var col = ground.GetComponent<MeshCollider>();
            return col.Raycast(new Ray(new Vector3(x, 60, z), Vector3.down), out var hit, 200) ? hit.point.y : 0;
        }

        /// Broken service road: a strip of cracked concrete a few centimetres above the ground, UVs in metres.
        static void BuildRoad(Transform parent, GameObject ground)
        {
            Physics.SyncTransforms();
            var P = new List<Vector3>(); var U = new List<Vector2>(); var I = new List<int>();
            float len = RoadLength; int steps = Mathf.CeilToInt(len / .75f);
            for (int k = 0; k <= steps; k++)
            {
                float s = len * k / steps; var c = PointAt(s); var ahead = PointAt(Mathf.Min(len, s + .5f)) - PointAt(Mathf.Max(0, s - .5f));
                var side = new Vector2(-ahead.y, ahead.x).normalized;
                // worn, uneven edges: the width wanders and narrows at the depot
                float half = (RoadHalf - .35f) * (1 + .08f * Mathf.Sin(s * 1.7f) + .06f * Mathf.Sin(s * 4.3f + 1)) * Mathf.Lerp(1, .8f, Mathf.InverseLerp(len - 8, len, s));
                for (int e = -1; e <= 1; e += 2)
                {
                    var q = c + side * half * e; float x = Mathf.Min(q.x, -60.05f);
                    P.Add(new Vector3(x, GroundY(ground, x, q.y) + .03f, q.y)); U.Add(new Vector2((e + 1) * half / 3f, s / 3f));
                }
                if (k > 0) { int a = P.Count - 4; I.AddRange(new[] { a, a + 2, a + 1, a + 1, a + 2, a + 3 }); }
            }
            // wind so every triangle faces up
            for (int k = 0; k < I.Count; k += 3)
                if (Vector3.Cross(P[I[k + 1]] - P[I[k]], P[I[k + 2]] - P[I[k]]).y < 0) (I[k + 1], I[k + 2]) = (I[k + 2], I[k + 1]);
            var mesh = new Mesh { name = "Outer Berms service road" }; mesh.SetVertices(P); mesh.SetUVs(0, U); mesh.SetTriangles(I, 0);
            mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh, Art + "BermsRoad.asset");
            var go = new GameObject("Service road", typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(parent, false); go.isStatic = true;
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = CopyMaterial("Assets/AthenHill/Art/BuildingMaterials/WardConcrete/WardConcrete.mat", Art + "BermsRoadConcrete.mat", new Color(.6f, .52f, .42f)); r.shadowCastingMode = ShadowCastingMode.Off;
        }

        /// Box of concrete with metre-scaled UVs on each face (foundation slabs and broken walls).
        static void Slab(Transform parent, string name, Vector3 center, Vector3 size, float yaw, Material mat, bool collider)
        {
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(parent, false);
            go.transform.SetPositionAndRotation(center, Quaternion.Euler(0, yaw, 0)); go.isStatic = true;
            string key = $"BermsSlab_{size.x:0.##}x{size.y:0.##}x{size.z:0.##}".Replace('.', '_');
            var path = Art + key + ".asset";
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (!mesh)
            {
                mesh = BoxMesh(size, 2.5f); mesh.name = key; AssetDatabase.CreateAsset(mesh, path);
            }
            go.GetComponent<MeshFilter>().sharedMesh = mesh; go.GetComponent<MeshRenderer>().sharedMaterial = mat;
            if (collider) { var b = go.AddComponent<BoxCollider>(); b.size = size; }
        }
        static Mesh BoxMesh(Vector3 s, float tile)
        {
            var P = new List<Vector3>(); var N = new List<Vector3>(); var U = new List<Vector2>(); var I = new List<int>();
            var h = s / 2;
            void Face(Vector3 n, Vector3 u, Vector3 v, float su, float sv)
            {
                int b = P.Count; var c = Vector3.Scale(n, h);
                foreach (var (a, bb) in new[] { (-1, -1), (1, -1), (1, 1), (-1, 1) })
                {
                    P.Add(c + Vector3.Scale(u, h) * a + Vector3.Scale(v, h) * bb); N.Add(n);
                    U.Add(new Vector2((a + 1) * su / 2 / tile, (bb + 1) * sv / 2 / tile));
                }
                I.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            Face(Vector3.up, Vector3.right, Vector3.forward, s.x, s.z); Face(Vector3.down, Vector3.right, Vector3.back, s.x, s.z);
            Face(Vector3.forward, Vector3.left, Vector3.up, s.x, s.y); Face(Vector3.back, Vector3.right, Vector3.up, s.x, s.y);
            Face(Vector3.right, Vector3.forward, Vector3.up, s.z, s.y); Face(Vector3.left, Vector3.back, Vector3.up, s.z, s.y);
            var m = new Mesh(); m.SetVertices(P); m.SetNormals(N); m.SetUVs(0, U); m.SetTriangles(I, 0);
            // Winding follows (u, v) cross-product; flip any face whose triangle normal disagrees with n.
            var tri = m.triangles; var v3 = m.vertices; var nn = m.normals;
            for (int k = 0; k < tri.Length; k += 3)
                if (Vector3.Dot(Vector3.Cross(v3[tri[k + 1]] - v3[tri[k]], v3[tri[k + 2]] - v3[tri[k]]), nn[tri[k]]) < 0) (tri[k + 1], tri[k + 2]) = (tri[k + 2], tri[k + 1]);
            m.triangles = tri; m.RecalculateTangents(); m.RecalculateBounds();
            return m;
        }

        // ---------- props ----------
        static GameObject Place(string prefabPath, Transform parent, string name, Vector3 pos, Quaternion rot)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath), parent);
            go.name = name; go.transform.SetPositionAndRotation(pos, rot); return go;
        }
        static void AddBoxFromRenderers(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) return;
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            var col = go.AddComponent<BoxCollider>();
            col.center = go.transform.InverseTransformPoint(b.center);
            var e = go.transform.InverseTransformVector(b.size); col.size = new Vector3(Mathf.Abs(e.x), Mathf.Abs(e.y), Mathf.Abs(e.z)) * .92f;
        }
        static void Carcass(Transform parent, Vector3 pos)
        {
            const string path = "Assets/AthenHill/Art/WardRetrofit/MiningDroid.glb";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!model) return;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model, parent);
            go.name = "Stripped mining droid carcass";
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(9, 118, -14));
            var anim = go.GetComponentInChildren<Animation>();
            var idle = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().FirstOrDefault(c => c.name == "idle");
            if (anim) { if (idle) idle.SampleAnimation(anim.gameObject, 0); anim.enabled = false; anim.playAutomatically = false; }
            foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>()) r.updateWhenOffscreen = false;
            var box = go.AddComponent<BoxCollider>(); box.center = new Vector3(0, 1.3f, 0); box.size = new Vector3(2.2f, 2.4f, 3.6f);
        }
        static DroidEncounter Encounter(Transform parent, string name, GameSession session, (GameObject prefab, Vector3 pos)[] spawns, float respawn)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            var avg = spawns.Aggregate(Vector3.zero, (a, s) => a + s.pos) / spawns.Length; go.transform.position = avg;
            var e = go.AddComponent<DroidEncounter>(); e.displayName = name; e.session = session; e.respawnSeconds = respawn;
            e.spawns = spawns.Select((s, i) =>
            {
                var p = new GameObject("Spawn " + (i + 1) + " · " + s.prefab.name).transform; p.SetParent(go.transform, true);
                var face = new Vector3(-66, 0, 5) - s.pos; face.y = 0;
                p.SetPositionAndRotation(s.pos, Quaternion.LookRotation(face.normalized));
                return new DroidEncounter.Spawn { prefab = s.prefab.GetComponent<FeralDroid>(), point = p };
            }).ToArray();
            return e;
        }

        // ---------- enemy / target / pistol prefabs ----------
        static GameObject Model(string file, bool legacy)
        {
            var path = Art + file;
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            if (legacy)
            {
                var importer = AssetImporter.GetAtPath(path);
                var so = new SerializedObject(importer); var method = so.FindProperty("importSettings.animationMethod");
                if (method != null && method.enumNames[method.enumValueIndex] != "Legacy")
                { method.enumValueIndex = Array.IndexOf(method.enumNames, "Legacy"); so.ApplyModifiedPropertiesWithoutUndo(); importer.SaveAndReimport(); }
            }
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(path) ?? throw new InvalidOperationException("Missing " + path);
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials) if (!m || m.shader.name.Contains("Error")) throw new InvalidOperationException(file + " material failed to import.");
            return model;
        }
        static Bounds RendererBounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(); var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); return b;
        }
        static GameObject BuildWorkerDroid(UnityEngine.Audio.AudioMixerGroup sfx, Material sparks, Material smoke)
        {
            var model = Model("WorkerDroid.glb", true);
            var clips = AssetDatabase.LoadAllAssetsAtPath(Art + "WorkerDroid.glb").OfType<AnimationClip>().ToDictionary(c => c.name);
            foreach (var n in new[] { "idle", "walk", "run", "attack", "hit", "death" }) if (!clips.ContainsKey(n) || !clips[n].legacy) throw new InvalidOperationException("Worker droid missing legacy clip " + n);
            var root = new GameObject("FeralWorkerDroid");
            var rig = (GameObject)PrefabUtility.InstantiatePrefab(model); rig.transform.SetParent(root.transform, false);
            var anim = rig.GetComponentInChildren<Animation>() ?? throw new InvalidOperationException("Worker droid has no Animation");
            anim.playAutomatically = false; clips["idle"].SampleAnimation(anim.gameObject, 0);
            var b = RendererBounds(root);
            foreach (var r in rig.GetComponentsInChildren<SkinnedMeshRenderer>()) { r.updateWhenOffscreen = false; r.localBounds = new Bounds(r.localBounds.center, r.localBounds.size + Vector3.one * .8f); }
            var h = root.AddComponent<Health>(); h.max = 100; h.aimOffset = new Vector3(0, b.size.y * .62f, 0);
            var d = root.AddComponent<FeralDroid>(); d.kind = DroidKind.Walker; d.displayName = "Feral worker droid";
            d.animationSource = anim; d.idle = clips["idle"]; d.walk = clips["walk"]; d.run = clips["run"]; d.attack = clips["attack"]; d.hit = clips["hit"]; d.death = clips["death"];
            d.wanderSpeed = 1.0f; d.chaseSpeed = 3.1f; d.attackRange = 1.9f; d.strikeDamage = 16; d.windupSeconds = .65f; d.recoverSeconds = 1.0f;
            d.walkStrideSpeed = 1.25f; d.runStrideSpeed = 3.4f; d.attackImpact = .42f;
            var cap = root.AddComponent<CapsuleCollider>(); cap.center = new Vector3(0, b.size.y / 2, 0); cap.height = b.size.y; cap.radius = .42f;
            var rb = root.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false;
            var head = rig.GetComponentsInChildren<Transform>().FirstOrDefault(t => t.name.ToLower().Contains("head"));
            d.eyeLight = EyeLight(head ? head : root.transform, head ? Vector3.zero : new Vector3(0, b.size.y * .9f, .15f), 3.5f);
            if (head) { d.eyeLight.transform.position = head.position + root.transform.forward * .18f; }
            Voice(d, root, sfx); d.sparks = Sparks(root.transform, "Hit sparks", sparks); d.smoke = Smoke(root.transform, smoke, b.size.y * .7f);
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, Prefabs + "FeralWorkerDroid.prefab");
            UnityEngine.Object.DestroyImmediate(root);
            Record["workerDroid"] = new { size = V(b.size), triangles = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).Sum(r => r.sharedMesh.triangles.Length / 3), clips = clips.Values.Select(c => new { c.name, c.length }) };
            return prefab;
        }
        static GameObject BuildScrapDrone(UnityEngine.Audio.AudioMixerGroup sfx, Material sparks, Material smoke)
        {
            var model = Model("ScrapDrone.glb", false);
            var root = new GameObject("FeralScrapDrone");
            var visual = new GameObject("Visual").transform; visual.SetParent(root.transform, false);
            var mesh = (GameObject)PrefabUtility.InstantiatePrefab(model); mesh.transform.SetParent(visual, false);
            var b = RendererBounds(mesh); float s = 1.25f / Mathf.Max(b.size.x, b.size.z);
            mesh.transform.localScale = Vector3.one * s; mesh.transform.localPosition = -b.center * s;
            var h = root.AddComponent<Health>(); h.max = 60; h.aimOffset = Vector3.zero;
            var d = root.AddComponent<FeralDroid>(); d.kind = DroidKind.Hover; d.displayName = "Feral scrap drone";
            d.wanderSpeed = 1.4f; d.chaseSpeed = 4.2f; d.attackRange = 2.6f; d.strikeDamage = 9; d.windupSeconds = .55f; d.recoverSeconds = 1.1f; d.hoverHeight = 1.5f; d.aggroRadius = 16;
            var sphere = root.AddComponent<SphereCollider>(); sphere.radius = .55f;
            var rb = root.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false; rb.mass = 20; rb.angularDamping = .5f;
            d.eyeLight = EyeLight(visual, new Vector3(0, 0, b.size.z * s * .55f), 3f);
            Voice(d, root, sfx); d.sparks = Sparks(root.transform, "Hit sparks", sparks); d.smoke = Smoke(root.transform, smoke, 0);
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, Prefabs + "FeralScrapDrone.prefab");
            UnityEngine.Object.DestroyImmediate(root);
            Record["scrapDrone"] = new { sourceSize = V(b.size), scale = s, triangles = model.GetComponentsInChildren<MeshFilter>(true).Sum(f => f.sharedMesh.triangles.Length / 3) };
            return prefab;
        }
        static GameObject BuildRangeTarget(UnityEngine.Audio.AudioMixerGroup sfx, Material sparks)
        {
            var model = Model("RangeTarget.glb", false);
            var root = new GameObject("RangeTarget");
            var pivot = new GameObject("Plate pivot").transform; pivot.SetParent(root.transform, false);
            var mesh = (GameObject)PrefabUtility.InstantiatePrefab(model); mesh.transform.SetParent(pivot, false);
            var b = RendererBounds(mesh); float s = 1.5f / b.size.y;
            mesh.transform.localScale = Vector3.one * s; mesh.transform.localPosition = new Vector3(-b.center.x * s, -b.min.y * s, -b.center.z * s);
            var box = pivot.gameObject.AddComponent<BoxCollider>(); box.center = new Vector3(0, .75f, 0); box.size = new Vector3(b.size.x * s, 1.5f, Mathf.Max(.2f, b.size.z * s));
            var h = root.AddComponent<Health>(); h.max = 30; h.aimOffset = new Vector3(0, .95f, 0);
            var t = root.AddComponent<RangeTarget>(); t.pivot = pivot;
            var clang = root.AddComponent<AudioSource>(); clang.clip = Clip("target-clang"); clang.playOnAwake = false; clang.spatialBlend = 1; clang.rolloffMode = AudioRolloffMode.Linear; clang.minDistance = 3; clang.maxDistance = 45; clang.outputAudioMixerGroup = sfx;
            t.clang = clang; t.sparks = Sparks(root.transform, "Hit sparks", sparks);
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, Prefabs + "RangeTarget.prefab");
            UnityEngine.Object.DestroyImmediate(root);
            Record["rangeTarget"] = new { sourceSize = V(b.size), scale = s };
            return prefab;
        }
        /// Scrap pistol in the colonist's right hand. The grip offset is solved in the idle pose so the barrel
        /// points along the colonist's forward with the grip down; shown only while drawn.
        static void AttachPistol(PlayerCombat combat, PlayerMotor motor)
        {
            var model = Model("ScrapPistol.glb", false);
            var hand = motor.visual.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "hand_r" || t.name.ToLower().Contains("righthand"));
            if (!hand) { Record["pistol"] = "no right hand bone; hip muzzle used"; return; }
            var holder = new GameObject("Berms held pistol").transform;
            var mesh = (GameObject)PrefabUtility.InstantiatePrefab(model); mesh.transform.SetParent(holder, false);
            var b = RendererBounds(mesh);
            // long axis = barrel; the grip (lower half) sits toward the rear
            var verts = mesh.GetComponentsInChildren<MeshFilter>().SelectMany(f => f.sharedMesh.vertices.Select(v => f.transform.TransformPoint(v))).ToArray();
            bool alongX = b.size.x >= b.size.z;
            var lower = verts.Where(v => v.y < b.center.y - b.extents.y * .3f).ToArray();
            float rear = lower.Length > 0 ? (alongX ? lower.Average(v => v.x) - b.center.x : lower.Average(v => v.z) - b.center.z) : 0;
            var barrel = (alongX ? Vector3.right : Vector3.forward) * (rear > 0 ? -1 : 1);
            float s = .26f / Mathf.Max(b.size.x, b.size.z);
            mesh.transform.localScale = Vector3.one * s;
            mesh.transform.localRotation = Quaternion.Inverse(Quaternion.LookRotation(barrel, Vector3.up));
            var gripPoint = mesh.transform.localRotation * ((lower.Length > 0 ? new Vector3(lower.Average(v => v.x), b.center.y, lower.Average(v => v.z)) : b.center) * s);
            mesh.transform.localPosition = -gripPoint;
            var muzzle = new GameObject("Muzzle").transform; muzzle.SetParent(holder, false);
            muzzle.localPosition = mesh.transform.localRotation * (new Vector3(alongX ? b.center.x + b.extents.x * Mathf.Sign(barrel.x) : b.center.x, b.center.y + b.extents.y * .35f, alongX ? b.center.z : b.center.z + b.extents.z * Mathf.Sign(barrel.z)) * s) + mesh.transform.localPosition;
            // idle pose: place in the hand facing the colonist's forward, then parent keeping the world pose
            var actor = motor.actor; var anim = actor ? actor.animationSource : null;
            if (anim && actor.idle && !actor.humanoidAnimator) actor.idle.SampleAnimation(anim.gameObject, 0);
            holder.SetPositionAndRotation(hand.position + motor.visual.forward * .02f - motor.visual.up * .03f, Quaternion.LookRotation(motor.visual.forward, Vector3.up));
            holder.SetParent(hand, true);
            foreach (var r in holder.GetComponentsInChildren<Renderer>()) { r.shadowCastingMode = ShadowCastingMode.On; }
            combat.heldPistol = holder.gameObject; combat.muzzlePoint = muzzle;
            holder.gameObject.SetActive(false);
            Record["pistol"] = new { hand = hand.name, sourceSize = V(b.size), scale = s, barrel = V(barrel) };
        }
        static Light EyeLight(Transform parent, Vector3 local, float range)
        {
            var l = new GameObject("Optic glow", typeof(Light)).GetComponent<Light>();
            l.transform.SetParent(parent, false); l.transform.localPosition = local;
            l.type = LightType.Point; l.color = new Color(1f, .45f, .16f); l.intensity = .5f; l.range = range; l.shadows = LightShadows.None;
            return l;
        }
        static void Voice(FeralDroid d, GameObject root, UnityEngine.Audio.AudioMixerGroup sfx)
        {
            var a = root.AddComponent<AudioSource>(); a.playOnAwake = false; a.spatialBlend = 1; a.rolloffMode = AudioRolloffMode.Linear; a.minDistance = 2.5f; a.maxDistance = 40; a.outputAudioMixerGroup = sfx; a.dopplerLevel = 0;
            d.voice = a; d.alertClip = Clip("droid-alert"); d.strikeClip = Clip("droid-strike"); d.hitClip = Clip("droid-hit"); d.deathClip = Clip("droid-death");
        }
        static ParticleSystem Sparks(Transform parent, string name, Material mat)
        {
            var go = new GameObject(name, typeof(ParticleSystem)); go.transform.SetParent(parent, false);
            var ps = go.GetComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.playOnAwake = false; main.loop = false; main.duration = .5f; main.startLifetime = new ParticleSystem.MinMaxCurve(.18f, .45f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(2.5f, 7f); main.startSize = new ParticleSystem.MinMaxCurve(.025f, .06f); main.gravityModifier = 1.4f;
            main.simulationSpace = ParticleSystemSimulationSpace.World; main.maxParticles = 80; main.startColor = new Color(1f, .75f, .4f);
            var em = ps.emission; em.enabled = false;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 35; shape.radius = .02f;
            var col = ps.colorOverLifetime; col.enabled = true; var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(new Color(1, .85f, .55f), 0), new GradientColorKey(new Color(1, .35f, .1f), 1) }, new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) }); col.color = g;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = .04f; r.lengthScale = 1; r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.Off;
            return ps;
        }
        static ParticleSystem Smoke(Transform parent, Material mat, float height)
        {
            var go = new GameObject("Wreck smoke", typeof(ParticleSystem)); go.transform.SetParent(parent, false); go.transform.localPosition = new Vector3(0, height, 0);
            go.transform.localRotation = Quaternion.Euler(-90, 0, 0);
            var ps = go.GetComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.playOnAwake = false; main.loop = true; main.startLifetime = new ParticleSystem.MinMaxCurve(2.2f, 3.5f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.4f, .9f); main.startSize = new ParticleSystem.MinMaxCurve(.5f, 1.1f); main.maxParticles = 30;
            main.simulationSpace = ParticleSystemSimulationSpace.World; main.startColor = new Color(.22f, .2f, .18f, .55f);
            var em = ps.emission; em.rateOverTime = 5;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 12; shape.radius = .15f;
            var sol = ps.sizeOverLifetime; sol.enabled = true; sol.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .6f, 1, 1.8f));
            var col = ps.colorOverLifetime; col.enabled = true; var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(.8f, .15f), new GradientAlphaKey(0, 1) }); col.color = g;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.Off;
            return ps;
        }
        static Material CopyMaterial(string from, string to, Color color)
        {
            if (!AssetDatabase.LoadAssetAtPath<Material>(to)) AssetDatabase.CopyAsset(from, to);
            var m = AssetDatabase.LoadAssetAtPath<Material>(to); m.SetColor("_BaseColor", color); EditorUtility.SetDirty(m); return m;
        }
        static AudioClip Clip(string name) => AssetDatabase.LoadAssetAtPath<AudioClip>(Audio + name + ".wav") ?? throw new InvalidOperationException("Missing combat clip " + name);

        // ---------- helpers ----------
        static void Cameras(Scene scene)
        {
            var root = new GameObject(CamerasName); SceneManager.MoveGameObjectToScene(root, scene);
            foreach (var (name, pos, look) in new[]
            {
                ("cam_berms_gate", new Vector3(-47, 2.2f, 5.5f), new Vector3(-62, 0, 1)),
                ("cam_berms_threshold", new Vector3(-56.5f, 1.7f, 3.2f), new Vector3(-72, -.5f, 0)),
                ("cam_berms_post", new Vector3(-60.5f, 2.4f, 12.5f), new Vector3(-65, .3f, 5.5f)),
                ("cam_berms_range", new Vector3(-66, 1.7f, 7.5f), new Vector3(-79, .2f, 15.5f)),
                ("cam_berms_road", new Vector3(-68, 2.2f, 2), new Vector3(-84, -.5f, -18)),
                ("cam_berms_depot", new Vector3(-72, 2.4f, -28), new Vector3(-81, -.4f, -41)),
                ("cam_berms_overview", new Vector3(-54, 14, 22), new Vector3(-80, -1, -14)),
            })
            {
                var c = new GameObject(name, typeof(Camera)).GetComponent<Camera>(); c.transform.SetParent(root.transform, false);
                c.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(look - pos)); c.fieldOfView = 55; c.farClipPlane = 650; c.enabled = false;
            }
        }
        static Transform Child(Transform parent, string name) { var t = new GameObject(name).transform; t.SetParent(parent, false); return t; }
        static void Box(Transform parent, string name, Vector3 center, Vector3 size) { var go = new GameObject(name, typeof(BoxCollider)); go.transform.SetParent(parent, false); go.transform.position = center; go.GetComponent<BoxCollider>().size = size; }
        static Transform Find(Scene scene, string path)
        {
            var root = scene.GetRootGameObjects().First(g => g.name == path.Split('/')[0]).transform;
            return root.Find(path.Substring(path.IndexOf('/') + 1)) ?? throw new InvalidOperationException("Missing " + path);
        }
        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
    }
}
