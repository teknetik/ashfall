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
   items=definitions.ToDictionary(x=>x.id,x=>new ItemSpec{id=x.id,name=x.name,description=x.description,buyPrice=x.buyPrice,sellPrice=x.sellPrice,startingQuantity=x.startingQuantity,tags=x.tags==null?null:(string[])x.tags.Clone(),maxStack=x.maxStack,excludeFromTrade=x.excludeFromTrade,rarity=x.rarity,sellOnly=x.sellOnly,icon=x.icon,partsPrice=x.partsPrice,weightKg=x.weightKg});
   if(items.Values.Any(x=>x.buyPrice<0||x.sellPrice<0||x.partsPrice<0||x.startingQuantity<0||x.maxStack<0||x.weightKg<0||x.maxStack>0&&x.startingQuantity>x.maxStack))throw new ArgumentException("Prices, quantities and caps must be valid.");
   quantities=items.ToDictionary(x=>x.Key,x=>x.Value.startingQuantity);Credits=credits;
  }
  public int Quantity(string id)=>id!=null&&quantities.TryGetValue(id,out int q)?q:0;
  public IReadOnlyCollection<ItemSpec> Definitions=>items.Values;
  /// Return null when the projected pack fits, or a player-facing failure code when it does not.
  public Func<IReadOnlyDictionary<string,int>,string> CapacityFailure {get;set;}
  public float PackWeightKg=>quantities.Sum(x=>x.Value*items[x.Key].weightKg);
  public ItemSpec Spec(string id)=>id!=null&&items.TryGetValue(id,out var item)?item:null;
  /// How many more of this item the pack can hold (its stack cap), or int.MaxValue when uncapped.
  public int Room(string id)
  {
   var item=Spec(id);if(item==null)return 0;
   return item.maxStack>0?Math.Max(0,item.maxStack-Quantity(id)):int.MaxValue-Quantity(id);
  }
  /// Salvage Mira buys but does not stock: shown in the shop's Sell salvage list while carried.
  public static bool BuysAsSalvage(ItemSpec item)=>item!=null&&item.sellOnly&&!item.excludeFromTrade&&item.sellPrice>0;
  /// Crafting parts Mira stocks under Buy parts: a premium price is set, the part is common or uncommon (rare parts stay
  /// loot-only) and it is tradeable.
  public static bool SellsAsPart(ItemSpec item)=>item!=null&&item.partsPrice>0&&item.rarity!=ItemRarity.Rare&&!item.excludeFromTrade;
  /// One atomic purchase of crafting parts at Mira's premium price. Nothing changes if the credits or pack room fall short.
  public bool BuyPart(string id,int count,out string message)
  {
   if(id==null||!items.TryGetValue(id,out var item)){message="That item is not available.";return false;}
   if(!SellsAsPart(item)){message=item.rarity==ItemRarity.Rare?$"Mira does not stock {item.name}. Rare parts only come out of the Berms.":$"Mira does not stock {item.name}.";return false;}
   if(count<1){message="Choose at least one part to buy.";return false;}
   long total=(long)item.partsPrice*count;
   if(total>Credits){message=$"You need {total-Credits} more credits for {(count==1?item.name:$"{count} × {item.name}")}.";return false;}
   if(Room(id)<count){message=item.maxStack>0?$"Your pack cannot hold more {item.name} (limit {item.maxStack}).":"Your pack cannot hold that many.";return false;}
   if(Purchases==int.MaxValue){message="This trade cannot be completed.";return false;}
   if(!TryApply(new[]{new KeyValuePair<string,int>(id,count)},-(int)total,out var reason)){message=reason.Contains("capacity")?reason:"This trade cannot be completed.";return false;}
   Purchases++;
   message=count==1?$"Bought {item.name} for {total} credit{(total==1?"":"s")}.":$"Bought {count} × {item.name} for {total} credits.";return true;
  }
  /// Check a proposed pack transaction without changing balances.
  public bool CanApply(IEnumerable<KeyValuePair<string,int>> changes,int creditDelta,out string reason)
   =>Validate(changes,creditDelta,out _,out _,out reason);
  /// Validate all deltas against one snapshot, then commit once. Duplicate IDs are summed.
  public bool TryApply(IEnumerable<KeyValuePair<string,int>> changes,int creditDelta,out string reason)
  {
   if(!Validate(changes,creditDelta,out var next,out var credits,out reason))return false;
   Credits=credits;foreach(var pair in next)quantities[pair.Key]=pair.Value;
   reason="ok";return true;
  }
  bool Validate(IEnumerable<KeyValuePair<string,int>> changes,int creditDelta,out Dictionary<string,int> next,out int credits,out string reason)
  {
   var deltas=new Dictionary<string,long>();
   next=new Dictionary<string,int>();credits=0;
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
   if(CapacityFailure!=null)
   {
    var projected=new Dictionary<string,int>(quantities);
    foreach(var pair in next)projected[pair.Key]=pair.Value;
    reason=CapacityFailure(projected);
    if(reason!=null)return false;
   }
   reason="ok";return true;
  }
  /// Adds found items and credits in one step; nothing changes if either would overflow.
  public bool Grant(string id,int quantity,int credits,out string message)
  {
   if(quantity<0||credits<0){message="Rewards cannot be negative.";return false;}
   if(quantity>0&&(id==null||!items.ContainsKey(id))){message="That item is not available.";return false;}
   if(!TryApply(quantity>0?new[]{new KeyValuePair<string,int>(id,quantity)}:Array.Empty<KeyValuePair<string,int>>(),credits,out var reason)){message=reason.Contains("capacity")?reason:"This reward cannot be added.";return false;}
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
   if(!buy)return Sell(id,1,out message);
   if(item.excludeFromTrade){message="This item is not tradeable.";return false;}
   if(item.sellOnly){message=$"Mira buys {item.name} but does not stock it.";return false;}
   int price=item.buyPrice;
   if(Credits<price){message=$"You need {price-Credits} more credits for {item.name}.";return false;}
   if(Purchases==int.MaxValue){message="This trade cannot be completed.";return false;}
   if(!TryApply(new[]{new KeyValuePair<string,int>(id,1)},-price,out var reason)){message=reason.Contains("capacity")?reason:"This trade cannot be completed.";return false;}
   Purchases++;
   message=$"Bought {item.name} for {price} credit{(price==1?"":"s")}.";return true;
  }
  /// One atomic sale of several units: every unit and its credits move together, or nothing changes.
  public bool Sell(string id,int count,out string message)
  {
   if(id==null||!items.TryGetValue(id,out var item)){message="That item is not available.";return false;}
   if(item.excludeFromTrade){message="This item is not tradeable.";return false;}
   if(count<1){message="Choose at least one item to sell.";return false;}
   if(Quantity(id)<count){message=Quantity(id)<1?$"You have no {item.name} to sell.":$"You carry only {Quantity(id)} {item.name}.";return false;}
   long total=(long)item.sellPrice*count;
   if(total>int.MaxValue||Sales==int.MaxValue||!TryApply(new[]{new KeyValuePair<string,int>(id,-count)},(int)total,out _)){message="This trade cannot be completed.";return false;}
   Sales++;
   message=count==1?$"Sold {item.name} for {total} credit{(total==1?"":"s")}.":$"Sold {count} × {item.name} for {total} credits.";return true;
  }
  /// Save-game restore: replaces balances in one step. Unknown IDs are ignored; quantities are clamped to caps.
  public void Restore(int credits,int purchases,int sales,IEnumerable<KeyValuePair<string,int>> carried)
  {
   Credits=Math.Max(0,credits);Purchases=Math.Max(0,purchases);Sales=Math.Max(0,sales);
   foreach(var id in quantities.Keys.ToList())quantities[id]=0;
   if(carried!=null)foreach(var pair in carried)
   {
    if(pair.Key==null||!items.TryGetValue(pair.Key,out var item))continue;
    int q=Math.Max(0,pair.Value);if(item.maxStack>0)q=Math.Min(q,item.maxStack);
    quantities[pair.Key]=q;
   }
  }
  public IEnumerable<KeyValuePair<string,int>> Carried=>quantities.Where(x=>x.Value>0);
 }
}
