using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Snapshot fields for the native checks of the hotbar, journal and home (5 Oct 2026); NativeQa writes them.
 public static class HomeQa
 {
  public static object Hotbar(GameSession s)=>s.Quickbar==null?null:Enumerable.Range(1,HotbarModel.Slots).Select(i=>new{slot=i,key=HotbarModel.Key(i),item=HotbarModel.IsWeaponSlot(i)?s.Character?.Equipped(HotbarModel.WeaponSlot(i)):s.Quickbar.Item(i),count=HotbarModel.IsItemSlot(i)&&s.Quickbar.Item(i)!=null?s.Shop.Quantity(s.Quickbar.Item(i)):-1}).ToArray();
  public static object Journal(GameSession s)
  {
   var j=s.Journal;if(!j)return null;
   var t=j.Tracked;
   return new{tracked=j.TrackedId,trackedTitle=t?.title,trackedObjective=t?.objective,trackedTarget=t?.target?t.target.name:null,trackedLabel=t?.targetLabel,
    missions=j.Missions.Select(m=>new{m.id,m.title,status=m.status.ToString(),done=m.StepsDone,steps=m.steps.Count,current=m.steps.FirstOrDefault(x=>x.current)?.text}).ToArray()};
  }
  public static object Home(GameSession s)
  {
   var h=s.Home;
   var zone=h?h.GetComponentInChildren<CameraConfineZone>(true):null;
   return new{present=(bool)h,leased=s.HasFlag(WardHome.LeasedFlag),stored=s.HasFlag(WardHome.StoredFlag),rested=s.HasFlag(WardHome.RestedFlag),
    doorLocked=h&&h.door?h.door.Locked:true,doorOpen=h&&h.door?h.door.OpenFraction:0,insideZone=zone&&zone.Inside,confined=s.follow&&s.follow.Confined,
    stash=s.Stash?.Stored.Select(x=>new{item=x.Key,quantity=x.Value}).ToArray(),stashSlots=s.Stash?.SlotsUsed??0,stashCapacity=s.Stash?.SlotCapacity??0};
  }
 }
}
