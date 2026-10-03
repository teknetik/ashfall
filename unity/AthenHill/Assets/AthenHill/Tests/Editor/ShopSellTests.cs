using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill.Tests
{
 /// Gameplay v2 M3: Mira buys common/uncommon salvage; rare parts, components and mods never trade; the legacy
 /// Basic General rows are unchanged.
 public class ShopSellTests
 {
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.id,x.n)),0,out var r),Is.True,r);

  [Test] public void CatalogSellRulesFollowRarityAndKind()
  {
   foreach(var item in City().items)
   {
    bool raw=item.HasTag("salvage")&&item.rarity!=ItemRarity.Rare&&item.id!="scrap_coil";
    if(raw){Assert.That(ShopModel.BuysAsSalvage(item),item.id);Assert.That(item.sellPrice,Is.InRange(1,5),item.id);Assert.That(item.buyPrice,Is.Zero,item.id);}
    else Assert.That(ShopModel.BuysAsSalvage(item),Is.False,item.id);
    if(item.rarity==ItemRarity.Rare||item.HasTag("refined")||item.HasTag("weapon_mod"))Assert.That(item.excludeFromTrade,item.id);
   }
   Assert.That(City().items.Where(ShopModel.BuysAsSalvage).Select(x=>x.id),Is.EquivalentTo(new[]{"droid_servo_damaged","scrap_alloy","nanite_residue","copper_filament","micro_capacitor","optic_lens_cracked","strap_webbing","padded_liner","rivet_stock"}));
  }

  [Test] public void SellListShowsOnlyCarriedSalvageMiraBuys()
  {
   var pack=new ShopModel(City().items);
   Assert.That(SalvageSalePanel.Sellable(City().items,pack),Is.Empty,"the starting scrap coil stays in its legacy row");
   Give(pack,("scrap_alloy",3),("lattice_shard",1),("alloy_plate",1),("grip_stabilised_pistol",1),("optic_lens_cracked",1),("water_flask",1));
   Assert.That(SalvageSalePanel.Sellable(City().items,pack).Select(x=>x.id),Is.EqualTo(new[]{"scrap_alloy","optic_lens_cracked"}));
  }

  [Test] public void SalvageSalesAreAtomicAndNeverBuyBack()
  {
   var pack=new ShopModel(City().items);Give(pack,("scrap_alloy",5),("micro_capacitor",2),("lattice_shard",1));
   Assert.That(pack.Sell("scrap_alloy",5,out var m));Assert.That(m,Is.EqualTo("Sold 5 × Scrap Alloy for 5 credits."));
   Assert.That(pack.Credits,Is.EqualTo(30));Assert.That(pack.Quantity("scrap_alloy"),Is.Zero);Assert.That(pack.Sales,Is.EqualTo(1));
   Assert.That(pack.Sell("micro_capacitor",3,out m),Is.False);Assert.That(m,Does.Contain("only 2"));Assert.That(pack.Quantity("micro_capacitor"),Is.EqualTo(2));Assert.That(pack.Credits,Is.EqualTo(30));
   Assert.That(pack.Sell("micro_capacitor",0,out _),Is.False);
   Assert.That(pack.Trade("micro_capacitor",false,out _));Assert.That(pack.Credits,Is.EqualTo(33));
   Assert.That(pack.Trade("micro_capacitor",true,out m),Is.False);Assert.That(m,Does.Contain("does not stock"));Assert.That(pack.Credits,Is.EqualTo(33));
   Assert.That(pack.Sell("lattice_shard",1,out m),Is.False);Assert.That(m,Does.Contain("not tradeable"));Assert.That(pack.Quantity("lattice_shard"),Is.EqualTo(1));
   var rich=new ShopModel(City().items,int.MaxValue-1);Give(rich,("droid_servo_damaged",1));
   Assert.That(rich.Sell("droid_servo_damaged",1,out _),Is.False,"credit overflow refuses the sale");Assert.That(rich.Quantity("droid_servo_damaged"),Is.EqualTo(1));
  }

  [Test] public void LegacyFlaskPurchaseAndScrapSaleAreUnchanged()
  {
   var pack=new ShopModel(City().items,City().startingCredits);
   Assert.That(pack.Trade("water_flask",true,out var m));Assert.That(m,Is.EqualTo("Bought Water Flask for 4 credits."));Assert.That(pack.Credits,Is.EqualTo(21));
   Assert.That(pack.Trade("scrap_coil",false,out m));Assert.That(m,Is.EqualTo("Sold Scrap Coil for 1 credit."));Assert.That(pack.Credits,Is.EqualTo(22));
   Assert.That(pack.Trade("scrap_coil",true,out _));Assert.That(pack.Credits,Is.EqualTo(20));
   Assert.That(pack.Purchases,Is.EqualTo(2));Assert.That(pack.Sales,Is.EqualTo(1));
  }

  [Test] public void SessionSellSalvageNeedsTheShopAndRaisesTraded()
  {
   var go=new GameObject("sell test");go.SetActive(false);
   try
   {
    var input=go.AddComponent<GameInput>();input.definition=AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/AthenHill/Data/Controls.inputactions");
    var player=go.AddComponent<PlayerMotor>();var session=go.AddComponent<GameSession>();session.input=input;session.player=player;session.catalog=City();
    var pack=new ShopModel(City().items);Give(pack,("copper_filament",4));
    typeof(GameSession).GetProperty("Shop",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(session,pack);
    go.SetActive(true);
    typeof(GameInput).GetMethod("OnEnable",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(input,null);
    var state=typeof(GameSession).GetProperty("State",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic);
    int traded=0;session.Traded+=()=>traded++;
    state.SetValue(session,CityState.Play);
    Assert.That(session.SellSalvage("copper_filament",1),Is.False,"only inside Basic General");
    state.SetValue(session,CityState.Shop);
    Assert.That(session.SellSalvage("copper_filament",4));Assert.That(pack.Quantity("copper_filament"),Is.Zero);Assert.That(traded,Is.EqualTo(1));
    Assert.That(session.SellSalvage("water_flask",1),Is.False,"legacy stock is sold through its own row");
    Assert.That(session.notice,Is.EqualTo("Mira does not buy that."));
    Assert.That(session.Trade("water_flask",true));Assert.That(traded,Is.EqualTo(2));Assert.That(session.boughtFlask);
   }
   finally{Object.DestroyImmediate(go);Time.timeScale=1;}
  }
 }
}
