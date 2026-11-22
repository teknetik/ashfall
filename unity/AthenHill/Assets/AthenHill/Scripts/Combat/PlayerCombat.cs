using System;
using UnityEngine;
namespace AthenHill
{
 /// The player's nanite-fed scrap pistol and field rifle, vitality and knock-down/respawn.
 /// Controls (5 Oct 2026): hotbar 1 draws/holsters the primary weapon (rifle), 2 the sidearm (drawing one holsters the
 /// other; GameSession's hotbar calls ToggleDraw); hold right mouse to aim over the shoulder; left mouse or F fires,
 /// aiming or not. Automatic weapons (the rifle) fire while the button is held.
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
  [Tooltip("Per-weapon layered sets (19 Nov 2026). The active weapon's set replaces the arrays above; a weapon with no set (the scrap pistol) keeps them.")]
  public WeaponSoundSet[] weaponSounds=new WeaponSoundSet[0];
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
  /// Nano recharge overclock (Field Supply, 5 Oct 2026): until this time the charge refills even while firing, faster.
  public float OverclockUntil {get;private set;}=-1;
  public float OverclockBonus {get;private set;}
  public bool Overclocked=>Time.time<OverclockUntil;
  /// A nano recharge was used: refills the charge at once and overclocks the regulator for seconds (bonus 0.5 = +50 %
  /// regeneration, with no pause after a shot). A longer or stronger overclock replaces a weaker one still running.
  public void Recharge(float nano,float seconds,float bonus)
  {
   Nano=Mathf.Min(Stats.nanoMax,Nano+Mathf.Max(0,nano));
   if(seconds>0)
   {
    if(!Overclocked||Time.time+seconds>OverclockUntil)OverclockUntil=Time.time+seconds;
    OverclockBonus=Overclocked?Mathf.Max(OverclockBonus,bonus):bonus;
    OverclockBonus=Mathf.Max(0,OverclockBonus);
   }
  }
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
  [Header("Handling sounds (Steady Hands bench, 20 Nov 2026; empty until the audio agent's asm.rattle.* / asm.damper.* land)")]
  [Tooltip("A loose grip rattling: on draw, every shot and while moving, when the weapon's Side Kick is at least Rattle Above.")]
  public AudioClip[] rattleClips=new AudioClip[0];
  [Tooltip("One soft tick of a damper settling, after a shot, when the grip slot holds a mod and the weapon is steadier than Rattle Above.")]
  public AudioClip[] damperClips=new AudioClip[0];
  [Min(0)]public float rattleAbove=.5f;
  [Range(0,1.5f)]public float rattleGain=.45f,rattleMoveGain=.22f,damperGain=.35f;
  [Tooltip("Seconds between rattles while walking with a rattling weapon drawn (random in this range).")]
  public Vector2 rattleMoveInterval=new Vector2(.55f,.9f);
  /// Effective weapon stats from the fitted loadout (cached; recomputed only when the loadout changes).
  public WeaponStats Stats {get;private set;}
  /// The unmodified weapon: recoil presentation scales relative to its base recoil.
  public WeaponStats BaseStats {get;private set;}
  public WeaponLoadout Loadout {get;private set;}
  public CharacterModel Character {get;private set;}
  public CraftingModel Crafting {get;private set;}
  public string ActiveSlot {get;private set;}="secondary";
  /// A primary weapon (the field rifle) is equipped and has a crafting definition, so hotbar 1 can draw it.
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
  /// A weapon was drawn, holstered or the trigger pulled (a field repair stops on it).
  public event Action WeaponHandled;
  /// Hit marker: (target, killed).
  public event Action<Health,bool> TargetHit;
  /// Every landed shot with its detail (19 Nov 2026 combat feel: marker variant, critical flash, QA).
  public event Action<CombatHit> HitLanded;
  /// Landed shots that were critical (a weapon critical roll or a weak-point hit), and the weak-point hits alone.
  public int CriticalHits {get;private set;}
  public int WeakPointHits {get;private set;}
  public CombatHit LastHit {get;private set;}
  public event Action<float> Hurt;
  /// Damage with where it came from (the attacker's position), for the HUD's direction indicator.
  public event Action<float,Vector3> HurtFrom;
  /// Ranged ballistic hit while unarmoured in the torso (Milestone 1: stronger HUD flash & exposed indicator).
  public event Action<float,Vector3> ExposedHit;
  public event Action Downed;
  /// Experience awarded for a kill: (amount, tier, levelled up). Easy kills raise it with 0.
  public event Action<int,ThreatTier,bool> ExperienceAwarded;
  /// Phase 2 combat verbs (21 Nov 2026): dodge, shove, EMP disruptor, nano overcharge.
  public event Action Dodged,Shoved,EmpTriggered,OverchargeTriggered;
  /// Field Rifle ammunition selection changed (Milestone 4).
  public event Action<RifleAmmoKind> AmmoChanged;
  public bool HasEyeImplant=>Character!=null&&!string.IsNullOrEmpty(Character.Equipped("implant_eye"));
  public bool OverchargeActive=>Time.time<overchargeUntil;
  public float OverchargeRemaining=>Mathf.Max(0,overchargeUntil-Time.time);
  public float OverchargeCooldownRemaining=>Mathf.Max(0,overchargeReadyAt-Time.time);
  public float EmpCooldownRemaining=>Mathf.Max(0,empReadyAt-Time.time);
  public float ShoveCooldownRemaining=>Mathf.Max(0,shoveReadyAt-Time.time);
  /// Torso armour exposure & ranged ballistic hit tracking (Milestone 1).
  public bool IsExposedToRanged=>BermsBallistics.IsExposedToRanged(Character);
  public bool LastHitWasRanged {get;private set;}
  public bool LastHitWasExposed {get;private set;}
  public int ExposedHits {get;private set;}
  public bool Band2UnarmouredWarned=>band2UnarmouredWarned;
  /// Field Rifle ammo runtime (Milestone 4): Scrap Pistol stays nano-only; rifle cycles Standard / AP / EMP.
  public RifleAmmoKind ActiveAmmo {get;private set;}=RifleAmmoKind.Standard;
  public bool ActiveWeaponUsesAmmo=>Loadout!=null?BermsBallistics.UsesBallisticAmmo(Loadout.WeaponId):RifleActive;
  public string ActiveAmmoItemId=>BermsBallistics.ItemIdFor(ActiveAmmo);
  public int ActiveAmmoCount=>AmmoCount(ActiveAmmo);
  public RifleAmmoKind LastFiredAmmo {get;private set;}=RifleAmmoKind.Standard;
  public bool LastShotConsumedAmmo {get;private set;}
  public int AmmoCount(RifleAmmoKind kind)=>session!=null&&session.Shop!=null?session.Shop.Quantity(BermsBallistics.ItemIdFor(kind)):0;
  public float EffectiveArmourPenetration=>Stats.armourPenetration+(OverchargeActive?CombatVerbs.OverchargeArmourPenBonus:0)+(ActiveWeaponUsesAmmo&&ActiveAmmoCount>0?BermsBallistics.ArmourPenBonusFor(ActiveAmmo):0);
  float nextFire,faceUntil,tracerOff,emptyNotice,jamNotice,shoveReadyAt=-99,empReadyAt=-99,overchargeReadyAt=-99,overchargeUntil=-99;
  bool incomingRangedBallistic,band2UnarmouredWarned;
  // ---- Handling (Steady Hands bench, 20 Nov 2026): rapid-fire heat, side kick and the rattle/damper cues. See WeaponFeel.
  float heat,heatShot=-99,nextRattle,damperAt=-1;int lastRattle=-1,lastDamper=-1;
  /// Rapid-fire heat now (0 = the next shot has the base cone).
  public float Heat=>WeaponFeel.Decay(heat,Time.time-heatShot);
  /// The last shot's sideways camera kick (degrees, signed) and its cone multiplier from heat.
  public float LastSideKick {get;private set;}
  /// World direction of the last shot's ray (after scatter): the order test fire measures the group from it.
  public Vector3 LastShotDirection {get;private set;}=Vector3.forward;
  /// Where the last shot's ray ended (the surface it struck, or its range), before aim assist.
  public Vector3 LastShotEnd {get;private set;}
  public float LastHeatScale {get;private set;}=1;
  /// Seconds the last shot's kick takes to settle (the weapon's recovery stat, or Recoil Recover Seconds).
  public float RecoverySeconds=>Stats.recovery>0?Stats.recovery:recoilRecoverSeconds;
  /// The drawn weapon rattles (its side kick is at least Rattle Above).
  public bool Rattles=>Stats.sideKick>=rattleAbove&&rattleAbove>0;
  void Awake(){Health=GetComponent<Health>();ApplyLoadout();Nano=Stats.nanoMax;Health.AdjustIncomingDamage=MitigateDamage;Health.Damaged+=OnDamaged;Health.Died+=OnDied;}
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
   if(Health)Health.AdjustIncomingDamage=MitigateDamage;
   OnCharacterChanged();
  }
  float MitigateDamage(float incoming)
  {
   if(motor&&motor.DodgeInvulnerable)return 0;
   if(incomingRangedBallistic)return BermsBallistics.ComputeRangedPhysicalDamage(Character,incoming);
   return ComputePhysicalDamage(Character,incoming);
  }
  public static float ComputePhysicalDamage(CharacterModel character,float incoming)
  {
   if(character==null)return incoming;
   float armour=Mathf.Max(0,character.Stat("armour"));
   float absorbed=armour*Mathf.Max(0,character.Data.armourAbsorptionPerPoint);
   float resistance=Mathf.Clamp01(character.Stat("physicalResistance"));
   return Mathf.Max(0,incoming*(1-resistance)-absorbed);
  }
  /// Ranged ballistic mitigation (Milestone 1): unarmoured torso takes 1.35x before physical mitigation.
  public static float ComputeRangedDamage(CharacterModel character,float incoming)
   =>BermsBallistics.ComputeRangedPhysicalDamage(character,incoming);
  /// Entry point used by DroidBolt for direct ranged hits so the unarmoured torso exposure rule applies
  /// specifically to ranged ballistic fire while melee and splash hits keep standard physical mitigation.
  public bool TakeRangedBallisticHit(float incomingDamage,Vector3 from)
  {
   if(!Health)return false;
   incomingRangedBallistic=true;
   try{return Health.Damage(incomingDamage,from);}
   finally{incomingRangedBallistic=false;}
  }
  /// Cycles Field Rifle ammunition between Standard, AP and EMP (Scrap Pistol stays nano-only).
  public RifleAmmoKind CycleAmmo()
  {
   if(!ActiveWeaponUsesAmmo)return RifleAmmoKind.Standard;
   var next=BermsBallistics.NextAmmo(ActiveAmmo,id=>session!=null&&session.Shop!=null?session.Shop.Quantity(id):0);
   ActiveAmmo=next;
   AmmoChanged?.Invoke(ActiveAmmo);
   if(session)
   {
    int count=AmmoCount(ActiveAmmo);
    session.Notify(count>0
     ?$"Rifle ammo: {BermsBallistics.DisplayName(ActiveAmmo)} ({count})."
     :$"Rifle ammo: {BermsBallistics.DisplayName(ActiveAmmo)} (0 in pack — standard fallback).");
   }
   return ActiveAmmo;
  }
  public bool SelectAmmo(RifleAmmoKind kind)
  {
   if(!ActiveWeaponUsesAmmo)return false;
   ActiveAmmo=kind;
   AmmoChanged?.Invoke(ActiveAmmo);
   return true;
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
  void OnDestroy(){if(Health){Health.Damaged-=OnDamaged;Health.Died-=OnDied;}if(Loadout!=null)Loadout.Changed-=ApplyLoadout;if(Character!=null)Character.Changed-=OnCharacterChanged;}
  public void GivePistol()
  {
   if(Character!=null&&Character.Equipped("secondary")!="scrap_pistol"&&session&&session.Shop.Quantity("scrap_pistol")==0)
   {
    if(!Character.TryGrantEquipped("scrap_pistol","secondary",out var reason))Debug.LogWarning("Pistol reward could not grant equipment: "+reason);
   }
   hasPistol=true;Nano=Stats.nanoMax;
  }
  public void ToggleDraw()=>ToggleDraw("secondary");
  /// Hotbar 2 draws or holsters the sidearm, 1 the rifle. Drawing the other slot's weapon switches to it (holstering this one).
  public void ToggleDraw(string slot)
  {
   if(session.State!=CityState.Play)return;
   WeaponHandled?.Invoke();
   if(!hasPistol){session.Notify("Complete the field primer before drawing a weapon.");return;}
   if(Character!=null&&Character.Equipped(slot)==null){session.Notify(slot=="primary"?"No rifle equipped. Fit one in your loadout first.":"Equip a weapon in your loadout first.");return;}
   if(!Armed&&!InBerms){session.Notify("Wardens keep weapons holstered inside the walls.","Ward");return;}
   // 20 Nov 2026 (Steady Hands bench): a weapon taken apart on the bench cannot be drawn until the job is finished or abandoned.
   if(!Armed&&OnBench(slot)){session.Notify(CraftingText.ConditionReason("on_bench",Crafting,Crafting.GetLoadout(Crafting.OpenTicket.weaponId)),"Field Pack");return;}
   if(slot!=ActiveSlot)
   {
    if(!SelectWeapon(slot)){session.Notify(slot=="primary"?"That rifle has no field pattern yet.":"That weapon has no field pattern yet.");return;}
    if(!InBerms)return;
    Armed=true;
   }
   else Armed=!Armed;
   if(audioSource)
   {
    var set=ActiveSoundSet;var own=set!=null?(Armed?set.draw:set.holster):null;
    var clips=own!=null&&own.Length>0?own:Armed?drawClips:holsterClips;
    var clip=clips!=null&&clips.Length>0?Pick(clips,ref lastFoley):Armed?drawClip:null;
    if(clip)audioSource.PlayOneShot(clip,.8f);
    if(Armed&&Rattles)PlayRattle(rattleGain);
   }
   string name=RifleActive?"Field rifle":"Scrap pistol";
   session.Notify(Armed?(RifleActive?"Field rifle drawn. Left mouse fires (hold for bursts); hold right mouse to aim.":"Scrap pistol drawn. Left mouse fires; hold right mouse to aim."):name+" holstered.");
  }
  /// The weapon equipped in this slot is on the bench (an open bench job).
  public bool OnBench(string slot)
  {
   if(Crafting==null||Crafting.OpenTicket==null||Character==null)return false;
   var weapon=Crafting.FindWeapon(Character.Equipped(slot));
   return weapon!=null&&Crafting.OnBench(weapon.id);
  }
  /// Rapid-fire heat back to 0 (QA: a timed string starts cold).
  public void CoolDown(){heat=0;heatShot=-99;}
  /// The bench took the drawn weapon (a job opened on it): holster without the draw/holster notice.
  public void HolsterForBench(){if(!Armed)return;Armed=false;WeaponHandled?.Invoke();}
  void Update()
  {
   if(tracer&&tracer.enabled&&Time.time>tracerOff){tracer.enabled=false;if(muzzleLight)muzzleLight.enabled=false;}
   if(Overclocked)Nano=Mathf.Min(Stats.nanoMax,Nano+Stats.nanoRegen*(1+OverclockBonus)*Time.deltaTime);
   else if(Time.time-LastShotTime>nanoRegenDelay)Nano=Mathf.Min(Stats.nanoMax,Nano+Stats.nanoRegen*Time.deltaTime);
   bool play=session.State==CityState.Play;
   if(Armed&&!InBerms){Armed=false;session.Notify(RifleActive?"Back inside the walls. Field rifle holstered.":"Back inside the walls. Scrap pistol holstered.","Ward");}
   bool showPistol=Armed&&!RifleActive,showRifle=Armed&&RifleActive;
   if(heldPistol&&heldPistol.activeSelf!=showPistol)heldPistol.SetActive(showPistol);
   if(heldRifle&&heldRifle.activeSelf!=showRifle)heldRifle.SetActive(showRifle);
   Aiming=play&&Armed&&input.Held("Aim");
   if(follow)follow.aimMode=Aiming;
   motor.SpeedScale=(Aiming?aimMoveScale:1)*(Character!=null?Character.Stat("movementSpeed"):1);
   motor.FaceView=Aiming||Armed&&Time.time<faceUntil;
   if(view)motor.FaceYaw=view.transform.eulerAngles.y;
   if(damperAt>0&&Time.time>=damperAt){damperAt=-1;if(Armed)PlayDamper();}
   if(play&&Armed&&Rattles&&motor&&motor.Speed>WeaponBallistics.MovingSpeed&&Time.time>=nextRattle)
   {
    nextRattle=Time.time+UnityEngine.Random.Range(rattleMoveInterval.x,Mathf.Max(rattleMoveInterval.x,rattleMoveInterval.y));
    PlayRattle(rattleMoveGain);
   }
   if(!play)return;
   if(Health.Alive&&session&&BermsBallistics.ShouldWarnUnarmouredBand2(transform.position.x,Character,band2UnarmouredWarned))
   {
    band2UnarmouredWarned=true;
    session.Notify("Ossa [Radio]: You're pushing past the Depot with no chest armour — Gunner bolts will drop you fast. Craft a Field Vest at Brann's bench.","Warden Ossa");
   }
   if(input.ConsumeDodge())TryDodge();
   if(!Armed)return;
   if(ActiveWeaponUsesAmmo&&((input&&input.Pressed("CycleAmmo"))||(UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.tKey.wasPressedThisFrame)))CycleAmmo();
   if(input.Pressed("Shove"))TryShove();
   if(input.Pressed("NanoEmp"))TryNanoEmp();
   if(input.Pressed("NanoOvercharge"))TryNanoOvercharge();
   if(input.FirePressed||Automatic&&input.FireHeld)Fire();
  }
  public bool TryDodge()
  {
   if(!motor||!Health.Alive||session.State!=CityState.Play)return false;
   if(InBerms&&Armed&&Nano<CombatVerbs.DodgeNanoCost)
   {
    if(Time.time>emptyNotice){emptyNotice=Time.time+2;session.Notify("Not enough nano charge to dodge.");}
    return false;
   }
   var dir=CombatVerbs.DodgeDirection(input?input.Move:Vector2.zero,view?view.transform.forward:transform.forward);
   if(!motor.TryDodge(dir))return false;
   if(InBerms&&Armed){Nano=Mathf.Max(0,Nano-CombatVerbs.DodgeNanoCost);LastShotTime=Time.time;}
   if(audioSource&&drawClip)audioSource.PlayOneShot(drawClip,.45f);
   Dodged?.Invoke();
   return true;
  }
  public bool TryShove()
  {
   if(!Armed||!InBerms||!Health.Alive||Time.time<shoveReadyAt)return false;
   WeaponHandled?.Invoke();
   shoveReadyAt=Time.time+CombatVerbs.ShoveCooldown;faceUntil=Time.time+.55f;
   var fwd=view?view.transform.forward:transform.forward;
   int hitCount=0;
   foreach(var d in FeralDroid.Active)
   {
    if(!d||!d.Health||!d.Health.Alive||d.State==DroidState.Dead)continue;
    if(!CombatVerbs.InShoveCone(transform.position,fwd,d.transform.position))continue;
    d.ApplyShove(d.transform.position-transform.position,CombatVerbs.ShoveKnockback,CombatVerbs.ShoveStaggerSeconds,CombatVerbs.ShoveDamage);
    hitCount++;
   }
   if(follow)follow.ApplyShotKick(hitCount>0?3.5f:1.8f,.55f,.16f);
   if(audioSource&&drawClip)audioSource.PlayOneShot(drawClip,hitCount>0?.85f:.55f);
   Shoved?.Invoke();
   return true;
  }
  public bool TryNanoEmp()
  {
   if(!Armed||!InBerms||!Health.Alive||Time.time<empReadyAt)return false;
   if(Nano<CombatVerbs.EmpNanoCost)
   {
    if(Time.time>emptyNotice){emptyNotice=Time.time+2;session.Notify("Need 30 nano charge for EMP Disruptor.");}
    return false;
   }
   WeaponHandled?.Invoke();
   Nano-=CombatVerbs.EmpNanoCost;LastShotTime=Time.time;empReadyAt=Time.time+CombatVerbs.EmpCooldown;
   int affected=0;
   foreach(var d in FeralDroid.Active)
   {
    if(!d||!d.Health||!d.Health.Alive||d.State==DroidState.Dead)continue;
    if(!CombatVerbs.InEmpRadius(transform.position,d.transform.position))continue;
    d.ApplyEmp(CombatVerbs.EmpStunSeconds,CombatVerbs.EmpArmourStripFraction,CombatVerbs.EmpArmourStripSeconds);
    affected++;
   }
   if(impactSparks){impactSparks.transform.position=transform.position+Vector3.up*1.1f;impactSparks.Emit(28);}
   if(follow)follow.ApplyShotKick(2.8f,.5f,.22f);
   if(audioSource&&shotClip)audioSource.PlayOneShot(shotClip,.65f);
   session.Notify(affected>0?$"EMP Disruptor pulsed — {affected} droid{(affected==1?"":"s")} stunned and armour stripped.":"EMP Disruptor pulsed (no droids in range).");
   EmpTriggered?.Invoke();
   return true;
  }
  public bool TryNanoOvercharge()
  {
   if(!Armed||!InBerms||!Health.Alive||Time.time<overchargeReadyAt)return false;
   if(Nano<CombatVerbs.OverchargeNanoCost)
   {
    if(Time.time>emptyNotice){emptyNotice=Time.time+2;session.Notify("Need 25 nano charge for Nano Overcharge.");}
    return false;
   }
   WeaponHandled?.Invoke();
   Nano-=CombatVerbs.OverchargeNanoCost;LastShotTime=Time.time;
   float dur=CombatVerbs.OverchargeSeconds(HasEyeImplant);
   overchargeUntil=Time.time+dur;
   overchargeReadyAt=Time.time+CombatVerbs.OverchargeCooldown;
   if(audioSource&&drawClip)audioSource.PlayOneShot(drawClip,.75f);
   session.Notify(HasEyeImplant?$"Nano Overcharge + Optic Suite active ({dur:0} s): +armour pen, +fire rate, wider optic lock.":"Nano Overcharge active (6 s): +armour pen, +fire rate, +20% damage.");
   OverchargeTriggered?.Invoke();
   return true;
  }
  public void Fire()
  {
   if(!Armed||Time.time<nextFire||!Health.Alive)return;
   WeaponHandled?.Invoke();
   var stats=Stats;
   // Condition (20 Nov 2026, Phase 3): a jammed weapon will not fire; a worn one may misfire (nothing fired, no nano spent).
   var condition=Crafting!=null&&Loadout!=null&&Loadout.HasCondition?Crafting.Condition:null;
   if(condition!=null)
   {
    var outcome=WeaponCondition.BeforeShot(Loadout,condition,UnityEngine.Random.value);
    if(outcome!=ShotOutcome.Fire)
    {
     var set=ActiveSoundSet;
     var click=set!=null&&set.empty!=null&&set.empty.Length>0?Pick(set.empty,ref lastEmpty):emptyClips!=null&&emptyClips.Length>0?Pick(emptyClips,ref lastEmpty):emptyClip;
     if(audioSource&&click)audioSource.PlayOneShot(click,.7f);
     if(Time.time>jamNotice)
     {
      jamNotice=Time.time+(outcome==ShotOutcome.Jammed?3:1);
      string weaponName=Loadout.WeaponName;
      session.Notify(outcome==ShotOutcome.Jammed?$"{weaponName} jammed. Repair it with your Field Toolkit in the field pack, or overhaul it at the workbench.":$"{weaponName} misfired. Its condition is low: repair it in the field pack.");
     }
     nextFire=Time.time+stats.fireInterval;return;
    }
   }
   if(Nano<stats.nanoPerShot)
   {
    var set=ActiveSoundSet;
    var empty=set!=null&&set.empty!=null&&set.empty.Length>0?Pick(set.empty,ref lastEmpty):emptyClips!=null&&emptyClips.Length>0?Pick(emptyClips,ref lastEmpty):emptyClip;
    if(audioSource&&empty)audioSource.PlayOneShot(empty,.7f);
    if(Time.time>emptyNotice){emptyNotice=Time.time+3;session.Notify("Nano charge depleted. Hold fire to let it refill.");}
    nextFire=Time.time+stats.fireInterval;return;
   }
   bool overcharged=OverchargeActive;
   RifleAmmoKind shotAmmo=RifleAmmoKind.Standard;
   bool consumedAmmo=false;
   if(ActiveWeaponUsesAmmo)
   {
    Func<string,int> qty=session!=null&&session.Shop!=null?(Func<string,int>)(id=>session.Shop.Quantity(id)):null;
    shotAmmo=BermsBallistics.ResolveActiveAmmo(ActiveAmmo,qty,out bool usingStock);
    if(usingStock&&session!=null&&session.Shop!=null)
    {
     string ammoId=BermsBallistics.ItemIdFor(shotAmmo);
     if(session.Shop.TryApply(new[]{new System.Collections.Generic.KeyValuePair<string,int>(ammoId,-1)},0,out _))
     {
      consumedAmmo=true;
      if(shotAmmo!=ActiveAmmo){ActiveAmmo=shotAmmo;AmmoChanged?.Invoke(ActiveAmmo);}
     }
    }
   }
   LastFiredAmmo=shotAmmo;
   LastShotConsumedAmmo=consumedAmmo;
   float interval=stats.fireInterval*(overcharged?CombatVerbs.OverchargeFireIntervalScale:1f);
   nextFire=Time.time+interval;Nano-=stats.nanoPerShot;ShotsFired++;LastShotTime=Time.time;faceUntil=Time.time+.7f;
   if(condition!=null)Loadout.Wear(Loadout.WearPerShot);
   var cam=view.transform;
   // Start past the boom so geometry behind the player cannot block a shot.
   float skip=follow?follow.Distance:0;
   var origin=cam.position+cam.forward*skip;
   float range=stats.range;
   // Cone: weapon spread narrowed by effective accuracy (weapon + character + skill), halved while aiming, widened on the move.
   bool moving=motor&&motor.Speed>WeaponBallistics.MovingSpeed;
   float cone=WeaponBallistics.Cone(stats.spread,stats.accuracy,Aiming,moving)*(condition!=null?WeaponCondition.SpreadScale(condition,Loadout.Durability):1);
   // Rapid fire (20 Nov 2026): the heat left by earlier shots widens this one; the first shot of a string has the base cone.
   float since=Time.time-heatShot;LastHeatScale=WeaponFeel.ScatterScale(WeaponFeel.Decay(heat,since));cone*=LastHeatScale;
   heat=WeaponFeel.HeatAfterShot(heat,since,stats.scatterGrowth);heatShot=Time.time;
   LastCone=cone;
   Vector2 scatter=UnityEngine.Random.insideUnitCircle*cone;
   Vector3 direction=(Quaternion.AngleAxis(scatter.x,cam.up)*Quaternion.AngleAxis(-scatter.y,cam.right)*cam.forward).normalized;
   LastShotDirection=direction;
   Vector3 end=origin+direction*range;Health target=null;
   if(Physics.Raycast(origin,direction,out var hit,range,shotMask,QueryTriggerInteraction.Ignore))
   {end=hit.point;target=hit.collider.GetComponentInParent<Health>();if(target==Health)target=null;}
   LastShotEnd=end;
   bool direct=target&&target.Alive;
   if(!target||!target.Alive)
   {
    var assisted=AimAssist(origin,direction,hit.collider?hit.distance:range,range,stats.aimAssist);
    if(assisted){target=assisted;end=assisted.AimPoint;}
   }
   // Weak point: the shot's own ray must pass through the zone. An aim-assisted shot only counts when the ray really
   // crossed the optic (it can stand proud of the body collider); assist alone never makes a critical.
   var weak=target&&target.Alive?target.GetComponent<DroidWeakPoint>():null;
   float weakAt=-1;
   float weakScale=CombatVerbs.WeakPointRadiusScale(overcharged,HasEyeImplant);
   bool weakHit=weak&&weak.isActiveAndEnabled&&weak.Test(origin,direction,direct?hit.distance:Vector3.Distance(origin,end),out weakAt,weakScale);
   // The shot uses the pre-kick view. LateUpdate applies recovery before writing the next view.
   LastKickDegrees=stats.recoil*recoilDegreesPerPoint;
   // Handling (20 Nov 2026): a random sideways step, the weapon's own recovery time and one overshoot when that is slow.
   LastSideKick=WeaponFeel.SideKick(stats.sideKick,UnityEngine.Random.value,UnityEngine.Random.value);
   float recover=RecoverySeconds;
   if(follow)follow.ApplyShotKick(LastKickDegrees,LastSideKick,recoilRecoverFraction,recover,WeaponHandlingRules.OvershootFraction(recover));
   if(Rattles)PlayRattle(rattleGain);
   else if(Loadout!=null&&Loadout.Fitted("grip")!=null)damperAt=Time.time+recover*.8f;
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
    float ammoDamageScale=consumedAmmo?BermsBallistics.DamageScaleFor(shotAmmo):1f;
    float hitDamage=stats.damage*(critical?Mathf.Max(1,stats.criticalMultiplier):1)*(overcharged?CombatVerbs.OverchargeDamageScale:1f)*ammoDamageScale;
    // Range falloff from the colonist to the hit, then the droid's flat armour against the weapon's penetration.
    float distance=Vector3.Distance(transform.position,end);
    hitDamage*=WeaponBallistics.Falloff(distance,range);
    var threat=target.GetComponent<DroidThreat>();
    var droid=target.GetComponent<FeralDroid>();
    if(droid&&consumedAmmo&&BermsBallistics.AppliesEmpStrip(shotAmmo))
     droid.ApplyEmp(BermsBallistics.EmpRoundStunSeconds,BermsBallistics.EmpRoundStripFraction,BermsBallistics.EmpRoundStripSeconds);
    if(threat)
    {
     float effectiveArmour=droid?CombatVerbs.StrippedArmour(threat.armour,droid.ActiveArmourStrip):threat.armour;
     float shotArmourPen=stats.armourPenetration+(overcharged?CombatVerbs.OverchargeArmourPenBonus:0)+(consumedAmmo?BermsBallistics.ArmourPenBonusFor(shotAmmo):0);
     hitDamage=WeaponBallistics.ArmourReduced(hitDamage,effectiveArmour,shotArmourPen);
    }
    LastHitDamage=hitDamage;LastHitDistance=distance;
    var point=weakHit?origin+direction*weakAt:end;
    if(weakHit){WeakPointHits++;weak.NoteHit();if(droid)droid.MarkCriticalHit();}
    float before=target.Current;
    target.Damage(hitDamage,point,weakHit?weak.damageMultiplier:1);
    if(droid)droid.ClearCriticalMark();
    bool killed=!target.Alive;
    if(critical||weakHit)CriticalHits++;
    LastHit=new CombatHit{target=target,point=point,dealt=Mathf.Max(0,before-target.Current),critical=critical||weakHit,weakPoint=weakHit,killed=killed,zone=weakHit?weak.label:null};
    TargetHit?.Invoke(target,killed);
    HitLanded?.Invoke(LastHit);
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
  /// Rattle and damper cues (QA reads the counts; the clips may still be empty).
  public int Rattled {get;private set;}
  public int DamperTicks {get;private set;}
  /// The player's own clips, else the crafting catalog's (WardCrafting.asset, bound by the craft data script).
  AudioClip[] Rattles_=>rattleClips!=null&&rattleClips.Length>0?rattleClips:Crafting?.Data?.rattleClips;
  AudioClip[] Dampers=>damperClips!=null&&damperClips.Length>0?damperClips:Crafting?.Data?.damperClips;
  void PlayRattle(float gain)
  {
   Rattled++;var clips=Rattles_;
   if(!audioSource||clips==null||clips.Length==0)return;
   var clip=Pick(clips,ref lastRattle);if(clip)audioSource.PlayOneShot(clip,gain);
  }
  void PlayDamper()
  {
   DamperTicks++;var clips=Dampers;
   if(!audioSource||clips==null||clips.Length==0)return;
   var clip=Pick(clips,ref lastDamper);if(clip)audioSource.PlayOneShot(clip,damperGain);
  }
  static AudioClip Pick(AudioClip[] clips,ref int last)=>CombatAudio.Pick(clips,ref last);
  /// The bound weapon's own sound set, or null when it has none (the legacy arrays play).
  public WeaponSoundSet ActiveSoundSet=>CombatAudio.SelectSet(weaponSounds,Loadout!=null?Loadout.WeaponId:null);
  public bool LayeredShot=>audioSource&&(ActiveSoundSet!=null||shotBody!=null&&shotBody.Length>0);
  /// Shots of the active set (QA: which set the last shot used; null id = the legacy pistol arrays).
  public string LastShotSoundSet {get;private set;}
  float lastSetShot=-99;
  void PlayShot()
  {
   if(!audioSource)return;
   var set=ActiveSoundSet;
   LastShotSoundSet=set!=null?set.weaponId:null;
   if(set!=null){PlaySetShot(set);return;}
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
  int setMech=-1,setBody=-1,setTail=-1;
  /// Same layering as the pistol path, with the set's own gains and a quieter tail inside a held burst.
  void PlaySetShot(WeaponSoundSet set)
  {
   bool close=Aiming||follow&&follow.FirstPerson;
   bool inBurst=Time.time-lastSetShot<Stats.fireInterval*1.5f;lastSetShot=Time.time;
   audioSource.pitch=UnityEngine.Random.Range(set.pitch.x,Mathf.Max(set.pitch.x,set.pitch.y));
   var mech=Pick(set.mech,ref setMech);if(mech)audioSource.PlayOneShot(mech,set.mechGain*(close?closeMechScale:1));
   var body=Pick(set.body,ref setBody);if(body)audioSource.PlayOneShot(body,set.bodyGain);
   var tailClip=Pick(set.tail,ref setTail);
   if(tailClip)
   {
    var tail=tailSource?tailSource:audioSource;
    if(tailSource)tailSource.pitch=UnityEngine.Random.Range(.96f,1.04f);
    tail.PlayOneShot(tailClip,set.tailGain*(close?closeTailScale:1)*(inBurst?set.burstTailScale:1));
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
   bool ranged=incomingRangedBallistic;
   bool exposed=ranged&&BermsBallistics.IsExposedToRanged(Character);
   LastHitWasRanged=ranged;
   LastHitWasExposed=exposed;
   if(exposed)ExposedHits++;
   if(audioSource&&hurtClip)
   {
    float prevPitch=audioSource.pitch;
    audioSource.pitch=ranged?(exposed?.88f:1.18f):1f;
    audioSource.PlayOneShot(hurtClip,exposed?1f:.9f);
    audioSource.pitch=prevPitch;
   }
   if(ranged&&follow&&!(session&&session.reducedMotion))
   {
    float sideSign=UnityEngine.Random.value<.5f?-1f:1f;
    if(exposed)follow.ApplyShotKick(BermsBallistics.ExposedHitKickDegrees,sideSign*BermsBallistics.ExposedHitSideKickDegrees,.65f,BermsBallistics.ExposedHitRecoverSeconds,.15f);
    else follow.ApplyShotKick(BermsBallistics.ArmouredHitKickDegrees,sideSign*BermsBallistics.ArmouredHitSideKickDegrees,.8f,BermsBallistics.ArmouredHitRecoverSeconds,0f);
   }
   Hurt?.Invoke(amount);HurtFrom?.Invoke(amount,from);
   if(exposed)ExposedHit?.Invoke(amount,from);
  }
  void OnDied()
  {
   Downs++;Armed=false;
   // the nearest Warden waystation the player has found, else the gate post
   var station=WardenWaystation.NearestFound(transform.position,respawnPoint?respawnPoint.position:transform.position);
   var point=station&&station.respawnPoint?station.respawnPoint:respawnPoint;
   session.Notify(station?$"You go down in the dust. A Warden patrol drags you back to the {station.displayName.ToLowerInvariant()}.":"You go down in the dust. A Warden patrol drags you back to the post.","Outer Berms");
   if(point){motor.Teleport(point.position);motor.visual.rotation=point.rotation;}
   Health.Restore();Nano=Stats.nanoMax;OverclockUntil=-1;
   Downed?.Invoke();
  }
 }
 /// One landed player shot: where it struck (the weak point's entry for a weak-point hit), what it removed after armour,
 /// and whether it was critical (weapon roll or weak point), a weak-point hit and a kill.
 public struct CombatHit
 {
  public Health target;public Vector3 point;public float dealt;
  public bool critical,weakPoint,killed;public string zone;
 }
}
