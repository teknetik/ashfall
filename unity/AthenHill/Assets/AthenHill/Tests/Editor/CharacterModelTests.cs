using System;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
 public class CharacterModelTests
 {
  CharacterCatalog data;
  ShopModel pack;
  CharacterModel model;
  [SetUp]public void Setup()
  {
   data=ScriptableObject.CreateInstance<CharacterCatalog>();
   data.attributes=new[]{new CharacterAttribute{id="strength",label="Strength",initial=10},new CharacterAttribute{id="intellect",label="Intellect",initial=10},new CharacterAttribute{id="perception",label="Perception",initial=10}};
   data.skills=new[]{new CharacterSkill{id="rifle",label="Rifle",dependencies=new[]{new CharacterDependency{stat="perception",factor=.5f},new CharacterDependency{stat="intellect",factor=.5f}}}};
   data.derivedStats=new[]{
    new CharacterDerivedStat{id="carryCapacity",initial=20,dependencies=new[]{new CharacterDependency{stat="strength",factor=2}}},
    new CharacterDerivedStat{id="storageCapacity",initial=5},
    new CharacterDerivedStat{id="health",initial=50,perLevel=2},
    new CharacterDerivedStat{id="movementSpeed",initial=1},
    new CharacterDerivedStat{id="stamina",initial=100}};
   data.slots=new[]{new CharacterSlot{id="implant_head"},new CharacterSlot{id="armour_chest"},new CharacterSlot{id="storage"},new CharacterSlot{id="primary"},new CharacterSlot{id="secondary"}};
   data.equipment=new[]{
    new CharacterEquipment{itemId="implant1",slots=new[]{"implant_head"},modifiers=new[]{new CharacterModifier{stat="perception",flat=2},new CharacterModifier{stat="rifle",flat=8}},upgradeToItemId="implant2",upgradeCredits=5,upgradeIngredients=new[]{new CountEntry{id="scrap",count=2}}},
    new CharacterEquipment{itemId="implant2",slots=new[]{"implant_head"},tier=ImplantTier.Industrial,upgradeLevel=1,modifiers=new[]{new CharacterModifier{stat="perception",flat=4}}},
    new CharacterEquipment{itemId="vest",slots=new[]{"armour_chest"},requirements=new[]{new CharacterRequirement{stat="strength",minimum=12}},modifiers=new[]{new CharacterModifier{stat="strength",flat=5}}},
    new CharacterEquipment{itemId="backpack",slots=new[]{"storage"},modifiers=new[]{new CharacterModifier{stat="storageCapacity",flat=25}}},
    new CharacterEquipment{itemId="weapon",slots=new[]{"primary","secondary"}}
   };
   pack=new ShopModel(new[]{
    new ItemSpec{id="implant1",startingQuantity=1,maxStack=1,weightKg=.1f},
    new ItemSpec{id="implant2",maxStack=5,weightKg=.1f},
    new ItemSpec{id="vest",startingQuantity=1,weightKg=1},
    new ItemSpec{id="backpack",startingQuantity=1,weightKg=1},
    new ItemSpec{id="weapon",startingQuantity=1,weightKg=1},
    new ItemSpec{id="scrap",startingQuantity=2,weightKg=.1f},
    new ItemSpec{id="ore",weightKg=10}
   },25);
   model=new CharacterModel(data,pack);
   pack.CapacityFailure=model.CapacityFailure;
  }
  [TearDown]public void Teardown(){UnityEngine.Object.DestroyImmediate(data);}
  [Test]public void ImplantAttributesTrickleBeforeDirectSkillModifiers()
  {
   Assert.That(model.Skill("rifle"),Is.EqualTo(10));
   Assert.That(model.TryEquip("implant1","implant_head",out _));
   Assert.That(model.Attribute("perception"),Is.EqualTo(12));
   Assert.That(model.Skill("rifle"),Is.EqualTo(19));
   var parts=model.Breakdown("rifle");Assert.That(parts.dependencies,Is.EqualTo(11));Assert.That(parts.flat,Is.EqualTo(8));
   parts.finalValue=99;Assert.That(model.Skill("rifle"),Is.EqualTo(19));
  }
  [Test]public void FlatAndPercentEffectsAggregateWithoutOrderDependentCompounding()
  {
   model.SetEffects("weather",new[]{new CharacterModifier{stat="strength",flat=2,percent=.1f}});
   model.SetEffects("buff",new[]{new CharacterModifier{stat="strength",flat=3,percent=.2f}});
   Assert.That(model.Attribute("strength"),Is.EqualTo(19.5f).Within(.0001f));
   Assert.That(model.CarryCapacity,Is.EqualTo(59).Within(.0001f));
   model.SetEffects("weather",null);Assert.That(model.Attribute("strength"),Is.EqualTo(15.6f).Within(.0001f));
  }
  [Test]public void EquipmentCannotSupplyItsOwnInstallationRequirement()
  {
   Assert.That(model.TryEquip("vest","armour_chest",out var reason),Is.False);
   Assert.That(reason,Does.Contain("Strength 12"));Assert.That(pack.Quantity("vest"),Is.EqualTo(1));
   Assert.That(model.Equipped("armour_chest"),Is.Null);
  }
  [Test]public void ExpiredInstallationBuffDoesNotStripEquipment()
  {
   model.SetEffects("buff",new[]{new CharacterModifier{stat="strength",flat=2}});
   Assert.That(model.TryEquip("vest","armour_chest",out _));model.SetEffects("buff",null);
   Assert.That(model.Equipped("armour_chest"),Is.EqualTo("vest"));Assert.That(model.Attribute("strength"),Is.EqualTo(15));
  }
  [Test]public void FailedSwapDoesNotConsumeIncomingItemOrChangeStats()
  {
   Assert.That(model.TryEquip("implant1","implant_head",out _));
   Assert.That(pack.Grant("implant1",1,0,out _));Assert.That(pack.Grant("implant2",1,0,out _));
   Assert.That(model.TryEquip("implant2","implant_head",out var reason),Is.False);
   Assert.That(reason,Is.EqualTo("stack_full"));Assert.That(pack.Quantity("implant2"),Is.EqualTo(1));
   Assert.That(model.Equipped("implant_head"),Is.EqualTo("implant1"));Assert.That(model.Skill("rifle"),Is.EqualTo(19));
  }
  [Test]public void UpgradingConsumesCostOnceAndPreservesTierThroughRemovalAndRestore()
  {
   Assert.That(model.TryEquip("implant1","implant_head",out _));Assert.That(model.TryUpgradeImplant("implant_head",out _));
   Assert.That(pack.Credits,Is.EqualTo(20));Assert.That(pack.Quantity("scrap"),Is.Zero);
   Assert.That(model.TryUnequip("implant_head",out _));Assert.That(pack.Quantity("implant2"),Is.EqualTo(1));
   Assert.That(model.TryEquip("implant2","implant_head",out _));var state=model.Capture();
   model.Restore(state);Assert.That(model.Equipment(model.Equipped("implant_head")).upgradeLevel,Is.EqualTo(1));
   Assert.That(model.Attribute("perception"),Is.EqualTo(14));Assert.That(pack.Quantity("implant1"),Is.Zero);
  }
  [Test]public void MissingUpgradeIngredientsPreserveImplantAndCredits()
  {
   Assert.That(model.TryEquip("implant1","implant_head",out _));Assert.That(pack.TryApply(new[]{new KeyValuePair<string,int>("scrap",-1)},0,out _));
   Assert.That(model.TryUpgradeImplant("implant_head",out _),Is.False);
   Assert.That(model.Equipped("implant_head"),Is.EqualTo("implant1"));Assert.That(pack.Credits,Is.EqualTo(25));Assert.That(pack.Quantity("scrap"),Is.EqualTo(1));
  }
  [Test]public void MovingEquippedWeaponDoesNotTouchInventory()
  {
   Assert.That(model.TryEquip("weapon","secondary",out _));Assert.That(model.TryMove("secondary","primary",out _));
   Assert.That(pack.Quantity("weapon"),Is.Zero);Assert.That(model.Equipped("secondary"),Is.Null);Assert.That(model.Equipped("primary"),Is.EqualTo("weapon"));
  }
  [Test]public void RewardCanInstallIntoFreeSlotWhenAlreadyOverburdened()
  {
   model.SetEffects("fatigue",new[]{new CharacterModifier{stat="carryCapacity",flat=-40}});
   Assert.That(model.Overburdened,Is.True);
   Assert.That(model.TryGrantEquipped("implant2","implant_head",out var reason),Is.True,reason);
   Assert.That(model.Equipped("implant_head"),Is.EqualTo("implant2"));
   Assert.That(pack.Quantity("implant2"),Is.Zero);
   Assert.That(model.Overburdened,Is.True);
  }
  [Test]public void BackpackCapacityIsCheckedAgainstProspectiveEquipment()
  {
   Assert.That(pack.Grant("ore",1,0,out _),Is.False);
   Assert.That(model.TryEquip("backpack","storage",out _));Assert.That(pack.Grant("ore",2,0,out _));
   Assert.That(model.TryUnequip("storage",out _),Is.False);Assert.That(model.Equipped("storage"),Is.EqualTo("backpack"));
   Assert.That(pack.Quantity("backpack"),Is.Zero);
  }
  [Test]public void EquippedDeviceWeightCountsAgainstPhysicalCarryLimit()
  {
   Assert.That(model.TryEquip("backpack","storage",out _));
   model.SetEffects("fatigue",new[]{new CharacterModifier{stat="carryCapacity",flat=-17}});
   Assert.That(pack.Grant("ore",2,0,out var reason),Is.False);
   Assert.That(reason,Does.Contain("carrying capacity"));
   Assert.That(pack.Quantity("ore"),Is.Zero);
  }
  [Test]public void TrainingAndLevelRewardsRecalculateAuthoritativeInputs()
  {
   Assert.That(model.TryRaiseAttribute("perception",out _));Assert.That(model.Skill("rifle"),Is.EqualTo(10.5f));
   Assert.That(model.TryRaiseSkill("rifle",out _));Assert.That(model.Skill("rifle"),Is.EqualTo(15.5f));
   Assert.That(model.GrantExperience(250,out _));Assert.That(model.Level,Is.EqualTo(3));Assert.That(model.Experience,Is.EqualTo(50));
   Assert.That(model.Stat("health"),Is.EqualTo(54));Assert.That(model.AttributePoints,Is.EqualTo(7));Assert.That(model.SkillPoints,Is.EqualTo(39));
  }
  [Test]public void OperatingRequirementSuppressesBonusWithoutDestroyingItem()
  {
   data.equipment[0].operatingRequirements=new[]{new CharacterRequirement{stat="strength",minimum=11}};
   Assert.That(model.TryEquip("implant1","implant_head",out _));Assert.That(model.Skill("rifle"),Is.EqualTo(10));
   Assert.That(model.IsOperating("implant_head",out _),Is.False);
   Assert.That(model.TryRaiseAttribute("strength",out _));Assert.That(model.Skill("rifle"),Is.EqualTo(19));
   Assert.That(model.Equipped("implant_head"),Is.EqualTo("implant1"));
  }
  [Test]public void HeavyArmourAppliesConfiguredPenaltyUntilCharacterCanHandleIt()
  {
   data.equipment[2].requirements=Array.Empty<CharacterRequirement>();data.equipment[2].modifiers=Array.Empty<CharacterModifier>();data.equipment[2].comfortableStrength=11;data.equipment[2].movementPenalty=.2f;data.equipment[2].staminaPenalty=.1f;
   Assert.That(model.TryEquip("vest","armour_chest",out _));Assert.That(model.Stat("movementSpeed"),Is.EqualTo(.8f).Within(.001f));
   Assert.That(model.Stat("stamina"),Is.EqualTo(90));Assert.That(model.TryRaiseAttribute("strength",out _));Assert.That(model.Stat("movementSpeed"),Is.EqualTo(1));
  }
  [Test]public void EquippedArmourAndResistanceReduceIncomingPlayerDamage()
  {
   data.armourAbsorptionPerPoint=.2f;
   data.derivedStats=new[]{
    new CharacterDerivedStat{id="armour",initial=0},
    new CharacterDerivedStat{id="physicalResistance",initial=0,maximum=1}};
   data.equipment[2].requirements=Array.Empty<CharacterRequirement>();
   data.equipment[2].modifiers=new[]{new CharacterModifier{stat="armour",flat=12},new CharacterModifier{stat="physicalResistance",flat=.1f}};
   model.Recalculate();
   Assert.That(PlayerCombat.ComputePhysicalDamage(model,20),Is.EqualTo(20));
   Assert.That(model.TryEquip("vest","armour_chest",out _));
   Assert.That(PlayerCombat.ComputePhysicalDamage(model,20),Is.EqualTo(15.6f).Within(.001f));
  }
  [Test]public void RestoreRebuildsStatsAndReportsUnknownContent()
  {
   Assert.That(model.TryEquip("implant1","implant_head",out _));var state=model.Capture();
   state.equipped=new[]{new SlotEntry{slot="implant_head",itemId="implant1"},new SlotEntry{slot="primary",itemId="removed-content"}};
   model.SetEffects("temporary",new[]{new CharacterModifier{stat="perception",flat=99}});
   var skipped=model.Restore(state);Assert.That(skipped,Contains.Item("removed-content"));Assert.That(model.Attribute("perception"),Is.EqualTo(12));
  }
 }
}
