using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// Focused Edit Mode tests for crafting/progression/order polish fixes.
 public class CraftingProgressionPolishTests
 {
  const string Station="station_field_fabricator";
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static CharacterCatalog Chars()=>Resources.Load<CharacterCatalog>("CharacterCatalog");
  static KeyValuePair<string,int> Delta(string id,int n)=>new KeyValuePair<string,int>(id,n);

  [Test] public void CanCraftAndBeginCraftRejectOverCapacityBeforeStartingTimer()
  {
   var data=ScriptableObject.CreateInstance<CraftingCatalog>();
   var charCat=ScriptableObject.CreateInstance<CharacterCatalog>();
   try
   {
    var items=new[]{new ItemSpec{id="part",name="Part",weightKg=1},new ItemSpec{id="heavy",name="Heavy Module",weightKg=50}};
    var pack=new ShopModel(items);
    Assert.That(pack.TryApply(new[]{Delta("part",1)},0,out _));
    charCat.derivedStats=new[]{new CharacterDerivedStat{id="carryCapacity",initial=10},new CharacterDerivedStat{id="storageCapacity",initial=10}};
    var character=new CharacterModel(charCat,pack);
    pack.CapacityFailure=character.CapacityFailure;
    data.weapons=new[]{new CraftWeapon{id="weapon_scrap_pistol",name="Scrap Pistol"}};
    data.modifiers=Array.Empty<CraftModifier>();
    data.recipes=new[]{new CraftRecipe{id="r_heavy",name="Heavy Module",knownByDefault=true,outputItemId="heavy",craftSeconds=5,inputs=new[]{new CraftIngredient{kind="item",id="part",quantity=1}}}};
    var model=new CraftingModel(data,items,pack,()=>true,character:character);
    Assert.That(model.CanCraft("r_heavy",null,out var reason),Is.False);
    Assert.That(reason,Does.Contain("capacity"));
    Assert.That(model.BeginCraft("r_heavy",null,0,out reason),Is.False);
    Assert.That(model.Job,Is.Null,"timed job must not start when output cannot fit");
   }
   finally{UnityEngine.Object.DestroyImmediate(data);UnityEngine.Object.DestroyImmediate(charCat);}
  }

  [Test] public void ActiveRepairJobBlocksCraftAndOverhaulAndRestoreClearsLastAward()
  {
   var pack=new ShopModel(City().items);
   var character=new CharacterModel(Chars(),pack);
   var model=new CraftingModel(Data(),City().items,pack,()=>true,character:character);
   model.Identify("npc_ossa:servo_look");
   Assert.That(pack.TryApply(new[]{Delta("droid_servo_damaged",1),Delta("scrap_alloy",2),Delta("nanite_residue",5)},0,out _));
   Assert.That(model.TryCraft("recipe_grip_stabilised_pistol",Station,out var reason),reason);
   Assert.That(model.LastAward,Is.Not.Null);
   model.Restore(null);
   Assert.That(model.LastAward,Is.Null,"restore clears stale craft award");

   // Start a repair job and verify BeginCraft and CanOverhaul report busy.
   model.Loadout.Wear(40);
   Assert.That(model.BeginRepair(model.Loadout.WeaponId,1f,out reason),reason);
   Assert.That(model.RepairJob,Is.Not.Null);
   Assert.That(model.BeginCraft("recipe_wound_coil",Station,1f,out reason),Is.False);
   Assert.That(reason,Is.EqualTo("busy"));
   Assert.That(model.CanOverhaul(model.Loadout.WeaponId,Station,out reason),Is.False);
   Assert.That(reason,Is.EqualTo("busy"));
  }

  [Test] public void CraftingTextNamesMissingPrerequisiteWeaponAndModTools()
  {
   var pack=new ShopModel(City().items);
   var model=new CraftingModel(Data(),City().items,pack,()=>false);
   var rifleMod=Data().recipes.First(r=>r.requiresWeaponId=="weapon_field_rifle");
   Assert.That(CraftingText.Reason("missing_weapon",model,rifleMod),Does.Contain("Field Rifle"));
   var synthetic=new CraftRecipe{id="r_dep",requiredSchematics=new[]{"recipe_grip_stabilised_pistol"}};
   Assert.That(CraftingText.Reason("missing_schematic",model,synthetic),Does.Contain("Stabilised Pistol Grip"));
  }

  [Test] public void IngredientAllocatorGuardsNullsAndShortCircuitsImpossibleNeeds()
  {
   Assert.That(IngredientAllocator.TryAllocate(null,Array.Empty<ItemSpec>(),_=>0,out _),Is.False);
   Assert.That(IngredientAllocator.TryAllocate(new[]{new CraftIngredient{kind="item",id="x",quantity=1}},null,_=>1,out _),Is.False);
   var items=new[]{new ItemSpec{id="a",tags=new[]{"t"}},new ItemSpec{id="b",tags=new[]{"t"}},new ItemSpec{id="c",tags=new[]{"t"}}};
   // 3 items × 1 each = 3 available, asking for 100 should short-circuit immediately without hanging
   Assert.That(IngredientAllocator.TryAllocate(new[]{new CraftIngredient{kind="tag",id="t",quantity=100}},items,_=>1,out _),Is.False);
  }

  [Test] public void FieldOrderProgressDetectsFittedModOnNonDefaultWeapon()
  {
   var data=ScriptableObject.CreateInstance<CraftingCatalog>();
   var orders=ScriptableObject.CreateInstance<FieldOrderSet>();
   try
   {
    var items=new[]{new ItemSpec{id="rifle",name="Rifle"},new ItemSpec{id="scope",name="Scope"}};
    var pack=new ShopModel(items);
    Assert.That(pack.TryApply(new[]{Delta("rifle",1),Delta("scope",1)},0,out _));
    data.weapons=new[]{
     new CraftWeapon{id="weapon_scrap_pistol",name="Pistol",slots=new[]{"grip"}},
     new CraftWeapon{id="weapon_field_rifle",name="Rifle",itemId="rifle",slots=new[]{"optic"}}
    };
    data.modifiers=new[]{new CraftModifier{id="m_scope",itemId="scope",slot="optic",weaponIds=new[]{"weapon_field_rifle"}}};
    data.recipes=Array.Empty<CraftRecipe>();
    var model=new CraftingModel(data,items,pack,()=>true);
    orders.orders=new[]{new FieldOrder{id="ord_scope",title="Scope",goal=FieldOrderGoal.FitMod,targetItemId="scope"}};
    var progress=new FieldOrderProgress(orders);progress.Begin();
    Assert.That(progress.Advance(model,_=>false),Is.Empty);
    Assert.That(model.TryFit("weapon_field_rifle","scope",out var reason),reason);
    Assert.That(progress.Advance(model,_=>false).Select(o=>o.id),Is.EqualTo(new[]{"ord_scope"}));
   }
   finally{UnityEngine.Object.DestroyImmediate(data);UnityEngine.Object.DestroyImmediate(orders);}
  }
 }
}
