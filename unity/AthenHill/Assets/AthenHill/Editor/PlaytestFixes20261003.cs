using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// <summary>
    /// Carl's playtest notes, 3 Oct 2026 (art/playtest_fixes_20261003/README.md). Narrow scene edits, recorded for rollback:
    /// - lattice: one Lattice Jack. The old glb Jack behind Vanguard Hall is retired (its ENV_/PROP_/COL_ lattice nodes
    ///   inactive, render chunks rebuilt) and the Meshy ring across the hill becomes the Lattice Jack: the Lattice
    ///   interaction (with its hum) moves to the ring's console and the ring's "offline" interaction is unbound.
    /// - droid: the walking mining droid leaves the Ward (instance and route inactive; the Berms scrapyard copy stays).
    /// - trolley: the retired West Gate field-fabricator tool cart goes (inactive; Brann's bench is the station).
    /// - barrels: the Karaveen market barrel collider shrinks to the two whole barrels, so the loose staves are walk-over.
    /// - outpost: the West Gate light tower (and its flood) moves off the range approach, the range sign stands beside the
    ///   barrier line and the shrub in the approach goes. Range-kit props move through art/training_range_20261001/layout.py.
    /// -executeMethod AthenHill.Editor.PlaytestFixes20261003.RunBatch --steps lattice,droid,trolley,barrels,outpost,verify | rollback
    /// </summary>
    public static class PlaytestFixes20261003
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        static string Record => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../art/playtest_fixes_20261003/record.json"));
        static readonly string[] LatticePrefixes = { "ENV_lattice", "PROP_lattice", "COL_ENV_lattice", "COL_PROP_lattice", "COL_lattice" };
        static readonly Vector3 PlatesCentre = new Vector3(-78.7f, 0, 15.5f);

        // ---- rollback record: original active state and transforms of everything touched
        class Rec { public Dictionary<string, bool> active = new Dictionary<string, bool>(); public Dictionary<string, float[]> pose = new Dictionary<string, float[]>(); public Dictionary<string, float[]> box = new Dictionary<string, float[]>(); public string ringPoint; public List<string> log = new List<string>(); }
        static Rec rec;
        static Rec Load() => File.Exists(Record) ? JsonConvert.DeserializeObject<Rec>(File.ReadAllText(Record)) : new Rec();
        static void Save() { Directory.CreateDirectory(Path.GetDirectoryName(Record)); File.WriteAllText(Record, JsonConvert.SerializeObject(rec, Formatting.Indented)); }

        static IEnumerable<Transform> All() => EditorSceneManager.GetActiveScene().GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true));
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static Transform Find(string path) => All().FirstOrDefault(t => PathOf(t) == path) ?? throw new Exception("Not found: " + path);
        static void SetActive(Transform t, bool on) { var p = PathOf(t); if (!rec.active.ContainsKey(p)) rec.active[p] = t.gameObject.activeSelf; t.gameObject.SetActive(on); }
        static void Pose(Transform t, Vector3 pos, Quaternion rot)
        {
            var p = PathOf(t);
            if (!rec.pose.ContainsKey(p)) rec.pose[p] = new[] { t.position.x, t.position.y, t.position.z, t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w };
            t.SetPositionAndRotation(pos, rot);
            if (PrefabUtility.IsPartOfPrefabInstance(t)) PrefabUtility.RecordPrefabInstancePropertyModifications(t);
        }
        static string V(Vector3 v) => $"({v.x:0.##}, {v.y:0.##}, {v.z:0.##})";

        /// Ground height under (x, z): highest non-trigger collider hit, ignoring the moved object itself.
        static float Ground(float x, float z, Transform ignore)
        {
            Physics.SyncTransforms();
            var hits = Physics.RaycastAll(new Vector3(x, 60, z), Vector3.down, 120, ~0, QueryTriggerInteraction.Ignore)
                .Where(h => !ignore || !h.collider.transform.IsChildOf(ignore)).OrderBy(h => h.distance).ToArray();
            return hits.Length > 0 ? hits[0].point.y : float.NaN;
        }

        // ---- steps
        static string Lattice()
        {
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include) ?? throw new Exception("No GameSession");
            var authored = All().FirstOrDefault(t => t.name == "AuthoredWorld" && !t.parent) ?? throw new Exception("No AuthoredWorld");
            var gate = All().FirstOrDefault(t => t.name == "Meshy Ring Gate" && !t.parent) ?? throw new Exception("No Meshy Ring Gate");
            var nodes = authored.GetComponentsInChildren<Transform>(true).Where(t => LatticePrefixes.Any(p => t.name.StartsWith(p, StringComparison.Ordinal))).ToArray();
            if (nodes.Length < 20) throw new Exception("Only " + nodes.Length + " lattice nodes found");
            foreach (var t in nodes) SetActive(t, false);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            // the Meshy ring's console faces the city (-Z); the interaction sits on its approach step, the ring's debug
            // landmark in front of the console (ImportRingGate.PositionDebugDestination) is the player's stand point
            var ring = session.ringPoint;
            if (ring) { rec.ringPoint = PathOf(ring); session.ringPoint = null; }
            var lp = session.latticePoint; if (!lp) throw new Exception("No latticePoint");
            var stand = All().FirstOrDefault(t => PathOf(t) == "Landmarks/ring_gate");
            var target = new Vector3(gate.position.x, lp.position.y, stand ? stand.position.z : gate.position.z - 1.9f);
            Pose(lp, target, lp.rotation);
            var lm = All().FirstOrDefault(t => PathOf(t) == "Landmarks/lattice_jack");
            if (lm) Pose(lm, new Vector3(target.x, lm.position.y, target.z - 1.6f), lm.rotation);
            var cam = All().FirstOrDefault(t => t.name == "cam_grid");
            if (cam) { var p = new Vector3(10, 6, gate.position.z - 8); Pose(cam, p, Quaternion.LookRotation(new Vector3(gate.position.x, 3, gate.position.z) - p)); }
            EditorUtility.SetDirty(session);
            return $"{nodes.Length} old Jack nodes inactive, chunks rebuilt; lattice interaction {V(target)} at the Meshy ring {V(gate.position)}; ring offline interaction unbound ({rec.ringPoint})";
        }

        static string Droid()
        {
            var d = Find("Ward mining droid"); SetActive(d, false);
            var r = All().FirstOrDefault(t => t.name == "Mining droid route" && !t.parent); if (r) SetActive(r, false);
            return "Ward mining droid and its route inactive";
        }

        static string Trolley()
        {
            var t = Find("Outer Berms/West Gate outpost/Outpost/Field fabricator"); SetActive(t, false);
            return "West Gate field fabricator tool cart inactive at " + V(t.position);
        }

        static string Barrels()
        {
            var t = Find("Karaveen caravan market/Caravan stock/COL_barrels");
            var box = t.GetComponent<BoxCollider>(); if (!box) throw new Exception("COL_barrels has no BoxCollider");
            var p = PathOf(t);
            if (!rec.box.ContainsKey(p)) rec.box[p] = new[] { box.center.x, box.center.y, box.center.z, box.size.x, box.size.y, box.size.z };
            // the two whole barrels stand at about (-45.9, 5.3) and (-46.6, 7.1) (build_market.py line 812, scale 0.8);
            // the box covers them (0.85 m wide, 0.9 m high) and leaves the loose staves, hoops and lids walk-over
            var a = new Vector3(-45.9f, 0, 5.3f); var b = new Vector3(-46.6f, 0, 7.1f);
            var mid = (a + b) * 0.5f; var dir = (b - a).normalized; float len = (b - a).magnitude + 0.75f;
            Pose(t, new Vector3(mid.x, t.position.y, mid.z), Quaternion.LookRotation(dir));
            var s = t.lossyScale;
            box.center = Vector3.zero;
            box.size = new Vector3(0.85f / Mathf.Abs(s.x), 0.9f / Mathf.Abs(s.y), len / Mathf.Abs(s.z));
            box.center = new Vector3(0, (0.45f - t.position.y) / Mathf.Abs(s.y), 0);
            if (PrefabUtility.IsPartOfPrefabInstance(box)) PrefabUtility.RecordPrefabInstancePropertyModifications(box);
            Physics.SyncTransforms();
            return $"COL_barrels now {V(box.bounds.min)}..{V(box.bounds.max)}";
        }

        static string Outpost()
        {
            var log = new List<string>();
            // light tower trailer: 12 m west, beside the 10 m distance post outside every line of fire, turned so its
            // flood keeps the same bearing onto the plates; its practical light moves and turns with it
            var tower = Find("Outer Berms/West Gate outpost/Outpost/Light tower");
            var flood = Find("Outer Berms/West Gate outpost/Practical lights/Light tower flood");
            var from = tower.position; var to = new Vector3(-79.5f, 0, 5.0f);
            float yaw = Vector3.SignedAngle(Flat(PlatesCentre - from), Flat(PlatesCentre - to), Vector3.up);
            var q = Quaternion.Euler(0, yaw, 0);
            float gy = Ground(to.x, to.z, tower), gy0 = Ground(from.x, from.z, tower);
            if (float.IsNaN(gy) || float.IsNaN(gy0)) throw new Exception("No ground under the light tower");
            var np = new Vector3(to.x, from.y + (gy - gy0), to.z);
            var fOff = flood.position - from;
            Pose(tower, np, q * tower.rotation);
            Pose(flood, np + q * fOff, q * flood.rotation);
            log.Add($"light tower {V(from)} -> {V(np)} yaw {yaw:0}");
            // range sign: beside the barrier line, left of the approach
            var sign = Find("Outer Berms/West Gate outpost/Outpost/Training range sign");
            var sTo = new Vector3(-67.4f, 0, 4.4f);
            float sg = Ground(sTo.x, sTo.z, sign), sg0 = Ground(sign.position.x, sign.position.z, sign);
            var sp = new Vector3(sTo.x, sign.position.y + (sg - sg0), sTo.z);
            log.Add($"range sign {V(sign.position)} -> {V(sp)}");
            Pose(sign, sp, sign.rotation);
            // the didelta shrub standing in the approach
            var shrub = All().Where(t => t.name == "dideltasmall" && PathOf(t).StartsWith("Outer Berms/West Gate outpost/"))
                .OrderBy(t => Vector2.Distance(new Vector2(t.position.x, t.position.z), new Vector2(-64f, 6.3f))).FirstOrDefault();
            if (shrub && Vector2.Distance(new Vector2(shrub.position.x, shrub.position.z), new Vector2(-64f, 6.3f)) < 1.5f) { SetActive(shrub, false); log.Add("shrub inactive at " + V(shrub.position)); }
            else log.Add("shrub not found near (-64, 6.3)");
            return string.Join("; ", log);
        }
        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }

        static string Verify()
        {
            var fails = new List<string>();
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var authored = All().First(t => t.name == "AuthoredWorld" && !t.parent);
            if (authored.GetComponentsInChildren<Transform>(true).Any(t => t.gameObject.activeSelf && LatticePrefixes.Any(p => t.name.StartsWith(p, StringComparison.Ordinal)))) fails.Add("old Jack node active");
            if (session.ringPoint) fails.Add("ring offline interaction still bound");
            var gate = All().First(t => t.name == "Meshy Ring Gate" && !t.parent);
            if (Vector3.Distance(Flat(session.latticePoint.position), Flat(gate.position)) > 3f) fails.Add("lattice point not at the Meshy ring");
            if (Find("Ward mining droid").gameObject.activeSelf) fails.Add("mining droid active");
            if (Find("Outer Berms/West Gate outpost/Outpost/Field fabricator").gameObject.activeSelf) fails.Add("trolley active");
            var box = Find("Karaveen caravan market/Caravan stock/COL_barrels").GetComponent<BoxCollider>();
            var bs = Vector3.Scale(box.size, box.transform.lossyScale); if (Mathf.Abs(bs.x * bs.z) > 3.5f) fails.Add("barrel collider still large " + V(bs));   // oriented footprint
            var missing = All().SelectMany(t => t.GetComponents<Component>()).Count(c => c == null);
            var result = $"verify {(fails.Count == 0 ? "PASS" : "FAIL " + string.Join(", ", fails))}; lattice {V(session.latticePoint.position)}; barrel box {V(box.bounds.min)}..{V(box.bounds.max)}; missing scripts in scene {missing}";
            if (fails.Count > 0) throw new Exception(result);
            return result;
        }

        static string Rollback()
        {
            foreach (var kv in rec.active) { var t = All().FirstOrDefault(x => PathOf(x) == kv.Key); if (t) t.gameObject.SetActive(kv.Value); }
            foreach (var kv in rec.pose) { var t = All().FirstOrDefault(x => PathOf(x) == kv.Key); if (t) { var v = kv.Value; t.SetPositionAndRotation(new Vector3(v[0], v[1], v[2]), new Quaternion(v[3], v[4], v[5], v[6])); } }
            foreach (var kv in rec.box) { var t = All().FirstOrDefault(x => PathOf(x) == kv.Key); var b = t ? t.GetComponent<BoxCollider>() : null; if (b) { var v = kv.Value; b.center = new Vector3(v[0], v[1], v[2]); b.size = new Vector3(v[3], v[4], v[5]); } }
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            if (!string.IsNullOrEmpty(rec.ringPoint)) { session.ringPoint = All().First(x => PathOf(x) == rec.ringPoint); EditorUtility.SetDirty(session); }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) StaticRenderChunksEditor.Rebuild(chunks);
            rec = new Rec();
            return "rolled back";
        }

        /// -executeMethod AthenHill.Editor.PlaytestFixes20261003.RunBatch --steps lattice,droid,trolley,barrels,outpost,verify
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = (i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify").Split(',');
            try
            {
                EditorSceneManager.OpenScene(ScenePath);
                rec = Load();
                foreach (var st in steps)
                {
                    string r = st switch { "lattice" => Lattice(), "droid" => Droid(), "trolley" => Trolley(), "barrels" => Barrels(), "outpost" => Outpost(), "verify" => Verify(), "rollback" => Rollback(), _ => throw new Exception("unknown step " + st) };
                    rec.log.Add(DateTime.UtcNow.ToString("u") + " " + st + ": " + r);
                    Debug.Log("PlaytestFixes20261003 " + st + ": " + r);
                }
                var scene = EditorSceneManager.GetActiveScene();
                EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
                Save();
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }   // scene not saved, record unchanged
        }
    }
}
