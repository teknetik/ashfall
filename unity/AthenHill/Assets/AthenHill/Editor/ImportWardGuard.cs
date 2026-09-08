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
    public static class ImportWardGuard
    {
        const string ModelPath = "Assets/AthenHill/Art/Imported/Meshy/ward-guard.glb";
        const string PrefabPath = "Assets/AthenHill/Prefabs/WardGuard.prefab";

        // Batch entry point opens the existing scene; no city reconstruction.
        public static void ImportAndBuild()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            Install();
            LinuxBuild.Development();
            File.Copy("Captures/linux-build.json", "Captures/ward-guard-development-build.json", true);
            LinuxBuild.Release();
            File.Copy("Captures/linux-build.json", "Captures/ward-guard-release-build.json", true);
        }

        [MenuItem("Athen Hill/Characters/Use supplied Ward Guard for talking NPCs")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play before importing NPCs.");
            var npcs = UnityEngine.Object.FindObjectsByType<NpcAgent>().OrderBy(n => n.name).ToArray();
            var expected = new[] { "npc_linn", "npc_mira", "npc_torr", "npc_vex" };
            if (!npcs.Select(n => n.name).SequenceEqual(expected)) throw new Exception("Expected the four existing talking NPCs.");
            var walkers = UnityEngine.Object.FindObjectsByType<AmbientWalker>();
            var walkerState = walkers.Select(w => new { w.name, actor = w.actor, mesh = w.actor.GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh }).ToArray();
            var player = UnityEngine.Object.FindAnyObjectByType<PlayerMotor>();
            var playerVisual = player.visual;

            Directory.CreateDirectory(Path.GetDirectoryName(ModelPath));
            File.Copy("../staging/ward-guard.glb", ModelPath, true);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(ModelPath);
            var settings = new SerializedObject(importer);
            var method = settings.FindProperty("importSettings.animationMethod");
            method.enumValueIndex = Array.IndexOf(method.enumNames, "Legacy");
            settings.ApplyModifiedPropertiesWithoutUndo();
            importer.SaveAndReimport();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            var clips = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<AnimationClip>().ToArray();
            foreach (var name in new[] { "idle", "walk", "run", "talk" })
                if (!clips.Any(c => c.name == name && c.legacy)) throw new Exception("Missing legacy state: " + name);

            var template = new GameObject("WardGuard");
            var rig = (GameObject)PrefabUtility.InstantiatePrefab(model);
            rig.transform.SetParent(template.transform, false);
            var actor = template.AddComponent<ActorAnimation>();
            actor.animationSource = rig.GetComponentInChildren<Animation>();
            actor.animationSource.playAutomatically = false;
            actor.idle = clips.Single(c => c.name == "idle");
            actor.walk = clips.Single(c => c.name == "walk");
            actor.run = clips.Single(c => c.name == "run");
            actor.talk = clips.Single(c => c.name == "talk");
            actor.idle.SampleAnimation(actor.animationSource.gameObject, .3f);
            var renderers = rig.GetComponentsInChildren<SkinnedMeshRenderer>();
            int triangles = renderers.Sum(r => r.sharedMesh.triangles.Length / 3);
            if (triangles <= 0 || renderers.Length != 1) throw new Exception("Guard import must contain one valid source mesh.");
            foreach (var r in renderers)
            {
                r.shadowCastingMode = ShadowCastingMode.On;
                r.receiveShadows = true;
                r.updateWhenOffscreen = true;
                if (!r.sharedMaterial || !r.sharedMaterial.shader || r.sharedMaterial.shader.name.Contains("Error")) throw new Exception("Guard material failed to import.");
                // glTF skins ignore the mesh node's scale; evaluate the actual bone/bind matrices.
                // BakeMesh's scale option is ambiguous for Meshy's centimetre armature parent.
                var mesh = r.sharedMesh;
                var matrices = r.bones.Select((bone, i) => template.transform.worldToLocalMatrix * bone.localToWorldMatrix * mesh.bindposes[i]).ToArray();
                var weights = mesh.boneWeights;
                var points = mesh.vertices.Select((v, i) => {
                    var w = weights[i];
                    return matrices[w.boneIndex0].MultiplyPoint3x4(v) * w.weight0
                        + matrices[w.boneIndex1].MultiplyPoint3x4(v) * w.weight1
                        + matrices[w.boneIndex2].MultiplyPoint3x4(v) * w.weight2
                        + matrices[w.boneIndex3].MultiplyPoint3x4(v) * w.weight3;
                }).ToArray();
                float low = points.Min(v => v.y), height = points.Max(v => v.y) - low;
                Debug.Log($"Guard skinned bounds: height={height}, low={low}, renderer scale={r.transform.lossyScale}");
                if (Mathf.Abs(height - 1.8f) > .03f || Mathf.Abs(low) > .03f) throw new Exception($"Guard pose has wrong height/origin: {height}/{low}");
            }
            var prefab = PrefabUtility.SaveAsPrefabAsset(template, PrefabPath);
            UnityEngine.Object.DestroyImmediate(template);

            foreach (var npc in npcs)
            {
                var oldActor = npc.actor;
                if (!oldActor) throw new Exception("Missing actor on " + npc.name);
                // Retain each NpcAgent/root so GameSession, dialogue and authored placement references survive.
                if (PrefabUtility.IsPartOfPrefabInstance(npc.gameObject))
                    PrefabUtility.UnpackPrefabInstance(PrefabUtility.GetOutermostPrefabInstanceRoot(npc.gameObject), PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                if (oldActor.gameObject == npc.gameObject)
                {
                    var visualRoots = oldActor.GetComponentsInChildren<SkinnedMeshRenderer>().Select(r => {
                        var t = r.transform;
                        while (t.parent != npc.transform && t.parent) t = t.parent;
                        return t.gameObject;
                    }).Distinct().ToArray();
                    if (visualRoots.Any(go => go == npc.gameObject)) throw new Exception("Unexpected NPC renderer on gameplay root.");
                    if (oldActor.animationSource && oldActor.animationSource.gameObject == npc.gameObject)
                        UnityEngine.Object.DestroyImmediate(oldActor.animationSource);
                    foreach (var go in visualRoots) UnityEngine.Object.DestroyImmediate(go);
                    UnityEngine.Object.DestroyImmediate(oldActor);
                }
                else UnityEngine.Object.DestroyImmediate(oldActor.gameObject);
                var replacement = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                replacement.transform.SetParent(npc.transform, false);
                npc.actor = replacement.GetComponent<ActorAnimation>();
                npc.actor.idle.SampleAnimation(npc.actor.animationSource.gameObject, .3f);
                EditorUtility.SetDirty(npc);
            }
            if (player.visual != playerVisual) throw new Exception("Player visual changed unexpectedly.");
            foreach (var before in walkerState)
            {
                var w = walkers.Single(x => x.name == before.name);
                if (w.actor != before.actor || w.actor.GetComponentInChildren<SkinnedMeshRenderer>().sharedMesh != before.mesh)
                    throw new Exception("Ambient walker changed unexpectedly.");
            }
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(npcs[0].gameObject.scene);
            EditorSceneManager.SaveOpenScenes();
            Directory.CreateDirectory("Captures");
            File.WriteAllText("Captures/ward-guard-import.json", JsonConvert.SerializeObject(new {
                model = ModelPath, triangles, npcs = npcs.Select(n => new { n.name, visual = n.actor.name }).ToArray(),
                ambientWalkers = walkerState.Select(w => w.name).ToArray(), player = playerVisual.name,
                animation = "Relaxed arms-down pose derived from supplied rig; no authored idle/talk motion in supplied GLB."
            }, Formatting.Indented));
        }
    }
}
