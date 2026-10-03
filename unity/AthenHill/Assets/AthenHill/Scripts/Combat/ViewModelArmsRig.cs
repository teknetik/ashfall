using UnityEngine;
namespace AthenHill
{
 /// Weapon-driven first-person arms (3 Oct 2026, player_face_20261003). FirstPersonViewModel places the weapon (its
 /// `rig` is a weapon mount, not the arms); this keeps the player's arms rig at a fixed camera-space anchor (the
 /// shoulders where the hold clip had them in the hip pose) and the arm IK components (SupportHandIK, order 500) put
 /// both hands on grip points on the weapon. So the grip can be authored round the weapon (palm on the grip, fingers
 /// solved against it) without the hold clip's hand orientation swinging the whole arm, and sway, recoil, aim and
 /// draw move the weapon while the arms follow it.
 [DefaultExecutionOrder(450)]
 [DisallowMultipleComponent]
 public class ViewModelArmsRig:MonoBehaviour
 {
  public FirstPersonViewModel viewModel;
  [Tooltip("Root of the player's arms rig (the Animation plays the hold clip on it).")]public Transform arms;
  [Tooltip("Arms root pose in camera space.")]public Vector3 anchorPosition;
  public Quaternion anchorRotation=Quaternion.identity;
  void LateUpdate()
  {
   if(!viewModel||!arms||!viewModel.viewCamera||!viewModel.Visible)return;
   var cam=viewModel.viewCamera.transform;
   Place(cam.position,cam.rotation);
  }
  public void Place(Vector3 camPos,Quaternion camRot)
  {
   if(!arms)return;
   arms.SetPositionAndRotation(camPos+camRot*anchorPosition,camRot*anchorRotation);
  }
 }
}
