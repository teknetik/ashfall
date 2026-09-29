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
    Assert.That(foreman.spawns.Length,Is.EqualTo(1));
    Assert.That(AssetDatabase.GetAssetPath(foreman.spawns[0].prefab),Is.EqualTo("Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab"));
    Assert.That(foreman.player&&foreman.session,Is.True);Assert.That(foreman.respawnSeconds,Is.GreaterThan(0));
    var depot=All<BermsTutorial>(scene).Single().depot;
    foreach(var s in depot.spawns)Assert.That(Vector3.Distance(s.point.position,foreman.spawns[0].point.position),Is.GreaterThan(2.5f));
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
    var fab=All<CraftingStationMarker>(scene).Single();Assert.That(fab.transform.position.x,Is.EqualTo(-75f).Within(.01f));
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
