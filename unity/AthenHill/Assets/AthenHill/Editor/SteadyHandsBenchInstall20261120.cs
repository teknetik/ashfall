using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>
    /// 20 November 2026, Steady Hands bench programme, integration agent: the real models on the bench, their surfaces,
    /// the bench's light and its close review cameras. Record: art/steady_hands_bench_20261120/integration/README.md.
    /// Every number is in art/steady_hands_bench_20261120/integration/look.json.
    ///
    /// import    : import settings of every family under Art/Bench (GLB anisotropy; the as-found PNG sets as plain linear /
    ///             sRGB textures, BC7, streamed), then triangles, materials and texture memory per family -> import.json.
    /// materials : one Bench Surface material per GLB material (Art/Bench/&lt;Family&gt;/Materials), with an as-found variant
    ///             for the parts a family lists under `wipes` and a lamp variant for the parts the bench drives as lamps.
    ///             Re-run after a family is re-exported: textures are bound by the GLB's own material, by name.
    /// bind      : the bench's own installer steps `prefab` and `scene` (AssemblyBenchInstall20261120), with the families
    ///             of data/sources.json as real art. Nothing is written into its prefab from here. -> bind.json
    /// light     : scene roots "Steady Hands bench light" (work lamp, cure lamp, BenchLook) and "Steady Hands bench review
    ///             cameras" (cam_bench_close_*). Found or made, never rebuilt: a second run leaves the scene as it is.
    /// install   : import, materials, bind, light.
    /// verify    : on the saved scene, -nographics -> verify.json (throws on a problem).
    /// dryrun    : BenchLook's own code run on the saved scene in the Editor (no Play mode, nothing saved) -> dryrun.json
    /// benchverify, benchselftest, benchbindcheck : the bench installer's own verify, selftest and bindcheck, in the same Unity run.
    /// rollback  : removes the two scene roots (assets stay). To go back to stand-ins as well: set every family in
    ///             data/sources.json to "greybox" and run `bind` (integration/run.sh rollback does both).
    /// -executeMethod AthenHill.Editor.SteadyHandsBenchInstall20261120.RunBatch --steps install,verify [--real a,b,c]
    /// </summary>
    public static class SteadyHandsBenchInstall20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string ArtDir = "Assets/AthenHill/Art/Bench/";
        const string ShaderName = "Athen Hill/Bench Surface";
        const string ShaderPath = "Assets/AthenHill/Shaders/BenchSurface.shader";
        public const string LightRoot = "Steady Hands bench light";
        public const string CameraRoot = "Steady Hands bench review cameras";
        const uint InteriorLayer = 1u << 7;
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Programme => Path.Combine(Repo, "art/steady_hands_bench_20261120");
        static string LookPath => Path.Combine(Programme, "integration/look.json");
        static string SourcesPath => Path.Combine(Programme, "data/sources.json");
        static string LayoutPath => Path.Combine(Programme, "data/layout.json");
        static string RecordPath => Path.Combine(Programme, "integration/record.json");
        static string Evidence => Path.Combine(Repo, "unity/evidence/steady_hands/20261120/integration");

        static JObject look;
        static JObject Look => look ?? (look = JObject.Parse(File.ReadAllText(LookPath)));
        static float F(JToken t, float fallback = 0) => t == null || t.Type == JTokenType.Null ? fallback : (float)t;
        static Vector3 V(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static Color C(JToken t, float a = 1) => new Color((float)t[0], (float)t[1], (float)t[2], a);
        static string Cap(string family) => char.ToUpperInvariant(family[0]) + family.Substring(1);
        static string Glb(string family) => ArtDir + Cap(family) + "/" + family + ".glb";
        static string PartsFile(string family) => ArtDir + Cap(family) + "/" + family + ".parts.json";
        static void WriteEvidence(string name, object value) { Directory.CreateDirectory(Evidence); File.WriteAllText(Path.Combine(Evidence, name), value is JToken t ? t.ToString(Formatting.Indented) : JsonConvert.SerializeObject(value, Formatting.Indented)); }
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        /// The families that have a model in Art/Bench.
        static List<string> Present() => AssemblyKitBuilder.Families.Where(f => File.Exists(Glb(f)) && File.Exists(PartsFile(f))).ToList();

        /// The families the bench is built from as real art: data/sources.json.
        static List<string> Real()
        {
            if (!File.Exists(SourcesPath)) return new List<string>();
            // the shape the bench installer's reader takes: {"pistol": "real", "tools": "greybox", ...} (a family not named is a stand-in)
            var o = JObject.Parse(File.ReadAllText(SourcesPath));
            return AssemblyKitBuilder.Families.Where(f => o[f] != null && o[f].Type == JTokenType.String && (string)o[f] == "real").ToList();
        }

        // ------------------------------------------------------------------ the GLB's own JSON (factors glTFast does not keep)
        static JObject GlbJson(string assetPath)
        {
            using (var f = File.OpenRead(assetPath))
            using (var r = new BinaryReader(f))
            {
                if (r.ReadUInt32() != 0x46546C67) throw new Exception(assetPath + " is not a GLB");
                r.ReadUInt32(); r.ReadUInt32();
                int length = (int)r.ReadUInt32(); r.ReadUInt32();
                return JObject.Parse(Encoding.UTF8.GetString(r.ReadBytes(length)));
            }
        }

        // ------------------------------------------------------------------ import
        static bool SetImporter(string path, Action<SerializedObject, List<string>> edit, List<string> log)
        {
            var importer = AssetImporter.GetAtPath(path); if (!importer) { log.Add("no importer for " + path); return false; }
            var so = new SerializedObject(importer); var changes = new List<string>(); edit(so, changes);
            if (changes.Count == 0) return false;
            so.ApplyModifiedPropertiesWithoutUndo(); importer.SaveAndReimport();
            log.Add(path + ": " + string.Join(", ", changes));
            return true;
        }
        static void Int(SerializedObject so, string prop, int value, List<string> changes)
        {
            var p = so.FindProperty(prop); if (p == null) { changes.Add("no property " + prop); return; }
            if (p.intValue != value) { changes.Add($"{prop} {p.intValue} -> {value}"); p.intValue = value; }
        }

        static void DirtyTexture(string path, bool srgb, int maxSize, int aniso, List<string> log)
        {
            var ti = AssetImporter.GetAtPath(path) as TextureImporter; if (!ti) { log.Add("no texture importer for " + path); return; }
            var want = new { type = TextureImporterType.Default, srgb, mip = true, aniso, max = maxSize, comp = TextureImporterCompression.CompressedHQ };
            var ps = ti.GetPlatformTextureSettings("Standalone");
            bool same = ti.textureType == want.type && ti.sRGBTexture == srgb && ti.mipmapEnabled && ti.anisoLevel == aniso && ti.maxTextureSize == maxSize && ti.textureCompression == want.comp
                && ti.streamingMipmaps && ti.wrapMode == TextureWrapMode.Repeat && ti.filterMode == FilterMode.Trilinear && !ti.isReadable && ti.alphaSource == TextureImporterAlphaSource.None
                && ps.overridden && ps.format == TextureImporterFormat.BC7 && ps.maxTextureSize == maxSize && ti.npotScale == TextureImporterNPOTScale.ToNearest;
            if (same) return;
            // a plain texture, not a Unity normal map: the GLB's own normals arrive as RGB and both sets go through one decode
            ti.textureType = TextureImporterType.Default; ti.sRGBTexture = srgb; ti.mipmapEnabled = true; ti.anisoLevel = aniso; ti.maxTextureSize = maxSize;
            ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.streamingMipmaps = true; ti.wrapMode = TextureWrapMode.Repeat; ti.filterMode = FilterMode.Trilinear;
            ti.isReadable = false; ti.alphaSource = TextureImporterAlphaSource.None; ti.npotScale = TextureImporterNPOTScale.ToNearest;
            ps.name = "Standalone"; ps.overridden = true; ps.format = TextureImporterFormat.BC7; ps.maxTextureSize = maxSize; ti.SetPlatformTextureSettings(ps);
            ti.SaveAndReimport();
            log.Add($"{path}: plain {(srgb ? "sRGB" : "linear")} BC7, max {maxSize}, aniso {aniso}, streamed");
        }

        static long TextureBytes(Texture t) => UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(t);

        static object Import()
        {
            var log = new List<string>(); var cfg = (JObject)Look["import"]; int aniso = (int)cfg["anisotropic"];
            AssetDatabase.Refresh();
            var glbs = Present().Select(Glb).Concat(((JArray)cfg["extraGlbs"]).Select(x => ArtDir + (string)x).Where(File.Exists)).ToList();
            // Legacy animation: AssemblyParam samples each *_param clip with AnimationClip.SampleAnimation, which in a player
            // works on legacy clips only (sh-real1, 21 Nov: 10,025 "Non-Legacy animations cannot be sampled" errors)
            foreach (var path in glbs)
                SetImporter(path, (so, changes) =>
                {
                    Int(so, "importSettings.anisotropicFilterLevel", aniso, changes);
                    var m = so.FindProperty("importSettings.animationMethod");
                    if (m == null) changes.Add("no property importSettings.animationMethod");
                    else { int legacy = Array.IndexOf(m.enumNames, "Legacy"); if (legacy < 0) changes.Add("no Legacy animation method"); else if (m.enumValueIndex != legacy) { changes.Add($"animationMethod {m.enumNames[m.enumValueIndex]} -> Legacy"); m.enumValueIndex = legacy; } }
                }, log);
            var notLegacy = glbs.SelectMany(g => AssetDatabase.LoadAllAssetsAtPath(g).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__") && !c.legacy).Select(c => g + ":" + c.name)).ToList();
            if (notLegacy.Count > 0) throw new Exception("import: clips still not legacy after the reimport: " + string.Join(", ", notLegacy.Take(8)));
            var families = new JObject();
            foreach (var family in Present())
            {
                string dir = ArtDir + Cap(family) + "/tex";
                int max = (int)(cfg["dirtyMaxSize"][family] ?? cfg["dirtyMaxSize"]["default"]);
                if (Directory.Exists(dir))
                    foreach (var png in Directory.GetFiles(dir, "*__dirty_*.png").Select(p => p.Replace('\\', '/')).OrderBy(p => p))
                        DirtyTexture(png, png.EndsWith("_color.png"), max, aniso, log);
                families[family] = Stats(family);
            }
            var extra = new JObject();
            foreach (var path in glbs.Where(p => !Present().Select(Glb).Contains(p))) extra[path] = StatsOf(path, null);
            var report = new JObject { ["families"] = families, ["otherModels"] = extra, ["changes"] = new JArray(log),
                ["compressionAddOn"] = GltfTextureCompression.Enabled, ["note"] = "texture bytes are what the Editor holds (Profiler.GetRuntimeMemorySizeLong); design budget: one 2048 set per family (16 MB as BC7 with mips)" };
            WriteEvidence("import.json", report);
            return new { families = Present(), changed = log.Count, log };
        }

        static JObject Stats(string family)
        {
            var o = StatsOf(Glb(family), family);
            string dir = ArtDir + Cap(family) + "/tex"; var dirty = new JArray(); long bytes = 0;
            if (Directory.Exists(dir))
                foreach (var png in Directory.GetFiles(dir, "*__dirty_*.png").Select(p => p.Replace('\\', '/')).OrderBy(p => p))
                {
                    var t = AssetDatabase.LoadAssetAtPath<Texture2D>(png); if (!t) continue;
                    long b = TextureBytes(t); bytes += b;
                    dirty.Add(new JObject { ["file"] = Path.GetFileName(png), ["size"] = t.width + "x" + t.height, ["format"] = t.format.ToString(), ["srgb"] = UnityEngine.Experimental.Rendering.GraphicsFormatUtility.IsSRGBFormat(t.graphicsFormat), ["mips"] = t.mipmapCount, ["streamed"] = t.streamingMipmaps, ["megabytes"] = Math.Round(b / 1048576.0, 2) });
                }
            o["asFoundTextures"] = dirty; o["asFoundMegabytes"] = Math.Round(bytes / 1048576.0, 2);
            o["textureMegabytesTotal"] = Math.Round((double)o["textureMegabytes"] + bytes / 1048576.0, 2);
            return o;
        }

        static JObject StatsOf(string glb, string family)
        {
            var o = new JObject { ["model"] = glb };
            var all = AssetDatabase.LoadAllAssetsAtPath(glb);
            var meshes = all.OfType<Mesh>().ToList(); long tris = 0;
            foreach (var m in meshes) for (int s = 0; s < m.subMeshCount; s++) tris += m.GetIndexCount(s) / 3;
            o["meshes"] = meshes.Count; o["triangles"] = tris; o["readableMeshes"] = meshes.Count(m => m.isReadable);
            var root = AssetDatabase.LoadAssetAtPath<GameObject>(glb);
            if (root)
            {
                o["renderers"] = root.GetComponentsInChildren<Renderer>(true).Length; o["skinned"] = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length;
                o["colliders"] = root.GetComponentsInChildren<Collider>(true).Length; o["nodes"] = root.GetComponentsInChildren<Transform>(true).Length;
                o["notCastingShadows"] = root.GetComponentsInChildren<Renderer>(true).Count(r => r.shadowCastingMode == ShadowCastingMode.Off);
            }
            o["materials"] = new JArray(all.OfType<Material>().Select(m => m.name + " (" + (m.shader ? m.shader.name : "no shader") + ")").OrderBy(x => x));
            o["clips"] = new JArray(all.OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).Select(c => c.name).OrderBy(x => x));
            var textures = new JArray(); long bytes = 0;
            foreach (var t in all.OfType<Texture2D>().OrderBy(t => t.name))
            {
                long b = TextureBytes(t); bytes += b;
                textures.Add(new JObject { ["name"] = t.name, ["size"] = t.width + "x" + t.height, ["format"] = t.format.ToString(), ["srgb"] = UnityEngine.Experimental.Rendering.GraphicsFormatUtility.IsSRGBFormat(t.graphicsFormat), ["mips"] = t.mipmapCount, ["aniso"] = t.anisoLevel, ["filter"] = t.filterMode.ToString(), ["readable"] = t.isReadable, ["megabytes"] = Math.Round(b / 1048576.0, 2) });
            }
            o["textures"] = textures; o["textureMegabytes"] = Math.Round(bytes / 1048576.0, 2);
            if (family != null)
            {
                var parts = JObject.Parse(File.ReadAllText(PartsFile(family)));
                o["partsListed"] = ((JArray)parts["parts"]).Count; o["generated"] = (string)parts["generated"];
                int budget = family == "pistol" ? 45000 : family == "grip" ? 25000 : family == "servo" ? 45000 : family == "materials" ? 15000 : family == "tools" ? 60000 : 70000;
                o["triangleBudget"] = budget; o["withinTriangleBudget"] = tris <= budget;
            }
            return o;
        }

        // ------------------------------------------------------------------ materials
        static Material Asset(string path, Shader shader, out bool created)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path); created = !m;
            if (!m) { Directory.CreateDirectory(Path.GetDirectoryName(path)); m = new Material(shader) { name = Path.GetFileNameWithoutExtension(path) }; AssetDatabase.CreateAsset(m, path); }
            if (m.shader != shader) m.shader = shader;
            return m;
        }
        static void Keyword(Material m, string keyword, bool on) { if (on) m.EnableKeyword(keyword); else m.DisableKeyword(keyword); }

        /// The part ids of a family whose nodes use a material, by the model's own hierarchy.
        static Dictionary<string, HashSet<string>> MaterialsOfParts(string family, JObject parts)
        {
            var result = new Dictionary<string, HashSet<string>>();
            var root = AssetDatabase.LoadAssetAtPath<GameObject>(Glb(family)); if (!root) return result;
            // a renderer belongs to the nearest node above it (or itself) that is a part: glTFast may put a part's primitives on children
            var partOfNode = new Dictionary<string, string>();
            foreach (JObject e in (JArray)parts["parts"]) { result[(string)e["id"]] = new HashSet<string>(); partOfNode[(string)e["node"] ?? ""] = (string)e["id"]; }
            foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            {
                string id = null; for (var t = r.transform; t && id == null; t = t.parent) partOfNode.TryGetValue(t.name, out id);
                if (id != null) foreach (var m in r.sharedMaterials) if (m) result[id].Add(m.name);
            }
            return result;
        }

        static object Materials()
        {
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath) ?? throw new Exception("missing " + ShaderPath);
            if (ShaderUtil.ShaderHasError(shader)) throw new Exception("Bench Surface has errors: " + string.Join(" | ", ShaderUtil.GetShaderMessages(shader).Select(m => m.message + " @" + m.line)));
            var cfg = (JObject)Look["surface"]; var report = new JObject(); var problems = new List<string>();
            var lampParts = new HashSet<string>(((JArray)JObject.Parse(File.ReadAllText(LayoutPath))["lamps"] ?? new JArray()).Select(l => (string)l["part"]));
            foreach (var family in Present())
            {
                string glb = Glb(family), dir = ArtDir + Cap(family) + "/Materials/";
                var json = GlbJson(glb); var parts = JObject.Parse(File.ReadAllText(PartsFile(family)));
                var sources = AssetDatabase.LoadAllAssetsAtPath(glb).OfType<Material>().GroupBy(m => m.name).ToDictionary(g => g.Key, g => g.First());
                var used = MaterialsOfParts(family, parts);
                var wipeMaterials = new HashSet<string>(((JArray)parts["parts"]).Where(e => e["wipes"] is JArray w && w.Count > 0).SelectMany(e => used.TryGetValue((string)e["id"], out var s) ? s : new HashSet<string>()));
                var lampMaterials = new HashSet<string>(((JArray)parts["parts"]).Where(e => lampParts.Contains((string)e["id"])).SelectMany(e => used.TryGetValue((string)e["id"], out var s) ? s : new HashSet<string>()));
                var rows = new JArray();
                foreach (JObject jm in (JArray)(json["materials"] ?? new JArray()))
                {
                    string name = (string)jm["name"] ?? "";
                    if (!sources.TryGetValue(name, out var src)) { problems.Add($"{family}: the model's material '{name}' was not imported under that name"); continue; }
                    Texture Tex(string prop) => src.HasProperty(prop) ? src.GetTexture(prop) : null;
                    var pbr = jm["pbrMetallicRoughness"] as JObject ?? new JObject();
                    Texture baseTex = Tex("baseColorTexture"), normal = Tex("normalTexture"), orm = Tex("metallicRoughnessTexture"), occ = Tex("occlusionTexture"), emit = Tex("emissiveTexture");
                    if (pbr["baseColorTexture"] != null && !baseTex) problems.Add($"{family}/{name}: base colour texture not found on the imported material");
                    if (jm["normalTexture"] != null && !normal) problems.Add($"{family}/{name}: normal texture not found on the imported material");
                    if (pbr["metallicRoughnessTexture"] != null && !orm) problems.Add($"{family}/{name}: metallic-roughness texture not found on the imported material");
                    if (occ && orm && occ != orm) problems.Add($"{family}/{name}: occlusion is not packed with roughness and metallic (the surface reads one map)");
                    var bc = pbr["baseColorFactor"] as JArray; var baseColour = bc != null ? new Color((float)bc[0], (float)bc[1], (float)bc[2], (float)bc[3]).gamma : Color.white;
                    if (bc != null) baseColour.a = (float)bc[3];
                    float metallic = F(pbr["metallicFactor"], 1), roughness = F(pbr["roughnessFactor"], 1);
                    var ef = jm["emissiveFactor"] as JArray; float strength = F(jm["extensions"]?["KHR_materials_emissive_strength"]?["emissiveStrength"], F(cfg["emissionStrength"]?[name], 1));
                    var emission = ef != null ? new Color((float)ef[0], (float)ef[1], (float)ef[2]) * strength * F(cfg["emission"], 1) : Color.black; emission.a = 1;
                    bool emissive = emission.maxColorComponent > 0, transparent = (string)jm["alphaMode"] == "BLEND", clip = (string)jm["alphaMode"] == "MASK", twoSided = jm["doubleSided"] != null && (bool)jm["doubleSided"];
                    if (transparent) roughness = Mathf.Max(roughness, 1 - F(cfg["glassSmoothnessCap"], 1));
                    // glTFast flips V in the mesh and leaves standard images alone; an image it could not flip gets a texture
                    // transform on its material instead. Whatever it set is taken over (every map of a surface shares one UV).
                    var st = new Vector4(1, 1, 0, 0);
                    if (baseTex && src.HasProperty("baseColorTexture_ST")) st = src.GetVector("baseColorTexture_ST");
                    foreach (var other in new[] { "normalTexture_ST", "metallicRoughnessTexture_ST", "occlusionTexture_ST", "emissiveTexture_ST" })
                        if (baseTex && src.HasProperty(other) && src.GetTexture(other.Substring(0, other.Length - 3)) && src.GetVector(other) != st) problems.Add($"{family}/{name}: {other} {src.GetVector(other)} differs from the base colour's {st} (the surface has one UV transform)");

                    void Fill(Material m, bool wipe, bool lamp)
                    {
                        m.SetTexture("_BaseMap", baseTex); m.SetColor("_BaseColor", baseColour);
                        m.SetTextureScale("_BaseMap", new Vector2(st.x, st.y)); m.SetTextureOffset("_BaseMap", new Vector2(st.z, st.w));
                        m.SetTexture("_BumpMap", normal); m.SetFloat("_BumpScale", F(jm["normalTexture"]?["scale"], 1) * F(cfg["normalScale"], 1)); Keyword(m, "_NORMALMAP", normal);
                        m.SetTexture("_BenchOrmMap", orm); m.SetFloat("_Metallic", metallic); m.SetFloat("_BenchRoughness", roughness);
                        m.SetFloat("_OcclusionStrength", occ ? F(jm["occlusionTexture"]?["strength"], 1) * F(cfg["occlusion"], 1) : 0);
                        bool glow = emissive && !lamp;
                        m.SetTexture("_EmissionMap", glow ? emit : null); m.SetColor("_BenchEmission", glow ? emission : Color.black); Keyword(m, "_EMISSION", glow);
                        m.SetColor("_EmissionColor", Color.black); m.SetColor("emissiveFactor", Color.black);
                        m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                        m.SetFloat("_BenchRim", lamp ? 0 : F(cfg["rim"], 1)); m.SetFloat("_BenchRimPower", F(cfg["rimPower"], 2)); m.SetFloat("_BenchRimFloor", F(cfg["rimFloor"], .2f));
                        m.SetFloat("_BenchWipeGrain", F(cfg["wipeGrain"], .35f)); m.SetFloat("_BenchWipeEdge", F(cfg["wipeEdge"], .14f));
                        Keyword(m, "_BENCH_WIPE", wipe);
                        if (!wipe) { m.SetTexture("_BenchDirtyBaseMap", null); m.SetTexture("_BenchDirtyNormalMap", null); m.SetTexture("_BenchDirtyOrmMap", null); }
                        // surface type, as URP's Lit GUI would set it
                        m.SetFloat("_Surface", transparent ? 1 : 0); m.SetFloat("_Blend", 0); m.SetFloat("_Cull", twoSided ? (float)CullMode.Off : (float)CullMode.Back);
                        m.SetFloat("_AlphaClip", clip ? 1 : 0); m.SetFloat("_Cutoff", F(jm["alphaCutoff"], .5f)); Keyword(m, "_ALPHATEST_ON", clip);
                        m.SetFloat("_SrcBlend", (float)BlendMode.One); m.SetFloat("_DstBlend", transparent ? (float)BlendMode.OneMinusSrcAlpha : (float)BlendMode.Zero);
                        m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); m.SetFloat("_DstBlendAlpha", transparent ? (float)BlendMode.OneMinusSrcAlpha : (float)BlendMode.Zero);
                        m.SetFloat("_ZWrite", transparent ? 0 : 1); m.SetFloat("_BlendModePreserveSpecular", 1); m.SetFloat("_ReceiveShadows", 1);
                        Keyword(m, "_SURFACE_TYPE_TRANSPARENT", transparent); Keyword(m, "_ALPHAPREMULTIPLY_ON", transparent);
                        m.SetOverrideTag("RenderType", transparent ? "Transparent" : clip ? "TransparentCutout" : "Opaque");
                        m.renderQueue = transparent ? (int)RenderQueue.Transparent : clip ? (int)RenderQueue.AlphaTest : (int)RenderQueue.Geometry;
                        foreach (var pass in new[] { "ShadowCaster", "DepthOnly", "DepthNormals", "MotionVectors" }) m.SetShaderPassEnabled(pass, !transparent);
                        m.enableInstancing = false;
                        EditorUtility.SetDirty(m);
                    }

                    var plain = Asset(dir + name + ".mat", shader, out bool made); Fill(plain, false, false);
                    var row = new JObject { ["source"] = name, ["plain"] = dir + name + ".mat", ["created"] = made, ["transparent"] = transparent, ["twoSided"] = twoSided,
                        ["metallic"] = metallic, ["roughness"] = roughness, ["uvTransform"] = new JArray(st.x, st.y, st.z, st.w), ["emission"] = emissive ? new JArray(emission.r, emission.g, emission.b) : null,
                        ["textures"] = new JObject { ["base"] = baseTex ? baseTex.name : null, ["normal"] = normal ? normal.name : null, ["orm"] = orm ? orm.name : null, ["emission"] = emit ? emit.name : null } };
                    // the as-found set: tex/<family>__dirty_* for M_<family>, tex/<family>_<x>__dirty_* for M_<family>_<x>
                    string stem = name.StartsWith("M_") ? name.Substring(2) : name, tex = ArtDir + Cap(family) + "/tex/" + stem + "__dirty_";
                    var dc = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "color.png"); var dn = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "normal.png"); var dorm = AssetDatabase.LoadAssetAtPath<Texture2D>(tex + "orm.png");
                    string wipePath = dir + name + "__wipe.mat";
                    if (wipeMaterials.Contains(name))
                    {
                        if (!dc || !dn || !dorm) problems.Add($"{family}/{name}: parts list wipes but {tex}color/normal/orm.png are not all there");
                        else
                        {
                            var w = Asset(wipePath, shader, out _); Fill(w, true, false);
                            w.SetTexture("_BenchDirtyBaseMap", dc); w.SetTexture("_BenchDirtyNormalMap", dn); w.SetTexture("_BenchDirtyOrmMap", dorm); EditorUtility.SetDirty(w);
                            row["wipe"] = wipePath;
                        }
                    }
                    else if (File.Exists(wipePath)) AssetDatabase.DeleteAsset(wipePath);
                    string lampPath = dir + name + "__lamp.mat";
                    if (lampMaterials.Contains(name)) { var l = Asset(lampPath, shader, out _); Fill(l, false, true); row["lamp"] = lampPath; }
                    else if (File.Exists(lampPath)) AssetDatabase.DeleteAsset(lampPath);
                    rows.Add(row);
                }
                report[family] = rows;
            }
            AssetDatabase.SaveAssets();
            report["problems"] = new JArray(problems); report["shader"] = ShaderName; report["variants"] = Variants(shader, problems);
            WriteEvidence("materials.json", report);
            if (problems.Count > 0) throw new Exception("materials: " + string.Join("; ", problems));
            return new { families = Present(), materials = Present().Sum(f => ((JArray)report[f]).Count) };
        }

        /// Compiles the forward pass for the OpenGL player with the keyword sets the bench uses, so a shader error shows here
        /// and not in a build nobody has looked at.
        static JArray Variants(Shader shader, List<string> problems)
        {
            var rows = new JArray();
            try
            {
                var data = ShaderUtil.GetShaderData(shader); var sub = data.GetSubshader(0);
                string[] urp = { "_ADDITIONAL_LIGHTS", "_ADDITIONAL_LIGHT_SHADOWS", "_SHADOWS_SOFT", "_LIGHT_LAYERS", "_CLUSTER_LIGHT_LOOP", "_MAIN_LIGHT_SHADOWS_CASCADE", "_REFLECTION_PROBE_BOX_PROJECTION", "_SCREEN_SPACE_OCCLUSION" };
                var sets = new (string name, string[] keys)[]
                {
                    ("plain", new[] { "_NORMALMAP" }), ("as found", new[] { "_NORMALMAP", "_BENCH_WIPE" }), ("emissive", new[] { "_NORMALMAP", "_EMISSION" }),
                    ("glass", new[] { "_SURFACE_TYPE_TRANSPARENT", "_ALPHAPREMULTIPLY_ON" }),
                };
                for (int p = 0; p < sub.PassCount; p++)
                {
                    var pass = sub.GetPass(p);
                    foreach (var set in pass.Name == "ForwardLit" ? sets : sets.Take(1))
                        foreach (var stage in new[] { ShaderType.Vertex, ShaderType.Fragment })
                        {
                            var keys = pass.Name == "ForwardLit" ? set.keys.Concat(urp).ToArray() : set.keys;
                            var info = pass.CompileVariant(stage, keys, ShaderCompilerPlatform.OpenGLCore, BuildTarget.StandaloneLinux64);
                            var errors = (info.Messages ?? new ShaderMessage[0]).Where(m => m.severity == ShaderCompilerMessageSeverity.Error).Select(m => m.message + " @" + m.file + ":" + m.line).Distinct().ToList();
                            rows.Add(new JObject { ["pass"] = pass.Name, ["set"] = set.name, ["stage"] = stage.ToString(), ["ok"] = info.Success, ["bytes"] = info.ShaderData != null ? info.ShaderData.Length : 0, ["errors"] = new JArray(errors) });
                            if (!info.Success) problems.Add($"Bench Surface {pass.Name} ({set.name}, {stage}) does not compile for GLCore: {string.Join(" | ", errors.Take(3))}");
                        }
                }
            }
            catch (Exception e) { rows.Add(new JObject { ["exception"] = e.GetType().Name + ": " + e.Message }); problems.Add("could not compile the Bench Surface variants: " + e.Message); }
            return rows;
        }

        // ------------------------------------------------------------------ bind (the bench installer's own steps)
        static object BenchStep(string method)
        {
            var m = typeof(AssemblyBenchInstall20261120).GetMethod(method, BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public)
                ?? throw new Exception("AssemblyBenchInstall20261120 has no step method " + method + " (the bench installer changed: run its steps through its own RunBatch)");
            // the bench's steps may take optional parameters (SelfTest gained one on 21 Nov): pass their defaults
            var ps = m.GetParameters(); var values = ps.Select(p => p.HasDefaultValue ? p.DefaultValue : (p.ParameterType.IsValueType ? Activator.CreateInstance(p.ParameterType) : null)).ToArray();
            try { return m.Invoke(null, values); }
            catch (TargetInvocationException e) { throw new Exception("bench " + method + ": " + (e.InnerException != null ? e.InnerException.Message : e.Message), e.InnerException ?? e); }
        }

        static object Bind()
        {
            var args = Environment.GetCommandLineArgs(); int ri = Array.IndexOf(args, "--real");
            var asked = ri >= 0 && ri + 1 < args.Length ? args[ri + 1].Split(',').Where(x => x != "" && x != "none").OrderBy(x => x).ToList() : new List<string>();
            var real = Real().OrderBy(x => x).ToList();
            foreach (var f in real) if (!Present().Contains(f)) throw new Exception($"data/sources.json names {f} as real but {Glb(f)} or its parts.json is not there");
            // the bench's prefab step reads data/sources.json too, and lets --real / --greybox override it for one run: an
            // override that disagrees with the file would build a bench the surfaces and verify do not expect
            if (ri >= 0 && !asked.SequenceEqual(real)) throw new Exception($"--real {string.Join(",", asked)} does not match data/sources.json ({string.Join(",", real)}): change the file, not the command line");
            if (Array.IndexOf(args, "--greybox") >= 0) throw new Exception("--greybox overrides data/sources.json for one run: change the file instead");
            var prefab = BenchStep("Prefab"); var scene = BenchStep("SceneStep");
            var bind = AssemblyKitBuilder.LastReport;
            var report = new JObject { ["real"] = new JArray(real), ["prefab"] = JToken.FromObject(prefab), ["scene"] = JToken.FromObject(scene),
                ["problems"] = new JArray(bind.problems), ["standIns"] = JObject.FromObject(bind.standIns), ["notes"] = new JArray(bind.notes),
                ["placesOnMarks"] = bind.boundPlaces.Count, ["placesOnPoseMarks"] = new JArray(bind.posePlaces), ["placesFromLayout"] = new JArray(bind.fallbackPlaces) };
            // the bench installer builds its stand-in prefab after the real one, so LastReport may describe that: its own record wins
            var benchPrefab = Path.Combine(Repo, "unity/evidence/steady_hands/20261120/bench/prefab.json");
            if (File.Exists(benchPrefab)) { var bp = JObject.Parse(File.ReadAllText(benchPrefab)); report["benchPrefabReport"] = new JObject { ["placesOnMarks"] = bp["placesOnMarks"], ["placesOnPoseMarks"] = bp["placesOnPoseMarks"], ["placesFromLayout"] = bp["placesFromLayout"], ["standIns"] = bp["standIns"], ["problems"] = bp["problems"] }; }
            report["note"] = "standIns / places above come from AssemblyKitBuilder.LastReport, which since 21 Nov may be the stand-in prefab's build; benchPrefabReport is the bench installer's own record of the real prefab";
            WriteEvidence("bind.json", report);
            if (bind.problems.Count > 0) throw new Exception("bind: " + string.Join("; ", bind.problems));
            return new { real, standIns = bind.standIns.ToDictionary(p => p.Key, p => p.Value.Length), placesOnMarks = bind.boundPlaces.Count, posePlaces = bind.posePlaces.Count, fromLayout = bind.fallbackPlaces.Count };
        }

        // ------------------------------------------------------------------ light and cameras (scene)
        static GameObject SceneRoot(Scene scene, string name, out bool made)
        {
            var go = scene.GetRootGameObjects().FirstOrDefault(g => g.name == name); made = !go;
            if (!go) { go = new GameObject(name); SceneManager.MoveGameObjectToScene(go, scene); }
            return go;
        }
        static Transform Child(Transform parent, string name)
        {
            var t = parent.Find(name);
            if (!t) { t = new GameObject(name).transform; t.SetParent(parent, false); }
            return t;
        }
        static T Need<T>(GameObject go) where T : Component { var c = go.GetComponent<T>(); if (!c) c = go.AddComponent<T>(); return c; }

        static Light Lamp(Transform root, JObject cfg, bool shadows)
        {
            var t = Child(root, (string)cfg["name"]);
            var l = Need<Light>(t.gameObject);
            l.type = LightType.Spot; l.color = C(cfg["color"]); l.intensity = F(cfg["intensity"]); l.range = F(cfg["range"]);
            l.spotAngle = F(cfg["spot"]); l.innerSpotAngle = F(cfg["inner"]); l.bounceIntensity = 0; l.lightmapBakeType = LightmapBakeType.Realtime; l.cullingMask = ~0;
            l.shadows = shadows ? ((string)cfg["shadows"] == "hard" ? LightShadows.Hard : LightShadows.Soft) : LightShadows.None;
            if (shadows)
            {
                l.shadowStrength = F(cfg["shadowStrength"], 1); l.shadowBias = F(cfg["bias"], .5f); l.shadowNormalBias = F(cfg["normalBias"], .2f); l.shadowNearPlane = F(cfg["nearPlane"], .1f);
            }
            l.enabled = false;   // BenchLook switches it on at the bench
            var data = Need<UniversalAdditionalLightData>(t.gameObject);
            string soft = (string)cfg["softQuality"] ?? "medium";
            data.usePipelineSettings = !shadows; data.customShadowLayers = false;
            data.softShadowQuality = !shadows ? SoftShadowQuality.UsePipelineSettings : soft == "high" ? SoftShadowQuality.High : soft == "low" ? SoftShadowQuality.Low : SoftShadowQuality.Medium;
            // the interior lamps' layer: the rooms' shells, props and the bench carry bit 7; in this URP the light's layers are on its additional data
            data.renderingLayers = InteriorLayer; l.renderingLayerMask = (int)InteriorLayer;
            var so = new SerializedObject(data); var tier = so.FindProperty("m_AdditionalLightsShadowResolutionTier");
            int want = shadows ? UniversalAdditionalLightData.AdditionalLightsShadowResolutionTierCustom : UniversalAdditionalLightData.AdditionalLightsShadowDefaultResolutionTier;
            if (tier != null && tier.intValue != want) { tier.intValue = want; so.ApplyModifiedPropertiesWithoutUndo(); }
            // URP: with the custom tier the tile size is the light's own shadow resolution as a plain number of pixels (its
            // light editor writes the serialized field; the property's setter only takes the built-in enum)
            var lso = new SerializedObject(l); var tile = lso.FindProperty("m_Shadows.m_Resolution");
            int pixels = shadows ? (int)cfg["shadowResolution"] : -1;
            if (tile != null && tile.intValue != pixels) { tile.intValue = pixels; lso.ApplyModifiedPropertiesWithoutUndo(); }
            EditorUtility.SetDirty(l); EditorUtility.SetDirty(data);
            return l;
        }

        static Bounds WorldBounds(AssemblyPart p)
        {
            bool any = false; var b = new Bounds(p.transform.position, Vector3.zero); var lb = p.localBounds;
            for (int i = 0; i < 8; i++)
            {
                var c = p.transform.TransformPoint(lb.center + Vector3.Scale(lb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1)));
                if (!any) { b = new Bounds(c, Vector3.zero); any = true; } else b.Encapsulate(c);
            }
            return b;
        }

        static object LightStep()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var benchRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == AssemblyBenchInstall20261120.RootName) ?? throw new Exception("no scene root " + AssemblyBenchInstall20261120.RootName + ": run bind first");
            var bench = benchRoot.GetComponent<AssemblyBench>() ?? throw new Exception("the bench root has no AssemblyBench"); bench.Index(true);
            var log = new List<string>(); var real = Real();

            // ---- lamps and the look
            var lightRoot = SceneRoot(scene, LightRoot, out bool madeLight);
            lightRoot.transform.SetPositionAndRotation(benchRoot.transform.position, benchRoot.transform.rotation); lightRoot.transform.localScale = Vector3.one;
            var keyCfg = (JObject)Look["key"]; var cureCfg = (JObject)Look["cure"]; var ses = (JObject)Look["session"]; var surf = (JObject)Look["surface"];
            var key = Lamp(lightRoot.transform, keyCfg, true);
            key.transform.localPosition = V(keyCfg["pos"]);
            var aim = V(keyCfg["aim"]) - V(keyCfg["pos"]);
            key.transform.localRotation = Quaternion.LookRotation(aim.normalized, Mathf.Abs(Vector3.Dot(aim.normalized, Vector3.up)) > .95f ? Vector3.forward : Vector3.up);
            var cure = Lamp(lightRoot.transform, cureCfg, false);
            cure.transform.localPosition = new Vector3(0, 1.2f, 0); cure.transform.localRotation = Quaternion.LookRotation(Vector3.down, Vector3.forward);
            foreach (Transform c in lightRoot.transform.Cast<Transform>().ToList()) if (c != key.transform && c != cure.transform) { log.Add("removed stale " + c.name); UnityEngine.Object.DestroyImmediate(c.gameObject); }

            var lookC = Need<BenchLook>(lightRoot);
            var surfaces = new List<BenchLook.Surface>(); var wipes = new List<BenchLook.WipePart>();
            foreach (var family in real)
            {
                string dir = ArtDir + Cap(family) + "/Materials/";
                if (!Directory.Exists(dir)) throw new Exception("no materials for " + family + ": run the materials step");
                foreach (var path in Directory.GetFiles(dir, "*.mat").Select(p => p.Replace('\\', '/')).OrderBy(p => p, StringComparer.Ordinal))
                {
                    string name = Path.GetFileNameWithoutExtension(path); if (name.EndsWith("__wipe") || name.EndsWith("__lamp")) continue;
                    surfaces.Add(new BenchLook.Surface { source = name, plain = AssetDatabase.LoadAssetAtPath<Material>(path),
                        wipe = AssetDatabase.LoadAssetAtPath<Material>(dir + name + "__wipe.mat"), lamp = AssetDatabase.LoadAssetAtPath<Material>(dir + name + "__lamp.mat") });
                }
                // the parts that start as found: their own zones; where the family gives none ("zone": null: a clip, a screw in
                // the lid, a punch mark) the bench makes a whole-part zone part/<wipe id> that an effect of the job reveals;
                // on a bench without that, the zones of the part's wipe group
                var parts = (JArray)JObject.Parse(File.ReadAllText(PartsFile(family)))["parts"];
                string Group(JToken e) => e["wipes"] is JArray w && w.Count > 0 ? (string)w[0]["id"] ?? "" : null;
                List<string> Zones(JToken e) => (e["zones"] as JArray ?? new JArray()).Select(z => (string)e["id"] + "/" + (string)z["id"]).ToList();
                foreach (var e in parts)
                {
                    string group = Group(e); if (group == null) continue;
                    var own = Zones(e); string whole = (string)e["id"] + "/" + group;
                    if (!own.Contains(whole) && bench.Marker(whole) is AssemblyMarker wm && wm.kind == AssemblyMarkerKind.Zone) own.Add(whole);
                    var zones = own.Count > 0 ? own : parts.Where(o => Group(o) == group).SelectMany(Zones).Distinct().ToList();
                    if (zones.Count > 6) { log.Add($"{(string)e["id"]}: {zones.Count} zones, the surface reads six"); zones = zones.Take(6).ToList(); }
                    wipes.Add(new BenchLook.WipePart { part = (string)e["id"], group = group, zones = zones.ToArray(), ownZones = own.Count > 0 });
                }
            }
            var duplicate = surfaces.GroupBy(s => s.source).Where(g => g.Count() > 1).Select(g => g.Key).ToList();
            if (duplicate.Count > 0) throw new Exception("two families have a material of the same name (surfaces are found by name): " + string.Join(", ", duplicate));
            lookC.surfaces = surfaces.ToArray(); lookC.wipeParts = wipes.ToArray();
            lookC.wipeReach = F(surf["wipeReach"], .012f); lookC.partsCastShadows = ses["partsCastShadows"] == null || (bool)ses["partsCastShadows"];
            lookC.noShadowParts = (ses["noShadowParts"] as JArray ?? new JArray()).Select(x => (string)x).ToArray();
            foreach (var id in lookC.noShadowParts) if (!bench.Part(id)) log.Add("noShadowParts names a part that is not on this bench: " + id);
            lookC.reveals = ((JArray)Look["reveals"]).Select(r => new BenchLook.Reveal { parts = r["parts"].Select(x => (string)x).ToArray(), step = (string)r["step"] ?? "", action = (string)r["action"] ?? "",
                progress = r["progress"] != null && (bool)r["progress"], glow = r["glow"] != null ? C(r["glow"]) : Color.black, settle = F(r["settle"], .5f) }).ToArray();
            lookC.enclosed = ((Look["enclosed"] as JArray) ?? new JArray()).Select(e => new BenchLook.Enclosed { part = (string)e["part"], shells = e["shells"].Select(x => (string)x).ToArray() }).ToArray();
            lookC.enclosedSlack = F(ses["enclosedSlack"], .001f);
            foreach (var e in lookC.enclosed) if (BenchLook.Links(bench, e, lookC.enclosedSlack, out _) == null) log.Add("enclosed names a part that is not on this bench: " + e.part + " / " + string.Join(",", e.shells));
            lookC.key = key; lookC.keyIntensity = F(keyCfg["intensity"]); lookC.cureLamp = cure; lookC.cureLampPart = (string)cureCfg["part"]; lookC.cureIntensity = F(cureCfg["intensity"]);
            lookC.cureLampOffset = V(cureCfg["offset"]); lookC.fadeSeconds = F(ses["fadeSeconds"], .6f); lookC.roomDim = F(ses["roomDim"], .4f); lookC.screenDim = F(ses["screenDim"], .12f); lookC.glowDim = F(ses["glowDim"], .04f);
            lookC.screenMaterial = (string)ses["screenMaterial"]; lookC.screenLampName = (string)ses["screenLamp"];
            EditorUtility.SetDirty(lookC);

            // ---- close review cameras (35 mm at 0.3 m, DESIGN section 4 and CONTRACT's review gate), in the bench's frame
            var camRoot = SceneRoot(scene, CameraRoot, out bool madeCams);
            camRoot.transform.SetPositionAndRotation(benchRoot.transform.position, benchRoot.transform.rotation); camRoot.transform.localScale = Vector3.one;
            var cams = (JObject)Look["cameras"]; var wanted = new HashSet<string>(); var shots = new JObject();
            foreach (JObject shot in (JArray)cams["close"])
            {
                Vector3? target = null; string what = null;
                if (shot["frames"] is JArray frames)
                {
                    bool any = false; var b = new Bounds();
                    foreach (var id in frames.Select(x => (string)x)) { var p = bench.Part(id); if (!p) continue; var wb = WorldBounds(p); if (!any) { b = wb; any = true; } else b.Encapsulate(wb); }
                    if (any) { target = b.center; what = string.Join(", ", frames.Select(x => (string)x)); }
                }
                else if (shot["at"] != null) { var m = bench.Marker((string)shot["at"]); if (m) { target = m.transform.position; what = (string)shot["at"]; } }
                string name = "cam_bench_close_" + (string)shot["id"];
                if (!target.HasValue) { log.Add(name + ": nothing to frame on this bench (" + (shot["frames"] ?? shot["at"]) + ")"); continue; }
                wanted.Add(name);
                float pitch = F(shot["pitch"], F(cams["pitch"], 40)), yaw = F(shot["yaw"]), distance = F(shot["distance"], F(cams["distance"], .3f));
                var t = Child(camRoot.transform, name);
                // yaw 0 stands on the player's side (+z of the bench) and looks toward its back, as the bench's own shots do
                var local = Quaternion.Euler(pitch, 180 + yaw, 0);
                t.localRotation = local; t.position = target.Value - camRoot.transform.rotation * (local * Vector3.forward) * distance;
                var cam = Need<Camera>(t.gameObject); cam.enabled = false; cam.fieldOfView = F(cams["fov"], 37.8f); cam.nearClipPlane = F(cams["near"], .02f); cam.farClipPlane = 60;
                shots[name] = new JObject { ["frames"] = what, ["pitch"] = pitch, ["yaw"] = yaw, ["metres"] = distance, ["benchLocal"] = new JArray(Math.Round(t.localPosition.x, 3), Math.Round(t.localPosition.y, 3), Math.Round(t.localPosition.z, 3)) };
            }
            foreach (Transform c in camRoot.transform.Cast<Transform>().ToList()) if (!wanted.Contains(c.name)) { log.Add("removed stale " + c.name); UnityEngine.Object.DestroyImmediate(c.gameObject); }

            File.WriteAllText(RecordPath, JsonConvert.SerializeObject(new { roots = new[] { LightRoot, CameraRoot }, madeLight, madeCams, installed = DateTime.Now.ToString("yyyy-MM-dd HH:mm"), real,
                note = "rollback removes the two roots; the bench root and the shop are not edited by this pass" }, Formatting.Indented));
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            var result = new JObject { ["lightRoot"] = LightRoot, ["cameraRoot"] = CameraRoot, ["real"] = new JArray(real), ["surfaces"] = surfaces.Count, ["asFoundParts"] = wipes.Count, ["reveals"] = lookC.reveals.Length,
                ["key"] = new JObject { ["benchLocal"] = keyCfg["pos"], ["aim"] = keyCfg["aim"], ["intensity"] = lookC.keyIntensity, ["spot"] = key.spotAngle, ["range"] = key.range, ["shadowTile"] = (int)keyCfg["shadowResolution"] },
                ["cameras"] = shots, ["log"] = new JArray(log) };
            WriteEvidence("light.json", result);
            return new { lights = 2, cameras = wanted.Count, surfaces = surfaces.Count, asFoundParts = wipes.Count, log };
        }

        static object Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath); var removed = new List<string>();
            foreach (var name in new[] { LightRoot, CameraRoot })
            {
                var go = scene.GetRootGameObjects().FirstOrDefault(g => g.name == name);
                if (go) { UnityEngine.Object.DestroyImmediate(go); removed.Add(name); }
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            if (File.Exists(RecordPath)) File.Move(RecordPath, RecordPath.Replace(".json", "-rolledback-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json"));
            var r = new { removed, note = "Materials, the shader and import settings stay. The real parts then show their glTF materials; to go back to stand-ins set data/sources.json to greybox and run bind." };
            WriteEvidence("rollback.json", r);
            return r;
        }

        // ------------------------------------------------------------------ verify
        static Plane[] Frustum(Camera cam, float far)
        {
            var proj = Matrix4x4.Perspective(cam.fieldOfView, 16f / 9f, cam.nearClipPlane, far);
            return GeometryUtility.CalculateFrustumPlanes(proj * cam.worldToCameraMatrix);
        }

        static object Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var problems = new List<string>(); var warnings = new List<string>(); var report = new JObject();
            var real = Real(); report["real"] = new JArray(real);
            var budget = (JObject)Look["budget"];
            var benchRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == AssemblyBenchInstall20261120.RootName);
            var lightRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == LightRoot);
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CameraRoot);
            if (!benchRoot) problems.Add("no scene root " + AssemblyBenchInstall20261120.RootName);
            if (!lightRoot) problems.Add("no scene root " + LightRoot);
            if (!camRoot) problems.Add("no scene root " + CameraRoot);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            if (!shader) problems.Add("missing " + ShaderPath);
            else
            {
                if (ShaderUtil.ShaderHasError(shader)) problems.Add("Bench Surface has errors: " + string.Join(" | ", ShaderUtil.GetShaderMessages(shader).Select(m => m.message + " @" + m.line).Take(4)));
                report["shaderVariants"] = Variants(shader, problems);
            }
            var bench = benchRoot ? benchRoot.GetComponent<AssemblyBench>() : null;
            var lookC = lightRoot ? lightRoot.GetComponent<BenchLook>() : null;
            if (lightRoot && !lookC) problems.Add(LightRoot + " has no BenchLook");
            var surfaces = new Dictionary<string, BenchLook.Surface>(); var mine = new HashSet<Material>();
            if (lookC)
                foreach (var s in lookC.surfaces)
                {
                    surfaces[s.source] = s;
                    if (!s.plain) problems.Add("surface " + s.source + " has no material");
                    foreach (var m in new[] { s.plain, s.wipe, s.lamp })
                    {
                        if (!m) continue; mine.Add(m);
                        if (!m.shader || m.shader.name != ShaderName) problems.Add(m.name + " is not on " + ShaderName);
                        if (m.IsKeywordEnabled("_BENCH_WIPE") && (!m.GetTexture("_BenchDirtyBaseMap") || !m.GetTexture("_BenchDirtyNormalMap") || !m.GetTexture("_BenchDirtyOrmMap"))) problems.Add(m.name + " lacks an as-found texture");
                        if (m.GetFloat("_Surface") < .5f && (!m.GetTexture("_BaseMap") || !m.GetTexture("_BenchOrmMap") || !m.GetTexture("_BumpMap"))) warnings.Add(m.name + " is opaque with no base, normal or ORM map (a constant material)");
                    }
                }

            // ---- what the bench is built from, family by family
            if (bench)
            {
                bench.Index(true);
                var families = new JObject(); var unmapped = new SortedSet<string>(StringComparer.Ordinal);
                var wipeIds = new HashSet<string>(lookC ? lookC.wipeParts.Select(w => w.part) : new string[0]);
                foreach (var family in AssemblyKitBuilder.Families)
                {
                    var parts = bench.Parts.Where(p => p.id.StartsWith(family + ".")).ToList();
                    int realParts = 0, standIns = 0, renderers = 0, surfaced = 0; long tris = 0; var missing = new List<string>();
                    foreach (var p in parts)
                    {
                        bool isReal = false;
                        foreach (var r in p.renderers)
                        {
                            if (!r) continue; renderers++;
                            var mesh = r is SkinnedMeshRenderer sk ? sk.sharedMesh : r.GetComponent<MeshFilter>() ? r.GetComponent<MeshFilter>().sharedMesh : null;
                            if (mesh) for (int s = 0; s < mesh.subMeshCount; s++) tris += mesh.GetIndexCount(s) / 3;
                            if (mesh && AssetDatabase.GetAssetPath(mesh).StartsWith(ArtDir)) isReal = true;
                            foreach (var m in r.sharedMaterials)
                            {
                                if (!m) { problems.Add($"{p.id}: a renderer has no material"); continue; }
                                if (!AssetDatabase.GetAssetPath(m).StartsWith(ArtDir)) continue;
                                if (surfaces.ContainsKey(m.name) || mine.Contains(m)) surfaced++; else unmapped.Add(family + "/" + m.name);
                            }
                        }
                        if (isReal) realParts++; else standIns++;
                    }
                    var listed = File.Exists(PartsFile(family)) ? ((JArray)JObject.Parse(File.ReadAllText(PartsFile(family)))["parts"]).Select(e => (string)e["id"]).ToList() : new List<string>();
                    if (real.Contains(family))
                    {
                        foreach (var id in listed) if (!bench.Part(id)) missing.Add(id);
                        if (missing.Count > 0) problems.Add($"{family}: parts of its parts.json are not on the bench: {string.Join(", ", missing.Take(6))}");
                        if (realParts == 0) problems.Add($"{family} is real in data/sources.json but the bench has none of its model's meshes (was the bench prefab rebuilt without --real?)");
                    }
                    else if (realParts > 0) problems.Add($"{family} is greybox in data/sources.json but the bench holds {realParts} parts of its model");
                    families[family] = new JObject { ["source"] = real.Contains(family) ? "real" : "greybox", ["parts"] = parts.Count, ["fromTheModel"] = realParts, ["standIns"] = standIns, ["listedInPartsJson"] = listed.Count,
                        ["renderers"] = renderers, ["triangles"] = tris, ["materialSlotsWithASurface"] = surfaced, ["asFoundParts"] = parts.Count(p => wipeIds.Contains(p.id)) };
                }
                report["families"] = families;
                var paramRows = new JArray();
                foreach (var prm in benchRoot.GetComponentsInChildren<AssemblyParam>(true))
                {
                    if (!prm.clip) continue;
                    paramRows.Add(new JObject { ["param"] = prm.id, ["clip"] = prm.clip.name, ["legacy"] = prm.clip.legacy, ["root"] = prm.clipRoot ? prm.clipRoot.name : null });
                    if (!prm.clip.legacy) problems.Add($"param {prm.id}: clip {prm.clip.name} is not legacy (SampleAnimation fails in a player)");
                    if (!prm.clipRoot) problems.Add($"param {prm.id}: clip {prm.clip.name} has no clip root");
                }
                report["paramClips"] = paramRows;
                if (unmapped.Count > 0) problems.Add("model materials with no Bench Surface (run the materials and light steps): " + string.Join(", ", unmapped));
                if (lookC)
                {
                    var driven = bench.recipe ? bench.recipe.data.WipesDriven() : null; var notCleaned = new List<string>();
                    foreach (var w in lookC.wipeParts)
                    {
                        if (!bench.Part(w.part)) { problems.Add("as-found part not on the bench: " + w.part); continue; }
                        foreach (var z in w.zones) { var m = bench.Marker(z); if (!m || m.kind != AssemblyMarkerKind.Zone) problems.Add($"{w.part}: wipe zone {z} is not a zone on the bench"); }
                        if (w.zones.Length == 0 && !lookC.reveals.Any(r => r.parts.Contains(w.part))) warnings.Add($"{w.part} starts as found but has no zone and no reveal rule: it stays as found");
                        else if (driven != null && !w.zones.Any(driven.Contains) && !lookC.reveals.Any(r => r.parts.Contains(w.part))) notCleaned.Add(w.part);
                    }
                    report["asFoundPartsTheJobNeverCleans"] = new JArray(notCleaned);
                    var steps = bench.recipe ? bench.recipe.data.Steps.ToDictionary(s => s.id) : new Dictionary<string, AssemblyStepDef>();
                    foreach (var r in lookC.reveals)
                    {
                        if (!steps.TryGetValue(r.step, out var st)) problems.Add("reveal names an unknown step " + r.step);
                        else if (!string.IsNullOrEmpty(r.action) && st.actions.All(a => a.key != r.action)) problems.Add($"reveal names an unknown action {r.step}:{r.action}");
                        foreach (var id in r.parts) if (!bench.Part(id)) warnings.Add("reveal part not on this bench: " + id);
                    }
                    foreach (var id in bench.recipe ? bench.recipe.data.Steps.SelectMany(s => s.actions).Where(a => a.verb == AssemblyVerbKind.Wipe).Select(a => a.target).Distinct() : new string[0])
                    {
                        var owner = bench.Marker(id) ? bench.Part(bench.Marker(id).ownerPart) : null;
                        bool isReal = owner && owner.renderers.Any(r => r && r.sharedMaterials.Any(m => m && AssetDatabase.GetAssetPath(m).StartsWith(ArtDir)));
                        if (isReal && !lookC.wipeParts.Any(w => w.zones.Contains(id))) warnings.Add($"the job wipes {id} but no as-found part reads that zone (its family lists no wipe there)");
                    }
                    if (!string.IsNullOrEmpty(lookC.cureLampPart) && !bench.Part(lookC.cureLampPart)) problems.Add("cure lamp part not on the bench: " + lookC.cureLampPart);
                    report["surfaces"] = lookC.surfaces.Length; report["asFoundParts"] = lookC.wipeParts.Length; report["reveals"] = lookC.reveals.Length;
                }
                var interior = UnityEngine.Object.FindObjectsByType<InteriorLighting>(FindObjectsInactive.Include).FirstOrDefault(i => i.interiorRoots.Contains(benchRoot.transform));
                if (!interior) problems.Add("the bench root is not an interior root of the shop");
                else
                {
                    report["shopLamps"] = new JArray(interior.lamps.Where(l => l).Select(l => $"{l.name}: {l.type} {l.intensity:0.##} range {l.range:0.#} shadows {l.shadows}"));
                    if (lookC && !interior.GetComponentsInChildren<Renderer>(true).Any(r => r.sharedMaterial && r.sharedMaterial.name == lookC.screenMaterial)) warnings.Add("no renderer in the shop uses " + lookC.screenMaterial + " (the screen will not dim)");
                }
            }

            // ---- lamps
            var key = lookC ? lookC.key : null; var cureLamp = lookC ? lookC.cureLamp : null;
            if (lookC && (!key || !cureLamp)) problems.Add("BenchLook lacks its work lamp or cure lamp");
            foreach (var l in new[] { key, cureLamp })
            {
                if (!l) continue;
                var data = l.GetComponent<UniversalAdditionalLightData>();
                if (!data || (uint)data.renderingLayers != InteriorLayer) problems.Add(l.name + " is not on the interior rendering layer (bit 7)");
                if (l.enabled) problems.Add(l.name + " is saved switched on (BenchLook switches it on at the bench; it must be dark from the avenue)");
                if (l == cureLamp && l.shadows != LightShadows.None) problems.Add("the cure lamp casts shadows");
            }
            if (key)
            {
                if (key.shadows == LightShadows.None) problems.Add("the work lamp casts no shadows");
                float half = Mathf.Tan(key.spotAngle * .5f * Mathf.Deg2Rad), tile = new SerializedObject(key).FindProperty("m_Shadows.m_Resolution").intValue;
                report["workLamp"] = new JObject { ["intensity"] = lookC.keyIntensity, ["spot"] = key.spotAngle, ["range"] = key.range, ["shadows"] = key.shadows.ToString(), ["shadowTile"] = tile,
                    ["texelMmAtWorkMat"] = Math.Round(2 * half * .7f / Mathf.Max(1, tile) * 1000, 2), ["biasMm"] = Math.Round(key.shadowBias * half * key.range / Mathf.Max(1, tile) * 2.5f * 1000, 2),
                    ["casterShrinkMm"] = Math.Round(key.shadowNormalBias * half * key.range / Mathf.Max(1, tile) * 2.5f * 1000, 2), ["softQuality"] = key.GetComponent<UniversalAdditionalLightData>() ? key.GetComponent<UniversalAdditionalLightData>().softShadowQuality.ToString() : null,
                    ["neverCasting"] = new JArray(lookC.noShadowParts) };
            }
            var others = new List<Light>(); var managed = new HashSet<Light>();
            var lb = UnityEngine.Object.FindAnyObjectByType<LightBudget>(FindObjectsInactive.Include);
            if (lb) foreach (var lamp in lb.lamps) if (lamp != null && lamp.light) managed.Add(lamp.light);
            foreach (var l in UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude))
                if (l.type != LightType.Directional && !managed.Contains(l) && (l.enabled || l == key || l == cureLamp)) others.Add(l);
            int cap = lb ? lb.hardCap : (int)budget["lights"];

            // ---- every shot: lights, triangles and draws the bench adds
            var wideList = new List<string>();
            var shotRows = new JObject(); int worstLights = 0; long worstTris = 0; int worstDraws = 0;
            var cameras = new List<Camera>();
            if (benchRoot) cameras.AddRange(benchRoot.GetComponentsInChildren<Camera>(true));
            if (camRoot) cameras.AddRange(camRoot.GetComponentsInChildren<Camera>(true));
            var benchRenderers = benchRoot ? benchRoot.GetComponentsInChildren<Renderer>(false).Where(r => r.enabled).ToList() : new List<Renderer>();
            // parts BenchLook does not draw while they are closed in (as found: the saved scene is the bench as found)
            var closedIn = new HashSet<Renderer>(); var enclosedRows = new JArray();
            if (bench && lookC)
                foreach (var e in lookC.enclosed)
                {
                    var links = BenchLook.Links(bench, e, lookC.enclosedSlack, out var part);
                    if (links == null) { problems.Add("enclosed part or shell not on the bench: " + e.part + " / " + string.Join(",", e.shells)); continue; }
                    bool hide = BenchLook.AsFound(links, lookC.enclosedSlack);
                    if (hide) foreach (var r in part.renderers) if (r) closedIn.Add(r);
                    enclosedRows.Add(new JObject { ["part"] = e.part, ["hiddenAsFound"] = hide, ["links"] = links.Count });
                }
            report["enclosed"] = enclosedRows; report["closedInRenderersAsFound"] = closedIn.Count;
            // a mechanism's as-found value switches objects and meshes (the rolled tool roll keeps its tools out of sight until it
            // is unrolled): the saved scene has them all on, the game sets them at start, so count them as the game shows them
            int switchedOff = 0;
            if (benchRoot)
                foreach (var prm in benchRoot.GetComponentsInChildren<AssemblyParam>(true))
                {
                    bool high = prm.asFound >= prm.switchAt;
                    foreach (var g in high ? prm.shownLow : prm.shownHigh) if (g) foreach (var r in g.GetComponentsInChildren<Renderer>(true)) if (closedIn.Add(r)) switchedOff++;
                    foreach (var r in high ? prm.meshLow : prm.meshHigh) if (r && closedIn.Add(r)) switchedOff++;
                }
            report["switchedOffAsFound"] = switchedOff;
            var drawnBench = benchRenderers.Where(r => !closedIn.Contains(r)).ToList();
            foreach (var cam in cameras)
            {
                if (!cam.name.StartsWith("cam_bench_")) problems.Add("camera not named cam_bench_*: " + cam.name);
                if (cam.enabled) problems.Add("review camera enabled: " + cam.name);
                var planes = Frustum(cam, 150);
                int unmanagedInView = others.Count(l => GeometryUtility.TestPlanesAABB(planes, new Bounds(l.transform.position, Vector3.one * (2 * l.range))));
                int managedInView = managed.Count(l => l && GeometryUtility.TestPlanesAABB(planes, new Bounds(l.transform.position, Vector3.one * (2 * l.range))));
                long tris = 0; int draws = 0, seen = 0; var byFamily = new Dictionary<string, int>();
                foreach (var r in drawnBench)
                {
                    if (!GeometryUtility.TestPlanesAABB(planes, r.bounds)) continue; seen++;
                    var owner = r.GetComponentInParent<AssemblyPart>(); string fam = owner && owner.id.Contains('.') ? owner.id.Substring(0, owner.id.IndexOf('.')) : "other";
                    byFamily[fam] = (byFamily.TryGetValue(fam, out var n0) ? n0 : 0) + Mathf.Max(1, r.sharedMaterials.Length);
                    if (cam.name == "cam_bench_wide") wideList.Add($"{(owner ? owner.id : "-")}:{r.name}x{Mathf.Max(1, r.sharedMaterials.Length)}");
                    var mesh = r is SkinnedMeshRenderer sk ? sk.sharedMesh : r.GetComponent<MeshFilter>() ? r.GetComponent<MeshFilter>().sharedMesh : null; if (!mesh) continue;
                    for (int s = 0; s < mesh.subMeshCount; s++) tris += mesh.GetIndexCount(s) / 3;
                    draws += Mathf.Max(1, r.sharedMaterials.Length);
                }
                shotRows[cam.name] = new JObject { ["lightsNotBudgeted"] = unmanagedInView, ["budgetedLampsInRange"] = managedInView, ["slotsLeftForBudgetedLamps"] = cap - unmanagedInView, ["benchRenderers"] = seen, ["benchTriangles"] = tris, ["benchColourDraws"] = draws, ["drawsByFamily"] = JObject.FromObject(byFamily) };
                worstLights = Mathf.Max(worstLights, unmanagedInView); worstTris = Math.Max(worstTris, tris); worstDraws = Mathf.Max(worstDraws, draws);
                if (unmanagedInView > cap) problems.Add($"{cam.name}: {unmanagedInView} lights the budget does not manage are in view, over its cap of {cap}");
            }
            report["shots"] = shotRows; report["wideShotRenderers"] = new JArray(wideList.OrderBy(x => x, StringComparer.Ordinal));
            int casters = key ? drawnBench.Count(r => Vector3.Distance(r.bounds.ClosestPoint(key.transform.position), key.transform.position) < key.range) : 0;
            report["budgets"] = new JObject
            {
                ["lightCap"] = cap, ["mostLightsNotBudgetedInAShot"] = worstLights, ["lightsOk"] = worstLights <= cap,
                ["triangleBudget"] = (long)budget["triangles"], ["mostBenchTrianglesInAShot"] = worstTris, ["trianglesOk"] = worstTris <= (long)budget["triangles"],
                ["drawBudget"] = (int)budget["draws"], ["mostBenchColourDrawsInAShot"] = worstDraws, ["drawsOk"] = worstDraws <= (int)budget["draws"],
                ["shadowCastersInTheWorkLampsRange"] = casters,
                ["note"] = "as found, parts BenchLook keeps undrawn while closed in and what a mechanism's as-found value switches off (tools in the rolled roll) left out, with every other active renderer under the bench root counted when its bounds meet the shot's 16:9 frustum; parts hidden inside others are drawn too (the city has no occlusion culling). Lights: every enabled light the light budget does not manage, plus the work lamp and the cure lamp, by the budget's own range-box test."
            };
            if (worstTris > (long)budget["triangles"]) warnings.Add($"triangle budget: {worstTris} of {(long)budget["triangles"]} in the widest shot");
            if (worstDraws > (int)budget["draws"]) warnings.Add($"draw budget: {worstDraws} colour draws of {(int)budget["draws"]} in the widest shot (one per part; property blocks keep them off the SRP batcher)");

            // ---- the scene as a whole
            foreach (var root in new[] { lightRoot, camRoot })
            {
                if (!root) continue;
                if (root.GetComponentsInChildren<Component>(true).Any(c => c == null)) problems.Add("missing script under " + root.name);
                if (benchRoot && (Vector3.Distance(root.transform.position, benchRoot.transform.position) > .001f || Quaternion.Angle(root.transform.rotation, benchRoot.transform.rotation) > .01f)) problems.Add(root.name + " is not at the bench's transform");
            }
            if (camRoot) report["closeCameras"] = new JArray(camRoot.GetComponentsInChildren<Camera>(true).Select(c => c.name));
            int missingScripts = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<Transform>(true)).SelectMany(t => t.GetComponents<Component>()).Count(c => c == null);
            if (missingScripts > 0) problems.Add(missingScripts + " missing scripts in the scene");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            bool fingerprint = !chunks || chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            if (!fingerprint) problems.Add("render chunk fingerprint stale");
            report["missingScripts"] = missingScripts; report["chunkFingerprintMatches"] = fingerprint;
            report["warnings"] = new JArray(warnings); report["problems"] = new JArray(problems); report["pass"] = problems.Count == 0;
            WriteEvidence("verify.json", report);
            if (problems.Count > 0) throw new Exception("SteadyHandsBenchInstall20261120 verify: " + string.Join("; ", problems));
            return new { ok = true, real, warnings = warnings.Count, mostLights = worstLights, mostTriangles = worstTris, mostDraws = worstDraws };
        }

        // ------------------------------------------------------------------ dryrun (BenchLook without a player)
        /// Runs BenchLook's own code on the saved scene in the Editor, without Play mode and without saving: Start, a frame
        /// away from the bench, a frame lit for work, every wipe zone filled, another frame. It cannot show a picture; it
        /// shows that the driver binds what verify expects and throws nothing. -> dryrun.json
        static object DryRun()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var lightRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == LightRoot) ?? throw new Exception("no scene root " + LightRoot);
            var lookC = lightRoot.GetComponent<BenchLook>() ?? throw new Exception("no BenchLook");
            var problems = new List<string>(); var report = new JObject();
            const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
            void Call(string method) { try { typeof(BenchLook).GetMethod(method, Private).Invoke(lookC, null); } catch (TargetInvocationException e) { throw new Exception("BenchLook." + method + ": " + e.InnerException, e.InnerException); } }
            var messages = new List<string>();
            Application.LogCallback grab = (text, stack, type) => { if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert) messages.Add(type + ": " + text); else if (text.StartsWith("BenchLook")) report["startLine"] = text; };
            Application.logMessageReceived += grab;
            try
            {
                Call("Start");
                var bench = lookC.Bench ?? throw new Exception("BenchLook found no bench");
                report["afterStart"] = new JObject { ["boundRenderers"] = lookC.BoundRenderers, ["asFoundRenderers"] = lookC.WipeRenderers, ["lampRenderers"] = lookC.LampRenderers, ["materialsWithNoSurface"] = lookC.UnknownMaterials, ["closedInHidden"] = lookC.HiddenRenderers };
                lookC.Step(.25f);
                bool keyOffAway = lookC.key && !lookC.key.enabled;
                // lit for work, as ATHEN_BENCH_LOOK=always does
                typeof(BenchLook).GetField("always", Private).SetValue(lookC, true);
                for (int i = 0; i < 3; i++) lookC.Step(.25f);
                var real = bench.GetComponentsInChildren<Renderer>(true).Where(r => r.sharedMaterials.Any(m => m && AssetDatabase.GetAssetPath(m).StartsWith(ArtDir))).ToList();
                var stillGltf = real.Where(r => r.sharedMaterials.Any(m => m && AssetDatabase.GetAssetPath(m).EndsWith(".glb"))).Select(r => r.name).Distinct().ToList();
                if (stillGltf.Count > 0) problems.Add("still on glTF materials after binding: " + string.Join(", ", stillGltf.Take(8)));
                report["realRenderers"] = real.Count;
                report["shaders"] = new JObject(real.SelectMany(r => r.sharedMaterials).Where(m => m).GroupBy(m => m.shader ? m.shader.name : "none").Select(g => new JProperty(g.Key, g.Count())));
                report["materialsInUse"] = new JObject(real.SelectMany(r => r.sharedMaterials).Where(m => m).GroupBy(m => m.name).OrderBy(g => g.Key).Select(g => new JProperty(g.Key, g.Count())));
                report["castingWhileWorking"] = bench.Parts.SelectMany(p => p.renderers).Count(r => r && r.shadowCastingMode != ShadowCastingMode.Off);
                report["weight"] = lookC.Weight; report["keyOffAwayFromTheBench"] = keyOffAway; report["keyOnAtTheBench"] = lookC.key && lookC.key.enabled;
                if (!keyOffAway) problems.Add("the work lamp is on away from the bench");
                if (!(lookC.key && lookC.key.enabled)) problems.Add("the work lamp did not come on for work");
                // every wipe zone: as found, then clean
                var block = new MaterialPropertyBlock(); var rows = new JArray();
                foreach (var w in lookC.wipeParts)
                {
                    var part = bench.Part(w.part); if (!part) continue;
                    var r = part.renderers.FirstOrDefault(x => x && x.sharedMaterials.Any(m => m && m.IsKeywordEnabled("_BENCH_WIPE")));
                    if (!r) { rows.Add(new JObject { ["part"] = w.part, ["note"] = "no as-found renderer (a stand-in, or its material has no as-found variant)" }); continue; }
                    r.GetPropertyBlock(block); var state = block.GetVector("_BenchWipeState");
                    rows.Add(new JObject { ["part"] = w.part, ["group"] = w.group, ["zonesAsked"] = w.zones.Length, ["zonesBound"] = (int)state.x, ["ownZones"] = w.ownZones, ["cleanAsFound"] = Math.Round(state.y, 3), ["masks"] = block.GetTexture("_BenchWipeMasks") ? block.GetTexture("_BenchWipeMasks").name : null });
                    if (w.ownZones && (int)state.x != Mathf.Min(6, w.zones.Length)) problems.Add($"{w.part}: {(int)state.x} of its {w.zones.Length} zones reached the renderer");
                    if (state.y > .001f) problems.Add($"{w.part} is not as found at the start (clean {state.y:0.00})");
                }
                foreach (var w in lookC.wipeParts) foreach (var z in w.zones) { var mask = bench.Wipe(z); if (mask.Coverage < 1) mask.Fill(); }
                lookC.Step(.25f);
                foreach (JObject row in rows)
                {
                    if (row["zonesBound"] == null) continue;
                    var part = bench.Part((string)row["part"]); var r = part.renderers.First(x => x && x.sharedMaterials.Any(m => m && m.IsKeywordEnabled("_BENCH_WIPE")));
                    r.GetPropertyBlock(block); row["cleanOnceEveryZoneIsWiped"] = Math.Round(block.GetVector("_BenchWipeState").y, 3);
                }
                report["asFoundParts"] = rows;
                typeof(BenchLook).GetField("always", Private).SetValue(lookC, false);
                for (int i = 0; i < 200 && lookC.Weight > 0; i++) lookC.Step(.25f);
                if (lookC.key && lookC.key.enabled) problems.Add("the work lamp stayed on after leaving");
                report["castingAfterLeaving"] = bench.Parts.SelectMany(p => p.renderers).Count(r => r && r.shadowCastingMode != ShadowCastingMode.Off);
                if ((int)report["castingAfterLeaving"] > 0) problems.Add(report["castingAfterLeaving"] + " bench renderers still cast shadows after leaving");
            }
            finally { Application.logMessageReceived -= grab; }
            foreach (var m in messages) problems.Add(m);
            report["problems"] = new JArray(problems); report["pass"] = problems.Count == 0;
            report["note"] = "Editor, no Play mode, nothing saved. The frame time of one LateUpdate is not measured here.";
            WriteEvidence("dryrun.json", report);
            // leave nothing of the run in memory for a later step
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            if (problems.Count > 0) throw new Exception("dryrun: " + string.Join("; ", problems));
            return new { ok = true, bound = (int)report["afterStart"]["boundRenderers"], asFound = (int)report["afterStart"]["asFoundRenderers"] };
        }


        // ------------------------------------------------------------------ Part 2: the rebuilt pistol in the hand
        const string OldPistolPath = "Assets/AthenHill/Art/OuterBerms/ScrapPistol.glb";
        const string HandPath = ArtDir + "Pistol/pistol_hand.glb";
        const float HandScale = 0.13674f;   // pistol_hand.glb is pistol.glb divided by this (pistol/README.md)
        const string HandName = "Rebuilt pistol (Steady Hands)", RealGripName = "Real grip (Steady Hands)";
        static string HandRecordPath => Path.Combine(Programme, "integration/hand-record.json");

        /// The player's pistols: the held third-person pistol and the first-person view model's. Their ScrapPistol mesh node.
        static List<(string label, MeshFilter node)> PlayerPistols(out List<string> others)
        {
            var meshes = new HashSet<Mesh>(AssetDatabase.LoadAllAssetsAtPath(OldPistolPath).OfType<Mesh>());
            var all = UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(f => meshes.Contains(f.sharedMesh)).ToList();
            var result = new List<(string, MeshFilter)>();
            var combat = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>(FindObjectsInactive.Include);
            if (combat && combat.heldPistol) { var f = all.FirstOrDefault(m => m.transform.IsChildOf(combat.heldPistol.transform)); if (f) result.Add(("held", f)); }
            var vm = combat && combat.viewModel ? combat.viewModel : UnityEngine.Object.FindObjectsByType<FirstPersonViewModel>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(v => !v.rifle);
            if (vm && vm.pistol) { var f = all.FirstOrDefault(m => m.transform.IsChildOf(vm.pistol)); if (f) result.Add(("first-person", f)); }
            others = all.Where(f => !result.Any(r => r.Item2 == f)).Select(f => PathOf(f.transform)).ToList();
            return result;
        }

        static GameObject CopyNode(GameObject assetRoot, string node, Transform parent, Matrix4x4 local, string name, int layer, ShadowCastingMode shadows)
        {
            var src = assetRoot.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == node) ?? throw new Exception(AssetDatabase.GetAssetPath(assetRoot) + " has no node " + node);
            var mf = src.GetComponent<MeshFilter>(); var mr = src.GetComponent<MeshRenderer>();
            if (!mf || !mr) throw new Exception(node + " has no mesh renderer");
            // found or made: a second install leaves the scene as it is
            var found = parent.Find(name); var go = found ? found.gameObject : new GameObject(name); go.layer = layer; if (!found) go.transform.SetParent(parent, false);
            go.transform.localPosition = local.GetColumn(3); go.transform.localRotation = local.rotation; go.transform.localScale = local.lossyScale;
            Need<MeshFilter>(go).sharedMesh = mf.sharedMesh;
            var r = Need<MeshRenderer>(go); r.sharedMaterials = mr.sharedMaterials; r.shadowCastingMode = shadows; r.receiveShadows = true;
            r.lightProbeUsage = LightProbeUsage.BlendProbes; r.motionVectorGenerationMode = MotionVectorGenerationMode.Object;
            return go;
        }
        static Matrix4x4 AssetPose(GameObject root, string node)
        {
            var t = root.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == node) ?? throw new Exception(AssetDatabase.GetAssetPath(root) + " has no node " + node);
            return root.transform.worldToLocalMatrix * t.localToWorldMatrix;
        }

        static object Hand()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var hand = AssetDatabase.LoadAssetAtPath<GameObject>(HandPath) ?? throw new Exception("missing " + HandPath);
            var grip = AssetDatabase.LoadAssetAtPath<GameObject>(Glb("grip")); var mats = AssetDatabase.LoadAssetAtPath<GameObject>(Glb("materials")); var servo = AssetDatabase.LoadAssetAtPath<GameObject>(Glb("servo"));
            if (!grip || !mats || !servo) throw new Exception("grip, materials and servo GLBs are needed for the real grip");
            var pistols = PlayerPistols(out var others);
            if (pistols.Count == 0) throw new Exception("no player pistol (PlayerCombat.heldPistol / the view model's pistol) with the ScrapPistol mesh");
            var handNodes = AssetDatabase.LoadAllAssetsAtPath(HandPath).OfType<Mesh>().Select(m => m.name).ToList();
            var record = new JArray(); var rows = new JArray();
            // the real grip, in P metres; seat marks of the grip core give the plates', strap's and case screws' poses
            var gripParts = new List<(GameObject asset, string node, Matrix4x4 pose)>();
            foreach (var n in new[] { "grip_core", "grip_screw_a", "grip_screw_b", "grip_seam_l", "grip_seam_r" }) gripParts.Add((grip, n, AssetPose(grip, n)));
            gripParts.Add((mats, "materials_sheet_a_plate", AssetPose(grip, "grip_core__mark_seat_plate_l")));
            gripParts.Add((mats, "materials_sheet_b_plate", AssetPose(grip, "grip_core__mark_seat_plate_r")));
            gripParts.Add((mats, "materials_strap_bent", AssetPose(grip, "grip_core__mark_seat_strap")));
            foreach (var (scr, mark) in new[] { ("a", "lc"), ("b", "ld"), ("c", "rc"), ("d", "rd") })
                gripParts.Add((servo, "servo_screw_case_" + scr, AssetPose(grip, "grip_core__mark_seat_plate_screw_" + mark)));

            foreach (var (label, node) in pistols)
            {
                var t = node.transform; var oldR = node.GetComponent<MeshRenderer>(); int layer = node.gameObject.layer; var shadows = oldR ? oldR.shadowCastingMode : ShadowCastingMode.On;
                // found or made, never stacked: a second run replaces what the first made
                var rebuilt = Child(t, HandName).gameObject; rebuilt.layer = layer;
                rebuilt.transform.localPosition = Vector3.zero; rebuilt.transform.localRotation = Quaternion.identity; rebuilt.transform.localScale = Vector3.one;
                Renderer stock = null;
                // copies are named pistol_hand*, never ScrapPistol*: tests and grip solvers index the player's hierarchy by
                // name (PlayerLocomotionTests failed on a second "ScrapPistol", 21 Nov); copies of an earlier install go
                foreach (Transform c in rebuilt.transform.Cast<Transform>().ToList()) if (c.name.StartsWith("ScrapPistol")) UnityEngine.Object.DestroyImmediate(c.gameObject);
                foreach (var n in new[] { "ScrapPistol", "ScrapPistol_grip_stock", "ScrapPistol_cell", "ScrapPistol_trigger", "ScrapPistol_lamp" })
                {
                    var go = CopyNode(hand, n, rebuilt.transform, AssetPose(hand, n), n.Replace("ScrapPistol", "pistol_hand"), layer, shadows);
                    if (n == "ScrapPistol_grip_stock") stock = go.GetComponent<Renderer>();
                }
                if (oldR && oldR.enabled) { oldR.enabled = false; EditorUtility.SetDirty(oldR); }
                // the Stabilised grip mod: the old wrap's mesh is not drawn, the real grip is drawn in its place
                var mods = t.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "grip_stabilised_pistol");
                string gripNote = "no grip_stabilised_pistol under this pistol";
                if (mods)
                {
                    var oldGrip = mods.GetComponent<Renderer>(); if (oldGrip && oldGrip.enabled) { oldGrip.enabled = false; EditorUtility.SetDirty(oldGrip); }
                    var real = Child(mods, RealGripName).gameObject; real.layer = layer;
                    real.transform.localPosition = Vector3.zero; real.transform.localRotation = Quaternion.identity; real.transform.localScale = Vector3.one / HandScale;   // the mod node is in ScrapPistol units; the families are in metres
                    foreach (Transform c in real.transform.Cast<Transform>().ToList()) if (!c.name.StartsWith("real_grip_")) UnityEngine.Object.DestroyImmediate(c.gameObject);
                    foreach (var (asset, n, pose) in gripParts) CopyNode(asset, n, real.transform, pose, "real_grip_" + n, layer, shadows);
                    Need<HideWhileActive>(real).hide = stock ? new[] { stock } : new Renderer[0];
                    gripNote = $"{gripParts.Count} parts under {PathOf(real.transform)}";
                }
                record.Add(new JObject { ["label"] = label, ["pistolNode"] = PathOf(t), ["oldRendererWasEnabled"] = true, ["made"] = PathOf(rebuilt.transform), ["grip"] = gripNote });
                rows.Add(new JObject { ["label"] = label, ["node"] = PathOf(t), ["layer"] = LayerMask.LayerToName(layer), ["shadows"] = shadows.ToString(), ["grip"] = gripNote });
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(HandRecordPath, new JObject { ["installed"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm"), ["pistols"] = record, ["notTouched"] = new JArray(others),
                ["note"] = "hand-rollback removes the made objects and draws the ScrapPistol mesh and the old grip_stabilised_pistol mesh again; ScrapPistol.glb and its GUID were never edited" }.ToString(Formatting.Indented));
            var result = new JObject { ["pistols"] = rows, ["otherScrapPistolInstancesNotTouched"] = new JArray(others) };
            WriteEvidence("hand.json", result);
            return new { pistols = pistols.Count, others = others.Count };
        }

        static object HandRollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath); var done = new List<string>();
            foreach (var (label, node) in PlayerPistols(out _))
            {
                var t = node.transform; var made = t.Find(HandName); if (made) UnityEngine.Object.DestroyImmediate(made.gameObject);
                var oldR = node.GetComponent<MeshRenderer>(); if (oldR && !oldR.enabled) { oldR.enabled = true; EditorUtility.SetDirty(oldR); }
                var mods = t.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "grip_stabilised_pistol");
                if (mods)
                {
                    var real = mods.Find(RealGripName); if (real) UnityEngine.Object.DestroyImmediate(real.gameObject);
                    var oldGrip = mods.GetComponent<Renderer>(); if (oldGrip && !oldGrip.enabled) { oldGrip.enabled = true; EditorUtility.SetDirty(oldGrip); }
                }
                done.Add(label);
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            if (File.Exists(HandRecordPath)) File.Move(HandRecordPath, HandRecordPath.Replace(".json", "-rolledback-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".json"));
            WriteEvidence("hand-rollback.json", new { rolledBack = done });
            return new { rolledBack = done };
        }

        static object HandVerify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath); var problems = new List<string>(); var rows = new JArray();
            var oldGuid = AssetDatabase.AssetPathToGUID(OldPistolPath);
            if (oldGuid != "71b44ddb08bf255219058f51badd9bfa") problems.Add("ScrapPistol.glb GUID changed: " + oldGuid);
            var pistols = PlayerPistols(out var others);
            if (pistols.Count != 2) problems.Add($"expected the held and the first-person pistol, found {pistols.Count}");
            foreach (var (label, node) in pistols)
            {
                var t = node.transform; var made = t.Find(HandName); var row = new JObject { ["label"] = label, ["node"] = PathOf(t) };
                if (!made) { problems.Add(label + ": no " + HandName); rows.Add(row); continue; }
                var rs = made.GetComponentsInChildren<MeshRenderer>(true);
                row["rebuiltRenderers"] = rs.Length; row["rebuiltTriangles"] = rs.Sum(r => { var m = r.GetComponent<MeshFilter>().sharedMesh; long n = 0; for (int i = 0; i < m.subMeshCount; i++) n += m.GetIndexCount(i) / 3; return n; });
                if (rs.Length != 5 || rs.Any(r => !r.GetComponent<MeshFilter>().sharedMesh || r.sharedMaterials.Any(m => !m))) problems.Add(label + ": rebuilt pistol lacks a mesh or a material");
                if (rs.Any(r => r.gameObject.layer != node.gameObject.layer)) problems.Add(label + ": rebuilt pistol not on the pistol's layer");
                if (Vector3.Distance(made.localPosition, Vector3.zero) > 1e-6f || Quaternion.Angle(made.localRotation, Quaternion.identity) > .001f || (made.localScale - Vector3.one).sqrMagnitude > 1e-10f) problems.Add(label + ": rebuilt pistol not at identity under the ScrapPistol node");
                if (node.GetComponent<MeshRenderer>().enabled) problems.Add(label + ": the old ScrapPistol mesh is still drawn");
                var mods = t.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "grip_stabilised_pistol");
                var real = mods ? mods.Find(RealGripName) : null;
                if (!real) problems.Add(label + ": no real grip under grip_stabilised_pistol");
                else
                {
                    var gr = real.GetComponentsInChildren<MeshRenderer>(true); row["realGripParts"] = gr.Length;
                    var hide = real.GetComponent<HideWhileActive>();
                    if (!hide || hide.hide.Length != 1 || !hide.hide[0] || hide.hide[0].name != "pistol_hand_grip_stock" || !hide.hide[0].transform.IsChildOf(made)) problems.Add(label + ": the real grip does not hide this pistol's stock grip");
                    if (mods.GetComponent<Renderer>() && mods.GetComponent<Renderer>().enabled) problems.Add(label + ": the old Stabilised wrap is still drawn");
                    if (gr.Any(r => r.gameObject.layer != node.gameObject.layer)) problems.Add(label + ": real grip not on the pistol's layer");
                    // the grip sits on the pistol: the core's box overlaps the rebuilt frame's grip area
                    var core = gr.FirstOrDefault(r => r.name == "real_grip_grip_core"); var stock = made.Find("pistol_hand_grip_stock")?.GetComponent<Renderer>();
                    if (core && stock) { float d = Vector3.Distance(core.bounds.center, stock.bounds.center); row["coreToStockGripCentreMm"] = Math.Round(d / t.lossyScale.x * HandScale * 1000, 1); }
                }
                var wmv = t.GetComponentInParent<WeaponModVisuals>(true);
                if (!wmv || wmv.mods == null || !mods || !mods.IsChildOf(wmv.mods)) problems.Add(label + ": WeaponModVisuals does not switch grip_stabilised_pistol on this pistol");
                rows.Add(row);
            }
            foreach (var (label, node) in pistols)
            {
                var top = node.transform; while (top.parent) top = top.parent;
                var dup = top.GetComponentsInChildren<Transform>(true).GroupBy(x => x.name).Where(g => g.Count() > 1).Select(g => g.Key).ToList();
                var mine = dup.Where(n => n.StartsWith("pistol_hand") || n.StartsWith("real_grip_") || n == HandName || n == RealGripName || n.StartsWith("ScrapPistol")).ToList();
                if (mine.Count > 0) problems.Add($"{label}: names repeated under {top.name}: {string.Join(", ", mine)}");
            }
            var report = new JObject { ["pistols"] = rows, ["otherScrapPistolInstancesNotTouched"] = new JArray(others), ["problems"] = new JArray(problems), ["pass"] = problems.Count == 0 };
            WriteEvidence("hand-verify.json", report);
            if (problems.Count > 0) throw new Exception("handverify: " + string.Join("; ", problems));
            return new { ok = true, pistols = rows.Count };
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            string steps = i >= 0 && i + 1 < args.Length ? args[i + 1] : "verify";
            try
            {
                foreach (var name in steps.Split(',').SelectMany(s => s == "install" ? new[] { "import", "materials", "bind", "light" } : new[] { s }))
                {
                    object result = name switch
                    {
                        "import" => Import(),
                        "materials" => Materials(),
                        "bind" => Bind(),
                        "light" => LightStep(),
                        "verify" => Verify(),
                        "dryrun" => DryRun(),
                        "benchverify" => BenchStep("Verify"),
                        "benchselftest" => BenchStep("SelfTest"),
                        "benchbindcheck" => BenchStep("BindCheck"),
                        "rollback" => Rollback(),
                        "hand" => Hand(),
                        "hand-rollback" => HandRollback(),
                        "handverify" => HandVerify(),
                        _ => throw new Exception("unknown step " + name),
                    };
                    Debug.Log("SteadyHandsBenchInstall20261120 " + name + ": " + JsonConvert.SerializeObject(result));
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        [MenuItem("Athen Hill/Steady Hands bench (20 Nov 2026)/Real art: verify")] public static void MenuVerify() => Debug.Log(JsonConvert.SerializeObject(Verify()));
    }
}
