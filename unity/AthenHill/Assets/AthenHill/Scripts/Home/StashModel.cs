using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// The home locker (5 Oct 2026): item stacks kept outside the field pack. One stack per item kind takes a slot; there is
 /// no weight limit and no per-stack cap. Every move goes through the pack's own transaction first (ShopModel.TryApply),
 /// so a move the pack refuses (a full pack, a stack cap) changes nothing on either side.
 public sealed class StashModel
 {
  readonly Dictionary<string,int> items=new Dictionary<string,int>();
  public int SlotCapacity {get;}
  public StashModel(int slotCapacity=60){SlotCapacity=Math.Max(1,slotCapacity);}
  public event Action Changed;
  public int Quantity(string id)=>id!=null&&items.TryGetValue(id,out var q)?q:0;
  public IEnumerable<KeyValuePair<string,int>> Stored=>items.Where(x=>x.Value>0).OrderBy(x=>x.Key,StringComparer.Ordinal);
  public int SlotsUsed=>items.Count(x=>x.Value>0);
  public int TotalItems=>items.Values.Sum();
  /// Moves count units from the pack into the locker. Reasons: "bad_count", "not_carried", "locker_full", or the pack's.
  public bool Store(ShopModel pack,string id,int count,out string reason)
  {
   if(pack==null||id==null||count<1){reason="bad_count";return false;}
   if(pack.Quantity(id)<count){reason="not_carried";return false;}
   if(Quantity(id)==0&&SlotsUsed>=SlotCapacity){reason="locker_full";return false;}
   if(!pack.TryApply(new[]{new KeyValuePair<string,int>(id,-count)},0,out reason))return false;
   items[id]=Quantity(id)+count;reason="ok";Changed?.Invoke();return true;
  }
  /// Moves count units from the locker into the pack. Reasons: "bad_count", "not_stored", or the pack's (stack_full,
  /// capacity), in which case nothing moves.
  public bool Take(ShopModel pack,string id,int count,out string reason)
  {
   if(pack==null||id==null||count<1){reason="bad_count";return false;}
   if(Quantity(id)<count){reason="not_stored";return false;}
   if(!pack.TryApply(new[]{new KeyValuePair<string,int>(id,count)},0,out reason))return false;
   int left=Quantity(id)-count;if(left>0)items[id]=left;else items.Remove(id);
   reason="ok";Changed?.Invoke();return true;
  }
  /// Uses stored units directly (the bench drawing parts from the locker, after its own pack transaction committed).
  public bool Consume(string id,int count)
  {
   if(id==null||count<1||Quantity(id)<count)return false;
   int left=Quantity(id)-count;if(left>0)items[id]=left;else items.Remove(id);
   Changed?.Invoke();return true;
  }
  /// How many units of a stored item the pack would accept right now (stack cap and capacity), at most what is stored.
  public int TakeableCount(ShopModel pack,string id)
  {
   int stored=Quantity(id);if(pack==null||stored<1)return 0;
   int low=0,high=Math.Min(stored,pack.Room(id));
   // capacity (weight, slots) is a monotone limit: binary search the largest accepted count
   while(low<high)
   {
    int mid=(low+high+1)/2;
    if(pack.CanApply(new[]{new KeyValuePair<string,int>(id,mid)},0,out _))low=mid;else high=mid-1;
   }
   return low;
  }
  public ItemStack[] Capture()=>Stored.Select(x=>new ItemStack(x.Key,x.Value)).ToArray();
  /// Save restore. Unknown ids (known returns false) are skipped and returned; stacks beyond the slot capacity are kept
  /// (a smaller locker in a later build must never delete what was stored), they just leave no free slot.
  public List<string> Restore(IEnumerable<ItemStack> stacks,Func<string,bool> known)
  {
   items.Clear();var skipped=new List<string>();
   if(stacks!=null)foreach(var s in stacks)
   {
    if(s==null||string.IsNullOrEmpty(s.itemId)||s.quantity<1)continue;
    if(known!=null&&!known(s.itemId)){skipped.Add(s.itemId);continue;}
    items[s.itemId]=Quantity(s.itemId)+s.quantity;
   }
   Changed?.Invoke();return skipped;
  }
 }
}
