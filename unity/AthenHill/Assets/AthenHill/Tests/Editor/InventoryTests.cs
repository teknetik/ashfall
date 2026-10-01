using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEditor;
using UnityEngine.InputSystem;
using System.Reflection;
namespace AthenHill.Tests
{
 public class InventoryTests
 {
  static ItemSpec[] Items()=>new[]{new ItemSpec{id="water_flask",name="Water Flask",description="Clean water",buyPrice=4,sellPrice=2},new ItemSpec{id="scrap_coil",name="Scrap Coil",description="Copper coil",buyPrice=2,sellPrice=1,startingQuantity=1}};
  [Test] public void PackListsOnlyCarriedItemsAndReflectsTrade()
  {
   var items=Items();var shop=new ShopModel(items);
   Assert.That(InventoryView.Items(items,shop).Select(x=>x.id),Is.EqualTo(new[]{"scrap_coil"}));
   Assert.That(shop.Trade("water_flask",true,out _),Is.True);
   Assert.That(InventoryView.Items(items,shop).Select(x=>x.id),Is.EqualTo(new[]{"water_flask","scrap_coil"}));
   Assert.That(shop.Trade("scrap_coil",false,out _),Is.True);
   Assert.That(InventoryView.Items(items,shop).Select(x=>x.id),Is.EqualTo(new[]{"water_flask"}));
  }
  [Test] public void FullPackRejectsPurchaseWithoutChangingCreditsOrItems()
  {
   var items=new[]{new ItemSpec{id="alloy",startingQuantity=1,weightKg=2},new ItemSpec{id="flask",name="Flask",buyPrice=4,weightKg=3}};
   var shop=new ShopModel(items,25);
   shop.CapacityFailure=next=>next["alloy"]*2+next["flask"]*3>4?"Not enough carrying or storage capacity.":null;
   Assert.That(shop.Trade("flask",true,out var message),Is.False);
   Assert.That(message,Does.Contain("capacity"));
   Assert.That(shop.Credits,Is.EqualTo(25));Assert.That(shop.Quantity("flask"),Is.Zero);
   Assert.That(shop.Purchases,Is.Zero);
  }
  [Test] public void OverviewAndFullDetailsOnlyExposeSerializedFacts()
  {
   var item=Items()[1];
   Assert.That(InventoryView.Overview(item,1),Does.Contain("Copper coil"));
   Assert.That(InventoryView.Overview(item,1),Does.Contain("1 carried"));
   Assert.That(InventoryView.Details(item,1),Does.Contain("Buy 2 cr"));
   Assert.That(InventoryView.Details(item,1),Does.Contain("Sell 1 cr"));
   Assert.That(InventoryView.Details(item,1),Does.Not.Contain("Damage"));
   Assert.That(InventoryView.Details(item,1),Does.Not.Contain("Item ID"));
  }
  [Test] public void TabToggleAndDetailsStayInsideInventoryModal()
  {
   var go=new GameObject("inventory test");go.SetActive(false);
   try
   {
    var input=go.AddComponent<GameInput>();
    input.definition=AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/AthenHill/Data/Controls.inputactions");
    var player=go.AddComponent<PlayerMotor>();
    var session=go.AddComponent<GameSession>();session.input=input;session.player=player;
    typeof(GameSession).GetProperty("Shop",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(session,new ShopModel(Items()));
    go.SetActive(true);
    typeof(GameInput).GetMethod("OnEnable",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(input,null);
    typeof(GameSession).GetProperty("State",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(session,CityState.Play);
    session.ToggleInventory();Assert.That(session.State,Is.EqualTo(CityState.Inventory));Assert.That(player.Blocked,Is.True);
    session.OpenItemDetails("scrap_coil");Assert.That(session.DetailItemId,Is.EqualTo("scrap_coil"));
    session.Close();Assert.That(session.State,Is.EqualTo(CityState.Inventory));Assert.That(session.DetailItemId,Is.Null);
    session.ToggleInventory();Assert.That(session.State,Is.EqualTo(CityState.Play));Assert.That(player.Blocked,Is.False);
    session.Open(CityState.Shop);session.ToggleInventory();Assert.That(session.State,Is.EqualTo(CityState.Shop));
    typeof(GameSession).GetProperty("State",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(session,CityState.MainMenu);
    session.ToggleInventory();Assert.That(session.State,Is.EqualTo(CityState.MainMenu));
    typeof(GameSession).GetProperty("State",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(session,CityState.Settings);
    session.ToggleInventory();Assert.That(session.State,Is.EqualTo(CityState.Settings));
   }
   finally{Object.DestroyImmediate(go);Time.timeScale=1;}
  }
  [Test] public void MissingMetadataIsNotInvented()
  {
   var item=new ItemSpec{id="test",name="Test",description="Description",buyPrice=0,sellPrice=0};
   Assert.That(InventoryView.Details(item,2),Does.Not.Contain("Category"));
   Assert.That(InventoryView.Details(item,2),Does.Not.Contain("Weight"));
  }
 }
}
