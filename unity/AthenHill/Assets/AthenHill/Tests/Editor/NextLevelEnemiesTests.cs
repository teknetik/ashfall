using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace AthenHill.Tests
{
 /// Next-level enemies (2 Oct 2026): the two outer droids (the delivered "Ironclad Warden" turned out to be Brann and is
 /// retired under Prefabs/OuterBerms/Retired), their threat/loot data, the four POIs and the loot crates.
 public class NextLevelEnemiesTests
 {
  const string ScenePath="Assets/AthenHill/Scenes/AthenHill.unity",OB="Assets/AthenHill/Prefabs/OuterBerms/";
  static T[] All<T>(Scene scene)where T:Component=>scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<T>(true)).ToArray();

  [Test] public void ArmourTakesAFlatAmountAfterPenetrationButNeverEverything()
  {
   Assert.That(FeralDroid.MitigatedDamage(34,14,0,.25f),Is.EqualTo(20f).Within(1e-4f),"pistol vs Reaper");
   Assert.That(FeralDroid.MitigatedDamage(28.35f,14,16,.25f),Is.EqualTo(28.35f).Within(1e-3f),"modded rifle vs Reaper: full damage");
   Assert.That(FeralDroid.MitigatedDamage(10,40,0,.25f),Is.EqualTo(2.5f).Within(1e-4f),"the floor");
   Assert.That(FeralDroid.MitigatedDamage(20,5,30,.25f),Is.EqualTo(20f).Within(1e-4f),"penetration beyond the armour changes nothing");
  }

  [Test] public void NewDroidPrefabsOutclassTheStarterPistol()
  {
   var catalog=AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
   var pistol=catalog.weapons.Single(w=>w.id=="weapon_scrap_pistol").stats;var rifle=catalog.weapons.Single(w=>w.id=="weapon_field_rifle").stats;
   float barrelPen=catalog.modifiers.Single(m=>m.id=="mod_rifle_precision_barrel").effects.Single(e=>e.stat=="armourPenetration").value;
   Assert.That(barrelPen,Is.GreaterThanOrEqualTo(8),"precision barrel penetration (nl1 fix round)");
   foreach(var (file,level) in new[]{("FeralScrapReaper",3),("FeralPostSentinel",3)})
   {
    var go=AssetDatabase.LoadAssetAtPath<GameObject>(OB+file+".prefab");
    if(!go){Assert.Inconclusive(file+" not built yet (NextLevelEnemiesInstall droids)");return;}
    var d=go.GetComponent<FeralDroid>();var h=go.GetComponent<Health>();var t=go.GetComponent<DroidThreat>();var l=go.GetComponent<LootSource>();
    Assert.That(t,Is.Not.Null,file);Assert.That(t.level,Is.EqualTo(level),file);Assert.That(t.experience,Is.GreaterThanOrEqualTo(50),file);
    Assert.That(d.armour,Is.GreaterThan(0),file);Assert.That(h.max,Is.GreaterThanOrEqualTo(400),file);
    Assert.That(l&&catalog.lootTables.Any(x=>x.id==l.lootTableId),file+": loot table");
    // one full pistol charge (11 shots) must not come close; a modded rifle burst (12 shots, +12 penetration) must do real work
    float pistolCharge=Mathf.Floor(pistol.nanoMax/pistol.nanoPerShot)*FeralDroid.MitigatedDamage(pistol.damage,d.armour,0,d.armourMinFraction);
    float rifleBurst=Mathf.Floor(rifle.nanoMax/rifle.nanoPerShot)*FeralDroid.MitigatedDamage(rifle.damage*1.05f,d.armour,rifle.armourPenetration+barrelPen,d.armourMinFraction);
    Assert.That(pistolCharge,Is.LessThan(h.max*.6f),file+": a pistol charge is well under its vitality");
    Assert.That(rifleBurst,Is.GreaterThan(pistolCharge*1.3f),file+": the rifle gets through the armour");
    // nl1 targets: a Reaper in about 15-20 modded-rifle hits, a Sentinel in about 20
    float perHit=FeralDroid.MitigatedDamage(rifle.damage*1.05f,d.armour,rifle.armourPenetration+barrelPen,d.armourMinFraction);
    Assert.That(h.max/perHit,Is.InRange(13,22),file+": modded rifle hits to kill");
    Assert.That(d.idleThrottleDistance,Is.GreaterThan(d.aggroRadius*1.5f),file);
    if(d.kind==DroidKind.Walker){Assert.That(d.idle&&d.walk&&d.run&&d.attack&&d.hit&&d.death,file+": clips");Assert.That(d.attackMode,Is.EqualTo(DroidAttack.Melee));}
    if(d.kind==DroidKind.Wheeled){Assert.That(d.wheel,Is.Not.Null,file);Assert.That(d.Ranged,file);Assert.That(d.muzzle&&d.aimLaser,file);Assert.That(d.boltSpeed,Is.InRange(20,50));}
    Assert.That(go.GetComponentsInChildren<FeralDroid>(true).Length,Is.EqualTo(1),file+": no nested droid");
   }
  }

  [Test] public void EveryDroidPrefabCarriesAThreatLevel()
  {
   foreach(var file in new[]{"FeralWorkerDroid","FeralScrapDrone","FeralGunnerDroid","FeralLancerDrone","FeralDepotForeman"})
   {
    var go=AssetDatabase.LoadAssetAtPath<GameObject>(OB+file+".prefab");if(!go)continue;
    var t=go.GetComponent<DroidThreat>();
    if(!t){Assert.Inconclusive(file+": DroidThreat not installed yet");return;}
    Assert.That(t.level,Is.InRange(1,3),file);
    Assert.That(go.GetComponentsInChildren<FeralDroid>(true).Length,Is.EqualTo(1),file+": no nested droid (gunner/lancer fix)");
   }
  }

  [Test] public void TheIroncladWardenIsRetiredButRecoverable()
  {
   Assert.That(AssetDatabase.LoadAssetAtPath<GameObject>(OB+"FeralIroncladWarden.prefab"),Is.Null,"no live Ironclad prefab");
   var retired=AssetDatabase.LoadAssetAtPath<GameObject>(OB+"Retired/FeralIroncladWarden.prefab");
   if(!retired){Assert.Inconclusive("retire step not run yet");return;}
   Assert.That(retired.GetComponent<FeralDroid>()&&retired.GetComponent<DroidThreat>(),"the retired prefab keeps its setup");
   Assert.That(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/Retired/SalvageDealer_hauler_20261001.prefab"),Is.Not.Null,"the previous Brann is kept");
  }

  [Test] public void OuterPoisAreInstalledWithCratesAndLandmarks()
  {
   var scene=EditorSceneManager.OpenPreviewScene(ScenePath);
   try
   {
    var berms=scene.GetRootGameObjects().Single(g=>g.name=="Outer Berms").transform;
    var root=berms.Find("Next level sites");
    if(!root){Assert.Inconclusive("Next level sites not installed yet");return;}
    var combat=All<PlayerCombat>(scene).Single();var session=All<GameSession>(scene).Single();
    var encs=root.GetComponentsInChildren<DroidEncounter>(true);Assert.That(encs.Length,Is.EqualTo(4));
    foreach(var e in encs)
    {
     Assert.That(e.player,Is.EqualTo(combat),e.name);Assert.That(e.session,Is.EqualTo(session),e.name);
     Assert.That(e.activateWithin,Is.EqualTo(75f),e.name);Assert.That(e.parkBeyond,Is.GreaterThan(e.activateWithin+30),e.name);Assert.That(e.respawnSeconds,Is.GreaterThan(0),e.name);
     Assert.That(e.spawns.Length,Is.InRange(2,3),e.name);
     foreach(var s in e.spawns){Assert.That(s.prefab&&s.point,e.name);Assert.That(s.prefab.GetComponent<DroidThreat>().level,Is.GreaterThanOrEqualTo(3),e.name+": only outer droids");}
     // in the outer third of the bowl, away from the gate
     Assert.That(Vector3.Distance(e.transform.position,new Vector3(-58,0,0)),Is.GreaterThan(220),e.name);
    }
    // every expansion site keeps its distance
    var expanse=berms.Find("Berms expanse").Find("Sites");
    foreach(var e in encs)foreach(Transform s in expanse)Assert.That(Vector3.Distance(e.transform.position,s.position),Is.GreaterThan(55),e.name+" vs "+s.name);
    var catalog=AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
    var crates=root.GetComponentsInChildren<SalvageNode>(true).Where(n=>n.name.StartsWith("Loot crate")).ToArray();
    Assert.That(crates.Length,Is.GreaterThanOrEqualTo(8));
    foreach(var c in crates){Assert.That(c.lootTableId,Does.StartWith("loot_nextlevel_"),c.name);Assert.That(catalog.lootTables.Any(t=>t.id==c.lootTableId),c.name);Assert.That(c.readyPrompt,Does.StartWith("E · "),c.name);}
    var strongbox=catalog.lootTables.Single(t=>t.id=="loot_nextlevel_strongbox");
    Assert.That(strongbox.entries.Count(e=>e.guaranteeUntilCollected),Is.EqualTo(2),"the two parts are guaranteed until first collected");
    var landmarks=scene.GetRootGameObjects().Single(g=>g.name=="Landmarks").transform;
    foreach(var n in new[]{"nextlevel_post_relay","nextlevel_reaper_den","nextlevel_ironclad_camp","nextlevel_southern_cache"})Assert.That(landmarks.Find(n),Is.Not.Null,n);
    Assert.That(root.GetComponentsInChildren<Camera>(true).Count(c=>c.name.StartsWith("cam_nextlevel_")),Is.GreaterThanOrEqualTo(4));
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }

  [Test] public void NewLootItemsAreRareTradeExcludedPartsWithIcons()
  {
   var city=AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
   foreach(var id in new[]{"reaper_blade","sentinel_optic"})
   {
    var item=city.items.SingleOrDefault(i=>i.id==id);
    if(item==null){Assert.Inconclusive(id+" not in the catalog yet (apply_data.py)");return;}
    // rare parts are trade-excluded by the catalog rules (ShopSellTests): crafting rewards, not credits
    Assert.That(item.excludeFromTrade&&item.partsPrice==0&&!ShopModel.BuysAsSalvage(item),id);Assert.That(item.rarity,Is.EqualTo(ItemRarity.Rare),id);
    Assert.That(item.icon,Does.EndWith("-icon"),id);
   }
  }
 }
}
