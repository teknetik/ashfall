#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Task t_e14abefb (29 Sep 2026). Editor-only, recoverable. Inspect writes a report and changes nothing.
    public static class ToolExchangeLightPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Evidence => Path.Combine(Repo, "unity/evidence/tool-exchange/20260929-light");
        static void Write(string name, object data) { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, name), JsonConvert.SerializeObject(data, Formatting.Indented)); }
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        static void OpenScene()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play first.");
            if (EditorSceneManager.GetActiveScene().path != ScenePath) EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        const string LightName = "Tool Exchange display practical light";
        const string InstanceName = "Tool Exchange display and shutter";

        // Params come from <evidence>/light-params.json so tuning does not need a recompile:
        // { "pos":[x,y,z] world, "aim":[x,y,z] world, "type":"Spot|Point", "intensity":f, "range":f, "spotAngle":f, "innerSpotAngle":f, "color":[r,g,b], "nightOnly":bool, "enabled":bool }
        // Creates or updates the single light (idempotent by name). Never touches shadows (always None: no point-shadow-atlas use).
        public static void ApplyBatch()
        {
            OpenScene();
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.isDirty) throw new InvalidOperationException("Scene has unsaved edits.");
            var p = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(Path.Combine(Evidence, "light-params.json")));
            var display = GameObject.Find(InstanceName); if (!display) throw new InvalidOperationException("Tool Exchange display instance missing.");
            var circuit = Object.FindAnyObjectByType<CityLightCircuit>(); if (!circuit) throw new InvalidOperationException("CityLightCircuit missing.");
            var go = GameObject.Find(LightName);
            bool created = !go;
            if (created) { go = new GameObject(LightName); Undo.RegisterCreatedObjectUndo(go, "Tool Exchange practical light"); go.transform.SetParent(display.transform, true); }
            Vec(p["pos"], out var pos); Vec(p["aim"], out var aim);
            go.transform.position = pos; go.transform.rotation = Quaternion.LookRotation((aim - pos).normalized, Vector3.up);
            var l = go.GetComponent<Light>() ? go.GetComponent<Light>() : go.AddComponent<Light>();
            l.type = (string)p["type"] == "Point" ? LightType.Point : LightType.Spot;
            l.lightmapBakeType = LightmapBakeType.Realtime; l.renderMode = LightRenderMode.Auto;
            var c = (Newtonsoft.Json.Linq.JArray)p["color"]; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
            l.intensity = (float)p["intensity"]; l.range = (float)p["range"];
            if (l.type == LightType.Spot) { l.spotAngle = (float)p["spotAngle"]; l.innerSpotAngle = (float)p["innerSpotAngle"]; }
            l.shadows = LightShadows.None; l.enabled = true;
            bool nightOnly = (bool)p["nightOnly"];
            Undo.RecordObject(circuit, "Bind Tool Exchange light");
            circuit.practicalLights = circuit.practicalLights.Where(x => x && x != l).Concat(new[] { l }).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(x => x && x != l).Concat(nightOnly ? new[] { l } : new Light[0]).ToArray();
            EditorUtility.SetDirty(circuit); EditorUtility.SetDirty(l);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Write("apply.json", new { utc = DateTime.UtcNow, created, parameters = p.ToString(Formatting.None), path = PathOf(go.transform), worldPos = A(go.transform.position), worldEuler = A(go.transform.eulerAngles), practicalCount = circuit.practicalLights.Length, nightOnlyCount = circuit.nightOnlyLights.Length });
        }

        static void Vec(Newtonsoft.Json.Linq.JToken a, out Vector3 v) { v = new Vector3((float)a[0], (float)a[1], (float)a[2]); }

        public static void VerifyBatch()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single); // reopen from disk
            var go = GameObject.Find(LightName); var l = go ? go.GetComponent<Light>() : null;
            var circuit = Object.FindAnyObjectByType<CityLightCircuit>();
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var display = GameObject.Find(InstanceName);
            var vex = Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(n => n.name == "npc_vex").Select(n => A(n.transform.position)).FirstOrDefault();
            Write("verify-saved-scene.json", new
            {
                utc = DateTime.UtcNow, reopenedFromDisk = true, lightPresent = l != null, path = go ? PathOf(go.transform) : null,
                type = l ? l.type.ToString() : null, intensity = l ? l.intensity : 0, range = l ? l.range : 0, shadows = l ? l.shadows.ToString() : null, enabled = l && l.enabled,
                worldPos = go ? A(go.transform.position) : null, parentedToDisplay = go && display && go.transform.IsChildOf(display.transform),
                boundToCircuit = circuit && l && circuit.practicalLights.Contains(l), nightOnly = circuit && l && circuit.nightOnlyLights.Contains(l),
                displayRenderers = display ? display.GetComponentsInChildren<MeshRenderer>(true).Length : 0,
                displayColliders = display ? display.GetComponentsInChildren<Collider>(true).Length : -1,
                sceneColliderCount = Object.FindObjectsByType<Collider>(FindObjectsInactive.Include, FindObjectsSortMode.None).Length,
                chunkFingerprintMatches = chunks && !chunks.editingSources && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks), chunkSourcesShown = chunks ? chunks.editingSources : (bool?)null,
                vexRoot = vex, additionalShadowLightsInScene = Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None).Count(x => x.type != LightType.Directional && x.shadows != LightShadows.None && x.enabled),
                sceneSha256 = System.BitConverter.ToString(System.Security.Cryptography.SHA256.Create().ComputeHash(File.ReadAllBytes(Path.Combine(Repo, "unity/AthenHill/" + ScenePath)))).Replace("-", "").ToLowerInvariant()
            });
        }

        public static void InspectBatch()
        {
            OpenScene();
            var centre = new Vector3(-18f, 1.8f, 8.5f);
            var building = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(t => t.name == "tool_exchange" && t.GetComponentsInChildren<MeshRenderer>(true).Length > 100);
            var lampish = building ? building.GetComponentsInChildren<Renderer>(true).Where(r => r.name.IndexOf("lamp", StringComparison.OrdinalIgnoreCase) >= 0 || r.name.IndexOf("light", StringComparison.OrdinalIgnoreCase) >= 0)
                .Select(r => new { path = PathOf(r.transform), r.enabled, center = A(r.bounds.center), size = A(r.bounds.size), mats = r.sharedMaterials.Select(m => m ? m.name : null).ToArray(),
                    emission = r.sharedMaterials.Select(m => m && m.HasProperty("_EmissionColor") ? (float[])new[] { m.GetColor("_EmissionColor").r, m.GetColor("_EmissionColor").g, m.GetColor("_EmissionColor").b } : null).ToArray() }).ToArray() : null;
            var lights = Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(l => l.type != LightType.Directional)
                .Select(l => new { path = PathOf(l.transform), type = l.type.ToString(), l.intensity, l.range, color = new[] { l.color.r, l.color.g, l.color.b }, shadows = l.shadows.ToString(), l.enabled, pos = A(l.transform.position), dist = Vector3.Distance(l.transform.position, centre) })
                .OrderBy(l => l.dist).ToArray();
            var circuit = Object.FindAnyObjectByType<CityLightCircuit>();
            var dir = Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(l => l.type == LightType.Directional)
                .Select(l => new { path = PathOf(l.transform), l.intensity, rot = A(l.transform.eulerAngles), shadows = l.shadows.ToString() }).ToArray();
            var display = GameObject.Find("Tool Exchange display and shutter");
            Write("inspect.json", new
            {
                utc = DateTime.UtcNow, buildingPos = building ? A(building.position) : null, buildingYaw = building ? building.eulerAngles.y : 0,
                displayBounds = display ? (object)display.GetComponentsInChildren<Renderer>(true).Select(r => new { r.name, center = A(r.bounds.center), size = A(r.bounds.size) }).ToArray() : null,
                lampish, totalPointSpotLights = lights.Length, lightsNearest40 = lights.Take(40).ToArray(), directional = dir,
                circuit = circuit ? new { practical = circuit.practicalLights.Length, nightOnly = circuit.nightOnlyLights.Length, circuit.fullLightDistance, circuit.culledLightDistance, circuit.shadowDistance, circuit.shadowStrengthThreshold, circuit.daytimeStrength,
                    emissive = circuit.emissiveMaterials.Where(m => m).Select(m => m.name).ToArray(), listedNearby = circuit.practicalLights.Where(l => l && Vector3.Distance(l.transform.position, centre) < 25).Select(l => PathOf(l.transform)).ToArray() } : null,
                ambient = new { mode = RenderSettings.ambientMode.ToString(), sky = A(new Vector3(RenderSettings.ambientSkyColor.r, RenderSettings.ambientSkyColor.g, RenderSettings.ambientSkyColor.b)), RenderSettings.ambientIntensity },
                sceneSha256 = System.BitConverter.ToString(System.Security.Cryptography.SHA256.Create().ComputeHash(File.ReadAllBytes(Path.Combine(Repo, "unity/AthenHill/" + ScenePath)))).Replace("-", "").ToLowerInvariant()
            });
        }
    }
}
#endif
