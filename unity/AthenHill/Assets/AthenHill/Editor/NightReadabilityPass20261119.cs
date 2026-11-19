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

namespace AthenHill.Editor
{
    /// Night readability pass (19 Nov 2026). Sources and record: art/night_readability_20261119/README.md.
    ///
    ///   -executeMethod AthenHill.Editor.NightReadabilityPass20261119.RunBatch --steps survey|apply|verify|rollback
    ///
    /// survey   read-only: clock, live profile, key/fill, grade, URP settings, every actor's renderers and the lights near
    ///          them (layer masks, probe usage, materials) -> survey.json
    /// apply    idempotent: reads night-tune.json and sets the night frames of the clock's live profile (found through
    ///          CityTimeOfDay.profile, not by asset name), the NightActorLighting component on the clock object, any listed
    ///          light edits and the cam_night_* review cameras. Every original value is recorded in originals.json before
    ///          its first write; later applies start from those originals.
    /// verify   saved scene: the values match the tune, the day frames match the recorded snapshot exactly, cameras present.
    /// rollback restores every recorded value, removes the component and the camera root it added, and deletes nothing else.
    public static class NightReadabilityPass20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Dir = "../../art/night_readability_20261119/";
        const string TunePath = Dir + "night-tune.json", OriginalsPath = Dir + "originals.json";
        const string CameraRoot = "Night readability review cameras";

