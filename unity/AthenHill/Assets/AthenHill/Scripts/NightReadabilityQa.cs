#if UNITY_EDITOR || DEBUG
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill
{
    /// Night readability (19 Nov 2026) native diagnostics, development players only, opt-in by environment:
    ///   ATHEN_NIGHT_DIAG=1        with --athen-qa OUT: write OUT/night-diag.json, one entry per (review camera, hour)
    ///                             once the view has settled: ambient, key/fill, every actor's renderers (layer mask,
    ///                             probe usage, materials), the lights that reach each actor, the actor's face/torso and
    ///                             surrounding ground as screen boxes for luminance measurement, and the lights in view.
    ///   ATHEN_NIGHT_TUNE=file     a JSON override applied after the scene loads (tuning without a rebuild):
    ///                             {"frames":{"19":{"ambientSky":[r,g,b],"keyIntensity":0.5,...}},
    ///                              "actor":{"nightKeyShadowStrength":0.6,"actorAmbientGain":1,...},
    ///                              "lights":[{"prefix":"name","intensityScale":1.2}]}
    /// Nothing is saved; a release player never compiles this.
    public sealed class NightReadabilityQa : MonoBehaviour
    {
        string folder, tunePath; bool diag;
        CityTimeOfDay clock; AthenDebugBridge bridge;
        string lastKey; float settleSince; readonly HashSet<string> written = new HashSet<string>();
        readonly List<object> entries = new List<object>();
        object tuneApplied;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (!Debug.isDebugBuild && !Application.isEditor) return;
            var d = Environment.GetEnvironmentVariable("ATHEN_NIGHT_DIAG"); var t = Environment.GetEnvironmentVariable("ATHEN_NIGHT_TUNE");
            if (string.IsNullOrEmpty(d) && string.IsNullOrEmpty(t)) return;
            var args = Environment.GetCommandLineArgs(); int i = Array.IndexOf(args, "--athen-qa");
            var qa = new GameObject("Night readability QA").AddComponent<NightReadabilityQa>();
            qa.folder = i >= 0 && i + 1 < args.Length ? Path.GetFullPath(args[i + 1]) : null;
            qa.diag = d == "1" && qa.folder != null; qa.tunePath = string.IsNullOrEmpty(t) ? null : t;
        }

        void Start()
        {
            clock = FindAnyObjectByType<CityTimeOfDay>(); bridge = FindAnyObjectByType<AthenDebugBridge>();
            if (tunePath != null) { try { ApplyTune(JObject.Parse(File.ReadAllText(tunePath))); } catch (Exception e) { Debug.LogError("Night tune failed: " + e); tuneApplied = "error: " + e.Message; } }
        }

        static object Read(JToken v, Type t)
        {
            var a = v as JArray;
            if (t == typeof(float)) return (float)v;
            if (t == typeof(Color)) return new Color((float)a[0], (float)a[1], (float)a[2], a.Count > 3 ? (float)a[3] : 1);
            if (t == typeof(Vector3)) return new Vector3((float)a[0], (float)a[1], (float)a[2]);
            if (t == typeof(bool)) return (bool)v;
            throw new ArgumentException("unsupported field type " + t);
        }

        void ApplyTune(JObject j)
        {
            var log = new List<string>();
            if (j["frames"] is JObject frames && clock && clock.profile)
            {
                var fr = clock.profile.frames;
                foreach (var p in frames.Properties())
                {
                    float hour = float.Parse(p.Name, System.Globalization.CultureInfo.InvariantCulture);
                    int idx = Array.FindIndex(fr, f => Mathf.Abs(f.hour - hour) < .01f);
                    if (idx < 0) { log.Add("no frame at " + p.Name); continue; }
                    object boxed = fr[idx];
                    foreach (var f in ((JObject)p.Value).Properties())
                    {
                        var field = typeof(DayNightFrame).GetField(f.Name);
                        if (field == null) { log.Add("no field " + f.Name); continue; }
                        field.SetValue(boxed, Read(f.Value, field.FieldType)); log.Add(p.Name + "." + f.Name);
                    }
                    fr[idx] = (DayNightFrame)boxed;
                }
                clock.Refresh();
            }
            if (j["actor"] is JObject actor && clock)
            {
                var nal = clock.GetComponent<NightActorLighting>() ?? clock.gameObject.AddComponent<NightActorLighting>();
                nal.clock = clock;
                foreach (var f in actor.Properties())
                {
                    var field = typeof(NightActorLighting).GetField(f.Name);
                    if (field == null) { log.Add("no actor field " + f.Name); continue; }
                    field.SetValue(nal, Read(f.Value, field.FieldType)); log.Add("actor." + f.Name);
                }
            }
            if (j["circuit"] is JObject circ)
            {
                var c = FindAnyObjectByType<CityLightCircuit>();
                if (c)
                {
                    foreach (var f in circ.Properties())
                    {
                        var field = typeof(CityLightCircuit).GetField(f.Name);
                        if (field == null) { log.Add("no circuit field " + f.Name); continue; }
                        field.SetValue(c, Read(f.Value, field.FieldType)); log.Add("circuit." + f.Name);
                    }
                    c.Refresh();
                }
            }
            if (j["lights"] is JArray lights)
            {
                var circuit = FindAnyObjectByType<CityLightCircuit>();
                foreach (JObject l in lights)
                {
                    string prefix = (string)l["prefix"]; float scale = l["intensityScale"] != null ? (float)l["intensityScale"] : 1;
                    int n = 0;
                    foreach (var light in FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                        if (light.name.StartsWith(prefix, StringComparison.Ordinal)) { light.intensity *= scale; n++; }
                    log.Add("lights " + prefix + " x" + scale + " (" + n + ")");
                }
                // The circuit cached authored intensities at OnEnable: re-enable it so scaled lamps are its new base.
                if (circuit) { circuit.enabled = false; circuit.enabled = true; }
            }
            tuneApplied = log;
            Debug.Log("Night tune applied: " + string.Join(", ", log));
        }

        void Update()
        {
            if (!diag || !clock || !bridge) return;
            string key = bridge.selectedCamera + "@" + clock.Hour.ToString("00.00", System.Globalization.CultureInfo.InvariantCulture);
            if (key != lastKey) { lastKey = key; settleSince = Time.unscaledTime; return; }
            if (bridge.selectedCamera == "follow" || written.Contains(key) || Time.unscaledTime - settleSince < .9f) return;
            written.Add(key);
            try { entries.Add(Snapshot()); Write(); } catch (Exception e) { Debug.LogError("Night diag failed: " + e); }
        }

        void Write()
        {
            var path = Path.Combine(folder, "night-diag.json");
            File.WriteAllText(path + ".tmp", JsonConvert.SerializeObject(new { tune = tuneApplied, entries }, Formatting.Indented));
            if (File.Exists(path)) File.Delete(path); File.Move(path + ".tmp", path);
        }

        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
        static float[] C(Color c) => new[] { (float)Math.Round(c.r, 4), (float)Math.Round(c.g, 4), (float)Math.Round(c.b, 4) };

        static Transform FindBone(Transform root, params string[] names)
        {
            foreach (var n in names)
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (string.Equals(t.name, n, StringComparison.OrdinalIgnoreCase) || t.name.EndsWith(":" + n, StringComparison.OrdinalIgnoreCase)) return t;
            return null;
        }

        static float[] Box(Camera cam, Vector3 world, float halfMetres)
        {
            var c = cam.WorldToScreenPoint(world); if (c.z <= .05f) return null;
            var e = cam.WorldToScreenPoint(world + cam.transform.right * halfMetres);
            float r = Mathf.Max(2, Vector2.Distance(c, e));
            return new[] { c.x - r, Screen.height - c.y - r, c.x + r, Screen.height - c.y + r };
        }

        static bool Visible(Camera cam, Vector3 world, Transform ignore)
        {
            var from = cam.transform.position; var d = world - from; float dist = d.magnitude;
            foreach (var hit in Physics.RaycastAll(from, d / dist, dist - .25f, ~0, QueryTriggerInteraction.Ignore))
            {
                if (ignore && hit.transform.IsChildOf(ignore)) continue;
                return false;
            }
            return true;
        }

        object Snapshot()
        {
            var cam = Camera.main; var planes = GeometryUtility.CalculateFrustumPlanes(cam);
            var lights = FindObjectsByType<Light>(FindObjectsSortMode.None);
            var inView = new List<Light>(); int dirs = 0;
            foreach (var l in lights)
            {
                if (!l.isActiveAndEnabled || l.intensity <= 0) continue;
                if (l.type == LightType.Directional) { dirs++; continue; }
                if (GeometryUtility.TestPlanesAABB(planes, new Bounds(l.transform.position, Vector3.one * 2 * l.range))) inView.Add(l);
            }
            var key = clock.keyLight; var fill = clock.skyFill; var nal = clock.GetComponent<NightActorLighting>();
            var sh = RenderSettings.ambientProbe;
            var actorRoots = new List<(Transform t, string kind)>();
            foreach (var p in FindObjectsByType<PlayerMotor>(FindObjectsSortMode.None)) actorRoots.Add((p.transform, "player"));
            foreach (var n in FindObjectsByType<NpcAgent>(FindObjectsSortMode.None)) actorRoots.Add((n.transform, "npc"));
            foreach (var w in FindObjectsByType<AmbientWalker>(FindObjectsSortMode.None)) actorRoots.Add((w.transform, "walker"));
            foreach (var a in FindObjectsByType<ActorAnimation>(FindObjectsSortMode.None))
                if (!actorRoots.Any(x => a.transform.IsChildOf(x.t) || x.t.IsChildOf(a.transform))) actorRoots.Add((a.transform, "actor"));
            var actors = new List<object>();
            foreach (var (root, kind) in actorRoots)
            {
                var rends = root.GetComponentsInChildren<Renderer>(false).Where(r => r.enabled && !(r is ParticleSystemRenderer)).ToArray();
                if (rends.Length == 0) continue;
                var bounds = rends[0].bounds; foreach (var r in rends) bounds.Encapsulate(r.bounds);
                float dist = Vector3.Distance(cam.transform.position, bounds.center);
                bool onScreen = GeometryUtility.TestPlanesAABB(planes, bounds) && dist < 45;
                var head = FindBone(root, "Head", "head"); var chest = FindBone(root, "Spine02", "Spine2", "spine_03", "Spine1", "Spine01", "Spine", "spine_02");
                var headPos = head ? head.position + Vector3.up * .06f : new Vector3(bounds.center.x, bounds.max.y - .13f, bounds.center.z);
                var chestPos = chest ? chest.position : new Vector3(bounds.center.x, bounds.min.y + bounds.size.y * .68f, bounds.center.z);
                var feet = new Vector3(headPos.x, bounds.min.y, headPos.z);
                object screen = null;
                if (onScreen)
                {
                    var ground = new List<float[]>();
                    for (int k = 0; k < 12; k++)
                    {
                        float ang = k * 30f * Mathf.Deg2Rad; float rad = k % 2 == 0 ? 1.1f : 1.6f;
                        var p = feet + new Vector3(Mathf.Cos(ang) * rad, 1, Mathf.Sin(ang) * rad);
                        if (!Physics.Raycast(p, Vector3.down, out var hit, 2.5f, ~0, QueryTriggerInteraction.Ignore)) continue;
                        if (hit.transform.IsChildOf(root) || Mathf.Abs(hit.point.y - feet.y) > .4f) continue;
                        if (!Visible(cam, hit.point + Vector3.up * .03f, root)) continue;
                        var b = Box(cam, hit.point + Vector3.up * .02f, .1f); if (b != null) ground.Add(b);
                    }
                    screen = new
                    {
                        face = Box(cam, headPos, .07f), faceVisible = Visible(cam, headPos, root),
                        torso = Box(cam, chestPos, .1f), torsoVisible = Visible(cam, chestPos, root), ground
                    };
                }
                var reach = new List<object>();
                foreach (var l in lights)
                {
                    if (l.type == LightType.Directional) continue;
                    float d = Vector3.Distance(l.transform.position, chestPos); if (d > l.range) continue;
                    uint lm = (uint)l.renderingLayerMask; bool layerOk = rends.All(r => (r.renderingLayerMask & lm) != 0);
                    float cone = 1;
                    if (l.type == LightType.Spot)
                    {
                        float ang = Vector3.Angle(l.transform.forward, chestPos - l.transform.position);
                        cone = Mathf.Clamp01(Mathf.InverseLerp(l.spotAngle * .5f, l.innerSpotAngle * .5f, ang));
                    }
                    float atten = 1f / Mathf.Max(.01f, d * d) * Mathf.Pow(Mathf.Clamp01(1 - Mathf.Pow(d / l.range, 4)), 2);
                    reach.Add(new { l.name, type = l.type.ToString(), enabled = l.isActiveAndEnabled, intensity = Math.Round(l.intensity, 3), range = Math.Round(l.range, 2), dist = Math.Round(d, 2),
                        cone = Math.Round(cone, 2), estChest = Math.Round(l.intensity * cone * atten, 4), layerMask = lm, layerOk, cookie = l.cookie ? l.cookie.name : null, shadows = l.shadows.ToString() });
                }
                bool moonShadow = key && key.enabled && Physics.Raycast(chestPos, -key.transform.forward, 200, ~0, QueryTriggerInteraction.Ignore);
                actors.Add(new
                {
                    name = root.name, kind, position = V(root.position), distance = Math.Round(dist, 1), onScreen, screen, moonShadowAtChest = moonShadow,
                    facingCamera = Math.Round(Vector3.Dot(root.forward, (cam.transform.position - root.position).normalized), 2),
                    renderers = rends.Take(14).Select(r => new
                    {
                        r.name, type = r.GetType().Name, layerMask = r.renderingLayerMask, probe = r.lightProbeUsage.ToString(), r.receiveShadows, shadow = r.shadowCastingMode.ToString(),
                        materials = r.sharedMaterials.Where(m => m).Select(m => new
                        {
                            m.name, shader = m.shader.name,
                            baseColor = m.HasProperty("_BaseColor") ? C(m.GetColor("_BaseColor")) : null,
                            baseMap = m.HasProperty("_BaseMap") && m.GetTexture("_BaseMap") ? m.GetTexture("_BaseMap").name : null,
                            smoothness = m.HasProperty("_Smoothness") ? (float?)m.GetFloat("_Smoothness") : null,
                            metallic = m.HasProperty("_Metallic") ? (float?)m.GetFloat("_Metallic") : null,
                            specOff = m.IsKeywordEnabled("_SPECULARHIGHLIGHTS_OFF"), envOff = m.IsKeywordEnabled("_ENVIRONMENTREFLECTIONS_OFF"),
                            receiveShadowsOff = m.IsKeywordEnabled("_RECEIVE_SHADOWS_OFF"), occlusion = m.HasProperty("_OcclusionStrength") ? (float?)m.GetFloat("_OcclusionStrength") : null,
                            occlusionMap = m.HasProperty("_OcclusionMap") && m.GetTexture("_OcclusionMap") ? m.GetTexture("_OcclusionMap").name : null,
                            metallicMap = m.HasProperty("_MetallicGlossMap") && m.GetTexture("_MetallicGlossMap") ? m.GetTexture("_MetallicGlossMap").name : null,
                            emission = m.HasProperty("_EmissionColor") && m.IsKeywordEnabled("_EMISSION") ? C(m.GetColor("_EmissionColor")) : null
                        }).ToArray()
                    }).ToArray(),
                    lights = reach
                });
            }
            return new
            {
                camera = bridge.selectedCamera, hour = Math.Round(clock.Hour, 2), screen = new[] { Screen.width, Screen.height },
                cameraPosition = V(cam.transform.position),
                ambient = new { mode = RenderSettings.ambientMode.ToString(), intensity = RenderSettings.ambientIntensity, sky = C(RenderSettings.ambientSkyColor), equator = C(RenderSettings.ambientEquatorColor), ground = C(RenderSettings.ambientGroundColor),
                    probeL0 = new[] { sh[0, 0], sh[1, 0], sh[2, 0] }, probeL1y = new[] { sh[0, 2], sh[1, 2], sh[2, 2] }, reflectionIntensity = RenderSettings.reflectionIntensity },
                key = key ? new { key.enabled, intensity = key.intensity, color = C(key.color), euler = V(key.transform.eulerAngles), shadows = key.shadows.ToString(), key.shadowStrength, layerMask = key.renderingLayerMask } : null,
                fill = fill ? new { fill.enabled, type = fill.type.ToString(), intensity = fill.intensity, color = C(fill.color), euler = V(fill.transform.eulerAngles), shadows = fill.shadows.ToString(), layerMask = fill.renderingLayerMask } : null,
                postExposure = clock.CurrentFrame.postExposure, sunVisibility = clock.SunVisibility, lampStrength = clock.LampStrength,
                nightActor = nal ? new { nal.enabled, nal.NightWeight, nal.ActorsLit, nal.nightKeyShadowStrength, nal.actorAmbientGain, nal.viewerFillIntensity, nal.viewerFillElevation } : null,
                weather = WeatherDirector.QaSnapshot(),
                lightsInView = new { directional = dirs, local = inView.Count, total = dirs + inView.Count, shadowed = inView.Count(l => l.shadows != LightShadows.None), cap = 32 },
                circuit = FindObjectsByType<CityLightCircuit>(FindObjectsSortMode.None).Select(c => new { c.name, c.ActiveLights, c.ActiveShadowLights, c.CurrentStrength }).ToArray(),
                actors
            };
        }
    }
}
#endif
