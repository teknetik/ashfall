using UnityEngine;
namespace AthenHill
{
 /// First-person view models (3 Oct 2026, player_face_20261003): copies of the worn hand/forearm armour (field gloves,
 /// arm guards) skinned to the view-model arms. Each copy is shown exactly while its third-person piece is shown
 /// (PlayerArmourVisuals toggles the piece models by equipment), so the first-person hands match the body.
 [DisallowMultipleComponent]
 public class ViewModelArmourMirror:MonoBehaviour
 {
  [Tooltip("Third-person armour piece models (PlayerArmourVisuals.pieces[].model).")]public GameObject[] sources=new GameObject[0];
  [Tooltip("The view-model copies, same order.")]public GameObject[] mirrors=new GameObject[0];
  void LateUpdate()
  {
   for(int i=0;i<mirrors.Length&&i<sources.Length;i++)
   {
    var m=mirrors[i];if(!m)continue;
    bool on=sources[i]&&sources[i].activeSelf;
    if(m.activeSelf!=on)m.SetActive(on);
   }
  }
 }
}
