using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
namespace AthenHill
{
 [Serializable] public class ItemStack
 {
  public string itemId;public int quantity;
  public ItemStack(){}
  public ItemStack(string itemId,int quantity){this.itemId=itemId;this.quantity=quantity;}
  public override string ToString()=>itemId+" ×"+quantity;
 }

 /// SplitMix64: a tiny deterministic generator whose whole state is one 64-bit value, so it saves and restores exactly
 /// (System.Random cannot). The same seed always gives the same rolls on every platform.
 public sealed class LootRng
 {
  public ulong State {get;set;}
  public LootRng(ulong seed){State=seed;}
  public ulong NextULong()
  {
   unchecked
   {
    State+=0x9E3779B97F4A7C15UL;
    ulong z=State;
    z=(z^(z>>30))*0xBF58476D1CE4E5B9UL;
    z=(z^(z>>27))*0x94D049BB133111EBUL;
    return z^(z>>31);
   }
  }
  /// Uniform in [0,1) with 53 bits of precision.
  public double NextDouble()=>(NextULong()>>11)*(1.0/(1UL<<53));
  /// Uniform integer in [0,count).
  public int NextInt(int count)=>count<=1?0:(int)(NextULong()%(ulong)count);
  public string Save()=>State.ToString("x16",CultureInfo.InvariantCulture);
  public static bool TryParse(string text,out ulong state)=>ulong.TryParse(text,NumberStyles.HexNumber,CultureInfo.InvariantCulture,out state);
 }

