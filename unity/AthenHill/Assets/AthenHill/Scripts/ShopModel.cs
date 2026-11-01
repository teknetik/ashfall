using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 public sealed class ShopModel
 {
  readonly Dictionary<string,ItemSpec> items;
  readonly Dictionary<string,int> quantities;
  public int Credits {get;private set;}
  public int Purchases {get;private set;}
  public int Sales {get;private set;}
  public ShopModel(IEnumerable<ItemSpec> definitions,int credits=25)
  {
   if(credits<0)throw new ArgumentOutOfRangeException(nameof(credits));
   items=definitions.ToDictionary(x=>x.id,x=>new ItemSpec{id=x.id,name=x.name,description=x.description,buyPrice=x.buyPrice,sellPrice=x.sellPrice,startingQuantity=x.startingQuantity,tags=x.tags==null?null:(string[])x.tags.Clone(),maxStack=x.maxStack,excludeFromTrade=x.excludeFromTrade});
   if(items.Values.Any(x=>x.buyPrice<0||x.sellPrice<0||x.startingQuantity<0||x.maxStack<0||x.maxStack>0&&x.startingQuantity>x.maxStack))throw new ArgumentException("Prices, quantities and caps must be valid.");
   quantities=items.ToDictionary(x=>x.Key,x=>x.Value.startingQuantity);Credits=credits;
  }
  public int Quantity(string id)=>id!=null&&quantities.TryGetValue(id,out int q)?q:0;
  public IReadOnlyCollection<ItemSpec> Definitions=>items.Values;
  /// Validate all deltas against one snapshot, then commit once. Duplicate IDs are summed.
  public bool TryApply(IEnumerable<KeyValuePair<string,int>> changes,int creditDelta,out string reason)
  {
   var deltas=new Dictionary<string,long>();
   var next=new Dictionary<string,int>();int credits;
   try
   {
    credits=checked(Credits+creditDelta);
    if(credits<0){reason="insufficient_credits";return false;}
    foreach(var change in changes)
    {
     if(change.Key==null||!items.ContainsKey(change.Key)){reason="unknown_item";return false;}
     deltas[change.Key]=checked((deltas.TryGetValue(change.Key,out var previous)?previous:0)+change.Value);
    }
    foreach(var pair in deltas)
    {
     long quantity=checked(quantities[pair.Key]+pair.Value);
     if(quantity<0){reason="insufficient_items";return false;}
     if(quantity>int.MaxValue){reason="overflow";return false;}
     next[pair.Key]=(int)quantity;
    }
   }
   catch(OverflowException){reason="overflow";return false;}
   foreach(var pair in next)
   {
    int cap=items[pair.Key].maxStack;
    if(cap>0&&pair.Value>cap){reason="stack_full";return false;}
   }
   Credits=credits;foreach(var pair in next)quantities[pair.Key]=pair.Value;
   reason="ok";return true;
  }
  /// Adds found items and credits in one step; nothing changes if either would overflow.
  public bool Grant(string id,int quantity,int credits,out string message)
  {
   if(quantity<0||credits<0){message="Rewards cannot be negative.";return false;}
   if(quantity>0&&(id==null||!items.ContainsKey(id))){message="That item is not available.";return false;}
   if(!TryApply(quantity>0?new[]{new KeyValuePair<string,int>(id,quantity)}:Array.Empty<KeyValuePair<string,int>>(),credits,out _)){message="This reward cannot be added.";return false;}
   message=$"Received {credits} credits"+(quantity>0?$" and {quantity} × {items[id].name}.":".");return true;
  }
#if UNITY_EDITOR || DEBUG
  // Developer adjustments are not trades: no sale/purchase counters or prices change.
  public bool Remove(string id,int quantity,out string message)
  {
   if(quantity<=0||id==null||!items.ContainsKey(id)){message="Invalid item or quantity.";return false;}
   if(Quantity(id)<quantity){message="Not enough items carried.";return false;}
   if(!TryApply(new[]{new KeyValuePair<string,int>(id,-quantity)},0,out _)){message="Not enough items carried.";return false;}
   message=$"Removed {quantity} × {items[id].name}.";return true;
  }
  public bool RemoveCredits(int amount,out string message)
  {
   if(amount<=0){message="Amount must be positive.";return false;}
   if(Credits<amount){message="Not enough credits.";return false;}
   if(!TryApply(Array.Empty<KeyValuePair<string,int>>(),-amount,out _)){message="Not enough credits.";return false;}
   message=$"Removed {amount} credits.";return true;
  }
#endif
  public bool Trade(string id,bool buy,out string message)
  {
   if(id==null||!items.TryGetValue(id,out var item)){message="That item is not available.";return false;}
   if(item.excludeFromTrade){message="This item is not tradeable.";return false;}
   int price=buy?item.buyPrice:item.sellPrice;
   if(buy&&Credits<price){message=$"You need {price-Credits} more credits for {item.name}.";return false;}
   if(!buy&&Quantity(id)<1){message=$"You have no {item.name} to sell.";return false;}
   if((buy?Purchases:Sales)==int.MaxValue||!TryApply(new[]{new KeyValuePair<string,int>(id,buy?1:-1)},buy?-price:price,out _)){message="This trade cannot be completed.";return false;}
   if(buy)Purchases++;else Sales++;
   message=$"{(buy?"Bought":"Sold")} {item.name} for {price} credit{(price==1?"":"s")}.";return true;
  }
 }
}
