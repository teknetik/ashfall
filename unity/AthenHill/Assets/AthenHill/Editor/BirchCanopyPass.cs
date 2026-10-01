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

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: birch canopy and bed uplights (art-direction review item 11 and the section-4 uplight defect).
    /// The courtyard birches (`birch 3`, `birch 4b`, TreesBundleB prefab instances in the courtyard-tree stone beds) get
    /// a canopy pass: baked mesh copies (crown AO and per-card hue jitter in vertex colour, crown-volume normals) on the
    /// Athen Hill/Ward Canopy shader (wind, leaf transmission), and the bed uplights are re-aimed/retuned with their own lens
    /// material. Sources and run order: art/birch_canopy_20261001/README.md. Evidence: unity/evidence/birch-canopy/20261001.
    /// Batch: -executeMethod AthenHill.Editor.BirchCanopyPass.RunBatch --steps survey[,...] [--out dir].
    /// </summary>
    public static class BirchCanopyPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/birch-canopy/20261001/";
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
        static readonly string[] Trees = { "birch 3", "birch 4b" };
        const string BedRoot = "Courtyard tree beds";

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] F3(Vector3 v) => new[] { (float)Math.Round(v.x, 4), (float)Math.Round(v.y, 4), (float)Math.Round(v.z, 4) };

        static void Save(string name, object o)
        {
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + name, JsonConvert.SerializeObject(o, Formatting.Indented, new JsonSerializerSettings { ReferenceLoopHandling = ReferenceLoopHandling.Ignore }));
        }

        static UnityEngine.SceneManagement.Scene OpenScene()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (scene.path != ScenePath) scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            return scene;
        }

        static GameObject Root(UnityEngine.SceneManagement.Scene scene, string name) => scene.GetRootGameObjects().FirstOrDefault(g => g.name == name);

        // ------------------------------------------------------------------ survey (read-only, -nographics)
        public static string Survey()
        {
            var scene = OpenScene();
            var r = new Dictionary<string, object>();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var practical = new HashSet<Light>(circuit ? circuit.practicalLights.Where(l => l) : Enumerable.Empty<Light>());
            var nightOnly = new HashSet<Light>(circuit ? circuit.nightOnlyLights.Where(l => l) : Enumerable.Empty<Light>());
            r["circuit"] = circuit ? new
            {
                practical = circuit.practicalLights.Length, nightOnly = circuit.nightOnlyLights.Length, circuit.fullLightDistance,
                circuit.culledLightDistance, circuit.shadowDistance, circuit.nightOnlyThreshold, circuit.daytimeStrength,
                emissive = circuit.emissiveMaterials.Where(m => m).Select(m => m.name).ToArray(),
            } : null;

            foreach (var treeName in Trees)
            {
                var tree = Root(scene, treeName);
                if (!tree) { r[treeName] = "missing"; continue; }
                var lg = tree.GetComponent<LODGroup>();
                var rows = new List<object>();
                foreach (var mr in tree.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var mf = mr.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null;
                    if (!mesh) { rows.Add(new { mr.name, mesh = "none" }); continue; }
                    var subs = new List<object>();
                    for (int s = 0; s < mesh.subMeshCount; s++)
                    {
                        var tris = mesh.GetTriangles(s);
                        var mat = s < mr.sharedMaterials.Length ? mr.sharedMaterials[s] : null;
                        subs.Add(new
                        {
                            index = s, material = mat ? mat.name : null, shader = mat ? mat.shader.name : null,
                            matPath = mat ? AssetDatabase.GetAssetPath(mat) : null,
                            triangles = tris.Length / 3, cards = Components(tris), doubleSidedPairs = MirroredPairs(mesh, tris),
                            bounds = SubBounds(mesh, tris),
                        });
                    }
                    rows.Add(new
                    {
                        mr.name, mesh = mesh.name, asset = AssetDatabase.GetAssetPath(mesh), mesh.vertexCount, mesh.isReadable,
                        hasColors = mesh.HasVertexAttribute(VertexAttribute.Color), hasTangents = mesh.HasVertexAttribute(VertexAttribute.Tangent),
                        uv2 = mesh.HasVertexAttribute(VertexAttribute.TexCoord1), mesh.indexFormat,
                        shadows = mr.shadowCastingMode.ToString(), mr.receiveShadows, motion = mr.motionVectorGenerationMode.ToString(),
                        lossyScale = F3(mr.transform.lossyScale), localPos = F3(mr.transform.localPosition), localRot = F3(mr.transform.localEulerAngles),
                        subs,
                    });
                }
                var cols = tree.GetComponents<Collider>().Select(c => c.GetType().Name + " " + F3(c.bounds.center).Aggregate("", (a, b) => a + b + " ")).ToArray();
                r[treeName] = new
                {
                    position = F3(tree.transform.position), rotation = F3(tree.transform.eulerAngles), scale = F3(tree.transform.localScale),
                    prefab = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(tree),
                    overrides = PrefabUtility.GetPropertyModifications(tree)?.Select(m => (m.target ? m.target.name + ":" : "") + m.propertyPath + "=" + m.value + (m.objectReference ? " ref " + m.objectReference.name : "")).ToArray(),
                    lods = lg ? lg.GetLODs().Select(l => new { l.screenRelativeTransitionHeight, renderers = l.renderers.Where(x => x).Select(x => x.name).ToArray() }).ToArray() : null,
                    lodSize = lg ? lg.size : 0, lodFade = lg ? lg.fadeMode.ToString() : null,
                    colliders = cols, renderers = rows,
                };
            }

            // bed and hill uplights, and their lenses
            var lights = new List<object>();
            foreach (var rootName in new[] { BedRoot, "Ward hill" })
            {
                var root = Root(scene, rootName); if (!root) continue;
                foreach (var l in root.GetComponentsInChildren<Light>(true))
                    lights.Add(new
                    {
                        path = PathOf(l.transform), type = l.type.ToString(), pos = F3(l.transform.position), fwd = F3(l.transform.forward), l.intensity, l.range,
                        l.spotAngle, l.innerSpotAngle, color = new[] { l.color.r, l.color.g, l.color.b }, renderMode = l.renderMode.ToString(),
                        shadows = l.shadows.ToString(), cookie = l.cookie ? l.cookie.name : null, l.enabled, active = l.gameObject.activeInHierarchy,
                        practical = practical.Contains(l), nightOnly = nightOnly.Contains(l), l.bounceIntensity, mode = l.lightmapBakeType.ToString(),
                        prefabAsset = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(l.gameObject),
                    });
            }
            r["uplights"] = lights;
            var lens = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/VanguardHall/Materials/VH_LampLens.mat");
            if (lens)
                r["VH_LampLens"] = new
                {
                    shader = lens.shader.name, emission = lens.GetColor("_EmissionColor").ToString("F3"), baseColor = lens.GetColor("_BaseColor").ToString("F3"),
                    keywords = lens.shaderKeywords, gi = lens.globalIlluminationFlags.ToString(),
                    users = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include)
                        .Where(x => x.sharedMaterials.Contains(lens)).Select(x => PathOf(x.transform) + (x.gameObject.activeInHierarchy ? "" : " (inactive)")).ToArray(),
                };

            // the local light budget around each bed: enabled, active, non-directional lights by distance
            var all = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude).Where(l => l.enabled).ToArray();
            r["lightsInScene"] = new
            {
                enabledActive = all.Length,
                directional = all.Count(l => l.type == LightType.Directional),
                local = all.Count(l => l.type != LightType.Directional),
                practicalOnCircuit = all.Count(l => practical.Contains(l)),
            };
            var near = new Dictionary<string, object>();
            foreach (var treeName in Trees)
            {
                var tree = Root(scene, treeName); if (!tree) continue;
                var p = tree.transform.position;
                near[treeName] = new[] { 10f, 20f, 30f, 45f, 60f }.ToDictionary(d => "within" + d.ToString(Inv) + "m",
                    d => all.Count(l => l.type != LightType.Directional && Vector3.Distance(l.transform.position, p) - l.range < d));
            }
            r["localLightsReachingNear"] = near;
            Save("survey.json", r);
            return "survey.json written";
        }

        static int Components(int[] tris)
        {
            var parent = new Dictionary<int, int>();
            int Find(int a) { while (parent[a] != a) { parent[a] = parent[parent[a]]; a = parent[a]; } return a; }
            foreach (var v in tris) if (!parent.ContainsKey(v)) parent[v] = v;
            for (int i = 0; i < tris.Length; i += 3)
            {
                int a = Find(tris[i]), b = Find(tris[i + 1]), c = Find(tris[i + 2]);
                parent[b] = a; parent[Find(c)] = a;
            }
            return parent.Keys.ToList().Select(Find).Distinct().Count();
        }

        /// triangles whose three positions match another triangle's in reverse winding (double-sided cards)
        static int MirroredPairs(Mesh mesh, int[] tris)
        {
            var v = mesh.vertices;
            string K(Vector3 p) => $"{Mathf.RoundToInt(p.x * 1000)},{Mathf.RoundToInt(p.y * 1000)},{Mathf.RoundToInt(p.z * 1000)}";
            var set = new HashSet<string>();
            for (int i = 0; i < tris.Length; i += 3) set.Add(K(v[tris[i]]) + "|" + K(v[tris[i + 1]]) + "|" + K(v[tris[i + 2]]));
            int n = 0;
            for (int i = 0; i < tris.Length; i += 3)
            {
                string a = K(v[tris[i]]), b = K(v[tris[i + 1]]), c = K(v[tris[i + 2]]);
                if (set.Contains(a + "|" + c + "|" + b) || set.Contains(c + "|" + b + "|" + a) || set.Contains(b + "|" + a + "|" + c)) n++;
            }
            return n;
        }

        static object SubBounds(Mesh mesh, int[] tris)
        {
            if (tris.Length == 0) return null;
            var v = mesh.vertices;
            var b = new Bounds(v[tris[0]], Vector3.zero);
            foreach (var i in tris) b.Encapsulate(v[i]);
            return new { center = F3(b.center), size = F3(b.size) };
        }

        // ------------------------------------------------------------------ review cameras (player height, relative to each tree root)
        public const string CamRootName = "Birch canopy review cameras";
        static readonly (string name, string tree, Vector3 offset, Vector3 look, float fov)[] ReviewViews =
        {
            ("cam_bc_4b_crown", "birch 4b", new Vector3(6.34f, 1.62f, 13.85f), new Vector3(-0.26f, 8f, 0.65f), 60),
            ("cam_bc_4b_under", "birch 4b", new Vector3(2.6f, 1.62f, 1.4f), new Vector3(-0.3f, 7.5f, 0.4f), 60),
            ("cam_bc_4b_bed", "birch 4b", new Vector3(3.74f, 1.62f, 1.25f), new Vector3(0f, 2.9f, 0f), 60),
            ("cam_bc_3_crown", "birch 3", new Vector3(11.1f, 1.62f, -4.55f), new Vector3(0f, 5.5f, -0.4f), 60),
            ("cam_bc_3_bed", "birch 3", new Vector3(3.4f, 1.62f, 2.05f), new Vector3(0f, 2.9f, 0f), 60),
        };

        static (Vector3 pos, Vector3 target, float fov)? ViewOf(string name)
        {
            var v = ReviewViews.FirstOrDefault(x => x.name == name);
            if (v.name == null) return null;
            var tree = GameObject.Find(v.tree);
            if (!tree) return null;
            var t = tree.transform.position;
            return (t + v.offset, t + v.look, v.fov);
        }

        public static string Cameras()
        {
            var scene = OpenScene();
            var old = Root(scene, CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            foreach (var v in ReviewViews)
            {
                var view = ViewOf(v.name).Value;
                var go = new GameObject(v.name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(view.pos, Quaternion.LookRotation(view.target - view.pos, Vector3.up));
                var c = go.AddComponent<Camera>(); c.enabled = false; c.fieldOfView = view.fov; c.nearClipPlane = .05f;
            }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return string.Join(", ", ReviewViews.Select(v => v.name));
        }

        // ------------------------------------------------------------------ editor captures with the light clock emulated (graphics)
        static int capturedThisRun;

        /// spec: capture:HOUR:cam+cam (scene cameras or name:x,y,z:tx,ty,tz:fov). The lighting clock is emulated the way
        /// CityLightCircuit runs it in the player (practical lights x strength x distance weight from the camera as the
        /// viewer, night-only lights off below the threshold, emissive materials x strength); a 32-light culling probe
        /// (the OpenGL Core Forward+ limit) records which local lights survive for each view. Nothing is saved.
        public static string Capture(string spec, string outDir)
        {
            var parts = spec.Split(new[] { ':' }, 3);
            float hour = float.Parse(parts[1], Inv);
            var cams = parts[2].Split('+');
            capturedThisRun += cams.Length;
            if (capturedThisRun > 6) throw new Exception("at most 6 cameras per Unity run (VRAM rule)");
            OpenScene();
            // review views not yet in the scene become explicit name:pos:target:fov specs for DuskStartPass.Preview
            string F(Vector3 p) => string.Join(",", new[] { p.x, p.y, p.z }.Select(f => f.ToString("0.###", Inv)));
            cams = cams.Select(c =>
            {
                if (GameObject.Find(c)) return c;
                var v = ViewOf(c);
                return v == null ? c : $"{c}:{F(v.Value.pos)}:{F(v.Value.target)}:{v.Value.fov.ToString(Inv)}";
            }).ToArray();
            ShaderUtil.allowAsyncCompilation = false;
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            float strength = Mathf.Lerp(circuit.daytimeStrength, 1, clock.profile.Evaluate(hour).lampStrength);
            var practical = circuit.practicalLights.Where(l => l).Distinct().ToArray();
            var nightOnly = new HashSet<Light>(circuit.nightOnlyLights.Where(l => l));
            var saved = practical.Select(l => (l, l.intensity, l.enabled)).ToArray();
            var emissive = circuit.emissiveMaterials.Where(m => m && m.HasProperty("_EmissionColor")).Distinct().ToArray();
            var savedE = emissive.Select(m => (m, m.GetColor("_EmissionColor"))).ToArray();
            var probes = new List<object>();
            string current = null;
            void Probe(ScriptableRenderContext ctx, Camera cam)
            {
                if (cam.name != "__dusk" || current == null) return;
                try
                {
                    if (!cam.TryGetCullingParameters(out var p)) return;
                    p.maximumVisibleLights = 0xFFFF;
                    var all = ctx.Cull(ref p).visibleLights.ToArray().Select(v => v.light).ToList();
                    p.maximumVisibleLights = 32;
                    var kept = new HashSet<Light>(ctx.Cull(ref p).visibleLights.ToArray().Select(v => v.light));
                    var watch = all.Where(l => l && (l.transform.root.name == BedRoot || l.transform.root.name == "Ward hill")).ToList();
                    // does LightRenderMode.ForcePixel ("Important") move the bed uplights into the kept set?
                    var beds = all.Where(l => l && l.transform.root.name == BedRoot && l.type == LightType.Spot).ToList();
                    var modes = beds.Select(l => l.renderMode).ToList();
                    foreach (var l in beds) l.renderMode = LightRenderMode.ForcePixel;
                    var keptImportant = new HashSet<Light>(ctx.Cull(ref p).visibleLights.ToArray().Select(v => v.light));
                    for (int k = 0; k < beds.Count; k++) beds[k].renderMode = modes[k];
                    probes.Add(new
                    {
                        view = current, hour, visible = all.Count, keptAt32 = kept.Count,
                        order = all.Select((l, i) => new
                        {
                            i, name = l ? PathOf(l.transform) : "(particle)", type = l ? l.type.ToString() : null, kept = kept.Contains(l),
                            dist = l ? (float)Math.Round(Vector3.Distance(l.transform.position, cam.transform.position), 1) : 0,
                            intensity = l ? (float)Math.Round(l.intensity, 3) : 0, range = l ? l.range : 0, renderMode = l ? l.renderMode.ToString() : null,
                        }).ToArray(),
                        treeAndHillUplights = watch.Select(l => PathOf(l.transform) + (kept.Contains(l) ? " KEPT" : " DROPPED")).ToArray(),
                        bedUplightsKeptWhenImportant = beds.Select(l => PathOf(l.transform) + (keptImportant.Contains(l) ? " KEPT" : " DROPPED")).ToArray(),
                    });
                }
                catch (Exception e) { probes.Add(new { view = current, error = e.Message }); }
            }
            RenderPipelineManager.beginCameraRendering += Probe;
            var log = new List<string>();
            try
            {
                foreach (var m in emissive) m.SetColor("_EmissionColor", savedE.First(x => x.m == m).Item2 * strength);
                bool warmed = false;
                foreach (var c in cams)
                {
                    var name = c.Split(':')[0];
                    Vector3 viewer;
                    if (c.Contains(':')) { var a = c.Split(':')[1].Split(',').Select(s => float.Parse(s, Inv)).ToArray(); viewer = new Vector3(a[0], a[1], a[2]); }
                    else { var go = GameObject.Find(c); if (!go) { log.Add("missing " + c); continue; } viewer = go.transform.position; }
                    foreach (var (l, intensity, enabled) in saved)
                    {
                        float d = Vector3.Distance(viewer, l.transform.position);
                        float w = 1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(circuit.fullLightDistance, Mathf.Max(circuit.fullLightDistance + 1, circuit.culledLightDistance), d));
                        l.intensity = intensity * strength * w;
                        l.enabled = enabled && l.intensity > .002f && (strength >= circuit.nightOnlyThreshold || !nightOnly.Contains(l));
                    }
                    if (!warmed) { current = null; DuskStartPass.Preview(hour, Path.Combine(outDir, "warmup"), c); warmed = true; }
                    current = name;
                    log.Add(DuskStartPass.Preview(hour, outDir, c).Trim());
                }
            }
            finally
            {
                RenderPipelineManager.beginCameraRendering -= Probe;
                foreach (var (l, intensity, enabled) in saved) { l.intensity = intensity; l.enabled = enabled; }
                foreach (var (m, e) in savedE) m.SetColor("_EmissionColor", e);
            }
            Directory.CreateDirectory(outDir);
            File.WriteAllText(Path.Combine(outDir, $"lightcull-{hour.ToString("00.0", Inv)}.json"), JsonConvert.SerializeObject(probes, Formatting.Indented));
            return $"strength {strength:0.00}; " + string.Join(", ", log);
        }

        // ------------------------------------------------------------------ paths and tune
        const string ShaderPath = "Assets/AthenHill/Shaders/WardCanopy/WardCanopy.shader";
        const string ArtDir = "Assets/AthenHill/Art/BirchCanopy/";
        const string MatDir = ArtDir + "Materials/";
        const string MeshDir = ArtDir + "Meshes/";
        const string ArtSrc = "../../art/birch_canopy_20261001/";
        const string TuneFile = ArtSrc + "canopy-tune.json";
        const string OriginalsFile = ArtSrc + "originals.json";
        const string VendorMats = "Assets/TreesBundleB/Materials/universal/birch/";
        const string LensPath = MatDir + "BC_UplightLens.mat";
        const string HallLens = "Assets/AthenHill/Art/VanguardHall/Materials/VH_LampLens.mat";
        static readonly Dictionary<string, string> BedPrefabs = new Dictionary<string, string>
        {
            ["birch 3"] = "Assets/AthenHill/Prefabs/CourtyardTrees/TreeBed_Birch3.prefab",
            ["birch 4b"] = "Assets/AthenHill/Prefabs/CourtyardTrees/TreeBed_Birch4b.prefab",
        };

        static JObject Tune() => JObject.Parse(File.ReadAllText(TuneFile));
        static string Key(string tree) => (string)Tune()["trees"][tree]["key"];

        /// vendor material name -> our material name for one tree ("bark 1" -> BC_Birch4b_Bark1, the leaf -> BC_Birch4b_Leaf)
        static string OurMaterialName(string tree, string vendorName, JObject tune)
        {
            var key = (string)tune["trees"][tree]["key"];
            vendorName = vendorName.Replace(" (Instance)", "");
            if (vendorName == (string)tune["trees"][tree]["leafMaterial"]) return $"BC_{key}_Leaf";
            if (vendorName.StartsWith("bark ")) return $"BC_{key}_Bark{vendorName.Substring(5)}";
            return null;
        }

        static Material LoadVendor(string name)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(VendorMats + name + ".mat");
            if (!m) throw new Exception("vendor material missing: " + name);
            return m;
        }

        static void SetProps(Material m, JObject props)
        {
            foreach (var p in props.Properties())
            {
                if (p.Value.Type == JTokenType.Object) continue;
                if (!m.HasProperty(p.Name)) throw new Exception(m.name + " has no property " + p.Name);
                if (p.Value.Type == JTokenType.Array) { var a = p.Value.Select(v => (float)v).ToArray(); m.SetColor(p.Name, new Color(a[0], a[1], a[2], a.Length > 3 ? a[3] : 1)); }
                else m.SetFloat(p.Name, (float)p.Value);
            }
        }

        static JObject Merge(params JToken[] parts)
        {
            var o = new JObject();
            foreach (var part in parts) if (part is JObject j) foreach (var p in j.Properties()) if (p.Value.Type != JTokenType.Object) o[p.Name] = p.Value;
            return o;
        }

        /// Creates or updates (same GUID) the six canopy materials from the vendor textures and the tune file.
        static List<string> Materials(JObject tune)
        {
            var log = new List<string>();
            Directory.CreateDirectory(MatDir);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            if (!shader) throw new Exception("shader not imported: " + ShaderPath);
            if (ShaderUtil.ShaderHasError(shader)) throw new Exception("shader has errors: " + ShaderPath);
            var green = LoadVendor("leaf"); var yellow = LoadVendor("leaf y");
            foreach (var tree in Trees)
            {
                var key = (string)tune["trees"][tree]["key"];
                var per = (JObject)tune["materials"]["perTree"][tree];
                var vendorNames = tree == "birch 4b" ? new[] { "bark 1", "bark 2", (string)tune["trees"][tree]["leafMaterial"] } : new[] { "bark 2", "bark 3", (string)tune["trees"][tree]["leafMaterial"] };
                foreach (var vn in vendorNames)
                {
                    var name = OurMaterialName(tree, vn, tune);
                    var path = MatDir + name + ".mat";
                    var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                    bool create = !m;
                    if (create) m = new Material(shader) { name = name }; else m.shader = shader;
                    bool leaf = name.EndsWith("_Leaf");
                    var src = leaf ? green : LoadVendor(vn);
                    m.SetTexture("_BaseMap", src.GetTexture("_BaseMap"));
                    m.SetTexture("_BumpMap", src.GetTexture("_BumpMap"));
                    m.SetTexture("_MetallicGlossMap", null);
                    m.SetTexture("_WardSeasonMap", leaf ? yellow.GetTexture("_BaseMap") : null);
                    SetProps(m, Merge(tune["materials"][leaf ? "leaf" : "bark"], per, per[leaf ? "leaf" : "bark"]));
                    m.SetFloat("_WorkflowMode", 1); m.SetFloat("_Surface", 0); m.SetFloat("_Cull", 2);
                    m.SetFloat("_AlphaClip", leaf ? 1 : 0); m.SetFloat("_AlphaToMask", leaf ? 1 : 0);
                    m.SetFloat("_SrcBlend", 1); m.SetFloat("_DstBlend", 0); m.SetFloat("_ZWrite", 1);
                    m.shaderKeywords = leaf ? new[] { "_NORMALMAP", "_ALPHATEST_ON" } : new[] { "_NORMALMAP" };
                    m.SetOverrideTag("RenderType", leaf ? "TransparentCutout" : "Opaque");
                    m.renderQueue = leaf ? (int)RenderQueue.AlphaTest : (int)RenderQueue.Geometry;
                    m.enableInstancing = true;
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack;
                    if (create) AssetDatabase.CreateAsset(m, path); else EditorUtility.SetDirty(m);
                    log.Add((create ? "created " : "updated ") + path);
                }
            }
            // the bed uplight lens: its own copy of the hall lens, so VH_LampLens (hill uplights) stays as it is
            var lensSpec = (JObject)tune["lens"];
            var lens = AssetDatabase.LoadAssetAtPath<Material>(LensPath);
            if (!lens)
            {
                lens = new Material(AssetDatabase.LoadAssetAtPath<Material>(HallLens)) { name = "BC_UplightLens" };
                AssetDatabase.CreateAsset(lens, LensPath); log.Add("created " + LensPath);
            }
            SetProps(lens, new JObject(lensSpec.Properties().Where(p => p.Name.StartsWith("_"))));
            lens.EnableKeyword("_EMISSION"); lens.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            EditorUtility.SetDirty(lens);
            AssetDatabase.SaveAssets();
            return log;
        }

        // ------------------------------------------------------------------ canopy bake (crown occlusion, volume normals, per-card data)
        sealed class Grid
        {
            public Vector3 min; public float cell; public int nx, ny, nz; public float[] d;
            public Grid(Bounds b, float cell)
            {
                this.cell = cell; min = b.min;
                nx = Mathf.CeilToInt(b.size.x / cell) + 1; ny = Mathf.CeilToInt(b.size.y / cell) + 1; nz = Mathf.CeilToInt(b.size.z / cell) + 1;
                d = new float[nx * ny * nz];
            }
            public Grid Clone() { var g = (Grid)MemberwiseClone(); g.d = (float[])d.Clone(); return g; }
            int I(int x, int y, int z) => (z * ny + y) * nx + x;
            public void Add(Vector3 p, float v)
            {
                var q = (p - min) / cell; int x = Mathf.FloorToInt(q.x), y = Mathf.FloorToInt(q.y), z = Mathf.FloorToInt(q.z);
                if (x < 0 || y < 0 || z < 0 || x >= nx || y >= ny || z >= nz) return;
                d[I(x, y, z)] += v;
            }
            public bool Inside(Vector3 p) { var q = (p - min) / cell; return q.x >= 0 && q.y >= 0 && q.z >= 0 && q.x < nx - 1 && q.y < ny - 1 && q.z < nz - 1; }
            public float Sample(Vector3 p)
            {
                var q = (p - min) / cell - new Vector3(.5f, .5f, .5f);
                int x = Mathf.FloorToInt(q.x), y = Mathf.FloorToInt(q.y), z = Mathf.FloorToInt(q.z);
                float fx = q.x - x, fy = q.y - y, fz = q.z - z, s = 0;
                for (int k = 0; k < 8; k++)
                {
                    int xi = x + (k & 1), yi = y + ((k >> 1) & 1), zi = z + ((k >> 2) & 1);
                    if (xi < 0 || yi < 0 || zi < 0 || xi >= nx || yi >= ny || zi >= nz) continue;
                    float w = ((k & 1) != 0 ? fx : 1 - fx) * (((k >> 1) & 1) != 0 ? fy : 1 - fy) * (((k >> 2) & 1) != 0 ? fz : 1 - fz);
                    s += w * d[I(xi, yi, zi)];
                }
                return s;
            }
            public void Blur(int r)
            {
                var t = new float[d.Length];
                for (int axis = 0; axis < 3; axis++)
                {
                    for (int z = 0; z < nz; z++) for (int y = 0; y < ny; y++) for (int x = 0; x < nx; x++)
                    {
                        float s = 0; int n = 0;
                        for (int o = -r; o <= r; o++)
                        {
                            int xi = x + (axis == 0 ? o : 0), yi = y + (axis == 1 ? o : 0), zi = z + (axis == 2 ? o : 0);
                            if (xi < 0 || yi < 0 || zi < 0 || xi >= nx || yi >= ny || zi >= nz) { n++; continue; }
                            s += d[I(xi, yi, zi)]; n++;
                        }
                        t[I(x, y, z)] = s / n;
                    }
                    var swap = d; d = t; t = swap;
                }
            }
            public Vector3 Gradient(Vector3 p)
            {
                float h = cell;
                return new Vector3(Sample(p + Vector3.right * h) - Sample(p - Vector3.right * h), Sample(p + Vector3.up * h) - Sample(p - Vector3.up * h),
                                   Sample(p + Vector3.forward * h) - Sample(p - Vector3.forward * h)) / (2 * h);
            }
        }

        static float Hash(int x, int y, int z, int seed)
        {
            unchecked
            {
                uint h = (uint)(x * 73856093) ^ (uint)(y * 19349663) ^ (uint)(z * 83492791) ^ (uint)(seed * 2654435761);
                h ^= h >> 13; h *= 0x5bd1e995; h ^= h >> 15;
                return (h & 0xFFFFFF) / (float)0x1000000;
            }
        }

        static float ValueNoise(Vector3 p, int seed)
        {
            int x = Mathf.FloorToInt(p.x), y = Mathf.FloorToInt(p.y), z = Mathf.FloorToInt(p.z);
            float fx = p.x - x, fy = p.y - y, fz = p.z - z;
            fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); fz = fz * fz * (3 - 2 * fz);
            float s = 0;
            for (int k = 0; k < 8; k++)
            {
                int dx = k & 1, dy = (k >> 1) & 1, dz = (k >> 2) & 1;
                s += (dx != 0 ? fx : 1 - fx) * (dy != 0 ? fy : 1 - fy) * (dz != 0 ? fz : 1 - fz) * Hash(x + dx, y + dy, z + dz, seed);
            }
            return s;
        }

        /// Original (vendor FBX) mesh behind a tree LOD renderer, even after the install swapped in our copy.
        static Mesh OriginalMesh(MeshFilter mf)
        {
            var src = PrefabUtility.GetCorrespondingObjectFromOriginalSource(mf);
            var m = src ? src.sharedMesh : mf.sharedMesh;
            if (m && AssetDatabase.GetAssetPath(m).StartsWith(MeshDir)) throw new Exception("could not resolve the vendor mesh for " + mf.name);
            return m;
        }

        static Material[] OriginalMaterials(MeshRenderer mr)
        {
            var src = PrefabUtility.GetCorrespondingObjectFromSource(mr);
            return src ? src.sharedMaterials : mr.sharedMaterials;
        }

        static string MeshAssetPath(string key, string rendererName) => MeshDir + "BC_" + key + "_" + rendererName.Replace(" ", "_") + ".asset";

        public static string Build()
        {
            var tune = Tune();
            var log = Materials(tune);
            var scene = OpenScene();
            Directory.CreateDirectory(MeshDir);
            var report = new Dictionary<string, object>();
            var bk = (JObject)tune["bake"];
            float cell = (float)bk["cell"], step = (float)bk["step"], maxD = (float)bk["maxDistance"], start = (float)bk["startOffset"], ext = (float)bk["extinction"];
            float groundW = (float)bk["groundWeight"], floor = (float)bk["aoFloor"], gamma = (float)bk["aoGamma"], blend = (float)bk["normalBlend"];
            int nDir = (int)bk["directions"];
            // Fibonacci sphere directions, weighted: sky (cosine-ish) above, a weak ground bounce below
            var dirs = new List<(Vector3 d, float w)>();
            for (int i = 0; i < nDir; i++)
            {
                float y = 1 - 2 * (i + .5f) / nDir, r = Mathf.Sqrt(1 - y * y), phi = i * 2.39996323f;
                var d = new Vector3(Mathf.Cos(phi) * r, y, Mathf.Sin(phi) * r);
                dirs.Add((d, y >= 0 ? .35f + .65f * y : groundW * (.35f - .35f * y)));
            }
            foreach (var tree in Trees)
            {
                var tt = (JObject)tune["trees"][tree];
                var key = (string)tt["key"];
                var root = Root(scene, tree) ?? throw new Exception("tree missing: " + tree);
                var toRoot = root.transform.worldToLocalMatrix;
                var lods = root.GetComponentsInChildren<MeshRenderer>(true).OrderBy(r => r.name).ToArray();
                var lod0 = lods.First(r => r.name.EndsWith("lod0"));
                string leafName = (string)tt["leafMaterial"];

                // occluders: every LOD0 triangle (leaf cards x alpha coverage, bark solid), as area per cell volume
                var m0 = OriginalMesh(lod0.GetComponent<MeshFilter>());
                var mats0 = OriginalMaterials(lod0);
                var xf0 = toRoot * lod0.transform.localToWorldMatrix;
                var v0 = m0.vertices.Select(v => xf0.MultiplyPoint3x4(v)).ToArray();
                int leafSub0 = Array.FindIndex(mats0, m => m && m.name == leafName);
                var leafBounds = new Bounds(v0[m0.GetTriangles(leafSub0)[0]], Vector3.zero);
                foreach (var i in m0.GetTriangles(leafSub0)) leafBounds.Encapsulate(v0[i]);
                var all = new Bounds(leafBounds.center, leafBounds.size); foreach (var v in v0) all.Encapsulate(v);
                all.Expand(2f);
                var grid = new Grid(all, cell);
                float leafArea = 0, barkArea = 0;
                for (int s = 0; s < m0.subMeshCount; s++)
                {
                    bool leaf = s == leafSub0;
                    float weight = leaf ? .25f : 1f; // alpha coverage of a leaf card (16 %, clustered) vs solid bark
                    var t = m0.GetTriangles(s);
                    for (int i = 0; i < t.Length; i += 3)
                    {
                        Vector3 a = v0[t[i]], b = v0[t[i + 1]], c = v0[t[i + 2]];
                        float area = Vector3.Cross(b - a, c - a).magnitude * .5f;
                        if (leaf) leafArea += area; else barkArea += area;
                        int n = Mathf.Clamp(Mathf.CeilToInt(area / (cell * cell * .25f)), 1, 400);
                        for (int k = 0; k < n; k++)
                        {
                            float r1 = Hash(i, k, s, 1), r2 = Hash(i, k, s, 2);
                            if (r1 + r2 > 1) { r1 = 1 - r1; r2 = 1 - r2; }
                            grid.Add(a + (b - a) * r1 + (c - a) * r2, area * weight / n);
                        }
                    }
                }
                float vol = cell * cell * cell;
                for (int i = 0; i < grid.d.Length; i++) grid.d[i] /= vol;
                var occ = grid.Clone(); occ.Blur(1);
                var smooth = grid.Clone(); for (int p = 0; p < (int)bk["gradientBlurPasses"]; p++) smooth.Blur((int)bk["gradientBlurRadius"]);
                // crown ellipsoid from the leaf distribution (area-weighted centre, half extents)
                var centre = leafBounds.center; var half = leafBounds.extents;

                float RawAO(Vector3 p)
                {
                    float sw = 0, st = 0;
                    foreach (var (d, w) in dirs)
                    {
                        float tau = 0;
                        for (float t = start; t < maxD; t += step) { var q = p + d * t; if (!occ.Inside(q)) break; tau += occ.Sample(q) * step; }
                        st += w * Mathf.Exp(-ext * tau); sw += w;
                    }
                    return st / sw;
                }

                // pass 1: raw occlusion on LOD0 leaf vertices for the percentile remap
                var leafVerts0 = m0.GetTriangles(leafSub0).Distinct().ToArray();
                var raw0 = leafVerts0.Select(i => RawAO(v0[i])).OrderBy(x => x).ToArray();
                float lo = raw0[Mathf.Clamp((int)(raw0.Length * (float)bk["aoLowPercentile"] / 100), 0, raw0.Length - 1)];
                float hi = raw0[Mathf.Clamp((int)(raw0.Length * (float)bk["aoHighPercentile"] / 100), 0, raw0.Length - 1)];
                float Remap(float raw) => Mathf.Lerp(floor, 1, Mathf.Pow(Mathf.Clamp01((raw - lo) / Mathf.Max(1e-4f, hi - lo)), gamma));
                float gRef = leafVerts0.Select(i => smooth.Gradient(v0[i]).magnitude).OrderBy(x => x).ElementAt(leafVerts0.Length / 2);

                var treeReport = new Dictionary<string, object>
                {
                    ["leafArea"] = leafArea, ["barkArea"] = barkArea, ["grid"] = new[] { grid.nx, grid.ny, grid.nz }, ["rawAO"] = new { lo, hi, min = raw0[0], max = raw0[raw0.Length - 1] },
                    ["crownCentre"] = F3(centre), ["crownHalf"] = F3(half), ["gradientRef"] = gRef,
                };
                var lodReports = new List<object>();
                foreach (var r in lods)
                {
                    var mf = r.GetComponent<MeshFilter>();
                    var src = OriginalMesh(mf);
                    var mats = OriginalMaterials(r);
                    var xf = toRoot * r.transform.localToWorldMatrix; var inv = xf.inverse;
                    var mesh = UnityEngine.Object.Instantiate(src);
                    mesh.name = "BC_" + key + "_" + r.name.Replace(" ", "_");
                    var verts = src.vertices; var normals = src.normals; var tangents = src.tangents;
                    var oldColors = src.colors;
                    var pos = verts.Select(v => xf.MultiplyPoint3x4(v)).ToArray();
                    var colors = new Color[verts.Length];
                    for (int i = 0; i < verts.Length; i++) colors[i] = new Color(0, .5f, 0, Remap(RawAO(pos[i])));
                    int leafSub = Array.FindIndex(mats, m => m && m.name == leafName);
                    var seasons = new List<float>(); int dry = 0, cards = 0;
                    if (leafSub >= 0)
                    {
                        var t = src.GetTriangles(leafSub);
                        // cards: connected components by shared vertex index (front and back copies are separate cards with one centroid)
                        var parent = new Dictionary<int, int>();
                        int Find(int a) { while (parent[a] != a) { parent[a] = parent[parent[a]]; a = parent[a]; } return a; }
                        foreach (var v in t) if (!parent.ContainsKey(v)) parent[v] = v;
                        for (int i = 0; i < t.Length; i += 3) { int a = Find(t[i]); parent[Find(t[i + 1])] = a; parent[Find(t[i + 2])] = a; }
                        foreach (var g in parent.Keys.ToList().GroupBy(Find))
                        {
                            cards++;
                            var c = Vector3.zero; foreach (var v in g) c += pos[v]; c /= g.Count();
                            int hx = Mathf.RoundToInt(c.x * 20), hy = Mathf.RoundToInt(c.y * 20), hz = Mathf.RoundToInt(c.z * 20);
                            float exposure = Remap(RawAO(c));
                            float height = Mathf.Clamp01((c.y - leafBounds.min.y) / Mathf.Max(.1f, leafBounds.size.y));
                            float season = (float)tt["seasonMean"] + (float)tt["seasonExposure"] * (exposure - .65f) * 2 + (float)tt["seasonHeight"] * (height - .5f) * 2
                                         + (float)tt["seasonNoise"] * (ValueNoise(c * .55f, 7) - .5f) * 2 + (float)tt["seasonRandom"] * (Hash(hx, hy, hz, 11) - .5f) * 2;
                            season = Mathf.Clamp01(season);
                            float jitter = Mathf.Clamp01(.5f + ((Hash(hx, hy, hz, 13) - .5f) * .8f + (ValueNoise(c * .9f, 17) - .5f) * .6f) * (float)tt["jitterSpread"]);
                            float dr = Hash(hx, hy, hz, 19);
                            float dryness = dr < (float)tt["dryFraction"] * (.5f + exposure) ? .6f + .4f * Hash(hx, hy, hz, 23) : 0;
                            if (dryness > 0) dry++;
                            seasons.Add(season);
                            foreach (var v in g) { colors[v].r = season; colors[v].g = jitter; colors[v].b = dryness; }
                        }
                        // crown-volume normals on the leaf vertices (bark keeps its own)
                        foreach (var v in t.Distinct())
                        {
                            var p = pos[v];
                            var ell = new Vector3((p.x - centre.x) / (half.x * half.x), (p.y - centre.y) / (half.y * half.y), (p.z - centre.z) / (half.z * half.z)).normalized;
                            var g = smooth.Gradient(p);
                            var nv = (ell + 1.2f * Mathf.Clamp01(g.magnitude / Mathf.Max(1e-5f, gRef)) * (-g.normalized)).normalized;
                            var nWorld = xf.MultiplyVector(normals[v]).normalized;
                            var nn = Vector3.Lerp(nWorld, nv, blend).normalized;
                            var nLocal = inv.MultiplyVector(nn).normalized;
                            normals[v] = nLocal;
                            if (tangents.Length == verts.Length)
                            {
                                var tg = (Vector3)tangents[v];
                                var to = (tg - nLocal * Vector3.Dot(nLocal, tg));
                                if (to.sqrMagnitude > 1e-8f) { to.Normalize(); tangents[v] = new Vector4(to.x, to.y, to.z, tangents[v].w); }
                            }
                        }
                    }
                    mesh.normals = normals;
                    if (tangents.Length == verts.Length) mesh.tangents = tangents;
                    mesh.colors = colors;
                    var path = MeshAssetPath(key, r.name);
                    var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                    if (existing) { EditorUtility.CopySerialized(mesh, existing); existing.name = mesh.name; EditorUtility.SetDirty(existing); UnityEngine.Object.DestroyImmediate(mesh); }
                    else AssetDatabase.CreateAsset(mesh, path);
                    var ao = colors.Select(c => c.a).OrderBy(x => x).ToArray();
                    var oc = oldColors.Length > 0 ? new { r = oldColors.Average(c => c.r), g = oldColors.Average(c => c.g), b = oldColors.Average(c => c.b), a = oldColors.Average(c => c.a) } : null;
                    lodReports.Add(new
                    {
                        renderer = r.name, asset = path, vertices = verts.Length, triangles = Enumerable.Range(0, src.subMeshCount).Sum(s => (int)src.GetIndexCount(s) / 3),
                        leafCards = cards, drySeasonCards = dry, seasonMean = seasons.Count > 0 ? seasons.Average() : 0,
                        seasonP10 = seasons.Count > 0 ? seasons.OrderBy(x => x).ElementAt(seasons.Count / 10) : 0, seasonP90 = seasons.Count > 0 ? seasons.OrderBy(x => x).ElementAt(seasons.Count * 9 / 10) : 0,
                        aoP10 = ao[ao.Length / 10], aoMedian = ao[ao.Length / 2], aoP90 = ao[ao.Length * 9 / 10], vendorColorMean = oc,
                    });
                }
                treeReport["lods"] = lodReports;
                report[tree] = treeReport;
            }
            AssetDatabase.SaveAssets();
            report["materials"] = log;
            Save("bake-report.json", report);
            return "bake-report.json; " + string.Join("; ", log);
        }

        // ------------------------------------------------------------------ install (one time) / apply (idempotent) / rollback
        static bool IsOurs(Mesh m) => m && AssetDatabase.GetAssetPath(m).StartsWith(MeshDir);

        public static string Install()
        {
            var scene = OpenScene();
            foreach (var tree in Trees)
                if (Root(scene, tree).GetComponentsInChildren<MeshFilter>(true).Any(mf => IsOurs(mf.sharedMesh)))
                    throw new Exception("The birch canopy is already installed; use apply (or rollback first).");
            Directory.CreateDirectory(Evidence + "rollback");
            File.Copy(ScenePath, Evidence + "rollback/before-birch-canopy.unity", true);
            var originals = new JObject();
            var trees = new JObject();
            foreach (var tree in Trees)
            {
                var rows = new JArray();
                foreach (var mr in Root(scene, tree).GetComponentsInChildren<MeshRenderer>(true))
                {
                    var mf = mr.GetComponent<MeshFilter>();
                    rows.Add(new JObject
                    {
                        ["path"] = PathOf(mr.transform), ["mesh"] = AssetDatabase.GetAssetPath(mf.sharedMesh) + "#" + mf.sharedMesh.name,
                        ["materials"] = new JArray(mr.sharedMaterials.Select(m => m ? AssetDatabase.GetAssetPath(m) : "")),
                        ["staticFlags"] = (int)GameObjectUtility.GetStaticEditorFlags(mr.gameObject),
                    });
                }
                trees[tree] = rows;
            }
            originals["trees"] = trees;
            var beds = new JObject();
            foreach (var kv in BedPrefabs)
            {
                var root = PrefabUtility.LoadPrefabContents(kv.Value);
                try
                {
                    beds[kv.Key] = new JObject
                    {
                        ["prefab"] = kv.Value,
                        ["lights"] = new JArray(root.GetComponentsInChildren<Light>(true).Select(l => new JObject
                        {
                            ["name"] = l.name, ["localPos"] = new JArray(F3(l.transform.localPosition)), ["localRot"] = new JArray(l.transform.localRotation.x, l.transform.localRotation.y, l.transform.localRotation.z, l.transform.localRotation.w),
                            ["intensity"] = l.intensity, ["range"] = l.range, ["spotAngle"] = l.spotAngle, ["innerSpotAngle"] = l.innerSpotAngle,
                        })),
                        ["lensSlots"] = new JArray(root.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials.Select((m, i) => (r, m, i)))
                            .Where(x => x.m && AssetDatabase.GetAssetPath(x.m) == HallLens).Select(x => new JObject { ["renderer"] = x.r.name, ["slot"] = x.i })),
                    };
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            originals["beds"] = beds;
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            originals["circuitEmissive"] = circuit.emissiveMaterials.Length;
            var lensMat = AssetDatabase.LoadAssetAtPath<Material>(HallLens);
            originals["VH_LampLens"] = new JObject { ["emission"] = lensMat.GetColor("_EmissionColor").ToString("F4"), ["note"] = "unchanged by this pass" };
            File.WriteAllText(OriginalsFile, originals.ToString(Formatting.Indented));
            var log = Apply();
            Save("install.json", new { rollbackScene = Evidence + "rollback/before-birch-canopy.unity", originals = OriginalsFile, apply = log });
            return "installed; " + log;
        }

        /// Idempotent: meshes/materials/static flags on the tree LOD renderers, uplight aim/values and lens slots in the bed
        /// prefabs (recomputed from the recorded original positions), the lens on the light clock, review cameras.
        public static string Apply() => ApplyCore(true);

        /// In-memory preview for editor captures before the install: the same tree, light and lens values on the scene
        /// instances only (no prefab or scene save). Light originals come from the open scene's bed instances.
        public static string Preview() => ApplyCore(false);

        static JObject LiveOriginals()
        {
            var beds = new JObject();
            var bedRoot = Root(OpenScene(), BedRoot);
            foreach (var kv in BedPrefabs)
            {
                var inst = bedRoot.transform.Find("Tree bed " + kv.Key);
                beds[kv.Key] = new JObject
                {
                    ["lights"] = new JArray(inst.GetComponentsInChildren<Light>(true).Select(l => new JObject
                    { ["name"] = l.name, ["localPos"] = new JArray(F3(inst.InverseTransformPoint(l.transform.position))) })),
                    ["lensSlots"] = new JArray(inst.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials.Select((m, i) => (r, m, i)))
                        .Where(x => x.m && AssetDatabase.GetAssetPath(x.m) == HallLens).Select(x => new JObject { ["renderer"] = x.r.name, ["slot"] = x.i })),
                };
            }
            return new JObject { ["beds"] = beds };
        }

        static string ApplyCore(bool persist)
        {
            var tune = Tune();
            if (persist && !File.Exists(OriginalsFile)) throw new Exception("install first (no originals.json)");
            var originals = persist ? JObject.Parse(File.ReadAllText(OriginalsFile)) : LiveOriginals();
            Materials(tune);
            var scene = OpenScene();
            var log = new List<string>();
            foreach (var tree in Trees)
            {
                var key = (string)tune["trees"][tree]["key"];
                foreach (var mr in Root(scene, tree).GetComponentsInChildren<MeshRenderer>(true))
                {
                    var mf = mr.GetComponent<MeshFilter>();
                    var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(MeshAssetPath(key, mr.name)) ?? throw new Exception("not built: " + MeshAssetPath(key, mr.name));
                    mf.sharedMesh = mesh;
                    var mats = OriginalMaterials(mr).Select(m =>
                    {
                        var n = OurMaterialName(tree, m.name, tune) ?? throw new Exception("unmapped vendor material " + m.name);
                        return AssetDatabase.LoadAssetAtPath<Material>(MatDir + n + ".mat");
                    }).ToArray();
                    mr.sharedMaterials = mats;
                    mr.motionVectorGenerationMode = MotionVectorGenerationMode.Object;
                    var flags = GameObjectUtility.GetStaticEditorFlags(mr.gameObject) & ~StaticEditorFlags.BatchingStatic; // wind: never static-batch
                    GameObjectUtility.SetStaticEditorFlags(mr.gameObject, flags);
                    if (persist)
                    {
                        PrefabUtility.RecordPrefabInstancePropertyModifications(mf);
                        PrefabUtility.RecordPrefabInstancePropertyModifications(mr);
                        PrefabUtility.RecordPrefabInstancePropertyModifications(mr.gameObject);
                    }
                    log.Add($"{tree}/{mr.name}: {mesh.name} [{string.Join(",", mats.Select(m => m.name))}]");
                }
            }
            // bed uplights and lenses (prefab assets; scene instances follow, the clock keeps the same light objects)
            var lens = AssetDatabase.LoadAssetAtPath<Material>(LensPath);
            foreach (var kv in BedPrefabs)
            {
                var bedSpec = (JObject)tune["uplights"][kv.Key];
                var crown = tune["trees"][kv.Key]["crownXZ"];
                var root = persist ? PrefabUtility.LoadPrefabContents(kv.Value) : Root(scene, BedRoot).transform.Find("Tree bed " + kv.Key).gameObject;
                try
                {
                    foreach (var l in root.GetComponentsInChildren<Light>(true))
                    {
                        var o = originals["beds"][kv.Key]["lights"].First(x => (string)x["name"] == l.name);
                        var spec = (JObject)(bedSpec[l.name] ?? bedSpec);
                        var p = new Vector3((float)o["localPos"][0], (float)o["localPos"][1], (float)o["localPos"][2]);
                        var c = crown != null ? new Vector3((float)crown[0], 0, (float)crown[1]) : Vector3.zero;
                        var radial = new Vector3(p.x - c.x, 0, p.z - c.z).normalized;
                        var target = c - radial * (float)spec["aimPastTrunk"] + Vector3.up * (float)spec["aimHeight"];
                        l.transform.localPosition = p;
                        l.transform.localRotation = Quaternion.LookRotation(target - p, Vector3.up);
                        l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"];
                        l.spotAngle = (float)spec["spotAngle"]; l.innerSpotAngle = (float)spec["innerSpotAngle"];
                        log.Add($"{kv.Key}/{l.name} ({(string)spec["role"]}): {l.intensity} / {l.range} m / {l.spotAngle}-{l.innerSpotAngle} deg, aim {F3(target).Aggregate("", (a, b) => a + b + " ")}");
                    }
                    foreach (var slot in originals["beds"][kv.Key]["lensSlots"])
                    {
                        var r = root.GetComponentsInChildren<Renderer>(true).First(x => x.name == (string)slot["renderer"]);
                        var mats = r.sharedMaterials; mats[(int)slot["slot"]] = lens; r.sharedMaterials = mats;
                    }
                    if (persist) PrefabUtility.SaveAsPrefabAsset(root, kv.Value);
                }
                finally { if (persist) PrefabUtility.UnloadPrefabContents(root); }
            }
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            if (!circuit.emissiveMaterials.Contains(lens))
            {
                circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { lens }).ToArray();
                if (persist) EditorUtility.SetDirty(circuit);
            }
            if (persist) Cameras(); // saves the scene
            Save(persist ? "apply.json" : "preview-apply.json", log);
            return string.Join("\n", log);
        }

        public static string Rollback()
        {
            var originals = JObject.Parse(File.ReadAllText(OriginalsFile));
            var scene = OpenScene();
            foreach (var tree in Trees)
                foreach (var row in originals["trees"][tree])
                {
                    var go = GameObject.Find((string)row["path"]); var mr = go.GetComponent<MeshRenderer>(); var mf = go.GetComponent<MeshFilter>();
                    var mp = ((string)row["mesh"]).Split('#');
                    mf.sharedMesh = AssetDatabase.LoadAllAssetsAtPath(mp[0]).OfType<Mesh>().First(m => m.name == mp[1]);
                    mr.sharedMaterials = row["materials"].Select(p => AssetDatabase.LoadAssetAtPath<Material>((string)p)).ToArray();
                    GameObjectUtility.SetStaticEditorFlags(go, (StaticEditorFlags)(int)row["staticFlags"]);
                    PrefabUtility.RecordPrefabInstancePropertyModifications(mf); PrefabUtility.RecordPrefabInstancePropertyModifications(mr); PrefabUtility.RecordPrefabInstancePropertyModifications(go);
                }
            var hall = AssetDatabase.LoadAssetAtPath<Material>(HallLens);
            foreach (var kv in BedPrefabs)
            {
                var root = PrefabUtility.LoadPrefabContents(kv.Value);
                try
                {
                    foreach (var l in root.GetComponentsInChildren<Light>(true))
                    {
                        var o = originals["beds"][kv.Key]["lights"].First(x => (string)x["name"] == l.name);
                        l.transform.localPosition = new Vector3((float)o["localPos"][0], (float)o["localPos"][1], (float)o["localPos"][2]);
                        l.transform.localRotation = new Quaternion((float)o["localRot"][0], (float)o["localRot"][1], (float)o["localRot"][2], (float)o["localRot"][3]);
                        l.intensity = (float)o["intensity"]; l.range = (float)o["range"]; l.spotAngle = (float)o["spotAngle"]; l.innerSpotAngle = (float)o["innerSpotAngle"];
                    }
                    foreach (var slot in originals["beds"][kv.Key]["lensSlots"])
                    {
                        var r = root.GetComponentsInChildren<Renderer>(true).First(x => x.name == (string)slot["renderer"]);
                        var mats = r.sharedMaterials; mats[(int)slot["slot"]] = hall; r.sharedMaterials = mats;
                    }
                    PrefabUtility.SaveAsPrefabAsset(root, kv.Value);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var lens = AssetDatabase.LoadAssetAtPath<Material>(LensPath);
            circuit.emissiveMaterials = circuit.emissiveMaterials.Where(m => m != lens).ToArray(); EditorUtility.SetDirty(circuit);
            var cams = Root(scene, CamRootName); if (cams) UnityEngine.Object.DestroyImmediate(cams);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "rolled back (materials, meshes and BC_UplightLens assets stay in Art/BirchCanopy)";
        }

        // ------------------------------------------------------------------ verify (-nographics)
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var tune = Tune();
            var r = new Dictionary<string, object>();
            int problems = 0;
            foreach (var tree in Trees)
            {
                var root = Root(scene, tree);
                var rows = root.GetComponentsInChildren<MeshRenderer>(true).Select(mr => new
                {
                    mr.name, mesh = mr.GetComponent<MeshFilter>().sharedMesh?.name, ours = IsOurs(mr.GetComponent<MeshFilter>().sharedMesh),
                    materials = mr.sharedMaterials.Select(m => m ? m.name : "MISSING").ToArray(), shader = mr.sharedMaterials.Select(m => m ? m.shader.name : "").Distinct().ToArray(),
                    batchingStatic = (GameObjectUtility.GetStaticEditorFlags(mr.gameObject) & StaticEditorFlags.BatchingStatic) != 0,
                    hasColors = mr.GetComponent<MeshFilter>().sharedMesh.HasVertexAttribute(VertexAttribute.Color),
                    tris = Enumerable.Range(0, mr.GetComponent<MeshFilter>().sharedMesh.subMeshCount).Sum(s => (int)mr.GetComponent<MeshFilter>().sharedMesh.GetIndexCount(s) / 3),
                }).ToArray();
                problems += rows.Count(x => !x.ours || x.materials.Contains("MISSING") || x.batchingStatic || !x.hasColors || x.shader.Any(s => s != "Athen Hill/Ward Canopy"));
                var lg = root.GetComponent<LODGroup>();
                bool linked = PrefabUtility.IsPartOfPrefabInstance(root) && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(root).StartsWith("Assets/TreesBundleB/");
                var capsule = root.GetComponent<CapsuleCollider>();
                if (!linked || !capsule || !lg) problems++;
                r[tree] = new { prefabLinked = linked, prefab = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(root), trunkCapsule = capsule ? F3(capsule.bounds.center) : null, lodGroup = lg != null, renderers = rows };
            }
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var lens = AssetDatabase.LoadAssetAtPath<Material>(LensPath);
            var bedRoot = Root(scene, BedRoot);
            var lights = bedRoot.GetComponentsInChildren<Light>(true).Select(l => new
            {
                path = PathOf(l.transform), l.intensity, l.range, l.spotAngle, l.innerSpotAngle, fwd = F3(l.transform.forward),
                practical = circuit.practicalLights.Contains(l), nightOnly = circuit.nightOnlyLights.Contains(l),
            }).ToArray();
            problems += lights.Count(l => !l.practical || !l.nightOnly);
            var lensUsers = bedRoot.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Contains(lens));
            var hallUsers = bedRoot.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => m && AssetDatabase.GetAssetPath(m) == HallLens));
            if (hallUsers > 0 || lensUsers == 0 || !circuit.emissiveMaterials.Contains(lens)) problems++;
            r["uplights"] = lights;
            r["lens"] = new { users = lensUsers, hallLensUsersLeftInBeds = hallUsers, onClock = circuit.emissiveMaterials.Contains(lens), emission = lens.GetColor("_EmissionColor").ToString("F3") };
            r["bedPrefabLinks"] = bedRoot.GetComponentsInChildren<Transform>(true).Where(t => t.parent == bedRoot.transform).Select(t => t.name + ": " + PrefabUtility.IsPartOfPrefabInstance(t.gameObject)).ToArray();
            r["missingMaterials"] = scene.GetRootGameObjects().Where(g => Trees.Contains(g.name) || g.name == BedRoot).SelectMany(g => g.GetComponentsInChildren<Renderer>(true)).Count(x => x.sharedMaterials.Any(m => !m));
            problems += (int)r["missingMaterials"];
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            if (chunks) r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            r["reviewCameras"] = Root(scene, CamRootName)?.GetComponentsInChildren<Camera>(true).Select(c => c.name + (c.enabled ? " (ENABLED!)" : "")).ToArray();
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            r["shaderErrors"] = ShaderUtil.ShaderHasError(shader);
            if ((bool)r["shaderErrors"]) problems++;
            r["problems"] = problems;
            Save("verify-saved-scene.json", r);
            return "problems " + problems;
        }

        /// OpenGL Core compile of every pass of the canopy shader in the keyword sets the trees use.
        public static string ShaderCheck()
        {
            AssetDatabase.ImportAsset(ShaderPath, ImportAssetOptions.ForceUpdate);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            var log = new List<string>();
            var msgs = ShaderUtil.GetShaderMessages(shader);
            log.Add("import messages: " + msgs.Length + (msgs.Length > 0 ? " " + string.Join(" | ", msgs.Take(6).Select(m => m.severity + ": " + m.message + " @" + m.line)) : ""));
            bool ok = !ShaderUtil.ShaderHasError(shader);
            var data = ShaderUtil.GetShaderData(shader);
            var sub = data.GetSubshader(0);
            for (int p = 0; p < sub.PassCount; p++)
            {
                var pass = sub.GetPass(p);
                if (pass.Name == "GBuffer") continue; // excluded on OpenGL Core
                foreach (var kw in new[] { new[] { "_NORMALMAP" }, new[] { "_NORMALMAP", "_ALPHATEST_ON", "_MAIN_LIGHT_SHADOWS_CASCADE", "_CLUSTER_LIGHT_LOOP", "LOD_FADE_CROSSFADE", "_SHADOWS_SOFT" } })
                    foreach (var stage in new[] { ShaderType.Vertex, ShaderType.Fragment })
                    {
                        var res = pass.CompileVariant(stage, kw, ShaderCompilerPlatform.OpenGLCore, BuildTarget.StandaloneLinux64);
                        ok &= res.Success;
                        log.Add($"{pass.Name} {stage} [{string.Join(" ", kw)}]: {(res.Success ? "ok" : "FAIL")} " +
                                string.Join(" | ", res.Messages.Where(m => m.severity == ShaderCompilerMessageSeverity.Error).Take(4).Select(m => m.message + " @" + m.line)));
                    }
            }
            Save("shader-check.json", new { ok, log });
            if (!ok) throw new Exception("canopy shader failed to compile:\n" + string.Join("\n", log));
            return "shader ok (" + log.Count + " compiles)";
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.BirchCanopyPass.RunBatch --steps survey [--out dir]
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
                        "capture" => Capture(st, outDir),
                        "cameras" => Cameras(),
                        "build" => Build(),
                        "shadercheck" => ShaderCheck(),
                        "install" => Install(),
                        "apply" => Apply(),
                        "preview" => Preview(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("BirchCanopyPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
