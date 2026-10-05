using System;
using System.Collections.Generic;
using System.Linq;
namespace AthenHill
{
 /// One assigned hotbar slot in a save (slot 3–10; 10 is the 0 key).
 [Serializable] public class HotbarEntry {public int slot;public string itemId;}
 /// The ten-slot hotbar (5 Oct 2026, keys 1–9 and 0). Slot 1 draws the primary weapon and 2 the sidearm; slots 3–10
 /// hold usable items the player assigns from the field pack (CityCatalog consumables). An assignment stays when the
 /// last unit is used, so restocking refills the slot. One item sits in at most one slot: assigning it again moves it.
 public sealed class HotbarModel
 {
  public const int Slots=10,FirstItemSlot=3;
  /// A new game (and a save made before the configurable hotbar) starts with a medkit on 3 and a nano cell on 4.
  public static readonly KeyValuePair<int,string>[] Defaults={new KeyValuePair<int,string>(3,"medkit"),new KeyValuePair<int,string>(4,"nano_cell")};
  readonly string[] items=new string[Slots+1];
  readonly Func<string,bool> usable;
  public event Action Changed;
  /// usable: whether an item id may sit on the hotbar (null accepts any non-empty id).
  public HotbarModel(Func<string,bool> usable=null){this.usable=usable;ResetToDefaults();}
  public static bool IsWeaponSlot(int slot)=>slot==1||slot==2;
  public static bool IsItemSlot(int slot)=>slot>=FirstItemSlot&&slot<=Slots;
  /// The key that uses a slot: "1"…"9", and "0" for slot 10.
  public static string Key(int slot)=>slot==Slots?"0":slot.ToString();
  /// The weapon slot a hotbar slot draws ("primary" for 1, "secondary" for 2), else null.
  public static string WeaponSlot(int slot)=>slot==1?"primary":slot==2?"secondary":null;
  public string Item(int slot)=>IsItemSlot(slot)?items[slot]:null;
  public int SlotOf(string itemId){if(string.IsNullOrEmpty(itemId))return 0;for(int i=FirstItemSlot;i<=Slots;i++)if(items[i]==itemId)return i;return 0;}
  public bool CanHold(string itemId)=>!string.IsNullOrEmpty(itemId)&&(usable==null||usable(itemId));
  /// Puts an item on a slot (moving it if it already sits on another). Reasons: "weapon_slot", "not_usable", "bad_slot".
  public bool Assign(int slot,string itemId,out string reason)
  {
   if(IsWeaponSlot(slot)){reason="weapon_slot";return false;}
   if(!IsItemSlot(slot)){reason="bad_slot";return false;}
   if(!CanHold(itemId)){reason="not_usable";return false;}
   int previous=SlotOf(itemId);
   if(previous==slot){reason="ok";return true;}
   if(previous>0)items[previous]=null;
   items[slot]=itemId;reason="ok";Changed?.Invoke();return true;
  }
  /// Empties an item slot; false when it was already empty (or is a weapon slot).
  public bool Clear(int slot)
  {
   if(!IsItemSlot(slot)||items[slot]==null)return false;
   items[slot]=null;Changed?.Invoke();return true;
  }
  /// Swaps two item slots (drag one strip cell onto another).
  public bool Swap(int a,int b)
  {
   if(!IsItemSlot(a)||!IsItemSlot(b)||a==b)return false;
   (items[a],items[b])=(items[b],items[a]);Changed?.Invoke();return true;
  }
  public void ResetToDefaults()
  {
   Array.Clear(items,0,items.Length);
   foreach(var d in Defaults)if(CanHold(d.Value))items[d.Key]=d.Value;
   Changed?.Invoke();
  }
  public HotbarEntry[] Capture()=>Enumerable.Range(FirstItemSlot,Slots-FirstItemSlot+1).Where(i=>items[i]!=null).Select(i=>new HotbarEntry{slot=i,itemId=items[i]}).ToArray();
  /// Save restore. Null (a save from before the configurable hotbar) gives the defaults; an empty array is an empty bar.
  /// Entries for weapon or unknown slots, unusable items and repeats are skipped.
  public void Restore(HotbarEntry[] entries)
  {
   if(entries==null){ResetToDefaults();return;}
   Array.Clear(items,0,items.Length);
   foreach(var e in entries)
    if(e!=null&&IsItemSlot(e.slot)&&items[e.slot]==null&&CanHold(e.itemId)&&SlotOf(e.itemId)==0)items[e.slot]=e.itemId;
   Changed?.Invoke();
  }
 }
}