        static Scene OpenScene()
        {
            var scene = SceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            return scene;
        }
        static JObject Json(string path) => File.Exists(path) ? JObject.Parse(File.ReadAllText(path)) : new JObject();
        static void Save(string path, object o) => File.WriteAllText(path, JsonConvert.SerializeObject(o, Formatting.Indented,
            new JsonSerializerSettings { ReferenceLoopHandling = ReferenceLoopHandling.Ignore }));
        static float R(float v) => (float)Math.Round(v, 4);
        static float[] A(Vector3 v) => new[] { R(v.x), R(v.y), R(v.z) };
        static float[] A(Color c) => new[] { R(c.r), R(c.g), R(c.b), R(c.a) };
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static Transform Find(Scene scene, string path)
        {
            var parts = path.Split('/');
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]); if (!root) return null;
            var t = root.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
            return t;
        }

        static JToken ToJ(object v) => v switch
        {
            float f => new JValue(f), bool b => new JValue(b), Color c => new JArray(c.r, c.g, c.b, c.a), Vector3 x => new JArray(x.x, x.y, x.z),
            _ => throw new ArgumentException("unsupported " + v?.GetType())
        };
        static object FromJ(JToken v, Type t)
        {
            var a = v as JArray;
            if (t == typeof(float)) return (float)v;
            if (t == typeof(bool)) return (bool)v;
            if (t == typeof(Color)) return new Color((float)a[0], (float)a[1], (float)a[2], a.Count > 3 ? (float)a[3] : 1);
            if (t == typeof(Vector3)) return new Vector3((float)a[0], (float)a[1], (float)a[2]);
            throw new ArgumentException("unsupported " + t);
        }
        static bool Same(object a, object b)
        {
            if (a is float fa && b is float fb) return Mathf.Abs(fa - fb) < 1e-5f;
            if (a is Color ca && b is Color cb) return Mathf.Abs(ca.r - cb.r) + Mathf.Abs(ca.g - cb.g) + Mathf.Abs(ca.b - cb.b) + Mathf.Abs(ca.a - cb.a) < 1e-5f;
            if (a is Vector3 va && b is Vector3 vb) return (va - vb).sqrMagnitude < 1e-10f;
            return Equals(a, b);
        }

        static CityTimeOfDay Clock()
        {
            var clocks = UnityEngine.Object.FindObjectsByType<CityTimeOfDay>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            if (clocks.Length != 1) throw new Exception("expected one CityTimeOfDay, found " + clocks.Length);
            if (!clocks[0].profile) throw new Exception("the clock has no profile");
            return clocks[0];
        }

        static int FrameIndex(DayNightLightingProfile p, float hour)
        {
            int i = Array.FindIndex(p.frames, f => Mathf.Abs(f.hour - hour) < .01f);
            if (i < 0) throw new Exception("profile " + p.name + " has no frame at hour " + hour);
            return i;
        }

        // ------------------------------------------------------------------ survey (read-only)
        public static string Survey()
        {
            var scene = OpenScene(); var clock = Clock(); var p = clock.profile;
            var r = new Dictionary<string, object>();
            r["clock"] = new { path = PathOf(clock.transform), profile = AssetDatabase.GetAssetPath(p), key = clock.keyLight ? PathOf(clock.keyLight.transform) : null,
                fill = clock.skyFill ? PathOf(clock.skyFill.transform) : null, grade = clock.gradingVolume && clock.gradingVolume.sharedProfile ? AssetDatabase.GetAssetPath(clock.gradingVolume.sharedProfile) : null };
            r["frames"] = p.frames.Select(f => new { f.hour, f.keyIntensity, keyColor = A(f.keyColor), keyEuler = A(f.keyEuler), f.fillIntensity, fillColor = A(f.fillColor),
                ambientSky = A(f.ambientSky), ambientEquator = A(f.ambientEquator), ambientGround = A(f.ambientGround), f.postExposure, f.sunVisibility, f.lampStrength }).ToArray();
            object LightInfo(Light l) => l ? new { path = PathOf(l.transform), type = l.type.ToString(), l.intensity, l.range, l.spotAngle, l.innerSpotAngle, color = A(l.color),
                shadows = l.shadows.ToString(), l.shadowStrength, l.renderingLayerMask, culling = l.cullingMask, mode = l.lightmapBakeType.ToString(), cookie = l.cookie ? l.cookie.name : null,
                pos = A(l.transform.position), fwd = A(l.transform.forward), euler = A(l.transform.eulerAngles), active = l.isActiveAndEnabled, enabled = l.enabled } : null;
            r["key"] = LightInfo(clock.keyLight); r["fill"] = LightInfo(clock.skyFill);
            r["renderSettings"] = new { ambientMode = RenderSettings.ambientMode.ToString(), RenderSettings.ambientIntensity, sky = A(RenderSettings.ambientSkyColor),
                lightProbes = LightmapSettings.lightProbes ? LightmapSettings.lightProbes.count : 0, RenderSettings.reflectionIntensity, defaultReflection = RenderSettings.defaultReflectionMode.ToString() };
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var practical = circuit ? new HashSet<Light>(circuit.practicalLights.Where(l => l)) : new HashSet<Light>();
            r["circuit"] = circuit ? new { circuit.fullLightDistance, circuit.culledLightDistance, circuit.shadowDistance, practical = circuit.practicalLights.Length, nightOnly = circuit.nightOnlyLights.Length } : null;
            var allLights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            r["lightCount"] = new { total = allLights.Length, byType = allLights.GroupBy(l => l.type.ToString()).ToDictionary(g => g.Key, g => g.Count()),
                byLayerMask = allLights.GroupBy(l => l.renderingLayerMask.ToString()).ToDictionary(g => g.Key, g => g.Count()) };
            r["interiors"] = UnityEngine.Object.FindObjectsByType<InteriorLighting>(FindObjectsInactive.Include, FindObjectsSortMode.None).Select(i => new
            { path = PathOf(i.transform), lamps = i.lamps.Where(l => l).Select(l => PathOf(l.transform)).ToArray(), renderers = i.renderers.Count, roots = i.interiorRoots.Where(t => t).Select(t => PathOf(t)).ToArray(), i.ambientScale, i.openingLight }).ToArray();
            var actors = new List<object>();
            var roots = new List<(Transform, string)>();
            foreach (var x in UnityEngine.Object.FindObjectsByType<PlayerMotor>(FindObjectsSortMode.None)) roots.Add((x.transform, "player"));
            foreach (var x in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.None)) roots.Add((x.transform, "npc"));
            foreach (var x in UnityEngine.Object.FindObjectsByType<AmbientWalker>(FindObjectsSortMode.None)) roots.Add((x.transform, "walker"));
            foreach (var (t, kind) in roots)
            {
                var rends = t.GetComponentsInChildren<Renderer>(false).Where(x => x.enabled && !(x is ParticleSystemRenderer)).ToArray();
                if (rends.Length == 0) continue;
                var b = rends[0].bounds; foreach (var x in rends) b.Encapsulate(x.bounds);
                var chest = b.center + Vector3.up * b.extents.y * .35f;
                actors.Add(new
                {
                    path = PathOf(t), kind, pos = A(t.position), fwd = A(t.forward), height = R(b.size.y),
                    renderers = rends.Select(x => new { x.name, type = x.GetType().Name, x.renderingLayerMask, probe = x.lightProbeUsage.ToString(), x.receiveShadows,
                        mats = x.sharedMaterials.Where(m => m).Select(m => new { m.name, shader = m.shader.name,
                            baseColor = m.HasProperty("_BaseColor") ? A(m.GetColor("_BaseColor")) : null,
                            smooth = m.HasProperty("_Smoothness") ? (float?)R(m.GetFloat("_Smoothness")) : null, metal = m.HasProperty("_Metallic") ? (float?)R(m.GetFloat("_Metallic")) : null,
                            metalMap = m.HasProperty("_MetallicGlossMap") && m.GetTexture("_MetallicGlossMap") ? m.GetTexture("_MetallicGlossMap").name : null,
                            occ = m.HasProperty("_OcclusionMap") && m.GetTexture("_OcclusionMap") ? m.GetTexture("_OcclusionMap").name : null,
                            specOff = m.IsKeywordEnabled("_SPECULARHIGHLIGHTS_OFF"), envOff = m.IsKeywordEnabled("_ENVIRONMENTREFLECTIONS_OFF") }).ToArray() }).ToArray(),
                    nearLights = allLights.Where(l => l.type != LightType.Directional && Vector3.Distance(l.transform.position, chest) < l.range).Select(l => new
                    { light = LightInfo(l), dist = R(Vector3.Distance(l.transform.position, chest)), practical = practical.Contains(l),
                        coneDeg = l.type == LightType.Spot ? R(Vector3.Angle(l.transform.forward, chest - l.transform.position)) : -1,
                        layerOk = rends.All(x => (x.renderingLayerMask & (uint)l.renderingLayerMask) != 0) }).ToArray()
                });
            }
            r["actors"] = actors;
            Save(Dir + "survey.json", r);
            return actors.Count + " actors, " + allLights.Length + " lights";
        }

        // ------------------------------------------------------------------ apply (idempotent)
        public static string Apply()
        {
            var scene = OpenScene(); var clock = Clock(); var p = clock.profile;
            var tune = Json(TunePath); var orig = Json(OriginalsPath);
            if (orig["profile"] == null)
            {
                orig["profile"] = AssetDatabase.GetAssetPath(p);
                // Whole-profile snapshot (every frame, every field) taken before the first write: verify compares day frames to it.
                orig["snapshot"] = JArray.FromObject(p.frames.Select(f => typeof(DayNightFrame).GetFields().ToDictionary(fi => fi.Name, fi => ToJ(fi.GetValue(f)))));
            }
            else if ((string)orig["profile"] != AssetDatabase.GetAssetPath(p)) throw new Exception("originals were recorded for " + orig["profile"] + " but the clock now uses " + AssetDatabase.GetAssetPath(p));
            var log = new List<string>();
            // frames: originals first, then the tune
            var origFrames = (JObject)(orig["frames"] ??= new JObject());
            Undo.RecordObject(p, "Night readability");
            var frames = p.frames;
            foreach (var fp in ((JObject)tune["frames"] ?? new JObject()).Properties())
            {
                float hour = float.Parse(fp.Name, System.Globalization.CultureInfo.InvariantCulture);
                int i = FrameIndex(p, hour); object boxed = frames[i];
                var of = (JObject)(origFrames[fp.Name] ??= new JObject());
                foreach (var f in ((JObject)fp.Value).Properties())
                {
                    var fi = typeof(DayNightFrame).GetField(f.Name) ?? throw new Exception("no frame field " + f.Name);
                    if (of[f.Name] == null) of[f.Name] = ToJ(fi.GetValue(boxed));
                    fi.SetValue(boxed, FromJ(f.Value, fi.FieldType)); log.Add(fp.Name + "." + f.Name);
                }
                frames[i] = (DayNightFrame)boxed;
            }
            p.frames = frames; EditorUtility.SetDirty(p);
            // NightActorLighting on the clock object
            if (tune["actor"] is JObject actor)
            {
                var nal = clock.GetComponent<NightActorLighting>();
                if (orig["componentAdded"] == null) orig["componentAdded"] = nal == null;
                if (!nal) nal = Undo.AddComponent<NightActorLighting>(clock.gameObject);
                var oa = (JObject)(orig["actor"] ??= new JObject());
                nal.clock = clock;
                foreach (var f in actor.Properties())
                {
                    var fi = typeof(NightActorLighting).GetField(f.Name) ?? throw new Exception("no actor field " + f.Name);
                    if (oa[f.Name] == null) oa[f.Name] = ToJ(fi.GetValue(nal));
                    fi.SetValue(nal, FromJ(f.Value, fi.FieldType)); log.Add("actor." + f.Name);
                }
                EditorUtility.SetDirty(nal);
            }
            // light edits by scene path: intensity, range, spotAngle, innerSpotAngle, localEulerAngles, localPosition
            var ol = (JObject)(orig["lights"] ??= new JObject());
            foreach (JObject le in (JArray)tune["lights"] ?? new JArray())
            {
                string path = (string)le["path"];
                var t = Find(scene, path) ?? throw new Exception("no light at " + path);
                var l = t.GetComponent<Light>() ?? throw new Exception("no Light on " + path);
                if (ol[path] == null) ol[path] = new JObject { ["intensity"] = l.intensity, ["range"] = l.range, ["spotAngle"] = l.spotAngle, ["innerSpotAngle"] = l.innerSpotAngle,
                    ["localEulerAngles"] = ToJ(t.localEulerAngles), ["localPosition"] = ToJ(t.localPosition) };
                Undo.RecordObject(l, "Night readability"); Undo.RecordObject(t, "Night readability");
                SetLight(l, le); log.Add("light " + path);
                EditorUtility.SetDirty(l); EditorUtility.SetDirty(t);
                if (PrefabUtility.IsPartOfPrefabInstance(l)) { PrefabUtility.RecordPrefabInstancePropertyModifications(l); PrefabUtility.RecordPrefabInstancePropertyModifications(t); }
            }
            // review cameras (recreated each apply)
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CameraRoot);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            if (tune["cameras"] is JArray cams && cams.Count > 0)
            {
                if (cams.Count > 10) throw new Exception("at most 10 review cameras");
                var root = new GameObject(CameraRoot); SceneManager.MoveGameObjectToScene(root, scene);
                foreach (JObject c in cams)
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(root.transform, false);
                    var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = c["fov"] != null ? (float)c["fov"] : 45; cam.nearClipPlane = .1f;
                    if (c["from"] != null)
                    {
                        // a pulled-back copy of an existing review camera: same height and aim, `back` metres further away
                        var src = UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(x => x.name == (string)c["from"])
                                  ?? throw new Exception("no camera " + c["from"]);
                        var flat = src.transform.forward; flat.y = 0; flat.Normalize();
                        go.transform.SetPositionAndRotation(src.transform.position - flat * (float)c["back"], src.transform.rotation);
                        if (c["fov"] == null) cam.fieldOfView = src.fieldOfView;
                    }
                    else go.transform.SetPositionAndRotation((Vector3)FromJ(c["pos"], typeof(Vector3)), Quaternion.Euler((Vector3)FromJ(c["euler"], typeof(Vector3))));
                    if (Physics.CheckSphere(go.transform.position, .2f, ~0, QueryTriggerInteraction.Ignore)) Debug.LogWarning("NightReadabilityPass20261119: camera " + go.name + " starts inside a collider");
                }
                orig["cameraRootAdded"] = true; log.Add(cams.Count + " cameras");
            }
            Save(OriginalsPath, orig);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            return string.Join(", ", log);
        }

        static void SetLight(Light l, JObject v)
        {
            var t = l.transform;
            if (v["intensity"] != null) l.intensity = (float)v["intensity"];
            if (v["range"] != null) l.range = (float)v["range"];
            if (v["spotAngle"] != null) l.spotAngle = (float)v["spotAngle"];
            if (v["innerSpotAngle"] != null) l.innerSpotAngle = (float)v["innerSpotAngle"];
            if (v["localEulerAngles"] != null) t.localEulerAngles = (Vector3)FromJ(v["localEulerAngles"], typeof(Vector3));
            if (v["localPosition"] != null) t.localPosition = (Vector3)FromJ(v["localPosition"], typeof(Vector3));
        }

        // ------------------------------------------------------------------ verify (saved scene)
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var clock = Clock(); var p = clock.profile; var tune = Json(TunePath); var orig = Json(OriginalsPath);
            var problems = new List<string>(); var r = new Dictionary<string, object>();
            if ((string)orig["profile"] != AssetDatabase.GetAssetPath(p)) problems.Add("profile changed: " + orig["profile"] + " vs " + AssetDatabase.GetAssetPath(p));
            foreach (var fp in ((JObject)tune["frames"] ?? new JObject()).Properties())
            {
                var f = p.frames[FrameIndex(p, float.Parse(fp.Name, System.Globalization.CultureInfo.InvariantCulture))];
                foreach (var x in ((JObject)fp.Value).Properties())
                {
                    var fi = typeof(DayNightFrame).GetField(x.Name);
                    if (!Same(fi.GetValue(f), FromJ(x.Value, fi.FieldType))) problems.Add("frame " + fp.Name + "." + x.Name + " not applied");
                }
            }
            // every frame and field not named in the tune must equal the pre-install snapshot exactly (day frames unchanged)
            var snap = (JArray)orig["snapshot"]; var tuned = ((JObject)tune["frames"] ?? new JObject());
            int checkedFields = 0;
            if (snap == null || snap.Count != p.frames.Length) problems.Add("snapshot missing or frame count changed");
            else for (int i = 0; i < p.frames.Length; i++)
                {
                    var key = tuned.Properties().FirstOrDefault(x => Mathf.Abs(float.Parse(x.Name, System.Globalization.CultureInfo.InvariantCulture) - p.frames[i].hour) < .01f);
                    foreach (var fi in typeof(DayNightFrame).GetFields())
                    {
                        if (key != null && ((JObject)key.Value)[fi.Name] != null) continue;
                        checkedFields++;
                        if (!Same(fi.GetValue(p.frames[i]), FromJ(snap[i][fi.Name], fi.FieldType))) problems.Add("untuned field changed: frame " + p.frames[i].hour + "." + fi.Name);
                    }
                }
            var nal = clock.GetComponent<NightActorLighting>();
            if (tune["actor"] is JObject actor)
            {
                if (!nal) problems.Add("NightActorLighting missing");
                else
                {
                    if (nal.clock != clock) problems.Add("NightActorLighting.clock not the clock");
                    foreach (var x in actor.Properties()) { var fi = typeof(NightActorLighting).GetField(x.Name); if (!Same(fi.GetValue(nal), FromJ(x.Value, fi.FieldType))) problems.Add("actor." + x.Name + " not applied"); }
                }
            }
            foreach (JObject le in (JArray)tune["lights"] ?? new JArray())
            {
                var t = Find(scene, (string)le["path"]); var l = t ? t.GetComponent<Light>() : null;
                if (!l) { problems.Add("light missing " + le["path"]); continue; }
                if (le["intensity"] != null && Mathf.Abs(l.intensity - (float)le["intensity"]) > 1e-4f) problems.Add("light intensity " + le["path"]);
                if (le["localEulerAngles"] != null && Quaternion.Angle(t.localRotation, Quaternion.Euler((Vector3)FromJ(le["localEulerAngles"], typeof(Vector3)))) > .01f) problems.Add("light aim " + le["path"]);
            }
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CameraRoot);
            var camNames = camRoot ? camRoot.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            foreach (JObject c in (JArray)tune["cameras"] ?? new JArray()) if (!camNames.Contains((string)c["name"])) problems.Add("camera missing " + c["name"]);
            var lights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            r["problems"] = problems; r["untunedFieldsChecked"] = checkedFields; r["cameras"] = camNames;
            r["lightsInScene"] = lights.Length; r["nightActorLighting"] = nal ? new { nal.nightKeyShadowStrength, nal.actorAmbientGain, nal.viewerFillIntensity, nal.viewerFillElevation, color = A(nal.viewerFillColor) } : null;
            r["profile"] = AssetDatabase.GetAssetPath(p);
            Save(Dir + "verify.json", r);
            if (problems.Count > 0) throw new Exception("verify: " + string.Join("; ", problems));
            return "ok, " + checkedFields + " untuned fields unchanged, " + lights.Length + " lights in scene";
        }

        // ------------------------------------------------------------------ rollback
        public static string Rollback()
        {
            var scene = OpenScene(); var clock = Clock(); var p = clock.profile; var orig = Json(OriginalsPath);
            if (orig["profile"] == null) return "nothing recorded";
            var log = new List<string>();
            var frames = p.frames;
            foreach (var fp in ((JObject)orig["frames"] ?? new JObject()).Properties())
            {
                int i = FrameIndex(p, float.Parse(fp.Name, System.Globalization.CultureInfo.InvariantCulture)); object boxed = frames[i];
                foreach (var f in ((JObject)fp.Value).Properties()) { var fi = typeof(DayNightFrame).GetField(f.Name); fi.SetValue(boxed, FromJ(f.Value, fi.FieldType)); log.Add(fp.Name + "." + f.Name); }
                frames[i] = (DayNightFrame)boxed;
            }
            p.frames = frames; EditorUtility.SetDirty(p);
            var nal = clock.GetComponent<NightActorLighting>();
            if (nal)
            {
                if (orig["componentAdded"] != null && (bool)orig["componentAdded"]) { UnityEngine.Object.DestroyImmediate(nal); log.Add("component removed"); }
                else foreach (var f in ((JObject)orig["actor"] ?? new JObject()).Properties()) { var fi = typeof(NightActorLighting).GetField(f.Name); fi.SetValue(nal, FromJ(f.Value, fi.FieldType)); }
            }
            foreach (var lp in ((JObject)orig["lights"] ?? new JObject()).Properties())
            {
                var t = Find(scene, lp.Name); var l = t ? t.GetComponent<Light>() : null; if (!l) { log.Add("light gone " + lp.Name); continue; }
                SetLight(l, (JObject)lp.Value); EditorUtility.SetDirty(l); EditorUtility.SetDirty(t);
                if (PrefabUtility.IsPartOfPrefabInstance(l)) { PrefabUtility.RecordPrefabInstancePropertyModifications(l); PrefabUtility.RecordPrefabInstancePropertyModifications(t); }
                log.Add("light " + lp.Name);
            }
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CameraRoot);
            if (camRoot) { UnityEngine.Object.DestroyImmediate(camRoot); log.Add("cameras removed"); }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            // originals.json is kept (renamed) so a later apply records afresh from the restored state
            File.Copy(OriginalsPath, Dir + "originals.rolled-back-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json", true); File.Delete(OriginalsPath);
            return string.Join(", ", log);
        }

        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            try
            {
                foreach (var st in Arg("--steps", "survey").Split(','))
                {
                    string result = st switch { "survey" => Survey(), "apply" => Apply(), "verify" => Verify(), "rollback" => Rollback(), _ => throw new Exception("unknown step " + st) };
                    Debug.Log("NightReadabilityPass20261119 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
