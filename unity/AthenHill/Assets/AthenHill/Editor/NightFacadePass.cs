using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: night facade tune (art-direction review item 10). Material and light edits only:
    ///  * the caged wall lamps of the nine Ward shops and Vanguard Hall (PH_WallLamp heads + "Bulb" sphere + a warm point
    ///    light 0.2 m in front of the bulb) become down-and-out spots with a soft cookie, placed further out and lower, so
    ///    they wash the wall below and the porch instead of burning a clipped disc into the stone around the fixture;
    ///    the bulbs move from VH_LampLens (emission 6, shared with the tree uplights and West Gate bulkheads) to
    ///    NF_WallLampBulb (1–2 stops over the lit wall), registered on the Ward lighting clock;
    ///  * the Ward Window Interior glass: lower room-lamp emission, more blinds and curtains, a third lamp colour
    ///    temperature (shader property _NeutralFraction, default 0 = previous look) and per-street lit fractions
    ///    (WS_Glass for the hall-district west side, NF_Glass_HallEast for Finery and Field Supply, NF_Glass_North for
    ///    Salvage, Repairs and Thread + Hide; VH_Glass for the hall);
    ///  * the Ward masonry (VH_Ashlar, VH_AshlarRough) normal strength.
    /// Values live in art/night_facade_20261001/facade-tune.json; the original values are recorded once in
    /// originals.json at install, and every `apply` recomputes from those originals (idempotent). `rollback` restores them.
    /// Steps (batch): survey, shadercheck, build, install, apply, cameras, verify, rollback, capture:HOUR:cam+cam.
    /// </summary>
    public static class NightFacadePass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string ArtDir = "Assets/AthenHill/Art/NightFacade/";
        const string MatDir = ArtDir + "Materials/";
        const string TexDir = ArtDir + "Textures/";
        const string CookiePath = TexDir + "NF_WallLampCookie.png";
        const string BulbPath = MatDir + "NF_WallLampBulb.mat";
        const string LampGlassPath = MatDir + "NF_WallLampGlass.mat";
        const string PhGlassPath = "Assets/AthenHill/Art/WestGate/Materials/PH_industrial_wall_lamp_glass.mat";
        const string BulkheadLensPath = MatDir + "NF_BulkheadLens.mat";
        const string HallMats = "Assets/AthenHill/Art/VanguardHall/Materials/";
        const string ShopMats = "Assets/AthenHill/Art/WardShops/Materials/";
        const string WindowShader = "Assets/AthenHill/Shaders/WardWindowInterior.shader";
        const string Source = "../../art/night_facade_20261001/";
        const string Evidence = "../evidence/night-facade/20261001/";
        const string CamRootName = "Night facade review cameras";
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        static JObject Tune() => JObject.Parse(File.ReadAllText(Source + "facade-tune.json"));
        static string OriginalsPath => Source + "originals.json";
        static float[] A(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };
        static float[] A(Color c) => new[] { R(c.r), R(c.g), R(c.b), R(c.a) };
        static float R(float f) => (float)Math.Round(f, 4);
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static string Rel(Transform t, Transform root) => t == root ? "" : (t.parent == root ? t.name : Rel(t.parent, root) + "/" + t.name);

        static UnityEngine.SceneManagement.Scene OpenScene()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            return scene;
        }

        static void Save(string name, object o)
        {
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + name, JsonConvert.SerializeObject(o, Formatting.Indented));
        }

        // ------------------------------------------------------------------ survey (read only)
        /// Lamp heads, bulbs and lights of every PH_WallLamp in the shops and hall, prefab instance overrides on them,
        /// window-shader renderers per material, the light circuit, decals at the Finery frontage, and the caster of the
        /// floating 13:00 shadow at the hill benches (mesh ray tests along the sun direction).
        public static string Survey()
        {
            var scene = OpenScene();
            var r = new Dictionary<string, object>();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var practical = new HashSet<Light>(circuit ? circuit.practicalLights.Where(l => l) : Enumerable.Empty<Light>());
            var nightOnly = new HashSet<Light>(circuit ? circuit.nightOnlyLights.Where(l => l) : Enumerable.Empty<Light>());
            r["circuit"] = circuit ? new
            {
                path = PathOf(circuit.transform),
                practical = circuit.practicalLights.Length,
                nightOnly = circuit.nightOnlyLights.Length,
                emissive = circuit.emissiveMaterials.Select(m => m ? AssetDatabase.GetAssetPath(m) : "null").ToArray(),
                circuit.fullLightDistance, circuit.culledLightDistance, circuit.nightOnlyThreshold,
            } : null;

            // wall lamps
            var lamps = new List<object>();
            foreach (var bulb in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).Where(t => t.name == "Bulb"))
            {
                var head = bulb.parent; var fit = head ? head.parent : null; var root = fit ? fit.parent : null;
                var lightT = root ? root.Find("Practical lights/" + head.name + " light") : null;
                var l = lightT ? lightT.GetComponent<Light>() : null;
                var br = bulb.GetComponent<Renderer>();
                var inst = PrefabUtility.GetOutermostPrefabInstanceRoot(bulb.gameObject);
                lamps.Add(new
                {
                    head = PathOf(head),
                    active = bulb.gameObject.activeInHierarchy,
                    prefab = inst ? PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst) : null,
                    headPos = A(head.position), headFwd = A(head.forward),
                    bulbPos = A(bulb.position), bulbMat = br && br.sharedMaterial ? br.sharedMaterial.name : null,
                    light = l ? new
                    {
                        path = PathOf(lightT), pos = A(lightT.position), fwd = A(lightT.forward), type = l.type.ToString(),
                        l.intensity, l.range, l.spotAngle, l.innerSpotAngle, color = A(l.color), shadows = l.shadows.ToString(),
                        cookie = l.cookie ? l.cookie.name : null, enabled = l.enabled && l.gameObject.activeInHierarchy,
                        practical = practical.Contains(l), nightOnly = nightOnly.Contains(l),
                        offsetFromBulb = A(lightT.position - bulb.position),
                    } : null,
                });
            }
            r["lamps"] = lamps;

            // overrides on lights / bulbs in the scene instances (they would mask prefab-asset edits)
            var overrides = new List<object>();
            foreach (var g in scene.GetRootGameObjects())
                foreach (var inst in g.GetComponentsInChildren<Transform>(true).Select(t => t.gameObject).Where(PrefabUtility.IsOutermostPrefabInstanceRoot))
                {
                    var asset = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst);
                    if (!asset.Contains("/WardShops/") && !asset.Contains("/VanguardHall/")) continue;
                    foreach (var m in PrefabUtility.GetPropertyModifications(inst) ?? new PropertyModification[0])
                    {
                        var target = m.target;
                        string tname = target ? target.name : "?";
                        bool relevant = target is Light || (target is Transform tt && (tt.name.EndsWith(" light") || tt.name == "Bulb"))
                                        || (target is Renderer rr && (rr.name == "Bulb" || m.propertyPath.StartsWith("m_Materials")));
                        if (!relevant) continue;
                        overrides.Add(new { instance = PathOf(inst.transform), target = tname, type = target ? target.GetType().Name : "?", m.propertyPath, m.value, obj = m.objectReference ? AssetDatabase.GetAssetPath(m.objectReference) : null });
                    }
                }
            r["instanceOverrides"] = overrides;

            // window-shader renderers by material
            var windowShader = Shader.Find("Athen Hill/Ward Window Interior");
            var glass = new Dictionary<string, List<string>>();
            foreach (var rend in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>(true)))
                foreach (var m in rend.sharedMaterials.Where(m => m && m.shader == windowShader).Distinct())
                {
                    var key = AssetDatabase.GetAssetPath(m);
                    if (!glass.TryGetValue(key, out var list)) glass[key] = list = new List<string>();
                    list.Add((rend.gameObject.activeInHierarchy && rend.enabled ? "ON " : "off ") + PathOf(rend.transform));
                }
            r["windowGlass"] = glass.ToDictionary(k => k.Key, k => new { count = k.Value.Count, active = k.Value.Count(s => s.StartsWith("ON")), sample = k.Value.Where(s => s.StartsWith("ON")).Take(40).ToArray() });

            // Finery frontage decals and flat things
            var finery = new Vector3(16.5f, .5f, -17.5f);
            r["fineryDecals"] = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<DecalProjector>(true))
                .Where(d => Vector3.Distance(d.transform.position, finery) < 6f)
                .Select(d => new
                {
                    path = PathOf(d.transform), active = d.isActiveAndEnabled, pos = A(d.transform.position), euler = A(d.transform.eulerAngles),
                    size = A(d.size), pivot = A(d.pivot), mat = d.material ? AssetDatabase.GetAssetPath(d.material) + " | " + d.material.name : null,
                    d.fadeFactor, uvScale = new[] { d.uvScale.x, d.uvScale.y }, uvBias = new[] { d.uvBias.x, d.uvBias.y }, d.drawDistance,
                }).ToArray();

            // camera rays -> surface -> sun ray (13:00) for the floating shadow; and the Finery smear surface
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(false)).Where(x => x.enabled).ToArray();
            var probes = new List<object>();
            foreach (var (cam, px, py, hour) in new[]
            {
                ("cam_sd_hill_benches", 560f, 810f, 13f), ("cam_sd_hill_benches", 470f, 860f, 13f), ("cam_sd_hill_benches", 660f, 780f, 13f),
                ("cam_nl_hill_benches", 650f, 668f, 13f), ("cam_nl_hill_benches", 620f, 672f, 13f),
                ("cam_sd_finery", 300f, 700f, 20.5f), ("cam_sd_finery", 600f, 690f, 20.5f), ("cam_sd_finery", 900f, 740f, 20.5f),
            })
            {
                var c = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).FirstOrDefault(x => x.name == cam);
                if (!c) { probes.Add(new { cam, missing = true }); continue; }
                var ray = PixelRay(c, px, py, 1920, 1080);
                var hits = RayHits(renderers, ray, 200f, false);
                var surf = hits.FirstOrDefault();
                object casters = null, decals = null;
                if (surf.renderer)
                {
                    var f = clock.profile.Evaluate(hour);
                    var toSun = -(Quaternion.Euler(f.keyEuler) * Vector3.forward);
                    var sunRay = new Ray(surf.point + toSun * .02f, toSun);
                    casters = RayHits(renderers, sunRay, 300f, true).Take(12).Select(h => HitInfo(h)).ToArray();
                    decals = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<DecalProjector>(false)).Where(d => d.enabled && InsideDecal(d, surf.point))
                        .Select(d => new { path = PathOf(d.transform), mat = d.material ? d.material.name : null, d.fadeFactor, size = A(d.size), pos = A(d.transform.position) }).ToArray();
                }
                probes.Add(new
                {
                    cam, px, py, hour, camPos = A(c.transform.position),
                    surface = surf.renderer ? HitInfo(surf) : null,
                    sunCasters = casters, decalsAtSurface = decals,
                });
            }
            r["probes"] = probes;
            Save("survey.json", r);
            return $"lamps {lamps.Count}, overrides {overrides.Count}, glass materials {glass.Count}, probes {probes.Count}";
        }

        struct Hit { public Renderer renderer; public float distance; public Vector3 point; public int sub; }

        static object HitInfo(Hit h)
        {
            var mf = h.renderer.GetComponent<MeshFilter>();
            var lod = h.renderer.GetComponentInParent<LODGroup>();
            int level = -1;
            if (lod) { var lods = lod.GetLODs(); for (int i = 0; i < lods.Length; i++) if (lods[i].renderers.Contains(h.renderer)) level = i; }
            var mats = h.renderer.sharedMaterials;
            return new
            {
                path = PathOf(h.renderer.transform), distance = R(h.distance), point = A(h.point),
                shadows = h.renderer.shadowCastingMode.ToString(), mesh = mf && mf.sharedMesh ? mf.sharedMesh.name : null,
                meshAsset = mf && mf.sharedMesh ? AssetDatabase.GetAssetPath(mf.sharedMesh) : null,
                material = h.sub >= 0 && h.sub < mats.Length && mats[h.sub] ? mats[h.sub].name : null,
                lodGroup = lod ? PathOf(lod.transform) : null, lodLevel = level, layer = LayerMask.LayerToName(h.renderer.gameObject.layer),
                prefab = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(h.renderer.gameObject),
            };
        }

        static Ray PixelRay(Camera c, float px, float py, int w, int h)
        {
            float t = Mathf.Tan(c.fieldOfView * .5f * Mathf.Deg2Rad), aspect = (float)w / h;
            float x = (2 * px / w - 1) * t * aspect, y = (1 - 2 * py / h) * t;
            var tr = c.transform;
            return new Ray(tr.position, (tr.forward + x * tr.right + y * tr.up).normalized);
        }

        static bool InsideDecal(DecalProjector d, Vector3 p)
        {
            var local = d.transform.InverseTransformPoint(p) - d.pivot;
            var half = d.size * .5f;
            return Mathf.Abs(local.x) <= half.x && Mathf.Abs(local.y) <= half.y && Mathf.Abs(local.z) <= half.z;
        }

        /// Exact triangle hits (Möller–Trumbore) on every renderer whose bounds the ray crosses, nearest first.
        static List<Hit> RayHits(MeshRenderer[] renderers, Ray ray, float max, bool castersOnly)
        {
            var hits = new List<Hit>();
            foreach (var rend in renderers)
            {
                if (castersOnly && rend.shadowCastingMode == ShadowCastingMode.Off) continue;
                if (!rend.bounds.IntersectRay(ray, out float bd) || bd > max) continue;
                var mf = rend.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null;
                if (!mesh) continue;
                Vector3[] v; int subs = mesh.subMeshCount;
                try { v = mesh.vertices; } catch { continue; }
                if (v == null || v.Length == 0) continue;
                var m = rend.localToWorldMatrix;
                for (int i = 0; i < v.Length; i++) v[i] = m.MultiplyPoint3x4(v[i]);
                float best = float.MaxValue; int bestSub = -1;
                for (int s = 0; s < subs; s++)
                {
                    if (mesh.GetTopology(s) != MeshTopology.Triangles) continue;
                    var tri = mesh.GetTriangles(s);
                    for (int k = 0; k + 2 < tri.Length; k += 3)
                    {
                        if (Tri(ray, v[tri[k]], v[tri[k + 1]], v[tri[k + 2]], out float d) && d < best && d <= max) { best = d; bestSub = s; }
                    }
                }
                if (bestSub >= 0) hits.Add(new Hit { renderer = rend, distance = best, point = ray.GetPoint(best), sub = bestSub });
            }
            return hits.OrderBy(h => h.distance).ToList();
        }

        static bool Tri(Ray ray, Vector3 a, Vector3 b, Vector3 c, out float t)
        {
            t = 0; var e1 = b - a; var e2 = c - a; var p = Vector3.Cross(ray.direction, e2); float det = Vector3.Dot(e1, p);
            if (Mathf.Abs(det) < 1e-9f) return false;
            float inv = 1f / det; var s = ray.origin - a; float u = Vector3.Dot(s, p) * inv; if (u < 0 || u > 1) return false;
            var q = Vector3.Cross(s, e1); float w = Vector3.Dot(ray.direction, q) * inv; if (w < 0 || u + w > 1) return false;
            t = Vector3.Dot(e2, q) * inv; return t > 1e-4f;
        }

        // ------------------------------------------------------------------ defects: floating caster, orphaned decals
        /// Connected triangle islands (shared vertices, welded at 1 mm) of a mesh, in world space.
        sealed class Island { public List<long> tris = new List<long>(); public HashSet<int> subs = new HashSet<int>(); public Bounds b; public Vector3 n; }

        static List<Island> Islands(Mesh mesh, Matrix4x4 m, out Vector3[] world, out int[][] subTris)
        {
            var v = mesh.vertices; world = v.Select(x => m.MultiplyPoint3x4(x)).ToArray();
            var parent = Enumerable.Range(0, v.Length).ToArray();
            int Find(int a) { while (parent[a] != a) { parent[a] = parent[parent[a]]; a = parent[a]; } return a; }
            void Union(int a, int b) { a = Find(a); b = Find(b); if (a != b) parent[a] = b; }
            var weld = new Dictionary<(int, int, int), int>();
            for (int i = 0; i < v.Length; i++)
            {
                var k = (Mathf.RoundToInt(v[i].x * 1000), Mathf.RoundToInt(v[i].y * 1000), Mathf.RoundToInt(v[i].z * 1000));
                if (weld.TryGetValue(k, out int j)) Union(i, j); else weld[k] = i;
            }
            subTris = new int[mesh.subMeshCount][];
            for (int s = 0; s < mesh.subMeshCount; s++)
            {
                subTris[s] = mesh.GetTriangles(s);
                var tri = subTris[s];
                for (int k = 0; k + 2 < tri.Length; k += 3) { Union(tri[k], tri[k + 1]); Union(tri[k], tri[k + 2]); }
            }
            var map = new Dictionary<int, Island>();
            for (int s = 0; s < subTris.Length; s++)
            {
                var tri = subTris[s];
                for (int k = 0; k + 2 < tri.Length; k += 3)
                {
                    int r = Find(tri[k]);
                    if (!map.TryGetValue(r, out var isl)) { isl = new Island { b = new Bounds(world[tri[k]], Vector3.zero) }; map[r] = isl; }
                    isl.tris.Add((long)s * 1000000000L + k); isl.subs.Add(s);
                    isl.b.Encapsulate(world[tri[k]]); isl.b.Encapsulate(world[tri[k + 1]]); isl.b.Encapsulate(world[tri[k + 2]]);
                    isl.n += Vector3.Cross(world[tri[k + 1]] - world[tri[k]], world[tri[k + 2]] - world[tri[k]]);
                }
            }
            return map.Values.ToList();
        }

        /// Islands of every renderer under Ward district retrofit/Shop retrofits near the 13:00 caster point.
        public static string Remnant()
        {
            var scene = OpenScene();
            var p = new Vector3(-15.85f, 7.9f, 10.8f);
            var res = new List<object>();
            var root = scene.GetRootGameObjects().First(g => g.name == "Ward district retrofit").transform.Find("Shop retrofits");
            foreach (var rend in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mf = rend.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
                var isl = Islands(mf.sharedMesh, rend.localToWorldMatrix, out _, out _);
                var near = isl.Where(i => i.b.SqrDistance(p) < 16f).OrderBy(i => i.b.SqrDistance(p)).Take(40).Select(i => new
                {
                    tris = i.tris.Count, min = A(i.b.min), max = A(i.b.max), dist = R(Mathf.Sqrt(i.b.SqrDistance(p))),
                    mats = i.subs.Select(s => s < rend.sharedMaterials.Length && rend.sharedMaterials[s] ? rend.sharedMaterials[s].name : "?").ToArray(),
                    normal = A(i.n.normalized),
                }).ToArray();
                res.Add(new
                {
                    renderer = PathOf(rend.transform), active = rend.gameObject.activeInHierarchy && rend.enabled, mesh = AssetDatabase.GetAssetPath(mf.sharedMesh) + " | " + mf.sharedMesh.name,
                    islands = isl.Count, shadows = rend.shadowCastingMode.ToString(), colliders = rend.GetComponents<Collider>().Select(c => c.GetType().Name).ToArray(), near,
                });
            }
            Save("remnant.json", res);
            return res.Count + " renderers";
        }

        /// Active decal projectors that project sideways (wall decals) but have no wall inside their box while a
        /// horizontal surface (porch top or paving) crosses it: they smear onto the floor.
        public static string DecalAudit()
        {
            var scene = OpenScene();
            var renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(false)).Where(x => x.enabled).ToArray();
            var res = new List<object>();
            foreach (var d in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<DecalProjector>(false)).Where(x => x.enabled))
            {
                var f = d.transform.forward;
                if (Mathf.Abs(f.y) > .3f) continue;                       // floor/ceiling decals are fine
                var c = d.transform.TransformPoint(d.pivot);
                var half = d.size * .5f;
                // wall test: rays along the projection through the box centre and two side points
                bool wall = false;
                foreach (var off in new[] { 0f, -.35f, .35f })
                {
                    var o = c + d.transform.right * (off * half.x) - f * half.z;
                    var hits = RayHits(renderers.Where(r => r.bounds.SqrDistance(c) < 9f).ToArray(), new Ray(o, f), half.z * 2f + .01f, false);
                    if (hits.Count > 0) { wall = true; break; }
                }
                // floor test: a downward ray inside the box finds a surface between the box bottom and top
                var down = RayHits(renderers.Where(r => r.bounds.SqrDistance(c) < 9f).ToArray(), new Ray(c + Vector3.up * half.y, Vector3.down), half.y * 2f + .02f, false);
                bool floor = down.Count > 0;
                if (!wall && floor || !wall)
                    res.Add(new { path = PathOf(d.transform), pos = A(c), fwd = A(f), size = A(d.size), d.fadeFactor, mat = d.material ? d.material.name : null,
                                  wall, floor, floorHit = floor ? HitInfo(down[0]) : null });
            }
            Save("decal-audit.json", res);
            return res.Count + " suspicious wall decals";
        }

        /// Review defects found by survey/remnant/decalaudit: deactivate orphaned decals; strip floating remnant islands
        /// from a combined mesh into a new mesh asset (Art/NightFacade/Retrofit/*_nf.asset; the original stays).
        public static string FixDefects()
        {
            var scene = OpenScene();
            var tune = Tune(); var spec = (JObject)tune["defects"];
            var orig = JObject.Parse(File.ReadAllText(OriginalsPath));
            var rec = (JObject)orig["defects"] ?? new JObject();
            var log = new List<string>();
            Transform Find(string path)
            {
                var parts = path.Split('/');
                var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
                return root ? (parts.Length == 1 ? root.transform : root.transform.Find(string.Join("/", parts.Skip(1)))) : null;
            }
            var deact = (JObject)rec["deactivated"] ?? new JObject();
            foreach (var path in (spec["deactivate"] ?? new JArray()).Select(p => (string)p))
            {
                var tr = Find(path); if (!tr) { log.Add("missing " + path); continue; }
                if (deact[path] == null) deact[path] = tr.gameObject.activeSelf;
                tr.gameObject.SetActive(false); log.Add("deactivated " + path);
            }
            rec["deactivated"] = deact;
            var meshes = (JObject)rec["meshes"] ?? new JObject();
            foreach (var s in spec["strip"] ?? new JArray())
            {
                var path = (string)s["renderer"]; var tr = Find(path);
                var mf = tr ? tr.GetComponent<MeshFilter>() : null; if (!mf) { log.Add("missing " + path); continue; }
                if (meshes[path] == null) meshes[path] = AssetDatabase.GetAssetPath(mf.sharedMesh) + "|" + mf.sharedMesh.name;
                var srcRef = ((string)meshes[path]).Split('|');
                var src = AssetDatabase.LoadAllAssetsAtPath(srcRef[0]).OfType<Mesh>().First(m => m.name == srcRef[1]);
                var box = new Bounds(); box.SetMinMax(V3(s["boxMin"]), V3(s["boxMax"]));
                var isl = Islands(src, tr.localToWorldMatrix, out _, out var subTris);
                var drop = new HashSet<long>(isl.Where(i => box.Contains(i.b.min) && box.Contains(i.b.max)).SelectMany(i => i.tris));
                var copy = UnityEngine.Object.Instantiate(src); copy.name = src.name + "_nf";
                for (int sm = 0; sm < subTris.Length; sm++)
                {
                    var keep = new List<int>();
                    for (int k = 0; k + 2 < subTris[sm].Length; k += 3)
                        if (!drop.Contains((long)sm * 1000000000L + k)) { keep.Add(subTris[sm][k]); keep.Add(subTris[sm][k + 1]); keep.Add(subTris[sm][k + 2]); }
                    copy.SetTriangles(keep, sm, false);
                }
                copy.RecalculateBounds();
                Directory.CreateDirectory(ArtDir + "Retrofit");
                var dst = ArtDir + "Retrofit/" + copy.name + ".asset";
                if (AssetDatabase.LoadAssetAtPath<Mesh>(dst)) AssetDatabase.DeleteAsset(dst);
                AssetDatabase.CreateAsset(copy, dst);
                mf.sharedMesh = copy;
                if (PrefabUtility.IsPartOfPrefabInstance(mf)) PrefabUtility.RecordPrefabInstancePropertyModifications(mf);
                log.Add($"stripped {isl.Count(i => box.Contains(i.b.min) && box.Contains(i.b.max))} islands / {drop.Count} triangles from {path} -> {dst}");
            }
            rec["meshes"] = meshes;
            orig["defects"] = rec;
            File.WriteAllText(OriginalsPath, orig.ToString(Formatting.Indented));
            File.Copy(OriginalsPath, Evidence + "originals.json", true);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            Save("fix-defects.json", log);
            return string.Join("\n", log);
        }

        static string RollbackDefects(UnityEngine.SceneManagement.Scene scene, JObject orig)
        {
            var rec = (JObject)orig["defects"]; if (rec == null) return "no defect fixes recorded";
            var log = new List<string>();
            Transform Find(string path)
            {
                var parts = path.Split('/');
                var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
                return root ? (parts.Length == 1 ? root.transform : root.transform.Find(string.Join("/", parts.Skip(1)))) : null;
            }
            foreach (var d in ((JObject)rec["deactivated"] ?? new JObject()).Properties())
            { var tr = Find(d.Name); if (tr) { tr.gameObject.SetActive((bool)d.Value); log.Add("restored " + d.Name); } }
            foreach (var m in ((JObject)rec["meshes"] ?? new JObject()).Properties())
            {
                var tr = Find(m.Name); var mf = tr ? tr.GetComponent<MeshFilter>() : null; if (!mf) continue;
                var r = ((string)m.Value).Split('|');
                mf.sharedMesh = AssetDatabase.LoadAllAssetsAtPath(r[0]).OfType<Mesh>().First(x => x.name == r[1]);
                if (PrefabUtility.IsPartOfPrefabInstance(mf)) PrefabUtility.RecordPrefabInstancePropertyModifications(mf);
                log.Add("restored mesh " + m.Name);
            }
            return string.Join(", ", log);
        }

        /// Per-light contribution and shadow occluders at points of the Finery porch band (night).
        public static string LightProbe()
        {
            var scene = OpenScene();
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(false)).Where(x => x.enabled).ToArray();
            var lights = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Light>(false)).Where(l => l.enabled).ToArray();
            var pts = new[] { new Vector3(16.47f, .5f, -17.54f), new Vector3(16.28f, .5f, -18.51f), new Vector3(16.79f, .5f, -17.68f), new Vector3(16.15f, .5f, -17.40f), new Vector3(16.60f, .5f, -18.65f), new Vector3(15.96f, .5f, -18.37f), new Vector3(15.5f, .5f, -19.55f), new Vector3(15.9f, .5f, -16.9f) };
            var res = new List<object>();
            var f = clock.profile.Evaluate(20.5f);
            foreach (var p0 in pts)
            {
                var p = p0 + Vector3.up * .01f;
                var rows = new List<object>();
                foreach (var l in lights)
                {
                    float e; Vector3 toL; float dist = 0; string occ = null;
                    if (l.type == LightType.Directional)
                    {
                        if (l.name != "Sun" && !l.name.Contains("Sun") && l != clock.keyLight) continue;
                        toL = -(Quaternion.Euler(f.keyEuler) * Vector3.forward); e = f.keyIntensity * Mathf.Max(0, toL.y);
                        var h = RayHits(renderers, new Ray(p, toL), 200f, true); occ = h.Count > 0 ? PathOf(h[0].renderer.transform) + " @" + R(h[0].distance) : null;
                    }
                    else
                    {
                        var v = l.transform.position - p; dist = v.magnitude; if (dist > l.range) continue;
                        toL = v / dist;
                        float win = Mathf.Clamp01(1 - Mathf.Pow(dist / l.range, 4)); win *= win;
                        e = l.intensity / Mathf.Max(dist * dist, 1e-4f) * win * Mathf.Max(0, toL.y);
                        if (l.type == LightType.Spot)
                        {
                            float ang = Vector3.Angle(l.transform.forward, -toL);
                            e *= 1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(l.innerSpotAngle * .5f, l.spotAngle * .5f, ang));
                        }
                        if (l.shadows != LightShadows.None) { var h = RayHits(renderers, new Ray(p, toL), dist - .05f, true); occ = h.Count > 0 ? PathOf(h[0].renderer.transform) + " @" + R(h[0].distance) : null; }
                    }
                    if (e < .005f) continue;
                    rows.Add(new { light = PathOf(l.transform), type = l.type.ToString(), shadows = l.shadows.ToString(), e = R(e), dist = R(dist), color = A(l.color), occluder = occ });
                }
                res.Add(new { point = A(p0), lights = rows.OrderByDescending(x => (float)x.GetType().GetProperty("e").GetValue(x)).ToArray() });
            }
            Save("lightprobe-finery.json", res);
            return res.Count + " points";
        }

        /// Moon (night key light) shadow map of the Finery porch: 10 cm grid, first shadow caster per point.
        public static string MoonScan()
        {
            var scene = OpenScene();
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var f = clock.profile.Evaluate(20.5f);
            var toMoon = -(Quaternion.Euler(f.keyEuler) * Vector3.forward);
            var centre = new Vector3(16.2f, .5f, -18f);
            var renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<MeshRenderer>(false))
                .Where(x => x.enabled && x.shadowCastingMode != ShadowCastingMode.Off && x.bounds.SqrDistance(centre + toMoon * 4f) < 100f).ToArray();
            var names = new Dictionary<string, int>(); var rows = new List<string>();
            for (float z = -20f; z <= -16f; z += .1f)
            {
                var row = new System.Text.StringBuilder();
                for (float x = 15.0f; x <= 18.0f; x += .1f)
                {
                    var p = new Vector3(x, .505f, z);
                    var h = RayHits(renderers, new Ray(p, toMoon), 60f, true);
                    if (h.Count == 0) { row.Append('.'); continue; }
                    var n = PathOf(h[0].renderer.transform) + " [" + (h[0].sub >= 0 && h[0].sub < h[0].renderer.sharedMaterials.Length && h[0].renderer.sharedMaterials[h[0].sub] ? h[0].renderer.sharedMaterials[h[0].sub].name : "?") + "]";
                    if (!names.ContainsKey(n)) names[n] = names.Count;
                    row.Append((char)('A' + Math.Min(25, names[n])));
                }
                rows.Add(z.ToString("0.0", Inv).PadLeft(6) + " " + row);
            }
            Save("moonscan-finery.json", new { toMoon = A(toMoon), keyIntensity = f.keyIntensity, keyColor = A(f.keyColor), legend = names.ToDictionary(k => ((char)('A' + Math.Min(25, k.Value))).ToString() + k.Value, k => k.Key), xFrom = 15.0, xStep = .1, rows });
            return names.Count + " casters";
        }

        /// Debug renders (not saved) of one view with reflections, decals or the porch material's specular switched off,
        /// to find the source of the Finery porch band. 4 renders of a single close camera.
        public static string BandProbe(string outDir)
        {
            var scene = OpenScene();
            ShaderUtil.allowAsyncCompilation = false;
            const string cam = "cam_nf_finery_front";
            var log = new List<string>();
            DuskStartPass.Preview(20.5f, Path.Combine(outDir, "warmup"), cam);
            log.Add("base " + DuskStartPass.Preview(20.5f, Path.Combine(outDir, "base"), cam).Trim());
            var decals = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<DecalProjector>(false)).Where(d => d.enabled).ToList();
            foreach (var d in decals) d.enabled = false;
            log.Add("nodecals " + DuskStartPass.Preview(20.5f, Path.Combine(outDir, "nodecals"), cam).Trim());
            foreach (var d in decals) d.enabled = true;
            var probes = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<ReflectionProbe>(false)).Where(x => x.enabled).ToList();
            float ri = RenderSettings.reflectionIntensity;
            foreach (var pr in probes) pr.enabled = false; RenderSettings.reflectionIntensity = 0;
            log.Add("noreflections(" + probes.Count + ") " + DuskStartPass.Preview(20.5f, Path.Combine(outDir, "noreflections"), cam).Trim());
            foreach (var pr in probes) pr.enabled = true; RenderSettings.reflectionIntensity = ri;
            var slab = AssetDatabase.LoadAssetAtPath<Material>(HallMats + "VH_PodiumSlab.mat");
            float sp = slab.GetFloat("_SpecularHighlights"), er = slab.GetFloat("_EnvironmentReflections"), sm = slab.GetFloat("_Smoothness");
            slab.SetFloat("_SpecularHighlights", 0); slab.EnableKeyword("_SPECULARHIGHLIGHTS_OFF"); slab.SetFloat("_Smoothness", 0);
            log.Add("slabmatte " + DuskStartPass.Preview(20.5f, Path.Combine(outDir, "slabmatte"), cam).Trim());
            slab.SetFloat("_SpecularHighlights", sp); slab.DisableKeyword("_SPECULARHIGHLIGHTS_OFF"); slab.SetFloat("_Smoothness", sm);
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ shader check
        /// Compiles the window shader's forward pass for OpenGL Core (the shipping API) in a few keyword sets.
        public static string ShaderCheck()
        {
            AssetDatabase.ImportAsset(WindowShader, ImportAssetOptions.ForceUpdate);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(WindowShader);
            var log = new List<string>();
            var msgs = ShaderUtil.GetShaderMessages(shader);
            log.Add("import messages: " + msgs.Length + (msgs.Length > 0 ? " " + string.Join(" | ", msgs.Take(6).Select(m => m.severity + ": " + m.message + " @" + m.line)) : ""));
            log.Add("hasError: " + ShaderUtil.ShaderHasError(shader));
            var data = ShaderUtil.GetShaderData(shader);
            var sub = data.GetSubshader(0);
            bool ok = !ShaderUtil.ShaderHasError(shader);
            for (int p = 0; p < sub.PassCount; p++)
            {
                var pass = sub.GetPass(p);
                foreach (var kw in new[] { new string[0], new[] { "_ADDITIONAL_LIGHTS", "_MAIN_LIGHT_SHADOWS_CASCADE", "_CLUSTER_LIGHT_LOOP" } })
                    foreach (var stage in new[] { ShaderType.Vertex, ShaderType.Fragment })
                    {
                        var res = pass.CompileVariant(stage, kw, ShaderCompilerPlatform.OpenGLCore, BuildTarget.StandaloneLinux64);
                        ok &= res.Success;
                        log.Add($"{pass.Name} {stage} [{string.Join(" ", kw)}]: {(res.Success ? "ok" : "FAIL")} " +
                                string.Join(" | ", res.Messages.Where(m => m.severity == ShaderCompilerMessageSeverity.Error).Take(4).Select(m => m.message + " @" + m.line)));
                    }
            }
            Save("shader-check.json", new { ok, log });
            if (!ok) throw new Exception("Window shader failed to compile:\n" + string.Join("\n", log));
            return string.Join("\n", log);
        }

        // ------------------------------------------------------------------ build (assets only)
        public static string BuildAssets()
        {
            Directory.CreateDirectory(MatDir); Directory.CreateDirectory(TexDir);
            var log = new List<string>();
            log.Add(MakeCookie());
            var lens = AssetDatabase.LoadAssetAtPath<Material>(HallMats + "VH_LampLens.mat");
            if (!AssetDatabase.LoadAssetAtPath<Material>(BulbPath))
            {
                var m = new Material(lens) { name = "NF_WallLampBulb" };
                AssetDatabase.CreateAsset(m, BulbPath); log.Add("created " + BulbPath);
            }
            if (!AssetDatabase.LoadAssetAtPath<Material>(BulkheadLensPath))
            {
                var m = new Material(lens) { name = "NF_BulkheadLens" };
                AssetDatabase.CreateAsset(m, BulkheadLensPath); log.Add("created " + BulkheadLensPath);
            }
            if (!AssetDatabase.LoadAssetAtPath<Material>(LampGlassPath))
            {
                var m = new Material(AssetDatabase.LoadAssetAtPath<Material>(PhGlassPath)) { name = "NF_WallLampGlass" };
                m.EnableKeyword("_EMISSION"); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                AssetDatabase.CreateAsset(m, LampGlassPath); log.Add("created " + LampGlassPath);
            }
            var tune = Tune();
            foreach (var g in ((JObject)tune["glass"]).Properties())
            {
                var from = (string)g.Value["from"];
                if (from == null) continue;
                var path = MatDir + g.Name + ".mat";
                if (AssetDatabase.LoadAssetAtPath<Material>(path)) continue;
                var src = AssetDatabase.LoadAssetAtPath<Material>(ShopMats + from + ".mat");
                if (!src) throw new Exception("missing " + from);
                var m = new Material(src) { name = g.Name };
                AssetDatabase.CreateAsset(m, path); log.Add("created " + path);
            }
            AssetDatabase.SaveAssets();
            return string.Join("\n", log);
        }

        /// Soft spot cookie: wide plateau, smooth falloff to the cone edge, faint radial shadows of the lamp cage's six
        /// bars and its ring, the wall-side half a little dimmer (back plate); +y of the cookie faces the street.
        static string MakeCookie()
        {
            const int N = 256;
            var tex = new Texture2D(N, N, TextureFormat.RGBA32, false, true);
            var px = new Color[N * N];
            var rnd = new System.Random(1001);
            var noise = new float[34 * 34]; for (int i = 0; i < noise.Length; i++) noise[i] = (float)rnd.NextDouble();
            float Noise(float x, float y)
            {
                x *= 32; y *= 32; int ix = Mathf.Clamp((int)x, 0, 32), iy = Mathf.Clamp((int)y, 0, 32); float fx = x - ix, fy = y - iy;
                float a = noise[iy * 34 + ix], b = noise[iy * 34 + ix + 1], c = noise[(iy + 1) * 34 + ix], d = noise[(iy + 1) * 34 + ix + 1];
                return Mathf.Lerp(Mathf.Lerp(a, b, fx), Mathf.Lerp(c, d, fx), fy);
            }
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float u = (x + .5f) / N * 2 - 1, v = (y + .5f) / N * 2 - 1;
                    float r = Mathf.Sqrt(u * u + v * v);
                    float val = 1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(.72f, .99f, r));
                    float ang = Mathf.Atan2(v, u);
                    float bars = Mathf.Pow(Mathf.Abs(Mathf.Cos(ang * 3f)), 40f);                 // six cage bars
                    val *= 1f - .12f * bars * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(.12f, .35f, r));
                    val *= 1f - .08f * Mathf.Exp(-Mathf.Pow((r - .42f) / .035f, 2f));          // cage ring
                    val *= Mathf.Lerp(.94f, 1f, Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(-.6f, .2f, v)));  // wall side (v<0)
                    val *= .96f + .08f * Noise((u + 1) * .5f, (v + 1) * .5f);                       // glass irregularity
                    val = Mathf.Clamp01(val);
                    px[y * N + x] = new Color(val, val, val, val);
                }
            tex.SetPixels(px); tex.Apply();
            File.WriteAllBytes(CookiePath, tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(CookiePath, ImportAssetOptions.ForceUpdate);
            var imp = (TextureImporter)AssetImporter.GetAtPath(CookiePath);
            imp.textureType = TextureImporterType.Default; imp.sRGBTexture = false; imp.alphaSource = TextureImporterAlphaSource.FromInput;
            imp.wrapMode = TextureWrapMode.Clamp; imp.mipmapEnabled = true; imp.filterMode = FilterMode.Bilinear;
            imp.textureCompression = TextureImporterCompression.Uncompressed; imp.maxTextureSize = 256; imp.streamingMipmaps = false;
            imp.SaveAndReimport();
            return "cookie " + CookiePath;
        }

        // ------------------------------------------------------------------ originals (recorded once)
        static JObject RecordOriginals(JObject tune)
        {
            var o = new JObject();
            var lights = new JObject(); var bulbs = new JObject(); var slots = new JObject();
            foreach (var path in tune["lamps"]["prefabs"].Select(p => (string)p))
            {
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var pl = new JObject(); var pb = new JObject();
                    foreach (var (head, bulb, lt, l) in Lamps(root))
                    {
                        pl[lt.name] = new JObject
                        {
                            ["localPosition"] = new JArray(A(lt.localPosition)), ["localRotation"] = new JArray(new[] { lt.localRotation.x, lt.localRotation.y, lt.localRotation.z, lt.localRotation.w }),
                            ["type"] = l.type.ToString(), ["intensity"] = l.intensity, ["range"] = l.range, ["spotAngle"] = l.spotAngle, ["innerSpotAngle"] = l.innerSpotAngle,
                            ["color"] = new JArray(A(l.color)), ["cookie"] = l.cookie ? AssetDatabase.GetAssetPath(l.cookie) : null, ["shadows"] = l.shadows.ToString(),
                        };
                        var br = bulb.GetComponent<Renderer>();
                        pb[Rel(bulb, root.transform)] = AssetDatabase.GetAssetPath(br.sharedMaterial);
                    }
                    lights[path] = pl; bulbs[path] = pb;
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            foreach (var g in ((JObject)tune["glass"]).Properties())
                foreach (var path in (g.Value["prefabs"] ?? new JArray()).Select(p => (string)p))
                {
                    var root = PrefabUtility.LoadPrefabContents(path);
                    try
                    {
                        var ps = new JObject();
                        foreach (var rend in root.GetComponentsInChildren<Renderer>(true))
                        {
                            var mats = rend.sharedMaterials;
                            for (int i = 0; i < mats.Length; i++)
                                if (mats[i] && mats[i].shader && mats[i].shader.name == "Athen Hill/Ward Window Interior")
                                    ps[Rel(rend.transform, root.transform) + "#" + i] = AssetDatabase.GetAssetPath(mats[i]);
                        }
                        slots[path] = ps;
                    }
                    finally { PrefabUtility.UnloadPrefabContents(root); }
                }
            var props = new JObject();
            foreach (var (matPath, spec) in MaterialSpecs(tune))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(matPath); if (!m) continue;
                var mp = new JObject();
                foreach (var p in spec.Properties()) if (p.Name != "from" && p.Name != "prefabs" && m.HasProperty(p.Name)) mp[p.Name] = ReadProp(m, p.Name);
                props[matPath] = mp;
            }
            o["recorded"] = DateTime.Now.ToString("s", Inv);
            o["lights"] = lights; o["bulbs"] = bulbs; o["glassSlots"] = slots; o["materials"] = props;
            return o;
        }

        static IEnumerable<(string path, JObject spec)> MaterialSpecs(JObject tune)
        {
            foreach (var g in ((JObject)tune["glass"]).Properties())
            {
                var from = (string)g.Value["from"];
                var path = from != null ? MatDir + g.Name + ".mat" : FindMaterial(g.Name);
                yield return (path, (JObject)g.Value);
            }
            foreach (var g in ((JObject)tune["masonry"]).Properties()) yield return (FindMaterial(g.Name), (JObject)g.Value);
            yield return (BulbPath, (JObject)tune["bulb"]);
            if (tune["lampGlass"] is JObject lg) yield return (LampGlassPath, lg);
            if (tune["bulkheads"]?["lensMaterial"] is JObject bl) yield return (BulkheadLensPath, bl);
        }

        static string FindMaterial(string name)
        {
            foreach (var dir in new[] { HallMats, ShopMats, "Assets/AthenHill/Art/Quality/RelayArchitecture/Revision02/Materials/" })
                if (File.Exists(dir + name + ".mat")) return dir + name + ".mat";
            throw new Exception("material not found: " + name);
        }

        static JToken ReadProp(Material m, string name)
        {
            int idx = m.shader.FindPropertyIndex(name);
            var type = m.shader.GetPropertyType(idx);
            switch (type)
            {
                case ShaderPropertyType.Color: return new JArray(A(m.GetColor(name)));
                case ShaderPropertyType.Vector: { var v = m.GetVector(name); return new JArray(v.x, v.y, v.z, v.w); }
                case ShaderPropertyType.Float: case ShaderPropertyType.Range: return m.GetFloat(name);
                default: return null;
            }
        }

        static void WriteProp(Material m, string name, JToken value)
        {
            int idx = m.shader.FindPropertyIndex(name);
            if (idx < 0) throw new Exception($"{m.name}: no property {name}");
            switch (m.shader.GetPropertyType(idx))
            {
                case ShaderPropertyType.Color: m.SetColor(name, new Color((float)value[0], (float)value[1], (float)value[2], value.Count() > 3 ? (float)value[3] : 1f)); break;
                case ShaderPropertyType.Vector: m.SetVector(name, new Vector4((float)value[0], (float)value[1], (float)value[2], value.Count() > 3 ? (float)value[3] : 0f)); break;
                default: m.SetFloat(name, (float)value); break;
            }
        }

        /// PH_WallLamp heads (with the added "Bulb") and their "&lt;head&gt; light" in Practical lights.
        static IEnumerable<(Transform head, Transform bulb, Transform lightT, Light light)> Lamps(GameObject root)
        {
            var fit = root.transform.Find("Fittings"); var lights = root.transform.Find("Practical lights");
            if (!fit || !lights) yield break;
            foreach (Transform head in fit)
            {
                var bulb = head.Find("Bulb"); if (!bulb) continue;
                var lt = lights.Find(head.name + " light"); var l = lt ? lt.GetComponent<Light>() : null;
                if (!l) { Debug.LogWarning("NightFacade: no light for " + head.name + " in " + root.name); continue; }
                yield return (head, bulb, lt, l);
            }
        }

        // ------------------------------------------------------------------ install (one time) / apply (idempotent)
        public static string Install()
        {
            if (File.Exists(OriginalsPath)) throw new Exception("Already installed (originals.json exists); use apply / rollback.");
            var scene = OpenScene();
            Directory.CreateDirectory(Evidence + "rollback");
            File.Copy(ScenePath, Evidence + "rollback/before-night-facade.unity", true);
            var tune = Tune();
            var orig = RecordOriginals(tune);
            // circuit emissive list as found
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            orig["circuitEmissive"] = new JArray(circuit.emissiveMaterials.Select(m => m ? AssetDatabase.GetAssetPath(m) : null));
            File.WriteAllText(OriginalsPath, orig.ToString(Formatting.Indented));
            File.Copy(OriginalsPath, Evidence + "originals.json", true);
            return "originals recorded; " + Apply();
        }

        public static string Apply()
        {
            if (!File.Exists(OriginalsPath)) throw new Exception("Run install first (no originals.json).");
            var tune = Tune(); var orig = JObject.Parse(File.ReadAllText(OriginalsPath));
            var log = new List<string>();
            var cookie = AssetDatabase.LoadAssetAtPath<Texture2D>(CookiePath);
            var bulbMat = AssetDatabase.LoadAssetAtPath<Material>(BulbPath);
            var lampSpec = (JObject)tune["lamps"];
            float outM = (float)lampSpec["out"], downM = (float)lampSpec["down"], tilt = (float)lampSpec["tilt"];
            float outer = (float)lampSpec["outer"], inner = (float)lampSpec["inner"];
            float iScale = (float)lampSpec["intensityScale"], rScale = (float)lampSpec["rangeScale"];
            bool useCookie = (bool)lampSpec["cookie"];

            // properties added to the tune file after install: record their (untouched) values before the first write
            bool newOrig = false;
            foreach (var (path, spec) in MaterialSpecs(tune))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(path); if (!m) continue;
                var om = (JObject)orig["materials"][path];
                if (om == null) { om = new JObject(); orig["materials"][path] = om; }
                foreach (var p in spec.Properties())
                    if (p.Name != "from" && p.Name != "prefabs" && om[p.Name] == null && m.HasProperty(p.Name)) { om[p.Name] = ReadProp(m, p.Name); newOrig = true; }
            }
            if (newOrig) { File.WriteAllText(OriginalsPath, orig.ToString(Formatting.Indented)); File.Copy(OriginalsPath, Evidence + "originals.json", true); }

            // materials first (values from the tune file)
            foreach (var (path, spec) in MaterialSpecs(tune))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) throw new Exception("missing material " + path);
                foreach (var p in spec.Properties())
                {
                    if (p.Name == "from" || p.Name == "prefabs") continue;
                    WriteProp(m, p.Name, p.Value);
                }
                if (m.HasProperty("_EmissionColor") && m.GetColor("_EmissionColor").maxColorComponent > 0 && m.shader.name != "Athen Hill/Ward Window Interior") m.EnableKeyword("_EMISSION");
                EditorUtility.SetDirty(m);
                log.Add("material " + Path.GetFileNameWithoutExtension(path) + ": " + string.Join(", ", spec.Properties().Where(p => p.Name != "from" && p.Name != "prefabs").Select(p => p.Name)));
            }
            AssetDatabase.SaveAssets();

            // lamp glass originals (added after the first install; recorded once from the untouched prefabs)
            var phGlass = AssetDatabase.LoadAssetAtPath<Material>(PhGlassPath);
            var lampGlass = AssetDatabase.LoadAssetAtPath<Material>(LampGlassPath);
            if (orig["lampGlass"] == null)
            {
                var lgRec = new JObject();
                foreach (var path in lampSpec["prefabs"].Select(p => (string)p))
                {
                    var root = PrefabUtility.LoadPrefabContents(path);
                    try
                    {
                        var pg = new JObject();
                        foreach (var (head, bulb, lt, l) in Lamps(root).ToList())
                            foreach (var rend in head.GetComponentsInChildren<Renderer>(true))
                            {
                                var mats = rend.sharedMaterials;
                                for (int i = 0; i < mats.Length; i++) if (mats[i] == phGlass) pg[Rel(rend.transform, root.transform) + "#" + i] = PhGlassPath;
                            }
                        lgRec[path] = pg;
                    }
                    finally { PrefabUtility.UnloadPrefabContents(root); }
                }
                orig["lampGlass"] = lgRec;
                File.WriteAllText(OriginalsPath, orig.ToString(Formatting.Indented));
                File.Copy(OriginalsPath, Evidence + "originals.json", true);
            }
            bool glowGlass = tune["lampGlass"] != null && lampGlass;

            // lamps (prefab assets)
            int lampCount = 0, glassSlots = 0;
            foreach (var path in lampSpec["prefabs"].Select(p => (string)p))
            {
                var ol = (JObject)orig["lights"][path];
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    foreach (var (head, bulb, lt, l) in Lamps(root).ToList())
                    {
                        var o = ol[lt.name]; if (o == null) { log.Add("no original for " + lt.name); continue; }
                        var parent = lt.parent;
                        var n = head.forward; n.y = 0; n.Normalize();
                        var origWorld = parent.TransformPoint(V3(o["localPosition"]));
                        lt.position = origWorld + n * outM + Vector3.down * downM;
                        var dir = (Vector3.down * Mathf.Cos(tilt * Mathf.Deg2Rad) + n * Mathf.Sin(tilt * Mathf.Deg2Rad)).normalized;
                        lt.rotation = Quaternion.LookRotation(dir, n);
                        l.type = LightType.Spot; l.spotAngle = outer; l.innerSpotAngle = inner;
                        l.intensity = (float)o["intensity"] * iScale; l.range = (float)o["range"] * rScale;
                        l.cookie = useCookie ? cookie : null;
                        l.shadows = LightShadows.None;
                        bulb.GetComponent<Renderer>().sharedMaterial = bulbMat;
                        lampCount++;
                    }
                    foreach (var slot in ((JObject)orig["lampGlass"][path] ?? new JObject()).Properties())
                    {
                        var parts = slot.Name.Split('#'); var tr = root.transform.Find(parts[0]); int i = int.Parse(parts[1], Inv);
                        var rend = tr ? tr.GetComponent<Renderer>() : null; if (!rend) continue;
                        var mats = rend.sharedMaterials; mats[i] = glowGlass ? lampGlass : phGlass; rend.sharedMaterials = mats; glassSlots++;
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            log.Add("lamps " + lampCount + ", lamp glass slots " + glassSlots + (glowGlass ? " (NF_WallLampGlass)" : " (original glass)"));

            // West Gate arch bulkheads (added 1 Oct after the batch-2 lookbook): lens slots and the spot, from recorded originals
            if (tune["bulkheads"] is JObject bh)
            {
                var vhLens = AssetDatabase.LoadAssetAtPath<Material>(HallMats + "VH_LampLens.mat");
                var bhLens = AssetDatabase.LoadAssetAtPath<Material>(BulkheadLensPath);
                if (orig["bulkheads"] == null)
                {
                    var rec = new JObject();
                    foreach (var path in bh["prefabs"].Select(p => (string)p))
                    {
                        var root = PrefabUtility.LoadPrefabContents(path);
                        try
                        {
                            var r = new JObject(); var lens = new JObject();
                            var lt = root.GetComponentsInChildren<Light>(true).First(x => x.name == (string)bh["light"]);
                            r["light"] = new JObject
                            {
                                ["path"] = Rel(lt.transform, root.transform), ["localPosition"] = new JArray(A(lt.transform.localPosition)),
                                ["localRotation"] = new JArray(new[] { lt.transform.localRotation.x, lt.transform.localRotation.y, lt.transform.localRotation.z, lt.transform.localRotation.w }),
                                ["type"] = lt.type.ToString(), ["intensity"] = lt.intensity, ["range"] = lt.range, ["spotAngle"] = lt.spotAngle, ["innerSpotAngle"] = lt.innerSpotAngle,
                                ["cookie"] = lt.cookie ? AssetDatabase.GetAssetPath(lt.cookie) : null,
                            };
                            foreach (var rend in root.GetComponentsInChildren<Renderer>(true))
                            {
                                var mats = rend.sharedMaterials;
                                for (int i = 0; i < mats.Length; i++) if (mats[i] == vhLens) lens[Rel(rend.transform, root.transform) + "#" + i] = HallMats + "VH_LampLens.mat";
                            }
                            r["lens"] = lens; rec[path] = r;
                        }
                        finally { PrefabUtility.UnloadPrefabContents(root); }
                    }
                    orig["bulkheads"] = rec;
                    File.WriteAllText(OriginalsPath, orig.ToString(Formatting.Indented));
                    File.Copy(OriginalsPath, Evidence + "originals.json", true);
                }
                foreach (var pp in ((JObject)orig["bulkheads"]).Properties())
                {
                    var root = PrefabUtility.LoadPrefabContents(pp.Name);
                    try
                    {
                        var o = pp.Value["light"];
                        var lt = root.transform.Find((string)o["path"]); var l = lt.GetComponent<Light>();
                        var q = o["localRotation"]; var origRot = lt.parent.rotation * new Quaternion((float)q[0], (float)q[1], (float)q[2], (float)q[3]);
                        var f = origRot * Vector3.forward; var outDir = new Vector3(f.x, 0, f.z).normalized;   // away from the leaves
                        float bhTilt = (float)bh["tilt"];
                        lt.position = lt.parent.TransformPoint(V3(o["localPosition"])) + outDir * (float)bh["out"] + Vector3.down * (float)bh["down"];
                        var dir = (Vector3.down * Mathf.Cos(bhTilt * Mathf.Deg2Rad) + outDir * Mathf.Sin(bhTilt * Mathf.Deg2Rad)).normalized;
                        lt.rotation = Quaternion.LookRotation(dir, outDir);
                        l.type = LightType.Spot; l.spotAngle = (float)bh["outer"]; l.innerSpotAngle = (float)bh["inner"];
                        l.intensity = (float)o["intensity"] * (float)bh["intensityScale"]; l.range = (float)o["range"] * (float)bh["rangeScale"];
                        int n = 0;
                        foreach (var slot in ((JObject)pp.Value["lens"]).Properties())
                        {
                            var parts = slot.Name.Split('#'); var tr = root.transform.Find(parts[0]); int i = int.Parse(parts[1], Inv);
                            var rend = tr ? tr.GetComponent<Renderer>() : null; if (!rend) continue;
                            var mats = rend.sharedMaterials; mats[i] = bhLens; rend.sharedMaterials = mats; n++;
                        }
                        PrefabUtility.SaveAsPrefabAsset(root, pp.Name);
                        log.Add($"bulkhead {Path.GetFileNameWithoutExtension(pp.Name)}: spot {l.spotAngle}/{l.innerSpotAngle}, {l.intensity} / {l.range} m, lens slots {n}");
                    }
                    finally { PrefabUtility.UnloadPrefabContents(root); }
                }
            }

            // glass slots per street
            foreach (var g in ((JObject)tune["glass"]).Properties())
            {
                var prefabs = g.Value["prefabs"]; if (prefabs == null) continue;
                var mat = AssetDatabase.LoadAssetAtPath<Material>((string)g.Value["from"] != null ? MatDir + g.Name + ".mat" : FindMaterial(g.Name));
                foreach (var path in prefabs.Select(p => (string)p))
                {
                    var os = (JObject)orig["glassSlots"][path];
                    var root = PrefabUtility.LoadPrefabContents(path);
                    int n = 0;
                    try
                    {
                        foreach (var slot in os.Properties())
                        {
                            var parts = slot.Name.Split('#'); var t = root.transform.Find(parts[0]); int i = int.Parse(parts[1], Inv);
                            var rend = t ? t.GetComponent<Renderer>() : null; if (!rend) { log.Add("missing glass renderer " + slot.Name); continue; }
                            var mats = rend.sharedMaterials; mats[i] = mat; rend.sharedMaterials = mats; n++;
                        }
                        PrefabUtility.SaveAsPrefabAsset(root, path);
                    }
                    finally { PrefabUtility.UnloadPrefabContents(root); }
                    log.Add($"glass {g.Name} -> {Path.GetFileNameWithoutExtension(path)}: {n} slots");
                }
            }

            // scene: circuit emissive list, revert stray instance overrides on the tuned lights/bulbs, review cameras
            var scene = OpenScene();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var add = new List<Material> { bulbMat };
            if (glowGlass) add.Add(lampGlass);
            if (tune["bulkheads"] != null) add.Add(AssetDatabase.LoadAssetAtPath<Material>(BulkheadLensPath));
            foreach (var g in ((JObject)tune["glass"]).Properties())
                if ((string)g.Value["from"] != null) add.Add(AssetDatabase.LoadAssetAtPath<Material>(MatDir + g.Name + ".mat"));
            circuit.emissiveMaterials = circuit.emissiveMaterials.Where(m => m).Concat(add).Distinct().ToArray();
            EditorUtility.SetDirty(circuit);
            int reverted = 0;
            foreach (var g in scene.GetRootGameObjects())
                foreach (var inst in g.GetComponentsInChildren<Transform>(true).Select(t => t.gameObject).Where(PrefabUtility.IsOutermostPrefabInstanceRoot).ToList())
                {
                    var asset = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst);
                    if (!lampSpec["prefabs"].Any(p => (string)p == asset)) continue;
                    foreach (var (head, bulb, lt, l) in Lamps(inst).ToList())
                    {
                        foreach (UnityEngine.Object obj in new UnityEngine.Object[] { l, lt, bulb.GetComponent<Renderer>() })
                            if (PrefabUtility.GetPropertyModifications(inst).Any(m => m.target == PrefabUtility.GetCorrespondingObjectFromSource(obj)))
                            { PrefabUtility.RevertObjectOverride(obj, InteractionMode.AutomatedAction); reverted++; }
                    }
                }
            log.Add("reverted instance overrides " + reverted);
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            var result = string.Join("\n", log);
            Save("apply.json", new { time = DateTime.Now.ToString("s", Inv), tune = JObject.Parse(File.ReadAllText(Source + "facade-tune.json")), log });
            return result;
        }

        // ------------------------------------------------------------------ rollback
        public static string Rollback()
        {
            var orig = JObject.Parse(File.ReadAllText(OriginalsPath));
            var log = new List<string>();
            foreach (var mp in ((JObject)orig["materials"]).Properties())
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(mp.Name); if (!m) continue;
                foreach (var p in ((JObject)mp.Value).Properties()) WriteProp(m, p.Name, p.Value);
                EditorUtility.SetDirty(m); log.Add("material " + m.name);
            }
            foreach (var pp in ((JObject)orig["lights"]).Properties())
            {
                var root = PrefabUtility.LoadPrefabContents(pp.Name);
                try
                {
                    foreach (var (head, bulb, lt, l) in Lamps(root).ToList())
                    {
                        var o = pp.Value[lt.name]; if (o == null) continue;
                        lt.localPosition = V3(o["localPosition"]); var q = o["localRotation"]; lt.localRotation = new Quaternion((float)q[0], (float)q[1], (float)q[2], (float)q[3]);
                        l.type = (LightType)Enum.Parse(typeof(LightType), (string)o["type"]); l.intensity = (float)o["intensity"]; l.range = (float)o["range"];
                        l.spotAngle = (float)o["spotAngle"]; l.innerSpotAngle = (float)o["innerSpotAngle"];
                        l.cookie = (string)o["cookie"] != null ? AssetDatabase.LoadAssetAtPath<Texture>((string)o["cookie"]) : null;
                        var bp = (string)orig["bulbs"][pp.Name][Rel(bulb, root.transform)];
                        if (bp != null) bulb.GetComponent<Renderer>().sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(bp);
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, pp.Name);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
                log.Add("lamps " + pp.Name);
            }
            foreach (var pp in ((JObject)orig["bulkheads"] ?? new JObject()).Properties())
            {
                var root = PrefabUtility.LoadPrefabContents(pp.Name);
                try
                {
                    var o = pp.Value["light"]; var lt = root.transform.Find((string)o["path"]); var l = lt.GetComponent<Light>();
                    lt.localPosition = V3(o["localPosition"]); var q = o["localRotation"]; lt.localRotation = new Quaternion((float)q[0], (float)q[1], (float)q[2], (float)q[3]);
                    l.type = (LightType)Enum.Parse(typeof(LightType), (string)o["type"]); l.intensity = (float)o["intensity"]; l.range = (float)o["range"];
                    l.spotAngle = (float)o["spotAngle"]; l.innerSpotAngle = (float)o["innerSpotAngle"];
                    foreach (var slot in ((JObject)pp.Value["lens"]).Properties())
                    {
                        var parts = slot.Name.Split('#'); var tr = root.transform.Find(parts[0]); int i = int.Parse(parts[1], Inv);
                        var rend = tr ? tr.GetComponent<Renderer>() : null; if (!rend) continue;
                        var mats = rend.sharedMaterials; mats[i] = AssetDatabase.LoadAssetAtPath<Material>((string)slot.Value); rend.sharedMaterials = mats;
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, pp.Name);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
                log.Add("bulkhead " + pp.Name);
            }
            foreach (var pp in ((JObject)orig["lampGlass"] ?? new JObject()).Properties())
            {
                var root = PrefabUtility.LoadPrefabContents(pp.Name);
                try
                {
                    foreach (var slot in ((JObject)pp.Value).Properties())
                    {
                        var parts = slot.Name.Split('#'); var tr = root.transform.Find(parts[0]); int i = int.Parse(parts[1], Inv);
                        var rend = tr ? tr.GetComponent<Renderer>() : null; if (!rend) continue;
                        var mats = rend.sharedMaterials; mats[i] = AssetDatabase.LoadAssetAtPath<Material>((string)slot.Value); rend.sharedMaterials = mats;
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, pp.Name);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
                log.Add("lamp glass " + pp.Name);
            }
            foreach (var pp in ((JObject)orig["glassSlots"]).Properties())
            {
                var root = PrefabUtility.LoadPrefabContents(pp.Name);
                try
                {
                    foreach (var slot in ((JObject)pp.Value).Properties())
                    {
                        var parts = slot.Name.Split('#'); var t = root.transform.Find(parts[0]); int i = int.Parse(parts[1], Inv);
                        var rend = t ? t.GetComponent<Renderer>() : null; if (!rend) continue;
                        var mats = rend.sharedMaterials; mats[i] = AssetDatabase.LoadAssetAtPath<Material>((string)slot.Value); rend.sharedMaterials = mats;
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, pp.Name);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
                log.Add("glass " + pp.Name);
            }
            var scene = OpenScene();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var ours = new HashSet<string>(new[] { BulbPath, LampGlassPath, BulkheadLensPath }.Concat(((JObject)Tune()["glass"]).Properties().Where(g => (string)g.Value["from"] != null).Select(g => MatDir + g.Name + ".mat")));
            circuit.emissiveMaterials = circuit.emissiveMaterials.Where(m => m && !ours.Contains(AssetDatabase.GetAssetPath(m))).ToArray();
            EditorUtility.SetDirty(circuit);
            log.Add(RollbackDefects(scene, orig));
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            return string.Join("\n", log);
        }

        // ------------------------------------------------------------------ review cameras (player height)
        static readonly (string name, Vector3 pos, Vector3 target, float fov)[] ReviewViews =
        {
            ("cam_nf_air_water_lamps", new Vector3(-13.6f, 1.65f, -12.4f), new Vector3(-18.1f, 2.5f, -9.6f), 60),
            ("cam_nf_relay_works", new Vector3(-13.4f, 1.65f, -15.6f), new Vector3(-18.1f, 2.4f, -19.2f), 60),
            ("cam_nf_tool_exchange", new Vector3(-13.6f, 1.65f, 4.4f), new Vector3(-18.1f, 2.4f, 7.6f), 60),
            ("cam_nf_finery_front", new Vector3(13.2f, 1.65f, -20.4f), new Vector3(18.1f, 1.7f, -17.4f), 60),
            ("cam_nf_field_supply", new Vector3(13.4f, 1.65f, -4.0f), new Vector3(18.1f, 2.3f, -7.0f), 60),
            ("cam_nf_repairs_thread", new Vector3(13.4f, 1.65f, 13.4f), new Vector3(18.1f, 2.4f, 16.8f), 60),
            ("cam_nf_salvage", new Vector3(-13.4f, 1.65f, 13.0f), new Vector3(-18.1f, 2.4f, 16.6f), 60),
            ("cam_nf_hall_portal", new Vector3(-8.2f, 1.65f, -21.4f), new Vector3(-10.0f, 2.8f, -26.4f), 60),
        };

        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            foreach (var (name, pos, target, fov) in ReviewViews)
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var c = go.AddComponent<Camera>(); c.enabled = false; c.fieldOfView = fov; c.nearClipPlane = .05f;
            }
        }

        public static string Cameras()
        {
            var scene = OpenScene();
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return ReviewViews.Length + " cameras";
        }

        // ------------------------------------------------------------------ verify (saved scene, -nographics)
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var tune = Tune();
            var r = new Dictionary<string, object>();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var practical = new HashSet<Light>(circuit.practicalLights.Where(l => l));
            var nightOnly = new HashSet<Light>(circuit.nightOnlyLights.Where(l => l));
            var bulbMat = AssetDatabase.LoadAssetAtPath<Material>(BulbPath);
            var cookie = AssetDatabase.LoadAssetAtPath<Texture2D>(CookiePath);
            var lamps = new List<object>(); int bad = 0;
            foreach (var g in scene.GetRootGameObjects())
                foreach (var inst in g.GetComponentsInChildren<Transform>(true).Select(t => t.gameObject).Where(PrefabUtility.IsOutermostPrefabInstanceRoot))
                {
                    var asset = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst);
                    if (!tune["lamps"]["prefabs"].Any(p => (string)p == asset)) continue;
                    foreach (var (head, bulb, lt, l) in Lamps(inst))
                    {
                        bool ok = l.type == LightType.Spot && (l.cookie == cookie || !(bool)tune["lamps"]["cookie"]) && bulb.GetComponent<Renderer>().sharedMaterial == bulbMat
                                  && practical.Contains(l) && nightOnly.Contains(l) && Vector3.Dot(lt.forward, Vector3.down) > .8f;
                        if (!ok) bad++;
                        var wall = Vector3.Dot(lt.position - head.position, head.forward);
                        var glassMats = head.GetComponentsInChildren<Renderer>(true).Where(x => x.transform != bulb).SelectMany(x => x.sharedMaterials).Where(m => m && (m.name.Contains("lamp_glass") || m.name == "NF_WallLampGlass")).Select(m => m.name).Distinct().ToArray();
                        lamps.Add(new { light = PathOf(lt), ok, glass = glassMats, type = l.type.ToString(), l.intensity, l.range, l.spotAngle, l.innerSpotAngle, cookie = l.cookie ? l.cookie.name : null,
                                        bulb = bulb.GetComponent<Renderer>().sharedMaterial.name, outFromHead = R(wall), belowBulb = R(bulb.position.y - lt.position.y),
                                        practical = practical.Contains(l), nightOnly = nightOnly.Contains(l) });
                    }
                }
            r["lamps"] = lamps; r["lampProblems"] = bad;
            r["bulkheads"] = scene.GetRootGameObjects().Where(g => g.name == "Ward west gate arches").SelectMany(g => g.GetComponentsInChildren<Light>(true))
                .Select(l => new { light = PathOf(l.transform), type = l.type.ToString(), l.intensity, l.range, l.spotAngle, l.innerSpotAngle, pos = A(l.transform.position), fwd = A(l.transform.forward),
                                   practical = practical.Contains(l), nightOnly = nightOnly.Contains(l),
                                   lens = l.transform.parent.GetComponentsInChildren<Renderer>(true).SelectMany(x => x.sharedMaterials).Where(m => m && (m.name == "NF_BulkheadLens" || m.name == "VH_LampLens")).Select(m => m.name).Distinct().ToArray() }).ToArray();
            r["circuitEmissive"] = circuit.emissiveMaterials.Select(m => m ? m.name : "null").ToArray();
            r["missingMaterialsOnTunedPrefabs"] = tune["lamps"]["prefabs"].Select(p => (string)p).Sum(p => AssetDatabase.LoadAssetAtPath<GameObject>(p).GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => !m)));
            var windowShader = Shader.Find("Athen Hill/Ward Window Interior");
            r["windowGlass"] = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>(true)).Where(x => x.gameObject.activeInHierarchy && x.enabled)
                .SelectMany(x => x.sharedMaterials.Where(m => m && m.shader == windowShader).Distinct().Select(m => m.name))
                .GroupBy(n => n).ToDictionary(k => k.Key, k => k.Count());
            r["materials"] = MaterialSpecs(tune).Select(ms =>
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(ms.path);
                return new { path = ms.path, values = ms.spec.Properties().Where(p => p.Name != "from" && p.Name != "prefabs" && m.HasProperty(p.Name)).ToDictionary(p => p.Name, p => ReadProp(m, p.Name)) };
            }).ToArray();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            r["reviewCameras"] = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName)?.transform.childCount ?? 0;
            Save("verify-saved-scene.json", r);
            return $"lamps {lamps.Count}, problems {bad}, review cameras {r["reviewCameras"]}";
        }

        // ------------------------------------------------------------------ editor captures (graphics; <= 6 close cameras per run)
        static int capturedThisRun;
        public static string Capture(string spec, string outDir)
        {
            capturedThisRun += spec.Split(':')[2].Split('+').Length;
            if (capturedThisRun > 6) throw new Exception("at most 6 cameras per Unity run (VRAM rule)");
            // spec: HOUR:cam+cam+cam
            var parts = spec.Split(':');
            float hour = float.Parse(parts[1], Inv);
            var cams = parts[2].Split('+');
            if (cams.Length > 6) throw new Exception("at most 6 cameras per capture run");
            OpenScene();
            // review views not yet in the scene (before install) are passed as explicit name:pos:target:fov specs
            cams = cams.Select(c =>
            {
                if (GameObject.Find(c)) return c;
                var v = ReviewViews.FirstOrDefault(x => x.name == c);
                if (v.name == null) return c;
                string F(Vector3 p) => string.Join(",", new[] { p.x, p.y, p.z }.Select(f => f.ToString("0.###", Inv)));
                return $"{v.name}:{F(v.pos)}:{F(v.target)}:{v.fov.ToString(Inv)}";
            }).ToArray();
            // the first render after a scene load comes out half-shaded (shaders/streaming still settling): warm up once
            ShaderUtil.allowAsyncCompilation = false;
            DuskStartPass.Preview(hour, Path.Combine(outDir, "warmup"), cams[0]);
            return DuskStartPass.Preview(hour, outDir, cams);
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.NightFacadePass.RunBatch --steps survey,shadercheck,build,install,verify [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "survey").Split(',');
            var outDir = Arg("--out", Evidence + "editor");
            try
            {
                foreach (var st in steps)
                {
                    string result = st.Split(':')[0] switch
                    {
                        "survey" => Survey(),
                        "remnant" => Remnant(),
                        "decalaudit" => DecalAudit(),
                        "fixdefects" => FixDefects(),
                        "lightprobe" => LightProbe(),
                        "bandprobe" => BandProbe(outDir),
                        "moonscan" => MoonScan(),
                        "shadercheck" => ShaderCheck(),
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "apply" => Apply(),
                        "cameras" => Cameras(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        "capture" => Capture(st, outDir),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("NightFacadePass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
