using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>
    /// Walking mining droid (Meshy source meshy/mining-droid-20260926, rig art/ward_retrofit_20260926/rig_droid.py).
    /// Imports MiningDroid.glb with legacy clips, saves Prefabs/WardMiningDroid.prefab (ActorAnimation + kinematic
    /// collider) and places one instance on an AmbientWalker patrol loop through the aquifer pump station yard.
    /// Uses the same actor/walker components as the existing ambient walkers; no other scene objects change.
    /// </summary>
    public static class WardMiningDroidPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string ModelPath = "Assets/AthenHill/Art/WardRetrofit/MiningDroid.glb";
        const string PrefabPath = "Assets/AthenHill/Prefabs/WardMiningDroid.prefab";
        const string RootName = "Ward mining droid";
        const string RouteName = "Mining droid route";
        const string Evidence = "../evidence/district-retrofit/20260926/";
        static readonly Vector3[] Route = { new Vector3(-46f, 0, -28f), new Vector3(-32f, 0, -28f), new Vector3(-32f, 0, -22f), new Vector3(-46f, 0, -22f) };
        const float PatrolSpeed = 1.1f, StrideSpeed = 1.51f;   // stride speed from mining-droid-rig.json

        [MenuItem("Athen Hill/District/Install walking mining droid")]
        public static void InstallMenu()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (scene.GetRootGameObjects().Any(g => g.name == RootName))
                throw new InvalidOperationException("The mining droid is already installed; edit its prefab or route instead.");
            Install(scene);
        }

        /// Batch entry point during authoring; replaces only this pass's own droid and route.
        public static void RunAll()
        {
            AssetDatabase.Refresh();
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == RootName || g.name == RouteName).ToArray())
                UnityEngine.Object.DestroyImmediate(old);
            Install(scene);
        }

        static void Install(Scene scene)
        {
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(ModelPath) ?? throw new InvalidOperationException("Missing " + ModelPath + " (run rig_droid.py).");
            var settings = new SerializedObject(importer);
            var method = settings.FindProperty("importSettings.animationMethod");
            if (method.enumNames[method.enumValueIndex] != "Legacy")
            {
                method.enumValueIndex = Array.IndexOf(method.enumNames, "Legacy");
                settings.ApplyModifiedPropertiesWithoutUndo();
                importer.SaveAndReimport();
            }
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            var clips = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<AnimationClip>().ToArray();
            foreach (var name in new[] { "idle", "walk" })
                if (!clips.Any(c => c.name == name && c.legacy)) throw new InvalidOperationException("Missing legacy clip: " + name);

            var template = new GameObject("WardMiningDroid");
            var rig = (GameObject)PrefabUtility.InstantiatePrefab(model);
            rig.transform.SetParent(template.transform, false);
            var actor = template.AddComponent<ActorAnimation>();
            actor.animationSource = rig.GetComponentInChildren<Animation>();
            actor.animationSource.playAutomatically = false;
            actor.idle = clips.Single(c => c.name == "idle");
            actor.walk = clips.Single(c => c.name == "walk");
            actor.run = actor.walk;
            actor.walkStrideSpeed = StrideSpeed; actor.runStrideSpeed = StrideSpeed;
            actor.idle.SampleAnimation(actor.animationSource.gameObject, 0);
            var renderers = rig.GetComponentsInChildren<SkinnedMeshRenderer>();
            if (renderers.Length != 1 || renderers[0].sharedMesh.triangles.Length == 0) throw new InvalidOperationException("Droid import must contain one skinned mesh.");
            foreach (var r in renderers)
            {
                r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true;
                r.updateWhenOffscreen = false;
                r.localBounds = new Bounds(r.localBounds.center, r.localBounds.size + Vector3.one * .6f);   // room for leg swing
                if (!r.sharedMaterial || r.sharedMaterial.shader.name.Contains("Error")) throw new InvalidOperationException("Droid material failed to import.");
            }
            // moving obstacle for the player's CharacterController
            var body = template.AddComponent<BoxCollider>();
            body.center = new Vector3(0, 1.9f, 0); body.size = new Vector3(1.8f, 1.6f, 3.3f);
            var rb = template.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false;
            int triangles = renderers.Sum(r => r.sharedMesh.triangles.Length / 3), bones = renderers[0].bones.Length;
            var prefab = PrefabUtility.SaveAsPrefabAsset(template, PrefabPath);
            UnityEngine.Object.DestroyImmediate(template);

            var route = new GameObject(RouteName);
            SceneManager.MoveGameObjectToScene(route, scene);
            var points = Route.Select((p, i) =>
            {
                var w = new GameObject("Droid waypoint " + i).transform;
                w.SetParent(route.transform, false); w.position = p;
                return w;
            }).ToArray();
            var droid = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            droid.name = RootName;
            droid.transform.position = Route[0];
            droid.transform.rotation = Quaternion.LookRotation(Route[1] - Route[0]);
            var walker = droid.AddComponent<AmbientWalker>();
            walker.waypoints = points; walker.speed = PatrolSpeed; walker.phase = .1f; walker.turnLookAhead = .9f; walker.turnSharpness = 2.5f;
            walker.actor = droid.GetComponent<ActorAnimation>();

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "mining-droid.json", JsonConvert.SerializeObject(new
            {
                model = ModelPath, prefab = PrefabPath, clips = clips.Select(c => new { c.name, c.length, c.legacy }),
                triangles, bones,
                route = Route.Select(p => new[] { p.x, p.z }), speed = PatrolSpeed, strideSpeed = StrideSpeed
            }, Formatting.Indented));
        }
    }
}
