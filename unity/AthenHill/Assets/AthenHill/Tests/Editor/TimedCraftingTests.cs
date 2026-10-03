using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// Timed crafting at Brann's workbench (3 Oct 2026): parts are used and the output given only when the bench timer
 /// completes, in one transaction; cancelling, leaving the bench or taking damage changes nothing.
 public class TimedCraftingTests
 {
  const string Station="station_field_fabricator";
  const string Grip="recipe_grip_stabilised_pistol";
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static VisualElement Hud()=>AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
  static KeyValuePair<string,int> Delta(string id,int n)=>new KeyValuePair<string,int>(id,n);
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>Delta(x.id,x.n)),0,out var r),Is.True,r);
  static void GiveGripParts(ShopModel pack)=>Give(pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));
  static Dictionary<string,int> Snapshot(ShopModel pack)=>City().items.ToDictionary(x=>x.id,x=>pack.Quantity(x.id));
  static (ShopModel pack,CraftingModel model) Model(CraftingCatalog data=null)
  {
   data=data?data:Data();
   var pack=new ShopModel(City().items);var model=new CraftingModel(data,City().items,pack,()=>true);
   foreach(var r in data.recipes)model.Unlock(r.id);
   return (pack,model);
  }
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public ShopModel pack;public CraftingModel model;
   public Rig()
   {
    go=new GameObject("timed crafting rig");go.SetActive(false);
    session=go.AddComponent<GameSession>();session.catalog=City();crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    var player=new GameObject("combat");player.transform.SetParent(go.transform);combat=player.AddComponent<PlayerCombat>();combat.hasPistol=true;crafting.combat=combat;
    pack=new ShopModel(City().items);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",CityState.Fabricator);Set(session,"ActiveStationId",Station);
    Set(crafting,"Model",model);Set(crafting,"Session",session);combat.BindLoadout(model.Loadout);
   }
   public void Dispose(){Object.DestroyImmediate(go);Time.timeScale=1;}
  }

  [Test] public void BenchTimesAreAuthoredForEveryWardSchematic()
  {
   var data=Data();
   float S(string id)=>data.recipes.Single(r=>r.id==id).craftSeconds;
   foreach(var id in new[]{"recipe_wound_coil","recipe_charge_cell_core","recipe_alloy_plate"})Assert.That(S(id),Is.InRange(4f,6f),id);
   foreach(var r in data.recipes.Where(r=>r.group==RecipeGroup.MarkI||r.group==RecipeGroup.MarkII||r.group==RecipeGroup.WeaponMod))Assert.That(r.craftSeconds,Is.InRange(8f,12f),r.id);
   foreach(var r in data.recipes.Where(r=>r.group==RecipeGroup.Armour))Assert.That(r.craftSeconds,Is.InRange(15f,25f),r.id);
   Assert.That(S("recipe_field_leggings"),Is.EqualTo(data.recipes.Where(r=>r.group==RecipeGroup.Armour).Max(r=>r.craftSeconds)),"leggings take longest");
   Assert.That(S("recipe_field_helmet"),Is.LessThan(S("recipe_field_armguards")));Assert.That(S("recipe_field_gloves"),Is.LessThan(S("recipe_field_armguards")));
   Assert.That(S("recipe_field_rifle"),Is.InRange(18f,22f));
  }

  [Test] public void TimerCompletionIsOneAtomicInventoryChange()
  {
   var (pack,model)=Model();GiveGripParts(pack);
   float seconds=model.CraftSeconds(Grip);Assert.That(seconds,Is.GreaterThan(0));
   var before=Snapshot(pack);int changed=0;model.Changed+=()=>changed++;
   Assert.That(model.BeginCraft(Grip,Station,10,out var reason),reason);
   Assert.That(model.Job,Is.Not.Null);Assert.That(model.Job.recipeId,Is.EqualTo(Grip));
   Assert.That(Snapshot(pack),Is.EqualTo(before),"nothing is taken when the timer starts");
   Assert.That(model.TickCraft(10+seconds-.01f,out _,out _),Is.EqualTo(CraftTick.None));
   Assert.That(model.Job.Progress(10+seconds/2),Is.EqualTo(.5f).Within(1e-4));Assert.That(model.Job.Remaining(10+seconds/2),Is.EqualTo(seconds/2).Within(1e-4));
   Assert.That(Snapshot(pack),Is.EqualTo(before));Assert.That(changed,Is.Zero);
   Assert.That(model.TickCraft(10+seconds,out var job,out reason),Is.EqualTo(CraftTick.Completed),reason);
   Assert.That(job.recipeId,Is.EqualTo(Grip));Assert.That(model.Job,Is.Null);
   Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));
   Assert.That(pack.Quantity("droid_servo_damaged"),Is.EqualTo(before["droid_servo_damaged"]-1));
   Assert.That(pack.Quantity("scrap_alloy"),Is.EqualTo(before["scrap_alloy"]-2));
   Assert.That(pack.Quantity("nanite_residue"),Is.EqualTo(before["nanite_residue"]-5));
   Assert.That(model.Crafts,Is.EqualTo(1));Assert.That(model.CraftCount(Grip),Is.EqualTo(1));Assert.That(changed,Is.EqualTo(1),"one Changed, on the commit");
   Assert.That(model.TickCraft(10+seconds*3,out _,out _),Is.EqualTo(CraftTick.None),"a completed job never pays twice");
   Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));
  }

  [Test] public void CancelChangesNothingAndTheBenchIsFreeAgain()
  {
   var (pack,model)=Model();GiveGripParts(pack);var before=Snapshot(pack);
   Assert.That(model.BeginCraft(Grip,Station,0,out _));
   Assert.That(model.BeginCraft("recipe_wound_coil",Station,1,out var reason),Is.False);Assert.That(reason,Is.EqualTo("busy"),"one job at a time");
   Assert.That(model.CancelCraft(out var job));Assert.That(job.recipeId,Is.EqualTo(Grip));
   Assert.That(model.Job,Is.Null);Assert.That(Snapshot(pack),Is.EqualTo(before));Assert.That(model.Crafts,Is.Zero);
   Assert.That(model.TickCraft(1000,out _,out _),Is.EqualTo(CraftTick.None),"a cancelled job never completes later");
   Assert.That(model.CancelCraft(out _),Is.False);
   Assert.That(model.BeginCraft(Grip,Station,5,out reason),reason);
   Assert.That(model.TickCraft(5+model.CraftSeconds(Grip),out _,out reason),Is.EqualTo(CraftTick.Completed),reason);
  }

  [Test] public void PartsThatLeaveThePackMidwayFailTheCraftWithNothingChanged()
  {
   var (pack,model)=Model();GiveGripParts(pack);
   Assert.That(model.BeginCraft(Grip,Station,0,out _));
   Give(pack,("nanite_residue",-1));
   var before=Snapshot(pack);
   Assert.That(model.TickCraft(model.Job.EndsAt,out _,out var reason),Is.EqualTo(CraftTick.Failed));
   Assert.That(reason,Is.EqualTo("missing_ingredients"));
   Assert.That(Snapshot(pack),Is.EqualTo(before),"no partial consumption, no output");Assert.That(model.Job,Is.Null);Assert.That(model.Crafts,Is.Zero);
   // Starting without the parts is refused up front.
   Assert.That(model.BeginCraft(Grip,Station,0,out reason),Is.False);Assert.That(reason,Is.EqualTo("missing_ingredients"));Assert.That(model.Job,Is.Null);
  }

  [Test] public void InstantRecipesAndTryCraftAreUnchanged()
  {
   var data=Object.Instantiate(Data());
   try
   {
    foreach(var r in data.recipes)r.craftSeconds=0;
    var (pack,model)=Model(data);GiveGripParts(pack);
    Assert.That(model.CraftSeconds(Grip),Is.Zero);
    Assert.That(model.BeginCraft(Grip,Station,0,out var reason),reason);
    Assert.That(model.Job,Is.Null,"0 s schematics commit straight away");Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));
   }
   finally{Object.DestroyImmediate(data);}
   // TryCraft itself stays the instant transaction (tests and fixtures use it), whatever the bench time.
   var (pack2,model2)=Model();GiveGripParts(pack2);
   Assert.That(model2.TryCraft(Grip,Station,out var r2),r2);Assert.That(pack2.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));Assert.That(model2.Job,Is.Null);
  }

  [Test] public void RestoreDropsAJobInProgress()
  {
   var (pack,model)=Model();GiveGripParts(pack);var before=Snapshot(pack);
   var state=model.Capture();
   Assert.That(model.BeginCraft(Grip,Station,0,out _));
   model.Restore(state);
   Assert.That(model.Job,Is.Null);Assert.That(Snapshot(pack),Is.EqualTo(before));
  }

  [Test] public void SessionCancelsWhenTheBenchClosesOrThePlayerIsHit()
  {
   using var rig=new Rig();GiveGripParts(rig.pack);rig.model.Unlock(Grip);var before=Snapshot(rig.pack);
   var finished=new List<(string id,bool ok,string reason)>();rig.crafting.CraftFinished+=(j,ok,r)=>finished.Add((j.recipeId,ok,r));
   Assert.That(rig.crafting.Craft(Grip,out var reason),reason);Assert.That(rig.crafting.Job,Is.Not.Null);
   Assert.That(rig.crafting.Fit("grip_stabilised_pistol",out reason),Is.False);Assert.That(reason,Is.EqualTo("busy"),"fitting waits for the bench");
   typeof(CraftingSession).GetMethod("OnDamaged",Any).Invoke(rig.crafting,new object[]{5f,Vector3.zero});
   Assert.That(rig.crafting.Job,Is.Null);Assert.That(finished.Last(),Is.EqualTo((Grip,false,"cancelled")));Assert.That(Snapshot(rig.pack),Is.EqualTo(before));
   Assert.That(rig.session.notice,Does.Contain("Nothing was used"));
   // Leaving the bench (any state but Fabricator) cancels on the next frame at the latest.
   Assert.That(rig.crafting.Craft(Grip,out reason),reason);
   Set(rig.session,"State",CityState.Play);
   typeof(CraftingSession).GetMethod("Update",Any).Invoke(rig.crafting,null);
   Assert.That(rig.crafting.Job,Is.Null);Assert.That(Snapshot(rig.pack),Is.EqualTo(before));Assert.That(finished.Count,Is.EqualTo(2));
   // Back at the bench the timer completes through the session: output, notice and event.
   Set(rig.session,"State",CityState.Fabricator);
   Assert.That(rig.crafting.Craft(Grip,out reason),reason);
   rig.crafting.TickCraft(rig.crafting.Job.EndsAt);
   Assert.That(rig.pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));Assert.That(finished.Last(),Is.EqualTo((Grip,true,"ok")));
   Assert.That(rig.session.notice,Does.Contain("fabricated"));
  }

  [Test] public void FabricatorShowsBenchTimeProgressAndCancel()
  {
   using var rig=new Rig();GiveGripParts(rig.pack);rig.model.Unlock(Grip);
   var root=Hud();var panel=new FabricatorPanel(root,rig.session,rig.crafting);
   panel.Opened();panel.Select(Grip);panel.Refresh();
   float seconds=rig.model.CraftSeconds(Grip);string time=CraftingText.Duration(seconds);
   var craft=root.Q<Button>("fabricator-craft");var cancel=root.Q<Button>("fabricator-cancel");var progress=root.Q("fab-progress");
   Assert.That(cancel,Is.Not.Null);Assert.That(progress,Is.Not.Null);
   Assert.That(root.Q<Label>("fab-description").text,Does.Contain("Bench time: "+time));
   Assert.That(root.Q<Button>("fab-recipe-"+Grip).tooltip,Does.Contain(time+" at the bench"));
   Assert.That(craft.tooltip,Does.Contain(time));
   Assert.That(progress.style.display.value,Is.EqualTo(DisplayStyle.None));Assert.That(cancel.focusable,Is.False,"Cancel is no tab stop while idle");
   panel.Craft();
   var job=rig.crafting.Job;Assert.That(job,Is.Not.Null);Assert.That(rig.pack.Quantity("grip_stabilised_pistol"),Is.Zero);
   panel.Refresh();
   Assert.That(progress.style.display.value,Is.EqualTo(DisplayStyle.Flex));
   Assert.That(craft.enabledSelf,Is.False);Assert.That(root.Q<Button>("fabricator-fit").enabledSelf,Is.False);
   Assert.That(cancel.enabledSelf&&cancel.focusable,"Cancel is reachable by keyboard while working");
   Assert.That(panel.ActionFocus,Is.SameAs(cancel));Assert.That(panel.FocusAfterAction,Is.SameAs(cancel));
   Assert.That(root.Q<Button>("fab-recipe-"+Grip).Q<Label>(className:"fab-recipe-state").text,Is.EqualTo("Working"));
   panel.UpdateProgress(job.startedAt+seconds/2);
   Assert.That(panel.ProgressShown,Is.EqualTo(.5f).Within(1e-3));
   Assert.That(panel.ProgressText,Does.Contain(CraftingText.Duration(seconds/2)+" left"));Assert.That(root.Q<Label>("fab-progress-label").text,Is.EqualTo(panel.ProgressText));
   // Cancel: nothing used, actions back.
   var before=Snapshot(rig.pack);
   panel.Cancel();
   Assert.That(rig.crafting.Job,Is.Null);Assert.That(Snapshot(rig.pack),Is.EqualTo(before));
   Assert.That(progress.style.display.value,Is.EqualTo(DisplayStyle.None));Assert.That(craft.enabledSelf);
   // Again, to completion: the made part is offered for fitting.
   panel.Craft();rig.crafting.TickCraft(rig.crafting.Job.EndsAt);
   Assert.That(rig.pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));
   Assert.That(progress.style.display.value,Is.EqualTo(DisplayStyle.None));
   Assert.That(root.Q<Button>("fabricator-fit").enabledSelf);Assert.That(panel.FocusAfterAction,Is.SameAs(root.Q<Button>("fabricator-fit")));
  }

  [Test] public void DurationsReadAsWholeSeconds()
  {
   Assert.That(CraftingText.Duration(8),Is.EqualTo("8 s"));Assert.That(CraftingText.Duration(3.2f),Is.EqualTo("4 s"));
   Assert.That(CraftingText.Duration(0),Is.EqualTo("0 s"));Assert.That(CraftingText.Duration(65),Is.EqualTo("1:05"));
  }
 }
}
