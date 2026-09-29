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
  [Tooltip("Seed for a new game's loot generator. Saved games keep their own generator state.")]
  public int lootSeed=1729;
  [Tooltip("Physical drop spawned at a droid wreck or beside a searched heap whose leftovers did not fit.")]
  public SalvageCache cachePrefab;
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
  public LootBook Loot {get;private set;}
  /// A pickup (cache or heap) moved items into the pack. Raised after the pack changed.
  public event Action<LootPickup> Collected;
  IEnumerator Start()
  {
   Session=GetComponent<GameSession>();
   while(Session.Shop==null)yield return null;
   if(!combat)combat=FindAnyObjectByType<PlayerCombat>();
   if(!tutorial)tutorial=FindAnyObjectByType<BermsTutorial>();
   if(!data){Debug.LogError("Ward crafting data is missing.");yield break;}
   Loot=new LootBook(unchecked((ulong)lootSeed));
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
  LootTable Table(string id)=>data&&data.lootTables!=null?data.lootTables.FirstOrDefault(x=>x.id==id):null;
  /// Rolls a droid's table and leaves a salvage cache at its wreck. False only when the loot system is not ready,
  /// so the caller can retry instead of marking the kill paid.
  public bool DropLoot(string tableId,Vector3 at,Transform parent,out SalvageCache cache,string source=null)
  {
   cache=null;
   if(Model==null||Loot==null||Session==null||Session.Shop==null)return false;
   var table=Table(tableId);
   if(table==null){Debug.LogWarning("Unknown loot table "+tableId+"; nothing dropped.");return true;}
   var rolled=Loot.Roll(table);LootEvents++;
   LastLoot="Dropped: "+Describe(rolled);
   if(rolled.Count==0)return true;
   if(!cachePrefab){Collect(new SalvageContents(rolled),source,at);return true;}
   var ground=SalvageCache.Ground(at,cachePrefab.groundMask);
   cache=Instantiate(cachePrefab,ground,Quaternion.Euler(0,UnityEngine.Random.Range(0,360f),0),parent);
   cache.name=cachePrefab.name+(string.IsNullOrEmpty(source)?"":" · "+source);
   cache.Fill(this,rolled,source);
   return true;
  }
  /// A searched scrap heap: rolls straight into the pack; anything over a stack cap is left in a cache beside it.
  public void SearchHeap(string tableId,Vector3 at,Transform parent,string source)
  {
   if(Model==null||Loot==null)return;
   var table=Table(tableId);if(table==null){Debug.LogWarning("Unknown loot table "+tableId);return;}
   var rolled=Loot.Roll(table);LootEvents++;
   if(rolled.Count==0){LastLoot="Nothing useful";Session.Notify($"Nothing useful in this {(source??"heap").ToLowerInvariant()}.","Field Pack");Collected?.Invoke(new LootPickup{source=source,position=at});return;}
   var contents=new SalvageContents(rolled);
   Collect(contents,source,at);
   if(!contents.Empty&&cachePrefab)
   {
    var cache=Instantiate(cachePrefab,SalvageCache.Ground(at,cachePrefab.groundMask),Quaternion.identity,parent);
    cache.name=cachePrefab.name+" · "+source;cache.Fill(this,contents.Stacks,source);
   }
  }
  /// Moves what fits from a cache into the pack, reveals schematics for new parts and reports the pickup.
  public LootPickup Collect(SalvageContents contents,string source,Vector3 at)
  {
   var pickup=new LootPickup{source=source,position=at};
   if(Model==null||contents==null)return pickup;
   contents.Collect(Session.Shop,out pickup.taken,out pickup.left);
   foreach(var s in pickup.taken){Loot.MarkCollected(s.itemId);pickup.discovered.AddRange(Model.Acquire(s.itemId));}
   LastLoot=(pickup.taken.Count>0?"Collected: "+Describe(pickup.taken):"Collected nothing")+(pickup.left.Count>0?" · pack full, left in the cache: "+Describe(pickup.left):"");
   Session.Notify(LastLoot+(pickup.discovered.Count>0?" "+CraftingText.Discovered(pickup.discovered):""),"Field Pack");
   Collected?.Invoke(pickup);
   return pickup;
  }
  string Describe(IEnumerable<ItemStack> stacks)=>string.Join(", ",stacks.Select(x=>$"{CraftingText.ItemName(Model,x.itemId)} ×{x.quantity}"));
 }
 public class LootPickup
 {
  public string source;
  public Vector3 position;
  public List<ItemStack> taken=new List<ItemStack>(),left=new List<ItemStack>();
  public List<CraftRecipe> discovered=new List<CraftRecipe>();
 }
}
