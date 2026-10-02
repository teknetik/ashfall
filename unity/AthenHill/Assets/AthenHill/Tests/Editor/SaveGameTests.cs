using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill.Tests
{
 /// Gameplay v2 M4: versioned JSON save, full round trip through every state machine, corrupt/unknown saves,
 /// Continue / New Game.
 public class SaveGameTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static FieldOrderSet Orders()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  string folder;
  [SetUp] public void MakeFolder(){folder=Path.Combine(Path.GetTempPath(),"ward-save-tests-"+System.Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);}
  [TearDown] public void RemoveFolder(){if(Directory.Exists(folder))Directory.Delete(folder,true);Time.timeScale=1;}

  /// A minimal live session: GameSession (main menu), CraftingSession, PlayerCombat, BermsTutorial, FieldOrders, WardSaveGame.
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public BermsTutorial tutorial;public FieldOrders orders;public WardSaveGame save;public ShopModel pack;public CraftingModel model;
   public Rig(string folder)
   {
    go=new GameObject("save rig");go.SetActive(false);
    var input=go.AddComponent<GameInput>();input.definition=AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/AthenHill/Data/Controls.inputactions");
    var motor=go.AddComponent<PlayerMotor>();
    session=go.AddComponent<GameSession>();session.input=input;session.player=motor;session.catalog=City();session.npcs=new NpcAgent[0];
    crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    var p=new GameObject("combat");p.transform.SetParent(go.transform);combat=p.AddComponent<PlayerCombat>();crafting.combat=combat;
    var t=new GameObject("berms");t.transform.SetParent(go.transform);tutorial=t.AddComponent<BermsTutorial>();tutorial.session=session;tutorial.combat=combat;
    orders=go.AddComponent<FieldOrders>();orders.data=Orders();orders.crafting=crafting;orders.tutorial=tutorial;orders.combat=combat;
    save=go.AddComponent<WardSaveGame>();save.directoryOverride=folder;
    go.SetActive(true);
    typeof(GameInput).GetMethod("OnEnable",Any).Invoke(input,null);
    pack=new ShopModel(City().items,City().startingCredits);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",CityState.MainMenu);
    Set(crafting,"Model",model);Set(crafting,"Session",session);Set(crafting,"Loot",new LootBook(1729));
    combat.BindLoadout(model.Loadout);
   }
   public void Dispose(){Object.DestroyImmediate(go);}
  }

  [Test] public void SerializerRejectsDamagedUnknownAndImpossibleSaves()
  {
   string good=WardSaveFile.Serialize(new WardSaveData{version=1,credits=5,items=new[]{new ItemStack("scrap_alloy",2)},bermsStep="Depot"});
   Assert.That(WardSaveFile.TryParse(good,out var data,out var error),error);Assert.That(data.items.Single().quantity,Is.EqualTo(2));
   foreach(var (text,expect) in new[]{("",'e'),("   ",'e'),("not json at all",'n'),("{\"version\":1,\"credits\":",'d'),("{\"credits\":4}",'v'),("{\"version\":99}",'b'),("{\"version\":1,\"credits\":-5}",'i'),("{\"version\":1,\"bermsStep\":\"Moon\"}",'u'),("[1,2,3]",'n')})
   {
    Assert.That(WardSaveFile.TryParse(text,out data,out error),Is.False,text);
    Assert.That(data,Is.Null,text);Assert.That(error,Is.Not.Empty,text);
    if(expect=='b')Assert.That(error,Does.Contain("newer build"));
   }
   Assert.That(WardSaveFile.TryRead(Path.Combine(folder,"missing.json"),out _,out error),Is.False);Assert.That(error,Is.EqualTo("no save file"));
  }

  [Test] public void CharacterEquipmentAndTrainingRoundTripAndV1UsesDefaults()
  {
   using var rig=new Rig(folder);
   var catalog=ScriptableObject.CreateInstance<CharacterCatalog>();
   try
   {
    catalog.attributes=new[]{new CharacterAttribute{id="strength",initial=10}};
    catalog.skills=new[]{new CharacterSkill{id="engineering",initial=20}};
    catalog.slots=new[]{new CharacterSlot{id="primary"}};
    catalog.equipment=new[]{new CharacterEquipment{itemId="field_rifle",slots=new[]{"primary"}}};
    var character=new CharacterModel(catalog,rig.pack);Set(rig.session,"Character",character);
    Assert.That(rig.pack.TryApply(new[]{new KeyValuePair<string,int>("field_rifle",1)},0,out var give),give);   // 2 Oct 2026: no rifle in the starting pack
    Assert.That(character.TryRaiseAttribute("strength",out var reason),reason);
    Assert.That(character.TryRaiseSkill("engineering",out reason),reason);
    Assert.That(character.TryEquip("field_rifle","primary",out reason),reason);
    var data=rig.save.Capture();
    Assert.That(data.version,Is.EqualTo(WardSaveData.CurrentVersion));
    Assert.That(WardSaveFile.TryParse(WardSaveFile.Serialize(data),out var parsed,out reason),reason);
    character.Restore(null);
    Assert.That(rig.save.Apply(parsed),Is.Empty);
    Assert.That(character.BaseAttribute("strength"),Is.EqualTo(11));Assert.That(character.TrainedSkill("engineering"),Is.EqualTo(25));
    Assert.That(character.Equipped("primary"),Is.EqualTo("field_rifle"));Assert.That(rig.pack.Quantity("field_rifle"),Is.Zero);
    parsed.version=1;parsed.character=null;parsed.crafting.weapons=null;
    rig.save.Apply(parsed);
    Assert.That(character.BaseAttribute("strength"),Is.EqualTo(10));Assert.That(character.TrainedSkill("engineering"),Is.EqualTo(20));
    Assert.That(character.Equipped("primary"),Is.Null);Assert.That(character.AttributePoints,Is.EqualTo(catalog.initialAttributePoints));
   }
   finally{Object.DestroyImmediate(catalog);}
  }

  [Test] public void InventoryModulesRoundTripWithoutChangingBermsProgress()
  {
   using var rig=new Rig(folder);
   var catalog=AssetDatabase.LoadAssetAtPath<CharacterCatalog>("Assets/AthenHill/Resources/CharacterCatalog.asset");
   var character=new CharacterModel(catalog,rig.pack);Set(rig.session,"Character",character);rig.pack.CapacityFailure=character.CapacityFailure;
   Assert.That(character.TryEquip("targeting_implant_mk1","implant_head",out var reason),reason);
   Assert.That(rig.pack.Grant("aug_cognition",1,0,out reason),reason);
   Assert.That(character.TryInstallModification("implant_head",2,"aug_cognition",out reason),reason);
   float mass=character.CarryWeight;var data=rig.save.Capture();
   Assert.That(data.version,Is.EqualTo(3));string berms=data.bermsStep;
   Assert.That(WardSaveFile.TryParse(WardSaveFile.Serialize(data),out var parsed,out reason),reason);
   character.Restore(null);Assert.That(rig.save.Apply(parsed),Is.Empty);
   Assert.That(character.InstalledModification("implant_head",2),Is.EqualTo("aug_cognition"));
   Assert.That(character.Stat("intellect"),Is.EqualTo(11));Assert.That(rig.pack.Quantity("aug_cognition"),Is.Zero);
   Assert.That(character.CarryWeight,Is.EqualTo(mass).Within(.0001f));Assert.That(rig.save.Capture().bermsStep,Is.EqualTo(berms));
  }

  [Test] public void PreviousSaveVersionsRemainReadableAndFutureCharacterVersionIsRejected()
  {
   foreach(int version in new[]{1,2})
   {
    Assert.That(WardSaveFile.TryParse("{\"version\":"+version+",\"credits\":25,\"character\":{\"version\":1,\"level\":2}}",out var data,out var error),error);
    Assert.That(data.credits,Is.EqualTo(25));Assert.That(data.character.modifications,Is.Null);
   }
   var future=new WardSaveData{version=WardSaveData.CurrentVersion,character=new CharacterState{version=CharacterState.CurrentVersion+1}};
   Assert.That(WardSaveFile.TryParse(WardSaveFile.Serialize(future),out var rejected,out var reason),Is.False);
   Assert.That(rejected,Is.Null);Assert.That(reason,Does.Contain("newer build"));
  }

  [Test] public void EarnedRifleAndModifiedPlateCarrierRoundTripTogether()
  {
   using var rig=new Rig(folder);
   var catalog=AssetDatabase.LoadAssetAtPath<CharacterCatalog>("Assets/AthenHill/Resources/CharacterCatalog.asset");
   var character=new CharacterModel(catalog,rig.pack);Set(rig.session,"Character",character);rig.pack.CapacityFailure=character.CapacityFailure;
   int carrierOrder=System.Array.FindIndex(Orders().orders,o=>o.id=="order_plate_carrier");
   Assert.That(carrierOrder,Is.GreaterThan(0));
   rig.orders.Restore(new FieldOrderState{index=carrierOrder,testFired=new[]{"order_steady_hands"},reported=new[]{"order_steady_hands","order_long_arm"}});
   Assert.That(rig.orders.Progress.Completed("order_long_arm"));
   foreach(string item in new[]{"field_rifle","warden_plate_carrier","armour_extra_plate","armour_impact_liner"})
    Assert.That(rig.pack.Grant(item,1,0,out var give),give);
   for(int i=0;i<4;i++)Assert.That(character.TryRaiseSkill("rifle",out var trained),trained);
   Assert.That(character.TryEquip("field_rifle","primary",out var reason),reason);
   Assert.That(character.TryEquip("warden_plate_carrier","armour_chest",out reason),reason);
   var sockets=character.ModificationSockets("armour_chest");
   int plate=System.Array.FindIndex(sockets.ToArray(),s=>s.type=="armour_plate");
   int liner=System.Array.FindIndex(sockets.ToArray(),s=>s.type=="armour_lining");
   Assert.That(plate,Is.GreaterThanOrEqualTo(0),"the quest carrier accepts additional plates");
   Assert.That(liner,Is.GreaterThanOrEqualTo(0),"the quest carrier accepts a liner");
   float armour=character.Stat("armour"),resistance=character.Stat("physicalResistance");
   Assert.That(character.TryInstallModification("armour_chest",plate,"armour_extra_plate",out reason),reason);
   Assert.That(character.TryInstallModification("armour_chest",liner,"armour_impact_liner",out reason),reason);
   float mass=character.CarryWeight;
   var data=rig.save.Capture();
   Assert.That(WardSaveFile.TryParse(WardSaveFile.Serialize(data),out var parsed,out reason),reason);
   character.Restore(null);Assert.That(rig.save.Apply(parsed),Is.Empty);
   Assert.That(character.Equipped("primary"),Is.EqualTo("field_rifle"));
   Assert.That(character.Equipped("armour_chest"),Is.EqualTo("warden_plate_carrier"));
   Assert.That(character.InstalledModification("armour_chest",plate),Is.EqualTo("armour_extra_plate"));
   Assert.That(character.InstalledModification("armour_chest",liner),Is.EqualTo("armour_impact_liner"));
   Assert.That(character.Stat("armour"),Is.EqualTo(armour+8).Within(.0001f));
   Assert.That(character.Stat("physicalResistance"),Is.EqualTo(resistance+.04f).Within(.0001f));
   Assert.That(character.CarryWeight,Is.EqualTo(mass).Within(.0001f));
   Assert.That(rig.pack.Quantity("field_rifle"),Is.Zero);Assert.That(rig.pack.Quantity("armour_extra_plate"),Is.Zero);Assert.That(rig.pack.Quantity("armour_impact_liner"),Is.Zero);
   Assert.That(rig.orders.Progress.Current.id,Is.EqualTo("order_plate_carrier"));
   Assert.That(rig.orders.Progress.Completed("order_long_arm"));Assert.That(rig.orders.Progress.Reported("order_long_arm"));
  }

  [Test] public void FutureSaveVersionCannotMutateLiveInventoryOrEquipment()
  {
   using var rig=new Rig(folder);
   int credits=rig.pack.Credits;int flasks=rig.pack.Quantity("water_flask");
   var data=rig.save.Capture();data.version=WardSaveData.CurrentVersion+1;data.credits=9999;data.items=new[]{new ItemStack("water_flask",99)};
   WardSaveFile.Write(rig.save.SavePath,data);
   Assert.That(rig.save.Continue(),Is.False);Assert.That(rig.pack.Credits,Is.EqualTo(credits));Assert.That(rig.pack.Quantity("water_flask"),Is.EqualTo(flasks));
  }

  [Test] public void FullRoundTripRestoresEveryStateMachine()
  {
   string path;
   using(var a=new Rig(folder))
   {
    a.session.StartGame();
    Assert.That(a.pack.TryApply(new[]{new KeyValuePair<string,int>("scrap_alloy",7),new KeyValuePair<string,int>("barrel_bored_alloy",1),new KeyValuePair<string,int>("grip_stabilised_pistol",1),new KeyValuePair<string,int>("lattice_shard",1)},12,out _));
    a.combat.RestorePistol(true);a.tutorial.Restore(BermsStep.Complete);
    a.model.Acquire("droid_servo_damaged");a.model.OrderStarted("order_keep_charge");
    Assert.That(a.model.TryFit("barrel_bored_alloy",out _));Assert.That(a.model.TryFit("grip_stabilised_pistol",out _));
    Assert.That(a.pack.TryApply(new[]{new KeyValuePair<string,int>("copper_filament",2)},0,out _));Assert.That(a.model.TryCraft("recipe_wound_coil","station_field_fabricator",out _));
    for(int i=0;i<5;i++)a.crafting.Loot.Roll(Data().lootTables.Single(t=>t.id=="loot_feral_scrap_drone"));
    a.crafting.Loot.MarkCollected("foreman_control_core");
    a.orders.Restore(new FieldOrderState{index=2,testFired=new[]{"order_steady_hands"}});
    a.session.visitedHill=true;a.session.boughtFlask=true;
    Assert.That(a.save.SaveNow("test"));path=a.save.SavePath;
    Assert.That(File.Exists(path));Assert.That(File.Exists(path+".tmp"),Is.False);
    var expectedStats=a.model.Loadout.Stats;var expectedLoot=a.crafting.Loot.Capture();
    using(var b=new Rig(folder))
    {
     Assert.That(b.save.HasSave);Assert.That(b.save.Summary(),Does.StartWith("Field order 3/7 · Plate Carrier · 37 cr"));
     Assert.That(b.save.Continue());
     Assert.That(b.session.State,Is.EqualTo(CityState.Play));Assert.That(b.session.notice,Does.Contain("Plate Carrier"));
     Assert.That(b.pack.Credits,Is.EqualTo(37));Assert.That(b.pack.Quantity("scrap_alloy"),Is.EqualTo(7));Assert.That(b.pack.Quantity("lattice_shard"),Is.EqualTo(1));
     Assert.That(b.pack.Quantity("wound_coil"),Is.EqualTo(1));Assert.That(b.pack.Quantity("scrap_coil"),Is.Zero,"the conductor went into the coil");
     Assert.That(b.model.Loadout.Fitted("barrel"),Is.EqualTo("barrel_bored_alloy"));Assert.That(b.model.Loadout.Fitted("grip"),Is.EqualTo("grip_stabilised_pistol"));
     Assert.That(b.model.Loadout.Stats.Approximately(expectedStats));Assert.That(b.combat.Stats.Approximately(expectedStats),"PlayerCombat follows the restored loadout");
     Assert.That(b.model.KnownRecipes,Is.EquivalentTo(a.model.KnownRecipes));Assert.That(b.model.CraftCount("recipe_wound_coil"),Is.EqualTo(1));Assert.That(b.model.Crafts,Is.EqualTo(1));
     Assert.That(b.combat.hasPistol);Assert.That(b.combat.Nano,Is.EqualTo(b.combat.Stats.nanoMax));
     Assert.That(b.tutorial.Step,Is.EqualTo(BermsStep.Complete));
     Assert.That(b.orders.Progress.Index,Is.EqualTo(2));Assert.That(b.orders.Progress.TestFired("order_steady_hands"));
     Assert.That(JsonUtility.ToJson(b.crafting.Loot.Capture()),Is.EqualTo(JsonUtility.ToJson(expectedLoot)),"bad-luck counters and generator state");
     Assert.That(b.session.visitedHill&&b.session.boughtFlask);Assert.That(b.session.soldScrap,Is.False);
     // Continuing never re-grants rewards: orders 1–2 are simply behind us.
     Assert.That(b.pack.Credits,Is.EqualTo(37));
    }
   }
  }

  [Test] public void PistolAndPrimerCannotContradictEachOther()
  {
   using var rig=new Rig(folder);
   var data=rig.save.Capture();data.bermsStep="TakePistol";data.hasPistol=true;
   rig.save.Apply(data);Assert.That(rig.combat.hasPistol,Is.False);Assert.That(rig.tutorial.Step,Is.EqualTo(BermsStep.TakePistol));
   data.bermsStep="Targets";data.hasPistol=false;
   rig.save.Apply(data);Assert.That(rig.combat.hasPistol,Is.True);
  }

  [Test] public void UnknownEntriesAreSkippedAndReported()
  {
   using(var a=new Rig(folder))
   {
    a.session.StartGame();
    var data=a.save.Capture();
    data.items=data.items.Append(new ItemStack("retired_widget",3)).ToArray();
    data.crafting.known=new[]{"recipe_wound_coil","recipe_from_the_future"};
    data.crafting.fitted=new[]{new SlotEntry{slot="grip",itemId="barrel_bored_alloy"}};// wrong slot
    data.crafting.weapons=null; // Exercise the legacy loadout migration with its wrong-slot entry.
    data.version=1;
    File.WriteAllText(a.save.SavePath,WardSaveFile.Serialize(data));
   }
   using var b=new Rig(folder);
   Assert.That(b.save.Continue());
   Assert.That(b.session.notice,Does.Contain("retired_widget").And.Contain("recipe_from_the_future").And.Contain("barrel_bored_alloy"));
   Assert.That(b.model.Knows("recipe_wound_coil"));Assert.That(b.model.Loadout.Fitted("grip"),Is.Null);
  }

  [Test] public void CorruptSaveFallsBackToANewGameAndIsKeptAside()
  {
   File.WriteAllText(Path.Combine(folder,"ward-save.json"),"{\"version\":1,\"credits\":12,\"items\":[{\"itemId\":\"scrap_al");
   using var rig=new Rig(folder);
   Assert.That(rig.save.HasSave);Assert.That(rig.save.Summary(),Does.Contain("cannot be read"));
   Assert.DoesNotThrow(()=>Assert.That(rig.save.Continue(),Is.False));
   Assert.That(rig.session.State,Is.EqualTo(CityState.Play));
   Assert.That(rig.session.notice,Does.StartWith("Your saved game could not be loaded").And.Contain("a new game has started").And.Contain("unreadable"));
   Assert.That(rig.session.notice,Does.Not.Contain("Exception"),"no exception type names in the player's notice");
   Assert.That(rig.pack.Credits,Is.EqualTo(City().startingCredits));
   Assert.That(Directory.GetFiles(folder,"ward-save.unreadable-*.json").Length,Is.EqualTo(1),"the damaged file is kept");
   Assert.That(WardSaveFile.TryRead(rig.save.SavePath,out var fresh,out _),"a fresh save replaces it");Assert.That(fresh.credits,Is.EqualTo(City().startingCredits));
  }

  [Test] public void NewerVersionSaveIsNotLoaded()
  {
   File.WriteAllText(Path.Combine(folder,"ward-save.json"),"{\"version\":7,\"credits\":999}");
   using var rig=new Rig(folder);
   Assert.That(rig.save.Continue(),Is.False);
   Assert.That(rig.session.notice,Does.Contain("newer build"));Assert.That(rig.pack.Credits,Is.EqualTo(City().startingCredits));
  }

  [Test] public void NewGameKeepsThePreviousSaveAndStartsFresh()
  {
   using(var a=new Rig(folder)){a.session.StartGame();Assert.That(a.pack.TryApply(new KeyValuePair<string,int>[0],500,out _));a.save.SaveNow("old");}
   using var b=new Rig(folder);
   b.save.NewGame();
   Assert.That(b.session.State,Is.EqualTo(CityState.Play));
   Assert.That(WardSaveFile.TryRead(Path.Combine(folder,"ward-save.previous.json"),out var old,out _));Assert.That(old.credits,Is.EqualTo(525));
   Assert.That(WardSaveFile.TryRead(b.save.SavePath,out var now,out _));Assert.That(now.credits,Is.EqualTo(City().startingCredits));
   Assert.That(b.save.Continue(),Is.False,"Continue only works from the start menu");
  }

  [Test] public void AutosaveCoalescesChangesAfterTheGameStarts()
  {
   using var rig=new Rig(folder);
   typeof(WardSaveGame).GetMethod("Subscribe",Any).Invoke(rig.save,null);
   var late=typeof(WardSaveGame).GetMethod("LateUpdate",Any);
   Assert.That(rig.pack.TryApply(new[]{new KeyValuePair<string,int>("grip_stabilised_pistol",1)},0,out _));rig.combat.RestorePistol(true);
   Assert.That(rig.model.TryFit("grip_stabilised_pistol",out _));late.Invoke(rig.save,null);
   Assert.That(rig.save.SaveCount,Is.Zero,"nothing is written from the start menu");
   rig.session.StartGame();
   Assert.That(rig.model.TryRemove("grip",out _));Assert.That(rig.model.TryFit("grip_stabilised_pistol",out _));
   late.Invoke(rig.save,null);late.Invoke(rig.save,null);
   Assert.That(rig.save.SaveCount,Is.EqualTo(1));Assert.That(rig.save.LastSaveReason,Is.EqualTo("autosave"));
   rig.crafting.Collect(new SalvageContents(new[]{new ItemStack("scrap_alloy",2)}),"test",Vector3.zero);late.Invoke(rig.save,null);
   Assert.That(rig.save.SaveCount,Is.EqualTo(2));
   Set(rig.session,"State",CityState.Shop);Assert.That(rig.session.SellSalvage("scrap_alloy",2));late.Invoke(rig.save,null);
   Assert.That(rig.save.SaveCount,Is.EqualTo(3));
   Assert.That(WardSaveFile.TryRead(rig.save.SavePath,out var data,out _));Assert.That(data.credits,Is.EqualTo(City().startingCredits+2));
  }
 }
}
