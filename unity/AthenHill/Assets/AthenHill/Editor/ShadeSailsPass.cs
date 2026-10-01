using System;
using System.Collections.Generic;
using System.Globalization;
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
    /// 1 October 2026: shade sails with festoon bulbs over the big bare spaces (art-direction review item 7: "The largest
    /// open spaces have nothing overhead and nothing to break the paving: the courtyard by the terminals, the market floor,
    /// the West Gate apron and the Lattice court").
    ///
    /// Four tensioned sails in patched canvas (madder, indigo, natural and natural-with-indigo cloths), form-found with the
    /// force density method in art/shade_sails_20261001 (formfind.py, sails.py layout + validation, author_sails.py
    /// Blender geometry, make_textures.py canvas maps). Each site is one prefab (Prefabs/ShadeSails/SS_&lt;Site&gt;.prefab)
    /// with three LODGroups: Sail (canvas, hem, corner plates and hardware; the sail's shadow at every distance comes
    /// from a ShadowsOnly copy of the coarse canvas 4 cm below it, so the cloth never shadows itself), Rig (poles, stone footings or sandbagged base plates,
    /// guys and anchors, band clamps on the retrofit service poles; poles and stone cast at LOD0 only) and Festoons
    /// (cable, lampholders, bulbs; no shadows), plus unshadowed festoon lights (practical + night-only on the Ward
    /// lighting clock) and colliders on the poles, footings, ballast and guy anchors only — and one camera-only
    /// collider per sail (the coarse canvas, both windings, 3.6 m+ above the paving) so the follow camera stays under it.
    ///
    /// The canvas uses Athen Hill/Ward Ground Cover (the Lit-derived ground-cover shader: two-sided, alpha-clipped holes,
    /// sun and ambient transmission through the cloth; its wind is switched off). Menu: Athen Hill → Shade sails →
    /// Build assets, Install (one time), Verify saved scene, Add review cameras. Batch: RunBatch --steps
    /// survey,build,install,verify,cams,capture:HOUR:cam+cam,toggle:on|off.
    /// </summary>
    public static class ShadeSailsPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Root = "Assets/AthenHill/Art/ShadeSails/";
        const string ModelDir = Root + "Models/";
        const string TexDir = Root + "Textures/";
        const string MatDir = Root + "Materials/";
        const string ColDir = Root + "Colliders/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/ShadeSails/";
        const string Evidence = "../evidence/shade-sails/20261001/";
        const string ArtDir = "../../art/shade_sails_20261001/";
        public const string RootName = "Ward shade sails";
        const string CamRootName = "Shade sail review cameras";
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
        static readonly string[] SharedMaterialDirs =
        {
            "Assets/AthenHill/Art/VanguardHall/Materials", "Assets/AthenHill/Art/WardShops/Materials",
            "Assets/AthenHill/Art/StreetDressing/Materials", "Assets/AthenHill/Art/ShadeSails/Materials",
        };
        // light transmission through the cloth by dye (thin natural canvas glows most)
        static readonly Dictionary<string, float> Transmission = new Dictionary<string, float>
        { ["madder"] = .24f, ["indigo"] = .18f, ["natural"] = .32f, ["natural_indigo"] = .28f };
        const float SailLod0 = .35f, SailLod1 = .01f, RigLod0 = .4f, RigLod1 = .02f, FestoonLod0 = .45f, FestoonLod1 = .04f;

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] A(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static JObject Sails() => JObject.Parse(File.ReadAllText(ModelDir + "sails.json"));
        static JObject Cams() => JObject.Parse(File.ReadAllText(ArtDir + "review-cameras.json"));
        public static string PrefabPath(string site) => PrefabDir + "SS_" + site + ".prefab";

        static void Save(string name, object o)
        {
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + name, JsonConvert.SerializeObject(o, Formatting.Indented));
        }

        // ------------------------------------------------------------------ build
        [MenuItem("Athen Hill/Shade sails/Build assets")]
        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            ConfigureTextures();
            var sails = Sails();
            foreach (var p in sails.Properties())
                foreach (var grp in new[] { "Sail", "Rig", "Festoon" })
                    for (int lod = 0; lod < 2; lod++)
                        AssetDatabase.ImportAsset(ModelDir + $"SS_{p.Name}_{grp}_LOD{lod}.glb", ImportAssetOptions.ForceUpdate);
            var mats = BuildMaterials(sails);
            Directory.CreateDirectory(PrefabDir);
            Directory.CreateDirectory(ColDir);
            var missing = new HashSet<string>();
            var report = new Dictionary<string, object>();
            foreach (var p in sails.Properties()) report[p.Name] = BuildPrefab(p.Name, (JObject)p.Value, mats, missing);
            AssetDatabase.SaveAssets();
            var r = new { prefabs = report, unmappedMaterials = missing.OrderBy(x => x).ToArray() };
            Save("build-assets.json", r);
            if (missing.Count > 0) throw new Exception("Unmapped materials: " + string.Join(", ", missing));
            return JsonConvert.SerializeObject(r, Formatting.Indented);
        }

        static void ConfigureTextures()
        {
            foreach (var g in AssetDatabase.FindAssets("t:Texture", new[] { TexDir.TrimEnd('/') }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                bool normal = path.Contains("_Normal");
                bool baseMap = path.Contains("_BaseMap");
                bool weave = path.Contains("CanvasWeave");
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal;
                ti.alphaSource = baseMap ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
                ti.alphaIsTransparency = false;
                ti.mipMapsPreserveCoverage = baseMap;          // keep the worn-through holes open in the mips
                if (baseMap) ti.alphaTestReferenceValue = .5f;
                ti.mipmapEnabled = true;
                ti.streamingMipmaps = true;
                ti.anisoLevel = 8;
                ti.wrapMode = weave ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
                ti.maxTextureSize = weave ? 512 : (normal ? 1024 : 2048);
                ti.textureCompression = TextureImporterCompression.CompressedHQ;   // BC7 / BC5
                ti.SaveAndReimport();
            }
        }

        static Material NewOrLoad(string name, Shader shader)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            else if (m.shader != shader) m.shader = shader;
            return m;
        }

        static Texture2D T(string path)
        {
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!t) throw new Exception("Texture missing: " + path);
            return t;
        }

        static Dictionary<string, Material> BuildMaterials(JObject sails)
        {
            var cover = Shader.Find("Athen Hill/Ward Ground Cover");
            if (!cover) throw new Exception("Athen Hill/Ward Ground Cover shader missing (Shaders/WardGroundCover)");
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var weaveAlbedo = T(TexDir + "SS_CanvasWeave_Detail.png");
            var weaveNormal = T(TexDir + "SS_CanvasWeave_Normal.png");
            foreach (var p in sails.Properties())
            {
                var s = (JObject)p.Value;
                var m = NewOrLoad("SS_Sail_" + p.Name, cover);
                m.SetTexture("_BaseMap", T(TexDir + $"SS_Sail_{p.Name}_BaseMap.png"));
                m.SetTextureScale("_BaseMap", Vector2.one); m.SetTextureOffset("_BaseMap", Vector2.zero);
                m.SetColor("_BaseColor", Color.white);
                m.SetTexture("_BumpMap", T(TexDir + $"SS_Sail_{p.Name}_Normal.png")); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP");
                // the plain-weave detail pair: one 512 px tile = 0.2 m of canvas
                float tiles = (float)s["uv"]["size"] / .2f;
                m.SetTexture("_DetailAlbedoMap", weaveAlbedo); m.SetTexture("_DetailNormalMap", weaveNormal);
                m.SetTextureScale("_DetailAlbedoMap", new Vector2(tiles, tiles));
                m.SetFloat("_DetailAlbedoMapScale", 1f); m.SetFloat("_DetailNormalMapScale", .55f);
                m.EnableKeyword("_DETAIL_MULX2");
                m.SetFloat("_Smoothness", .16f); m.SetFloat("_Metallic", 0f); m.SetFloat("_SmoothnessTextureChannel", 0);
                m.SetFloat("_AlphaClip", 1); m.SetFloat("_Cutoff", .5f); m.EnableKeyword("_ALPHATEST_ON");
                m.SetOverrideTag("RenderType", "TransparentCutout"); m.renderQueue = (int)RenderQueue.AlphaTest;
                m.SetFloat("_Cull", 0); m.doubleSidedGI = true;
                m.SetFloat("_WardWindStrength", 0f); m.SetFloat("_WardLeafFlutter", 0f); m.SetFloat("_WardBendHeight", 2f);
                float tr = Transmission.TryGetValue((string)s["dye"], out var v) ? v : .2f;
                m.SetFloat("_WardTranslucency", tr); m.SetFloat("_WardIndirectTranslucency", tr * .45f);
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
            }
            var bulb = NewOrLoad("SS_FestoonBulb", lit);
            bulb.SetColor("_BaseColor", new Color(.98f, .84f, .62f)); bulb.SetFloat("_Smoothness", .82f); bulb.SetFloat("_Metallic", 0);
            bulb.SetColor("_EmissionColor", new Color(1f, .5f, .2f) * 2.3f); bulb.EnableKeyword("_EMISSION");
            bulb.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;   // keeps _EMISSION in builds
            var dead = NewOrLoad("SS_BulbDead", lit);
            dead.SetColor("_BaseColor", new Color(.17f, .15f, .13f)); dead.SetFloat("_Smoothness", .78f); dead.SetFloat("_Metallic", 0);
            foreach (var m in new[] { bulb, dead }) { m.enableInstancing = true; EditorUtility.SetDirty(m); }
            // pole paints: VH_Steel's weathered sheet-steel maps under a paint tint (old paint over rust)
            var steel = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/VanguardHall/Materials/VH_Steel.mat");
            if (!steel) throw new Exception("VH_Steel missing");
            foreach (var (name, tint) in new[] { ("SS_PoleGrey", new Color(.5f, .54f, .5f)), ("SS_PoleRed", new Color(.6f, .27f, .2f)), ("SS_PoleOlive", new Color(.44f, .47f, .32f)) })
            {
                var m = NewOrLoad(name, steel.shader);
                m.CopyPropertiesFromMaterial(steel);
                m.SetColor("_BaseColor", tint);
                m.SetFloat("_Smoothness", Mathf.Min(m.GetFloat("_Smoothness"), .55f));
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
            }
            AssetDatabase.SaveAssets();
            var mats = new Dictionary<string, Material>();
            foreach (var dir in SharedMaterialDirs)
                foreach (var g in AssetDatabase.FindAssets("t:Material", new[] { dir }))
                {
                    var p = AssetDatabase.GUIDToAssetPath(g);
                    if (Path.GetDirectoryName(p).Replace('\\', '/') != dir) continue;
                    var m = AssetDatabase.LoadAssetAtPath<Material>(p);
                    if (m && !mats.ContainsKey(m.name)) mats[m.name] = m;
                }
            return mats;
        }

        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m) && m) return m;
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
                    if (m) slots[i] = m; else missing.Add(Path.GetFileNameWithoutExtension(glb) + ":" + (slots[i] ? slots[i].name : "null"));
                }
                r.sharedMaterials = slots;
                r.receiveShadows = true;
                r.shadowCastingMode = ShadowCastingMode.Off;
                if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
                rs.Add(r);
            }
            return rs;
        }

        static long Tris(IEnumerable<Renderer> rs)
        {
            long t = 0;
            foreach (var r in rs)
                if (r && r.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh)
                    for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) t += mf.sharedMesh.GetIndexCount(s) / 3;
            return t;
        }

        static LODGroup Group(GameObject go, float c0, float c1, List<Renderer> l0, List<Renderer> l1)
        {
            var g = go.AddComponent<LODGroup>();
            g.SetLODs(new[] { new LOD(c0, l0.ToArray()), new LOD(c1, l1.ToArray()) });
            g.fadeMode = LODFadeMode.None;
            g.RecalculateBounds();
            return g;
        }

        /// The camera blocker: the coarse canvas, both windings (PhysX mesh queries ignore back faces), saved as an asset.
        static Mesh CameraBlockMesh(string site, Mesh src, Matrix4x4 toRoot)
        {
            var path = ColDir + "SS_" + site + "_CameraBlock.asset";
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            bool create = !mesh;
            if (create) mesh = new Mesh { name = "SS_" + site + "_CameraBlock" };
            var v = src.vertices.Select(p => toRoot.MultiplyPoint3x4(p)).ToArray();
            var t = new List<int>();
            for (int s = 0; s < src.subMeshCount; s++) t.AddRange(src.GetTriangles(s, true));
            var both = new List<int>(t);
            for (int i = 0; i < t.Count; i += 3) { both.Add(t[i]); both.Add(t[i + 2]); both.Add(t[i + 1]); }
            mesh.Clear();
            mesh.indexFormat = v.Length > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16;
            mesh.SetVertices(v); mesh.SetTriangles(both, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            if (create) AssetDatabase.CreateAsset(mesh, path); else EditorUtility.SetDirty(mesh);
            return mesh;
        }

        static object BuildPrefab(string site, JObject rec, Dictionary<string, Material> mats, HashSet<string> missing)
        {
            var root = new GameObject("SS_" + site);
            try
            {
                // ---- Sail: LOD0 detailed, LOD1 coarse; neither casts (see the proxies below)
                var sail = new GameObject("Sail"); sail.transform.SetParent(root.transform, false);
                var s0 = Instance(ModelDir + $"SS_{site}_Sail_LOD0.glb", sail.transform, "LOD0", mats, missing);
                var s1 = Instance(ModelDir + $"SS_{site}_Sail_LOD1.glb", sail.transform, "LOD1", mats, missing);
                var fabric1 = s1.First(r => r.name.Contains("_Fabric_"));
                // The sail's shadow comes from ShadowsOnly copies of the coarse canvas 4 cm BELOW it (one per LOD), so the
                // canvas never shadows itself: its underside keeps the sun's transmission through the cloth and its top
                // stays lit, while trees and buildings still shadow it.
                Renderer Proxy(string name)
                {
                    var go = new GameObject(name); go.transform.SetParent(sail.transform, false);
                    go.transform.SetPositionAndRotation(fabric1.transform.position + Vector3.down * .04f, fabric1.transform.rotation);
                    go.transform.localScale = fabric1.transform.lossyScale;
                    go.AddComponent<MeshFilter>().sharedMesh = fabric1.GetComponent<MeshFilter>().sharedMesh;
                    var pr = go.AddComponent<MeshRenderer>(); pr.sharedMaterials = fabric1.sharedMaterials; pr.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                    pr.receiveShadows = false;
                    return pr;
                }
                var proxy = Proxy("Shadow proxy LOD0 (canvas, 4 cm below)");
                var proxy1 = Proxy("Shadow proxy LOD1 (canvas, 4 cm below)");
                var sailGroup = Group(sail, SailLod0, SailLod1, s0.Concat(new[] { proxy }).ToList(), s1.Concat(new[] { proxy1 }).ToList());

                // ---- Rig: poles and stone footings cast at LOD0
                var rig = new GameObject("Rig"); rig.transform.SetParent(root.transform, false);
                var r0 = Instance(ModelDir + $"SS_{site}_Rig_LOD0.glb", rig.transform, "LOD0", mats, missing);
                var r1 = Instance(ModelDir + $"SS_{site}_Rig_LOD1.glb", rig.transform, "LOD1", mats, missing);
                foreach (var r in r0) if (r.name.Contains("_Poles_") || r.name.Contains("_Stone_")) r.shadowCastingMode = ShadowCastingMode.On;
                Group(rig, RigLod0, RigLod1, r0, r1);

                // ---- Festoons: no shadows
                var fest = new GameObject("Festoons"); fest.transform.SetParent(root.transform, false);
                var f0 = Instance(ModelDir + $"SS_{site}_Festoon_LOD0.glb", fest.transform, "LOD0", mats, missing);
                var f1 = Instance(ModelDir + $"SS_{site}_Festoon_LOD1.glb", fest.transform, "LOD1", mats, missing);
                Group(fest, FestoonLod0, FestoonLod1, f0, f1);

                // ---- festoon lights (bound to the Ward lighting clock on install)
                var origin = V3(rec["origin"]);
                var lights = new GameObject("Festoon lights"); lights.transform.SetParent(root.transform, false);
                foreach (var l in rec["lights"])
                {
                    var go = new GameObject((string)l["name"]); go.transform.SetParent(lights.transform, false);
                    go.transform.localPosition = V3(l["pos"]) - origin;
                    var li = go.AddComponent<Light>(); li.type = LightType.Point; li.lightmapBakeType = LightmapBakeType.Realtime;
                    var c = l["color"]; li.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                    li.intensity = (float)l["intensity"]; li.range = (float)l["range"]; li.shadows = LightShadows.None;
                }

                // ---- colliders: poles, footings, ballast, guy anchors; the canvas for the camera only
                var cols = new GameObject("Colliders"); cols.transform.SetParent(root.transform, false);
                foreach (var c in rec["colliders"])
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(cols.transform, false);
                    if (c["a"] != null)
                    {
                        var a = V3(c["a"]); var b = V3(c["b"]); float rad = (float)c["radius"];
                        go.transform.localPosition = (a + b) * .5f;
                        go.transform.localRotation = Quaternion.FromToRotation(Vector3.up, (b - a).normalized);
                        var cc = go.AddComponent<CapsuleCollider>(); cc.direction = 1; cc.radius = rad; cc.height = (b - a).magnitude + 2 * rad;
                    }
                    else
                    {
                        go.transform.localPosition = V3(c["center"]);
                        go.AddComponent<BoxCollider>().size = V3(c["size"]);
                    }
                }
                var block = new GameObject("COL_SailCameraBlock (camera only, 3.6 m+)"); block.transform.SetParent(cols.transform, false);
                var mc = block.AddComponent<MeshCollider>();
                mc.sharedMesh = CameraBlockMesh(site, fabric1.GetComponent<MeshFilter>().sharedMesh, root.transform.worldToLocalMatrix * fabric1.transform.localToWorldMatrix);

                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    if (t.GetComponent<Light>() || t.GetComponent<Collider>()) continue;
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(site));
                return new
                {
                    sail = new { lod0 = Tris(s0), lod1 = Tris(s1), shadowProxy = Tris(new[] { proxy }) },
                    rig = new { lod0 = Tris(r0), lod1 = Tris(r1), lod0Casters = Tris(r0.Where(r => r.shadowCastingMode != ShadowCastingMode.Off)) },
                    festoons = new { lod0 = Tris(f0), lod1 = Tris(f1) },
                    lights = rec["lights"].Count(), colliders = rec["colliders"].Count() + 1,
                };
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        // ------------------------------------------------------------------ install (one time)
        [MenuItem("Athen Hill/Shade sails/Install (one time)")]
        public static string Install() => Install(false);

        /// Authoring iteration only: replaces the installed root (keeps the first rollback copy and re-binds the lights).
        public static string Reinstall() => Install(true);

        static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (existing && !replace) throw new Exception("The shade sails are already installed; edit the instances in place (or Reinstall while authoring).");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            string fpBefore = chunks ? StaticRenderChunksEditor.Fingerprint(chunks) : null;
            Directory.CreateDirectory(Evidence + "rollback");
            var rollback = Evidence + "rollback/before-shade-sails.unity";
            if (!replace || !File.Exists(rollback)) File.Copy(ScenePath, rollback, true);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            if (existing)
            {
                var old = new HashSet<Light>(existing.GetComponentsInChildren<Light>(true));
                if (circuit)
                {
                    circuit.practicalLights = circuit.practicalLights.Where(l => l && !old.Contains(l)).ToArray();
                    circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !old.Contains(l)).ToArray();
                }
                UnityEngine.Object.DestroyImmediate(existing);
            }
            var sails = Sails();
            var root = new GameObject(RootName);
            var placed = new List<object>();
            var lights = new List<Light>();
            foreach (var p in sails.Properties())
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(p.Name));
                if (!prefab) throw new Exception("Prefab missing: " + PrefabPath(p.Name) + " (run build first)");
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                inst.transform.SetParent(root.transform, false);
                inst.transform.SetPositionAndRotation(V3(p.Value["origin"]), Quaternion.identity);
                inst.name = (string)p.Value["name"];
                lights.AddRange(inst.GetComponentsInChildren<Light>(true));
                placed.Add(new { site = p.Name, name = inst.name, origin = A(inst.transform.position) });
            }
            var bulb = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "SS_FestoonBulb.mat");
            if (circuit)
            {
                circuit.practicalLights = circuit.practicalLights.Where(l => l).Concat(lights).Distinct().ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l).Concat(lights).Distinct().ToArray();
                if (bulb && !circuit.emissiveMaterials.Contains(bulb)) circuit.emissiveMaterials = circuit.emissiveMaterials.Concat(new[] { bulb }).ToArray();
                EditorUtility.SetDirty(circuit);
            }
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            var record = new
            {
                utc = DateTime.UtcNow, rollback, replace, placed, lights = lights.Select(l => PathOf(l.transform)).ToArray(),
                circuitFound = circuit != null, emissiveRegistered = circuit && bulb && circuit.emissiveMaterials.Contains(bulb),
                retired = new string[0], chunkFingerprintBefore = fpBefore, chunkFingerprintAfter = chunks ? StaticRenderChunksEditor.Fingerprint(chunks) : null,
                reviewCameras = Cams().Properties().Select(x => x.Name).ToArray(),
            };
            Save(replace ? "reinstall.json" : "install.json", record);
            return JsonConvert.SerializeObject(record, Formatting.Indented);
        }

        // ------------------------------------------------------------------ review cameras
        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            foreach (var p in Cams().Properties())
            {
                var pos = V3(p.Value["pos"]); var target = V3(p.Value["target"]);
                var go = new GameObject(p.Name); go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = (float)p.Value["fov"]; k.nearClipPlane = .05f; k.farClipPlane = 1200f;
            }
        }

        [MenuItem("Athen Hill/Shade sails/Add review cameras")]
        public static string CamerasOnly()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return "review cameras: " + scene.GetRootGameObjects().First(g => g.name == CamRootName).transform.childCount;
        }

        // ------------------------------------------------------------------ verify
        [MenuItem("Athen Hill/Shade sails/Verify saved scene")]
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var sails = Sails();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var problems = new List<string>();
            if (root)
            {
                var sites = new Dictionary<string, object>();
                long lod0 = 0, lod1 = 0, casters0 = 0;
                foreach (var p in sails.Properties())
                {
                    var inst = root.transform.Cast<Transform>().FirstOrDefault(t => t.name == (string)p.Value["name"]);
                    if (!inst) { problems.Add("missing instance " + p.Name); continue; }
                    bool linked = PrefabUtility.IsPartOfPrefabInstance(inst.gameObject) && !PrefabUtility.IsPrefabAssetMissing(inst.gameObject);
                    if (!linked) problems.Add("not prefab-linked: " + p.Name);
                    if ((inst.position - V3(p.Value["origin"])).magnitude > 1e-3) problems.Add("moved off its layout origin: " + p.Name);
                    var groups = inst.GetComponentsInChildren<LODGroup>(true);
                    var g = groups.Select(x => new
                    {
                        x.name,
                        lods = x.GetLODs().Select(l => new
                        {
                            l.screenRelativeTransitionHeight, renderers = l.renderers.Length, triangles = Tris(l.renderers),
                            shadowCasterTriangles = Tris(l.renderers.Where(rr => rr && rr.shadowCastingMode != ShadowCastingMode.Off)),
                        }).ToArray(),
                    }).ToArray();
                    foreach (var x in groups)
                    {
                        var ls = x.GetLODs();
                        lod0 += Tris(ls[0].renderers.Where(rr => rr && rr.shadowCastingMode != ShadowCastingMode.ShadowsOnly));
                        lod1 += Tris(ls[1].renderers.Where(rr => rr && rr.shadowCastingMode != ShadowCastingMode.ShadowsOnly));
                        casters0 += Tris(ls[0].renderers.Where(rr => rr && rr.shadowCastingMode != ShadowCastingMode.Off));
                    }
                    var lights = inst.GetComponentsInChildren<Light>(true);
                    sites[p.Name] = new
                    {
                        instance = PathOf(inst), linked, groups = g,
                        lights = lights.Select(l => new { l.name, l.intensity, l.range, shadows = l.shadows.ToString(), inCircuit = circuit && circuit.practicalLights.Contains(l) && circuit.nightOnlyLights.Contains(l) }).ToArray(),
                        colliders = inst.GetComponentsInChildren<Collider>(true).Select(c => c.name + " (" + c.GetType().Name + ")").ToArray(),
                    };
                    foreach (var l in lights) if (!(circuit && circuit.practicalLights.Contains(l) && circuit.nightOnlyLights.Contains(l))) problems.Add("light not on the clock: " + PathOf(l.transform));
                }
                r["sites"] = sites;
                r["lod0Triangles"] = lod0; r["lod1Triangles"] = lod1; r["lod0ShadowCasterTriangles"] = casters0;
                var rends = root.GetComponentsInChildren<Renderer>(true);
                r["renderers"] = rends.Length;
                r["missingMaterials"] = rends.Count(x => x.sharedMaterials.Any(m => !m));
                r["errorShaderMaterials"] = rends.SelectMany(x => x.sharedMaterials).Where(m => m && (m.shader == null || m.shader.name.Contains("Error"))).Select(m => m.name).Distinct().ToArray();
                r["materials"] = rends.SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => m.name + " (" + m.shader.name + ")").Distinct().OrderBy(x => x).ToArray();
                r["shadowCasters"] = rends.Where(x => x.shadowCastingMode != ShadowCastingMode.Off).Select(x => PathOf(x.transform)).ToArray();
                r["lights"] = root.GetComponentsInChildren<Light>(true).Length;
                r["nonUniformScale"] = root.GetComponentsInChildren<Transform>(true).Where(t => Mathf.Abs(t.localScale.x - t.localScale.y) > 1e-4 || Mathf.Abs(t.localScale.y - t.localScale.z) > 1e-4).Select(PathOf).ToArray();
                if ((int)r["missingMaterials"] > 0) problems.Add("missing materials");
                if (((string[])r["errorShaderMaterials"]).Length > 0) problems.Add("error shaders");
                if (((string[])r["nonUniformScale"]).Length > 0) problems.Add("non-uniform scale");
            }
            else problems.Add("not installed");
            var bulb = AssetDatabase.LoadAssetAtPath<Material>(MatDir + "SS_FestoonBulb.mat");
            r["bulbOnEmissiveList"] = circuit && bulb && circuit.emissiveMaterials.Contains(bulb);
            if (!(bool)r["bulbOnEmissiveList"]) problems.Add("festoon bulb material not on the clock's emissive list");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>(FindObjectsInactive.Include);
            if (chunks)
            {
                bool match = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
                r["chunkFingerprintMatches"] = match; r["chunkEditing"] = chunks.editingSources;
                if (!match) problems.Add("render chunks stale");
            }
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            r["reviewCameras"] = cams ? cams.GetComponentsInChildren<Camera>(true).Select(c => c.name + (c.enabled ? " (ENABLED)" : "")).ToArray() : new string[0];
            if (cams && cams.GetComponentsInChildren<Camera>(true).Any(c => c.enabled)) problems.Add("a review camera is enabled");
            r["retiredStillActive"] = new string[0];          // this pass retires nothing
            r["problems"] = problems;
            Save("verify-saved-scene.json", r);
            return problems.Count == 0 ? "verify OK" : "verify PROBLEMS: " + string.Join("; ", problems);
        }

        // ------------------------------------------------------------------ editor captures (graphics; <= 6 close cameras per run)
        static int capturedThisRun;
        public static string Capture(string hourText, string camList, string outDir, bool off)
        {
            var names = camList.Split('+');
            capturedThisRun += names.Length;
            if (capturedThisRun > 6) throw new Exception("at most 6 cameras per Unity run (VRAM rule)");
            float hour = float.Parse(hourText, Inv);
            var scene = EditorSceneManager.OpenScene(ScenePath);
            if (off)
            {
                var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
                if (root) root.SetActive(false);                // in memory only; the scene is not saved
            }
            var cams = Cams();
            var specs = names.Select(n =>
            {
                if (n.Contains('@')) { var q = n.Replace(';', ',').Split('@'); return $"{q[0]}:{q[1]}:{q[2]}:{q[3]}"; }   // name@x;y;z@x;y;z@fov
                if (GameObject.Find(n)) return n;
                var c = cams[n];
                if (c == null) throw new Exception("No camera " + n);
                string F(Vector3 p) => string.Join(",", new[] { p.x, p.y, p.z }.Select(f => f.ToString("0.###", Inv)));
                return $"{n}:{F(V3(c["pos"]))}:{F(V3(c["target"]))}:{((float)c["fov"]).ToString(Inv)}";
            }).ToArray();
            ShaderUtil.allowAsyncCompilation = false;
            var dir = off ? Path.Combine(outDir, "off") : outDir;
            DuskStartPass.Preview(hour, Path.Combine(dir, "warmup"), specs[0]);
            return DuskStartPass.Preview(hour, dir, specs);
        }

        /// Measurement only (A/B): switches the whole sails root off or on in the saved scene.
        static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            root.SetActive(on);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            return RootName + (on ? " on" : " off");
        }

        // ------------------------------------------------------------------ survey (read-only, -nographics)
        static readonly (string renderer, Vector3 min, Vector3 max)[] Probes =
        {
            ("Ward district retrofit/Service lanes/Service lanes Structure", new Vector3(-30f, -1f, -16f), new Vector3(-26.5f, 12f, -2f)),
            ("Ward district retrofit/Service lanes/Service lanes Detail", new Vector3(-30f, -1f, -16f), new Vector3(-26.5f, 12f, -2f)),
            ("Ward district retrofit/Service lanes/Service lanes Structure", new Vector3(26.5f, -1f, -6f), new Vector3(30f, 12f, 15f)),
            ("Ward oasis tree/Shadow proxy/LOD0 range/WardTree_Shadow_leaves", new Vector3(1f, -1f, -11f), new Vector3(13f, 20f, -5f)),
            ("Ward oasis tree/Shadow proxy/LOD0 range/WardTree_Shadow_branches", new Vector3(1f, -1f, -11f), new Vector3(13f, 20f, -5f)),
            ("Karaveen caravan market/Bunting/Bunting Structure", new Vector3(-36f, -1f, -12f), new Vector3(-28f, 8f, 2f)),
            ("Karaveen caravan market/Bunting/Bunting Goods", new Vector3(-36f, -1f, -12f), new Vector3(-28f, 8f, 2f)),
        };

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
                practical = practical.Contains(l), nightOnly = nightOnly.Contains(l),
            }).ToArray();
            var cams = all.Select(t => t.GetComponent<Camera>()).Where(c => c).Select(c => new
            {
                name = c.name, path = PathOf(c.transform), pos = A(c.transform.position), fwd = A(c.transform.forward), up = A(c.transform.up), c.fieldOfView, c.enabled,
            }).ToArray();
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var sun = new List<object>();
            if (clock && clock.profile)
                foreach (var h in new[] { 7f, 9f, 11f, 12f, 13f, 14f, 15f, 17f, 18.5f, 20.5f })
                {
                    var f = clock.profile.Evaluate(h);
                    var fwd = Quaternion.Euler(f.keyEuler) * Vector3.forward;
                    sun.Add(new { hour = h, euler = A(f.keyEuler), lightForward = A(fwd), f.keyIntensity, f.sunVisibility });
                }
            var probes = new List<object>();
            foreach (var (path, min, max) in Probes)
            {
                var t = all.FirstOrDefault(x => PathOf(x) == path);
                var mf = t ? t.GetComponent<MeshFilter>() : null;
                if (!mf || !mf.sharedMesh) { probes.Add(new { path, missing = true }); continue; }
                var bounds = new Bounds((min + max) * .5f, max - min);
                var pts = new List<float[]>();
                Vector3[] verts;
                try { verts = mf.sharedMesh.vertices; }
                catch (Exception e) { probes.Add(new { path, error = e.Message }); continue; }
                var m = t.localToWorldMatrix;
                foreach (var v in verts)
                {
                    var w = m.MultiplyPoint3x4(v);
                    if (bounds.Contains(w)) pts.Add(A(w));
                }
                int step = Math.Max(1, pts.Count / 6000);
                probes.Add(new { path, min = A(min), max = A(max), count = pts.Count, step, points = pts.Where((p, i) => i % step == 0).ToArray() });
            }
            Save("survey.json", new
            {
                circuit = circuit ? new { circuit.daytimeStrength, circuit.fullLightDistance, circuit.culledLightDistance, circuit.shadowDistance, practical = circuit.practicalLights.Length, nightOnly = circuit.nightOnlyLights.Length, emissive = circuit.emissiveMaterials.Where(x => x).Select(x => x.name).ToArray() } : null,
                lights, cameras = cams, sun, probes,
            });
            return $"survey: {lights.Length} lights, {cams.Length} cameras, {probes.Count} probes";
        }

        static string Wrap(Func<object> f) { var o = f(); AssetDatabase.SaveAssets(); return "ok"; }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.ShadeSailsPass.RunBatch --steps survey,build,install,verify [--out dir]
        /// capture:HOUR:cam+cam[:off] renders (graphics, at most six cameras per run); a camera may be given inline as
        /// name@x;y;z@x;y;z@fov (eye, target, vertical field of view).
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
                        "materials" => Wrap(() => BuildMaterials(Sails())),
                        "install" => Install(),
                        "reinstall" => Reinstall(),
                        "verify" => Verify(),
                        "cams" => CamerasOnly(),
                        "capture" => Capture(parts[1], parts[2], outDir, parts.Length > 3 && parts[3] == "off"),
                        "toggle" => Toggle(parts[1] == "on"),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("ShadeSailsPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
