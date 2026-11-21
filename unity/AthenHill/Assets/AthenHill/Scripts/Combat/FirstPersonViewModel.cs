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
  [Header("Handling (Steady Hands bench, 20 Nov 2026): read from the weapon's handling stats")]
  [Tooltip("Share of the weapon's Aim Sway (degrees) the held weapon shows: a slow figure of eight plus tremor, visual only (the shot follows the crosshair).")]
  [Range(0,2)]public float handlingSwayScale=1;
  [Tooltip("While aiming down the sights the sway is multiplied by this.")]
  [Range(0,1)]public float aimSwayShare=.8f;
  [Tooltip("Degrees of view-model yaw per degree of the shot's side kick.")]
  [Range(0,5)]public float sideKickYaw=1.6f;
  [Tooltip("Reduced Motion keeps this share of the idle sway.")]
  [Range(0,1)]public float reducedSwayShare=.3f;
  [Range(0,6)]public float strafeRollDegrees=1.6f;
  [Tooltip("Shown with the field rifle instead of the pistol (3 Oct 2026: one view model per weapon, sharing the overlay camera).")]
  public bool rifle;
  public bool Visible {get;private set;}
  static readonly System.Collections.Generic.List<FirstPersonViewModel> all=new System.Collections.Generic.List<FirstPersonViewModel>();
  void OnEnable(){if(!all.Contains(this))all.Add(this);BindCombat(true);}
  void OnDisable(){all.Remove(this);BindCombat(false);}
  void OnDestroy(){BindCombat(false);}
  bool OverlayWanted(){foreach(var v in all)if(v&&v.overlayCamera==overlayCamera&&v.Visible)return true;return false;}
  public float AimBlend=>aim;
  /// Draw/holster slide, 0 (holstered) to 1 (drawn) (20 Nov 2026, rifle_hands_20261120: read by ViewModelArmsRig).
  public float DrawBlend=>draw;
  float draw,aim,aimVelocity,recoil,bobPhase,lastShot=-99,shotSide,shotRecover=.18f,shotOvershoot,dodgeBlend,shoveImpulse,empImpulse,overchargeSurge,strafeRoll;
  int lastShotsFired=-1;
  Vector2 sway,lastLook;
  Vector3 lastMotorPos;
  bool looked,hasMotorPos,combatSubscribed;
  void BindCombat(bool on)
  {
   if(!combat||combatSubscribed==on)return;
   if(on){combat.Shoved+=OnShoved;combat.EmpTriggered+=OnEmpTriggered;combat.OverchargeTriggered+=OnOverchargeTriggered;}
   else{combat.Shoved-=OnShoved;combat.EmpTriggered-=OnEmpTriggered;combat.OverchargeTriggered-=OnOverchargeTriggered;}
   combatSubscribed=on;
  }
  void OnShoved(){if(Visible)shoveImpulse=1;}
  void OnEmpTriggered(){if(Visible)empImpulse=1;}
  void OnOverchargeTriggered(){if(Visible)overchargeSurge=1;}
  void Start()
  {
   BindCombat(true);
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
   if(combat&&!combatSubscribed)BindCombat(true);
   // One view model per weapon (pistol / field rifle); each shows only with its own weapon drawn.
   bool want=follow&&follow.FirstPerson&&combat&&combat.Armed&&(!combat.Health||combat.Health.Alive)&&combat.RifleActive==rifle&&(!session||session.State==CityState.Play);
   float dt=Time.deltaTime;
   if(dt>1e-6f)draw=Mathf.MoveTowards(draw,want?1:0,dt/drawSeconds);
   Visible=draw>0;
   if(visuals&&visuals.activeSelf!=Visible)visuals.SetActive(Visible);
   // The overlay camera costs a URP camera pass every frame, so it only runs while there is something to draw.
   if(overlayCamera){bool o=OverlayWanted();if(overlayCamera.enabled!=o)overlayCamera.enabled=o;}
   if(!Visible){looked=false;hasMotorPos=false;lastShotsFired=combat?combat.ShotsFired:-1;dodgeBlend=shoveImpulse=empImpulse=overchargeSurge=strafeRoll=0;return;}
   if(animationSource&&holdClip&&!animationSource.IsPlaying(holdClip.name))animationSource.Play(holdClip.name);
   // Track ShotsFired rather than LastShotTime: Dodge/EMP/Overcharge also stamp LastShotTime to pause nano regen.
   if(lastShotsFired<0)lastShotsFired=combat.ShotsFired;
   else if(combat.ShotsFired>lastShotsFired)
   {
    lastShotsFired=combat.ShotsFired;lastShot=combat.LastShotTime;
    Kick();shotSide=combat.LastSideKick;shotRecover=combat.RecoverySeconds;shotOvershoot=WeaponHandlingRules.OvershootFraction(shotRecover);
   }
   else if(combat.ShotsFired<lastShotsFired)lastShotsFired=combat.ShotsFired;
   bool reduced=session&&session.reducedMotion;
   if(dt>1e-6f)
   {
    aim=Mathf.SmoothDamp(aim,combat.Aiming?1:0,ref aimVelocity,aimSeconds*.5f,Mathf.Infinity,dt);
    // look sway: lag behind camera rotation
    var look=new Vector2(follow.yaw,follow.pitch);
    if(!looked){lastLook=look;looked=true;}
    var delta=new Vector2(Mathf.DeltaAngle(lastLook.x,look.x),look.y-lastLook.y);lastLook=look;
    var swayTarget=reduced?Vector2.zero:Vector2.ClampMagnitude(-delta*.08f,1)*(1-aim*.7f);
    sway=Vector2.Lerp(sway,swayTarget,1-Mathf.Exp(-swaySmoothing*dt));
    // lateral strafe tilt
    float lateralSpeed=0;
    if(motor)
    {
     var pos=motor.transform.position;
     if(hasMotorPos)lateralSpeed=Vector3.Dot((pos-lastMotorPos)/dt,viewCamera.transform.right);
     lastMotorPos=pos;hasMotorPos=true;
    }
    float targetRoll=ViewModelMotion.StrafeRoll(lateralSpeed,motor?motor.runSpeed:6f,strafeRollDegrees,aim,reduced);
    strafeRoll=Mathf.Lerp(strafeRoll,targetRoll,1-Mathf.Exp(-10f*dt));
    // walk bob
    float speed=motor?motor.Speed:0;
    bobPhase+=dt*Mathf.Lerp(0,9,Mathf.Clamp01(speed/4));
    dodgeBlend=Mathf.MoveTowards(dodgeBlend,motor&&motor.Dodging?1:0,dt/.09f);
    shoveImpulse=Mathf.MoveTowards(shoveImpulse,0,dt/.22f);
    empImpulse=Mathf.MoveTowards(empImpulse,0,dt/.28f);
    overchargeSurge=Mathf.MoveTowards(overchargeSurge,0,dt/.24f);
   }
   float curSpeed=motor?motor.Speed:0;
   float bob=reduced?0:bobAmount*Mathf.Clamp01(curSpeed/3)*(1-aim*.75f);
   var bobOffset=new Vector3(Mathf.Cos(bobPhase)*bob,Mathf.Abs(Mathf.Sin(bobPhase))*-bob,0);
   ViewModelMotion.VerbPose(dodgeBlend,shoveImpulse,empImpulse,overchargeSurge,combat.OverchargeActive,Time.time,aim,reduced,out var verbOffset,out var verbEuler);
   // 20 Nov 2026: the return time follows the weapon's recovery (recoilReturn at the default 0.18 s); a slow one swings
   // once past rest (negative r) before it settles.
   float returnSeconds=recoilReturn*Mathf.Max(.25f,shotRecover/WeaponHandlingRules.DefaultRecoverySeconds);
   recoil=Mathf.MoveTowards(recoil,0,dt/returnSeconds);
   float r=recoil*recoil*(3-2*recoil);
   float sinceShot=Time.time-lastShot;
   if(recoil<=0&&shotOvershoot>0&&sinceShot<returnSeconds*1.8f)r=-shotOvershoot*Mathf.Sin(Mathf.PI*Mathf.Clamp01((sinceShot-returnSeconds)/(returnSeconds*.8f)));
   // idle handling sway: figure of eight and tremor, degrees (WeaponFeel.Sway)
   var hold=WeaponFeel.Sway(Time.time,combat.Stats.sway*handlingSwayScale*(reduced?reducedSwayShare:1)*Mathf.Lerp(1,aimSwayShare,aim));
   var offset=Vector3.Lerp(hipOffset,aimOffset,aim)+bobOffset+verbOffset+new Vector3(sway.x*swayAmount,sway.y*swayAmount,0)+Vector3.back*recoilBack*r;
   var euler=Vector3.Lerp(hipEuler,aimEuler,aim)+verbEuler+new Vector3(-recoilPitch*combat.RecoilScale*r+sway.y*swayRotation-hold.y,sway.x*swayRotation+hold.x+shotSide*sideKickYaw*Mathf.Max(0,r),sway.x*swayRotation*.5f+strafeRoll);
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
