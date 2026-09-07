using System;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class ItemSpec {public string id,name;[TextArea]public string description;[Min(0)]public int buyPrice,sellPrice,startingQuantity;}
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
