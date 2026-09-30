using System;
using UnityEngine;
namespace AthenHill
{
 /// Shows the fitted pistol mods on a pistol model (first-person view model or the held third-person pistol):
 /// each child of <see cref="mods"/> is named after a mod item id and is visible only while that mod is fitted.
 /// A fitted barrel moves the muzzle to the end of its shroud so the flash and tracer leave the new barrel.
 public class WeaponModVisuals:MonoBehaviour
 {
  [Serializable]public class MuzzleOverride{public string itemId;public Vector3 localPosition;}
  public GameSession session;
  [Tooltip("Parent of the attachment objects; child names are mod item ids (e.g. barrel_bored_alloy).")]
  public Transform mods;
  [Tooltip("Muzzle transform moved when a barrel mod is fitted (optional).")]
  public Transform muzzle;
  public Vector3 defaultMuzzle;
  public MuzzleOverride[] barrelMuzzles=new MuzzleOverride[0];
  CraftingSession crafting;WeaponLoadout bound;
  void Start(){if(session)crafting=session.GetComponent<CraftingSession>();Apply();}
  void OnDestroy(){if(bound!=null)bound.Changed-=Apply;}
  void Update()
  {
   // The crafting model is created after scene start (and again on Continue): bind to whichever loadout is live.
   var loadout=crafting&&crafting.Model!=null?crafting.Model.Loadout:null;
   if(loadout==bound)return;
   if(bound!=null)bound.Changed-=Apply;
   bound=loadout;if(bound!=null)bound.Changed+=Apply;
   Apply();
  }
  public void Apply()
  {
   if(!mods)return;
   string barrel=null;
   for(int i=0;i<mods.childCount;i++)
   {
    var child=mods.GetChild(i);bool on=false;
    if(bound!=null)foreach(var slot in bound.Slots){var id=bound.Fitted(slot);if(id==child.name){on=true;if(slot=="barrel")barrel=id;}}
    if(child.gameObject.activeSelf!=on)child.gameObject.SetActive(on);
   }
   if(!muzzle)return;
   var target=defaultMuzzle;
   if(barrel!=null)foreach(var o in barrelMuzzles)if(o.itemId==barrel)target=o.localPosition;
   muzzle.localPosition=target;
  }
 }
}
