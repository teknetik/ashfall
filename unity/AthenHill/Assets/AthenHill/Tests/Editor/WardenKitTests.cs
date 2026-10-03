using System.IO;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// 3 Oct 2026 (Carl: "that should be a crafting mission and not so easy to get"): the Warden kit is built, not issued.
 /// The primer grants no armour, nobody sells the Field pieces, each piece's schematic is revealed by its own field
 /// order, and every new material drops from more than one kind of Berms source.
 public class WardenKitTests
 {
  static readonly string[] Kit={"field_helmet","field_armguards","field_gloves","field_leggings"};
  static readonly string[] KitOrders={"order_kit_helmet","order_kit_arms","order_kit_hands","order_kit_legs"};
  static readonly string[] Materials={"strap_webbing","padded_liner","rivet_stock"};
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static FieldOrderSet Set()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");
  static NpcDefinition Npc(string id)=>AssetDatabase.LoadAssetAtPath<NpcDefinition>("Assets/AthenHill/Data/"+id+".asset");

  [Test] public void ThePrimerIssuesNoKit()
  {
   var go=new GameObject("primer");
   try{var t=go.AddComponent<BermsTutorial>();Assert.That(t.kitItems,Is.Empty);Assert.That(t.kitNotice,Is.Empty);Assert.That(t.GrantKit(),Is.Zero);}
   finally{Object.DestroyImmediate(go);}
   var scene=File.ReadAllText("Assets/AthenHill/Scenes/AthenHill.unity");
   int i=scene.IndexOf("AthenHill.BermsTutorial\n",System.StringComparison.Ordinal);Assert.That(i,Is.GreaterThan(0));
   Assert.That(scene.Substring(i,Mathf.Min(4000,scene.Length-i)),Does.Contain("  kitItems: []\n"),"the saved primer component carries no kit");
  }

  [Test] public void KitPiecesAreBuiltNotBought()
  {
   var mira=Npc("npc_mira");var brann=Npc("npc_brann");
   foreach(var id in Kit)
   {
    var item=City().items.Single(x=>x.id==id);
    Assert.That(item.excludeFromTrade,id);
    Assert.That(MerchantStock.CanBuy(item,mira.shop),Is.False,id+" is not on Mira's counter");
    Assert.That(MerchantStock.CanBuy(item,brann.shop),Is.False,id+" is not on Brann's counter");
   }
   var pack=new ShopModel(City().items,500);
   Assert.That(pack.Trade("field_helmet",true,out _),Is.False);Assert.That(pack.Credits,Is.EqualTo(500));Assert.That(pack.Quantity("field_helmet"),Is.Zero);
   // the vest and boots stay the colonist's starting gear
   foreach(var id in new[]{"field_vest","field_boots"})Assert.That(City().items.Any(x=>x.id==id),id);
  }

  [Test] public void EachKitSchematicIsRevealedByItsOwnOrder()
  {
   var pack=new ShopModel(City().items);var model=new CraftingModel(Data(),City().items,pack,()=>true);
   Assert.That(Data().GroupName(RecipeGroup.Armour),Is.EqualTo("Armour"));
   for(int i=0;i<Kit.Length;i++)
   {
    var recipe=Data().recipes.Single(r=>r.outputItemId==Kit[i]);
    Assert.That(recipe.group,Is.EqualTo(RecipeGroup.Armour),recipe.id);Assert.That(recipe.knownByDefault,Is.False,recipe.id);
    Assert.That(recipe.stationId,Is.EqualTo("station_field_fabricator"),recipe.id);Assert.That(recipe.requirements,Is.Empty,recipe.id);
    Assert.That(recipe.unlocks.Select(u=>u.type+":"+u.id),Is.EqualTo(new[]{"orderStart:"+KitOrders[i]}),recipe.id);
    Assert.That(model.Knows(recipe.id),Is.False,recipe.id);
    Assert.That(model.OrderStarted(KitOrders[i]).Select(r=>r.id),Does.Contain(recipe.id));
   }
   Assert.That(Data().recipes.Single(r=>r.id=="recipe_alloy_plate").unlocks.Any(u=>u.type=="orderStart"&&u.id=="order_kit_helmet"),"plate is rolled from the first kit order");
   Assert.That(model.Knows("recipe_alloy_plate"));
   // the four orders follow Steady Hands in order, each a CraftItem order for its piece; only the helm reports to Brann
   var orders=Set().orders.ToList();int steady=orders.FindIndex(o=>o.id=="order_steady_hands");
   for(int i=0;i<KitOrders.Length;i++)
   {
    var o=orders[steady+1+i];
    Assert.That(o.id,Is.EqualTo(KitOrders[i]));Assert.That(o.goal,Is.EqualTo(FieldOrderGoal.CraftItem),o.id);Assert.That(o.targetItemId,Is.EqualTo(Kit[i]),o.id);
    if(i==0)Assert.That(o.reportTo,Is.EqualTo("npc_brann"),o.id);else Assert.That(o.reportTo,Is.Null.Or.Empty,o.id);Assert.That(o.urgentStart,Is.False,o.id);Assert.That(o.engageLine,Is.Null.Or.Empty,o.id);
   }
  }

  [Test] public void EveryKitMaterialDropsFromSeveralBermsSources()
  {
   var tables=Data().lootTables;
   foreach(var id in Materials)
   {
    var item=City().items.Single(x=>x.id==id);
    Assert.That(item.HasTag("salvage")&&item.sellOnly&&item.partsPrice==0&&!ShopModel.SellsAsPart(item),id+" is loot-only salvage");
    Assert.That(tables.Count(t=>t.entries.Any(e=>e.itemId==id&&e.chance>0)),Is.GreaterThanOrEqualTo(2),id+" drops from more than one source");
    Assert.That(tables.SelectMany(t=>t.entries).Where(e=>e.itemId==id).All(e=>e.chance>=1||e.pityAfter>0),id+" has bad-luck protection");
   }
   Assert.That(tables.Single(t=>t.id=="loot_feral_scrap_drone").entries.Any(e=>Materials.Contains(e.itemId)),Is.False,"the first-contact drones drop no kit material");
   // every input of every armour schematic can be obtained: a loot drop or another schematic's output
   foreach(var r in Data().recipes.Where(r=>r.group==RecipeGroup.Armour))foreach(var i in r.inputs)
    Assert.That(tables.Any(t=>t.entries.Any(e=>e.itemId==i.id))||Data().recipes.Any(x=>x.outputItemId==i.id),r.id+"/"+i.id);
  }
 }
}
