using System;
using UnityEngine;
namespace AthenHill
{
 /// The player's nanite-fed scrap pistol and field rifle, vitality and knock-down/respawn.
 /// Controls: 7 draws/holsters the sidearm, 8 the rifle (drawing one holsters the other); hold right mouse to aim over
 /// the shoulder, then left click fires; F fires from the hip. Automatic weapons (the rifle) fire while the button is held.
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
  [Tooltip("Fallback numbers used only when no Ward crafting loadout is bound. The authoritative base stats and mods live in Data/Crafting/WardCrafting.asset.")]
  [Min(1)]public float damage=34,range=30;
  [Tooltip("Fallback shot spread in degrees (WeaponBallistics narrows it by accuracy, aiming and movement).")]
  [Min(0)]public float spread=4;
  [Min(.05f)]public float fireInterval=.28f;
  [Min(0)]public float nanoMax=100,nanoPerShot=9,nanoRegen=30,recoil=38;
  [Range(0,15)]public float aimAssistDegrees=3.5f;
  [Tooltip("Seconds after a shot before nano charge refills. Not a weapon stat.")]
  [Min(0)]public float nanoRegenDelay=.6f;
  [Range(.1f,1)]public float aimMoveScale=.62f;
  [Tooltip("The pistol is holstered while the player stands east of this X (inside Ward's walls).")]
  public float cityEdgeX=-58.3f;
  [Tooltip("Pistol model in the colonist's right hand, shown while drawn.")]
  public GameObject heldPistol;
  public Transform muzzlePoint;
  [Header("Field rifle")]
  [Tooltip("Rifle model in the colonist's hands, shown while the primary weapon is drawn (2 Oct 2026).")]
  public GameObject heldRifle;
  public Transform rifleMuzzle;
  [Tooltip("Weapon definition ids that keep firing while the fire button is held.")]
  public string[] automaticWeaponIds={"weapon_field_rifle"};
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
  [Tooltip("First-person view model for the field rifle (3 Oct 2026).")]public FirstPersonViewModel rifleViewModel;
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
  /// Droid kills credited to the player's shots, and the experience they earned (2 Oct 2026).
  public int Kills {get;private set;}
  public int ExperienceEarned {get;private set;}
  public ThreatTier LastKillTier {get;private set;}=ThreatTier.Normal;
  /// The last landed shot: damage dealt after falloff and armour, its distance and the cone it was fired with.
  public float LastHitDamage {get;private set;}
  public float LastHitDistance {get;private set;}
  public float LastCone {get;private set;}
  public float LastShotTime {get;private set;}=-99;
  [Header("Camera recoil")]
  public float recoilDegreesPerPoint=.05f,recoilRecoverFraction=.5f,recoilRecoverSeconds=.18f;
  /// Effective weapon stats from the fitted loadout (cached; recomputed only when the loadout changes).
  public WeaponStats Stats {get;private set;}
  /// The unmodified weapon: recoil presentation scales relative to its base recoil.
  public WeaponStats BaseStats {get;private set;}
  public WeaponLoadout Loadout {get;private set;}
  public CharacterModel Character {get;private set;}
  public CraftingModel Crafting {get;private set;}
  public string ActiveSlot {get;private set;}="secondary";
  /// A primary weapon (the field rifle) is equipped and has a crafting definition, so 8 can draw it.
  public bool HasRifle=>Character!=null&&Crafting!=null&&Crafting.FindWeapon(Character.Equipped("primary"))!=null;
  public bool RifleActive=>ActiveSlot=="primary";
  /// The held model of the active slot (rifle or pistol), shown while drawn.
  public GameObject HeldWeapon=>RifleActive?heldRifle:heldPistol;
  public Transform HeldMuzzle=>RifleActive?rifleMuzzle:muzzlePoint;
  public bool Automatic=>Loadout!=null&&automaticWeaponIds!=null&&Array.IndexOf(automaticWeaponIds,Loadout.WeaponId)>=0;
  public float RecoilStat=>Stats.recoil;
  public float RecoilScale=>BaseStats.recoil>0?Stats.recoil/BaseStats.recoil:1;
  public float LastKickDegrees {get;private set;}
  public event Action ShotFired;
  /// Hit marker: (target, killed).
  public event Action<Health,bool> TargetHit;
  public event Action<float> Hurt;
  /// Damage with where it came from (the attacker's position), for the HUD's direction indicator.
  public event Action<float,Vector3> HurtFrom;
  public event Action Downed;
  /// Experience awarded for a kill: (amount, tier, levelled up). Easy kills raise it with 0.
  public event Action<int,ThreatTier,bool> ExperienceAwarded;
  float nextFire,faceUntil,tracerOff,emptyNotice;
  void Awake(){Health=GetComponent<Health>();ApplyLoadout();Nano=Stats.nanoMax;Health.Damaged+=OnDamaged;Health.Died+=OnDied;}
  /// CraftingSession binds the pistol's loadout once its model exists. Null returns to the serialized fallback.
  public void BindLoadout(WeaponLoadout loadout)
  {
   if(Loadout!=null)Loadout.Changed-=ApplyLoadout;
   Loadout=loadout;
   if(Loadout!=null)Loadout.Changed+=ApplyLoadout;
   ApplyLoadout();
  }
  public void BindCharacter(CharacterModel character)
  {
   if(Character!=null)Character.Changed-=OnCharacterChanged;
   Character=character;
   if(Character!=null)Character.Changed+=OnCharacterChanged;
   if(Health)Health.AdjustIncomingDamage=Character!=null?MitigateDamage:null;
   OnCharacterChanged();
  }
  float MitigateDamage(float incoming)
   =>ComputePhysicalDamage(Character,incoming);
  public static float ComputePhysicalDamage(CharacterModel character,float incoming)
  {
   if(character==null)return incoming;
   float armour=Mathf.Max(0,character.Stat("armour"));
   float absorbed=armour*Mathf.Max(0,character.Data.armourAbsorptionPerPoint);
   float resistance=Mathf.Clamp01(character.Stat("physicalResistance"));
   return Mathf.Max(0,incoming*(1-resistance)-absorbed);
  }
  public void BindCraftingModel(CraftingModel model)
  {
   Crafting=model;
   if(model==null){BindLoadout(null);return;}
   RefreshEquippedWeapon();
  }
  public bool SelectWeapon(string slot)
  {
   if(slot!="primary"&&slot!="secondary"||Character==null||Crafting==null)return false;
   var itemId=Character.Equipped(slot);
   var weapon=Crafting.FindWeapon(itemId);
   var loadout=weapon!=null?Crafting.GetLoadout(weapon.id):null;
   if(loadout==null)return false;
   if(ActiveSlot!=slot)Armed=false;
   ActiveSlot=slot;BindLoadout(loadout);return true;
  }
  void RefreshEquippedWeapon()
  {
   if(SelectWeapon(ActiveSlot))return;
   if(SelectWeapon("secondary"))return;
   if(SelectWeapon("primary"))return;
   Armed=false;
   if(Crafting!=null)BindLoadout(Crafting.Loadout);
  }
  void OnCharacterChanged()
  {
   if(Health&&Character!=null)Health.SetMaximum(Character.Stat("health"));
   if(Crafting!=null)RefreshEquippedWeapon();
   else ApplyLoadout();
  }
  void ApplyLoadout()
  {
   BaseStats=Loadout!=null?Loadout.Base:new WeaponStats{damage=damage,fireInterval=fireInterval,range=range,recoil=recoil,nanoMax=nanoMax,nanoPerShot=nanoPerShot,nanoRegen=nanoRegen,aimAssist=aimAssistDegrees,spread=spread};
   Stats=Loadout!=null?Loadout.WithCharacter(Character):WeaponStatPipeline.ApplyCharacter(BaseStats,Character);
   if(Nano>Stats.nanoMax)Nano=Stats.nanoMax;
   StatsChanged?.Invoke();
  }
  /// Raised when the effective stats change (a mod fitted or removed, or a loadout bound).
  public event Action StatsChanged;
  /// Save restore: the pistol is carried (and charged) exactly when the save says so.
  public void RestorePistol(bool carried)
  {
   hasPistol=carried;Armed=false;
   if(carried&&Character!=null&&Character.Equipped("secondary")!="scrap_pistol"&&session&&session.Shop.Quantity("scrap_pistol")==0)
   {
    if(!Character.TryGrantEquipped("scrap_pistol","secondary",out var reason))Debug.LogWarning("Pistol restore could not grant equipment: "+reason);
   }
   Nano=Stats.nanoMax;
  }
  void Start()
  {
   if(!view&&follow)view=follow.GetComponent<Camera>();
   var cityAudio=session?FindAnyObjectByType<CityAudio>():null;
   // Weapon sounds belong to the SFX group (the footstep source's group); fall back to the confirmation group.
   var group=cityAudio&&cityAudio.steps&&cityAudio.steps.outputAudioMixerGroup?cityAudio.steps.outputAudioMixerGroup:cityAudio&&cityAudio.confirmation?cityAudio.confirmation.outputAudioMixerGroup:null;
   if(group){if(audioSource)audioSource.outputAudioMixerGroup=group;if(tailSource)tailSource.outputAudioMixerGroup=group;}
   if(tracer)tracer.enabled=false;if(muzzleLight)muzzleLight.enabled=false;
   if(heldPistol)heldPistol.SetActive(false);
   if(heldRifle)heldRifle.SetActive(false);
  }
  void OnDestroy(){if(Health){Health.Damaged-=OnDamaged;Health.Died-=OnDied;}if(Loadout!=null)Loadout.Changed-=ApplyLoadout;if(Character!=null)Character.Changed-=OnCharacterChanged;ReleaseCursor();}
  public void GivePistol()
  {
   if(Character!=null&&Character.Equipped("secondary")!="scrap_pistol"&&session&&session.Shop.Quantity("scrap_pistol")==0)
   {
    if(!Character.TryGrantEquipped("scrap_pistol","secondary",out var reason))Debug.LogWarning("Pistol reward could not grant equipment: "+reason);
   }
   hasPistol=true;Nano=Stats.nanoMax;
  }
  public void ToggleDraw()=>ToggleDraw("secondary");
  /// 7 draws or holsters the sidearm, 8 the rifle. Drawing the other slot's weapon switches to it (holstering this one).
  public void ToggleDraw(string slot)
  {
   if(session.State!=CityState.Play)return;
   if(!hasPistol){session.Notify("Complete the field primer before drawing a weapon.");return;}
   if(Character!=null&&Character.Equipped(slot)==null){session.Notify(slot=="primary"?"No rifle equipped. Fit one in your loadout first.":"Equip a weapon in your loadout first.");return;}
   if(!Armed&&!InBerms){session.Notify("Wardens keep weapons holstered inside the walls.","Ward");return;}
   if(slot!=ActiveSlot)
   {
    if(!SelectWeapon(slot)){session.Notify(slot=="primary"?"That rifle has no field pattern yet.":"That weapon has no field pattern yet.");return;}
    if(!InBerms)return;
    Armed=true;
   }
   else Armed=!Armed;
   if(audioSource)
   {
    var clips=Armed?drawClips:holsterClips;
    var clip=clips!=null&&clips.Length>0?Pick(clips,ref lastFoley):Armed?drawClip:null;
    if(clip)audioSource.PlayOneShot(clip,.8f);
   }
   string name=RifleActive?"Field rifle":"Scrap pistol";
   session.Notify(Armed?(RifleActive?"Field rifle drawn. Hold right mouse to aim; hold fire for bursts.":"Scrap pistol drawn. Hold right mouse to aim."):name+" holstered.");
  }
  void Update()
  {
   if(tracer&&tracer.enabled&&Time.time>tracerOff){tracer.enabled=false;if(muzzleLight)muzzleLight.enabled=false;}
   if(Time.time-LastShotTime>nanoRegenDelay)Nano=Mathf.Min(Stats.nanoMax,Nano+Stats.nanoRegen*Time.deltaTime);
   bool play=session.State==CityState.Play;
   if(play&&input.Pressed("Slot7"))ToggleDraw("secondary");
   if(play&&input.Pressed("Slot8"))ToggleDraw("primary");
   if(Armed&&!InBerms){Armed=false;session.Notify(RifleActive?"Back inside the walls. Field rifle holstered.":"Back inside the walls. Scrap pistol holstered.","Ward");}
   bool showPistol=Armed&&!RifleActive,showRifle=Armed&&RifleActive;
   if(heldPistol&&heldPistol.activeSelf!=showPistol)heldPistol.SetActive(showPistol);
   if(heldRifle&&heldRifle.activeSelf!=showRifle)heldRifle.SetActive(showRifle);
   Aiming=play&&Armed&&input.Held("Aim");
   if(follow)follow.aimMode=Aiming;
   if(Aiming)Cursor.lockState=CursorLockMode.Locked;else ReleaseCursor();
   motor.SpeedScale=(Aiming?aimMoveScale:1)*(Character!=null?Character.Stat("movementSpeed"):1);
   motor.FaceView=Aiming||Armed&&Time.time<faceUntil;
   if(view)motor.FaceYaw=view.transform.eulerAngles.y;
   if(!play||!Armed)return;
   if(input.Pressed("Fire")||Aiming&&input.Pressed("Orbit")||Automatic&&(input.Held("Fire")||Aiming&&input.Held("Orbit")))Fire();
  }
  void ReleaseCursor(){if(Cursor.lockState==CursorLockMode.Locked)Cursor.lockState=CursorLockMode.None;}
  public void Fire()
  {
   if(!Armed||Time.time<nextFire||!Health.Alive)return;
   var stats=Stats;
   if(Nano<stats.nanoPerShot)
   {
    var empty=emptyClips!=null&&emptyClips.Length>0?Pick(emptyClips,ref lastEmpty):emptyClip;
    if(audioSource&&empty)audioSource.PlayOneShot(empty,.7f);
    if(Time.time>emptyNotice){emptyNotice=Time.time+3;session.Notify("Nano charge depleted. Hold fire to let it refill.");}
    nextFire=Time.time+stats.fireInterval;return;
   }
   nextFire=Time.time+stats.fireInterval;Nano-=stats.nanoPerShot;ShotsFired++;LastShotTime=Time.time;faceUntil=Time.time+.7f;
   var cam=view.transform;
   // Start past the boom so geometry behind the player cannot block a shot.
   float skip=follow?follow.Distance:0;
   var origin=cam.position+cam.forward*skip;
   float range=stats.range;
   // Cone: weapon spread narrowed by effective accuracy (weapon + character + skill), halved while aiming, widened on the move.
   bool moving=motor&&motor.Speed>WeaponBallistics.MovingSpeed;
   float cone=WeaponBallistics.Cone(stats.spread,stats.accuracy,Aiming,moving);LastCone=cone;
   Vector2 scatter=UnityEngine.Random.insideUnitCircle*cone;
   Vector3 direction=(Quaternion.AngleAxis(scatter.x,cam.up)*Quaternion.AngleAxis(-scatter.y,cam.right)*cam.forward).normalized;
   Vector3 end=origin+direction*range;Health target=null;
   if(Physics.Raycast(origin,direction,out var hit,range,shotMask,QueryTriggerInteraction.Ignore))
   {end=hit.point;target=hit.collider.GetComponentInParent<Health>();if(target==Health)target=null;}
   if(!target||!target.Alive)
   {
    var assisted=AimAssist(origin,direction,hit.collider?hit.distance:range,range,stats.aimAssist);
    if(assisted){target=assisted;end=assisted.AimPoint;}
   }
   // The shot uses the pre-kick view. LateUpdate applies recovery before writing the next view.
   LastKickDegrees=stats.recoil*recoilDegreesPerPoint;
   if(follow)follow.ApplyShotKick(LastKickDegrees,recoilRecoverFraction,recoilRecoverSeconds);
   ShotFired?.Invoke();
   var vm=RifleActive?rifleViewModel:viewModel;
   bool firstPerson=vm&&vm.Visible&&vm.muzzle;
   var held=HeldWeapon;var heldMuzzle=HeldMuzzle;
   var muzzle=firstPerson?vm.muzzle.position:heldMuzzle&&held&&held.activeInHierarchy?heldMuzzle.position:motor.visual?motor.visual.TransformPoint(muzzleOffset):transform.TransformPoint(muzzleOffset);
   if(!firstPerson&&thirdPersonFlash)thirdPersonFlash.Fire();
   if(tracer){tracer.enabled=true;tracer.SetPosition(0,muzzle);tracer.SetPosition(1,end);tracerOff=Time.time+tracerSeconds;}
   if(muzzleLight){muzzleLight.transform.position=muzzle;muzzleLight.enabled=true;}
   PlayShot();
   if(impactSparks){impactSparks.transform.position=end;impactSparks.transform.forward=(muzzle-end).normalized;impactSparks.Emit(target?14:6);}
   if(target&&target.Alive)
   {
    Hits++;
    bool critical=stats.criticalChance>0&&UnityEngine.Random.value<Mathf.Clamp01(stats.criticalChance/100);
    float hitDamage=stats.damage*(critical?Mathf.Max(1,stats.criticalMultiplier):1);
    // Range falloff from the colonist to the hit, then the droid's flat armour against the weapon's penetration.
    float distance=Vector3.Distance(transform.position,end);
    hitDamage*=WeaponBallistics.Falloff(distance,range);
    var threat=target.GetComponent<DroidThreat>();
    if(threat)hitDamage=WeaponBallistics.ArmourReduced(hitDamage,threat.armour,stats.armourPenetration);
    LastHitDamage=hitDamage;LastHitDistance=distance;
    target.Damage(hitDamage,end);
    bool killed=!target.Alive;
    TargetHit?.Invoke(target,killed);
    if(killed)AwardKill(target);
   }
  }
  /// A droid put down by the player's shot: experience by its threat tier (DroidThreat), levelling the character.
  void AwardKill(Health target)
  {
   var droid=target.GetComponent<FeralDroid>();
   if(!droid)return;
   Kills++;
   var threat=target.GetComponent<DroidThreat>();
   var tier=DroidThreat.Tier(droid,this);LastKillTier=tier;
   int amount=DroidThreat.AwardFor(threat?threat.experience:DroidThreat.DefaultExperience,tier);
   bool levelled=false;
   if(amount>0&&Character!=null)
   {
    int before=Character.Level;
    if(Character.GrantExperience(amount,out var reason)){ExperienceEarned+=amount;levelled=Character.Level>before;}
    else{Debug.LogWarning("Experience not granted: "+reason);amount=0;}
   }
   else if(Character==null)amount=0;
   ExperienceAwarded?.Invoke(amount,tier,levelled);
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
  Health AimAssist(Vector3 origin,Vector3 forward,float maxDistance,float range,float degrees)
  {
   Health best=null;float bestAngle=degrees;
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
   Hurt?.Invoke(amount);HurtFrom?.Invoke(amount,from);
  }
  void OnDied()
  {
   Downs++;Armed=false;
   // the nearest Warden waystation the player has found, else the gate post
   var station=WardenWaystation.NearestFound(transform.position,respawnPoint?respawnPoint.position:transform.position);
   var point=station&&station.respawnPoint?station.respawnPoint:respawnPoint;
   session.Notify(station?$"You go down in the dust. A Warden patrol drags you back to the {station.displayName.ToLowerInvariant()}.":"You go down in the dust. A Warden patrol drags you back to the post.","Outer Berms");
   if(point){motor.Teleport(point.position);motor.visual.rotation=point.rotation;}
   Health.Restore();Nano=Stats.nanoMax;
   Downed?.Invoke();
  }
 }
}
