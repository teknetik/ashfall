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

namespace AthenHill.Editor
{
    /// <summary>
    /// 30 September 2026: courtyard tree beds. Carl: "i think the other two trees in the courtyard should have similar
    /// enclosures to the large tree. move the trees if need be". The birches `birch 3` (by Salvage) and `birch 4b` (by
    /// Air + Water) get the hero tree's stone ring at street level and move north so the rings clear the porches.
    ///
    /// Source: art/courtyard_trees_20260930/author_tree_beds.py (Blender, on the shared masonry kit and the hill ring's
    /// helpers) -> Art/CourtyardTrees/Models/TreeBed_&lt;Key&gt;_LOD0/1.glb, TreeBedPlants_&lt;Key&gt;_LOD0/1.glb, tree-beds.json.
    /// Materials are shared, not copied: Masonry Lit stone and fittings from Art/VanguardHall/Materials, litter, root bark
    /// and the Poly Haven plants from Art/WardHill/Materials. Menu: Athen Hill → Courtyard trees → Build assets,
    /// Install tree beds (one time; moves the two trees), Add review cameras, Verify saved scene. The beds are not
    /// render-chunk sources; the trees keep their prefab links, LODGroups and trunk capsules.
    /// </summary>
    public static class CourtyardTreesPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/CourtyardTrees/";
        const string ModelDir = Root + "Models/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/CourtyardTrees/";
        const string HallMats = "Assets/AthenHill/Art/VanguardHall/Materials/";
        const string HillMats = "Assets/AthenHill/Art/WardHill/Materials/";
        const string Evidence = "../evidence/courtyard-trees/20260930/";
        public const string RootName = "Courtyard tree beds";
        const string CamRootName = "Courtyard tree bed review cameras";
        const float BedLod0 = .12f, BedLod1 = .01f, PlantsLod0 = .2f, PlantsLod1 = .06f;

        static JObject Record() => JObject.Parse(File.ReadAllText(ModelDir + "tree-beds.json"));
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static string PrefabPath(string key) => PrefabDir + "TreeBed_" + key + ".prefab";

        // ------------------------------------------------------------------ build
        [MenuItem("Athen Hill/Courtyard trees/Build assets")]
        public static string BuildAssets()
        {
            var rec = Record();
            foreach (var bed in rec["beds"].Children<JProperty>())
                foreach (var m in new[] { "TreeBed_", "TreeBedPlants_" })
                    for (int lod = 0; lod < 2; lod++)
                        AssetDatabase.ImportAsset(ModelDir + m + bed.Name + "_LOD" + lod + ".glb", ImportAssetOptions.ForceUpdate);
            var mats = Materials();
            Directory.CreateDirectory(PrefabDir);
            var missing = new HashSet<string>();
            foreach (var bed in rec["beds"].Children<JProperty>())
                BuildBedPrefab(bed.Name, (JObject)bed.Value, mats, missing);
            AssetDatabase.SaveAssets();
            return "built " + string.Join(", ", rec["beds"].Children<JProperty>().Select(p => p.Name)) +
                   "; unmapped materials: " + (missing.Count == 0 ? "none" : string.Join(", ", missing));
        }

        static Dictionary<string, Material> Materials()
        {
            var mats = new Dictionary<string, Material>();
            foreach (var n in new[] { "VH_Ashlar", "VH_AshlarRough", "VH_Mortar", "VH_PodiumSlab", "VH_Sand", "VH_Steel", "VH_Dark", "VH_Bronze", "VH_LampLens" })
                mats[n] = Load(HallMats + n + ".mat");
            foreach (var n in new[] { "WH_RingLitter", "WH_RootBark", "bark_debris_01", "celandine_01", "crystalline_iceplant", "dry_branches_medium_01",
                                      "grass_medium_01", "grass_medium_02", "namaqualand_stones_01", "weed_plant_02", "cheiridopsis_succulent",
                                      "cheiridopsis_succulent_flower" })
                mats[n] = Load(HillMats + n + ".mat");
            mats["RootBark"] = mats["WH_RootBark"];
            mats["weed_plant_02.001"] = mats["weed_plant_02"];
            return mats;
        }

