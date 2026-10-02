using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace AthenHill.Tests
{
 /// Gameplay v2 M3: the saved scene after GameplayV2Installer — wiring, placements and untouched gameplay roots.
 public class GameplayV2SceneTests
 {
  const string ScenePath="Assets/AthenHill/Scenes/AthenHill.unity";
  static T[] All<T>(Scene scene)where T:Component=>scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<T>(true)).ToArray();
  static float Flat(Vector3 v){v.y=0;return v.magnitude;}

  [Test] public void InstallerWiredOrdersCachesHeapsAndTheForeman()
  {
   var scene=EditorSceneManager.OpenPreviewScene(ScenePath);
   try
   {
    var session=All<GameSession>(scene).Single();var crafting=session.GetComponent<CraftingSession>();
    Assert.That(session.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="Gameplay v2 · installed (GameplayV2Installer)"),"installer marker");
    Assert.That(crafting.cachePrefab,Is.Not.Null);
    var save=session.GetComponent<WardSaveGame>();Assert.That(save,Is.Not.Null);Assert.That(save.fileName,Is.EqualTo("ward-save.json"));Assert.That(save.directoryOverride,Is.Empty.Or.Null);
    Assert.That(AssetDatabase.GetAssetPath(crafting.cachePrefab),Is.EqualTo("Assets/AthenHill/Prefabs/OuterBerms/SalvageCache.prefab"));
    var orders=session.GetComponent<FieldOrders>();
    Assert.That(orders,Is.Not.Null);Assert.That(orders.data,Is.Not.Null);Assert.That(orders.crafting,Is.EqualTo(crafting));
    Assert.That(orders.tutorial,Is.EqualTo(All<BermsTutorial>(scene).Single()));Assert.That(orders.combat,Is.EqualTo(All<PlayerCombat>(scene).Single()));
    foreach(var key in orders.data.orders.Select(o=>o.guidance).Where(k=>!string.IsNullOrEmpty(k)).Append("fabricator").Distinct())
     Assert.That(orders.guidanceTargets.Any(t=>t.key==key&&t.point&&!string.IsNullOrEmpty(t.label)),"guidance "+key);
    foreach(var key in orders.data.orders.Select(o=>o.activateEncounter).Where(k=>!string.IsNullOrEmpty(k)))
     Assert.That(orders.encounters.Any(e=>e.key==key&&e.encounter),"encounter "+key);
    // Foreman: one spawn of the variant prefab, re-forms after clearing, not on top of the depot nest.
    var foreman=All<DroidEncounter>(scene).Single(e=>e.name=="Depot Foreman · processing hall");
    // Patch 1: the Foreman leads (spawn 0) with two worker escorts beside it, all clear of the depot nest.
    Assert.That(foreman.spawns.Length,Is.EqualTo(3));
    Assert.That(AssetDatabase.GetAssetPath(foreman.spawns[0].prefab),Is.EqualTo("Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab"));
    foreach(var s in foreman.spawns.Skip(1))
    {
     Assert.That(AssetDatabase.GetAssetPath(s.prefab),Is.EqualTo("Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab"));
     Assert.That(Vector3.Distance(s.point.position,foreman.spawns[0].point.position),Is.InRange(1.8f,4.5f));
     Assert.That(s.point.parent,Is.EqualTo(foreman.transform));
    }
    Assert.That(foreman.player&&foreman.session,Is.True);Assert.That(foreman.respawnSeconds,Is.GreaterThan(0));
    var tutorial=All<BermsTutorial>(scene).Single();var depot=tutorial.depot;
    foreach(var s in depot.spawns)foreach(var f in foreman.spawns)Assert.That(Vector3.Distance(s.point.position,f.point.position),Is.GreaterThan(2.5f));
    // Since 1 Oct 2026 the workbench is Brann's, in the Salvage shop inside the walls: the depot nest and the Foreman
    // re-form while the player is in town (the "away" rule), never while they stand next to them.
    var bench=crafting.fabricator.position;
    Assert.That(bench.x,Is.GreaterThan(All<PlayerCombat>(scene).Single().cityEdgeX),"the workbench is inside Ward");
    foreach(var e in new[]{depot,foreman})
    {
     Assert.That(e.respawnClearance,Is.LessThan(Flat(bench-e.transform.position)),e.name);
     Assert.That(e.awaySeconds,Is.GreaterThanOrEqualTo(30),e.name);
    }
    Assert.That(tutorial.depotRespawnSeconds,Is.InRange(180,360));
    Assert.That(session.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="Gameplay v2 · patch 1 (GameplayV2Patch1)"),"patch 1 marker");
    Assert.That(All<DroidEncounter>(scene).Length,Is.EqualTo(3));
    // Heaps: 6–10 searchable nodes with real tables, clear of colonists and Wardens.
    var catalog=AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
    var nodes=All<SalvageNode>(scene);
    Assert.That(nodes.Length,Is.InRange(6,10));
    foreach(var n in nodes)
    {
     Assert.That(catalog.lootTables.Any(t=>t.id==n.lootTableId),n.name);Assert.That(n.crafting,Is.EqualTo(crafting),n.name);
     Assert.That(n.transform.position.x,Is.LessThan(All<PlayerCombat>(scene).Single().cityEdgeX),n.name+" must be in the Outer Berms");
     foreach(var npc in session.npcs.Where(x=>x))Assert.That(Vector3.Distance(npc.transform.position,n.transform.position),Is.GreaterThan(2.4f+n.GetComponent<WorldInteractable>().range),n.name);
     foreach(var w in All<WorldInteractable>(scene).Where(w=>!w.GetComponent<SalvageNode>()))Assert.That(Vector3.Distance(w.transform.position,n.transform.position),Is.GreaterThan(4),n.name+" vs "+w.name);
    }
    Assert.That(nodes.Select(n=>n.lootTableId).Distinct().Count(),Is.GreaterThanOrEqualTo(3));
    // Prompts name what is searched.
    Assert.That(nodes.Select(n=>n.readyPrompt).Distinct().Count(),Is.GreaterThanOrEqualTo(4));
    foreach(var n in nodes)
    {
     Assert.That(n.readyPrompt,Does.StartWith("E · "),n.name);Assert.That(n.progressLabel,Is.Not.Empty,n.name);
     if(n.displayName.Contains("carcass"))Assert.That(n.readyPrompt,Does.StartWith("E · Strip"),n.name);
     if(n.displayName=="Crashed drone")Assert.That(n.readyPrompt,Is.EqualTo("E · Salvage the crashed drone"));
    }
    // Patch 2: names agree with what they are.
    Assert.That(nodes.Single(n=>n.name=="Salvage node · Depot litter").readyPrompt,Is.EqualTo("E · Search the depot litter"));
    foreach(var n in nodes.Where(n=>n.name.StartsWith("Salvage node · Roadside scrap heap")))Assert.That(n.readyPrompt,Is.EqualTo("E · Search the roadside scrap"),n.name);
    Assert.That(session.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="Gameplay v2 · patch 2 (GameplayV2Patch2)"),"patch 2 marker");
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }

  [Test] public void InstallerLeftExistingGameplayRootsInPlace()
  {
   var scene=EditorSceneManager.OpenPreviewScene(ScenePath);
   try
   {
    var tutorial=All<BermsTutorial>(scene).Single();
    Assert.That(tutorial.firstContact.name,Is.EqualTo("First contact · service road"));Assert.That(tutorial.depot.name,Is.EqualTo("Machine depot nest"));
    Assert.That(tutorial.depot.spawns.Select(s=>s.point.position.x),Is.EqualTo(new[]{-82.2f,-75.2f,-84.9f}).Within(.05f));
    var names=All<NpcAgent>(scene).Select(n=>n.name).ToArray();
    foreach(var n in new[]{"npc_mira","npc_torr","npc_vex","npc_linn","Warden Ossa","Warden Rell"})Assert.That(names,Does.Contain(n));
    var fab=All<CraftingStationMarker>(scene).Single(m=>m.name=="Field fabricator");Assert.That(fab.transform.position.x,Is.EqualTo(-75f).Within(.01f));
    Assert.That(fab.enabled,Is.False,"since 1 Oct 2026 crafting is at Brann's workbench in Salvage; the cart stays as outpost dressing");
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
