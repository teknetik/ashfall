using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // 27 Sep 2026 pm, request #2 follow-up: Warden Rell's feet float ~56 mm above the ground in the saved scene
    // (requests-1-5-verify.json). Moves only each Warden's visual child vertically so the lowest skinned vertex over the
    // idle cycle sits 3 mm into the ground; the gameplay root (interaction, look-at, colliders) is not moved.
    public static class WardenGroundFix
    {
        const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";
        const float Target=-.003f,Tolerance=.012f;

        [MenuItem("Athen Hill/Characters/Ground Wardens (visual only)")]
        public static void Run()
        {
            if(EditorSceneManager.GetActiveScene().path!=Scene)EditorSceneManager.OpenScene(Scene);
            var log=new StringBuilder();bool changed=false;
            foreach(var n in new[]{"Warden Ossa","Warden Rell"})
            {
                var root=Object.FindObjectsByType<Transform>(FindObjectsInactive.Include).FirstOrDefault(t=>t.name==n);
                if(!root){log.AppendLine(n+": not found");continue;}
                var skins=root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                if(skins.Length==0){log.AppendLine(n+": no skin");continue;}
                var actor=root.GetComponentInChildren<ActorAnimation>(true);
                float lowest=float.MaxValue;Vector3 at=Vector3.zero;var mesh=new Mesh();
                for(int i=0;i<8;i++)
                {
                    if(actor&&actor.idle&&actor.animationSource)actor.idle.SampleAnimation(actor.animationSource.gameObject,actor.idle.length*i/8f);
                    foreach(var s in skins){s.BakeMesh(mesh,true);var m=s.transform.localToWorldMatrix;foreach(var v in mesh.vertices){var w=m.MultiplyPoint3x4(v);if(w.y<lowest){lowest=w.y;at=w;}}}
                }
                var hits=Physics.RaycastAll(at+Vector3.up*3,Vector3.down,20,~0,QueryTriggerInteraction.Ignore).Where(h=>!h.transform.IsChildOf(root)).OrderBy(h=>h.distance).ToArray();
                if(hits.Length==0){log.AppendLine(n+": no ground");continue;}
                float delta=lowest-hits[0].point.y;
                // the visual child that carries the skinned model (direct child of the root)
                var visual=skins[0].transform;while(visual.parent&&visual.parent!=root)visual=visual.parent;
                if(Mathf.Abs(delta-Target)<=Tolerance){log.AppendLine($"{n}: {delta*1000:F1} mm, within tolerance, unchanged");continue;}
                Undo.RecordObject(visual,"Ground Warden");
                float before=visual.localPosition.y;
                visual.position+=Vector3.up*(Target-delta);
                EditorUtility.SetDirty(visual);changed=true;
                log.AppendLine($"{n}: {delta*1000:F1} mm -> {Target*1000:F1} mm; {visual.name} localY {before:F3} -> {visual.localPosition.y:F3}");
            }
            if(changed){EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());}
            var outp=Path.GetFullPath("../../unity/evidence/character-feel/20260927-pm/warden-ground-fix.txt");
            File.WriteAllText(outp,log.ToString());
            Debug.Log("WardenGroundFix\n"+log);
        }

        /// Batch entry: ground the Wardens, then FPGripPass.FinalAndBuild (install hands, render, verify #1-5, builds).
        public static void RunThenFinalAndBuild(){Run();FPGripPass.FinalAndBuild();}
    }
}
