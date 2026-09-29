#if UNITY_EDITOR
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Read-only listing of the existing Basic General sign group for task t_196932d9.
    public static class BasicGeneralSignReport2
    {
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        public static void RunBatch()
        {
            EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity", OpenSceneMode.Single);
            var frontage = GameObject.Find("Basic General authored frontage");
            var rows = frontage.GetComponentsInChildren<MeshRenderer>(true)
                .Where(r => { var b = r.bounds; return b.center.y > 2.3f && b.center.y < 3.5f && b.center.z > 16.5f && b.center.z < 17.2f; })
                .Select(r => new { path = r.transform.parent.name + "/" + r.name, tris = r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3, center = A(r.bounds.center), size = A(r.bounds.size), mats = r.sharedMaterials.Select(m => m.name).ToArray() }).ToArray();
            var others = Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include).Where(r => r.name.ToLower().Contains("open") && r.bounds.center.z > 15 && r.bounds.center.z < 18 && Mathf.Abs(r.bounds.center.x - 8) < 4).Select(r => new { r.name, center = A(r.bounds.center), size = A(r.bounds.size) }).ToArray();
            File.WriteAllText(Path.GetFullPath(Path.Combine(Application.dataPath, "../../evidence/basic-general-sign/20260929/sign-group-report.json")), JsonConvert.SerializeObject(new { rows, others }, Formatting.Indented));
        }
    }
}
#endif
