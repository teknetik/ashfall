using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 /// Narrow checkpoint retrofit. Existing tutorial, locker root, terrain, encounter and city IDs stay intact.
 public static class WestGateCheckpointPass
 {
  const string Art="Assets/AthenHill/Art/Checkpoint/";
  const string Evidence="../evidence/checkpoint/20260926/";
  static GameSession session; static MeshCollider ground;
  static Vector3 At(float x,float z,float lift=0){RaycastHit h;float y=ground.Raycast(new Ray(new Vector3(x,40,z),Vector3.down),out h,100)?h.point.y:0;return new Vector3(x,y+lift,z);}
  static GameObject Place(string path,Transform parent,string name,Vector3 pos,float yaw=0)
  {
   var model=AssetDatabase.LoadAssetAtPath<GameObject>(path);if(!model)throw new Exception("Missing "+path);
   var g=(GameObject)PrefabUtility.InstantiatePrefab(model);g.name=name;g.transform.SetParent(parent,true);g.transform.SetPositionAndRotation(pos,Quaternion.Euler(0,yaw,0));return g;
  }
  static void Proxies(GameObject g)
  {
   foreach(var t in g.GetComponentsInChildren<Transform>())if(t.name.StartsWith("COL_"))
   {var f=t.GetComponent<MeshFilter>();if(f){var b=t.gameObject.AddComponent<BoxCollider>();b.center=f.sharedMesh.bounds.center;b.size=f.sharedMesh.bounds.size;}var r=t.GetComponent<Renderer>();if(r)r.enabled=false;}
  }
  static void Sign(Transform parent,string name,string text,Vector3 local,Vector3 euler,float size)
  {
   var g=new GameObject(name);g.transform.SetParent(parent,false);g.transform.localPosition=local;g.transform.localEulerAngles=euler;
   var t=g.AddComponent<TextMesh>();t.text=text;t.fontSize=80;t.characterSize=size;t.anchor=TextAnchor.MiddleCenter;t.alignment=TextAlignment.Center;t.color=new Color(.92f,.90f,.76f);
   var r=g.GetComponent<MeshRenderer>();r.shadowCastingMode=ShadowCastingMode.Off;r.receiveShadows=false;
  }
  static DialogueChoice Choice(string id,string label,string next=null)=>new DialogueChoice{id=id,label=label,next=next,action=next==null?"close":""};
  static DialogueNode Node(string id,string title,string text,params DialogueChoice[] choices)=>new DialogueNode{id=id,title=title,text=text,choices=choices};
  static NpcAgent Guard(GameObject g,string id,string name,string role,DialogueNode[] nodes)
  {
   string path="Assets/AthenHill/Data/"+id+".asset";var d=AssetDatabase.LoadAssetAtPath<NpcDefinition>(path);
   if(!d){d=ScriptableObject.CreateInstance<NpcDefinition>();AssetDatabase.CreateAsset(d,path);}d.id=id;d.displayName=name;d.role=role;d.nodes=nodes;EditorUtility.SetDirty(d);
   var n=g.GetComponent<NpcAgent>()??g.AddComponent<NpcAgent>();n.definition=d;n.actor=g.GetComponent<ActorAnimation>();n.countsForCityVisit=false;return n;
  }
  // Sidearm visibly secured to hip, preserving the supplied guard's arms-at-sides pose.
  static void Arm(GameObject guard)
  {
   var old=guard.GetComponentsInChildren<Transform>().FirstOrDefault(t=>t.name=="Warden sidearm holster");if(old)UnityEngine.Object.DestroyImmediate(old.gameObject);
   var actor=guard.GetComponent<ActorAnimation>();if(actor&&actor.idle&&actor.animationSource)actor.idle.SampleAnimation(actor.animationSource.gameObject,0);
   var hand=guard.GetComponentsInChildren<Transform>().First(t=>t.name=="RightHand");
   var holder=new GameObject("Warden secured sidearm").transform;
   var gun=Place("Assets/AthenHill/Art/OuterBerms/ScrapPistol.glb",holder,"Scrap sidearm",Vector3.zero);
   var rs=gun.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
   var verts=gun.GetComponentsInChildren<MeshFilter>().SelectMany(f=>f.sharedMesh.vertices.Select(v=>f.transform.TransformPoint(v))).ToArray();
   bool alongX=b.size.x>=b.size.z;var lower=verts.Where(v=>v.y<b.center.y-b.extents.y*.3f).ToArray();
   float rear=lower.Length>0?(alongX?lower.Average(v=>v.x)-b.center.x:lower.Average(v=>v.z)-b.center.z):0;
   var barrel=(alongX?Vector3.right:Vector3.forward)*(rear>0?-1:1);float scale=.34f/Mathf.Max(b.size.x,b.size.z);
   gun.transform.localScale=Vector3.one*scale;gun.transform.localRotation=Quaternion.Inverse(Quaternion.LookRotation(barrel,Vector3.up));
   var grip=lower.Length>0?new Vector3(lower.Average(v=>v.x),b.center.y,lower.Average(v=>v.z)):b.center;
   gun.transform.localPosition=-(gun.transform.localRotation*grip)*scale;
   holder.SetPositionAndRotation(hand.position+guard.transform.forward*.025f,Quaternion.LookRotation(Vector3.down,guard.transform.forward));holder.SetParent(hand,true);

  }
  [MenuItem("Athen Hill/Outer Berms/Install west gate checkpoint")]
  public static void Install()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first");
   var scene=EditorSceneManager.GetActiveScene();if(scene.path!="Assets/AthenHill/Scenes/AthenHill.unity")throw new Exception("Open saved Athen Hill scene first");
   var post=GameObject.Find("Outer Berms/Warden post").transform;if(post.Find("West Gate checkpoint"))throw new Exception("Checkpoint already installed; edit the saved objects");
   Directory.CreateDirectory(Evidence);File.Copy(scene.path,Evidence+"scene-before-checkpoint.unity",true);
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
   session=UnityEngine.Object.FindAnyObjectByType<GameSession>();ground=GameObject.Find("Berms ground").GetComponent<MeshCollider>();
   var root=new GameObject("West Gate checkpoint").transform;root.SetParent(post,false);
   var booth=Place(Art+"WardenBooth.glb",root,"Warden watch booth",new Vector3(-64,-1.02f,7));Proxies(booth);
   Sign(booth.transform,"West Gate sign","WEST GATE  /  WARDENS",new Vector3(0,2.39f,-2.405f),Vector3.zero,.035f);
   Sign(booth.transform,"Passage sign","OUTER BERMS   ·   CHECK IN WITH OSSA",new Vector3(0,2.05f,-1.82f),Vector3.zero,.018f);
   var ossa=post.Find("Warden Ossa").gameObject;ossa.transform.SetPositionAndRotation(At(-62.5f,4.3f),Quaternion.Euler(0,120,0));
   var o=Guard(ossa,"npc_ossa","Warden Ossa","West Gate watch",new[]{
    Node("greeting","West Gate watch","Ossa. West Gate watch. The cyan-lit ARMS LOCKER is beside this booth, to my right. Take the scrap pistol before you head onto the service road. Rell keeps the return lane clear.",Choice("locker","Where is the locker?","locker"),Choice("machines","What are those machines?","machines")),
    Node("locker","Arms issue","The tall green cabinet beside the booth has ARMS LOCKER written over the doors and a cyan strip on top. Walk up to it and press E. Press 7 to draw the pistol outside the walls; it runs on nano charge. The three range plates are just beyond the checkpoint.",Choice("back","Tell me about the machines.","machines"),Choice("leave","I'll check the locker.")),
    Node("machines","Industrial machines","The walkers are cargo-handling droids; the hovering ones are inspection and salvage drones. Feral industrial code makes them treat people as obstacles or raw material. The aquifer service droid inside Ward is maintained and loyal. Keep your aim on the hostile machines beyond the range.",Choice("range","How do I use the range?","range"),Choice("leave","Understood.")),
    Node("range","Safe range practice","Draw with 7. Hold right mouse to aim, then left click to fire; F fires from the hip. Knock down all three plates. Watch for the loose drone on the service road afterward. If you get hurt, break contact. Vitality recovers and nano refills when you stop firing.",Choice("back","Where was the locker?","locker"),Choice("leave","I'm ready."))});Arm(ossa);
   var rell=Place("Assets/AthenHill/Prefabs/WardGuard.prefab",root,"Warden Rell",At(-62.2f,-1.7f),270);
   var rguard=Guard(rell,"npc_rell","Warden Rell","Checkpoint sentry",new[]{
    Node("greeting","Checkpoint sentry","Rell. I'm watching the return lane. Check in with Ossa by the booth, collect your pistol from the marked locker, then try the range. Keep this gap clear; it is your way back to Ward.",Choice("safe","What if the machines chase me?","safe"),Choice("leave","I'll speak to Ossa.")),
    Node("safe","Berms patrol","Don't linger in reach of their clamps. The feral machines signal before they strike. Break contact toward the checkpoint if you need time to recover. Weapons are holstered automatically when you cross back inside Ward.",Choice("back","Where do I start?","greeting"),Choice("leave","Keep the lane clear. Got it."))});Arm(rell);
   session.npcs=session.npcs.Concat(new[]{o,rguard}).ToArray();EditorUtility.SetDirty(session);
   var tutorial=UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();tutorial.briefingWarden=ossa.transform;
   tutorial.lineStart="I'm Ossa, on West Gate watch. Take the scrap pistol from the cyan-lit ARMS LOCKER beside the booth. Then use the range beyond the barriers.";
   var locker=tutorial.locker.gameObject;
   // Keep original visual inactive and recoverable under the existing interaction root.
   foreach(var renderer in locker.GetComponentsInChildren<Renderer>())renderer.enabled=false;
   foreach(var collider in locker.GetComponents<Collider>())collider.enabled=false;
   var lamp=locker.GetComponentInChildren<Light>();if(lamp)lamp.transform.localPosition=new Vector3(0,1.8f,0);
   locker.transform.SetPositionAndRotation(new Vector3(-65.3f,-.88f,5.15f),Quaternion.identity);
   var cab=Place(Art+"ArmsLocker.glb",locker.transform,"Arms issue cabinet",locker.transform.position);cab.transform.localRotation=Quaternion.identity;Proxies(cab);
   tutorial.locker.prompt="E · Open ARMS LOCKER · Take scrap pistol";tutorial.locker.range=1.8f;
   Sign(cab.transform,"Arms locker lettering","ARMS LOCKER",new Vector3(0,1.59f,-.322f),Vector3.zero,.03f);
   Sign(cab.transform,"Pistol issue lettering","SCRAP PISTOL\nNANO CHARGE",new Vector3(0,.93f,-.335f),Vector3.zero,.016f);
   foreach(var p in new[]{new Vector3(-62.3f,0,-3.25f),new Vector3(-65.2f,0,-3.6f),new Vector3(-69.2f,0,-1.6f),new Vector3(-68.7f,0,5.5f)})
   {var b=Place(Art+"CheckpointBarrier.glb",root,"Checkpoint barrier",At(p.x,p.z),p.x<-68?32:0);Proxies(b);}
   // Water-supported shrubs along shaded wall and barrier edges; varied scale and rotation, lane kept clear.
   var shrub=UnityEngine.Object.FindObjectsByType<MeshRenderer>().First(x=>x.name=="Drum drought shrub").gameObject;
   var plants=new GameObject("Checkpoint foliage").transform;plants.SetParent(root,false);
   int i=0;foreach(var p in new[]{new Vector2(-60.9f,10.7f),new Vector2(-61.3f,12.0f),new Vector2(-64.2f,10.2f),new Vector2(-67.3f,8.8f),new Vector2(-68.7f,7.9f),new Vector2(-69.9f,6.5f),new Vector2(-63.4f,-5.6f),new Vector2(-65.1f,-6.1f),new Vector2(-68.1f,-4.7f),new Vector2(-70.2f,-3.8f)})
   {var g=UnityEngine.Object.Instantiate(shrub,plants);g.name="Drought shrub "+(++i);g.transform.SetPositionAndRotation(At(p.x,p.y,-.025f),Quaternion.Euler(0,i*137,0));g.transform.localScale=Vector3.one*(1.25f+(i%3)*.42f);g.GetComponent<Renderer>().enabled=true;var rb=g.GetComponent<Renderer>().bounds;g.transform.position+=Vector3.up*(At(p.x,p.y).y-rb.min.y+.02f);}
   // Marker board uses E and leaves the authored tutorial intact.
   var board=new GameObject("Checkpoint field briefing");board.transform.SetParent(root,false);board.transform.position=At(-61.4f,7.0f,.1f);
   var use=board.AddComponent<WorldInteractable>();use.prompt="E · Read checkpoint field briefing";use.range=2;
   var notice=board.AddComponent<CheckpointNotice>();notice.session=session;notice.message="WEST GATE: Speak to Ossa, collect the scrap pistol at the cyan-lit locker, then knock down the three range plates. Feral cargo droids and inspection drones patrol the old service road. The aquifer machine inside Ward is friendly. Keep the return lane clear.";
   Sign(board.transform,"Field briefing text","WEST GATE\nFIELD BRIEFING\nE · READ",new Vector3(0,1.55f,0),new Vector3(0,-90,0),.035f);
   // Saved landmarks support matched native review and real-input route checks.
   var marks=GameObject.Find("Landmarks").transform;
   Marker(marks,"checkpoint_approach",new Vector3(-57,.1f,1));Marker(marks,"checkpoint_ossa",At(-61.0f,3.3f));Marker(marks,"checkpoint_locker",new Vector3(-65.3f,-.88f,3.8f));Marker(marks,"checkpoint_rell",At(-60.9f,-1.8f));Marker(marks,"checkpoint_board",At(-60.3f,7));
   Camera(root,"cam_checkpoint_player",new Vector3(-59.8f,1.05f,1.8f),new Vector3(-64,.3f,6),65);
   Camera(root,"cam_checkpoint_locker",new Vector3(-64.0f,.72f,2.65f),new Vector3(-65.2f,.1f,5.3f),60);
   var circuit=UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();var added=new List<Light>();
   foreach(var t in booth.GetComponentsInChildren<Transform>())if(t.name.StartsWith("LIGHT_")){var l=t.gameObject.AddComponent<Light>();l.type=LightType.Point;l.color=new Color(1,.72f,.45f);l.intensity=1.3f;l.range=4;l.shadows=LightShadows.None;added.Add(l);}
   circuit.practicalLights=circuit.practicalLights.Concat(added).ToArray();EditorUtility.SetDirty(circuit);
   StaticRenderChunksEditor.Rebuild(chunks);EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
   File.WriteAllText(Evidence+"checkpoint-install.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{guards=new[]{"Warden Ossa","Warden Rell"},locker=new[]{locker.transform.position.x,locker.transform.position.y,locker.transform.position.z},shrubs=i,booth=new[]{booth.transform.position.x,booth.transform.position.y,booth.transform.position.z},tutorial_preserved=true,original_city_npcs=4},Newtonsoft.Json.Formatting.Indented));
  }
  [MenuItem("Athen Hill/Outer Berms/Finish west gate checkpoint")]
  public static void Finish()
  {
   session=UnityEngine.Object.FindAnyObjectByType<GameSession>();ground=GameObject.Find("Berms ground").GetComponent<MeshCollider>();
   var root=GameObject.Find("West Gate checkpoint").transform;
   if(root.Find("Checkpoint groundcover"))throw new Exception("Finishing pass already applied; edit saved content.");
   Arm(GameObject.Find("Warden Ossa"));Arm(GameObject.Find("Warden Rell"));
   var board=GameObject.Find("Checkpoint field briefing");board.transform.position=new Vector3(-62.27f,-1.02f,7);
   var panel=GameObject.CreatePrimitive(PrimitiveType.Cube);panel.name="Field briefing backing";panel.transform.SetParent(board.transform,false);panel.transform.localPosition=new Vector3(-.04f,1.5f,0);panel.transform.localScale=new Vector3(.08f,.75f,.68f);
   panel.GetComponent<Renderer>().sharedMaterial=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/BuildingMaterials/WardConcrete/WardConcrete.mat");
   var text=board.GetComponentInChildren<TextMesh>();text.transform.localPosition=new Vector3(.006f,1.52f,0);text.transform.localEulerAngles=new Vector3(0,-90,0);text.characterSize=.028f;
   // Baked groundcover cards use the existing wind/reduced-motion shader and actual terrain heights.
   var rng=new System.Random(2626);var v=new List<Vector3>();var uv=new List<Vector2>();var cols=new List<Color>();var ix=new List<int>();
   for(int i=0;i<180;i++)
   {
    bool north=i<90;float x=-70+(float)rng.NextDouble()*10,z=(north?9:-7)+(float)rng.NextDouble()*3;
    var c=At(x,z,-.01f);float h=.2f+(float)rng.NextDouble()*.27f,w=.32f+(float)rng.NextDouble()*.35f,a=(float)rng.NextDouble()*Mathf.PI;
    for(int j=0;j<2;j++){var d=new Vector3(Mathf.Cos(a+j*Mathf.PI/2),0,Mathf.Sin(a+j*Mathf.PI/2))*w*.5f;int n=v.Count;v.AddRange(new[]{c-d,c+d,c+d+Vector3.up*h,c-d+Vector3.up*h});uv.AddRange(new[]{Vector2.zero,Vector2.right,Vector2.one,Vector2.up});var color=new Color((float)rng.NextDouble(),(float)rng.NextDouble(),0,(float)rng.NextDouble());cols.AddRange(new[]{color,color,color,color});ix.AddRange(new[]{n,n+2,n+1,n,n+3,n+2});}
   }
   var mesh=new Mesh{name="Checkpoint groundcover"};mesh.SetVertices(v);mesh.SetUVs(0,uv);mesh.SetColors(cols);mesh.SetTriangles(ix,0);mesh.RecalculateNormals();mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,Art+"CheckpointGroundcover.asset");
   var grass=new GameObject("Checkpoint groundcover",typeof(MeshFilter),typeof(MeshRenderer));grass.transform.SetParent(root,false);grass.GetComponent<MeshFilter>().sharedMesh=mesh;grass.GetComponent<MeshRenderer>().sharedMaterial=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/Atmosphere/HillGrass.mat");grass.GetComponent<MeshRenderer>().shadowCastingMode=ShadowCastingMode.Off;
   var circuit=UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();EditorUtility.SetDirty(circuit);
   EditorSceneManager.SaveOpenScenes();AssetDatabase.SaveAssets();
   File.WriteAllText(Evidence+"checkpoint-install.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{guards=new[]{"Warden Ossa","Warden Rell"},groundcover_tufts=180,shrubs=10,all_robot_models_preserved=true,worker_and_mining_droids_preserved=true,locker=new[]{-65.3f,-.88f,5.15f}},Newtonsoft.Json.Formatting.Indented));
  }
  static void Marker(Transform p,string name,Vector3 pos){var g=new GameObject(name);g.transform.SetParent(p,true);g.transform.position=pos;}
  static void Camera(Transform p,string name,Vector3 pos,Vector3 target,float fov){var g=new GameObject(name,typeof(Camera));g.transform.SetParent(p,true);g.transform.position=pos;g.transform.LookAt(target);var c=g.GetComponent<Camera>();c.enabled=false;c.fieldOfView=fov;c.farClipPlane=650;}
 }
}
