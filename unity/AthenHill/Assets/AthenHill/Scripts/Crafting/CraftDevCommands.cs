#if UNITY_EDITOR || DEBUG
using System;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEngine;
namespace AthenHill
{
 /// dev.craft.* developer operations for the Steady Hands bench (craft agent, 20 Nov 2026; development players only).
 /// DevBridgeCommands.Execute forwards every "dev.craft." action here (one-line hook owned by the bench agent):
 ///   if (action.StartsWith("dev.craft.", StringComparison.Ordinal)) return CraftDevCommands.Execute(action, command, session, adjustable);
 ///  dev.craft.handmade {recipeId}                         record a hands-on recipe as made by hand (opens the timer)
 ///  dev.craft.fit {itemId, quality?, weaponId?}           grant one mod and fit it at Rough / Standard / Fine (no bench, no inputs)
 ///  dev.craft.strip {slot, weaponId?}                     empty a slot (the mod is removed and discarded): the bare weapon
 ///  dev.craft.heat {}                                     cool the drawn weapon (rapid-fire heat to 0) before a timed string
 public static class CraftDevCommands
 {
  static readonly Regex Id=new Regex("^[a-z][a-z0-9_]{1,63}$",RegexOptions.CultureInvariant);
  static string Str(JObject c,string key)=>c?[key]?.Type==JTokenType.String?(string)c[key]:null;
  public static DevBridgeCommands.Result Execute(string action,JObject command,GameSession session,bool adjustable)
  {
   var crafting=session?session.GetComponent<CraftingSession>():null;var model=crafting?crafting.Model:null;
   if(model==null)return DevBridgeCommands.Result.Fail("unavailable","The crafting system is not ready.");
   if(!adjustable)return DevBridgeCommands.Result.Fail("invalid_state","Crafting developer controls need Play, Paused, Inventory or Shop.");
   string weaponId=Str(command,"weaponId")??model.Loadout.WeaponId;
   if(!Id.IsMatch(weaponId)||model.GetLoadout(weaponId)==null)return DevBridgeCommands.Result.Fail("unknown_weapon","Unknown weapon id.");
   switch(action)
   {
    case "dev.craft.handmade":
    {
     var recipe=Str(command,"recipeId");
     if(recipe==null||!Id.IsMatch(recipe)||!model.HasAssembly(recipe))return DevBridgeCommands.Result.Fail("unknown_recipe","recipeId must name a recipe with a bench job.");
     model.MarkHandMade(recipe);session.DevChanged("Recipe marked as made by hand.");return DevBridgeCommands.Result.Ok();
    }
    case "dev.craft.fit":
    {
     var item=Str(command,"itemId");var q=Str(command,"quality")??"Standard";
     if(item==null||!Id.IsMatch(item))return DevBridgeCommands.Result.Fail("invalid_argument","itemId is required.");
     if(!Enum.TryParse(q,false,out CraftQuality quality)||!Enum.IsDefined(typeof(CraftQuality),quality))return DevBridgeCommands.Result.Fail("invalid_argument","quality is Rough, Standard or Fine.");
     if(!model.DevFit(weaponId,item,quality,out var why))return DevBridgeCommands.Result.Fail("refused",CraftingText.Reason(why,model,null,item));
     session.DevChanged($"{CraftingText.WithQuality(model,item,quality,true)} fitted.");return DevBridgeCommands.Result.Ok();
    }
    case "dev.craft.strip":
    {
     var slot=Str(command,"slot");
     if(slot==null||!Id.IsMatch(slot))return DevBridgeCommands.Result.Fail("invalid_argument","slot is required.");
     if(!model.DevStrip(weaponId,slot,out var why))return DevBridgeCommands.Result.Fail("refused",CraftingText.Reason(why,model));
     session.DevChanged("Slot emptied.");return DevBridgeCommands.Result.Ok();
    }
    case "dev.craft.heat":
    {
     var combat=crafting.combat?crafting.combat:UnityEngine.Object.FindAnyObjectByType<PlayerCombat>();
     if(combat)combat.CoolDown();return DevBridgeCommands.Result.Ok();
    }
   }
   return DevBridgeCommands.Result.Fail("unknown_action","Unknown developer operation.");
  }
 }
}
#endif
