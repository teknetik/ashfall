using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// Player-facing words for crafting results. Names come from the catalogs; reason codes never reach the screen.
 public static class CraftingText
 {
  public static string InputName(CraftingModel model,CraftIngredient input)
  {
   if(input==null)return "";
   if(input.kind=="item"){var item=model.Item(input.id);return item!=null?item.name:input.id;}
   return model.Data.TagName(input.id);
  }
  public static string ItemName(CraftingModel model,string id){var item=model.Item(id);return item!=null?item.name:id;}
  /// "2 × Micro Capacitor, 3 × Any tier-one nanites" — only the lines still short.
  public static string Shortfall(CraftingModel model,CraftRecipe recipe)
  {
   if(recipe?.inputs==null)return "";
   var parts=new List<string>();
   foreach(var input in recipe.inputs)
   {
    int missing=input.quantity-model.Available(input);
    if(missing>0)parts.Add($"{missing} × {InputName(model,input)}");
   }
   return string.Join(", ",parts);
  }
  public static string Reason(string code,CraftingModel model,CraftRecipe recipe=null,string itemId=null)
  {
   switch(code)
   {
    case "ok":return "";
    case "recipe_locked":return "Schematic not yet known."+(string.IsNullOrEmpty(recipe?.lockedHint)?"":" "+recipe.lockedHint);
    case "wrong_station":return "This schematic needs the Warden field fabricator.";
    case "missing_weapon":return "Take the scrap pistol from the Warden arms locker first.";
    case "missing_ingredients":
    {
     var shortfall=model!=null&&recipe!=null?Shortfall(model,recipe):"";
     // Every line can look covered while one carried part is claimed by two lines.
     return string.IsNullOrEmpty(shortfall)?"Missing parts: a carried part is already needed by another line.":"Missing parts: "+shortfall+".";
    }
    case "output_stack_full":{var item=model?.Item(recipe?.outputItemId);return item!=null?$"Your pack cannot hold another {item.name} (limit {item.maxStack}).":"Your pack cannot hold another of those.";}
    case "stack_full":return itemId!=null&&model!=null?$"No room in your pack to take back the {ItemName(model,itemId)}.":"No room in your pack for that.";
    case "already_fitted":return "That mod is already fitted.";
    case "not_carried":return itemId!=null&&model!=null?$"You are not carrying a {ItemName(model,itemId)}. Fabricate one first.":"You are not carrying that mod.";
    case "not_a_mod":return "That is a component for other schematics, not a pistol mod.";
    case "wrong_slot":return "That part does not fit the scrap pistol.";
    case "empty_slot":return "Nothing is fitted in that slot.";
    case "overflow":return "The fabricator's counters are full.";
    case "insufficient_items":return "Those parts are no longer in your pack.";
    case "unknown_recipe":case "invalid_recipe":case "unknown_item":return "This schematic record is damaged; check the crafting data.";
    default:return "The fabricator refused that operation.";
   }
  }
  /// "Schematic discovered: Charge Cell Core, Salvaged Capacitor Cell."
  public static string Discovered(IEnumerable<CraftRecipe> recipes)
  {
   var names=recipes?.Where(x=>x!=null).Select(x=>x.name).ToList();
   if(names==null||names.Count==0)return "";
   return (names.Count==1?"Schematic discovered: ":"Schematics discovered: ")+string.Join(", ",names)+".";
  }
  public static string FormatStat(StatLabel label,float value)=>value.ToString(label!=null&&!string.IsNullOrEmpty(label.format)?label.format:"0.#")+(label!=null&&!string.IsNullOrEmpty(label.unit)?label.unit:"");
  /// Signed change for the stats table, e.g. "+6.8", "−7". Empty when unchanged.
  public static string FormatDelta(StatLabel label,float delta)
  {
   if(Math.Abs(delta)<.0005f)return "";
   string format=label!=null&&!string.IsNullOrEmpty(label.format)?label.format:"0.#";
   string text=Math.Abs(delta).ToString(format);
   if(text.Trim('0','.',',')=="")text=Math.Abs(delta).ToString("0.###");
   return (delta>0?"+":"−")+text+(label!=null&&!string.IsNullOrEmpty(label.unit)?label.unit:"");
  }
  /// True when the change is an improvement for this stat (for green/red colouring).
  public static bool Improves(StatLabel label,float delta)=>label!=null&&label.lowerIsBetter?delta<0:delta>0;
  /// "Recoil 38 → 31 · Damage 34 → 40.8" for a notice after fitting.
  public static string StatChanges(CraftingCatalog data,WeaponStats before,WeaponStats after)
  {
   var parts=new List<string>();
   for(int i=0;i<WeaponStats.Count;i++)
   {
    if(Math.Abs(before[i]-after[i])<.0005f)continue;
    var label=data.Stat(WeaponStats.Ids[i]);
    parts.Add($"{(label!=null?label.label:WeaponStats.Ids[i])} {FormatStat(label,before[i])} → {FormatStat(label,after[i])}");
   }
   return string.Join(" · ",parts);
  }
 }
}
