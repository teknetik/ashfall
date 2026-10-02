using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 public class MerchantPanelTests
 {
  [Test] public void CounterStockRespectsVendorPolicyAndRarePartRules()
  {
   var supplies=new ItemSpec{id="water",name="Water",buyPrice=4,sellPrice=2};
   var gear=new ItemSpec{id="plate",name="Plate",buyPrice=30,sellPrice=8,tags=new[]{"armour"}};
   var part=new ItemSpec{id="wire",name="Wire",partsPrice=8,sellPrice=2,sellOnly=true};
   var rare=new ItemSpec{id="core",name="Core",partsPrice=60,sellPrice=5,sellOnly=true,rarity=ItemRarity.Rare};
   var reward=new ItemSpec{id="reward",name="Reward",buyPrice=0,excludeFromTrade=true};
   var general=new ShopProfile();var salvage=new ShopProfile{supplies=false,parts=true,salvage=true};
   Assert.That(MerchantStock.CanBuy(supplies,general));Assert.That(MerchantStock.CanBuy(gear,general));
   Assert.That(MerchantStock.CanBuy(gear,salvage),Is.False);Assert.That(MerchantStock.CanBuy(part,salvage));
   Assert.That(MerchantStock.CanBuy(rare,general),Is.False);Assert.That(MerchantStock.CanBuy(reward,general),Is.False);
   Assert.That(MerchantStock.CanSell(gear,salvage),Is.False);Assert.That(MerchantStock.CanSell(rare,salvage));
   Assert.That(MerchantStock.Price(part,general,false),Is.EqualTo(8));Assert.That(MerchantStock.Price(part,general,true),Is.EqualTo(2));
  }
  [Test] public void InventoryAndSearchDriveSellListWithoutFabricatingStock()
  {
   var catalog=ScriptableObject.CreateInstance<CityCatalog>();catalog.items=new[]{new ItemSpec{id="plate",name="Armour Plate",description="A bolted liner",buyPrice=20,sellPrice=5,tags=new[]{"armour"}},new ItemSpec{id="water",name="Water",buyPrice=4,sellPrice=2}};
   try
   {
    var pack=new ShopModel(catalog.items,25);var profile=new ShopProfile();
    Assert.That(MerchantStock.Items(catalog,pack,profile,true),Is.Empty);
    pack.Grant("plate",1,0,out _);
    Assert.That(MerchantStock.Items(catalog,pack,profile,true," BOLTED ","Equipment").Select(x=>x.id),Is.EqualTo(new[]{"plate"}));
    Assert.That(MerchantStock.Items(catalog,pack,profile,false,"water").Select(x=>x.id),Is.EqualTo(new[]{"water"}));
   }
   finally{Object.DestroyImmediate(catalog);}
  }
  [Test] public void StockSelectionUpdatesDetailedPaneAndPurchaseRemainsAtomic()
  {
   var catalog=AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
   var root=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
   var go=new GameObject("merchant test");go.SetActive(false);
   try
   {
    var session=go.AddComponent<GameSession>();session.catalog=catalog;var pack=new ShopModel(catalog.items,25);
    typeof(GameSession).GetProperty("Shop").SetValue(session,pack);typeof(GameSession).GetProperty("State").SetValue(session,CityState.Shop);
    var panel=new MerchantPanel(root,session,null);panel.Refresh();panel.Select("water_flask");
    Assert.That(root.Q<Label>("merchant-name").text,Is.EqualTo("Water Flask"));
    Assert.That(root.Q<Label>("merchant-after").text,Does.Contain("21"));
    Assert.That(root.Q<Button>("merchant-trade").enabledSelf);
    panel.Select("medkit");
    Assert.That(root.Q<Button>("merchant-item-medkit").tabIndex,Is.Zero);
    Assert.That(root.Q<Button>("merchant-item-water_flask").tabIndex,Is.EqualTo(-1));
    panel.Select("water_flask");
    typeof(MerchantPanel).GetMethod("Trade",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(panel,null);
    Assert.That(pack.Credits,Is.EqualTo(21));Assert.That(pack.Quantity("water_flask"),Is.EqualTo(1));Assert.That(session.boughtFlask);
    panel.SetMode(true);panel.Select("scrap_coil");
    typeof(MerchantPanel).GetMethod("Trade",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(panel,null);
    Assert.That(pack.Credits,Is.EqualTo(22));Assert.That(pack.Quantity("scrap_coil"),Is.Zero);Assert.That(session.soldScrap);
    pack.CapacityFailure=_=>"Pack capacity is full.";panel.SetMode(false);panel.Select("water_flask");
    Assert.That(root.Q<Button>("merchant-trade").enabledSelf,Is.False);
    Assert.That(pack.Credits,Is.EqualTo(22));Assert.That(pack.Quantity("water_flask"),Is.EqualTo(1));
   }
   finally{Object.DestroyImmediate(go);Time.timeScale=1;}
  }
 }
}
