using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    public static class ImportMeshyPlayer
    {
        const string ModelPath = "Assets/AthenHill/Art/Imported/Meshy/colonist.glb";
        const string PrefabPath = "Assets/AthenHill/Prefabs/MeshyPlayer.prefab";

        [MenuItem("Athen Hill/Characters/Use supplied Meshy player")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play before changing the player.");
            var player = UnityEngine.Object.FindAnyObjectByType<PlayerMotor>();
            if (!player) throw new Exception("Open the AthenHill scene first.");
            var importer = AssetImporter.GetAtPath(ModelPath);
            var settings = new SerializedObject(importer);
            var method = settings.FindProperty("importSettings.animationMethod");
            method.enumValueIndex = Array.IndexOf(method.enumNames, "Legacy");
            settings.ApplyModifiedPropertiesWithoutUndo();
            importer.SaveAndReimport();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            var clips = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<AnimationClip>().ToArray();
            foreach (var name in new[] { "idle", "walk", "run" })
                if (!clips.Any(c => c.name == name && c.legacy)) throw new Exception("Missing legacy clip: " + name);

            var root = new GameObject("MeshyPlayer");
            var rig = (GameObject)PrefabUtility.InstantiatePrefab(model);
            rig.transform.SetParent(root.transform, false);
            // Measure the animated standing pose (1.670 m), not the wider bind-pose bounds.
            rig.transform.localScale = Vector3.one * (1.8f / 1.6700f);
            rig.transform.localPosition = Vector3.zero;
            var actor = root.AddComponent<ActorAnimation>();
            actor.animationSource = rig.GetComponentInChildren<Animation>();
            actor.animationSource.playAutomatically = false;
            actor.idle = clips.Single(c => c.name == "idle");
            actor.walk = clips.Single(c => c.name == "walk");
            actor.run = clips.Single(c => c.name == "run");
            actor.talk = actor.idle; // Meshy supplied no talk or animated idle clip.
            actor.walkStrideSpeed = 1.6f;
            actor.runStrideSpeed = 3.5f;
            foreach (var renderer in rig.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                renderer.shadowCastingMode = ShadowCastingMode.On;
                renderer.receiveShadows = true;
                renderer.updateWhenOffscreen = true;
            }
            foreach (var t in root.GetComponentsInChildren<Transform>()) t.gameObject.layer = 8;
            actor.idle.SampleAnimation(actor.animationSource.gameObject, 0);
            PrefabUtility.SaveAsPrefabAssetAndConnect(root, PrefabPath, InteractionMode.AutomatedAction);
            var old = player.visual;
            root.transform.SetParent(player.transform, false);
            root.transform.localRotation = old.localRotation;
            player.enabled = true;
            player.visual = root.transform;
            player.actor = actor;
            UnityEngine.Object.DestroyImmediate(old.gameObject);
            EditorUtility.SetDirty(player);
            PrefabUtility.RecordPrefabInstancePropertyModifications(player);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(player.gameObject.scene);
            EditorSceneManager.SaveOpenScenes();
            Selection.activeGameObject = root;
            Debug.Log("Meshy player installed with idle, walking and running. Prior player prefab retained.");
        }
    }
}
