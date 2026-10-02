using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// Gameplay v2 M2: seeded loot rolls, bad-luck protection, first-collection guarantees, cache collection,
 /// scrap-heap timing, paid-only-after-payout and the Depot Foreman variant.
 public class LootTests
 {
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static LootTable Table(string id)=>Data().lootTables.Single(x=>x.id==id);
  static Dictionary<string,int> AsMap(List<ItemStack> s)=>s.ToDictionary(x=>x.itemId,x=>x.quantity);

  [Test] public void SplitMixGeneratorMatchesReferenceVectors()
  {
   var rng=new LootRng(1729);
   Assert.That(new[]{rng.NextULong(),rng.NextULong(),rng.NextULong()},Is.EqualTo(new[]{0xc027d2a98bba7194UL,0x4e4d58faa87007d9UL,0x95cc471323c889a6UL}));
   rng=new LootRng(1729);
   Assert.That(rng.NextDouble(),Is.EqualTo(0.7506076492243012).Within(1e-15));
   Assert.That(rng.NextDouble(),Is.EqualTo(0.30586773032740666).Within(1e-15));
   Assert.That(LootRng.TryParse(new LootRng(99).Save(),out var state)&&state==99);
  }

  [Test] public void SeededDroneRollsAreExactAndBadLuckProtectionFires()
  {
   var book=new LootBook(1729);var table=Table("loot_feral_scrap_drone");
   Assert.That(AsMap(book.Roll(table)),Is.EquivalentTo(new Dictionary<string,int>{{"scrap_alloy",1},{"nanite_residue",3},{"copper_filament",1}}));
   Assert.That(book.Misses(table.id,"micro_capacitor"),Is.EqualTo(1));Assert.That(book.Misses(table.id,"optic_lens_cracked"),Is.EqualTo(1));
   Assert.That(AsMap(book.Roll(table)),Is.EquivalentTo(new Dictionary<string,int>{{"scrap_alloy",2},{"nanite_residue",3},{"copper_filament",1},{"optic_lens_cracked",1}}));
   Assert.That(book.Misses(table.id,"micro_capacitor"),Is.EqualTo(2));Assert.That(book.Misses(table.id,"optic_lens_cracked"),Is.Zero);
   // Two misses in a row: the third roll is guaranteed by pityAfter = 2.
   Assert.That(AsMap(book.Roll(table)),Is.EquivalentTo(new Dictionary<string,int>{{"scrap_alloy",2},{"nanite_residue",3},{"copper_filament",1},{"micro_capacitor",1}}));
   Assert.That(book.Misses(table.id,"micro_capacitor"),Is.Zero);
   Assert.That(book.Rng.Save(),Is.EqualTo("454021de755d4bfc"));
  }

  [Test] public void PityThresholdBoundsConsecutiveMisses()
  {
   var table=new LootTable{id="t",entries=new[]{new LootEntry{itemId="rare",minQuantity=1,maxQuantity=1,chance=1e-9f,pityAfter=3}}};
   var book=new LootBook(7);
   var pattern=Enumerable.Range(0,12).Select(_=>book.Roll(table).Count).ToArray();
   Assert.That(pattern,Is.EqualTo(new[]{0,0,0,1,0,0,0,1,0,0,0,1}));
   // Without protection the same near-impossible entry never drops.
   var plain=new LootTable{id="u",entries=new[]{new LootEntry{itemId="rare",minQuantity=1,maxQuantity=1,chance=1e-9f}}};
   Assert.That(Enumerable.Range(0,50).Sum(_=>book.Roll(plain).Count),Is.Zero);
   Assert.That(book.Misses("u","rare"),Is.EqualTo(50));
  }

  [Test] public void RealTablesNeverExceedTheirPityWindow()
  {
   foreach(var table in Data().lootTables)
   {
    var book=new LootBook(4242);var run=table.entries.ToDictionary(e=>e.itemId,e=>0);
    for(int i=0;i<400;i++)
    {
     var got=book.Roll(table).Select(x=>x.itemId).ToHashSet();
     foreach(var e in table.entries)
     {
      if(got.Contains(e.itemId))run[e.itemId]=0;else run[e.itemId]++;
      if(e.pityAfter>0)Assert.That(run[e.itemId],Is.LessThanOrEqualTo(e.pityAfter),table.id+"/"+e.itemId);
     }
    }
   }
  }

  [Test] public void ForemanCoreIsGuaranteedUntilCollectedThenNeverDrops()
  {
   var table=Table("loot_depot_foreman");var book=new LootBook(1);
   for(int i=0;i<3;i++)
   {
    var drop=AsMap(book.Roll(table));
    Assert.That(drop["foreman_control_core"],Is.EqualTo(1));
    Assert.That(drop["actuator_intact"],Is.InRange(1,2));
   }
   book.MarkCollected("foreman_control_core");
   Assert.That(Enumerable.Range(0,40).Any(_=>book.Roll(table).Any(x=>x.itemId=="foreman_control_core")),Is.False);
   // Lattice shard: 50% with pity 1 means never two misses in a row.
   int missesInARow=0;
   for(int i=0;i<200;i++){if(book.Roll(table).Any(x=>x.itemId=="lattice_shard"))missesInARow=0;else Assert.That(++missesInARow,Is.LessThanOrEqualTo(1));}
  }

  [Test] public void QuantityRangesAreInclusiveAndMergeDuplicates()
  {
   var table=new LootTable{id="q",entries=new[]{new LootEntry{itemId="a",minQuantity=2,maxQuantity=4,chance=1},new LootEntry{itemId="a",minQuantity=1,maxQuantity=1,chance=1},new LootEntry{itemId="b",minQuantity=3,maxQuantity=1,chance=1}}};
   var book=new LootBook(11);var seen=new HashSet<int>();
   for(int i=0;i<200;i++)
   {
    var drop=AsMap(book.Roll(table));
    Assert.That(drop.Count,Is.EqualTo(2));Assert.That(drop["b"],Is.EqualTo(3));
    Assert.That(drop["a"],Is.InRange(3,5));seen.Add(drop["a"]);
   }
   Assert.That(seen,Is.EquivalentTo(new[]{3,4,5}));
  }

  [Test] public void LootStateRoundTripsAndContinuesTheSameSequence()
  {
   var table=Table("loot_scrap_heap");
   var a=new LootBook(1729);for(int i=0;i<7;i++)a.Roll(table);
   a.MarkCollected("lattice_shard");
   var saved=JsonUtility.ToJson(a.Capture());
   var b=new LootBook(5);Assert.That(b.Restore(JsonUtility.FromJson<LootState>(saved)));
   Assert.That(b.HasCollected("lattice_shard"));Assert.That(b.Rolls,Is.EqualTo(7));
   foreach(var e in table.entries)Assert.That(b.Misses(table.id,e.itemId),Is.EqualTo(a.Misses(table.id,e.itemId)));
   for(int i=0;i<25;i++)Assert.That(AsMap(b.Roll(table)),Is.EquivalentTo(AsMap(a.Roll(table))));
   Assert.That(b.Restore(new LootState{rng="not hex"}),Is.False);Assert.That(b.Restore(null),Is.False);
  }

  [Test] public void CacheCollectsWhatFitsAndKeepsTheRest()
  {
   var pack=new ShopModel(City().items);
   Assert.That(pack.TryApply(new[]{new KeyValuePair<string,int>("scrap_alloy",29)},0,out _));
   var cache=new SalvageContents(new[]{new ItemStack("scrap_alloy",3),new ItemStack("nanite_residue",2),new ItemStack("lattice_shard",1),new ItemStack("scrap_alloy",1),new ItemStack("not_an_item",1)});
   Assert.That(cache.Stacks.Single(x=>x.itemId=="scrap_alloy").quantity,Is.EqualTo(4));
   Assert.That(cache.BestRarity(pack),Is.EqualTo(ItemRarity.Rare));
   Assert.That(cache.Collect(pack,out var taken,out var left));
   Assert.That(AsMap(taken),Is.EquivalentTo(new Dictionary<string,int>{{"scrap_alloy",1},{"nanite_residue",2},{"lattice_shard",1}}));
   Assert.That(AsMap(left),Is.EquivalentTo(new Dictionary<string,int>{{"scrap_alloy",3},{"not_an_item",1}}));
   Assert.That(pack.Quantity("scrap_alloy"),Is.EqualTo(30));Assert.That(pack.Quantity("lattice_shard"),Is.EqualTo(1));
   Assert.That(cache.BestRarity(pack),Is.EqualTo(ItemRarity.Common));
   // Still full: nothing moves, nothing is lost.
   Assert.That(cache.Collect(pack,out taken,out left),Is.False);Assert.That(taken,Is.Empty);Assert.That(AsMap(left)["scrap_alloy"],Is.EqualTo(3));
   Assert.That(pack.Sell("scrap_alloy",10,out _));
   Assert.That(cache.Collect(pack,out taken,out _));Assert.That(AsMap(taken)["scrap_alloy"],Is.EqualTo(3));
   Assert.That(cache.Stacks.Select(x=>x.itemId),Is.EqualTo(new[]{"not_an_item"}));
   Assert.That(new SalvageContents(new[]{new ItemStack("scrap_alloy",0),null}).Empty);
  }

  [Test] public void CacheTakesPartialStacksWithinWeightCapacity()
  {
   var pack=new ShopModel(new[]{new ItemSpec{id="alloy",name="Alloy",weightKg=2},new ItemSpec{id="wire",name="Wire",weightKg=1}});
   pack.CapacityFailure=future=>future["alloy"]*2+future["wire"]>5?"over_capacity":null;
   var cache=new SalvageContents(new[]{new ItemStack("alloy",3),new ItemStack("wire",3)});
   Assert.That(cache.Collect(pack,out var taken,out var left));
   Assert.That(AsMap(taken),Is.EquivalentTo(new Dictionary<string,int>{{"alloy",2},{"wire",1}}));
   Assert.That(AsMap(left),Is.EquivalentTo(new Dictionary<string,int>{{"alloy",1},{"wire",2}}));
   Assert.That(pack.PackWeightKg,Is.EqualTo(5));
   Assert.That(pack.CanApply(new[]{new KeyValuePair<string,int>("wire",1)},0,out _),Is.False);
   Assert.That(pack.Quantity("wire"),Is.EqualTo(1),"Dry-run validation must not commit inventory.");
  }

  [Test] public void HeapSearchCancelsCompletesAndRespawnsOnTheClock()
  {
   var s=new SalvageSearch(1.2f,270,.6f);
   Assert.That(s.State,Is.EqualTo(SalvageNodeState.Ready));
   Assert.That(s.Begin(10,Vector3.zero));Assert.That(s.Begin(10,Vector3.zero),Is.False);
   Assert.That(s.Tick(10.5f,new Vector3(.3f,5,.3f),true),Is.EqualTo(SalvageTick.None));// height and small steps are fine
   Assert.That(s.Progress(10.6f),Is.EqualTo(.5f).Within(1e-4));
   Assert.That(s.Tick(10.7f,new Vector3(.7f,0,0),true),Is.EqualTo(SalvageTick.Cancelled));Assert.That(s.State,Is.EqualTo(SalvageNodeState.Ready));
   Assert.That(s.Begin(20,Vector3.zero));
   Assert.That(s.Tick(20.5f,Vector3.zero,false),Is.EqualTo(SalvageTick.Cancelled));// a menu or pause opened
   Assert.That(s.Begin(30,Vector3.one));
   Assert.That(s.Tick(31.1f,Vector3.one,true),Is.EqualTo(SalvageTick.None));
   Assert.That(s.Tick(31.2f,Vector3.one,true),Is.EqualTo(SalvageTick.Completed));Assert.That(s.State,Is.EqualTo(SalvageNodeState.Depleted));
   Assert.That(s.Begin(40,Vector3.one),Is.False);
   Assert.That(s.RespawnRemaining(131.2f),Is.EqualTo(170).Within(1e-3));
   Assert.That(s.Tick(301,Vector3.one,true),Is.EqualTo(SalvageTick.None));
   Assert.That(s.Tick(301.2f,Vector3.one,true),Is.EqualTo(SalvageTick.Respawned));Assert.That(s.State,Is.EqualTo(SalvageNodeState.Ready));
  }

  [Test] public void KillIsOnlyPaidAfterThePayoutSucceeds()
  {
   var go=new GameObject("test drone");
   try
   {
    var health=go.AddComponent<Health>();var droid=go.AddComponent<FeralDroid>();var loot=go.AddComponent<LootSource>();loot.lootTableId="loot_feral_scrap_drone";
    foreach(var c in new MonoBehaviour[]{health,droid,loot})c.GetType().GetMethod("Awake",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic)?.Invoke(c,null);
    typeof(LootSource).GetMethod("OnEnable",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).Invoke(loot,null);
    var update=typeof(LootSource).GetMethod("Update",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);
    bool ready=false;int paid=0;
    loot.Bind(id=>{if(!ready)return false;paid++;return true;});
    Assert.That(health.Damage(health.max,go.transform.position));
    Assert.That(loot.Paid,Is.False);Assert.That(loot.Pending);Assert.That(paid,Is.Zero);
    update.Invoke(loot,null);Assert.That(loot.Paid,Is.False);
    ready=true;update.Invoke(loot,null);update.Invoke(loot,null);
    Assert.That(paid,Is.EqualTo(1));Assert.That(loot.Paid);Assert.That(loot.Pending,Is.False);
    loot.Revived();Assert.That(loot.Paid,Is.False);
    droid.ResetToHome(true);Assert.That(health.Damage(health.max,go.transform.position));Assert.That(paid,Is.EqualTo(2));
   }
   finally{Object.DestroyImmediate(go);}
  }

  [Test] public void DepotForemanIsATougherUniformlyScaledWorkerVariant()
  {
   var worker=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab");
   var foreman=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab");
   Assert.That(foreman,Is.Not.Null);
   Assert.That(PrefabUtility.GetPrefabAssetType(foreman),Is.EqualTo(PrefabAssetType.Variant));
   Assert.That(PrefabUtility.GetCorrespondingObjectFromSource(foreman),Is.EqualTo(worker));
   var s=foreman.transform.localScale;Assert.That(s.x,Is.EqualTo(1.3f).Within(1e-4));Assert.That(s.y,Is.EqualTo(s.x));Assert.That(s.z,Is.EqualTo(s.x));
   // 30 Sep 2026 tuning: an elite fight (1400 HP, then 14 workers; see GameplayV2FixesTests.ForemanIsAnEliteWithinTheWorkerBehaviour).
   // 2 Oct 2026: workers were toughened to 130 HP for the expanded Berms; the Foreman keeps its 1400 (still over 10 workers).
   Assert.That(foreman.GetComponent<Health>().max,Is.EqualTo(1400));
   Assert.That(foreman.GetComponent<Health>().max,Is.GreaterThan(worker.GetComponent<Health>().max*10));
   var f=foreman.GetComponent<FeralDroid>();var w=worker.GetComponent<FeralDroid>();
   Assert.That(f.displayName,Is.EqualTo("Depot Foreman"));
   Assert.That(f.strikeDamage,Is.GreaterThan(w.strikeDamage));Assert.That(f.windupSeconds,Is.GreaterThan(w.windupSeconds));
   Assert.That(f.chaseSpeed,Is.LessThan(w.chaseSpeed));Assert.That(f.staggerImmunity,Is.GreaterThan(w.staggerImmunity*3));
   Assert.That(f.glowHostile,Is.Not.EqualTo(w.glowHostile));
   Assert.That(foreman.GetComponent<LootSource>().lootTableId,Is.EqualTo("loot_depot_foreman"));
   Assert.That(Data().lootTables.Any(t=>t.id=="loot_depot_foreman"));
   var body=foreman.GetComponentInChildren<SkinnedMeshRenderer>(true);Assert.That(body.sharedMaterial.name,Is.EqualTo("RB_ForemanDroid"));
  }

  [Test] public void SalvagePrefabsAreWiredForInteraction()
  {
   var cache=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/SalvageCache.prefab");
   var c=cache.GetComponent<SalvageCache>();
   Assert.That(cache.GetComponent<WorldInteractable>(),Is.Not.Null);
   Assert.That(c.glowLight,Is.Not.Null);Assert.That(c.motes,Is.Not.Null);Assert.That(c.glowRenderers.Length,Is.GreaterThan(0));
   Assert.That(cache.GetComponentsInChildren<Collider>(true),Is.Empty,"a cache must never block movement");
   Assert.That(c.GlowColor(ItemRarity.Rare),Is.Not.EqualTo(c.GlowColor(ItemRarity.Uncommon)));
   var node=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/SalvageHeapNode.prefab").GetComponent<SalvageNode>();
   Assert.That(node.lootTableId,Is.EqualTo("loot_scrap_heap"));Assert.That(node.searchSeconds,Is.EqualTo(1.2f));Assert.That(node.respawnSeconds,Is.InRange(240,300));
   Assert.That(Data().lootTables.Any(t=>t.id==node.lootTableId));
  }
 }
}
