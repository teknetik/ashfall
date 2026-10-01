#if UNITY_EDITOR || DEBUG
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Profiling;
namespace AthenHill
{
 // 1 Oct 2026 city paving pass: opt-in mipmap-streaming diagnostic for development players only (compiled out of releases).
 // Runs only with --athen-qa <folder> AND the environment variable ATHEN_TEXSTREAM_PROBE=1, so normal play, the city loop
 // and performance runs are untouched. Writes into the QA folder:
 //   texture-streaming.jsonl       one compact line per second (global counters + the watched textures)
 //   texture-streaming-full.json   every 8 s: every streamed texture whose loaded/desired mip is above its calculated mip
 // Optional overrides for an A/B inside one build (applied once at start, recorded in the output):
 //   ATHEN_TEXSTREAM_BUDGET=<MB>   QualitySettings.streamingMipmapsMemoryBudget
 //   ATHEN_TEXSTREAM_REDUCTION=<n> QualitySettings.streamingMipmapsMaxLevelReduction
 //   ATHEN_TEXSTREAM_OFF=1         QualitySettings.streamingMipmapsActive = false
 //   ATHEN_TEXSTREAM_WATCH=a,b     substrings of texture names to log every second (default "Paving")
 // Look-development helper for development players (same opt-in rules): ATHEN_MATERIAL_TUNE=<json file> applies
 // {"<material name>": {"_Float": 0.5, "_Color": [r,g,b,a]}} to the loaded materials once the scene is up, so a material
 // can be tuned in the native player without a rebuild. The values that win are copied back into the source tuning file.
 public static class MaterialTuneProbe
 {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Apply()
  {
   var path=Environment.GetEnvironmentVariable("ATHEN_MATERIAL_TUNE");
   if(!Debug.isDebugBuild||string.IsNullOrEmpty(path)||!File.Exists(path))return;
   var root=Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(path));
   foreach(var m in Resources.FindObjectsOfTypeAll<Material>())
   {
    if(!(root[m.name] is Newtonsoft.Json.Linq.JObject props))continue;
    foreach(var p in props.Properties())
    {
     if(!m.HasProperty(p.Name))continue;
     if(p.Value.Type==Newtonsoft.Json.Linq.JTokenType.Array){var a=p.Value.Select(x=>(float)x).ToArray();m.SetColor(p.Name,new Color(a[0],a[1],a[2],a.Length>3?a[3]:1));}
     else m.SetFloat(p.Name,(float)p.Value);
    }
    Debug.Log("MaterialTuneProbe: tuned "+m.name);
   }
  }
 }
 public class TextureStreamingProbe:MonoBehaviour
 {
  string folder;string[] watch;float nextLine,nextFull;object overrides;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void StartIfRequested()
  {
   if(!Debug.isDebugBuild||Environment.GetEnvironmentVariable("ATHEN_TEXSTREAM_PROBE")!="1")return;
   var args=Environment.GetCommandLineArgs();int index=Array.IndexOf(args,"--athen-qa");
   if(index<0||index+1>=args.Length)return;
   var p=new GameObject("Texture streaming probe").AddComponent<TextureStreamingProbe>();
   DontDestroyOnLoad(p.gameObject);p.folder=Path.GetFullPath(args[index+1]);Directory.CreateDirectory(p.folder);
   p.watch=(Environment.GetEnvironmentVariable("ATHEN_TEXSTREAM_WATCH")??"Paving").Split(',').Where(s=>s.Length>0).ToArray();
   string budget=Environment.GetEnvironmentVariable("ATHEN_TEXSTREAM_BUDGET"),reduction=Environment.GetEnvironmentVariable("ATHEN_TEXSTREAM_REDUCTION"),off=Environment.GetEnvironmentVariable("ATHEN_TEXSTREAM_OFF");
   if(float.TryParse(budget,out var mb))QualitySettings.streamingMipmapsMemoryBudget=mb;
   if(int.TryParse(reduction,out var red))QualitySettings.streamingMipmapsMaxLevelReduction=red;
   if(off=="1")QualitySettings.streamingMipmapsActive=false;
   p.overrides=new{budget,reduction,off};
  }
  static object Global()=>new{
   active=QualitySettings.streamingMipmapsActive,budgetMB=QualitySettings.streamingMipmapsMemoryBudget,maxLevelReduction=QualitySettings.streamingMipmapsMaxLevelReduction,
   renderersPerFrame=QualitySettings.streamingMipmapsRenderersPerFrame,addAllCameras=QualitySettings.streamingMipmapsAddAllCameras,mipmapLimit=QualitySettings.globalTextureMipmapLimit,
   currentMB=Texture.currentTextureMemory/1048576.0,desiredMB=Texture.desiredTextureMemory/1048576.0,targetMB=Texture.targetTextureMemory/1048576.0,
   totalMB=Texture.totalTextureMemory/1048576.0,nonStreamingMB=Texture.nonStreamingTextureMemory/1048576.0,
   streamingTextures=Texture.streamingTextureCount,nonStreamingTextures=Texture.nonStreamingTextureCount,pending=Texture.streamingTexturePendingLoadCount,
   loading=Texture.streamingTextureLoadingCount,uploads=Texture.streamingMipmapUploadCount,renderers=Texture.streamingRendererCount,discardUnused=Texture.streamingTextureDiscardUnusedMips};
  static object Describe(Texture2D t)=>new{t.name,w=t.width,h=t.height,mips=t.mipmapCount,format=t.format.ToString(),t.streamingMipmaps,priority=t.streamingMipmapsPriority,
   loaded=t.streamingMipmaps?t.loadedMipmapLevel:0,desired=t.streamingMipmaps?t.desiredMipmapLevel:0,requested=t.streamingMipmaps?t.requestedMipmapLevel:0,
   calculated=t.streamingMipmaps?t.calculatedMipmapLevel:0,mb=Profiler.GetRuntimeMemorySizeLong(t)/1048576.0};
  void Update()
  {
   float now=Time.realtimeSinceStartup;
   if(now>=nextLine)
   {
    nextLine=now+1;
    var watched=Resources.FindObjectsOfTypeAll<Texture2D>().Where(t=>watch.Any(w=>t.name.Contains(w))).Select(Describe).ToArray();
    File.AppendAllText(Path.Combine(folder,"texture-streaming.jsonl"),JsonConvert.SerializeObject(new{t=Math.Round(now,2),frame=Time.frameCount,
     camera=Camera.main?Camera.main.transform.position.ToString("F1"):null,overrides,global=Global(),watched})+"\n");
   }
   if(now>=nextFull)
   {
    nextFull=now+8;
    var all=Resources.FindObjectsOfTypeAll<Texture2D>().Where(t=>t.streamingMipmaps).ToArray();
    var reduced=all.Where(t=>t.desiredMipmapLevel>t.calculatedMipmapLevel||t.loadedMipmapLevel>t.calculatedMipmapLevel)
     .OrderByDescending(t=>(long)t.width*t.height).Select(Describe).ToArray();
    var largest=all.OrderByDescending(t=>Profiler.GetRuntimeMemorySizeLong(t)).Take(60).Select(Describe).ToArray();
    var nonStreamed=Resources.FindObjectsOfTypeAll<Texture2D>().Where(t=>!t.streamingMipmaps).OrderByDescending(t=>Profiler.GetRuntimeMemorySizeLong(t)).Take(40).Select(Describe).ToArray();
    var json=JsonConvert.SerializeObject(new{t=Math.Round(now,2),frame=Time.frameCount,overrides,global=Global(),streamedCount=all.Length,
     reducedCount=reduced.Length,reduced,largest,nonStreamed,graphicsMemoryMB=SystemInfo.graphicsMemorySize},Formatting.Indented);
    var path=Path.Combine(folder,"texture-streaming-full.json");File.WriteAllText(path+".tmp",json);
    if(File.Exists(path))File.Delete(path);File.Move(path+".tmp",path);
   }
  }
 }
}
#endif
