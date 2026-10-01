using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// Gameplay v2 M1: weapon stat math, slots, swaps and the PlayerCombat binding.
 public class WeaponLoadoutTests
 {
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static KeyValuePair<string,int> Delta(string id,int n)=>new KeyValuePair<string,int>(id,n);
  static (ShopModel pack,CraftingModel model) Model(bool pistol=true){var pack=new ShopModel(City().items);return (pack,new CraftingModel(Data(),City().items,pack,()=>pistol));}
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>Delta(x.id,x.n)),0,out var r),Is.True,r);

  [Test] public void BaseStatsMatchThePreviousPlayerCombatTuning()
  {
   var go=new GameObject("combat defaults");
   try
   {
    var combat=go.AddComponent<PlayerCombat>();
    var b=Data().weapons.Single(w=>w.id=="weapon_scrap_pistol").stats;
    Assert.That(new[]{b.damage,b.fireInterval,b.range,b.recoil,b.nanoMax,b.nanoPerShot,b.nanoRegen,b.aimAssist},
     Is.EqualTo(new[]{combat.damage,combat.fireInterval,combat.range,combat.recoil,combat.nanoMax,combat.nanoPerShot,combat.nanoRegen,combat.aimAssistDegrees}));
    Assert.That(new[]{b.damage,b.fireInterval,b.range,b.recoil,b.nanoMax,b.nanoPerShot,b.nanoRegen,b.aimAssist},Is.EqualTo(new[]{34,.28f,70,38,100,9,30,3.5f}));
    Assert.That(Data().weapons.Single(w=>w.id=="weapon_scrap_pistol").slots,Is.EqualTo(new[]{"grip","barrel","cell"}));
   }
   finally{Object.DestroyImmediate(go);}
  }

  [Test] public void EveryModAppliesItsAddAndPercentTermsExactly()
  {
   var w=Data().weapons.Single(w=>w.id=="weapon_scrap_pistol");
   WeaponStats With(string item)=>WeaponLoadout.Compute(w,new[]{Data().modifiers.Single(m=>m.itemId==item)});
   Assert.That(With("grip_stabilised_pistol").recoil,Is.EqualTo(31));
   var bored=With("barrel_bored_alloy");Assert.That(bored.damage,Is.EqualTo(40.8f).Within(1e-4));Assert.That(bored.range,Is.EqualTo(80));
   var cell=With("cell_salvaged_capacitor");Assert.That(cell.nanoMax,Is.EqualTo(135));Assert.That(cell.nanoRegen,Is.EqualTo(34.5f).Within(1e-4));
   var gyro=With("grip_gyro_braced");Assert.That(gyro.recoil,Is.EqualTo(23));Assert.That(gyro.aimAssist,Is.EqualTo(4.5f));
   var lattice=With("barrel_lattice_focused");Assert.That(lattice.damage,Is.EqualTo(49.3f).Within(1e-4));Assert.That(lattice.range,Is.EqualTo(95));Assert.That(lattice.fireInterval,Is.EqualTo(.302f).Within(1e-4));
   var over=With("cell_overclocked");Assert.That(over.nanoMax,Is.EqualTo(160));Assert.That(over.nanoPerShot,Is.EqualTo(7));Assert.That(over.nanoRegen,Is.EqualTo(39));
   // Untouched stats stay at base.
   Assert.That(bored.recoil,Is.EqualTo(38));Assert.That(gyro.damage,Is.EqualTo(34));
  }

  [Test] public void FlatTermsApplyBeforePercentAndResultsClampToWeaponBounds()
  {
   var weapon=new CraftWeapon{id="w",name="W",stats=new WeaponStats{damage=10,fireInterval=.5f,range=50,recoil=20,nanoMax=50,nanoPerShot=5,nanoRegen=10,aimAssist=1},minStats=WeaponStats.DefaultMin,maxStats=WeaponStats.DefaultMax,slots=new[]{"a","b"}};
   var a=new CraftModifier{itemId="a1",slot="a",weaponIds=new[]{"w"},effects=new[]{new CraftEffect{stat="damage",op="add",value=10},new CraftEffect{stat="damage",op="percent",value=50},new CraftEffect{stat="recoil",op="add",value=-80}}};
   var b=new CraftModifier{itemId="b1",slot="b",weaponIds=new[]{"w"},effects=new[]{new CraftEffect{stat="damage",op="percent",value=50},new CraftEffect{stat="aimAssist",op="add",value=100},new CraftEffect{stat="unknown",op="add",value=5},new CraftEffect{stat="range",op="multiply",value=5}}};
   var s=WeaponLoadout.Compute(weapon,new[]{a,b});
   Assert.That(s.damage,Is.EqualTo(40));                       // (10+10)×(1+100%)
   Assert.That(s.recoil,Is.EqualTo(WeaponStats.DefaultMin.recoil));   // clamped at the floor
   Assert.That(s.aimAssist,Is.EqualTo(WeaponStats.DefaultMax.aimAssist)); // clamped at the ceiling
   Assert.That(s.range,Is.EqualTo(50));                        // unknown ops and stats are ignored
  }

  [Test] public void SwappingAModReturnsTheOldOneInTheSameTransaction()
  {
   var (pack,model)=Model();
   Give(pack,("grip_stabilised_pistol",1),("grip_gyro_braced",1));
   int changed=0;model.Loadout.Changed+=()=>changed++;
   Assert.That(model.TryFit("grip_stabilised_pistol",out var r),r);
   Assert.That(model.RecoilStat,Is.EqualTo(31));Assert.That(changed,Is.EqualTo(1));
   Assert.That(model.TryFit("grip_gyro_braced",out r),r);
   Assert.That(model.Loadout.Fitted("grip"),Is.EqualTo("grip_gyro_braced"));
   Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));Assert.That(pack.Quantity("grip_gyro_braced"),Is.Zero);
   Assert.That(model.RecoilStat,Is.EqualTo(23));Assert.That(model.Loadout.Stats.aimAssist,Is.EqualTo(4.5f));
   Assert.That(model.TryFit("grip_gyro_braced",out r),Is.False);Assert.That(r,Is.EqualTo("not_carried").Or.EqualTo("already_fitted"));
  }

  [Test] public void FittedModKeepsItsMassAndCanReturnToAFullWeightPack()
  {
   var characterData=ScriptableObject.CreateInstance<CharacterCatalog>();
   try
   {
    characterData.derivedStats=new[]{new CharacterDerivedStat{id="carryCapacity",initial=5},new CharacterDerivedStat{id="storageCapacity",initial=5}};
    var items=new[]{new ItemSpec{id="scrap_pistol",startingQuantity=1,weightKg=2},new ItemSpec{id="grip_stabilised_pistol",startingQuantity=1,weightKg=1},new ItemSpec{id="ballast",startingQuantity=2,weightKg=1}};
    var pack=new ShopModel(items);var character=new CharacterModel(characterData,pack);pack.CapacityFailure=character.CapacityFailure;
    var model=new CraftingModel(Data(),items,pack,()=>true,character:character);
    Assert.That(character.CarryWeight,Is.EqualTo(5));
    Assert.That(model.TryFit("grip_stabilised_pistol",out var reason),reason);
    Assert.That(pack.PackWeightKg,Is.EqualTo(4));Assert.That(model.FittedWeightKg,Is.EqualTo(1));
    Assert.That(character.CarryWeight,Is.EqualTo(5));
    Assert.That(pack.Grant("ballast",1,0,out var rejected),Is.False);
    Assert.That(rejected,Does.Contain("carrying capacity"));
    Assert.That(model.TryRemove("grip",out reason),reason);
    Assert.That(pack.PackWeightKg,Is.EqualTo(5));Assert.That(model.FittedWeightKg,Is.Zero);
    Assert.That(character.CarryWeight,Is.EqualTo(5));
   }
   finally{Object.DestroyImmediate(characterData);}
  }

  [Test] public void SwapIsRefusedWhenThePackCannotTakeTheOldModBack()
  {
   var (pack,model)=Model();
   Give(pack,("barrel_bored_alloy",1));Assert.That(model.TryFit("barrel_bored_alloy",out _));
   int cap=City().items.Single(x=>x.id=="barrel_bored_alloy").maxStack;
   Give(pack,("barrel_bored_alloy",cap),("barrel_lattice_focused",1));
   var before=model.Loadout.Stats;
   Assert.That(model.TryFit("barrel_lattice_focused",out var reason),Is.False);Assert.That(reason,Is.EqualTo("stack_full"));
   Assert.That(model.Loadout.Fitted("barrel"),Is.EqualTo("barrel_bored_alloy"));Assert.That(pack.Quantity("barrel_lattice_focused"),Is.EqualTo(1));
   Assert.That(model.Loadout.Stats.Approximately(before));
   Assert.That(model.TryRemove("barrel",out reason),Is.False);Assert.That(reason,Is.EqualTo("stack_full"));
  }

  [Test] public void SlotsAreIndependentAndComponentsOrForeignItemsNeverFit()
  {
   var (pack,model)=Model();
   Give(pack,("grip_stabilised_pistol",1),("barrel_bored_alloy",1),("cell_salvaged_capacitor",1),("alloy_plate",1));
   Assert.That(model.TryFit("grip_stabilised_pistol",out _));Assert.That(model.TryFit("barrel_bored_alloy",out _));Assert.That(model.TryFit("cell_salvaged_capacitor",out _));
   var s=model.Loadout.Stats;
   Assert.That(s.recoil,Is.EqualTo(31));Assert.That(s.damage,Is.EqualTo(40.8f).Within(1e-4));Assert.That(s.nanoMax,Is.EqualTo(135));
   Assert.That(model.TryFit("alloy_plate",out var r),Is.False);Assert.That(r,Is.EqualTo("not_a_mod"));
   Assert.That(model.TryFit("water_flask",out r),Is.False);Assert.That(r,Is.EqualTo("not_a_mod"));
   Assert.That(model.TryRemove("stock",out r),Is.False);Assert.That(r,Is.EqualTo("wrong_slot"));
   Assert.That(model.TryRemove("cell",out r),r);Assert.That(model.Loadout.Stats.nanoMax,Is.EqualTo(100));Assert.That(model.Loadout.Fitted("grip"),Is.Not.Null);
   Assert.That(model.TryRemove("cell",out r),Is.False);Assert.That(r,Is.EqualTo("empty_slot"));
   var (_,unarmed)=Model(false);Assert.That(unarmed.TryFit("grip_stabilised_pistol",out r),Is.False);Assert.That(r,Is.EqualTo("missing_weapon"));
  }

  [Test] public void PreviewShowsASwapWithoutChangingTheLoadout()
  {
   var (pack,model)=Model();
   Give(pack,("barrel_bored_alloy",1));Assert.That(model.TryFit("barrel_bored_alloy",out _));
   var preview=model.Loadout.Preview("barrel","barrel_lattice_focused");
   Assert.That(preview.damage,Is.EqualTo(49.3f).Within(1e-4));
   Assert.That(model.Loadout.Preview("barrel",null).damage,Is.EqualTo(34));
   Assert.That(model.Loadout.Stats.damage,Is.EqualTo(40.8f).Within(1e-4));
  }

  [Test] public void PlayerCombatReadsEveryEffectiveStatFromTheBoundLoadout()
  {
   var go=new GameObject("combat binding");
   try
   {
    var combat=go.AddComponent<PlayerCombat>();
    var (pack,model)=Model();
    int changed=0;combat.StatsChanged+=()=>changed++;
    combat.BindLoadout(model.Loadout);
    Assert.That(changed,Is.EqualTo(1));Assert.That(combat.Stats.Approximately(model.Loadout.Base));Assert.That(combat.RecoilScale,Is.EqualTo(1));
    combat.RestorePistol(true);Assert.That(combat.Nano,Is.EqualTo(100));
    Give(pack,("grip_gyro_braced",1),("cell_overclocked",1),("barrel_lattice_focused",1));
    Assert.That(model.TryFit("grip_gyro_braced",out _));Assert.That(model.TryFit("cell_overclocked",out _));Assert.That(model.TryFit("barrel_lattice_focused",out _));
    Assert.That(changed,Is.EqualTo(4));
    Assert.That(combat.Stats.Approximately(model.Loadout.Stats));
    Assert.That(combat.RecoilStat,Is.EqualTo(23));Assert.That(combat.RecoilScale,Is.EqualTo(23f/38f).Within(1e-5));
    Assert.That(combat.Stats.nanoPerShot,Is.EqualTo(7));Assert.That(combat.Stats.nanoMax,Is.EqualTo(160));
    combat.RestorePistol(true);Assert.That(combat.Nano,Is.EqualTo(160));
    // Removing the cell lowers capacity; stored charge never exceeds it.
    Assert.That(model.TryRemove("cell",out _));Assert.That(combat.Nano,Is.EqualTo(100));
    combat.BindLoadout(null);Assert.That(combat.Stats.damage,Is.EqualTo(combat.damage));
    Assert.That(model.TryRemove("grip",out _));Assert.That(combat.RecoilStat,Is.EqualTo(combat.recoil)); // unbound: no longer follows
   }
   finally{Object.DestroyImmediate(go);}
  }

  [Test] public void StatChangeTextComesFromCatalogLabels()
  {
   var w=Data().weapons.Single(w=>w.id=="weapon_scrap_pistol");
   var after=WeaponLoadout.Compute(w,new[]{Data().modifiers.Single(m=>m.itemId=="grip_stabilised_pistol")});
   Assert.That(CraftingText.StatChanges(Data(),w.stats,after),Is.EqualTo(CraftingText.NoBreak("Recoil 38 → 31")));
   var label=Data().Stat("recoil");
   Assert.That(CraftingText.FormatDelta(label,-7),Is.EqualTo("−7"));Assert.That(CraftingText.Improves(label,-7));
   Assert.That(CraftingText.Improves(Data().Stat("damage"),6.8f));Assert.That(CraftingText.FormatDelta(Data().Stat("damage"),6.8f),Is.EqualTo("+6.8"));
   Assert.That(CraftingText.FormatDelta(Data().Stat("fireInterval"),.022f),Is.EqualTo("+0.02 s"));
   Assert.That(CraftingText.Improves(Data().Stat("fireInterval"),.022f),Is.False);
  }

  [Test] public void RecipeSocketsAndIndependentWeaponModsSurviveSaveRestore()
  {
   var (pack,model)=Model();
   Give(pack,("rifle_precision_barrel",1),("grip_stabilised_pistol",1));
   var rifle=model.GetLoadout("weapon_field_rifle");
   Assert.That(rifle.Slots,Is.EqualTo(Data().recipes.Single(x=>x.id=="recipe_field_rifle").outputSlots));
   Assert.That(model.TryFit(rifle.WeaponId,"grip_stabilised_pistol",out var reason),Is.False);
   Assert.That(reason,Is.EqualTo("wrong_slot"));Assert.That(pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1));
   Assert.That(model.TryFit(rifle.WeaponId,"rifle_precision_barrel",out reason),reason);
   Assert.That(model.TryFit("grip_stabilised_pistol",out reason),reason);
   Assert.That(rifle.Stats.accuracy,Is.EqualTo(90));Assert.That(rifle.Stats.spread,Is.EqualTo(.9f));
   Assert.That(model.Loadout.Stats.recoil,Is.EqualTo(31));
   var saved=model.Capture();
   var other=new CraftingModel(Data(),City().items,pack,()=>true);
   Assert.That(other.Restore(saved),Is.Empty);
   Assert.That(other.GetLoadout(rifle.WeaponId).Fitted("barrel"),Is.EqualTo("rifle_precision_barrel"));
   Assert.That(other.Loadout.Fitted("grip"),Is.EqualTo("grip_stabilised_pistol"));
   Assert.That(other.GetLoadout(rifle.WeaponId).Stats.Approximately(rifle.Stats));
   Assert.That(other.TryRemove(rifle.WeaponId,"barrel",out reason),reason);
   Assert.That(other.Loadout.Fitted("grip"),Is.EqualTo("grip_stabilised_pistol"));
  }

  [Test] public void V1FittedArrayMigratesToPistolWithoutInventingRifleMods()
  {
   var (_,model)=Model();
   var old=new CraftingState{fitted=new[]{new SlotEntry{slot="grip",itemId="grip_stabilised_pistol"}},crafted=new[]{new CountEntry{id="recipe_wound_coil",count=int.MaxValue},new CountEntry{id="recipe_alloy_plate",count=int.MaxValue}}};
   Assert.That(model.Restore(old),Is.Empty);
   Assert.That(model.Loadout.Fitted("grip"),Is.EqualTo("grip_stabilised_pistol"));
   Assert.That(model.GetLoadout("weapon_field_rifle").FittedMods,Is.Empty);
   Assert.That(model.Crafts,Is.EqualTo(int.MaxValue));
  }

  [Test] public void AdditionalStatsApplySupportedEffectsAndRejectForeignPreviews()
  {
   var w=Data().weapons.Single(x=>x.id=="weapon_field_rifle");
   var effects=WeaponStats.Ids.Skip(8).Select(id=>new CraftEffect{stat=id,op="add",value=1}).ToArray();
   var mod=new CraftModifier{itemId="extended",slot="barrel",weaponIds=new[]{w.id},effects=effects};
   var actual=WeaponLoadout.Compute(w,new[]{mod});
   for(int i=8;i<WeaponStats.Count;i++)Assert.That(actual[i],Is.EqualTo(w.stats[i]+1).Within(.001f),WeaponStats.Ids[i]);
   var loadout=new WeaponLoadout(w,Data().modifiers);
   Assert.That(loadout.Preview("barrel","barrel_bored_alloy").Approximately(loadout.Stats),"foreign mod must not advertise invalid stats");
   Assert.That(loadout.Preview("grip","rifle_precision_barrel").Approximately(loadout.Stats),"unknown socket must not advertise invalid stats");
  }

  [Test] public void CharacterWeaponContributionUsesTheSharedRuntimePipeline()
  {
   var catalog=ScriptableObject.CreateInstance<CharacterCatalog>();
   try
   {
    catalog.derivedStats=new[]{new CharacterDerivedStat{id="rangedDamage",initial=1.2f},new CharacterDerivedStat{id="recoilControl",initial=.25f},new CharacterDerivedStat{id="accuracy",initial=5},new CharacterDerivedStat{id="criticalChance",initial=.1f}};
    var (pack,model)=Model();var character=new CharacterModel(catalog,pack);
    var rifle=model.GetLoadout("weapon_field_rifle");var result=rifle.WithCharacter(character);
    Assert.That(result.damage,Is.EqualTo(32.4f).Within(.001f));Assert.That(result.recoil,Is.EqualTo(33));
    Assert.That(result.accuracy,Is.EqualTo(87));Assert.That(result.criticalChance,Is.EqualTo(15));
    Assert.That(rifle.Stats.damage,Is.EqualTo(27),"inspection does not mutate the mod-only baseline");
   }
   finally{Object.DestroyImmediate(catalog);}
  }
 }
}
