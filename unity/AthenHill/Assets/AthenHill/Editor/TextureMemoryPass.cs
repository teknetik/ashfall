using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: texture memory pass. A native run took ~9.5 GB of the shared 12 GB RTX 3060 because ~4.4 GB of
    /// scene textures were uncompressed and never streamed (the city paving pass's probe). This pass inventories every
    /// texture the saved scene loads (active or not: a player deserialises inactive objects too), then compresses the
    /// uncompressed ones without downsampling their sources and without touching materials, prefabs or GUIDs.
    ///
    /// Sources/notes: art/texture_memory_20261001 (README, PROGRESS.md). Evidence: unity/evidence/texture-memory/20261001.
    /// Batch: -executeMethod AthenHill.Editor.TextureMemoryPass.RunBatch --steps inventory[:tag] -nographics
    /// </summary>
    public static class TextureMemoryPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        public const string Evidence = "../evidence/texture-memory/20261001/";

        // ------------------------------------------------------------------ memory model
        /// GPU bytes of a texture as stored for the current build target: every mip, face and slice.
        public static long Bytes(Texture t)
        {
            var gf = t.graphicsFormat;
            if (gf == GraphicsFormat.None) return 0;
            int mips = Mathf.Max(1, t.mipmapCount);
            long sum = 0;
            for (int m = 0; m < mips; m++)
            {
                int w = Mathf.Max(1, t.width >> m), h = Mathf.Max(1, t.height >> m);
                sum += GraphicsFormatUtility.ComputeMipmapSize(w, h, gf);
            }
            int layers = t is Cubemap ? 6 : t is Texture2DArray a ? a.depth : t is CubemapArray ca ? ca.cubemapCount * 6 : t is Texture3D t3 ? t3.depth : 1;
            return sum * layers;
        }

        static double MB(long b) => Math.Round(b / 1048576.0, 2);

        // ------------------------------------------------------------------ inventory
        public class Row
        {
            public string name, path, importer, kind, format, graphicsFormat, role;
            public bool subAsset, compressed, streaming, readable, srgb, activeUse;
            public int w, h, mips, srcW, srcH;
            public double mb;
            public Dictionary<string, object> settings;
            public List<string> uses = new List<string>();
        }

        static string RoleOf(string prop)
        {
            var p = prop.ToLowerInvariant();
            if (p.Contains("bump") || p.Contains("normal")) return "normal";
            if (p.Contains("emission") || p.Contains("emissive")) return "emission";
            if (p.Contains("metallic") || p.Contains("rough") || p.Contains("mask") || p.Contains("orm") || p.Contains("occlusion") || p.Contains("spec") || p.Contains("smooth")) return "mask";
            if (p.Contains("base") || p.Contains("albedo") || p.Contains("maintex") || p.Contains("color") || p.Contains("diffuse")) return "colour";
            return "other";
        }

        /// Every texture the saved scene pulls into a player (dependencies of all root objects, active or not, plus the
        /// skybox and lightmaps), with format, size, mips, streaming flag, memory and where it comes from.
        public static List<Row> Collect(out Dictionary<string, object> totals)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var roots = new List<UnityEngine.Object>(scene.GetRootGameObjects());
            if (RenderSettings.skybox) roots.Add(RenderSettings.skybox);
            if (Lightmapping.lightingDataAsset) roots.Add(Lightmapping.lightingDataAsset);
            foreach (var ld in LightmapSettings.lightmaps ?? new LightmapData[0])
                foreach (var t in new Texture[] { ld.lightmapColor, ld.lightmapDir, ld.shadowMask })
                    if (t) roots.Add(t);
            var all = EditorUtility.CollectDependencies(roots.ToArray());

            // "Active" = referenced from a component on an active object (disabled renderers/behaviours excluded; chunk
            // sources share their materials with the active chunk renderers). Approximate, for prioritising only.
            var activeComps = new List<UnityEngine.Object>();
            foreach (var go in scene.GetRootGameObjects())
                foreach (var c in go.GetComponentsInChildren<Component>(false))
                {
                    if (!c || !c.gameObject.activeInHierarchy) continue;
                    if (c is Renderer r && !r.enabled) continue;
                    if (c is Behaviour b && !b.enabled) continue;
                    if (c is Transform) continue;
                    activeComps.Add(c);
                }
            if (RenderSettings.skybox) activeComps.Add(RenderSettings.skybox);
            var activeSet = new HashSet<UnityEngine.Object>(EditorUtility.CollectDependencies(activeComps.ToArray()).Where(o => o is Texture));

            var users = new Dictionary<Texture, List<string>>();
            foreach (var m in all.OfType<Material>())
            {
                if (!m.shader) continue;
                foreach (var prop in m.GetTexturePropertyNames())
                {
                    var t = m.GetTexture(prop);
                    if (!t) continue;
                    if (!users.TryGetValue(t, out var l)) users[t] = l = new List<string>();
                    l.Add(prop + "@" + m.name);
                }
            }

            var rows = new List<Row>();
            foreach (var t in all.OfType<Texture>().Distinct())
            {
                if (t is RenderTexture || t is CustomRenderTexture) continue;
                var path = AssetDatabase.GetAssetPath(t);
                var imp = string.IsNullOrEmpty(path) ? null : AssetImporter.GetAtPath(path);
                var row = new Row
                {
                    name = t.name, path = path, kind = t.GetType().Name, format = t is Texture2D t2 ? t2.format.ToString() : t.graphicsFormat.ToString(),
                    graphicsFormat = t.graphicsFormat.ToString(), w = t.width, h = t.height, mips = t.mipmapCount,
                    subAsset = !string.IsNullOrEmpty(path) && AssetDatabase.IsSubAsset(t),
                    importer = imp ? imp.GetType().Name : (string.IsNullOrEmpty(path) ? "none" : path.StartsWith("Resources/unity_builtin") || path.StartsWith("Library/") ? "builtin" : "asset"),
                    compressed = GraphicsFormatUtility.IsCompressedFormat(t.graphicsFormat),
                    streaming = t is Texture2D s && s.streamingMipmaps, readable = t.isReadable,
                    srgb = GraphicsFormatUtility.IsSRGBFormat(t.graphicsFormat), mb = MB(Bytes(t)),
                    activeUse = activeSet.Contains(t),
                };
                if (users.TryGetValue(t, out var u)) { row.uses = u.Distinct().ToList(); row.role = u.Select(x => RoleOf(x.Split('@')[0])).GroupBy(x => x).OrderByDescending(g => g.Count()).First().Key; }
                if (imp is TextureImporter ti)
                {
                    ti.GetSourceTextureWidthAndHeight(out row.srcW, out row.srcH);
                    row.settings = Settings(ti);
                }
                rows.Add(row);
            }
            rows = rows.OrderByDescending(r => r.mb).ToList();
            totals = new Dictionary<string, object>
            {
                ["scene"] = ScenePath, ["time"] = DateTime.Now.ToString("s"), ["buildTarget"] = EditorUserBuildSettings.activeBuildTarget.ToString(),
                ["textures"] = rows.Count, ["totalMB"] = Math.Round(rows.Sum(r => r.mb), 1),
                ["nonStreamedMB"] = Math.Round(rows.Where(r => !r.streaming).Sum(r => r.mb), 1),
                ["streamedMB"] = Math.Round(rows.Where(r => r.streaming).Sum(r => r.mb), 1),
                ["uncompressedCount"] = rows.Count(r => !r.compressed), ["uncompressedMB"] = Math.Round(rows.Where(r => !r.compressed).Sum(r => r.mb), 1),
                ["inactiveOnlyMB"] = Math.Round(rows.Where(r => !r.activeUse).Sum(r => r.mb), 1),
                ["byImporter"] = rows.GroupBy(r => r.importer).ToDictionary(g => g.Key, g => new { count = g.Count(), mb = Math.Round(g.Sum(r => r.mb), 1), uncompressedMB = Math.Round(g.Where(r => !r.compressed).Sum(r => r.mb), 1), nonStreamedMB = Math.Round(g.Where(r => !r.streaming).Sum(r => r.mb), 1) }),
                ["byFormat"] = rows.GroupBy(r => r.format).ToDictionary(g => g.Key, g => new { count = g.Count(), mb = Math.Round(g.Sum(r => r.mb), 1) }),
            };
            return rows;
        }

        public static Dictionary<string, object> Settings(TextureImporter ti)
        {
            var s = ti.GetPlatformTextureSettings("Standalone");
            var d = ti.GetDefaultPlatformTextureSettings();
            return new Dictionary<string, object>
            {
                ["textureType"] = ti.textureType.ToString(), ["sRGB"] = ti.sRGBTexture, ["mipmaps"] = ti.mipmapEnabled, ["streaming"] = ti.streamingMipmaps,
                ["streamingPriority"] = ti.streamingMipmapsPriority, ["readable"] = ti.isReadable, ["alphaSource"] = ti.alphaSource.ToString(),
                ["npot"] = ti.npotScale.ToString(), ["maxSize"] = ti.maxTextureSize, ["compression"] = ti.textureCompression.ToString(),
                ["crunched"] = ti.crunchedCompression, ["quality"] = ti.compressionQuality,
                ["default"] = new { d.maxTextureSize, format = d.format.ToString(), compression = d.textureCompression.ToString(), d.compressionQuality },
                ["standalone"] = new { s.overridden, s.maxTextureSize, format = s.format.ToString(), compression = s.textureCompression.ToString(), s.compressionQuality },
            };
        }

        public static string Inventory(string tag)
        {
            var rows = Collect(out var totals);
            Directory.CreateDirectory(Evidence);
            var json = Evidence + "inventory-" + tag + ".json";
            File.WriteAllText(json, JsonConvert.SerializeObject(new { totals, rows }, Formatting.Indented));
            var md = new System.Text.StringBuilder();
            md.AppendLine($"# Texture inventory — {tag} ({totals["time"]})\n");
            md.AppendLine($"Scene `{ScenePath}`, target {totals["buildTarget"]}. {totals["textures"]} textures, {totals["totalMB"]} MB; " +
                          $"not streamed {totals["nonStreamedMB"]} MB; uncompressed {totals["uncompressedCount"]} textures / {totals["uncompressedMB"]} MB; " +
                          $"referenced only by inactive objects {totals["inactiveOnlyMB"]} MB. Memory = all mips as stored for the target (GPU copy).\n");
            md.AppendLine("| MB | Texture | Source | Importer | Format | Size | Mips | Streamed | Role | Active |");
            md.AppendLine("| ---: | --- | --- | --- | --- | --- | ---: | --- | --- | --- |");
            foreach (var r in rows.Take(80))
                md.AppendLine($"| {r.mb} | {r.name} | `{r.path}` | {r.importer} | {r.format} | {r.w}×{r.h} | {r.mips} | {(r.streaming ? "yes" : "no")} | {r.role} | {(r.activeUse ? "yes" : "no")} |");
            md.AppendLine("\nUncompressed by source file (top 40):\n");
            md.AppendLine("| MB | Count | Source |");
            md.AppendLine("| ---: | ---: | --- |");
            foreach (var grp in rows.Where(x => !x.compressed).GroupBy(x => x.path).OrderByDescending(gg => gg.Sum(x => x.mb)).Take(40))
                md.AppendLine($"| {Math.Round(grp.Sum(x => x.mb), 1)} | {grp.Count()} | `{grp.Key}` |");
            File.WriteAllText(Evidence + "inventory-" + tag + ".md", md.ToString());
            return $"{json}: {totals["textures"]} textures, {totals["totalMB"]} MB, non-streamed {totals["nonStreamedMB"]} MB, uncompressed {totals["uncompressedMB"]} MB";
        }

        class InventoryFile { public Dictionary<string, object> totals; public List<Row> rows; }
        static List<Row> LoadInventory(string tag) =>
            JsonConvert.DeserializeObject<InventoryFile>(File.ReadAllText(Evidence + "inventory-" + tag + ".json")).rows;

        static void WriteJson(string file, object o)
        {
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + file, JsonConvert.SerializeObject(o, Formatting.Indented));
        }

        // ------------------------------------------------------------------ TextureImporter textures
        static readonly string[] SkipPrefixes = { "Assets/AthenHill/UI/", "Packages/" };
        const string RollbackMeta = Evidence + "rollback/meta/";
        static readonly HashSet<string> RawFormats = new HashSet<string>
        {
            "RGBA32", "ARGB32", "RGB24", "RGBA64", "RGB48", "R8", "R16", "Alpha8", "RGBAHalf", "RGBAFloat", "RHalf", "RFloat",
            "RG16", "RG32", "RGHalf", "RGFloat", "RGB16", "RGBA16", "ARGB16",
        };

        public class PlanItem
        {
            public string path, name, role, type, oldFormat, newFormat, decision;
            public int w, h;
            public double oldMB, newMB;
            public bool activeUse;
        }

        /// Uncompressed TextureImporter textures in the scene inventory and what to do with each (filter: '+'-separated
        /// path substrings, empty = all).
        public static List<PlanItem> ImporterPlan(string filter)
        {
            var plan = new List<PlanItem>();
            foreach (var r in LoadInventory("before").Where(x => x.importer == "TextureImporter" && !x.compressed))
            {
                if (!string.IsNullOrEmpty(filter) && !filter.Split('+').Any(f => r.path.Contains(f))) continue;
                var ti = AssetImporter.GetAtPath(r.path) as TextureImporter;
                if (!ti) continue;
                var it = new PlanItem { path = r.path, name = r.name, role = r.role, type = ti.textureType.ToString(), oldFormat = r.format, w = r.w, h = r.h, oldMB = r.mb, activeUse = r.activeUse };
                var sa = ti.GetPlatformTextureSettings("Standalone");
                if (SkipPrefixes.Any(p => r.path.StartsWith(p))) it.decision = "skip: UI/package art (uncompressed by design)";
                else if (sa.overridden && (sa.textureCompression == TextureImporterCompression.Uncompressed || RawFormats.Contains(sa.format.ToString())))
                    it.decision = "skip: author's explicit uncompressed Standalone override";
                else if (!sa.overridden && ti.textureCompression == TextureImporterCompression.Uncompressed)
                    it.decision = "skip: author chose Uncompressed";
                else if (ti.textureType != TextureImporterType.Default && ti.textureType != TextureImporterType.NormalMap)
                    it.decision = "skip: texture type " + ti.textureType;
                else if (r.w != r.srcW || r.h != r.srcH)
                    it.decision = "skip: imported size differs from the source";
                else if (!ti.mipmapEnabled)
                    it.decision = "skip: no mipmaps (not a world-material texture)";
                else if (ti.convertToNormalmap && (!Mathf.IsPowerOfTwo(r.w) || !Mathf.IsPowerOfTwo(r.h)))
                    it.decision = "skip: normal map generated from a height source (scaling it to POT would flatten the bumps)";
                else
                {
                    // This Unity (6000.6) leaves non-power-of-two textures with mipmaps uncompressed even with an explicit
                    // BC7 override (tested on sign_emission 2048x660: still RGBA32), so NPOT sources are scaled up to the
                    // next power of two at import (ToLarger: never downsampled; the source file is untouched).
                    bool npot = !Mathf.IsPowerOfTwo(r.w) || !Mathf.IsPowerOfTwo(r.h);
                    it.decision = npot ? "compress (NPOT, import scaled up to the next power of two)" : "compress";
                    it.newFormat = ti.textureType == TextureImporterType.NormalMap ? "BC5" : "BC7";
                    int pw = npot ? NextPow2(r.w) : r.w, ph = npot ? NextPow2(r.h) : r.h;
                    it.newMB = Math.Round(pw * (double)ph * 4.0 / 3.0 / 1048576.0, 2);
                }
                plan.Add(it);
            }
            return plan;
        }

        static int NextPow2(int v) { int p = 32; while (p < v) p <<= 1; return p; }

        /// Standalone override BC7 (colour, packed masks) / BC5 (normal maps), full size (max size >= source), mipmaps
        /// streamed; sRGB/linear and texture type untouched. The original .meta goes to rollback/meta first.
        public static string ApplyImporters(string filter)
        {
            var plan = ImporterPlan(filter);
            WriteJson("importer-plan" + (string.IsNullOrEmpty(filter) ? "" : "-partial") + ".json", plan);
            var recordFile = Evidence + "importers-applied.json";
            var record = File.Exists(recordFile) ? JsonConvert.DeserializeObject<Dictionary<string, object>>(File.ReadAllText(recordFile)) : new Dictionary<string, object>();
            int n = 0;
            foreach (var it in plan.Where(p => p.decision.StartsWith("compress")))
            {
                var ti = (TextureImporter)AssetImporter.GetAtPath(it.path);
                var backup = RollbackMeta + it.path + ".meta";
                Directory.CreateDirectory(Path.GetDirectoryName(backup));
                if (!File.Exists(backup)) File.Copy(it.path + ".meta", backup);
                var before = Settings(ti);
                var ps = ti.GetPlatformTextureSettings("Standalone");
                var d = ti.GetDefaultPlatformTextureSettings();
                ps.overridden = true;
                ps.maxTextureSize = Math.Min(16384, Math.Max(d.maxTextureSize, NextPow2(Math.Max(it.w, it.h))));
                ps.format = it.newFormat == "BC5" ? TextureImporterFormat.BC5 : TextureImporterFormat.BC7;
                ps.textureCompression = TextureImporterCompression.CompressedHQ;
                ps.compressionQuality = 50;
                ti.SetPlatformTextureSettings(ps);
                if (it.decision.Contains("NPOT")) ti.npotScale = TextureImporterNPOTScale.ToLarger;
                if (ti.mipmapEnabled) ti.streamingMipmaps = true;
                var t0 = DateTime.Now;
                ti.SaveAndReimport();
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(it.path);
                record[it.path] = new
                {
                    time = DateTime.Now.ToString("s"), seconds = Math.Round((DateTime.Now - t0).TotalSeconds, 1), before, after = Settings(ti),
                    result = new { format = tex.format.ToString(), graphicsFormat = tex.graphicsFormat.ToString(), tex.width, tex.height, mips = tex.mipmapCount, streaming = tex.streamingMipmaps, mb = MB(Bytes(tex)), oldMB = it.oldMB },
                    rollbackMeta = backup,
                };
                n++;
            }
            File.WriteAllText(recordFile, JsonConvert.SerializeObject(record, Formatting.Indented));
            return $"{n} importers changed of {plan.Count} uncompressed (" + string.Join("; ", plan.GroupBy(p => p.decision).Select(g => g.Key + " " + g.Count())) + ")";
        }

        /// Restores the original .meta files saved by ApplyImporters (filter as above) and reimports.
        public static string RevertImporters(string filter)
        {
            if (!Directory.Exists(RollbackMeta)) return "nothing to revert";
            int n = 0;
            var paths = new List<string>();
            foreach (var backup in Directory.GetFiles(RollbackMeta, "*.meta", SearchOption.AllDirectories))
            {
                var path = backup.Substring(RollbackMeta.Length).Replace('\\', '/');
                path = path.Substring(0, path.Length - ".meta".Length);
                if (!string.IsNullOrEmpty(filter) && !filter.Split('+').Any(f => path.Contains(f))) continue;
                File.Copy(backup, path + ".meta", true);
                paths.Add(path);
                n++;
            }
            AssetDatabase.Refresh();
            foreach (var p in paths) AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);
            var recordFile = Evidence + "importers-applied.json";
            if (File.Exists(recordFile))
            {
                var record = JsonConvert.DeserializeObject<Dictionary<string, object>>(File.ReadAllText(recordFile));
                foreach (var p in paths)
                    if (record.ContainsKey(p)) { record["reverted: " + p] = record[p]; record.Remove(p); }
                File.WriteAllText(recordFile, JsonConvert.SerializeObject(record, Formatting.Indented));
            }
            return n + " .meta files restored: " + string.Join(", ", paths);
        }

        // ------------------------------------------------------------------ glTF embedded textures
        static object MeshMetrics(string path) => AssetDatabase.LoadAllAssetsAtPath(path).OfType<Mesh>().Take(8)
            .Select(m => new { m.name, uv0 = Math.Round(m.GetUVDistributionMetric(0), 3), size = m.bounds.size.ToString("F2") }).ToArray();

        /// Force-reimports .glb files (filter '+'-separated substrings or "all" = every .glb with embedded textures in the
        /// inventory) with the GltfTextureCompression add-on enabled, and records before/after per texture.
        public static string ReimportGltf(string which, string tag, bool requireAddon = true)
        {
            if (requireAddon && !GltfTextureCompression.Enabled) throw new Exception("GltfTextureCompression is disabled (set ATHEN_GLTF_COMPRESS=1)");
            if (!requireAddon && GltfTextureCompression.Enabled) throw new Exception("plain reimport requested but the add-on is enabled (set ATHEN_GLTF_COMPRESS=0)");
            var rows = LoadInventory("before");
            var glbs = rows.Where(r => r.importer == "GltfImporter").GroupBy(r => r.path).OrderByDescending(g => g.Sum(r => r.mb)).Select(g => g.Key).ToList();
            if (which != "all") glbs = glbs.Where(p => which.Split('+').Any(f => p.Contains(f))).ToList();
            var results = new List<object>();
            double before = 0, after = 0, secs = 0;
            foreach (var p in glbs)
            {
                var old = rows.Where(r => r.path == p).ToList();
                var metricsBefore = MeshMetrics(p);
                EditorUtility.UnloadUnusedAssetsImmediate();
                GltfTextureCompression.Report.Clear();
                var t0 = DateTime.Now;
                AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
                var s = (DateTime.Now - t0).TotalSeconds;
                var texs = AssetDatabase.LoadAllAssetsAtPath(p).OfType<Texture2D>().ToList();
                double mbOld = old.Sum(r => r.mb), mbNew = texs.Sum(t => MB(Bytes(t)));
                before += mbOld; after += mbNew; secs += s;
                results.Add(new
                {
                    path = p, seconds = Math.Round(s, 1), mbBefore = Math.Round(mbOld, 1), mbAfter = Math.Round(mbNew, 1),
                    countBefore = old.Count, countAfter = texs.Count,
                    formats = texs.GroupBy(t => t.graphicsFormat.ToString()).ToDictionary(g => g.Key, g => g.Count()),
                    streamed = texs.Count(t => t.streamingMipmaps), readable = texs.Count(t => t.isReadable),
                    addon = GltfTextureCompression.Report.ToList(),
                    textures = texs.Select(t => new { t.name, t.width, t.height, mips = t.mipmapCount, format = t.graphicsFormat.ToString(), streaming = t.streamingMipmaps, readable = t.isReadable, mb = MB(Bytes(t)) }).ToArray(),
                    metricsBefore, metricsAfter = MeshMetrics(p),
                });
                Debug.Log($"TextureMemoryPass gltf {p}: {mbOld:F1} -> {mbNew:F1} MB in {s:F0} s");
                EditorUtility.UnloadUnusedAssetsImmediate();
            }
            WriteJson("gltf-reimport-" + tag + ".json", new { time = DateTime.Now.ToString("s"), seconds = Math.Round(secs, 1), mbBefore = Math.Round(before, 1), mbAfter = Math.Round(after, 1), results });
            return $"{glbs.Count} glb reimported in {secs:F0} s: {before:F0} -> {after:F0} MB";
        }

        /// Saved-scene check after a .glb reimport: every renderer that comes from the .glb (prefab source or mesh asset)
        /// still has its mesh and all material slots, and the .glb's sub-assets are all there.
        public static string VerifyGlb(string which)
        {
            var rows = LoadInventory("before");
            var glbs = rows.Where(r => r.importer == "GltfImporter").Select(r => r.path).Distinct().ToList();
            if (which != "all") glbs = glbs.Where(p => which.Split('+').Any(f => p.Contains(f))).ToList();
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>(true)).ToList();
            var report = new Dictionary<string, object>();
            bool ok = true;
            foreach (var p in glbs)
            {
                var subs = AssetDatabase.LoadAllAssetsAtPath(p);
                int tex = subs.OfType<Texture2D>().Count(), mats = subs.OfType<Material>().Count(), meshes = subs.OfType<Mesh>().Count();
                int expectTex = rows.Count(r => r.path == p);
                int used = 0, nullMesh = 0, nullSlots = 0, usedActive = 0;
                foreach (var r in renderers)
                {
                    var src = PrefabUtility.GetCorrespondingObjectFromSource(r);
                    Mesh m = r is SkinnedMeshRenderer smr ? smr.sharedMesh : r.GetComponent<MeshFilter>() ? r.GetComponent<MeshFilter>().sharedMesh : null;
                    bool fromGlb = (src && AssetDatabase.GetAssetPath(src) == p) || (m && AssetDatabase.GetAssetPath(m) == p);
                    if (!fromGlb) continue;
                    used++;
                    if (r.gameObject.activeInHierarchy && r.enabled) usedActive++;
                    if (!m && !(r is ParticleSystemRenderer)) nullMesh++;
                    nullSlots += r.sharedMaterials.Count(x => !x);
                }
                bool good = tex >= expectTex && nullMesh == 0 && nullSlots == 0;
                ok &= good;
                var texs = subs.OfType<Texture2D>().ToList();
                report[p] = new
                {
                    ok = good, textures = tex, expectedTextures = expectTex, materials = mats, meshes = meshes,
                    formats = texs.GroupBy(t => t.graphicsFormat.ToString()).ToDictionary(g => g.Key, g => g.Count()),
                    mb = Math.Round(texs.Sum(t => MB(Bytes(t))), 1), sceneRenderers = used, activeRenderers = usedActive, nullMesh, nullMaterialSlots = nullSlots,
                };
            }
            WriteJson("verify-glb-" + DateTime.Now.ToString("HHmm") + ".json", report);
            if (!ok) throw new Exception("glb verification failed: " + JsonConvert.SerializeObject(report));
            return JsonConvert.SerializeObject(report);
        }

        // ------------------------------------------------------------------ parity captures (graphics, isolated scene)
        const string Market = "Assets/AthenHill/Art/KaraveenMarket/KaraveenMarket.glb";
        const string Retrofit = "Assets/AthenHill/Art/WardRetrofit/WardRetrofit.glb";

        /// Close-up views of the biggest changed assets, rendered in a new empty scene (one sun, flat ambient, no post) so a
        /// capture never loads the city (VRAM). Positions are in the asset's own space: the market and retrofit .glb files
        /// are authored in city coordinates and placed at the origin. Vector3.zero = frame the asset's bounds.
        static readonly Dictionary<string, (string name, string asset, Vector3 pos, Vector3 target)[]> ParitySets =
            new Dictionary<string, (string name, string asset, Vector3 pos, Vector3 target)[]>
        {
            ["a"] = new[]
            {
                ("tm_market_pottery", Market, new Vector3(-36.4f, 1.62f, 3.6f), new Vector3(-39.4f, 1.0f, 5.6f)),
                ("tm_retro_pump", Retrofit, new Vector3(-30.5f, 1.62f, -25.5f), new Vector3(-33.0f, 2.2f, -30.5f)),
                ("tm_retro_nanofab", Retrofit, new Vector3(29.5f, 1.62f, -19.5f), new Vector3(32.5f, 2.5f, -24.0f)),
                ("tm_tool_wall", "Assets/AthenHill/Art/WardShops/ToolExchangeProps/TE_tool_wall.glb", Vector3.zero, Vector3.zero),
                ("tm_droid", "Assets/AthenHill/Art/WardRetrofit/MiningDroid.glb", Vector3.zero, Vector3.zero),
                ("tm_target_plate", "Assets/AthenHill/Art/Checkpoint/SteelTargetPlate.glb", Vector3.zero, Vector3.zero),
            },
            ["b"] = new[]
            {
                ("tm_market_tools", Market, new Vector3(-36.6f, 1.62f, -8.4f), new Vector3(-39.5f, 1.0f, -10.2f)),
                ("tm_arms_locker", "Assets/AthenHill/Art/Checkpoint/ArmsLocker.glb", Vector3.zero, Vector3.zero),
                ("tm_warden_booth", "Assets/AthenHill/Art/Checkpoint/WardenBooth.glb", Vector3.zero, Vector3.zero),
                ("tm_terminal", "Assets/AthenHill/Art/Imported/Meshy/MissionTerminal/mission-terminal.glb", Vector3.zero, Vector3.zero),
                ("tm_pistol_mods", "Assets/AthenHill/Art/Weapons/PistolMods/PistolMods.glb", Vector3.zero, Vector3.zero),
                ("tm_district_gate", "Assets/AthenHill/Prefabs/District/gate.prefab", Vector3.zero, Vector3.zero),
            },
        };

        public static string Parity(string set, string tag)
        {
            var views = ParitySets[set];
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            Texture.streamingTextureForceLoadAll = true;
            RenderSettings.skybox = null;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(.42f, .42f, .45f);
            RenderSettings.fog = false;
            var sun = new GameObject("sun").AddComponent<Light>();
            sun.type = LightType.Directional; sun.intensity = 2.2f; sun.color = new Color(1f, .96f, .9f); sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(48f, 35f, 0f);
            var camGo = new GameObject("__cap");
            var cam = camGo.AddComponent<Camera>();
            var acd = camGo.AddComponent<UniversalAdditionalCameraData>();
            acd.renderPostProcessing = false; acd.antialiasing = AntialiasingMode.None; acd.renderShadows = true;
            cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(.55f, .62f, .7f);
            cam.nearClipPlane = .05f; cam.farClipPlane = 400f; cam.fieldOfView = 50f; cam.enabled = false;
            var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32);
            var tex = new Texture2D(1920, 1080, TextureFormat.RGB24, false);
            var outDir = Evidence + "parity/" + tag;
            Directory.CreateDirectory(outDir);
            var placed = new Dictionary<string, GameObject>();
            var done = new List<string>();
            int slot = 0;
            foreach (var v in views)
            {
                if (!placed.TryGetValue(v.asset, out var go))
                {
                    var src = AssetDatabase.LoadAssetAtPath<GameObject>(v.asset);
                    if (!src) { done.Add(v.name + ": missing " + v.asset); continue; }
                    go = UnityEngine.Object.Instantiate(src);
                    go.SetActive(true);
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                        if (r.name.StartsWith("COL")) r.enabled = false;     // collision proxies are hidden in the city too
                    if (v.pos == Vector3.zero) go.transform.position = new Vector3(300f + 60f * slot++, 0f, 300f);
                    placed[v.asset] = go;
                }
                Vector3 pos = v.pos, target = v.target;
                if (pos == Vector3.zero)
                {
                    var rs = go.GetComponentsInChildren<Renderer>(true);
                    if (rs.Length == 0) { done.Add(v.name + ": no renderers"); continue; }
                    var b = rs[0].bounds;
                    foreach (var r in rs) b.Encapsulate(r.bounds);
                    target = b.center;
                    pos = b.center + new Vector3(-.55f, .3f, -.85f).normalized * Mathf.Max(1.0f, b.extents.magnitude * 1.9f);
                }
                cam.transform.position = pos;
                cam.transform.LookAt(target);
                cam.targetTexture = rt;
                for (int k = 0; k < 3; k++) cam.Render();
                RenderTexture.active = rt;
                tex.ReadPixels(new Rect(0, 0, 1920, 1080), 0, 0);
                tex.Apply();
                RenderTexture.active = null;
                File.WriteAllBytes(Path.Combine(outDir, v.name + ".png"), tex.EncodeToPNG());
                done.Add(v.name);
            }
            cam.targetTexture = null;
            rt.Release();
            return outDir + ": " + string.Join(", ", done);
        }

        /// After ApplyImporters (graphics run): every changed TextureImporter texture is drawn back at its source size and
        /// compared with the source file (PSNR per channel; R/G only for normal maps, whose BC5 copy has no blue).
        public static string ImporterPsnr()
        {
            var rec = JsonConvert.DeserializeObject<Dictionary<string, Newtonsoft.Json.Linq.JObject>>(File.ReadAllText(Evidence + "importers-applied.json"));
            var outp = new Dictionary<string, object>();
            foreach (var kv in rec)
            {
                var path = kv.Key;
                if (path.StartsWith("reverted: ")) continue;
                var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                if (!ti || !tex) continue;
                bool normal = ti.textureType == TextureImporterType.NormalMap;
                bool linear = normal || !ti.sRGBTexture;
                var src = new Texture2D(2, 2, TextureFormat.RGBA32, false, linear);
                src.LoadImage(File.ReadAllBytes(path));
                int w = src.width, h = src.height;
                var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32, linear ? RenderTextureReadWrite.Linear : RenderTextureReadWrite.sRGB);
                Graphics.Blit(tex, rt);
                var back = new Texture2D(w, h, TextureFormat.RGBA32, false, linear);
                RenderTexture.active = rt;
                back.ReadPixels(new Rect(0, 0, w, h), 0, 0);
                back.Apply();
                RenderTexture.active = null;
                RenderTexture.ReleaseTemporary(rt);
                var a = src.GetPixels32(); var c = back.GetPixels32();
                double[] se = new double[4]; int worst = 0;
                for (int i = 0; i < a.Length; i++)
                {
                    int dr = a[i].r - c[i].r, dg = a[i].g - c[i].g, db = normal ? 0 : a[i].b - c[i].b, da = a[i].a - c[i].a;
                    se[0] += dr * dr; se[1] += dg * dg; se[2] += db * db; se[3] += da * da;
                    worst = Math.Max(worst, Math.Max(Math.Max(Math.Abs(dr), Math.Abs(dg)), Math.Max(Math.Abs(db), Math.Abs(da))));
                }
                string P(double e) => e <= 0 ? "inf" : (10 * Math.Log10(255.0 * 255.0 / (e / a.Length))).ToString("F1");
                outp[path] = new { size = w + "x" + h, imported = tex.width + "x" + tex.height + " " + tex.graphicsFormat, psnrR = P(se[0]), psnrG = P(se[1]), psnrB = normal ? "n/a (BC5)" : P(se[2]), psnrA = P(se[3]), maxErr = worst };
                UnityEngine.Object.DestroyImmediate(src); UnityEngine.Object.DestroyImmediate(back);
            }
            WriteJson("importers-psnr.json", outp);
            return outp.Count + " importer textures compared";
        }

        /// Visual parity for the changed TextureImporter textures (graphics run): the same 256 x 256-texel window of the
        /// source file (decoded fresh, uncompressed, own mips) and of the imported texture, both drawn at 2x into a 512 px
        /// tile with the same sampler, side by side (source left), with a PSNR of the two tiles. Normal maps skipped (BC5
        /// has no blue to show; their R/G PSNR is in importers-psnr.json).
        public static string Board()
        {
            Texture.streamingTextureForceLoadAll = true;
            var rec = JsonConvert.DeserializeObject<Dictionary<string, object>>(File.ReadAllText(Evidence + "importers-applied.json"));
            var outDir = Evidence + "parity/importers";
            Directory.CreateDirectory(outDir);
            var res = new Dictionary<string, object>();
            foreach (var path in rec.Keys.Where(k => !k.StartsWith("reverted: ")))
            {
                var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                if (!ti || !tex || ti.textureType == TextureImporterType.NormalMap) continue;
                bool linear = !ti.sRGBTexture;
                var src = new Texture2D(2, 2, TextureFormat.RGBA32, true, linear);
                src.LoadImage(File.ReadAllBytes(path));
                src.filterMode = FilterMode.Bilinear; src.wrapMode = TextureWrapMode.Clamp;
                var scale = new Vector2(256f / src.width, 256f / src.height);
                var offset = new Vector2(.5f - scale.x / 2, .5f - scale.y / 2);
                var rt = RenderTexture.GetTemporary(512, 512, 0, RenderTextureFormat.ARGB32, linear ? RenderTextureReadWrite.Linear : RenderTextureReadWrite.sRGB);
                var tiles = new Color32[2][];
                var tile = new Texture2D(512, 512, TextureFormat.RGBA32, false, linear);
                int k = 0;
                foreach (var t in new Texture[] { src, tex })
                {
                    Graphics.Blit(t, rt, scale, offset);
                    RenderTexture.active = rt; tile.ReadPixels(new Rect(0, 0, 512, 512), 0, 0); tile.Apply(); RenderTexture.active = null;
                    tiles[k++] = tile.GetPixels32();
                }
                RenderTexture.ReleaseTemporary(rt);
                var pair = new Texture2D(1032, 512, TextureFormat.RGB24, false, linear);
                var px = new Color32[1032 * 512];
                for (int y = 0; y < 512; y++)
                    for (int x = 0; x < 1032; x++)
                        px[y * 1032 + x] = x < 512 ? tiles[0][y * 512 + x] : x < 520 ? new Color32(255, 255, 255, 255) : tiles[1][y * 512 + x - 520];
                pair.SetPixels32(px); pair.Apply();
                var name = Path.GetFileNameWithoutExtension(path);
                File.WriteAllBytes(Path.Combine(outDir, name + ".png"), pair.EncodeToPNG());
                double se = 0; int worst = 0;
                for (int i = 0; i < tiles[0].Length; i++)
                {
                    int dr = tiles[0][i].r - tiles[1][i].r, dg = tiles[0][i].g - tiles[1][i].g, db = tiles[0][i].b - tiles[1][i].b;
                    se += dr * dr + dg * dg + db * db; worst = Math.Max(worst, Math.Max(Math.Abs(dr), Math.Max(Math.Abs(dg), Math.Abs(db))));
                }
                res[path] = new { tilePsnrRGB = se <= 0 ? "inf" : (10 * Math.Log10(255.0 * 255.0 / (se / (3.0 * tiles[0].Length)))).ToString("F1"), maxErr = worst, imported = tex.width + "x" + tex.height + " " + tex.graphicsFormat };
                UnityEngine.Object.DestroyImmediate(src); UnityEngine.Object.DestroyImmediate(tile); UnityEngine.Object.DestroyImmediate(pair);
            }
            WriteJson("importers-board.json", res);
            return res.Count + " tiles in " + outDir;
        }

        // ------------------------------------------------------------------ review cameras (combined native lookbook)
        const string CamRootName = "Texture memory review cameras";

        /// Player-height views of the biggest recompressed assets (eye 1.62 m above the ground found by a ray down at the
        /// camera; target heights absolute, or ground + y when groundTarget). Disabled Camera components only.
        static readonly (string name, Vector2 xz, Vector3 target, bool groundTarget)[] ReviewViews =
        {
            ("cam_tm_market_pottery", new Vector2(-36.4f, 3.6f), new Vector3(-39.4f, 1.0f, 5.6f), false),
            ("cam_tm_retro_pump", new Vector2(-30.5f, -25.5f), new Vector3(-33.0f, 2.2f, -30.5f), false),
            ("cam_tm_retro_nanofab", new Vector2(29.5f, -19.5f), new Vector3(32.5f, 2.5f, -24.0f), false),
            ("cam_tm_mining_droid", new Vector2(-46.0f, -22.5f), new Vector3(-46.1f, 1.6f, -28.0f), false),
            ("cam_tm_warden_post", new Vector2(-68.8f, -7.8f), new Vector3(-71.3f, 0.9f, -4.2f), true),
            ("cam_tm_range_plate", new Vector2(-75.0f, 9.0f), new Vector3(-78.0f, 0.6f, 11.0f), true),
        };

        static float Ground(Vector2 xz)
        {
            Physics.SyncTransforms();
            var hits = Physics.RaycastAll(new Vector3(xz.x, 60f, xz.y), Vector3.down, 120f, ~0, QueryTriggerInteraction.Ignore);
            // highest walkable surface below 20 m (skip roofs/canopies above a person's head)
            var ys = hits.Where(h => h.point.y < 20f && h.normal.y > .6f).Select(h => h.point.y).OrderByDescending(y => y).ToList();
            return ys.Count > 0 ? ys.Last() > ys[0] - 3f ? ys[0] : ys.Last() : 0f;
        }

        public static string AddReviewCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            var rec = new List<object>();
            foreach (var v in ReviewViews)
            {
                float gy = Ground(v.xz);
                var pos = new Vector3(v.xz.x, gy + 1.62f, v.xz.y);
                var target = v.groundTarget ? new Vector3(v.target.x, Ground(new Vector2(v.target.x, v.target.z)) + v.target.y, v.target.z) : v.target;
                var go = new GameObject(v.name);
                go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var c = go.AddComponent<Camera>(); c.enabled = false; c.fieldOfView = 55f; c.nearClipPlane = .05f;
                rec.Add(new { v.name, pos = new[] { pos.x, pos.y, pos.z }, target = new[] { target.x, target.y, target.z }, ground = gy });
            }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            WriteJson("review-cameras.json", rec);
            return ReviewViews.Length + " cameras under " + CamRootName + ": " + JsonConvert.SerializeObject(rec);
        }

        /// Final check of the saved project (-nographics): every scene .glb verified (VerifyGlb), the TextureImporter
        /// overrides in place and compressed, the add-on on, the review cameras present, and scene-wide missing material
        /// slots counted (should be the same as before the pass: it changes no scene references).
        public static string Verify()
        {
            var glb = VerifyGlb("all");
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            var renderers = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>(true)).ToList();
            int nullSlots = renderers.Sum(r => r.sharedMaterials.Count(m => !m));
            var rec = JsonConvert.DeserializeObject<Dictionary<string, object>>(File.ReadAllText(Evidence + "importers-applied.json"));
            var importers = rec.Keys.Where(k => !k.StartsWith("reverted: ")).Select(k =>
            {
                var ti = AssetImporter.GetAtPath(k) as TextureImporter;
                var t = AssetDatabase.LoadAssetAtPath<Texture2D>(k);
                var ps = ti ? ti.GetPlatformTextureSettings("Standalone") : null;
                return new { path = k, overridden = ps != null && ps.overridden, format = ps != null ? ps.format.ToString() : null, imported = t ? t.graphicsFormat.ToString() : null, compressed = t && GraphicsFormatUtility.IsCompressedFormat(t.graphicsFormat), streaming = t && t.streamingMipmaps };
            }).ToList();
            bool ok = cams && cams.transform.childCount == ReviewViews.Length && importers.All(i => i.overridden && i.compressed) && GltfTextureCompression.DefaultOn;
            var result = new
            {
                ok, addonDefaultOn = GltfTextureCompression.DefaultOn, reviewCameras = cams ? cams.transform.childCount : 0,
                renderers = renderers.Count, sceneNullMaterialSlots = nullSlots, importers, glb = Newtonsoft.Json.Linq.JToken.Parse(glb),
            };
            WriteJson("verify-saved-scene.json", result);
            if (!ok) throw new Exception("verify failed: " + JsonConvert.SerializeObject(result));
            return $"ok: {importers.Count} importers compressed, add-on on, {result.reviewCameras} review cameras, scene null material slots {nullSlots}";
        }

        // ------------------------------------------------------------------ measurement player (own folder)
        /// Development player of the saved scene into Builds/tm-&lt;name&gt; (OpenGL, as LinuxBuild) for the native probe runs;
        /// never touches Builds/LinuxDevelopment or the scene. Delete the folder when the numbers are recorded.
        static string BuildPlayer(string name)
        {
            EditorSceneManager.OpenScene(ScenePath);
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ScenePath }, locationPathName = "Builds/tm-" + name + "/AthenHill.x86_64",
                target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development,
            });
            if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("build failed: " + name);
            return $"Builds/tm-{name} {report.summary.totalTime.TotalSeconds:0} s, {report.summary.totalSize / 1048576} MB";
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "inventory").Split(',');
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    var t0 = DateTime.Now;
                    string result = parts[0] switch
                    {
                        "inventory" => Inventory(parts.Length > 1 ? parts[1] : "before"),
                        "plan" => JsonConvert.SerializeObject(ImporterPlan(parts.Length > 1 ? parts[1] : "").GroupBy(p => p.decision).ToDictionary(g => g.Key, g => g.Count())),
                        "importers" => ApplyImporters(parts.Length > 1 ? parts[1] : ""),
                        "revert" => RevertImporters(parts.Length > 1 ? parts[1] : ""),
                        "parity" => Parity(parts[1], parts[2]),
                        "psnr" => ImporterPsnr(),
                        "board" => Board(),
                        "cameras" => AddReviewCameras(),
                        "verify" => Verify(),
                        "build" => BuildPlayer(parts[1]),
                        "metrics" => JsonConvert.SerializeObject(parts[1].Split('+').ToDictionary(x => x, x => MeshMetrics(x))),
                        "gltf" => ReimportGltf(parts.Length > 1 ? parts[1] : "all", parts.Length > 2 ? parts[2] : "run"),
                        "gltfplain" => ReimportGltf(parts[1], parts.Length > 2 ? parts[2] : "plain", false),
                        "verifyglb" => VerifyGlb(parts.Length > 1 ? parts[1] : "all"),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log($"TextureMemoryPass {st} ({(DateTime.Now - t0).TotalSeconds:F0} s): {result}");
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
