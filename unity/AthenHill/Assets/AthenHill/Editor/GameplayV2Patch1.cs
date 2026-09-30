using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Editor
{
 /// Gameplay v2 fixes, patch 1 (30 September 2026): the scene-serialized part of the native QA fixes.
 /// Batch: Unity -batchmode -projectPath … -executeMethod AthenHill.Editor.GameplayV2Patch1.ApplyBatch -logFile …
 /// (exits by itself: 0 = applied, 1 = refused or failed; read the single GAMEPLAY_V2_PATCH1 {…} log line).
 ///  1. Depot nest re-form: clearance 35 → 55 m (the field fabricator, 38.9 m away, now counts as "near") and the
 ///     player must have stayed away 45 s; BermsTutorial.depotRespawnSeconds 240 (was a hard-coded 120).
 ///  2. Depot Foreman: two worker escorts spawn with it (clear capsule points beside it in the processing hall);
 ///     the same re-form rule (55 m, 45 s away).
 ///  3. Salvage nodes: prompts and progress labels name what is searched (heap, debris, carcass, crashed drone).
 /// Requires the GameplayV2Installer marker; refuses to run twice (its own marker) or over unsaved scene edits; finds
 /// everything by name and component; never moves existing objects; checks render-chunk sources are untouched.
 public static class GameplayV2Patch1
 {
  public const string MarkerName="Gameplay v2 · patch 1 (GameplayV2Patch1)";
  public const float NestClearance=55,AwaySeconds=45,DepotRespawnSeconds=240;
  const string WorkerPrefab="Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab";
  // Escort candidates relative to the Foreman spawn (metres, X/Z); the first two clear ones are used.
  static readonly Vector2[] EscortOffsets={new(2.4f,1.2f),new(-2.4f,1.2f),new(2.6f,-1.0f),new(-2.6f,-1.0f),new(1.2f,2.6f),new(-1.2f,2.6f),new(3.2f,0f),new(-3.2f,0f),new(0f,3.0f)};
  /// Per node display name: ready prompt, searching prompt, progress label.
  public static readonly Dictionary<string,(string ready,string searching,string progress)> Prompts=new Dictionary<string,(string,string,string)>
  {
   {"Scrap heap",("E · Search the scrap heap","Searching the scrap heap… hold still","Searching the scrap heap…")},
   {"Machine debris",("E · Search the machine debris","Searching the debris… hold still","Searching the machine debris…")},
   {"Worker droid carcass",("E · Strip the droid carcass","Stripping the carcass… hold still","Stripping the droid carcass…")},
   {"Mining droid carcass",("E · Strip the mining droid carcass","Stripping the carcass… hold still","Stripping the mining droid carcass…")},
   {"Crashed drone",("E · Salvage the crashed drone","Salvaging the drone… hold still","Salvaging the crashed drone…")},
   {"Roadside scrap",("E · Search the roadside scrap","Searching the scrap… hold still","Searching the roadside scrap…")},
  };

  public static void ApplyBatch()
  {
   int code=0;
   try{var record=Apply();Debug.Log("GAMEPLAY_V2_PATCH1 "+JsonConvert.SerializeObject(record));}
   catch(Exception e){code=1;Debug.LogWarning("GAMEPLAY_V2_PATCH1 "+JsonConvert.SerializeObject(new{ok=false,error=e.Message}));}
   EditorApplication.Exit(code);
  }
  [MenuItem("Athen Hill/Gameplay v2/Apply patch 1 (QA fixes)")]
  public static void ApplyMenu(){var record=Apply();Debug.Log("GAMEPLAY_V2_PATCH1 "+JsonConvert.SerializeObject(record));}

  public static Dictionary<string,object> Apply()
  {
   var record=new Dictionary<string,object>{{"ok",true},{"utc",DateTime.UtcNow.ToString("o")},{"scene",ImportBaseline.ScenePath}};
   var scene=EditorSceneManager.GetActiveScene();
   if(scene.path==ImportBaseline.ScenePath){if(scene.isDirty)throw new InvalidOperationException("AthenHill.unity has unsaved edits. Save or revert them, then run GameplayV2Patch1.");}
   else
   {
    for(int i=0;i<EditorSceneManager.sceneCount;i++)if(EditorSceneManager.GetSceneAt(i).isDirty)throw new InvalidOperationException("An open scene has unsaved edits. Save or revert them first.");
    scene=EditorSceneManager.OpenScene(ImportBaseline.ScenePath,OpenSceneMode.Single);
   }
   var all=scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<Transform>(true)).ToList();
   if(all.Any(t=>t.name==MarkerName))throw new InvalidOperationException("Patch 1 is already applied (marker '"+MarkerName+"'). Edit the patched objects instead.");
   if(!all.Any(t=>t.name==GameplayV2Installer.MarkerName))throw new InvalidOperationException("Gameplay v2 is not installed in this scene; run GameplayV2Installer.InstallBatch first.");
   var session=Single<GameSession>();var crafting=session.GetComponent<CraftingSession>();var tutorial=Single<BermsTutorial>();
   var depot=tutorial.depot;if(!depot)throw new InvalidOperationException("BermsTutorial has no depot encounter.");
   var foreman=UnityEngine.Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include,FindObjectsSortMode.None).SingleOrDefault(e=>e.name==GameplayV2Installer.ForemanEncounterName);
   if(!foreman)throw new InvalidOperationException("Encounter '"+GameplayV2Installer.ForemanEncounterName+"' not found.");
   if(foreman.spawns.Length!=1||!foreman.spawns[0].prefab||!foreman.spawns[0].point)throw new InvalidOperationException("The Foreman encounter should have exactly its one Foreman spawn before patch 1 (found "+foreman.spawns.Length+").");
   var worker=AssetDatabase.LoadAssetAtPath<GameObject>(WorkerPrefab);var workerDroid=worker?worker.GetComponent<FeralDroid>():null;
   if(!workerDroid)throw new InvalidOperationException("Missing "+WorkerPrefab);
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
   string fingerprint=chunks?StaticRenderChunksEditor.Fingerprint(chunks):null;
   if(chunks&&(chunks.editingSources||chunks.sourceFingerprint!=fingerprint))throw new InvalidOperationException("City render chunks are stale or showing sources; rebuild and save before patching.");
   Physics.SyncTransforms();
   var created=new List<Transform>();

   // 1. Depot nest re-form rule.
   float fabToDepot=crafting&&crafting.fabricator?Flat(crafting.fabricator.position-depot.transform.position):-1;
   float fabToForeman=crafting&&crafting.fabricator?Flat(crafting.fabricator.position-foreman.transform.position):-1;
   record["depot"]=new{name=depot.name,respawnClearance=new[]{depot.respawnClearance,NestClearance},awaySeconds=new[]{depot.awaySeconds,AwaySeconds},respawnSecondsSerialized=depot.respawnSeconds,tutorialDepotRespawnSeconds=new[]{tutorial.depotRespawnSeconds,DepotRespawnSeconds},fabricatorDistance=R(fabToDepot)};
   Undo.RecordObject(depot,"Gameplay v2 patch 1");depot.respawnClearance=NestClearance;depot.awaySeconds=AwaySeconds;EditorUtility.SetDirty(depot);
   Undo.RecordObject(tutorial,"Gameplay v2 patch 1");tutorial.depotRespawnSeconds=DepotRespawnSeconds;EditorUtility.SetDirty(tutorial);
   if(fabToDepot>=0&&fabToDepot>=NestClearance)throw new InvalidOperationException($"The field fabricator is {fabToDepot:0.0} m from the depot nest, outside the new clearance; review NestClearance.");

   // 2. Foreman escorts: clear capsule spots beside the Foreman, away from the depot nest spawns.
   var fp=foreman.spawns[0].point.position;
   var spots=new List<Vector3>();
   foreach(var o in EscortOffsets)
   {
    if(spots.Count==2)break;
    if(!Ground(new Vector3(fp.x+o.x,fp.y+2.5f,fp.z+o.y),5,out var at))continue;
    if(Mathf.Abs(at.y-fp.y)>.8f)continue; // same floor as the Foreman
    if(Physics.CheckCapsule(at+Vector3.up*.65f,at+Vector3.up*2.4f,.5f,~(1<<8),QueryTriggerInteraction.Ignore))continue;
    if(Physics.Linecast(fp+Vector3.up*1.2f,at+Vector3.up*1.2f,~(1<<8),QueryTriggerInteraction.Ignore))continue; // no wall between them
    if(depot.spawns.Any(s=>s.point&&Flat(s.point.position-at)<2.5f))continue;
    if(spots.Any(s=>Flat(s-at)<1.8f))continue;
    spots.Add(at);
   }
   if(spots.Count<2)throw new InvalidOperationException("No two clear escort spots beside the Foreman spawn; check the processing hall layout.");
   var spawns=foreman.spawns.ToList();var escorts=new List<object>();
   var toYard=depot.transform.position-fp;toYard.y=0;
   for(int i=0;i<spots.Count;i++)
   {
    var point=new GameObject($"Spawn {i+2} · FeralWorkerDroid (escort)");point.transform.SetParent(foreman.transform,false);point.transform.position=spots[i];
    if(toYard.sqrMagnitude>.01f)point.transform.rotation=Quaternion.LookRotation(toYard);
    Undo.RegisterCreatedObjectUndo(point,"Gameplay v2 patch 1");created.Add(point.transform);
    spawns.Add(new DroidEncounter.Spawn{prefab=workerDroid,point=point.transform});
    escorts.Add(new{point=point.name,position=V(spots[i]),fromForeman=R(Flat(spots[i]-fp))});
   }
   Undo.RecordObject(foreman,"Gameplay v2 patch 1");
   record["foreman"]=new{name=foreman.name,escorts,respawnClearance=new[]{foreman.respawnClearance,NestClearance},awaySeconds=new[]{foreman.awaySeconds,AwaySeconds},respawnSeconds=foreman.respawnSeconds,fabricatorDistance=R(fabToForeman)};
   foreman.spawns=spawns.ToArray();foreman.respawnClearance=NestClearance;foreman.awaySeconds=AwaySeconds;EditorUtility.SetDirty(foreman);

   // 3. Salvage node wording.
   var nodes=new List<object>();
   foreach(var node in UnityEngine.Object.FindObjectsByType<SalvageNode>(FindObjectsInactive.Include,FindObjectsSortMode.None).OrderBy(n=>n.name,StringComparer.Ordinal))
   {
    var name=node.displayName??"Scrap heap";
    (string ready,string searching,string progress) words=Prompts.TryGetValue(name,out var p)?p:($"E · Search the {name.ToLowerInvariant()}",$"Searching the {name.ToLowerInvariant()}… hold still",$"Searching the {name.ToLowerInvariant()}…");
    Undo.RecordObject(node,"Gameplay v2 patch 1");
    node.readyPrompt=words.ready;node.searchingPrompt=words.searching;node.progressLabel=words.progress;
    EditorUtility.SetDirty(node);
    nodes.Add(new{node=node.name,displayName=name,prompt=words.ready});
   }
   record["salvageNodes"]=nodes;

   // 4. Marker (editor-only; stripped from builds).
   var marker=new GameObject(MarkerName){tag="EditorOnly"};marker.transform.SetParent(session.transform,false);created.Add(marker.transform);

   if(chunks)
   {
    foreach(var t in created)if(chunks.sourceRoots.Any(r=>r&&t.IsChildOf(r)))throw new InvalidOperationException(t.name+" landed under a render-chunk source root.");
    if(StaticRenderChunksEditor.Fingerprint(chunks)!=fingerprint)throw new InvalidOperationException("Render-chunk sources changed during the patch; aborting without saving.");
   }
   EditorSceneManager.MarkSceneDirty(scene);
   if(!EditorSceneManager.SaveScene(scene))throw new Exception("Saving AthenHill.unity failed.");
   record["created"]=created.Select(Path).ToArray();
   record["fieldsSet"]=new[]{depot.name+"/DroidEncounter.respawnClearance,awaySeconds",tutorial.name+"/BermsTutorial.depotRespawnSeconds",foreman.name+"/DroidEncounter.spawns,respawnClearance,awaySeconds","SalvageNode.readyPrompt,searchingPrompt,progressLabel ×"+nodes.Count};
   return record;
  }
  static T Single<T>()where T:UnityEngine.Object{var all=UnityEngine.Object.FindObjectsByType<T>(FindObjectsInactive.Include,FindObjectsSortMode.None);if(all.Length!=1)throw new InvalidOperationException($"Expected exactly one {typeof(T).Name}, found {all.Length}.");return all[0];}
  static bool Ground(Vector3 from,float drop,out Vector3 at)
  {
   at=from;
   var hits=Physics.RaycastAll(from,Vector3.down,drop,~(1<<8),QueryTriggerInteraction.Ignore);
   if(hits.Length==0)return false;
   at=hits.OrderByDescending(h=>h.point.y).First().point;return true;
  }
  static float Flat(Vector3 v){v.y=0;return v.magnitude;}
  static float R(float v)=>(float)Math.Round(v,2);
  static float[] V(Vector3 v)=>new[]{R(v.x),R(v.y),R(v.z)};
  static string Path(Transform t)=>t.parent?Path(t.parent)+"/"+t.name:t.name;
 }
}
