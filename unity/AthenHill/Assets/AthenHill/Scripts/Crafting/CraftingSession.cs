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
  [Tooltip("Recipe the post-primer grip tutorial walks through.")]
  public string tutorialRecipeId="recipe_grip_stabilised_pistol";
  public CraftingModel Model {get;private set;}
  public int LootEvents {get;private set;}
  public string LastLoot {get;private set;}="";
  public string TutorialStep {get;private set;}="Dormant";
  public string Objective
  {
   get
   {
    var recipe=Model?.Recipe(tutorialRecipeId);if(recipe==null)return "";
    var output=CraftingText.ItemName(Model,recipe.outputItemId);
    switch(TutorialStep)
    {
     case "Salvage":return "Salvage parts · "+string.Join(" · ",recipe.inputs.Select(i=>$"{CraftingText.InputName(Model,i)} {Math.Min(i.quantity,Model.Available(i))}/{i.quantity}"));
     case "Fabricate":return $"Use the field fabricator at Ossa's post to make a {output}.";
     case "Fit":return $"Fit the {output} to your {Model.Loadout.WeaponName}.";
     case "TestFire":return "Fire your upgraded pistol in the Outer Berms.";
     default:return "";
    }
   }
  }
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
   if(combat){combat.BindLoadout(Model.Loadout);combat.ShotFired+=OnShot;}
  }
  void OnDestroy(){if(combat){combat.ShotFired-=OnShot;combat.BindLoadout(null);}}
  string TutorialOutput=>Model?.Recipe(tutorialRecipeId)?.outputItemId;
  bool TutorialFitted=>TutorialOutput!=null&&Model.Loadout.FittedMods.Any(x=>x.Value==TutorialOutput);
  void Update()
  {
   if(Model==null||!tutorial||tutorial.Step!=BermsStep.Complete||TutorialStep=="Done")return;
   if(TutorialStep=="Dormant"&&Model.Knows(tutorialRecipeId))TutorialStep="Salvage";
   if(TutorialStep=="Salvage"&&Model.CanCraft(tutorialRecipeId,Model.Recipe(tutorialRecipeId).stationId,out _))TutorialStep="Fabricate";
   if(TutorialStep=="Fabricate"&&Model.CraftCount(tutorialRecipeId)>0)TutorialStep="Fit";
   if(TutorialStep=="Fit"&&TutorialFitted)TutorialStep="TestFire";
  }
  void OnShot(){if(TutorialStep=="TestFire"&&TutorialFitted){TutorialStep="Done";Session.Notify("Stabilised grip tested. Your pistol holds steadier.","Warden Ossa");}}
  bool AtStation(out string reason){if(Model==null||Session.State!=CityState.Fabricator){reason="wrong_station";return false;}reason="ok";return true;}
  public bool Craft(string recipeId,out string reason)
  {
   if(!AtStation(out reason))return false;
   var recipe=Model.Recipe(recipeId);
   bool ok=Model.TryCraft(recipeId,Session.ActiveStationId,out reason);
   Session.Notify(ok?$"{CraftingText.ItemName(Model,recipe.outputItemId)} fabricated."+(Model.Loadout.Modifier(recipe.outputItemId)!=null?" Fit it to your pistol.":""):"Fabrication failed. "+CraftingText.Reason(reason,Model,recipe),"Field Fabricator");
   return ok;
  }
  public bool Fit(string itemId,out string reason)
  {
   if(!AtStation(out reason))return false;
   var before=Model.Loadout.Stats;
   bool ok=Model.TryFit(itemId,out reason);
   var mod=Model.Loadout.Modifier(itemId);
   Session.Notify(ok?$"{CraftingText.ItemName(Model,itemId)} fitted. {CraftingText.StatChanges(data,before,Model.Loadout.Stats)}":"Cannot fit. "+CraftingText.Reason(reason,Model,null,reason=="stack_full"&&mod!=null?Model.Loadout.Fitted(mod.slot):itemId),"Field Fabricator");
   return ok;
  }
  public bool Remove(string slot,out string reason)
  {
   if(!AtStation(out reason))return false;
   var itemId=Model.Loadout.Fitted(slot);
   bool ok=Model.TryRemove(slot,out reason);
   Session.Notify(ok?$"{CraftingText.ItemName(Model,itemId)} returned to your pack.":"Cannot remove. "+CraftingText.Reason(reason,Model,null,itemId),"Field Fabricator");
   return ok;
  }
  public void Salvage(string tableId)
  {
   if(Model==null||random==null)return;
   var table=data.lootTables.FirstOrDefault(x=>x.id==tableId);
   if(table==null)return;
   LootEvents++;
   var collected=new List<string>();var left=new List<string>();var discovered=new List<CraftRecipe>();
   foreach(var entry in table.entries.OrderByDescending(x=>x.chance>=1))
   {
    if(entry.chance<1&&random.NextDouble()>=entry.chance)continue;
    var item=Session.catalog.items.FirstOrDefault(x=>x.id==entry.itemId);
    if(item==null){left.Add(entry.itemId+" (unknown)");continue;}
    int quantity=Math.Max(1,entry.minQuantity);
    if(Session.Shop.TryApply(new[]{new KeyValuePair<string,int>(entry.itemId,quantity)},0,out _))
    {
     collected.Add(item.name+" ×"+quantity);
     discovered.AddRange(Model.Acquire(entry.itemId));
    }
    else left.Add(item.name+" ×"+quantity);
   }
   LastLoot="Salvaged: "+(collected.Count>0?string.Join(", ",collected):"nothing")+(left.Count>0?" · left behind (pack full): "+string.Join(", ",left):"");
   Session.Notify(LastLoot+(discovered.Count>0?" "+CraftingText.Discovered(discovered):""),"Field Pack");
  }
 }
}
