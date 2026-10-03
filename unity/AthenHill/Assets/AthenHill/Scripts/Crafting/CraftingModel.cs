using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// Two deliberate transactions: crafting makes a carried item; fitting consumes it into a weapon slot.
 /// Every change to the pack goes through one ShopModel.TryApply, so a failed step changes nothing.
 public sealed class CraftingModel
 {
  readonly CraftingCatalog data;
  readonly ItemSpec[] items;
  readonly ShopModel pack;
  readonly Func<bool> hasWeapon;
  readonly CharacterModel character;
  readonly HashSet<string> known=new HashSet<string>();
  readonly Dictionary<string,int> crafted=new Dictionary<string,int>();
  readonly Dictionary<string,WeaponLoadout> loadouts=new Dictionary<string,WeaponLoadout>();
  public CraftingCatalog Data=>data;
  public WeaponLoadout Loadout {get;}
  public IEnumerable<WeaponLoadout> Loadouts=>loadouts.Values;
  public IReadOnlyCollection<string> KnownRecipes=>known;
  public IReadOnlyDictionary<string,int> CraftCounts=>crafted;
  public int Crafts {get;private set;}
  public float BaseRecoil=>Loadout.Base.recoil;
  public float RecoilStat=>Loadout.Stats.recoil;
  /// Raised after a committed craft, fit, removal, unlock or restore.
  public event Action Changed;
  public CraftingModel(CraftingCatalog data,IEnumerable<ItemSpec> items,ShopModel pack,Func<bool> hasWeapon,string weaponId=null,CharacterModel character=null)
  {
   this.data=data;this.items=items.ToArray();this.pack=pack;this.hasWeapon=hasWeapon;this.character=character;
   foreach(var weapon in data.weapons)
   {
    var recipe=string.IsNullOrEmpty(weapon.recipeId)?data.recipes.FirstOrDefault(r=>r.outputWeaponId==weapon.id):data.recipes.FirstOrDefault(r=>r.id==weapon.recipeId&&r.outputWeaponId==weapon.id);
    loadouts.Add(weapon.id,new WeaponLoadout(weapon,data.modifiers,recipe?.outputSlots));
   }
   Loadout=GetLoadout(weaponId??"weapon_scrap_pistol")??loadouts.Values.First();
   foreach(var recipe in data.recipes)if(recipe.knownByDefault)known.Add(recipe.id);
   character?.BindAttachmentWeight(()=>FittedWeightKg);
  }
  float Weight(string id)=>Math.Max(0,pack.Spec(id)?.weightKg??0);
  public float FittedWeightKg=>loadouts.Values.Where(l=>HasWeapon(l.WeaponId)).Sum(l=>l.FittedMods.Sum(x=>Weight(x.Value)));
  public CraftRecipe Recipe(string id)=>data.recipes.FirstOrDefault(x=>x.id==id);
  public ItemSpec Item(string id)=>items.FirstOrDefault(x=>x.id==id);
  public WeaponLoadout GetLoadout(string weaponId)=>weaponId!=null&&loadouts.TryGetValue(weaponId,out var loadout)?loadout:null;
  public CraftWeapon FindWeapon(string itemId)=>data.weapons.FirstOrDefault(w=>!string.IsNullOrEmpty(itemId)&&w.itemId==itemId);
  public bool HasWeapon(string weaponId)
  {
   var loadout=GetLoadout(weaponId);if(loadout==null)return false;
   if(loadout==Loadout&&hasWeapon())return true;
   var item=loadout.ItemId;
   return !string.IsNullOrEmpty(item)&&(pack.Quantity(item)>0||(character!=null&&(character.Equipped("primary")==item||character.Equipped("secondary")==item)));
  }
  public int CraftCount(string recipeId)=>recipeId!=null&&crafted.TryGetValue(recipeId,out int n)?n:0;
  public bool Knows(string recipeId)=>recipeId!=null&&known.Contains(recipeId);
  /// The item entered the pack: reveals every schematic that lists it. Returns the newly known recipes.
  public List<CraftRecipe> Acquire(string itemId)=>UnlockWhere("acquireItem",itemId);
  /// A field order became current: reveals schematics tied to it.
  public List<CraftRecipe> OrderStarted(string orderId)=>UnlockWhere("orderStart",orderId);
  List<CraftRecipe> UnlockWhere(string type,string id)
  {
   var unlocked=new List<CraftRecipe>();
   foreach(var recipe in data.recipes)if(recipe.unlocks!=null&&recipe.unlocks.Any(x=>x.type==type&&x.id==id)&&known.Add(recipe.id))unlocked.Add(recipe);
   if(unlocked.Count>0)Changed?.Invoke();
   return unlocked;
  }
  /// Direct schematic reward (field orders). False when unknown or already known.
  public bool Unlock(string recipeId)
  {
   if(Recipe(recipeId)==null||!known.Add(recipeId))return false;
   Changed?.Invoke();return true;
  }
  public bool CanCraft(string recipeId,string stationId,out string reason)=>ValidateCraft(recipeId,stationId,out _,out reason);
  bool ValidateCraft(string recipeId,string stationId,out List<KeyValuePair<string,int>> used,out string reason)
  {
   used=null;
   var recipe=Recipe(recipeId);
   if(recipe==null){reason="unknown_recipe";return false;}
   if(!known.Contains(recipeId)){reason="recipe_locked";return false;}
   if(!string.IsNullOrEmpty(recipe.stationId)&&recipe.stationId!=stationId){reason="wrong_station";return false;}
   if(recipe.requiredSchematics!=null&&recipe.requiredSchematics.Any(id=>!Knows(id))){reason="missing_schematic";return false;}
   if(!Meets(recipe.requirements)){reason="unmet_requirements";return false;}
   if(!HasTools(recipe.requiredTools)){reason="missing_tool";return false;}
   if(!string.IsNullOrEmpty(recipe.requiresWeaponId)&&!HasWeapon(recipe.requiresWeaponId)){reason="missing_weapon";return false;}
   if(!string.IsNullOrEmpty(recipe.outputWeaponId))
   {
    var weapon=GetLoadout(recipe.outputWeaponId);
    if(weapon==null||weapon.ItemId!=recipe.outputItemId||recipe.outputQuantity!=1||recipe.outputSlots==null||!weapon.Slots.SequenceEqual(recipe.outputSlots)){reason="invalid_recipe";return false;}
   }
   if(recipe.outputQuantity<1||recipe.inputs==null||recipe.inputs.Any(x=>x.kind=="item"&&x.id==recipe.outputItemId)){reason="invalid_recipe";return false;}
   var output=Item(recipe.outputItemId);
   if(output==null){reason="unknown_item";return false;}
   // Reserve reusable tools in the same allocation search so a tagged ingredient can select another item.
   var tools=(recipe.requiredTools??Array.Empty<string>()).Distinct().ToArray();
   var requirements=recipe.inputs.Concat(tools.Select(id=>new CraftIngredient{kind="item",id=id,quantity=1})).ToArray();
   if(!IngredientAllocator.TryAllocate(requirements,items,pack,out used)){reason="missing_ingredients";return false;}
   used=used.Select(x=>new KeyValuePair<string,int>(x.Key,x.Value-(tools.Contains(x.Key)?1:0))).Where(x=>x.Value>0).ToList();
   if(output.maxStack>0&&(long)pack.Quantity(output.id)+recipe.outputQuantity>output.maxStack){reason="output_stack_full";return false;}
   reason="ok";return true;
  }
  /// The timed fabrication in progress (one at a time), or null. Nothing is reserved or consumed while it runs.
  public CraftJob Job {get;private set;}
  /// Bench seconds for a schematic (0 = instant).
  public float CraftSeconds(string recipeId){var r=Recipe(recipeId);return r!=null&&r.craftSeconds>0?r.craftSeconds:0;}
  /// Starts fabrication at time now. An instant schematic (0 s) commits straight away through TryCraft and leaves Job
  /// null; a timed one only validates and starts the timer: the parts stay in the pack until TickCraft completes it.
  public bool BeginCraft(string recipeId,string stationId,float now,out string reason)
  {
   if(Job!=null){reason="busy";return false;}
   if(!ValidateCraft(recipeId,stationId,out _,out reason))return false;
   float seconds=CraftSeconds(recipeId);
   if(seconds<=0)return TryCraft(recipeId,stationId,out reason);
   Job=new CraftJob(recipeId,stationId,now,seconds);reason="started";return true;
  }
  /// Completes the job once its time is up: validates again and commits inputs and output in one transaction, so parts
  /// that left the pack meanwhile fail the craft with nothing changed. Returns None while it is still running.
  public CraftTick TickCraft(float now,out CraftJob job,out string reason)
  {
   job=Job;reason="ok";
   if(job==null||!job.Done(now))return CraftTick.None;
   Job=null;
   return TryCraft(job.recipeId,job.stationId,out reason)?CraftTick.Completed:CraftTick.Failed;
  }
  /// Stops the job; nothing was consumed. False when nothing was running.
  public bool CancelCraft(out CraftJob job){job=Job;Job=null;return job!=null;}
  public bool TryCraft(string recipeId,string stationId,out string reason)
  {
   if(!ValidateCraft(recipeId,stationId,out var used,out reason))return false;
   var recipe=Recipe(recipeId);
   if(Crafts==int.MaxValue||CraftCount(recipeId)==int.MaxValue){reason="overflow";return false;}
   var delta=used.Select(x=>new KeyValuePair<string,int>(x.Key,-x.Value)).ToList();
   delta.Add(new KeyValuePair<string,int>(recipe.outputItemId,recipe.outputQuantity));
   if(!pack.TryApply(delta,0,out reason))return false;
   Crafts++;crafted[recipeId]=CraftCount(recipeId)+1;
   Changed?.Invoke();return true;
  }
  /// Fits one carried mod into its slot. A mod already in that slot returns to the pack in the same transaction.
  public bool TryFit(string itemId,out string reason)
   =>TryFit(Loadout.WeaponId,itemId,out reason);
  public bool CanFit(string weaponId,string itemId,out string reason)
  {
   var loadout=GetLoadout(weaponId);
   if(loadout==null||!HasWeapon(weaponId)){reason="missing_weapon";return false;}
   var mod=loadout.Modifier(itemId);
   if(mod==null){reason="not_a_mod";return false;}
   if(!loadout.Accepts(mod)){reason="wrong_slot";return false;}
   if(!Meets(mod.requirements)){reason="unmet_requirements";return false;}
   if(!HasTools(mod.requiredTools)){reason="missing_tool";return false;}
   var previous=loadout.Fitted(mod.slot);
   if(previous==itemId){reason="already_fitted";return false;}
   if(pack.Quantity(itemId)<1){reason="not_carried";return false;}
   reason="ok";return true;
  }
  public bool TryFit(string weaponId,string itemId,out string reason)
  {
   if(!CanFit(weaponId,itemId,out reason))return false;
   var loadout=GetLoadout(weaponId);var mod=loadout.Modifier(itemId);var previous=loadout.Fitted(mod.slot);
   var delta=new List<KeyValuePair<string,int>>{new KeyValuePair<string,int>(itemId,-1)};
   if(previous!=null)delta.Add(new KeyValuePair<string,int>(previous,1));
   float attachmentDelta=Weight(itemId)-Weight(previous);
   if(!(character!=null?character.TryTransferAttachment(delta,attachmentDelta,out reason):pack.TryApply(delta,0,out reason)))return false;
   loadout.Set(mod.slot,itemId);Changed?.Invoke();return true;
  }
  public bool TryRemove(string slot,out string reason)
   =>TryRemove(Loadout.WeaponId,slot,out reason);
  public bool TryRemove(string weaponId,string slot,out string reason)
  {
   var loadout=GetLoadout(weaponId);
   if(loadout==null||!HasWeapon(weaponId)){reason="missing_weapon";return false;}
   if(!loadout.HasSlot(slot)){reason="wrong_slot";return false;}
   var current=loadout.Fitted(slot);
   if(current==null){reason="empty_slot";return false;}
   var delta=new[]{new KeyValuePair<string,int>(current,1)};
   if(!(character!=null?character.TryTransferAttachment(delta,-Weight(current),out reason):pack.TryApply(delta,0,out reason)))return false;
   loadout.Set(slot,null);Changed?.Invoke();return true;
  }
  /// Have/need for one ingredient line, for display. Tag lines count every carried item with the tag;
  /// the allocator still decides the exact, non-overlapping consumption when crafting.
  public int Available(CraftIngredient input)
  {
   if(input==null)return 0;
   if(input.kind=="item")return pack.Quantity(input.id);
   long total=0;foreach(var item in items)if(item.HasTag(input.id))total+=pack.Quantity(item.id);
   return (int)Math.Min(int.MaxValue,total);
  }
  bool Meets(CharacterRequirement[] requirements)=>requirements==null||requirements.Length==0||(character!=null&&character.Meets(requirements,out _));
  bool HasTools(string[] tools)=>tools==null||tools.All(id=>!string.IsNullOrEmpty(id)&&pack.Quantity(id)>0);
  static SlotEntry[] CaptureSlots(WeaponLoadout loadout)=>loadout.FittedMods.Select(x=>new SlotEntry{slot=x.Key,itemId=x.Value}).OrderBy(x=>x.slot).ToArray();
  public CraftingState Capture()=>new CraftingState
  {
   known=known.OrderBy(x=>x).ToArray(),crafted=crafted.Select(x=>new CountEntry{id=x.Key,count=x.Value}).OrderBy(x=>x.id).ToArray(),crafts=Crafts,
   fitted=CaptureSlots(Loadout),weapons=loadouts.Values.OrderBy(x=>x.WeaponId).Select(x=>new WeaponLoadoutState{weaponId=x.WeaponId,fitted=CaptureSlots(x)}).ToArray()
  };
  /// Save-game restore. Unknown recipe IDs and unfit mods are skipped and returned for the load notice.
  public List<string> Restore(CraftingState state)
  {
   var skipped=new List<string>();
   Job=null; // a fabrication in progress is never saved: nothing was consumed, so nothing is lost
   known.Clear();crafted.Clear();Crafts=0;
   foreach(var loadout in loadouts.Values)loadout.Replace(null);
   foreach(var recipe in data.recipes)if(recipe.knownByDefault)known.Add(recipe.id);
   if(state!=null)
   {
    if(state.known!=null)foreach(var id in state.known){if(Recipe(id)!=null)known.Add(id);else skipped.Add(id);}
    if(state.crafted!=null)foreach(var c in state.crafted)if(c!=null&&Recipe(c.id)!=null&&c.count>0)crafted[c.id]=c.count;
    Crafts=(int)Math.Min(int.MaxValue,Math.Max(Math.Max(0,state.crafts),crafted.Values.Sum(x=>(long)x)));
    if(state.weapons!=null&&state.weapons.Length>0)
    {
     var restored=new HashSet<string>();
     foreach(var saved in state.weapons)
     {
      if(saved==null)continue;
      var loadout=GetLoadout(saved.weaponId);
      if(loadout==null||!restored.Add(saved.weaponId)){skipped.Add(saved.weaponId);continue;}
      skipped.AddRange(loadout.Replace(saved.fitted?.Where(x=>x!=null).Select(x=>new KeyValuePair<string,string>(x.slot,x.itemId))));
     }
    }
    else skipped.AddRange(Loadout.Replace(state.fitted?.Where(x=>x!=null).Select(x=>new KeyValuePair<string,string>(x.slot,x.itemId))));
   }
   Changed?.Invoke();
   return skipped;
  }
 }
 public enum CraftTick { None, Completed, Failed }
 /// One timed fabrication: which schematic, at which station, when it started and how long it takes. Pure (the caller
 /// supplies the clock), like SalvageSearch.
 public sealed class CraftJob
 {
  public readonly string recipeId,stationId;
  public readonly float startedAt,seconds;
  public CraftJob(string recipeId,string stationId,float startedAt,float seconds){this.recipeId=recipeId;this.stationId=stationId;this.startedAt=startedAt;this.seconds=Math.Max(0,seconds);}
  public float EndsAt=>startedAt+seconds;
  public bool Done(float now)=>now>=EndsAt;
  public float Progress(float now)=>seconds<=0?1:Math.Min(1,Math.Max(0,(now-startedAt)/seconds));
  public float Remaining(float now)=>Math.Max(0,EndsAt-now);
 }
 [Serializable] public class CountEntry {public string id;public int count;}
 [Serializable] public class SlotEntry {public string slot,itemId;}
 [Serializable] public class WeaponLoadoutState {public string weaponId;public SlotEntry[] fitted;}
 [Serializable] public class CraftingState
 {
  public string[] known;
  public CountEntry[] crafted;
  public int crafts;
  public SlotEntry[] fitted;
  public WeaponLoadoutState[] weapons;
 }
}
