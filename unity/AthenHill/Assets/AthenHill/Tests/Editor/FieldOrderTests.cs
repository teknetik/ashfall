using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// Gameplay v2 M3: Ossa's field orders — transitions, data-built objectives, guidance and non-regression.
 public class FieldOrderTests
 {
  const string Station="station_field_fabricator";
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static FieldOrderSet Orders()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.id,x.n)),0,out var r),Is.True,r);
  sealed class Run
  {
   public ShopModel pack;public CraftingModel model;public FieldOrderProgress orders;public HashSet<string> collected=new HashSet<string>();
   public Run()
   {
    pack=new ShopModel(City().items);
    // 2 Oct 2026: the rifle recipe asks for engineering 20, so the run carries a colonist who meets it
    var catalog=ScriptableObject.CreateInstance<CharacterCatalog>();catalog.skills=new[]{new CharacterSkill{id="engineering",initial=20}};
    model=new CraftingModel(Data(),City().items,pack,()=>true,character:new CharacterModel(catalog,pack));orders=new FieldOrderProgress(Orders());
   }
   public List<FieldOrder> Advance()=>orders.Advance(model,id=>collected.Contains(id)||pack.Quantity(id)>0);
   public void Craft(string recipe,int n=1){model.Unlock(recipe);for(int i=0;i<n;i++)Assert.That(model.TryCraft(recipe,Station,out var r),r);}
  }

  [Test] public void OrderDataIsCompleteAndMatchesTheArc()
  {
   var set=Orders();Assert.That(set,Is.Not.Null);
   // 2 Oct 2026: Long Arm (the field rifle) and Plate Carrier (the Warden plate carrier) follow Steady Hands.
   Assert.That(set.orders.Select(o=>o.title),Is.EqualTo(new[]{"Steady Hands","Long Arm","Plate Carrier","Keep the Charge","Bore It True","The Depot Foreman","Mark II"}));
   Assert.That(set.orders.Select(o=>o.id).Distinct().Count(),Is.EqualTo(7));
   foreach(var o in set.orders)
   {
    Assert.That(o.completeLine,Is.Not.Empty,o.id);Assert.That(o.brief,Is.Not.Empty,o.id);
    if(o.goal!=FieldOrderGoal.CraftFromGroup)Assert.That(City().items.Any(i=>i.id==o.targetItemId),o.id);
   }
   Assert.That(set.orders[0].requireTestFire);Assert.That(set.orders.Single(o=>o.id=="order_depot_foreman").activateEncounter,Is.EqualTo("foreman"));
   var longArm=set.orders.Single(o=>o.id=="order_long_arm");var carrier=set.orders.Single(o=>o.id=="order_plate_carrier");
   Assert.That(longArm.goal,Is.EqualTo(FieldOrderGoal.CraftItem));Assert.That(longArm.targetItemId,Is.EqualTo("field_rifle"));Assert.That(longArm.reportTo,Is.EqualTo("npc_brann"));
   Assert.That(longArm.activateEncounter,Is.EqualTo("relay_knoll"));Assert.That(longArm.guidance,Is.EqualTo("relay_knoll"));Assert.That(longArm.engageLine,Is.Not.Empty);
   Assert.That(carrier.goal,Is.EqualTo(FieldOrderGoal.CollectItem));Assert.That(carrier.targetItemId,Is.EqualTo("warden_plate_carrier"));Assert.That(carrier.activateEncounter,Is.EqualTo("caravan"));
   Assert.That(Data().lootTables.Single(t=>t.id=="loot_feral_gunner").entries.Any(e=>e.itemId=="rifle_receiver"&&e.guaranteeUntilCollected),"the gunners carry the receiver until one is collected");
   Assert.That(Data().lootTables.Single(t=>t.id=="loot_caravan_strongbox").entries.Any(e=>e.itemId=="warden_plate_carrier"&&e.guaranteeUntilCollected));
   Assert.That(Data().recipes.Single(r=>r.id=="recipe_field_rifle").inputs.Any(i=>i.id=="rifle_receiver"),"the rifle is built around the receiver");
   Assert.That(City().items.Single(i=>i.id=="field_rifle").startingQuantity,Is.Zero,"the rifle is earned, not issued");
   // The Keep the Charge and Bore It True orders reveal their schematics when they start.
   Assert.That(Data().recipes.Where(r=>r.unlocks?.Any(u=>u.type=="orderStart"&&u.id=="order_keep_charge")==true).Select(r=>r.outputItemId),Does.Contain("cell_salvaged_capacitor"));
   Assert.That(Data().recipes.Where(r=>r.unlocks?.Any(u=>u.type=="orderStart"&&u.id=="order_bore_true")==true).Select(r=>r.outputItemId),Does.Contain("barrel_bored_alloy"));
  }

  [Test] public void GripOrderWalksGatherFabricateFitTestFireAndCompletesOnce()
  {
   var run=new Run();
   Assert.That(run.orders.Objective(run.model,run.pack),Is.Null);Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.NotStarted));
   Assert.That(run.Advance(),Is.Empty);
   Assert.That(run.orders.Begin().id,Is.EqualTo("order_steady_hands"));Assert.That(run.orders.Begin(),Is.Null);
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Gather));
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Stabilised Pistol Grip: Any servo 0/1 · Scrap Alloy 0/2 · Any tier-one nanites 0/5"));
   Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("depot"));
   Give(run.pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",3));
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Any servo 1/1 · Scrap Alloy 2/2 · Any tier-one nanites 3/5"));
   Give(run.pack,("nanite_residue",2));run.model.Acquire("droid_servo_damaged");
   // 1 Oct 2026: with the parts in the pack the order waits for the visit to Brann at Salvage
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Report));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("dealer"));
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Brann at Salvage"));
   Assert.That(run.orders.NoteReport("npc_mira"),Is.False,"only the named colonist counts");
   Assert.That(run.orders.NoteReport("npc_brann"));Assert.That(run.orders.NoteReport("npc_brann"),Is.False,"once");
   Assert.That(run.orders.CurrentReported);
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Fabricate));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("fabricator"));
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Fabricate the Stabilised Pistol Grip"));
   run.Craft("recipe_grip_stabilised_pistol");
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Fit));Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Fit the Stabilised Pistol Grip to your Scrap Pistol"));
   Assert.That(run.orders.NoteShot(run.model),Is.False,"a shot before fitting is not the test fire");
   Assert.That(run.model.TryFit("grip_stabilised_pistol",out _));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.TestFire));Assert.That(run.Advance(),Is.Empty);
   Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.Null);
   Assert.That(run.orders.NoteShot(run.model));
   var done=run.Advance();Assert.That(done.Select(o=>o.id),Is.EqualTo(new[]{"order_steady_hands"}));
   Assert.That(run.orders.Index,Is.EqualTo(1));Assert.That(run.orders.Current.id,Is.EqualTo("order_long_arm"));
  }

  /// 2 Oct 2026: the Long Arm order gathers the rifle's inputs, reports to Brann and fabricates the rifle; the Plate
  /// Carrier order is a hunt for the caravan strongbox.
  static void RifleAndCarrier(Run run)
  {
   Assert.That(run.orders.Current.id,Is.EqualTo("order_long_arm"));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Gather));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("relay_knoll"));
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Warden Rifle Receiver 0/1"));
   Give(run.pack,("rifle_receiver",1),("scrap_alloy",6),("copper_filament",3),("nanite_residue",4));   // the field toolkit is in the starting pack
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Report));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("dealer"));
   Assert.That(run.orders.NoteReport("npc_brann"));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Fabricate));Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Fabricate the Field Rifle"));
   run.Craft("recipe_field_rifle");
   Assert.That(run.Advance().Single().id,Is.EqualTo("order_long_arm"));Assert.That(run.pack.Quantity("field_rifle"),Is.EqualTo(1));
   Assert.That(run.orders.Current.id,Is.EqualTo("order_plate_carrier"));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Hunt));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("caravan"));
   run.collected.Add("warden_plate_carrier");
   Assert.That(run.Advance().Single().id,Is.EqualTo("order_plate_carrier"));
   Assert.That(run.orders.Current.id,Is.EqualTo("order_keep_charge"));
  }

  [Test] public void RepeatingAFinishedTaskNeverRestartsOrRepeatsAnOrder()
  {
   var run=new Run();run.orders.Begin();
   Give(run.pack,("grip_stabilised_pistol",1));Assert.That(run.model.TryFit("grip_stabilised_pistol",out _));
   run.orders.NoteShot(run.model);Assert.That(run.Advance().Count,Is.EqualTo(1));
   // The audit case: craft and fit again after the order is done, then fire again.
   Assert.That(run.model.TryRemove("grip",out _));
   Give(run.pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));run.Craft("recipe_grip_stabilised_pistol");
   Assert.That(run.model.TryFit("grip_stabilised_pistol",out _));
   Assert.That(run.orders.NoteShot(run.model),Is.False);
   for(int i=0;i<3;i++)Assert.That(run.Advance(),Is.Empty);
   Assert.That(run.orders.Index,Is.EqualTo(1));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.Not.EqualTo(OrderStage.TestFire));
  }

  [Test] public void FullArcToFreePlay()
  {
   var run=new Run();run.orders.Begin();
   Give(run.pack,("grip_stabilised_pistol",1));run.model.TryFit("grip_stabilised_pistol",out _);run.orders.NoteShot(run.model);
   Assert.That(run.Advance().Single().id,Is.EqualTo("order_steady_hands"));
   RifleAndCarrier(run);
   // Keep the Charge: the objective lists the capacitor cell's parts from the recipe.
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Salvaged Capacitor Cell: Charge Cell Core 0/1 · Scrap Alloy 0/2"));
   Give(run.pack,("copper_filament",2),("micro_capacitor",2),("nanite_residue",3),("scrap_alloy",2));
   run.Craft("recipe_wound_coil");run.Craft("recipe_charge_cell_core");run.Craft("recipe_cell_salvaged_capacitor");
   Assert.That(run.Advance(),Is.Empty,"carried is not fitted");
   run.model.TryFit("cell_salvaged_capacitor",out _);
   Assert.That(run.Advance().Single().id,Is.EqualTo("order_keep_charge"));
   Give(run.pack,("barrel_bored_alloy",1));run.model.TryFit("barrel_bored_alloy",out _);
   Assert.That(run.Advance().Single().id,Is.EqualTo("order_bore_true"));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Hunt));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("foreman"));
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Foreman Control Core"));
   run.collected.Add("foreman_control_core");
   Assert.That(run.Advance().Single().id,Is.EqualTo("order_depot_foreman"));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Craft));
   Assert.That(run.Advance(),Is.Empty);
   Give(run.pack,("actuator_intact",1),("alloy_plate",2));run.Craft("recipe_grip_gyro_braced");
   Assert.That(run.Advance().Single().id,Is.EqualTo("order_mark_two"));
   Assert.That(run.orders.FreePlay);Assert.That(run.orders.Current,Is.Null);
   Assert.That(run.orders.Objective(run.model,run.pack),Is.EqualTo(Orders().freePlayObjective));
   Assert.That(run.Advance(),Is.Empty);
  }

  [Test] public void AlreadyMetOrdersCompleteTogetherInOrder()
  {
   var run=new Run();
   Give(run.pack,("grip_stabilised_pistol",1),("cell_salvaged_capacitor",1),("barrel_bored_alloy",1));
   foreach(var mod in new[]{"grip_stabilised_pistol","cell_salvaged_capacitor","barrel_bored_alloy"})run.model.TryFit(mod,out _);
   Give(run.pack,("rifle_receiver",1),("scrap_alloy",6),("copper_filament",3),("nanite_residue",4));   // the field toolkit is in the starting pack
   run.Craft("recipe_field_rifle");
   run.collected.Add("warden_plate_carrier");
   run.orders.Begin();
   Assert.That(run.Advance(),Is.Empty,"order 1 still wants its test fire");
   run.orders.NoteShot(run.model);
   Assert.That(run.Advance().Select(o=>o.id),Is.EqualTo(new[]{"order_steady_hands","order_long_arm","order_plate_carrier","order_keep_charge","order_bore_true"}));
   Assert.That(run.orders.Current.id,Is.EqualTo("order_depot_foreman"));
  }

  [Test] public void ProgressRoundTripsAndClampsCorruptIndices()
  {
   var run=new Run();run.orders.Begin();
   Give(run.pack,("grip_stabilised_pistol",1));run.model.TryFit("grip_stabilised_pistol",out _);run.orders.NoteShot(run.model);run.Advance();
   var json=JsonUtility.ToJson(run.orders.Capture());
   var copy=new FieldOrderProgress(Orders());copy.Restore(JsonUtility.FromJson<FieldOrderState>(json));
   Assert.That(copy.Index,Is.EqualTo(1));Assert.That(copy.TestFired("order_steady_hands"));
   copy.Restore(new FieldOrderState{index=99});Assert.That(copy.FreePlay);Assert.That(copy.Index,Is.EqualTo(Orders().orders.Length));
   copy.Restore(new FieldOrderState{index=-7});Assert.That(copy.Started,Is.False);
   copy.Restore(null);Assert.That(copy.Index,Is.EqualTo(-1));
  }

  [Test] public void ObjectiveTemplatesAreDataNotCode()
  {
   var set=Object.Instantiate(Orders());
   try
   {
    set.gatherFormat="GATHER[{brief}|{recipe}|{inputs}]";set.inputFormat="{need}x{name}";set.inputSeparator="+";
    var run=new Run();var orders=new FieldOrderProgress(set);orders.Begin();
    Assert.That(orders.Objective(run.model,run.pack),Is.EqualTo("GATHER["+set.orders[0].brief+"|Stabilised Pistol Grip|1xAny servo+2xScrap Alloy+5xAny tier-one nanites]"));
   }
   finally{Object.DestroyImmediate(set);}
  }
 }
}
