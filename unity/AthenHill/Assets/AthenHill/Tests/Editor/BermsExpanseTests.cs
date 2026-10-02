using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace AthenHill.Tests
{
 /// Outer Berms expansion (2 Oct 2026): the ~500 m bowl, its sites and the ranged droids.
 public class BermsExpanseTests
 {
  const string ScenePath="Assets/AthenHill/Scenes/AthenHill.unity";
  static T[] All<T>(Scene scene)where T:Component=>scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<T>(true)).ToArray();

  [Test] public void BoltHitTestMeasuresTheClosestApproach()
  {
   // a bolt passing 0.5 m beside a vertical body segment
   float d=DroidBolt.SegmentToSegment(new Vector3(-5,1,.5f),new Vector3(5,1,.5f),new Vector3(0,.35f,0),new Vector3(0,1.55f,0),out var at);
   Assert.That(d,Is.EqualTo(.5f).Within(1e-4f));Assert.That(at.y,Is.EqualTo(1f).Within(1e-4f));
   // passing over the head
   d=DroidBolt.SegmentToSegment(new Vector3(-5,3,0),new Vector3(5,3,0),new Vector3(0,.35f,0),new Vector3(0,1.55f,0),out at);
   Assert.That(d,Is.EqualTo(1.45f).Within(1e-4f));Assert.That(at.y,Is.EqualTo(1.55f).Within(1e-4f));
   // a step that stops short of the body
   d=DroidBolt.SegmentToSegment(new Vector3(-5,1,0),new Vector3(-2,1,0),new Vector3(0,.35f,0),new Vector3(0,1.55f,0),out at);
   Assert.That(d,Is.EqualTo(2f).Within(1e-4f));
  }

  [Test] public void ExpansionIsInstalledAndWired()
  {
   var scene=EditorSceneManager.OpenPreviewScene(ScenePath);
   try
   {
    var berms=scene.GetRootGameObjects().Single(g=>g.name=="Outer Berms").transform;
    var root=berms.Find("Berms expanse");Assert.That(root,Is.Not.Null,"installed");
    Assert.That(scene.GetRootGameObjects().Single(g=>g.name=="Basin expanse").activeSelf,Is.True);
    Assert.That(scene.GetRootGameObjects().Where(g=>g.name=="Basin mountains").All(g=>!g.activeSelf),"old basin parked for rollback");
    Assert.That(berms.Find("Boundary colliders").gameObject.activeSelf,Is.False,"old 44 x 102 m walls retired");
    // walkable ground: tiles with a LOD0 collider each, on the Berms ground material
    var tiles=root.Find("Ground").Cast<Transform>().ToArray();
    Assert.That(tiles.Length,Is.GreaterThanOrEqualTo(40));
    foreach(var t in tiles){var c=t.Find("LOD0").GetComponent<MeshCollider>();Assert.That(c&&c.sharedMesh,t.name);}
    // the playable floor spans about 500 m
    var b=new Bounds(tiles[0].GetComponentInChildren<Renderer>().bounds.center,Vector3.zero);
    foreach(var r in root.Find("Ground").GetComponentsInChildren<MeshRenderer>())b.Encapsulate(r.bounds);
    Assert.That(b.size.x,Is.GreaterThan(450));Assert.That(b.size.z,Is.GreaterThan(400));
    // encounters: proximity-activated, parked when far, packs, re-forming; spread over the bowl
    var encs=root.GetComponentsInChildren<DroidEncounter>(true);
    Assert.That(encs.Length,Is.GreaterThanOrEqualTo(10));
    var combat=All<PlayerCombat>(scene).Single();var session=All<GameSession>(scene).Single();
    foreach(var e in encs)
    {
     Assert.That(e.player,Is.EqualTo(combat),e.name);Assert.That(e.session,Is.EqualTo(session),e.name);
     Assert.That(e.activateWithin,Is.InRange(40,120),e.name);Assert.That(e.requirePistol,e.name);
     Assert.That(e.parkBeyond,Is.GreaterThan(e.activateWithin+30),e.name);Assert.That(e.packRadius,Is.GreaterThan(0),e.name);
     Assert.That(e.respawnSeconds,Is.GreaterThan(0),e.name);
     Assert.That(e.spawns.Length,Is.GreaterThanOrEqualTo(1),e.name);
     foreach(var s in e.spawns){Assert.That(s.prefab&&s.point,e.name);Assert.That(s.point.position.x,Is.LessThan(combat.cityEdgeX),e.name);}
    }
    float far=encs.Max(e=>Vector3.Distance(e.transform.position,new Vector3(-58,0,0)));
    Assert.That(far,Is.GreaterThan(400),"sites reach well out into the bowl");
    // salvage spread across the sites, each on a real loot table
    var catalog=AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
    var nodes=root.GetComponentsInChildren<SalvageNode>(true);
    Assert.That(nodes.Length,Is.GreaterThanOrEqualTo(15));
    foreach(var n in nodes){Assert.That(catalog.lootTables.Any(t=>t.id==n.lootTableId),n.name);Assert.That(n.readyPrompt,Does.StartWith("E · "),n.name);}
    // a Warden waystation with a clear respawn point
    var way=root.GetComponentsInChildren<WardenWaystation>(true).Single();
    Assert.That(way.respawnPoint&&way.session==session&&way.player==combat);
    // the tutorial's first contact is a pair of drones on the service road just past the range (moved back beside
    // the gate on 2 Oct 2026 after a playtest: past the depot rise nothing was in sight after the plates); the depot nest is five
    var tut=berms.GetComponent<BermsTutorial>();
    Assert.That(tut.firstContact.spawns.Length,Is.EqualTo(2));Assert.That(tut.firstContact.transform.position.x,Is.InRange(-95,-75));
    Assert.That(Vector3.Distance(tut.firstContact.transform.position,tut.gateMarker.position),Is.LessThan(35));
    Assert.That(tut.depot.spawns.Length,Is.EqualTo(5));
    Assert.That(tut.lineComplete,Does.Contain("Brann"));Assert.That(tut.lineComplete,Does.Contain("waystation"));
    // the gameplay camera can see across the bowl
    Assert.That(session.follow.GetComponent<Camera>().farClipPlane,Is.GreaterThanOrEqualTo(1200));
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }

  [Test] public void TougherMeleeDroidsKeepThrottlingClearOfPerception()
  {
   var worker=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab");
   var drone=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab");
   Assert.That(worker.GetComponent<Health>().max,Is.GreaterThanOrEqualTo(120));Assert.That(drone.GetComponent<Health>().max,Is.GreaterThanOrEqualTo(70));
   foreach(var d in new[]{worker,drone}.Select(g=>g.GetComponent<FeralDroid>()))
   {
    Assert.That(d.attackMode,Is.EqualTo(DroidAttack.Melee));
    Assert.That(d.idleThrottleDistance,Is.GreaterThan(d.aggroRadius*2),d.name);
    Assert.That(d.flank,Is.InRange(.1f,.8f),d.name);
   }
  }

  [Test] public void RangedDroidsAreRangedWithDodgeableBolts()
  {
   foreach(var path in new[]{"Assets/AthenHill/Prefabs/OuterBerms/FeralGunnerDroid.prefab","Assets/AthenHill/Prefabs/OuterBerms/FeralLancerDrone.prefab"})
   {
    var go=AssetDatabase.LoadAssetAtPath<GameObject>(path);
    if(!go){Assert.Inconclusive(path+" not built yet (Meshy visuals pending)");return;}
    var d=go.GetComponent<FeralDroid>();
    Assert.That(d.attackMode,Is.EqualTo(DroidAttack.Ranged),path);Assert.That(d.Ranged,path);
    Assert.That(d.boltPrefab,Is.Not.Null,path);Assert.That(d.muzzle,Is.Not.Null,path);Assert.That(d.aimLaser,Is.Not.Null,path);
    Assert.That(d.fireRange,Is.GreaterThan(d.preferredRange),path);Assert.That(d.preferredRange,Is.GreaterThan(d.retreatRange),path);
    Assert.That(d.windupSeconds,Is.GreaterThanOrEqualTo(.6f),"a readable tell: "+path);
    Assert.That(d.boltSpeed,Is.InRange(20,50),"slow enough to sidestep at range: "+path);
    Assert.That(d.idleThrottleDistance,Is.GreaterThan(d.aggroRadius*2),path);
    Assert.That(go.GetComponent<LootSource>().lootTableId,Does.StartWith("loot_feral_"),path);
    if(d.kind==DroidKind.Walker)
    {
     Assert.That(d.idle&&d.walk&&d.run&&d.attack&&d.hit&&d.death,path+": clips");
     Assert.That(d.animationSource,Is.Not.Null);
    }
    else Assert.That(d.rotors.Length,Is.GreaterThanOrEqualTo(2),path);
   }
  }
 }
}
