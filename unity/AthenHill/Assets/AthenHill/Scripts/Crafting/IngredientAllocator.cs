using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// Complete deterministic allocation over a shared inventory pool. A failed branch restores its own unit.
 public static class IngredientAllocator
 {
  public static bool TryAllocate(CraftIngredient[] inputs,IEnumerable<ItemSpec> catalog,ShopModel shop,out List<KeyValuePair<string,int>> consumption)
   =>TryAllocate(inputs,catalog,shop.Quantity,out consumption);
  /// The same search over any pool (5 Oct 2026: the pack plus the home locker for Brann's bench).
  public static bool TryAllocate(CraftIngredient[] inputs,IEnumerable<ItemSpec> catalog,Func<string,int> quantity,out List<KeyValuePair<string,int>> consumption)
  {
   consumption=new List<KeyValuePair<string,int>>();
   if(inputs==null||catalog==null||quantity==null||inputs.Any(x=>x==null||x.quantity<1||x.kind!="item"&&x.kind!="tag"))return false;
   var items=catalog.Where(x=>x!=null&&!string.IsNullOrEmpty(x.id)).ToArray();
   var remaining=new Dictionary<string,int>(items.Length);
   foreach(var item in items)if(!remaining.ContainsKey(item.id))remaining[item.id]=Math.Max(0,quantity(item.id));
   var candidatesByInput=new string[inputs.Length][];
   for(int i=0;i<inputs.Length;i++)
   {
    var input=inputs[i];
    candidatesByInput[i]=items.Select((item,index)=>new {item,index})
     .Where(x=>input.kind=="item"?x.item.id==input.id:x.item.tags!=null&&Array.IndexOf(x.item.tags,input.id)>=0)
     .OrderBy(x=>x.item.sellPrice).ThenBy(x=>x.index)
     .Select(x=>x.item.id).Distinct().ToArray();
    long available=0;
    foreach(var id in candidatesByInput[i])available+=remaining[id];
    if(available<input.quantity)return false;
   }
   var chosen=new Dictionary<string,int>();
   bool Search(int inputIndex,int unit)
   {
    if(inputIndex==inputs.Length)return true;
    var input=inputs[inputIndex];
    if(unit==input.quantity)return Search(inputIndex+1,0);
    int need=input.quantity-unit;
    long avail=0;
    foreach(var id in candidatesByInput[inputIndex])avail+=remaining[id];
    if(avail<need)return false;
    foreach(var id in candidatesByInput[inputIndex])
    {
     if(remaining[id]<1)continue;
     remaining[id]--;chosen[id]=chosen.TryGetValue(id,out int count)?count+1:1;
     if(Search(inputIndex,unit+1))return true;
     remaining[id]++;if(--chosen[id]==0)chosen.Remove(id);
    }
    return false;
   }
   if(!Search(0,0))return false;
   consumption=items.Where(x=>chosen.ContainsKey(x.id)).Select(x=>new KeyValuePair<string,int>(x.id,chosen[x.id])).ToList();
   return true;
  }
 }
}
