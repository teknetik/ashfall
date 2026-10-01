using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: night lighting and ambient life (art-direction next-wins items 3 and 9).
    /// * Street lamps: the existing Ward utility post and wall fixtures (Art/Quality/Lamps) as merged-part prefabs with
    ///   LODs (Prefabs/NightLife/NL_StreetLampPost/Wall; the originals are 103/73-part render-chunk sources), placed from
    ///   art/night_life_20261001/night-layout.json in the dark pockets, each with a warm spot light on the Ward lighting
    ///   clock (practical + night-only, unshadowed). Wall brackets are snapped onto the real wall mesh by a ray.
    /// * Mission terminals: a new material MissionTerminal_Lit (the Meshy material plus an emission map derived from the
    ///   albedo: display, badge, status button; constant like the hill RECLAIM kiosks) on the three scene instances, and a
    ///   small cool night-only fill in front of each screen. The original material is unchanged.
    /// * Ambient life (AmbientLife runtime component, Reduced Motion aware): barrel fire with embers and a flickering
    ///   night light, wind-drifted flue smoke (Repairs, Salvage stovepipe), intermittent steam at the Air + Water filter
    ///   header, faint generator exhaust haze. Cookfire materials reused; steam/haze materials new.
    /// Everything lives under the scene root "Ward night life" (not a render-chunk source), review cameras under
    /// "Night life review cameras". Batch: -executeMethod AthenHill.Editor.NightLifePass.RunBatch --steps
    /// survey|build|install|verify|cameras|retune|relayout|rebuildfx|capture[:filter]|abbuild:on|abbuild:off [--out dir]
    /// </summary>
    public static class NightLifePass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/night-life/20261001/";
        const string ArtSrc = "../../art/night_life_20261001/";
        const string ArtDir = "Assets/AthenHill/Art/NightLife/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/NightLife/";
        const string PostSrc = "Assets/AthenHill/Art/Quality/Lamps/WardUtilityPost.prefab";
        const string WallSrc = "Assets/AthenHill/Art/Quality/Lamps/WardUtilityWall.prefab";
        const string PostPrefab = PrefabDir + "NL_StreetLampPost.prefab";
        const string WallPrefab = PrefabDir + "NL_StreetLampWall.prefab";
        const string TerminalSrcMat = "Assets/AthenHill/Art/Imported/Meshy/MissionTerminal/MissionTerminal.mat";
        const string TerminalMat = ArtDir + "Terminal/MissionTerminal_Lit.mat";
        const string TerminalEmission = ArtDir + "Terminal/MissionTerminal_Emission.png";
        const string CookDir = "Assets/AthenHill/Art/Atmosphere/Dustbowl/";
        public const string RootName = "Ward night life";
        const string CamRootName = "Night life review cameras";
        static readonly string[] TerminalPaths = { "Mission Terminal Upgrade/Mission Terminal 01", "Mission Terminal Upgrade/Mission Terminal 02", "Mission Terminal Upgrade/Mission Terminal 03" };
        const float TerminalEmissionStrength = 1.5f;
        static readonly Color LampColor = new Color(1f, .76f, .48f);
        static readonly Vector3 PostLightLocal = new Vector3(0, 4.16f, .52f), WallLightLocal = new Vector3(0, -.02f, .414f);

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] A(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static JObject Layout() => JObject.Parse(File.ReadAllText(ArtSrc + "night-layout.json"));
        static Transform Find(UnityEngine.SceneManagement.Scene scene, string path)
        {
            var parts = path.Split('/');
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!root) return null;
            var t = root.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Find(parts[i]);
            return t;
        }
        static long Tris(Mesh m) { long n = 0; if (m) for (int s = 0; s < m.subMeshCount; s++) n += m.GetIndexCount(s) / 3; return n; }

        // ================================================================== build
        public static string BuildAssets()
        {
            Directory.CreateDirectory(ArtDir + "Lamps"); Directory.CreateDirectory(ArtDir + "Terminal"); Directory.CreateDirectory(ArtDir + "FX");
            Directory.CreateDirectory(PrefabDir);
            var log = new Dictionary<string, object>
            {
                ["post"] = BuildMergedLamp(PostSrc, "Post", PostPrefab, true),
                ["wall"] = BuildMergedLamp(WallSrc, "Wall", WallPrefab, false),
                ["terminal"] = BuildTerminalMaterial(),
                ["fx"] = BuildFxMaterials(),
            };
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(log, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "build-assets.json", json);
            return json;
        }

        static bool IsLens(Material m) => m && m.name.Contains("LampEmission");
        static bool IsDecal(Material m) => m && (m.name.Contains("Dust") || m.name.Contains("Oxide"));

        /// Merges the authored lamp's parts per material into one mesh per LOD (LOD0 every part; LOD1 without the
        /// small hardware; LOD2 only the big masses and the lens). LOD0/1 cast through a ShadowsOnly copy of LOD2.
        static object BuildMergedLamp(string src, string key, string dst, bool post)
        {
            var source = PrefabUtility.LoadPrefabContents(src);
            var root = new GameObject(Path.GetFileNameWithoutExtension(dst));
            var stats = new List<object>();
            try
            {
                var toRoot = source.transform.worldToLocalMatrix;
                var parts = new List<(Mesh mesh, int sub, Material mat, Matrix4x4 m, float size)>();
                foreach (var r in source.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var f = r.GetComponent<MeshFilter>();
                    if (!f || !f.sharedMesh) continue;
                    var mats = r.sharedMaterials;
                    float size = r.bounds.size.magnitude;
                    for (int s = 0; s < f.sharedMesh.subMeshCount; s++)
                    {
                        var mat = mats.Length == 0 ? null : mats[Mathf.Min(s, mats.Length - 1)];
                        if (!mat) continue;
                        parts.Add((f.sharedMesh, s, mat, toRoot * r.localToWorldMatrix, size));
                    }
                }
                Func<(Mesh mesh, int sub, Material mat, Matrix4x4 m, float size), bool>[] keep =
                {
                    p => true,
                    p => IsLens(p.mat) || p.size >= .12f,
                    p => IsLens(p.mat) || (!IsDecal(p.mat) && p.size >= .5f),
                };
                var levels = new List<LOD>();
                var lodRenderers = new List<Renderer>[3];
                for (int lod = 0; lod < 3; lod++)
                {
                    var holder = new GameObject("LOD" + lod); holder.transform.SetParent(root.transform, false);
                    lodRenderers[lod] = new List<Renderer>();
                    long lodTris = 0;
                    foreach (var g in parts.Where(keep[lod]).GroupBy(p => p.mat))
                    {
                        var mesh = Combine(g.ToList(), $"NL_{key}_LOD{lod}_{g.Key.name}");
                        var go = new GameObject($"{key} LOD{lod} {g.Key.name}"); go.transform.SetParent(holder.transform, false);
                        go.AddComponent<MeshFilter>().sharedMesh = mesh;
                        var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = g.Key;
                        mr.shadowCastingMode = lod == 2 && !IsLens(g.Key) && !IsDecal(g.Key) ? ShadowCastingMode.On : ShadowCastingMode.Off;
                        mr.receiveShadows = true; mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                        lodRenderers[lod].Add(mr); lodTris += Tris(mesh);
                    }
                    stats.Add(new { lod, renderers = lodRenderers[lod].Count, triangles = lodTris });
                }
                var proxyRoot = new GameObject("Shadow proxy (LOD2 masses)"); proxyRoot.transform.SetParent(root.transform, false);
                var proxies = new List<Renderer>();
                foreach (var r2 in lodRenderers[2].Where(r => r.shadowCastingMode == ShadowCastingMode.On))
                {
                    var go = new GameObject(r2.name + " shadow"); go.transform.SetParent(proxyRoot.transform, false);
                    go.AddComponent<MeshFilter>().sharedMesh = r2.GetComponent<MeshFilter>().sharedMesh;
                    var pr = go.AddComponent<MeshRenderer>(); pr.sharedMaterial = r2.sharedMaterial; pr.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                    proxies.Add(pr);
                }
                // post: LOD0 within ~33 m, LOD1 to ~66 m (PC LOD bias 2); the wall fixture is smaller
                float[] cuts = post ? new[] { .3f, .15f, .012f } : new[] { .12f, .06f, .006f };   // (LodCuts applies the same in place)
                levels.Add(new LOD(cuts[0], lodRenderers[0].Concat(proxies).ToArray()));
                levels.Add(new LOD(cuts[1], lodRenderers[1].Concat(proxies).ToArray()));
                levels.Add(new LOD(cuts[2], lodRenderers[2].ToArray()));
                var group = root.AddComponent<LODGroup>(); group.SetLODs(levels.ToArray()); group.fadeMode = LODFadeMode.None; group.RecalculateBounds();
                if (post)
                {   // the mast and the footing (the original posts kept their old proxies in AuthoredWorld)
                    var col = new GameObject("Colliders"); col.transform.SetParent(root.transform, false);
                    var mast = parts.Where(p => p.mesh.name.Contains("Tapered_steel_mast") || p.mesh.name.Contains("mast")).ToList();
                    var footing = parts.Where(p => p.mesh.name.Contains("concrete_footing") || p.mesh.name.Contains("footing")).ToList();
                    var cap = col.AddComponent<CapsuleCollider>(); cap.direction = 1; cap.radius = .14f; cap.height = 4.3f; cap.center = new Vector3(0, 2.15f, 0);
                    if (mast.Count > 0)
                    {
                        var b = WorldBounds(mast); cap.center = new Vector3(b.center.x, b.center.y, b.center.z);
                        cap.height = Mathf.Max(1, b.size.y); cap.radius = Mathf.Clamp(Mathf.Max(b.size.x, b.size.z) * .5f, .08f, .2f);
                    }
                    if (footing.Count > 0)
                    {
                        var b = WorldBounds(footing);
                        var box = col.AddComponent<BoxCollider>(); box.center = b.center; box.size = b.size;
                    }
                }
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic);
                PrefabUtility.SaveAsPrefabAsset(root, dst);
                return new { source = src, prefab = dst, parts = parts.Count, lods = stats, cuts };
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
                PrefabUtility.UnloadPrefabContents(source);
            }
        }

        static Bounds WorldBounds(List<(Mesh mesh, int sub, Material mat, Matrix4x4 m, float size)> ps)
        {
            Bounds? acc = null;
            foreach (var p in ps)
            {
                var b = p.mesh.bounds;
                foreach (var c in new[] { new Vector3(-1, -1, -1), new Vector3(1, -1, -1), new Vector3(-1, 1, -1), new Vector3(1, 1, -1), new Vector3(-1, -1, 1), new Vector3(1, -1, 1), new Vector3(-1, 1, 1), new Vector3(1, 1, 1) })
                {
                    var w = p.m.MultiplyPoint3x4(b.center + Vector3.Scale(b.extents, c));
                    if (acc == null) acc = new Bounds(w, Vector3.zero); else { var x = acc.Value; x.Encapsulate(w); acc = x; }
                }
            }
            return acc ?? new Bounds();
        }

        static Mesh Combine(List<(Mesh mesh, int sub, Material mat, Matrix4x4 m, float size)> parts, string name)
        {
            var ci = parts.Select(p => new CombineInstance { mesh = p.mesh, subMeshIndex = p.sub, transform = p.m }).ToArray();
            var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
            mesh.CombineMeshes(ci, true, true);
            mesh.RecalculateBounds();
            var path = ArtDir + "Lamps/" + name.Replace(' ', '_') + ".asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing) { EditorUtility.CopySerialized(mesh, existing); existing.name = name; UnityEngine.Object.DestroyImmediate(mesh); return existing; }
            AssetDatabase.CreateAsset(mesh, path);
            return mesh;
        }

        static object BuildTerminalMaterial()
        {
            var src = AssetDatabase.LoadAssetAtPath<Material>(TerminalSrcMat) ?? throw new Exception("missing " + TerminalSrcMat);
            AssetDatabase.ImportAsset(TerminalEmission, ImportAssetOptions.ForceSynchronousImport);
            var imp = (TextureImporter)AssetImporter.GetAtPath(TerminalEmission) ?? throw new Exception("run prepare_terminal_emission.py first");
            imp.textureType = TextureImporterType.Default; imp.sRGBTexture = true; imp.maxTextureSize = 2048; imp.mipmapEnabled = true;
            imp.streamingMipmaps = true; imp.anisoLevel = 4; imp.textureCompression = TextureImporterCompression.CompressedHQ; imp.SaveAndReimport();
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(TerminalEmission);
            var m = AssetDatabase.LoadAssetAtPath<Material>(TerminalMat);
            if (!m) { m = new Material(src) { name = "MissionTerminal_Lit" }; AssetDatabase.CreateAsset(m, TerminalMat); }
            else { m.shader = src.shader; m.CopyPropertiesFromMaterial(src); m.shaderKeywords = src.shaderKeywords; }
            m.SetTexture("_EmissionMap", tex);
            m.SetColor("_EmissionColor", Color.white * TerminalEmissionStrength);
            m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;   // URP keeps _EMISSION only with an emissive GI flag
            EditorUtility.SetDirty(m);
            return new { material = TerminalMat, source = TerminalSrcMat, emissionMap = TerminalEmission, strength = TerminalEmissionStrength };
        }

        /// Retunes the LOD transition heights of the two lamp prefabs in place (same objects, so the installed instances
        /// and their scene-added lights are untouched). Post: LOD0 within ~33 m, LOD1 to ~66 m, LOD2 beyond (60° FOV, bias 2).
        public static string LodCuts()
        {
            var log = new List<string>();
            foreach (var (path, cuts) in new[] { (PostPrefab, new[] { .3f, .15f, .012f }), (WallPrefab, new[] { .12f, .06f, .006f }) })
            {
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var g = root.GetComponent<LODGroup>(); var lods = g.GetLODs();
                    for (int i = 0; i < lods.Length && i < cuts.Length; i++) lods[i].screenRelativeTransitionHeight = cuts[i];
                    g.SetLODs(lods);
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    log.Add(path + ": " + string.Join(", ", cuts));
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            return string.Join("\n", log);
        }

        /// Only the particle materials (re-running "build" would re-save the lamp prefabs under the installed instances).
        static object BuildFxMaterialsSaved() { var r = BuildFxMaterials(); AssetDatabase.SaveAssets(); return r; }

        static object BuildFxMaterials()
        {
            var puff = AssetDatabase.LoadAssetAtPath<Texture2D>(CookDir + "SoftPuff.png") ?? throw new Exception("SoftPuff.png missing");
            var steam = ParticleMaterial(ArtDir + "FX/NL_Steam.mat", true, false, puff, new Color(.9f, .92f, .94f, 1f), .35f);
            var haze = ParticleMaterial(ArtDir + "FX/NL_ExhaustHaze.mat", true, false, puff, new Color(.42f, .44f, .47f, 1f), 1.2f);
            // the barrel's own flame material: HDR base colour (an additive puff at 1.0 vanishes in daylight and reads
            // as faint wisps at night) and a short depth fade so tongues by the barrel wall are not erased
            var flame = ParticleMaterial(ArtDir + "FX/NL_BarrelFlame.mat", false, true, puff, new Color(2.2f, 1.25f, .5f, 1f), .35f);
            return new { steam = AssetDatabase.GetAssetPath(steam), haze = AssetDatabase.GetAssetPath(haze), flame = AssetDatabase.GetAssetPath(flame), reused = new[] { CookDir + "CookfireSmoke.mat", CookDir + "CookfireFlame.mat" } };
        }

        static Material ParticleMaterial(string path, bool lit, bool additive, Texture texture, Color color, float softFar)
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            var shader = Shader.Find(lit ? "Universal Render Pipeline/Particles/Simple Lit" : "Universal Render Pipeline/Particles/Unlit");
            if (!mat) { mat = new Material(shader) { name = Path.GetFileNameWithoutExtension(path) }; AssetDatabase.CreateAsset(mat, path); }
            mat.shader = shader;
            mat.SetTexture("_BaseMap", texture); mat.SetColor("_BaseColor", color);
            mat.SetFloat("_Surface", 1); mat.SetFloat("_Blend", additive ? 2 : 0);
            mat.SetFloat("_SoftParticlesEnabled", 1); mat.SetFloat("_SoftParticlesNearFadeDistance", 0); mat.SetFloat("_SoftParticlesFarFadeDistance", softFar);
            mat.SetFloat("_CameraFadingEnabled", 1); mat.SetFloat("_CameraNearFadeDistance", .4f); mat.SetFloat("_CameraFarFadeDistance", 2.2f);
            BaseShaderGUI.SetMaterialKeywords(mat, null, ParticleGUI.SetMaterialKeywords);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // ================================================================== install (one time)
        public static string Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            if (scene.GetRootGameObjects().Any(g => g.name == RootName))
                throw new Exception("Ward night life is already installed; edit it in place (retune / rebuildfx steps).");
            var postPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(PostPrefab) ?? throw new Exception("build first: " + PostPrefab);
            var wallPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(WallPrefab) ?? throw new Exception("build first: " + WallPrefab);
            var litMat = AssetDatabase.LoadAssetAtPath<Material>(TerminalMat) ?? throw new Exception("build first: " + TerminalMat);
            Directory.CreateDirectory(Evidence + "rollback");
            File.Copy(ScenePath, Evidence + "rollback/before-night-life.unity", true);
            var layout = Layout();
            var record = new Dictionary<string, object>();
            var root = new GameObject(RootName);
            SceneManagerMove(root, scene);
            var lampsRoot = Child(root.transform, "Street lamps");
            var wallRoot = Child(root.transform, "Wall lamps");
            var glowRoot = Child(root.transform, "Mission terminal glow");
            var circuitLights = new List<Light>();
            var fixtures = new List<object>();
            foreach (var f in layout["fixtures"])
            {
                var kind = (string)f["kind"];
                var name = (string)f["name"];
                var pos = V3(f["pos"]);
                if (kind == "post")
                {
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(postPrefab, scene);
                    inst.name = name; inst.transform.SetParent(lampsRoot, false);
                    inst.transform.SetPositionAndRotation(pos, Quaternion.Euler(0, (float)f["yaw"], 0));
                    var l = AddLampLight(inst.transform, "Lamp warm street light", PostLightLocal, Quaternion.Euler(90, 0, 0), f, 150f, 100f);
                    circuitLights.Add(l);
                    fixtures.Add(new { name, kind, pos = A(inst.transform.position), yaw = inst.transform.eulerAngles.y, light = A(l.transform.position) });
                }
                else
                {
                    var dir = Quaternion.Euler(0, (float)f["intoYaw"], 0) * Vector3.forward;
                    if (!SnapRay(pos - dir * 1.5f, dir, 6f, root.transform, out var hit, out var normal, out var what))
                        throw new Exception("no wall found for bracket " + name + " from " + pos);
                    var outward = new Vector3(normal.x, 0, normal.z);
                    if (outward.sqrMagnitude < .25f || Vector3.Dot(outward, -dir) < .5f) outward = -dir;
                    outward.Normalize();
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(wallPrefab, scene);
                    inst.name = name; inst.transform.SetParent(wallRoot, false);
                    inst.transform.SetPositionAndRotation(hit + outward * .01f, Quaternion.LookRotation(outward, Vector3.up));
                    var l = AddLampLight(inst.transform, "Lamp warm wall light", WallLightLocal, Quaternion.Euler(65, 0, 0), f, 130f, 75f);
                    circuitLights.Add(l);
                    fixtures.Add(new { name, kind, requested = A(pos), pos = A(inst.transform.position), wall = what, normal = A(normal), light = A(l.transform.position) });
                }
            }
            record["fixtures"] = fixtures;

            // mission terminals: lit material on the three scene instances (prefab-instance override), cool fills
            var terminals = new List<object>();
            foreach (var spec in layout["terminalFills"])
            {
                var t = Find(scene, (string)spec["terminal"]) ?? throw new Exception("terminal missing: " + spec["terminal"]);
                var r = t.GetComponentInChildren<MeshRenderer>(true) ?? throw new Exception("terminal renderer missing");
                var before = r.sharedMaterial;
                r.sharedMaterial = litMat;
                if (PrefabUtility.IsPartOfPrefabInstance(r)) PrefabUtility.RecordPrefabInstancePropertyModifications(r);
                var go = new GameObject(t.name + " screen fill"); go.transform.SetParent(glowRoot, false);
                go.transform.position = t.TransformPoint(V3(spec["local"]));
                var l = go.AddComponent<Light>(); l.type = LightType.Point; l.lightmapBakeType = LightmapBakeType.Realtime;
                var c = spec["color"]; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"]; l.shadows = LightShadows.None;
                circuitLights.Add(l);
                terminals.Add(new { terminal = PathOf(t), renderer = PathOf(r.transform), materialBefore = AssetDatabase.GetAssetPath(before), materialAfter = TerminalMat, fill = A(go.transform.position) });
            }
            record["terminals"] = terminals;

            // circuit: practical + night-only (shadows stay off; the circuit limits any shadow to 32 m anyway)
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include) ?? throw new Exception("Ward lighting clock circuit missing");
            int pBefore = circuit.practicalLights.Length, nBefore = circuit.nightOnlyLights.Length;
            circuit.practicalLights = circuit.practicalLights.Where(x => x).Concat(circuitLights).Distinct().ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(x => x).Concat(circuitLights).Distinct().ToArray();
            EditorUtility.SetDirty(circuit);
            record["circuit"] = new { practicalBefore = pBefore, practicalAfter = circuit.practicalLights.Length, nightOnlyBefore = nBefore, nightOnlyAfter = circuit.nightOnlyLights.Length, added = circuitLights.Select(x => PathOf(x.transform)).ToArray() };

            record["effects"] = BuildEffects(scene, root.transform, layout);
            AddReviewCameras(scene, layout);
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene)) throw new Exception("scene save failed");
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        static void SceneManagerMove(GameObject go, UnityEngine.SceneManagement.Scene scene)
        {
            if (go.scene != scene) UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(go, scene);
        }

        static Transform Child(Transform parent, string name)
        {
            var t = parent.Find(name);
            if (t) return t;
            var go = new GameObject(name); go.transform.SetParent(parent, false); return go.transform;
        }

        static Light AddLampLight(Transform parent, string name, Vector3 local, Quaternion rot, JToken spec, float outer, float inner)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            go.transform.localPosition = local; go.transform.localRotation = rot;
            var l = go.AddComponent<Light>();
            l.type = LightType.Spot; l.lightmapBakeType = LightmapBakeType.Realtime; l.renderMode = LightRenderMode.Auto;
            l.color = LampColor; l.spotAngle = outer; l.innerSpotAngle = inner;
            ApplyLightSpec(l, spec);
            return l;
        }

        static void ApplyLightSpec(Light l, JToken spec)
        {
            l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"];
            bool shadows = spec["shadows"] != null && (bool)spec["shadows"];
            l.shadows = shadows ? LightShadows.Soft : LightShadows.None;
            l.shadowStrength = .82f; l.shadowBias = .03f; l.shadowNormalBias = .08f; l.shadowNearPlane = .05f;
        }

        /// Nearest hit of a ray against the visible LOD0 / un-LODed meshes of the scene (the real masonry, not the old
        /// box colliders). Excludes the given root, shadow-only renderers and LOD1+ renderers.
        static bool SnapRay(Vector3 origin, Vector3 dir, float maxDist, Transform exclude, out Vector3 hit, out Vector3 normal, out string what)
        {
            hit = normal = default; what = null;
            float best = maxDist;
            var ray = new Ray(origin, dir.normalized);
            var lodHigher = new HashSet<Renderer>();
            foreach (var g in UnityEngine.Object.FindObjectsByType<LODGroup>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                var lods = g.GetLODs();
                for (int i = 1; i < lods.Length; i++) foreach (var r in lods[i].renderers) if (r) lodHigher.Add(r);
            }
            foreach (var mr in UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (!mr.enabled || mr.shadowCastingMode == ShadowCastingMode.ShadowsOnly || lodHigher.Contains(mr)) continue;
                if (exclude && mr.transform.IsChildOf(exclude)) continue;
                if (mr.transform.IsChildOf(GeneratedChunks())) continue;
                if (!mr.bounds.IntersectRay(ray, out float d0) || d0 > best) continue;
                var f = mr.GetComponent<MeshFilter>(); var mesh = f ? f.sharedMesh : null;
                if (!mesh) continue;
                var w2l = mr.transform.worldToLocalMatrix; var l2w = mr.transform.localToWorldMatrix;
                var o = w2l.MultiplyPoint3x4(ray.origin); var d = w2l.MultiplyVector(ray.direction);
                var v = mesh.vertices; var tri = mesh.triangles;
                for (int i = 0; i < tri.Length; i += 3)
                {
                    var a = v[tri[i]]; var b = v[tri[i + 1]]; var c = v[tri[i + 2]];
                    if (!RayTri(o, d, a, b, c, out float tl)) continue;
                    var wp = l2w.MultiplyPoint3x4(o + d * tl);
                    float dist = Vector3.Distance(ray.origin, wp);
                    if (dist >= best) continue;
                    best = dist; hit = wp;
                    normal = l2w.MultiplyVector(Vector3.Cross(b - a, c - a)).normalized;
                    if (Vector3.Dot(normal, ray.direction) > 0) normal = -normal;
                    what = PathOf(mr.transform);
                }
            }
            return what != null;
        }

        static Transform generated;
        static Transform GeneratedChunks()
        {
            if (generated) return generated;
            var c = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            generated = c && c.generatedRoot ? c.generatedRoot : null;
            return generated;
        }

        static bool RayTri(Vector3 o, Vector3 d, Vector3 a, Vector3 b, Vector3 c, out float t)
        {
            t = 0;
            var e1 = b - a; var e2 = c - a; var p = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, p);
            if (Mathf.Abs(det) < 1e-9f) return false;
            float inv = 1f / det; var s = o - a; float u = Vector3.Dot(s, p) * inv; if (u < 0 || u > 1) return false;
            var q = Vector3.Cross(s, e1); float v = Vector3.Dot(d, q) * inv; if (v < 0 || u + v > 1) return false;
            t = Vector3.Dot(e2, q) * inv; return t > 0;
        }

        // ================================================================== ambient life
        /// Highest point of a renderer's mesh (optionally only vertices within radius of an XZ point): the centre of the
        /// top vertex cluster and its horizontal spread.
        static (Vector3 top, float spread) MeshTop(Renderer r, Vector2? near, float radius)
        {
            var mesh = r.GetComponent<MeshFilter>().sharedMesh; var m = r.localToWorldMatrix;
            var pts = mesh.vertices.Select(v => m.MultiplyPoint3x4(v));
            if (near.HasValue) pts = pts.Where(p => Vector2.Distance(new Vector2(p.x, p.z), near.Value) <= radius);
            var list = pts.ToList();
            if (list.Count == 0) throw new Exception("no vertices near " + near + " on " + PathOf(r.transform));
            float maxY = list.Max(p => p.y);
            var top = list.Where(p => p.y > maxY - .03f).ToList();
            var c = new Vector3(top.Average(p => p.x), maxY, top.Average(p => p.z));
            float spread = top.Max(p => new Vector2(p.x - c.x, p.z - c.z).magnitude);
            return (c, spread);
        }

        static Renderer Lod0(Transform t) => t.GetComponentsInChildren<Renderer>(true).FirstOrDefault(r => r.name == "LOD0") ?? t.GetComponentInChildren<Renderer>(true);

        public static Dictionary<string, Vector3> EffectAnchors(UnityEngine.SceneManagement.Scene scene, JObject layout, List<object> log)
        {
            var anchors = new Dictionary<string, Vector3>();
            foreach (var e in layout["effects"])
            {
                var kind = (string)e["kind"]; var name = (string)e["name"];
                Vector3 p; float spread = 0; string src;
                if (e["anchor"] != null)
                {
                    var t = Find(scene, (string)e["anchor"]) ?? throw new Exception("anchor missing: " + e["anchor"]);
                    var b = Lod0(t).bounds; src = PathOf(t);
                    p = new Vector3(b.center.x, b.max.y, b.center.z);
                }
                else
                {
                    var t = Find(scene, (string)e["renderer"]) ?? throw new Exception("renderer missing: " + e["renderer"]);
                    var r = t.GetComponent<Renderer>(); src = PathOf(t);
                    Vector2? near = e["near"] != null && e["near"].Type == JTokenType.Array ? new Vector2((float)e["near"][0], (float)e["near"][1]) : (Vector2?)null;
                    (p, spread) = MeshTop(r, near, (float)e["radius"]);
                }
                anchors[name] = p;
                log?.Add(new { name, kind, source = src, anchor = A(p), topSpread = Math.Round(spread, 3) });
            }
            return anchors;
        }

        static object BuildEffects(UnityEngine.SceneManagement.Scene scene, Transform root, JObject layout)
        {
            var log = new List<object>();
            var anchors = EffectAnchors(scene, layout, log);
            var fxRoot = Child(root, "Ambient life");
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var smokeMat = AssetDatabase.LoadAssetAtPath<Material>(CookDir + "CookfireSmoke.mat");
            var flameMat = AssetDatabase.LoadAssetAtPath<Material>(ArtDir + "FX/NL_BarrelFlame.mat") ?? AssetDatabase.LoadAssetAtPath<Material>(CookDir + "CookfireFlame.mat");
            var steamMat = AssetDatabase.LoadAssetAtPath<Material>(ArtDir + "FX/NL_Steam.mat");
            var hazeMat = AssetDatabase.LoadAssetAtPath<Material>(ArtDir + "FX/NL_ExhaustHaze.mat");
            if (!smokeMat || !flameMat || !steamMat || !hazeMat) throw new Exception("particle materials missing (build first)");
            foreach (var e in layout["effects"])
            {
                var kind = (string)e["kind"]; var name = (string)e["name"]; var a = anchors[name];
                var go = new GameObject(name); go.transform.SetParent(fxRoot, false); go.transform.position = a;
                var life = go.AddComponent<AmbientLife>(); life.session = session; life.clock = clock;
                var systems = new List<ParticleSystem>();
                switch (kind)
                {
                    case "barrel_fire":
                    {
                        go.transform.position = a + Vector3.down * .12f;          // just inside the open rim
                        var flames = NewSystem("Barrel flames", go.transform, Vector3.zero, flameMat, out var main);
                        main.startLifetime = new ParticleSystem.MinMaxCurve(.35f, .7f); main.startSpeed = new ParticleSystem.MinMaxCurve(.6f, 1.15f);
                        main.startSize = new ParticleSystem.MinMaxCurve(.2f, .38f); main.startRotation = new ParticleSystem.MinMaxCurve(0, 0);
                        main.startColor = new Color(1f, .62f, .26f, 1f); main.maxParticles = 56;
                        var em = flames.emission; em.rateOverTime = 32;
                        var sh = flames.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 8; sh.radius = .14f; sh.rotation = new Vector3(-90, 0, 0);
                        var sz = flames.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, 1, 1, .15f));
                        var col = flames.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(1f, .82f, .45f), new Color(1f, .3f, .08f), 1f, .1f);
                        var fn = flames.noise; fn.enabled = true; fn.strength = .25f; fn.frequency = 2.5f; fn.scrollSpeed = 1.2f;
                        var fr = flames.GetComponent<ParticleSystemRenderer>();          // tongues, not balls
                        fr.renderMode = ParticleSystemRenderMode.Stretch; fr.velocityScale = .22f; fr.lengthScale = 1.4f;
                        systems.Add(flames);
                        var embers = NewSystem("Barrel embers", go.transform, new Vector3(0, .05f, 0), flameMat, out main);
                        main.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 2.6f); main.startSpeed = new ParticleSystem.MinMaxCurve(.7f, 1.6f);
                        main.startSize = new ParticleSystem.MinMaxCurve(.012f, .03f); main.startColor = new Color(1f, .55f, .2f, 1f); main.maxParticles = 30;
                        em = embers.emission; em.rateOverTime = 5;
                        sh = embers.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 18; sh.radius = .14f; sh.rotation = new Vector3(-90, 0, 0);
                        var noise = embers.noise; noise.enabled = true; noise.strength = .6f; noise.frequency = 1.2f;
                        col = embers.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(1f, .7f, .3f), new Color(1f, .25f, .05f), 1f, .05f);
                        systems.Add(embers);
                        var smoke = NewSystem("Barrel smoke", go.transform, new Vector3(0, .22f, 0), smokeMat, out main);
                        SmokeSettings(smoke, main, 7f, .3f, .55f, 5f, 7.5f, 3.6f, .8f, 70, new Color(.62f, .59f, .56f, 1f));
                        main.startSpeed = new ParticleSystem.MinMaxCurve(.08f, .18f);
                        var bv = smoke.velocityOverLifetime; bv.y = new ParticleSystem.MinMaxCurve(.18f, .32f); bv.x = new ParticleSystem.MinMaxCurve(.18f, .4f);
                        var bc = smoke.colorOverLifetime; bc.color = Fade(new Color(.5f, .46f, .42f), new Color(.66f, .63f, .6f), .8f, .03f);
                        systems.Add(smoke);
                        var lgo = new GameObject("Barrel fire light"); lgo.transform.SetParent(go.transform, false); lgo.transform.localPosition = new Vector3(0, .55f, 0);
                        var l = lgo.AddComponent<Light>(); l.type = LightType.Point; l.lightmapBakeType = LightmapBakeType.Realtime;
                        l.color = new Color(1f, .55f, .25f); l.range = 6.5f; l.intensity = 1.7f; l.shadows = LightShadows.None;
                        life.fireLight = l; life.fireIntensity = 1.7f; life.flicker = .35f; life.flickerSpeed = 7f; life.fireDayStrength = 0f;
                        life.dayTint = Color.white; life.nightTint = new Color(.8f, .8f, .8f, 1f);   // HDR flames: full by day, a little lower at night (bloom)
                        break;
                    }
                    case "flue_smoke":
                    {
                        go.transform.position = a + Vector3.up * .05f;
                        var smoke = NewSystem("Flue smoke", go.transform, Vector3.zero, smokeMat, out var main);
                        SmokeSettings(smoke, main, 5f, .3f, .5f, 7f, 10f, 4.6f, .38f, 70, new Color(.68f, .66f, .64f, .9f));
                        systems.Add(smoke);
                        life.dayTint = Color.white; life.nightTint = new Color(.75f, .75f, .78f, 1f);
                        break;
                    }
                    case "steam_puffs":
                    {
                        go.transform.position = a + new Vector3(.12f, .05f, 0);
                        var steam = NewSystem("Relief steam", go.transform, Vector3.zero, steamMat, out var main);
                        main.prewarm = false;
                        main.startLifetime = new ParticleSystem.MinMaxCurve(1.6f, 2.8f); main.startSpeed = new ParticleSystem.MinMaxCurve(.7f, 1.2f);
                        main.startSize = new ParticleSystem.MinMaxCurve(.2f, .34f); main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
                        main.startColor = new Color(.92f, .94f, .97f, .9f); main.maxParticles = 80;
                        var em = steam.emission; em.rateOverTime = 24;
                        var sh = steam.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 14; sh.radius = .03f; sh.rotation = new Vector3(-35, 90, 0);
                        var vel = steam.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
                        vel.x = new ParticleSystem.MinMaxCurve(.15f, .35f); vel.y = new ParticleSystem.MinMaxCurve(.35f, .6f); vel.z = new ParticleSystem.MinMaxCurve(.0f, .12f);
                        var lim = steam.limitVelocityOverLifetime; lim.enabled = true; lim.limit = .9f; lim.dampen = .25f;
                        var sz = steam.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .6f, 1, 5f));
                        var col = steam.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(.97f, .98f, 1f), new Color(.88f, .9f, .93f), .9f, .03f);
                        var rot = steam.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-.5f, .5f);
                        systems.Add(steam);
                        life.puffSeconds = 1.4f; life.minGap = 3f; life.maxGap = 6.5f;
                        life.dayTint = Color.white; life.nightTint = new Color(.8f, .82f, .85f, 1f);
                        break;
                    }
                    case "exhaust_haze":
                    {
                        go.transform.position = a + new Vector3(0, .02f, 0);
                        var haze = NewSystem("Exhaust haze", go.transform, Vector3.zero, hazeMat, out var main);
                        main.startLifetime = new ParticleSystem.MinMaxCurve(1.4f, 2.4f); main.startSpeed = new ParticleSystem.MinMaxCurve(.35f, .6f);
                        main.startSize = new ParticleSystem.MinMaxCurve(.25f, .4f); main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
                        main.startColor = new Color(.66f, .68f, .7f, .45f); main.maxParticles = 24;
                        var em = haze.emission; em.rateOverTime = 7;
                        var sh = haze.shape; sh.shapeType = ParticleSystemShapeType.Circle; sh.radius = .12f; sh.rotation = new Vector3(-90, 0, 0);
                        var vel = haze.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
                        vel.x = new ParticleSystem.MinMaxCurve(.2f, .45f); vel.y = new ParticleSystem.MinMaxCurve(.1f, .25f); vel.z = new ParticleSystem.MinMaxCurve(.03f, .12f);
                        var sz = haze.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .7f, 1, 3f));
                        var col = haze.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(.62f, .63f, .65f), new Color(.68f, .68f, .68f), .8f, .12f);
                        systems.Add(haze);
                        life.dayTint = Color.white; life.nightTint = new Color(.7f, .7f, .72f, 1f);
                        break;
                    }
                    default: throw new Exception("unknown effect kind " + kind);
                }
                life.systems = systems.ToArray();
            }
            return log;
        }

        /// Thin wind-drifted smoke (the cookfire's look): the same world wind as the market smoke (towards +X, a little +Z).
        static void SmokeSettings(ParticleSystem ps, ParticleSystem.MainModule main, float rate, float size0, float size1, float life0, float life1, float grow, float alpha, int max, Color tint)
        {
            main.startLifetime = new ParticleSystem.MinMaxCurve(life0, life1); main.startSpeed = new ParticleSystem.MinMaxCurve(.25f, .45f);
            main.startSize = new ParticleSystem.MinMaxCurve(size0, size1); main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
            main.startColor = tint; main.maxParticles = max;
            var em = ps.emission; em.rateOverTime = rate;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 6; sh.radius = .06f; sh.rotation = new Vector3(-90, 0, 0);
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(.3f, .6f); vel.y = new ParticleSystem.MinMaxCurve(.3f, .5f); vel.z = new ParticleSystem.MinMaxCurve(.05f, .2f);
            var sz = ps.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .6f, 1, grow));
            var col = ps.colorOverLifetime; col.enabled = true; col.color = Fade(new Color(.42f, .38f, .34f), new Color(.6f, .56f, .52f), alpha, .08f);
            var rot = ps.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-.35f, .35f);
            var noise = ps.noise; noise.enabled = true; noise.strength = .15f; noise.frequency = .4f; noise.scrollSpeed = .2f;
        }

        static ParticleSystem NewSystem(string name, Transform parent, Vector3 local, Material mat, out ParticleSystem.MainModule main)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false); go.transform.localPosition = local;
            var ps = go.AddComponent<ParticleSystem>();
            main = ps.main;
            main.loop = true; main.prewarm = true; main.duration = 10; main.playOnAwake = true;
            main.simulationSpace = ParticleSystemSimulationSpace.World; main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            var renderer = go.GetComponent<ParticleSystemRenderer>();
            renderer.sharedMaterial = mat; renderer.shadowCastingMode = ShadowCastingMode.Off; renderer.receiveShadows = false;
            renderer.sortMode = ParticleSystemSortMode.Distance;
            return ps;
        }

        static ParticleSystem.MinMaxGradient Fade(Color a, Color b, float peak, float fadeIn)
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(a, 0), new GradientColorKey(b, 1) },
                      new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(peak, fadeIn), new GradientAlphaKey(peak * .6f, .6f), new GradientAlphaKey(0, 1) });
            return new ParticleSystem.MinMaxGradient(g);
        }

        /// Recreates the "Ambient life" group from the layout (no clock bindings live there, so this is safe to repeat).
        public static string RebuildEffects()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName) ?? throw new Exception("not installed");
            var old = root.transform.Find("Ambient life");
            if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
            var log = BuildEffects(scene, root.transform, Layout());
            AddReviewCameras(scene, Layout());
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            var json = JsonConvert.SerializeObject(log, Formatting.Indented);
            File.WriteAllText(Evidence + "rebuild-effects.json", json);
            return json;
        }

        /// Re-applies light intensity/range/shadows from night-layout.json to the installed lights in place (same objects,
        /// so the Ward lighting clock bindings survive), and the terminal fills and the terminal emission strength.
        public static string Retune()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName) ?? throw new Exception("not installed");
            var layout = Layout(); var log = new List<string>();
            foreach (var f in layout["fixtures"])
            {
                var parent = root.transform.Find(((string)f["kind"] == "post" ? "Street lamps/" : "Wall lamps/") + (string)f["name"]);
                var l = parent ? parent.GetComponentInChildren<Light>(true) : null;
                if (!l) { log.Add("missing " + f["name"]); continue; }
                ApplyLightSpec(l, f);
                log.Add($"{f["name"]}: {l.intensity} / {l.range} m / {l.shadows}");
            }
            foreach (var spec in layout["terminalFills"])
            {
                var t = root.transform.Find("Mission terminal glow/" + ((string)spec["terminal"]).Split('/').Last() + " screen fill");
                var l = t ? t.GetComponent<Light>() : null;
                if (!l) { log.Add("missing fill " + spec["terminal"]); continue; }
                l.intensity = (float)spec["intensity"]; l.range = (float)spec["range"];
                var c = spec["color"]; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                log.Add($"{t.name}: {l.intensity} / {l.range} m");
            }
            var m = AssetDatabase.LoadAssetAtPath<Material>(TerminalMat);
            if (m) { m.SetColor("_EmissionColor", Color.white * TerminalEmissionStrength); EditorUtility.SetDirty(m); AssetDatabase.SaveAssets(); }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return string.Join("\n", log);
        }

        /// Brings the installed fixtures in line with night-layout.json: removes fixtures no longer in the layout (and
        /// their lights from the circuit), adds new ones (registered), and moves/re-snaps existing ones in place (same
        /// light objects, so their clock bindings survive). Light settings are applied as in Retune.
        public static string Relayout()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName) ?? throw new Exception("not installed");
            var layout = Layout(); var log = new List<object>();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include) ?? throw new Exception("circuit missing");
            var lampsRoot = Child(root.transform, "Street lamps"); var wallRoot = Child(root.transform, "Wall lamps");
            var wanted = new HashSet<string>(layout["fixtures"].Select(f => (string)f["name"]));
            foreach (var t in lampsRoot.Cast<Transform>().Concat(wallRoot.Cast<Transform>()).ToList())
            {
                if (wanted.Contains(t.name)) continue;
                var gone = t.GetComponentsInChildren<Light>(true);
                circuit.practicalLights = circuit.practicalLights.Where(l => l && !gone.Contains(l)).ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !gone.Contains(l)).ToArray();
                log.Add(new { removed = PathOf(t) });
                UnityEngine.Object.DestroyImmediate(t.gameObject);
            }
            var added = new List<Light>();
            foreach (var f in layout["fixtures"])
            {
                var kind = (string)f["kind"]; var name = (string)f["name"]; var pos = V3(f["pos"]);
                var parentRoot = kind == "post" ? lampsRoot : wallRoot;
                var inst = parentRoot.Find(name)?.gameObject;
                bool isNew = !inst;
                if (isNew)
                {
                    inst = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(kind == "post" ? PostPrefab : WallPrefab), scene);
                    inst.name = name; inst.transform.SetParent(parentRoot, false);
                }
                if (kind == "post") inst.transform.SetPositionAndRotation(pos, Quaternion.Euler(0, (float)f["yaw"], 0));
                else
                {
                    var dir = Quaternion.Euler(0, (float)f["intoYaw"], 0) * Vector3.forward;
                    if (!SnapRay(pos - dir * 1.5f, dir, 6f, root.transform, out var hit, out var normal, out var what)) throw new Exception("no wall for " + name);
                    var outward = new Vector3(normal.x, 0, normal.z);
                    if (outward.sqrMagnitude < .25f || Vector3.Dot(outward, -dir) < .5f) outward = -dir;
                    outward.Normalize();
                    inst.transform.SetPositionAndRotation(hit + outward * .01f, Quaternion.LookRotation(outward, Vector3.up));
                }
                var l = inst.GetComponentInChildren<Light>(true);
                if (!l)
                {
                    l = kind == "post" ? AddLampLight(inst.transform, "Lamp warm street light", PostLightLocal, Quaternion.Euler(90, 0, 0), f, 150f, 100f)
                                       : AddLampLight(inst.transform, "Lamp warm wall light", WallLightLocal, Quaternion.Euler(65, 0, 0), f, 130f, 75f);
                    added.Add(l);
                }
                else ApplyLightSpec(l, f);
                log.Add(new { name, kind, isNew, pos = A(inst.transform.position), light = A(l.transform.position), l.intensity, l.range });
            }
            circuit.practicalLights = circuit.practicalLights.Where(x => x).Concat(added).Distinct().ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(x => x).Concat(added).Distinct().ToArray();
            EditorUtility.SetDirty(circuit);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            var json = JsonConvert.SerializeObject(log, Formatting.Indented);
            File.WriteAllText(Evidence + "relayout.json", json);
            return json;
        }

        // ================================================================== review cameras
        static List<(string name, Vector3 pos, Vector3 target, float fov)> Views(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var anchors = EffectAnchors(scene, layout, null);
            var v = new List<(string, Vector3, Vector3, float)>
            {
                ("cam_nl_courtyard", new Vector3(2.6f, 1.65f, -9.6f), new Vector3(12f, 1.4f, -19f), 60),
                ("cam_nl_terminals", new Vector3(8.2f, 1.65f, -8.6f), new Vector3(8f, 1.25f, -14f), 55),
                ("cam_nl_lattice", new Vector3(7f, 1.65f, -29f), new Vector3(0f, 1.6f, -38.5f), 60),
                ("cam_nl_hall_corner", new Vector3(4f, 1.65f, -24f), new Vector3(-3f, 1.3f, -30f), 60),
                ("cam_nl_hill_benches", new Vector3(-13.5f, 1.65f, -4f), new Vector3(-7.6f, .9f, .6f), 60),
                ("cam_nl_apron_south", new Vector3(38f, 1.65f, 2f), new Vector3(44.5f, 2f, -13.5f), 60),
                ("cam_nl_apron_north", new Vector3(38f, 1.65f, 3f), new Vector3(44.5f, 2f, 18f), 60),
                ("cam_nl_south_collapse", new Vector3(9f, 1.65f, -33f), new Vector3(11f, 1.6f, -43.5f), 60),
                ("cam_nl_south_lane", new Vector3(-29f, 1.65f, -38.5f), new Vector3(-12f, 2.2f, -43f), 60),
                ("cam_nl_north_collapse", new Vector3(-47.5f, 1.65f, 33f), new Vector3(-45f, 2.2f, 43.5f), 60),
                ("cam_nl_rampart_south", new Vector3(38.5f, 1.65f, -21f), new Vector3(45.5f, 2.6f, -26.5f), 60),
                ("cam_nl_market_fire", new Vector3(-32.0f, 1.65f, -13.2f), new Vector3(-32.1f, 1.35f, -9.2f), 60),
                ("cam_nl_air_water_steam", new Vector3(-12.8f, 1.65f, -11.5f), new Vector3(-17.6f, 2.4f, -7.9f), 60),
                ("cam_nl_generator", new Vector3(26.8f, 1.65f, -11.2f), new Vector3(30.3f, .8f, -14.9f), 60),
            };
            if (anchors.TryGetValue("Repairs flue smoke", out var rf)) v.Add(("cam_nl_repairs_flue", new Vector3(9.5f, 1.65f, -3.5f), rf + Vector3.up * 1.2f, 60));
            if (anchors.TryGetValue("Salvage stovepipe smoke", out var sp)) v.Add(("cam_nl_salvage_stack", new Vector3(-8f, 1.65f, 9f), sp + Vector3.up * 1.2f, 60));
            return v;
        }

        public static string ReviewCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            AddReviewCameras(scene, Layout());
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "cameras";
        }

        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            SceneManagerMove(root, scene);
            foreach (var (name, pos, target, fov) in Views(scene, layout))
            {
                var go = new GameObject(name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var c = go.AddComponent<Camera>(); c.enabled = false; c.fieldOfView = fov; c.nearClipPlane = .05f;
            }
        }

        /// Editor captures (saved-scene lighting, i.e. the authored afternoon, particles simulated 4 s): geometry checks
        /// only; night is judged in the native player. Filter: "cam_nl_a+cam_nl_b" or a prefix. Max 6 per run (VRAM).
        public static string Capture(string outDir, string filter)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var views = Views(scene, Layout()).Where(v => string.IsNullOrEmpty(filter) || filter.Split('+').Any(f => v.name.StartsWith(f))).Take(6).ToList();
            foreach (var ps in UnityEngine.Object.FindObjectsByType<ParticleSystem>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                if (ps.transform.root.name == RootName) ps.Simulate(4f, false, true);
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        /// Debug close-ups of the effects (editor, saved afternoon light, particles simulated): not review cameras.
        public static string FxProbe(string outDir)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var anchors = EffectAnchors(scene, Layout(), null);
            foreach (var ps in UnityEngine.Object.FindObjectsByType<ParticleSystem>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                if (ps.transform.root.name == RootName) ps.Simulate(5f, false, true);
            var b = anchors["Barrel fire"]; var st = anchors["Air + Water relief steam"]; var g = anchors["Generator exhaust haze"];
            var views = new List<(string, Vector3, Vector3, float)>
            {
                ("probe_barrel_side", b + new Vector3(0, .9f, 3.2f), b + new Vector3(.4f, .6f, 0), 50),
                ("probe_barrel_down", b + new Vector3(1.8f, 1.4f, -1.2f), b + new Vector3(0, .3f, 0), 50),
                ("probe_steam", st + new Vector3(3.2f, -.9f, -1.6f), st + new Vector3(.4f, .4f, 0), 50),
                ("probe_haze", g + new Vector3(-2.2f, .7f, 2.4f), g + new Vector3(.2f, .3f, 0), 50),
            };
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        /// Particle counts and bounds after a 5 s simulation (debug, -nographics).
        public static string FxStats()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var rows = new List<object>();
            foreach (var ps in UnityEngine.Object.FindObjectsByType<ParticleSystem>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (ps.transform.root.name != RootName && !ps.name.StartsWith("Cookfire")) continue;
                ps.Simulate(5f, false, true);
                var parts = new ParticleSystem.Particle[ps.main.maxParticles];
                int n = ps.GetParticles(parts);
                var r = ps.GetComponent<ParticleSystemRenderer>();
                rows.Add(new
                {
                    path = PathOf(ps.transform), n, pos = A(ps.transform.position),
                    first = n > 0 ? A(parts[0].position) : null, size = n > 0 ? parts[0].GetCurrentSize(ps) : 0,
                    color = n > 0 ? parts[0].GetCurrentColor(ps).ToString() : null,
                    bounds = r ? A(r.bounds.center) : null, bsize = r ? A(r.bounds.size) : null,
                    mat = r && r.sharedMaterial ? r.sharedMaterial.name : null,
                });
            }
            var json = JsonConvert.SerializeObject(rows, Formatting.Indented);
            File.WriteAllText(Evidence + "fxstats.json", json);
            return json;
        }

        // ================================================================== verify
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = Layout();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (root)
            {
                r["active"] = root.activeSelf;
                var fixtures = root.GetComponentsInChildren<LODGroup>(true);
                r["fixtures"] = fixtures.Length;
                r["expectedFixtures"] = layout["fixtures"].Count();
                r["prefabLinked"] = fixtures.Count(f => PrefabUtility.IsPartOfPrefabInstance(f.gameObject));
                r["nonUniformScale"] = fixtures.Where(f => (f.transform.lossyScale - Vector3.one).sqrMagnitude > 1e-6).Select(f => PathOf(f.transform)).ToArray();
                var rends = root.GetComponentsInChildren<Renderer>(true);
                r["renderers"] = rends.Length;
                r["missingMaterials"] = rends.Count(x => x.sharedMaterials.Any(m => !m));
                var lights = root.GetComponentsInChildren<Light>(true);
                var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
                r["lights"] = lights.Select(l => new
                {
                    path = PathOf(l.transform), type = l.type.ToString(), l.intensity, l.range, spot = l.type == LightType.Spot ? l.spotAngle : 0, shadows = l.shadows.ToString(),
                    practical = circuit && circuit.practicalLights.Contains(l), nightOnly = circuit && circuit.nightOnlyLights.Contains(l),
                    ambientLife = l.GetComponentInParent<AmbientLife>() != null,
                }).ToArray();
                r["circuitLightsMissing"] = lights.Where(l => !l.GetComponentInParent<AmbientLife>() && !(circuit && circuit.practicalLights.Contains(l) && circuit.nightOnlyLights.Contains(l))).Select(l => PathOf(l.transform)).ToArray();
                var lives = root.GetComponentsInChildren<AmbientLife>(true);
                r["effects"] = lives.Select(l => new
                {
                    path = PathOf(l.transform), pos = A(l.transform.position), systems = l.systems.Length, sessionBound = l.session != null, clockBound = l.clock != null,
                    maxParticles = l.systems.Sum(s => s ? s.main.maxParticles : 0), fireLight = l.fireLight ? PathOf(l.fireLight.transform) : null, l.puffSeconds,
                    materials = l.systems.Where(s => s).Select(s => s.GetComponent<ParticleSystemRenderer>().sharedMaterial ? s.GetComponent<ParticleSystemRenderer>().sharedMaterial.name : null).ToArray(),
                }).ToArray();
                long[] tri = new long[3];
                foreach (var g in fixtures) { var lods = g.GetLODs(); for (int i = 0; i < lods.Length && i < 3; i++) tri[i] += lods[i].renderers.Where(x => x && x.shadowCastingMode != ShadowCastingMode.ShadowsOnly).Sum(x => Tris(x.GetComponent<MeshFilter>()?.sharedMesh)); }
                r["fixtureTriangles"] = new { lod0 = tri[0], lod1 = tri[1], lod2 = tri[2] };
            }
            r["terminals"] = TerminalPaths.Select(p =>
            {
                var t = Find(scene, p); var mr = t ? t.GetComponentInChildren<MeshRenderer>(true) : null;
                return new { path = p, material = mr && mr.sharedMaterial ? AssetDatabase.GetAssetPath(mr.sharedMaterial) : null, prefabLinked = t && PrefabUtility.IsPartOfPrefabInstance(t.gameObject) };
            }).ToArray();
            var lit = AssetDatabase.LoadAssetAtPath<Material>(TerminalMat);
            r["terminalMaterial"] = lit ? new { emission = lit.GetColor("_EmissionColor").r, keyword = lit.IsKeywordEnabled("_EMISSION"), map = lit.GetTexture("_EmissionMap") ? lit.GetTexture("_EmissionMap").name : null, gi = lit.globalIlluminationFlags.ToString() } : null;
            r["originalTerminalMaterialEmission"] = AssetDatabase.LoadAssetAtPath<Material>(TerminalSrcMat)?.GetColor("_EmissionColor").maxColorComponent;
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; r["rootIsChunkSource"] = root && chunks.sourceRoots.Any(s => s && (s == root.transform || root.transform.IsChildOf(s))); }
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            r["reviewCameras"] = cams ? cams.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ================================================================== A/B builds from one snapshot
        /// "on" writes two scene copies of the saved scene (night life on / off: root inactive and the terminals back on
        /// their original material) and builds the on copy to Builds/nl-ab-on; "off" builds the off copy to
        /// Builds/nl-ab-off and deletes both copies. The saved scene itself is never toggled. Run one build per Editor job.
        const string AbOnCopy = "Assets/AthenHill/Scenes/__nl_ab_on.unity", AbOffCopy = "Assets/AthenHill/Scenes/__nl_ab_off.unity";

        static string AbBuild(string arm)
        {
            string src;
            if (arm == "on")
            {
                var scene = EditorSceneManager.OpenScene(ScenePath);
                var root = scene.GetRootGameObjects().First(g => g.name == RootName);
                root.SetActive(true);
                if (!EditorSceneManager.SaveScene(scene, AbOnCopy, true)) throw new Exception("could not write " + AbOnCopy);
                root.SetActive(false);
                var orig = AssetDatabase.LoadAssetAtPath<Material>(TerminalSrcMat);
                foreach (var p in TerminalPaths) { var mr = Find(scene, p).GetComponentInChildren<MeshRenderer>(true); mr.sharedMaterial = orig; }
                if (!EditorSceneManager.SaveScene(scene, AbOffCopy, true)) throw new Exception("could not write " + AbOffCopy);
                src = AbOnCopy;
            }
            else
            {
                if (!File.Exists(AbOffCopy)) throw new Exception("Run abbuild:on first (it writes the scene snapshot for both arms).");
                src = AbOffCopy;
            }
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneLinux64, false);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneLinux64, new[] { GraphicsDeviceType.OpenGLCore });
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { src }, locationPathName = "Builds/nl-ab-" + arm + "/AthenHill.x86_64",
                    target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
                });
                if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("A/B build failed: " + arm);
                return "nl-ab-" + arm + " " + report.summary.totalTime.TotalSeconds.ToString("0") + " s";
            }
            finally
            {
                if (arm == "off") { AssetDatabase.DeleteAsset(AbOnCopy); AssetDatabase.DeleteAsset(AbOffCopy); }
            }
        }

        // ================================================================== survey (read-only)
        public static string Survey()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).ToArray();
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var practical = new HashSet<Light>(circuit ? circuit.practicalLights.Where(l => l) : Enumerable.Empty<Light>());
            var nightOnly = new HashSet<Light>(circuit ? circuit.nightOnlyLights.Where(l => l) : Enumerable.Empty<Light>());
            var lights = all.Select(t => t.GetComponent<Light>()).Where(l => l).Select(l => new
            {
                path = PathOf(l.transform), active = l.gameObject.activeInHierarchy, l.enabled, type = l.type.ToString(),
                pos = A(l.transform.position), fwd = A(l.transform.forward), l.range, l.intensity, color = new[] { l.color.r, l.color.g, l.color.b },
                spot = l.type == LightType.Spot ? new[] { l.innerSpotAngle, l.spotAngle } : null, shadows = l.shadows.ToString(),
                practical = practical.Contains(l), nightOnly = nightOnly.Contains(l), flicker = l.GetComponent<FireFlicker>() != null,
            }).ToArray();
            var cams = all.Select(t => t.GetComponent<Camera>()).Where(c => c).Select(c => new
            {
                name = c.name, path = PathOf(c.transform), pos = A(c.transform.position), fwd = A(c.transform.forward), c.fieldOfView, c.enabled,
            }).ToArray();
            var r = new Dictionary<string, object>
            {
                ["circuit"] = circuit ? new { circuit.daytimeStrength, circuit.fullLightDistance, circuit.culledLightDistance, circuit.shadowDistance, practical = circuit.practicalLights.Length, nightOnly = circuit.nightOnlyLights.Length } : null,
                ["lightCount"] = lights.Length,
                ["activeShadowedLights"] = lights.Count(l => l.active && l.enabled && l.shadows != "None"),
                ["lights"] = lights,
                ["cameras"] = cams,
            };
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "survey-lights.json", json);
            return "survey: " + lights.Length + " lights, " + cams.Length + " cameras";
        }

        // ================================================================== batch
        /// -executeMethod AthenHill.Editor.NightLifePass.RunBatch --steps build,install,verify [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "verify").Split(',');
            var outDir = Arg("--out", Evidence + "editor");
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "survey" => Survey(),
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "cameras" => ReviewCameras(),
                        "retune" => Retune(),
                        "rebuildfx" => RebuildEffects(),
                        "relayout" => Relayout(),
                        "capture" => Capture(outDir, parts.Length > 1 ? parts[1] : ""),
                        "fxprobe" => FxProbe(outDir),
                        "fxstats" => FxStats(),
                        "fxmats" => JsonConvert.SerializeObject(BuildFxMaterialsSaved()),
                        "lodcuts" => LodCuts(),
                        "abbuild" => AbBuild(parts[1]),
                        "abclean" => (AssetDatabase.DeleteAsset(AbOnCopy) | AssetDatabase.DeleteAsset(AbOffCopy)) ? "scene copies deleted" : "no scene copies",
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("NightLifePass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
