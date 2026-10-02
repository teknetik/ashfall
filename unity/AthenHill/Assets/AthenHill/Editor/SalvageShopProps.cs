using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: hero props for the walk-in Salvage shop (Carl: "the salvage shop should be open to trade and have the
    /// equipment in there ... get to upgrade my pistol"). Assets only: this builds prefabs and never opens or saves a scene.
    ///
    /// Sources: Meshy text-to-3D (meshy/salvage-shop-props-20261001, task ids and credits in each record.json), fitted in
    /// Blender by its prepare.py (uniform scale, base on the floor at the footprint centre, front = +Z, LOD1 by collapse
    /// decimation, maps extracted) into Art/SalvageShop/Props/&lt;id&gt;/ with Props/salvage-shop-props.json (sizes, colliders,
    /// the workbench's screen panel, use and light points, in Unity axes).
    ///
    ///   SS_Workbench      fabrication bench (where the player fabricates parts and fits pistol mods): LODGroup, bench and
    ///                     rear-frame box colliders, an emissive `Screen` quad over the modelled screen plate (an authored
    ///                     overlay, so decimation never smears it), `Use point` (floor, where the player stands) and
    ///                     `Light point` (at the print head, for an optional small cyan light).
    ///   SS_PartsRack      stocked steel shelving bay.
    ///   SS_PartsRackHeavy low heavy rack with a motor/drum assembly (if its model exists).
    ///
    /// Batch: -executeMethod AthenHill.Editor.SalvageShopProps.RunBatch -nographics --steps build,verify
    /// verify writes unity/evidence/salvage-shop/20261001/props-verify.json.
    /// </summary>
    public static class SalvageShopProps
    {
        const string ArtDir = "Assets/AthenHill/Art/SalvageShop/";
        const string PropDir = ArtDir + "Props/";
        const string MatDir = ArtDir + "Materials/";
        const string MeshDir = ArtDir + "Meshes/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/SalvageShop/";
        const string ManifestPath = PropDir + "salvage-shop-props.json";
        const string ScreenMatPath = MatDir + "SS_FabScreen.mat";
        const string Evidence = "../evidence/salvage-shop/20261001/";
        static readonly string[] Ids = { "SS_Workbench", "SS_PartsRack", "SS_PartsRackHeavy" };
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        // LOD switch heights (relative to the LODGroup's largest dimension; the PC preset's LOD bias is 2, so for the 2.2 m
        // bench LOD1 takes over at ~13 m and the prop culls at ~190 m)
        const float Lod1At = .3f, CullAt = .02f;
        // URP mask alpha is 1 - Meshy roughness; Meshy maps run a little glossy (as the street-dressing Meshy props)
        const float SmoothnessScale = .8f;

        public static string PrefabPath(string id) => PrefabDir + id + ".prefab";

        static JObject Manifest() => File.Exists(ManifestPath) ? JObject.Parse(File.ReadAllText(ManifestPath)) : throw new Exception("Manifest missing: " + ManifestPath);
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static float[] A(Vector3 v) => new[] { (float)Math.Round(v.x, 4), (float)Math.Round(v.y, 4), (float)Math.Round(v.z, 4) };

        // ------------------------------------------------------------------ textures
        static void ConfigureTexture(string path, bool normal, bool linear, int maxSize, bool streaming)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter ti) throw new Exception("Not a texture: " + path);
            ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = !normal && !linear;
            ti.alphaSource = linear && !normal ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
            ti.alphaIsTransparency = false;
            ti.mipmapEnabled = true;
            ti.streamingMipmaps = streaming;
            ti.anisoLevel = 8;
            ti.filterMode = FilterMode.Trilinear;
            ti.wrapMode = TextureWrapMode.Clamp;                       // Meshy atlases: no bleed from the opposite edge
            ti.maxTextureSize = maxSize;
            ti.npotScale = TextureImporterNPOTScale.None;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;   // BC7 colour/mask, BC5 normal
            ti.SaveAndReimport();
        }

        static Texture2D Tex(string path) => AssetDatabase.LoadAssetAtPath<Texture2D>(path) ?? throw new Exception("Texture missing: " + path);

        // ------------------------------------------------------------------ materials
        static Material MatAsset(string path)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var lit = Shader.Find("Universal Render Pipeline/Lit") ?? throw new Exception("URP Lit shader missing");
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(lit) { name = Path.GetFileNameWithoutExtension(path) }; AssetDatabase.CreateAsset(m, path); }
            else if (m.shader != lit) m.shader = lit;
            return m;
        }

        static void Validate(Material m) =>
            BaseShaderGUI.SetMaterialKeywords(m, LitGUI.SetMaterialKeywords, x => { x.DisableKeyword("_DETAIL_MULX2"); x.DisableKeyword("_DETAIL_SCALED"); });

        static Material PropMaterial(string id, JObject e)
        {
            var dir = PropDir + id + "/";
            var maps = e["maps"];
            var m = MatAsset(MatDir + id + ".mat");
            m.SetFloat("_WorkflowMode", 1); m.SetFloat("_Surface", 0); m.SetFloat("_Cull", 2); m.SetFloat("_AlphaClip", 0);
            m.SetTexture("_BaseMap", Tex(dir + (string)maps["BaseColor"])); m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BumpMap", Tex(dir + (string)maps["Normal"])); m.SetFloat("_BumpScale", 1f);
            m.SetTexture("_MetallicGlossMap", Tex(dir + (string)maps["Mask"]));
            m.SetFloat("_Metallic", 1f); m.SetFloat("_Smoothness", SmoothnessScale); m.SetFloat("_SmoothnessTextureChannel", 0);
            m.SetTexture("_OcclusionMap", null); m.SetTexture("_EmissionMap", null); m.SetColor("_EmissionColor", Color.black);
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack;
            m.SetFloat("_SpecularHighlights", 1); m.SetFloat("_EnvironmentReflections", 1);
            m.enableInstancing = true;
            Validate(m);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Material ScreenMaterial(string texPath)
        {
            var m = MatAsset(ScreenMatPath);
            var t = Tex(texPath);
            m.SetFloat("_WorkflowMode", 1); m.SetFloat("_Surface", 0); m.SetFloat("_Cull", 2);
            m.SetTexture("_BaseMap", t); m.SetColor("_BaseColor", new Color(.28f, .3f, .3f));     // dark glass by day
            m.SetFloat("_Metallic", 0f); m.SetFloat("_Smoothness", .82f); m.SetTexture("_MetallicGlossMap", null);
            m.SetTexture("_BumpMap", null);
            m.SetTexture("_EmissionMap", t);
            m.SetColor("_EmissionColor", new Color(1f, 1f, 1f) * 1.4f);                       // HDR: restrained, readable in sun
            // URP strips _EMISSION on save unless the material is flagged as realtime emissive
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            m.enableInstancing = true;
            Validate(m);
            m.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(m);
            return m;
        }

        /// A quad facing +Z (towards the user standing in front of the bench), u running to the viewer's right.
        static Mesh ScreenQuad(float w, float h)
        {
            Directory.CreateDirectory(MeshDir);
            var path = MeshDir + "SS_FabScreenQuad.asset";
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (!mesh) { mesh = new Mesh(); AssetDatabase.CreateAsset(mesh, path); }
            mesh.Clear();
            mesh.name = "SS_FabScreenQuad";
            float x = w / 2, y = h / 2;
            mesh.vertices = new[] { new Vector3(x, -y, 0), new Vector3(-x, -y, 0), new Vector3(-x, y, 0), new Vector3(x, y, 0) };
            mesh.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            mesh.normals = Enumerable.Repeat(Vector3.forward, 4).ToArray();
            mesh.triangles = new[] { 3, 2, 1, 3, 1, 0 };
            mesh.RecalculateTangents(); mesh.RecalculateBounds();
            EditorUtility.SetDirty(mesh);
            return mesh;
        }

        // ------------------------------------------------------------------ build
        static List<Renderer> Instance(string glb, Transform parent, string name, Material mat)
        {
            AssetDatabase.ImportAsset(glb, ImportAssetOptions.ForceUpdate);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb) ?? throw new Exception("Model not imported: " + glb);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            inst.name = name;
            inst.transform.SetParent(parent, false);
            inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
            var rs = new List<Renderer>();
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
            {
                r.sharedMaterials = Enumerable.Repeat(mat, r.sharedMaterials.Length).ToArray();
                r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true;
                if (r is MeshRenderer mr) { mr.receiveGI = ReceiveGI.LightProbes; mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; }
                rs.Add(r);
            }
            foreach (var c in inst.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
            return rs;
        }

        static Bounds Measure(IEnumerable<Renderer> rs)
        {
            Bounds? b = null;
            foreach (var r in rs) { if (b == null) b = r.bounds; else { var x = b.Value; x.Encapsulate(r.bounds); b = x; } }
            return b ?? new Bounds();
        }

        static GameObject Empty(string name, Transform parent, Vector3 local)
        {
            var g = new GameObject(name);
            g.transform.SetParent(parent, false);
            g.transform.localPosition = local;
            return g;
        }

        static string BuildPrefab(string id, JObject e)
        {
            var dir = PropDir + id + "/";
            var mat = PropMaterial(id, e);
            var root = new GameObject(id);
            try
            {
                var lod0 = Instance(dir + id + "_LOD0.glb", root.transform, "LOD0", mat);
                var lod1 = Instance(dir + id + "_LOD1.glb", root.transform, "LOD1", mat);
                // uniform fit (Blender already fitted; this only corrects drift) and pivot at the floor centre
                var b = Measure(lod0);
                var fit = e["fit"];
                string axis = (string)fit[0]; float metres = (float)fit[1];
                float measured = axis == "x" ? b.size.x : axis == "y" ? b.size.y : b.size.z;
                float k = metres / measured;
                if (Mathf.Abs(k - 1f) < .001f) k = 1f;
                foreach (var t in new[] { root.transform.Find("LOD0"), root.transform.Find("LOD1") }) t.localScale = Vector3.one * k;
                b = Measure(lod0);
                var shift = new Vector3(-b.center.x, -b.min.y, -b.center.z);
                foreach (var t in new[] { root.transform.Find("LOD0"), root.transform.Find("LOD1") }) t.localPosition = shift;
                Vector3 P(JToken t) => V3(t) * k + shift;

                var lod0Renderers = new List<Renderer>(lod0);
                var lod1Renderers = new List<Renderer>(lod1);
                if (e["screen"] is JObject s)
                {
                    var screenMat = ScreenMaterial((string)s["texture"]);
                    var q = s["quad_size"];
                    var go = new GameObject("Screen");
                    go.transform.SetParent(root.transform, false);
                    go.transform.localPosition = P(s["center"]);
                    go.transform.localRotation = Quaternion.LookRotation(V3(s["normal"]).normalized, V3(s["up"]).normalized);
                    go.AddComponent<MeshFilter>().sharedMesh = ScreenQuad((float)q[0] * k, (float)q[1] * k);
                    var mr = go.AddComponent<MeshRenderer>();
                    mr.sharedMaterial = screenMat;
                    mr.shadowCastingMode = ShadowCastingMode.Off; mr.receiveShadows = true;
                    mr.receiveGI = ReceiveGI.LightProbes;
                    lod0Renderers.Add(mr); lod1Renderers.Add(mr);
                }
                if (e["use_point"] != null) Empty("Use point", root.transform, P(e["use_point"]));
                if (e["light_point"] != null) Empty("Light point", root.transform, P(e["light_point"]));

                var g = root.AddComponent<LODGroup>();
                g.SetLODs(new[] { new LOD(Lod1At, lod0Renderers.ToArray()), new LOD(CullAt, lod1Renderers.ToArray()) });
                g.fadeMode = LODFadeMode.None;
                g.RecalculateBounds();

                var cols = new GameObject("Colliders");
                cols.transform.SetParent(root.transform, false);
                foreach (var c in e["colliders"])
                {
                    var cg = new GameObject((string)c["name"]);
                    cg.transform.SetParent(cols.transform, false);
                    var box = cg.AddComponent<BoxCollider>();
                    box.center = P(c["center"]);
                    box.size = V3(c["size"]) * k;
                }
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic);
                Directory.CreateDirectory(PrefabDir);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(id));
                var fb = Measure(lod0);
                return $"{id}: scale {k:F4}, size {fb.size.x:F3} x {fb.size.y:F3} x {fb.size.z:F3}";
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        public static string Build()
        {
            AssetDatabase.Refresh();
            var man = Manifest();
            var log = new List<string>();
            foreach (var id in Ids)
            {
                if (man[id] is not JObject e || !File.Exists(PropDir + id + "/" + id + "_LOD0.glb")) { log.Add(id + ": not prepared, skipped"); continue; }
                var dir = PropDir + id + "/";
                var maps = e["maps"];
                int baseSize = (int)maps["BaseColor_size"][0];
                ConfigureTexture(dir + (string)maps["BaseColor"], false, false, Math.Min(4096, baseSize), true);
                ConfigureTexture(dir + (string)maps["Normal"], true, true, Math.Min(4096, (int)maps["Normal_size"][0]), true);
                ConfigureTexture(dir + (string)maps["Mask"], false, true, 2048, true);   // metal/smoothness need no more than 2k
                if (e["screen"] is JObject s) ConfigureTexture((string)s["texture"], false, false, 2048, false);
                log.Add(BuildPrefab(id, e));
            }
            AssetDatabase.SaveAssets();
            return string.Join("\n", log);
        }

        // ------------------------------------------------------------------ verify
        static long TextureBytes(Texture2D t)
        {
            long sum = 0;
            for (int i = 0; i < t.mipmapCount; i++)
                sum += GraphicsFormatUtility.ComputeMipmapSize(Math.Max(1, t.width >> i), Math.Max(1, t.height >> i), t.graphicsFormat);
            return sum;
        }

        static int Tris(Mesh m) { long n = 0; for (int i = 0; i < m.subMeshCount; i++) n += m.GetIndexCount(i); return (int)(n / 3); }

        /// Nearest hit of a ray against the renderers' meshes (prefab space), or -1.
        static float RayHit(IEnumerable<Renderer> rs, Vector3 o, Vector3 d, Transform space)
        {
            float best = -1;
            foreach (var r in rs)
            {
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
                var mesh = mf.sharedMesh; var v = mesh.vertices;
                var m = space.worldToLocalMatrix * r.transform.localToWorldMatrix;
                for (int i = 0; i < v.Length; i++) v[i] = m.MultiplyPoint3x4(v[i]);
                for (int sub = 0; sub < mesh.subMeshCount; sub++)
                {
                    var tri = mesh.GetTriangles(sub, true);
                    for (int i = 0; i < tri.Length; i += 3)
                    {
                        Vector3 a = v[tri[i]], e1 = v[tri[i + 1]] - a, e2 = v[tri[i + 2]] - a;
                        var p = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, p);
                        if (Mathf.Abs(det) < 1e-9f) continue;
                        float inv = 1 / det; var tv = o - a; float u = Vector3.Dot(tv, p) * inv; if (u < 0 || u > 1) continue;
                        var q = Vector3.Cross(tv, e1); float w = Vector3.Dot(d, q) * inv; if (w < 0 || u + w > 1) continue;
                        float t = Vector3.Dot(e2, q) * inv;
                        if (t > 0 && (best < 0 || t < best)) best = t;
                    }
                }
            }
            return best;
        }

        public static string Verify()
        {
            var report = new Dictionary<string, object>();
            var problems = new List<string>();
            var allTextures = new HashSet<Texture2D>();
            foreach (var id in Ids)
            {
                var path = PrefabPath(id);
                if (!File.Exists(path)) { report[id] = "not built"; continue; }
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var g = root.GetComponent<LODGroup>();
                    var lods = g.GetLODs();
                    var lod0 = lods[0].renderers.Where(r => r && r.name != "Screen").ToList();
                    var b = Measure(lods[0].renderers.Where(r => r));
                    var b0 = Measure(lod0);
                    var lodInfo = lods.Select((l, i) => new
                    {
                        level = i, screenRelativeTransitionHeight = l.screenRelativeTransitionHeight,
                        triangles = l.renderers.Where(r => r).Sum(r => r.GetComponent<MeshFilter>() && r.GetComponent<MeshFilter>().sharedMesh ? Tris(r.GetComponent<MeshFilter>().sharedMesh) : 0),
                        renderers = l.renderers.Where(r => r).Select(r => r.name).ToArray(),
                        shadows = l.renderers.Where(r => r).Select(r => r.shadowCastingMode.ToString()).Distinct().ToArray(),
                    }).ToArray();
                    var mats = lods.SelectMany(l => l.renderers).Where(r => r).SelectMany(r => r.sharedMaterials).Where(m => m).Distinct().Select(m =>
                    {
                        var texs = m.GetTexturePropertyNames().Select(p => (p, t: m.GetTexture(p) as Texture2D)).Where(x => x.t).ToArray();
                        foreach (var x in texs) allTextures.Add(x.t);
                        return new
                        {
                            name = m.name, shader = m.shader.name, path = AssetDatabase.GetAssetPath(m), keywords = m.shaderKeywords,
                            smoothness = m.GetFloat("_Smoothness"), metallic = m.GetFloat("_Metallic"),
                            emission = m.IsKeywordEnabled("_EMISSION") ? A((Vector4)m.GetColor("_EmissionColor")) : null,
                            gi = m.globalIlluminationFlags.ToString(),
                            textures = texs.Select(x =>
                            {
                                var ti = AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(x.t)) as TextureImporter;
                                return new
                                {
                                    slot = x.p, file = AssetDatabase.GetAssetPath(x.t), size = new[] { x.t.width, x.t.height }, format = x.t.format.ToString(),
                                    srgb = ti ? ti.sRGBTexture : (bool?)null, normalMap = ti ? ti.textureType == TextureImporterType.NormalMap : (bool?)null,
                                    mips = x.t.mipmapCount, streaming = x.t.streamingMipmaps, aniso = x.t.anisoLevel, mb = Math.Round(TextureBytes(x.t) / 1048576.0, 2),
                                };
                            }).ToArray(),
                        };
                    }).ToArray();
                    var cols = root.GetComponentsInChildren<BoxCollider>(true).Select(c => new { name = c.name, center = A(c.center), size = A(c.size) }).ToArray();
                    var points = root.GetComponentsInChildren<Transform>(true).Where(t => t.name.EndsWith(" point")).ToDictionary(t => t.name, t => A(t.localPosition));
                    object screen = null;
                    var st = root.transform.Find("Screen");
                    if (st)
                    {
                        var mesh = st.GetComponent<MeshFilter>().sharedMesh;
                        var n = st.forward;
                        float gap;
                        try { gap = RayHit(lod0, st.localPosition + n * .001f, -n, root.transform); }
                        catch (Exception ex) { Debug.LogWarning("SalvageShopProps: screen gap not measured: " + ex.Message); gap = -2; }
                        screen = new { position = A(st.localPosition), facing = A(n), up = A(st.up), size = A(mesh.bounds.size), material = st.GetComponent<MeshRenderer>().sharedMaterial.name, gap_to_panel_m = Math.Round(gap, 4) };
                        if (n.z < .95f) problems.Add(id + ": screen does not face +Z");
                        if (gap < 0 || gap > .03f) problems.Add($"{id}: screen is {gap:F3} m from the modelled panel");
                    }
                    if (Mathf.Abs(b0.min.y) > .005f || Mathf.Abs(b0.center.x) > .01f || Mathf.Abs(b0.center.z) > .01f) problems.Add(id + ": pivot is not at the floor centre");
                    if (points.TryGetValue("Use point", out var up))
                    {
                        var body = root.GetComponentsInChildren<BoxCollider>(true).First();
                        float front = body.center.z + body.size.z / 2;
                        if (up[2] - front < .45f) problems.Add(id + ": use point within the player's radius of the bench");
                    }
                    if (points.TryGetValue("Light point", out var lp))
                        foreach (var c in root.GetComponentsInChildren<BoxCollider>(true))
                            if (new Bounds(c.center, c.size).Contains(new Vector3(lp[0], lp[1], lp[2]))) problems.Add(id + ": light point inside " + c.name);
                    report[id] = new
                    {
                        prefab = path, bounds_size = A(b.size), bounds_center = A(b.center), lod0_mesh_bounds_size = A(b0.size),
                        lodgroup_size = Math.Round(g.size, 3), fade = g.fadeMode.ToString(), lods = lodInfo, materials = mats, colliders = cols, points, screen,
                        static_flags = GameObjectUtility.GetStaticEditorFlags(root).ToString(),
                    };
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            var texMb = allTextures.Sum(t => TextureBytes(t)) / 1048576.0;
            var json = JsonConvert.SerializeObject(new
            {
                date = DateTime.Now.ToString("s", Inv), unity = Application.unityVersion,
                texture_memory_mb_all_mips = Math.Round(texMb, 1), problems, prefabs = report,
            }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "props-verify.json", json);
            return $"verified {report.Count} prefabs, textures {texMb:F1} MB, problems: {(problems.Count == 0 ? "none" : string.Join("; ", problems))}";
        }

        /// -executeMethod AthenHill.Editor.SalvageShopProps.RunBatch -nographics --steps build,verify
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string key, string d) { int i = Array.IndexOf(args, key); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            try
            {
                foreach (var st in Arg("--steps", "build,verify").Split(','))
                {
                    string result = st switch
                    {
                        "build" => Build(),
                        "verify" => Verify(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("SalvageShopProps " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
