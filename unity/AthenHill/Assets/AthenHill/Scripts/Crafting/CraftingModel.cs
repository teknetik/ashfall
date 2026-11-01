using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// Two deliberate transactions: crafting makes a carried item; fitting consumes it into the slot.
 public sealed class CraftingModel
 {
  readonly CraftingCatalog data;
  readonly ItemSpec[] items;
  readonly ShopModel pack;
  readonly Func<bool> hasPistol;
  readonly HashSet<string> known=new HashSet<string>();
  public IReadOnlyCollection<string> KnownRecipes=>known;
  public string GripSlot {get;private set;}
  public int Crafts {get;private set;}
  public float BaseRecoil=>data.weapons.First(w=>w.id=="weapon_scrap_pistol").recoil;
  public float RecoilStat
  {
   get
   {
    float add=0,percent=0;
    var mod=data.modifiers.FirstOrDefault(x=>x.itemId==GripSlot);
    if(mod?.effects!=null)foreach(var effect in mod.effects)if(effect.stat=="recoil")
    {if(effect.op=="add")add+=effect.value;else if(effect.op=="percent")percent+=effect.value;}
    return Math.Max(0,Math.Min(100,(float)Math.Round((BaseRecoil+add)*(1+percent/100f),1,MidpointRounding.AwayFromZero)));
   }
  }
  public CraftingModel(CraftingCatalog data,IEnumerable<ItemSpec> items,ShopModel pack,Func<bool> hasPistol)
  {
   this.data=data;this.items=items.ToArray();this.pack=pack;this.hasPistol=hasPistol;
   foreach(var recipe in data.recipes)if(recipe.knownByDefault)known.Add(recipe.id);
  }
  public bool Acquire(string itemId)
  {
   bool unlocked=false;
   foreach(var recipe in data.recipes)if(recipe.unlocks!=null&&recipe.unlocks.Any(x=>x.type=="acquireItem"&&x.id==itemId))unlocked|=known.Add(recipe.id);
   return unlocked;
  }
  public bool UnlockStep(string step)
  {
   bool unlocked=false;
   foreach(var recipe in data.recipes)if(recipe.unlocks!=null&&recipe.unlocks.Any(x=>x.type=="tutorialStep"&&x.id==step))unlocked|=known.Add(recipe.id);
   return unlocked;
  }
  public bool CanCraft(string recipeId,string stationId,out string reason)=>ValidateCraft(recipeId,stationId,out _,out reason);
  bool ValidateCraft(string recipeId,string stationId,out List<KeyValuePair<string,int>> used,out string reason)
  {
   used=null;
   var recipe=data.recipes.FirstOrDefault(x=>x.id==recipeId);
   if(recipe==null){reason="unknown_recipe";return false;}
   if(!known.Contains(recipeId)){reason="recipe_locked";return false;}
   if(recipe.stationId!=stationId){reason="wrong_station";return false;}
   if(recipe.requiresWeaponId=="weapon_scrap_pistol"&&!hasPistol()){reason="missing_weapon";return false;}
   if(recipe.outputQuantity<1||recipe.inputs==null||recipe.inputs.Any(x=>x.kind=="item"&&x.id==recipe.outputItemId)){reason="invalid_recipe";return false;}
   if(!IngredientAllocator.TryAllocate(recipe.inputs,items,pack,out used)){reason="missing_ingredients";return false;}
   var output=items.FirstOrDefault(x=>x.id==recipe.outputItemId);
   if(output==null){reason="unknown_item";return false;}
   if(output.maxStack>0&&(long)pack.Quantity(output.id)+recipe.outputQuantity>output.maxStack){reason="output_stack_full";return false;}
   reason="ok";return true;
  }
  public bool TryCraft(string recipeId,string stationId,out string reason)
  {
   if(!ValidateCraft(recipeId,stationId,out var used,out reason))return false;
   var recipe=data.recipes.First(x=>x.id==recipeId);
   if(Crafts==int.MaxValue){reason="overflow";return false;}
   var delta=used.Select(x=>new KeyValuePair<string,int>(x.Key,-x.Value)).ToList();
   delta.Add(new KeyValuePair<string,int>(recipe.outputItemId,recipe.outputQuantity));
   if(!pack.TryApply(delta,0,out reason))return false;
   Crafts++;return true;
  }
  public bool TryFit(string itemId,out string reason)
  {
   if(!hasPistol()){reason="missing_weapon";return false;}
   var mod=data.modifiers.FirstOrDefault(x=>x.itemId==itemId);
   if(mod==null){reason="not_a_mod";return false;}
   if(mod.slot!="grip"||mod.weaponIds==null||Array.IndexOf(mod.weaponIds,"weapon_scrap_pistol")<0){reason="wrong_slot";return false;}
   if(GripSlot==itemId){reason="already_fitted";return false;}
   if(pack.Quantity(itemId)<1){reason="not_carried";return false;}
   var delta=new List<KeyValuePair<string,int>>{new KeyValuePair<string,int>(itemId,-1)};
   if(GripSlot!=null)delta.Add(new KeyValuePair<string,int>(GripSlot,1));
   if(!pack.TryApply(delta,0,out reason))return false;
   GripSlot=itemId;return true;
  }
  public bool TryRemove(out string reason)
  {
   if(!hasPistol()){reason="missing_weapon";return false;}
   if(GripSlot==null){reason="empty_slot";return false;}
   if(!pack.TryApply(new[]{new KeyValuePair<string,int>(GripSlot,1)},0,out reason))return false;
   GripSlot=null;return true;
  }
 }
}
