using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// The home locker window (5 Oct 2026): the field pack on the left, the locker on the right. Select a stack and Store or
 /// Take one or all of it (double-click or Shift+Enter moves the whole stack, Enter one); Store all salvage moves every
 /// crafting part and piece of salvage into the locker and keeps medkits, nano recharges, gear and tools in the pack.
 public sealed class StashPanel
 {
  readonly VisualElement panel,packGrid,lockerGrid;
  readonly Label packHeading,lockerHeading,selection;
  readonly Button storeOne,storeAll,takeOne,takeAll,storeSalvage;
  readonly GameSession session;
  readonly CraftingSession crafting;
  string selectedId;bool selectedInLocker;string signature;
  public string SelectedId=>selectedId;
  public bool SelectedInLocker=>selectedInLocker;
  public StashPanel(VisualElement panel,GameSession session,CraftingSession crafting)
  {
   this.panel=panel;this.session=session;this.crafting=crafting;
   var columns=new VisualElement{name="stash-columns"};columns.AddToClassList("stash-columns");panel.Add(columns);
   VisualElement Column(string name,out Label heading,out VisualElement grid)
   {
    var col=new VisualElement{name=name};col.AddToClassList("stash-col");columns.Add(col);
    heading=new Label{name=name+"-heading"};heading.AddToClassList("stash-heading");col.Add(heading);
    grid=new VisualElement{name=name+"-grid"};grid.AddToClassList("stash-grid");col.Add(grid);
    return col;
   }
   Column("stash-pack",out packHeading,out packGrid);
   Column("stash-locker",out lockerHeading,out lockerGrid);
   selection=new Label{name="stash-selection"};selection.AddToClassList("stash-selection");panel.Add(selection);
   var actions=new VisualElement{name="stash-actions"};actions.AddToClassList("stash-actions");panel.Add(actions);
   Button Action(string name,string text,Action a){var b=new Button(a){name=name,text=text};b.AddToClassList("stash-action");actions.Add(b);return b;}
   storeOne=Action("stash-store-one","Store 1",()=>Move(false,true));
   storeAll=Action("stash-store-all","Store all",()=>Move(true,true));
   takeOne=Action("stash-take-one","Take 1",()=>Move(false,false));
   takeAll=Action("stash-take-all","Take all",()=>Move(true,false));
   storeSalvage=Action("stash-store-salvage","Store all salvage",StoreAllSalvage);storeSalvage.AddToClassList("primary-setting-action");
  }
  public void Opened()
  {
   signature=null;
   if(selectedId==null||!(selectedInLocker?session.Stash.Quantity(selectedId)>0:session.Shop.Quantity(selectedId)>0)){selectedId=null;}
   Refresh();
   panel.schedule.Execute(()=>{var b=Tile(selectedId,selectedInLocker)??packGrid.Q<Button>()??lockerGrid.Q<Button>();if(b!=null)b.Focus();else storeSalvage.Focus();});
  }
  Button Tile(string id,bool locker)=>id==null?null:(locker?lockerGrid:packGrid).Q<Button>((locker?"stash-locker-":"stash-pack-")+id);
  public void Select(string id,bool locker){selectedId=id;selectedInLocker=locker;Refresh();}
  /// Moves the selected stack (one or all of it) between the pack and the locker.
  public void Move(bool all,bool store)
  {
   if(selectedId==null||selectedInLocker==store)return;
   string id=selectedId;
   int count=all?(store?session.Shop.Quantity(id):session.Stash.TakeableCount(session.Shop,id)):1;
   if(!store&&all&&count<1)count=1; // let the pack's refusal explain why nothing fits
   session.MoveStash(id,count,store);
   // keep the selection on whatever is left of the stack, else on the other side where it went
   if((store?session.Shop.Quantity(id):session.Stash.Quantity(id))<=0)selectedInLocker=store;
   Refresh();
   panel.schedule.Execute(()=>Tile(selectedId,selectedInLocker)?.Focus());
  }
  /// Crafting parts and salvage: anything a schematic takes (by id or tag) or a trader buys as salvage, but never
  /// consumables, wearable gear or the tools schematics need.
  public static bool IsSalvage(GameSession session,CraftingModel model,ItemSpec item)
  {
   if(item==null||session.catalog.Consumable(item.id)!=null||session.Character?.Equipment(item.id)!=null)return false;
   if(model!=null)
   {
    var recipes=model.Data.recipes.Where(r=>r!=null).ToList();
    if(recipes.Any(r=>r.requiredTools!=null&&Array.IndexOf(r.requiredTools,item.id)>=0))return false;
    if(recipes.Any(r=>r.inputs!=null&&r.inputs.Any(i=>i!=null&&(i.kind=="item"?i.id==item.id:item.HasTag(i.id)))))return true;
   }
   return ShopModel.BuysAsSalvage(item);
  }
  public void StoreAllSalvage()
  {
   var model=crafting?crafting.Model:null;
   var moving=session.Shop.Carried.Where(x=>IsSalvage(session,model,session.Shop.Spec(x.Key))).ToList();
   if(moving.Count==0){session.Notify("No salvage or crafting parts in your pack.","Home locker");return;}
   int kinds=0,units=0;
   foreach(var pair in moving)
   {
    if(!session.Stash.Store(session.Shop,pair.Key,pair.Value,out var reason)){if(reason=="locker_full")break;continue;}
    kinds++;units+=pair.Value;
   }
   if(kinds>0)session.SetFlag(WardHome.StoredFlag);
   session.Notify(kinds==0?$"The locker is full ({session.Stash.SlotCapacity} stacks).":$"Stored {units} items of salvage ({kinds} kinds) in the locker."+(kinds<moving.Count?" The locker filled up before the rest.":""),"Home locker");
   session.NotifyHomeChanged();
   Refresh();
  }
  public void Refresh()
  {
   var shop=session.Shop;var stash=session.Stash;var character=session.Character;
   var carried=shop.Carried.OrderBy(x=>shop.Spec(x.Key)?.name,StringComparer.Ordinal).ToList();
   var stored=stash.Stored.OrderBy(x=>shop.Spec(x.Key)?.name??x.Key,StringComparer.Ordinal).ToList();
   if(selectedId!=null&&!(selectedInLocker?stash.Quantity(selectedId)>0:shop.Quantity(selectedId)>0))selectedId=null;
   if(selectedId==null){var first=carried.Count>0?carried[0].Key:stored.Count>0?stored[0].Key:null;selectedId=first;selectedInLocker=carried.Count==0&&first!=null;}
   string sig=string.Join(";",carried.Select(x=>x.Key+x.Value))+"|"+string.Join(";",stored.Select(x=>x.Key+x.Value));
   if(sig!=signature)
   {
    signature=sig;
    Fill(packGrid,carried,false);Fill(lockerGrid,stored,true);
   }
   foreach(var b in panel.Query<Button>(className:"stash-tile").ToList())b.EnableInClassList("selected",b.name==(selectedInLocker?"stash-locker-":"stash-pack-")+selectedId);
   packHeading.text=character!=null?$"FIELD PACK · {character.PackSlotsUsed} / {character.PackSlotCapacity} slots · {character.CarryWeight:0.0} / {character.CarryCapacity:0.#} kg":$"FIELD PACK · {carried.Count} stacks";
   lockerHeading.text=$"HOME LOCKER · {stash.SlotsUsed} / {stash.SlotCapacity} stacks · {stash.TotalItems} items";
   var spec=shop.Spec(selectedId);
   int here=selectedId==null?0:selectedInLocker?stash.Quantity(selectedId):shop.Quantity(selectedId);
   selection.text=spec==null?"Select a stack in your pack or the locker.":$"{spec.name} · {here} {(selectedInLocker?"in the locker":"in your pack")} · {spec.weightKg:0.##} kg each"+(IsSalvage(session,crafting?crafting.Model:null,spec)?" · salvage":"");
   bool fromPack=spec!=null&&!selectedInLocker,fromLocker=spec!=null&&selectedInLocker;
   storeOne.SetEnabled(fromPack);storeAll.SetEnabled(fromPack);takeOne.SetEnabled(fromLocker);takeAll.SetEnabled(fromLocker);
   storeAll.text=fromPack?$"Store all · {here}":"Store all";takeAll.text=fromLocker?$"Take all · {here}":"Take all";
  }
  void Fill(VisualElement grid,List<KeyValuePair<string,int>> stacks,bool locker)
  {
   grid.Clear();
   foreach(var pair in stacks)
   {
    var spec=session.Shop.Spec(pair.Key);string id=pair.Key;
    var tile=new Button{name=(locker?"stash-locker-":"stash-pack-")+id,tooltip=(spec?.name??id)+" · ×"+pair.Value};
    tile.AddToClassList("inventory-tile");tile.AddToClassList("stash-tile");
    if(spec!=null&&spec.rarity!=ItemRarity.Common)tile.AddToClassList(spec.rarity==ItemRarity.Rare?"tile-rare":"tile-uncommon");
    var icon=new VisualElement{pickingMode=PickingMode.Ignore};icon.AddToClassList("inventory-tile-icon");icon.AddToClassList(string.IsNullOrEmpty(spec?.icon)?"pack-icon":spec.icon);tile.Add(icon);
    var qty=new Label("×"+pair.Value){pickingMode=PickingMode.Ignore};qty.AddToClassList("inventory-tile-qty");tile.Add(qty);
    var name=new Label(spec?.name??id){pickingMode=PickingMode.Ignore};name.AddToClassList("inventory-tile-name");tile.Add(name);
    tile.RegisterCallback<FocusInEvent>(_=>{if(selectedId!=id||selectedInLocker!=locker)Select(id,locker);});
    tile.RegisterCallback<ClickEvent>(e=>{Select(id,locker);if(e.clickCount==2)Move(true,!locker);});
    tile.RegisterCallback<KeyDownEvent>(e=>{if(e.keyCode==KeyCode.Return||e.keyCode==KeyCode.KeypadEnter){Select(id,locker);Move(e.shiftKey,!locker);e.StopPropagation();}});
    grid.Add(tile);
   }
   if(stacks.Count==0){var none=new Label(locker?"The locker is empty.":"Your pack is empty."){pickingMode=PickingMode.Ignore};none.AddToClassList("stash-empty");grid.Add(none);}
  }
 }
}
