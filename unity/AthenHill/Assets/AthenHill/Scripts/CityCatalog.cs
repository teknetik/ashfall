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
  [Tooltip("Mass of one item in kilograms while it is in the field pack.")]
  [Min(0)]public float weightKg;
  public bool HasTag(string tag)=>tags!=null&&Array.IndexOf(tags,tag)>=0;
 }
 /// What using a carried item does (from a hotbar slot the player assigned it to, 5 Oct 2026). One unit is used per use.
 [Serializable] public class ConsumableSpec
 {
  public string itemId;
  [Tooltip("Health restored, multiplied by the character's Healing efficiency (Medicine).")]
  [Min(0)]public float restoreHealth;
  [Tooltip("Weapon nano charge restored at once.")]
  [Min(0)]public float restoreNano;
  [Tooltip("Seconds the nano regulator stays overclocked after use: the charge keeps refilling while firing, at the bonus below. 0 = no overclock.")]
  [Min(0)]public float overclockSeconds;
  [Tooltip("Extra nano regeneration while overclocked (0.5 = +50 %).")]
  [Min(0)]public float overclockRegen;
  [Tooltip("Short label under the hotbar slot (5 Oct 2026). Empty = the item name's first word.")]
  public string hotbarLabel;
 }
 [Serializable] public class TravelNode {public string id,name;[TextArea] public string description;}
 [CreateAssetMenu(menuName="Athen Hill/City catalog")]
 public class CityCatalog : ScriptableObject
 {
  [Min(0)]public int startingCredits=25;
  public ItemSpec[] items;
  [Tooltip("Usable items: medkits heal, nano recharges refill and overclock the weapon charge.")]
  public ConsumableSpec[] consumables=new ConsumableSpec[0];
  [Min(0),Tooltip("Seconds between two uses of any consumable.")]
  public float consumableCooldown=1f;
  public TravelNode[] destinations;
  [Min(.01f)]public float transitionSeconds=1.25f;
  [TextArea(3,12)]public string notes="Meet the colonists, trade at Basic General, and establish a Lattice link. WASD or arrows move; Shift runs; right-drag turns the camera. E interacts. Esc closes a panel or pauses. R returns to West Gate.";
  public TextAsset credits;
  public ConsumableSpec Consumable(string itemId){if(consumables!=null&&itemId!=null)foreach(var c in consumables)if(c!=null&&c.itemId==itemId)return c;return null;}
 }
}
