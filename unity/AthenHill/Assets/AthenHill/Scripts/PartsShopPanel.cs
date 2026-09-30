using System.Collections.Generic;
using System.Linq;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// Basic General's "Buy parts" list: the common and uncommon crafting parts Mira stocks at a premium
 /// (CityCatalog partsPrice; ShopModel.SellsAsPart), so credits can shortcut a grind. Rare parts stay loot-only.
 /// Rows are built once in catalog order and update in place, so keyboard focus survives a purchase.
 public sealed class PartsShopPanel
 {
  readonly GameSession session;
  readonly VisualElement list;
  readonly Dictionary<string,(Label copy,Button buy)> rows=new Dictionary<string,(Label,Button)>();
  public PartsShopPanel(VisualElement root,GameSession session){this.session=session;list=root.Q("parts-list");}
  /// Parts Mira stocks, in catalog order.
  public static IEnumerable<ItemSpec> Stocked(IEnumerable<ItemSpec> catalog)=>catalog.Where(ShopModel.SellsAsPart);
  static string Rarity(ItemRarity r)=>r==ItemRarity.Uncommon?"Uncommon":"Common";
  public void Refresh()
  {
   if(list==null||session.Shop==null)return;
   var shop=session.Shop;
   if(rows.Count==0)foreach(var item in Stocked(session.catalog.items))
   {
    var id=item.id;
    var row=new VisualElement{name="part-"+id};row.AddToClassList("trade-row");row.AddToClassList("part-row");
    var art=new VisualElement{pickingMode=PickingMode.Ignore};art.AddToClassList("trade-art");art.AddToClassList("part-art");art.AddToClassList(string.IsNullOrEmpty(item.icon)?"pack-icon":item.icon);row.Add(art);
    var copy=new Label{pickingMode=PickingMode.Ignore};copy.AddToClassList("item-copy");row.Add(copy);
    var buy=new Button(()=>session.BuyPart(id)){name="buy-part-"+id};row.Add(buy);
    list.Add(row);rows[id]=(copy,buy);
   }
   foreach(var item in Stocked(session.catalog.items))
   {
    if(!rows.TryGetValue(item.id,out var row))continue;
    int q=shop.Quantity(item.id);
    row.copy.text=$"{item.name} · {q} carried\n{Rarity(item.rarity)} part"+(ShopModel.BuysAsSalvage(item)?$" · Mira pays {item.sellPrice} cr":"");
    row.copy.EnableInClassList("rarity-uncommon",item.rarity==ItemRarity.Uncommon);
    row.buy.text=$"Buy · {item.partsPrice} cr";
    bool room=shop.Room(item.id)>0;
    row.buy.SetEnabled(shop.Credits>=item.partsPrice&&room);
    row.buy.tooltip=!room?$"Your pack holds no more {item.name}.":shop.Credits<item.partsPrice?$"You need {item.partsPrice-shop.Credits} more credits.":$"Buy one {item.name} for {item.partsPrice} credits";
   }
  }
 }
}
