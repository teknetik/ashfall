using UnityEngine;
namespace AthenHill
{
 public class NpcAgent : MonoBehaviour
 {
  public NpcDefinition definition;
  public ActorAnimation actor;
  [Tooltip("Counts toward the original four-colonist city visit objective.")]
  public bool countsForCityVisit=true;
  public bool talking;
  void Update(){if(actor)actor.SetMotion(0,false,talking);}
 }
}
