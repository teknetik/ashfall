using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// Light budget pass (20 Nov 2026). Record: art/light_budget_20261120/README.md.
    ///
    ///   -executeMethod AthenHill.Editor.LightBudgetPass20261120.RunBatch --steps survey|install|mira|verify|rollback
    ///
    /// survey   read-only: every light (owners found from serialized references, the clock's lists, layer masks, cookies),
    ///          the review cameras and how many lights each would see at night with no budget, near-duplicate pairs -> survey.json
    /// install  idempotent: reads lb-tune.json; retires the listed redundant lights (Light component disabled, originals in
    ///          originals.json; merged keepers get the recorded intensity/range change), builds the `Ward light budget` root
    ///          with LightBudget (every clock lamp and every unowned static light, minus the retired ones), the pool
    ///          material asset and the `Light budget review cameras` root with the cam_lb_* cameras.
    /// mira     idempotent: re-aims Basic General's two counter lamps (owned by the night facade pass) from lb-tune.json,
    ///          originals recorded first. Re-running NightFacadePass would undo this.
    /// verify   saved scene -> verify.json; throws on any problem.
    /// rollback restores every recorded light, removes the two roots; the pool material asset is left in place.
    public static class LightBudgetPass20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Dir = "../../art/light_budget_20261120/";
        const string TunePath = Dir + "lb-tune.json", OriginalsPath = Dir + "originals.json";
        const string RootName = "Ward light budget", CameraRoot = "Light budget review cameras";
        const string ShaderPath = "Assets/AthenHill/Shaders/LampPool.shader";
        const string MaterialPath = "Assets/AthenHill/Materials/Lighting/LB_LampPool.mat";

        static Scene OpenScene()
        {
            var scene = SceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            return scene;
        }
        static JObject Json(string path) => File.Exists(path) ? JObject.Parse(File.ReadAllText(path)) : new JObject();
        static void Save(string path, object o) => File.WriteAllText(path, JsonConvert.SerializeObject(o, Formatting.Indented,
            new JsonSerializerSettings { ReferenceLoopHandling = ReferenceLoopHandling.Ignore }));
        static float R(float v) => (float)Math.Round(v, 3);
        static float[] A(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };
        static float[] A(Color c) => new[] { R(c.r), R(c.g), R(c.b) };
        static Vector3 V(JToken a) => new Vector3((float)a[0], (float)a[1], (float)a[2]);
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static Transform Find(Scene scene, string path)
        {
            var parts = path.Split('/');
            foreach (var root in scene.GetRootGameObjects().Where(g => g.name == parts[0]))
            {
                var t = root.transform;
                for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
                if (t) return t;
            }
            return null;
        }
        static Light LightAt(Scene scene, string path)
        {
            var t = Find(scene, path) ?? throw new Exception("no object at " + path);
            return t.GetComponent<Light>() ?? throw new Exception("no Light on " + path);
        }

        static Light[] AllLights(Scene scene) => scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Light>(true)).ToArray();

        /// Every MonoBehaviour type that holds a serialized reference to each light (arrays included).
        static Dictionary<Light, HashSet<string>> Owners(Scene scene)
        {
            var map = new Dictionary<Light, HashSet<string>>();
            foreach (var mb in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MonoBehaviour>(true)))
            {
                if (!mb || mb is LightBudget) continue;
                var so = new SerializedObject(mb); var it = so.GetIterator();
                while (it.Next(true))
                {
                    if (it.propertyType != SerializedPropertyType.ObjectReference) continue;
                    if (it.objectReferenceValue is Light l)
                    {
                        if (!map.TryGetValue(l, out var set)) map[l] = set = new HashSet<string>();
                        set.Add(mb.GetType().Name);
                    }
                }
            }
            return map;
        }

        // Components that move or drive their lights themselves: anything under them is never managed.
        static readonly string[] MovingOwners = { "PlayerMotor", "NpcAgent", "AmbientWalker", "FeralDroid", "FxBurst", "MuzzleFlash", "SalvageCache", "CharacterPreview" };

        static string Classify(Light l, HashSet<string> owners, CityLightCircuit circuit)
        {
            if (l.type == LightType.Directional) return "directional";
            if (!l.gameObject.activeInHierarchy || !l.enabled) return "inactive";
            foreach (var mb in l.GetComponentsInParent<MonoBehaviour>(true))
                if (mb && MovingOwners.Contains(mb.GetType().Name)) return "unmanaged:" + mb.GetType().Name;
            var other = owners == null ? new string[0] : owners.Where(o => o != "CityLightCircuit" && o != "NightReadabilityQa").ToArray();
            // salvage search markers: SalvageNode switches them on change only; the budget reads the node's state instead
            if (other.Length == 1 && other[0] == "SalvageNode" && !(circuit && circuit.practicalLights.Contains(l))) return "marker";
            if (other.Length > 0) return "unmanaged:" + string.Join("+", other);
            // a script on the light's own object drives it through GetComponent (FireFlicker and the like)
            var self = l.GetComponents<MonoBehaviour>().FirstOrDefault(x => x && !(x.GetType().Namespace ?? "").StartsWith("UnityEngine", StringComparison.Ordinal));
            if (self) return "unmanaged:" + self.GetType().Name;
            if (((uint)l.renderingLayerMask & 1u) == 0) return "unmanaged:layer";
            bool inCircuit = circuit && circuit.practicalLights.Contains(l);
            return inCircuit ? "circuit" : "static";
        }

        // ------------------------------------------------------------------ survey (read-only)
        public static string Survey()
        {
            var scene = OpenScene();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var owners = Owners(scene); var lights = AllLights(scene);
            var nightOnly = circuit ? new HashSet<Light>(circuit.nightOnlyLights.Where(x => x)) : new HashSet<Light>();
            var rows = new List<Dictionary<string, object>>();
            var cls = new Dictionary<Light, string>();
            foreach (var l in lights)
            {
                owners.TryGetValue(l, out var o);
                var c = Classify(l, o, circuit); cls[l] = c;
                rows.Add(new Dictionary<string, object>
                {
                    ["path"] = PathOf(l.transform), ["type"] = l.type.ToString(), ["class"] = c, ["owners"] = o?.ToArray() ?? new string[0],
                    ["nightOnly"] = nightOnly.Contains(l), ["active"] = l.gameObject.activeInHierarchy, ["enabled"] = l.enabled,
                    ["intensity"] = R(l.intensity), ["range"] = R(l.range), ["spot"] = l.type == LightType.Spot ? new[] { R(l.spotAngle), R(l.innerSpotAngle) } : null,
                    ["color"] = A(l.color), ["cookie"] = l.cookie ? l.cookie.name : null, ["layer"] = l.renderingLayerMask, ["shadows"] = l.shadows.ToString(),
                    ["pos"] = A(l.transform.position), ["fwd"] = A(l.transform.forward), ["prefab"] = PrefabUtility.IsPartOfPrefabInstance(l) ? AssetDatabase.GetAssetPath(PrefabUtility.GetCorrespondingObjectFromSource(l)) : null,
                });
            }
            // near-duplicate pairs: same type, both live, within 0.75 m, similar colour and aim
            var live = lights.Where(l => cls[l] == "circuit" || cls[l] == "static").ToArray();
            var pairs = new List<object>();
            for (int i = 0; i < live.Length; i++)
                for (int j = i + 1; j < live.Length; j++)
                {
                    var a = live[i]; var b = live[j];
                    if (a.type != b.type) continue;
                    float d = Vector3.Distance(a.transform.position, b.transform.position); if (d > .75f) continue;
                    float aim = a.type == LightType.Spot ? Vector3.Angle(a.transform.forward, b.transform.forward) : 0;
                    pairs.Add(new { a = PathOf(a.transform), b = PathOf(b.transform), dist = R(d), aimDeg = R(aim), ia = R(a.intensity), ib = R(b.intensity), ra = R(a.range), rb = R(b.range) });
                }
            // per review camera: lights in view at night with no budget (clock lamps within its 150 m cull, interiors within 34 m)
            var cams = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).Where(c => c.name.StartsWith("cam_", StringComparison.Ordinal)).ToArray();
            var interiors = UnityEngine.Object.FindObjectsByType<InteriorLighting>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            var camRows = new List<object>();
            foreach (var c in cams)
            {
                var planes = GeometryUtility.CalculateFrustumPlanes(Matrix4x4.Perspective(c.fieldOfView, 16f / 9f, .1f, 1600) * c.worldToCameraMatrix);
                int n = 0, managed = 0;
                foreach (var l in lights)
                {
                    var k = cls[l]; if (k == "directional" || k == "inactive") continue;
                    if (k.StartsWith("unmanaged:Feral") || k.StartsWith("unmanaged:Fx") || k.StartsWith("unmanaged:Muzzle") || k.StartsWith("unmanaged:Salvage") || k.StartsWith("unmanaged:Character")) continue;
                    float d = Vector3.Distance(c.transform.position, l.transform.position);
                    if (k == "circuit" && d > (circuit ? circuit.culledLightDistance : 150)) continue;
                    if (k.Contains("InteriorLighting") && interiors.All(x => Vector3.Distance(c.transform.position, x.transform.position) > x.lampsOnWithin)) continue;
                    if (!GeometryUtility.TestPlanesAABB(planes, new Bounds(l.transform.position, Vector3.one * 2 * l.range))) continue;
                    n++; if (k == "circuit" || k == "static") managed++;
                }
                camRows.Add(new { c.name, pos = A(c.transform.position), euler = A(c.transform.eulerAngles), fov = R(c.fieldOfView), parent = c.transform.parent ? c.transform.parent.name : null, nightInView = n, managedInView = managed });
            }
            // geometry round Mira's counter (for the counter-lamp re-aim)
            var miraT = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).FirstOrDefault(t => t.name == "npc_mira");
            object miraArea = null;
            if (miraT)
            {
                var mp = miraT.position;
                miraArea = new
                {
                    pos = A(mp), fwd = A(miraT.forward),
                    renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>(false)).Where(x => x.enabled && !x.transform.IsChildOf(miraT) && Vector3.Distance(x.bounds.center, mp) < 3.5f && x.bounds.size.magnitude < 12)
                        .Select(x => new { name = PathOf(x.transform), c = A(x.bounds.center), size = A(x.bounds.size) }).ToArray(),
                    colliders = Physics.OverlapSphere(mp + Vector3.up, 3f).Where(x => !x.transform.IsChildOf(miraT)).Select(x => new { name = PathOf(x.transform), c = A(x.bounds.center), size = A(x.bounds.size) }).ToArray(),
                    bones = miraT.GetComponentsInChildren<Transform>(true).Where(t => t.name.ToLower().Contains("head") || t.name.ToLower().Contains("spine")).Select(t => new { t.name, p = A(t.position) }).ToArray()
                };
            }
            var r = new Dictionary<string, object>
            {
                ["miraArea"] = miraArea,
                ["lights"] = lights.Length,
                ["byClass"] = cls.GroupBy(x => x.Value).OrderBy(g => g.Key).ToDictionary(g => g.Key, g => g.Count()),
                ["circuit"] = circuit ? new { path = PathOf(circuit.transform), circuit.fullLightDistance, circuit.culledLightDistance, circuit.shadowDistance, practical = circuit.practicalLights.Length, nightOnly = circuit.nightOnlyLights.Length, viewer = circuit.viewer ? PathOf(circuit.viewer) : null, circuit.daytimeStrength, circuit.nightOnlyThreshold } : null,
                ["cameras"] = camRows, ["nearDuplicates"] = pairs, ["rows"] = rows,
            };
            Save(Dir + "survey.json", r);
            return lights.Length + " lights; " + string.Join(", ", ((Dictionary<string, int>)r["byClass"]).Select(x => x.Key + " " + x.Value)) + "; " + pairs.Count + " near-duplicate pairs; " + cams.Length + " cameras";
        }

        // ------------------------------------------------------------------ install
        static Material PoolMaterial()
        {
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath) ?? throw new Exception("missing " + ShaderPath);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            if (!mat)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(MaterialPath));
                mat = new Material(shader) { name = "LB_LampPool" };
                AssetDatabase.CreateAsset(mat, MaterialPath);
            }
            else if (mat.shader != shader) mat.shader = shader;
            mat.enableInstancing = false; EditorUtility.SetDirty(mat);
            return mat;
        }

        static void RecordLight(JObject orig, string path, Light l)
        {
            var ol = (JObject)(orig["lights"] ??= new JObject());
            if (ol[path] != null) return;
            var t = l.transform;
            ol[path] = new JObject { ["enabled"] = l.enabled, ["intensity"] = l.intensity, ["range"] = l.range, ["spotAngle"] = l.spotAngle, ["innerSpotAngle"] = l.innerSpotAngle,
                ["localEuler"] = new JArray(t.localEulerAngles.x, t.localEulerAngles.y, t.localEulerAngles.z), ["localPosition"] = new JArray(t.localPosition.x, t.localPosition.y, t.localPosition.z) };
        }
        static void RestoreLight(Light l, JObject v)
        {
            var t = l.transform;
            Undo.RecordObject(l, "Light budget"); Undo.RecordObject(t, "Light budget");
            l.enabled = (bool)v["enabled"]; l.intensity = (float)v["intensity"]; l.range = (float)v["range"];
            l.spotAngle = (float)v["spotAngle"]; l.innerSpotAngle = (float)v["innerSpotAngle"];
            t.localEulerAngles = V(v["localEuler"]); t.localPosition = V(v["localPosition"]);
            Dirty(l);
        }
        static void Dirty(Light l)
        {
            EditorUtility.SetDirty(l); EditorUtility.SetDirty(l.transform);
            if (PrefabUtility.IsPartOfPrefabInstance(l)) { PrefabUtility.RecordPrefabInstancePropertyModifications(l); PrefabUtility.RecordPrefabInstancePropertyModifications(l.transform); }
        }

        public static string Install()
        {
            var scene = OpenScene(); var tune = Json(TunePath); var orig = Json(OriginalsPath);
            var log = new List<string>();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>() ?? throw new Exception("no CityLightCircuit");
            // 1. retire redundant lights (merge keepers first get their recorded change)
            var retired = new HashSet<Light>();
            foreach (JObject m in (JArray)tune["merge"] ?? new JArray())
            {
                var keepPath = (string)m["keep"]; var keep = LightAt(scene, keepPath);
                RecordLight(orig, keepPath, keep);
                var o = (JObject)orig["lights"][keepPath];
                Undo.RecordObject(keep, "Light budget");
                keep.intensity = (float)o["intensity"] * (m["intensityScale"] != null ? (float)m["intensityScale"] : 1);
                keep.range = (float)o["range"] * (m["rangeScale"] != null ? (float)m["rangeScale"] : 1);
                if (m["spotAngle"] != null) keep.spotAngle = (float)m["spotAngle"];
                Dirty(keep);
                foreach (var dp in (JArray)m["retire"]) { var l = LightAt(scene, (string)dp); RecordLight(orig, (string)dp, l); retired.Add(l); }
                log.Add("merge into " + keep.name);
            }
            foreach (JObject d in (JArray)tune["retire"] ?? new JArray()) { var p = (string)d["path"]; var l = LightAt(scene, p); RecordLight(orig, p, l); retired.Add(l); }
            foreach (var l in retired) { Undo.RecordObject(l, "Light budget"); l.enabled = false; Dirty(l); }
            if (retired.Count > 0) log.Add(retired.Count + " retired");
            Save(OriginalsPath, orig);

            // 2. budget root
            var owners = Owners(scene);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (!root) { root = new GameObject(RootName); SceneManager.MoveGameObjectToScene(root, scene); Undo.RegisterCreatedObjectUndo(root, "Light budget"); }
            var budget = root.GetComponent<LightBudget>() ?? root.AddComponent<LightBudget>();
            budget.circuit = circuit; budget.poolMaterial = PoolMaterial();
            var priorities = ((JArray)tune["priorities"] ?? new JArray()).Cast<JObject>().ToArray();
            var noPool = ((JArray)tune["noPool"] ?? new JArray()).Select(x => (string)x).ToArray();
            var lamps = new List<LightBudget.Lamp>();
            foreach (var l in AllLights(scene))
            {
                if (retired.Contains(l)) continue;
                owners.TryGetValue(l, out var o);
                var c = Classify(l, o, circuit);
                if (c != "circuit" && c != "static" && c != "marker") continue;
                var path = PathOf(l.transform);
                SalvageNode node = null;
                if (c == "marker") node = UnityEngine.Object.FindObjectsByType<SalvageNode>(FindObjectsInactive.Include).FirstOrDefault(x => x.readyLight == l);
                float pr = 1; foreach (var p in priorities) if (path.Contains((string)p["match"])) pr = (float)p["priority"];
                lamps.Add(new LightBudget.Lamp { light = l, owner = c == "circuit" ? LightBudget.LampOwner.Circuit : c == "marker" ? LightBudget.LampOwner.Marker : LightBudget.LampOwner.Static,
                    marker = node, priority = pr, pool = c != "marker" && !noPool.Any(x => path.Contains(x)), poolScale = 1 });
            }
            budget.lamps = lamps.ToArray();
            if (tune["budget"] is JObject b)
                foreach (var p in b.Properties())
                {
                    var f = typeof(LightBudget).GetField(p.Name) ?? throw new Exception("no LightBudget field " + p.Name);
                    f.SetValue(budget, f.FieldType == typeof(int) ? (object)(int)p.Value : f.FieldType == typeof(Color) ? new Color((float)p.Value[0], (float)p.Value[1], (float)p.Value[2], 1) : (float)p.Value);
                }
            EditorUtility.SetDirty(budget);
            log.Add(lamps.Count + " lamps (" + lamps.Count(x => x.owner == LightBudget.LampOwner.Circuit) + " clock, " + lamps.Count(x => x.owner == LightBudget.LampOwner.Static) + " static, " + lamps.Count(x => x.owner == LightBudget.LampOwner.Marker) + " salvage markers)");

            // 3. review cameras (recreated each install)
            var oldCams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CameraRoot);
            if (oldCams) UnityEngine.Object.DestroyImmediate(oldCams);
            if (tune["cameras"] is JArray cams && cams.Count > 0)
            {
                var camRoot = new GameObject(CameraRoot); SceneManager.MoveGameObjectToScene(camRoot, scene);
                var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).ToArray();
                foreach (JObject c in cams)
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(camRoot.transform, false);
                    var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = c["fov"] != null ? (float)c["fov"] : 50; cam.nearClipPlane = .1f; cam.farClipPlane = 1600;
                    if (c["from"] != null)
                    {
                        var src = all.FirstOrDefault(x => x.name == (string)c["from"]) ?? throw new Exception("no camera " + c["from"]);
                        go.transform.SetPositionAndRotation(src.transform.position + (c["offset"] != null ? V(c["offset"]) : Vector3.zero), src.transform.rotation);
                        if (c["fov"] == null) cam.fieldOfView = src.fieldOfView;
                    }
                    else go.transform.SetPositionAndRotation(V(c["pos"]), Quaternion.Euler(V(c["euler"])));
                    if (c["lookAt"] != null) go.transform.rotation = Quaternion.LookRotation(V(c["lookAt"]) - go.transform.position, Vector3.up);
                    if (Physics.CheckSphere(go.transform.position, .2f, ~0, QueryTriggerInteraction.Ignore)) Debug.LogWarning("LightBudgetPass20261120: camera " + go.name + " starts inside a collider");
                }
                log.Add(cams.Count + " cameras");
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            return string.Join(", ", log);
        }

        // ------------------------------------------------------------------ mira
        public static string Mira()
        {
            var scene = OpenScene(); var tune = Json(TunePath); var orig = Json(OriginalsPath);
            var log = new List<string>();
            foreach (JObject a in (JArray)tune["mira"] ?? new JArray())
            {
                var path = (string)a["path"]; var l = LightAt(scene, path);
                RecordLight(orig, path, l);
                var o = (JObject)orig["lights"][path];
                var t = l.transform;
                Undo.RecordObject(l, "Light budget Mira"); Undo.RecordObject(t, "Light budget Mira");
                // always from the recorded original, so a second run gives the same result
                t.localEulerAngles = V(o["localEuler"]); t.localPosition = V(o["localPosition"]);
                if (a["localOffset"] != null) t.localPosition += V(a["localOffset"]);
                if (a["aimAt"] != null) t.rotation = Quaternion.LookRotation(V(a["aimAt"]) - t.position, Vector3.up);
                l.intensity = (float)o["intensity"] * (a["intensityScale"] != null ? (float)a["intensityScale"] : 1);
                if (a["spotAngle"] != null) l.spotAngle = (float)a["spotAngle"];
                if (a["innerSpotAngle"] != null) l.innerSpotAngle = (float)a["innerSpotAngle"];
                Dirty(l);
                log.Add(l.name + " euler " + string.Join(",", A(t.eulerAngles)));
            }
            Save(OriginalsPath, orig);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ verify (saved scene)
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var tune = Json(TunePath); var orig = Json(OriginalsPath);
            var problems = new List<string>(); var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            var budget = root ? root.GetComponent<LightBudget>() : null;
            if (!budget) problems.Add("LightBudget root missing");
            else
            {
                if (!budget.circuit) problems.Add("budget has no circuit");
                if (!budget.poolMaterial || !budget.poolMaterial.shader || budget.poolMaterial.shader.name != "Athen Hill/Lamp Pool") problems.Add("pool material/shader missing");
                int nulls = budget.lamps.Count(x => x == null || !x.light); if (nulls > 0) problems.Add(nulls + " lamp entries without a light");
                if (budget.lamps.Select(x => x.light).Distinct().Count() != budget.lamps.Length) problems.Add("duplicate lamp entries");
                if (budget.lamps.Any(x => x.light && x.light.type == LightType.Directional)) problems.Add("directional light in the budget");
                r["lamps"] = budget.lamps.Length; r["clockLamps"] = budget.lamps.Count(x => x.owner == LightBudget.LampOwner.Circuit);
                r["staticLamps"] = budget.lamps.Count(x => x.owner == LightBudget.LampOwner.Static); r["pools"] = budget.lamps.Count(x => x.pool);
                r["hardCap"] = budget.hardCap; r["settings"] = new { budget.fadeMargin, budget.hysteresis, budget.minHoldSeconds, budget.fadeSeconds, budget.offscreenKeep, budget.pinBoost, budget.wideFovScale, budget.poolGain, budget.cookiePoolScale, budget.shadowedPoolScale, budget.nearMetres, poolAlbedo = A(budget.poolAlbedo), budget.poolMinStrength };
                var circuitSet = new HashSet<Light>(budget.circuit ? budget.circuit.practicalLights.Where(x => x) : new Light[0]);
                foreach (var l in budget.lamps.Where(x => x?.light && x.owner == LightBudget.LampOwner.Circuit)) if (!circuitSet.Contains(l.light)) problems.Add("clock lamp not on the clock: " + l.light.name);
                // the budget must not take lamps another script drives
                var owners = Owners(scene);
                foreach (var l in budget.lamps.Where(x => x?.light))
                    if (owners.TryGetValue(l.light, out var o) && o.Any(x => x != "CityLightCircuit" && x != "NightReadabilityQa" && !(x == "SalvageNode" && l.owner == LightBudget.LampOwner.Marker))) problems.Add("lamp driven by " + string.Join("+", o) + ": " + l.light.name);
                foreach (var l in budget.lamps.Where(x => x?.light && x.owner == LightBudget.LampOwner.Marker)) if (!l.marker || l.marker.readyLight != l.light) problems.Add("salvage marker without its node: " + l.light.name);
                r["markerLamps"] = budget.lamps.Count(x => x.owner == LightBudget.LampOwner.Marker);
            }
            // retired lights are off, merged keepers changed, Mira's lamps aimed
            var retiredPaths = ((JArray)tune["retire"] ?? new JArray()).Select(x => (string)x["path"])
                .Concat(((JArray)tune["merge"] ?? new JArray()).SelectMany(m => ((JArray)m["retire"]).Select(x => (string)x))).ToArray();
            foreach (var p in retiredPaths)
            {
                var t = Find(scene, p); var l = t ? t.GetComponent<Light>() : null;
                if (!l) problems.Add("retired light missing " + p); else if (l.enabled) problems.Add("retired light still enabled " + p);
                if (orig["lights"]?[p] == null) problems.Add("no original recorded for " + p);
                if (budget && l && budget.lamps.Any(x => x.light == l)) problems.Add("retired light in the budget " + p);
            }
            r["retired"] = retiredPaths;
            var mira = new List<object>();
            foreach (JObject a in (JArray)tune["mira"] ?? new JArray())
            {
                var t = Find(scene, (string)a["path"]); var l = t ? t.GetComponent<Light>() : null;
                if (!l) { problems.Add("Mira lamp missing " + a["path"]); continue; }
                if (orig["lights"]?[(string)a["path"]] == null) problems.Add("Mira lamp original not recorded");
                if (a["aimAt"] != null && Vector3.Angle(t.forward, V(a["aimAt"]) - t.position) > .5f) problems.Add("Mira lamp not aimed " + l.name);
                mira.Add(new { l.name, euler = A(t.eulerAngles), fwd = A(t.forward), pos = A(t.position), l.intensity, l.spotAngle, l.innerSpotAngle });
            }
            r["mira"] = mira;
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CameraRoot);
            var camNames = camRoot ? camRoot.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            foreach (JObject c in (JArray)tune["cameras"] ?? new JArray()) if (!camNames.Contains((string)c["name"])) problems.Add("camera missing " + c["name"]);
            r["cameras"] = camNames;
            // nothing missing anywhere under the new roots
            foreach (var go in new[] { root, camRoot }.Where(x => x))
                foreach (var c in go.GetComponentsInChildren<Component>(true)) if (c == null) problems.Add("missing script under " + go.name);
            var lights = AllLights(scene);
            r["lightsInScene"] = lights.Length; r["lightsEnabled"] = lights.Count(l => l.enabled && l.gameObject.activeInHierarchy);
            r["problems"] = problems;
            Save(Dir + "verify.json", r);
            if (problems.Count > 0) throw new Exception("verify: " + string.Join("; ", problems));
            return "ok: " + r["lamps"] + " lamps, " + retiredPaths.Length + " retired, " + mira.Count + " Mira lamps, " + camNames.Length + " cameras";
        }

        // ------------------------------------------------------------------ rollback
        public static string Rollback()
        {
            var scene = OpenScene(); var orig = Json(OriginalsPath); var log = new List<string>();
            foreach (var lp in ((JObject)orig["lights"] ?? new JObject()).Properties())
            {
                var t = Find(scene, lp.Name); var l = t ? t.GetComponent<Light>() : null;
                if (!l) { log.Add("gone " + lp.Name); continue; }
                RestoreLight(l, (JObject)lp.Value); log.Add("restored " + l.name);
            }
            foreach (var n in new[] { RootName, CameraRoot })
            {
                var g = scene.GetRootGameObjects().FirstOrDefault(x => x.name == n);
                if (g) { UnityEngine.Object.DestroyImmediate(g); log.Add("removed " + n); }
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            if (File.Exists(OriginalsPath)) { File.Copy(OriginalsPath, Dir + "originals.rolled-back-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json", true); File.Delete(OriginalsPath); }
            return string.Join(", ", log);
        }

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int k = Array.IndexOf(args, "--steps"); var steps = k >= 0 && k + 1 < args.Length ? args[k + 1] : "survey";
            try
            {
                Directory.CreateDirectory(Dir);
                foreach (var st in steps.Split(','))
                {
                    string result = st switch { "survey" => Survey(), "install" => Install(), "mira" => Mira(), "verify" => Verify(), "rollback" => Rollback(), _ => throw new Exception("unknown step " + st) };
                    Debug.Log("LightBudgetPass20261120 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
