using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 public enum MissionStatus { Active, Complete }
 public sealed class MissionStep {public string text;public bool done,current;}
 /// One journal entry, rebuilt from the live story state (nothing here is saved except which mission is tracked).
 public sealed class Mission
 {
  public string id,title,giver,area,summary,objective,reward,targetLabel;
  public MissionStatus status;
  public readonly List<MissionStep> steps=new List<MissionStep>();
  /// Where the tracked marker points (compass and in-world label); null when there is nowhere to go.
  public Transform target;
  /// A droid the marker is following (its own health bar replaces the in-world label once engaged).
  public FeralDroid droid;
  public int StepsDone=>steps.Count(s=>s.done);
  public bool Active=>status==MissionStatus.Active;
 }
 /// Journal state in a save (5 Oct 2026): the tracked mission, and whether the player chose it (a chosen mission stays
 /// tracked until it completes; otherwise tracking follows the most pressing active mission).
 [Serializable] public class JournalState {public string tracked;public bool chosen;}
 /// The mission journal (5 Oct 2026): the city visit, the Warden's primer, each of Ossa's field orders and the home
 /// lease, built from the live state whenever it changes. One mission is tracked: the Field Notes box shows it and the
 /// compass and in-world marker point at its target. Until the player picks one (Track), tracking follows the most
 /// pressing active mission (Ossa's field orders, the primer once begun, the home, the city visit); a picked mission stays
 /// tracked until it completes, then tracking follows again (a finished field order hands over to the next order).
 [RequireComponent(typeof(GameSession))]
 public class QuestJournal:MonoBehaviour
 {
  public const string ArrivalId="arrival",PrimerId="primer",HomeId="home",OrderPrefix="order:";
  GameSession session;FieldOrders orders;BermsTutorial tutorial;WardHome home;CraftingSession crafting;
  readonly List<Mission> missions=new List<Mission>();
  readonly HashSet<string> announced=new HashSet<string>();
  bool dirty=true,silent=true,bound;
  string tracked,signature;bool chosen;
  readonly List<string> pendingNotices=new List<string>();
  bool changedPending;
  public IReadOnlyList<Mission> Missions{get{Rebuild();return missions;}}
  public event Action Changed;
  /// The tracked mission's id (picked by the player or automatic).
  public string TrackedId=>tracked;
  /// The player picked the tracked mission (Track) rather than it following the most pressing one.
  public bool TrackedChosen=>chosen;
  public Mission Tracked{get{Rebuild();return Find(tracked);}}
  public Mission Find(string id)=>string.IsNullOrEmpty(id)?null:missions.FirstOrDefault(m=>m.id==id);
  void Awake(){session=GetComponent<GameSession>();}
  void Bind()
  {
   if(bound)return;bound=true;
   orders=GetComponent<FieldOrders>();crafting=GetComponent<CraftingSession>();
   tutorial=orders&&orders.tutorial?orders.tutorial:FindAnyObjectByType<BermsTutorial>();
   home=FindAnyObjectByType<WardHome>();
   session.Changed+=MarkDirty;
   if(orders)orders.Changed+=MarkDirty;
   if(tutorial)tutorial.Changed+=MarkDirty;
  }
  void OnDestroy(){if(!bound)return;if(session)session.Changed-=MarkDirty;if(orders)orders.Changed-=MarkDirty;if(tutorial)tutorial.Changed-=MarkDirty;}
  void MarkDirty()=>dirty=true;
  float nextRefresh;
  // Targets move (the nearest colonist, a droid leader, its wreck): rebuild on every change and at least once a second.
  // Changed and the "new mission" notices go out from here, never from inside a getter (the HUD reads Tracked while it
  // refreshes, and must not be re-entered).
  void Update()
  {
   Bind();
   if(Time.unscaledTime>=nextRefresh){nextRefresh=Time.unscaledTime+1;dirty=true;}
   if(dirty&&session.HasStarted)Rebuild();
   foreach(var n in pendingNotices)session.Notify(n,"Journal");
   pendingNotices.Clear();
   if(changedPending){changedPending=false;Changed?.Invoke();}
  }
  /// Track a mission (Journal → Track). Only an active mission can be tracked.
  public bool Track(string id)
  {
   Rebuild();var m=Find(id);
   if(m==null||!m.Active)return false;
   if(tracked==id&&chosen)return true;
   tracked=id;chosen=true;Changed?.Invoke();session.Notify($"Tracking {m.title}.","Journal");return true;
  }
  public JournalState Capture()=>new JournalState{tracked=tracked??"",chosen=chosen};
  /// Save restore: the tracked mission, and every mission already active counts as announced (no "new" notices; one
  /// queued while the save was being applied is dropped too).
  public void Restore(JournalState state){tracked=string.IsNullOrEmpty(state?.tracked)?null:state.tracked;chosen=tracked!=null&&state.chosen;silent=true;announced.Clear();pendingNotices.Clear();dirty=true;}

  // ------------------------------------------------------------------ building
  void Rebuild()
  {
   Bind();
   if(!dirty)return;
   dirty=false;missions.Clear();
   Arrival();Primer();Orders();Home();
   // the tracked mission: kept while active; otherwise the most pressing active one
   var current=Find(tracked);
   if(current==null||!current.Active||!chosen)
   {
    if(current==null||!current.Active)chosen=false;
    tracked=AutoTrack()?.id;
   }
   foreach(var m in missions.Where(m=>m.Active))
    if(announced.Add(m.id)&&!silent&&!m.id.StartsWith(OrderPrefix))pendingNotices.Add($"New in your journal: {m.title} · {m.giver}. Press J to read it.");
   silent=false;
   // listeners hear about real changes only (the periodic rebuild for moving targets usually changes nothing shown)
   var sig=tracked+"|"+string.Join(";",missions.Select(m=>m.id+":"+m.status+":"+m.objective+":"+m.targetLabel+":"+string.Join(",",m.steps.Select(x=>x.done?"1":"0"))));
   if(sig!=signature){signature=sig;changedPending=true;}
  }
  /// Field orders first (Ossa's chain), then the primer once begun, the home, the city visit, the primer's approach.
  Mission AutoTrack()
  {
   var active=missions.Where(m=>m.Active).ToList();
   return active.FirstOrDefault(m=>m.id.StartsWith(OrderPrefix))
    ??active.FirstOrDefault(m=>m.id==PrimerId&&tutorial&&tutorial.Step>BermsStep.Approach)
    ??active.FirstOrDefault(m=>m.id==HomeId)
    ??active.FirstOrDefault(m=>m.id==ArrivalId)
    ??active.FirstOrDefault();
  }
  static MissionStep Step(Mission m,string text,bool done){var s=new MissionStep{text=text,done=done};m.steps.Add(s);return s;}
  /// Marks the first unfinished step as current.
  static void MarkCurrent(Mission m){var s=m.steps.FirstOrDefault(x=>!x.done);if(s!=null&&m.Active)s.current=true;}
  NpcAgent Npc(string id)=>session.npcs?.FirstOrDefault(n=>n&&n.definition&&n.definition.id==id);

  void Arrival()
  {
   var m=new Mission{id=ArrivalId,title="Arrival in Ward",giver="Linn",area="Ward · the hill and the market avenue",
    summary="Linn asked you to meet her on the hill. Find your feet in Ward: climb to the Hill Tree, meet the colonists who keep the city running, trade at Basic General and open a link from the Lattice Jack.",
    status=session.Complete?MissionStatus.Complete:MissionStatus.Active,objective=session.Objective,reward="A place on the hill."};
   Step(m,"Reach the Hill Tree",session.visitedHill);
   Step(m,$"Meet the colonists · {Math.Min(4,session.Spoken.Count)}/4 conversations",session.Spoken.Count>=4);
   Step(m,"Buy a water flask at Basic General",session.boughtFlask);
   Step(m,"Sell your scrap at Basic General",session.soldScrap);
   Step(m,"Use the Lattice Jack",session.linked);
   MarkCurrent(m);
   if(m.Active)
   {
    if(!session.visitedHill){m.target=session.hillPoint;m.targetLabel="HILL TREE";}
    else if(session.Spoken.Count<4)
    {
     var p=session.player?session.player.transform.position:Vector3.zero;
     var next=session.npcs?.Where(n=>n&&n.countsForCityVisit&&n.definition&&!session.Spoken.Contains(n.definition.id)).OrderBy(n=>(n.transform.position-p).sqrMagnitude).FirstOrDefault();
     if(next){m.target=next.transform;m.targetLabel=next.definition.displayName.ToUpperInvariant();}
    }
    else if(!session.boughtFlask||!session.soldScrap){var mira=Npc("npc_mira");if(mira){m.target=mira.transform;m.targetLabel="BASIC GENERAL";}}
    else if(!session.linked){m.target=session.latticePoint;m.targetLabel="LATTICE JACK";}
   }
   missions.Add(m);
  }

  void Primer()
  {
   if(!tutorial)return;
   var step=tutorial.Step;
   var m=new Mission{id=PrimerId,title="Warden's Primer",giver=tutorial.radioSpeaker,area="Outer Berms · the West Gate post",
    summary="Nobody walks the Berms unarmed. Warden Ossa keeps the West Gate post: draw a scrap pistol from her arms locker, learn it on the range, then help clear the feral machines nesting by the service road.",
    status=step==BermsStep.Complete?MissionStatus.Complete:MissionStatus.Active,objective=tutorial.Objective,
    reward=$"{tutorial.rewardCredits} credits and {tutorial.rewardScrap} × scrap coil; Ossa's field orders"};
   Step(m,"Report to Warden Ossa at the West Gate post",step>BermsStep.Approach);
   Step(m,"Take the scrap pistol from the arms locker",step>BermsStep.TakePistol);
   Step(m,"Draw the pistol (2)",step>BermsStep.Draw);
   Step(m,$"Knock down the range plates · {Math.Min(tutorial.TargetsDown,tutorial.targets.Length)}/{tutorial.targets.Length}",step>BermsStep.Targets);
   Step(m,"Put down the loose scrap drone",step>BermsStep.FirstContact);
   Step(m,"Clear the machine depot",step>BermsStep.Depot);
   MarkCurrent(m);
   if(m.Active){m.target=tutorial.GuidanceTarget;m.targetLabel=tutorial.GuidanceLabel;}
   missions.Add(m);
  }

  void Orders()
  {
   if(!orders||!orders.Ready||!orders.Progress.Started||crafting==null||crafting.Model==null)return;
   var progress=orders.Progress;var model=crafting.Model;var data=progress.Data;
   for(int i=0;i<data.orders.Length&&i<=progress.Index;i++)
   {
    var o=data.orders[i];if(o==null)continue;
    bool done=progress.Index>i;
    string item=CraftingText.ItemName(model,o.targetItemId);
    var m=new Mission{id=OrderPrefix+o.id,title=o.title,giver=o.speaker,area=$"Outer Berms · field order {i+1} of {data.orders.Length}",
     summary=FieldOrderProgress.Fill(o.brief??"",("item",item)).Trim(),status=done?MissionStatus.Complete:MissionStatus.Active,
     objective=done?null:orders.Objective,reward=Reward(o,model)};
    var stage=done?OrderStage.FreePlay:orders.Stage;
    bool report=!string.IsNullOrEmpty(o.reportTo)&&(o.goal==FieldOrderGoal.FitMod||o.goal==FieldOrderGoal.CraftItem);
    string reportName=report?(Npc(o.reportTo)?.definition.displayName??"the trader"):null;
    switch(o.goal)
    {
     case FieldOrderGoal.CollectItem:Step(m,$"Recover the {item}",done);break;
     case FieldOrderGoal.CraftFromGroup:Step(m,"Fabricate one of the schematics Ossa named",done);break;
     default:
     {
      // Gather → (Report) → Fabricate → (Fit → TestFire): a step is done once the order has moved past it.
      int at=done?99:stage switch{OrderStage.Gather=>0,OrderStage.Report=>1,OrderStage.Fabricate=>2,OrderStage.Fit=>3,OrderStage.TestFire=>4,_=>0};
      Step(m,"Gather the parts",at>0);
      if(report)Step(m,$"Take them to {reportName}",at>1);
      Step(m,$"Fabricate the {item} at the workbench",at>2);
      if(o.goal==FieldOrderGoal.FitMod)
      {
       Step(m,$"Fit the {item}",at>3);
       if(o.requireTestFire)Step(m,"Test-fire it in the Outer Berms",done);
      }
      break;
     }
    }
    MarkCurrent(m);
    if(m.Active){m.target=orders.GuidanceTarget;m.targetLabel=orders.GuidanceLabel;m.droid=orders.GuidanceDroid;}
    missions.Add(m);
   }
  }
  static string Reward(FieldOrder o,CraftingModel model)
  {
   var parts=new List<string>();
   if(o.rewardCredits>0)parts.Add($"{o.rewardCredits} credits");
   if(o.rewardItems!=null)parts.AddRange(o.rewardItems.Where(x=>x!=null&&x.quantity>0).Select(x=>$"{CraftingText.ItemName(model,x.itemId)} ×{x.quantity}"));
   if(o.rewardRecipes!=null)parts.AddRange(o.rewardRecipes.Select(id=>model.Recipe(id)).Where(r=>r!=null).Select(r=>r.name+" schematic"));
   return parts.Count>0?string.Join(", ",parts):null;
  }

  void Home()
  {
   if(!home)home=FindAnyObjectByType<WardHome>();
   bool leased=session.HasFlag(WardHome.LeasedFlag),stored=session.HasFlag(WardHome.StoredFlag);
   bool started=leased||tutorial&&tutorial.Step==BermsStep.Complete;
   if(!started)return;
   int price=home?home.leasePrice:40;
   var m=new Mission{id=HomeId,title="A Roof in Ward",giver="Linn",area="Ward · the south wall",
    summary="The Berms will fill your pack faster than you can carry it. Linn on the hill keeps the housing roll: an empty container home on the south wall, with a bunk and a steel locker, is waiting for a tenant.",
    status=leased&&stored?MissionStatus.Complete:MissionStatus.Active,reward="Your own locker for salvage and a bunk to rest on."};
   Step(m,"Ask Linn on the hill about a place to stay",leased||session.HasFlag(WardHome.AskedFlag));
   Step(m,$"Take the lease on the container home · {price} credits",leased);
   Step(m,"Store something in the home locker",stored);
   MarkCurrent(m);
   var current=m.steps.FirstOrDefault(s=>s.current);
   m.objective=current!=null?current.text+".":"Your home is on the south wall, behind the Nanofab yard.";
   if(m.Active)
   {
    if(!leased){var linn=Npc("npc_linn");if(linn){m.target=linn.transform;m.targetLabel="LINN";}}
    else if(home){m.target=home.lockerPoint?home.lockerPoint:home.transform;m.targetLabel="HOME LOCKER";}
   }
   missions.Add(m);
  }
 }
}
