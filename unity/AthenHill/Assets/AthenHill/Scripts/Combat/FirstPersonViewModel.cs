using UnityEngine;
namespace AthenHill
{
 /// First-person arms and scrap pistol. The arms are the player colonist's own forearms/hands (split mesh, same
 /// skin and textures) posed by the retargeted aim clip; they render on the ViewModel layer through a URP overlay
 /// camera, so they never clip into walls. Each frame the rig is placed so the pistol sits at a camera-space hip or
 /// aim-down-sights pose, plus look sway, walk bob, recoil and a draw/holster slide. Shown only in first person with
 /// the pistol drawn and gameplay active (so never inside Ward, in dialogue, shops or menus).
 public class FirstPersonViewModel:MonoBehaviour
 {
  public GameSession session;
  public PlayerCombat combat;
  public PlayerMotor motor;
  public FollowCamera follow;
  public Camera viewCamera;
  [Tooltip("Overlay camera that renders only the ViewModel layer; its field of view follows the main camera so the tracer lines up.")]
  public Camera overlayCamera;
  [Tooltip("Moved every frame so the pistol lands on the target pose.")]
  public Transform rig;
  public Animation animationSource;
  public AnimationClip holdClip;
  public Transform pistol,muzzle;
  public MuzzleFlash flash;
  public GameObject visuals;
  [Header("Pose (camera space, metres / degrees)")]
  public Vector3 hipOffset=new Vector3(.14f,-.15f,.38f);
  public Vector3 hipEuler=new Vector3(-1.5f,-3.5f,-4f);
  public Vector3 aimOffset=new Vector3(0,-.075f,.3f);
  public Vector3 aimEuler=Vector3.zero;
  [Min(.01f)]public float aimSeconds=.16f;
  [Header("Draw / holster")]
  [Min(.01f)]public float drawSeconds=.28f;
  public Vector3 holsterOffset=new Vector3(.05f,-.32f,.1f);
  public Vector3 holsterEuler=new Vector3(35,-10,-20);
  [Header("Motion")]
  [Range(0,.05f)]public float swayAmount=.012f;
  [Range(0,10)]public float swayRotation=2.5f;
  [Min(.1f)]public float swaySmoothing=8;
  [Range(0,.03f)]public float bobAmount=.008f;
  [Range(0,.1f)]public float recoilBack=.05f;
  [Range(0,15)]public float recoilPitch=6;
  [Min(.01f)]public float recoilReturn=.13f;
  [Tooltip("Shown with the field rifle instead of the pistol (3 Oct 2026: one view model per weapon, sharing the overlay camera).")]
  public bool rifle;
  public bool Visible {get;private set;}
  static readonly System.Collections.Generic.List<FirstPersonViewModel> all=new System.Collections.Generic.List<FirstPersonViewModel>();
  void OnEnable(){if(!all.Contains(this))all.Add(this);}
  void OnDisable(){all.Remove(this);}
  bool OverlayWanted(){foreach(var v in all)if(v&&v.overlayCamera==overlayCamera&&v.Visible)return true;return false;}
  public float AimBlend=>aim;
  float draw,aim,aimVelocity,recoil,bobPhase,lastShot=-99;
  Vector2 sway,lastLook;
  bool looked;
  void Start()
  {
   if(animationSource&&holdClip)
   {
    if(animationSource.GetClip(holdClip.name)==null)animationSource.AddClip(holdClip,holdClip.name);
    var s=animationSource[holdClip.name];s.wrapMode=WrapMode.Loop;s.speed=.35f;
   }
   if(visuals)visuals.SetActive(false);
   if(overlayCamera)overlayCamera.enabled=false;
  }
  public void Kick(){recoil=1;if(flash)flash.Fire();}
  void LateUpdate()
  {
   if(!viewCamera||!rig||!pistol)return;
   // One view model per weapon (pistol / field rifle); each shows only with its own weapon drawn.
   bool want=follow&&follow.FirstPerson&&combat&&combat.Armed&&combat.RifleActive==rifle&&(!session||session.State==CityState.Play);
   float dt=Time.deltaTime;
   draw=Mathf.MoveTowards(draw,want?1:0,dt/drawSeconds);
   Visible=draw>0;
   if(visuals&&visuals.activeSelf!=Visible)visuals.SetActive(Visible);
   // The overlay camera costs a URP camera pass every frame, so it only runs while there is something to draw.
   if(overlayCamera){bool o=OverlayWanted();if(overlayCamera.enabled!=o)overlayCamera.enabled=o;}
   if(!Visible){looked=false;return;}
   if(animationSource&&holdClip&&!animationSource.IsPlaying(holdClip.name))animationSource.Play(holdClip.name);
   if(combat.LastShotTime!=lastShot){lastShot=combat.LastShotTime;if(Time.time-lastShot<.1f)Kick();}
   bool reduced=session&&session.reducedMotion;
   aim=Mathf.SmoothDamp(aim,combat.Aiming?1:0,ref aimVelocity,aimSeconds*.5f,Mathf.Infinity,dt);
   // look sway: lag behind camera rotation
   var look=new Vector2(follow.yaw,follow.pitch);
   if(!looked){lastLook=look;looked=true;}
   var delta=new Vector2(Mathf.DeltaAngle(lastLook.x,look.x),look.y-lastLook.y);lastLook=look;
   var swayTarget=reduced?Vector2.zero:Vector2.ClampMagnitude(-delta*.08f,1)*(1-aim*.7f);
   sway=Vector2.Lerp(sway,swayTarget,1-Mathf.Exp(-swaySmoothing*dt));
   // walk bob
   float speed=motor?motor.Speed:0;
   bobPhase+=dt*Mathf.Lerp(0,9,Mathf.Clamp01(speed/4));
   float bob=reduced?0:bobAmount*Mathf.Clamp01(speed/3)*(1-aim*.75f);
   var bobOffset=new Vector3(Mathf.Cos(bobPhase)*bob,Mathf.Abs(Mathf.Sin(bobPhase))*-bob,0);
   recoil=Mathf.MoveTowards(recoil,0,dt/recoilReturn);
   float r=recoil*recoil*(3-2*recoil);
   var offset=Vector3.Lerp(hipOffset,aimOffset,aim)+bobOffset+new Vector3(sway.x*swayAmount,sway.y*swayAmount,0)+Vector3.back*recoilBack*r;
   var euler=Vector3.Lerp(hipEuler,aimEuler,aim)+new Vector3(-recoilPitch*combat.RecoilScale*r+sway.y*swayRotation,sway.x*swayRotation,sway.x*swayRotation*.5f);
   float d=draw*draw*(3-2*draw);
   offset=Vector3.Lerp(holsterOffset,offset,d);euler=Vector3.Lerp(holsterEuler,euler,d);
   var cam=viewCamera.transform;
   var target=Matrix4x4.TRS(cam.position+cam.rotation*offset,cam.rotation*Quaternion.Euler(euler),Vector3.one);
   // place the rig so the (animated) pistol lands exactly on the target pose
   var rel=rig.worldToLocalMatrix*pistol.localToWorldMatrix;
   var place=target*rel.inverse;
   rig.SetPositionAndRotation(place.GetColumn(3),place.rotation);
   if(overlayCamera)overlayCamera.fieldOfView=viewCamera.fieldOfView;
  }
 }
}
