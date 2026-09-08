using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 public static class SalvageCityPass
 {
  const string RootName="Post-war salvage";
  const string Evidence="../evidence/salvage/20260908";
  static Transform root;static Transform[] original;static List<object> placements;static AmbientWalker[] walkers;static GameSession session;
  static Vector3 P(float x,float y,float z)=>new Vector3(x,y,z);
  static float[] V(Vector3 p)=>new[]{p.x,p.y,p.z};
  static GameObject Instance(string asset,string name,Vector3 p,float yaw=0,Vector3? scale=null)
  {
   var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(ImportSalvageAssets.Prefabs+"/"+asset+".prefab");if(!prefab)throw new Exception("Missing prefab "+asset);
   var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.name=name;go.transform.SetParent(root,false);go.transform.SetPositionAndRotation(p,Quaternion.Euler(0,yaw,0));go.transform.localScale=scale??Vector3.one;return go;
  }
  static void MeshCollision(GameObject go)
  {
   foreach(var f in go.GetComponentsInChildren<MeshFilter>())
   {var c=f.gameObject.AddComponent<MeshCollider>();c.sharedMesh=f.sharedMesh;c.convex=false;}
  }
  static void DisableFamily(string prefix,params string[] keep)
  {
   foreach(var t in original)
   {
    if(!t)continue;var n=t.name;var bare=n.StartsWith("COL_")?n.Substring(4):n;
    if(!bare.StartsWith(prefix.TrimEnd('_'),StringComparison.Ordinal))continue;
    if(keep.Any(k=>bare==prefix+k))continue;
    t.gameObject.SetActive(false);
   }
  }
  static string GameplaySignature()
  {
   var bridge=UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>();
   return JsonConvert.SerializeObject(new{landmarks=bridge.landmarks.GetComponentsInChildren<Transform>().Select(t=>new{t.name,p=V(t.position)}).ToArray(),player=V(session.player.transform.position),npcs=session.npcs.Select(n=>new{n.name,p=V(n.transform.position),q=n.transform.rotation.ToString("R")}).ToArray(),walkers=walkers.OrderBy(w=>w.name).Select(w=>new{w.name,w.speed,w.phase,p=V(w.transform.position),route=w.waypoints.Select(t=>V(t.position)).ToArray()}).ToArray()});
  }
  public static void Install()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");ShaderUtil.allowAsyncCompilation=false;EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   if(GameObject.Find(RootName))throw new Exception("Salvage is already installed. Edit the saved instances instead of reinstalling.");
   original=UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include,FindObjectsSortMode.None);
   session=UnityEngine.Object.FindAnyObjectByType<GameSession>();walkers=UnityEngine.Object.FindObjectsByType<AmbientWalker>();string gameplay=GameplaySignature();
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
   root=new GameObject(RootName).transform;placements=new List<object>();
   float[] zs={-18,-9,9,18};float[] heights={8.7f,10.7f,7.7f,9.7f};
   for(int side=-1;side<=1;side+=2)for(int i=0;i<4;i++)
   {
    string prefix="BLD_shop_"+(side==1?"e":"w")+"_"+(i+1).ToString("00")+"_";
    float height=heights[i]+(side==-1&&i==0?2:0);var shop=Instance("relay",prefix.TrimEnd('_')+" repaired",P(-side*20.6f,.5f,zs[i]),side*90,new Vector3(1,height/9.75f,1));
    MeshCollision(shop);Physics.SyncTransforms();
    if(!(side==1&&i==0))ReuseNameplate(prefix,shop,height);
    DisableFamily(prefix,"first_step","porch","interior_floor");
    placements.Add(new{type="replacement",asset="relay",name=shop.name,position=V(shop.transform.position),height});
   }
   var general=Instance("general","Basic General repaired",P(8,.3f,15.1f));MeshCollision(general);Physics.SyncTransforms();
   // Fit the generated porch floor to Mira's existing floor rather than moving her gameplay root.
   var vendor=session.npcs.First(n=>n.name=="npc_mira");var hit=Physics.RaycastAll(new Ray(vendor.transform.position+Vector3.up*.8f,Vector3.down),2)
    .Where(h=>h.collider.transform.IsChildOf(general.transform)).OrderByDescending(h=>h.point.y).FirstOrDefault();
   if(hit.collider)general.transform.position+=Vector3.up*(.503f-hit.point.y);
   DisableFamily("BLD_general_","first_step","porch");foreach(var c in general.GetComponentsInChildren<MeshCollider>())c.enabled=false;foreach(var t in original.Where(t=>t.name.StartsWith("COL_BLD_general_")))t.gameObject.SetActive(true);placements.Add(new{type="replacement",asset="general",position=V(general.transform.position)});
   var hall=Instance("hall","Vanguard Hall repaired",P(-10,.5f,-31.8f));MeshCollision(hall);DisableFamily("BLD_hall_","step","plinth");placements.Add(new{type="replacement",asset="hall",position=V(hall.transform.position)});
   var board=Instance("billboard","Hill community board",P(-5.4f,1.5f,-5.3f));MeshCollision(board);DisableFamily("PROP_billboard_");
   foreach(var t in original.Where(t=>t.name=="COL_billboard_panel"))t.gameObject.SetActive(false);
   placements.Add(new{type="replacement",asset="billboard",position=V(board.transform.position)});
   Vector3[] oldCrates={P(29,0,-23),P(31,0,-22),P(-28,0,22),P(-30,0,23),P(-29,0,-24)};
   for(int i=0;i<oldCrates.Length;i++)
   {
    var crate=Instance("crate","crate original "+i,oldCrates[i]);var c=crate.AddComponent<BoxCollider>();c.center=new Vector3(0,.685f,0);c.size=new Vector3(1.3f,1.37f,1.3f);DisableFamily("PROP_crate_"+i.ToString("00")+"_");
    placements.Add(new{type="replacement",asset="crate",position=V(crate.transform.position)});
   }
   Scatter();
   // Keep individual prefabs and source objects editable; build saved render chunks once.
   chunks.sourceRoots=chunks.sourceRoots.Concat(new[]{root}).ToArray();StaticRenderChunksEditor.Rebuild(chunks);
   if(GameplaySignature()!=gameplay)throw new Exception("Gameplay roots or routes changed during the visual pass.");
   AddCameras();AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(root.gameObject.scene);EditorSceneManager.SaveOpenScenes();
   Directory.CreateDirectory(Evidence);File.WriteAllText(Evidence+"/placements.json",JsonConvert.SerializeObject(placements,Formatting.Indented));File.WriteAllText(Evidence+"/gameplay-preserved.json",gameplay);
   Capture();
  }
  static void ReuseNameplate(string prefix,GameObject shop,float height)
  {
   var direction=shop.transform.forward;var center=shop.transform.position+Vector3.up*(height*.445f);
   var ray=new Ray(center+direction*12,-direction);var hit=Physics.RaycastAll(ray,24).Where(h=>h.collider.transform.IsChildOf(shop.transform)).OrderBy(h=>h.distance).FirstOrDefault();
   if(!hit.collider)throw new Exception("Could not locate shop fascia "+shop.name);
   center=hit.point+direction*.22f;
   var frameSource=original.First(t=>t.name==prefix+"sign_frame");var backSource=original.First(t=>t.name==prefix+"sign_back");var textSource=original.First(t=>t.name==prefix+"shop_name");
   var frame=CloneAt(frameSource,center,shop.transform,"Reused sign frame");var fb=frame.GetComponent<Renderer>().bounds;frame.transform.localScale=Vector3.Scale(frame.transform.localScale,new Vector3(1,height*.115f/fb.size.y,1.15f));frame.transform.position+=center-frame.GetComponent<Renderer>().bounds.center;
   var back=CloneAt(backSource,center+direction*.13f,shop.transform,"Reused sign face");var bb=back.GetComponent<Renderer>().bounds;back.transform.localScale=Vector3.Scale(back.transform.localScale,new Vector3(1,height*.09f/bb.size.y,1.05f));back.transform.position+=center+direction*.13f-back.GetComponent<Renderer>().bounds.center;
   // The old mesh is original authored lettering, preserving each existing shop identity.
   var letters=CloneAt(textSource,center+direction*.15f,shop.transform,"Original shop name");var lb=letters.GetComponent<Renderer>().bounds;float width=Mathf.Max(lb.size.x,lb.size.z);letters.transform.localScale*=4.4f/width;
   var after=letters.GetComponent<Renderer>().bounds;letters.transform.position+=center+direction*.15f-after.center;
  }
  static GameObject CloneAt(Transform source,Vector3 center,Transform parent,string name)
  {
   var go=UnityEngine.Object.Instantiate(source.gameObject);go.name=name;go.SetActive(true);go.GetComponent<Renderer>().enabled=true;go.transform.SetParent(parent,true);go.transform.position+=center-go.GetComponent<Renderer>().bounds.center;return go;
  }
  static bool Clear(Vector3 p,float radius)
  {
   // Lattice Jack is excluded from this art pass, including nearby scatter.
   if(Vector2.Distance(new Vector2(p.x,p.z),new Vector2(0,-36.5f))<10)return false;
   if(Mathf.Abs(p.z)<3&&p.x>-52&&p.x<44)return false;
   if(Mathf.Abs(p.x)<2.7f)return false;
   if(session.npcs.Any(n=>Planar(n.transform.position,p)<radius+1.05f))return false;
   foreach(var w in walkers)for(int i=0;i<w.waypoints.Length;i++)if(SegmentDistance(p,w.waypoints[i].position,w.waypoints[(i+1)%w.waypoints.Length].position)<radius+.8f)return false;
   var bridge=UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>();if(bridge.landmarks.Cast<Transform>().Any(t=>Planar(t.position,p)<radius+1.1f))return false;
   return true;
  }
  static float Planar(Vector3 a,Vector3 b)=>Vector2.Distance(new Vector2(a.x,a.z),new Vector2(b.x,b.z));
  static float SegmentDistance(Vector3 p,Vector3 a,Vector3 b){p.y=a.y=b.y=0;var d=b-a;return Vector3.Distance(p,a+d*Mathf.Clamp01(Vector3.Dot(p-a,d)/Mathf.Max(.001f,d.sqrMagnitude)));}
  static void Scatter()
  {
   var random=new System.Random(20010908);int index=0;
   // These are service yards, bench edges, gate verges, and the east wreck edge.
   Vector3[] yards={P(29,0,-19),P(31,0,18),P(-29,0,-20),P(-31,0,19),P(28,0,10),P(-28,0,10),P(28,0,-11),P(-28,0,-11),P(35,0,-7),P(36,0,7),P(-40,0,-6),P(-42,0,7),P(12,0,20),P(5,0,18),P(-16,0,-29),P(14,0,-22)};
   foreach(var p in yards)
   {
    AddScatter(index%3==0?"generator":"scrap",p,(float)(random.NextDouble()*360),.82f+(float)random.NextDouble()*.22f,index++);
    AddScatter("crate",p+P(1.65f,0,1.3f),(float)(random.NextDouble()*360),.72f+(float)random.NextDouble()*.3f,index++);
    for(int n=0;n<2;n++)AddScatter("trash",p+P(-1.5f+n*2.5f,0,-1.2f+(float)random.NextDouble()),(float)(random.NextDouble()*360),.65f+(float)random.NextDouble()*.5f,index++);
   }
   // Small waste at facade corners and the outside corners of the hill plinth.
   float[] zs={-21.3f,-12.3f,5.7f,14.7f,21.4f};
   foreach(int side in new[]{-1,1})foreach(float z in zs)AddScatter("trash",P(side*15.4f,0,z),(float)(random.NextDouble()*360),.65f+(float)random.NextDouble()*.4f,index++);
   foreach(var p in new[]{P(-7.7f,0,6.5f),P(7.9f,0,6.5f),P(-7.9f,0,-6.4f),P(8.1f,0,-6.2f),P(29.5f,0,-8.5f),P(-29.8f,0,8.5f),P(39,0,-5.2f),P(39,0,5.8f)})AddScatter("trash",p,(float)(random.NextDouble()*360),.7f,index++);
  }
  static void AddScatter(string asset,Vector3 p,float yaw,float scale,int index)
  {
   float radius=(asset=="trash"?.45f:asset=="scrap"?.95f:.8f)*scale;if(!Clear(p,radius))return;
   Physics.SyncTransforms();var hits=Physics.RaycastAll(p+Vector3.up*2.5f,Vector3.down,5).Where(h=>!h.collider.transform.IsChildOf(root)&&h.normal.y>.75f).OrderByDescending(h=>h.point.y).ToArray();if(hits.Length==0)return;
   p.y=hits[0].point.y+.005f;var go=Instance(asset,asset+" scatter "+index,p,yaw,Vector3.one*scale);
   if(asset!="trash")
   {var c=go.AddComponent<BoxCollider>();var local=ImportSalvageAssets.BoundsOf(AssetDatabase.LoadAssetAtPath<GameObject>(ImportSalvageAssets.Prefabs+"/"+asset+".prefab"));c.center=new Vector3(0,local.size.y*.5f,0);c.size=local.size;}
   placements.Add(new{type="scatter",asset,index,position=V(p),yaw,scale,routeClearance=true});
  }
  static void AddCameras()
  {
   ShotCamera("cam_salvage_hall",P(-10,6.2f,-11),P(-10,7,-31),54);
   ShotCamera("cam_salvage_shop",P(-7,4,-11),P(-21,4.7f,-18),52);
   ShotCamera("cam_salvage_general",P(12,3.7f,23),P(8,1.6f,15.1f),50);
   ShotCamera("cam_salvage_yard",P(35,2.5f,-14),P(29,1,-20),53);
   ShotCamera("cam_salvage_board",P(-3,4.5f,5),P(-5.4f,4.2f,-5.3f),46);
   ShotCamera("cam_salvage_wreck",P(-35,3,-2),P(-43,1.2f,-6),50);
  }
  static void ShotCamera(string n,Vector3 p,Vector3 t,float fov){var old=GameObject.Find(n);if(old)UnityEngine.Object.DestroyImmediate(old);ImportBaseline.Camera(n,p,t,fov);}
  public static void Capture()
  {
   ShaderUtil.allowAsyncCompilation=false;Directory.CreateDirectory(Evidence+"/editor");
   foreach(var n in new[]{"cam_hill","cam_avenue","cam_gate","cam_salvage_hall","cam_salvage_shop","cam_salvage_general","cam_salvage_yard","cam_salvage_board","cam_salvage_wreck"}){PortDiagnostics.Capture(n);PortDiagnostics.Capture(n);File.Copy("Captures/Fixed/"+n+".png",Evidence+"/editor/"+n+".png",true);}
  }
  public static void FixSignsAndCapture()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);root=GameObject.Find(RootName).transform;var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
   foreach(var t in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include,FindObjectsSortMode.None))
   {if(t.IsChildOf(root))continue;if(t.name.StartsWith("BLD_shop_")&&t.name.Contains(" "))t.gameObject.SetActive(false);}
   Physics.SyncTransforms();
   foreach(Transform shop in root)
   {
    if(!shop.name.StartsWith("BLD_shop_"))continue;var frame=shop.Find("Reused sign frame");if(!frame)continue;
    float height=shop.localScale.y*9.75f;var direction=shop.forward;var origin=shop.position+Vector3.up*(height*.445f);
    var hit=Physics.RaycastAll(new Ray(origin+direction*12,-direction),24).Where(h=>h.collider.transform.IsChildOf(shop)).OrderBy(h=>h.distance).First();var center=hit.point+direction*.22f;
    frame.position+=center-frame.GetComponent<Renderer>().bounds.center;
    var back=shop.Find("Reused sign face");back.position+=center+direction*.13f-back.GetComponent<Renderer>().bounds.center;
    var letters=shop.Find("Original shop name");letters.position+=center+direction*.15f-letters.GetComponent<Renderer>().bounds.center;
   }
   StaticRenderChunksEditor.Rebuild(chunks);AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();Capture();
  }
  public static void FixGeneralCollision()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);var go=GameObject.Find("Basic General repaired");
   foreach(var c in go.GetComponentsInChildren<MeshCollider>())c.enabled=false;
   foreach(var t in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include,FindObjectsSortMode.None))if(t.name.StartsWith("COL_BLD_general_"))t.gameObject.SetActive(true);
   Physics.SyncTransforms();
   var rays=new List<object>();for(float y=.7f;y<2.4f;y+=.5f)
   {var hit=Physics.RaycastAll(new Ray(new Vector3(8,y,19),Vector3.back),6).Select(h=>new{h.collider.name,point=V(h.point),normal=V(h.normal)}).ToArray();rays.Add(new{y,hits=hit});}
   File.WriteAllText(Evidence+"/general-collision.json",JsonConvert.SerializeObject(rays,Formatting.Indented));
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();StaticRenderChunksEditor.Rebuild(chunks);AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();LinuxBuild.Development();LinuxBuild.Release();
  }
  public static void Build(){EditorSceneManager.OpenScene(ImportBaseline.ScenePath);LinuxBuild.Development();LinuxBuild.Release();}
 }
}
