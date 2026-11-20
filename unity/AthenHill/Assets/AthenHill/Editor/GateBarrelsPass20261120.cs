using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>
    /// 20 November 2026, Carl's playtest note: "Barrels on the floor by the waste gate, the broken ones on the floor need to
    /// be able to be walked over or need to go". Record: art/gate_barrels_20261120/README.md.
    ///
    /// survey  : lists every low collider (top under 1.2 m above the local ground) on the walkable city, the West Gate
    ///           outpost and the spawn apron, with the renderers it stands for, and walks a CharacterController with the
    ///           player's exact settings across each one along eight headings (the same Move/ground-snap sequence as
    ///           PlayerMotor). Also lists every barrel-like or debris renderer with the colliders under it.
    ///           Writes survey.json; does not save the scene.
    /// install : applies the Fixes table (collider off / box resized / object moved), originals recorded once in
    ///           art/gate_barrels_20261120/record.json; adds cam_gb_* review cameras. Idempotent.
    /// verify  : repeats the walk on every line in Lines on the saved scene (must reach the far side with no pop),
    ///           checks the fixes, cameras and that nothing else is touched. Writes verify.json.
    /// rollback: restores colliders, transforms and active flags from record.json and removes the cameras.
    /// -executeMethod AthenHill.Editor.GateBarrelsPass20261120.RunBatch --steps survey | install,verify | rollback
    /// </summary>
    public static class GateBarrelsPass20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string CamRootName = "Gate barrels review cameras";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string ArtDir => Path.Combine(Repo, "art/gate_barrels_20261120");
        static string RecordPath => Path.Combine(ArtDir, "record.json");
        static string Evidence => Path.Combine(Repo, "unity/evidence/showcase_phase2/20261120/gate_barrels");

        // ------------------------------------------------------------------ the fixes (filled in from the survey)
        // kind "worldBox": the BoxCollider on `path` is re-fitted to the world-space box a (centre) / b (size), axis-aligned:
        //   the collider's transform goes to a with no rotation, its box to centre 0 and size b / |lossyScale|.
        // kind "addBox": a new GameObject `name` with a BoxCollider a / b under the scene root CollidersRoot (layer copied
        //   from `path`).
        // Values measured on the saved scene's LOD0 vertices (heightmaps step, heightmaps.json): see the README.
        class Fix { public string kind, path, name, why; public Vector3 a, b; }
        const string CollidersRoot = "Gate barrels colliders";
        const string MarketBarrels = "Karaveen caravan market/Caravan stock/COL_barrels";
        const string RationsGoods = "Karaveen caravan market/Stall Rations/COL_goods.010";
        static readonly Fix[] Fixes =
        {
            new Fix { kind = "worldBox", path = MarketBarrels, a = new Vector3(-46.5f, .425f, 5.25f), b = new Vector3(.72f, .85f, .76f),
                why = "caravan overflow by the West Gate: the 3 Oct box lay over the broken staves (x -46.9..-46.2, z 6.1..7.6) and half of the west barrel; now it holds the west whole barrel only (x -46.8..-46.2, z 4.9..5.6, 0.79 m tall)" },
            new Fix { kind = "addBox", path = MarketBarrels, name = "COL_caravan_barrel_east", a = new Vector3(-44.45f, .425f, 5.25f), b = new Vector3(.74f, .85f, .76f),
                why = "caravan overflow: the east whole barrel (x -44.8..-44.1, z 4.9..5.6) had no collider since 3 Oct" },
            new Fix { kind = "worldBox", path = RationsGoods, a = new Vector3(-36.8f, .3f, -17.35f), b = new Vector3(1.9f, .6f, .6f),
                why = "Rations stall side: one 1.9 x 2.5 x 0.6 m box covered the two small whole barrels and every broken stave, lid and the 0.2 m barrel half; now it holds the two whole barrels (x -37.7..-35.9, z -17.6..-17.1, 0.59 m)" },
        };

        // Walk lines that used to be blocked (or must stay open): name, start (x, z), end (x, z). verify and the native
        // check walk these both ways.
        static readonly (string name, float x0, float z0, float x1, float z1)[] Lines =
        {
            ("caravan_staves_ew", -48.4f, 6.6f, -42.6f, 6.6f),      // west-east through the stave field and the broken half
            ("caravan_staves_ns", -46.6f, 9.2f, -46.6f, 6.15f),     // north-south over the staves the 3 Oct box covered, stops short of the west barrel
            ("caravan_between", -45.5f, 3.4f, -45.5f, 8.8f),        // between the two whole barrels and on over the staves
            ("rations_staves_ns", -37.0f, -14.6f, -37.0f, -16.6f),  // over the staves and lids beside the Rations stall, stops short of the barrels
            ("rations_staves_ew", -39.4f, -16.2f, -36.1f, -16.2f),  // west-east over the stave field to the stall's side
        };

        // Review cameras at player eye height: name, position, target.
        static readonly (string name, Vector3 pos, Vector3 target)[] Cameras =
        {
            ("cam_gb_caravan_east", new Vector3(-41.6f, 1.6f, 7.4f), new Vector3(-45.6f, .25f, 6.2f)),
            ("cam_gb_caravan_north", new Vector3(-45.6f, 1.6f, 10.6f), new Vector3(-45.6f, .25f, 6.0f)),
            ("cam_gb_rations_west", new Vector3(-40.4f, 1.6f, -15.0f), new Vector3(-36.8f, .2f, -16.4f)),
            ("cam_gb_rations_north", new Vector3(-37.0f, 1.6f, -12.6f), new Vector3(-36.9f, .2f, -16.4f)),
        };

        // ------------------------------------------------------------------ scene helpers
        static IEnumerable<Transform> All(Scene s) => s.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true));
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static Transform Find(Scene s, string path) => All(s).FirstOrDefault(t => PathOf(t) == path) ?? throw new Exception("Not found: " + path);
        static float[] V(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };
        static float R(float f) => (float)Math.Round(f, 3);
        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }

        // ------------------------------------------------------------------ the walking probe
        class Probe
        {
            public GameObject go; public CharacterController cc; public CharacterController player; public bool playerWasEnabled;
            public float walk = 3.4f, gravity = 22f, groundSnap = .4f; public LayerMask worldMask = ~(1 << 8);
        }

        static Probe MakeProbe()
        {
            var motor = UnityEngine.Object.FindAnyObjectByType<PlayerMotor>(FindObjectsInactive.Include);
            if (!motor) throw new Exception("PlayerMotor not found");
            var pc = motor.GetComponent<CharacterController>();
            var p = new Probe { player = pc, playerWasEnabled = pc.enabled, walk = motor.walkSpeed, gravity = motor.gravity, groundSnap = motor.groundSnap, worldMask = motor.worldMask };
            pc.enabled = false; // the probe must not bump into the real player at the spawn
            p.go = new GameObject("__gate_barrels_probe") { hideFlags = HideFlags.DontSave, layer = motor.gameObject.layer };
            p.cc = p.go.AddComponent<CharacterController>();
            p.cc.height = pc.height; p.cc.radius = pc.radius; p.cc.slopeLimit = pc.slopeLimit; p.cc.stepOffset = pc.stepOffset;
            p.cc.skinWidth = pc.skinWidth; p.cc.minMoveDistance = pc.minMoveDistance; p.cc.center = pc.center;
            return p;
        }

        static void DropProbe(Probe p)
        {
            if (p == null) return;
            if (p.go) UnityEngine.Object.DestroyImmediate(p.go);
            if (p.player) p.player.enabled = p.playerWasEnabled;
        }

        /// Ground height under (x, z): the first non-trigger hit from above, skipping colliders in `skip`.
        static float Ground(float x, float z, float from, ICollection<Collider> skip)
        {
            var hits = Physics.RaycastAll(new Vector3(x, from, z), Vector3.down, from + 30, ~0, QueryTriggerInteraction.Ignore)
                .Where(h => skip == null || !skip.Contains(h.collider)).OrderBy(h => h.distance).ToArray();
            return hits.Length > 0 ? hits[0].point.y : float.NaN;
        }

        class WalkResult
        {
            public bool reached, startBlocked; public float seconds, rise, drop, progress, startY; public int stalledFrames;
            public List<string> touched = new List<string>();
        }

        /// One walk from a to b with PlayerMotor's FixedUpdate sequence (walk speed, gravity, ground snap), fixed dt 0.02.
        static WalkResult Walk(Probe p, Vector3 a, Vector3 b)
        {
            var res = new WalkResult();
            var dir = Flat(b - a); float dist = dir.magnitude; dir /= dist;
            float gy = Ground(a.x, a.z, Mathf.Max(a.y, 0) + 3f, null);
            if (float.IsNaN(gy)) { res.startBlocked = true; return res; }
            var feet = new Vector3(a.x, gy, a.z);
            var c0 = feet + Vector3.up * (p.cc.radius + .05f); var c1 = feet + Vector3.up * (p.cc.height - p.cc.radius);
            if (Physics.CheckCapsule(c0, c1, p.cc.radius - .02f, ~0, QueryTriggerInteraction.Ignore)) { res.startBlocked = true; return res; }
            p.cc.enabled = false; p.go.transform.position = feet + Vector3.up * .015f; p.cc.enabled = true; Physics.SyncTransforms();
            res.startY = p.go.transform.position.y;
            float vertical = 0, dt = .02f, maxY = res.startY, minY = res.startY; bool grounded = false;
            int maxSteps = Mathf.CeilToInt(dist / p.walk / dt * 2.0f) + 25;
            var touched = new HashSet<string>();
            int i = 0;
            for (; i < maxSteps; i++)
            {
                var before = p.go.transform.position;
                bool was = grounded || p.cc.isGrounded;
                if (was && vertical <= 0) vertical = -2; else vertical = Mathf.Max(vertical - p.gravity * dt, -35);
                var flags = p.cc.Move((dir * p.walk + Vector3.up * vertical) * dt);
                if ((flags & CollisionFlags.Above) != 0 && vertical > 0) vertical = 0;
                grounded = p.cc.isGrounded;
                var pos = p.go.transform.position;
                if (was && !grounded && vertical <= 0 && Physics.SphereCast(pos + Vector3.up * .55f, .28f, Vector3.down, out var hit, .55f + p.groundSnap, p.worldMask, QueryTriggerInteraction.Ignore) && hit.normal.y > .7f)
                {
                    float d = hit.distance - .27f;
                    if (d > 0 && d <= p.groundSnap) { p.cc.Move(Vector3.down * (d + .02f)); grounded = p.cc.isGrounded; }
                }
                pos = p.go.transform.position;
                if ((flags & CollisionFlags.Sides) != 0)
                {
                    var cc0 = pos + Vector3.up * (p.cc.radius + .05f); var cc1 = pos + Vector3.up * (p.cc.height - p.cc.radius);
                    foreach (var c in Physics.OverlapCapsule(cc0 + dir * .06f, cc1 + dir * .06f, p.cc.radius + .04f, ~0, QueryTriggerInteraction.Ignore))
                        if (c != p.cc) touched.Add(PathOf(c.transform) + " [" + c.GetType().Name + "]");
                }
                if (Vector3.Dot(Flat(pos - before), dir) < p.walk * dt * .3f) res.stalledFrames++;
                maxY = Mathf.Max(maxY, pos.y); minY = Mathf.Min(minY, pos.y);
                res.progress = Vector3.Dot(Flat(pos - a), dir);
                if (res.progress >= dist - .05f) { res.reached = true; break; }
            }
            res.seconds = R((i + 1) * dt); res.progress = R(res.progress); res.rise = R(maxY - res.startY); res.drop = R(res.startY - minY);
            res.touched = touched.ToList();
            return res;
        }

        // ------------------------------------------------------------------ survey
        static readonly Regex Debris = new Regex(@"barrel|drum|keg|cask|stave|hoop|lid|piece|debris|rubble|broken|crush|tyre|tire|scrap|litter|plank|caravan stock|wreck", RegexOptions.IgnoreCase);
        static bool InArea(Vector3 c) => c.x > -95 && c.x < 54 && c.z > -62 && c.z < 62 && c.y < 6;

        static object Survey()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            Physics.SyncTransforms();
            var probe = MakeProbe();
            try
            {
                Physics.SyncTransforms();
                // sanity: the probe walks on open paving at the spawn avenue
                var sanity = Walk(probe, new Vector3(30, 0, 6), new Vector3(26, 0, 6));
                var renderers = All(scene).Where(t => t.gameObject.activeInHierarchy).SelectMany(t => t.GetComponents<Renderer>())
                    .Where(r => r.enabled && (r is MeshRenderer || r is SkinnedMeshRenderer) && InArea(r.bounds.center) && r.bounds.size.y < 3f).ToArray();
                var colliders = All(scene).Where(t => t.gameObject.activeInHierarchy).SelectMany(t => t.GetComponents<Collider>())
                    .Where(c => c.enabled && !c.isTrigger && !(c is CharacterController) && !(c is TerrainCollider) && InArea(c.bounds.center)).ToArray();
                var low = new List<object>();
                int idx = 0;
                foreach (var c in colliders)
                {
                    var b = c.bounds;
                    if (Mathf.Max(b.size.x, b.size.z) > 8f) continue;   // floors, walls, buildings
                    var skip = new HashSet<Collider> { c };
                    float off = .6f; var gs = new List<float>();
                    foreach (var (dx, dz) in new[] { (-1, -1), (-1, 1), (1, -1), (1, 1) })
                    {
                        float g = Ground(b.center.x + dx * (b.extents.x + off), b.center.z + dz * (b.extents.z + off), b.max.y + 1f, skip);
                        if (!float.IsNaN(g)) gs.Add(g);
                    }
                    if (gs.Count == 0) continue;
                    gs.Sort(); float ground = gs[gs.Count / 2];
                    float top = b.max.y - ground, bottom = b.min.y - ground;
                    if (top < .05f || top > 1.2f || bottom > .6f) continue;  // not a low obstacle a walker meets
                    var reps = renderers.Where(r => r.bounds.Intersects(new Bounds(b.center, b.size + Vector3.one * .1f)) && !r.name.StartsWith("Chunk_"))
                        .Select(r => PathOf(r.transform) + (r.GetComponent<MeshFilter>() && r.GetComponent<MeshFilter>().sharedMesh ? " {" + r.GetComponent<MeshFilter>().sharedMesh.name + "}" : "")).Distinct().Take(10).ToArray();
                    string text = PathOf(c.transform) + " " + string.Join(" ", reps);
                    bool debrisName = Debris.IsMatch(text);
                    // walks across along eight headings through the collider centre
                    float r0 = new Vector2(b.extents.x, b.extents.z).magnitude + probe.cc.radius + .6f;
                    var walks = new List<object>(); int blocked = 0, popped = 0, clear = 0, skipped = 0;
                    for (int h = 0; h < 8; h++)
                    {
                        var d = Quaternion.Euler(0, h * 45f, 0) * Vector3.forward;
                        var a = new Vector3(b.center.x, ground, b.center.z) - d * r0; var e = new Vector3(b.center.x, ground, b.center.z) + d * r0;
                        var w = Walk(probe, a, e);
                        string verdict = w.startBlocked ? "start-blocked" : !w.reached ? "blocked" : w.rise > .32f ? "popped" : "clear";
                        if (verdict == "start-blocked") skipped++; else if (verdict == "blocked") blocked++; else if (verdict == "popped") popped++; else clear++;
                        walks.Add(new { heading = h * 45, from = new[] { R(a.x), R(a.z) }, to = new[] { R(e.x), R(e.z) }, verdict, w.seconds, w.progress, w.rise, w.stalledFrames, touched = w.touched.Take(4) });
                    }
                    low.Add(new
                    {
                        id = idx++, path = PathOf(c.transform), type = c.GetType().Name,
                        boxSize = c is BoxCollider bx ? V(bx.size) : null, boxCenter = c is BoxCollider bx2 ? V(bx2.center) : null,
                        min = V(b.min), max = V(b.max), ground = R(ground), top = R(top), bottom = R(bottom), debrisName, renderers = reps,
                        crossings = new { clear, popped, blocked, skipped },
                        distWestGate = R(Vector2.Distance(new Vector2(b.center.x, b.center.z), new Vector2(-59f, 1f))),
                        distSpawnArches = R(Vector2.Distance(new Vector2(b.center.x, b.center.z), new Vector2(47f, 6f))),
                        walks
                    });
                }
                // barrel-like and debris renderers, with the colliders their bounds overlap
                var debrisRenderers = new List<object>();
                foreach (var r in renderers)
                {
                    var mf = r.GetComponent<MeshFilter>();
                    string name = PathOf(r.transform) + " " + (mf && mf.sharedMesh ? mf.sharedMesh.name : "");
                    if (!Debris.IsMatch(name) || r.name.StartsWith("Chunk_")) continue;
                    var lod = r.GetComponentInParent<LODGroup>();
                    if (lod) { var l0 = lod.GetLODs(); if (l0.Length > 0 && !l0[0].renderers.Contains(r)) continue; }
                    var b = r.bounds; float hz = Mathf.Max(b.size.x, b.size.z);
                    var under = Physics.OverlapBox(b.center, b.extents + Vector3.one * .02f, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore)
                        .Where(c => !(c is CharacterController) && Mathf.Max(c.bounds.size.x, c.bounds.size.z) < 12f)
                        .Select(c => new { path = PathOf(c.transform), type = c.GetType().Name, min = V(c.bounds.min), max = V(c.bounds.max) }).ToArray();
                    debrisRenderers.Add(new
                    {
                        path = PathOf(r.transform), mesh = mf && mf.sharedMesh ? mf.sharedMesh.name : r.GetType().Name, min = V(b.min), max = V(b.max),
                        height = R(b.size.y), footprint = R(hz), shape = b.size.y < hz * .85f ? "lying-or-low" : "upright",
                        up = V(r.transform.up), colliders = under,
                        distWestGate = R(Vector2.Distance(new Vector2(b.center.x, b.center.z), new Vector2(-59f, 1f))),
                        distSpawnArches = R(Vector2.Distance(new Vector2(b.center.x, b.center.z), new Vector2(47f, 6f)))
                    });
                }
                var result = new
                {
                    probe = new { probe.cc.height, probe.cc.radius, probe.cc.stepOffset, probe.cc.slopeLimit, probe.cc.skinWidth, probe.walk, probe.gravity, probe.groundSnap, layer = probe.go.layer },
                    sanity = new { sanity.reached, sanity.seconds, sanity.rise, sanity.startBlocked, sanity.progress },
                    lowColliders = low, debrisRenderers
                };
                Directory.CreateDirectory(Evidence);
                File.WriteAllText(Path.Combine(Evidence, "survey.json"), JsonConvert.SerializeObject(result, Formatting.Indented));
                return new { sanity = result.sanity, lowColliders = low.Count, debrisRenderers = debrisRenderers.Count };
            }
            finally { DropProbe(probe); }
        }

        // ------------------------------------------------------------------ height maps (where the props really are)
        // For each region: a 0.1 m grid of the highest visible vertex (LOD0 / non-LOD renderers) and of the highest
        // collider top (ray from above), written as text rows so a person can read them. Digits are decimetres above
        // the region's floor ('.' = nothing, '#' = 1 m or more).
        static readonly (string name, float x0, float x1, float z0, float z1)[] MapRegions =
        {
            ("caravan_overflow", -48.2f, -42.4f, 3.6f, 9.0f),
            ("rations_stall_side", -38.6f, -34.4f, -19.0f, -14.4f),
            ("spawn_drums_cluster3", 20.8f, 24.6f, 2.4f, 5.6f),
        };

        static object HeightMaps()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            Physics.SyncTransforms();
            var outDict = new Dictionary<string, object>();
            var rends = All(scene).Where(t => t.gameObject.activeInHierarchy).SelectMany(t => t.GetComponents<MeshRenderer>()).Where(r => r.enabled).ToArray();
            foreach (var (name, x0, x1, z0, z1) in MapRegions)
            {
                const float cell = .1f;
                int nx = Mathf.CeilToInt((x1 - x0) / cell), nz = Mathf.CeilToInt((z1 - z0) / cell);
                var vis = new float[nx, nz]; var col = new float[nx, nz];
                for (int i = 0; i < nx; i++) for (int k = 0; k < nz; k++) { vis[i, k] = float.NegativeInfinity; col[i, k] = float.NegativeInfinity; }
                var area = new Bounds(new Vector3((x0 + x1) / 2, 0, (z0 + z1) / 2), new Vector3(x1 - x0, 20, z1 - z0));
                var used = new List<string>();
                foreach (var r in rends)
                {
                    if (!r.bounds.Intersects(area) || r.bounds.size.y > 6f || r.name.StartsWith("Chunk_")) continue;
                    var lod = r.GetComponentInParent<LODGroup>();
                    if (lod) { var l = lod.GetLODs(); if (l.Length > 0 && !l[0].renderers.Contains(r)) continue; }
                    var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || !mf.sharedMesh.isReadable) { if (mf && mf.sharedMesh) used.Add(PathOf(r.transform) + " (mesh not readable)"); continue; }
                    var m = r.localToWorldMatrix; int n = 0;
                    foreach (var v in mf.sharedMesh.vertices)
                    {
                        var w = m.MultiplyPoint3x4(v);
                        int i = Mathf.FloorToInt((w.x - x0) / cell), k = Mathf.FloorToInt((w.z - z0) / cell);
                        if (i < 0 || k < 0 || i >= nx || k >= nz) continue;
                        if (w.y > vis[i, k]) vis[i, k] = w.y; n++;
                    }
                    if (n > 0) used.Add(PathOf(r.transform) + " (" + n + " vertices)");
                }
                for (int i = 0; i < nx; i++) for (int k = 0; k < nz; k++)
                {
                    var p = new Vector3(x0 + (i + .5f) * cell, 8f, z0 + (k + .5f) * cell);
                    if (Physics.Raycast(p, Vector3.down, out var h, 16f, ~0, QueryTriggerInteraction.Ignore)) col[i, k] = h.point.y;
                }
                float floor = Ground((x0 + x1) / 2, z0 - .5f, 8f, null); if (float.IsNaN(floor)) floor = 0;
                string Row(float[,] a, int k) { var sb = new System.Text.StringBuilder(); for (int i = 0; i < nx; i++) { float h = a[i, k] - floor; sb.Append(float.IsInfinity(a[i, k]) || h < .03f ? '.' : h >= 1f ? '#' : (char)('0' + Mathf.Clamp(Mathf.FloorToInt(h * 10f), 0, 9))); } return sb.ToString(); }
                // rows from north (z1) to south (z0); columns west (x0) to east (x1)
                var visRows = Enumerable.Range(0, nz).Reverse().Select(k => $"{z0 + (k + .5f) * cell,7:0.00} {Row(vis, k)}").ToArray();
                var colRows = Enumerable.Range(0, nz).Reverse().Select(k => $"{z0 + (k + .5f) * cell,7:0.00} {Row(col, k)}").ToArray();
                outDict[name] = new { x0, x1, z0, z1, cell, floor = R(floor), legend = "rows north to south (z), columns west to east (x); digit = decimetres above floor, # >= 1 m", renderers = used, visible = visRows, colliderTop = colRows };
            }
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Path.Combine(Evidence, "heightmaps.json"), JsonConvert.SerializeObject(outDict, Formatting.Indented));
            return new { regions = MapRegions.Length };
        }

        // ------------------------------------------------------------------ install / rollback
        class Rec
        {
            public Dictionary<string, float[]> box = new Dictionary<string, float[]>();   // path: box center xyz, size xyz
            public Dictionary<string, float[]> pose = new Dictionary<string, float[]>();  // path: local pos xyz, local rot xyzw
            public List<string> landmarks = new List<string>();                           // landmark children this pass added
        }
        static Rec LoadRec() => File.Exists(RecordPath) ? JsonConvert.DeserializeObject<Rec>(File.ReadAllText(RecordPath)) : new Rec();
        static void SaveRec(Rec r) { Directory.CreateDirectory(ArtDir); File.WriteAllText(RecordPath, JsonConvert.SerializeObject(r, Formatting.Indented)); }

        static void Dirty(UnityEngine.Object o) { if (PrefabUtility.IsPartOfPrefabInstance(o)) PrefabUtility.RecordPrefabInstancePropertyModifications(o); EditorUtility.SetDirty(o); }

        static Vector3 Abs(Vector3 v) => new Vector3(Mathf.Abs(v.x), Mathf.Abs(v.y), Mathf.Abs(v.z));
        static Vector3 Div(Vector3 a, Vector3 b) => new Vector3(a.x / b.x, a.y / b.y, a.z / b.z);

        static Transform LandmarkRoot()
        {
            var bridge = UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            if (!bridge || !bridge.landmarks) throw new Exception("No AthenDebugBridge landmarks root");
            return bridge.landmarks;
        }
        static IEnumerable<(string name, Vector3 pos)> LandmarkPoints() =>
            Lines.SelectMany(l => new[] { ("gb_" + l.name + "_a", new Vector3(l.x0, 0, l.z0)), ("gb_" + l.name + "_b", new Vector3(l.x1, 0, l.z1)) });

        static object Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var rec = LoadRec(); var log = new List<string>();
            // find-or-create (not destroy-and-recreate), so a second install leaves the scene file identical
            GameObject added = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CollidersRoot);
            foreach (var f in Fixes)
            {
                var t = Find(scene, f.path);
                if (f.kind == "worldBox")
                {
                    var box = t.GetComponent<BoxCollider>();
                    if (!box) throw new Exception(f.path + " has no BoxCollider");
                    if (!rec.box.ContainsKey(f.path)) rec.box[f.path] = new[] { box.center.x, box.center.y, box.center.z, box.size.x, box.size.y, box.size.z };
                    if (!rec.pose.ContainsKey(f.path)) rec.pose[f.path] = new[] { t.localPosition.x, t.localPosition.y, t.localPosition.z, t.localRotation.x, t.localRotation.y, t.localRotation.z, t.localRotation.w };
                    t.SetPositionAndRotation(f.a, Quaternion.identity); Dirty(t);
                    box.center = Vector3.zero; box.size = Div(f.b, Abs(t.lossyScale)); Dirty(box);
                    Physics.SyncTransforms();
                    log.Add($"{f.path}: box now {box.bounds.min} .. {box.bounds.max}");
                }
                else if (f.kind == "addBox")
                {
                    if (!added) { added = new GameObject(CollidersRoot); SceneManager.MoveGameObjectToScene(added, scene); }
                    var ct = added.transform.Find(f.name);
                    var go = ct ? ct.gameObject : new GameObject(f.name);
                    go.layer = t.gameObject.layer;
                    if (!ct) go.transform.SetParent(added.transform, false);
                    go.transform.SetPositionAndRotation(f.a, Quaternion.identity);
                    var box = go.GetComponent<BoxCollider>(); if (!box) box = go.AddComponent<BoxCollider>();
                    box.center = Vector3.zero; box.size = f.b;
                    Physics.SyncTransforms();
                    log.Add($"{CollidersRoot}/{f.name}: box {box.bounds.min} .. {box.bounds.max} (layer {go.layer})");
                }
                else throw new Exception("unknown fix kind " + f.kind);
            }
            // QA landmarks at the ends of every walk line (AthenDebugBridge goto)
            var lm = LandmarkRoot();
            Physics.SyncTransforms();
            foreach (var (name, p) in LandmarkPoints())
            {
                var t = lm.Find(name);
                if (!t) { t = new GameObject(name).transform; t.SetParent(lm, false); if (!rec.landmarks.Contains(name)) rec.landmarks.Add(name); }
                float g = Ground(p.x, p.z, 4f, null);
                t.position = new Vector3(p.x, float.IsNaN(g) ? 0 : g, p.z);
            }
            EditorUtility.SetDirty(lm);
            SaveRec(rec);
            AddCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            var r = new { fixes = log, landmarks = LandmarkPoints().Select(l => l.name).ToArray(), cameras = Cameras.Select(c => c.name).ToArray() };
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "install.json"), JsonConvert.SerializeObject(r, Formatting.Indented));
            return r;
        }

        static void AddCameras(Scene scene)
        {
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (!root) { root = new GameObject(CamRootName); SceneManager.MoveGameObjectToScene(root, scene); }
            foreach (var (name, pos, target) in Cameras)
            {
                var tr = root.transform.Find(name);
                if (!tr) { tr = new GameObject(name).transform; tr.SetParent(root.transform, false); }
                tr.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var cam = tr.GetComponent<Camera>(); if (!cam) cam = tr.gameObject.AddComponent<Camera>();
                cam.enabled = false; cam.fieldOfView = 55f; cam.nearClipPlane = .05f;
            }
        }

        static object Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var rec = LoadRec(); var log = new List<string>();
            foreach (var kv in rec.pose)
            {
                var t = Find(scene, kv.Key); var v = kv.Value;
                t.localPosition = new Vector3(v[0], v[1], v[2]); t.localRotation = new Quaternion(v[3], v[4], v[5], v[6]); Dirty(t); log.Add("pose " + kv.Key);
            }
            foreach (var kv in rec.box)
            {
                var box = Find(scene, kv.Key).GetComponent<BoxCollider>(); var v = kv.Value;
                box.center = new Vector3(v[0], v[1], v[2]); box.size = new Vector3(v[3], v[4], v[5]); Dirty(box); log.Add("box " + kv.Key);
            }
            var lm = LandmarkRoot();
            foreach (var name in rec.landmarks) { var t = lm.Find(name); if (t) { UnityEngine.Object.DestroyImmediate(t.gameObject); log.Add("landmark " + name); } }
            EditorUtility.SetDirty(lm);
            foreach (var g in scene.GetRootGameObjects().Where(g => g.name == CamRootName || g.name == CollidersRoot).ToArray()) { log.Add("root " + g.name); UnityEngine.Object.DestroyImmediate(g); }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            if (File.Exists(RecordPath)) File.Move(RecordPath, RecordPath.Replace(".json", "-rolledback-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json"));
            var r = new { restored = log };
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "rollback.json"), JsonConvert.SerializeObject(r, Formatting.Indented));
            return r;
        }

        // ------------------------------------------------------------------ verify
        static List<object> WalkLines(List<string> problems)
        {
            Physics.SyncTransforms();
            var probe = MakeProbe(); var walks = new List<object>();
            try
            {
                foreach (var (name, x0, z0, x1, z1) in Lines)
                    foreach (var rev in new[] { false, true })
                    {
                        var a = rev ? new Vector3(x1, 0, z1) : new Vector3(x0, 0, z0); var b = rev ? new Vector3(x0, 0, z0) : new Vector3(x1, 0, z1);
                        var w = Walk(probe, a, b);
                        float expected = Flat(b - a).magnitude / probe.walk;
                        bool ok = !w.startBlocked && w.reached && w.rise <= .32f && w.seconds <= expected * 1.25f + .1f;
                        if (!ok && problems != null) problems.Add($"line {name}{(rev ? " (reverse)" : "")} not clear: reached {w.reached} start-blocked {w.startBlocked} {w.seconds}s (expected {expected:0.00}) progress {w.progress} rise {w.rise} touched {string.Join(", ", w.touched)}");
                        walks.Add(new { name, reverse = rev, ok, w.reached, w.startBlocked, w.seconds, expected = R(expected), w.progress, w.rise, w.drop, w.stalledFrames, w.touched });
                    }
            }
            finally { DropProbe(probe); }
            return walks;
        }

        /// Lines only, no assertions (evidence before the install): lines-TAG.json.
        static object LinesOnly(string tag)
        {
            EditorSceneManager.OpenScene(ScenePath);
            var walks = WalkLines(null);
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "lines-" + tag + ".json"), JsonConvert.SerializeObject(walks, Formatting.Indented));
            return new { tag, walks = walks.Count };
        }

        static float SegDist(Vector2 p, Vector2 a, Vector2 b) { var ab = b - a; float t = ab.sqrMagnitude < 1e-6f ? 0 : Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude); return Vector2.Distance(p, a + ab * t); }
        static float RectDist(Bounds r, Vector2 a, Vector2 b)
        {
            // distance in XZ from segment ab to the rectangle r (0 when they touch); sampled finely enough for metre-scale props
            float best = float.MaxValue;
            for (int i = 0; i <= 40; i++)
            {
                var p = Vector2.Lerp(a, b, i / 40f);
                float dx = Mathf.Max(r.min.x - p.x, 0, p.x - r.max.x), dz = Mathf.Max(r.min.z - p.y, 0, p.y - r.max.z);
                best = Mathf.Min(best, Mathf.Sqrt(dx * dx + dz * dz));
            }
            return best;
        }

        static object Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            Physics.SyncTransforms();
            var problems = new List<string>(); var rec = LoadRec();
            var boxes = new List<(string name, Bounds b)>();
            foreach (var f in Fixes)
            {
                var t = All(scene).FirstOrDefault(x => PathOf(x) == (f.kind == "addBox" ? CollidersRoot + "/" + f.name : f.path));
                if (!t) { problems.Add("missing " + (f.kind == "addBox" ? f.name : f.path)); continue; }
                var box = t.GetComponent<BoxCollider>();
                if (!box || !box.enabled || !t.gameObject.activeInHierarchy) { problems.Add("no active box on " + PathOf(t)); continue; }
                var want = new Bounds(f.a, f.b);
                if ((box.bounds.center - want.center).magnitude > 2e-3f || (box.bounds.size - want.size).magnitude > 2e-3f) problems.Add($"box on {PathOf(t)} is {box.bounds.min}..{box.bounds.max}, wanted {want.min}..{want.max}");
                if (f.kind == "worldBox" && (!rec.box.ContainsKey(f.path) || !rec.pose.ContainsKey(f.path))) problems.Add("no rollback record for " + f.path);
                boxes.Add((PathOf(t), box.bounds));
            }
            // routes, NPCs and landmarks clear of the boxes
            var near = new List<object>();
            foreach (var w in UnityEngine.Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (w.waypoints == null) continue;
                var pts = w.waypoints.Where(p => p).Select(p => new Vector2(p.position.x, p.position.z)).ToList();
                for (int i = 0; i < pts.Count; i++)
                    foreach (var (name, b) in boxes)
                    {
                        float d = RectDist(b, pts[i], pts[(i + 1) % pts.Count]);
                        if (d < 1.0f) near.Add(new { walker = PathOf(w.transform), segment = i, box = name, distance = R(d) });
                        if (d < .35f) problems.Add($"walker route {PathOf(w.transform)} segment {i} passes {d:0.00} m from {name}");
                    }
            }
            foreach (var n in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                foreach (var (name, b) in boxes)
                {
                    var p = new Vector2(n.transform.position.x, n.transform.position.z); float d = RectDist(b, p, p);
                    if (d < 1.0f) { near.Add(new { npc = PathOf(n.transform), box = name, distance = R(d) }); if (d < .4f) problems.Add($"NPC {PathOf(n.transform)} {d:0.00} m from {name}"); }
                }
            var lm = LandmarkRoot();
            foreach (var (name, p) in LandmarkPoints()) if (!lm.Find(name)) problems.Add("landmark missing " + name);
            var walks = WalkLines(problems);
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            var camNames = camRoot ? camRoot.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            foreach (var c in Cameras) if (!camNames.Contains(c.name)) problems.Add("camera missing " + c.name);
            int missingScripts = All(scene).SelectMany(t => t.GetComponents<Component>()).Count(c => c == null);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            bool fp = !chunks || chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            if (!fp) problems.Add("render chunk fingerprint stale");
            var market = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Karaveen caravan market");
            bool marketLinked = market && PrefabUtility.IsPartOfPrefabInstance(market) && !PrefabUtility.IsPrefabAssetMissing(market);
            if (!marketLinked) problems.Add("Karaveen caravan market prefab link broken");
            var r = new
            {
                installed = problems.Count == 0, fixes = boxes.Select(b => new { b.name, min = V(b.b.min), max = V(b.b.max) }), lines = walks,
                routesAndNpcsWithin1m = near, cameras = camNames, missingScripts, chunkFingerprintMatches = fp, marketPrefabLinked = marketLinked, problems
            };
            Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, "verify.json"), JsonConvert.SerializeObject(r, Formatting.Indented));
            if (problems.Count > 0) throw new Exception("GateBarrelsPass20261120 verify: " + string.Join("; ", problems));
            return new { ok = true, lines = walks.Count, fixes = boxes.Count, near = near.Count };
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            string steps = i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify";
            try
            {
                foreach (var st in steps.Split(','))
                {
                    object result = st switch
                    {
                        "survey" => Survey(),
                        "heightmaps" => HeightMaps(),
                        "lines-before" => LinesOnly("before"),
                        "lines-after" => LinesOnly("after"),
                        "install" => Install(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("GateBarrelsPass20261120 " + st + ": " + JsonConvert.SerializeObject(result));
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        [MenuItem("Athen Hill/Gate barrels (20 Nov 2026)/Survey")] public static void MenuSurvey() => Debug.Log(JsonConvert.SerializeObject(Survey()));
        [MenuItem("Athen Hill/Gate barrels (20 Nov 2026)/Install")] public static void MenuInstall() => Debug.Log(JsonConvert.SerializeObject(Install()));
        [MenuItem("Athen Hill/Gate barrels (20 Nov 2026)/Verify")] public static void MenuVerify() => Debug.Log(JsonConvert.SerializeObject(Verify()));
        [MenuItem("Athen Hill/Gate barrels (20 Nov 2026)/Rollback")] public static void MenuRollback() => Debug.Log(JsonConvert.SerializeObject(Rollback()));
    }
}
