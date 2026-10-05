using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object=UnityEngine.Object;
namespace AthenHill.Editor
{
 // Scoped inspection/capture for the 5 October player pass. Does not reconstruct or save the scene.
 public static class CharacterPolish20261005
 {
  public const string Model="Assets/AthenHill/Art/Imported/Meshy/colonist.glb";
  static string Out=>Path.GetFullPath("../../art/character_polish_20261005/unity");
  static Transform Bone(ActorAnimation a,string n)=>a.animationSource.GetComponentsInChildren<Transform>(true).Single(t=>t.name==n);
  public static float Sole(ActorAnimation a)
  {
   var s=a.animationSource.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(x=>x.sharedMesh.vertexCount).First();
   var m=s.sharedMesh;var mats=s.bones.Select((b,i)=>a.transform.worldToLocalMatrix*b.localToWorldMatrix*m.bindposes[i]).ToArray();
   var vs=m.vertices;var ws=m.boneWeights;float low=float.MaxValue;
   for(int i=0;i<vs.Length;i++){var w=ws[i];var p=mats[w.boneIndex0].MultiplyPoint3x4(vs[i])*w.weight0+mats[w.boneIndex1].MultiplyPoint3x4(vs[i])*w.weight1+mats[w.boneIndex2].MultiplyPoint3x4(vs[i])*w.weight2+mats[w.boneIndex3].MultiplyPoint3x4(vs[i])*w.weight3;low=Mathf.Min(low,p.y);}
   return low;
  }
  public static Vector3 ShoulderDirection(ActorAnimation a,string side)=>Bone(a,"Spine").InverseTransformDirection(Bone(a,side+"Arm").position-Bone(a,side+"Shoulder").position).normalized;
  static float[] V(Vector3 v)=>new[]{v.x,v.y,v.z};
  public static object Audit(ActorAnimation actor)
  {
   var result=new List<object>();
   foreach(var clip in new[]{actor.idle,actor.walk,actor.run})
   {
    if(!clip)throw new InvalidOperationException("Missing player clip");
    var frames=new List<object>();
    for(int i=0;i<=32;i++)
    {
     float t=clip.length*i/32;clip.SampleAnimation(actor.animationSource.gameObject,t);
     frames.Add(new{time=t,sole=Sole(actor),left=V(ShoulderDirection(actor,"Left")),right=V(ShoulderDirection(actor,"Right")),hip=V(actor.transform.InverseTransformPoint(Bone(actor,"Hips").position))});
    }
    result.Add(new{clip=clip.name,path=AssetDatabase.GetAssetPath(clip),clip.length,frames});
   }
   return result;
  }
  public static void RunBatch()
  {
   try
   {
    Directory.CreateDirectory(Out);EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity",OpenSceneMode.Single);
    var motor=Object.FindAnyObjectByType<PlayerMotor>();var actor=motor.actor;
    var skin=actor.animationSource.GetComponentsInChildren<SkinnedMeshRenderer>(true).OrderByDescending(s=>s.sharedMesh.vertexCount).First();
    if(skin.sharedMaterials.Length!=skin.sharedMesh.subMeshCount||skin.sharedMaterials.Any(m=>!m))throw new InvalidOperationException("Missing material slot after import");
    var report=new{mesh=skin.sharedMesh.name,triangles=skin.sharedMesh.triangles.Length/3,bones=skin.bones.Length,materials=skin.sharedMaterials.Select(m=>new{m.name,shader=m.shader.name}),motor.walkSpeed,motor.runSpeed,actor.walkStrideSpeed,actor.runStrideSpeed,clips=Audit(actor)};
    File.WriteAllText(Path.Combine(Out,"audit.json"),JsonConvert.SerializeObject(report,Formatting.Indented));
    // The older checker writes its dated report; preserve that historical evidence when reusing it here.
    var historical=Path.GetFullPath("../evidence/next-level/20261002/character/check.json");
    var previous=File.Exists(historical)?File.ReadAllBytes(historical):null;
    try {var check=MainCharacterInstall.Check();File.WriteAllText(Path.Combine(Out,"integration-check.json"),check);}
    finally {if(previous!=null)File.WriteAllBytes(historical,previous);else if(File.Exists(historical))File.Delete(historical);}
    if(Environment.GetCommandLineArgs().Contains("--capture"))Capture(motor);
    EditorApplication.Exit(0);
   }
   catch(Exception e){Debug.LogException(e);EditorApplication.Exit(1);}
  }
  static void Capture(PlayerMotor motor)
  {
   var actor=motor.actor;var combat=motor.GetComponent<PlayerCombat>();var vis=motor.GetComponent<PlayerArmourVisuals>();
   foreach(var piece in vis.pieces)if(piece.model)piece.model.SetActive(piece.itemId=="field_vest"||piece.itemId=="field_boots");
   combat.heldPistol.SetActive(false);combat.heldRifle.SetActive(false);
   if(combat.muzzleLight)combat.muzzleLight.enabled=false;
   var feet=RifleArmourInstall.Stand;if(Physics.Raycast(feet+Vector3.up*6,Vector3.down,out var hit,30,~(1<<8),QueryTriggerInteraction.Ignore))feet.y=hit.point.y;
   motor.transform.position=feet+Vector3.up*.015f;motor.visual.rotation=Quaternion.LookRotation(Vector3.left);
   foreach(var s in motor.visual.GetComponentsInChildren<SkinnedMeshRenderer>(true))s.forceMatrixRecalculationPerRender=true;
   string Spec(string n,bool back=false){var p=feet+new Vector3(back?2.7f:-2.7f,1.3f,back?-1.1f:1.1f);var t=feet+Vector3.up*.95f;return string.Format(CultureInfo.InvariantCulture,"{0}:{1},{2},{3}:{4},{5},{6}:36",n,p.x,p.y,p.z,t.x,t.y,t.z);}
   actor.idle.SampleAnimation(actor.animationSource.gameObject,.4f);DuskStartPass.Preview(13,Out,Spec("warm"));
   DuskStartPass.Preview(13,Out,Spec("idle_front"),Spec("idle_back",true));
   for(int i=0;i<4;i++){actor.walk.SampleAnimation(actor.animationSource.gameObject,actor.walk.length*i/4);DuskStartPass.Preview(13,Out,Spec("walk_"+i));}
  }
 }
}
