using System;
using UnityEngine;
namespace AthenHill
{
 /// Bound explicitly by DroidEncounter, never by a global kill event.
 [RequireComponent(typeof(FeralDroid))]
 public class LootSource:MonoBehaviour
 {
  public string lootTableId;
  FeralDroid droid;
  Action<string> payout;
  bool paid;
  void Awake(){droid=GetComponent<FeralDroid>();}
  public void Bind(CraftingSession session){payout=session?session.Salvage:null;}
  public void Bind(Action<string> grant){payout=grant;}
  void OnEnable(){if(!droid)droid=GetComponent<FeralDroid>();droid.Killed+=OnKilled;}
  void OnDisable(){if(droid)droid.Killed-=OnKilled;}
  void OnKilled(FeralDroid killed)
  {
   if(paid||payout==null)return;
   paid=true;payout(lootTableId);
  }
  public void Revived(){paid=false;}
 }
}
