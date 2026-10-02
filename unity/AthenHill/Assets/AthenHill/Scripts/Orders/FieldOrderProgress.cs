using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
namespace AthenHill
{
 /// Report: the parts are gathered and the order's report-to colonist has not been visited yet (appended last, so
 /// existing numeric values are unchanged).
 public enum OrderStage { NotStarted, Gather, Fabricate, Fit, TestFire, Hunt, Craft, FreePlay, Report }
 /// Pure field-order state machine. The index only ever moves forward, so repeating a finished task (crafting or
 /// fitting again, firing again) can never restart an order or repeat Ossa's completion line.
 public sealed class FieldOrderProgress
 {
  readonly HashSet<string> testFired=new HashSet<string>();
  readonly HashSet<string> reported=new HashSet<string>();
  public FieldOrderSet Data {get;}
  /// −1 before the primer is complete; orders.Length once every order is done (free play).
  public int Index {get;private set;}=-1;
  public bool Started=>Index>=0;
  public bool FreePlay=>Index>=Data.orders.Length;
  public FieldOrder Current=>Started&&!FreePlay?Data.orders[Index]:null;
  public FieldOrderProgress(FieldOrderSet data){Data=data??throw new ArgumentNullException(nameof(data));}
  /// The primer is complete: the first order becomes current. Null if orders had already begun.
  public FieldOrder Begin(){if(Started)return null;Index=0;return Current;}
  static bool Fitted(CraftingModel model,string itemId)=>model.Loadout.FittedMods.Any(x=>x.Value==itemId);
  public bool TestFired(string orderId)=>testFired.Contains(orderId);
  public bool Reported(string orderId)=>reported.Contains(orderId);
  /// The current order names a report-to colonist and the player has spoken to them during it.
  public bool CurrentReported=>Current!=null&&reported.Contains(Current.id);
  static bool HasReport(FieldOrder o)=>o!=null&&o.goal==FieldOrderGoal.FitMod&&!string.IsNullOrEmpty(o.reportTo);
  /// The player spoke to a colonist: counts as the current order's report when it is the one the order names.
  public bool NoteReport(string npcId)
  {
   var o=Current;
   return HasReport(o)&&o.reportTo==npcId&&reported.Add(o.id);
  }
  /// A shot was fired: counts as the current order's test fire when its mod is fitted.
  public bool NoteShot(CraftingModel model)
  {
   var o=Current;
   return o!=null&&o.goal==FieldOrderGoal.FitMod&&o.requireTestFire&&Fitted(model,o.targetItemId)&&testFired.Add(o.id);
  }
  public bool IsComplete(FieldOrder o,CraftingModel model,Func<string,bool> collected)
  {
   switch(o.goal)
   {
    case FieldOrderGoal.FitMod:return Fitted(model,o.targetItemId)&&(!o.requireTestFire||testFired.Contains(o.id));
    case FieldOrderGoal.CollectItem:return collected!=null&&collected(o.targetItemId);
    case FieldOrderGoal.CraftFromGroup:return model.Data.recipes.Any(r=>r.group==o.targetGroup&&model.CraftCount(r.id)>0);
    default:return false;
   }
  }
  /// Completes the current order when its goal is met, continuing while the next is already met. Never goes back.
  public List<FieldOrder> Advance(CraftingModel model,Func<string,bool> collected)
  {
   var done=new List<FieldOrder>();
   while(Current!=null&&IsComplete(Current,model,collected)){done.Add(Current);Index++;}
   return done;
  }
  public CraftRecipe RecipeFor(CraftingModel model,FieldOrder o)=>o==null||string.IsNullOrEmpty(o.targetItemId)?null:model.Data.recipes.FirstOrDefault(r=>r.outputItemId==o.targetItemId);
  public OrderStage Stage(CraftingModel model,ShopModel pack)
  {
   if(!Started)return OrderStage.NotStarted;
   var o=Current;if(o==null)return OrderStage.FreePlay;
   switch(o.goal)
   {
    case FieldOrderGoal.CollectItem:return OrderStage.Hunt;
    case FieldOrderGoal.CraftFromGroup:return OrderStage.Craft;
   }
   if(Fitted(model,o.targetItemId))return OrderStage.TestFire;
   if(pack.Quantity(o.targetItemId)>0)return OrderStage.Fit;
   var recipe=RecipeFor(model,o);
   if(recipe==null||!model.CanCraft(recipe.id,recipe.stationId,out _))return OrderStage.Gather;
   return HasReport(o)&&!reported.Contains(o.id)?OrderStage.Report:OrderStage.Fabricate;
  }
  public string GuidanceKey(CraftingModel model,ShopModel pack)
  {
   switch(Stage(model,pack))
   {
    case OrderStage.Fabricate:case OrderStage.Fit:case OrderStage.Craft:return "fabricator";
    case OrderStage.Gather:case OrderStage.Hunt:return Current.guidance;
    case OrderStage.Report:return Current.reportGuidance;
    case OrderStage.FreePlay:return Data.freePlayGuidance;
    default:return null;
   }
  }
  /// Field Notes text, built from the order's data templates and live recipe/inventory facts.
  public string Objective(CraftingModel model,ShopModel pack)
  {
   var stage=Stage(model,pack);
   if(stage==OrderStage.NotStarted)return null;
   if(stage==OrderStage.FreePlay)return Data.freePlayObjective;
   var o=Current;var recipe=RecipeFor(model,o);
   string item=CraftingText.ItemName(model,o.targetItemId);
   if(stage==OrderStage.Report)return Fill(o.reportBrief??"",("item",item)).Trim();
   string template=stage switch
   {
    OrderStage.Gather=>Data.gatherFormat,
    OrderStage.Fabricate=>Data.fabricateFormat,
    OrderStage.Fit=>Data.fitFormat,
    OrderStage.TestFire=>Data.testFireFormat,
    OrderStage.Hunt=>Data.collectFormat,
    _=>Data.craftGroupFormat
   };
   string inputs="";
   if(recipe?.inputs!=null)inputs=string.Join(Data.inputSeparator,recipe.inputs.Select(i=>Fill(Data.inputFormat,("name",CraftingText.InputName(model,i)),("have",Math.Min(i.quantity,model.Available(i)).ToString()),("need",i.quantity.ToString()))));
   int count=o.goal==FieldOrderGoal.CraftFromGroup?model.Data.recipes.Count(r=>r.group==o.targetGroup&&model.Knows(r.id)):0;
   string brief=Fill(o.brief??"",("item",item));
   return Fill(template,("brief",brief),("item",item),("weapon",model.Loadout.WeaponName),("recipe",recipe!=null?recipe.name:item),("inputs",inputs),("count",count.ToString())).Trim();
  }
  public static string Fill(string template,params (string key,string value)[] values)
  {
   var sb=new StringBuilder(template??"");
   foreach(var (key,value) in values)sb.Replace("{"+key+"}",value??"");
   return sb.ToString();
  }
  public FieldOrderState Capture()=>new FieldOrderState{index=Index,testFired=testFired.OrderBy(x=>x,StringComparer.Ordinal).ToArray(),reported=reported.OrderBy(x=>x,StringComparer.Ordinal).ToArray()};
  public void Restore(FieldOrderState state)
  {
   testFired.Clear();reported.Clear();
   if(state==null){Index=-1;return;}
   Index=Math.Max(-1,Math.Min(Data.orders.Length,state.index));
   if(state.testFired!=null)foreach(var id in state.testFired)if(!string.IsNullOrEmpty(id))testFired.Add(id);
   if(state.reported!=null)foreach(var id in state.reported)if(!string.IsNullOrEmpty(id))reported.Add(id);
  }
 }
 /// reported (1 Oct 2026): orders whose report-to colonist was visited; absent in older saves (none reported, so an
 /// order in progress asks for the visit once).
 [Serializable] public class FieldOrderState {public int index=-1;public string[] testFired;public string[] reported;}
}
