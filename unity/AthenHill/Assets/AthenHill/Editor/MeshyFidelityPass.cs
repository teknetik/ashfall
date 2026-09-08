using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Profiling;

namespace AthenHill.Editor
{
    // Scoped recovery of retained source data. Never reload/reconstruct the live city.
    public static class MeshyFidelityPass
    {
        const string Evidence = "../evidence/fidelity/20260908";
        const string Folder = "Assets/AthenHill/Art/Imported/Meshy/Fidelity";
        const string Guard = "Assets/AthenHill/Art/Imported/Meshy/ward-guard.glb";
        const string TerminalFolder = "Assets/AthenHill/Art/Imported/Meshy/MissionTerminal";
        static readonly string[] Cameras = { "cam_hill", "cam_avenue", "cam_gate", "cam_terminal", "cam_fidelity_guard", "cam_shop_recovery_close", "cam_salvage_general", "cam_fidelity_generator" };

        static void CheckScene()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new Exception("Finish Play/compilation before fidelity operations.");
            if (EditorSceneManager.GetActiveScene().path != ImportBaseline.ScenePath) throw new Exception("The existing AthenHill scene must be open; this pass does not reload it.");
            Directory.CreateDirectory(Evidence);
        }
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };
        static void Write(string file, object data) => File.WriteAllText(Evidence + "/" + file, JsonConvert.SerializeObject(data, Formatting.Indented));
        static void Backup(string path)
        {
            if (!File.Exists(path)) return;
            var destination = Evidence + "/asset-backup/" + path;
            if (File.Exists(destination)) return;
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            File.Copy(path, destination);
            if (File.Exists(path + ".meta")) File.Copy(path + ".meta", destination + ".meta");
        }
        static string PhysicsSignature() => JsonConvert.SerializeObject(UnityEngine.Object.FindObjectsByType<Collider>().OrderBy(c => Hierarchy(c.transform)).ThenBy(c => c.GetType().Name)
            .Select(c => new { path = Hierarchy(c.transform), type = c.GetType().Name, position = V(c.transform.position), rotation = V(c.transform.eulerAngles), scale = V(c.transform.lossyScale), c.enabled, c.isTrigger,
                boxCenter = c is BoxCollider b ? V(b.center) : null, boxSize = c is BoxCollider box ? V(box.size) : null,
                mesh = c is MeshCollider m ? AssetDatabase.GetAssetPath(m.sharedMesh) : null }));
        static string Hierarchy(Transform t) => t.parent ? Hierarchy(t.parent) + "/" + t.name : t.name;
        static Mesh MeshOf(Renderer r)
        {
            if (r is SkinnedMeshRenderer skin) return skin.sharedMesh;
            var filter = r.GetComponent<MeshFilter>();
            return filter ? filter.sharedMesh : null;
        }

        [MenuItem("Athen Hill/Fidelity/1 Capture and build baseline")]
        public static void Baseline()
        {
            CheckScene();
            if (File.Exists(Evidence + "/applied.json")) throw new Exception("A recovery is already applied; do not overwrite its baseline.");
            Backup(ImportBaseline.ScenePath);
            var npc = UnityEngine.Object.FindObjectsByType<NpcAgent>().Single(n => n.name == "npc_vex");
            ImportBaseline.Camera("cam_fidelity_guard", npc.transform.position + npc.transform.forward * 3f + npc.transform.right * .5f + Vector3.up * 1.35f,
                npc.transform.position + Vector3.up * 1.05f, 42);
            var generator = GameObject.Find("Post-war salvage").GetComponentsInChildren<MeshFilter>(true).First(f =>
                AssetDatabase.GetAssetPath(f.sharedMesh).Contains("generator") && f.gameObject.activeInHierarchy);
            var center = generator.GetComponent<Renderer>().bounds.center;
            ImportBaseline.Camera("cam_fidelity_generator", center + new Vector3(2.3f, 1.1f, 2.3f), center, 45);
            EditorSceneManager.SaveOpenScenes();
            Capture("before-editor");
            Report("before-assets.json");
            Build("FidelityBaseline");
        }

        [MenuItem("Athen Hill/Fidelity/2 Restore source meshes and materials")]
        public static void Restore()
        {
            CheckScene();
            if (!File.Exists(Evidence + "/before-assets.json")) throw new Exception("Capture the fidelity baseline first.");
            var gameplay = DistrictCityPass.GameplaySignature();
            var physics = PhysicsSignature();
            Directory.CreateDirectory(Folder);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            var stoneWearPath = "Assets/AthenHill/Art/Weathering/MAT_stone Local wear.mat";
            var stoneWear = AssetDatabase.LoadAssetAtPath<Material>(stoneWearPath);
            if (stoneWear && !stoneWear.GetTexture("_BaseMap"))
            {
                Backup(stoneWearPath);
                WardWeatheringPass.CopyGltfSurface(AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/World/MAT_stone.mat"), stoneWear);
            }
            // The processor changes only the four arm rotations and static state aliases.
            Backup(Guard);
            File.Copy("../staging/ward-guard.glb", Guard, true);
            AssetDatabase.ImportAsset(Guard, ImportAssetOptions.ForceSynchronousImport);
            RestoreTerminal();
            foreach (var name in ImportSalvageAssets.Names) RestoreFamily(ImportSalvageAssets.Folder, ImportSalvageAssets.Prefabs, name, "Salvage");
            // Seven district shop candidates remain rejected/inactive. Restore only the two active arches.
            RestoreFamily(ImportDistrictAssets.Folder, ImportDistrictAssets.Prefabs, "gate", "District");
            var guards = UnityEngine.Object.FindObjectsByType<NpcAgent>().OrderBy(n => n.name).Select(n => new {
                n.name, triangles = n.actor.GetComponentsInChildren<SkinnedMeshRenderer>().Sum(r => r.sharedMesh.triangles.Length / 3)
            }).ToArray();
            if (guards.Length != 4 || guards.Any(g => g.triangles != 38071)) throw new Exception("All four guards must reference the intact 38,071-triangle source.");
            if (DistrictCityPass.GameplaySignature() != gameplay || PhysicsSignature() != physics)
                throw new Exception("Recovery changed gameplay roots/routes or colliders; inspect before saving.");
            StaticRenderChunksEditor.Rebuild(chunks);
            AssetDatabase.SaveAssets();
            EditorSceneManager.SaveOpenScenes();
            Write("applied.json", new { guards, guardGeometryPreserved = true, terminalTriangles = 25656,
                gameplayPreserved = true, collisionPreserved = true, rejectedShopsRemainInactive = true,
                sourceMaterialFamilies = ImportSalvageAssets.Names.Concat(new[] { "district/gate" }),
                note = "Restored original UVs/PBR textures; no building transforms, foundations or gameplay roots were replaced." });
            Report("after-assets.json");
            Capture("after-editor");
        }
        static void RestoreTerminal()
        {
            var modelPath = TerminalFolder + "/mission-terminal.glb";
            Backup(modelPath); Backup(TerminalFolder + "/MissionTerminal.mat");
            File.Copy("../../meshy/mission-terminal-v1/model/mission-terminal.glb", modelPath, true);
            AssetDatabase.ImportAsset(modelPath, ImportAssetOptions.ForceSynchronousImport);
            var source = AssetDatabase.LoadAllAssetsAtPath(modelPath).OfType<Mesh>().Single();
            if (source.triangles.Length / 3 != 25656) throw new Exception("Wrong terminal source mesh.");
            var mesh = ImportMissionTerminal.WithTangents(source);
            var material = ImportMissionTerminal.ImportMaterial();
            var prefabPath = "Assets/AthenHill/Prefabs/MissionTerminal.prefab";
            Backup(prefabPath);
            var prefab = PrefabUtility.LoadPrefabContents(prefabPath);
            try
            {
                foreach (var f in prefab.GetComponentsInChildren<MeshFilter>(true)) { f.sharedMesh = mesh; f.GetComponent<Renderer>().sharedMaterial = material; }
                PrefabUtility.SaveAsPrefabAsset(prefab, prefabPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(prefab); }
            var root = GameObject.Find("Mission Terminal Upgrade");
            if (!root) throw new Exception("Existing mission terminals are missing.");
            foreach (var f in root.GetComponentsInChildren<MeshFilter>(true))
            {
                f.sharedMesh = mesh; f.GetComponent<Renderer>().sharedMaterial = material;
                PrefabUtility.RecordPrefabInstancePropertyModifications(f);
                PrefabUtility.RecordPrefabInstancePropertyModifications(f.GetComponent<Renderer>());
            }
        }
        static void RestoreFamily(string sourceFolder, string prefabs, string name, string family)
        {
            var modelPath = sourceFolder + "/" + name + "/" + name + ".fbx";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            var source = model.GetComponentInChildren<MeshFilter>().sharedMesh;
            var originalMaterial = AssetDatabase.LoadAssetAtPath<Material>(sourceFolder + "/" + name + "/" + name + ".mat");
            if (!originalMaterial) throw new Exception("Missing original PBR material for " + name);
            var materialPath = Folder + "/" + family + "_" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if (!mat) { mat = new Material(originalMaterial) { name = family + "_" + name + "_Source", enableInstancing = true }; AssetDatabase.CreateAsset(mat, materialPath); }
            foreach (var map in new[] { ("base_color", "_BaseMap"), ("normal", "_BumpMap"), ("metallic_smoothness", "_MetallicGlossMap") })
            {
                var path = sourceFolder + "/" + name + "/" + map.Item1 + ".png";
                Backup(path + ".meta");
                var importer = (TextureImporter)AssetImporter.GetAtPath(path);
                importer.GetSourceTextureWidthAndHeight(out int width, out int height);
                importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(width, height));
                importer.textureType = map.Item1 == "normal" ? TextureImporterType.NormalMap : TextureImporterType.Default;
                importer.sRGBTexture = map.Item1 == "base_color";
                importer.mipmapEnabled = true; importer.anisoLevel = 8; importer.wrapMode = TextureWrapMode.Repeat;
                importer.isReadable = false; importer.textureCompression = TextureImporterCompression.CompressedHQ;
                importer.SaveAndReimport();
                mat.SetTexture(map.Item2, AssetDatabase.LoadAssetAtPath<Texture2D>(path));
            }
            mat.SetFloat("_BumpScale", 1); mat.SetFloat("_Smoothness", 1);
            mat.EnableKeyword("_NORMALMAP"); mat.EnableKeyword("_METALLICSPECGLOSSMAP");
            EditorUtility.SetDirty(mat);
            bool Target(MeshFilter f)
            {
                var p = AssetDatabase.GetAssetPath(f.sharedMesh);
                return p == modelPath || p == sourceFolder + "/Atlas/" + name + ".asset"
                    || (family == "Salvage" && p == ImportDistrictAssets.Folder + "/Atlas/salvage_" + name + ".asset");
            }
            void Apply(MeshFilter f)
            {
                f.sharedMesh = source; f.GetComponent<Renderer>().sharedMaterial = mat;
                PrefabUtility.RecordPrefabInstancePropertyModifications(f);
                PrefabUtility.RecordPrefabInstancePropertyModifications(f.GetComponent<Renderer>());
            }
            var prefabPath = prefabs + "/" + name + ".prefab";
            Backup(prefabPath);
            var prefab = PrefabUtility.LoadPrefabContents(prefabPath);
            try { foreach (var f in prefab.GetComponentsInChildren<MeshFilter>(true).Where(Target)) Apply(f); PrefabUtility.SaveAsPrefabAsset(prefab, prefabPath); }
            finally { PrefabUtility.UnloadPrefabContents(prefab); }
            foreach (var f in UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include).Where(f => f.gameObject.scene.IsValid() && Target(f))) Apply(f);
        }
        static void Report(string name)
        {
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            bool editing = chunks.editingSources; chunks.ShowSources(true);
            try
            {
                var renderers = UnityEngine.Object.FindObjectsByType<Renderer>().Where(r => r.enabled && r.gameObject.activeInHierarchy && !r.transform.IsChildOf(chunks.transform)).ToArray();
                var textures = renderers.SelectMany(r => r.sharedMaterials).Where(m => m).Distinct()
                    .SelectMany(m => m.GetTexturePropertyNames().Select(m.GetTexture)).Where(t => t).Distinct().ToArray();
                Write(name, new { scene = EditorSceneManager.GetActiveScene().path, sourceFingerprint = chunks.sourceFingerprint,
                    sourceRendererCount = renderers.Length,
                    actors = UnityEngine.Object.FindObjectsByType<ActorAnimation>().Length,
                    textures = textures.Select(t => new { path = AssetDatabase.GetAssetPath(t), t.name, t.width, t.height, runtimeBytes = Profiler.GetRuntimeMemorySizeLong(t) }),
                    textureRuntimeBytes = textures.Sum(Profiler.GetRuntimeMemorySizeLong),
                    note = "Unity texture object memory is not total GPU VRAM usage; measure native process memory separately.",
                    meshes = renderers.Select(r => new { path = Hierarchy(r.transform), materials = r.sharedMaterials.Select(AssetDatabase.GetAssetPath),
                        mesh = AssetDatabase.GetAssetPath(MeshOf(r)) }) });
            }
            finally { chunks.ShowSources(editing); }
        }
        static void Capture(string phase)
        {
            Directory.CreateDirectory(Evidence + "/" + phase);
            ShaderUtil.allowAsyncCompilation = false;
            foreach (var camera in Cameras)
            {
                PortDiagnostics.Capture(camera); PortDiagnostics.Capture(camera);
                File.Copy("Captures/Fixed/" + camera + ".png", Evidence + "/" + phase + "/" + camera + ".png", true);
            }
        }
        static void Build(string name)
        {
            CheckScene();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            StaticRenderChunksEditor.Rebuild(chunks);
            AssetDatabase.SaveAssets(); EditorSceneManager.SaveOpenScenes();
            var output = "Builds/" + name + "/AthenHill.x86_64";
            var result = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { ImportBaseline.ScenePath }, locationPathName = output,
                target = BuildTarget.StandaloneLinux64, options = BuildOptions.Development });
            Write(name + "-build.json", new { result = result.summary.result.ToString(), errors = result.summary.totalErrors,
                warnings = result.summary.totalWarnings, seconds = result.summary.totalTime.TotalSeconds, bytes = result.summary.totalSize,
                path = result.summary.outputPath, sourceFingerprint = chunks.sourceFingerprint });
            if (result.summary.result != BuildResult.Succeeded) throw new Exception("Fidelity build failed.");
        }
        [MenuItem("Athen Hill/Fidelity/3 Build restored review player")]
        public static void BuildReview() { CheckScene(); Capture("after-editor"); Report("after-assets.json"); Build("FidelityReview"); }
        [MenuItem("Athen Hill/Fidelity/4 Build final Linux players")]
        public static void BuildFinal()
        {
            CheckScene(); StaticRenderChunksEditor.Rebuild(UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>());
            LinuxBuild.Development(); File.Copy("Captures/linux-build.json", Evidence + "/development-build.json", true);
            LinuxBuild.Release(); File.Copy("Captures/linux-build.json", Evidence + "/release-build.json", true);
        }
    }
}
