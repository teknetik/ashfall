using System.Linq;
using UnityEngine;
namespace AthenHill
{
 // Called only by the opt-in development QA bridge, never in the game loop.
 public static class ActorDiagnostics
 {
  static float[] V(Vector3 p)=>new[]{p.x,p.y,p.z};
  static Vector3[] WorldSkin(SkinnedMeshRenderer skin)
  {
   var source=skin.sharedMesh;
   // BakeMesh double-applies centimetre scaling on the legacy Meshy hierarchy.
   // Use the same bind-pose evaluation as the importer for readable source skins.
   if(source.isReadable && source.bindposes.Length==skin.bones.Length && source.boneWeights.Length==source.vertexCount)
   {
    var matrices=skin.bones.Select((bone,i)=>bone.localToWorldMatrix*source.bindposes[i]).ToArray();
    var vertices=source.vertices;var weights=source.boneWeights;
    return vertices.Select((v,i)=>{var w=weights[i];return
     matrices[w.boneIndex0].MultiplyPoint3x4(v)*w.weight0+
     matrices[w.boneIndex1].MultiplyPoint3x4(v)*w.weight1+
     matrices[w.boneIndex2].MultiplyPoint3x4(v)*w.weight2+
     matrices[w.boneIndex3].MultiplyPoint3x4(v)*w.weight3;}).ToArray();
   }
   var baked=new Mesh();skin.BakeMesh(baked);
   var points=baked.vertices.Select(skin.transform.TransformPoint).ToArray();Object.Destroy(baked);return points;
  }
  public static object Snapshot()=>Object.FindObjectsByType<ActorAnimation>().Select(a=>{
   var skins=a.GetComponentsInChildren<SkinnedMeshRenderer>();
   var points=skins.SelectMany(WorldSkin).ToArray();
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
