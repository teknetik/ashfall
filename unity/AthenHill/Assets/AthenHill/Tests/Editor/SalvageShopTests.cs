using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// 1 Oct 2026: the walk-in Salvage shop. Brann's quest-aware dialogue, the first field order's report to him, counters
 /// that show only their trader's lists, the workbench that replaced the field cart, and saves of flags and visits.
 public class SalvageShopTests
 {
  sealed class State:IQuestState
  {
   public bool primer,pistol,reported;public string order;public OrderStage stage;public readonly HashSet<string> flags=new HashSet<string>();
   public bool PrimerComplete=>primer;public bool HasPistol=>pistol;public string CurrentOrderId=>order;public OrderStage Stage=>stage;
   public bool CurrentReported=>reported;public bool HasFlag(string id)=>flags.Contains(id);
  }
  static NpcDefinition Brann()=>AssetDatabase.LoadAssetAtPath<NpcDefinition>("Assets/AthenHill/Data/npc_brann.asset");
  static FieldOrderSet Orders()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");

  [Test] public void ConditionsEvaluateTermsNegationAndConjunction()
  {
   var s=new State{primer=true,order="order_steady_hands",stage=OrderStage.Report};
   Assert.That(QuestConditions.Evaluate("",s));Assert.That(QuestConditions.Evaluate(null,s));
   Assert.That(QuestConditions.Evaluate("primer",s));Assert.That(QuestConditions.Evaluate("!primer",s),Is.False);
   Assert.That(QuestConditions.Evaluate("order:order_steady_hands, stage:Report, !reported",s));
   Assert.That(QuestConditions.Evaluate("order:order_keep_charge",s),Is.False);
   Assert.That(QuestConditions.Evaluate("stage:report",s),"stage names ignore case");
   s.flags.Add("brann_met");Assert.That(QuestConditions.Evaluate("flag:brann_met",s));Assert.That(QuestConditions.Evaluate("!flag:brann_met",s),Is.False);
   Assert.That(QuestConditions.Problems("primer, stage:Nowhere, colour:red, order:").ToArray(),Is.EqualTo(new[]{"stage:Nowhere","colour:red","order:"}));
   LogAssert.Expect(LogType.Warning,"Unknown dialogue condition: colour:red");
   Assert.That(QuestConditions.Evaluate("colour:red",s),Is.False,"unknown terms never hold");
  }

  [Test] public void BrannOpensWithTheRightLineAtEachStepOfTheFirstOrder()
  {
   var d=Brann();Assert.That(d,Is.Not.Null);
   var s=new State();
   Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("first_visit"));
   s.flags.Add("brann_met");Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("greeting"));
   s.primer=true;s.pistol=true;s.order="order_steady_hands";s.stage=OrderStage.Gather;
   Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("report_early"));
   s.stage=OrderStage.Report;Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("report_ready"));
   s.reported=true;s.stage=OrderStage.Gather;Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("steady_gather"));
   s.stage=OrderStage.Fabricate;Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("steady_bench"));
   s.stage=OrderStage.Fit;Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("steady_fit"));
   s.stage=OrderStage.TestFire;Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("steady_test"));
   s.order="order_keep_charge";s.reported=false;s.stage=OrderStage.Gather;Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("orders"));
   s.order=null;s.stage=OrderStage.FreePlay;Assert.That(DialogueFlow.StartNode(d,s),Is.EqualTo("greeting"));
  }

  [Test] public void BrannsDialogueHasNoDeadEndsAndFitsTheHud()
  {
   var d=Brann();
   Assert.That(d.id,Is.EqualTo("npc_brann"));Assert.That(d.displayName,Is.EqualTo("Brann"));
   Assert.That(d.shop.supplies,Is.False);Assert.That(d.shop.parts&&d.shop.salvage);Assert.That(d.shop.title,Is.EqualTo("Salvage"));
   Assert.That(d.nodes.Any(n=>n.id=="greeting"));
   foreach(var e in d.entries){Assert.That(QuestConditions.Problems(e.requires),Is.Empty,e.node);Assert.That(d.nodes.Any(n=>n.id==e.node),e.node);}
   foreach(var n in d.nodes)
   {
    Assert.That(n.choices.Length,Is.InRange(1,GameSession.MaxChoices),n.id);
    Assert.That(n.text.Length,Is.LessThan(420),n.id+" fits the dialogue panel");
    foreach(var c in n.choices)
    {
     Assert.That(QuestConditions.Problems(c.requires),Is.Empty,n.id+"/"+c.label);
     Assert.That(new[]{"","close","shop","fabricator"},Does.Contain(c.action),c.label);
     if(string.IsNullOrEmpty(c.action))Assert.That(d.nodes.Any(x=>x.id==c.next),n.id+"/"+c.label+" leads somewhere");
    }
    Assert.That(DialogueFlow.Choices(n,new State(),GameSession.MaxChoices).Length,Is.GreaterThan(0),n.id+" offers something without a pistol");
   }
   // the bench is never offered before the pistol is carried (it fits mods to it)
   Assert.That(d.nodes.SelectMany(n=>DialogueFlow.Choices(n,new State(),GameSession.MaxChoices)).Any(c=>c.action=="fabricator"),Is.False);
   Assert.That(d.nodes.SelectMany(n=>DialogueFlow.Choices(n,new State{pistol=true},GameSession.MaxChoices)).Any(c=>c.action=="fabricator"));
  }

  [Test] public void ReportVisitsRoundTripThroughSavesAndOldSavesAskForTheVisit()
  {
   var set=Orders();
   var a=new FieldOrderProgress(set);a.Begin();Assert.That(a.NoteReport("npc_brann"));
   var b=new FieldOrderProgress(set);b.Restore(JsonUtility.FromJson<FieldOrderState>(JsonUtility.ToJson(a.Capture())));
   Assert.That(b.CurrentReported);Assert.That(b.Reported("order_steady_hands"));
   var old=new FieldOrderProgress(set);old.Restore(JsonUtility.FromJson<FieldOrderState>("{\"index\":0,\"testFired\":[]}"));
   Assert.That(old.CurrentReported,Is.False);
   Assert.That(set.orders.Where(o=>!string.IsNullOrEmpty(o.reportTo)).Select(o=>o.id),Is.EqualTo(new[]{"order_steady_hands","order_kit_helmet","order_long_arm"}),"the grip, the Warden helm and the rifle orders ask for the visit");
   Assert.That(set.orders[0].reportTo,Is.EqualTo("npc_brann"));Assert.That(set.orders[0].reportGuidance,Is.EqualTo("dealer"));
   Assert.That(set.fabricateFormat,Does.Contain("Brann"));Assert.That(set.fitFormat,Does.Contain("Brann"));
   foreach(var o in set.orders)foreach(var line in new[]{o.startLine,o.completeLine,o.brief})Assert.That(line??"",Does.Not.Contain("fabricator"),o.id);
  }

  [Test] public void CityVisitStateCarriesStoryFlags()
  {
   var back=JsonUtility.FromJson<CityVisitState>(JsonUtility.ToJson(new CityVisitState{flags=new[]{"brann_met"}}));
   Assert.That(back.flags,Is.EqualTo(new[]{"brann_met"}));
   Assert.That(JsonUtility.FromJson<CityVisitState>("{\"visitedHill\":true}").flags,Is.Null.Or.Empty,"older saves carry none");
  }

  [Test] public void ShopRefusalsNameTheTrader()
  {
   var city=AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
   var s=new ShopModel(city.items,100);
   Assert.That(s.BuyPart("actuator_intact",1,out var m,"Brann"),Is.False);Assert.That(m,Does.StartWith("Brann does not stock"));
   Assert.That(s.BuyPart("actuator_intact",1,out m),Is.False);Assert.That(m,Does.StartWith("Mira does not stock"));
   Assert.That(s.Trade("scrap_alloy",true,out m,"Brann"),Is.False);Assert.That(m,Does.StartWith("Brann buys"));
   Assert.That(s.BuyPart("scrap_alloy",1,out m,"Brann"));Assert.That(s.Quantity("scrap_alloy"),Is.EqualTo(1));
  }

  [Test] public void HudHasAThirdChoiceAndNamedShopSections()
  {
   var root=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
   foreach(var n in new[]{"choice0","choice1","choice2"})Assert.That(root.Q<Button>(n),Is.Not.Null,n);
   Assert.That(root.Q("shop-panel"),Is.Not.Null);
   var go=new GameObject("merchant policy test");go.SetActive(false);
   try
   {
    var session=go.AddComponent<GameSession>();session.catalog=AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
    typeof(GameSession).GetProperty("Shop").SetValue(session,new ShopModel(session.catalog.items));
    var merchant=new MerchantPanel(root,session,null);merchant.Refresh();
    foreach(var n in new[]{"merchant-name","merchant-balance","merchant-empty","merchant-capacity"})Assert.That(root.Q<Label>(n),Is.Not.Null,n);
    foreach(var n in new[]{"merchant-tab-buy","merchant-tab-sell","merchant-trade","merchant-sell-all"})Assert.That(root.Q<Button>(n),Is.Not.Null,n);
    Assert.That(root.Query<Button>(className:"merchant-row").ToList().Count,Is.GreaterThan(9),"Expanded catalogue includes supplies, parts and authored equipment");
    var brann=new ShopProfile{supplies=false,parts=true,salvage=true};
    Assert.That(MerchantStock.Items(session.catalog,session.Shop,brann,false).All(i=>ShopModel.SellsAsPart(i)),"Brann remains a parts and salvage dealer");
   }
   finally{Object.DestroyImmediate(go);}
  }

  [Test] public void SceneHasTheWalkInShopWiredIntoTheFirstOrder()
  {
   var scene=EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
   try
   {
    T[] All<T>()where T:Component=>scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<T>(true)).ToArray();
    var session=All<GameSession>().Single();var crafting=session.GetComponent<CraftingSession>();var orders=session.GetComponent<FieldOrders>();
    var brann=session.npcs.Single(n=>n&&n.definition&&n.definition.id=="npc_brann");
    Assert.That(brann.countsForCityVisit,Is.False,"the four-colonist city visit is unchanged");
    Assert.That(session.npcs.Count(n=>n&&n.countsForCityVisit),Is.EqualTo(4));
    Assert.That(brann.actor,Is.Not.Null);
    var station=crafting.fabricator.GetComponent<CraftingStationMarker>();
    Assert.That(station&&station.enabled&&station.stationId=="station_field_fabricator"&&station.session==session);
    Assert.That(station.title,Is.EqualTo("Salvage workbench"));
    Assert.That(brann.workbench,Is.EqualTo(station));
    // only the workbench is a station now; the outpost tool cart stays as dressing
    Assert.That(All<CraftingStationMarker>().Where(m=>m.enabled).ToArray(),Is.EqualTo(new[]{station}));
    Assert.That(orders.guidanceTargets.Single(t=>t.key=="dealer").point,Is.EqualTo(brann.transform));
    Assert.That(orders.guidanceTargets.Single(t=>t.key=="fabricator").point,Is.EqualTo(station.transform));
    Assert.That(Vector3.Distance(station.transform.position,brann.transform.position),Is.GreaterThan(session.interactionRange+station.GetComponent<WorldInteractable>().range));
    Assert.That(All<BermsTutorial>().Single().lineComplete,Does.Contain("Brann"));
    var room=All<InteriorLighting>().Single();
    Assert.That(room.lamps.Length,Is.GreaterThan(0));
    foreach(var l in room.lamps)Assert.That((uint)l.renderingLayerMask,Is.EqualTo(room.interiorLayer),l.name+" lights the interior layer only");
    Assert.That(room.renderers.Count,Is.GreaterThan(5));
    foreach(var r in room.renderers)Assert.That((r.renderingLayerMask&room.interiorLayer)!=0,r.name);
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
