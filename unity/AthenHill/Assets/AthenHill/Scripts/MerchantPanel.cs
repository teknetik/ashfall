using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// Catalog-backed stock selection shared by the counter and its tests. No invented stock or discounts.
 public static class MerchantStock
 {
  public static bool UsesPartsPrice(ItemSpec item,ShopProfile profile)=>profile.parts&&ShopModel.SellsAsPart(item);
  public static bool CanBuy(ItemSpec item,ShopProfile profile)=>item!=null&&!item.excludeFromTrade&&
   (UsesPartsPrice(item,profile)||profile.supplies&&!item.sellOnly&&item.buyPrice>0);
  public static bool CanSell(ItemSpec item,ShopProfile profile)=>item!=null&&!item.excludeFromTrade&&item.sellPrice>0&&
   (profile.supplies||profile.salvage&&ShopModel.BuysAsSalvage(item));
  public static int Price(ItemSpec item,ShopProfile profile,bool selling)=>selling?item.sellPrice:UsesPartsPrice(item,profile)?item.partsPrice:item.buyPrice;
  public static string Category(ItemSpec item)
  {
   if(item.HasTag("augmentation")||item.HasTag("armour_mod")||item.HasTag("mod")||item.HasTag("weapon_mod"))return "Mods";
   if(item.HasTag("implant"))return "Implants";
   if(item.HasTag("armour")||item.HasTag("equipment")||item.HasTag("weapon")||item.HasTag("backpack"))return "Equipment";
   if(item.HasTag("consumable"))return "Supplies";
   return "Parts";
  }
  public static IEnumerable<ItemSpec> Items(CityCatalog catalog,ShopModel pack,ShopProfile profile,bool selling,string search="",string category="All")
   =>catalog.items.Where(i=>selling?CanSell(i,profile)&&pack.Quantity(i.id)>0:CanBuy(i,profile))
    .Where(i=>category=="All"||Category(i)==category).Where(i=>string.IsNullOrWhiteSpace(search)||
      i.name.IndexOf(search.Trim(),StringComparison.OrdinalIgnoreCase)>=0||i.description?.IndexOf(search.Trim(),StringComparison.OrdinalIgnoreCase)>=0);
 }
 /// Dense scrollable stock on the left, a stable item inspector on the right. Trading still uses GameSession's atomic verbs.
 public sealed class MerchantPanel
 {
  readonly GameSession session;
  readonly CraftingSession crafting;
  readonly VisualElement root,list,detail,art,facts,effects,filters;
  readonly ScrollView scroll;
  readonly Label balance,count,name,rarity,description,empty,price,balanceAfter,reason,capacity;
  readonly Button buyTab,sellTab,trade,sellAll;
  readonly TextField search;
  readonly Dictionary<string,Button> rows=new Dictionary<string,Button>();
  readonly Dictionary<string,Button> chips=new Dictionary<string,Button>();
  string selected,category="All",query="",signature,profileKey;
  bool selling;
  public string SelectedItemId=>selected;
  public bool Selling=>selling;
  public MerchantPanel(VisualElement hud,GameSession session,CraftingSession crafting)
  {
   this.session=session;this.crafting=crafting;root=hud.Q("shop-panel");root.Clear();root.AddToClassList("merchant");
   var toolbar=Element(root,"merchant-toolbar","merchant-toolbar");
   buyTab=Button(toolbar,"merchant-tab-buy","BUY",()=>SetMode(false),"merchant-tab");
   sellTab=Button(toolbar,"merchant-tab-sell","SELL",()=>SetMode(true),"merchant-tab");
   balance=Label(toolbar,"merchant-balance","","merchant-balance");
   var columns=Element(root,"merchant-columns","merchant-columns");
   var browser=Element(columns,"merchant-browser","merchant-browser");
   search=new TextField{name="merchant-search",tooltip="Search the merchant's items"};search.AddToClassList("merchant-search");search.label="Search";browser.Add(search);
   search.RegisterValueChangedCallback(e=>{query=e.newValue??"";signature=null;Refresh();});
   filters=Element(browser,"merchant-filters","merchant-filters");
   foreach(var title in new[]{"All","Supplies","Parts","Equipment","Implants","Mods"})
   {string c=title;chips[c]=Button(filters,"merchant-filter-"+c.ToLowerInvariant(),c,()=>{category=c;signature=null;Refresh();},"merchant-chip");}
   scroll=new ScrollView(ScrollViewMode.Vertical){name="merchant-scroll",horizontalScrollerVisibility=ScrollerVisibility.Hidden};scroll.AddToClassList("merchant-scroll");browser.Add(scroll);list=scroll.contentContainer;
   empty=Label(browser,"merchant-empty","","merchant-empty");count=Label(browser,"merchant-count","","merchant-count");UiNavigation.KeepFocusVisible(scroll);
   scroll.RegisterCallback<NavigationMoveEvent>(Navigate,TrickleDown.TrickleDown);
   detail=Element(columns,"merchant-detail","merchant-detail");
   var detailScroll=new ScrollView(ScrollViewMode.Vertical){name="merchant-detail-scroll",horizontalScrollerVisibility=ScrollerVisibility.Hidden};detailScroll.AddToClassList("merchant-detail-scroll");detail.Add(detailScroll);UiNavigation.KeepFocusVisible(detailScroll);
   rarity=Label(detailScroll,"merchant-rarity","","merchant-rarity");name=Label(detailScroll,"merchant-name","","merchant-title");
   art=Element(detailScroll,"merchant-art","merchant-art");description=Label(detailScroll,"merchant-description","","merchant-description");
   facts=Element(detailScroll,"merchant-facts","merchant-facts");effects=Element(detailScroll,"merchant-effects","merchant-effects");
   var checkout=Element(detail,"merchant-checkout","merchant-checkout");price=Label(checkout,"merchant-price","","merchant-price");
   balanceAfter=Label(checkout,"merchant-after","","merchant-after");
   var actions=Element(checkout,"merchant-actions","merchant-actions");trade=Button(actions,"merchant-trade","Buy one",Trade,"merchant-primary");
   sellAll=Button(actions,"merchant-sell-all","Sell stack",SellStack,"merchant-secondary");
   reason=Label(checkout,"merchant-reason","","merchant-reason");capacity=Label(root,"merchant-capacity","","merchant-capacity");
  }
  public void Opened(){Refresh();root.schedule.Execute(()=>{if(selected!=null&&rows.TryGetValue(selected,out var row))row.Focus();else search.Focus();});}
  public void SetMode(bool sell){selling=sell;signature=null;Refresh();}
  public void Select(string id){if(!rows.ContainsKey(id))return;selected=id;UpdateDetail();foreach(var p in rows){p.Value.EnableInClassList("selected",p.Key==id);p.Value.tabIndex=p.Key==id?0:-1;}}
  public void Refresh()
  {
   if(session.Shop==null||session.catalog==null)return;
   var shop=session.ActiveShop;string key=session.Vendor+"|"+shop.title;
   if(profileKey!=key){profileKey=key;selling=false;category="All";query="";search.SetValueWithoutNotify("");signature=null;}
   buyTab.EnableInClassList("active",!selling);sellTab.EnableInClassList("active",selling);balance.text=$"{session.Shop.Credits:N0} cr";
   var available=MerchantStock.Items(session.catalog,session.Shop,shop,selling,query,category).ToList();
   var all=MerchantStock.Items(session.catalog,session.Shop,shop,selling).ToList();
   foreach(var pair in chips){pair.Value.EnableInClassList("active",pair.Key==category);pair.Value.SetEnabled(pair.Key=="All"||all.Any(i=>MerchantStock.Category(i)==pair.Key));}
   if(!available.Any(i=>i.id==selected))selected=available.FirstOrDefault()?.id;
   string next=profileKey+"|"+selling+"|"+category+"|"+query+"|"+string.Join(";",available.Select(i=>i.id+":"+session.Shop.Quantity(i.id)));
   if(next!=signature)
   {
    signature=next;string focused=(root.focusController?.focusedElement as VisualElement)?.name;rows.Clear();list.Clear();
    foreach(var item in available)
    {
     string id=item.id;var row=new Button(()=>Select(id)){name="merchant-item-"+id,tooltip=item.name};row.AddToClassList("merchant-row");
     var icon=Element(row,null,"merchant-row-icon");icon.AddToClassList(string.IsNullOrEmpty(item.icon)?"pack-icon":item.icon);icon.pickingMode=PickingMode.Ignore;
     var copy=Element(row,null,"merchant-row-copy");copy.pickingMode=PickingMode.Ignore;Label(copy,null,item.name,"merchant-row-name");
     Label(copy,null,$"{MerchantStock.Category(item)} · {item.rarity} · {session.Shop.Quantity(id)} carried","merchant-row-meta");
     Label(row,null,$"{MerchantStock.Price(item,shop,selling):N0} cr","merchant-row-price");
     row.RegisterCallback<FocusInEvent>(_=>Select(id));list.Add(row);rows[id]=row;
    }
    if(focused!=null&&focused.StartsWith("merchant-item-",StringComparison.Ordinal))root.schedule.Execute(()=>{if(rows.TryGetValue(focused.Substring(14),out var row))row.Focus();else if(selected!=null)rows[selected].Focus();else search.Focus();});
   }
   foreach(var pair in rows){pair.Value.EnableInClassList("selected",pair.Key==selected);pair.Value.tabIndex=pair.Key==selected?0:-1;}
   empty.style.display=available.Count==0?DisplayStyle.Flex:DisplayStyle.None;
   empty.text=selling?"No matching items to sell. Try another category or clear the search.":"No matching stock. Try another category or clear the search.";
   count.text=$"{available.Count} of {all.Count} {(selling?"carried items":"items available")}";
   var c=session.Character;capacity.text=c==null?$"Pack · {session.Shop.PackWeightKg:0.0} kg":$"PACK  {c.PackSlotsUsed} / {c.PackSlotCapacity} slots     CARRIED  {c.CarriedWeightKg:0.0} / {c.CarryCapacityKg:0.0} kg     Includes equipped gear";
   UpdateDetail();
  }
  void UpdateDetail()
  {
   var item=session.Shop.Spec(selected);detail.style.display=item==null?DisplayStyle.None:DisplayStyle.Flex;if(item==null)return;
   var profile=session.ActiveShop;int cost=MerchantStock.Price(item,profile,selling),quantity=session.Shop.Quantity(item.id);
   name.text=item.name;rarity.text=$"{item.rarity.ToString().ToUpperInvariant()}  /  {MerchantStock.Category(item).ToUpperInvariant()}";
   foreach(var cls in art.GetClasses().ToList())if(cls!="merchant-art")art.RemoveFromClassList(cls);art.AddToClassList(string.IsNullOrEmpty(item.icon)?"pack-icon":item.icon);
   description.text=item.description;facts.Clear();effects.Clear();
   Fact("Unit weight",$"{item.weightKg:0.##} kg");Fact("Carried",quantity.ToString());Fact("Stack limit",item.maxStack>0?item.maxStack.ToString():"No item limit");
   Fact("Buy price",MerchantStock.CanBuy(item,profile)?$"{MerchantStock.Price(item,profile,false):N0} cr":"Not stocked");Fact("Sell value",MerchantStock.CanSell(item,profile)?$"{item.sellPrice:N0} cr":"Not purchased here");
   var equipment=session.Character?.Equipment(item.id);var modification=session.Character?.Modification(item.id);
   if(equipment!=null)
   {
    Heading("EQUIPMENT");Effect("Fits "+string.Join(", ",equipment.slots.Select(s=>session.Character.Data.slots.FirstOrDefault(x=>x.id==s)?.label??s)));
    foreach(var modifier in equipment.modifiers??Array.Empty<CharacterModifier>())Effect(Modifier(modifier));
    if((equipment.requirements?.Length??0)>0){Heading("REQUIREMENTS");foreach(var r in equipment.requirements)Effect($"{session.Character.Data.Label(r.stat)} {r.minimum:0.#}  ·  You {session.Character.Stat(r.stat):0.#}");}
    foreach(var slot in equipment.slots??Array.Empty<string>())
    {
     string current=session.Character.Equipped(slot);if(current==null||current==item.id)continue;
     var existing=session.Character.Equipment(current);Heading("COMPARE · "+(session.Shop.Spec(current)?.name??current));
     foreach(var m in equipment.modifiers??Array.Empty<CharacterModifier>())
     {var old=existing?.modifiers?.FirstOrDefault(x=>x.stat==m.stat);Effect($"{session.Character.Data.Label(m.stat)}: {m.flat:+0.##;-0.##;0} ({m.flat-(old?.flat??0):+0.##;-0.##;0}) · {m.percent*100:+0.#;-0.#;0}%");}
     break;
    }
   }
   if(modification!=null){Heading("MODIFICATION");foreach(var m in modification.modifiers??Array.Empty<CharacterModifier>())Effect(Modifier(m));}
   var weapon=crafting?.Model?.FindWeapon(item.id);
   if(weapon!=null)
   {
    Heading("BASE WEAPON STATS");var stats=weapon.stats;
    Effect($"Damage  {stats.damage:0.#}     Range  {stats.range:0.#} m");Effect($"Rate  {(stats.fireInterval>0?60/stats.fireInterval:0):0} rounds/min     Recoil  {stats.recoil:0.#}");
   }
   price.text=$"{(selling?"SELL VALUE":"PURCHASE")}   {cost:N0} cr";long after=(long)session.Shop.Credits+(selling?cost:-cost);balanceAfter.text=$"Balance after trade  {after:N0} cr";
   bool valid=session.Shop.CanApply(new[]{new KeyValuePair<string,int>(item.id,selling?-1:1)},selling?cost:-cost,out var failure);
   trade.text=selling?$"Sell one · {cost:N0} cr":$"Buy one · {cost:N0} cr";trade.SetEnabled(valid);
   reason.text=valid?(selling?"Items and credits transfer together.":"One item per purchase. Select equipment in your pack to fit it."):FriendlyReason(failure);
   reason.EnableInClassList("rejected",!valid);
   sellAll.style.display=selling&&ShopModel.BuysAsSalvage(item)?DisplayStyle.Flex:DisplayStyle.None;
   sellAll.text=$"Sell {quantity} · {(long)quantity*item.sellPrice:N0} cr";
   bool stackOk=quantity>0&&(long)quantity*item.sellPrice<=int.MaxValue&&session.Shop.CanApply(new[]{new KeyValuePair<string,int>(item.id,-quantity)},quantity*item.sellPrice,out _);sellAll.SetEnabled(stackOk);
  }
  string Modifier(CharacterModifier m)=>session.Character.Data.Label(m.stat)+"  "+(m.flat!=0?$"{m.flat:+0.##;-0.##;0}":"")+(m.percent!=0?$" {m.percent*100:+0.#;-0.#;0}%":"");
  void Heading(string text)=>Label(effects,null,text,"merchant-stats-heading");
  void Effect(string text)=>Label(effects,null,text,"merchant-effect");
  void Fact(string label,string value){var row=Element(facts,null,"merchant-fact");Label(row,null,label,"merchant-fact-label");Label(row,null,value,"merchant-fact-value");}
  static string FriendlyReason(string reason)=>reason switch{"insufficient_credits"=>"Not enough credits for this item.","stack_full"=>"This item stack is full.","insufficient_items"=>"You no longer carry this item.","overflow"=>"This trade exceeds the inventory limit.",_=>reason??"This trade cannot be completed."};
  void Trade()
  {
   if(selected==null)return;var item=session.Shop.Spec(selected);if(item==null)return;
   if(selling){if(ShopModel.BuysAsSalvage(item))session.SellSalvage(selected,1);else session.Trade(selected,false);}
   else if(MerchantStock.UsesPartsPrice(item,session.ActiveShop))session.BuyPart(selected);else session.Trade(selected,true);
   Refresh();if(!trade.enabledSelf&&selected!=null&&rows.TryGetValue(selected,out var row))row.Focus();
  }
  void SellStack(){if(selected!=null)session.SellSalvage(selected,session.Shop.Quantity(selected));Refresh();}
  void Navigate(NavigationMoveEvent e)
  {
   if(e.direction!=NavigationMoveEvent.Direction.Up&&e.direction!=NavigationMoveEvent.Direction.Down)return;
   var ids=rows.Keys.ToList();int at=ids.IndexOf(selected),next=UiNavigation.ListStep(at,ids.Count,e.direction==NavigationMoveEvent.Direction.Down?1:-1);
   if(next>=0){rows[ids[next]].Focus();Select(ids[next]);}UiNavigation.Consume(e,root);
  }
  static VisualElement Element(VisualElement parent,string name,string cls){var e=new VisualElement{name=name};e.AddToClassList(cls);parent.Add(e);return e;}
  static Label Label(VisualElement parent,string name,string text,string cls){var l=new Label(text){name=name,pickingMode=PickingMode.Ignore};l.AddToClassList(cls);parent.Add(l);return l;}
  static Button Button(VisualElement parent,string name,string text,Action action,string cls){var b=new Button(action){name=name,text=text};b.AddToClassList(cls);parent.Add(b);return b;}
 }
}
