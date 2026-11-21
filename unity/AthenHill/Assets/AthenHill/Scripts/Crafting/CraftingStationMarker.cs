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
  /// 20 Nov 2026 (Steady Hands bench): a hands-on job that is due or open opens the bench directly; otherwise the window.
  void Use()
  {
   if(!session)return;
   var crafting=session.GetComponent<CraftingSession>();
   if(crafting&&crafting.UseStation(this))return;
   session.OpenFabricator(this);
  }
 }
}
