using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
using UnityEngine.TestTools;
using System.Text.RegularExpressions;
namespace AthenHill.Tests
{
 /// Steady Hands bench, crafting side (20 Nov 2026, craft agent): the bench job's ticket (reservation, completion,
 /// abandoning, saving), the hand-made gate on the timer, crafted quality, the order stages with a bench job and the
 /// pistol's handling with and without the grip.
 public class SteadyHandsCraftTests
 {
  const string Station="station_field_fabricator";
  const string Grip="recipe_grip_stabilised_pistol";
  const string GripItem="grip_stabilised_pistol";
  const string Pistol="weapon_scrap_pistol";
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static FieldOrderSet Orders()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");
  static VisualElement Hud()=>AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.id,x.n)),0,out var r),Is.True,r);
  static void GiveGripParts(ShopModel pack)=>Give(pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  static AssemblyResult Result(CraftQuality q,params ItemStack[] by)=>new AssemblyResult{recipeId=Grip,quality=q,score=q==CraftQuality.Fine?.9f:q==CraftQuality.Standard?.7f:.4f,faults=1,seconds=900,byproducts=by};
  static ItemStack Filament=>new ItemStack("copper_filament",1);
  sealed class Run
  {
   public ShopModel pack;public CraftingModel model;public CharacterModel character;public bool hasPistol=true;
   public Run()
   {
    pack=new ShopModel(City().items);
    var catalog=ScriptableObject.CreateInstance<CharacterCatalog>();catalog.skills=new[]{new CharacterSkill{id="engineering",initial=20}};
    character=new CharacterModel(catalog,pack);
    model=new CraftingModel(Data(),City().items,pack,()=>hasPistol,character:character);
    model.Unlock(Grip);
   }
  }
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public ShopModel pack;public CraftingModel model;
   public Rig()
   {
    go=new GameObject("steady hands rig");go.SetActive(false);
    session=go.AddComponent<GameSession>();session.catalog=City();crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    var player=new GameObject("combat");player.transform.SetParent(go.transform);combat=player.AddComponent<PlayerCombat>();combat.hasPistol=true;crafting.combat=combat;
    pack=new ShopModel(City().items);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",CityState.Fabricator);Set(session,"ActiveStationId",Station);
    Set(crafting,"Model",model);Set(crafting,"Session",session);combat.BindLoadout(model.Loadout);combat.BindCraftingModel(model);
    model.Unlock(Grip);
   }
   public void Dispose(){Object.DestroyImmediate(go);Time.timeScale=1;}
  }

  [Test] public void DataGivesTheGripAHandsOnJobAndThePistolItsRoughness()
  {
   var data=Data();
   Assert.That(data.recipes.Single(r=>r.id==Grip).assembly,Is.EqualTo("assembly_grip_stabilised_pistol"));
   Assert.That(data.recipes.Where(r=>!string.IsNullOrEmpty(r.assembly)).Select(r=>r.id),Is.EqualTo(new[]{Grip}),"only the grip has a bench job this round");
   var pistol=data.weapons.Single(w=>w.id==Pistol).stats;
   Assert.That(pistol.sway,Is.GreaterThan(0));Assert.That(pistol.sideKick,Is.GreaterThan(0));Assert.That(pistol.recovery,Is.GreaterThan(WeaponHandlingRules.DefaultRecoverySeconds));Assert.That(pistol.scatterGrowth,Is.GreaterThan(0));
   var rifle=data.weapons.Single(w=>w.id=="weapon_field_rifle").stats;
   Assert.That(new[]{rifle.sway,rifle.sideKick,rifle.recovery,rifle.scatterGrowth},Is.All.EqualTo(0f),"the rifle's feel is unchanged");
   var grip=data.modifiers.Single(m=>m.itemId==GripItem);
   Assert.That(grip.effects.Single(e=>e.stat=="recoil").byQuality,Is.EqualTo(new[]{-5f,-7f,-10f}));
   foreach(var e in grip.effects)Assert.That(e.byQuality,Has.Length.EqualTo(3),e.stat);
   foreach(var id in new[]{"sway","sideKick","recovery","scatterGrowth"})Assert.That(data.Stat(id),Is.Not.Null,id+" has a label");
   // the audio agent's takes are bound by the data script
   Assert.That(data.rattleClips,Has.Length.EqualTo(3).And.All.Not.Null);Assert.That(data.damperClips,Has.Length.EqualTo(4).And.All.Not.Null);
   var steady=Orders().orders[0];
   foreach(var clip in new[]{steady.testFireVoice,steady.testFireTightVoice,steady.testFirePoorVoice,steady.completeVoice})Assert.That(clip,Is.Not.Null);
   Assert.That(AssetDatabase.LoadAssetAtPath<NpcDefinition>("Assets/AthenHill/Data/npc_brann.asset").nodes.Single(n=>n.id=="steady_bench_open").voice,Is.Not.Null);
   // the base pistol keeps its first-shot numbers
   Assert.That(pistol.recoil,Is.EqualTo(38));Assert.That(pistol.spread,Is.EqualTo(4));
  }

  [Test] public void BeginReservesTheInputsOnTheBenchAndTakesThePistol()
  {
   var run=new Run();GiveGripParts(run.pack);Give(run.pack,("scrap_alloy",1));
   Assert.That(run.model.CanBeginAssembly(Grip,Station,out var why),why);
   var ticket=run.model.BeginAssembly(Grip,Station,out why);
   Assert.That(ticket,Is.Not.Null,why);
   Assert.That(ticket.weaponId,Is.EqualTo(Pistol));Assert.That(ticket.resumed,Is.False);
   Assert.That(ticket.inputs.ToDictionary(s=>s.itemId,s=>s.quantity),Is.EquivalentTo(new Dictionary<string,int>{{"droid_servo_damaged",1},{"scrap_alloy",2},{"nanite_residue",5}}));
   // out of the pack: nothing to sell, store or use in another craft; the spare alloy stays
   Assert.That(run.pack.Quantity("droid_servo_damaged"),Is.Zero);Assert.That(run.pack.Quantity("nanite_residue"),Is.Zero);Assert.That(run.pack.Quantity("scrap_alloy"),Is.EqualTo(1));
   Assert.That(run.pack.Quantity("field_toolkit"),Is.EqualTo(1),"tools are not reserved");
   Assert.That(run.model.OnBench(Pistol));Assert.That(run.model.OpenTicket,Is.SameAs(ticket));
   // the timer cannot make it meanwhile, and a second job cannot start
   Assert.That(run.model.CanCraftOnTimer(Grip,Station,out why),Is.False);Assert.That(why,Is.EqualTo("on_bench"));
   Assert.That(run.model.TryCraft(Grip,Station,out why),Is.False);
   GiveGripParts(run.pack);
   Assert.That(run.model.BeginAssembly(Grip,Station,out why),Is.SameAs(ticket),"the open job is resumed");Assert.That(why,Is.EqualTo("resumed"));Assert.That(ticket.resumed);
   // the pistol: no fitting, removing, field repair or overhaul while it is on the bench
   Give(run.pack,("barrel_bored_alloy",1));
   Assert.That(run.model.CanFit(Pistol,"barrel_bored_alloy",out why,Station),Is.False);Assert.That(why,Is.EqualTo("on_bench"));
   Assert.That(run.model.TryRemove(Pistol,"grip",out why),Is.False);Assert.That(why,Is.EqualTo("on_bench"));
   Assert.That(run.model.CanFieldRepair(Pistol,out why),Is.False);Assert.That(why,Is.EqualTo("on_bench"));
   Assert.That(run.model.CanOverhaul(Pistol,Station,out why),Is.False);Assert.That(why,Is.EqualTo("on_bench"));
   Assert.That(CraftingText.ConditionReason("on_bench",run.model,run.model.Loadout),Does.Contain("on the bench"));
   Assert.That(CraftingText.Reason("hand_made_first",run.model,run.model.Recipe(Grip)),Does.Contain("by hand"));
  }

  [Test] public void ReservationTakesTheLockerAfterThePack()
  {
   var run=new Run();var stash=new StashModel();run.model.Reserve=stash;run.model.ReserveOpen=()=>true;
   Give(run.pack,("droid_servo_damaged",1),("scrap_alloy",1),("nanite_residue",5));
   Give(run.pack,("scrap_alloy",1));Assert.That(stash.Store(run.pack,"scrap_alloy",1,out var r),r);
   Assert.That(run.model.BeginAssembly(Grip,Station,out r),Is.Not.Null,r);
   Assert.That(run.pack.Quantity("scrap_alloy"),Is.Zero);Assert.That(stash.Quantity("scrap_alloy"),Is.Zero);
   Assert.That(run.model.AbandonAssembly(null,out r),r);
   Assert.That(run.pack.Quantity("scrap_alloy"),Is.EqualTo(2),"abandoned inputs come back to the pack");
  }

  [Test] public void CompleteFitsTheGripAtItsQualityAndUnlocksTheTimer()
  {
   var run=new Run();GiveGripParts(run.pack);
   Assert.That(run.model.NeedsHandMade(Grip));
   Assert.That(run.model.TryCraft(Grip,Station,out var why),Is.False);Assert.That(why,Is.EqualTo("hand_made_first"));
   Assert.That(run.model.BeginCraft(Grip,Station,0,out why),Is.False);Assert.That(why,Is.EqualTo("hand_made_first"));
   Assert.That(run.model.CanCraftOnTimer(Grip,Station,out why),Is.False);Assert.That(why,Is.EqualTo("hand_made_first"));
   Assert.That(run.model.CanCraft(Grip,Station,out why),why+": order stages still see a craftable recipe");
   Assert.That(run.model.BeginAssembly(Grip,Station,out why),Is.Not.Null,why);
   int xp=run.character.Experience;
   Assert.That(run.model.CompleteAssembly(Result(CraftQuality.Fine,Filament),out why),why);
   Assert.That(run.model.OpenTicket,Is.Null);Assert.That(run.model.OnBench(Pistol),Is.False);
   Assert.That(run.model.Loadout.Fitted("grip"),Is.EqualTo(GripItem));Assert.That(run.model.Loadout.Quality("grip"),Is.EqualTo(CraftQuality.Fine));
   Assert.That(run.pack.Quantity(GripItem),Is.Zero,"fitted in the same transaction, never in the pack");
   Assert.That(run.pack.Quantity("copper_filament"),Is.EqualTo(1));
   Assert.That(run.pack.Quantity("droid_servo_damaged")+run.pack.Quantity("scrap_alloy")+run.pack.Quantity("nanite_residue"),Is.Zero);
   Assert.That(run.model.Loadout.Stats.recoil,Is.EqualTo(28).Within(.001f),"38 - 10 for Fine");
   Assert.That(run.model.CraftCount(Grip),Is.EqualTo(1));Assert.That(run.model.HandMade(Grip));Assert.That(run.model.LastAssemblyFitted);
   Assert.That(run.character.Experience,Is.EqualTo(xp+run.model.Recipe(Grip).craftXp),"XP as for a timed craft");
   Assert.That(run.model.LastAward,Is.Not.Null);
   // 21 Nov 2026 (Carl: "no auto assemble for anything ever"): made by hand once, the timer is still refused; the next one is
   // built by hand too. The job counts as finished at the bench (Brann's guidance stops after it; older saves have none)
   Assert.That(run.model.FinishedAtBench(Grip));
   GiveGripParts(run.pack);
   Assert.That(run.model.NeedsHandMade(Grip));
   Assert.That(run.model.BeginCraft(Grip,Station,0,out why),Is.False);Assert.That(why,Is.EqualTo("hand_made_first"));
   Assert.That(run.model.CanCraftOnTimer(Grip,Station,out why),Is.False);
   Assert.That(run.model.BeginAssembly(Grip,Station,out why),Is.Not.Null,"Build by hand again: "+why);
   var saved=JsonUtility.ToJson(run.model.Capture());Assert.That(saved,Does.Contain("benchFinished"));
   var reloaded=new Run();reloaded.model.Restore(JsonUtility.FromJson<CraftingState>(saved));Assert.That(reloaded.model.FinishedAtBench(Grip));
   var older=new Run();older.model.Restore(JsonUtility.FromJson<CraftingState>("{\"known\":[\"recipe_grip_stabilised_pistol\"],\"crafted\":[{\"id\":\"recipe_grip_stabilised_pistol\",\"count\":1}],\"crafts\":1}"));
   Assert.That(older.model.HandMade(Grip),"an older save that made the grip on the timer counts as made by hand");
   Assert.That(older.model.FinishedAtBench(Grip),Is.False,"but has never finished a job at the bench: guided");
   Assert.That(older.model.CanCraftOnTimer(Grip,Station,out why),Is.False,"and gets no timer from it");
   Assert.That(run.model.AbandonAssembly(new string[0],out why),why);
   // a part completed with nothing open is refused
   Assert.That(run.model.CompleteAssembly(Result(CraftQuality.Fine),out why),Is.False);Assert.That(why,Is.EqualTo("no_job"));
  }

  [Test] public void CompleteReplacesAnotherGripAndKeepsItsQuality()
  {
   var run=new Run();
   Give(run.pack,("grip_gyro_braced",1));Assert.That(run.model.TryFit("grip_gyro_braced",out var why),why);
   GiveGripParts(run.pack);Assert.That(run.model.BeginAssembly(Grip,Station,out why),Is.Not.Null,why);
   Assert.That(run.model.CompleteAssembly(Result(CraftQuality.Rough),out why),why);
   Assert.That(run.model.Loadout.Fitted("grip"),Is.EqualTo(GripItem));Assert.That(run.model.Loadout.Quality("grip"),Is.EqualTo(CraftQuality.Rough));
   Assert.That(run.pack.Quantity("grip_gyro_braced"),Is.EqualTo(1),"the replaced grip returns to the pack");
   // removed: the Rough grip is carried as Rough; fitted again it is still Rough
   Assert.That(run.model.TryRemove("grip",out why),why);
   Assert.That(run.model.CarriedQuality(GripItem,CraftQuality.Rough),Is.EqualTo(1));Assert.That(run.model.CarriedQuality(GripItem,CraftQuality.Standard),Is.Zero);
   Assert.That(run.model.TryFit(GripItem,out why),why);Assert.That(run.model.Loadout.Quality("grip"),Is.EqualTo(CraftQuality.Rough));
   Assert.That(run.model.Loadout.Stats.recoil,Is.EqualTo(33).Within(.001f));
  }

  [Test] public void AbandonReturnsThePistolAndWhatWasNotSpent()
  {
   var run=new Run();GiveGripParts(run.pack);
   Assert.That(run.model.BeginAssembly(Grip,Station,out var why),Is.Not.Null,why);
   Assert.That(run.model.AbandonAssembly(new[]{"scrap_alloy","nanite_residue","nanite_residue","not_an_input"},out why),why);
   Assert.That(run.model.OpenTicket,Is.Null);Assert.That(run.model.OnBench(Pistol),Is.False);
   Assert.That(run.pack.Quantity("droid_servo_damaged"),Is.EqualTo(1));Assert.That(run.pack.Quantity("scrap_alloy"),Is.EqualTo(1));Assert.That(run.pack.Quantity("nanite_residue"),Is.EqualTo(3));
   Assert.That(run.model.CraftCount(Grip),Is.Zero);Assert.That(run.model.HandMade(Grip),Is.False);
   Assert.That(run.model.AbandonAssembly(null,out why),Is.False);Assert.That(why,Is.EqualTo("no_job"));
  }

  [Test] public void TheBenchNeedsThePistolTheToolkitAndThePartsToStart()
  {
   var run=new Run();
   Assert.That(run.model.CanBeginAssembly(Grip,Station,out var why),Is.False);Assert.That(why,Is.EqualTo("missing_ingredients"));
   GiveGripParts(run.pack);
   run.hasPistol=false;
   Assert.That(run.model.CanBeginAssembly(Grip,Station,out why),Is.False);Assert.That(why,Is.EqualTo("missing_weapon"));
   run.hasPistol=true;
   Give(run.pack,("field_toolkit",-run.pack.Quantity("field_toolkit")));
   Assert.That(run.model.CanBeginAssembly(Grip,Station,out why),Is.False);Assert.That(why,Is.EqualTo("missing_tool"));
   Assert.That(run.model.CanBeginAssembly("recipe_charge_cell_core",Station,out why),Is.False);Assert.That(why,Is.EqualTo("no_assembly"));
  }

  [Test] public void SaveRoundTripWithAnOpenTicketAndOlderSaves()
  {
   var run=new Run();GiveGripParts(run.pack);
   Assert.That(run.model.BeginAssembly(Grip,Station,out var why),Is.Not.Null,why);
   run.model.AssemblyStageId="s3";run.model.AssemblyStageLabel="Process the parts";
   var json=JsonUtility.ToJson(run.model.Capture());
   var copy=new Run();
   copy.model.Restore(JsonUtility.FromJson<CraftingState>(json));
   var t=copy.model.OpenTicket;
   Assert.That(t,Is.Not.Null);Assert.That(t.resumed);Assert.That(t.recipeId,Is.EqualTo(Grip));Assert.That(t.weaponId,Is.EqualTo(Pistol));Assert.That(t.stationId,Is.EqualTo(Station));
   Assert.That(t.inputs.Sum(s=>s.quantity),Is.EqualTo(8));
   Assert.That(copy.model.AssemblyStageLabel,Is.EqualTo("Process the parts"));Assert.That(copy.model.OnBench(Pistol));
   // the whole save file carries the bench system's blob additively
   var data=new WardSaveData{version=WardSaveData.CurrentVersion,crafting=run.model.Capture(),benchJob="{\"steps\":3}"};
   Assert.That(WardSaveFile.TryParse(WardSaveFile.Serialize(data),out var parsed,out var error),error);
   Assert.That(parsed.benchJob,Is.EqualTo("{\"steps\":3}"));Assert.That(parsed.crafting.bench.recipeId,Is.EqualTo(Grip));
   // completed at Fine, then saved: quality of the fitted grip and the hand-made record survive
   Assert.That(copy.model.CompleteAssembly(Result(CraftQuality.Fine),out why),why);
   Assert.That(copy.model.TryRemove("grip",out why),why);
   var after=JsonUtility.ToJson(copy.model.Capture());
   var third=new Run();third.pack=copy.pack;third.model=new CraftingModel(Data(),City().items,copy.pack,()=>true);third.model.Restore(JsonUtility.FromJson<CraftingState>(after));
   Assert.That(third.model.HandMade(Grip));Assert.That(third.model.OpenTicket,Is.Null);
   Assert.That(third.model.CarriedQuality(GripItem,CraftQuality.Fine),Is.EqualTo(1));
   Assert.That(third.model.TryFit(GripItem,out why),why);Assert.That(third.model.Loadout.Quality("grip"),Is.EqualTo(CraftQuality.Fine));
   var fitted=JsonUtility.ToJson(third.model.Capture());
   var fourth=new CraftingModel(Data(),City().items,copy.pack,()=>true);fourth.Restore(JsonUtility.FromJson<CraftingState>(fitted));
   Assert.That(fourth.Loadout.Quality("grip"),Is.EqualTo(CraftQuality.Fine));Assert.That(fourth.Loadout.Stats.recoil,Is.EqualTo(28).Within(.001f));
  }

  [Test] public void OlderSavesLoadUnchanged()
  {
   // a save from before the bench: a fitted grip with no quality, no hand-made record, no bench job; it had made the grip
   const string old="{\"known\":[\"recipe_grip_stabilised_pistol\"],\"crafted\":[{\"id\":\"recipe_grip_stabilised_pistol\",\"count\":1}],\"crafts\":1,\"weapons\":[{\"weaponId\":\"weapon_scrap_pistol\",\"fitted\":[{\"slot\":\"grip\",\"itemId\":\"grip_stabilised_pistol\"}],\"conditionVersion\":1,\"durability\":90,\"maxDurability\":100,\"repairs\":0}]}";
   var run=new Run();
   var skipped=run.model.Restore(JsonUtility.FromJson<CraftingState>(old));
   Assert.That(skipped,Is.Empty);
   Assert.That(run.model.OpenTicket,Is.Null);Assert.That(run.model.Loadout.Quality("grip"),Is.EqualTo(CraftQuality.Standard));
   Assert.That(run.model.Loadout.Stats.recoil,Is.EqualTo(31).Within(.001f));
   Assert.That(run.model.HandMade(Grip),"an old save that already made the grip keeps its timer");
   // an old save that never made it must build the first one by hand
   var fresh=new Run();fresh.model.Restore(JsonUtility.FromJson<CraftingState>("{\"known\":[\"recipe_grip_stabilised_pistol\"],\"crafts\":0}"));
   Assert.That(fresh.model.NeedsHandMade(Grip));Assert.That(fresh.model.OpenTicket,Is.Null);
   // a bench record naming a recipe this build does not know is dropped and reported
   var odd=new Run();var bad=odd.model.Restore(new CraftingState{handMade=new string[0],bench=new BenchTicketState{recipeId="recipe_gone",weaponId=Pistol}});
   Assert.That(odd.model.OpenTicket,Is.Null);Assert.That(bad,Does.Contain("recipe_gone"));
  }

  [Test] public void CarriedQualityFollowsThePack()
  {
   var run=new Run();
   GiveGripParts(run.pack);run.model.BeginAssembly(Grip,Station,out _);
   run.hasPistol=false; // the part cannot be fitted: it goes to the pack at its quality
   Assert.That(run.model.CompleteAssembly(Result(CraftQuality.Fine),out var why),why);
   Assert.That(run.model.LastAssemblyFitted,Is.False);
   Assert.That(run.pack.Quantity(GripItem),Is.EqualTo(1));Assert.That(run.model.CarriedQuality(GripItem,CraftQuality.Fine),Is.EqualTo(1));
   Give(run.pack,(GripItem,1));
   Assert.That(run.model.CarriedQuality(GripItem,CraftQuality.Standard),Is.EqualTo(1));Assert.That(run.model.BestCarried(GripItem),Is.EqualTo(CraftQuality.Fine));
   // one sold: the recorded quality goes only when the pack has fewer units than recorded
   Give(run.pack,(GripItem,-1));
   Assert.That(run.model.CarriedQuality(GripItem,CraftQuality.Fine),Is.EqualTo(1));Assert.That(run.model.CarriedQuality(GripItem,CraftQuality.Standard),Is.Zero);
   Give(run.pack,(GripItem,-1));
   Assert.That(run.model.CarriedQuality(GripItem,CraftQuality.Fine),Is.Zero);
  }

  [Test] public void QualityScalesEffectsForFittedAndPreviewedMods()
  {
   var data=Data();var weapon=data.weapons.Single(w=>w.id==Pistol);var grip=data.modifiers.Single(m=>m.itemId==GripItem);
   float R(CraftQuality q)=>WeaponLoadout.Compute(weapon,new[]{new KeyValuePair<CraftModifier,CraftQuality>(grip,q)}).recoil;
   Assert.That(R(CraftQuality.Rough),Is.EqualTo(33).Within(.001f));Assert.That(R(CraftQuality.Standard),Is.EqualTo(31).Within(.001f));Assert.That(R(CraftQuality.Fine),Is.EqualTo(28).Within(.001f));
   Assert.That(WeaponLoadout.Compute(weapon,new[]{grip}).recoil,Is.EqualTo(31).Within(.001f),"the old overload is Standard");
   // an effect without per-quality values scales by the modifier's (or the default) scale
   var plain=new CraftModifier{id="m",itemId="x",slot="grip",weaponIds=new[]{Pistol},effects=new[]{new CraftEffect{stat="damage",op="add",value=4}}};
   Assert.That(WeaponLoadout.EffectValue(plain,plain.effects[0],CraftQuality.Rough),Is.EqualTo(3).Within(1e-4));
   Assert.That(WeaponLoadout.EffectValue(plain,plain.effects[0],CraftQuality.Fine),Is.EqualTo(5).Within(1e-4));
   plain.qualityScale=new[]{.5f,1,2};Assert.That(WeaponLoadout.EffectValue(plain,plain.effects[0],CraftQuality.Fine),Is.EqualTo(8).Within(1e-4));
   var run=new Run();
   Assert.That(run.model.Loadout.Preview("grip",GripItem,CraftQuality.Fine).recoil,Is.EqualTo(28).Within(.001f));
  }

  [Test] public void HandlingBareAndGrippedAtEachQuality()
  {
   var run=new Run();
   var bare=run.model.HandlingFor(Pistol);
   var rough=run.model.HandlingFor(Pistol,GripItem,CraftQuality.Rough);var std=run.model.HandlingFor(Pistol,GripItem);var fine=run.model.HandlingFor(Pistol,GripItem,CraftQuality.Fine);
   Assert.That(bare.kick,Is.EqualTo(38*WeaponHandlingRules.KickDegreesPerPoint).Within(1e-4),"the bare pistol's kick is today's");
   Assert.That(bare.sway,Is.EqualTo(1.2f).Within(1e-4));Assert.That(bare.recovery,Is.EqualTo(.34f).Within(1e-4));
   foreach(var (h,name) in new[]{(rough,"Rough"),(std,"Standard"),(fine,"Fine")})
   {
    Assert.That(h.kick,Is.LessThan(bare.kick),name);Assert.That(h.sway,Is.LessThan(bare.sway),name);Assert.That(h.sideStep,Is.LessThan(bare.sideStep),name);
    Assert.That(h.recovery,Is.LessThan(bare.recovery),name);Assert.That(h.scatterGrowth,Is.LessThan(bare.scatterGrowth),name);
   }
   Assert.That(rough.sway,Is.GreaterThan(std.sway));Assert.That(std.sway,Is.GreaterThan(fine.sway));
   Assert.That(rough.kick,Is.GreaterThan(std.kick));Assert.That(std.kick,Is.GreaterThan(fine.kick));
   // Standard removes more than half of the bare pistol's roughness (sway, side kick, scatter growth; recovery back to the default)
   Assert.That(std.sway,Is.LessThan(bare.sway/2));Assert.That(std.sideStep,Is.LessThan(bare.sideStep/2));Assert.That(std.scatterGrowth,Is.LessThan(bare.scatterGrowth/2));
   Assert.That(std.recovery,Is.LessThanOrEqualTo(WeaponHandlingRules.DefaultRecoverySeconds+1e-4f));
   Assert.That(WeaponHandlingRules.OvershootFraction(bare.recovery),Is.GreaterThan(0),"the bare pistol overshoots once");
   Assert.That(WeaponHandlingRules.OvershootFraction(std.recovery),Is.Zero,"the gripped one settles without overshoot");
   // fitted: HandlingFor with no mod is the loadout as it is; HandlingWithout strips the slot
   Give(run.pack,(GripItem,1));Assert.That(run.model.TryFit(GripItem,out var why),why);
   Assert.That(run.model.HandlingFor(Pistol).sway,Is.EqualTo(std.sway).Within(1e-4));
   Assert.That(run.model.HandlingWithout(Pistol,"grip").sway,Is.EqualTo(bare.sway).Within(1e-4));
   // the rifle has no handling roughness
   var rifle=run.model.HandlingFor("weapon_field_rifle");
   Assert.That(rifle.sway,Is.Zero);Assert.That(rifle.sideStep,Is.Zero);Assert.That(rifle.scatterGrowth,Is.Zero);Assert.That(rifle.recovery,Is.EqualTo(WeaponHandlingRules.DefaultRecoverySeconds));
  }

  [Test] public void ScatterGrowsUnderRapidFireAndTheFirstShotIsUnchanged()
  {
   Assert.That(WeaponFeel.ScatterScale(0),Is.EqualTo(1),"no heat: today's cone");
   // five shots at the pistol's fire interval: the cone of the fifth shot is the heat before it, decayed
   float Fifth(float growth){float h=0;for(int i=0;i<4;i++)h=WeaponFeel.HeatAfterShot(h,.28f,growth);return WeaponFeel.ScatterScale(WeaponFeel.Decay(h,.28f));}
   float bare=Fifth(.35f),std=Fifth(.12f);
   Assert.That(bare,Is.GreaterThan(1.4f),"bare pistol at its fire rate");
   Assert.That(std,Is.LessThan(bare));Assert.That(std-1,Is.LessThan((bare-1)/2),"the grip halves the growth");
   Assert.That(WeaponFeel.Decay(1,10),Is.LessThan(.01f),"a pause cools it");
   Assert.That(WeaponFeel.ScatterScale(100),Is.LessThanOrEqualTo(1+WeaponFeel.MaxHeat+1e-4f),"capped");
  }

  [Test] public void OrderStagesWithAndWithoutABenchJob()
  {
   var run=new Run();var orders=new FieldOrderProgress(Orders());orders.Begin();orders.NoteReport("npc_brann");
   GiveGripParts(run.pack);
   Assert.That(orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Fabricate));
   Assert.That(orders.BenchRoute(run.model));
   Assert.That(orders.Objective(run.model,run.pack),Does.Contain("Build and fit"));
   Assert.That(run.model.BeginAssembly(Grip,Station,out var why),Is.Not.Null,why);
   run.model.AssemblyStageLabel="Strip the pistol";
   Assert.That(orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Fabricate),"inputs on the bench: still Fabricate, not Gather");
   Assert.That(orders.Objective(run.model,run.pack),Does.Contain("Strip the pistol"));
   Assert.That(run.model.CompleteAssembly(Result(CraftQuality.Standard),out why),why);
   Assert.That(orders.NoteBenchBuilt(Grip,run.model));Assert.That(orders.Benched("order_steady_hands"));
   Assert.That(orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.TestFire),"fabricate and fit in one visit: Fit is never seen");
   // a bench-built grip's test fire is a judged string of shots (one shot for the timer route, as before)
   int n=Orders().orders[0].testFireShots;Assert.That(n,Is.GreaterThanOrEqualTo(3));
   for(int i=0;i<n-1;i++){Assert.That(orders.NoteShot(run.model,Vector3.forward,out var v),Is.False);Assert.That(v,Is.EqualTo(TestFireVerdict.Counting));}
   Assert.That(orders.NoteShot(run.model,Vector3.forward,out var tight));Assert.That(tight,Is.EqualTo(TestFireVerdict.Tight));
   Assert.That(orders.Advance(run.model,_=>false).Single().id,Is.EqualTo("order_steady_hands"));
   // the timer route keeps Fit. 21 Nov 2026 (no Auto-assemble): a hand-made record no longer opens the timer; only a world with
   // no bench system for the recipe does (the game is never stuck)
   var made=new Run();made.model.MarkHandMade(Grip);var o1=new FieldOrderProgress(Orders());o1.Begin();Assert.That(o1.BenchRoute(made.model),"made by hand before: still the bench");
   var timed=new Run();timed.model.HandsOnAvailable=_=>false;var o2=new FieldOrderProgress(Orders());o2.Begin();o2.NoteReport("npc_brann");
   GiveGripParts(timed.pack);Assert.That(o2.BenchRoute(timed.model),Is.False);
   Assert.That(timed.model.TryCraft(Grip,Station,out why),why);
   Assert.That(o2.Stage(timed.model,timed.pack),Is.EqualTo(OrderStage.Fit));
  }

  [Test] public void APoorGroupAsksForOneMoreStringAndBenchedSurvivesTheSave()
  {
   var run=new Run();var orders=new FieldOrderProgress(Orders());orders.Begin();
   var o=Orders().orders[0];int n=o.testFireShots;
   Give(run.pack,(GripItem,1));Assert.That(run.model.TryFit(GripItem,out var why),why);
   Assert.That(orders.NoteBenchBuilt(Grip,run.model));Assert.That(orders.NoteBenchBuilt(Grip,run.model),Is.False,"once");
   var copy=new FieldOrderProgress(Orders());copy.Restore(JsonUtility.FromJson<FieldOrderState>(JsonUtility.ToJson(orders.Capture())));
   Assert.That(copy.Benched(o.id));
   Vector3 Dir(float deg)=>Quaternion.Euler(0,deg,0)*Vector3.forward;
   float wide=o.testFireTightDegrees+2;
   TestFireVerdict v=TestFireVerdict.None;bool done=false;
   for(int i=0;i<n;i++)done=copy.NoteShot(run.model,Dir(i==0?0:wide),out v);
   Assert.That(done,Is.False);Assert.That(v,Is.EqualTo(TestFireVerdict.Again));Assert.That(copy.LastGroupDegrees,Is.EqualTo(wide).Within(.01f));
   for(int i=0;i<n;i++)done=copy.NoteShot(run.model,Dir(i==0?0:wide),out v);
   Assert.That(done,"the second string completes the test fire whatever the group");Assert.That(v,Is.EqualTo(TestFireVerdict.Poor));
   // an order whose grip was not built at the bench keeps the one-shot test fire
   var timed=new FieldOrderProgress(Orders());timed.Begin();
   Assert.That(timed.NoteShot(run.model,Vector3.forward,out v));Assert.That(v,Is.EqualTo(TestFireVerdict.None));
   foreach(var line in new[]{o.testFireLine,o.testFireTightLine,o.testFirePoorLine,o.completeLine})Assert.That(line,Is.Not.Empty);
  }

  [Test] public void BenchAndHandMadeDialogueConditions()
  {
   var go=new GameObject("quest");go.SetActive(false);try
   {
    var session=go.AddComponent<GameSession>();var crafting=go.AddComponent<CraftingSession>();
    var pack=new ShopModel(City().items);var model=new CraftingModel(Data(),City().items,pack,()=>true);model.Unlock(Grip);
    Set(crafting,"Model",model);
    IQuestState q=session;
    Assert.That(QuestConditions.Evaluate("bench",q),Is.False);Assert.That(QuestConditions.Evaluate("!handmade:"+Grip,q));
    GiveGripParts(pack);Assert.That(model.BeginAssembly(Grip,Station,out var why),Is.Not.Null,why);
    Assert.That(QuestConditions.Evaluate("bench",q));
    Assert.That(model.CompleteAssembly(Result(CraftQuality.Standard),out why),why);
    Assert.That(QuestConditions.Evaluate("!bench, handmade:"+Grip,q));
    Assert.That(QuestConditions.Problems("bench, handmade:x, !handmade:"+Grip),Is.Empty);Assert.That(QuestConditions.Problems("handmade"),Is.Not.Empty);
   }
   finally{Object.DestroyImmediate(go);}
  }

  [Test] public void TheBenchBuiltGripIsTestedFromTheRangeFiringLine()
  {
   var o=Orders().orders[0];
   // the data: the three firing bays of the Warden range (checkpoint_firingline -66.2, 7.6 is bay 1)
   Assert.That(o.testFireRadius,Is.InRange(3.5f,6f));
   Assert.That(new Vector2(o.testFireAt.x-(-66.2f),o.testFireAt.z-7.6f).magnitude,Is.LessThan(2.5f));
   Assert.That(FieldOrderProgress.AtFiringLine(o,new Vector3(-66.2f,-1.5f,7.6f)),"bay 1");
   Assert.That(FieldOrderProgress.AtFiringLine(o,new Vector3(-64.75f,-1.5f,10.45f)),"bay 3");
   Assert.That(FieldOrderProgress.AtFiringLine(o,new Vector3(-78f,-1.5f,11f)),Is.False,"at the plates");
   Assert.That(o.testFireBrief,Does.Contain("firing line"));Assert.That(o.testFireStep,Does.Contain("firing line"));Assert.That(o.testFireLabel,Is.Not.Empty);
   var run=new Run();var orders=new FieldOrderProgress(Orders());orders.Begin();
   Give(run.pack,(GripItem,1));Assert.That(run.model.TryFit(GripItem,out var why),why);
   Assert.That(orders.RangeTest(),Is.False,"a timer-made grip: one shot anywhere, as before");
   Assert.That(orders.NoteBenchBuilt(Grip,run.model));Assert.That(orders.RangeTest());
   Assert.That(orders.Objective(run.model,run.pack),Does.Contain("Warden range"));
   var line=o.testFireAt;var away=new Vector3(-90,-1.5f,0);
   Assert.That(orders.NoteShot(run.model,Vector3.forward,line,out var v),Is.False);Assert.That(v,Is.EqualTo(TestFireVerdict.Counting));
   Assert.That(orders.NoteShot(run.model,Vector3.forward,away,out v),Is.False);Assert.That(v,Is.EqualTo(TestFireVerdict.OffRange));
   Assert.That(orders.TestShots,Is.Zero,"a shot from elsewhere starts the string again");
   for(int i=0;i<o.testFireShots-1;i++){Assert.That(orders.NoteShot(run.model,Vector3.forward,line,out v),Is.False);Assert.That(v,Is.EqualTo(TestFireVerdict.Counting));}
   Assert.That(orders.NoteShot(run.model,Vector3.forward,line,out v));Assert.That(v,Is.EqualTo(TestFireVerdict.Tight));
   Assert.That(orders.RangeTest(),Is.False,"done");
  }

  [Test] public void TheWeaponOnTheBenchCannotBeUnequippedSwappedOrMoved()
  {
   var pack=new ShopModel(City().items);var character=new CharacterModel(Resources.Load<CharacterCatalog>("CharacterCatalog"),pack);
   Assert.That(character.TryGrantEquipped("scrap_pistol","secondary",out var why),why);
   var model=new CraftingModel(Data(),City().items,pack,()=>false,character:character);model.Unlock(Grip);
   character.SlotLocked=model.SlotLockFor(character);
   Assert.That(character.SlotLocked("secondary"),Is.Null,"free before the job");
   GiveGripParts(pack);Assert.That(model.BeginAssembly(Grip,Station,out why),Is.Not.Null,why);
   Assert.That(model.BenchStateFor(Pistol),Is.EqualTo("On Brann's bench"));
   Assert.That(character.TryUnequip("secondary",out why),Is.False);Assert.That(why,Does.Contain("on the bench"));
   Assert.That(character.TryMove("secondary","primary",out why),Is.False);Assert.That(why,Does.Contain("on the bench"));
   Assert.That(character.TryEquip("scrap_pistol","secondary",out why),Is.False,"no swap into its slot");Assert.That(why,Does.Contain("on the bench"));
   Assert.That(character.Equipped("secondary"),Is.EqualTo("scrap_pistol"));
   Assert.That(model.AbandonAssembly(null,out why),why);
   Assert.That(model.BenchStateFor(Pistol),Is.Null);Assert.That(character.SlotLocked("secondary"),Is.Null);
   if(pack.Quantity("scrap_pistol")>0)Give(pack,("scrap_pistol",-pack.Quantity("scrap_pistol"))); // a pistol stacks one to a pack
   Assert.That(character.TryUnequip("secondary",out why),why);
  }

  static CraftingStationMarker Station_(GameObject parent){var go=new GameObject("bench");go.transform.SetParent(parent.transform);var m=go.AddComponent<CraftingStationMarker>();m.stationId=Station;return m;}

  [Test] public void NoOpenerAndNoOpenAssemblyMeansTheTimerMayMakeIt()
  {
   using var rig=new Rig();rig.model.HandsOnAvailable=rig.crafting.BenchPresent;
   rig.crafting.OpenAssemblyFound=()=>false;rig.crafting.AssemblyRecipeFound=_=>true;
   LogAssert.Expect(LogType.Log,new Regex("no AssemblyOpener and no GameSession.OpenAssembly"));
   Assert.That(rig.crafting.BenchPresent(Grip),Is.False);
   Assert.That(rig.model.NeedsHandMade(Grip),Is.False);
   GiveGripParts(rig.pack);Assert.That(rig.model.TryCraft(Grip,Station,out var why),why+": the timer is allowed");
   Assert.That(rig.crafting.UseStation(Station_(rig.go)),Is.False,"the station opens the Fabricator");
  }

  [Test] public void AMissingAssemblyRecipeMeansTheTimerMayMakeIt()
  {
   using var rig=new Rig();rig.model.HandsOnAvailable=rig.crafting.BenchPresent;
   rig.crafting.OpenAssemblyFound=()=>true;rig.crafting.AssemblyRecipeFound=_=>false;
   LogAssert.Expect(LogType.Log,new Regex("no AssemblyRecipe 'assembly_grip_stabilised_pistol'"));
   Assert.That(rig.crafting.BenchPresent(Grip),Is.False);Assert.That(rig.model.NeedsHandMade(Grip),Is.False);
   GiveGripParts(rig.pack);
   // a job left open from a save with a bench is returned when the bench is gone, so nothing is stuck
   rig.model.HandsOnAvailable=null;Assert.That(rig.model.BeginAssembly(Grip,Station,out var why),Is.Not.Null,why);rig.model.HandsOnAvailable=rig.crafting.BenchPresent;
   Assert.That(rig.crafting.UseStation(Station_(rig.go)),Is.False);
   Assert.That(rig.model.OpenTicket,Is.Null);Assert.That(rig.pack.Quantity("scrap_alloy"),Is.EqualTo(2));
   Assert.That(rig.model.TryCraft(Grip,Station,out why),why);
  }

  [Test] public void AnOpenerWithoutTheRecipeAssetMeansTheTimerMayMakeIt()
  {
   using var rig=new Rig();rig.model.HandsOnAvailable=rig.crafting.BenchPresent;
   bool asked=false;rig.crafting.AssemblyOpener=(s,r)=>asked=true;rig.crafting.AssemblyRecipeFound=_=>false;
   Assert.That(rig.crafting.BenchPresent(Grip),Is.False);Assert.That(rig.model.NeedsHandMade(Grip),Is.False);
   GiveGripParts(rig.pack);
   Assert.That(rig.crafting.OpenAssembly(null,Grip),Is.False);Assert.That(asked,Is.False,"the bench is not asked to open a job it cannot run");
   Assert.That(rig.model.TryCraft(Grip,Station,out var why),why);
   // with the bench present, the hand-made gate is back
   var rig2=new Rig();try
   {
    rig2.model.HandsOnAvailable=rig2.crafting.BenchPresent;rig2.crafting.AssemblyOpener=(s,r)=>true;rig2.crafting.AssemblyRecipeFound=_=>true;
    Assert.That(rig2.crafting.BenchPresent(Grip));Assert.That(rig2.model.NeedsHandMade(Grip));
    GiveGripParts(rig2.pack);Assert.That(rig2.model.TryCraft(Grip,Station,out why),Is.False);Assert.That(why,Is.EqualTo("hand_made_first"));
   }
   finally{rig2.Dispose();}
  }

  [Test] public void SessionRefusesTheWeaponWhileOnTheBenchAndReportsStages()
  {
   using var rig=new Rig();GiveGripParts(rig.pack);
   int changed=0;rig.crafting.AssemblyChanged+=()=>changed++;
   var ticket=rig.crafting.BeginAssembly(Grip,out var why);
   Assert.That(ticket,Is.Not.Null,why);Assert.That(changed,Is.EqualTo(1));
   Assert.That(rig.crafting.OpenTicket,Is.SameAs(ticket));Assert.That(rig.crafting.HasAssembly(Grip));Assert.That(rig.crafting.HandMade(Grip),Is.False);
   rig.crafting.ReportAssemblyStage("s1","Strip the pistol");rig.crafting.ReportAssemblyStage("s1","Strip the pistol");
   Assert.That(changed,Is.EqualTo(2),"a repeated stage report is not a change");
   rig.crafting.AssemblyBlob="{}";Assert.That(changed,Is.EqualTo(3));
   Give(rig.pack,("barrel_bored_alloy",1));
   Assert.That(rig.crafting.Fit(Pistol,"barrel_bored_alloy",out why),Is.False);Assert.That(why,Is.EqualTo("on_bench"));
   Assert.That(rig.session.notice,Does.Contain("on the bench"));
   Assert.That(rig.crafting.Overhaul(Pistol,out why),Is.False);
   Assert.That(rig.crafting.HandlingFor(Pistol).sway,Is.EqualTo(1.2f).Within(1e-4));
   Assert.That(rig.crafting.CompleteAssembly(Result(CraftQuality.Standard,Filament),out why),why);
   Assert.That(changed,Is.EqualTo(4));Assert.That(rig.crafting.AssemblyBlob,Is.Null);
   Assert.That(rig.session.notice,Does.Contain("Stabilised Pistol Grip · Standard"));Assert.That(rig.session.notice,Does.Contain("Copper Filament"));
   Assert.That(rig.combat.Stats.recoil,Is.EqualTo(31).Within(.001f));Assert.That(rig.combat.Stats.sway,Is.EqualTo(.45f).Within(1e-4));
  }

  [Test] public void FabricatorOffersOnlyBuildByHandForAHandsOnSchematic()
  {
   using var rig=new Rig();GiveGripParts(rig.pack);
   rig.crafting.AssemblyRecipeFound=_=>true; // the bench system is there (no scene in Edit Mode)
   var root=Hud();var panel=new FabricatorPanel(root,rig.session,rig.crafting);
   panel.Opened();panel.Select(Grip);panel.Refresh();
   var craft=root.Q<Button>("fabricator-craft");var build=root.Q<Button>("fabricator-build");
   Assert.That(build,Is.Not.Null);Assert.That(build.style.display.value,Is.EqualTo(DisplayStyle.Flex));Assert.That(build.enabledSelf);Assert.That(build.text,Is.EqualTo("Build by hand"));
   Assert.That(craft.enabledSelf,Is.False,"no timer for a hands-on schematic");Assert.That(craft.style.display.value,Is.EqualTo(DisplayStyle.None));
   Assert.That(root.Q<Label>("fab-reason").text,Does.Contain("by hand"));
   Assert.That(panel.ActionFocus,Is.SameAs(build));
   // a schematic without a job: no button, Fabricate as before
   panel.Select("recipe_charge_cell_core");panel.Refresh();
   Assert.That(build.style.display.value,Is.EqualTo(DisplayStyle.None));Assert.That(build.focusable,Is.False);
   Assert.That(craft.style.display.value,Is.EqualTo(DisplayStyle.Flex),"a schematic without a job keeps its timed Fabricate");
   // made by hand once: still only Build by hand, no timer button (Carl, 21 Nov: "no auto assemble for anything ever")
   rig.model.MarkHandMade(Grip);panel.Select(Grip);panel.Refresh();
   Assert.That(craft.style.display.value,Is.EqualTo(DisplayStyle.None));Assert.That(craft.enabledSelf,Is.False);Assert.That(build.text,Is.EqualTo("Build by hand"));
   Assert.That(root.Q<Label>("fab-reason").text,Does.Not.Contain("Auto"));
   // with no bench system in the scene, Build by hand says so instead of failing silently
   rig.crafting.AssemblyOpener=(s,r)=>false;
   panel.BuildByHand();Assert.That(rig.session.notice,Does.Contain("not set up for hand work"));
   bool opened=false;rig.crafting.AssemblyOpener=(s,r)=>opened=r==Grip;
   panel.BuildByHand();Assert.That(opened,"Build by hand asks the bench system to open the grip's job");
  }
 }
}