 /// Loot rolls with bad-luck protection. Pure C#: the counters and generator state are the whole memory of the
 /// loot system and are saved with the game.
 ///  • Entries roll in declared order; each chance-based entry consumes exactly one roll, and a quantity range one more.
 ///  • Bad-luck protection: per table+item consecutive misses; once a miss count reaches pityAfter the next roll drops.
 ///  • guaranteeUntilCollected drops every time until the item has been collected once (so a lost cache cannot
 ///    strand a story part); afterwards the entry's ordinary chance applies.
 public sealed class LootBook
 {
  readonly Dictionary<string,int> misses=new Dictionary<string,int>();
  readonly HashSet<string> collected=new HashSet<string>();
  public LootRng Rng {get;private set;}
  public int Rolls {get;private set;}
  public LootBook(ulong seed){Rng=new LootRng(seed);}
  public static string Key(string tableId,string itemId)=>tableId+"/"+itemId;
  public int Misses(string tableId,string itemId)=>misses.TryGetValue(Key(tableId,itemId),out int n)?n:0;
  public bool HasCollected(string itemId)=>itemId!=null&&collected.Contains(itemId);
  public void MarkCollected(string itemId){if(!string.IsNullOrEmpty(itemId))collected.Add(itemId);}
  public List<ItemStack> Roll(LootTable table)
  {
   var result=new List<ItemStack>();
   if(table?.entries==null)return result;
   Rolls++;
   foreach(var entry in table.entries)
   {
    if(entry==null||string.IsNullOrEmpty(entry.itemId))continue;
    bool hit;
    if(entry.guaranteeUntilCollected&&!collected.Contains(entry.itemId))hit=true;
    else if(entry.chance>=1)hit=true;
    else if(entry.chance<=0)continue;
    else
    {
     string key=Key(table.id,entry.itemId);
     misses.TryGetValue(key,out int missed);
     double roll=Rng.NextDouble();
     hit=roll<entry.chance||entry.pityAfter>0&&missed>=entry.pityAfter;
     if(hit)misses.Remove(key);else misses[key]=missed+1;
    }
    if(!hit)continue;
    int min=Math.Max(1,entry.minQuantity),max=Math.Max(min,entry.maxQuantity);
    int quantity=min+(max>min?Rng.NextInt(max-min+1):0);
    var existing=result.FirstOrDefault(x=>x.itemId==entry.itemId);
    if(existing!=null)existing.quantity+=quantity;else result.Add(new ItemStack(entry.itemId,quantity));
   }
   return result;
  }
  public LootState Capture()=>new LootState{rng=Rng.Save(),rolls=Rolls,misses=misses.OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>new CountEntry{id=x.Key,count=x.Value}).ToArray(),collected=collected.OrderBy(x=>x,StringComparer.Ordinal).ToArray()};
  /// False (and nothing changes) when the saved generator state is unreadable.
  public bool Restore(LootState state)
  {
   if(state==null||!LootRng.TryParse(state.rng,out ulong rng))return false;
   Rng=new LootRng(rng);Rolls=Math.Max(0,state.rolls);
   misses.Clear();collected.Clear();
   if(state.misses!=null)foreach(var m in state.misses)if(m!=null&&!string.IsNullOrEmpty(m.id)&&m.count>0)misses[m.id]=m.count;
   if(state.collected!=null)foreach(var id in state.collected)if(!string.IsNullOrEmpty(id))collected.Add(id);
   return true;
  }
 }
 [Serializable] public class LootState {public string rng;public int rolls;public CountEntry[] misses;public string[] collected;}

 /// What a salvage cache (or a searched heap) still holds. Collection moves every item that fits in one pack
 /// transaction; anything over a stack cap stays behind.
 public sealed class SalvageContents
 {
  readonly List<ItemStack> stacks=new List<ItemStack>();
  public IReadOnlyList<ItemStack> Stacks=>stacks;
  public bool Empty=>stacks.Count==0;
  public SalvageContents(IEnumerable<ItemStack> items)
  {
   if(items!=null)foreach(var s in items)if(s!=null&&!string.IsNullOrEmpty(s.itemId)&&s.quantity>0)
   {
    var existing=stacks.FirstOrDefault(x=>x.itemId==s.itemId);
    if(existing!=null)existing.quantity+=s.quantity;else stacks.Add(new ItemStack(s.itemId,s.quantity));
   }
  }
  /// Highest rarity still inside (drives the cache glow).
  public ItemRarity BestRarity(ShopModel pack)
  {
   var best=ItemRarity.Common;
   foreach(var s in stacks){var spec=pack.Spec(s.itemId);if(spec!=null&&spec.rarity>best)best=spec.rarity;}
   return best;
  }
  /// Moves what fits. taken/left describe this attempt; unknown item IDs are left in place and reported as left.
  public bool Collect(ShopModel pack,out List<ItemStack> taken,out List<ItemStack> left)
  {
   taken=new List<ItemStack>();left=new List<ItemStack>();
   foreach(var s in stacks)
   {
    int room=pack.Spec(s.itemId)!=null?pack.Room(s.itemId):0;
    int take=Math.Min(room,s.quantity);
    if(take>0)taken.Add(new ItemStack(s.itemId,take));
    if(take<s.quantity)left.Add(new ItemStack(s.itemId,s.quantity-take));
   }
   if(taken.Count>0&&!pack.TryApply(taken.Select(x=>new KeyValuePair<string,int>(x.itemId,x.quantity)),0,out _))
   {left=stacks.Select(x=>new ItemStack(x.itemId,x.quantity)).ToList();taken.Clear();return false;}
   stacks.Clear();stacks.AddRange(left.Select(x=>new ItemStack(x.itemId,x.quantity)));
   return taken.Count>0;
  }
 }

 public enum SalvageNodeState { Ready, Searching, Depleted }
 public enum SalvageTick { None, Cancelled, Completed, Respawned }
 /// Search-and-respawn timing for a scrap heap. Pure: the caller supplies the clock and player position.
 public sealed class SalvageSearch
 {
  public float searchSeconds,respawnSeconds,cancelDistance;
  public SalvageNodeState State {get;private set;}
  float startedAt,depletedAt;
  UnityEngine.Vector3 origin;
  public SalvageSearch(float searchSeconds,float respawnSeconds,float cancelDistance){this.searchSeconds=searchSeconds;this.respawnSeconds=respawnSeconds;this.cancelDistance=cancelDistance;}
  public bool Begin(float now,UnityEngine.Vector3 player)
  {
   if(State!=SalvageNodeState.Ready)return false;
   State=SalvageNodeState.Searching;startedAt=now;origin=player;return true;
  }
  public float Progress(float now)=>State==SalvageNodeState.Searching?UnityEngine.Mathf.Clamp01((now-startedAt)/UnityEngine.Mathf.Max(.01f,searchSeconds)):State==SalvageNodeState.Depleted?1:0;
  public float RespawnRemaining(float now)=>State==SalvageNodeState.Depleted?UnityEngine.Mathf.Max(0,respawnSeconds-(now-depletedAt)):0;
  /// playing: the city is in its Play state (no menu, dialogue or pause).
  public SalvageTick Tick(float now,UnityEngine.Vector3 player,bool playing)
  {
   switch(State)
   {
    case SalvageNodeState.Searching:
     var moved=player-origin;moved.y=0;
     if(!playing||moved.magnitude>cancelDistance){State=SalvageNodeState.Ready;return SalvageTick.Cancelled;}
     if(now-startedAt>=searchSeconds){State=SalvageNodeState.Depleted;depletedAt=now;return SalvageTick.Completed;}
     return SalvageTick.None;
    case SalvageNodeState.Depleted:
     if(now-depletedAt>=respawnSeconds){State=SalvageNodeState.Ready;return SalvageTick.Respawned;}
     return SalvageTick.None;
    default:return SalvageTick.None;
   }
  }
 }
}
