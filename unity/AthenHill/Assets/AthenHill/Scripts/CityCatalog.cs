using System;
using UnityEngine;
namespace AthenHill
{
 /// Loot presentation tier: Common (warm white), Uncommon (Ward cyan), Rare (amber).
 public enum ItemRarity { Common, Uncommon, Rare }
 [Serializable] public class ItemSpec
 {
  public string id,name;[TextArea]public string description;[Min(0)]public int buyPrice,sellPrice,startingQuantity;public string[] tags;[Min(0)]public int maxStack;public bool excludeFromTrade;
  public ItemRarity rarity;
  [Tooltip("Basic General buys this salvage but does not stock it; it is listed under Sell salvage.")]
  public bool sellOnly;
  [Tooltip("USS illustration class (flask-icon, scrap-icon, pistol-icon…). Empty uses the field-pack illustration.")]
  public string icon;
  [Tooltip("Basic General's Buy parts price (Mira's premium over what she pays). 0 = not stocked. Rare parts are never stocked.")]
  [Min(0)]public int partsPrice;
  public bool HasTag(string tag)=>tags!=null&&Array.IndexOf(tags,tag)>=0;
 }
 [Serializable] public class TravelNode {public string id,name;[TextArea] public string description;}
 [CreateAssetMenu(menuName="Athen Hill/City catalog")]
 public class CityCatalog : ScriptableObject
 {
  [Min(0)]public int startingCredits=25;
  public ItemSpec[] items;
  public TravelNode[] destinations;
  [Min(.01f)]public float transitionSeconds=1.25f;
  [TextArea(3,12)]public string notes="Meet the colonists, trade at Basic General, and establish a Lattice link. WASD or arrows move; Shift runs; right-drag turns the camera. E interacts. Esc closes a panel or pauses. R returns to West Gate.";
  public TextAsset credits;
 }
}
