using System;
using System.IO;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Editor
{
 public static class LinuxBuild
 {
  [MenuItem("Athen Hill/Build/Linux development player")]
  public static void Development()=>Build(true);
  [MenuItem("Athen Hill/Build/Linux release player")]
  public static void Release()=>Build(false);
  static void Build(bool development)
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play before building.");
   EditorSceneManager.SaveOpenScenes();
   PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneLinux64,false);PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneLinux64,new[]{UnityEngine.Rendering.GraphicsDeviceType.OpenGLCore});
   PlayerSettings.companyName="Free Column";PlayerSettings.productName="Athen Hill";PlayerSettings.defaultScreenWidth=1920;PlayerSettings.defaultScreenHeight=1080;PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.resizableWindow=true;PlayerSettings.runInBackground=false;PlayerSettings.enableFrameTimingStats=true;
   var scene=ImportBaseline.ScenePath;EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(scene,true)};
   string output=development?"Builds/LinuxDevelopment/AthenHill.x86_64":"Builds/Linux/AthenHill.x86_64";
   var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scene},locationPathName=output,target=BuildTarget.StandaloneLinux64,options=development?BuildOptions.Development:BuildOptions.None});
   Directory.CreateDirectory("Captures");File.WriteAllText("Captures/linux-build.json",JsonConvert.SerializeObject(new{development,result=result.summary.result.ToString(),errors=result.summary.totalErrors,warnings=result.summary.totalWarnings,seconds=result.summary.totalTime.TotalSeconds,bytes=result.summary.totalSize,path=result.summary.outputPath},Formatting.Indented));
   if(result.summary.result!=BuildResult.Succeeded)throw new Exception("Linux build failed. Inspect build report and Console.");
  }
 }
}
