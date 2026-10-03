using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
namespace AthenHill.Tests
{
 /// Gameplay v2 M1: every recipe chain from raw salvage to a fitted mod, schematic unlocks and tag allocation.
 public class RecipeChainTests
 {
  const string Station="station_field_fabricator";
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static KeyValuePair<string,int> Delta(string id,int n)=>new KeyValuePair<string,int>(id,n);
  static (ShopModel pack,CraftingModel model) Model(){var pack=new ShopModel(City().items);var model=new CraftingModel(Data(),City().items,pack,()=>true);foreach(var r in Data().recipes)model.Unlock(r.id);return (pack,model);}
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>Delta(x.id,x.n)),0,out var r),Is.True,r);
  static void Craft(CraftingModel model,string recipe,int times=1){for(int i=0;i<times;i++)Assert.That(model.TryCraft(recipe,Station,out var r),Is.True,recipe+": "+r);}

  [Test] public void ContentKeepsLegacyRowsAndEveryReferenceResolves()
  {
   var city=City();var craft=Data();
   Assert.That(city.items.Take(3).Select(x=>x.id),Is.EqualTo(new[]{"water_flask","medkit","scrap_coil"}));
   Assert.That(city.items.Take(3).Select(x=>(x.buyPrice,x.sellPrice)),Is.EqualTo(new[]{(4,2),(9,4),(2,1)}));
   foreach(var id in new[]{"droid_servo_damaged","scrap_alloy","nanite_residue","copper_filament","micro_capacitor","grip_stabilised_pistol","optic_lens_cracked","actuator_intact","lattice_shard","foreman_control_core","alloy_plate","wound_coil","charge_cell_core","barrel_bored_alloy","cell_salvaged_capacitor","grip_gyro_braced","barrel_lattice_focused","cell_overclocked"})
    Assert.That(city.items.Count(x=>x.id==id),Is.EqualTo(1),id);
   var ids=city.items.Select(x=>x.id).ToHashSet();
   foreach(var r in craft.recipes){Assert.That(ids.Contains(r.outputItemId),r.id);foreach(var i in r.inputs)Assert.That(i.kind=="item"?ids.Contains(i.id):city.items.Any(x=>x.HasTag(i.id)),r.id+"/"+i.id);}
   foreach(var t in craft.lootTables)foreach(var e in t.entries)Assert.That(ids.Contains(e.itemId),t.id+"/"+e.itemId);
   foreach(var m in craft.modifiers)Assert.That(ids.Contains(m.itemId)&&craft.weapons.Any(w=>m.weaponIds.Contains(w.id)&&w.slots.Contains(m.slot)),m.id);
   // Every mod has exactly one schematic; every Mark II schematic needs a rare part.
   foreach(var mod in craft.modifiers)Assert.That(craft.recipes.Count(r=>r.outputItemId==mod.itemId),Is.EqualTo(1),mod.itemId);
   var rare=city.items.Where(x=>x.rarity==ItemRarity.Rare).Select(x=>x.id).ToHashSet();
   foreach(var r in craft.recipes.Where(r=>r.group==RecipeGroup.MarkII))Assert.That(r.inputs.Any(i=>i.kind=="item"&&rare.Contains(i.id)),r.id);
   Assert.That(craft.recipes.Where(r=>r.group==RecipeGroup.MarkII).All(r=>r.unlocks.Any(u=>u.type=="acquireItem"&&u.id=="foreman_control_core")));
  }

  [Test] public void CapacitorCellChainFromRawSalvage()
  {
   var (pack,model)=Model();
   // Starting pack already holds one scrap coil (the conductor line prefers it over filament).
   Give(pack,("copper_filament",2),("micro_capacitor",2),("nanite_residue",3),("scrap_alloy",2));
   Craft(model,"recipe_wound_coil");Assert.That(pack.Quantity("scrap_coil"),Is.Zero);Assert.That(pack.Quantity("copper_filament"),Is.Zero);
   Craft(model,"recipe_charge_cell_core");Craft(model,"recipe_cell_salvaged_capacitor");
   foreach(var id in new[]{"copper_filament","micro_capacitor","nanite_residue","scrap_alloy","wound_coil","charge_cell_core"})Assert.That(pack.Quantity(id),Is.Zero,id);
   Assert.That(model.TryFit("cell_salvaged_capacitor",out var r),r);
   Assert.That(model.Loadout.Stats.nanoMax,Is.EqualTo(135));
   Assert.That(model.CraftCount("recipe_wound_coil"),Is.EqualTo(1));Assert.That(model.Crafts,Is.EqualTo(3));
  }

  [Test] public void BoredBarrelChainFromRawSalvage()
  {
   var (pack,model)=Model();
   Give(pack,("scrap_alloy",6),("nanite_residue",4),("copper_filament",2));
   Craft(model,"recipe_alloy_plate",2);Craft(model,"recipe_wound_coil");Craft(model,"recipe_barrel_bored_alloy");
   foreach(var id in new[]{"scrap_alloy","nanite_residue","copper_filament","scrap_coil","alloy_plate","wound_coil"})Assert.That(pack.Quantity(id),Is.Zero,id);
   Assert.That(model.TryFit("barrel_bored_alloy",out var r),r);
   Assert.That(model.Loadout.Stats.damage,Is.EqualTo(40.8f).Within(1e-4));Assert.That(model.Loadout.Stats.range,Is.EqualTo(36));   // 2 Oct 2026: 30 m pistol + 6 m bored barrel
  }

  [Test] public void MarkTwoChainsNeedTheirRareParts()
  {
   var (pack,model)=Model();
   Give(pack,("scrap_alloy",18),("nanite_residue",18),("copper_filament",12),("micro_capacitor",4),("optic_lens_cracked",1),("actuator_intact",1),("lattice_shard",1));
   Craft(model,"recipe_alloy_plate",6);Craft(model,"recipe_wound_coil",4);Craft(model,"recipe_charge_cell_core",2);
   Craft(model,"recipe_grip_gyro_braced");
   Craft(model,"recipe_barrel_lattice_focused");
   // The only lattice shard went into the barrel.
   Assert.That(model.TryCraft("recipe_cell_overclocked",Station,out var r),Is.False);Assert.That(r,Is.EqualTo("missing_ingredients"));
   Assert.That(CraftingText.Reason(r,model,model.Recipe("recipe_cell_overclocked")),Is.EqualTo("Missing parts: 1 × Quantum Lattice Shard."));
   Give(pack,("lattice_shard",1));Craft(model,"recipe_cell_overclocked");
   foreach(var mod in new[]{"grip_gyro_braced","barrel_lattice_focused","cell_overclocked"})Assert.That(model.TryFit(mod,out r),r);
   var s=model.Loadout.Stats;
   Assert.That(s.recoil,Is.EqualTo(23));Assert.That(s.damage,Is.EqualTo(49.3f).Within(1e-4));Assert.That(s.nanoMax,Is.EqualTo(160));Assert.That(s.nanoPerShot,Is.EqualTo(7));
  }

  [Test] public void ConductorTagLineUsesACoilOrAThirdFilamentButNeverDoubleSpends()
  {
   var inputs=Data().recipes.Single(r=>r.id=="recipe_wound_coil").inputs;
   var items=City().items;
   var pack=new ShopModel(items);// starts with one scrap coil
   Give(pack,("copper_filament",2));
   Assert.That(IngredientAllocator.TryAllocate(inputs,items,pack,out var use));
   Assert.That(use.ToDictionary(x=>x.Key,x=>x.Value),Is.EquivalentTo(new Dictionary<string,int>{{"copper_filament",2},{"scrap_coil",1}}));
   Assert.That(pack.TryApply(new[]{Delta("scrap_coil",-1),Delta("copper_filament",1)},0,out _));
   Assert.That(IngredientAllocator.TryAllocate(inputs,items,pack,out use));
   Assert.That(use.ToDictionary(x=>x.Key,x=>x.Value),Is.EquivalentTo(new Dictionary<string,int>{{"copper_filament",3}}));
   Assert.That(pack.TryApply(new[]{Delta("copper_filament",-2),Delta("scrap_coil",2)},0,out _));// 1 filament, 2 coils
   Assert.That(IngredientAllocator.TryAllocate(inputs,items,pack,out _),Is.False);
  }

  [Test] public void SchematicsUnlockByOrderAndByAcquisition()
  {
   var pack=new ShopModel(City().items);var model=new CraftingModel(Data(),City().items,pack,()=>true);
   Assert.That(model.KnownRecipes,Is.EquivalentTo(new[]{"recipe_field_rifle","recipe_rifle_precision_barrel"}));
   Assert.That(model.Acquire("droid_servo_damaged").Select(r=>r.id),Is.EqualTo(new[]{"recipe_grip_stabilised_pistol"}));
   Assert.That(model.Acquire("droid_servo_damaged"),Is.Empty);
   Assert.That(model.Acquire("micro_capacitor").Select(r=>r.id),Is.EqualTo(new[]{"recipe_charge_cell_core"}));
   Assert.That(model.OrderStarted("order_keep_charge").Select(r=>r.id),Is.EquivalentTo(new[]{"recipe_wound_coil","recipe_cell_salvaged_capacitor"}));
   Assert.That(model.OrderStarted("order_bore_true").Select(r=>r.id),Is.EquivalentTo(new[]{"recipe_alloy_plate","recipe_barrel_bored_alloy"}));
   Assert.That(model.Acquire("foreman_control_core").Select(r=>r.id),Is.EquivalentTo(new[]{"recipe_grip_gyro_braced","recipe_barrel_lattice_focused","recipe_cell_overclocked"}));
   // 3 Oct 2026: each Warden Kit order reveals its armour schematic (alloy plate is already known here)
   Assert.That(model.OrderStarted("order_kit_helmet").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_helmet"}));
   Assert.That(model.OrderStarted("order_kit_arms").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_armguards"}));
   Assert.That(model.OrderStarted("order_kit_hands").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_gloves"}));
   Assert.That(model.OrderStarted("order_kit_legs").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_leggings"}));
   Assert.That(model.KnownRecipes.Count,Is.EqualTo(Data().recipes.Length));
   // Locked schematics explain themselves in words.
   var fresh=new CraftingModel(Data(),City().items,pack,()=>true);
   Assert.That(fresh.TryCraft("recipe_grip_gyro_braced",Station,out var r),Is.False);
   Assert.That(CraftingText.Reason(r,fresh,fresh.Recipe("recipe_grip_gyro_braced")),Does.StartWith("Schematic not yet known.").And.Contain("foreman"));
  }

  [Test] public void ComponentsNeedNoPistolButModsDo()
  {
   var pack=new ShopModel(City().items);bool pistol=false;
   var model=new CraftingModel(Data(),City().items,pack,()=>pistol);foreach(var r in Data().recipes)model.Unlock(r.id);
   Give(pack,("scrap_alloy",8),("nanite_residue",4),("copper_filament",2));
   Craft(model,"recipe_alloy_plate",2);Craft(model,"recipe_wound_coil");
   Assert.That(model.TryCraft("recipe_barrel_bored_alloy",Station,out var reason),Is.False);Assert.That(reason,Is.EqualTo("missing_weapon"));
   Assert.That(CraftingText.Reason(reason,model),Does.Contain("carry or equip the required weapon"));
   pistol=true;Craft(model,"recipe_barrel_bored_alloy");
  }

  [Test] public void FailureReasonsAreWordsNotCodes()
  {
   var (pack,model)=Model();
   Assert.That(model.TryCraft("recipe_charge_cell_core",Station,out var r),Is.False);
   var text=CraftingText.Reason(r,model,model.Recipe("recipe_charge_cell_core"));
   Assert.That(text,Is.EqualTo("Missing parts: 2 × Any capacitor, 1 × Wound Copper Coil, 3 × Any tier-one nanites."));
   foreach(var code in new[]{"recipe_locked","wrong_station","missing_weapon","output_stack_full","stack_full","already_fitted","not_carried","not_a_mod","wrong_slot","empty_slot","overflow","unknown_recipe","something_new"})
   {
    var words=CraftingText.Reason(code,model,model.Recipe("recipe_wound_coil"),"grip_stabilised_pistol");
    Assert.That(words,Is.Not.Empty.And.Not.Contain("_"),code);
   }
  }
 }
}
