using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    public static class ImportTraveler
    {
        const string Folder = "Assets/AthenHill/Art/Imported/Meshy/Traveler";
        const string ModelPath = Folder + "/Traveler.fbx";
        const string SourceFolder = "../../meshy/Meshy_AI_weathered_traveler_ri_biped/";
        const string SourceStem = "Meshy_AI_weathered_traveler_ri_biped";
        const string PrefabPath = "Assets/AthenHill/Prefabs/Traveler.prefab";

        public static void ImportAndBuild()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            ImportWardGuard.Install();
            Install();
            LinuxBuild.Development();
            File.Copy("Captures/linux-build.json", "Captures/traveler-development-build.json", true);
            LinuxBuild.Release();
            File.Copy("Captures/linux-build.json", "Captures/traveler-release-build.json", true);
        }

        [MenuItem("Athen Hill/Characters/Use supplied Traveler for ambient walkers")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play before importing NPCs.");
            var walkers = UnityEngine.Object.FindObjectsByType<AmbientWalker>().OrderBy(w => w.name).ToArray();
            if (walkers.Length != 3) throw new Exception("Expected the three existing ambient walkers.");
            var routes = walkers.Select(w => new { walker = w, waypoints = w.waypoints.ToArray(), w.speed, w.phase }).ToArray();
            var talking = UnityEngine.Object.FindObjectsByType<NpcAgent>();
            var talkingActors = talking.Select(n => n.actor).ToArray();
            var player = UnityEngine.Object.FindAnyObjectByType<PlayerMotor>();
            var playerVisual = player.visual;

            Directory.CreateDirectory(Path.GetDirectoryName(ModelPath));
            File.Copy(SourceFolder + SourceStem + "_Animation_Walking_withSkin.fbx", ModelPath, true);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            importer.animationType = ModelImporterAnimationType.Legacy;
            importer.importAnimation = true;
            importer.importCameras = false;
            importer.importLights = false;
            importer.isReadable = true;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.animationCompression = ModelImporterAnimationCompression.Off;
            importer.SaveAndReimport();
            var takes = importer.defaultClipAnimations;
            if (takes.Length != 1) throw new Exception("Expected one supplied walking take.");
            takes[0].name = "walk";
            takes[0].loopTime = true;
            takes[0].wrapMode = WrapMode.Loop;
            importer.clipAnimations = takes;
            importer.SaveAndReimport();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            var clips = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<AnimationClip>().ToArray();
            var walk = clips.Single(c => c.name == "walk");
            if (!walk.legacy) throw new Exception("Expected legacy walking animation.");
            var idle = AssetDatabase.LoadAssetAtPath<AnimationClip>(Folder + "/idle.anim");
            if (!idle) { idle = new AnimationClip(); AssetDatabase.CreateAsset(idle, Folder + "/idle.anim"); }
            idle.ClearCurves(); idle.name = "idle"; idle.legacy = true;
            foreach (var binding in AnimationUtility.GetCurveBindings(walk))
            {
                float value = AnimationUtility.GetEditorCurve(walk, binding).Evaluate(0);
                AnimationUtility.SetEditorCurve(idle, binding, AnimationCurve.Constant(0, 1, value));
            }
            EditorUtility.SetDirty(idle);
            var material = ImportMaterial();

            var template = new GameObject("Traveler");
            var rig = (GameObject)PrefabUtility.InstantiatePrefab(model);
            rig.transform.SetParent(template.transform, false);
            var actor = template.AddComponent<ActorAnimation>();
            actor.animationSource = rig.GetComponentInChildren<Animation>();
            if (!actor.animationSource) actor.animationSource = rig.AddComponent<Animation>();
            actor.animationSource.playAutomatically = false;
            actor.idle = idle;
            actor.walk = walk;
            actor.run = walk; // Ambient NPCs never run or talk; no invented animation.
            actor.talk = idle;
            actor.walkStrideSpeed = actor.runStrideSpeed = 1.35f;
            if (actor.walk.length < .5f) throw new Exception("Traveler walking loop is missing.");
            var renderers = rig.GetComponentsInChildren<SkinnedMeshRenderer>();
            int triangles = renderers.Sum(r => r.sharedMesh.triangles.Length / 3);
            if (triangles > 12000 || renderers.Length != 1 || renderers[0].bones.Length != 24)
                throw new Exception("Traveler exceeds mesh/rig budget.");
            // Native FBX import preserves the supplied mesh and skin weights, with metre normalization on its visual root.
            var rest = SkinPoints(renderers[0], template.transform);
            float restLow = rest.Min(v => v.y), restHeight = rest.Max(v => v.y) - restLow;
            float scale = 1.8f / restHeight;
            rig.transform.localScale *= scale;
            rig.transform.localPosition = Vector3.up * (-restLow * scale);
            foreach (var r in renderers)
            {
                r.sharedMaterial = material;
                r.shadowCastingMode = ShadowCastingMode.On;
                r.receiveShadows = true;
                r.updateWhenOffscreen = true;
                if (!r.sharedMaterial || !r.sharedMaterial.shader || r.sharedMaterial.shader.name.Contains("Error"))
                    throw new Exception("Traveler material failed to import.");
            }
            var bounds = Enumerable.Range(0, 16).Select(i => {
                actor.walk.SampleAnimation(actor.animationSource.gameObject, actor.walk.length * i / 16);
                var points = SkinPoints(renderers[0], template.transform);
                float low = points.Min(v => v.y), height = points.Max(v => v.y) - low;
                if (Mathf.Abs(height - 1.8f) > .15f || Mathf.Abs(low) > .08f)
                    throw new Exception($"Traveler walk has wrong height/origin at frame {i}: {height}/{low}");
                var foot = renderers[0].bones.Single(b => b.name == "LeftFoot");
                return new { frame = i, low, height, foot = template.transform.InverseTransformPoint(foot.position) };
            }).ToArray();
            if (Vector3.Distance(bounds[0].foot, bounds[4].foot) < .05f) throw new Exception("Traveler walk has no foot motion.");
            actor.idle.SampleAnimation(actor.animationSource.gameObject, 0);
            var prefab = PrefabUtility.SaveAsPrefabAsset(template, PrefabPath);
            UnityEngine.Object.DestroyImmediate(template);

            foreach (var walker in walkers)
            {
                var oldActor = walker.actor;
                if (!oldActor) throw new Exception("Missing actor on " + walker.name);
                // Preserve the existing gameplay root, waypoint references, speed and phase.
                if (PrefabUtility.IsPartOfPrefabInstance(walker.gameObject))
                    PrefabUtility.UnpackPrefabInstance(PrefabUtility.GetOutermostPrefabInstanceRoot(walker.gameObject), PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                if (oldActor.gameObject == walker.gameObject)
                {
                    var visualRoots = oldActor.GetComponentsInChildren<SkinnedMeshRenderer>().Select(r => {
                        var t = r.transform;
                        while (t.parent != walker.transform && t.parent) t = t.parent;
                        return t.gameObject;
                    }).Distinct().ToArray();
                    if (visualRoots.Any(go => go == walker.gameObject)) throw new Exception("Unexpected renderer on walker root.");
                    if (oldActor.animationSource && oldActor.animationSource.gameObject == walker.gameObject)
                        UnityEngine.Object.DestroyImmediate(oldActor.animationSource);
                    foreach (var go in visualRoots) UnityEngine.Object.DestroyImmediate(go);
                    UnityEngine.Object.DestroyImmediate(oldActor);
                }
                else UnityEngine.Object.DestroyImmediate(oldActor.gameObject);
                var replacement = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                replacement.transform.SetParent(walker.transform, false);
                walker.actor = replacement.GetComponent<ActorAnimation>();
                walker.actor.idle.SampleAnimation(walker.actor.animationSource.gameObject, 0);
                EditorUtility.SetDirty(walker);
            }
            foreach (var route in routes)
                if (!route.walker.waypoints.SequenceEqual(route.waypoints) || route.walker.speed != route.speed || route.walker.phase != route.phase)
                    throw new Exception("Ambient route changed unexpectedly.");
            if (!talking.Select(n => n.actor).SequenceEqual(talkingActors) || player.visual != playerVisual)
                throw new Exception("Talking NPC or player changed unexpectedly.");
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(walkers[0].gameObject.scene);
            EditorSceneManager.SaveOpenScenes();
            Directory.CreateDirectory("Captures");
            File.WriteAllText("Captures/traveler-import.json", JsonConvert.SerializeObject(new {
                model = ModelPath, triangles, walkers = walkers.Select(w => new { w.name, visual = w.actor.name, w.speed, w.phase }),
                animation = "Supplied walking loop; idle/talk are first-frame poses, run is a walk alias (unused by ambient NPCs).",
                bounds = bounds.Select(b => new { b.frame, b.low, b.height, foot = new[] { b.foot.x, b.foot.y, b.foot.z } })
            }, Formatting.Indented));
        }

        static Vector3[] SkinPoints(SkinnedMeshRenderer r, Transform root)
        {
            var mesh = r.sharedMesh;
            var matrices = r.bones.Select((bone, i) => root.worldToLocalMatrix * bone.localToWorldMatrix * mesh.bindposes[i]).ToArray();
            var weights = mesh.boneWeights;
            return mesh.vertices.Select((v, i) => {
                var w = weights[i];
                return matrices[w.boneIndex0].MultiplyPoint3x4(v) * w.weight0
                    + matrices[w.boneIndex1].MultiplyPoint3x4(v) * w.weight1
                    + matrices[w.boneIndex2].MultiplyPoint3x4(v) * w.weight2
                    + matrices[w.boneIndex3].MultiplyPoint3x4(v) * w.weight3;
            }).ToArray();
        }

        static Texture2D ImportTexture(string source, string name, bool srgb, bool readable = false)
        {
            string path = Folder + "/" + name + ".png";
            File.Copy(source, path, true);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = TextureImporterType.Default;
            importer.sRGBTexture = srgb;
            importer.maxTextureSize = 2048;
            importer.isReadable = readable;
            importer.textureCompression = readable ? TextureImporterCompression.Uncompressed : TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static Material ImportMaterial()
        {
            var color = ImportTexture(SourceFolder + SourceStem + "_texture_0.png", "Albedo", true);
            var roughness = ImportTexture(SourceFolder + SourceStem + "_texture_0_roughness.png", "Roughness", false, true);
            var metallic = ImportTexture(SourceFolder + SourceStem + "_texture_0_metallic.png", "Metallic", false, true);
            if (roughness.width != metallic.width || roughness.height != metallic.height) throw new Exception("Mismatched PBR texture sizes.");
            var roughPixels = roughness.GetPixels32(); var metalPixels = metallic.GetPixels32();
            for (int i = 0; i < metalPixels.Length; i++) metalPixels[i] = new Color32(metalPixels[i].r, 0, 0, (byte)(255 - roughPixels[i].r));
            var packed = new Texture2D(metallic.width, metallic.height, TextureFormat.RGBA32, false, true);
            packed.SetPixels32(metalPixels); packed.Apply();
            string packedPath = Folder + "/MetallicSmoothness.png";
            File.WriteAllBytes(packedPath, packed.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(packed);
            AssetDatabase.ImportAsset(packedPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(packedPath);
            importer.sRGBTexture = false; importer.maxTextureSize = 2048;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
            var material = AssetDatabase.LoadAssetAtPath<Material>(Folder + "/Traveler.mat");
            if (!material) { material = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(material, Folder + "/Traveler.mat"); }
            material.SetTexture("_BaseMap", color); material.SetColor("_BaseColor", Color.white);
            material.SetTexture("_MetallicGlossMap", AssetDatabase.LoadAssetAtPath<Texture2D>(packedPath));
            material.SetFloat("_Metallic", 1); material.SetFloat("_Smoothness", 1);
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            EditorUtility.SetDirty(material);
            return material;
        }
    }
}
