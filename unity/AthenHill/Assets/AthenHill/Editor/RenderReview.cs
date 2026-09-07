using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 public static class RenderReview
 {
  [MenuItem("Athen Hill/U4/Create daylight setup")]
  public static void Daylight()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
   const string path="Assets/AthenHill/Materials/DesertSky.mat";
   if(File.Exists(path))throw new Exception("Daylight setup exists; edit lights and DesertSky in the Inspector.");
   var sky=new Material(Shader.Find("Skybox/Procedural")){name="DesertSky"};sky.SetColor("_SkyTint",new Color(.58f,.53f,.46f));sky.SetColor("_GroundColor",new Color(.58f,.44f,.29f));sky.SetFloat("_AtmosphereThickness",1.35f);sky.SetFloat("_Exposure",.85f);sky.SetFloat("_SunSize",.025f);AssetDatabase.CreateAsset(sky,path);RenderSettings.skybox=sky;
   var sun=GameObject.Find("Sun").GetComponent<Light>();sun.transform.rotation=Quaternion.LookRotation(-new Vector3(36,69.282f,42));sun.color=new Color(1,.886f,.698f);sun.intensity=2.2f;RenderSettings.sun=sun;
   RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=new Color(.63f,.68f,.72f);RenderSettings.ambientEquatorColor=new Color(.65f,.57f,.44f);RenderSettings.ambientGroundColor=new Color(.36f,.30f,.23f);RenderSettings.reflectionIntensity=1.2f;
   RenderSettings.fogColor=new Color(.72f,.60f,.44f);RenderSettings.fogStartDistance=45;RenderSettings.fogEndDistance=155;
   var fill=new GameObject("Sky fill").AddComponent<Light>();fill.type=LightType.Directional;fill.transform.rotation=Quaternion.LookRotation(new Vector3(.3f,-.7f,.5f));fill.color=new Color(.70f,.80f,1);fill.intensity=.45f;fill.shadows=LightShadows.None;
   var probe=new GameObject("City sky reflection").AddComponent<ReflectionProbe>();probe.transform.position=new Vector3(0,3,0);probe.size=new Vector3(140,60,120);probe.mode=ReflectionProbeMode.Baked;probe.cullingMask=0;probe.clearFlags=ReflectionProbeClearFlags.Skybox;probe.resolution=128;probe.hdr=true;
   const string reflection="Assets/AthenHill/Materials/DesertSkyReflection.exr";if(!Lightmapping.BakeReflectionProbe(probe,reflection))throw new Exception("Sky reflection bake failed.");AssetDatabase.ImportAsset(reflection);probe.bakedTexture=AssetDatabase.LoadAssetAtPath<Texture>(reflection);
   EditorSceneManager.MarkSceneDirty(sun.gameObject.scene);AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();
  }
  [MenuItem("Athen Hill/U4/Restore pavement texture")]
  public static void Pavement()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
   var mat=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/Paving.mat");if(mat.GetTexture("_BaseMap"))throw new Exception("Pavement already has a texture; edit the material directly.");
   const string path="Assets/AthenHill/Art/Textures/StonePaving.png";var importer=(TextureImporter)AssetImporter.GetAtPath(path);importer.sRGBTexture=true;importer.mipmapEnabled=true;importer.wrapMode=TextureWrapMode.Repeat;importer.anisoLevel=4;importer.SaveAndReimport();
   mat.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(path));mat.SetColor("_BaseColor",Color.white);mat.SetTextureScale("_BaseMap",new Vector2(15,11.25f));EditorUtility.SetDirty(mat);AssetDatabase.SaveAssets();
   EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());EditorSceneManager.SaveOpenScenes();
  }
  [MenuItem("Athen Hill/U4/Capture hero cameras")]
  public static void Capture(){foreach(var name in new[]{"cam_hill","cam_avenue","cam_gate"})PortDiagnostics.Capture(name);PortDiagnostics.Snapshot();}
  [MenuItem("Athen Hill/U4/Create cutout foliage variant")]
  public static void Foliage()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
   const string path="Assets/AthenHill/Materials/TreeLeaves.mat";
   if(File.Exists(path))throw new Exception("Foliage variant exists. Edit TreeLeaves.mat directly.");
   var original=AssetDatabase.LoadAllAssetsAtPath(ImportBaseline.Art+"world.glb").OfType<Material>().Single(m=>m.name=="MAT_leaf");
   var m=new Material(original){name="TreeLeaves"};
   foreach(var keyword in new[]{"_SURFACE_TYPE_TRANSPARENT","_DISABLE_SSR_TRANSPARENT","_ENABLE_FOG_ON_TRANSPARENT"})m.DisableKeyword(keyword);
   m.EnableKeyword("_ALPHATEST_ON");m.SetOverrideTag("RenderType","TransparentCutout");m.renderQueue=(int)RenderQueue.AlphaTest;
   void Set(string property,float value){if(m.HasProperty(property))m.SetFloat(property,value);}
   Set("alphaCutoff",.35f);Set("_AlphaCutoff",.35f);Set("_AlphaClip",1);Set("_Surface",0);Set("_ZWrite",1);Set("_Cull",0);Set("_CullMode",0);Set("_SrcBlend",1);Set("_DstBlend",0);Set("_AlphaDstBlend",0);Set("_SrcBlendAlpha",1);Set("_DstBlendAlpha",0);
   m.SetShaderPassEnabled("DepthOnly",true);m.SetShaderPassEnabled("ShadowCaster",true);AssetDatabase.CreateAsset(m,path);
   foreach(var r in GameObject.Find("AuthoredWorld").GetComponentsInChildren<Renderer>(true))if(r.sharedMaterial==original){r.sharedMaterial=m;r.shadowCastingMode=ShadowCastingMode.On;}
   StaticRenderChunksEditor.Rebuild(UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>());
  }
 }
}
