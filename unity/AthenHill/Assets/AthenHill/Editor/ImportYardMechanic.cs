using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 public static class ImportYardMechanic
 {
  const string Folder=ImportDistrictAssets.Folder+"/mechanic";
  public const string PrefabPath="Assets/AthenHill/Prefabs/YardMechanic.prefab";
  public static void Install()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   if(GameObject.Find("npc_yard_mechanic"))throw new Exception("The yard mechanic is already installed.");
   string gameplay=DistrictCityPass.GameplaySignature();Directory.CreateDirectory(Folder);
   const string source="../../meshy/district-20260908/mechanic";
   foreach(var name in new[]{"rigged","walk","run"})File.Copy(source+"/"+name+".fbx",Folder+"/"+name+".fbx",true);
   foreach(var file in Directory.GetFiles(source+"/mechanic_textures","*.png"))File.Copy(file,Folder+"/"+Path.GetFileName(file),true);
   AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
   var rigImporter=(ModelImporter)AssetImporter.GetAtPath(Folder+"/rigged.fbx");Configure(rigImporter);rigImporter.importAnimation=false;rigImporter.avatarSetup=ModelImporterAvatarSetup.CreateFromThisModel;rigImporter.SaveAndReimport();
   var avatar=AssetDatabase.LoadAllAssetsAtPath(Folder+"/rigged.fbx").OfType<Avatar>().FirstOrDefault();
   if(!avatar||!avatar.isValid||!avatar.isHuman)throw new Exception("Meshy rig did not produce a valid Unity Humanoid Avatar.");
   var walk=Clip("walk",avatar);var run=Clip("run",avatar);var material=ImportDistrictAssets.MaterialFor("mechanic");
   string controllerPath=Folder+"/YardMechanic.controller";var controller=AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
   if(!controller)controller=AnimatorController.CreateAnimatorControllerAtPath(controllerPath);
   var machine=controller.layers[0].stateMachine;foreach(var s in machine.states)machine.RemoveState(s.state);
   var idle=machine.AddState("idle");idle.motion=walk;idle.speed=0;machine.defaultState=idle;
   machine.AddState("walk").motion=walk;machine.AddState("run").motion=run;EditorUtility.SetDirty(controller);
   var root=new GameObject("YardMechanic");var rig=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Folder+"/rigged.fbx"));rig.transform.SetParent(root.transform,false);
   var animator=rig.GetComponent<Animator>();if(!animator)animator=rig.AddComponent<Animator>();animator.avatar=avatar;animator.runtimeAnimatorController=controller;animator.applyRootMotion=false;animator.cullingMode=AnimatorCullingMode.AlwaysAnimate;
   var actor=root.AddComponent<ActorAnimation>();actor.humanoidAnimator=animator;actor.walk=actor.idle=actor.talk=walk;actor.run=run;actor.walkStrideSpeed=1.25f;actor.runStrideSpeed=3.2f;
   var skins=rig.GetComponentsInChildren<SkinnedMeshRenderer>();int triangles=skins.Sum(s=>s.sharedMesh.triangles.Length/3);int boneCount=skins.Sum(s=>s.bones.Length);
   if(triangles>7000||skins.Length!=1)throw new Exception("Mechanic mesh exceeds its actor budget.");
   var points=SkinPoints(skins[0],root.transform);float low=points.Min(v=>v.y),height=points.Max(v=>v.y)-low;float scale=1.72f/height;
   rig.transform.localScale*=scale;rig.transform.localPosition=Vector3.up*(-low*scale+.02f);
   foreach(var s in skins){s.sharedMaterial=material;s.shadowCastingMode=ShadowCastingMode.On;s.receiveShadows=true;s.updateWhenOffscreen=true;}
   animator.Rebind();animator.Update(0);var samples=new List<object>();var feet=new List<Vector3>();
   for(int i=0;i<16;i++)
   {
    animator.Play("walk",0,i/16f);animator.Update(0);var p=SkinPoints(skins[0],root.transform);var foot=root.transform.InverseTransformPoint(animator.GetBoneTransform(HumanBodyBones.LeftFoot).position);feet.Add(foot);
    samples.Add(new{frame=i,low=p.Min(v=>v.y),height=p.Max(v=>v.y)-p.Min(v=>v.y),foot=new[]{foot.x,foot.y,foot.z}});
   }
   if(feet.Max(p=>Vector3.Distance(p,feet[0]))<.05f)throw new Exception("Humanoid walk has no leg motion.");
   animator.Play("idle",0,0);animator.Update(0);
   var prefab=PrefabUtility.SaveAsPrefabAsset(root,PrefabPath);UnityEngine.Object.DestroyImmediate(root);
   var npc=(GameObject)PrefabUtility.InstantiatePrefab(prefab);npc.name="npc_yard_mechanic";npc.transform.position=new Vector3(34,0,-16);
   var route=new GameObject("Yard mechanic route").transform;var positions=new[]{new Vector3(34,0,-16),new Vector3(38,0,-16),new Vector3(38,0,-12),new Vector3(34,0,-12)};
   var walker=npc.AddComponent<AmbientWalker>();walker.actor=npc.GetComponent<ActorAnimation>();walker.speed=.85f;walker.phase=.1f;
   walker.waypoints=positions.Select((p,i)=>{var t=new GameObject("Mechanic waypoint "+i).transform;t.SetParent(route,false);t.position=p;return t;}).ToArray();
   if(DistrictCityPass.GameplaySignature()!=gameplay)throw new Exception("An existing actor or route was modified.");
   DistrictCityPass.Camera("cam_district_mechanic",new Vector3(40,2.6f,-11),new Vector3(35.5f,1,-14.5f),43);
   AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(npc.scene);EditorSceneManager.SaveScene(npc.scene,ImportBaseline.ScenePath);
   File.WriteAllText(DistrictCityPass.Evidence+"/mechanic-import.json",JsonConvert.SerializeObject(new{avatarValid=avatar.isValid,avatarHuman=avatar.isHuman,triangles,heightMeters=1.72,walkLength=walk.length,runLength=run.length,boneCount,walkSamples=samples,existingGameplayPreserved=true,route=positions.Select(p=>new[]{p.x,p.y,p.z})},Formatting.Indented));
  }
  static void Configure(ModelImporter i){i.animationType=ModelImporterAnimationType.Human;i.importCameras=false;i.importLights=false;i.materialImportMode=ModelImporterMaterialImportMode.None;i.isReadable=true;i.optimizeGameObjects=false;i.animationCompression=ModelImporterAnimationCompression.Off;}
  static AnimationClip Clip(string name,Avatar avatar)
  {
   var path=Folder+"/"+name+".fbx";var i=(ModelImporter)AssetImporter.GetAtPath(path);Configure(i);i.importAnimation=true;i.avatarSetup=ModelImporterAvatarSetup.CopyFromOther;i.sourceAvatar=avatar;i.SaveAndReimport();
   var clips=i.defaultClipAnimations;if(clips.Length!=1)throw new Exception("Expected one Meshy "+name+" animation.");clips[0].name=name;clips[0].loopTime=true;clips[0].loopPose=true;clips[0].lockRootRotation=true;clips[0].lockRootHeightY=true;clips[0].lockRootPositionXZ=false;i.clipAnimations=clips;i.SaveAndReimport();
   return AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Single(c=>c.name==name);
  }
  static Vector3[] SkinPoints(SkinnedMeshRenderer r,Transform root)
  {
   var mesh=r.sharedMesh;var matrices=r.bones.Select((b,i)=>root.worldToLocalMatrix*b.localToWorldMatrix*mesh.bindposes[i]).ToArray();var ws=mesh.boneWeights;
   return mesh.vertices.Select((v,i)=>{var w=ws[i];return matrices[w.boneIndex0].MultiplyPoint3x4(v)*w.weight0+matrices[w.boneIndex1].MultiplyPoint3x4(v)*w.weight1+matrices[w.boneIndex2].MultiplyPoint3x4(v)*w.weight2+matrices[w.boneIndex3].MultiplyPoint3x4(v)*w.weight3;}).ToArray();
  }
 }
}
