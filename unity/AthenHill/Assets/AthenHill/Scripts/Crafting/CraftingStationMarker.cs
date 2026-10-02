using UnityEngine;
namespace AthenHill
{
 /// A workbench: E opens the fabricator window for its station (recipes name the station they need). Title and
 /// subtitle head the window; the notices after fabricating or fitting are signed with the title.
 [RequireComponent(typeof(WorldInteractable))]
 public class CraftingStationMarker:MonoBehaviour
 {
  public string stationId="station_field_fabricator";
  public GameSession session;
  public string title="Field fabricator";
  public string subtitle="Fabricate parts and fit pistol mods";
  WorldInteractable interaction;
  void OnEnable(){interaction=GetComponent<WorldInteractable>();interaction.Used+=Use;}
  void OnDisable(){if(interaction)interaction.Used-=Use;}
  void Use(){if(session)session.OpenFabricator(this);}
 }
}
