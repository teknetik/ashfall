using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Editor
{
 /// Realistic culling bounds for the feral worker droid (and so its Foreman variant). The imported Meshy rig carried a
 /// hand-set 450 × 180 × 450 local AABB (centimetre root-bone space), so the droids were never culled: always skinned,
 /// animated and drawn into every shadow cascade. This measures the skinned mesh over every clip the droid plays
 /// (idle, walk, run, attack, hit, death) in root-bone space, adds a margin, writes it to the prefab and sets the
 /// legacy Animation to animate only while its renderers are visible (FeralDroid switches to AlwaysAnimate once
 /// engaged). Batch: -executeMethod AthenHill.Editor.DroidRenderBounds.ApplyBatch (logs DROID_BOUNDS {…}, exits 0/1).
 public static class DroidRenderBounds
 {
  public const string WorkerPrefab="Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab";
  /// Extra room beyond the measured animation envelope (fraction of each extent), for blending between clips.
  public const float Margin=.12f;
  public static IEnumerable<AnimationClip> Clips(FeralDroid d)=>DroidBounds.Clips(d);
  public static Bounds Measure(GameObject instance,float samplesPerSecond=30)=>DroidBounds.Measure(instance,samplesPerSecond);
  public static Bounds WithMargin(Bounds b)=>new Bounds(b.center,b.size*(1+2*Margin));

  [MenuItem("Athen Hill/Performance/Fit feral droid culling bounds")]
  public static void ApplyMenu()=>Debug.Log("DROID_BOUNDS "+JsonConvert.SerializeObject(Apply()));
  public static void ApplyBatch()
  {
   int code=0;
   try{Debug.Log("DROID_BOUNDS "+JsonConvert.SerializeObject(Apply()));}
   catch(Exception e){code=1;Debug.LogWarning("DROID_BOUNDS "+JsonConvert.SerializeObject(new{ok=false,error=e.Message}));}
   EditorApplication.Exit(code);
  }
  public static Dictionary<string,object> Apply()
  {
   // Measure on a throwaway instance: sampling clips moves bones, and the prefab's bone poses must not change.
   var probe=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(WorkerPrefab));
   Bounds envelope;
   try{probe.transform.SetPositionAndRotation(Vector3.zero,Quaternion.identity);envelope=Measure(probe);}
   finally{UnityEngine.Object.DestroyImmediate(probe);}
   var fitted=WithMargin(envelope);
   var root=PrefabUtility.LoadPrefabContents(WorkerPrefab);
   try
   {
    var smr=root.GetComponentInChildren<SkinnedMeshRenderer>(true);var droid=root.GetComponent<FeralDroid>();
    var before=smr.localBounds;
    smr.localBounds=fitted;smr.updateWhenOffscreen=false;
    if(droid.animationSource)droid.animationSource.cullingType=AnimationCullingType.BasedOnRenderers;
    PrefabUtility.SaveAsPrefabAsset(root,WorkerPrefab);
    var space=smr.rootBone?smr.rootBone:smr.transform;
    return new Dictionary<string,object>{{"ok",true},{"prefab",WorkerPrefab},{"space",space.name},
     {"before",new{center=V(before.center),extents=V(before.extents)}},{"envelope",new{center=V(envelope.center),extents=V(envelope.extents)}},
     {"fitted",new{center=V(fitted.center),extents=V(fitted.extents)}},{"clips",Clips(droid).Select(c=>c.name).ToArray()},{"animationCulling","BasedOnRenderers"}};
   }
   finally{PrefabUtility.UnloadPrefabContents(root);}
  }
  static float[] V(Vector3 v)=>new[]{(float)Math.Round(v.x,2),(float)Math.Round(v.y,2),(float)Math.Round(v.z,2)};
 }
}
