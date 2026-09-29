using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 public class CraftingSliceTests
 {
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static KeyValuePair<string,int> Delta(string id,int n)=>new KeyValuePair<string,int>(id,n);
  static CraftRecipe Grip()=>Data().recipes.Single(x=>x.id=="recipe_grip_stabilised_pistol");
  [Test] public void RealAssetsHaveFeasibleFixedTutorialDropsAndPreserveShopRows()
  {
   Assert.That(City(),Is.Not.Null);Assert.That(Data(),Is.Not.Null);
   Assert.That(City().items.Take(3).Select(x=>x.id),Is.EqualTo(new[]{"water_flask","medkit","scrap_coil"}));
   Assert.That(Grip().inputs.Select(x=>x.quantity),Is.EqualTo(new[]{1,2,5}));
   var guaranteed=new ShopModel(City().items);
   foreach(var id in new[]{"loot_feral_scrap_drone","loot_feral_worker_droid","loot_feral_worker_droid","loot_feral_scrap_drone"})
    foreach(var entry in Data().lootTables.Single(x=>x.id==id).entries.Where(x=>x.chance==1))Assert.That(guaranteed.TryApply(new[]{Delta(entry.itemId,entry.minQuantity)},0,out _));
   Assert.That(IngredientAllocator.TryAllocate(Grip().inputs,City().items,guaranteed,out _));
   foreach(var pair in new[]{("FeralScrapDrone","loot_feral_scrap_drone"),("FeralWorkerDroid","loot_feral_worker_droid")})
   {
    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/"+pair.Item1+".prefab");
    Assert.That(prefab.GetComponent<LootSource>().lootTableId,Is.EqualTo(pair.Item2));
   }
  }
  [Test] public void TransactionSumsDuplicatesAndFailsWithoutPartialWrites()
  {
   var shop=new ShopModel(City().items);
   Assert.That(shop.TryApply(new[]{Delta("scrap_alloy",2),Delta("scrap_alloy",3)},0,out _));
   Assert.That(shop.Quantity("scrap_alloy"),Is.EqualTo(5));
   Assert.That(shop.TryApply(new[]{Delta("scrap_alloy",int.MaxValue),Delta("scrap_alloy",-int.MaxValue)},0,out _));
   Assert.That(shop.Quantity("scrap_alloy"),Is.EqualTo(5));
   Assert.That(shop.TryApply(new[]{Delta("scrap_alloy",-2),Delta("unknown",1)},1,out var unknown),Is.False);
   Assert.That(unknown,Is.EqualTo("unknown_item"));Assert.That(shop.Quantity("scrap_alloy"),Is.EqualTo(5));Assert.That(shop.Credits,Is.EqualTo(25));
   Assert.That(shop.TryApply(new[]{Delta("scrap_alloy",26),Delta("water_flask",1)},0,out var cap),Is.False);
   Assert.That(cap,Is.EqualTo("stack_full"));Assert.That(shop.Quantity("water_flask"),Is.Zero);
   Assert.That(shop.TryApply(new[]{Delta("scrap_alloy",-1)},int.MaxValue,out var overflow),Is.False);
   Assert.That(overflow,Is.EqualTo("overflow"));Assert.That(shop.Quantity("scrap_alloy"),Is.EqualTo(5));
   // v2: raw salvage sells to Mira (sell-only); mods never trade.
   Assert.That(shop.Trade("scrap_alloy",true,out _),Is.False);Assert.That(shop.Quantity("scrap_alloy"),Is.EqualTo(5));
   Assert.That(shop.Trade("scrap_alloy",false,out _),Is.True);Assert.That(shop.Quantity("scrap_alloy"),Is.EqualTo(4));
   Assert.That(shop.Trade("grip_stabilised_pistol",false,out _),Is.False);
   Assert.That(shop.Trade("water_flask",true,out _),Is.True);
  }
  [Test] public void AllocatorBacktracksOnAnExactNeedAndNeverDoubleSpends()
  {
   var items=new[]{new ItemSpec{id="coil",sellPrice=0,tags=new[]{"conductive"}},new ItemSpec{id="copper",sellPrice=1,tags=new[]{"conductive"}}};
   var shop=new ShopModel(items);
   Assert.That(shop.TryApply(new[]{Delta("coil",1),Delta("copper",1)},0,out _));
   var input=new[]{new CraftIngredient{kind="tag",id="conductive",quantity=1},new CraftIngredient{kind="item",id="coil",quantity=1}};
   Assert.That(IngredientAllocator.TryAllocate(input,items,shop,out var allocation));
   Assert.That(allocation.ToDictionary(x=>x.Key,x=>x.Value),Is.EquivalentTo(new Dictionary<string,int>{{"coil",1},{"copper",1}}));
   Assert.That(shop.TryApply(new[]{Delta("copper",-1)},0,out _));
   Assert.That(IngredientAllocator.TryAllocate(input,items,shop,out _),Is.False);
  }
  [Test] public void CraftAndFitAreSeparateAtomicTransactions()
  {
   var pack=new ShopModel(City().items);
   bool pistol=false;var model=new CraftingModel(Data(),City().items,pack,()=>pistol);
   Assert.That(model.TryCraft(Grip().id,"station_field_fabricator",out var reason),Is.False);
   Assert.That(reason,Is.EqualTo("recipe_locked"));
   model.Acquire("droid_servo_damaged");
   Assert.That(pack.TryApply(new[]{Delta("droid_servo_damaged",1),Delta("scrap_alloy",2),Delta("nanite_residue",4)},0,out _));
   pistol=true;Assert.That(model.TryCraft(Grip().id,"station_field_fabricator",out reason),Is.False);
   Assert.That(reason,Is.EqualTo("missing_ingredients"));Assert.That(pack.Quantity("scrap_alloy"),Is.EqualTo(2));
   Assert.That(pack.TryApply(new[]{Delta("nanite_residue",1)},0,out _));
   Assert.That(model.TryCraft(Grip().id,"wrong",out reason),Is.False);
   Assert.That(model.TryCraft(Grip().id,"station_field_fabricator",out reason));
   Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));Assert.That(model.RecoilStat,Is.EqualTo(38));
   pistol=false;Assert.That(model.TryFit("grip_stabilised_pistol",out reason),Is.False);Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));
   pistol=true;Assert.That(model.TryFit("grip_stabilised_pistol",out reason));Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.Zero);
   Assert.That(model.RecoilStat,Is.EqualTo(31));Assert.That(model.TryRemove("grip",out reason));Assert.That(model.RecoilStat,Is.EqualTo(38));
  }
  [Test] public void FittedGripCannotBeRemovedIntoFullStack()
  {
   var pack=new ShopModel(City().items);var model=new CraftingModel(Data(),City().items,pack,()=>true);
   Assert.That(pack.TryApply(new[]{Delta("grip_stabilised_pistol",1)},0,out _));Assert.That(model.TryFit("grip_stabilised_pistol",out _));
   Assert.That(pack.TryApply(new[]{Delta("grip_stabilised_pistol",3)},0,out _));
   Assert.That(model.TryRemove("grip",out var reason),Is.False);Assert.That(reason,Is.EqualTo("stack_full"));
   Assert.That(model.Loadout.Fitted("grip"),Is.EqualTo("grip_stabilised_pistol"));Assert.That(model.RecoilStat,Is.EqualTo(31));
  }
  [Test] public void LootIsInstanceScopedBeforeClearAndRepaysOnlyAfterRevival()
  {
   var go=new GameObject("test worker");
   try
   {
    var health=go.AddComponent<Health>();var droid=go.AddComponent<FeralDroid>();
    var loot=go.AddComponent<LootSource>();loot.lootTableId="loot_feral_worker_droid";
    // EditMode does not call MonoBehaviour lifecycle methods on these synthetic objects.
    foreach(var component in new MonoBehaviour[]{health,droid,loot})
    {
     var awake=component.GetType().GetMethod("Awake",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);
     awake?.Invoke(component,null);
    }
    typeof(LootSource).GetMethod("OnEnable",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).Invoke(loot,null);
    int paid=0;var events=new List<string>();
    loot.Bind(id=>{paid++;events.Add("loot:"+id);});
    droid.Killed+=_=>events.Add("cleared");
    Assert.That(health.Damage(health.max,go.transform.position));
    Assert.That(health.Damage(health.max,go.transform.position),Is.False);
    Assert.That(events,Is.EqualTo(new[]{"loot:loot_feral_worker_droid","cleared"}));
    droid.ResetToHome(true);
    Assert.That(health.Damage(health.max,go.transform.position));Assert.That(paid,Is.EqualTo(2));
   }
   finally{UnityEngine.Object.DestroyImmediate(go);}
  }
  [Test] public void CameraKickUsesFittedStatAndRespectsFixedAndAimBounds()
  {
   var go=new GameObject("test camera");
   try
   {
    var camera=go.AddComponent<FollowCamera>();
    var pack=new ShopModel(City().items);var model=new CraftingModel(Data(),City().items,pack,()=>true);
    Assert.That(model.RecoilStat*.05f,Is.EqualTo(1.9f).Within(.0001f));
    camera.pitch=0;camera.ApplyShotKick(model.RecoilStat*.05f,.5f,.18f);
    Assert.That(camera.pitch,Is.EqualTo(-1.9f).Within(.0001f));
    Assert.That(pack.TryApply(new[]{Delta("grip_stabilised_pistol",1)},0,out _));
    Assert.That(model.TryFit("grip_stabilised_pistol",out _));
    Assert.That(model.RecoilStat*.05f,Is.EqualTo(1.55f).Within(.0001f));
    camera.aimMode=true;camera.pitch=-69.9f;camera.ApplyShotKick(model.RecoilStat*.05f,.5f,.18f);
    Assert.That(camera.pitch,Is.EqualTo(-70).Within(.0001f));
    camera.FixedView=true;camera.ApplyShotKick(5,.5f,.18f);
    Assert.That(camera.pitch,Is.EqualTo(-70).Within(.0001f));
   }
   finally{UnityEngine.Object.DestroyImmediate(go);}
  }
 }
}
