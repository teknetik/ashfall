using UnityEngine;
namespace AthenHill
{
 /// Limits of one arm state (idle, walk, run, talk, air). Angles in degrees, lengths in centimetres.
 [System.Serializable]
 public class ArmPoseProfile
 {
  [Tooltip("Shoulder joint height above its bind height, relative to the chest, that is allowed before the collarbone is lowered (cm).")]
  public float shoulderLiftMax=1.5f;
  [Tooltip("Upper arm lean out of the body the pull aims for (deg).")]
  public float abductionTarget=7;
  [Range(0,1)]public float abductionPull=.8f;
  [Tooltip("The pull never brings an arm closer than this (torso, kit and belt clearance, deg).")]
  public float abductionMin=4;
  [Tooltip("Soft limit on the upper arm pointing forward (deg): no reaching at the listener.")]
  public float forwardMax=60;
  [Range(0,1)]public float forwardKeep=.3f;
  [Tooltip("Elbow turned out of the body the pull aims for (deg; 0 = the forearm bends straight forward).")]
  public float elbowOutTarget=10;
  [Range(0,1)]public float elbowOutPull=.7f;
  public float elbowFlexMin=8,elbowFlexMax=145;
  [Tooltip("Most the hand may be ahead of the shoulder, along the body's forward (m): no reaching at the listener.")]
  public float handReachMax=1;
  [Tooltip("Palm facing about the forearm (deg; 0 = palm to the thigh, + = palm turned back).")]
  public float palmTarget=12;
  [Range(0,1)]public float palmPull=.7f;
  [Range(0,1)]public float twistOnForearm=.5f;
  [Tooltip("Wrist bend kept after straightening, as a share, and its ceiling (deg).")]
  [Range(0,1)]public float wristKeep=.5f;
  public float wristMaxBend=22;
  [Tooltip("Extra finger curl toward the palm per joint (deg), thumb curl, and share of the finger spread removed.")]
  public float fingerCurl=0,thumbCurl=0;
  [Range(0,1)]public float spreadPull=0;
  public ArmPoseProfile Clone()=>(ArmPoseProfile)MemberwiseClone();
  /// Field-by-field blend into r (no allocation; r may be a or b).
  public static void Lerp(ArmPoseProfile a,ArmPoseProfile b,float t,ArmPoseProfile r)
  {
   float L(float x,float y)=>x+(y-x)*t;
   r.shoulderLiftMax=L(a.shoulderLiftMax,b.shoulderLiftMax);r.abductionTarget=L(a.abductionTarget,b.abductionTarget);
   r.abductionPull=L(a.abductionPull,b.abductionPull);r.abductionMin=L(a.abductionMin,b.abductionMin);
   r.forwardMax=L(a.forwardMax,b.forwardMax);r.forwardKeep=L(a.forwardKeep,b.forwardKeep);
   r.elbowOutTarget=L(a.elbowOutTarget,b.elbowOutTarget);r.elbowOutPull=L(a.elbowOutPull,b.elbowOutPull);
   r.elbowFlexMin=L(a.elbowFlexMin,b.elbowFlexMin);r.elbowFlexMax=L(a.elbowFlexMax,b.elbowFlexMax);r.handReachMax=L(a.handReachMax,b.handReachMax);
   r.palmTarget=L(a.palmTarget,b.palmTarget);r.palmPull=L(a.palmPull,b.palmPull);r.twistOnForearm=L(a.twistOnForearm,b.twistOnForearm);
   r.wristKeep=L(a.wristKeep,b.wristKeep);r.wristMaxBend=L(a.wristMaxBend,b.wristMaxBend);
   r.fingerCurl=L(a.fingerCurl,b.fingerCurl);r.thumbCurl=L(a.thumbCurl,b.thumbCurl);r.spreadPull=L(a.spreadPull,b.spreadPull);
  }
 }

