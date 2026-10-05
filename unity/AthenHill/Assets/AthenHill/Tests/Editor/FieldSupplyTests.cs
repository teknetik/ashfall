using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill.Tests
{
 /// 5 Oct 2026: Field Supply. Tamsin's counter trades only field gear, packs raise storage, slots and carry and take
 /// pouch and frame upgrades, digital magazines download schematics for Brann's bench in one atomic purchase, and
 /// medkits and nano recharges are used from hotbar 2 and 9.
 public class FieldSupplyTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static CharacterCatalog Characters()=>AssetDatabase.LoadAssetAtPath<CharacterCatalog>("Assets/AthenHill/Resources/CharacterCatalog.asset");
  static NpcDefinition Npc(string id)=>AssetDatabase.LoadAssetAtPath<NpcDefinition>($"Assets/AthenHill/Data/{id}.asset");
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  static readonly string[] Packs={"canvas_rucksack","frame_pack","porter_carrier","courier_cargo_rig"};
  static readonly string[] Magazines={"mag_packcraft_12","mag_karaveen_freight_3","mag_nanoweave_monthly","mag_ward_armourer"};

  /// GameSession, CraftingSession and the player (motor, health, combat) on one object; Tamsin at the counter.
  sealed class Rig:System.IDisposable
  {
   public GameObject go,npc;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public Health health;public ShopModel pack;public CraftingModel model;
   public Rig(string vendor="npc_tamsin",int credits=0)
   {
    go=new GameObject("field supply rig");go.SetActive(false);
    var input=go.AddComponent<GameInput>();input.definition=AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/AthenHill/Data/Controls.inputactions");
    var motor=go.AddComponent<PlayerMotor>();health=go.AddComponent<Health>();combat=go.AddComponent<PlayerCombat>();
    session=go.AddComponent<GameSession>();session.input=input;session.player=motor;session.catalog=City();session.npcs=new NpcAgent[0];combat.session=session;
    crafting=go.AddComponent<CraftingSession>();crafting.data=Data();crafting.combat=combat;
    npc=new GameObject("vendor");var agent=npc.AddComponent<NpcAgent>();agent.definition=Npc(vendor);
    go.SetActive(true);
    // Edit mode runs no Awake: health starts full and the combat rig binds to it as in play.
    foreach(var c in new MonoBehaviour[]{health,combat})c.GetType().GetMethod("Awake",Any)?.Invoke(c,null);
    pack=new ShopModel(City().items,credits);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(crafting,"Model",model);Set(crafting,"Session",session);
    Set(session,"ActiveNpc",agent);Set(session,"State",CityState.Shop);
   }
   public void Play(){Set(session,"ActiveNpc",null);Set(session,"State",CityState.Play);}
   public void Cooled()=>typeof(GameSession).GetField("consumableReady",Any).SetValue(session,-1f);
   public void Dispose(){Object.DestroyImmediate(go);Object.DestroyImmediate(npc);}
  }

  [Test] public void FieldSupplyTradesOnlyFieldGearAndBasicGeneralLeavesItAlone()
  {
   var city=City();var pack=new ShopModel(city.items,0);var tamsin=Npc("npc_tamsin");var mira=Npc("npc_mira");
   Assert.That(tamsin,Is.Not.Null);Assert.That(tamsin.shop.title,Is.EqualTo("Field Supply"));
   Assert.That(tamsin.shop.parts||tamsin.shop.salvage,Is.False,"Tamsin buys no salvage and sells no parts");Assert.That(tamsin.shop.magazines);
   var stock=MerchantStock.Items(city,pack,tamsin.shop,false).Select(i=>i.id).ToList();
   Assert.That(stock,Is.SupersetOf(Packs.Concat(new[]{"field_backpack","medkit","trauma_kit","nano_cell","nano_surge_pack"})));
   Assert.That(stock.Select(id=>city.items.First(i=>i.id==id)).All(i=>i.HasTag("field_supply")&&!i.HasTag("magazine")),"only field gear, never a magazine");
   Assert.That(stock,Does.Not.Contain("water_flask"));Assert.That(stock,Does.Not.Contain("scrap_alloy"));
   var general=MerchantStock.Items(city,pack,mira.shop,false).Select(i=>i.id).ToList();
   Assert.That(general,Is.SupersetOf(new[]{"water_flask","medkit","field_backpack","scrap_alloy"}),"the city loop's flask and Mira's parts stay");
   Assert.That(general.Intersect(Packs.Concat(new[]{"trauma_kit","nano_cell","nano_surge_pack"})),Is.Empty,"field_supply_only stock is Tamsin's");
   Assert.That(MerchantStock.Magazines(city,tamsin.shop).Select(i=>i.id),Is.EqualTo(Magazines));
   Assert.That(MerchantStock.Magazines(city,mira.shop),Is.Empty);
   // selling back: Tamsin buys field gear only, Mira does not take Tamsin's stock
   var rucksack=city.items.First(i=>i.id=="canvas_rucksack");var scrap=city.items.First(i=>i.id=="scrap_coil");
   Assert.That(MerchantStock.CanSell(rucksack,tamsin.shop));Assert.That(MerchantStock.CanSell(scrap,tamsin.shop),Is.False);
   Assert.That(MerchantStock.CanSell(rucksack,mira.shop),Is.False);Assert.That(MerchantStock.CanSell(scrap,mira.shop));
  }

  [Test] public void CountersRefuseTradesOutsideTheirStock()
  {
   using(var rig=new Rig("npc_mira",500))
   {
    Assert.That(rig.session.Trade("courier_cargo_rig",true),Is.False);Assert.That(rig.pack.Credits,Is.EqualTo(500));Assert.That(rig.session.notice,Does.Contain("does not stock"));
    Assert.That(rig.session.Trade("water_flask",true));Assert.That(rig.session.boughtFlask,"the city loop still buys the flask from Mira");
   }
   using(var rig=new Rig("npc_tamsin",500))
   {
    Assert.That(rig.session.Trade("water_flask",true),Is.False);Assert.That(rig.session.Trade("mag_packcraft_12",true),Is.False);Assert.That(rig.pack.Credits,Is.EqualTo(500));
    Assert.That(rig.session.Trade("nano_cell",true));Assert.That(rig.pack.Quantity("nano_cell"),Is.EqualTo(1));Assert.That(rig.pack.Credits,Is.EqualTo(494));
    Assert.That(rig.session.Trade("nano_cell",false));Assert.That(rig.pack.Credits,Is.EqualTo(496));
   }
  }

  [Test] public void EveryMagazineTeachesExistingSchematicsForTheBench()
  {
   var city=City();var data=Data();var model=new CraftingModel(data,city.items,new ShopModel(city.items,0),()=>true);
   foreach(var id in Magazines)
   {
    var item=city.items.Single(i=>i.id==id);Assert.That(item.HasTag("magazine")&&item.buyPrice>0&&item.weightKg==0,id);
    var taught=model.MagazineRecipes(id).ToList();Assert.That(taught.Count,Is.InRange(2,4),id);
    Assert.That(model.OwnsMagazine(id),Is.False,id);
    foreach(var r in taught)
    {
     Assert.That(r.knownByDefault,Is.False,r.id);Assert.That(r.stationId,Is.EqualTo("station_field_fabricator"),r.id);
     Assert.That(city.items.Any(i=>i.id==r.outputItemId),r.id);Assert.That(r.craftSeconds,Is.InRange(4f,25f),r.id);
     Assert.That(r.lockedHint,Does.Contain("magazine shelf"),r.id);
     foreach(var input in r.inputs)Assert.That(input.kind=="tag"?city.items.Any(i=>i.HasTag(input.id)):city.items.Any(i=>i.id==input.id),r.id+"/"+input.id);
    }
   }
   foreach(var r in data.recipes)foreach(var u in r.unlocks??new CraftUnlock[0])if(u.type=="magazine")Assert.That(Magazines,Does.Contain(u.id),r.id);
   // every new pack and pack upgrade can be fabricated from a magazine
   foreach(var id in Packs.Concat(new[]{"pack_side_pouches","pack_hip_belt","pack_nanoweave_pouch","pack_servo_lifter"}))
    Assert.That(data.recipes.Any(r=>r.outputItemId==id&&r.group==RecipeGroup.Gear&&r.unlocks.Any(u=>u.type=="magazine")),id);
   var learned=model.ReadMagazine("mag_packcraft_12");Assert.That(learned.Select(r=>r.outputItemId),Is.EquivalentTo(new[]{"canvas_rucksack","pack_side_pouches","pack_hip_belt"}));
   Assert.That(model.OwnsMagazine("mag_packcraft_12"));Assert.That(model.ReadMagazine("mag_packcraft_12"),Is.Empty,"a second read teaches nothing new");
   Assert.That(model.OwnsMagazine("mag_karaveen_freight_3"),Is.False);
   var saved=model.Capture();var restored=new CraftingModel(data,city.items,new ShopModel(city.items,0),()=>true);restored.Restore(saved);
   Assert.That(restored.OwnsMagazine("mag_packcraft_12"),"ownership is saved through the known schematics");
  }

  [Test] public void BuyingAMagazineIsOneAtomicDownload()
  {
   using(var rig=new Rig("npc_tamsin",10))
   {
    Assert.That(rig.session.BuyMagazine("mag_packcraft_12"),Is.False);Assert.That(rig.pack.Credits,Is.EqualTo(10));Assert.That(rig.model.Knows("recipe_canvas_rucksack"),Is.False);
    Assert.That(rig.session.notice,Does.Contain("more credits"));
    rig.pack.Grant(null,0,40,out _);
    bool bought=false;rig.session.MagazineBought+=id=>bought=id=="mag_packcraft_12";
    Assert.That(rig.session.BuyMagazine("mag_packcraft_12"));Assert.That(bought);
    Assert.That(rig.pack.Credits,Is.EqualTo(32));Assert.That(rig.pack.Quantity("mag_packcraft_12"),Is.Zero,"downloaded, never carried");
    Assert.That(rig.model.Knows("recipe_canvas_rucksack")&&rig.model.Knows("recipe_pack_side_pouches")&&rig.model.Knows("recipe_pack_hip_belt"));
    Assert.That(rig.session.notice,Does.Contain("Brann"));
    Assert.That(rig.session.BuyMagazine("mag_packcraft_12"),Is.False,"already on the slate");Assert.That(rig.pack.Credits,Is.EqualTo(32));
    Assert.That(rig.session.BuyMagazine("nano_cell"),Is.False);Assert.That(rig.pack.Credits,Is.EqualTo(32));
   }
   using(var rig=new Rig("npc_mira",500))
   {
    Assert.That(rig.session.BuyMagazine("mag_packcraft_12"),Is.False,"Basic General has no magazine shelf");Assert.That(rig.pack.Credits,Is.EqualTo(500));
   }
  }

  [Test] public void PacksRaiseStorageSlotsAndCarryAndTakeTheirUpgrades()
  {
   var city=City();var pack=new ShopModel(city.items,0);var character=new CharacterModel(Characters(),pack);pack.CapacityFailure=character.CapacityFailure;
   Assert.That(character.Equipped("storage"),Is.EqualTo("field_backpack"));
   Assert.That(character.ModificationSockets("storage").Select(s=>s.type),Is.EqualTo(new[]{"pack_pouch"}),"the starting pack has one pouch socket");
   float storage=character.StorageCapacity,carry=character.CarryCapacity;int slots=character.PackSlotCapacity;
   var tiers=Packs.Select(id=>character.Equipment(id)).ToList();
   Assert.That(tiers.All(e=>e!=null&&e.slots.SequenceEqual(new[]{"storage"})));
   float Bonus(CharacterEquipment e,string stat)=>e.modifiers.Where(m=>m.stat==stat).Sum(m=>m.flat);
   for(int i=1;i<tiers.Count;i++)
    foreach(var stat in new[]{"storageCapacity","packSlots","carryCapacity"})Assert.That(Bonus(tiers[i],stat),Is.GreaterThan(Bonus(tiers[i-1],stat)),tiers[i].itemId+" "+stat);
   pack.Grant("courier_cargo_rig",1,0,out _);
   Assert.That(character.TryEquip("courier_cargo_rig","storage",out var reason),Is.False,"the servo rig needs Engineering 35");Assert.That(reason,Does.Contain("Engineering"));
   Assert.That(character.SkillPoints,Is.GreaterThan(0));Assert.That(character.TryRaiseSkill("engineering",out _));
   Assert.That(character.TryEquip("courier_cargo_rig","storage",out reason),reason);
   Assert.That(pack.Quantity("field_backpack"),Is.EqualTo(1),"the old pack returns to the pack");
   Assert.That(character.StorageCapacity,Is.EqualTo(storage+33).Within(.01f));Assert.That(character.PackSlotCapacity,Is.EqualTo(slots+14));Assert.That(character.CarryCapacity,Is.EqualTo(carry+14).Within(.01f));
   var sockets=character.ModificationSockets("storage");Assert.That(sockets.Select(s=>s.type),Is.EqualTo(new[]{"pack_pouch","pack_pouch","pack_frame"}));
   pack.Grant("pack_servo_lifter",1,0,out _);pack.Grant("pack_side_pouches",1,0,out _);
   Assert.That(character.CanInstallModification("storage",0,"pack_servo_lifter",out _),Is.False,"a frame lifter does not clip into a pouch socket");
   Assert.That(character.TryInstallModification("storage",2,"pack_servo_lifter",out reason),reason);
   Assert.That(character.TryInstallModification("storage",0,"pack_side_pouches",out reason),reason);
   Assert.That(character.CarryCapacity,Is.EqualTo(carry+23).Within(.01f));Assert.That(character.PackSlotCapacity,Is.EqualTo(slots+18));
   Assert.That(character.TryEquip("field_backpack","storage",out reason),reason);
   Assert.That(pack.Quantity("pack_servo_lifter")+pack.Quantity("pack_side_pouches"),Is.EqualTo(2),"upgrades come off with the pack");
  }

  [Test] public void MedkitsHealAndNanoRechargesOverclockFromTheHotbar()
  {
   using(var rig=new Rig("npc_tamsin",0))
   {
    rig.Play();
    rig.pack.Grant("medkit",1,0,out _);rig.pack.Grant("trauma_kit",1,0,out _);rig.pack.Grant("nano_cell",2,0,out _);
    Assert.That(rig.session.UseItem("medkit"),Is.False,"no use at full health");Assert.That(rig.pack.Quantity("medkit"),Is.EqualTo(1));
    rig.health.Damage(70,Vector3.zero);
    // 5 Oct 2026: the hotbar uses exactly what was put on it (3 = medkit and 4 = nano cell by default).
    Assert.That(rig.session.AssignHotbar(10,"trauma_kit"),"a trauma kit goes on hotbar 0");
    rig.session.UseHotbar(10);
    Assert.That(rig.pack.Quantity("trauma_kit"),Is.Zero);Assert.That(rig.health.Current,Is.EqualTo(rig.health.max).Within(.01f));
    rig.Cooled();rig.health.Damage(25,Vector3.zero);
    Assert.That(rig.session.UseItem("medkit"));Assert.That(rig.pack.Quantity("medkit"),Is.Zero);Assert.That(rig.health.Current,Is.EqualTo(rig.health.max).Within(.01f));
    rig.Cooled();
    Assert.That(rig.session.UseItem("nano_cell"),Is.False,"no nano weapon yet");Assert.That(rig.pack.Quantity("nano_cell"),Is.EqualTo(2));
    rig.combat.hasPistol=true;Set(rig.combat,"Nano",10f);
    rig.session.UseHotbar(4);
    Assert.That(rig.pack.Quantity("nano_cell"),Is.EqualTo(1));Assert.That(rig.combat.Nano,Is.EqualTo(rig.combat.Stats.nanoMax).Within(.01f));
    Assert.That(rig.combat.Overclocked);Assert.That(rig.combat.OverclockBonus,Is.EqualTo(.5f).Within(.001f));
    Assert.That(rig.session.UseItem("nano_cell"),Is.False,"cooling down");Assert.That(rig.pack.Quantity("nano_cell"),Is.EqualTo(1));
    rig.Cooled();rig.pack.Grant("nano_surge_pack",1,0,out _);
    Assert.That(rig.session.UseItem("nano_surge_pack"));Assert.That(rig.combat.OverclockBonus,Is.EqualTo(1f).Within(.001f),"the stronger overclock wins");
    Assert.That(rig.combat.OverclockUntil-Time.time,Is.EqualTo(40f).Within(.5f));
   }
  }

  [Test] public void SceneHasTheWalkInFieldSupplyWithTamsinAtTheCounter()
  {
   var scene=EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
   try
   {
    T[] All<T>()where T:Component=>scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<T>(true)).ToArray();
    var session=All<GameSession>().Single();
    var tamsin=session.npcs.Single(n=>n&&n.definition&&n.definition.id=="npc_tamsin");
    Assert.That(tamsin.countsForCityVisit,Is.False,"the four-colonist city visit is unchanged");
    Assert.That(session.npcs.Count(n=>n&&n.countsForCityVisit),Is.EqualTo(4));
    Assert.That(tamsin.actor,Is.Not.Null);Assert.That(tamsin.definition.shop.magazines);
    var room=All<InteriorLighting>().Single(x=>x.name=="Field Supply interior");
    Assert.That(room.lamps.Length,Is.GreaterThan(3));
    foreach(var l in room.lamps)Assert.That((uint)l.renderingLayerMask,Is.EqualTo(room.interiorLayer),l.name+" lights the interior layer only");
    Assert.That(room.renderers.Count(r=>r.name.Contains("_InteriorScreens")),Is.EqualTo(2),"the magazine screens at both LODs");
    Assert.That(tamsin.transform.IsChildOf(room.transform));
    Assert.That(room.transform.Find("Packs").childCount,Is.GreaterThanOrEqualTo(8),"packs hang on the wall and the stand");
    foreach(var n in session.npcs.Where(n=>n&&n!=tamsin))Assert.That(Vector3.Distance(n.transform.position,tamsin.transform.position),Is.GreaterThan(session.interactionRange*2),n.name);
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }

  [Test] public void ConsumableDataMatchesTheCatalog()
  {
   var city=City();
   Assert.That(city.consumables.Select(c=>c.itemId),Is.EquivalentTo(new[]{"medkit","trauma_kit","nano_cell","nano_surge_pack"}));
   foreach(var c in city.consumables){var item=city.items.Single(i=>i.id==c.itemId);Assert.That(item.HasTag("consumable"),c.itemId);Assert.That(c.restoreHealth>0||c.restoreNano>0||c.overclockSeconds>0,c.itemId);}
   Assert.That(city.Consumable("trauma_kit").restoreHealth,Is.GreaterThan(city.Consumable("medkit").restoreHealth));
   Assert.That(city.Consumable("nano_surge_pack").overclockSeconds,Is.GreaterThan(city.Consumable("nano_cell").overclockSeconds));
   Assert.That(city.Consumable("water_flask"),Is.Null);
  }
 }
}
