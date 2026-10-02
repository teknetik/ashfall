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
  public Transform fabricator;
  [Tooltip("Seed for a new game's loot generator when Fresh Seed Per New Game is off. Saved games keep their own generator state.")]
  public int lootSeed=1729;
  [Tooltip("Each new game rolls loot from a fresh seed (then saved with the game). Off = always start from Loot Seed (repeatable QA runs).")]
  public bool freshSeedPerNewGame=true;
  [Tooltip("Physical drop spawned at a droid wreck or beside a searched heap whose leftovers did not fit.")]
  public SalvageCache cachePrefab;
  [Tooltip("Uncollected caches stay in the world this many seconds of game time (menus that pause the game do not count). They no longer vanish when a nest re-forms.")]
  [Min(30)]public float cacheLifetimeSeconds=600;
  [Tooltip("At most this many uncollected caches exist at once; a new drop retires the oldest (caches holding rare parts last).")]
  [Min(1)]public int maxCaches=12;
  public CraftingModel Model {get;private set;}
  public int LootEvents {get;private set;}
  public string LastLoot {get;private set;}="";
  public GameSession Session {get;private set;}
  public LootBook Loot {get;private set;}
  /// A pickup (cache or heap) moved items into the pack. Raised after the pack changed.
  public event Action<LootPickup> Collected;
  IEnumerator Start()
  {
   Session=GetComponent<GameSession>();
   while(Session.Shop==null)yield return null;
   if(!combat)combat=FindAnyObjectByType<PlayerCombat>();
   if(!data){Debug.LogError("Ward crafting data is missing.");yield break;}
   Loot=new LootBook(freshSeedPerNewGame?unchecked((ulong)DateTime.UtcNow.Ticks):unchecked((ulong)lootSeed));
   Model=new CraftingModel(data,Session.catalog.items,Session.Shop,()=>combat&&combat.hasPistol,character:Session.Character);
   if(combat){combat.BindLoadout(Model.Loadout);combat.BindCraftingModel(Model);}
   Session.PartBought+=OnPartBought;
  }
  void OnDestroy(){if(combat){combat.BindCraftingModel(null);combat.BindLoadout(null);}if(Session)Session.PartBought-=OnPartBought;}
  /// A part bought at a counter reveals the schematics that use it, exactly like finding one.
  void OnPartBought(PartPurchase purchase)
  {
   if(Model==null||purchase==null)return;
   var found=Model.Acquire(purchase.itemId);
   if(found.Count>0)purchase.note+=" "+CraftingText.Discovered(found);
  }
  /// Spawns a cache on a clear, flat spot near the wreck or heap (SalvageCache.FindSpot), after retiring the oldest
  /// caches over the cap.
  SalvageCache SpawnCache(Vector3 near,Quaternion rotation,Transform parent,IEnumerable<ItemStack> items,string source)
  {
   foreach(var old in SalvageCache.Evictions(SalvageCache.Active,maxCaches-1))old.Despawn();
   var others=new List<Vector3>();foreach(var c in SalvageCache.Active)if(c)others.Add(c.transform.position);
   cachePrefab.FindSpot(near,rotation,others,out var at);
   var cache=Instantiate(cachePrefab,at,rotation,parent);
   cache.name=cachePrefab.name+(string.IsNullOrEmpty(source)?"":" · "+source);
   cache.lifetimeSeconds=cacheLifetimeSeconds;
   cache.Fill(this,items,source);
   return cache;
  }
  /// Who signs the fabrication notices: the open workbench's title.
  string Bench=>Session&&Session.ActiveStation&&!string.IsNullOrEmpty(Session.ActiveStation.title)?Session.ActiveStation.title:"Workbench";
  bool AtStation(out string reason){if(Model==null||Session.State!=CityState.Fabricator){reason="wrong_station";return false;}reason="ok";return true;}
  public bool Craft(string recipeId,out string reason)
  {
   if(!AtStation(out reason))return false;
   var recipe=Model.Recipe(recipeId);
   bool ok=Model.TryCraft(recipeId,Session.ActiveStationId,out reason);
   Session.Notify(ok?$"{CraftingText.ItemName(Model,recipe.outputItemId)} fabricated."+(Model.Loadout.Modifier(recipe.outputItemId)!=null?" Fit it to a compatible weapon.":""):"Fabrication failed. "+CraftingText.Reason(reason,Model,recipe),Bench);
   return ok;
  }
  public bool Fit(string itemId,out string reason)
   =>Fit(Model?.Loadout.WeaponId,itemId,out reason);
  public bool Fit(string weaponId,string itemId,out string reason)
  {
   if(!AtStation(out reason))return false;
   var loadout=Model.GetLoadout(weaponId);
   var before=loadout?.Stats??default;
   bool ok=Model.TryFit(weaponId,itemId,out reason);
   var mod=loadout?.Modifier(itemId);
   Session.Notify(ok?$"{CraftingText.ItemName(Model,itemId)} fitted. {CraftingText.StatChanges(data,before,loadout.Stats)}":"Cannot fit. "+CraftingText.Reason(reason,Model,null,reason=="stack_full"&&mod!=null?loadout.Fitted(mod.slot):itemId),Bench);
   return ok;
  }
  public bool Remove(string slot,out string reason)
   =>Remove(Model?.Loadout.WeaponId,slot,out reason);
  public bool Remove(string weaponId,string slot,out string reason)
  {
   if(!AtStation(out reason))return false;
   var itemId=Model.GetLoadout(weaponId)?.Fitted(slot);
   bool ok=Model.TryRemove(weaponId,slot,out reason);
   Session.Notify(ok?$"{CraftingText.ItemName(Model,itemId)} returned to your pack.":"Cannot remove. "+CraftingText.Reason(reason,Model,null,itemId),Bench);
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
   cache=SpawnCache(at,Quaternion.Euler(0,UnityEngine.Random.Range(0,360f),0),parent,rolled,source);
   return true;
  }
  /// A searched scrap heap: rolls straight into the pack; anything over a stack cap is left in a cache beside it.
  public void SearchHeap(string tableId,Vector3 at,Transform parent,string source)
  {
   if(Model==null||Loot==null)return;
   var table=Table(tableId);if(table==null){Debug.LogWarning("Unknown loot table "+tableId);return;}
   var rolled=Loot.Roll(table);LootEvents++;
   // Pickups are reported by the salvage toast and the event log; the notice banner stays free for prompts.
   if(rolled.Count==0){LastLoot="Nothing useful";Session.Record($"Nothing useful in this {(source??"heap").ToLowerInvariant()}.","Field Pack");Collected?.Invoke(new LootPickup{source=source,position=at});return;}
   var contents=new SalvageContents(rolled);
   Collect(contents,source,at);
   if(!contents.Empty&&cachePrefab)SpawnCache(at,Quaternion.Euler(0,UnityEngine.Random.Range(0,360f),0),parent,contents.Stacks,source);
  }
  /// Moves what fits from a cache into the pack, reveals schematics for new parts and reports the pickup.
  public LootPickup Collect(SalvageContents contents,string source,Vector3 at)
  {
   var pickup=new LootPickup{source=source,position=at};
   if(Model==null||contents==null)return pickup;
   contents.Collect(Session.Shop,out pickup.taken,out pickup.left);
   foreach(var s in pickup.taken){Loot.MarkCollected(s.itemId);pickup.discovered.AddRange(Model.Acquire(s.itemId));}
   LastLoot=(pickup.taken.Count>0?"Collected: "+Describe(pickup.taken):"Collected nothing")+(pickup.left.Count>0?" · pack full, left in the cache: "+Describe(pickup.left):"");
   Session.Record(LastLoot+(pickup.discovered.Count>0?" "+CraftingText.Discovered(pickup.discovered):""),"Field Pack");
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
