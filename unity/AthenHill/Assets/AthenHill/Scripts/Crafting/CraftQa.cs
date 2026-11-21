using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Steady Hands bench state for NativeQa's crafting.json (craft agent, 20 Nov 2026). NativeQa adds one field (hook owned by
 /// the bench agent): ...,craftJob=...,bench=CraftQa.Snapshot(crafting,combat)}
 /// Plain fields only, so it serialises as it stands.
 public static class CraftQa
 {
  public static object Snapshot(CraftingSession crafting,PlayerCombat combat)
  {
   var model=crafting?crafting.Model:null;if(model==null)return null;
   var t=model.OpenTicket;var loadout=combat&&combat.Loadout!=null?combat.Loadout:model.Loadout;
   var h=model.HandlingFor(loadout.WeaponId);
   return new
   {
    ticket=t==null?null:new{t.recipeId,t.stationId,t.weaponId,t.resumed,inputs=(t.inputs??new ItemStack[0]).Select(s=>new{s.itemId,s.quantity}).ToArray(),stageId=model.AssemblyStageId,stageLabel=model.AssemblyStageLabel,blobLength=model.AssemblyBlob?.Length??0},
    handMade=model.HandMadeRecipes.OrderBy(x=>x).ToArray(),
    weaponId=loadout.WeaponId,onBench=model.OnBench(loadout.WeaponId),
    qualities=loadout.FittedMods.ToDictionary(x=>x.Key,x=>loadout.Quality(x.Key).ToString()),
    handling=new{h.sway,h.kick,h.sideStep,h.recovery,h.scatterGrowth,overshoot=WeaponHandlingRules.OvershootFraction(h.recovery)},
    shot=combat?new{heat=combat.Heat,lastHeatScale=combat.LastHeatScale,lastCone=combat.LastCone,lastKick=combat.LastKickDegrees,lastSideKick=combat.LastSideKick,dir=new[]{combat.LastShotDirection.x,combat.LastShotDirection.y,combat.LastShotDirection.z},end=new[]{combat.LastShotEnd.x,combat.LastShotEnd.y,combat.LastShotEnd.z},lastShotTime=combat.LastShotTime,now=Time.time,combat.ShotsFired,combat.Hits,combat.Rattled,combat.DamperTicks}:null,
    lastAssembly=model.LastAssembly==null?null:new{model.LastAssembly.recipeId,quality=model.LastAssembly.quality.ToString(),model.LastAssembly.score,model.LastAssembly.faults,fitted=model.LastAssemblyFitted}
   };
  }
 }
}
