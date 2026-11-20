using UnityEngine;
namespace AthenHill
{
 /// Native review camera that rides with the player colonist (character arms pass, 20 Nov 2026; development builds only).
 /// The scene keeps one inactive object per view under "Character arms review cameras" ("Arms review rig front", "... side",
 /// ...); native QA switches one on with the setActive command. While on, the main camera sits at Offset in the colonist's
 /// own frame (x right, y up, z forward of his facing) looking at Look At, every frame, so walking, running and aiming can be
 /// filmed from the front, side or three-quarter. Movement, facing and the weapon's aim line follow a steering proxy fixed
 /// at the heading the follow camera had when the rig was switched on (W walks that way whatever the review view), so the
 /// colonist does not turn toward the review camera. Switching it off puts everything back.
 [DefaultExecutionOrder(950)]
 public class ArmsReviewRig:MonoBehaviour
 {
  public Vector3 offset=new Vector3(0,1,3.4f);
  public Vector3 lookAt=new Vector3(0,.92f,0);
  [Range(10,90)]public float fieldOfView=40;
  PlayerMotor motor;PlayerCombat combat;PlayerWeaponPose pose;FollowCamera follow;Camera main;
  GameObject proxy;Transform oldMotorView;Camera oldCombatView,oldPoseView;float oldFov;bool oldFixed;float yaw;bool live;
  void OnEnable()
  {
   live=false;
   if(!Application.isEditor&&!Debug.isDebugBuild)return;
   motor=FindAnyObjectByType<PlayerMotor>();combat=FindAnyObjectByType<PlayerCombat>();pose=FindAnyObjectByType<PlayerWeaponPose>();follow=FindAnyObjectByType<FollowCamera>();
   if(!motor||!follow)return;
   main=follow.GetComponent<Camera>();
   yaw=follow.transform.eulerAngles.y;
   proxy=new GameObject("Arms review steer");var cam=proxy.AddComponent<Camera>();cam.enabled=false;
   PlaceProxy();
   oldMotorView=motor.view;motor.view=proxy.transform;
   if(combat){oldCombatView=combat.view;combat.view=cam;}
   if(pose){oldPoseView=pose.view;pose.view=cam;}
   oldFixed=follow.FixedView;follow.FixedView=true;
   if(main){oldFov=main.fieldOfView;}
   live=true;
  }
  void PlaceProxy()
  {
   var rot=Quaternion.Euler(0,yaw,0);
   proxy.transform.SetPositionAndRotation(motor.transform.position+Vector3.up*1.6f-rot*Vector3.forward*2.5f,rot);
  }
  void LateUpdate()
  {
   if(!live||!motor)return;
   PlaceProxy();
   var visual=motor.visual?motor.visual:motor.transform;
   var face=Quaternion.Euler(0,visual.eulerAngles.y,0);
   var feet=visual.position;
   var pos=feet+face*offset;var look=feet+face*lookAt;
   follow.transform.SetPositionAndRotation(pos,Quaternion.LookRotation(look-pos,Vector3.up));
   if(main)main.fieldOfView=fieldOfView;
  }
  void OnDisable()
  {
   if(!live)return;live=false;
   if(motor)motor.view=oldMotorView;
   if(combat)combat.view=oldCombatView;
   if(pose)pose.view=oldPoseView;
   if(follow)follow.FixedView=oldFixed;
   if(main)main.fieldOfView=oldFov;
   if(proxy)Destroy(proxy);
  }
 }
}
