using UnityEngine;
namespace AthenHill
{
 public class NpcAgent : MonoBehaviour
 {
  public NpcDefinition definition;
  public ActorAnimation actor;
  [Tooltip("Counts toward the original four-colonist city visit objective.")]
  public bool countsForCityVisit=true;
  [Tooltip("Workbench this colonist keeps: a dialogue choice with action \"fabricator\" opens it (Brann at Salvage).")]
  public CraftingStationMarker workbench;
  public bool talking;
  void Update(){if(actor)actor.SetMotion(0,false,talking);}
 }
}
