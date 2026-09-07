using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Editor
{
 public static class PortDiagnostics
 {
  [MenuItem("Athen Hill/Diagnostics/Apply command")]
  public static void Command()
  {
   var b=Object.FindAnyObjectByType<AthenDebugBridge>();
   var j=JObject.Parse(File.ReadAllText("Captures/debug-command.json"));
   switch((string)j["action"])
   {
    case "goto":b.Goto((string)j["landmark"]);break;
    case "view":b.View((string)j["camera"]);break;
    case "reset":b.ResetPlayer();break;
    case "capture":Capture((string)j["camera"]);break;
    case "cameraYaw": b.follow.yaw=(float)j["yaw"];break;
    default:throw new System.ArgumentException("Unknown diagnostic command");
   }
   Snapshot();
  }
  public static void Capture(string name)
  {
   var camera=Object.FindObjectsByType<Camera>().First(c=>c.name==name);
   var old=camera.targetTexture;var active=RenderTexture.active;float aspect=camera.aspect;
   var rt=new RenderTexture(1920,1080,24,RenderTextureFormat.ARGB32);var texture=new Texture2D(1920,1080,TextureFormat.RGB24,false);
   try{camera.aspect=16f/9;camera.targetTexture=rt;camera.Render();RenderTexture.active=rt;texture.ReadPixels(new Rect(0,0,1920,1080),0,0);texture.Apply();Directory.CreateDirectory("Captures/Fixed");File.WriteAllBytes("Captures/Fixed/"+name+".png",texture.EncodeToPNG());}
   finally{camera.targetTexture=old;camera.aspect=aspect;RenderTexture.active=active;Object.DestroyImmediate(texture);Object.DestroyImmediate(rt);}
  }
  [MenuItem("Athen Hill/Diagnostics/Write snapshot")]
  public static void Snapshot()
  {
   var sound=Object.FindAnyObjectByType<CityAudio>();
   var bridge=Object.FindAnyObjectByType<AthenDebugBridge>();
   var session=Object.FindAnyObjectByType<GameSession>();
   var doc=Object.FindAnyObjectByType<UIDocument>();
   var player=bridge?bridge.player:null;
   var actors=Object.FindObjectsByType<ActorAnimation>();
   var a=actors.Select(x=>new {name=x.name,position=new[]{x.transform.position.x,x.transform.position.y,x.transform.position.z},rotation=x.transform.eulerAngles.ToString(),clip=x.CurrentClip,animationPlaying=x.animationSource.isPlaying,clips=x.animationSource.Cast<AnimationState>().Select(s=>new{name=s.name,time=s.time,speed=s.speed,enabled=s.enabled}).ToArray(),renderers=x.GetComponentsInChildren<Renderer>().Select(r=>new{name=r.name,bounds=r.bounds.ToString(),shadows=r.shadowCastingMode.ToString()}).ToArray()});
   Directory.CreateDirectory("Captures");File.WriteAllText("Captures/snapshot.json",JsonConvert.SerializeObject(new{audio=sound?new{sound.StepCount,sound.ClickCount,listenerVolume=AudioListener.volume,listenerPaused=AudioListener.pause,sources=Object.FindObjectsByType<AudioSource>().Select(x=>new{name=x.name,playing=x.isPlaying,clip=x.clip?x.clip.name:null,length=x.clip?x.clip.length:0,group=x.outputAudioMixerGroup?x.outputAudioMixerGroup.name:null,x.spatialBlend,x.volume,x.time}).ToArray()}:null,playing=EditorApplication.isPlaying,session=session?new{state=session.State.ToString(),session.visitedHill,session.muted,session.reducedMotion,spoken=session.Spoken.ToArray(),session.boughtFlask,session.soldScrap,session.linked,session.notice,session.selectedDestination,gridProgress=session.GridProgress,credits=session.Shop?.Credits,quantities=session.catalog.items.ToDictionary(i=>i.id,i=>session.Shop?.Quantity(i.id)),focused=(doc?.rootVisualElement.focusController.focusedElement as VisualElement)?.name}:null,player=player?new{position=new[]{player.transform.position.x,player.transform.position.y,player.transform.position.z},grounded=player.Grounded,speed=player.Speed}:null,fps=bridge?bridge.fps:0,camera=bridge?new{position=bridge.follow.transform.position.ToString(),overlaps=Physics.OverlapSphere(bridge.follow.transform.position,.20f,bridge.follow.worldMask,QueryTriggerInteraction.Ignore).Select(x=>x.name).ToArray()}:null,actors=a,draws=UnityStats.drawCalls,triangles=UnityStats.triangles,setPass=UnityStats.setPassCalls},Formatting.Indented));
  }
 }
}