        static Material Load(string path)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) throw new Exception("Shared material missing: " + path);
            return m;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m)) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        static List<Renderer> Instance(string glb, Transform parent, string name, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
            if (!model) throw new Exception("Model not imported: " + glb);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            inst.transform.SetParent(parent, false);
            inst.name = name;
            var rs = new List<Renderer>();
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
            {
                var slots = r.sharedMaterials;
                for (int i = 0; i < slots.Length; i++)
                {
                    var m = slots[i] ? Lookup(mats, slots[i].name) : null;
                    if (m) slots[i] = m; else missing.Add(r.name + ":" + (slots[i] ? slots[i].name : "null"));
                }
                r.sharedMaterials = slots;
                r.receiveShadows = true;
                if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
                rs.Add(r);
            }
            return rs;
        }

        // the stone course and coping cast (through their LOD1 meshes); apron, litter, fittings and roots only receive
        static bool Casts(string rendererName) => rendererName.Contains("_Ring_");

        static void BuildBedPrefab(string key, JObject rec, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var root = new GameObject("TreeBed_" + key);
            try
            {
                var levels = new List<LOD>();
                var lodRenderers = new List<Renderer>[2];
                foreach (var (lod, cut) in new[] { (0, BedLod0), (1, BedLod1) })
                {
                    var rs = Instance(ModelDir + $"TreeBed_{key}_LOD{lod}.glb", root.transform, "LOD" + lod, mats, missing);
                    foreach (var r in rs) r.shadowCastingMode = lod == 1 && Casts(r.name) ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    lodRenderers[lod] = rs;
                    levels.Add(new LOD(cut, rs.ToArray()));
                }
                var proxyRoot = new GameObject("Shadow proxy (LOD1 ring)"); proxyRoot.transform.SetParent(root.transform, false);
                var proxies = new List<Renderer>();
                foreach (var r1 in lodRenderers[1].Where(r => Casts(r.name)))
                {
                    var go = new GameObject(r1.name.Replace("_LOD1", "_Shadow"));
                    go.transform.SetParent(proxyRoot.transform, false);
                    go.transform.SetPositionAndRotation(r1.transform.position, r1.transform.rotation); go.transform.localScale = r1.transform.lossyScale;
                    go.AddComponent<MeshFilter>().sharedMesh = r1.GetComponent<MeshFilter>().sharedMesh;
                    var pr = go.AddComponent<MeshRenderer>(); pr.sharedMaterials = r1.sharedMaterials; pr.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                    proxies.Add(pr);
                }
                levels[0] = new LOD(levels[0].screenRelativeTransitionHeight, levels[0].renderers.Concat(proxies).ToArray());
                var group = root.AddComponent<LODGroup>(); group.SetLODs(levels.ToArray()); group.fadeMode = LODFadeMode.None; group.RecalculateBounds();

                // planting: its own LOD group; never static-batched (the ground-cover wind bends by height above the origin)
                var planting = new GameObject("Planting"); planting.transform.SetParent(root.transform, false);
                var plantLods = new List<Renderer>[2];
                for (int lod = 0; lod < 2; lod++)
                {
                    plantLods[lod] = Instance(ModelDir + $"TreeBedPlants_{key}_LOD{lod}.glb", planting.transform, "LOD" + lod, mats, missing);
                    foreach (var r in plantLods[lod]) r.shadowCastingMode = r.name.Contains("_cast") && lod == 0 ? ShadowCastingMode.On : ShadowCastingMode.Off;
                }
                var pg = planting.AddComponent<LODGroup>();
                pg.SetLODs(new[] { new LOD(PlantsLod0, plantLods[0].ToArray()), new LOD(PlantsLod1, plantLods[1].ToArray()) });
                pg.fadeMode = LODFadeMode.None; pg.RecalculateBounds();

                // colliders: the ring wall (annulus) and the soil inside it (so the player can step onto the coping and in)
                var cols = new GameObject("Colliders").transform; cols.SetParent(root.transform, false);
                var ring = rec["ring"];
                var ringGo = new GameObject("COL_TreeBedRing"); ringGo.transform.SetParent(cols, false);
                ringGo.AddComponent<MeshCollider>().sharedMesh = RingMesh($"TreeBed_{key}_Ring", (float)ring["inner"], (float)ring["outer"], (float)ring["bottom"], (float)ring["top"], 40, true);
                var soilGo = new GameObject("COL_TreeBedSoil"); soilGo.transform.SetParent(cols, false);
                var soilCol = soilGo.AddComponent<MeshCollider>();
                soilCol.sharedMesh = RingMesh($"TreeBed_{key}_Soil", 0f, (float)ring["inner"] + .02f, (float)ring["bottom"], (float)ring["soil_top"], 28, false);
                soilCol.convex = true;

                // uplights in the coping (bound to the Ward lighting clock on install)
                var lights = new GameObject("Practical lights").transform; lights.SetParent(root.transform, false);
                foreach (var spec in rec["lights"])
                {
                    var go = new GameObject((string)spec["name"]); go.transform.SetParent(lights, false);
                    var pos = V3(spec["pos"]); go.transform.localPosition = pos;
                    go.transform.localRotation = Quaternion.LookRotation(V3(spec["target"]) - pos, Vector3.up);
                    var l = go.AddComponent<Light>(); var c = spec["color"];
                    l.type = LightType.Spot; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                    l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"]; l.spotAngle = (float)spec["angle"]; l.innerSpotAngle = (float)spec["inner"];
                    l.shadows = LightShadows.None;
                }

                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    if (t.GetComponent<Light>()) continue;
                    var flags = StaticEditorFlags.OccludeeStatic;
                    if (!t.IsChildOf(planting.transform)) flags |= StaticEditorFlags.BatchingStatic;
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, flags);
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(key));
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        /// Annulus (inner > 0) or disc (inner = 0) prism saved as a mesh asset for collision (as the hill ring's).
        static Mesh RingMesh(string name, float inner, float outer, float y0, float y1, int seg, bool annulus)
        {
            Directory.CreateDirectory(Root + "Colliders");
            var path = Root + "Colliders/" + name + ".asset";
            var v = new List<Vector3>(); var t = new List<int>();
            for (int i = 0; i < seg; i++)
            {
                float a = Mathf.PI * 2 * i / seg; var d = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                v.Add(d * outer + Vector3.up * y0); v.Add(d * outer + Vector3.up * y1);
                v.Add(d * inner + Vector3.up * y0); v.Add(d * inner + Vector3.up * y1);
            }
            for (int i = 0; i < seg; i++)
            {
                int a = i * 4, b = ((i + 1) % seg) * 4;
                t.AddRange(new[] { a, b + 1, b, a, a + 1, b + 1 });
                t.AddRange(new[] { a + 1, a + 3, b + 3, a + 1, b + 3, b + 1 });
                if (annulus) t.AddRange(new[] { a + 2, b + 2, b + 3, a + 2, b + 3, a + 3 });
                t.AddRange(new[] { a, b, b + 2, a, b + 2, a + 2 });
            }
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            bool create = !mesh;
            if (create) mesh = new Mesh { name = name };
            mesh.Clear(); mesh.SetVertices(v); mesh.SetTriangles(t, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            if (create) AssetDatabase.CreateAsset(mesh, path); else EditorUtility.SetDirty(mesh);
            return mesh;
        }

        // ------------------------------------------------------------------ install
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        [MenuItem("Athen Hill/Courtyard trees/Install tree beds (one time)")]
        public static string Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            if (scene.GetRootGameObjects().Any(g => g.name == RootName))
                throw new Exception("The courtyard tree beds are already installed; edit them in place (move a bed with its tree).");
            Directory.CreateDirectory(Evidence + "rollback");
            File.Copy(ScenePath, Evidence + "rollback/before-tree-beds.unity", true);
            var rec = Record();
            var record = new Dictionary<string, object>();
            var root = new GameObject(RootName);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var moved = new List<object>();
            var lamps = new List<Light>();
            foreach (var bed in rec["beds"].Children<JProperty>())
            {
                var b = (JObject)bed.Value;
                var treeName = (string)b["tree"];
                var tree = scene.GetRootGameObjects().FirstOrDefault(g => g.name == treeName);
                if (!tree) throw new Exception("Tree root not found: " + treeName);
                var p = b["position"];
                var before = tree.transform.position;
                var target = new Vector3((float)p[0], before.y, (float)p[1]);
                Undo.RecordObject(tree.transform, "Move courtyard tree");
                tree.transform.position = target;
                if (PrefabUtility.IsPartOfPrefabInstance(tree)) PrefabUtility.RecordPrefabInstancePropertyModifications(tree.transform);
                moved.Add(new { tree = treeName, from = new[] { before.x, before.y, before.z }, to = new[] { target.x, target.y, target.z } });

                var inst = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(bed.Name)), scene);
                inst.name = "Tree bed " + treeName;
                inst.transform.SetParent(root.transform, false);
                inst.transform.SetPositionAndRotation(new Vector3(target.x, 0f, target.z), Quaternion.identity);
                lamps.AddRange(inst.GetComponentsInChildren<Light>(true));
            }
            record["moved"] = moved;
            if (circuit)
            {
                circuit.practicalLights = circuit.practicalLights.Where(l => l).Concat(lamps).Distinct().ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l).Concat(lamps).Distinct().ToArray();
                EditorUtility.SetDirty(circuit);
            }
            record["lights"] = lamps.Select(l => PathOf(l.transform)).ToArray();
            record["lightCircuitFound"] = circuit != null;
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        // ------------------------------------------------------------------ review cameras (player height, the tool's lookbook)
        static readonly (string name, string tree, Vector3 offset, Vector3 look, float fov)[] ReviewViews =
        {
            ("cam_tree_bed_birch4b", "birch 4b", new Vector3(5.2f, 1.62f, 2.6f), new Vector3(0f, 1.1f, 0f), 60),
            ("cam_tree_bed_birch4b_seat", "birch 4b", new Vector3(2.4f, 1.62f, -1.6f), new Vector3(-0.4f, 0.3f, 0.4f), 60),
            ("cam_tree_bed_birch4b_avenue", "birch 4b", new Vector3(9.5f, 1.62f, -6.5f), new Vector3(-1f, 2.5f, 0.5f), 60),
            ("cam_tree_bed_birch3", "birch 3", new Vector3(4.6f, 1.62f, -2.8f), new Vector3(0f, 1.1f, 0f), 60),
            ("cam_tree_bed_birch3_seat", "birch 3", new Vector3(-1.4f, 1.62f, 2.5f), new Vector3(0.3f, 0.3f, -0.2f), 60),
        };

        [MenuItem("Athen Hill/Courtyard trees/Add review cameras")]
        public static void ReviewCameras()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath);
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
        }

        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            foreach (var (name, treeName, offset, look, fov) in ReviewViews)
            {
                var tree = scene.GetRootGameObjects().First(g => g.name == treeName).transform.position;
                var pos = tree + offset; var target = tree + look;
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var c = go.AddComponent<Camera>(); c.enabled = false; c.fieldOfView = fov; c.nearClipPlane = .05f;
            }
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Courtyard trees/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var rec = Record();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            foreach (var bed in rec["beds"].Children<JProperty>())
            {
                var b = (JObject)bed.Value;
                var treeName = (string)b["tree"];
                var tree = scene.GetRootGameObjects().FirstOrDefault(g => g.name == treeName);
                var inst = root ? root.transform.Find("Tree bed " + treeName) : null;
                var tp = tree ? tree.transform.position : Vector3.zero;
                r[treeName] = new
                {
                    treePosition = new[] { tp.x, tp.y, tp.z },
                    treeCentredOnBed = inst && tree && Vector2.Distance(new Vector2(tp.x, tp.z), new Vector2(inst.position.x, inst.position.z)) < .01f,
                    prefabLinked = inst && PrefabUtility.IsPartOfPrefabInstance(inst.gameObject),
                    lods = inst ? inst.GetComponentsInChildren<LODGroup>(true).Select(g => new
                    {
                        g.name,
                        levels = g.GetLODs().Select(l => new
                        {
                            l.screenRelativeTransitionHeight,
                            renderers = l.renderers.Length,
                            triangles = l.renderers.Where(x => x && x.GetComponent<MeshFilter>()).Sum(x => { var m = x.GetComponent<MeshFilter>().sharedMesh; return Enumerable.Range(0, m.subMeshCount).Sum(s => (long)m.GetIndexCount(s) / 3); })
                        }).ToArray()
                    }).ToArray() : null,
                    colliders = inst ? inst.GetComponentsInChildren<Collider>(true).Select(c => c.name).ToArray() : null,
                    missingMaterials = inst ? inst.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => !m)) : -1,
                    materials = inst ? inst.GetComponentsInChildren<Renderer>(true).SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => m.name + " (" + m.shader.name + ")").Distinct().OrderBy(x => x).ToArray() : null,
                    trunkCollider = tree && tree.GetComponent<Collider>() ? tree.GetComponent<Collider>().bounds.center.ToString() : "none",
                };
            }
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            r["circuitLights"] = root && circuit ? circuit.practicalLights.Count(l => l && l.transform.IsChildOf(root.transform)) : 0;
            r["reviewCameras"] = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName)?.transform.childCount ?? 0;
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        /// Re-applies the light specs from tree-beds.json to the existing prefabs' lights in place (same objects, so the
        /// Ward lighting clock bindings of the scene instances survive; a full prefab rebuild would re-create them).
        [MenuItem("Athen Hill/Courtyard trees/Retune uplights (keeps clock bindings)")]
        public static string RetuneLights()
        {
            var rec = Record();
            var log = new List<string>();
            foreach (var bed in rec["beds"].Children<JProperty>())
            {
                var path = PrefabPath(bed.Name);
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    foreach (var spec in bed.Value["lights"])
                    {
                        var t = root.transform.Find("Practical lights/" + (string)spec["name"]);
                        var l = t ? t.GetComponent<Light>() : null;
                        if (!l) { log.Add(bed.Name + ": missing " + (string)spec["name"]); continue; }
                        var pos = V3(spec["pos"]);
                        t.localPosition = pos; t.localRotation = Quaternion.LookRotation(V3(spec["target"]) - pos, Vector3.up);
                        l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"];
                        l.spotAngle = (float)spec["angle"]; l.innerSpotAngle = (float)spec["inner"];
                        log.Add($"{bed.Name}/{l.name}: {l.intensity} / {l.range} m / {l.spotAngle} deg");
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return string.Join("\n", log);
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.CourtyardTreesPass.RunBatch --steps build,install,verify
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "build" };
            try
            {
                foreach (var s in steps)
                {
                    var result = s switch
                    {
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "cameras" => Wrap(ReviewCameras),
                        "verify" => Verify(),
                        "retune" => RetuneLights(),
                        _ => throw new Exception("unknown step " + s),
                    };
                    Debug.Log("CourtyardTreesPass " + s + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        static string Wrap(Action a) { a(); return "ok"; }
    }
}
