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

namespace AthenHill.Editor
{
    /// <summary>
    /// 26 September 2026 district retrofit (art/ward_retrofit_20260926): Blender-built service kit on the eight
    /// shop shells plus lore infill (processing-hall ruin, hydroponics bays, Nanofab 2, aquifer pump station,
    /// Warden watchtowers, Quantum Tube goods conduit, container homes, gate defences, overhead lines).
    /// One saved glTF prefab instance at the origin. COL_* nodes become box colliders, LIGHT_&lt;colour&gt;_* markers
    /// receive practical lights on the existing CityLightCircuit, "* Detail" meshes are distance-culled and
    /// decal/glow meshes cast no shadows. Existing shells, routes, colliders and gameplay roots are untouched.
    /// </summary>
    public static class WardRetrofitPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Glb = "Assets/AthenHill/Art/WardRetrofit/WardRetrofit.glb";
        const string RootName = "Ward district retrofit";
        const string ReviewCameras = "Ward retrofit review cameras";
        const string Evidence = "../evidence/district-retrofit/20260926/";

        [MenuItem("Athen Hill/District/Install district retrofit")]
        public static void InstallMenu()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (scene.GetRootGameObjects().Any(g => g.name == RootName))
                throw new InvalidOperationException("The district retrofit is already installed. Edit its prefab instance instead of reinstalling.");
            var record = Install(scene); AddReviewCameras(scene); Save(scene, record);
        }

        /// Batch entry point during authoring; replaces an earlier install of this pass only.
        public static void RunAll()
        {
            AssetDatabase.Refresh();
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var circuit = UnityEngine.Object.FindFirstObjectByType<CityLightCircuit>();
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == RootName || g.name == ReviewCameras).ToArray())
                UnityEngine.Object.DestroyImmediate(old);
            PruneCircuit(circuit);
            var record = Install(scene);
            AddReviewCameras(scene);
            Save(scene, record);
        }

        static void Save(Scene scene, object record)
        {
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "pass.json", JsonConvert.SerializeObject(record, Formatting.Indented));
        }

        static void PruneCircuit(CityLightCircuit circuit)
        {
            if (!circuit) return;
            var so = new SerializedObject(circuit);
            var list = so.FindProperty("practicalLights");
            for (int i = list.arraySize - 1; i >= 0; i--)
                if (!list.GetArrayElementAtIndex(i).objectReferenceValue) list.DeleteArrayElementAtIndex(i);
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        static object Install(Scene scene)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(Glb)
                ?? throw new InvalidOperationException("Import " + Glb + " first (art/ward_retrofit_20260926/build_retrofit.py).");
            var root = (GameObject)PrefabUtility.InstantiatePrefab(asset, scene);
            root.name = RootName;
            root.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

            var circuit = UnityEngine.Object.FindFirstObjectByType<CityLightCircuit>();
            var lights = new List<Light>();
            int colliders = 0, culled = 0;
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (t.name.StartsWith("COL_"))
                {
                    var filter = t.GetComponent<MeshFilter>();
                    if (filter && filter.sharedMesh)
                    {
                        var box = t.gameObject.AddComponent<BoxCollider>();
                        box.center = filter.sharedMesh.bounds.center; box.size = filter.sharedMesh.bounds.size;
                        colliders++;
                    }
                    var r = t.GetComponent<Renderer>(); if (r) r.enabled = false;
                }
                else if (t.name.StartsWith("LIGHT_"))
                {
                    var colour = t.name.Split('_')[1];
                    var go = new GameObject("Practical light " + colour);
                    go.transform.SetParent(t, false);
                    var light = go.AddComponent<Light>();
                    light.type = LightType.Point;
                    light.shadows = LightShadows.None;
                    switch (colour)
                    {
                        case "cyan": light.color = new Color(.4f, .86f, 1f); light.intensity = 1.3f; light.range = 4.5f; break;
                        case "red": light.color = new Color(1f, .18f, .12f); light.intensity = .7f; light.range = 2.5f; break;
                        default: light.color = new Color(1f, .68f, .4f); light.intensity = 1.5f; light.range = 5.5f; break;
                    }
                    lights.Add(light);
                }
            }
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (!r.enabled) continue;
                bool flatFx = r.name.EndsWith(" Decals") || r.name.EndsWith(" Glow");
                r.shadowCastingMode = flatFx ? ShadowCastingMode.Off : ShadowCastingMode.On;
                r.receiveShadows = true;
                if (r.name.EndsWith(" Detail"))
                {   // small fittings, props and bracing drop out beyond ~60 m (same convention as the market goods)
                    var lod = r.gameObject.AddComponent<LODGroup>();
                    lod.SetLODs(new[] { new LOD(.03f, new Renderer[] { r }) });
                    lod.fadeMode = LODFadeMode.None;
                    lod.RecalculateBounds();
                    culled++;
                }
            }
            if (circuit)
            {
                var so = new SerializedObject(circuit);
                var list = so.FindProperty("practicalLights");
                foreach (var light in lights)
                {
                    list.arraySize++;
                    list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = light;
                }
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            var groups = new List<object>();
            foreach (Transform g in root.transform)
                groups.Add(new
                {
                    name = g.name,
                    triangles = g.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh && !f.name.StartsWith("COL_")).Sum(f => (long)f.sharedMesh.triangles.Length / 3),
                    colliders = g.GetComponentsInChildren<BoxCollider>(true).Length,
                });
            return new
            {
                prefab = Glb, root = RootName, colliders, distanceCulledMeshes = culled, practicalLights = lights.Count,
                circuit = circuit ? circuit.name : null, groups,
                triangles = root.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh && !f.name.StartsWith("COL_")).Sum(f => (long)f.sharedMesh.triangles.Length / 3)
            };
        }

        /// Disabled cameras for the development View command (same convention as cam_gate etc.).
        static void AddReviewCameras(Scene scene)
        {
            var root = new GameObject(ReviewCameras);
            SceneManager.MoveGameObjectToScene(root, scene);
            foreach (var (name, eye, target) in Shots)
            {
                var go = new GameObject(name);
                go.transform.SetParent(root.transform, false);
                go.transform.position = eye; go.transform.LookAt(target);
                var cam = go.AddComponent<Camera>(); cam.fieldOfView = 60; cam.enabled = false;
            }
        }

        internal static readonly (string, Vector3, Vector3)[] Shots =
        {
            ("cam_retrofit_west_row", new Vector3(-8f, 1.7f, -24f), new Vector3(-20f, 3.5f, 5f)),
            ("cam_retrofit_east_row", new Vector3(8f, 1.7f, 24f), new Vector3(20f, 3.5f, -5f)),
            ("cam_retrofit_rear_lane", new Vector3(-30f, 1.7f, -26f), new Vector3(-26f, 4f, 10f)),
            ("cam_retrofit_ruin", new Vector3(26f, 1.8f, 18f), new Vector3(36f, 5f, 34f)),
            ("cam_retrofit_hydro", new Vector3(-27.5f, 1.8f, 21f), new Vector3(-36f, 2f, 32f)),
            ("cam_retrofit_fab", new Vector3(30f, 1.8f, -18f), new Vector3(36f, 4f, -32f)),
            ("cam_retrofit_aquifer", new Vector3(-26f, 2.4f, -17.5f), new Vector3(-39f, 1.4f, -26f)),
            ("cam_retrofit_conduit", new Vector3(6f, 2f, 28f), new Vector3(-12f, 4f, 42f)),
        };
    }
}
