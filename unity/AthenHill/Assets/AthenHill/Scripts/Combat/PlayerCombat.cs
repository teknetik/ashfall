using System;
using UnityEngine;
namespace AthenHill
{
 /// The player's nanite-fed scrap pistol, vitality and knock-down/respawn.
 /// Controls: 7 draws/holsters; hold right mouse to aim over the shoulder, then left click fires; F fires from the hip.
 /// Wardens keep weapons holstered inside the walls, so the pistol only draws in the Outer Berms (x below City Edge X).
 [RequireComponent(typeof(Health))]
 public class PlayerCombat:MonoBehaviour
 {
  public GameSession session;
  public GameInput input;
  public PlayerMotor motor;
  public FollowCamera follow;
  public Camera view;
  [Tooltip("Where a Warden patrol returns the player after being knocked down in the Berms.")]
  public Transform respawnPoint;
  [Header("Scrap pistol")]
  public bool hasPistol;
  [Min(1)]public float damage=34,range=70;
  [Min(.05f)]public float fireInterval=.28f;
  [Min(0)]public float nanoMax=100,nanoPerShot=9,nanoRegen=30,nanoRegenDelay=.6f;
  [Range(0,15)]public float aimAssistDegrees=3.5f;
  [Range(.1f,1)]public float aimMoveScale=.62f;
  [Tooltip("The pistol is holstered while the player stands east of this X (inside Ward's walls).")]
  public float cityEdgeX=-58.3f;
  [Tooltip("Pistol model in the colonist's right hand, shown while drawn.")]
  public GameObject heldPistol;
  public Transform muzzlePoint;
  [Tooltip("Muzzle position relative to the colonist when no held pistol is shown.")]
  public Vector3 muzzleOffset=new Vector3(.3f,1.36f,.62f);
  public LayerMask shotMask=~(1<<8);
  [Header("Presentation")]
  public AudioSource audioSource;
  public AudioClip shotClip,emptyClip,hurtClip,drawClip;
  [Header("Layered shot (mechanical snap + nano crack/thump + desert tail)")]
  [Tooltip("When layers are set they replace shotClip; one variant of each layer is combined per shot, never repeating.")]
  public AudioClip[] shotMech=new AudioClip[0],shotBody=new AudioClip[0],shotTail=new AudioClip[0];
  public AudioClip[] emptyClips=new AudioClip[0],drawClips=new AudioClip[0],holsterClips=new AudioClip[0];
  [Range(0,1.5f)]public float mechGain=.55f,bodyGain=.69f,tailGain=.37f;
  [Tooltip("First person / aiming down sights: the mechanism is closer and the tail drier.")]
  [Range(0,2)]public float closeMechScale=1.2f,closeTailScale=.7f;
  [Tooltip("Optional wide 2D source for the tail so its pitch is not tied to the transient.")]
  public AudioSource tailSource;
  public LineRenderer tracer;
  [Tooltip("First-person arms and pistol; when visible, shots start at its muzzle (it plays its own flash and recoil).")]
  public FirstPersonViewModel viewModel;
  public MuzzleFlash thirdPersonFlash;
  public Light muzzleLight;
  public ParticleSystem impactSparks;
  [Min(0)]public float tracerSeconds=.05f;
  public Health Health {get;private set;}
  public bool Armed {get;private set;}
  public bool Aiming {get;private set;}
  public float Nano {get;private set;}
  public bool InBerms=>transform.position.x<cityEdgeX;
  public int ShotsFired {get;private set;}
  public int Hits {get;private set;}
  public int Downs {get;private set;}
  public float LastShotTime {get;private set;}=-99;
  [Header("Camera recoil")]
  public float recoilDegreesPerPoint=.05f,recoilRecoverFraction=.5f,recoilRecoverSeconds=.18f;
  public float RecoilStat=>session?session.GetComponent<CraftingSession>()?.Model?.RecoilStat??38:38;
  public float RecoilScale=>RecoilStat/38f;
  public float LastKickDegrees {get;private set;}
  public event Action ShotFired;
  /// Hit marker: (target, killed).
  public event Action<Health,bool> TargetHit;
  public event Action<float> Hurt;
  public event Action Downed;
  float nextFire,faceUntil,tracerOff,emptyNotice;
  void Awake(){Health=GetComponent<Health>();Nano=nanoMax;Health.Damaged+=OnDamaged;Health.Died+=OnDied;}
  void Start()
  {
   if(!view&&follow)view=follow.GetComponent<Camera>();
   var cityAudio=session?FindAnyObjectByType<CityAudio>():null;
   // Weapon sounds belong to the SFX group (the footstep source's group); fall back to the confirmation group.
   var group=cityAudio&&cityAudio.steps&&cityAudio.steps.outputAudioMixerGroup?cityAudio.steps.outputAudioMixerGroup:cityAudio&&cityAudio.confirmation?cityAudio.confirmation.outputAudioMixerGroup:null;
   if(group){if(audioSource)audioSource.outputAudioMixerGroup=group;if(tailSource)tailSource.outputAudioMixerGroup=group;}
   if(tracer)tracer.enabled=false;if(muzzleLight)muzzleLight.enabled=false;
   if(heldPistol)heldPistol.SetActive(false);
  }
  void OnDestroy(){if(Health){Health.Damaged-=OnDamaged;Health.Died-=OnDied;}ReleaseCursor();}
  public void GivePistol(){hasPistol=true;Nano=nanoMax;}
  public void ToggleDraw()
  {
   if(session.State!=CityState.Play)return;
   if(!hasPistol){session.Notify("You are not carrying a weapon.");return;}
   if(!Armed&&!InBerms){session.Notify("Wardens keep weapons holstered inside the walls.","Ward");return;}
   Armed=!Armed;
   if(audioSource)
   {
    var clips=Armed?drawClips:holsterClips;
    var clip=clips!=null&&clips.Length>0?Pick(clips,ref lastFoley):Armed?drawClip:null;
    if(clip)audioSource.PlayOneShot(clip,.8f);
   }
   session.Notify(Armed?"Scrap pistol drawn. Hold right mouse to aim.":"Scrap pistol holstered.");
  }
  void Update()
  {
   if(tracer&&tracer.enabled&&Time.time>tracerOff){tracer.enabled=false;if(muzzleLight)muzzleLight.enabled=false;}
   if(Time.time-LastShotTime>nanoRegenDelay)Nano=Mathf.Min(nanoMax,Nano+nanoRegen*Time.deltaTime);
   bool play=session.State==CityState.Play;
   if(play&&input.Pressed("Slot7"))ToggleDraw();
   if(Armed&&!InBerms){Armed=false;session.Notify("Back inside the walls. Scrap pistol holstered.","Ward");}
   if(heldPistol&&heldPistol.activeSelf!=Armed)heldPistol.SetActive(Armed);
   Aiming=play&&Armed&&input.Held("Aim");
   if(follow)follow.aimMode=Aiming;
   if(Aiming)Cursor.lockState=CursorLockMode.Locked;else ReleaseCursor();
   motor.SpeedScale=Aiming?aimMoveScale:1;
   motor.FaceView=Aiming||Armed&&Time.time<faceUntil;
   if(view)motor.FaceYaw=view.transform.eulerAngles.y;
   if(!play||!Armed)return;
   if(input.Pressed("Fire")||Aiming&&input.Pressed("Orbit"))Fire();
  }
  void ReleaseCursor(){if(Cursor.lockState==CursorLockMode.Locked)Cursor.lockState=CursorLockMode.None;}
  public void Fire()
  {
   if(!Armed||Time.time<nextFire||!Health.Alive)return;
   if(Nano<nanoPerShot)
   {
    var empty=emptyClips!=null&&emptyClips.Length>0?Pick(emptyClips,ref lastEmpty):emptyClip;
    if(audioSource&&empty)audioSource.PlayOneShot(empty,.7f);
    if(Time.time>emptyNotice){emptyNotice=Time.time+3;session.Notify("Nano charge depleted. Hold fire to let it refill.");}
    nextFire=Time.time+fireInterval;return;
   }
   nextFire=Time.time+fireInterval;Nano-=nanoPerShot;ShotsFired++;LastShotTime=Time.time;faceUntil=Time.time+.7f;
   var cam=view.transform;
   // Start past the boom so geometry behind the player cannot block a shot.
   float skip=follow?follow.Distance:0;
   var origin=cam.position+cam.forward*skip;
   Vector3 end=origin+cam.forward*range;Health target=null;
   if(Physics.Raycast(origin,cam.forward,out var hit,range,shotMask,QueryTriggerInteraction.Ignore))
   {end=hit.point;target=hit.collider.GetComponentInParent<Health>();if(target==Health)target=null;}
   if(!target||!target.Alive)
   {
    var assisted=AimAssist(origin,cam.forward,hit.collider?hit.distance:range);
    if(assisted){target=assisted;end=assisted.AimPoint;}
   }
   // The shot uses the pre-kick view. LateUpdate applies recovery before writing the next view.
   LastKickDegrees=RecoilStat*recoilDegreesPerPoint;
   if(follow)follow.ApplyShotKick(LastKickDegrees,recoilRecoverFraction,recoilRecoverSeconds);
   ShotFired?.Invoke();
   bool firstPerson=viewModel&&viewModel.Visible&&viewModel.muzzle;
   var muzzle=firstPerson?viewModel.muzzle.position:muzzlePoint&&heldPistol&&heldPistol.activeInHierarchy?muzzlePoint.position:motor.visual?motor.visual.TransformPoint(muzzleOffset):transform.TransformPoint(muzzleOffset);
   if(!firstPerson&&thirdPersonFlash)thirdPersonFlash.Fire();
   if(tracer){tracer.enabled=true;tracer.SetPosition(0,muzzle);tracer.SetPosition(1,end);tracerOff=Time.time+tracerSeconds;}
   if(muzzleLight){muzzleLight.transform.position=muzzle;muzzleLight.enabled=true;}
   PlayShot();
   if(impactSparks){impactSparks.transform.position=end;impactSparks.transform.forward=(muzzle-end).normalized;impactSparks.Emit(target?14:6);}
   if(target&&target.Alive)
   {
    Hits++;target.Damage(damage,end);
    TargetHit?.Invoke(target,!target.Alive);
   }
  }
  int lastMech=-1,lastBody=-1,lastTail=-1,lastEmpty=-1,lastFoley=-1;
  static AudioClip Pick(AudioClip[] clips,ref int last)
  {
   int i=UnityEngine.Random.Range(0,clips.Length);
   if(clips.Length>1&&i==last)i=(i+1+UnityEngine.Random.Range(0,clips.Length-1))%clips.Length;
   last=i;return clips[i];
  }
  public bool LayeredShot=>audioSource&&shotBody!=null&&shotBody.Length>0;
  void PlayShot()
  {
   if(!audioSource)return;
   if(!LayeredShot){if(shotClip){audioSource.pitch=UnityEngine.Random.Range(.95f,1.05f);audioSource.PlayOneShot(shotClip);}return;}
   bool close=Aiming||follow&&follow.FirstPerson;
   audioSource.pitch=UnityEngine.Random.Range(.97f,1.03f);
   if(shotMech.Length>0)audioSource.PlayOneShot(Pick(shotMech,ref lastMech),mechGain*(close?closeMechScale:1));
   audioSource.PlayOneShot(Pick(shotBody,ref lastBody),bodyGain);
   if(shotTail.Length>0)
   {
    var tail=tailSource?tailSource:audioSource;
    if(tailSource)tailSource.pitch=UnityEngine.Random.Range(.96f,1.04f);
    tail.PlayOneShot(Pick(shotTail,ref lastTail),tailGain*(close?closeTailScale:1));
   }
  }
  Health AimAssist(Vector3 origin,Vector3 forward,float maxDistance)
  {
   Health best=null;float bestAngle=aimAssistDegrees;
   foreach(var h in Health.Targets)
   {
    if(!h||!h.Alive||h==Health)continue;
    var to=h.AimPoint-origin;float d=to.magnitude;
    if(d>range||d>maxDistance+2.5f)continue;
    float angle=Vector3.Angle(forward,to);
    if(angle>=bestAngle)continue;
    if(Physics.Linecast(origin,h.AimPoint,out var block,shotMask,QueryTriggerInteraction.Ignore)&&block.collider.GetComponentInParent<Health>()!=h)continue;
    best=h;bestAngle=angle;
   }
   return best;
  }
  void OnDamaged(float amount,Vector3 from)
  {
   if(audioSource&&hurtClip)audioSource.PlayOneShot(hurtClip,.9f);
   Hurt?.Invoke(amount);
  }
  void OnDied()
  {
   Downs++;Armed=false;
   session.Notify("You go down in the dust. A Warden patrol drags you back to the post.","Outer Berms");
   if(respawnPoint){motor.Teleport(respawnPoint.position);motor.visual.rotation=respawnPoint.rotation;}
   Health.Restore();Nano=nanoMax;
   Downed?.Invoke();
  }
 }
}
