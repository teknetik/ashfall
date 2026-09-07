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
   items=definitions.ToDictionary(x=>x.id,x=>new ItemSpec{id=x.id,name=x.name,description=x.description,buyPrice=x.buyPrice,sellPrice=x.sellPrice,startingQuantity=x.startingQuantity});
   if(items.Values.Any(x=>x.buyPrice<0||x.sellPrice<0||x.startingQuantity<0))throw new ArgumentException("Prices and quantities must be nonnegative.");
   quantities=items.ToDictionary(x=>x.Key,x=>x.Value.startingQuantity);Credits=credits;
  }
  public int Quantity(string id)=>id!=null&&quantities.TryGetValue(id,out int q)?q:0;
  public bool Trade(string id,bool buy,out string message)
  {
   if(id==null||!items.TryGetValue(id,out var item)){message="That item is not available.";return false;}
   int price=buy?item.buyPrice:item.sellPrice;
   if(buy&&Credits<price){message=$"You need {price-Credits} more credits for {item.name}.";return false;}
   if(!buy&&Quantity(id)<1){message=$"You have no {item.name} to sell.";return false;}
   try
   {
    int credits=checked(Credits+(buy?-price:price));int quantity=checked(Quantity(id)+(buy?1:-1));int count=checked((buy?Purchases:Sales)+1);
    Credits=credits;quantities[id]=quantity;if(buy)Purchases=count;else Sales=count;
   }
   catch(OverflowException){message="This trade cannot be completed.";return false;}
   message=$"{(buy?"Bought":"Sold")} {item.name} for {price} credit{(price==1?"":"s")}.";return true;
  }
 }
}
