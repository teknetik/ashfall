using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// <summary>Only facts recorded in the catalog and current shop balance are shown.</summary>
 public static class InventoryView
 {
  /// Field-pack filter: a catalog tag selects the items (null tag = everything carried).
  public sealed class Category
  {
   public readonly string id,label,tag;
   public Category(string id,string label,string tag){this.id=id;this.label=label;this.tag=tag;}
   public bool Contains(ItemSpec item)=>item!=null&&(tag==null||item.HasTag(tag));
  }
  /// Pack filters, in chip order. Tags come from CityCatalog; an item appears under every tag it carries.
  public static readonly Category[] Categories=
  {
   new Category("all","All",null),
   new Category("supplies","Supplies","consumable"),
   new Category("salvage","Salvage","salvage"),
   new Category("refined","Refined","refined"),
   new Category("mods","Mods","weapon_mod"),
  };
  public static Category FindCategory(string id)=>Categories.FirstOrDefault(c=>c.id==id)??Categories[0];

  public static IEnumerable<ItemSpec> Items(IEnumerable<ItemSpec> catalog,ShopModel shop)=>catalog.Where(item=>item!=null&&shop.Quantity(item.id)>0);
  /// Carried items in one category whose name contains the search text (case-insensitive; blank matches all).
  public static IEnumerable<ItemSpec> Items(IEnumerable<ItemSpec> catalog,ShopModel shop,Category category,string search)=>Items(catalog,shop).Where(item=>(category??Categories[0]).Contains(item)&&Matches(item.name,search));
  public static bool Matches(string name,string search)=>string.IsNullOrWhiteSpace(search)||(name??"").IndexOf(search.Trim(),StringComparison.OrdinalIgnoreCase)>=0;

  static string Description(ItemSpec item)=>string.IsNullOrWhiteSpace(item?.description)?"No description recorded.":item.description;

  public static string Overview(ItemSpec item,int quantity)=>$"{item.name} · {quantity} carried\n{Description(item)}";

  public static string Details(ItemSpec item,int quantity)
  {
   // Details must not invent attributes; show only catalog facts and explicit list prices.
   return $"{Description(item)}\n\n{quantity} carried\nBasic General list price · Buy {item.buyPrice} cr / Sell {item.sellPrice} cr";
  }
 }
}