 /// Natural arms over the legacy clips (character arms pass, 20 Nov 2026; art/character_arms_20261120/README.md).
 /// The Meshy library clips and the retargeted player clips hold the arms straight and out from the body with the
 /// shoulders up, turn the elbows out and the palms back, and some talk clips reach forward at the listener. Each
 /// LateUpdate, after the Animation has sampled and BEFORE PlayerWeaponPose, PlayerHandGrip and ActorLookAt (order 0;
 /// this runs at -20, so the pistol carry line and the finger grips are laid on the corrected arm), it pulls each arm into
 /// a natural envelope: collarbone lift, upper arm lean out of the body and forward reach, elbow turn-out and bend,
 /// forearm twist (split between forearm and hand: no twist bones) and wrist bend. The relaxed finger curl runs later
 /// (ArmPoseFingerPass, order 20, after PlayerHandGrip). Clip timing, legs, hips and head are untouched.
 /// Player: with the pistol drawn the arms keep the correction while the pistol is lowered and hand it to the hold clip
 /// as it is raised (PlayerWeaponPose.Weight); with the rifle drawn the rifle carry/hold own both arms.
 [DefaultExecutionOrder(-20)]
 [DisallowMultipleComponent]
 public class ArmPoseCorrector:MonoBehaviour
 {
  public ActorAnimation actor;
  [Tooltip("Player only: weapon state (fades the correction while a weapon is raised, or the rifle is drawn).")]
  public PlayerCombat combat;
  public PlayerWeaponPose weaponPose;
  public PlayerHandGrip handGrip;
  public Transform chest;
  public Transform leftShoulder,leftArm,leftForeArm,leftHand,rightShoulder,rightArm,rightForeArm,rightHand;
  [Tooltip("Finger joints (thumb, index, middle, ring, pinky; three each), empty on rigs without fingers.")]
  public Transform[] leftFingers=new Transform[0],rightFingers=new Transform[0];
  [Range(0,1)]public float weight=1;
  [Min(.01f)]public float blendSeconds=.2f;
  [Header("Pistol aim, third person (player)")]
  [Tooltip("Arms reach for a two-handed aim while the pistol is raised (PlayerWeaponPose.Weight): the hold clip brings the pistol up to the face with the elbows folded; this extends both arms (two-bone IK) so the pistol sits at Reach in front of the shoulders, the barrel still on the aim line, the support hand cupping the shooting hand. 0 = the hold clip alone.")]
  [Range(0,1)]public float pistolAimWeight=0;
  [Tooltip("Metres from the shoulders' midpoint to the shooting hand along the aim line.")]
  public float pistolAimReach=.44f;
  [Tooltip("Metres above (+) or below the shoulders' midpoint for the shooting hand.")]
  public float pistolAimHeight=.08f;
  [Tooltip("Metres to the body's right (+) of the shoulders' midpoint for the shooting hand.")]
  public float pistolAimSide=.02f;
  [Tooltip("The support hand relative to the shooting hand (body right, up, aim forward; metres).")]
  public Vector3 supportOffset=new Vector3(-.055f,-.03f,-.01f);
  [Tooltip("Elbow pole: how far down (y) and out (x) the elbows point while aiming.")]
  public Vector2 aimElbowPole=new Vector2(.45f,-1f);
  [Min(1)]public float activeDistance=45;
  public ArmPoseProfile idle=new ArmPoseProfile(),walk=new ArmPoseProfile(),run=new ArmPoseProfile(),talk=new ArmPoseProfile(),air=new ArmPoseProfile();
  // bind data (bone-local axes), computed on Awake
  Vector3 chestRight,chestUp,chestForward;
  Vector3 lHandDir,rHandDir,lPalm,rPalm;
  float lLiftBind,rLiftBind;
  bool bound;
  ArmPoseProfile current;float rifleBlend,lowered=1;bool activeThisFrame;
  float leftArmW=1,rightArmW=1,leftFingerW=1,rightFingerW=1;
  Renderer[] renderers;
  // accumulation guard: a bone nobody re-posed since our last write goes back to its uncorrected pose first
  Transform[] guarded;Quaternion[] written,based;
  public bool Bound=>bound;
  /// Torso axes in world space at the current pose (right, up, forward), from the chest's bind axes.
  public (Vector3 right,Vector3 up,Vector3 forward) Torso()=>(chest.rotation*chestRight,chest.rotation*chestUp,chest.rotation*chestForward);
  /// Current palm normal and hand length direction in world space.
  public Vector3 PalmNormal(bool rightSide)=>rightSide?rightHand.rotation*rPalm:leftHand.rotation*lPalm;
  public Vector3 HandDirection(bool rightSide)=>rightSide?rightHand.rotation*rHandDir:leftHand.rotation*lHandDir;
  /// Shoulder joint height above its bind height relative to the chest, in centimetres.
  public float ShoulderLift(bool rightSide){var up=chest.rotation*chestUp;var a=rightSide?rightArm:leftArm;return (Vector3.Dot(a.position-chest.position,up)-(rightSide?rLiftBind:lLiftBind))*100;}
  void Awake(){Bind();if(bound&&Application.isPlaying&&(leftFingers.Length==15||rightFingers.Length==15||weaponPose)&&!GetComponent<ArmPoseFingerPass>())gameObject.AddComponent<ArmPoseFingerPass>().corrector=this;}
  /// Reads the bind pose from the skinned mesh (works on a fresh instance or in the Editor).
  public bool Bind()
  {
   bound=false;
   if(!actor)actor=GetComponent<ActorAnimation>();
   renderers=GetComponentsInChildren<SkinnedMeshRenderer>(true);
   if(!chest||!leftArm||!rightArm||!leftForeArm||!rightForeArm||!leftHand||!rightHand)return false;
   SkinnedMeshRenderer skin=null;
   foreach(var s in GetComponentsInChildren<SkinnedMeshRenderer>(true))
    if(s.sharedMesh&&System.Array.IndexOf(s.bones,chest)>=0&&System.Array.IndexOf(s.bones,rightHand)>=0&&(!skin||s.sharedMesh.vertexCount>skin.sharedMesh.vertexCount))skin=s;
   if(!skin)return false;
   var skinToActor=Quaternion.Inverse(transform.rotation)*skin.transform.rotation;
   Matrix4x4 B(Transform t){int i=System.Array.IndexOf(skin.bones,t);return i>=0&&i<skin.sharedMesh.bindposes.Length?skin.sharedMesh.bindposes[i].inverse:Matrix4x4.identity;}
   bool Has(Transform t)=>t&&System.Array.IndexOf(skin.bones,t)>=0;
   Quaternion R(Transform t)=>skinToActor*B(t).rotation;
   float scale=skin.transform.lossyScale.x;
   Vector3 P(Transform t)=>skinToActor*(Vector3)B(t).GetColumn(3)*scale;
   var chestInv=Quaternion.Inverse(R(chest));
   chestRight=chestInv*Vector3.right;chestUp=chestInv*Vector3.up;chestForward=chestInv*Vector3.forward;
   (Vector3 dir,Vector3 palm) HandAxes(Transform fore,Transform hand,Transform[] fingers,float side)
   {
    var inv=Quaternion.Inverse(R(hand));
    Transform index=Finger(fingers,1,0),middle=Finger(fingers,2,0),pinky=Finger(fingers,4,0);
    if(Has(index)&&Has(middle)&&Has(pinky))
    {
     var d=(P(middle)-P(hand)).normalized;var across=P(index)-P(pinky);
     var n=(side*Vector3.Cross(d,across)).normalized;
     return (inv*d,inv*n);
    }
    var fd=(P(hand)-P(fore)).normalized;
    // no fingers: the Meshy auto-rig binds in a T/A pose with the palms down
    var pd=Vector3.down-Vector3.Dot(Vector3.down,fd)*fd;
    return (inv*fd,inv*pd.normalized);
   }
   (lHandDir,lPalm)=HandAxes(leftForeArm,leftHand,leftFingers,-1);
   (rHandDir,rPalm)=HandAxes(rightForeArm,rightHand,rightFingers,1);
   lLiftBind=Vector3.Dot(P(leftArm)-P(chest),Vector3.up);rLiftBind=Vector3.Dot(P(rightArm)-P(chest),Vector3.up);
   bound=true;return true;
  }
  /// Finger joint (digit 0 thumb .. 4 pinky, joint 0..2) or null.
  public static Transform Finger(Transform[] f,int digit,int joint){int i=digit*3+joint;return f!=null&&f.Length==15&&i<f.Length?f[i]:null;}

