using System;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 public enum BermsStep { Approach, TakePistol, Draw, Targets, FirstContact, Depot, Complete }
 /// Outer Berms combat primer, run by a Warden at the post beyond the market gate:
 /// take the pistol, draw it, drop three range plates, put down a loose drone, then clear the depot nest.
 /// Radio lines and objective text are serialized so they can be rewritten without code changes.
 public class BermsTutorial:MonoBehaviour
 {
  public GameSession session;
  public PlayerCombat combat;
  public WorldInteractable locker;
  [Tooltip("Warden who gives the checkpoint briefing.")]
  public Transform briefingWarden;
  public RangeTarget[] targets=new RangeTarget[0];
  public DroidEncounter firstContact,depot;
  [Tooltip("The tutorial starts when the player comes this close to the gate marker.")]
  public Transform gateMarker;
  [Min(1)]public float startRadius=12;
  [Tooltip("Field Notes shows Berms objectives while the player is west of this X, or once the tutorial has started.")]
  public float showObjectiveWestOf=-30;
  public string radioSpeaker="Warden Ossa";
  [Min(0)]public int rewardCredits=15,rewardScrap=2;
  public string rewardItem="scrap_coil";
  [Header("Radio")]
  [TextArea]public string lineStart="New scavenger? Nobody walks the Berms unarmed. I'm Ossa, on West Gate watch. Take the scrap pistol from the ARMS LOCKER under the canopy at my post; the cyan light marks it. Then use the range across the lane.";
  [TextArea]public string lineDraw="It runs on nano charge, not rounds. Press 7 to draw it.";
  [TextArea]public string lineTargets="Hold right mouse to steady your aim, then left click to fire. F fires from the hip. Knock down those three plates.";
  [TextArea]public string lineFirstContact="Movement on the service road. A scrap drone's slipped its cluster. They back off before they dart in, so shoot on the tell.";
  [TextArea]public string lineDepot="The rest of its cluster is nested at the old machine depot, south along the road. Clear it out. Break contact if you're hurt; vitality comes back, and nano refills when you stop firing.";
  [TextArea]public string lineComplete="Clean work. Take the salvage to Mira. The depot always fills up again. The Berms go on a long way; come back when you're ready.";
  public BermsStep Step {get;private set;}=BermsStep.Approach;
  public int TargetsDown=>targets.Count(t=>t&&t.Down);
  public bool ShowObjective=>Step!=BermsStep.Approach||(combat&&combat.transform.position.x<showObjectiveWestOf);
  public string Objective=>Step switch
  {
   BermsStep.Approach=>"Go through the market gate to the Warden post.",
   BermsStep.TakePistol=>"Take the pistol · cyan-lit ARMS LOCKER under the canopy at Ossa’s post.",
   BermsStep.Draw=>"Press 7 to draw the scrap pistol.",
   BermsStep.Targets=>$"Aim with right mouse, fire with left click · plates {TargetsDown}/{targets.Length}",
   BermsStep.FirstContact=>"Put down the scrap drone on the service road.",
   BermsStep.Depot=>$"Clear the machine depot · {(depot?depot.Remaining:0)} droids left",
   _=>"Outer Berms primer complete. Sell the salvage at Basic General."
  };
  public Transform GuidanceTarget=>Step==BermsStep.Approach?briefingWarden:Step==BermsStep.TakePistol&&locker?locker.transform:null;
  public event Action Changed;
  void Start()
  {
   if(locker){locker.Used+=TakePistol;locker.enabled=false;}
   foreach(var t in targets)if(t)t.KnockedDown+=_=>OnTargetDown();
   if(firstContact)firstContact.WasCleared+=_=>{if(Step==BermsStep.FirstContact)Advance(BermsStep.Depot,lineDepot);};
   if(depot){depot.WasCleared+=_=>{if(Step==BermsStep.Depot)Finish();};}
  }
  void Update()
  {
   if(!session||session.State!=CityState.Play)return;
   if(Step==BermsStep.Approach&&gateMarker&&Vector3.Distance(combat.transform.position,gateMarker.position)<startRadius)
   {Advance(BermsStep.TakePistol,lineStart);if(locker)locker.enabled=true;}
   if(Step==BermsStep.Draw&&combat.Armed)Advance(BermsStep.Targets,lineTargets);
   if(Step==BermsStep.Depot&&depot&&depot.Remaining!=lastRemaining){lastRemaining=depot.Remaining;Changed?.Invoke();}
  }
  int lastRemaining=-1;
  void TakePistol()
  {
   if(Step!=BermsStep.TakePistol)return;
   combat.GivePistol();locker.enabled=false;
   Advance(BermsStep.Draw,lineDraw);
  }
  void OnTargetDown()
  {
   Changed?.Invoke();
   if(Step==BermsStep.Targets&&TargetsDown==targets.Length)
   {
    Advance(BermsStep.FirstContact,lineFirstContact);
    if(firstContact)firstContact.Activate();
   }
  }
  void Advance(BermsStep step,string line)
  {
   Step=step;
   if(step==BermsStep.Depot&&depot)depot.Activate();
   if(!string.IsNullOrEmpty(line))session.Notify(line,radioSpeaker);
   Changed?.Invoke();
  }
  void Finish()
  {
   Step=BermsStep.Complete;
   session.Reward(rewardCredits,rewardItem,rewardScrap,radioSpeaker,lineComplete);
   // Plates go back up for practice; the depot re-forms while the player is away.
   foreach(var t in targets)if(t)t.Raise();
   if(depot&&depot.respawnSeconds<=0)depot.respawnSeconds=120;
   Changed?.Invoke();
  }
 }
}
