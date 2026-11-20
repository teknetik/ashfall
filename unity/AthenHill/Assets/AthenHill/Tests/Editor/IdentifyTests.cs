using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// 20 Nov 2026, crafting rework phase 1: salvage is identified by a colonist. Picking up the Damaged Servo no longer
 /// teaches the Stabilised Pistol Grip; Ossa looks at it and does (unlock type "identify", id "npc_ossa:servo_look").
 public class IdentifyTests
 {
  const string Station="station_field_fabricator",Grip="recipe_grip_stabilised_pistol",Topic="npc_ossa:servo_look";
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static FieldOrderSet Orders()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");
  static NpcDefinition Npc(string name)=>AssetDatabase.LoadAssetAtPath<NpcDefinition>("Assets/AthenHill/Data/"+name+".asset");
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.id,x.n)),0,out var r),Is.True,r);
  sealed class State:IQuestState
  {
   public bool primer=true,pistol=true,reported;public string order;public OrderStage stage;public readonly HashSet<string> flags=new HashSet<string>(),items=new HashSet<string>(),recipes=new HashSet<string>();
   public bool PrimerComplete=>primer;public bool HasPistol=>pistol;public string CurrentOrderId=>order;public OrderStage Stage=>stage;
   public bool CurrentReported=>reported;public bool HasFlag(string id)=>flags.Contains(id);
   public bool HasItem(string id)=>items.Contains(id);public bool KnowsRecipe(string id)=>recipes.Contains(id);
  }
  (ShopModel pack,CraftingModel model,FieldOrderProgress orders) Run()
  {
   var pack=new ShopModel(City().items);
   var catalog=ScriptableObject.CreateInstance<CharacterCatalog>();catalog.skills=new[]{new CharacterSkill{id="engineering",initial=20}};
   var model=new CraftingModel(Data(),City().items,pack,()=>true,character:new CharacterModel(catalog,pack));
   return (pack,model,new FieldOrderProgress(Orders()));
  }

  [Test] public void DataShapeTheGripIsTaughtByOssaAndTheServoSaysWhoToShow()
  {
   var recipe=Data().recipes.Single(r=>r.id==Grip);
   Assert.That(recipe.unlocks.Select(u=>(u.type,u.id)),Is.EqualTo(new[]{("identify",Topic)}),"no acquireItem unlock any more");
   Assert.That(recipe.knownByDefault,Is.False);
   Assert.That(City().items.Single(i=>i.id=="droid_servo_damaged").identifyBy,Is.EqualTo("npc_ossa"));
   var ossa=Npc("npc_ossa");var node=ossa.nodes.Single(n=>n.id=="servo_look");
   Assert.That(ossa.nodes.Any(n=>n.id=="servo"));Assert.That(ossa.nodes.Single(n=>n.id=="servo").choices.Any(c=>c.next=="servo_look"));
   Assert.That(ossa.entries.First().node,Is.EqualTo("servo"),"offered before her other openings");
   Assert.That(node.voice,Is.Not.Null,"voiced");
   foreach(var n in ossa.nodes.Where(n=>n.id.StartsWith("servo")))foreach(var c in n.choices)Assert.That(QuestConditions.Problems(c.requires),Is.Empty);
   foreach(var e in ossa.entries.Concat(Npc("npc_brann").entries))Assert.That(QuestConditions.Problems(e.requires),Is.Empty,e.requires);
  }

  [Test] public void CannotFabricateBeforeOssaIdentifiesAndPickupTeachesNothing()
  {
   var (pack,model,_)=Run();
   Give(pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));
   Assert.That(model.Acquire("droid_servo_damaged"),Is.Empty,"picking the servo up no longer teaches the grip");
   Assert.That(model.Knows(Grip),Is.False);
   Assert.That(model.CanCraft(Grip,Station,out var reason),Is.False);Assert.That(reason,Is.EqualTo("recipe_locked"));
   Assert.That(model.TryCraft(Grip,Station,out reason),Is.False);Assert.That(pack.Quantity("droid_servo_damaged"),Is.EqualTo(1),"nothing used");
   Assert.That(model.NeedsIdentifying("droid_servo_damaged"),"the pickup note says who to show it to");
   Assert.That(model.NeedsIdentifying("scrap_alloy"),Is.False);
   Assert.That(model.UnidentifiedCarried(Grip)?.id,Is.EqualTo("droid_servo_damaged"));
  }

  [Test] public void IdentificationTeachesTheRecipeOnceOnlyForItsOwnTopic()
  {
   var (pack,model,_)=Run();
   Give(pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));
   Assert.That(model.Identify("npc_ossa:servo"),Is.Empty,"the first node explains; only the look closer node teaches");
   Assert.That(model.Identify("npc_brann:servo_look"),Is.Empty,"another colonist's topic does not count");
   Assert.That(model.Identify(Topic).Select(r=>r.id),Is.EqualTo(new[]{Grip}));
   Assert.That(model.Identify(Topic),Is.Empty,"once");
   Assert.That(model.Knows(Grip));Assert.That(model.NeedsIdentifying("droid_servo_damaged"),Is.False);Assert.That(model.UnidentifiedCarried(Grip),Is.Null);
   Assert.That(model.TryCraft(Grip,Station,out var reason),reason);
   Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));
  }

  [Test] public void DialogueOffersOssasServoTalkOnlyWhileCarryingAnUnidentifiedServo()
  {
   var ossa=Npc("npc_ossa");var s=new State();
   Assert.That(DialogueFlow.StartNode(ossa,s),Is.EqualTo("greeting"));
   s.items.Add("droid_servo_damaged");Assert.That(DialogueFlow.StartNode(ossa,s),Is.EqualTo("servo"));
   s.recipes.Add(Grip);Assert.That(DialogueFlow.StartNode(ossa,s),Is.EqualTo("greeting"),"already identified (old saves too)");
   s.items.Clear();s.recipes.Clear();Assert.That(DialogueFlow.StartNode(ossa,s),Is.EqualTo("greeting"),"no servo");
   var brann=Npc("npc_brann");s.flags.Add("brann_toolkit");
   s.order="order_steady_hands";s.stage=OrderStage.Identify;Assert.That(DialogueFlow.StartNode(brann,s),Is.EqualTo("steady_identify"));
   s.stage=OrderStage.Report;Assert.That(DialogueFlow.StartNode(brann,s),Is.EqualTo("report_ready"));
   Assert.That(QuestConditions.Evaluate("carry:droid_servo_damaged, !recipe:"+Grip,new State()),Is.False);
  }

  [Test] public void SteadyHandsFlowsGatherIdentifyReportFabricateFitTestFire()
  {
   var (pack,model,orders)=Run();
   Assert.That(orders.Begin().id,Is.EqualTo("order_steady_hands"));
   Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Gather));
   Give(pack,("scrap_alloy",2),("nanite_residue",5));
   Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Gather),"no servo yet");
   Give(pack,("droid_servo_damaged",1));
   Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Identify));
   Assert.That(orders.Objective(model,pack),Does.Contain("Warden Ossa"));
   Assert.That(orders.NoteReport("npc_brann"),"the generic report tracker alone would accept Brann (FieldOrders ignores the visit while Identify)");
   model.Identify(Topic);
   Assert.That(orders.Stage(model,pack),Is.Not.EqualTo(OrderStage.Identify));
   // the order goes on exactly as before
   var fresh=new FieldOrderProgress(Orders());fresh.Begin();
   Assert.That(fresh.Stage(model,pack),Is.EqualTo(OrderStage.Report));Assert.That(fresh.GuidanceKey(model,pack),Is.EqualTo("dealer"));
   Assert.That(fresh.NoteReport("npc_brann"));Assert.That(fresh.Stage(model,pack),Is.EqualTo(OrderStage.Fabricate));
   Assert.That(model.TryCraft(Grip,Station,out var reason),reason);
   Assert.That(fresh.Stage(model,pack),Is.EqualTo(OrderStage.Fit));
   Assert.That(model.TryFit("grip_stabilised_pistol",out _));Assert.That(fresh.Stage(model,pack),Is.EqualTo(OrderStage.TestFire));
   Assert.That(fresh.NoteShot(model));Assert.That(fresh.Advance(model,id=>false).Select(o=>o.id),Is.EqualTo(new[]{"order_steady_hands"}));
  }

  [Test] public void OldSavesThatAlreadyKnowTheGripSkipIdentify()
  {
   var (pack,model,orders)=Run();
   // an old save: the schematic was learned on pickup and is stored with the known recipes
   Assert.That(model.Unlock(Grip));
   orders.Restore(new FieldOrderState{index=0,id="order_steady_hands"});
   Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Gather));
   Give(pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));
   Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Report),"no Identify step for a known schematic");
   Assert.That(model.NeedsIdentifying("droid_servo_damaged"),Is.False,"no 'show this to Ossa' note");
   var s=new State();s.items.Add("droid_servo_damaged");s.recipes.Add(Grip);
   Assert.That(DialogueFlow.StartNode(Npc("npc_ossa"),s),Is.EqualTo("greeting"));
   // and a save made at the Fabricate step is unchanged
   orders.NoteReport("npc_brann");Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Fabricate));
  }

  [Test] public void KnownRecipesRoundTripThroughRestoreAfterIdentification()
  {
   var (pack,model,_)=Run();
   model.Identify(Topic);
   var known=model.KnownRecipes.ToList();
   var (pack2,model2,_)=Run();
   foreach(var id in known)model2.Unlock(id);
   Assert.That(model2.Knows(Grip));Assert.That(model2.Identify(Topic),Is.Empty);
  }
 }
}
