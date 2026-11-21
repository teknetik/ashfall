using System;
using System.Linq;
using System.Reflection;
using UnityEngine;
namespace AthenHill
{
 /// Crafted quality of a hand-made part (Steady Hands bench, 20 Nov 2026). Timed crafts make Standard; old saves read Standard.
 public enum CraftQuality { Rough = 0, Standard = 1, Fine = 2 }
 /// What is on the bench for one hands-on job (CONTRACT.md section B).
 public sealed class AssemblyTicket
 {
  public string recipeId,stationId,weaponId;
  /// Reserved from the pack (and locker), not yet consumed.
  public ItemStack[] inputs;
  /// True when an unfinished job was reopened.
  public bool resumed;
 }
 /// What the bench reports when a job is finished.
 public sealed class AssemblyResult
 {
  public string recipeId;public CraftQuality quality;
  /// 0..1
  public float score;
  public int faults;public float seconds;
  /// e.g. copper_filament x1
  public ItemStack[] byproducts;
 }
 /// A weapon's handling numbers for the bench's test cards and the feel code (DESIGN.md section 10).
 [Serializable] public struct WeaponHandling
 {
  /// Aim sway amplitude, degrees.
  public float sway;
  /// Upward kick per shot, degrees.
  public float kick;
  /// Sideways step per shot, degrees (sign varies per shot).
  public float sideStep;
  /// Seconds to settle back after a shot.
  public float recovery;
  /// Extra scatter per rapid shot (fraction of the base cone added per shot in a string).
  public float scatterGrowth;
 }
 public partial class CraftingSession
 {
  /// Raised when a bench job opens, changes stage, completes or is abandoned.
  public event Action AssemblyChanged;
  /// A bench job was completed: (recipe id, the result as committed). Raised after the part is fitted or packed.
  public event Action<string,AssemblyResult> AssemblyFinished;
  /// The recipe has a hands-on job (CraftRecipe.assembly).
  public bool HasAssembly(string recipeId)=>Model!=null&&Model.HasAssembly(recipeId);
  /// Made by hand at least once (unlocks the timed craft).
  public bool HandMade(string recipeId)=>Model!=null&&Model.HandMade(recipeId);
  public bool CanBeginAssembly(string recipeId,out string reason)
  {
   if(Model==null){reason="no_model";return false;}
   return Model.CanBeginAssembly(recipeId,StationFor(recipeId),out reason);
  }
  /// Reserves inputs and takes the weapon to the bench. Returns the open ticket when one already exists for this recipe.
  public AssemblyTicket BeginAssembly(string recipeId,out string reason)
  {
   if(Model==null){reason="no_model";return null;}
   bool wasOpen=Model.OpenTicket!=null;
   var ticket=Model.BeginAssembly(recipeId,StationFor(recipeId),out reason);
   if(ticket!=null)
   {
    if(!wasOpen&&combat&&combat.Armed&&combat.Loadout!=null&&combat.Loadout.WeaponId==ticket.weaponId)combat.HolsterForBench();
    RaiseAssemblyChanged();
   }
   return ticket;
  }
  /// Unfinished job, also after loading a save.
  public AssemblyTicket OpenTicket=>Model?.OpenTicket;
  /// Opaque JSON of the bench job; saved as WardSaveData.benchJob.
  public string AssemblyBlob {get{return Model?.AssemblyBlob;}set{if(Model==null||Model.AssemblyBlob==value)return;Model.AssemblyBlob=value;RaiseAssemblyChanged();}}
  /// For the journal and Field Notes line.
  public void ReportAssemblyStage(string stageId,string label)
  {
   if(Model==null)return;
   if(Model.AssemblyStageId==stageId&&Model.AssemblyStageLabel==label)return;
   Model.AssemblyStageId=stageId;Model.AssemblyStageLabel=label;
   RaiseAssemblyChanged();
  }
  /// Consume, grant with quality, fit, award, byproducts.
  public bool CompleteAssembly(AssemblyResult result,out string reason)
  {
   if(Model==null){reason="no_model";return false;}
   var ticket=Model.OpenTicket;
   bool ok=Model.CompleteAssembly(result,out reason);
   if(ok){AssemblyCompleted(ticket,result);AssemblyFinished?.Invoke(ticket.recipeId,Model.LastAssembly);}
   RaiseAssemblyChanged();
   return ok;
  }
  /// Return the weapon and what was not spent.
  public bool AbandonAssembly(string[] spentInputs,out string reason)
  {
   if(Model==null){reason="no_model";return false;}
   var ticket=Model.OpenTicket;
   bool ok=Model.AbandonAssembly(spentInputs,out reason);
   if(ok)AssemblyAbandoned(ticket);
   RaiseAssemblyChanged();
   return ok;
  }
  /// Handling numbers of a weapon, optionally with one mod fitted at a quality (in place of whatever fills that slot).
  public WeaponHandling HandlingFor(string weaponId,string withModId=null,CraftQuality q=CraftQuality.Standard)
   =>Model!=null?Model.HandlingFor(weaponId,withModId,q):default;
  /// The handling of the weapon with nothing in a slot (the bare pistol for the before card).
  public WeaponHandling HandlingWithout(string weaponId,string slot)=>Model!=null?Model.HandlingWithout(weaponId,slot):default;
  void RaiseAssemblyChanged()=>AssemblyChanged?.Invoke();
  // ---- Station routing (CONTRACT B: CraftingStationMarker.Use) -------------------------------------------------------
  CraftingStationMarker usedStation;
  /// The station a bench job runs at: the open window's station, else the bench last used, else the recipe's own.
  string StationFor(string recipeId)
  {
   if(Session&&!string.IsNullOrEmpty(Session.ActiveStationId))return Session.ActiveStationId;
   if(usedStation)return usedStation.stationId;
   return Model?.Recipe(recipeId)?.stationId;
  }
  /// The recipe the bench should open by hand at this station, or null: the open job's recipe, else the current field
  /// order's recipe when it has a bench job not yet made by hand and CanBeginAssembly holds.
  public string AssemblyRecipeAt(CraftingStationMarker station,out string reason)
  {
   reason="none";
   if(Model==null||!station)return null;
   var open=Model.OpenTicket;
   if(open!=null){reason="resumed";return open.stationId==null||open.stationId==station.stationId?open.recipeId:null;}
   var orders=GetComponent<FieldOrders>();
   var recipe=orders&&orders.Ready?orders.Progress.RecipeFor(Model,orders.Progress.Current):null;
   if(recipe==null||!Model.NeedsHandMade(recipe.id)||(!string.IsNullOrEmpty(recipe.stationId)&&recipe.stationId!=station.stationId))return null;
   return Model.CanBeginAssembly(recipe.id,station.stationId,out reason)?recipe.id:null;
  }
  /// E at a workbench: opens the hands-on job directly when one is due (AssemblyRecipeAt), otherwise the caller opens the
  /// Fabricator window. True when the bench was opened. A job left open while the bench system is missing is abandoned
  /// (everything back to the pack), so the weapon and the parts are never stuck on a bench that is not there.
  public bool UseStation(CraftingStationMarker station)
  {
   usedStation=station;
   var open=Model?.OpenTicket;
   if(open!=null&&!BenchPresent(open.recipeId))
   {
    if(AbandonAssembly(null,out var why))Debug.Log($"Steady Hands bench: no bench system for {open.recipeId} ({lastBenchMissing}); the open job was abandoned and its parts returned.");
    else Debug.LogWarning($"Steady Hands bench: no bench system for {open.recipeId} ({lastBenchMissing}) and the open job could not be returned: {why}.");
    return false;
   }
   var recipeId=AssemblyRecipeAt(station,out _);
   return recipeId!=null&&OpenAssembly(station,recipeId);
  }
  // ---- Is the bench system there? (fix round, 20 Nov 2026) ------------------------------------------------------------
  /// Overrides for tests and QA: whether GameSession.OpenAssembly exists (null = reflection), and whether the scene has a
  /// bench for an assembly id (null = an AssemblyBench whose recipe has that id).
  public Func<bool> OpenAssemblyFound;
  public Func<string,bool> AssemblyRecipeFound;
  string lastBenchMissing;
  readonly System.Collections.Generic.HashSet<string> benchMissingLogged=new System.Collections.Generic.HashSet<string>();
  int benchCacheFrame=-1;readonly System.Collections.Generic.Dictionary<string,bool> benchCache=new System.Collections.Generic.Dictionary<string,bool>();
  /// The hands-on bench can run this recipe's job: a way to open it (AssemblyOpener, or GameSession.OpenAssembly) and its
  /// AssemblyRecipe in the scene. When not, the station opens the Fabricator and the timer may make the part (logged once).
  public bool BenchPresent(string recipeId)
  {
   var assembly=Model?.Recipe(recipeId)?.assembly;
   if(string.IsNullOrEmpty(assembly))return false;
   // cached for a frame in play (the Fabricator asks per row); Edit Mode tests change the overrides between calls
   if(!Application.isPlaying||benchCacheFrame!=Time.frameCount){benchCacheFrame=Time.frameCount;benchCache.Clear();}
   if(benchCache.TryGetValue(assembly,out bool known))return known;
   string missing=null;
   if(AssemblyOpener==null&&!(OpenAssemblyFound!=null?OpenAssemblyFound():FindOpenAssembly()!=null))missing="no AssemblyOpener and no GameSession.OpenAssembly";
   else if(!(AssemblyRecipeFound!=null?AssemblyRecipeFound(assembly):SceneHasBench(assembly)))missing=$"no AssemblyRecipe '{assembly}' on a bench in the scene";
   benchCache[assembly]=missing==null;
   if(missing!=null){lastBenchMissing=missing;if(benchMissingLogged.Add(recipeId+"|"+missing))Debug.Log($"Steady Hands bench: {missing}; {recipeId} opens in the Fabricator and the timed craft is allowed.");}
   return missing==null;
  }
  static bool SceneHasBench(string assembly)
  {
   foreach(var b in FindObjectsByType<AssemblyBench>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))if(b&&b.recipe&&b.recipe.Id==assembly)return true;
   return false;
  }
  static MethodInfo FindOpenAssembly()
  {
   if(!openSearched){openSearched=true;openAssembly=typeof(GameSession).GetMethod("OpenAssembly",BindingFlags.Public|BindingFlags.Instance,null,new[]{typeof(CraftingStationMarker),typeof(string)},null);}
   return openAssembly;
  }
  /// Build by hand (Fabricator window button, or the station): enters the bench through GameSession.OpenAssembly, which the
  /// bench system adds (CONTRACT B). False with a notice when the bench cannot start or the bench system is not installed.
  public bool OpenAssembly(CraftingStationMarker station,string recipeId)
  {
   if(Model==null||!Session)return false;
   if(station)usedStation=station;
   var recipe=Model.Recipe(recipeId);
   string reason;
   if(Model.OpenTicket!=null&&Model.OpenTicket.recipeId!=recipeId){reason="bench_busy";}
   else if(Model.OpenTicket==null&&!Model.CanBeginAssembly(recipeId,station?station.stationId:StationFor(recipeId),out reason)){}
   else if(!BenchPresent(recipeId))reason="no_bench";
   else if(AssemblyOpener!=null?AssemblyOpener(station,recipeId):InvokeOpenAssembly(station,recipeId))return true;
   else reason="no_bench";
   Session.Notify(reason=="no_bench"?"The bench is not set up for hand work yet.":"Cannot start at the bench. "+CraftingText.Reason(reason,Model,recipe),station&&!string.IsNullOrEmpty(station.title)?station.title:Bench);
   Session.Cue(CitySoundCue.Unavailable);
   return false;
  }
  /// Optional opener set by the bench system (station, recipe id) -> opened. When null, GameSession.OpenAssembly is found
  /// by name, so this file does not depend on the bench system's build order.
  public Func<CraftingStationMarker,string,bool> AssemblyOpener;
  static MethodInfo openAssembly;static bool openSearched;
  bool InvokeOpenAssembly(CraftingStationMarker station,string recipeId)
  {
   if(OpenAssemblyFound!=null&&!OpenAssemblyFound())return false;
   if(FindOpenAssembly()==null)return false;
   var result=openAssembly.Invoke(Session,new object[]{station,recipeId});
   return result is bool b?b:Session.State.ToString()=="Assembly";
  }
  // ---- Notices -------------------------------------------------------------------------------------------------------
  void AssemblyCompleted(AssemblyTicket ticket,AssemblyResult result)
  {
   var done=Model.LastAssembly;var recipe=Model.Recipe(ticket.recipeId);
   if(!Session||done==null||recipe==null)return;
   foreach(var s in done.byproducts??new ItemStack[0])Model.Acquire(s.itemId);
   var loadout=Model.GetLoadout(ticket.weaponId);
   string part=CraftingText.WithQuality(Model,recipe.outputItemId,done.quality,true);
   string where=Model.LastAssemblyFitted&&loadout!=null?$" fitted to your {loadout.WeaponName}.":" made; it is in your pack.";
   string by=done.byproducts!=null&&done.byproducts.Length>0?" Spare parts to your pack: "+string.Join(", ",done.byproducts.Select(s=>$"{CraftingText.ItemName(Model,s.itemId)} ×{s.quantity}"))+".":"";
   Session.Notify(part+where+CraftingText.AwardText(Model,Model.LastAward?.recipeId==recipe.id?Model.LastAward:null)+by,Bench);
  }
  void AssemblyAbandoned(AssemblyTicket ticket)
  {
   if(!Session||ticket==null)return;
   var loadout=Model.GetLoadout(ticket.weaponId);
   Session.Notify($"Job abandoned. The {(loadout!=null?loadout.WeaponName:"weapon")} and the unused parts are back in your pack.",Bench);
  }
 }
}
