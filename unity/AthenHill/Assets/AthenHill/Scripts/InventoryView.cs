using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// <summary>Only facts recorded in the catalog and current shop balance are shown.</summary>
 public static class InventoryView
 {
  public static IEnumerable<ItemSpec> Items(IEnumerable<ItemSpec> catalog,ShopModel shop)=>catalog.Where(item=>item!=null&&shop.Quantity(item.id)>0);

  static string Description(ItemSpec item)=>string.IsNullOrWhiteSpace(item?.description)?"No description recorded.":item.description;

  public static string Overview(ItemSpec item,int quantity)=>$"{item.name} · {quantity} carried\n{Description(item)}";

  public static string Details(ItemSpec item,int quantity)
  {
   // Details must not invent attributes; show only catalog facts and explicit list prices.
   return $"{Description(item)}\n\n{quantity} carried\nBasic General list price · Buy {item.buyPrice} cr / Sell {item.sellPrice} cr";
  }
 }
}