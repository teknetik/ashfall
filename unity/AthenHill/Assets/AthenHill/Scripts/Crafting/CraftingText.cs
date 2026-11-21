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
  /// A tool entry for the player: an item id gives the item's name, a tool tag its catalog label ("Screwdriver").
  public static string ToolName(CraftingModel model,string tool)
  {
   var item=model?.Item(tool);if(item!=null)return item.name;
   var label=model?.Data.TagName(tool);
   return string.IsNullOrEmpty(label)||label==tool?(tool??"").Replace("tool:","").Replace('_',' '):label;
  }
  /// "Carry a Field Toolkit." for tools a carried item provides; "Use a bench that has it." for fixed tools.
  public static string ToolHint(CraftingModel model,IEnumerable<string> missing)
  {
   var carried=new List<string>();bool fixedTool=false;
   foreach(var tool in missing)
   {
    var names=model.ToolItems(tool).Select(i=>i.name).Distinct().ToList();
    if(names.Count>0)carried.AddRange(names);else fixedTool=true;
   }
   var parts=new List<string>();
   if(carried.Count>0)parts.Add("Carry a "+string.Join(" or ",carried.Distinct())+".");
   if(fixedTool)parts.Add("It is fixed to a bench that has it.");
   return string.Join(" ",parts);
  }
  /// One line for a recipe's tool requirement: "Tool: Screwdriver (carried)" / "(at this bench)" / "(missing)".
  public static string ToolLine(CraftingModel model,string tool,string stationId)
  {
   string state=model.ToolState(tool,stationId);
   return $"Tool: {ToolName(model,tool)} ({(state=="bench"?"at this bench":state)})";
  }
  /// Experience and skill use of a completed craft for the notice: "+12 XP · Engineering +1".
  public static string AwardText(CraftingModel model,CraftAward award)
  {
   if(award==null)return "";
   var parts=new List<string>();
   if(award.xp>0)parts.Add($"+{award.xp} XP"+(award.levels>0?" · level up":""));
   if(award.skillGain>0&&!string.IsNullOrEmpty(award.skill))
   {
    string name=char.ToUpperInvariant(award.skill[0])+award.skill.Substring(1);
    parts.Add($"{name} {(award.skillPoints>0?"+"+award.skillPoints:"practice")}");
   }
   return parts.Count==0?"":" "+string.Join(" · ",parts)+".";
  }
  public static string ItemName(CraftingModel model,string id){var item=model.Item(id);return item!=null?item.name:id;}
  /// "2 × Micro Capacitor, 3 × Any tier-one nanites" — only the lines still short.
  public static string Shortfall(CraftingModel model,CraftRecipe recipe)
  {
   if(model==null||recipe?.inputs==null)return "";
   var parts=new List<string>();
   foreach(var input in recipe.inputs)
   {
    if(input==null)continue;
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
  /// Why a field repair or overhaul was refused (20 Nov 2026, Phase 3), in the player's words.
  public static string ConditionReason(string code,CraftingModel model,WeaponLoadout loadout=null)
  {
   string name=loadout!=null?loadout.WeaponName:"weapon";
   var rules=model?.Condition;
   switch(code)
   {
    case "no_condition":return $"The {name} does not wear.";
    case "missing_weapon":return $"You are not carrying the {name}.";
    case "broken":return $"The {name} is worn past a field fix (its best condition is down to {(loadout!=null?Math.Floor(loadout.MaxDurability):0):0}). It needs a bench overhaul at "+Workbench+".";
    case "in_good_order":return loadout!=null&&loadout.Repairs>0?$"The {name} is as good as the field can make it. A bench overhaul at {Workbench} restores its best condition.":$"The {name} is in good order.";
    case "missing_tool":return "Missing tool: "+ToolName(model,rules?.repairTool)+". Carry a Field Toolkit.";
    case "busy":return "Finish what you are doing first.";
    case "on_bench":return $"The {name} is on the bench in pieces. Finish the job at "+Workbench+" or abandon it there.";
    case "wrong_station":return "A weapon overhaul is done at "+Workbench+".";
    case "missing_ingredients":return "Missing parts for the overhaul: "+OverhaulCost(model)+".";
    default:return "That repair is not possible.";
   }
  }
  /// "Condition 76 / 92 · worn" (empty for a weapon that does not wear).
  public static string Condition(WeaponLoadout loadout,CraftingModel model)=>WeaponCondition.Label(loadout,model?.Condition);
  /// "3 × Scrap Alloy, 4 × Any tier-one nanites".
  public static string OverhaulCost(CraftingModel model)
   =>string.Join(", ",(model?.Condition?.overhaulInputs??Array.Empty<CraftIngredient>()).Where(i=>i!=null).Select(i=>$"{i.quantity} × {InputName(model,i)}"));
  public static string Reason(string code,CraftingModel model,CraftRecipe recipe=null,string itemId=null)
  {
   if(!string.IsNullOrEmpty(code)&&code.Contains(" "))return code;
   switch(code)
   {
    case "ok":return "";
    case "recipe_locked":return "Schematic not yet known."+(string.IsNullOrEmpty(recipe?.lockedHint)?"":" "+recipe.lockedHint);
    case "wrong_station":
    {
     var station=model?.Data.stations?.FirstOrDefault(x=>x!=null&&x.id==recipe?.stationId);
     return station!=null?$"This schematic needs {station.name}.":"Use the station specified by this schematic.";
    }
    case "missing_weapon":
    {
     var weapon=model!=null&&!string.IsNullOrEmpty(recipe?.requiresWeaponId)?model.GetLoadout(recipe.requiresWeaponId):null;
     return weapon!=null?$"You need to carry or equip the {weapon.WeaponName} first.":"You need to carry or equip the required weapon first.";
    }
    case "unmet_requirements":
    {
     var unmet=model?.UnmetRequirement(recipe);
     return string.IsNullOrEmpty(unmet)?"Your attributes or skills do not yet meet the requirements.":"Your skill is too low. "+unmet;
    }
    case "missing_tool":
    {
     string[] reqTools=recipe?.requiredTools??(itemId!=null?model?.Loadout?.Modifier(itemId)?.requiredTools:null);
     var missing=model!=null&&reqTools!=null?model.MissingTools(reqTools,recipe?.stationId):null;
     return missing!=null&&missing.Count>0?"Missing tool: "+string.Join(", ",missing.Select(x=>ToolName(model,x)))+". "+ToolHint(model,missing):"A required reusable tool is missing from your pack.";
    }
    case "missing_schematic":
    {
     var missing=model!=null&&recipe?.requiredSchematics!=null?recipe.requiredSchematics.Where(id=>!string.IsNullOrEmpty(id)&&!model.Knows(id)).Select(id=>model.Recipe(id)?.name??id).Distinct().ToList():null;
     return missing!=null&&missing.Count>0?"Learn the prerequisite schematic first: "+string.Join(", ",missing)+".":"Learn the prerequisite schematic first.";
    }
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
    // Steady Hands bench (20 Nov 2026)
    case "hand_made_first":return $"The {(recipe!=null?ItemName(model,recipe.outputItemId):"part")} is built by hand at the bench, every time: Build by hand.";
    case "on_bench":return itemId!=null&&model!=null?$"The {WeaponOnBench(model,itemId)} is on the bench in pieces. Finish the job or abandon it at the bench.":"That job is open on the bench. Carry on with it by hand.";
    case "bench_busy":{var open=model?.OpenTicket!=null?model.Recipe(model.OpenTicket.recipeId):null;return open!=null?$"The bench is still set up for the {ItemName(model,open.outputItemId)}. Finish or abandon that job first.":"The bench is set up for another job. Finish or abandon it first.";}
    case "no_assembly":return "This schematic is made on the timer.";
    case "no_job":return "Nothing is on the bench.";
    case "byproducts_left":return "Your pack was too full for the spare parts; they stayed on the bench.";
    case "unknown_recipe":case "invalid_recipe":case "unknown_item":return "This schematic record is damaged; check the crafting data.";
    default:return "The fabricator refused that operation.";
   }
  }
  /// The weapon name for an on-bench notice: itemId may be a weapon id, a weapon item id or a mod.
  static string WeaponOnBench(CraftingModel model,string id)
  {
   var loadout=model.GetLoadout(model.OpenTicket?.weaponId)??model.GetLoadout(id);
   return loadout!=null?loadout.WeaponName:ItemName(model,id);
  }
  /// "Rough", "Standard", "Fine".
  public static string QualityName(CraftQuality q)=>q.ToString();
  /// "Stabilised Pistol Grip · Fine" for a part made by hand; plain name for Standard unless always is set.
  public static string WithQuality(CraftingModel model,string itemId,CraftQuality q,bool always=false)
   =>ItemName(model,itemId)+(always||q!=CraftQuality.Standard?" · "+QualityName(q):"");
  /// The loadout panel's state line for a weapon taken apart on the bench.
  public const string OnBenchLabel="On Brann's bench";
  /// The mod in a weapon slot with its crafted quality: "Stabilised Pistol Grip · Fine". Parts that can be made by hand always
  /// name their quality; others only when it is not Standard. Null when the slot is empty.
  public static string FittedName(CraftingModel model,WeaponLoadout loadout,string slot)
  {
   var item=loadout?.Fitted(slot);if(item==null||model==null)return null;
   bool hands=model.Data.recipes.Any(r=>r.outputItemId==item&&!string.IsNullOrEmpty(r.assembly));
   return WithQuality(model,item,loadout.Quality(slot),hands);
  }
  /// Display name of the colonist with this NpcDefinition id ("npc_ossa" -> "Warden Ossa"); the id itself when unknown.
  public static string NpcName(GameSession session,string npcId)
  {
   var npc=session&&session.npcs!=null?session.npcs.FirstOrDefault(n=>n&&n.definition&&n.definition.id==npcId):null;
   return npc?npc.definition.displayName:npcId;
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
