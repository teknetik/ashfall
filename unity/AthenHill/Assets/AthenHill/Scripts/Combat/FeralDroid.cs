using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 public enum DroidKind { Walker, Hover }
 public enum DroidState { Idle, Alert, Chase, Windup, Recover, Stagger, Returning, Dead }
 /// Feral industrial droid of the Outer Berms: guards its home ground, telegraphs each strike
 /// (optic flares, then a lunge), gives up past its leash and repairs itself when left alone.
 /// Enemies stand still while any city modal is open, so dialogue and menus are always safe.
 [RequireComponent(typeof(Health))]
 public class FeralDroid:MonoBehaviour
 {
  public DroidKind kind;
  public string displayName="Feral worker droid";
  [Header("Behaviour")]
  [Min(0)]public float wanderSpeed=1.1f,chaseSpeed=3.3f,turnSpeed=7;
  [Min(0)]public float aggroRadius=15,leashRadius=30,attackRange=1.8f,wanderRadius=3.5f;
  [Min(0)]public float alertSeconds=.7f,windupSeconds=.6f,recoverSeconds=.9f,staggerSeconds=.25f,staggerImmunity=1.3f;
  [Min(0)]public float strikeDamage=14,repairPerSecond=12;
  [Tooltip("Hover height above ground (Hover kind).")]
  [Min(0)]public float hoverHeight=1.6f;
  [Min(0)]public float corpseSeconds=14;
  public LayerMask groundMask=~(1<<8);
  [Header("Presentation")]
  public Animation animationSource;
  public AnimationClip idle,walk,run,attack,hit,death;
  [Min(.01f)]public float walkStrideSpeed=1.2f,runStrideSpeed=3.2f;
  [Tooltip("Normalized time in the attack clip where the blow lands.")]
  [Range(0,1)]public float attackImpact=.45f;
  public Light eyeLight;
  [Min(0)]public float eyeCalm=.5f,eyeHostile=2.2f;
  public AudioSource voice;
  public AudioClip alertClip,strikeClip,hitClip,deathClip;
  public ParticleSystem sparks,smoke;
  [Header("Telegraph")]
  [Tooltip("Renderers whose emission map (the optic lenses) shows the droid's state: calm, hostile, a flare while winding up a strike, and a flash when hit.")]
  public Renderer[] glowRenderers=new Renderer[0];
  [ColorUsage(false,true)]public Color glowCalm=new Color(1.1f,.45f,.1f),glowHostile=new Color(3.4f,1f,.2f),glowWindup=new Color(9f,5.5f,2.6f);
  [Min(0)]public float hitFlash=5;
  public AudioClip windupClip;
  [Range(0,1)]public float windupVolume=.9f;
  [Header("Walker footsteps")]
  [Tooltip("Foot (toe) bones. A plant is detected when a foot drops back to its lowest height while the droid moves.")]
  public Transform[] feet=new Transform[0];
  public ParticleSystem footDust;
  public AudioClip[] footstepClips=new AudioClip[0];
  [Range(0,1)]public float footstepVolume=.5f;
  [Min(0)]public float footLift=.06f,footPlant=.025f;
  [Header("Hover rotors")]
  public Transform[] rotors=new Transform[0];
  [Tooltip("Degrees per second; alternate rotors counter-rotate.")]
  [Min(0)]public float rotorSpeed=1500,rotorWindupSpeed=2700;
  public ParticleSystem downwash;
  [Min(0)]public float downwashRate=26;
  public AudioSource motorLoop;
  public PlayerCombat Player {get;private set;}
  public GameSession Session {get;private set;}
  public Vector3 Home {get;private set;}
  public DroidState State {get;private set;}
  public Health Health {get;private set;}
  public static readonly List<FeralDroid> Active=new List<FeralDroid>();
  public event Action<FeralDroid> Killed;
  float timer,staggerReady,wanderWait,bob;
  Vector3 wanderTarget,velocity;
  bool struck;
  MaterialPropertyBlock glowBlock;
  Color glowShown=new Color(-1,-1,-1);
  float flash,rotorSpin,groundY,deadAt;
  bool grounded;
  float[] footBase;bool[] footUp;
  static readonly int EmissionId=Shader.PropertyToID("_EmissionColor");
  Rigidbody body;
  Quaternion homeRotation;
  readonly RaycastHit[] hits=new RaycastHit[12];

  void Awake()
  {
   Health=GetComponent<Health>();body=GetComponent<Rigidbody>();
   Health.Damaged+=OnDamaged;Health.Died+=OnDied;
   if(animationSource)foreach(var clip in new[]{idle,walk,run,attack,hit,death})
   {
    if(!clip||animationSource[clip.name]!=null)continue;
    animationSource.AddClip(clip,clip.name);
   }
   Loop(idle);Loop(walk);Loop(run);
   bob=UnityEngine.Random.value*10;
   footBase=new float[feet.Length];footUp=new bool[feet.Length];
   for(int i=0;i<footBase.Length;i++)footBase[i]=float.MaxValue;
   rotorSpin=rotorSpeed;
  }
  void Loop(AnimationClip c){if(animationSource&&c&&animationSource[c.name]!=null)animationSource[c.name].wrapMode=WrapMode.Loop;}
  void OnEnable(){Active.Add(this);}
  void OnDisable(){Active.Remove(this);}
  public void Bind(PlayerCombat player,GameSession session,Vector3 home)
  {
   Player=player;Session=session;Home=home;homeRotation=transform.rotation;
   wanderTarget=home;SetState(DroidState.Idle);Play(idle,1);
  }
  /// Return home at full health (player knocked down, or the encounter re-arming).
  public void ResetToHome(bool revive)
  {
   if(!Health.Alive&&!revive)return;
   bool wasDead=!Health.Alive;
   CancelInvoke(nameof(Sink));gameObject.SetActive(true);
   if(body){body.isKinematic=true;body.useGravity=false;}
   transform.SetPositionAndRotation(Home,homeRotation);
   foreach(var c in GetComponentsInChildren<Collider>())c.enabled=true;
   if(smoke)smoke.Stop();
   Health.Restore();SetState(DroidState.Idle);Play(idle,1);SnapToGround(1);
   if(revive&&wasDead){var loot=GetComponent<LootSource>();if(loot)loot.Revived();}
   flash=0;rotorSpin=rotorSpeed;
   if(motorLoop&&motorLoop.clip){motorLoop.volume=1;if(!motorLoop.isPlaying)motorLoop.Play();}
  }

  bool Hostile=>State==DroidState.Alert||State==DroidState.Chase||State==DroidState.Windup||State==DroidState.Recover||State==DroidState.Stagger;
  bool PlayerAvailable=>Player&&Player.Health.Alive&&Player.InBerms;
  float PlayerDistance=>Flat(Player.transform.position-transform.position).magnitude;

  void Update()
  {
   if(!Player||State==DroidState.Dead)return;
   if(Session&&Session.State!=CityState.Play)return;
   float dt=Time.deltaTime;timer+=dt;
   if(State==DroidState.Idle||State==DroidState.Returning)RepairStep(dt);
   switch(State)
   {
    case DroidState.Idle:
     Wander(dt);
     if(PlayerAvailable&&PlayerDistance<aggroRadius&&CanSee())Alert();
     break;
    case DroidState.Alert:
     Face(Player.transform.position,dt);
     if(timer>=alertSeconds)SetState(DroidState.Chase);
     break;
    case DroidState.Chase:
     if(!PlayerAvailable||Flat(transform.position-Home).magnitude>leashRadius){SetState(DroidState.Returning);break;}
     if(PlayerDistance<=attackRange)
     {
      SetState(DroidState.Windup);struck=false;Play(attack,AttackRate());
      if(voice&&windupClip)voice.PlayOneShot(windupClip,windupVolume);
      break;
     }
     Steer(Player.transform.position,chaseSpeed,dt);Play(run?run:walk,Mathf.Max(.6f,velocity.magnitude/runStrideSpeed));
     break;
    case DroidState.Windup:
     if(!struck)Face(Player.transform.position,dt);
     if(kind==DroidKind.Hover)HoverLunge(dt);
     if(!struck&&timer>=windupSeconds){struck=true;Strike();}
     if(timer>=windupSeconds+.2f)SetState(DroidState.Recover);
     break;
    case DroidState.Recover:
     if(kind==DroidKind.Hover)Steer(transform.position,0,dt);
     if(timer>=recoverSeconds)SetState(DroidState.Chase);
     break;
    case DroidState.Stagger:
     if(timer>=staggerSeconds)SetState(DroidState.Chase);
     break;
    case DroidState.Returning:
     Steer(Home,wanderSpeed*1.6f,dt);Play(walk,Mathf.Max(.6f,velocity.magnitude/walkStrideSpeed));
     if(Flat(transform.position-Home).magnitude<1){SetState(DroidState.Idle);velocity=Vector3.zero;}
     if(PlayerAvailable&&PlayerDistance<aggroRadius*.6f&&CanSee())Alert();
     break;
   }
   if(eyeLight)
   {
    float target=State==DroidState.Windup?eyeHostile*(1.3f+.4f*Mathf.Sin(Time.time*40)):Hostile?eyeHostile:eyeCalm;
    eyeLight.intensity=Mathf.MoveTowards(eyeLight.intensity,target,dt*12);
   }
   if(kind==DroidKind.Hover)HoverPose(dt);
  }

  void RepairStep(float dt){if(repairPerSecond>0&&Health.Alive&&Health.Current<Health.max&&Time.time-Health.LastDamageTime>4)Health.Heal(repairPerSecond*dt);}
  void Alert()
  {
   SetState(DroidState.Alert);Play(idle,1.6f);
   if(voice&&alertClip)voice.PlayOneShot(alertClip);
  }
  void SetState(DroidState s){State=s;timer=0;}
  float AttackRate(){return attack?Mathf.Max(.5f,attack.length*attackImpact/Mathf.Max(.05f,windupSeconds)):1;}

  void Strike()
  {
   if(voice&&strikeClip)voice.PlayOneShot(strikeClip);
   if(!PlayerAvailable)return;
   var to=Flat(Player.transform.position-transform.position);
   if(to.magnitude<=attackRange+.6f&&Vector3.Angle(Flat(transform.forward),to)<75)Player.Health.Damage(strikeDamage,transform.position);
  }

  void Wander(float dt)
  {
   if(Flat(wanderTarget-transform.position).magnitude<.4f)
   {
    wanderWait-=dt;velocity=Vector3.zero;Play(idle,1);
    if(wanderWait<=0){var r=UnityEngine.Random.insideUnitCircle*wanderRadius;wanderTarget=Home+new Vector3(r.x,0,r.y);wanderWait=UnityEngine.Random.Range(2.5f,6f);}
    return;
   }
   Steer(wanderTarget,wanderSpeed,dt);Play(walk,Mathf.Max(.5f,velocity.magnitude/walkStrideSpeed));
  }

  /// Ground steering: go around blocking colliders, keep apart from other droids, stay on the terrain.
  void Steer(Vector3 target,float speed,float dt)
  {
   var to=Flat(target-transform.position);
   Vector3 dir=to.sqrMagnitude>.01f?to.normalized:Vector3.zero;
   if(dir!=Vector3.zero&&Blocked(dir))
   {
    var left=Quaternion.Euler(0,-55,0)*dir;var right=Quaternion.Euler(0,55,0)*dir;
    dir=!Blocked(right)?right:!Blocked(left)?left:Quaternion.Euler(0,100,0)*dir;
   }
   foreach(var other in Active)
   {
    if(other==this||other.State==DroidState.Dead)continue;
    var away=Flat(transform.position-other.transform.position);float d=away.magnitude;
    if(d<1.6f&&d>.001f)dir+=away/d*(1.6f-d);
   }
   dir=Flat(dir);if(dir.sqrMagnitude>1)dir.Normalize();
   velocity=Vector3.Lerp(velocity,dir*speed,1-Mathf.Exp(-6*dt));
   if(velocity.sqrMagnitude>.01f)Face(transform.position+velocity,dt);
   transform.position+=velocity*dt;
   SnapToGround(dt);
  }
  bool Blocked(Vector3 dir)
  {
   var origin=transform.position+Vector3.up*(kind==DroidKind.Hover?0:.9f);
   int n=Physics.SphereCastNonAlloc(origin,.4f,dir,hits,1.3f,groundMask,QueryTriggerInteraction.Ignore);
   for(int i=0;i<n;i++)
   {
    var c=hits[i].collider;
    if(c.transform.IsChildOf(transform)||c.GetComponentInParent<FeralDroid>()||c.GetComponentInParent<PlayerMotor>())continue;
    if(hits[i].normal.y>.6f)continue; // walkable slope
    return true;
   }
   return false;
  }
  bool CanSee()
  {
   var eye=transform.position+Vector3.up*1.3f;var target=Player.transform.position+Vector3.up*1.2f;
   int n=Physics.RaycastNonAlloc(eye,(target-eye).normalized,hits,Vector3.Distance(eye,target),groundMask,QueryTriggerInteraction.Ignore);
   for(int i=0;i<n;i++){var c=hits[i].collider;if(!c.transform.IsChildOf(transform)&&!c.GetComponentInParent<PlayerMotor>()&&!c.GetComponentInParent<FeralDroid>())return false;}
   return true;
  }
  void Face(Vector3 point,float dt)
  {
   var to=Flat(point-transform.position);if(to.sqrMagnitude<.001f)return;
   transform.rotation=Quaternion.Slerp(transform.rotation,Quaternion.LookRotation(to),1-Mathf.Exp(-turnSpeed*dt));
  }
  void SnapToGround(float dt)
  {
   if(!GroundHeight(transform.position,out float y)){grounded=false;return;}
   grounded=true;groundY=y;
   var p=transform.position;
   if(kind==DroidKind.Hover)p.y=Mathf.Lerp(p.y,y+hoverHeight,1-Mathf.Exp(-4*dt));else p.y=y;
   transform.position=p;
  }
  bool GroundHeight(Vector3 at,out float y)
  {
   y=0;float best=float.MinValue;
   int n=Physics.RaycastNonAlloc(at+Vector3.up*(kind==DroidKind.Hover?1:2.2f),Vector3.down,hits,8,groundMask,QueryTriggerInteraction.Ignore);
   for(int i=0;i<n;i++)
   {
    var c=hits[i].collider;
    if(c.transform.IsChildOf(transform)||c.GetComponentInParent<FeralDroid>()||c.GetComponentInParent<PlayerMotor>())continue;
    if(hits[i].point.y>best)best=hits[i].point.y;
   }
   if(best==float.MinValue)return false;y=best;return true;
  }

  // Hover drones: bob and bank on their own, pull back, then dart at the player.
  void HoverPose(float dt)
  {
   bob+=dt*2.3f;
   var visual=animationSource?animationSource.transform:transform.childCount>0?transform.GetChild(0):null;
   if(!visual)return;
   var local=Quaternion.Inverse(transform.rotation)*velocity;
   visual.localPosition=new Vector3(0,Mathf.Sin(bob)*.08f,0);
   visual.localRotation=Quaternion.Euler(Mathf.Clamp(local.z*6,-20,20),0,Mathf.Clamp(-local.x*8,-20,20));
  }
  void HoverLunge(float dt)
  {
   var to=Flat(Player.transform.position-transform.position);
   float phase=timer/Mathf.Max(.05f,windupSeconds);
   // back off during the tell, then dash through the strike point
   velocity=phase<1?-to.normalized*1.2f:to.normalized*9f;
   if(phase>=1&&to.magnitude<.9f)velocity=Vector3.zero;
   transform.position+=velocity*dt;SnapToGround(dt);
  }

  void Play(AnimationClip clip,float speed)
  {
   if(!animationSource||!clip||animationSource[clip.name]==null)return;
   var state=animationSource[clip.name];state.speed=speed;
   if(!animationSource.IsPlaying(clip.name)||(clip==attack||clip==hit)&&timer==0)
   {
    if(clip==attack||clip==hit){state.wrapMode=WrapMode.ClampForever;state.time=0;}
    animationSource.CrossFade(clip.name,.12f);
   }
  }

  // ------------------------------------------------------------------ presentation (after animation)
  /// Optic glow (the state telegraph), walker foot plants and hover rotors, downwash and motor pitch.
  /// Runs even while a city modal pauses behaviour so the droids never freeze visually.
  void LateUpdate()
  {
   float dt=Time.deltaTime;bool reduced=Session&&Session.reducedMotion;
   Glow(dt,reduced);
   if(kind==DroidKind.Walker)Footsteps(reduced);else Rotors(dt,reduced);
  }
  Color glowNow;
  void Glow(float dt,bool reduced)
  {
   if(glowRenderers==null||glowRenderers.Length==0)return;
   Color target;float rate=10;
   if(State==DroidState.Dead)
   {
    // optics die with a short stutter, then stay dark
    float t=Time.time-deadAt;rate=40;
    target=t<.7f&&!reduced&&Mathf.PerlinNoise(Time.time*28,3.1f)>.45f?glowHostile*.5f:Color.black;
   }
   else if(State==DroidState.Windup)
   {
    // flare builds through the wind-up and peaks as the blow lands
    float p=Mathf.Clamp01(timer/Mathf.Max(.05f,windupSeconds));rate=30;
    target=Color.Lerp(glowHostile,glowWindup,p*p);
    if(!reduced)target*=1+.3f*Mathf.Sin(Time.time*38);
   }
   else target=Hostile?glowHostile:glowCalm;
   glowNow=Color.Lerp(glowNow,target,1-Mathf.Exp(-rate*dt));
   flash=Mathf.MoveTowards(flash,0,dt*4);
   var shown=glowNow+new Color(1,.85f,.7f)*(flash*hitFlash);
   if(Mathf.Abs(shown.r-glowShown.r)+Mathf.Abs(shown.g-glowShown.g)+Mathf.Abs(shown.b-glowShown.b)<.02f)return;
   glowShown=shown;
   if(glowBlock==null)glowBlock=new MaterialPropertyBlock();
   foreach(var r in glowRenderers){if(!r)continue;r.GetPropertyBlock(glowBlock);glowBlock.SetColor(EmissionId,shown);r.SetPropertyBlock(glowBlock);}
  }
  void Footsteps(bool reduced)
  {
   if(feet.Length==0||State==DroidState.Dead)return;
   if(footBase==null||footBase.Length!=feet.Length){footBase=new float[feet.Length];footUp=new bool[feet.Length];for(int i=0;i<feet.Length;i++)footBase[i]=float.MaxValue;}
   bool moving=velocity.sqrMagnitude>.09f;float y0=transform.position.y;
   for(int i=0;i<feet.Length;i++)
   {
    var f=feet[i];if(!f)continue;
    float h=f.position.y-y0;
    footBase[i]=Mathf.Min(footBase[i]+Time.deltaTime*.02f,h); // lowest recent height, slowly forgotten
    if(h>footBase[i]+footLift)footUp[i]=true;
    else if(footUp[i]&&h<footBase[i]+footPlant){footUp[i]=false;if(moving)Plant(f.position,reduced);}
   }
  }
  void Plant(Vector3 at,bool reduced)
  {
   if(footDust)
   {
    var e=new ParticleSystem.EmitParams{position=new Vector3(at.x,transform.position.y+.04f,at.z),applyShapeToPosition=true};
    footDust.Emit(e,reduced?2:6);
   }
   if(voice&&footstepClips.Length>0)
   {
    var c=footstepClips[UnityEngine.Random.Range(0,footstepClips.Length)];
    if(c)voice.PlayOneShot(c,footstepVolume*UnityEngine.Random.Range(.75f,1f));
   }
  }
  void Rotors(float dt,bool reduced)
  {
   bool dead=State==DroidState.Dead;
   float target=dead?0:State==DroidState.Windup?rotorWindupSpeed:rotorSpeed;
   rotorSpin=Mathf.MoveTowards(rotorSpin,target,dt*(dead?700:3500));
   for(int i=0;i<rotors.Length;i++)if(rotors[i])rotors[i].Rotate(0,rotorSpin*dt*(i%2==0?1:-1),0,Space.Self);
   if(motorLoop)
   {
    float idleRatio=Mathf.Clamp01(rotorSpin/Mathf.Max(1,rotorSpeed));
    float rev=Mathf.Clamp01((rotorSpin-rotorSpeed)/Mathf.Max(1,rotorWindupSpeed-rotorSpeed));
    motorLoop.pitch=.4f+.6f*idleRatio+.45f*rev+(Hostile&&!dead?.06f:0);
    motorLoop.volume=idleRatio;
    if(dead&&idleRatio<.02f&&motorLoop.isPlaying)motorLoop.Stop();
   }
   if(downwash)
   {
    var em=downwash.emission;
    float height=transform.position.y-groundY;
    bool on=grounded&&!dead&&height<3.2f;
    em.rateOverTimeMultiplier=on?downwashRate*Mathf.Clamp01(1.45f-height*.35f)*(reduced?.4f:1):0;
    if(on)downwash.transform.position=new Vector3(transform.position.x,groundY+.05f,transform.position.z);
   }
  }

  void OnDamaged(float amount,Vector3 point)
  {
   if(amount<=0)return;
   flash=1;
   if(sparks){sparks.transform.position=point;sparks.Emit(10);}
   if(voice&&hitClip)voice.PlayOneShot(hitClip,.8f);
   if(!Health.Alive)return;
   if(State==DroidState.Idle||State==DroidState.Returning||State==DroidState.Alert)SetState(DroidState.Chase);
   if(Time.time>=staggerReady&&State!=DroidState.Windup)
   {
    staggerReady=Time.time+staggerImmunity;SetState(DroidState.Stagger);Play(hit,1.4f);
    if(Player)transform.position+=Flat(transform.position-Player.transform.position).normalized*.25f;
   }
  }
  void OnDied()
  {
   SetState(DroidState.Dead);velocity=Vector3.zero;deadAt=Time.time;
   if(voice&&deathClip)voice.PlayOneShot(deathClip);
   if(eyeLight)eyeLight.intensity=0;
   if(sparks)sparks.Emit(30);
   if(smoke)smoke.Play();
   if(kind==DroidKind.Hover&&body)
   {
    body.isKinematic=false;body.useGravity=true;
    body.AddForce(Vector3.up*1.5f+UnityEngine.Random.insideUnitSphere,ForceMode.VelocityChange);
    body.AddTorque(UnityEngine.Random.insideUnitSphere*4,ForceMode.VelocityChange);
   }
   else if(death&&animationSource){var s=animationSource[death.name];s.wrapMode=WrapMode.ClampForever;s.speed=1;animationSource.CrossFade(death.name,.1f);}
   // keep blocking the player until it sinks, but no longer as a target
   Killed?.Invoke(this);
   Invoke(nameof(Sink),corpseSeconds);
  }
  void Sink(){if(State==DroidState.Dead){if(smoke)smoke.Stop();gameObject.SetActive(false);}}
  static Vector3 Flat(Vector3 v){v.y=0;return v;}
  void OnDestroy(){if(Health){Health.Damaged-=OnDamaged;Health.Died-=OnDied;}}
 }
}
