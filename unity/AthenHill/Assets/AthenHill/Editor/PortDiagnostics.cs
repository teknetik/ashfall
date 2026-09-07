using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Editor
{
 public static class PortDiagnostics
 {
  [MenuItem("Athen Hill/Diagnostics/Write snapshot")]
  public static void Snapshot()
  {
   var actors=Object.FindObjectsByType<ActorAnimation>(FindObjectsSortMode.None);
   var a=actors.Select(x=>new {name=x.name,position=new[]{x.transform.position.x,x.transform.position.y,x.transform.position.z},rotation=x.transform.eulerAngles.ToString(),clip=x.CurrentClip,animationPlaying=x.animationSource.isPlaying,clips=x.animationSource.Cast<AnimationState>().Select(s=>new{name=s.name,time=s.time,speed=s.speed,enabled=s.enabled}).ToArray(),renderers=x.GetComponentsInChildren<Renderer>().Select(r=>new{name=r.name,bounds=r.bounds.ToString(),shadows=r.shadowCastingMode.ToString()}).ToArray()});
   Directory.CreateDirectory("Captures");File.WriteAllText("Captures/snapshot.json",JsonConvert.SerializeObject(new{playing=EditorApplication.isPlaying,actors=a,draws=UnityStats.drawCalls,triangles=UnityStats.triangles,setPass=UnityStats.setPassCalls},Formatting.Indented));
  }
 }
}
