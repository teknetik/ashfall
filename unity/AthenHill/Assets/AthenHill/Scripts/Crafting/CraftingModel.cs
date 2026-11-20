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
  /// Parts kept outside the pack that schematics may also use (5 Oct 2026: the leased home's locker feeds Brann's bench).
  /// The pack's own units are always used first; null or a closed reserve means the pack alone.
  public StashModel Reserve {get;set;}
  public Func<bool> ReserveOpen {get;set;}
  bool ReserveActive=>Reserve!=null&&(ReserveOpen?.Invoke()??true);
  int Pool(string id)=>pack.Quantity(id)+(ReserveActive?Reserve.Quantity(id):0);
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
  /// The schematics a digital magazine teaches (recipes whose unlocks list {type: magazine, id}).
  public IEnumerable<CraftRecipe> MagazineRecipes(string magazineId)=>data.recipes.Where(r=>r.unlocks!=null&&r.unlocks.Any(x=>x.type=="magazine"&&x.id==magazineId));
  /// A magazine is owned once every schematic it teaches is known (ownership is saved through the known recipes).
  public bool OwnsMagazine(string magazineId){var taught=MagazineRecipes(magazineId).ToList();return taught.Count>0&&taught.All(r=>known.Contains(r.id));}
  /// A magazine was downloaded: teaches its schematics. Returns the newly known recipes.
  public List<CraftRecipe> ReadMagazine(string magazineId)=>UnlockWhere("magazine",magazineId);
  /// A colonist's dialogue node ran (id "npc_ossa:servo_look"): teaches the schematics identified there (20 Nov 2026).
  public List<CraftRecipe> Identify(string topicId)=>UnlockWhere("identify",topicId);
  /// The schematic is still unknown and is taught by identification (a colonist explains the salvage), not by finding the part.
  public bool NeedsIdentification(string recipeId){var r=Recipe(recipeId);return r!=null&&!known.Contains(r.id)&&r.unlocks!=null&&r.unlocks.Any(x=>x.type=="identify");}
  /// A carried item this schematic would use that someone has to identify first (ItemSpec.identifyBy), or null.
  public ItemSpec UnidentifiedCarried(string recipeId)
  {
   if(!NeedsIdentification(recipeId))return null;
   foreach(var input in Recipe(recipeId).inputs??Array.Empty<CraftIngredient>())
    foreach(var item in items)
     if(!string.IsNullOrEmpty(item.identifyBy)&&pack.Quantity(item.id)>0&&(input.kind=="item"?input.id==item.id:item.HasTag(input.id)))return item;
   return null;
  }
  /// True when a carried item still needs showing to its identifier (pickup notes, pack tooltip).
  public bool NeedsIdentifying(string itemId)
  {
   var spec=Item(itemId);if(spec==null||string.IsNullOrEmpty(spec.identifyBy))return false;
   return data.recipes.Any(r=>NeedsIdentification(r.id)&&r.inputs!=null&&r.inputs.Any(i=>i.kind=="item"?i.id==itemId:spec.HasTag(i.id)));
  }
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
   if(!HasTools(recipe.requiredTools,stationId)){reason="missing_tool";return false;}
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
   // A tool is an item id or a tool tag, met by the station's own tool or a carried item (20 Nov 2026); only carried items are reserved.
   var tools=CarriedTools(recipe.requiredTools,stationId).ToArray();
   var requirements=recipe.inputs.Concat(tools.Select(id=>new CraftIngredient{kind="item",id=id,quantity=1})).ToArray();
   if(!IngredientAllocator.TryAllocate(requirements,items,Pool,out used)){reason="missing_ingredients";return false;}
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
  /// What the last committed craft paid out (experience and skill use), or null when the craft had no award.
  public CraftAward LastAward {get;private set;}
  /// Experience and skill use for one completed craft. Pure given the counts, so tests can check each step.
  CraftAward Award(CraftRecipe recipe,int craftsBefore)
  {
   LastAward=null;
   if(character==null||recipe==null)return null;
   var award=new CraftAward{recipeId=recipe.id,skill=recipe.skill};
   int levelBefore=character.Level;
   if(recipe.craftXp>0&&character.GrantExperience(recipe.craftXp,out _))award.xp=recipe.craftXp;
   award.levels=character.Level-levelBefore;
   if(!string.IsNullOrEmpty(recipe.skill)&&recipe.skillUse>0)
   {
    award.skillGain=UseGain(recipe,craftsBefore);
    if(award.skillGain>0&&character.GrantSkillUse(recipe.skill,award.skillGain,out int whole))award.skillPoints=whole;
    else award.skillGain=0;
   }
   if(award.xp==0&&award.skillGain<=0)return null;
   return LastAward=award;
  }
  /// Skill points a craft of this schematic adds from use when it has been made craftsBefore times already: the first gain
  /// halves (UseRepeatFactor) with every repeat, is capped per craft and drops to nothing under 0.05.
  public float UseGain(CraftRecipe recipe,int craftsBefore)
  {
   if(recipe==null||string.IsNullOrEmpty(recipe.skill)||recipe.skillUse<=0)return 0;
   float gain=recipe.skillUse*(float)Math.Pow(Math.Max(0,Math.Min(1,data.useRepeatFactor)),Math.Max(0,craftsBefore));
   gain=Math.Min(gain,Math.Max(0,data.useGainCap));
   return gain<0.05f?0:gain;
  }
  public bool TryCraft(string recipeId,string stationId,out string reason)
  {
   if(!ValidateCraft(recipeId,stationId,out var used,out reason))return false;
   var recipe=Recipe(recipeId);
   if(Crafts==int.MaxValue||CraftCount(recipeId)==int.MaxValue){reason="overflow";return false;}
   // the pack's units first; whatever it lacks comes out of the reserve (the home locker) after the pack commits
   var fromReserve=used.Select(x=>new KeyValuePair<string,int>(x.Key,Math.Max(0,x.Value-pack.Quantity(x.Key)))).Where(x=>x.Value>0).ToList();
   var delta=used.Select(x=>new KeyValuePair<string,int>(x.Key,-Math.Min(x.Value,pack.Quantity(x.Key)))).Where(x=>x.Value!=0).ToList();
   delta.Add(new KeyValuePair<string,int>(recipe.outputItemId,recipe.outputQuantity));
   if(fromReserve.Count>0&&(!ReserveActive||fromReserve.Any(x=>Reserve.Quantity(x.Key)<x.Value))){reason="missing_ingredients";return false;}
   if(!pack.TryApply(delta,0,out reason))return false;
   foreach(var x in fromReserve)Reserve.Consume(x.Key,x.Value);
   int before=CraftCount(recipeId);
   Crafts++;crafted[recipeId]=before+1;
   Award(recipe,before);
   Changed?.Invoke();return true;
  }
  /// Fits one carried mod into its slot. A mod already in that slot returns to the pack in the same transaction.
  public bool TryFit(string itemId,out string reason)
   =>TryFit(Loadout.WeaponId,itemId,out reason);
  public bool CanFit(string weaponId,string itemId,out string reason,string stationId=null)
  {
   var loadout=GetLoadout(weaponId);
   if(loadout==null||!HasWeapon(weaponId)){reason="missing_weapon";return false;}
   var mod=loadout.Modifier(itemId);
   if(mod==null){reason="not_a_mod";return false;}
   if(!loadout.Accepts(mod)){reason="wrong_slot";return false;}
   if(!Meets(mod.requirements)){reason="unmet_requirements";return false;}
   if(!HasTools(mod.requiredTools,stationId)){reason="missing_tool";return false;}
   var previous=loadout.Fitted(mod.slot);
   if(previous==itemId){reason="already_fitted";return false;}
   if(pack.Quantity(itemId)<1){reason="not_carried";return false;}
   reason="ok";return true;
  }
  public bool TryFit(string weaponId,string itemId,out string reason,string stationId=null)
  {
   if(!CanFit(weaponId,itemId,out reason,stationId))return false;
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
   if(input.kind=="item")return Pool(input.id);
   long total=0;foreach(var item in items)if(item.HasTag(input.id))total+=Pool(item.id);
   return (int)Math.Min(int.MaxValue,total);
  }
  /// How much of Available comes from the reserve (the home locker), for display.
  public int FromReserve(CraftIngredient input)
  {
   if(input==null||!ReserveActive)return 0;
   if(input.kind=="item")return Reserve.Quantity(input.id);
   long total=0;foreach(var item in items)if(item.HasTag(input.id))total+=Reserve.Quantity(item.id);
   return (int)Math.Min(int.MaxValue,total);
  }
  /// Which skill or attribute requirement of this schematic is unmet ("Requires Engineering 35."), or null when all are met.
  public string UnmetRequirement(CraftRecipe recipe)
  {
   if(recipe?.requirements==null||recipe.requirements.Length==0)return null;
   if(character==null)return "Requires a character.";
   return character.Meets(recipe.requirements,out var why)?null:why;
  }
  bool Meets(CharacterRequirement[] requirements)=>requirements==null||requirements.Length==0||(character!=null&&character.Meets(requirements,out _));
  /// How a tool entry is met: the station's own fixed tool (tag), a carried item with that id, or a carried item with that tag.
  /// carriedId is the carried item that supplies it (null when the station does).
  bool ToolProvided(string tool,string stationId,out string carriedId)
  {
   carriedId=null;
   if(string.IsNullOrEmpty(tool))return false;
   var station=string.IsNullOrEmpty(stationId)?null:data.stations?.FirstOrDefault(s=>s!=null&&s.id==stationId);
   if(station?.tools!=null&&Array.IndexOf(station.tools,tool)>=0)return true;
   if(pack.Quantity(tool)>0){carriedId=tool;return true;}
   foreach(var item in items)if(item.HasTag(tool)&&pack.Quantity(item.id)>0){carriedId=item.id;return true;}
   return false;
  }
  bool HasTools(string[] tools,string stationId=null)=>tools==null||tools.All(id=>ToolProvided(id,stationId,out _));
  IEnumerable<string> CarriedTools(string[] tools,string stationId)
   =>(tools??Array.Empty<string>()).Select(id=>ToolProvided(id,stationId,out var carried)?carried:null).Where(id=>id!=null).Distinct();
  /// The entries of a tool list that neither a carried item nor the station supplies (for the bench's blocked text).
  public List<string> MissingTools(string[] tools,string stationId)
   =>(tools??Array.Empty<string>()).Where(id=>!string.IsNullOrEmpty(id)&&!ToolProvided(id,stationId,out _)).Distinct().ToList();
  /// Where a tool entry comes from right now, for display: "bench", "carried" or "missing".
  public string ToolState(string tool,string stationId){if(!ToolProvided(tool,stationId,out var carried))return "missing";return carried==null?"bench":"carried";}
  /// Carried items that provide a tool entry (an item id entry is itself).
  public IEnumerable<ItemSpec> ToolItems(string tool)=>items.Where(i=>i.id==tool||i.HasTag(tool));
  /// A colonist's dialogue node ran (id "npc_brann:toolkit"): hands over the item that node gives, once (20 Nov 2026).
  /// hasFlag is the story-flag test; the gift's flag is returned so the caller records that it was shown. Nothing is given
  /// when the flag is already set; the item is only added when it is not already carried and fits the pack.
  public ItemSpec Gift(string topicId,Func<string,bool> hasFlag,out string flag)
  {
   flag=null;
   var gift=data.nodeGifts?.FirstOrDefault(g=>g!=null&&g.topic==topicId);
   if(gift==null)return null;
   if(!string.IsNullOrEmpty(gift.flag)&&hasFlag!=null&&hasFlag(gift.flag))return null;
   var item=Item(gift.itemId);
   if(item==null||pack.Quantity(item.id)>0)return null;
   // a full or overloaded pack refuses the gift and leaves the flag unset, so the colonist offers it again next time
   if(!pack.TryApply(new[]{new KeyValuePair<string,int>(item.id,Math.Max(1,gift.quantity))},0,out _))return null;
   flag=gift.flag;
   Changed?.Invoke();return item;
  }
  // ---- Condition: field repair and bench overhaul (20 Nov 2026, Phase 3). Numbers: CraftingCatalog.condition.
  public ConditionRules Condition=>data.condition??(data.condition=new ConditionRules());
  /// The field repair in progress (one at a time), or null. Nothing changes until it completes. recipeId holds the weapon id.
  public CraftJob RepairJob {get;private set;}
  /// A weapon may be field repaired: carried, with a condition, not broken, not at its cap, the tool at hand, nothing else running.
  public bool CanFieldRepair(string weaponId,out string reason)
  {
   var loadout=GetLoadout(weaponId);
   if(loadout==null||!HasWeapon(weaponId)){reason="missing_weapon";return false;}
   if(!loadout.HasCondition){reason="no_condition";return false;}
   if(WeaponCondition.IsBroken(loadout,Condition)){reason="broken";return false;}
   if(RepairGain(weaponId)<=.001f){reason="in_good_order";return false;} // at (or within one repair's cap loss of) its best: a fix would gain nothing
   if(!ToolProvided(Condition.repairTool,null,out _)){reason="missing_tool";return false;}
   if(RepairJob!=null||Job!=null){reason="busy";return false;}
   reason="ok";return true;
  }
  /// Condition the next field repair would give this weapon (0 when none is possible).
  public float RepairGain(string weaponId)
  {
   var loadout=GetLoadout(weaponId);if(loadout==null)return 0;
   float amount=WeaponCondition.NextRepairAmount(loadout,Condition);
   float cap=Math.Max(0,loadout.MaxDurability-Condition.capLossPerRepair);
   return Math.Max(0,Math.Min(cap,loadout.Durability+amount)-loadout.Durability);
  }
  public bool BeginRepair(string weaponId,float now,out string reason)
  {
   if(!CanFieldRepair(weaponId,out reason))return false;
   RepairJob=new CraftJob(weaponId,null,now,Condition.repairSeconds);reason="started";return true;
  }
  /// Completes the repair once its time is up (validated again). amount = condition actually restored.
  public CraftTick TickRepair(float now,out CraftJob job,out string reason,out float amount)
  {
   job=RepairJob;reason="ok";amount=0;
   if(job==null||!job.Done(now))return CraftTick.None;
   RepairJob=null;
   if(!CanFieldRepair(job.recipeId,out reason))return CraftTick.Failed;
   var loadout=GetLoadout(job.recipeId);float before=loadout.Durability;
   loadout.ApplyRepair(WeaponCondition.NextRepairAmount(loadout,Condition),Condition.capLossPerRepair);
   amount=loadout.Durability-before;
   Changed?.Invoke();return CraftTick.Completed;
  }
  /// Stops the repair; nothing changed. False when none was running.
  public bool CancelRepair(out CraftJob job){job=RepairJob;RepairJob=null;return job!=null;}
  /// Bench overhaul (placeholder until Phase 6): restores the cap to the weapon's full condition and resets the repair count, for
  /// Condition.overhaulInputs. Only at Condition.overhaulStationId, only when there is something to restore.
  public bool CanOverhaul(string weaponId,string stationId,out string reason)=>ValidateOverhaul(weaponId,stationId,out _,out reason);
  bool ValidateOverhaul(string weaponId,string stationId,out List<KeyValuePair<string,int>> used,out string reason)
  {
   used=null;
   var loadout=GetLoadout(weaponId);
   if(loadout==null||!HasWeapon(weaponId)){reason="missing_weapon";return false;}
   if(!loadout.HasCondition){reason="no_condition";return false;}
   if(!string.IsNullOrEmpty(Condition.overhaulStationId)&&Condition.overhaulStationId!=stationId){reason="wrong_station";return false;}
   if(loadout.Repairs==0&&loadout.MaxDurability>=loadout.Base.durability-.001f&&loadout.Durability>=loadout.MaxDurability-.001f){reason="in_good_order";return false;}
   if(Job!=null){reason="busy";return false;}
   if(!IngredientAllocator.TryAllocate(Condition.overhaulInputs??Array.Empty<CraftIngredient>(),items,Pool,out used)){reason="missing_ingredients";return false;}
   reason="ok";return true;
  }
  public bool TryOverhaul(string weaponId,string stationId,out string reason)
  {
   if(!ValidateOverhaul(weaponId,stationId,out var used,out reason))return false;
   var fromReserve=used.Select(x=>new KeyValuePair<string,int>(x.Key,Math.Max(0,x.Value-pack.Quantity(x.Key)))).Where(x=>x.Value>0).ToList();
   var delta=used.Select(x=>new KeyValuePair<string,int>(x.Key,-Math.Min(x.Value,pack.Quantity(x.Key)))).Where(x=>x.Value!=0).ToList();
   if(fromReserve.Count>0&&(!ReserveActive||fromReserve.Any(x=>Reserve.Quantity(x.Key)<x.Value))){reason="missing_ingredients";return false;}
   if(delta.Count>0&&!pack.TryApply(delta,0,out reason))return false;
   foreach(var x in fromReserve)Reserve.Consume(x.Key,x.Value);
   GetLoadout(weaponId).ResetCondition();
   Changed?.Invoke();reason="ok";return true;
  }
  static SlotEntry[] CaptureSlots(WeaponLoadout loadout)=>loadout.FittedMods.Select(x=>new SlotEntry{slot=x.Key,itemId=x.Value}).OrderBy(x=>x.slot).ToArray();
  public CraftingState Capture()=>new CraftingState
  {
   known=known.OrderBy(x=>x).ToArray(),crafted=crafted.Select(x=>new CountEntry{id=x.Key,count=x.Value}).OrderBy(x=>x.id).ToArray(),crafts=Crafts,
   fitted=CaptureSlots(Loadout),weapons=loadouts.Values.OrderBy(x=>x.WeaponId).Select(x=>new WeaponLoadoutState{weaponId=x.WeaponId,fitted=CaptureSlots(x),conditionVersion=x.HasCondition?1:0,durability=x.Durability,maxDurability=x.MaxDurability,repairs=x.Repairs}).ToArray()
  };
  /// Save-game restore. Unknown recipe IDs and unfit mods are skipped and returned for the load notice.
  public List<string> Restore(CraftingState state)
  {
   var skipped=new List<string>();
   Job=null; // a fabrication in progress is never saved: nothing was consumed, so nothing is lost
   known.Clear();crafted.Clear();Crafts=0;
   RepairJob=null;
   foreach(var loadout in loadouts.Values){loadout.Replace(null);loadout.ResetCondition();}
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
      // saves before Phase 3 carry no condition (conditionVersion 0): the weapon loads at full condition
      if(saved.conditionVersion>=1&&loadout.HasCondition)loadout.SetCondition(saved.durability,saved.maxDurability,saved.repairs);
     }
    }
    else skipped.AddRange(Loadout.Replace(state.fitted?.Where(x=>x!=null).Select(x=>new KeyValuePair<string,string>(x.slot,x.itemId))));
   }
   Changed?.Invoke();
   return skipped;
  }
 }
 public enum CraftTick { None, Completed, Failed }
 /// What a completed craft paid out: character XP, levels it brought, and skill use (gain = fractional points, points = whole
 /// points added to the trained skill).
 public sealed class CraftAward
 {
  public string recipeId,skill;
  public int xp,levels,skillPoints;
  public float skillGain;
 }
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
 [Serializable] public class WeaponLoadoutState {public string weaponId;public SlotEntry[] fitted;public int conditionVersion;public float durability,maxDurability;public int repairs;}
 [Serializable] public class CraftingState
 {
  public string[] known;
  public CountEntry[] crafted;
  public int crafts;
  public SlotEntry[] fitted;
  public WeaponLoadoutState[] weapons;
 }
}