  ArmPoseProfile ProfileFor(string clip)
  {
   if(!actor)return idle;
   if(actor.talk&&clip==actor.talk.name)return talk;
   if(actor.run&&clip==actor.run.name&&actor.run!=actor.walk)return run;
   if(actor.walk&&clip==actor.walk.name&&actor.walk!=actor.idle)return walk;
   foreach(var j in new[]{actor.jumpTakeoff,actor.jumpAirborne,actor.jumpFall,actor.jumpLanding,actor.jumpLandingMoving})if(j&&clip==j.name)return air;
   return idle;
  }
  /// Per-arm weights from the player's weapon state: pistol lowered = full correction, raised = none (the hold clip
  /// owns the arms), rifle drawn = none. Fingers: none while PlayerHandGrip holds a grip on that hand.
  void WeaponWeights(float raise,bool rifle)
  {
   float arms=rifle?0:1-raise;
   leftArmW=rightArmW=arms;
   rightFingerW=handGrip?1-handGrip.RightWeight:1;
   leftFingerW=handGrip?1-handGrip.LeftWeight:1;
  }
  void LateUpdate()
  {
   activeThisFrame=false;
   if(!bound||weight<=0)return;
   var cam=Camera.main;
   if(cam&&(cam.transform.position-transform.position).sqrMagnitude>activeDistance*activeDistance)return;
   bool visible=renderers==null||renderers.Length==0;
   if(!visible)foreach(var r in renderers)if(r&&r.isVisible){visible=true;break;}
   if(!visible)return;
   float dt=Time.deltaTime;float k=1-Mathf.Exp(-dt*3/Mathf.Max(.01f,blendSeconds));
   var want=ProfileFor(actor?actor.CurrentClip:"idle");
   if(current==null)current=want.Clone();else ArmPoseProfile.Lerp(current,want,k,current);
   bool armed=combat&&combat.Armed;
   rifleBlend=Mathf.Lerp(rifleBlend,armed&&combat.RifleActive?1:0,k);
   float raise=armed?(weaponPose?weaponPose.Weight:1):0;
   WeaponWeights(raise,false);
   leftArmW*=1-rifleBlend;rightArmW*=1-rifleBlend;
   activeThisFrame=true;
   Apply(current,weight);
  }
  /// Called by ArmPoseFingerPass after PlayerWeaponPose and PlayerHandGrip (order 20).
  public void LateFingers()
  {
   if(bound&&pistolAimWeight>0&&weaponPose&&combat&&combat.Armed&&!combat.RifleActive&&weaponPose.Weight>.001f&&weaponPose.view)
   {
    bool visible=renderers==null||renderers.Length==0;
    if(!visible)foreach(var r in renderers)if(r&&r.isVisible){visible=true;break;}
    if(visible)PistolAim(weaponPose.view.transform.forward,weaponPose.Weight*pistolAimWeight);
   }
   if(activeThisFrame&&current!=null)Fingers(current,weight);
  }
  /// Two-handed pistol aim: both arms IK'd so the shooting hand sits ahead of the shoulders on the aim line and the
  /// support hand cups it; the shooting hand keeps the rotation PlayerWeaponPose gave it (barrel on the aim line).
  public void PistolAim(Vector3 aimDir,float w)
  {
   if(w<=.001f||!bound)return;
   var (right,up,_)=Torso();
   var aim=aimDir.normalized;var flatRight=Vector3.Cross(Vector3.up,Vector3.ProjectOnPlane(aim,Vector3.up)).normalized;
   if(flatRight.sqrMagnitude<.5f)flatRight=right;
   var mid=(leftArm.position+rightArm.position)/2;
   var rTarget=mid+aim*pistolAimReach+Vector3.up*pistolAimHeight+flatRight*pistolAimSide;
   var keepR=rightHand.rotation;
   rTarget=Vector3.Lerp(rightHand.position,rTarget,w);
   TwoBone(rightArm,rightForeArm,rightHand,rTarget,-Vector3.up*-aimElbowPole.y+flatRight*aimElbowPole.x);
   rightHand.rotation=keepR;
   // support hand: palm toward the shooting hand (+right), fingers down and forward round its fingers
   var lTarget=rightHand.position+flatRight*supportOffset.x+Vector3.up*supportOffset.y+aim*supportOffset.z;
   lTarget=Vector3.Lerp(leftHand.position,lTarget,w);
   var keepL=leftHand.rotation;
   TwoBone(leftArm,leftForeArm,leftHand,lTarget,-Vector3.up*-aimElbowPole.y-flatRight*aimElbowPole.x);
   var fingersDir=(aim*.55f-Vector3.up).normalized;var palm=flatRight;
   var want=Quaternion.LookRotation(fingersDir,palm)*Quaternion.Inverse(Quaternion.LookRotation(lHandDir,lPalm));
   leftHand.rotation=Quaternion.Slerp(keepL,want,w);
  }
  /// Places hand at target with upper/fore lengths kept; the elbow bends toward pole.
  static void TwoBone(Transform upper,Transform fore,Transform hand,Vector3 target,Vector3 pole)
  {
   var s=upper.position;float a=(fore.position-s).magnitude,b=(hand.position-fore.position).magnitude;
   var d=target-s;float L=Mathf.Clamp(d.magnitude,Mathf.Abs(a-b)+1e-3f,a+b-1e-3f);var dir=d.normalized;
   float cosA=Mathf.Clamp((a*a+L*L-b*b)/(2*a*L),-1,1);
   var perp=pole-Vector3.Dot(pole,dir)*dir;if(perp.sqrMagnitude<1e-8f)perp=Vector3.Cross(dir,Vector3.right);perp.Normalize();
   var elbow=s+dir*(cosA*a)+perp*(Mathf.Sqrt(1-cosA*cosA)*a);
   AimBone(upper,fore,elbow-s);
   AimBone(fore,hand,s+dir*L-fore.position);
  }
  /// Editor and tests: correct the arms now with a named state's profile (idle, walk, run, talk, air); raise/rifle preview
  /// the player's weapon state (0/false = unarmed or pistol lowered). Fingers follow unless fingers is false (then call
  /// FingersNow after the grip preview, as at runtime).
  public void ApplyNow(string state,float raise=0,bool rifle=false,bool fingers=true)
  {
   if(!bound&&!Bind())return;
   var p=Profile(state);
   guarded=null;
   WeaponWeights(raise,rifle);
   leftFingerW=rightFingerW=1;
   Apply(p,weight);if(fingers)Fingers(p,weight);
  }
  /// Editor: the finger pass alone, with the grip weights PlayerHandGrip holds on each hand (0 = relaxed).
  public void FingersNow(string state,float leftGrip,float rightGrip)
  {
   if(!bound&&!Bind())return;
   leftFingerW=1-leftGrip;rightFingerW=1-rightGrip;
   Fingers(Profile(state),weight);
  }
  ArmPoseProfile Profile(string state)=>state=="walk"?walk:state=="run"?run:state=="talk"?talk:state=="air"?air:idle;
  void Guard()
  {
   if(guarded==null)
   {
    var list=new System.Collections.Generic.List<Transform>{leftShoulder,leftArm,leftForeArm,leftHand,rightShoulder,rightArm,rightForeArm,rightHand};
    list.AddRange(leftFingers);list.AddRange(rightFingers);list.RemoveAll(t=>!t);
    guarded=list.ToArray();written=new Quaternion[guarded.Length];based=new Quaternion[guarded.Length];
    for(int i=0;i<guarded.Length;i++){based[i]=guarded[i].localRotation;written[i]=new Quaternion(9,9,9,9);}
   }
   for(int i=0;i<guarded.Length;i++)
   {
    var t=guarded[i];var q=t.localRotation;
    if(q==written[i])t.localRotation=based[i];else based[i]=q;
   }
  }
  void Seal(){if(guarded==null)return;for(int i=0;i<guarded.Length;i++)written[i]=guarded[i].localRotation;}
  void Apply(ArmPoseProfile p,float w)
  {
   if(Application.isPlaying)Guard();
   if(w>.001f)
   {
    var right=chest.rotation*chestRight;var up=chest.rotation*chestUp;var fwd=chest.rotation*chestForward;
    if(rightArmW>.001f)Arm(p,w*rightArmW,1,right,up,fwd,rightShoulder,rightArm,rightForeArm,rightHand,rHandDir,rPalm,rLiftBind);
    if(leftArmW>.001f)Arm(p,w*leftArmW,-1,right,up,fwd,leftShoulder,leftArm,leftForeArm,leftHand,lHandDir,lPalm,lLiftBind);
   }
   if(Application.isPlaying)Seal();
  }
  /// Turns bone so that its child's direction becomes desired (verified: under a mirrored hierarchy the inverse is used).
  static void AimBone(Transform bone,Transform child,Vector3 desired)
  {
   var cur=child.position-bone.position;if(cur.sqrMagnitude<1e-10f||desired.sqrMagnitude<1e-10f)return;
   float before=Vector3.Angle(cur,desired);if(before<.01f)return;
   var q0=bone.rotation;var q=Quaternion.FromToRotation(cur,desired);
   bone.rotation=q*q0;
   if(Vector3.Angle(child.position-bone.position,desired)>before*.5f){bone.rotation=Quaternion.Inverse(q)*q0;if(Vector3.Angle(child.position-bone.position,desired)>before)bone.rotation=q0;}
  }
  /// Rotates bone about a world axis through itself by the magnitude in whichever direction lowers cost (evaluated after).
  static void TurnBest(Transform bone,Vector3 axis,float magnitude,System.Func<float> cost)
  {
   if(Mathf.Abs(magnitude)<.01f||axis.sqrMagnitude<1e-10f)return;
   var q0=bone.rotation;float c0=cost();
   bone.rotation=Quaternion.AngleAxis(magnitude,axis)*q0;float a=cost();
   bone.rotation=Quaternion.AngleAxis(-magnitude,axis)*q0;float b=cost();
   bone.rotation=a<=b&&a<c0?Quaternion.AngleAxis(magnitude,axis)*q0:b<c0?Quaternion.AngleAxis(-magnitude,axis)*q0:q0;
  }
  void Arm(ArmPoseProfile p,float w,float side,Vector3 right,Vector3 up,Vector3 fwd,Transform clav,Transform upper,Transform fore,Transform hand,Vector3 handDirLocal,Vector3 palmLocal,float liftBind)
  {
   var lat=side*right;
   // the arm's lean before the collarbone moves (lowering the collarbone also swings the arm in)
   var d0=(fore.position-upper.position).normalized;
   float abd=ArmPoseMath.Abduction(d0,lat),fw=ArmPoseMath.Forward(d0,fwd);
   // 1. collarbone: a raised shoulder joint comes down to the allowed lift
   if(clav)
   {
    float lift=(Vector3.Dot(upper.position-chest.position,up)-liftBind)*100;
    if(lift>p.shoulderLiftMax)
    {
     var arm=upper.position-clav.position;float len=arm.magnitude;
     if(len>.01f)
     {
      float want=Mathf.Lerp(lift,p.shoulderLiftMax,w);
      float drop=Mathf.Asin(Mathf.Clamp((lift-want)/100/len,0,1))*Mathf.Rad2Deg;
      TurnBest(clav,Vector3.Cross(arm,up),drop,()=>Mathf.Abs((Vector3.Dot(upper.position-chest.position,up)-liftBind)*100-want));
     }
    }
   }
   // 2. upper arm: lean out of the body and forward reach
   var d=(fore.position-upper.position).normalized;
   float abd2=ArmPoseMath.PullDown(abd,p.abductionTarget,p.abductionPull);
   if(abd2<p.abductionMin)abd2=Mathf.Min(abd,p.abductionMin);
   float fw2=ArmPoseMath.SoftMax(fw,p.forwardMax,p.forwardKeep);
   var d2=ArmPoseMath.WithForward(ArmPoseMath.WithAbduction(d0,lat,Mathf.Lerp(abd,abd2,w)),fwd,up,Mathf.Lerp(fw,fw2,w));
   AimBone(upper,fore,d2);
   d=(fore.position-upper.position).normalized;
   // 3. elbow turned out: twist the upper arm about its own axis (only once the elbow is bent enough to show it)
   var fd=(hand.position-fore.position).normalized;
   float flex=ArmPoseMath.ElbowFlex(d,fd);
   float flexWeight=Mathf.InverseLerp(10,30,flex);
   if(flexWeight>0)
   {
    float outNow=ArmPoseMath.ElbowOut(d,ArmPoseMath.BendDirection(d,fd),fwd,up,lat);
    float outWant=ArmPoseMath.PullDown(outNow,p.elbowOutTarget,p.elbowOutPull);
    if(outNow<-p.elbowOutTarget)outWant=outNow+(-p.elbowOutTarget-outNow)*p.elbowOutPull;   // forearm swung outward (a shrug) or backward: bring it round to the front too
    float mag=Mathf.Abs(Mathf.DeltaAngle(outNow,outWant))*w*flexWeight;
    var u=d;
    TurnBest(upper,u,mag,()=>{var dd=(fore.position-upper.position).normalized;return Mathf.Abs(Mathf.DeltaAngle(ArmPoseMath.ElbowOut(dd,ArmPoseMath.BendDirection(dd,(hand.position-fore.position).normalized),fwd,up,lat),outWant));});
   }
   // 4. elbow bend: a slight bend at least, never past the max (the bend goes forward when the arm is straight)
   fd=(hand.position-fore.position).normalized;flex=ArmPoseMath.ElbowFlex(d,fd);
   {
    var front=ArmPoseMath.Front(d,fwd,up);var frontPerp=(front-Vector3.Dot(front,d)*d).normalized;
    var bend=ArmPoseMath.BendDirection(d,fd);
    // a nearly straight or backward-bending elbow (hyperextension in the clip) is measured from straight, bending forward
    bool backward=bend!=Vector3.zero&&Vector3.Dot(bend,frontPerp)<-.2f&&flex<40;
    if(bend==Vector3.zero||flex<6||backward){bend=frontPerp;if(backward)flex=-flex;}
    float flexWant=Mathf.Lerp(flex,Mathf.Clamp(flex,p.elbowFlexMin,p.elbowFlexMax),w);
    if(Mathf.Abs(flexWant-flex)>.01f)
    {
     var axis=Vector3.Cross(d,bend);
     AimBone(fore,hand,Quaternion.AngleAxis(flexWant,axis)*d);
     var nb=ArmPoseMath.BendDirection(d,(hand.position-fore.position).normalized);
     if(Vector3.Dot(nb,bend)<0)AimBone(fore,hand,Quaternion.AngleAxis(-flexWant,axis)*d);
    }
   }
   // 4b. reach: a hand far ahead of the shoulder swings down about the shoulder (elbow bend kept)
   {
    float reach=Vector3.Dot(hand.position-upper.position,fwd);
    if(reach>p.handReachMax)
    {
     float target=Mathf.Lerp(reach,p.handReachMax,w);float len=(hand.position-upper.position).magnitude;
     float ang=Mathf.Asin(Mathf.Clamp((reach-target)/Mathf.Max(.01f,len),0,1))*Mathf.Rad2Deg;
     TurnBest(upper,right,ang,()=>Mathf.Abs(Vector3.Dot(hand.position-upper.position,fwd)-target));
     d=(fore.position-upper.position).normalized;
    }
   }
   // 5. forearm twist: palm toward the thigh (split between forearm and hand)
   fd=(hand.position-fore.position).normalized;
   float pf=ArmPoseMath.PalmFacing(fd,hand.rotation*palmLocal,lat,side);
   float pfWant=pf;
   if(pf>p.palmTarget)pfWant=pf-(pf-p.palmTarget)*p.palmPull;
   else if(pf<p.palmTarget-45)pfWant=pf+(p.palmTarget-45-pf)*p.palmPull;   // palm turned far forward or out: back in too
   float twist=Mathf.Abs(Mathf.DeltaAngle(pf,pfWant))*w;
   if(twist>.01f)
   {
    float Cost(){var f2=(hand.position-fore.position).normalized;return Mathf.Abs(Mathf.DeltaAngle(ArmPoseMath.PalmFacing(f2,hand.rotation*palmLocal,lat,side),pfWant));}
    var h0=hand.rotation;var fo0=fore.rotation;float best=float.MaxValue;float sign=1;
    foreach(var sg in new[]{1f,-1f})
    {
     fore.rotation=Quaternion.AngleAxis(sg*twist*p.twistOnForearm,fd)*fo0;hand.rotation=Quaternion.AngleAxis(sg*twist,fd)*h0;
     float c=Cost();if(c<best){best=c;sign=sg;}
    }
    fore.rotation=Quaternion.AngleAxis(sign*twist*p.twistOnForearm,fd)*fo0;hand.rotation=Quaternion.AngleAxis(sign*twist,fd)*h0;
   }
   // 6. wrist bend
   fd=(hand.position-fore.position).normalized;
   var hd=hand.rotation*handDirLocal;
   float bendNow=Vector3.Angle(fd,hd);
   float bendWant=Mathf.Lerp(bendNow,Mathf.Min(bendNow*p.wristKeep,p.wristMaxBend),w);
   if(bendNow>.5f&&bendWant<bendNow)
    hand.rotation=Quaternion.Slerp(Quaternion.identity,Quaternion.FromToRotation(hd,fd),1-bendWant/bendNow)*hand.rotation;
  }
  /// Relaxed finger curl toward the palm, spread drawn in toward the middle finger.
  void Fingers(ArmPoseProfile p,float w)
  {
   if(p.fingerCurl<=0&&p.thumbCurl<=0&&p.spreadPull<=0)return;
   if(rightFingerW>.001f)Hand(p,w*rightFingerW,rightHand,rightFingers,rPalm,rHandDir);
   if(leftFingerW>.001f)Hand(p,w*leftFingerW,leftHand,leftFingers,lPalm,lHandDir);
   if(Application.isPlaying)Seal();
  }
  void Hand(ArmPoseProfile p,float w,Transform hand,Transform[] fingers,Vector3 palmLocal,Vector3 handDirLocal)
  {
   if(fingers==null||fingers.Length!=15)return;
   var palm=hand.rotation*palmLocal;
   var mid0=Finger(fingers,2,0);var mid1=Finger(fingers,2,1);
   var midDir=mid0&&mid1?(mid1.position-mid0.position).normalized:hand.rotation*handDirLocal;
   for(int digit=0;digit<5;digit++)
   {
    float curl=(digit==0?p.thumbCurl:p.fingerCurl)*w;
    for(int j=0;j<3;j++)
    {
     var b=Finger(fingers,digit,j);if(!b)continue;
     var next=j<2?Finger(fingers,digit,j+1):null;var prev=j>0?Finger(fingers,digit,j-1):null;
     var dir=next?(next.position-b.position):prev?(b.position-prev.position):Vector3.zero;
     if(dir.sqrMagnitude<1e-10f)continue;dir.Normalize();
     if(j==0&&digit>0&&digit!=2&&p.spreadPull>0)
     {
      var a=dir-Vector3.Dot(dir,palm)*palm;var m=midDir-Vector3.Dot(midDir,palm)*palm;
      if(a.sqrMagnitude>1e-8f&&m.sqrMagnitude>1e-8f)
      {
       var s=Quaternion.Slerp(Quaternion.identity,Quaternion.FromToRotation(a,m),p.spreadPull*w*.6f);
       b.rotation=s*b.rotation;dir=s*dir;
      }
     }
     if(curl<=0)continue;
     var perp=palm-Vector3.Dot(palm,dir)*dir;if(perp.sqrMagnitude<1e-8f)continue;
     var toPalm=Quaternion.FromToRotation(dir,perp.normalized);
     b.rotation=Quaternion.Slerp(Quaternion.identity,toPalm,Mathf.Clamp01(curl/90f))*b.rotation;
    }
   }
  }
 }

 /// The finger half of ArmPoseCorrector, after PlayerHandGrip (order 0) has posed the player's fingers. Added at runtime.
 [DefaultExecutionOrder(20)]
 public class ArmPoseFingerPass:MonoBehaviour
 {
  public ArmPoseCorrector corrector;
  void LateUpdate(){if(corrector)corrector.LateFingers();}
 }
}
