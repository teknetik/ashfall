using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
namespace AthenHill
{
 /// Report: the parts are gathered and the order's report-to colonist has not been visited yet (appended last, so
 /// existing numeric values are unchanged).
 /// Identify (20 Nov 2026): the player carries salvage the schematic needs (the Damaged Servo) but the schematic is not
 /// learned yet; the colonist named by the item's identifyBy (Ossa) has to look at it first.
 public enum OrderStage { NotStarted, Gather, Fabricate, Fit, TestFire, Hunt, Craft, FreePlay, Report, Identify }
 /// Pure field-order state machine. The index only ever moves forward, so repeating a finished task (crafting or
 /// fitting again, firing again) can never restart an order or repeat Ossa's completion line.
 public sealed class FieldOrderProgress
 {
  readonly HashSet<string> testFired=new HashSet<string>();
  readonly HashSet<string> reported=new HashSet<string>();
  /// Orders whose part was built by hand at the bench while they were current (20 Nov 2026): their test fire is a judged string.
  readonly HashSet<string> benched=new HashSet<string>();
  readonly System.Collections.Generic.List<UnityEngine.Vector3> testShots=new System.Collections.Generic.List<UnityEngine.Vector3>();
  int testStrings;
  public bool Benched(string orderId)=>benched.Contains(orderId);
  /// Shots in the current test-fire string, and the widest angle between two of them in the last judged string.
  public int TestShots=>testShots.Count;
  public float LastGroupDegrees {get;private set;}
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
  /// The order with this id has been completed (the index has moved past it).
  public bool Completed(string orderId){int i=Array.FindIndex(Data.orders,o=>o!=null&&o.id==orderId);return i>=0&&Index>i;}
  public bool Reported(string orderId)=>reported.Contains(orderId);
  /// The current order names a report-to colonist and the player has spoken to them during it.
  public bool CurrentReported=>Current!=null&&reported.Contains(Current.id);
  static bool HasReport(FieldOrder o)=>o!=null&&(o.goal==FieldOrderGoal.FitMod||o.goal==FieldOrderGoal.CraftItem)&&!string.IsNullOrEmpty(o.reportTo);
  /// The player spoke to a colonist: counts as the current order's report when it is the one the order names.
  public bool NoteReport(string npcId)
  {
   var o=Current;
   return HasReport(o)&&o.reportTo==npcId&&reported.Add(o.id);
  }
  /// A shot was fired: counts as the current order's test fire when its mod is fitted.
  public bool NoteShot(CraftingModel model)=>NoteShot(model,UnityEngine.Vector3.forward,out _);
  public bool NoteShot(CraftingModel model,UnityEngine.Vector3 direction,out TestFireVerdict verdict)=>NoteShot(model,direction,null,out verdict);
  /// The current order's test fire is a judged string fired from a set place (a bench-built part, FieldOrder.testFireRadius > 0).
  public bool RangeTest(FieldOrder o=null){o??=Current;return o!=null&&o.goal==FieldOrderGoal.FitMod&&o.requireTestFire&&o.testFireShots>1&&o.testFireRadius>0&&benched.Contains(o.id)&&!testFired.Contains(o.id);}
  /// The player stands at the order's firing line (always true for orders without one).
  public static bool AtFiringLine(FieldOrder o,UnityEngine.Vector3 position)
  {
   if(o==null||o.testFireRadius<=0)return true;
   float dx=position.x-o.testFireAt.x,dz=position.z-o.testFireAt.z;
   return dx*dx+dz*dz<=o.testFireRadius*o.testFireRadius;
  }
  /// The bench finished a hand-made job: when it made the current order's part, its test fire becomes a judged string.
  public bool NoteBenchBuilt(string recipeId,CraftingModel model)
  {
   var o=Current;var r=RecipeFor(model,o);
   if(o==null||r==null||r.id!=recipeId||!benched.Add(o.id))return false;
   testShots.Clear();testStrings=0;return true;
  }
  /// A shot with its world direction. One-shot orders complete at once (verdict None). A bench-built part's order collects
  /// FieldOrder.testFireShots shots and judges the group: Tight completes it; Poor asks for one more string (verdict Again),
  /// and the second string completes it whatever the group (Poor). Counting = the string is not finished.
  /// from: where the player stood (null = not known, counted as at the line). A judged string with a firing line counts only
  /// shots fired from it; a shot from elsewhere is OffRange and starts the string again.
  public bool NoteShot(CraftingModel model,UnityEngine.Vector3 direction,UnityEngine.Vector3? from,out TestFireVerdict verdict)
  {
   verdict=TestFireVerdict.None;
   var o=Current;
   if(o==null||o.goal!=FieldOrderGoal.FitMod||!o.requireTestFire||!Fitted(model,o.targetItemId)||testFired.Contains(o.id))return false;
   if(o.testFireShots<=1||!benched.Contains(o.id))return testFired.Add(o.id);
   if(from.HasValue&&!AtFiringLine(o,from.Value)){testShots.Clear();verdict=TestFireVerdict.OffRange;return false;}
   testShots.Add(direction.sqrMagnitude>0?direction.normalized:UnityEngine.Vector3.forward);
   if(testShots.Count<o.testFireShots){verdict=TestFireVerdict.Counting;return false;}
   float widest=0;
   for(int i=0;i<testShots.Count;i++)for(int j=i+1;j<testShots.Count;j++)widest=Math.Max(widest,UnityEngine.Vector3.Angle(testShots[i],testShots[j]));
   LastGroupDegrees=widest;testShots.Clear();testStrings++;
   bool tight=widest<=o.testFireTightDegrees;
   if(!tight&&testStrings<2){verdict=TestFireVerdict.Again;return false;}
   verdict=tight?TestFireVerdict.Tight:TestFireVerdict.Poor;
   return testFired.Add(o.id);
  }
  public bool IsComplete(FieldOrder o,CraftingModel model,Func<string,bool> collected)
  {
   switch(o.goal)
   {
    case FieldOrderGoal.FitMod:return Fitted(model,o.targetItemId)&&(!o.requireTestFire||testFired.Contains(o.id));
    case FieldOrderGoal.CollectItem:return collected!=null&&collected(o.targetItemId);
    case FieldOrderGoal.CraftFromGroup:return model.Data.recipes.Any(r=>r.group==o.targetGroup&&model.CraftCount(r.id)>0);
    case FieldOrderGoal.CraftItem:{var r=RecipeFor(model,o);return r!=null&&model.CraftCount(r.id)>0;}
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
    case FieldOrderGoal.CraftItem:
    {
     var r=RecipeFor(model,o);
     if(r!=null&&model.OnBenchRecipe(r.id))return OrderStage.Fabricate;
     if(r==null||!model.CanCraft(r.id,r.stationId,out _))return r!=null&&model.UnidentifiedCarried(r.id)!=null?OrderStage.Identify:OrderStage.Gather;
     return HasReport(o)&&!reported.Contains(o.id)?OrderStage.Report:OrderStage.Fabricate;
    }
   }
   if(Fitted(model,o.targetItemId))return OrderStage.TestFire;
   var recipe=RecipeFor(model,o);
   // 20 Nov 2026 (Steady Hands bench): with the job open on the bench the inputs are reserved there, so it stays Fabricate;
   // the bench fits the part in the same visit, so Fit is only seen for parts made on the timer.
   if(recipe!=null&&model.OnBenchRecipe(recipe.id))return OrderStage.Fabricate;
   if(pack.Quantity(o.targetItemId)>0)return OrderStage.Fit;
   if(recipe==null||!model.CanCraft(recipe.id,recipe.stationId,out _))return recipe!=null&&model.UnidentifiedCarried(recipe.id)!=null?OrderStage.Identify:OrderStage.Gather;
   return HasReport(o)&&!reported.Contains(o.id)?OrderStage.Report:OrderStage.Fabricate;
  }
  /// The current order's part is made by hand at the bench (its recipe has a bench job not yet done by hand, or the job is
  /// open): fabricate and fit are one bench visit.
  public bool BenchRoute(CraftingModel model,FieldOrder o=null)
  {
   o??=Current;var recipe=RecipeFor(model,o);
   return recipe!=null&&model.HasAssembly(recipe.id)&&(model.NeedsHandMade(recipe.id)||model.OnBenchRecipe(recipe.id));
  }
  public string GuidanceKey(CraftingModel model,ShopModel pack)
  {
   switch(Stage(model,pack))
   {
    case OrderStage.Fabricate:case OrderStage.Fit:case OrderStage.Craft:return "fabricator";
    case OrderStage.Gather:case OrderStage.Hunt:return Current.guidance;
    case OrderStage.Report:return Current.reportGuidance;
    case OrderStage.Identify:return Current.identifyGuidance;
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
   if(stage==OrderStage.Identify)return Fill(o.identifyBrief??"",("item",item)).Trim();
   if(stage==OrderStage.Report)return Fill(o.reportBrief??"",("item",item)).Trim();
   string template=stage switch
   {
    OrderStage.Gather=>Data.gatherFormat,
    OrderStage.Fabricate=>BenchRoute(model,o)&&!string.IsNullOrEmpty(Data.benchFormat)?Data.benchFormat:Data.fabricateFormat,
    OrderStage.Fit=>Data.fitFormat,
    OrderStage.TestFire=>RangeTest(o)&&!string.IsNullOrEmpty(o.testFireBrief)?o.testFireBrief:Data.testFireFormat,
    OrderStage.Hunt=>Data.collectFormat,
    _=>Data.craftGroupFormat
   };
   string inputs="";
   if(recipe?.inputs!=null)inputs=string.Join(Data.inputSeparator,recipe.inputs.Select(i=>Fill(Data.inputFormat,("name",CraftingText.InputName(model,i)),("have",Math.Min(i.quantity,model.Available(i)).ToString()),("need",i.quantity.ToString()))));
   int count=o.goal==FieldOrderGoal.CraftFromGroup?model.Data.recipes.Count(r=>r.group==o.targetGroup&&model.Knows(r.id)):0;
   string brief=Fill(o.brief??"",("item",item));
   string stageLabel=stage==OrderStage.Fabricate&&model.OnBenchRecipe(recipe?.id)&&!string.IsNullOrEmpty(model.AssemblyStageLabel)?model.AssemblyStageLabel:"";
   return Fill(template,("brief",brief),("stage",stageLabel),("item",item),("weapon",model.Loadout.WeaponName),("recipe",recipe!=null?recipe.name:item),("inputs",inputs),("count",count.ToString())).Trim();
  }
  public static string Fill(string template,params (string key,string value)[] values)
  {
   var sb=new StringBuilder(template??"");
   foreach(var (key,value) in values)sb.Replace("{"+key+"}",value??"");
   return sb.ToString();
  }
  public FieldOrderState Capture()=>new FieldOrderState{index=Index,id=FreePlay?FieldOrderState.FreePlayId:Current?.id??"",testFired=testFired.OrderBy(x=>x,StringComparer.Ordinal).ToArray(),reported=reported.OrderBy(x=>x,StringComparer.Ordinal).ToArray(),benched=benched.OrderBy(x=>x,StringComparer.Ordinal).ToArray()};
  public void Restore(FieldOrderState state)
  {
   testFired.Clear();reported.Clear();benched.Clear();testShots.Clear();testStrings=0;
   if(state==null){Index=-1;return;}
   Index=Math.Max(-1,Math.Min(Data.orders.Length,state.index));
   // 3 Oct 2026: orders can be inserted (the Warden kit chain), so a saved order id wins over its numeric index
   if(state.id==FieldOrderState.FreePlayId)Index=Data.orders.Length;
   else if(!string.IsNullOrEmpty(state.id)){int byId=Array.FindIndex(Data.orders,o=>o!=null&&o.id==state.id);if(byId>=0)Index=byId;}
   if(state.testFired!=null)foreach(var id in state.testFired)if(!string.IsNullOrEmpty(id))testFired.Add(id);
   if(state.reported!=null)foreach(var id in state.reported)if(!string.IsNullOrEmpty(id))reported.Add(id);
   if(state.benched!=null)foreach(var id in state.benched)if(!string.IsNullOrEmpty(id))benched.Add(id);
  }
 }
 /// reported (1 Oct 2026): orders whose report-to colonist was visited; absent in older saves (none reported, so an
 /// order in progress asks for the visit once).
 /// id (3 Oct 2026): the current order's id ("#freeplay" after the last order). Restore prefers it to the index, so
 /// inserting orders keeps saves on the right order; saves without it fall back to the index.
 /// benched (20 Nov 2026, Steady Hands bench): orders whose part was built by hand at the bench (their test fire is a judged
 /// string); absent in older saves (none). A string in progress is not saved.
 [Serializable] public class FieldOrderState {public const string FreePlayId="#freeplay";public int index=-1;public string id;public string[] testFired;public string[] reported;public string[] benched;}
 /// What a test-fire shot did: None (one-shot order or not a test fire), Counting (string not finished), Again (poor group,
 /// one more string), Tight or Poor (the string was judged and the test fire is done).
 public enum TestFireVerdict { None, Counting, Again, Tight, Poor, OffRange }
}
