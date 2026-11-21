using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// Hands-on bench jobs, crafted quality and weapon handling (Steady Hands bench, 20 Nov 2026). CONTRACT.md section B.
 /// A bench job reserves its inputs by taking them out of the pack (and locker) onto the bench, so they cannot be sold,
 /// stored or used by another craft; the weapon it works on stays equipped but cannot be drawn, fitted, repaired or
 /// overhauled until the job is completed or abandoned.
 public sealed partial class CraftingModel
 {
  readonly HashSet<string> handMade=new HashSet<string>();
  /// Recipes whose bench job has been finished by hand at the bench (not by MarkHandMade, not by an older save's timer craft).
  /// Brann's guidance (BenchTutor) runs until the player has finished one. tutor agent, 21 Nov 2026; saved additively.
  readonly HashSet<string> benchFinished=new HashSet<string>();
  public bool FinishedAtBench(string recipeId)=>recipeId!=null&&benchFinished.Contains(recipeId);
  public bool FinishedAnyAtBench=>benchFinished.Count>0;
  /// Carried units of a mod that are not Standard: item id to {rough, fine}. Standard units are the rest of the pack's count.
  readonly Dictionary<string,int[]> carriedQuality=new Dictionary<string,int[]>();
  /// The unfinished bench job, also after loading a save; null = none.
  public AssemblyTicket OpenTicket {get;private set;}
  /// Opaque JSON of the bench job (owned by the bench system); saved as WardSaveData.benchJob.
  public string AssemblyBlob {get;set;}
  /// Last stage the bench reported (journal step progress and the Field Notes line).
  public string AssemblyStageId {get;set;}
  public string AssemblyStageLabel {get;set;}
  /// What the last completed bench job reported, or null.
  public AssemblyResult LastAssembly {get;private set;}
  /// Where the last completed job's part went: true = fitted to the weapon, false = into the pack.
  public bool LastAssemblyFitted {get;private set;}
  public IReadOnlyCollection<string> HandMadeRecipes=>handMade;
  public bool HasAssembly(string recipeId)=>!string.IsNullOrEmpty(Recipe(recipeId)?.assembly);
  public bool HandMade(string recipeId)=>recipeId!=null&&handMade.Contains(recipeId);
  /// Records a recipe as made by hand without the bench (QA: dev.craft.handmade, and test fixtures that use the timer).
  public bool MarkHandMade(string recipeId){if(!HasAssembly(recipeId)||!handMade.Add(recipeId))return false;Changed?.Invoke();return true;}
  /// The recipe has a bench job: it is made by hand at the bench, every time, and the timer is refused for it (Carl, 21 Nov
  /// 2026: "no auto assemble for anything ever"; before that, one hand-made job opened Auto-assemble on the timer). Only when
  /// the bench system is not there for it (HandsOnAvailable says no) is the timer allowed, so the game is never stuck.
  public bool NeedsHandMade(string recipeId)=>HasAssembly(recipeId)&&(HandsOnAvailable?.Invoke(recipeId)??true);
  /// Whether the hands-on bench can run this recipe's job here (CraftingSession sets it from the scene; null = yes).
  public Func<string,bool> HandsOnAvailable {get;set;}
  /// The weapon is on the bench (an open job is working on it).
  public bool OnBench(string weaponId)=>OpenTicket!=null&&weaponId!=null&&OpenTicket.weaponId==weaponId;
  /// The job for this recipe is open on the bench.
  public bool OnBenchRecipe(string recipeId)=>OpenTicket!=null&&OpenTicket.recipeId==recipeId;
  /// The weapon a recipe's job works on: the carried weapon its output mod fits (the default sidearm first), or null.
  public string BenchWeaponFor(string recipeId)
  {
   var recipe=Recipe(recipeId);if(recipe==null)return null;
   if(!string.IsNullOrEmpty(recipe.requiresWeaponId))return HasWeapon(recipe.requiresWeaponId)?recipe.requiresWeaponId:null;
   var candidates=new List<WeaponLoadout>{Loadout};candidates.AddRange(loadouts.Values.Where(l=>l!=Loadout));
   foreach(var loadout in candidates)
   {
    var mod=loadout.Modifier(recipe.outputItemId);
    if(mod!=null&&loadout.Accepts(mod)&&HasWeapon(loadout.WeaponId))return loadout.WeaponId;
   }
   return null;
  }
  /// The timer may make this recipe (it has no bench job, or no bench system is there for it). CanCraft is unchanged so order
  /// stages still see "has everything".
  public bool CanCraftOnTimer(string recipeId,string stationId,out string reason)
  {
   if(OnBenchRecipe(recipeId)){reason="on_bench";return false;}
   if(!CanCraft(recipeId,stationId,out reason))return false;
   if(NeedsHandMade(recipeId)){reason="hand_made_first";return false;}
   return true;
  }
  public bool CanBeginAssembly(string recipeId,string stationId,out string reason)
  {
   if(OpenTicket!=null){if(OpenTicket.recipeId==recipeId){reason="resumed";return true;}reason="bench_busy";return false;}
   return ValidateAssembly(recipeId,stationId,out _,out _,out reason);
  }
  bool ValidateAssembly(string recipeId,string stationId,out List<KeyValuePair<string,int>> used,out string weaponId,out string reason)
  {
   used=null;weaponId=null;
   if(!HasAssembly(recipeId)){reason=Recipe(recipeId)==null?"unknown_recipe":"no_assembly";return false;}
   if(Job!=null||RepairJob!=null){reason="busy";return false;}
   if(!ValidateCraft(recipeId,stationId,out used,out reason))return false;
   weaponId=BenchWeaponFor(recipeId);
   if(weaponId==null){reason="missing_weapon";return false;}
   reason="ok";return true;
  }
  /// Reserves the inputs (pack first, then the locker) onto the bench and takes the weapon there. With a job already
  /// open for this recipe it is returned (resumed); another recipe's open job refuses (bench_busy).
  public AssemblyTicket BeginAssembly(string recipeId,string stationId,out string reason)
  {
   if(OpenTicket!=null)
   {
    if(OpenTicket.recipeId==recipeId){OpenTicket.resumed=true;reason="resumed";return OpenTicket;}
    reason="bench_busy";return null;
   }
   if(!ValidateAssembly(recipeId,stationId,out var used,out var weaponId,out reason))return null;
   var fromReserve=used.Select(x=>new KeyValuePair<string,int>(x.Key,Math.Max(0,x.Value-pack.Quantity(x.Key)))).Where(x=>x.Value>0).ToList();
   var delta=used.Select(x=>new KeyValuePair<string,int>(x.Key,-Math.Min(x.Value,pack.Quantity(x.Key)))).Where(x=>x.Value!=0).ToList();
   if(fromReserve.Count>0&&(!ReserveActive||fromReserve.Any(x=>Reserve.Quantity(x.Key)<x.Value))){reason="missing_ingredients";return null;}
   if(delta.Count>0&&!pack.TryApply(delta,0,out reason))return null;
   foreach(var x in fromReserve)Reserve.Consume(x.Key,x.Value);
   foreach(var x in used)ReconcileCarried(x.Key);
   OpenTicket=new AssemblyTicket{recipeId=recipeId,stationId=stationId,weaponId=weaponId,inputs=used.Where(x=>x.Value>0).OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>new ItemStack(x.Key,x.Value)).ToArray(),resumed=false};
   AssemblyBlob=null;AssemblyStageId=null;AssemblyStageLabel=null;
   reason="ok";Changed?.Invoke();return OpenTicket;
  }
  /// Finishes the open job: the reserved inputs are used, the part is made at the reported quality and fitted to the
  /// job's weapon in the same pack transaction (whatever filled that slot returns to the pack), by-products go to the pack,
  /// experience and skill use are awarded as for a timed craft, and the recipe counts as made by hand (unlocking the timer).
  /// When the part cannot be fitted (requirements, a slot the weapon lost) it goes into the pack instead.
  public bool CompleteAssembly(AssemblyResult result,out string reason)
  {
   var ticket=OpenTicket;
   if(ticket==null){reason="no_job";return false;}
   if(result==null){reason="no_result";return false;}
   if(!string.IsNullOrEmpty(result.recipeId)&&result.recipeId!=ticket.recipeId){reason="wrong_recipe";return false;}
   var recipe=Recipe(ticket.recipeId);
   if(recipe==null||Item(recipe.outputItemId)==null){reason="unknown_recipe";return false;}
   if(Crafts==int.MaxValue||CraftCount(recipe.id)==int.MaxValue){reason="overflow";return false;}
   var q=(CraftQuality)Math.Max(0,Math.Min(2,(int)result.quality));
   var byproducts=(result.byproducts??Array.Empty<ItemStack>()).Where(s=>s!=null&&s.quantity>0&&pack.Spec(s.itemId)!=null).ToList();
   var loadout=GetLoadout(ticket.weaponId);
   var mod=loadout?.Modifier(recipe.outputItemId);
   bool fit=mod!=null&&loadout.Accepts(mod)&&Meets(mod.requirements)&&HasWeapon(loadout.WeaponId)&&recipe.outputQuantity==1;
   string previous=fit?loadout.Fitted(mod.slot):null;var previousQ=fit?loadout.Quality(mod.slot):CraftQuality.Standard;
   var delta=new List<KeyValuePair<string,int>>();
   if(fit){if(previous!=null)delta.Add(new KeyValuePair<string,int>(previous,1));}
   else delta.Add(new KeyValuePair<string,int>(recipe.outputItemId,recipe.outputQuantity));
   var withBy=delta.Concat(byproducts.Select(s=>new KeyValuePair<string,int>(s.itemId,s.quantity))).ToList();
   float attachment=fit?Weight(recipe.outputItemId)-Weight(previous):0;
   bool Apply(List<KeyValuePair<string,int>> d,out string why)=>fit&&character!=null?character.TryTransferAttachment(d,attachment,out why):pack.TryApply(d,0,out why);
   bool byGiven=true;
   if(!Apply(withBy,out reason))
   {
    // a pack too full for the by-products still takes the part; the by-products are reported as left on the bench
    if(byproducts.Count==0||!Apply(delta,out reason))return false;
    byGiven=false;
   }
   if(fit)
   {
    loadout.Set(mod.slot,recipe.outputItemId,q);
    if(previous!=null)AddCarried(previous,previousQ,1);
   }
   else AddCarried(recipe.outputItemId,q,recipe.outputQuantity);
   int before=CraftCount(recipe.id);
   Crafts++;crafted[recipe.id]=before+1;
   handMade.Add(recipe.id);benchFinished.Add(recipe.id);
   Award(recipe,before);
   LastAssembly=new AssemblyResult{recipeId=recipe.id,quality=q,score=result.score,faults=result.faults,seconds=result.seconds,byproducts=byGiven?byproducts.ToArray():Array.Empty<ItemStack>()};
   LastAssemblyFitted=fit;
   OpenTicket=null;AssemblyBlob=null;AssemblyStageId=null;AssemblyStageLabel=null;
   reason=byGiven?"ok":"byproducts_left";Changed?.Invoke();return true;
  }
  /// Gives up the open job at the bench: the weapon is free again and every reserved input goes back to the pack except
  /// spentInputs (one entry per unit used up: cut or fused parts). Refused (nothing changes) when the pack cannot take them.
  public bool AbandonAssembly(string[] spentInputs,out string reason)
  {
   var ticket=OpenTicket;
   if(ticket==null){reason="no_job";return false;}
   var back=(ticket.inputs??Array.Empty<ItemStack>()).Where(s=>s!=null&&s.quantity>0).ToDictionary(s=>s.itemId,s=>s.quantity);
   foreach(var id in spentInputs??Array.Empty<string>())if(id!=null&&back.TryGetValue(id,out int n))back[id]=n-1;
   var delta=back.Where(x=>x.Value>0&&pack.Spec(x.Key)!=null).Select(x=>new KeyValuePair<string,int>(x.Key,x.Value)).ToList();
   if(delta.Count>0&&!pack.TryApply(delta,0,out reason))return false;
   OpenTicket=null;AssemblyBlob=null;AssemblyStageId=null;AssemblyStageLabel=null;
   reason="ok";Changed?.Invoke();return true;
  }
  /// CharacterModel.SlotLocked for this model: the equipment slot holding the weapon on the bench is locked, with the same
  /// notice as the draw block.
  public Func<string,string> SlotLockFor(CharacterModel character)
   =>slot=>{
    if(OpenTicket==null||character==null)return null;
    var weapon=FindWeapon(character.Equipped(slot));
    return weapon!=null&&OnBench(weapon.id)?CraftingText.ConditionReason("on_bench",this,GetLoadout(weapon.id)):null;
   };
  /// Where the weapon is, for the loadout panel: "On Brann's bench" while a job has it, else null.
  public string BenchStateFor(string weaponId)=>OnBench(weaponId)?CraftingText.OnBenchLabel:null;
  // ---- Developer operations (dev.craft.*, QA captures) -----------------------------------------------------------------
  /// Grants one mod at quality q and fits it (whatever filled the slot goes to the pack). No bench, inputs or tools.
  public bool DevFit(string weaponId,string itemId,CraftQuality q,out string reason)
  {
   var loadout=GetLoadout(weaponId);var mod=loadout?.Modifier(itemId);
   if(loadout==null){reason="missing_weapon";return false;}
   if(mod==null||!loadout.Accepts(mod)){reason="wrong_slot";return false;}
   if(OnBench(weaponId)){reason="on_bench";return false;}
   if(!pack.TryApply(new[]{new KeyValuePair<string,int>(itemId,1)},0,out reason))return false;
   AddCarried(itemId,q,1);
   var previous=loadout.Fitted(mod.slot);var previousQ=loadout.Quality(mod.slot);
   var delta=new List<KeyValuePair<string,int>>{new KeyValuePair<string,int>(itemId,-1)};
   if(previous!=null)delta.Add(new KeyValuePair<string,int>(previous,1));
   if(!pack.TryApply(delta,0,out reason)){pack.TryApply(new[]{new KeyValuePair<string,int>(itemId,-1)},0,out _);ReconcileCarried(itemId);return false;}
   TakeCarried(itemId,q);ReconcileCarried(itemId);
   loadout.Set(mod.slot,itemId,q);
   if(previous!=null)AddCarried(previous,previousQ,1);
   reason="ok";Changed?.Invoke();return true;
  }
  /// Empties a slot and discards its mod: the bare weapon for a before/after capture.
  public bool DevStrip(string weaponId,string slot,out string reason)
  {
   var loadout=GetLoadout(weaponId);
   if(loadout==null){reason="missing_weapon";return false;}
   if(!loadout.HasSlot(slot)){reason="wrong_slot";return false;}
   if(OnBench(weaponId)){reason="on_bench";return false;}
   loadout.Set(slot,null);reason="ok";Changed?.Invoke();return true;
  }
  // ---- Crafted quality of carried mods ----------------------------------------------------------------------------
  /// Carried units of an item at a quality (Standard = all units not recorded as Rough or Fine).
  public int CarriedQuality(string itemId,CraftQuality q)
  {
   ReconcileCarried(itemId);
   int total=pack.Quantity(itemId);
   if(!carriedQuality.TryGetValue(itemId??"",out var c))return q==CraftQuality.Standard?total:0;
   return q==CraftQuality.Rough?c[0]:q==CraftQuality.Fine?c[1]:Math.Max(0,total-c[0]-c[1]);
  }
  /// The quality a fit takes from the pack: the best carried unit.
  public CraftQuality BestCarried(string itemId)
   =>CarriedQuality(itemId,CraftQuality.Fine)>0?CraftQuality.Fine:CarriedQuality(itemId,CraftQuality.Standard)>0?CraftQuality.Standard:CarriedQuality(itemId,CraftQuality.Rough)>0?CraftQuality.Rough:CraftQuality.Standard;
  /// Records n carried units (already in the pack) as made at quality q.
  void AddCarried(string itemId,CraftQuality q,int n)
  {
   if(itemId==null||n<=0||q==CraftQuality.Standard){ReconcileCarried(itemId);return;}
   if(!carriedQuality.TryGetValue(itemId,out var c))carriedQuality[itemId]=c=new int[2];
   c[q==CraftQuality.Rough?0:1]+=n;
   ReconcileCarried(itemId);
  }
  /// One carried unit at quality q left the pack (fitted).
  void TakeCarried(string itemId,CraftQuality q)
  {
   if(itemId==null||q==CraftQuality.Standard||!carriedQuality.TryGetValue(itemId,out var c))return;
   int i=q==CraftQuality.Rough?0:1;if(c[i]>0)c[i]--;
   if(c[0]==0&&c[1]==0)carriedQuality.Remove(itemId);
  }
  /// Units that left the pack by other ways (sold, stored, used) drop the recorded qualities first, Rough before Fine.
  void ReconcileCarried(string itemId)
  {
   if(itemId==null||!carriedQuality.TryGetValue(itemId,out var c))return;
   int total=pack.Quantity(itemId);
   int over=c[0]+c[1]-total;
   if(over>0){int r=Math.Min(c[0],over);c[0]-=r;over-=r;c[1]=Math.Max(0,c[1]-over);}
   if(c[0]<=0&&c[1]<=0)carriedQuality.Remove(itemId);
  }
  // ---- Handling ---------------------------------------------------------------------------------------------------
  /// A weapon's handling numbers as fitted now, or with withModId fitted at quality q in place of its slot's mod.
  /// Character recoil control is included (it lowers the kick the player feels).
  public WeaponHandling HandlingFor(string weaponId,string withModId=null,CraftQuality q=CraftQuality.Standard)
  {
   var loadout=GetLoadout(weaponId??Loadout.WeaponId);if(loadout==null)return default;
   var stats=loadout.Stats;
   if(!string.IsNullOrEmpty(withModId)){var mod=loadout.Modifier(withModId);if(mod!=null&&loadout.Accepts(mod))stats=loadout.Preview(mod.slot,withModId,q);}
   stats=WeaponStatPipeline.ApplyCharacter(stats,character,loadout.WeaponId);
   return WeaponHandlingRules.From(stats);
  }
  /// The weapon with nothing in withoutSlot (the bare pistol for the before card).
  public WeaponHandling HandlingWithout(string weaponId,string slot)
  {
   var loadout=GetLoadout(weaponId??Loadout.WeaponId);if(loadout==null)return default;
   return WeaponHandlingRules.From(WeaponStatPipeline.ApplyCharacter(loadout.Preview(slot,null),character,loadout.WeaponId));
  }
  // ---- Save ----------------------------------------------------------------------------------------------------------
  void CaptureAssembly(CraftingState state)
  {
   state.handMade=handMade.OrderBy(x=>x,StringComparer.Ordinal).ToArray();
   state.benchFinished=benchFinished.Count==0?null:benchFinished.OrderBy(x=>x,StringComparer.Ordinal).ToArray();
   state.carriedQuality=carriedQuality.Keys.ToList().Select(id=>{ReconcileCarried(id);return carriedQuality.TryGetValue(id,out var c)?new QualityEntry{itemId=id,rough=c[0],fine=c[1]}:null;}).Where(x=>x!=null).OrderBy(x=>x.itemId,StringComparer.Ordinal).ToArray();
   state.bench=OpenTicket==null?null:new BenchTicketState{recipeId=OpenTicket.recipeId,stationId=OpenTicket.stationId,weaponId=OpenTicket.weaponId,inputs=(OpenTicket.inputs??Array.Empty<ItemStack>()).Select(s=>new ItemStack(s.itemId,s.quantity)).ToArray(),stageId=AssemblyStageId,stageLabel=AssemblyStageLabel};
  }
  void RestoreAssembly(CraftingState state,List<string> skipped)
  {
   handMade.Clear();benchFinished.Clear();carriedQuality.Clear();OpenTicket=null;AssemblyBlob=null;AssemblyStageId=null;AssemblyStageLabel=null;LastAssembly=null;
   if(state==null)return;
   if(state.handMade!=null)foreach(var id in state.handMade)if(Recipe(id)!=null)handMade.Add(id);
   if(state.benchFinished!=null)foreach(var id in state.benchFinished)if(Recipe(id)!=null)benchFinished.Add(id);
   // A save from before the bench (no handMade record) that already made a hands-on part on the timer keeps its timer:
   // that player has made one, and an old save loads unchanged.
   if(state.handMade==null&&state.crafted!=null)foreach(var c in state.crafted)if(c!=null&&c.count>0&&HasAssembly(c.id))handMade.Add(c.id);
   if(state.carriedQuality!=null)foreach(var e in state.carriedQuality)
   {
    if(e==null||Item(e.itemId)==null)continue;
    int r=Math.Max(0,e.rough),f=Math.Max(0,e.fine);if(r+f==0)continue;
    carriedQuality[e.itemId]=new[]{r,f};
    // reconciled against the pack on first read: the pack is restored separately
   }
   var b=state.bench;
   if(b!=null&&!string.IsNullOrEmpty(b.recipeId))
   {
    if(Recipe(b.recipeId)==null||GetLoadout(b.weaponId)==null){skipped.Add(b.recipeId);return;}
    OpenTicket=new AssemblyTicket{recipeId=b.recipeId,stationId=b.stationId,weaponId=b.weaponId,inputs=(b.inputs??Array.Empty<ItemStack>()).Where(s=>s!=null&&s.quantity>0&&Item(s.itemId)!=null).Select(s=>new ItemStack(s.itemId,s.quantity)).ToArray(),resumed=true};
    AssemblyStageId=b.stageId;AssemblyStageLabel=b.stageLabel;
   }
  }
  static CraftQuality ParseQuality(string q)=>q=="Rough"?CraftQuality.Rough:q=="Fine"?CraftQuality.Fine:CraftQuality.Standard;
  static string QualityName(CraftQuality q)=>q==CraftQuality.Standard?null:q.ToString();
 }
 /// The constants that turn weapon stats into handling the player sees (match PlayerCombat's defaults).
 public static class WeaponHandlingRules
 {
  /// PlayerCombat.recoilDegreesPerPoint: camera kick per recoil point.
  public const float KickDegreesPerPoint=.05f;
  /// PlayerCombat.recoilRecoverSeconds: the recovery time of a weapon whose recovery stat is 0.
  public const float DefaultRecoverySeconds=.18f;
  /// Recovery slower than this overshoots once on the way back (OvershootFraction).
  public const float OvershootFrom=.22f;
  public static float RecoverySeconds(WeaponStats s)=>s.recovery>0?s.recovery:DefaultRecoverySeconds;
  /// Fraction of the recovered kick that swings past the rest point before settling: 0 (critically damped) up to 0.3.
  public static float OvershootFraction(float recoverySeconds)=>Math.Max(0,Math.Min(.3f,(recoverySeconds-OvershootFrom)*1.5f));
  public static WeaponHandling From(WeaponStats s)=>new WeaponHandling{sway=s.sway,kick=s.recoil*KickDegreesPerPoint,sideStep=s.sideKick,recovery=RecoverySeconds(s),scatterGrowth=s.scatterGrowth};
 }
 [Serializable] public class QualityEntry {public string itemId;public int rough,fine;}
 [Serializable] public class BenchTicketState
 {
  public string recipeId,stationId,weaponId;
  public ItemStack[] inputs;
  public string stageId,stageLabel;
 }
}
