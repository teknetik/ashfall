using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Editor
{
 public static class SalvageSurvey
 {
  public static void Capture()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   var root=GameObject.Find("AuthoredWorld");
   var outDir=Path.GetFullPath("../evidence/salvage/20260908/survey");Directory.CreateDirectory(outDir);
   var renderers=root.GetComponentsInChildren<MeshRenderer>(true);
   File.WriteAllText(outDir+"/inventory.json",JsonConvert.SerializeObject(renderers.Select(r=>new{name=r.name,active=r.gameObject.activeInHierarchy,enabled=r.enabled,position=V(r.transform.position),center=V(r.bounds.center),size=V(r.bounds.size),triangles=r.GetComponent<MeshFilter>().sharedMesh.triangles.Length/3}),Formatting.Indented));
   var landmarks=GameObject.Find("Landmarks");
   File.WriteAllText(outDir+"/gameplay.json",JsonConvert.SerializeObject(new{landmarks=landmarks.GetComponentsInChildren<Transform>().Select(t=>new{t.name,position=V(t.position)}),actors=UnityEngine.Object.FindObjectsByType<ActorAnimation>().Select(a=>new{a.name,position=V(a.transform.position)}),walkers=UnityEngine.Object.FindObjectsByType<AmbientWalker>().Select(w=>new{w.name,position=V(w.transform.position)})},Formatting.Indented));
   Shot("poi_hall",new Vector3(-10,7,-11),new Vector3(-10,7,-32),outDir);
   Shot("poi_relay",new Vector3(-6,5,-18),new Vector3(-22,5,-18),outDir);
   Shot("poi_general",new Vector3(8,3.1f,23),new Vector3(8,1.7f,15),outDir);
   Shot("poi_billboard",new Vector3(-5.4f,5,6),new Vector3(-5.4f,4.5f,-5.3f),outDir);
   Shot("poi_crate",new Vector3(26,1.7f,-18),new Vector3(29, .65f,-23),outDir);
   Shot("poi_wreck",new Vector3(-41,5,0),new Vector3(-54,4,0),outDir);
   Shot("poi_west",new Vector3(28,5,-5),new Vector3(48,4,0),outDir);
   Shot("poi_hall",new Vector3(-10,7,-11),new Vector3(-10,7,-32),outDir);
  }
  static float[] V(Vector3 p)=>new[]{p.x,p.y,p.z};
  static void Shot(string name,Vector3 p,Vector3 target,string folder)
  {
   var c=ImportBaseline.Camera(name,p,target,52);PortDiagnostics.Capture(name);File.Copy("Captures/Fixed/"+name+".png",folder+"/"+name+".png",true);UnityEngine.Object.DestroyImmediate(c.gameObject);
  }
 }
}
