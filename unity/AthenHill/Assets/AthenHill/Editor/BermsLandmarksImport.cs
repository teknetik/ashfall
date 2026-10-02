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
    /// 2 October 2026: three hero landmarks for the expanded Outer Berms (Carl: the Berms out to about 500 m with enemy
    /// sites spread out). Assets only: this builds prefabs and never opens or saves a scene; placement belongs to the
    /// Berms expanse pass.
    ///
    ///   CaravanHaulerWreck  a Karaveen caravan cargo hauler ambushed and stripped by feral droids, level on its axles
    ///   AquiferDerrick      a Great-Rebuild aquifer wellhead under a steel lattice pump derrick, hut and solar frame
    ///   TubePylonFall       a cracked Quantum Tube pylon leaning 4 degrees, with a fallen tube section at its foot
    ///
    /// Sources: Meshy multi-image-to-3D from Codex concept views (meshy/berms-landmarks-20261002: task ids, credits,
    /// prompts and inspection in README.md and record.json), fitted in Blender by its prepare.py (uniform scale, front =
    /// +Z, ground at y = 0, footprint centre at the origin, LOD1/LOD2 by collapse decimation, two-sided repair of thin
    /// sheets, maps extracted, box colliders fitted) into Art/BermsExpanse/Landmarks/&lt;Id&gt;/ with
    /// Landmarks/berms-landmarks.json (sizes, parts, maps, colliders in Unity axes).
    ///
    /// Steps (-executeMethod AthenHill.Editor.BermsLandmarksImport.RunBatch -nographics -quit --steps import,prefab,verify):
    ///   import  texture importers (BC7 base / BC5 normal / BC7 mask, mip streaming, aniso 8, clamp) and a forced
    ///           glTFast reimport of every LOD .glb (no embedded images), report to import.json;
    ///   prefab  URP Lit materials (editable, Materials/) and Prefabs/BermsExpanse/Landmarks/&lt;Id&gt;.prefab: root at the
    ///           ground centre, LODGroup 0.30 / 0.09 / cull 0.012 (fade none), LOD0 and LOD1 cast shadows, LOD2 does not,
    ///           box colliders under Colliders/, Occluder/Occludee/ReflectionProbe static;
    ///   verify  writes unity/evidence/berms-expanse/20261002/landmarks/verify.json (triangles per LOD, bounds,
    ///           colliders, materials, texture memory, problems).
    /// </summary>
    public static class BermsLandmarksImport
    {
        const string ArtDir = "Assets/AthenHill/Art/BermsExpanse/Landmarks/";
        const string MatDir = ArtDir + "Materials/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/BermsExpanse/Landmarks/";
        const string ManifestPath = ArtDir + "berms-landmarks.json";
        const string Evidence = "../evidence/berms-expanse/20261002/landmarks/";
        static readonly string[] Ids = { "CaravanHaulerWreck", "AquiferDerrick", "TubePylonFall" };
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        // Screen-relative LOD heights. The PC preset's LOD bias is 2 and the LODGroup size is the largest dimension, so at
        // a 60 degree FOV the hauler (10.5 m) switches to LOD1 at ~60 m and LOD2 at ~200 m and culls at ~1.5 km; the
        // pylon group (21 m) at ~120 m / ~400 m / ~3 km. Culling stays far outside the ~500 m Berms.
        const float Lod1At = .30f, Lod2At = .09f, CullAt = .012f;
        // URP mask alpha is 1 - Meshy roughness; the maps are mid-rough already, scaled a little for sun-dried surfaces
        const float SmoothnessScale = .85f;

        public static string PrefabPath(string id) => PrefabDir + id + ".prefab";

        static JObject Manifest() => File.Exists(ManifestPath) ? JObject.Parse(File.ReadAllText(ManifestPath)) : throw new Exception("Manifest missing: " + ManifestPath);
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static float[] A(Vector3 v) => new[] { (float)Math.Round(v.x, 4), (float)Math.Round(v.y, 4), (float)Math.Round(v.z, 4) };
        static string Dir(string id) => ArtDir + id + "/";

        // ------------------------------------------------------------------ textures
        static void ConfigureTexture(string path, bool normal, bool linear, int maxSize)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter ti) throw new Exception("Not a texture: " + path);
            ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = !normal && !linear;
            ti.alphaSource = linear && !normal ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
            ti.alphaIsTransparency = false;
            ti.mipmapEnabled = true;
            ti.streamingMipmaps = true;
            ti.anisoLevel = 8;
            ti.filterMode = FilterMode.Trilinear;
            ti.wrapMode = TextureWrapMode.Clamp;                       // Meshy atlases: no bleed from the opposite edge
            ti.maxTextureSize = maxSize;
            ti.npotScale = TextureImporterNPOTScale.None;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;   // BC7 colour/mask, BC5 normal
            ti.SaveAndReimport();
        }

        static Texture2D Tex(string path) => AssetDatabase.LoadAssetAtPath<Texture2D>(path) ?? throw new Exception("Texture missing: " + path);

        public static string Import()
        {
            AssetDatabase.Refresh();
            var man = Manifest();
            var report = new List<object>();
            foreach (var id in Ids)
            {
                if (man[id] is not JObject e) { report.Add(new { id, status = "not prepared" }); continue; }
                foreach (JObject p in e["parts"])
                {
                    var maps = p["maps"];
                    var dir = Dir(id);
                    ConfigureTexture(dir + (string)maps["BaseColor"], false, false, Math.Min(4096, (int)maps["BaseColor_size"][0]));
                    ConfigureTexture(dir + (string)maps["Normal"], true, true, Math.Min(4096, (int)maps["Normal_size"][0]));
                    ConfigureTexture(dir + (string)maps["Mask"], false, true, 2048);
                    var glbs = new List<object>();
                    foreach (var f in p["lods"])
                    {
                        var glb = dir + (string)f;
                        AssetDatabase.ImportAsset(glb, ImportAssetOptions.ForceUpdate);
                        var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
                        var meshes = AssetDatabase.LoadAllAssetsAtPath(glb).OfType<Mesh>().ToArray();
                        glbs.Add(new
                        {
                            file = glb, imported = model != null,
                            meshes = meshes.Select(m => new { m.name, vertices = m.vertexCount, triangles = Tris(m), index = m.indexFormat.ToString(), submeshes = m.subMeshCount }).ToArray(),
                        });
                    }
                    report.Add(new { id, part = (string)p["name"], glbs });
                }
            }
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "import.json", JsonConvert.SerializeObject(new { date = DateTime.Now.ToString("s", Inv), unity = Application.unityVersion, report }, Formatting.Indented));
            return $"imported {report.Count} parts";
        }

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

        static Material PartMaterial(string id, JObject p)
        {
            var dir = Dir(id);
            var maps = p["maps"];
            var m = MatAsset(MatDir + (string)p["stem"] + ".mat");
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

        // ------------------------------------------------------------------ prefabs
        static List<Renderer> Instance(string glb, Transform parent, string name, Material mat, ShadowCastingMode shadows)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(glb) ?? throw new Exception("Model not imported: " + glb);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            inst.name = name;
            inst.transform.SetParent(parent, false);
            inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity; inst.transform.localScale = Vector3.one;
            var rs = new List<Renderer>();
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
            {
                r.sharedMaterials = Enumerable.Repeat(mat, r.sharedMaterials.Length).ToArray();
                r.shadowCastingMode = shadows; r.receiveShadows = true;
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

        static string BuildPrefab(string id, JObject e)
        {
            var root = new GameObject(id);
            try
            {
                var lods = new List<Renderer>[3];
                for (int l = 0; l < 3; l++)
                {
                    lods[l] = new List<Renderer>();
                    var lg = new GameObject("LOD" + l);
                    lg.transform.SetParent(root.transform, false);
                    foreach (JObject p in e["parts"])
                    {
                        var mat = PartMaterial(id, p);
                        lods[l].AddRange(Instance(Dir(id) + (string)p["lods"][l], lg.transform, (string)p["name"], mat,
                            l < 2 ? ShadowCastingMode.On : ShadowCastingMode.Off));
                    }
                }
                var g = root.AddComponent<LODGroup>();
                g.SetLODs(new[] { new LOD(Lod1At, lods[0].ToArray()), new LOD(Lod2At, lods[1].ToArray()), new LOD(CullAt, lods[2].ToArray()) });
                g.fadeMode = LODFadeMode.None;
                g.RecalculateBounds();

                var cols = new GameObject("Colliders");
                cols.transform.SetParent(root.transform, false);
                foreach (var c in e["colliders"])
                {
                    var cg = new GameObject((string)c["name"]);
                    cg.transform.SetParent(cols.transform, false);
                    cg.transform.localPosition = V3(c["center"]);
                    cg.transform.localRotation = Quaternion.Euler(0f, (float)c["yaw"], 0f);
                    var box = cg.AddComponent<BoxCollider>();
                    box.center = Vector3.zero;
                    box.size = V3(c["size"]);
                }
                var flags = StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic;
                foreach (var t in root.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, flags);
                Directory.CreateDirectory(PrefabDir);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(id));
                var b = Measure(lods[0]);
                return $"{id}: size {b.size.x:F3} x {b.size.y:F3} x {b.size.z:F3}, centre {b.center.x:F3},{b.center.z:F3}, min y {b.min.y:F3}";
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }

        public static string Prefabs()
        {
            AssetDatabase.Refresh();
            var man = Manifest();
            var log = new List<string>();
            foreach (var id in Ids)
            {
                if (man[id] is not JObject e) { log.Add(id + ": not prepared, skipped"); continue; }
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

        public static string Verify()
        {
            var man = Manifest();
            var report = new Dictionary<string, object>();
            var problems = new List<string>();
            var allTextures = new HashSet<Texture2D>();
            foreach (var id in Ids)
            {
                var path = PrefabPath(id);
                if (!File.Exists(path)) { report[id] = "not built"; problems.Add(id + ": prefab missing"); continue; }
                var e = (JObject)man[id];
                var root = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var g = root.GetComponent<LODGroup>();
                    if (!g) { problems.Add(id + ": no LODGroup"); continue; }
                    var lods = g.GetLODs();
                    var b0 = Measure(lods[0].renderers.Where(r => r));
                    var lodInfo = lods.Select((l, i) => new
                    {
                        level = i, screenRelativeTransitionHeight = l.screenRelativeTransitionHeight,
                        triangles = l.renderers.Where(r => r).Sum(r => r.GetComponent<MeshFilter>() && r.GetComponent<MeshFilter>().sharedMesh ? Tris(r.GetComponent<MeshFilter>().sharedMesh) : 0),
                        vertices = l.renderers.Where(r => r).Sum(r => r.GetComponent<MeshFilter>() && r.GetComponent<MeshFilter>().sharedMesh ? r.GetComponent<MeshFilter>().sharedMesh.vertexCount : 0),
                        renderers = l.renderers.Where(r => r).Select(r => r.transform.parent ? r.transform.parent.name + "/" + r.name : r.name).ToArray(),
                        index_formats = l.renderers.Where(r => r && r.GetComponent<MeshFilter>() && r.GetComponent<MeshFilter>().sharedMesh).Select(r => r.GetComponent<MeshFilter>().sharedMesh.indexFormat.ToString()).Distinct().ToArray(),
                        shadows = l.renderers.Where(r => r).Select(r => r.shadowCastingMode.ToString()).Distinct().ToArray(),
                        bounds_size = A(Measure(l.renderers.Where(r => r)).size),
                    }).ToArray();
                    var mats = lods.SelectMany(l => l.renderers).Where(r => r).SelectMany(r => r.sharedMaterials).Distinct().Select(m =>
                    {
                        if (!m) { problems.Add(id + ": missing material"); return null; }
                        var texs = m.GetTexturePropertyNames().Select(p => (p, t: m.GetTexture(p) as Texture2D)).Where(x => x.t).ToArray();
                        foreach (var x in texs) allTextures.Add(x.t);
                        if (m.shader.name != "Universal Render Pipeline/Lit") problems.Add(id + ": material " + m.name + " is not URP Lit");
                        return (object)new
                        {
                            name = m.name, shader = m.shader.name, path = AssetDatabase.GetAssetPath(m), keywords = m.shaderKeywords,
                            smoothness = m.GetFloat("_Smoothness"), metallic = m.GetFloat("_Metallic"), cull = m.GetFloat("_Cull"),
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
                    }).Where(x => x != null).ToArray();
                    var boxes = root.GetComponentsInChildren<BoxCollider>(true);
                    var cols = boxes.Select(c =>
                    {
                        var t = c.transform;
                        var wb = new Bounds(t.TransformPoint(c.center), Vector3.zero);
                        foreach (var sx in new[] { -.5f, .5f }) foreach (var sy in new[] { -.5f, .5f }) foreach (var sz in new[] { -.5f, .5f })
                            wb.Encapsulate(t.TransformPoint(c.center + Vector3.Scale(c.size, new Vector3(sx, sy, sz))));
                        return new { name = c.name, center = A(t.localPosition), size = A(c.size), yaw = Math.Round(t.localEulerAngles.y, 2), aabb_min = A(wb.min), aabb_max = A(wb.max) };
                    }).ToArray();
                    // checks: footprint centred, ground at 0 (the pylon's buried footing edge goes below), manifest size, colliders inside the model
                    var size = V3(e["size"]);
                    if (Mathf.Abs(b0.center.x) > .05f || Mathf.Abs(b0.center.z) > .05f) problems.Add($"{id}: footprint centre is {b0.center.x:F3},{b0.center.z:F3}, not the origin");
                    if ((b0.size - size).magnitude > .05f) problems.Add($"{id}: LOD0 size {b0.size} differs from the manifest {size}");
                    foreach (var c in cols)
                    {
                        var ctr = new Vector3(c.center[0], c.center[1], c.center[2]);
                        if (ctr.x < b0.min.x || ctr.x > b0.max.x || ctr.z < b0.min.z || ctr.z > b0.max.z) problems.Add($"{id}: collider {c.name} centre outside the model");
                    }
                    if (boxes.Length == 0) problems.Add(id + ": no colliders");
                    for (int i = 1; i < lodInfo.Length; i++)
                        if (lodInfo[i].triangles >= lodInfo[i - 1].triangles) problems.Add($"{id}: LOD{i} has no fewer triangles than LOD{i - 1}");
                    report[id] = new
                    {
                        prefab = path, lod0_bounds_size = A(b0.size), lod0_bounds_center = A(b0.center), lod0_bounds_min = A(b0.min), lod0_bounds_max = A(b0.max),
                        manifest_size = A(size), lodgroup_size = Math.Round(g.size, 3), fade = g.fadeMode.ToString(), lods = lodInfo, materials = mats,
                        colliders = cols, static_flags = GameObjectUtility.GetStaticEditorFlags(root).ToString(),
                    };
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            var texMb = allTextures.Sum(t => TextureBytes(t)) / 1048576.0;
            var json = JsonConvert.SerializeObject(new
            {
                date = DateTime.Now.ToString("s", Inv), unity = Application.unityVersion,
                lod_screen_heights = new[] { Lod1At, Lod2At, CullAt }, texture_memory_mb_all_mips = Math.Round(texMb, 1), problems, prefabs = report,
            }, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", json);
            return $"verified {report.Count} prefabs, textures {texMb:F1} MB, problems: {(problems.Count == 0 ? "none" : string.Join("; ", problems))}";
        }

        /// -executeMethod AthenHill.Editor.BermsLandmarksImport.RunBatch -nographics -quit --steps import,prefab,verify
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string key, string d) { int i = Array.IndexOf(args, key); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            try
            {
                foreach (var st in Arg("--steps", "import,prefab,verify").Split(','))
                {
                    string result = st switch
                    {
                        "import" => Import(),
                        "prefab" => Prefabs(),
                        "verify" => Verify(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("BermsLandmarksImport " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
