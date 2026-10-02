using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
 public class CharacterModificationTests
 {
  CharacterCatalog data;
  ShopModel pack;
  CharacterModel model;
  [SetUp]public void Setup()
  {
   data=ScriptableObject.CreateInstance<CharacterCatalog>();
   data.attributes=new[]{new CharacterAttribute{id="strength",initial=10},new CharacterAttribute{id="intellect",label="Intellect",initial=10}};
   data.derivedStats=new[]{new CharacterDerivedStat{id="carryCapacity",initial=100},new CharacterDerivedStat{id="storageCapacity",initial=100},new CharacterDerivedStat{id="movementSpeed",initial=1},new CharacterDerivedStat{id="armour"},new CharacterDerivedStat{id="packSlots"}};
   data.slots=new[]{new CharacterSlot{id="implant_head"},new CharacterSlot{id="implant_arms"},new CharacterSlot{id="armour_chest"},new CharacterSlot{id="armour_legs"},new CharacterSlot{id="storage"}};
   data.equipment=new[]{
    new CharacterEquipment{itemId="implant",slots=new[]{"implant_head","implant_arms"},upgradeToItemId="implant2",upgradeIngredients=new[]{new CountEntry{id="scrap",count=1}},upgradeCredits=5},
    new CharacterEquipment{itemId="implant2",slots=new[]{"implant_head","implant_arms"}},
    new CharacterEquipment{itemId="vest",slots=new[]{"armour_chest"},modificationSockets=new[]{new CharacterModificationSocket{id="plate",type="plate"},new CharacterModificationSocket{id="liner",type="lining"}}},
    new CharacterEquipment{itemId="legs",slots=new[]{"armour_legs"},modificationSockets=new[]{new CharacterModificationSocket{id="motor",type="motor"}}},
    new CharacterEquipment{itemId="backpack",slots=new[]{"storage"},modifiers=new[]{new CharacterModifier{stat="packSlots",flat=3}}}
   };
   data.modifications=new[]{
    new CharacterModification{itemId="amp",socketTypes=new[]{"implant"},modifiers=new[]{new CharacterModifier{stat="intellect",flat=2}}},
    new CharacterModification{itemId="buffer",socketTypes=new[]{"implant"},modifiers=new[]{new CharacterModifier{stat="carryCapacity",flat=5}}},
    new CharacterModification{itemId="plate",slots=new[]{"armour_chest"},socketTypes=new[]{"plate"},modifiers=new[]{new CharacterModifier{stat="armour",flat=8}}},
    new CharacterModification{itemId="motor",slots=new[]{"armour_legs"},socketTypes=new[]{"motor"},modifiers=new[]{new CharacterModifier{stat="movementSpeed",percent=.08f}}}
   };
   pack=new ShopModel(new[]{
    new ItemSpec{id="implant",startingQuantity=1,maxStack=1,weightKg=.2f},new ItemSpec{id="implant2",maxStack=1,weightKg=.3f},
    new ItemSpec{id="vest",startingQuantity=1,maxStack=1,weightKg=3},new ItemSpec{id="legs",startingQuantity=1,maxStack=1,weightKg=2},new ItemSpec{id="backpack",startingQuantity=1,maxStack=1,weightKg=1},
    new ItemSpec{id="amp",startingQuantity=1,maxStack=3,weightKg=.1f},new ItemSpec{id="buffer",startingQuantity=1,maxStack=3,weightKg=.2f},
    new ItemSpec{id="plate",startingQuantity=1,maxStack=3,weightKg=.75f},new ItemSpec{id="motor",startingQuantity=1,maxStack=3,weightKg=.9f},new ItemSpec{id="scrap",startingQuantity=1,maxStack=20,weightKg=.1f}
   },25);
   model=new CharacterModel(data,pack);pack.CapacityFailure=model.CapacityFailure;
  }
  [TearDown]public void Teardown(){UnityEngine.Object.DestroyImmediate(data);}
  [Test]public void EveryImplantHasExactlyThreeSocketsAndCannotAcceptAFourth()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.ModificationSockets("implant_head").Count,Is.EqualTo(3));
   Assert.That(pack.Grant("amp",2,0,out _));
   for(int i=0;i<3;i++)Assert.That(model.TryInstallModification("implant_head",i,"amp",out _));
   Assert.That(model.TryInstallModification("implant_head",3,"buffer",out _),Is.False);
   Assert.That(model.Attribute("intellect"),Is.EqualTo(16));Assert.That(pack.Quantity("buffer"),Is.EqualTo(1));
  }
  [Test]public void ComponentInstallationTransfersMassRatherThanDestroyingIt()
  {
   var initial=model.CarryWeight;
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out _));
   Assert.That(model.CarryWeight,Is.EqualTo(initial).Within(.0001f));Assert.That(pack.Quantity("amp"),Is.Zero);
   Assert.That(model.TryRemoveModification("implant_head",0,out _));Assert.That(model.CarryWeight,Is.EqualTo(initial).Within(.0001f));Assert.That(model.Attribute("intellect"),Is.EqualTo(10));
  }
  [Test]public void WrongArmourSocketAndWrongBodyRegionLeaveInventoryUntouched()
  {
   Assert.That(model.TryEquip("vest","armour_chest",out _));Assert.That(model.TryEquip("legs","armour_legs",out _));
   Assert.That(model.TryInstallModification("armour_chest",1,"plate",out _),Is.False);
   Assert.That(model.TryInstallModification("armour_chest",0,"motor",out _),Is.False);
   Assert.That(pack.Quantity("plate"),Is.EqualTo(1));Assert.That(pack.Quantity("motor"),Is.EqualTo(1));
  }
  [Test]public void ExtraPlateAndLegMotorChangeAuthoritativeArmourAndMovement()
  {
   Assert.That(model.TryEquip("vest","armour_chest",out _));Assert.That(model.TryEquip("legs","armour_legs",out _));
   Assert.That(model.TryInstallModification("armour_chest",0,"plate",out _));Assert.That(model.TryInstallModification("armour_legs",0,"motor",out _));
   Assert.That(model.Stat("armour"),Is.EqualTo(8));Assert.That(model.Stat("movementSpeed"),Is.EqualTo(1.08f).Within(.0001f));
   Assert.That(model.TryRemoveModification("armour_legs",0,out _));Assert.That(model.Stat("movementSpeed"),Is.EqualTo(1));
  }
  [Test]public void FailedComponentSwapDoesNotConsumeOrNotify()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out _));
   Assert.That(pack.Grant("amp",3,0,out _));int changed=0;model.Changed+=()=>changed++;
   Assert.That(model.TryInstallModification("implant_head",0,"buffer",out var reason),Is.False);Assert.That(reason,Is.EqualTo("stack_full"));
   Assert.That(model.InstalledModification("implant_head",0),Is.EqualTo("amp"));Assert.That(pack.Quantity("buffer"),Is.EqualTo(1));Assert.That(model.Attribute("intellect"),Is.EqualTo(12));Assert.That(changed,Is.Zero);
  }
  [Test]public void ParentRemovalReturnsItsModulesAndNotifiesOnlyAfterAtomicCommit()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out _));
   int changes=0;model.Changed+=()=>{changes++;Assert.That(pack.Quantity("implant"),Is.EqualTo(1));Assert.That(pack.Quantity("amp"),Is.EqualTo(1));Assert.That(model.Equipped("implant_head"),Is.Null);Assert.That(model.InstalledModification("implant_head",0),Is.Null);};
   Assert.That(model.TryUnequip("implant_head",out _));Assert.That(changes,Is.EqualTo(1));Assert.That(model.Attribute("intellect"),Is.EqualTo(10));
  }
  [Test]public void ParentRemovalRollsBackIfOneReturningModuleWouldOverflow()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out _));Assert.That(pack.Grant("amp",3,0,out _));
   Assert.That(model.TryUnequip("implant_head",out _),Is.False);Assert.That(model.Equipped("implant_head"),Is.EqualTo("implant"));Assert.That(pack.Quantity("implant"),Is.Zero);Assert.That(model.InstalledModification("implant_head",0),Is.EqualTo("amp"));
  }
  [Test]public void ParentReplacementReturnsModulesWithoutTransferringThemToDifferentHardware()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out _));Assert.That(pack.Grant("implant2",1,0,out _));
   Assert.That(model.TryEquip("implant2","implant_head",out _));Assert.That(pack.Quantity("amp"),Is.EqualTo(1));Assert.That(model.InstalledModification("implant_head",0),Is.Null);
  }
  [Test]public void MovingParentPreservesItsCompatibleModules()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",2,"amp",out _));
   Assert.That(model.TryMove("implant_head","implant_arms",out _));Assert.That(model.InstalledModification("implant_head",2),Is.Null);Assert.That(model.InstalledModification("implant_arms",2),Is.EqualTo("amp"));Assert.That(pack.Quantity("amp"),Is.Zero);Assert.That(model.Attribute("intellect"),Is.EqualTo(12));
  }
  [Test]public void UpgradeAndJsonSaveRoundTripPreserveThreeAugmentationPositions()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",2,"amp",out _));Assert.That(model.TryUpgradeImplant("implant_head",out _));
   var state=JsonUtility.FromJson<CharacterState>(JsonUtility.ToJson(model.Capture()));Assert.That(state.version,Is.EqualTo(2));Assert.That(model.Restore(state),Is.Empty);
   Assert.That(model.Equipped("implant_head"),Is.EqualTo("implant2"));Assert.That(model.InstalledModification("implant_head",2),Is.EqualTo("amp"));Assert.That(model.Attribute("intellect"),Is.EqualTo(12));Assert.That(pack.Credits,Is.EqualTo(20));
  }
  [Test]public void LegacySaveHasEmptySocketsWithoutChangingExistingEquipment()
  {
   var state=new CharacterState{version=1,equipped=new[]{new SlotEntry{slot="implant_head",itemId="implant"}},modifications=null};
   Assert.That(model.Restore(state),Is.Empty);Assert.That(model.Equipped("implant_head"),Is.EqualTo("implant"));Assert.That(model.ModificationSockets("implant_head").Count,Is.EqualTo(3));Assert.That(model.InstalledModification("implant_head",0),Is.Null);
  }
  [Test]public void InvalidSavedSocketsAreReportedWithoutApplyingTheirStats()
  {
   var state=new CharacterState{equipped=new[]{new SlotEntry{slot="implant_head",itemId="implant"}},modifications=new[]{new CharacterModificationEntry{slot="implant_head",socketIndex=3,itemId="amp"},new CharacterModificationEntry{slot="armour_chest",socketIndex=0,itemId="plate"}}};
   Assert.That(model.Restore(state),Is.EquivalentTo(new[]{"amp","plate"}));Assert.That(model.Attribute("intellect"),Is.EqualTo(10));Assert.That(model.Stat("armour"),Is.Zero);
  }
  [Test]public void ComponentCannotSupplyItsOwnInstallationRequirement()
  {
   data.modifications[0].requirements=new[]{new CharacterRequirement{stat="intellect",minimum=11}};
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out var reason),Is.False);Assert.That(reason,Does.Contain("Intellect 11"));Assert.That(pack.Quantity("amp"),Is.EqualTo(1));
  }
  [Test]public void SuppressedParentAlsoSuppressesItsAugmentationBonuses()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out _));
   data.equipment[0].operatingRequirements=new[]{new CharacterRequirement{stat="strength",minimum=11}};model.Recalculate();
   Assert.That(model.Attribute("intellect"),Is.EqualTo(10));Assert.That(model.InstalledModification("implant_head",0),Is.EqualTo("amp"));
  }
  [Test]public void PackSlotLimitCountsStacksAndDoesNotSpendCreditsOnFailedTrade()
  {
   data.basePackSlots=model.PackSlotsUsed;int credits=pack.Credits;
   Assert.That(pack.Trade("implant2",true,out var reason),Is.False);Assert.That(reason,Does.Contain("slot capacity"));Assert.That(pack.Credits,Is.EqualTo(credits));Assert.That(pack.Quantity("implant2"),Is.Zero);
   Assert.That(pack.Grant("amp",1,0,out _));Assert.That(model.PackSlotsUsed,Is.EqualTo(model.PackSlotCapacity));
  }
  [Test]public void RemovingLastInstalledComponentNeedsARealFreePackSlot()
  {
   Assert.That(model.TryEquip("implant","implant_head",out _));Assert.That(model.TryInstallModification("implant_head",0,"amp",out _));data.basePackSlots=model.PackSlotsUsed;
   Assert.That(model.TryRemoveModification("implant_head",0,out var reason),Is.False);Assert.That(reason,Does.Contain("slot capacity"));Assert.That(model.InstalledModification("implant_head",0),Is.EqualTo("amp"));Assert.That(pack.Quantity("amp"),Is.Zero);
  }
  [Test]public void RemovingBackpackChecksItsProspectiveSlotCapacity()
  {
   Assert.That(model.TryEquip("backpack","storage",out _));data.basePackSlots=model.PackSlotsUsed;
   Assert.That(model.TryUnequip("storage",out _),Is.False);Assert.That(model.Equipped("storage"),Is.EqualTo("backpack"));
  }
 }
}
