using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Editor
{
 /// Gameplay v2 fixes, patch 2 (30 September 2026, after the native re-QA): the scene-serialized part of the second
 /// fix batch. Batch: Unity -batchmode -projectPath … -executeMethod AthenHill.Editor.GameplayV2Patch2.ApplyBatch
 /// -logFile … (exits by itself: 0 = applied, 1 = refused or failed; read the single GAMEPLAY_V2_PATCH2 {…} line).
 ///  1. Heap names agree with what they are: the depot's litter is "Depot litter", the two roadside heaps are
 ///     "Roadside scrap" (prompts, searching prompts and progress labels to match).
 /// Everything else in the batch (radio, caches, droid culling, UI) lives in code, prefabs and data assets.
 /// Requires the Patch 1 marker; refuses to run twice (its own marker) or over unsaved scene edits; finds objects by
 /// name and component; never moves anything; checks render-chunk sources are untouched.
 public static class GameplayV2Patch2
 {
  public const string MarkerName="Gameplay v2 · patch 2 (GameplayV2Patch2)";
  /// Node GameObject name → display name, ready prompt, searching prompt, progress label.
  public static readonly Dictionary<string,(string name,string ready,string searching,string progress)> Nodes=new Dictionary<string,(string,string,string,string)>
  {
   {"Salvage node · Depot litter",("Depot litter","E · Search the depot litter","Searching the litter… hold still","Searching the depot litter…")},
   {"Salvage node · Roadside scrap heap (first contact)",("Roadside scrap","E · Search the roadside scrap","Searching the scrap… hold still","Searching the roadside scrap…")},
   {"Salvage node · Roadside scrap heap (mound)",("Roadside scrap","E · Search the roadside scrap","Searching the scrap… hold still","Searching the roadside scrap…")},
  };

  public static void ApplyBatch()
  {
   int code=0;
   try{Debug.Log("GAMEPLAY_V2_PATCH2 "+JsonConvert.SerializeObject(Apply()));}
   catch(Exception e){code=1;Debug.LogWarning("GAMEPLAY_V2_PATCH2 "+JsonConvert.SerializeObject(new{ok=false,error=e.Message}));}
   EditorApplication.Exit(code);
  }
  [MenuItem("Athen Hill/Gameplay v2/Apply patch 2 (re-QA fixes)")]
  public static void ApplyMenu()=>Debug.Log("GAMEPLAY_V2_PATCH2 "+JsonConvert.SerializeObject(Apply()));

  public static Dictionary<string,object> Apply()
  {
   var record=new Dictionary<string,object>{{"ok",true},{"utc",DateTime.UtcNow.ToString("o")},{"scene",ImportBaseline.ScenePath}};
   var scene=EditorSceneManager.GetActiveScene();
   if(scene.path==ImportBaseline.ScenePath){if(scene.isDirty)throw new InvalidOperationException("AthenHill.unity has unsaved edits. Save or revert them, then run GameplayV2Patch2.");}
   else
   {
    for(int i=0;i<EditorSceneManager.sceneCount;i++)if(EditorSceneManager.GetSceneAt(i).isDirty)throw new InvalidOperationException("An open scene has unsaved edits. Save or revert them first.");
    scene=EditorSceneManager.OpenScene(ImportBaseline.ScenePath,OpenSceneMode.Single);
   }
   var all=scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<Transform>(true)).ToList();
   if(all.Any(t=>t.name==MarkerName))throw new InvalidOperationException("Patch 2 is already applied (marker '"+MarkerName+"').");
   if(!all.Any(t=>t.name==GameplayV2Patch1.MarkerName))throw new InvalidOperationException("Patch 1 is not applied in this scene; run GameplayV2Patch1.ApplyBatch first.");
   var sessions=UnityEngine.Object.FindObjectsByType<GameSession>(FindObjectsInactive.Include,FindObjectsSortMode.None);
   if(sessions.Length!=1)throw new InvalidOperationException("Expected exactly one GameSession, found "+sessions.Length+".");
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
   string fingerprint=chunks?StaticRenderChunksEditor.Fingerprint(chunks):null;
   if(chunks&&(chunks.editingSources||chunks.sourceFingerprint!=fingerprint))throw new InvalidOperationException("City render chunks are stale or showing sources; rebuild and save before patching.");

   var nodes=UnityEngine.Object.FindObjectsByType<SalvageNode>(FindObjectsInactive.Include,FindObjectsSortMode.None);
   var changed=new List<object>();
   foreach(var pair in Nodes)
   {
    var node=nodes.SingleOrDefault(n=>n.name==pair.Key);
    if(!node)throw new InvalidOperationException("Salvage node '"+pair.Key+"' not found.");
    var w=pair.Value;
    changed.Add(new{node=node.name,displayName=new[]{node.displayName,w.name},prompt=new[]{node.readyPrompt,w.ready}});
    Undo.RecordObject(node,"Gameplay v2 patch 2");
    node.displayName=w.name;node.readyPrompt=w.ready;node.searchingPrompt=w.searching;node.progressLabel=w.progress;
    EditorUtility.SetDirty(node);
   }
   record["salvageNodes"]=changed;

   var marker=new GameObject(MarkerName){tag="EditorOnly"};marker.transform.SetParent(sessions[0].transform,false);
   if(chunks&&StaticRenderChunksEditor.Fingerprint(chunks)!=fingerprint)throw new InvalidOperationException("Render-chunk sources changed during the patch; aborting without saving.");
   EditorSceneManager.MarkSceneDirty(scene);
   if(!EditorSceneManager.SaveScene(scene))throw new Exception("Saving AthenHill.unity failed.");
   record["created"]=new[]{sessions[0].name+"/"+MarkerName};
   return record;
  }
 }
}
