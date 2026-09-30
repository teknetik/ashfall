using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Object=UnityEngine.Object;
namespace AthenHill.Editor
{
 /// One-time installer for the field pack's colonist view (30 Sep 2026): adds the CharacterPreview layer and a
 /// "Character preview" rig — a disabled camera with three studio lights as its children — to the open city scene,
 /// and points CityHud at it. An existing rig is only re-wired, never replaced, so Inspector tuning survives.
 public static class CharacterPreviewInstaller
 {
  public const string LayerName="CharacterPreview";
  public const int PreferredLayer=10;

  [MenuItem("Athen Hill/UI/Install field-pack colonist view")]
  public static void Install()
  {
   if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play before installing.");
   int layer=EnsureLayer(LayerName,PreferredLayer);
   var preview=Object.FindAnyObjectByType<CharacterPreview>(FindObjectsInactive.Include);
   if(!preview)preview=Create(layer);
   Wire(preview,layer);
   EditorSceneManager.MarkSceneDirty(preview.gameObject.scene);
   Debug.Log($"Field-pack colonist view ready: {preview.name} on layer {layer} ({LayerName}).");
  }
  /// Batch entry: open the city scene, install, save.
  public static void InstallBatch()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   Install();
   EditorSceneManager.SaveOpenScenes();
  }

  static CharacterPreview Create(int layer)
  {
   var root=new GameObject("Character preview");
   Undo.RegisterCreatedObjectUndo(root,"Install field-pack colonist view");
   var preview=root.AddComponent<CharacterPreview>();
   var camGo=new GameObject("Preview camera");camGo.transform.SetParent(root.transform,false);
   var cam=camGo.AddComponent<Camera>();
   cam.enabled=false;cam.cullingMask=1<<layer;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(0,0,0,0);
   cam.fieldOfView=preview.fieldOfView;cam.nearClipPlane=.3f;cam.farClipPlane=20;cam.allowHDR=false;cam.allowMSAA=true;cam.depth=-20;
   var data=camGo.AddComponent<UniversalAdditionalCameraData>();
   data.renderPostProcessing=false;data.antialiasing=AntialiasingMode.None;data.volumeLayerMask=0;data.renderShadows=true;
   data.requiresColorOption=CameraOverrideOption.Off;data.requiresDepthOption=CameraOverrideOption.Off;
   // Studio lights ride with the camera, so the colonist is lit the same way from whichever side it is viewed.
   // The camera looks down +Z at the colonist about Distance metres ahead.
   // Intensities from the Editor audition of 30 Sep 2026 (evidence/ui/20260930-pack-ark/audition).
   var subject=new Vector3(0,-.1f,preview.distance);
   var key=Studio(camGo.transform,"Key light",LightType.Spot,new Vector3(-2.3f,1.7f,2.3f),subject,new Color(1f,.95f,.87f),26f,11f,42f,layer,true);
   var fill=Studio(camGo.transform,"Fill light",LightType.Point,new Vector3(2.6f,.4f,1.6f),subject,new Color(.72f,.83f,1f),7f,11f,0,layer,false);
   var rim=Studio(camGo.transform,"Rim light",LightType.Spot,new Vector3(1.6f,2.3f,preview.distance+2.8f),new Vector3(0,.1f,preview.distance),new Color(.55f,.9f,1f),5f,9f,48f,layer,false);
   preview.previewCamera=cam;preview.studioLights=new[]{key,fill,rim};
   return preview;
  }
  static Light Studio(Transform parent,string name,LightType type,Vector3 local,Vector3 target,Color color,float intensity,float range,float angle,int layer,bool shadows)
  {
   var go=new GameObject(name);go.transform.SetParent(parent,false);
   go.transform.localPosition=local;go.transform.localRotation=Quaternion.LookRotation(target-local,Vector3.up);
   var l=go.AddComponent<Light>();
   l.type=type;l.color=color;l.intensity=intensity;l.range=range;l.cullingMask=1<<layer;l.enabled=false;
   if(type==LightType.Spot){l.spotAngle=angle;l.innerSpotAngle=angle*.55f;}
   l.shadows=shadows?LightShadows.Soft:LightShadows.None;l.shadowStrength=.7f;l.renderMode=LightRenderMode.ForcePixel;
   l.lightmapBakeType=LightmapBakeType.Realtime;
   return l;
  }
  static void Wire(CharacterPreview preview,int layer)
  {
   Undo.RecordObject(preview,"Wire field-pack colonist view");
   preview.previewLayer=layer;
   if(!preview.player)preview.player=Object.FindAnyObjectByType<PlayerMotor>();
   var clock=Object.FindAnyObjectByType<CityTimeOfDay>();
   if(clock&&(preview.muteLights==null||preview.muteLights.Length==0))preview.muteLights=Array.FindAll(new[]{clock.keyLight,clock.skyFill},l=>l);
   EditorUtility.SetDirty(preview);
   var hud=Object.FindAnyObjectByType<CityHud>(FindObjectsInactive.Include);
   if(hud&&hud.characterPreview!=preview){Undo.RecordObject(hud,"Wire field-pack colonist view");hud.characterPreview=preview;EditorUtility.SetDirty(hud);}
  }
  /// Returns the index of the named layer, creating it in the preferred (or first free user) slot.
  public static int EnsureLayer(string name,int preferred)
  {
   int existing=LayerMask.NameToLayer(name);
   if(existing>=0)return existing;
   var tags=new SerializedObject(AssetDatabase.LoadMainAssetAtPath("ProjectSettings/TagManager.asset"));
   var layers=tags.FindProperty("layers");
   int slot=-1;
   if(preferred>=8&&preferred<32&&string.IsNullOrEmpty(layers.GetArrayElementAtIndex(preferred).stringValue))slot=preferred;
   for(int i=8;slot<0&&i<32;i++)if(string.IsNullOrEmpty(layers.GetArrayElementAtIndex(i).stringValue))slot=i;
   if(slot<0)throw new InvalidOperationException("No free user layer for "+name+".");
   layers.GetArrayElementAtIndex(slot).stringValue=name;
   tags.ApplyModifiedProperties();
   return slot;
  }
 }
}
