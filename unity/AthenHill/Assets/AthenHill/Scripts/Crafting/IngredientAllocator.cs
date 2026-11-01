using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// Complete deterministic allocation over a shared inventory pool. A failed branch restores its own unit.
 public static class IngredientAllocator
 {
  public static bool TryAllocate(CraftIngredient[] inputs,IEnumerable<ItemSpec> catalog,ShopModel shop,out List<KeyValuePair<string,int>> consumption)
  {
   consumption=new List<KeyValuePair<string,int>>();
   if(inputs==null||inputs.Any(x=>x==null||x.quantity<1||x.kind!="item"&&x.kind!="tag"))return false;
   var items=catalog.ToArray();
   var remaining=items.ToDictionary(x=>x.id,x=>shop.Quantity(x.id));
   var chosen=new Dictionary<string,int>();
   bool Search(int inputIndex,int unit)
   {
    if(inputIndex==inputs.Length)return true;
    var input=inputs[inputIndex];
    if(unit==input.quantity)return Search(inputIndex+1,0);
    var candidates=items.Select((item,index)=>new {item,index})
     .Where(x=>input.kind=="item"?x.item.id==input.id:x.item.tags!=null&&Array.IndexOf(x.item.tags,input.id)>=0)
     .OrderBy(x=>x.item.sellPrice).ThenBy(x=>x.index);
    foreach(var candidate in candidates)
    {
     string id=candidate.item.id;
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
