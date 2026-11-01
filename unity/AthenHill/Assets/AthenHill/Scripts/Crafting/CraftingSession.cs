using System;
using System.Collections.Generic;
using System.Collections;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 [RequireComponent(typeof(GameSession))]
 public class CraftingSession:MonoBehaviour
 {
  public CraftingCatalog data;
  public PlayerCombat combat;
  public BermsTutorial tutorial;
  public Transform fabricator;
  public int lootSeed=1729;
  public CraftingModel Model {get;private set;}
  public int LootEvents {get;private set;}
  public string LastLoot {get;private set;}="";
  public string TutorialStep {get;private set;}="Dormant";
  public string Objective=>TutorialStep=="Salvage"?$"Salvage parts · Servo {Math.Min(1,Session.Shop.Quantity("droid_servo_damaged"))}/1 · Alloy {Math.Min(2,Session.Shop.Quantity("scrap_alloy"))}/2 · Residue {Math.Min(5,Session.Shop.Quantity("nanite_residue"))}/5":TutorialStep=="Fabricate"?"Use the field fabricator at Ossa's post to make a grip.":TutorialStep=="Fit"?"Fit the stabilised grip to your scrap pistol.":TutorialStep=="TestFire"?"Fire your upgraded pistol in the Outer Berms.":"";
  public GameSession Session {get;private set;}
  System.Random random;
  IEnumerator Start()
  {
   Session=GetComponent<GameSession>();
   while(Session.Shop==null)yield return null;
   if(!combat)combat=FindAnyObjectByType<PlayerCombat>();
   if(!tutorial)tutorial=FindAnyObjectByType<BermsTutorial>();
   if(!data){Debug.LogError("Ward crafting data is missing.");yield break;}
   random=new System.Random(lootSeed);
   Model=new CraftingModel(data,Session.catalog.items,Session.Shop,()=>combat&&combat.hasPistol);
   if(combat)combat.ShotFired+=OnShot;
  }
  void OnDestroy(){if(combat)combat.ShotFired-=OnShot;}
  void Update()
  {
   if(Model==null||!tutorial||tutorial.Step!=BermsStep.Complete)return;
   if(TutorialStep=="Dormant"&&Model.KnownRecipes.Count>0)TutorialStep="Salvage";
   if(TutorialStep=="Salvage"&&Model.CanCraft("recipe_grip_stabilised_pistol","station_field_fabricator",out _))TutorialStep="Fabricate";
   if(TutorialStep=="Fabricate"&&Model.Crafts>0)TutorialStep="Fit";
   if(TutorialStep=="Fit"&&Model.GripSlot!=null)TutorialStep="TestFire";
  }
  void OnShot(){if(TutorialStep=="TestFire"&&Model?.GripSlot!=null){TutorialStep="Done";Session.Notify("Stabilised grip tested. Your pistol holds steadier.","Warden Ossa");}}
  public bool Craft(out string reason)
  {
   if(Model==null||Session.State!=CityState.Fabricator){reason="wrong_station";return false;}
   bool ok=Model.TryCraft("recipe_grip_stabilised_pistol",Session.ActiveStationId,out reason);
   if(ok)TutorialStep="Fit";
   Session.Notify(ok?"Stabilised Pistol Grip crafted. Fit it to your pistol.":"Fabrication failed: "+reason,"Field Fabricator");return ok;
  }
  public bool Fit(out string reason)
  {
   if(Model==null||Session.State!=CityState.Fabricator){reason="wrong_station";return false;}
   bool ok=Model.TryFit("grip_stabilised_pistol",out reason);
   if(ok)TutorialStep="TestFire";
   Session.Notify(ok?"Stabilised grip fitted. Recoil 38 → 31.":"Cannot fit grip: "+reason,"Field Fabricator");return ok;
  }
  public bool Remove(out string reason)
  {
   if(Model==null||Session.State!=CityState.Fabricator){reason="wrong_station";return false;}
   bool ok=Model.TryRemove(out reason);
   Session.Notify(ok?"Stabilised grip returned to your pack.":"Cannot remove grip: "+reason,"Field Fabricator");return ok;
  }
  public void Salvage(string tableId)
  {
   if(Model==null||random==null)return;
   var table=data.lootTables.FirstOrDefault(x=>x.id==tableId);
   if(table==null)return;
   LootEvents++;
   var collected=new List<string>();var left=new List<string>();
   foreach(var entry in table.entries.OrderByDescending(x=>x.chance>=1))
   {
    if(entry.chance<1&&random.NextDouble()>=entry.chance)continue;
    var item=Session.catalog.items.FirstOrDefault(x=>x.id==entry.itemId);
    if(item==null){left.Add(entry.itemId+" (unknown)");continue;}
    if(Session.Shop.TryApply(new[]{new KeyValuePair<string,int>(entry.itemId,entry.quantity)},0,out _))
    {
     collected.Add(item.name+" ×"+entry.quantity);
     if(Model.Acquire(entry.itemId))Session.Notify("Schematic discovered: Stabilised Pistol Grip.","Field Pack");
    }
    else left.Add(item.name+" ×"+entry.quantity);
   }
   LastLoot="Salvaged: "+(collected.Count>0?string.Join(", ",collected):"nothing")+(left.Count>0?" · left behind (pack full): "+string.Join(", ",left):"");
   Session.Notify(LastLoot,"Field Pack");
  }
 }
}
