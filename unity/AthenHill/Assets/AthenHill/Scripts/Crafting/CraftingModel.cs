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
  readonly HashSet<string> known=new HashSet<string>();
  readonly Dictionary<string,int> crafted=new Dictionary<string,int>();
  public CraftingCatalog Data=>data;
  public WeaponLoadout Loadout {get;}
  public IReadOnlyCollection<string> KnownRecipes=>known;
  public IReadOnlyDictionary<string,int> CraftCounts=>crafted;
  public int Crafts {get;private set;}
  public float BaseRecoil=>Loadout.Base.recoil;
  public float RecoilStat=>Loadout.Stats.recoil;
  /// Raised after a committed craft, fit, removal, unlock or restore.
  public event Action Changed;
  public CraftingModel(CraftingCatalog data,IEnumerable<ItemSpec> items,ShopModel pack,Func<bool> hasWeapon,string weaponId=null)
  {
   this.data=data;this.items=items.ToArray();this.pack=pack;this.hasWeapon=hasWeapon;
   var weapon=weaponId==null?data.weapons.First():data.weapons.First(w=>w.id==weaponId);
   Loadout=new WeaponLoadout(weapon,data.modifiers);
   foreach(var recipe in data.recipes)if(recipe.knownByDefault)known.Add(recipe.id);
  }
  public CraftRecipe Recipe(string id)=>data.recipes.FirstOrDefault(x=>x.id==id);
  public ItemSpec Item(string id)=>items.FirstOrDefault(x=>x.id==id);
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
   if(recipe.stationId!=stationId){reason="wrong_station";return false;}
   if(!string.IsNullOrEmpty(recipe.requiresWeaponId)&&(recipe.requiresWeaponId!=Loadout.WeaponId||!hasWeapon())){reason="missing_weapon";return false;}
   if(recipe.outputQuantity<1||recipe.inputs==null||recipe.inputs.Any(x=>x.kind=="item"&&x.id==recipe.outputItemId)){reason="invalid_recipe";return false;}
   var output=Item(recipe.outputItemId);
   if(output==null){reason="unknown_item";return false;}
   if(!IngredientAllocator.TryAllocate(recipe.inputs,items,pack,out used)){reason="missing_ingredients";return false;}
   if(output.maxStack>0&&(long)pack.Quantity(output.id)+recipe.outputQuantity>output.maxStack){reason="output_stack_full";return false;}
   reason="ok";return true;
  }
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
  {
   if(!hasWeapon()){reason="missing_weapon";return false;}
   var mod=Loadout.Modifier(itemId);
   if(mod==null){reason="not_a_mod";return false;}
   if(!Loadout.Accepts(mod)){reason="wrong_slot";return false;}
   var previous=Loadout.Fitted(mod.slot);
   if(previous==itemId){reason="already_fitted";return false;}
   if(pack.Quantity(itemId)<1){reason="not_carried";return false;}
   var delta=new List<KeyValuePair<string,int>>{new KeyValuePair<string,int>(itemId,-1)};
   if(previous!=null)delta.Add(new KeyValuePair<string,int>(previous,1));
   if(!pack.TryApply(delta,0,out reason))return false;
   Loadout.Set(mod.slot,itemId);Changed?.Invoke();return true;
  }
  public bool TryRemove(string slot,out string reason)
  {
   if(!hasWeapon()){reason="missing_weapon";return false;}
   if(!Loadout.HasSlot(slot)){reason="wrong_slot";return false;}
   var current=Loadout.Fitted(slot);
   if(current==null){reason="empty_slot";return false;}
   if(!pack.TryApply(new[]{new KeyValuePair<string,int>(current,1)},0,out reason))return false;
   Loadout.Set(slot,null);Changed?.Invoke();return true;
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
  public CraftingState Capture()=>new CraftingState{known=known.OrderBy(x=>x).ToArray(),crafted=crafted.Select(x=>new CountEntry{id=x.Key,count=x.Value}).OrderBy(x=>x.id).ToArray(),crafts=Crafts,fitted=Loadout.FittedMods.Select(x=>new SlotEntry{slot=x.Key,itemId=x.Value}).OrderBy(x=>x.slot).ToArray()};
  /// Save-game restore. Unknown recipe IDs and unfit mods are skipped and returned for the load notice.
  public List<string> Restore(CraftingState state)
  {
   var skipped=new List<string>();
   known.Clear();crafted.Clear();Crafts=0;
   foreach(var recipe in data.recipes)if(recipe.knownByDefault)known.Add(recipe.id);
   if(state!=null)
   {
    if(state.known!=null)foreach(var id in state.known){if(Recipe(id)!=null)known.Add(id);else skipped.Add(id);}
    if(state.crafted!=null)foreach(var c in state.crafted)if(c!=null&&Recipe(c.id)!=null&&c.count>0)crafted[c.id]=c.count;
    Crafts=Math.Max(Math.Max(0,state.crafts),crafted.Values.Sum());
    skipped.AddRange(Loadout.Replace(state.fitted?.Where(x=>x!=null).Select(x=>new KeyValuePair<string,string>(x.slot,x.itemId))));
   }
   else Loadout.Replace(null);
   Changed?.Invoke();
   return skipped;
  }
 }
 [Serializable] public class CountEntry {public string id;public int count;}
 [Serializable] public class SlotEntry {public string slot,itemId;}
 [Serializable] public class CraftingState
 {
  public string[] known;
  public CountEntry[] crafted;
  public int crafts;
  public SlotEntry[] fitted;
 }
}
