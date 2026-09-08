using System.Linq;
using UnityEngine;
namespace AthenHill
{
 // Called only by the opt-in development QA bridge, never in the game loop.
 public static class ActorDiagnostics
 {
  static float[] V(Vector3 p)=>new[]{p.x,p.y,p.z};
  public static object Snapshot()=>Object.FindObjectsByType<ActorAnimation>().Select(a=>{
   var skins=a.GetComponentsInChildren<SkinnedMeshRenderer>();
   var points=skins.SelectMany(s=>{var m=new Mesh();s.BakeMesh(m);var vs=m.vertices.Select(v=>s.transform.TransformPoint(v)).ToArray();Object.Destroy(m);return vs;}).ToArray();
   var anim=a.humanoidAnimator;
   return new{name=a.name,position=V(a.transform.position),a.CurrentClip,humanoid=anim&&anim.isHuman,normalizedTime=anim?anim.GetCurrentAnimatorStateInfo(0).normalizedTime:0,
    leftFoot=anim&&anim.isHuman?V(a.transform.InverseTransformPoint(anim.GetBoneTransform(HumanBodyBones.LeftFoot).position)):null,
    rightFoot=anim&&anim.isHuman?V(a.transform.InverseTransformPoint(anim.GetBoneTransform(HumanBodyBones.RightFoot).position)):null,
    meshLow=points.Length>0?points.Min(p=>p.y)-a.transform.position.y:0,meshHigh=points.Length>0?points.Max(p=>p.y)-a.transform.position.y:0,
    rendererLow=skins.Length>0?skins.Min(s=>s.bounds.min.y)-a.transform.position.y:0,
    rendererHigh=skins.Length>0?skins.Max(s=>s.bounds.max.y)-a.transform.position.y:0,
    rendererCount=skins.Length,triangles=skins.Sum(s=>s.sharedMesh.triangles.Length/3)};
  }).ToArray();
 }
}
