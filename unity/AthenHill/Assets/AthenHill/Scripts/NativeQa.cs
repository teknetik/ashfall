using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 // Explicitly opt-in, development-player-only diagnostics. No command listener in releases.
 public class NativeQa:MonoBehaviour
 {
  string folder;GameSession session;AthenDebugBridge bridge;UIDocument document;
  ProfilerRecorder draws,tris,batches,setPass,mainThread,renderThread;
  readonly List<object> samples=new List<object>();bool profiling;float nextSnapshot;
  readonly FrameTiming[] timings=new FrameTiming[1];
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void StartIfRequested()
  {
   if(!Debug.isDebugBuild)return;
   var args=Environment.GetCommandLineArgs();int index=Array.IndexOf(args,"--athen-qa");
   if(index<0||index+1>=args.Length)return;
   var qa=new GameObject("Development QA").AddComponent<NativeQa>();qa.folder=Path.GetFullPath(args[index+1]);Directory.CreateDirectory(qa.folder);
  }
  void Start()
  {
   session=FindAnyObjectByType<GameSession>();bridge=FindAnyObjectByType<AthenDebugBridge>();document=FindAnyObjectByType<UIDocument>();
   draws=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Draw Calls Count");tris=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Triangles Count");batches=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Batches Count");setPass=ProfilerRecorder.StartNew(ProfilerCategory.Render,"SetPass Calls Count");mainThread=ProfilerRecorder.StartNew(ProfilerCategory.Internal,"Main Thread");renderThread=ProfilerRecorder.StartNew(ProfilerCategory.Internal,"Render Thread");
   QualitySettings.vSyncCount=0;Application.targetFrameRate=-1;
   Write("environment.json",new{unity=Application.unityVersion,os=SystemInfo.operatingSystem,gpu=SystemInfo.graphicsDeviceName,api=SystemInfo.graphicsDeviceType.ToString(),driver=SystemInfo.graphicsDeviceVersion,cpu=SystemInfo.processorType,quality=QualitySettings.names[QualitySettings.GetQualityLevel()],width=Screen.width,height=Screen.height,vsync=QualitySettings.vSyncCount,targetFrameRate=Application.targetFrameRate,drawCounter=draws.Valid,triangleCounter=tris.Valid,mainThreadCounter=mainThread.Valid,renderThreadCounter=renderThread.Valid,actorCount=FindObjectsByType<ActorAnimation>().Length});
  }
  void Write(string name,object value){var path=Path.Combine(folder,name);File.WriteAllText(path+".tmp",JsonConvert.SerializeObject(value,Formatting.Indented));if(File.Exists(path))File.Replace(path+".tmp",path,null);else File.Move(path+".tmp",path);}
  void Update()
  {
   string path=Path.Combine(folder,"command.json");
   if(File.Exists(path))
   {
    try
    {
     var j=JObject.Parse(File.ReadAllText(path));File.Delete(path);
     switch((string)j["action"])
     {
      case "goto":bridge.Goto((string)j["landmark"]);break;
      case "view":bridge.View((string)j["camera"]);break;
      case "reset":bridge.ResetPlayer();break;
      case "cameraYaw":bridge.follow.yaw=(float)j["yaw"];break;
      case "capture":ScreenCapture.CaptureScreenshot(Path.Combine(folder,Path.GetFileName((string)j["name"])+".png"));break;
      case "profileStart":samples.Clear();profiling=true;break;
      case "profileStop":profiling=false;Write("profile.json",samples);break;
      case "quit":Application.Quit();break;
      default:throw new ArgumentException("Unknown QA operation");
     }
     Write("ack.json",new{id=(string)j["id"],success=true});
    }
    catch(Exception e){Write("qa-error.json",new{error=e.ToString()});Debug.LogException(e);}
   }
   if(Time.unscaledTime>=nextSnapshot){nextSnapshot=Time.unscaledTime+.1f;Snapshot();}
  }
  void LateUpdate()
  {
   FrameTimingManager.CaptureFrameTimings();
   if(!profiling)return;
   uint count=FrameTimingManager.GetLatestTimings(1,timings);
   samples.Add(new{dt=Time.unscaledDeltaTime,draws=draws.Valid?draws.LastValue:-1,tris=tris.Valid?tris.LastValue:-1,batches=batches.Valid?batches.LastValue:-1,setPass=setPass.Valid?setPass.LastValue:-1,mainMs=mainThread.Valid?mainThread.LastValue/1e6:-1,renderMs=renderThread.Valid?renderThread.LastValue/1e6:-1,cpuMs=count>0?timings[0].cpuFrameTime:-1,gpuMs=count>0?timings[0].gpuFrameTime:-1,state=session.State.ToString(),speed=session.player.Speed});
  }
  void Snapshot()
  {
   var p=session.player;var sound=FindAnyObjectByType<CityAudio>();
   Write("snapshot.json",new{frame=Time.frameCount,width=Screen.width,height=Screen.height,session=new{state=session.State.ToString(),session.visitedHill,spoken=session.Spoken.ToArray(),session.boughtFlask,session.soldScrap,session.linked,session.muted,session.reducedMotion,session.notice,session.selectedDestination,gridProgress=session.GridProgress,credits=session.Shop?.Credits,quantities=session.catalog.items.ToDictionary(i=>i.id,i=>session.Shop?.Quantity(i.id)),focused=(document.rootVisualElement.focusController.focusedElement as VisualElement)?.name},player=new{position=new[]{p.transform.position.x,p.transform.position.y,p.transform.position.z},grounded=p.Grounded,speed=p.Speed},audio=sound?new{sound.StepCount,sound.ClickCount,paused=AudioListener.pause,volume=AudioListener.volume}:null,camera=new{overlaps=Physics.OverlapSphere(bridge.follow.transform.position,.20f,bridge.follow.worldMask,QueryTriggerInteraction.Ignore).Select(x=>x.name).ToArray()},fps=bridge.fps,draws=draws.Valid?draws.LastValue:-1,triangles=tris.Valid?tris.LastValue:-1});
  }
  void OnDestroy(){draws.Dispose();tris.Dispose();batches.Dispose();setPass.Dispose();mainThread.Dispose();renderThread.Dispose();}
 }
}
