using UnityEngine;
namespace AthenHill
{
 /// Weapon-driven first-person arms (3 Oct 2026, player_face_20261003). FirstPersonViewModel places the weapon (its
 /// `rig` is a weapon mount, not the arms); this keeps the player's arms rig at a fixed camera-space anchor (the
 /// shoulders where the hold clip had them in the hip pose) and the arm IK components (SupportHandIK, order 500) put
 /// both hands on grip points on the weapon. So the grip can be authored round the weapon (palm on the grip, fingers
 /// solved against it) without the hold clip's hand orientation swinging the whole arm, and sway, recoil, aim and
 /// draw move the weapon while the arms follow it.
 /// 20 Nov 2026 (rifle_hands_20261120): optional second anchor for aiming down the sights (blended by the view model's
 /// aim) and a partial follow of the weapon's sway, bob, recoil and draw, so long weapons stay within the arms' reach.
 /// With Aim Anchor off and Follow Weapon 0 (the pistol) the arms stay on the single anchor as before.
 [DefaultExecutionOrder(450)]
 [DisallowMultipleComponent]
 public class ViewModelArmsRig:MonoBehaviour
 {
  public FirstPersonViewModel viewModel;
  [Tooltip("Root of the player's arms rig (the Animation plays the hold clip on it).")]public Transform arms;
  [Tooltip("Arms root pose in camera space.")]public Vector3 anchorPosition;
  public Quaternion anchorRotation=Quaternion.identity;
  [Tooltip("Use a second camera-space anchor while aiming down the sights (blended by the view model's aim).")]public bool aimAnchor;
  public Vector3 aimAnchorPosition;
  public Quaternion aimAnchorRotation=Quaternion.identity;
  [Tooltip("How much the arms move with the weapon's sway, bob, recoil and draw (0 = fixed to the camera, the IK takes it all; 1 = rigid with the weapon).")]
  [Range(0,1)]public float followWeapon;
  [Tooltip("Follow used while the weapon is lowered in the draw/holster slide (blended to Follow Weapon as it comes up), so the wrists do not fold while the weapon drops away. Ignored when Follow Weapon is 0.")]
  [Range(0,1)]public float drawFollow;
  void LateUpdate()
  {
   if(!viewModel||!arms||!viewModel.viewCamera||!viewModel.Visible)return;
   var cam=viewModel.viewCamera.transform;
   Place(cam.position,cam.rotation,viewModel.AimBlend,viewModel.DrawBlend);
  }
  public void Place(Vector3 camPos,Quaternion camRot)=>Place(camPos,camRot,viewModel?viewModel.AimBlend:0);
  public void Place(Vector3 camPos,Quaternion camRot,float aim)=>Place(camPos,camRot,aim,1);
  public void Place(Vector3 camPos,Quaternion camRot,float aim,float draw)
  {
   if(!arms)return;
   Vector3 nominalPos=camPos,actualPos=camPos;Quaternion nominalRot=camRot,actualRot=camRot;
   if(followWeapon>0&&viewModel&&viewModel.pistol)
   {
    nominalPos=camPos+camRot*Vector3.Lerp(viewModel.hipOffset,viewModel.aimOffset,aim);
    nominalRot=camRot*Quaternion.Euler(Vector3.Lerp(viewModel.hipEuler,viewModel.aimEuler,aim));
    actualPos=viewModel.pistol.position;actualRot=viewModel.pistol.rotation;
   }
   Pose(camPos,camRot,anchorPosition,anchorRotation,aimAnchor?aimAnchorPosition:anchorPosition,aimAnchor?aimAnchorRotation:anchorRotation,aim,
    nominalPos,nominalRot,actualPos,actualRot,FollowFor(followWeapon,drawFollow,draw),out var p,out var r);
   arms.SetPositionAndRotation(p,r);
  }
  /// Follow share at a draw blend: Draw Follow while lowered, Follow Weapon once drawn (smoothstep, as the slide).
  public static float FollowFor(float follow,float drawFollow,float draw)
  {
   if(follow<=0||drawFollow<=follow)return follow;
   float d=Mathf.Clamp01(draw);d=d*d*(3-2*d);d*=d;   // stays near Draw Follow until the weapon is nearly up
   return Mathf.Lerp(drawFollow,follow,d);
  }
  /// Arms root pose: the camera-space anchor (hip to aim by `aim`), then moved with the weapon's deviation from its
  /// nominal pose (actual * nominal^-1) by `follow`, turning about the nominal weapon pivot.
  public static void Pose(Vector3 camPos,Quaternion camRot,Vector3 hipPos,Quaternion hipRot,Vector3 aimPos,Quaternion aimRot,float aim,
   Vector3 nominalPos,Quaternion nominalRot,Vector3 actualPos,Quaternion actualRot,float follow,out Vector3 pos,out Quaternion rot)
  {
   aim=Mathf.Clamp01(aim);
   pos=camPos+camRot*Vector3.Lerp(hipPos,aimPos,aim);
   rot=camRot*Quaternion.Slerp(hipRot,aimRot,aim);
   if(follow<=0)return;
   follow=Mathf.Clamp01(follow);
   var d=Quaternion.Slerp(Quaternion.identity,actualRot*Quaternion.Inverse(nominalRot),follow);
   pos=nominalPos+d*(pos-nominalPos)+(actualPos-nominalPos)*follow;
   rot=d*rot;
  }
 }
}
