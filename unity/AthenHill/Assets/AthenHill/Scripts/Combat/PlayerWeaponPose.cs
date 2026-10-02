using UnityEngine;
namespace AthenHill
{
 /// Third-person weapon pose for the player colonist (pistol, and since 2 Oct 2026 the field rifle). A retargeted two-handed hold (Meshy library "Walk Forward
 /// While Shooting", upper body only) is mixed over idle/walk/run from the lower spine on a higher legacy Animation
 /// layer while aiming, briefly after a hip shot, and as a quick raise when drawing. After the animation samples,
 /// the spine bends toward the camera pitch, the hand turns the barrel onto the aim line, and each shot adds a
 /// short recoil kick. Legs, feet and root motion stay with the locomotion clips. While the pistol is drawn but not
 /// raised, the hand turns it into a muzzle-down carry (the aim mount alone left the barrel sticking out at 45 degrees
 /// from the hanging idle hand, 2 Oct 2026).
 [DisallowMultipleComponent]
 public class PlayerWeaponPose:MonoBehaviour
 {
  public PlayerCombat combat;
  public ActorAnimation actor;
  public Camera view;
  public AnimationClip aimClip;
  [Tooltip("The upper-body layer is mixed from this bone down its hierarchy (the lowest spine bone).")]
  public Transform mixRoot;
  public Transform[] spine=new Transform[0];
  public Transform rightHand;
  [Min(.01f)]public float raiseSeconds=.12f,lowerSeconds=.25f;
  [Tooltip("Seconds the pistol stays raised after a hip-fire shot.")]
  [Min(0)]public float holdAfterShot=.9f;
  [Range(0,1)]public float drawRaise=.6f;
  [Min(0)]public float drawRaiseSeconds=.35f;
  [Range(0,1)]public float pitchShare=.85f;
  [Range(0,1)]public float barrelAlign=.8f;
  [Range(0,15)]public float recoilPitch=7;
  [Min(.01f)]public float recoilReturn=.14f;
  [Header("Carry (drawn, not raised)")]
  [Tooltip("Degrees below the colonist's forward that the barrel points while the pistol is drawn but not raised: the pistol turns in the hand into a muzzle-down carry beside the thigh (the hand keeps its locomotion pose).")]
  [Range(0,90)]public float carryPitch=60;
  [Tooltip("How far the pistol is turned onto the carry line (1 = fully).")]
  [Range(0,1)]public float carryAlign=1;
  [Header("Field rifle")]
  [Tooltip("Two-handed rifle hold mixed over the upper body while the rifle is raised (aiming, after a shot, on draw).")]
  public AnimationClip rifleAimClip;
  [Tooltip("Lowered two-handed rifle carry mixed in while the rifle is drawn but not raised. Empty = the rifle turns in the hand like the pistol.")]
  public AnimationClip rifleCarryClip;
  [Range(0,90)]public float rifleCarryPitch=45;
  [Range(0,1)]public float rifleCarryAlign=.5f;
  [Range(0,1)]public float rifleBarrelAlign=.8f;
  public float Weight {get;private set;}
  /// The weight of the rifle's lowered carry layer (0 with the pistol or when raised).
  public float CarryWeight {get;private set;}
  AnimationState state,rifleState,rifleCarryState;
  /// The raise state of the drawn weapon (pistol hold or rifle hold).
  AnimationState Raised=>combat&&combat.RifleActive&&rifleState!=null?rifleState:state;
  float recoil,drawStart=-99,lastShot=-99,weightVelocity;
  bool wasArmed;
  /// The pistol's saved mount in the hand (set for the two-handed hold); the carry turns away from it each frame.
  readonly System.Collections.Generic.Dictionary<Transform,Quaternion> mounts=new System.Collections.Generic.Dictionary<Transform,Quaternion>();
  void Start()
  {
   var anim=actor?actor.animationSource:null;
   if(!anim||!aimClip||!mixRoot){enabled=false;return;}
   state=Hold(anim,aimClip,"pistol_hold");
   if(rifleAimClip)rifleState=Hold(anim,rifleAimClip,"rifle_hold");
   if(rifleCarryClip)rifleCarryState=Hold(anim,rifleCarryClip,"rifle_carry");
  }
  /// An upper-body layer-5 state of a hold clip, from the mix root down, off until weighted.
  AnimationState Hold(Animation anim,AnimationClip clip,string name)
  {
   if(anim.GetClip(name)==null)anim.AddClip(clip,name);
   var st=anim[name];
   st.layer=5;st.wrapMode=WrapMode.Loop;st.blendMode=AnimationBlendMode.Blend;
   st.AddMixingTransform(mixRoot,true);
   st.weight=0;st.enabled=false;st.speed=.5f;
   return st;
  }
  void Update()
  {
   if(state==null)return;
   bool armed=combat&&combat.Armed;
   if(armed&&!wasArmed)drawStart=Time.time;
   wasArmed=armed;
   if(combat&&combat.LastShotTime!=lastShot){lastShot=combat.LastShotTime;if(Time.time-lastShot<.1f)recoil=1;}
   float want=0;
   if(armed)
   {
    if(combat.Aiming||Time.time-lastShot<holdAfterShot)want=1;
    else if(Time.time-drawStart<drawRaiseSeconds)want=drawRaise;
   }
   Weight=Mathf.SmoothDamp(Weight,want,ref weightVelocity,want>Weight?raiseSeconds*.5f:lowerSeconds*.5f);
   bool rifle=combat&&combat.RifleActive;
   var raised=Raised;
   foreach(var st in new[]{state,rifleState,rifleCarryState})if(st!=null&&st!=raised){st.weight=0;st.enabled=false;}
   raised.weight=Weight;raised.enabled=Weight>.001f;
   // The rifle's lowered carry fills the rest of the layer while it is drawn, so the upper body always holds the rifle.
   CarryWeight=rifle&&armed&&rifleCarryState!=null?1-Weight:0;
   if(rifleCarryState!=null){rifleCarryState.weight=CarryWeight;rifleCarryState.enabled=CarryWeight>.001f;}
  }
  void LateUpdate()
  {
   if(state==null||!view)return;
   var held=combat?combat.HeldWeapon:null;
   bool shown=rightHand&&held&&held.activeInHierarchy;
   if(Weight<=.001f&&!shown)return;
   recoil=Mathf.MoveTowards(recoil,0,Time.deltaTime/recoilReturn);
   var body=actor.transform;
   // Bend the spine toward the camera pitch (the clips hold the weapon level).
   var aimDir=view.transform.forward;
   float pitch=-Mathf.Asin(Mathf.Clamp(aimDir.y,-1,1))*Mathf.Rad2Deg;
   float r=recoil*recoil*(3-2*recoil);
   if(spine.Length>0&&Weight>.001f)
   {
    var axis=body.right;
    float each=(pitch*pitchShare-recoilPitch*combat.RecoilScale*r*.5f)*Weight/spine.Length;
    foreach(var b in spine)if(b)b.rotation=Quaternion.AngleAxis(each,axis)*b.rotation;
   }
   if(shown)
   {
    bool rifle=combat.RifleActive;
    float pitchDown=rifle?rifleCarryPitch:carryPitch,align=rifle?rifleCarryAlign:carryAlign,aimAlign=rifle?rifleBarrelAlign:barrelAlign;
    var weapon=held.transform;
    if(!mounts.TryGetValue(weapon,out var mountLocal)){mountLocal=weapon.localRotation;mounts[weapon]=mountLocal;}
    weapon.localRotation=mountLocal;
    // Not raised: turn the weapon in the hand onto the carry line (the pistol's aim mount alone left the barrel yawed
    // 117 degrees out of the hanging idle hand). The hand itself keeps its locomotion or carry-clip pose.
    if(Weight<.999f&&align>0)
    {
     var carry=Quaternion.FromToRotation(weapon.forward,CarryDirection(body,pitchDown));
     weapon.rotation=Quaternion.Slerp(Quaternion.identity,carry,align*(1-Weight))*weapon.rotation;
    }
    // Raised: turn the hand so the barrel follows the aim line, then kick it up on a shot.
    if(Weight>.001f)
    {
     var fix=Quaternion.FromToRotation(weapon.forward,aimDir);
     rightHand.rotation=Quaternion.Slerp(Quaternion.identity,fix,aimAlign*Weight)*rightHand.rotation;
     rightHand.rotation=Quaternion.AngleAxis(-recoilPitch*combat.RecoilScale*r*Weight,body.right)*rightHand.rotation;
    }
   }
  }
  /// The muzzle-down carry line: the colonist's forward pitched down by Carry Pitch degrees.
  public static Vector3 CarryDirection(Transform body,float carryPitch)=>Quaternion.AngleAxis(carryPitch,body.right)*body.forward;
 }
}
