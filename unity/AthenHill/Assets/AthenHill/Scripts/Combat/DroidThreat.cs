using System;
using UnityEngine;
namespace AthenHill
{
 public enum ThreatTier { Easy, Normal, Danger }
 /// The numbers behind a tier decision (HUD, tests, reports).
 [Serializable] public struct ThreatEstimate
 {
  public ThreatTier tier;
  public float engagementRange,damagePerHit,hitChance,shotsToKill,playerTimeToKill;
  public float droidDamagePerSecond,droidTimeToDown,ratio,levelFactor,threat;
  public override string ToString()=>$"{tier}: engage {engagementRange:0.#} m, {damagePerHit:0.#}/hit × {hitChance:0.00} hit, {shotsToKill:0.#} shots, TTK {playerTimeToKill:0.00} s; droid {droidDamagePerSecond:0.0} dps, TTD {droidTimeToDown:0.0} s; ratio {ratio:0.000} × level {levelFactor:0.00} = {threat:0.000}";
 }
 /// What the tier rule needs to know about a droid (pure data so the rule is testable without a scene).
 [Serializable] public struct DroidProfile
 {
  public int level;public float health,armour;
  public bool ranged;
  public float strikeDamage,windupSeconds,recoverSeconds;
  public int slamEvery;public float slamDamage,slamWindupSeconds,slamRecoverSeconds;
  public float preferredRange,boltDamage,burstInterval,volleyPauseMean;public int burstCount;
  public static DroidProfile From(FeralDroid d,DroidThreat threat)=>new DroidProfile
  {
   level=threat?threat.level:DroidThreat.DefaultLevel,health=d.Health?d.Health.max:d.GetComponent<Health>().max,armour=threat?threat.armour:0,
   ranged=d.attackMode==DroidAttack.Ranged,strikeDamage=d.strikeDamage,windupSeconds=d.windupSeconds,recoverSeconds=d.recoverSeconds,
   slamEvery=d.slamEvery,slamDamage=d.slamDamage,slamWindupSeconds=d.slamWindupSeconds,slamRecoverSeconds=d.slamRecoverSeconds,
   preferredRange=d.preferredRange,boltDamage=d.boltDamage,burstInterval=d.burstInterval,burstCount=d.burstCount,
   volleyPauseMean=(d.volleyPause.x+Mathf.Max(d.volleyPause.x,d.volleyPause.y))*.5f,
  };
 }
 /// What the tier rule needs to know about the player.
 public struct PlayerProfile
 {
  public WeaponStats stats;public float health,nanoRegenDelay;public int level;
  /// Incoming damage after the character's armour and physical resistance (PlayerCombat.ComputePhysicalDamage).
  public Func<float,float> mitigate;
  public static PlayerProfile From(PlayerCombat player)=>new PlayerProfile
  {
   stats=player.Stats,health=player.Health?player.Health.max:100,nanoRegenDelay=player.nanoRegenDelay,
   level=player.Character!=null?player.Character.Level:1,
   mitigate=incoming=>PlayerCombat.ComputePhysicalDamage(player.Character,incoming),
  };
 }
 /// Difficulty and reward of a feral droid relative to the player (2 Oct 2026 "next level" programme). The enemies
 /// pass sets Level, Experience and Armour per prefab; the combat pass implements Tier (the grey/green/red bar) and
 /// the award (PlayerCombat on a kill: Easy 0, Normal 1×, Danger 1.75× Experience).
 ///
 /// Tier rule. threat = (player time-to-kill ÷ droid time-to-down) × LevelStep^(droid level − player level).
 /// - Player time-to-kill with the equipped weapon's effective stats (mods, character, skills): damage per hit at
 ///   the typical engagement range (melee droids 10 m, ranged droids their preferred range, capped by the weapon's
 ///   range) with range falloff, expected criticals and the droid's armour against the weapon's penetration; the
 ///   aiming cone's chance to land on a 0.35 m half-width droid; the shots that takes at the fire interval, plus a
 ///   nano refill wait when the magazine cannot cover them and half a second to acquire the target.
 /// - Droid time-to-down: the player's maximum health over the droid's damage per second after
 ///   PlayerCombat.ComputePhysicalDamage (armour and physical resistance): melee strike/recover cycle (slams averaged
 ///   in for elites), or ranged volleys (burst × bolt damage × BoltHitFraction over wind-up, burst and the mean pause).
 /// - Easy (grey, no XP) below EasyBelow (0.04); Danger (red, high XP) from DangerFrom (0.25); Normal (green) between.
 ///   Calibrated 2 Oct 2026 (CombatBalanceTests): the depot workers, scrap drones, gunners and lancers are Normal for
 ///   the level-1 colonist with the scrap pistol and field vest, the Foreman and the outer sites Danger; with the field
 ///   rifle and plate carrier at level 3 the depot droids are Easy and the Foreman/outer droids Normal.
 [DisallowMultipleComponent]
 public class DroidThreat:MonoBehaviour
 {
  [Tooltip("Design level of this droid: 1 = the depot workers and scrap drones, 2 = gunners/lancers, 3+ = the outer sites.")]
  [Min(1)]public int level=1;
  [Tooltip("Experience awarded on a kill at Normal tier (Danger awards 1.75×, Easy none).")]
  [Min(0)]public int experience=10;
  [Tooltip("Flat armour: each point not covered by the weapon's armour penetration removes one point from every hit (never below 20 % of the hit).")]
  [Min(0)]public float armour;
  public const int DefaultLevel=1,DefaultExperience=10;
  /// Tier thresholds on the threat number (documented above).
  public const float EasyBelow=.04f,DangerFrom=.25f;
  /// Multiplier per level of difference between the droid and the player (clamped to ±4 levels).
  public const float LevelStep=1.5f;
  public const float DangerExperienceScale=1.75f;
  public const float MeleeEngagementRange=10f,AimOverheadSeconds=.5f,BoltHitFraction=.7f,DroidHalfWidth=.35f;
  /// Easy (grey, no XP), Normal (green) or Danger (red): the player's time to kill this droid with the equipped weapon
  /// against the droid's time to put the player down, with armour applied.
  public static ThreatTier Tier(FeralDroid droid,PlayerCombat player)=>Estimate(droid,player).tier;
  public static ThreatTier TierFor(float threat)=>threat<EasyBelow?ThreatTier.Easy:threat>=DangerFrom?ThreatTier.Danger:ThreatTier.Normal;
  public static ThreatEstimate Estimate(FeralDroid droid,PlayerCombat player)
  {
   if(!droid||!player)return new ThreatEstimate{tier=ThreatTier.Normal};
   return Estimate(DroidProfile.From(droid,droid.GetComponent<DroidThreat>()),PlayerProfile.From(player));
  }
  /// The pure rule.
  public static ThreatEstimate Estimate(DroidProfile droid,PlayerProfile player)
  {
   var s=player.stats;var e=new ThreatEstimate();
   float range=Mathf.Max(1,s.range);
   e.engagementRange=Mathf.Min(range,droid.ranged?Mathf.Max(1,droid.preferredRange):MeleeEngagementRange);
   float crit=Mathf.Clamp01(s.criticalChance/100)*(Mathf.Max(1,s.criticalMultiplier)-1);
   float perHit=Mathf.Max(0,s.damage)*WeaponBallistics.Falloff(e.engagementRange,range)*(1+crit);
   e.damagePerHit=WeaponBallistics.ArmourReduced(perHit,droid.armour,s.armourPenetration);
   float cone=WeaponBallistics.Cone(s.spread,s.accuracy,true,false);
   e.hitChance=WeaponBallistics.HitChance(cone,e.engagementRange,DroidHalfWidth);
   float hits=e.damagePerHit>0?Mathf.Ceil(Mathf.Max(1,droid.health)/e.damagePerHit):float.PositiveInfinity;
   e.shotsToKill=hits/Mathf.Max(.01f,e.hitChance);
   float ttk=float.PositiveInfinity;
   if(!float.IsInfinity(e.shotsToKill))
   {
    ttk=(e.shotsToKill-1)*Mathf.Max(.05f,s.fireInterval)+AimOverheadSeconds;
    float nano=e.shotsToKill*Mathf.Max(0,s.nanoPerShot);
    if(nano>s.nanoMax)ttk+=(nano-s.nanoMax)/Mathf.Max(1,s.nanoRegen)+Mathf.Max(0,player.nanoRegenDelay);
   }
   e.playerTimeToKill=ttk;
   Func<float,float> mitigate=player.mitigate??(x=>x);
   float dps;
   if(droid.ranged)
   {
    int burst=Mathf.Max(1,droid.burstCount);
    float volley=burst*Mathf.Max(0,mitigate(droid.boltDamage))*BoltHitFraction;
    float time=Mathf.Max(.1f,droid.windupSeconds+burst*droid.burstInterval+droid.volleyPauseMean);
    dps=volley/time;
   }
   else
   {
    float strike=Mathf.Max(0,mitigate(droid.strikeDamage)),cycle=Mathf.Max(.1f,droid.windupSeconds+.2f+droid.recoverSeconds);
    if(droid.slamEvery>0)
    {
     float slam=Mathf.Max(0,mitigate(droid.slamDamage)),slamCycle=Mathf.Max(.1f,droid.slamWindupSeconds+.2f+droid.slamRecoverSeconds);
     int n=droid.slamEvery;
     dps=((n-1)*strike+slam)/((n-1)*cycle+slamCycle);
    }
    else dps=strike/cycle;
   }
   e.droidDamagePerSecond=dps;
   e.droidTimeToDown=dps>0?Mathf.Max(1,player.health)/dps:float.PositiveInfinity;
   e.ratio=float.IsInfinity(e.playerTimeToKill)?float.PositiveInfinity:float.IsInfinity(e.droidTimeToDown)?0:e.playerTimeToKill/e.droidTimeToDown;
   e.levelFactor=Mathf.Pow(LevelStep,Mathf.Clamp(droid.level-Mathf.Max(1,player.level),-4,4));
   e.threat=e.ratio*e.levelFactor;
   e.tier=TierFor(e.threat);
   return e;
  }
  /// Experience for a kill at this tier.
  public int Award(ThreatTier tier)=>AwardFor(experience,tier);
  public static int AwardFor(int experience,ThreatTier tier)
   =>tier==ThreatTier.Easy?0:tier==ThreatTier.Danger?Mathf.RoundToInt(Mathf.Max(0,experience)*DangerExperienceScale):Mathf.Max(0,experience);
 }
}
