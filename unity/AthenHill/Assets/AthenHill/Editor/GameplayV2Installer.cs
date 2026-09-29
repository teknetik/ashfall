using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Editor
{
 /// One-time, idempotent scene installer for Gameplay v2 "Scavenger's Arc" (29 September 2026).
 /// Batch: Unity -batchmode -projectPath … -executeMethod AthenHill.Editor.GameplayV2Installer.InstallBatch -quit
 /// It finds everything by name and component (never by fileID), refuses to run twice (its marker object) or over
 /// unsaved scene edits, never moves or deletes existing gameplay roots, routes, NPCs or colliders, keeps render-chunk
 /// sources untouched, saves the scene and logs every change as one JSON line (GAMEPLAY_V2_INSTALL …).
 public static class GameplayV2Installer
 {
  public const string MarkerName="Gameplay v2 · installed (GameplayV2Installer)";
  public const string ForemanEncounterName="Depot Foreman · processing hall";
  public const string HeapGroupName="Salvage heaps";
  // Existing depot props that become searchable (path under "Outer Berms", loot table, display name, prompt range).
  static readonly (string path,string table,string name,float range)[] PropNodes=
  {
   ("Machine depot/Depot rebuild/Scrap/Stripped scrap heap","loot_scrap_heap","Scrap heap",3.4f),
   ("Machine depot/Depot rebuild/Scrap/Machine debris","loot_scrap_heap","Machine debris",2.6f),
   ("Machine depot/Depot rebuild/Scrap/Machine debris (hall)","loot_scrap_heap","Machine debris",2.6f),
   ("Machine depot/Depot rebuild/Scrap/Stripped worker droid carcass","loot_wreck_carcass","Worker droid carcass",2.4f),
   ("Machine depot/Depot rebuild/Scrap/Crashed scrap drone","loot_drone_wreck","Crashed drone",2.2f),
   ("Machine depot/Stripped mining droid carcass","loot_wreck_carcass","Mining droid carcass",3.0f),
   ("Machine depot/Depot litter","loot_scrap_heap","Roadside scrap",2.2f),
  };
  // Two new small heaps (the Meshy industrial-scrap prop, uniform scale) off the service road, ≥4 m from its centre line.
  static readonly (string name,float x,float z,float yaw)[] RoadsideHeaps={("Roadside scrap heap (first contact)",-88.5f,-17.5f,35f),("Roadside scrap heap (mound)",-78.5f,-27f,-60f)};
  static readonly Vector2[] ForemanCandidates={new(-81f,-45.8f),new(-80.5f,-44.6f),new(-82f,-46.4f),new(-79.6f,-44.2f),new(-81.4f,-43.8f)};

  public static void InstallBatch(){var record=Install();Debug.Log("GAMEPLAY_V2_INSTALL "+JsonConvert.SerializeObject(record));}
  [MenuItem("Athen Hill/Gameplay v2/Install Scavenger's Arc into the scene")]
  public static void InstallMenu()=>InstallBatch();

  public static Dictionary<string,object> Install()
  {
   var record=new Dictionary<string,object>{{"utc",DateTime.UtcNow.ToString("o")},{"scene",ImportBaseline.ScenePath}};
   var scene=EditorSceneManager.GetActiveScene();
   if(scene.path==ImportBaseline.ScenePath){if(scene.isDirty)throw new InvalidOperationException("AthenHill.unity has unsaved edits. Save or revert them, then run the Gameplay v2 installer.");}
   else
   {
    for(int i=0;i<EditorSceneManager.sceneCount;i++)if(EditorSceneManager.GetSceneAt(i).isDirty)throw new InvalidOperationException("An open scene has unsaved edits. Save or revert them first.");
    scene=EditorSceneManager.OpenScene(ImportBaseline.ScenePath,OpenSceneMode.Single);
   }
   var roots=scene.GetRootGameObjects();
   if(roots.SelectMany(r=>r.GetComponentsInChildren<Transform>(true)).Any(t=>t.name==MarkerName))
    throw new InvalidOperationException("Gameplay v2 is already installed in this scene (marker '"+MarkerName+"'). Edit the installed objects instead.");
   var session=Single<GameSession>();var crafting=session.GetComponent<CraftingSession>();
   var tutorial=Single<BermsTutorial>();var combat=Single<PlayerCombat>();
   if(!crafting)throw new InvalidOperationException("CraftingSession missing on "+session.name+"; the crafting slice must be installed first.");
   if(session.GetComponent<FieldOrders>())throw new InvalidOperationException("FieldOrders already exists on "+session.name+"; refusing to add a second.");
   if(session.GetComponent<WardSaveGame>())throw new InvalidOperationException("WardSaveGame already exists on "+session.name+"; refusing to add a second.");
   var berms=roots.FirstOrDefault(r=>r.name=="Outer Berms")?.transform;if(!berms)throw new InvalidOperationException("'Outer Berms' root missing.");
   var encounters=berms.Find("Encounters");if(!encounters)throw new InvalidOperationException("'Outer Berms/Encounters' missing.");
   if(!tutorial.depot)throw new InvalidOperationException("BermsTutorial has no depot encounter.");
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
   string fingerprint=chunks?StaticRenderChunksEditor.Fingerprint(chunks):null;
   if(chunks&&(chunks.editingSources||chunks.sourceFingerprint!=fingerprint))throw new InvalidOperationException("City render chunks are stale or showing sources; rebuild and save before installing.");

   var cachePrefab=Load<GameObject>(GameplayV2Content.CachePrefab);var nodePrefab=Load<GameObject>(GameplayV2Content.NodePrefab);
   var foremanPrefab=Load<GameObject>(GameplayV2Content.ForemanPrefab);var orderSet=Load<FieldOrderSet>(GameplayV2Content.OrdersPath);
   var scrapPrefab=Load<GameObject>("Assets/AthenHill/Prefabs/Salvage/scrap.prefab");
   Physics.SyncTransforms();
   var created=new List<Transform>();

   // 1. Droid wrecks drop physical caches.
   crafting.cachePrefab=cachePrefab.GetComponent<SalvageCache>();EditorUtility.SetDirty(crafting);
   record["cachePrefab"]=GameplayV2Content.CachePrefab;

   // 2. Depot Foreman encounter (inactive until field order 4 activates it).
   Vector3 spawnAt=Vector3.zero;bool found=false;
   foreach(var c in ForemanCandidates)
   {
    if(!Ground(new Vector3(c.x,3.5f,c.y),4,out var p))continue;
    if(Physics.CheckCapsule(p+Vector3.up*.7f,p+Vector3.up*2.8f,.55f,~(1<<8),QueryTriggerInteraction.Ignore))continue;
    if(tutorial.depot.spawns.Any(s=>s.point&&Flat(s.point.position-p)<2.5f))continue;
    spawnAt=p;found=true;break;
   }
   if(!found)throw new InvalidOperationException("No clear Foreman spawn point in the processing hall; check the depot layout.");
   var enc=new GameObject(ForemanEncounterName);enc.transform.SetParent(encounters,false);enc.transform.position=spawnAt;created.Add(enc.transform);
   var point=new GameObject("Spawn 1 · FeralDepotForeman");point.transform.SetParent(enc.transform,false);point.transform.position=spawnAt;
   var toYard=Flat3(tutorial.depot.transform.position-spawnAt);if(toYard.sqrMagnitude>.01f)point.transform.rotation=Quaternion.LookRotation(toYard);
   var foreman=enc.AddComponent<DroidEncounter>();
   foreman.displayName="Depot Foreman";foreman.spawns=new[]{new DroidEncounter.Spawn{prefab=foremanPrefab.GetComponent<FeralDroid>(),point=point.transform}};
   foreman.player=combat;foreman.session=session;foreman.respawnSeconds=300;foreman.respawnClearance=35;
   record["foremanEncounter"]=new{name=enc.name,position=V(spawnAt),respawnSeconds=foreman.respawnSeconds};

   // 3. Searchable scrap heaps on existing depot scrap and two new roadside heaps.
   var group=new GameObject(HeapGroupName).transform;group.SetParent(berms,false);created.Add(group);
   var nodes=new List<object>();
   SalvageNode Node(string name,Vector3 at,string table,string display,float range)
   {
    var go=(GameObject)PrefabUtility.InstantiatePrefab(nodePrefab,scene);go.name="Salvage node · "+name;go.transform.SetParent(group,true);go.transform.position=at;
    var node=go.GetComponent<SalvageNode>();node.crafting=crafting;node.lootTableId=table;node.displayName=display;
    var use=go.GetComponent<WorldInteractable>();use.range=range;
    nodes.Add(new{node=go.name,position=V(at),table,range});
    return node;
   }
   foreach(var (path,table,display,range) in PropNodes)
   {
    var prop=FindActive(berms,path);
    if(!prop)throw new InvalidOperationException("Depot prop 'Outer Berms/"+path+"' not found (active); check the depot scene.");
    Node(prop.name,prop.position,table,display,range);
   }
   foreach(var (name,x,z,yaw) in RoadsideHeaps)
   {
    if(!Ground(new Vector3(x,20,z),30,out var at))throw new InvalidOperationException("No Berms ground under "+name);
    var heap=(GameObject)PrefabUtility.InstantiatePrefab(scrapPrefab,scene);heap.name=name;heap.transform.SetParent(group,true);
    heap.transform.SetPositionAndRotation(at,Quaternion.Euler(0,yaw,0));heap.transform.localScale=Vector3.one*.85f;
    var node=Node(name,at,"loot_scrap_heap","Scrap heap",2.4f);node.transform.SetParent(heap.transform,true);
   }
   record["heaps"]=nodes;
   // Keep every interactable reachable: colonists and Wardens win within 2.4 m, so heaps must stay clear of them.
   foreach(var npc in session.npcs.Where(n=>n))foreach(var n in group.GetComponentsInChildren<SalvageNode>())
    if(Vector3.Distance(npc.transform.position,n.transform.position)<2.4f+n.GetComponent<WorldInteractable>().range)throw new InvalidOperationException(n.name+" is too close to "+npc.name);

   // 4. Ossa's field orders on the city session.
   var orders=session.gameObject.AddComponent<FieldOrders>();
   orders.data=orderSet;orders.crafting=crafting;orders.tutorial=tutorial;orders.combat=combat;
   orders.guidanceTargets=new[]
   {
    new FieldOrders.Target{key="fabricator",label="FIELD FABRICATOR",point=crafting.fabricator},
    new FieldOrders.Target{key="depot",label="MACHINE DEPOT",point=tutorial.depot.transform},
    new FieldOrders.Target{key="foreman",label="DEPOT FOREMAN",point=point.transform},
   };
   orders.encounters=new[]{new FieldOrders.EncounterBinding{key="foreman",encounter=foreman}};
   if(!crafting.fabricator)throw new InvalidOperationException("CraftingSession.fabricator is not set.");
   record["fieldOrders"]=new{asset=GameplayV2Content.OrdersPath,orders=orderSet.orders.Select(o=>o.id).ToArray()};
   // 4b. Save game (Continue / New Game, autosave).
   var save=session.gameObject.AddComponent<WardSaveGame>();
   record["saveGame"]=new{save.fileName,location="Application.persistentDataPath (development --athen-qa runs: <qa>/save; --athen-save-dir overrides)"};

   // 5. QA landmarks (editable markers; moving them does not move gameplay).
   var landmarks=roots.FirstOrDefault(r=>r.name=="Landmarks");
   if(landmarks)
   {
    foreach(var (name,at) in new[]{("berms_foreman_hall",spawnAt+Vector3.forward*4.5f),("berms_scrap_heap",group.GetChild(0).position+Vector3.forward*2.2f)})
    {if(landmarks.transform.Find(name))continue;var m=new GameObject(name);m.transform.SetParent(landmarks.transform,false);m.transform.position=at;created.Add(m.transform);}
   }

   // 6. Marker (editor-only; stripped from builds).
   var marker=new GameObject(MarkerName){tag="EditorOnly"};marker.transform.SetParent(session.transform,false);created.Add(marker.transform);

   if(chunks)
   {
    foreach(var t in created)if(chunks.sourceRoots.Any(r=>r&&t.IsChildOf(r)))throw new InvalidOperationException(t.name+" landed under a render-chunk source root.");
    if(StaticRenderChunksEditor.Fingerprint(chunks)!=fingerprint)throw new InvalidOperationException("Render-chunk sources changed during install; aborting without saving.");
   }
   EditorUtility.SetDirty(session);EditorUtility.SetDirty(crafting);
   EditorSceneManager.MarkSceneDirty(scene);
   if(!EditorSceneManager.SaveScene(scene))throw new Exception("Saving AthenHill.unity failed.");
   record["created"]=created.Select(t=>Path(t)).ToArray();
   record["componentsAdded"]=new[]{session.name+"/FieldOrders",session.name+"/WardSaveGame"};
   record["fieldsSet"]=new[]{session.name+"/CraftingSession.cachePrefab"};
   return record;
  }
  static T Single<T>()where T:UnityEngine.Object{var all=UnityEngine.Object.FindObjectsByType<T>(FindObjectsInactive.Include,FindObjectsSortMode.None);if(all.Length!=1)throw new InvalidOperationException($"Expected exactly one {typeof(T).Name}, found {all.Length}.");return all[0];}
  static T Load<T>(string path)where T:UnityEngine.Object{var a=AssetDatabase.LoadAssetAtPath<T>(path);if(!a)throw new InvalidOperationException("Missing asset "+path);return a;}
  /// Active descendant by path; duplicate sibling names (e.g. inactive retired props) are skipped.
  static Transform FindActive(Transform root,string path)
  {
   var current=new List<Transform>{root};
   foreach(var part in path.Split('/'))current=current.SelectMany(t=>t.Cast<Transform>()).Where(c=>c.name==part&&c.gameObject.activeInHierarchy).ToList();
   return current.FirstOrDefault();
  }
  /// Highest non-trigger surface below a point within a drop distance (ignores the player's layer).
  static bool Ground(Vector3 from,float drop,out Vector3 at)
  {
   at=from;
   var hits=Physics.RaycastAll(from,Vector3.down,drop,~(1<<8),QueryTriggerInteraction.Ignore);
   if(hits.Length==0)return false;
   at=hits.OrderByDescending(h=>h.point.y).First().point;return true;
  }
  static float Flat(Vector3 v){v.y=0;return v.magnitude;}
  static Vector3 Flat3(Vector3 v){v.y=0;return v;}
  static float[] V(Vector3 v)=>new[]{(float)Math.Round(v.x,2),(float)Math.Round(v.y,2),(float)Math.Round(v.z,2)};
  static string Path(Transform t)=>t.parent?Path(t.parent)+"/"+t.name:t.name;
 }
}
