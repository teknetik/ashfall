using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// Player-facing words for crafting results. Names come from the catalogs; reason codes never reach the screen.
 public static class CraftingText
 {
  /// Where crafting happens (1 Oct 2026: Brann's workbench in the Salvage shop on the north avenue).
  public const string WorkbenchName="Salvage workbench";
  public const string Workbench="the workbench at Salvage";
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
  /// Bench time for display: "8 s", "1:05" (whole seconds, rounded up so it never reads 0 while working).
  public static string Duration(float seconds)
  {
   int s=Math.Max(0,(int)Math.Ceiling(seconds-1e-4));
   return s<60?$"{s} s":$"{s/60}:{s%60:00}";
  }
  public static string Reason(string code,CraftingModel model,CraftRecipe recipe=null,string itemId=null)
  {
   if(!string.IsNullOrEmpty(code)&&code.Contains(" "))return code;
   switch(code)
   {
    case "ok":return "";
    case "recipe_locked":return "Schematic not yet known."+(string.IsNullOrEmpty(recipe?.lockedHint)?"":" "+recipe.lockedHint);
    case "wrong_station":
    {
     var station=model?.Data.stations?.FirstOrDefault(x=>x.id==recipe?.stationId);
     return station!=null?$"This schematic needs {station.name}.":"Use the station specified by this schematic.";
    }
    case "missing_weapon":return "You need to carry or equip the required weapon first.";
    case "unmet_requirements":return "Your attributes or skills do not yet meet the requirements.";
    case "missing_tool":return "A required reusable tool is missing from your pack.";
    case "missing_schematic":return "Learn the prerequisite schematic first.";
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
    case "not_a_mod":return "That item is not a weapon mod.";
    case "wrong_slot":return "That part does not fit this weapon's sockets.";
    case "empty_slot":return "Nothing is fitted in that slot.";
    case "overflow":return "The fabricator's counters are full.";
    case "busy":return "The bench is already working on a piece. Wait for it or cancel it.";
    case "cancelled":return "Fabrication stopped. Nothing was used.";
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
  /// "Recoil 38 → 31 · Damage 34 → 40.8" for a notice after fitting. Each change is kept on one line (no-break
  /// spaces, and a division slash in units such as "/s" so "39/s" never wraps as "39/ s"); lines break only at " · ".
  public static string StatChanges(CraftingCatalog data,WeaponStats before,WeaponStats after)
  {
   var parts=new List<string>();
   for(int i=0;i<WeaponStats.Count;i++)
   {
    if(Math.Abs(before[i]-after[i])<.0005f)continue;
    var label=data.Stat(WeaponStats.Ids[i]);
    parts.Add(NoBreak($"{(label!=null?label.label:WeaponStats.Ids[i])} {FormatStat(label,before[i])} → {FormatStat(label,after[i])}"));
   }
   return string.Join(" · ",parts);
  }
  /// Keeps a phrase on one line: spaces become no-break spaces and "/" a division slash (both in ColonySans).
  public static string NoBreak(string text)=>text?.Replace(' ','\u00A0').Replace('/','\u2215');
 }
}
