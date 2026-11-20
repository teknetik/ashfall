using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// 20 Nov 2026, crafting rework phase 3: weapons wear per shot (condition = the Durability stat), a worn weapon spreads and
 /// misfires, 0 is a jam; the carried toolkit repairs in the field for a falling amount and lowers the weapon's best
 /// condition until it is broken; a bench overhaul restores it; condition is saved (older saves load at full condition).
 public class WeaponConditionTests
 {
  const string Station="station_field_fabricator",Pistol="weapon_scrap_pistol",Rifle="weapon_field_rifle";
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.id,x.n)),0,out var r),Is.True,r);
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  static (ShopModel pack,CraftingModel model,WeaponLoadout pistol) Run(bool toolkit=true)
  {
   var pack=new ShopModel(City().items);
   if(!toolkit&&pack.Quantity("field_toolkit")>0)Give(pack,("field_toolkit",-pack.Quantity("field_toolkit")));
   var model=new CraftingModel(Data(),City().items,pack,()=>true);
   return (pack,model,model.GetLoadout(Pistol));
  }
  /// One completed field repair at an arbitrary clock; returns the condition restored.
  static float Repair(CraftingModel model,string weapon,float now=0)
  {
   Assert.That(model.BeginRepair(weapon,now,out var reason),reason);
   Assert.That(model.TickRepair(now+model.Condition.repairSeconds,out _,out reason,out float amount),Is.EqualTo(CraftTick.Completed),reason);
   return amount;
  }
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public ShopModel pack;public CraftingModel model;
   public Rig(CityState state=CityState.Inventory)
   {
    go=new GameObject("condition rig");go.SetActive(false);
    session=go.AddComponent<GameSession>();session.catalog=City();crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    var player=new GameObject("combat");player.transform.SetParent(go.transform);combat=player.AddComponent<PlayerCombat>();combat.hasPistol=true;crafting.combat=combat;
    pack=new ShopModel(City().items);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",state);Set(session,"ActiveStationId",Station);
    Set(crafting,"Model",model);Set(crafting,"Session",session);combat.BindLoadout(model.Loadout);
   }
   public void Dispose(){Object.DestroyImmediate(go);Time.timeScale=1;}
  }

  [Test] public void DataShapeDefaultsAreSane()
  {
   var data=Data();var rules=data.condition;
   Assert.That(data.weapons.Single(w=>w.id==Pistol).stats.durability,Is.EqualTo(100));Assert.That(data.weapons.Single(w=>w.id==Rifle).stats.durability,Is.EqualTo(100));
   Assert.That(data.weapons.Single(w=>w.id==Pistol).wearPerShot,Is.GreaterThan(0));Assert.That(data.weapons.Single(w=>w.id==Rifle).wearPerShot,Is.GreaterThan(0));
   Assert.That(rules.repairAmounts,Is.EqualTo(new[]{30f,20f,12f,6f}));Assert.That(rules.capLossPerRepair,Is.GreaterThan(0));Assert.That(rules.repairSeconds,Is.GreaterThan(0));
   Assert.That(rules.repairTool,Is.EqualTo("tool:screwdriver"));Assert.That(rules.overhaulInputs.Select(i=>i.id),Is.EquivalentTo(new[]{"scrap_alloy","nanite:tier1"}));
   // The field fix can be made four times; the cap falls under the broken line exactly after the fourth.
   float cap=100;for(int i=0;i<rules.repairAmounts.Length;i++){Assert.That(cap,Is.GreaterThanOrEqualTo(rules.brokenBelow),"repair "+(i+1)+" still allowed");cap-=rules.capLossPerRepair;}
   Assert.That(cap,Is.LessThan(rules.brokenBelow));
   // Ordinary play: 100 shots of the pistol (every droid of the primer and the orders at about five shots each) costs under 15 condition.
   Assert.That(100*data.weapons.Single(w=>w.id==Pistol).wearPerShot,Is.LessThan(rules.spreadBelow*.5f));
   Assert.That(rules.misfireBelow,Is.LessThanOrEqualTo(rules.spreadBelow));
  }

  [Test] public void ShotsWearConditionAndNothingJamsAtFullCondition()
  {
   var (_,model,pistol)=Run();
   Assert.That(pistol.HasCondition);Assert.That(pistol.Durability,Is.EqualTo(100));Assert.That(pistol.MaxDurability,Is.EqualTo(100));
   float wear=pistol.WearPerShot;Assert.That(wear,Is.EqualTo(.15f).Within(1e-4));
   for(int i=0;i<10;i++)pistol.Wear(wear);
   Assert.That(pistol.Durability,Is.EqualTo(100-10*wear).Within(1e-3));
   Assert.That(WeaponCondition.BeforeShot(pistol,model.Condition,0f),Is.EqualTo(ShotOutcome.Fire),"no misfire in good order even on the worst roll");
   Assert.That(WeaponCondition.SpreadScale(model.Condition,pistol.Durability),Is.EqualTo(1f));
   // a weapon with no base durability never wears
   var data=Object.Instantiate(Data());try{data.weapons.Single(w=>w.id==Pistol).stats.durability=0;
    var m2=new CraftingModel(data,City().items,new ShopModel(City().items),()=>true);var p2=m2.GetLoadout(Pistol);
    Assert.That(p2.HasCondition,Is.False);p2.Wear(5);Assert.That(WeaponCondition.BeforeShot(p2,data.condition,0f),Is.EqualTo(ShotOutcome.Fire));}finally{Object.DestroyImmediate(data);}
  }

  [Test] public void LowConditionWidensSpreadAndMisfiresAndZeroJams()
  {
   var (_,model,pistol)=Run();var r=model.Condition;
   Assert.That(WeaponCondition.SpreadScale(r,r.spreadBelow),Is.EqualTo(1f));
   Assert.That(WeaponCondition.SpreadScale(r,r.spreadBelow/2),Is.EqualTo(1+(r.spreadMaxScale-1)/2).Within(1e-4));
   Assert.That(WeaponCondition.SpreadScale(r,0),Is.EqualTo(r.spreadMaxScale).Within(1e-4));
   Assert.That(WeaponCondition.MisfireChance(r,r.misfireBelow),Is.Zero);Assert.That(WeaponCondition.MisfireChance(r,0),Is.Zero,"0 is a jam, not a misfire");
   Assert.That(WeaponCondition.MisfireChance(r,r.misfireBelow/2),Is.EqualTo(r.misfireMaxChance/2).Within(1e-4));
   pistol.Wear(100-r.misfireBelow/2);
   float chance=WeaponCondition.MisfireChance(r,pistol.Durability);Assert.That(chance,Is.GreaterThan(0));
   Assert.That(WeaponCondition.BeforeShot(pistol,r,chance-.001f),Is.EqualTo(ShotOutcome.Misfire));
   Assert.That(WeaponCondition.BeforeShot(pistol,r,chance+.001f),Is.EqualTo(ShotOutcome.Fire));
   pistol.Wear(1000);Assert.That(pistol.Durability,Is.Zero);Assert.That(pistol.Jammed);
   Assert.That(WeaponCondition.BeforeShot(pistol,r,.999f),Is.EqualTo(ShotOutcome.Jammed),"jammed cannot fire whatever the roll");
   Assert.That(WeaponCondition.Label(pistol,r),Does.Contain("jammed"));
  }

  [Test] public void RepairAmountsFallAndEachRepairLowersTheCapUntilBroken()
  {
   var (_,model,pistol)=Run();var r=model.Condition;
   float[] expectedCap={92,84,76,68};
   float[] expectedGain={30,20,12,6};
   for(int i=0;i<4;i++)
   {
    pistol.Wear(pistol.MaxDurability);  // run it flat each time: the cap, not the wear, limits the gain
    Assert.That(model.CanFieldRepair(Pistol,out var reason),reason);
    float gain=Repair(model,Pistol,i*100);
    Assert.That(gain,Is.EqualTo(expectedGain[i]).Within(1e-3),"repair "+(i+1));
    Assert.That(pistol.MaxDurability,Is.EqualTo(expectedCap[i]).Within(1e-3));Assert.That(pistol.Repairs,Is.EqualTo(i+1));
    Assert.That(pistol.Durability,Is.LessThanOrEqualTo(pistol.MaxDurability));
   }
   Assert.That(WeaponCondition.IsBroken(pistol,r));Assert.That(model.CanFieldRepair(Pistol,out var why),Is.False);Assert.That(why,Is.EqualTo("broken"));
   Assert.That(CraftingText.ConditionReason(why,model,pistol),Does.Contain("overhaul"));
   Assert.That(model.BeginRepair(Pistol,0,out why),Is.False);Assert.That(model.RepairJob,Is.Null);
  }

  [Test] public void RepairNeverExceedsTheLoweredCapAndNeedsDamageAndTheToolkit()
  {
   var (pack,model,pistol)=Run();
   Assert.That(model.CanFieldRepair(Pistol,out var reason),Is.False);Assert.That(reason,Is.EqualTo("in_good_order"),"a weapon at its cap needs nothing");
   pistol.Wear(5);Assert.That(model.CanFieldRepair(Pistol,out reason),Is.False);Assert.That(reason,Is.EqualTo("in_good_order"),"at 95 a fix would only lower the cap to 92: refused");
   pistol.Wear(15);float gain=Repair(model,Pistol);
   Assert.That(gain,Is.EqualTo(12).Within(1e-3),"80 + 30 stops at the lowered cap of 92");
   Assert.That(pistol.Durability,Is.EqualTo(92).Within(1e-3));Assert.That(pistol.MaxDurability,Is.EqualTo(92).Within(1e-3));
   var (pack2,model2,pistol2)=Run(toolkit:false);pistol2.Wear(40);
   Assert.That(model2.CanFieldRepair(Pistol,out reason),Is.False);Assert.That(reason,Is.EqualTo("missing_tool"));
   Assert.That(CraftingText.ConditionReason(reason,model2,pistol2),Does.Contain("Screwdriver"));
   Give(pack2,("field_toolkit",1));Assert.That(model2.CanFieldRepair(Pistol,out reason),reason);
   Assert.That(pack2.Quantity("field_toolkit"),Is.EqualTo(1),"the toolkit is never consumed");
   Assert.That(model2.RepairGain(Pistol),Is.EqualTo(30).Within(1e-3));
  }

  [Test] public void RepairIsTimedAndCancelRulesMirrorTimedCrafting()
  {
   var (_,model,pistol)=Run();pistol.Wear(50);
   Assert.That(model.BeginRepair(Pistol,10,out _));
   Assert.That(model.BeginRepair(Pistol,10,out var reason),Is.False);Assert.That(reason,Is.EqualTo("busy"));
   Assert.That(model.TickRepair(10+model.Condition.repairSeconds-.01f,out _,out _,out _),Is.EqualTo(CraftTick.None));Assert.That(pistol.Durability,Is.EqualTo(50).Within(1e-3),"nothing changes before the end");
   Assert.That(model.CancelRepair(out var job));Assert.That(job.recipeId,Is.EqualTo(Pistol));Assert.That(pistol.Durability,Is.EqualTo(50).Within(1e-3));Assert.That(pistol.Repairs,Is.Zero);
   Assert.That(model.CancelRepair(out _),Is.False);
   // the toolkit leaving the pack before the end fails the repair with nothing changed
   var (pack,m2,p2)=Run();p2.Wear(50);m2.BeginRepair(Pistol,0,out _);Give(pack,("field_toolkit",-1));
   Assert.That(m2.TickRepair(99,out _,out reason,out _),Is.EqualTo(CraftTick.Failed));Assert.That(reason,Is.EqualTo("missing_tool"));Assert.That(p2.Durability,Is.EqualTo(50).Within(1e-3));
  }

  [Test] public void SessionCancelsARepairOnDamageDrawingFiringAndLeavingTheFieldPack()
  {
   using var rig=new Rig();rig.model.GetLoadout(Pistol).Wear(60);
   var finished=new List<(bool ok,string reason)>();rig.crafting.RepairFinished+=(j,ok,r)=>finished.Add((ok,r));
   Assert.That(rig.crafting.BeginFieldRepair(Pistol,out var reason),reason);Assert.That(rig.crafting.RepairJob,Is.Not.Null);
   typeof(CraftingSession).GetMethod("OnDamaged",Any).Invoke(rig.crafting,new object[]{5f,Vector3.zero});
   Assert.That(rig.crafting.RepairJob,Is.Null);Assert.That(finished.Last(),Is.EqualTo((false,"cancelled")));Assert.That(rig.session.notice,Does.Contain("hit"));
   Assert.That(rig.model.Loadout.Durability,Is.EqualTo(40).Within(1e-3));
   // drawing or firing a weapon (PlayerCombat.WeaponHandled)
   Assert.That(rig.crafting.BeginFieldRepair(Pistol,out reason),reason);
   typeof(CraftingSession).GetMethod("OnWeaponHandled",Any).Invoke(rig.crafting,null);
   Assert.That(rig.crafting.RepairJob,Is.Null);Assert.That(finished.Count,Is.EqualTo(2));Assert.That(rig.session.notice,Does.Contain("weapon"));
   // leaving play and the field pack (the bench, a shop, a conversation)
   Assert.That(rig.crafting.BeginFieldRepair(Pistol,out reason),reason);
   Set(rig.session,"State",CityState.Shop);typeof(CraftingSession).GetMethod("Update",Any).Invoke(rig.crafting,null);
   Assert.That(rig.crafting.RepairJob,Is.Null);Assert.That(finished.Count,Is.EqualTo(3));Assert.That(rig.model.Loadout.Durability,Is.EqualTo(40).Within(1e-3));
   // and a quiet repair completes through the session
   Set(rig.session,"State",CityState.Inventory);
   Assert.That(rig.crafting.BeginFieldRepair(Pistol,out reason),reason);
   rig.crafting.TickRepair(rig.crafting.RepairJob.EndsAt);
   Assert.That(finished.Last(),Is.EqualTo((true,"ok")));Assert.That(rig.model.Loadout.Durability,Is.EqualTo(70).Within(1e-3));Assert.That(rig.session.notice,Does.Contain("repaired"));
   // refused outside the field pack and play
   Set(rig.session,"State",CityState.Dialogue);Assert.That(rig.crafting.BeginFieldRepair(Pistol,out reason),Is.False);
  }

  [Test] public void OverhaulRestoresTheCapAndResetsRepairsForAlloyAndNanites()
  {
   var (pack,model,pistol)=Run();
   Assert.That(model.CanOverhaul(Pistol,Station,out var reason),Is.False);Assert.That(reason,Is.EqualTo("in_good_order"));
   pistol.Wear(pistol.MaxDurability);for(int i=0;i<4;i++){Repair(model,Pistol,i);pistol.Wear(pistol.MaxDurability);}
   Assert.That(WeaponCondition.IsBroken(pistol,model.Condition));
   Assert.That(model.CanOverhaul(Pistol,"station_elsewhere",out reason),Is.False);Assert.That(reason,Is.EqualTo("wrong_station"));
   Assert.That(model.CanOverhaul(Pistol,Station,out reason),Is.False);Assert.That(reason,Is.EqualTo("missing_ingredients"));Assert.That(CraftingText.ConditionReason(reason,model,pistol),Does.Contain("Scrap Alloy"));
   Give(pack,("scrap_alloy",3),("nanite_residue",4));
   int alloy=pack.Quantity("scrap_alloy"),nanites=pack.Quantity("nanite_residue");
   Assert.That(model.TryOverhaul(Pistol,Station,out reason),reason);
   Assert.That(pistol.Durability,Is.EqualTo(100));Assert.That(pistol.MaxDurability,Is.EqualTo(100));Assert.That(pistol.Repairs,Is.Zero);Assert.That(WeaponCondition.IsBroken(pistol,model.Condition),Is.False);
   Assert.That(pack.Quantity("scrap_alloy"),Is.EqualTo(alloy-3));Assert.That(pack.Quantity("nanite_residue"),Is.EqualTo(nanites-4));
   Pistol_FieldRepairWorksAgain(model,pistol);
  }
  static void Pistol_FieldRepairWorksAgain(CraftingModel model,WeaponLoadout pistol){pistol.Wear(50);Assert.That(model.CanFieldRepair(Pistol,out var reason),reason);Assert.That(model.RepairGain(Pistol),Is.EqualTo(30).Within(1e-3));}

  [Test] public void SessionOverhaulWorksOnlyAtTheBench()
  {
   using var rig=new Rig(CityState.Fabricator);var pistol=rig.model.GetLoadout(Pistol);pistol.Wear(30);Give(rig.pack,("scrap_alloy",3),("nanite_residue",4));
   Set(rig.session,"State",CityState.Play);Assert.That(rig.crafting.Overhaul(Pistol,out var reason),Is.False);Assert.That(reason,Is.EqualTo("wrong_station"));
   Set(rig.session,"State",CityState.Fabricator);Assert.That(rig.crafting.Overhaul(Pistol,out reason),reason);
   Assert.That(pistol.Durability,Is.EqualTo(100));Assert.That(rig.session.notice,Does.Contain("overhauled"));
   Assert.That(rig.crafting.Overhaul(Pistol,out reason),Is.False);Assert.That(reason,Is.EqualTo("in_good_order"));
  }

  [Test] public void ConditionSurvivesSaveLoadAndOlderSavesLoadAtFullCondition()
  {
   var (_,model,pistol)=Run();var rifle=model.GetLoadout(Rifle);
   pistol.Wear(100);Repair(model,Pistol);Repair(model,Pistol,10);pistol.Wear(17.5f);rifle.Wear(12.5f);
   var json=JsonUtility.ToJson(model.Capture());var state=JsonUtility.FromJson<CraftingState>(json);
   var (_,fresh,p2)=Run();fresh.Restore(state);
   Assert.That(p2.MaxDurability,Is.EqualTo(pistol.MaxDurability).Within(1e-3));Assert.That(p2.Durability,Is.EqualTo(pistol.Durability).Within(1e-3));Assert.That(p2.Repairs,Is.EqualTo(2));
   Assert.That(fresh.GetLoadout(Rifle).Durability,Is.EqualTo(87.5f).Within(1e-3));
   // a broken weapon stays broken through save and load
   for(int i=0;i<2;i++){pistol.Wear(100);Repair(model,Pistol,20+i);}
   Assert.That(WeaponCondition.IsBroken(pistol,model.Condition));
   var (_,broken,p3)=Run();broken.Restore(JsonUtility.FromJson<CraftingState>(JsonUtility.ToJson(model.Capture())));
   Assert.That(WeaponCondition.IsBroken(p3,broken.Condition));Assert.That(broken.CanFieldRepair(Pistol,out var reason),Is.False);Assert.That(reason,Is.EqualTo("broken"));
   // a save from before phase 3 (no condition fields at all) loads at full condition
   const string old="{\"known\":[],\"crafted\":[],\"crafts\":0,\"fitted\":[],\"weapons\":[{\"weaponId\":\"weapon_scrap_pistol\",\"fitted\":[]},{\"weaponId\":\"weapon_field_rifle\",\"fitted\":[]}]}";
   var (_,legacy,p4)=Run();p4.Wear(60);legacy.GetLoadout(Rifle).Wear(60);
   Assert.That(legacy.Restore(JsonUtility.FromJson<CraftingState>(old)),Is.Empty);
   Assert.That(p4.Durability,Is.EqualTo(100));Assert.That(p4.MaxDurability,Is.EqualTo(100));Assert.That(legacy.GetLoadout(Rifle).Durability,Is.EqualTo(100));
   legacy.Restore(null);Assert.That(p4.Repairs,Is.Zero);
   // bad values are clamped
   var wild=new CraftingState{weapons=new[]{new WeaponLoadoutState{weaponId=Pistol,fitted=new SlotEntry[0],conditionVersion=1,durability=500,maxDurability=900,repairs=-3}}};
   var (_,clamp,p5)=Run();clamp.Restore(wild);Assert.That(p5.MaxDurability,Is.EqualTo(100));Assert.That(p5.Durability,Is.EqualTo(100));Assert.That(p5.Repairs,Is.Zero);
  }

  [Test] public void PanelsShowConditionAndTheRepairAndOverhaulActions()
  {
   using var rig=new Rig(CityState.Fabricator);var pistol=rig.model.GetLoadout(Pistol);pistol.Wear(35);
   foreach(var r in Data().recipes)rig.model.Unlock(r.id);
   var root=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
   var panel=new FabricatorPanel(root,rig.session,rig.crafting);panel.Opened();panel.Refresh();
   Assert.That(root.Q<Label>("fabricator-stat").text,Does.Contain("CONDITION 65 / 100"));
   var overhaul=root.Q<Button>("fabricator-overhaul");Assert.That(overhaul,Is.Not.Null);Assert.That(overhaul.enabledSelf,Is.False,"no parts");
   Give(rig.pack,("scrap_alloy",3),("nanite_residue",4));panel.Refresh();Assert.That(overhaul.enabledSelf);
   panel.Overhaul();Assert.That(pistol.Durability,Is.EqualTo(100));
   Assert.That(CraftingText.Condition(pistol,rig.model),Is.EqualTo("Condition 100 / 100"));
  }
 }
}
