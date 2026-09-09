using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    // Saved diagnostic cameras. These do not change the gameplay camera or tree.
    public static class TreeReviewSetup
    {
        const string Evidence = "../evidence/quality/20260908/tree";
        static float[] V(Vector3 v) => new[] { v.x, v.y, v.z };

        [MenuItem("Athen Hill/Hero tree/Prepare native review cameras")]
        public static void Install()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (EditorApplication.isPlaying || scene.path != ImportBaseline.ScenePath)
                throw new InvalidOperationException("Open the saved city outside Play Mode.");
            if (!GameObject.Find("Ward oasis tree")) throw new InvalidOperationException("Install the tree audition first.");
            var root = GameObject.Find("Tree review cameras") ?? new GameObject("Tree review cameras");
            var names = new[] { "north", "east", "south", "west" };
            var positions = new[] { new Vector3(0, 3.15f, 4.8f), new Vector3(4.8f, 3.15f, 0), new Vector3(0, 3.15f, -4.8f), new Vector3(-4.8f, 3.15f, 0) };
            for (int i = 0; i < names.Length; i++)
                Add(root.transform, "cam_tree_root_" + names[i], positions[i], new Vector3(0, 2.3f, 0), 55);
            Add(root.transform, "cam_tree_bark_close", new Vector3(1.85f, 3.15f, 1.65f), new Vector3(.15f, 3.35f, 0), 50);
            Add(root.transform, "cam_tree_canopy_below", new Vector3(-5.4f, 3.15f, -1.3f), new Vector3(0, 10, 0), 65);
            Add(root.transform, "cam_tree_canopy_edge", new Vector3(11.6f, 5.8f, -7), new Vector3(5.7f, 10.3f, -2), 45);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "/review-cameras.json", JsonConvert.SerializeObject(new
            {
                savedUtc = DateTime.UtcNow.ToString("o"), scene = scene.path,
                cameras = root.GetComponentsInChildren<Camera>().Select(c => new { c.name, position = V(c.transform.position), rotation = V(c.transform.eulerAngles), c.fieldOfView, c.nearClipPlane, c.enabled }),
                limitation = "Static inspection cameras. Canopy edge is an elevated diagnostic; root and bark views use 1.65m eye height over the 1.50m hill. Native framing and moving traversal remain to be reviewed."
            }, Formatting.Indented));
        }

        static void Add(Transform root, string name, Vector3 position, Vector3 target, float fov)
        {
            if (root.Find(name)) return; // Keep reviewed pose adjustments on repeat.
            var camera = ImportBaseline.Camera(name, position, target, fov);
            camera.transform.SetParent(root, true);
            Undo.RegisterCreatedObjectUndo(camera.gameObject, "Prepare tree review camera");
        }
    }
}
