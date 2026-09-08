using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
 public static class DistrictCityPass
 {
  public const string Evidence="../evidence/district/20260908";
  public const string RootName="District rebuild";
  public static readonly string[] ShopRoots={"BLD_shop_e_02 repaired","BLD_shop_e_03 repaired","BLD_shop_e_04 repaired","BLD_shop_w_01 repaired","BLD_shop_w_02 repaired","BLD_shop_w_03 repaired","BLD_shop_w_04 repaired"};
  static float[] V(Vector3 p)=>new[]{p.x,p.y,p.z};
  public static string GameplaySignature()
  {
   var session=UnityEngine.Object.FindAnyObjectByType<GameSession>();var landmarks=GameObject.Find("Landmarks");
   return JsonConvert.SerializeObject(new{player=V(session.player.transform.position),npcs=session.npcs.OrderBy(n=>n.name).Select(n=>new{n.name,p=V(n.transform.position)}).ToArray(),landmarks=landmarks.GetComponentsInChildren<Transform>().OrderBy(t=>t.name).Select(t=>new{t.name,p=V(t.position)}).ToArray(),walkers=UnityEngine.Object.FindObjectsByType<AmbientWalker>().Where(w=>w.name!="npc_yard_mechanic").OrderBy(w=>w.name).Select(w=>new{w.name,w.speed,w.phase,p=V(w.transform.position),route=w.waypoints.Select(t=>V(t.position)).ToArray()}).ToArray()});
  }
  public static void Install()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   if(GameObject.Find(RootName))throw new Exception("District is installed. Edit the existing instances instead.");
   Directory.CreateDirectory(Evidence);var signature=GameplaySignature();
   var old=ShopRoots.Select(GameObject.Find).ToArray();if(old.Any(g=>!g))throw new Exception("Missing original shop instance.");
   for(int i=0;i<old.Length;i++)
   {
    var t=old[i].transform;var b=ImportSalvageAssets.BoundsOf(old[i]);
    Camera("cam_district_"+ImportDistrictAssets.Names[i],t.position+t.forward*15+t.right*5+Vector3.up*4.2f,t.position+Vector3.up*b.size.y*.43f,48);
   }
   Camera("cam_district_gate",new Vector3(31,5,-7),new Vector3(48,4,5),58);
   Capture("before");
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
   var root=new GameObject(RootName).transform;
   for(int i=0;i<old.Length;i++)
   {
    var go=Instance(ImportDistrictAssets.Names[i],root,old[i].transform.position,old[i].transform.rotation);
    MeshCollision(go);old[i].SetActive(false);
   }
   foreach(float z in new[]{0f,12f})MeshCollision(Instance("gate",root,new Vector3(48,0,z),Quaternion.Euler(0,-90,0)));
   foreach(var t in GameObject.Find("AuthoredWorld").GetComponentsInChildren<Transform>(true))
   {
    var n=t.name;
    if(n.StartsWith("BLD_gate_")||n.StartsWith("COL_BLD_gate_")||n.StartsWith("COL_gate_arch_")||n.StartsWith("COL_gate_tunnel_")||n.StartsWith("PROP_free_column_gate_banner"))t.gameObject.SetActive(false);
   }
   chunks.sourceRoots=chunks.sourceRoots.Concat(new[]{root}).ToArray();StaticRenderChunksEditor.Rebuild(chunks);
   if(GameplaySignature()!=signature)throw new Exception("Existing gameplay roots or routes changed.");
   File.WriteAllText(Evidence+"/gameplay-preserved.json",JsonConvert.SerializeObject(new{preserved=true,before=JsonConvert.DeserializeObject(signature),after=JsonConvert.DeserializeObject(GameplaySignature())},Formatting.Indented));
   File.WriteAllText(Evidence+"/placements.json",JsonConvert.SerializeObject(root.Cast<Transform>().Select(t=>new{t.name,position=V(t.position),rotation=V(t.eulerAngles),size=V(ImportSalvageAssets.BoundsOf(t.gameObject).size)}),Formatting.Indented));
   AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();Capture("editor");
  }
  static GameObject Instance(string asset,Transform root,Vector3 p,Quaternion q)
  {
   var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(ImportDistrictAssets.Prefabs+"/"+asset+".prefab");if(!prefab)throw new Exception("Missing "+asset);
   var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.name="District "+asset;go.transform.SetParent(root,false);go.transform.SetPositionAndRotation(p,q);return go;
  }
  static void MeshCollision(GameObject go){foreach(var f in go.GetComponentsInChildren<MeshFilter>()){var c=f.gameObject.AddComponent<MeshCollider>();c.sharedMesh=f.sharedMesh;}}
  public static Camera Camera(string name,Vector3 p,Vector3 target,float fov)
  {var old=GameObject.Find(name);if(old)UnityEngine.Object.DestroyImmediate(old);return ImportBaseline.Camera(name,p,target,fov);}
  public static void Capture(string folder="editor")
  {
   ShaderUtil.allowAsyncCompilation=false;Directory.CreateDirectory(Evidence+"/"+folder);
   var names=new[]{"cam_hill","cam_avenue","cam_gate"}.Concat(UnityEngine.Object.FindObjectsByType<Camera>().Where(c=>c.name.StartsWith("cam_district_")).Select(c=>c.name)).ToArray();
   foreach(var n in names){PortDiagnostics.Capture(n);PortDiagnostics.Capture(n);File.Copy("Captures/Fixed/"+n+".png",Evidence+"/"+folder+"/"+n+".png",true);}
  }
  public static void GeometryReport()
  {
   var rs=UnityEngine.Object.FindObjectsByType<Renderer>().Where(r=>r.enabled&&r.gameObject.activeInHierarchy).ToArray();
   var report=UnityEngine.Object.FindObjectsByType<Camera>().Where(c=>c.name.StartsWith("cam_")).Select(c=>{
    var planes=GeometryUtility.CalculateFrustumPlanes(c);var visible=rs.Where(r=>GeometryUtility.TestPlanesAABB(planes,r.bounds)).Select(r=>new{r.name,triangles=r is SkinnedMeshRenderer s?s.sharedMesh.triangles.Length/3:r.GetComponent<MeshFilter>()?r.GetComponent<MeshFilter>().sharedMesh.triangles.Length/3:0}).Where(r=>r.triangles>0).ToArray();
    return new{camera=c.name,triangles=visible.Sum(r=>r.triangles),renderers=visible};
   }).ToArray();
   File.WriteAllText(Evidence+"/visible-geometry.json",JsonConvert.SerializeObject(report,Formatting.Indented));
  }
  public static void Build()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);StaticRenderChunksEditor.Rebuild(UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>());
   GeometryReport();Capture();LinuxBuild.Development();File.Copy("Captures/linux-build.json",Evidence+"/linux-development-build.json",true);LinuxBuild.Release();File.Copy("Captures/linux-build.json",Evidence+"/linux-release-build.json",true);
  }
  public static void FitFieldSign()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
   var field=GameObject.Find("District field").transform;var existing=field.Find("Field Supply nameplate");if(existing)UnityEngine.Object.DestroyImmediate(existing.gameObject);
   var old=UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include,FindObjectsSortMode.None).First(t=>t.name==ShopRoots[4]);
   var group=new GameObject("Field Supply nameplate").transform;group.SetParent(field,true);
   foreach(var n in new[]{"Reused sign frame","Reused sign face","Original shop name"})
   {
    var source=old.Find(n);var go=UnityEngine.Object.Instantiate(source.gameObject);go.name=n;go.transform.SetPositionAndRotation(source.position,source.rotation);go.transform.localScale=source.lossyScale;go.SetActive(true);go.GetComponent<Renderer>().enabled=true;go.transform.SetParent(group,true);
   }
   var bounds=ImportDistrictAssets.BoundsOf(group.gameObject);group.localScale=Vector3.Scale(group.localScale,new Vector3(1,1.5f/bounds.size.y,6.35f/bounds.size.z));
   Physics.SyncTransforms();var center=field.position+Vector3.up*5.25f;
   var hit=Physics.RaycastAll(new Ray(center+field.forward*15,-field.forward),25).Where(h=>h.collider.transform.IsChildOf(field)).OrderBy(h=>h.distance).First();
   group.position+=hit.point+field.forward*.94f-Vector3.up*.8f-ImportDistrictAssets.BoundsOf(group.gameObject).center;
   StaticRenderChunksEditor.Rebuild(chunks);AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(field.gameObject.scene);EditorSceneManager.SaveOpenScenes();
   PortDiagnostics.Capture("cam_district_field");PortDiagnostics.Capture("cam_district_field");File.Copy("Captures/Fixed/cam_district_field.png",Evidence+"/editor/cam_district_field.png",true);
  }
  public static void FitFieldSignAndBuild(){FitFieldSign();Build();}
 }
}
