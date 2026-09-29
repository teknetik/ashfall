#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Read-only geometry report for task t_196932d9: where is the existing Basic General sign and what is around it.
    public static class BasicGeneralSignReport
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        static float[] A(Vector3 v) => new[] { v.x, v.y, v.z };
        public static void RunBatch()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var chunks = Object.FindAnyObjectByType<StaticRenderChunks>();
            var frontage = GameObject.Find("Basic General authored frontage");
            var all = frontage.GetComponentsInChildren<MeshRenderer>(true);
            var sign = all.Where(r => r.name == "BASIC_GENERAL_sign").ToArray();
            var sb = sign[0].bounds;
            var near = all.Where(r => r.name != "BASIC_GENERAL_sign" && r.bounds.Intersects(new Bounds(sb.center, sb.size + new Vector3(1.2f, 1.2f, 1.2f))))
                .Select(r => new { r.name, enabled = r.enabled, center = A(r.bounds.center), size = A(r.bounds.size), mats = r.sharedMaterials.Select(m => m ? m.name : "null").ToArray() }).ToArray();
            var report = new
            {
                frontagePos = A(frontage.transform.position), frontageEuler = A(frontage.transform.eulerAngles), frontageScale = A(frontage.transform.lossyScale),
                signs = sign.Select(r => new { path = r.transform.parent.name + "/" + r.name, enabled = r.enabled, center = A(r.bounds.center), size = A(r.bounds.size), mats = r.sharedMaterials.Select(m => m.name).ToArray(), forward = A(r.transform.forward), up = A(r.transform.up), sharedShader = r.sharedMaterial.shader.name }).ToArray(),
                near,
                chunkSourceRoots = chunks.sourceRoots.Select(t => t ? t.name : "null").ToArray(), editingSources = chunks.editingSources,
                sunDir = A(Object.FindObjectsByType<Light>(FindObjectsInactive.Exclude).Where(l => l.type == LightType.Directional).Select(l => l.transform.forward).FirstOrDefault()),
                counterInstance = GameObject.Find("Basic General counter dressing") != null,
                miraRoots = Object.FindObjectsByType<NpcAgent>().Select(n => new { n.name, p = A(n.transform.position) }).ToArray()
            };
            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../evidence/basic-general-sign/20260929"));
            File.WriteAllText(Path.Combine(dir, "sign-placement-report.json"), JsonConvert.SerializeObject(report, Formatting.Indented));
            Debug.Log("SignReport done");
        }
    }
}
#endif
