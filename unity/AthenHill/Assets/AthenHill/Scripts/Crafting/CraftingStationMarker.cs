using UnityEngine;
namespace AthenHill
{
 [RequireComponent(typeof(WorldInteractable))]
 public class CraftingStationMarker:MonoBehaviour
 {
  public string stationId="station_field_fabricator";
  public GameSession session;
  WorldInteractable interaction;
  void OnEnable(){interaction=GetComponent<WorldInteractable>();interaction.Used+=Use;}
  void OnDisable(){if(interaction)interaction.Used-=Use;}
  void Use(){if(session)session.OpenFabricator(stationId);}
 }
}
