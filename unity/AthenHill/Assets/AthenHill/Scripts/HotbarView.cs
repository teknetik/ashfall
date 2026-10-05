using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// userData on a field pack HOTBAR strip cell: the drop target for a dragged pack item.
 public sealed class HotbarDrop {public int slot;}
 /// The HUD hotbar (5 Oct 2026): ten slots on keys 1–9 and 0. Slot 1 shows the primary weapon and 2 the sidearm
 /// (highlighted while drawn); 3–0 show the item assigned from the field pack with its carried count (dimmed at 0).
 /// The same cells are drawn in the field pack's HOTBAR strip, where items are dropped onto them.
 public sealed class HotbarView
 {
  readonly GameSession session;
  readonly Func<PlayerCombat> combat;
  readonly List<Button> slots=new List<Button>();
  readonly string[] signatures=new string[HotbarModel.Slots+1];
  public HotbarView(VisualElement root,GameSession session,Func<PlayerCombat> combat)
  {
   this.session=session;this.combat=combat;
   for(int i=1;i<=HotbarModel.Slots;i++)
   {
    var b=root.Q<Button>("slot"+i);slots.Add(b);
    if(b==null)continue;
    int slot=i;b.clicked+=()=>session.UseHotbar(slot);
    b.SetEnabled(true);
   }
  }
  public void Refresh()
  {
   var c=combat();
   for(int i=1;i<=HotbarModel.Slots;i++)
   {
    var b=slots[i-1];if(b==null)continue;
    Describe(session,c,i,out var icon,out var label,out var tooltip,out var count,out var empty);
    string sig=icon+"|"+label+"|"+empty;
    if(signatures[i]!=sig){signatures[i]=sig;Fill(b,i,icon,label,empty);}
    if(b.tooltip!=tooltip)b.tooltip=tooltip;
    var badge=b.Q<Label>(className:"slot-count");
    if(count>=0)
    {
     if(badge==null){badge=new Label{pickingMode=PickingMode.Ignore};badge.AddToClassList("slot-count");b.Add(badge);}
     string text=count.ToString();if(badge.text!=text)badge.text=text;
     badge.EnableInClassList("slot-count-empty",count<=0);b.EnableInClassList("slot-depleted",count<=0);
    }
    else{badge?.RemoveFromHierarchy();b.EnableInClassList("slot-depleted",false);}
    bool selected=c&&c.Armed&&HotbarModel.WeaponSlot(i)==c.ActiveSlot;
    b.EnableInClassList("selected",selected);
   }
  }
  /// What a slot shows: the weapon equipped in its loadout slot (1, 2) or the assigned item (3–0). count is −1 for weapons.
  public static void Describe(GameSession session,PlayerCombat combat,int slot,out string icon,out string label,out string tooltip,out int count,out bool empty)
  {
   string key=HotbarModel.Key(slot);icon=null;label=null;count=-1;empty=true;
   var weapon=HotbarModel.WeaponSlot(slot);
   if(weapon!=null)
   {
    var id=session.Character?.Equipped(weapon);var spec=session.Shop?.Spec(id);
    string role=weapon=="primary"?"primary weapon":"sidearm";
    if(spec==null){tooltip=$"No {role} equipped · {key}";label=weapon=="primary"?"Primary":"Sidearm";return;}
    empty=false;icon=spec.icon=="rifle-icon"?"rifle-slot-icon":string.IsNullOrEmpty(spec.icon)?"pack-icon":spec.icon;
    // weapons read by their kind: "Field Rifle" → Rifle, "Scrap Pistol" → Pistol
    var words=(spec.name??spec.id).Split(' ');label=words[words.Length-1];
    tooltip=combat&&!combat.hasPistol?$"{spec.name} · {key} · complete the field primer to draw it":$"Draw or holster the {spec.name.ToLowerInvariant()} · {key}";
    return;
   }
   var item=session.Quickbar?.Item(slot);var s=session.Shop?.Spec(item);
   if(s==null){tooltip=$"Empty · {key} · drag a medkit or nano recharge here in the field pack (Tab)";return;}
   empty=false;icon=string.IsNullOrEmpty(s.icon)?"pack-icon":s.icon;label=ShortName(session,s);count=session.Shop.Quantity(item);
   tooltip=$"Use {s.name} · {key} · {count} carried";
  }
  /// The hotbar label: the consumable's hotbarLabel, else the item name's first word.
  public static string ShortName(GameSession session,ItemSpec spec)
  {
   var c=session.catalog?.Consumable(spec.id);
   if(c!=null&&!string.IsNullOrEmpty(c.hotbarLabel))return c.hotbarLabel;
   var name=spec.name??spec.id;int space=name.IndexOf(' ');
   return space>0?name.Substring(0,space):name;
  }
  /// Rebuilds a slot's contents: keycap, illustration (or the empty marker), label.
  public static void Fill(VisualElement b,int slot,string icon,string label,bool empty)
  {
   b.Clear();
   var key=new Label(HotbarModel.Key(slot)){pickingMode=PickingMode.Ignore};key.AddToClassList("keycap");b.Add(key);
   b.EnableInClassList("empty-slot",empty&&icon==null);
   b.EnableInClassList("weapon-slot",HotbarModel.IsWeaponSlot(slot));
   if(icon!=null){var art=new VisualElement{pickingMode=PickingMode.Ignore};art.AddToClassList("item-art");art.AddToClassList(icon);b.Add(art);}
   else{var marker=new Label("–"){pickingMode=PickingMode.Ignore};marker.AddToClassList("empty-slot-marker");b.Add(marker);}
   if(!string.IsNullOrEmpty(label)){var l=new Label(label){pickingMode=PickingMode.Ignore};l.AddToClassList("slot-label");b.Add(l);}
  }
 }
}
