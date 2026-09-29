using System.Collections.Generic;
using System.Linq;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// Basic General's "Sell salvage" list: every carried item Mira buys but does not stock (CityCatalog sellOnly),
 /// one row each with Sell 1 and Sell all, both through the atomic ShopModel sale. Rows update in place so
 /// keyboard focus survives a sale; a row that empties hands focus to its neighbour.
 public sealed class SalvageSalePanel
 {
  readonly GameSession session;
  readonly VisualElement list;
  readonly Label empty;
  readonly Button fallbackFocus;
  readonly Dictionary<string,(VisualElement row,Label copy,Button one,Button all)> rows=new Dictionary<string,(VisualElement,Label,Button,Button)>();
  public SalvageSalePanel(VisualElement root,GameSession session)
  {
   this.session=session;list=root.Q("salvage-list");empty=root.Q<Label>("salvage-empty");fallbackFocus=root.Q<Button>("sell2");
  }
  /// Salvage the player can sell right now, in catalog order.
  public static IEnumerable<ItemSpec> Sellable(IEnumerable<ItemSpec> catalog,ShopModel shop)=>catalog.Where(x=>ShopModel.BuysAsSalvage(x)&&shop.Quantity(x.id)>0);
  static string Rarity(ItemRarity r)=>r==ItemRarity.Rare?"Rare":r==ItemRarity.Uncommon?"Uncommon":"Common";
  public void Refresh()
  {
   if(list==null||session.Shop==null)return;
   var shop=session.Shop;var items=Sellable(session.catalog.items,shop).ToList();
   var focused=list.panel?.focusController?.focusedElement as VisualElement;
   string focusedId=null;int focusedIndex=-1;
   foreach(var pair in rows)if(focused!=null&&(focused==pair.Value.one||focused==pair.Value.all)){focusedId=pair.Key;focusedIndex=list.IndexOf(pair.Value.row);}
   foreach(var id in rows.Keys.ToList())if(!items.Any(x=>x.id==id)){rows[id].row.RemoveFromHierarchy();rows.Remove(id);}
   int index=0;
   foreach(var item in items)
   {
    if(!rows.TryGetValue(item.id,out var row))
    {
     var id=item.id;
     var element=new VisualElement{name="salvage-"+id};element.AddToClassList("trade-row");element.AddToClassList("salvage-row");
     var art=new VisualElement{pickingMode=PickingMode.Ignore};art.AddToClassList("trade-art");art.AddToClassList("salvage-art");art.AddToClassList(string.IsNullOrEmpty(item.icon)?"pack-icon":item.icon);element.Add(art);
     var copy=new Label{pickingMode=PickingMode.Ignore};copy.AddToClassList("item-copy");element.Add(copy);
     var one=new Button(()=>session.SellSalvage(id,1)){name="sell-salvage-"+id};element.Add(one);
     var all=new Button(()=>session.SellSalvage(id,session.Shop.Quantity(id))){name="sell-all-"+id};element.Add(all);
     row=(element,copy,one,all);rows[id]=row;
    }
    if(list.IndexOf(row.row)!=index)list.Insert(index,row.row);
    int q=shop.Quantity(item.id);
    row.copy.text=$"{item.name} · {q} carried\n{Rarity(item.rarity)} salvage · {item.sellPrice} cr each";
    row.copy.EnableInClassList("rarity-uncommon",item.rarity==ItemRarity.Uncommon);
    row.one.text=$"Sell 1 · {item.sellPrice} cr";row.all.text=$"Sell all · {(long)item.sellPrice*q} cr";
    row.all.tooltip=$"Sell all {q} {item.name} in one trade";
    index++;
   }
   if(empty!=null)
   {
    empty.style.display=items.Count==0?DisplayStyle.Flex:DisplayStyle.None;
    empty.text="Mira buys "+string.Join(", ",session.catalog.items.Where(ShopModel.BuysAsSalvage).Select(x=>x.name))+". You are carrying none of it.";
   }
   // The focused row was sold out: keep keyboard focus in the list.
   if(focusedId!=null&&!rows.ContainsKey(focusedId))
   {
    var next=list.Children().Where(c=>rows.Values.Any(r=>r.row==c)).ElementAtOrDefault(System.Math.Min(focusedIndex,rows.Count-1));
    var target=next!=null?rows.Values.First(r=>r.row==next).one:null;
    target??=fallbackFocus;
    if(target!=null)target.schedule.Execute(target.Focus);
   }
  }
 }
}
