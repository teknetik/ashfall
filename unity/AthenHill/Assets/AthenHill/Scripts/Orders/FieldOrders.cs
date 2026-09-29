using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Runs Ossa's field orders once the Outer Berms primer is complete: evaluates goals when the pack, loadout or
 /// crafting state changes (never per frame), grants rewards once, speaks radio lines and exposes the Field Notes
 /// objective and guidance target. Order content lives in the FieldOrderSet asset.
 [RequireComponent(typeof(GameSession))]
 public class FieldOrders:MonoBehaviour
 {
  public FieldOrderSet data;
  public CraftingSession crafting;
  public BermsTutorial tutorial;
  public PlayerCombat combat;
  [Serializable]public class Target{public string key,label;public Transform point;}
  [Tooltip("Guidance keys used by the orders (fabricator, depot, foreman…) and their world points and labels.")]
  public Target[] guidanceTargets=new Target[0];
  [Serializable]public class EncounterBinding{public string key;public DroidEncounter encounter;}
  public EncounterBinding[] encounters=new EncounterBinding[0];
  public FieldOrderProgress Progress {get;private set;}
  public bool Ready=>Progress!=null&&crafting&&crafting.Model!=null;
  /// Raised once per completed order, after its reward was granted.
  public event Action<FieldOrder> Completed;
  /// Raised when the objective, stage or order changed.
  public event Action Changed;
  public string Objective {get;private set;}
  public string Heading {get;private set;}
  public OrderStage Stage {get;private set;}
  public Transform GuidanceTarget {get;private set;}
  public string GuidanceLabel {get;private set;}
  GameSession session;
  string pendingLine,pendingSpeaker;float pendingAt;
  bool dirty;
  IEnumerator Start()
  {
   session=GetComponent<GameSession>();
   if(!crafting)crafting=GetComponent<CraftingSession>();
   if(!tutorial)tutorial=FindAnyObjectByType<BermsTutorial>();
   if(!combat)combat=FindAnyObjectByType<PlayerCombat>();
   if(!data||!crafting){Debug.LogError("Field orders need their data asset and the crafting session.");yield break;}
   while(crafting.Model==null||crafting.Loot==null)yield return null;
   Progress??=new FieldOrderProgress(data);
   crafting.Model.Changed+=MarkDirty;crafting.Collected+=OnCollected;
   session.Changed+=MarkDirty;
   if(combat)combat.ShotFired+=OnShot;
   if(tutorial)tutorial.Changed+=MarkDirty;
   MarkDirty();
  }
  void OnDestroy()
  {
   if(crafting){if(crafting.Model!=null)crafting.Model.Changed-=MarkDirty;crafting.Collected-=OnCollected;}
   if(session)session.Changed-=MarkDirty;
   if(combat)combat.ShotFired-=OnShot;
   if(tutorial)tutorial.Changed-=MarkDirty;
  }
  void MarkDirty()=>dirty=true;
  void OnCollected(LootPickup _)=>dirty=true;
  void OnShot(){if(Ready&&Progress.NoteShot(crafting.Model))dirty=true;}
  bool Collected(string itemId)=>crafting.Loot.HasCollected(itemId)||session.Shop.Quantity(itemId)>0;
  void Update()
  {
   if(!Ready)return;
   if(!Progress.Started&&tutorial&&tutorial.Step==BermsStep.Complete){BeginOrder(Progress.Begin(),true);dirty=true;}
   if(pendingLine!=null&&Time.time>=pendingAt&&session.State==CityState.Play){session.Notify(pendingLine,pendingSpeaker);pendingLine=null;}
   if(dirty){dirty=false;Evaluate();}
  }
  void Evaluate()
  {
   var done=Progress.Advance(crafting.Model,Collected);
   foreach(var order in done){var reward=Reward(order);if(order==done[done.Count-1])session.Notify(Join(order.completeLine,reward),order.speaker);Completed?.Invoke(order);}
   if(done.Count>0)BeginOrder(Progress.Current,false);
   Refresh();
  }
  /// Order-start side effects: schematics tied to the order, its encounter, and its briefing line.
  void BeginOrder(FieldOrder order,bool immediate,bool speak=true)
  {
   if(order==null)return;
   var discovered=crafting.Model.OrderStarted(order.id);
   Activate(order.activateEncounter);
   if(!speak)return;
   var line=Join(order.startLine,CraftingText.Discovered(discovered));
   if(string.IsNullOrEmpty(line))return;
   if(immediate)session.Notify(line,order.speaker);
   else{pendingLine=line;pendingSpeaker=order.speaker;pendingAt=Time.time+data.nextLineDelay;}
  }
  void Activate(string key)
  {
   if(string.IsNullOrEmpty(key))return;
   var binding=encounters.FirstOrDefault(x=>x!=null&&x.key==key);
   if(binding!=null&&binding.encounter&&!binding.encounter.Spawned)binding.encounter.Activate();
  }
  /// Credits and items in one pack transaction (items beyond a stack cap are dropped with a note), then schematics.
  string Reward(FieldOrder order)
  {
   var pack=session.Shop;var parts=new List<string>();
   var items=(order.rewardItems??new ItemStack[0]).Where(x=>x!=null&&x.quantity>0&&pack.Spec(x.itemId)!=null).Select(x=>new ItemStack(x.itemId,Math.Min(x.quantity,pack.Room(x.itemId)))).Where(x=>x.quantity>0).ToList();
   if(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.itemId,x.quantity)),Math.Max(0,order.rewardCredits),out _))
   {
    if(order.rewardCredits>0)parts.Add($"{order.rewardCredits} credits");
    parts.AddRange(items.Select(x=>$"{CraftingText.ItemName(crafting.Model,x.itemId)} ×{x.quantity}"));
   }
   var unlocked=(order.rewardRecipes??new string[0]).Where(crafting.Model.Unlock).Select(id=>crafting.Model.Recipe(id)).ToList();
   var text=parts.Count>0?"Reward: "+string.Join(", ",parts)+".":"";
   return Join(text,CraftingText.Discovered(unlocked));
  }
  static string Join(string a,string b)=>string.IsNullOrEmpty(a)?b??"":string.IsNullOrEmpty(b)?a:a+" "+b;
  void Refresh()
  {
   var model=crafting.Model;var pack=session.Shop;
   Stage=Progress.Stage(model,pack);
   Objective=Progress.Objective(model,pack);
   var o=Progress.Current;
   Heading=o!=null?$"FIELD ORDER {Progress.Index+1}/{data.orders.Length} · {o.title.ToUpperInvariant()}":Progress.FreePlay?"OUTER BERMS · FREE HUNTING":null;
   var key=Progress.GuidanceKey(model,pack);
   var target=string.IsNullOrEmpty(key)?null:guidanceTargets.FirstOrDefault(t=>t!=null&&t.key==key&&t.point);
   GuidanceTarget=target?.point;GuidanceLabel=target?.label;
   Changed?.Invoke();
  }
  /// Save restore: sets the order index without replaying lines or rewards, re-applies every started order's
  /// schematics and encounters, then re-evaluates.
  public void Restore(FieldOrderState state)
  {
   if(!data)return;
   Progress??=new FieldOrderProgress(data);
   Progress.Restore(state);pendingLine=null;
   if(crafting&&crafting.Model!=null)for(int i=0;i<=Math.Min(Progress.Index,data.orders.Length-1);i++)BeginOrder(data.orders[i],true,false);
   dirty=true;
  }
  public FieldOrderState Capture()=>Progress?.Capture()??new FieldOrderState();
  /// Pre-v2 tooling name for the grip tutorial state (Dormant, Salvage, Fabricate, Fit, TestFire, Done).
  public string LegacyGripStep=>Progress==null||!Progress.Started?"Dormant":Progress.Index>0?"Done":Stage switch{OrderStage.Gather=>"Salvage",OrderStage.Fabricate=>"Fabricate",OrderStage.Fit=>"Fit",_=>"TestFire"};
 }
}
