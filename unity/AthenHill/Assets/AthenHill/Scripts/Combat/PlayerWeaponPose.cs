using UnityEngine;
namespace AthenHill
{
 /// Third-person pistol pose for the player colonist. A retargeted two-handed hold (Meshy library "Walk Forward
 /// While Shooting", upper body only) is mixed over idle/walk/run from the lower spine on a higher legacy Animation
 /// layer while aiming, briefly after a hip shot, and as a quick raise when drawing. After the animation samples,
 /// the spine bends toward the camera pitch, the hand turns the barrel onto the aim line, and each shot adds a
 /// short recoil kick. Legs, feet and root motion stay with the locomotion clips.
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
  public float Weight {get;private set;}
  AnimationState state;
  float recoil,drawStart=-99,lastShot=-99,weightVelocity;
  bool wasArmed;
  void Start()
  {
   var anim=actor?actor.animationSource:null;
   if(!anim||!aimClip||!mixRoot){enabled=false;return;}
   if(anim.GetClip(aimClip.name)==null)anim.AddClip(aimClip,aimClip.name);
   state=anim[aimClip.name];
   state.layer=5;state.wrapMode=WrapMode.Loop;state.blendMode=AnimationBlendMode.Blend;
   state.AddMixingTransform(mixRoot,true);
   state.weight=0;state.enabled=true;state.speed=.5f;
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
   state.weight=Weight;state.enabled=Weight>.001f;
  }
  void LateUpdate()
  {
   if(state==null||Weight<=.001f||!view)return;
   recoil=Mathf.MoveTowards(recoil,0,Time.deltaTime/recoilReturn);
   var body=actor.transform;
   // Bend the spine toward the camera pitch (the clip holds the pistol level).
   var aimDir=view.transform.forward;
   float pitch=-Mathf.Asin(Mathf.Clamp(aimDir.y,-1,1))*Mathf.Rad2Deg;
   float r=recoil*recoil*(3-2*recoil);
   if(spine.Length>0)
   {
    var axis=body.right;
    float each=(pitch*pitchShare-recoilPitch*r*.5f)*Weight/spine.Length;
    foreach(var b in spine)if(b)b.rotation=Quaternion.AngleAxis(each,axis)*b.rotation;
   }
   // Turn the hand so the barrel follows the aim line, then kick it up on a shot.
   if(rightHand&&combat.heldPistol&&combat.heldPistol.activeInHierarchy)
   {
    var barrel=combat.heldPistol.transform.forward;
    var fix=Quaternion.FromToRotation(barrel,aimDir);
    rightHand.rotation=Quaternion.Slerp(Quaternion.identity,fix,barrelAlign*Weight)*rightHand.rotation;
    rightHand.rotation=Quaternion.AngleAxis(-recoilPitch*r*Weight,body.right)*rightHand.rotation;
   }
  }
 }
}
