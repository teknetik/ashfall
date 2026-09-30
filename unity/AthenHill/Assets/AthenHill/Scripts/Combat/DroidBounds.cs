using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Animation envelope of a skinned feral droid: the skinned mesh sampled over every clip it plays, in the
 /// renderer's bounds space (its root bone). Used by the Editor tool that fits the prefab's culling bounds and by the
 /// test that proves the fitted bounds still cover the animation. Edit-time / tooling only (bakes meshes).
 public static class DroidBounds
 {
  public static IEnumerable<AnimationClip> Clips(FeralDroid d)=>new[]{d.idle,d.walk,d.run,d.attack,d.hit,d.death}.Where(c=>c).Distinct();
  public static Bounds Measure(GameObject instance,float samplesPerSecond=30)
  {
   var droid=instance.GetComponent<FeralDroid>();
   var smr=instance.GetComponentInChildren<SkinnedMeshRenderer>(true);
   if(!droid||!smr)throw new InvalidOperationException(instance.name+": no FeralDroid or skinned renderer.");
   var anim=droid.animationSource?droid.animationSource:instance.GetComponentInChildren<Animation>(true);
   if(!anim)throw new InvalidOperationException(instance.name+": no Animation to sample.");
   var space=smr.rootBone?smr.rootBone:smr.transform;
   var mesh=new Mesh();var verts=new List<Vector3>();
   var lo=new Vector3(float.MaxValue,float.MaxValue,float.MaxValue);var hi=-lo;
   try
   {
    foreach(var clip in Clips(droid))
    {
     int n=Mathf.Max(2,Mathf.CeilToInt(clip.length*samplesPerSecond));
     for(int i=0;i<=n;i++)
     {
      clip.SampleAnimation(anim.gameObject,clip.length*i/n);
      smr.BakeMesh(mesh,true);mesh.GetVertices(verts);
      var m=space.worldToLocalMatrix*smr.transform.localToWorldMatrix;
      foreach(var v in verts){var p=m.MultiplyPoint3x4(v);lo=Vector3.Min(lo,p);hi=Vector3.Max(hi,p);}
     }
    }
    if(droid.idle)droid.idle.SampleAnimation(anim.gameObject,0);
   }
   finally{UnityEngine.Object.DestroyImmediate(mesh);}
   if(lo.x>hi.x)throw new InvalidOperationException(instance.name+": no clips to measure.");
   var b=new Bounds();b.SetMinMax(lo,hi);return b;
  }
  /// True when every corner of inner lies inside outer.
  public static bool Covers(Bounds outer,Bounds inner)=>outer.Contains(inner.min)&&outer.Contains(inner.max);
 }
}
