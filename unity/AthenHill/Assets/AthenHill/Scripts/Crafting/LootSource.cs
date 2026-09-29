using System;
using UnityEngine;
namespace AthenHill
{
 /// Bound explicitly by DroidEncounter, never by a global kill event. On death the droid drops one salvage cache at
 /// its wreck; the cache despawns when the encounter re-forms (the droid is revived).
 /// A kill is only marked paid once the payout really happened: if the crafting model is not ready yet the payout
 /// is retried each frame until it succeeds or the droid is revived.
 [RequireComponent(typeof(FeralDroid))]
 public class LootSource:MonoBehaviour
 {
  public string lootTableId;
  FeralDroid droid;
  CraftingSession session;
  Func<string,bool> payout;
  bool paid,pending;
  public bool Paid=>paid;
  public bool Pending=>pending;
  public SalvageCache Cache {get;private set;}
  void Awake(){droid=GetComponent<FeralDroid>();}
  public void Bind(CraftingSession crafting){session=crafting;payout=null;}
  /// Test/tool hook: the grant returns true once it has paid out.
  public void Bind(Func<string,bool> grant){payout=grant;session=null;}
  public void Bind(Action<string> grant){payout=grant==null?null:id=>{grant(id);return true;};session=null;}
  void OnEnable(){if(!droid)droid=GetComponent<FeralDroid>();droid.Killed+=OnKilled;}
  void OnDisable(){if(droid)droid.Killed-=OnKilled;}
  void OnKilled(FeralDroid killed){if(paid)return;pending=true;TryPay();}
  void Update(){if(pending)TryPay();}
  void TryPay()
  {
   bool ok=false;
   if(payout!=null)ok=payout(lootTableId);
   else if(session){ok=session.DropLoot(lootTableId,transform.position,transform.parent,out var cache,droid?droid.displayName:null);if(ok)Cache=cache;}
   if(ok){paid=true;pending=false;}
  }
  public void Revived()
  {
   paid=pending=false;
   if(Cache)Cache.Despawn();
   Cache=null;
  }
 }
}
