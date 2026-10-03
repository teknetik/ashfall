using UnityEngine;
namespace AthenHill
{
 /// Pure weapon maths shared by PlayerCombat, the droid threat rule, the panels and the Edit Mode tests
 /// (2 Oct 2026 "next level" programme). No Unity lifecycle.
 ///
 /// Range: a weapon does full damage out to EffectiveFraction of its range stat, then tapers linearly to FalloffFloor
 /// at the range stat, beyond which a shot cannot reach (the hit scan stops there).
 /// Accuracy: the cone (degrees) is the weapon's spread narrowed by the effective accuracy (0..100, weapon base +
 /// the character's accuracy derived stat + the matching weapon skill × SkillAccuracyPerPoint), halved while aiming
 /// and widened while moving.
 public static class WeaponBallistics
 {
  /// Fraction of the range stat with full damage (pistol 30 m → 18 m, rifle 95 m → 57 m).
  public const float EffectiveFraction=.6f;
  /// Damage multiplier at the far end of the range.
  public const float FalloffFloor=.35f;
  /// Cone multipliers: aiming down the shoulder, firing from the hip, and moving faster than MovingSpeed.
  public const float AimSpreadScale=.5f,HipSpreadScale=1f,MovingSpreadScale=1.6f;
  public const float MovingSpeed=.6f;
  /// Each point of the weapon's skill (pistol, rifle, …; the catalog trains them in steps of 5 up to 1200) adds this
  /// much accuracy: the starting pistol skill of 30 gives +7.5, a skill of 200 gives +50.
  public const float SkillAccuracyPerPoint=.25f;
  /// A hit always keeps at least this fraction of its damage against armour.
  public const float MinArmourFraction=.2f;

  public static float EffectiveRange(float range)=>Mathf.Max(0,range)*EffectiveFraction;
  /// Damage multiplier at this distance: 1 inside the effective range, FalloffFloor at the range stat.
  public static float Falloff(float distance,float range)
  {
   if(range<=0)return 0;
   float effective=range*EffectiveFraction;
   if(distance<=effective)return 1;
   if(distance>=range)return FalloffFloor;
   return Mathf.Lerp(1,FalloffFloor,(distance-effective)/(range-effective));
  }
  /// Effective accuracy 0..100 from the weapon's stat, the character's accuracy derived stat and the weapon skill.
  public static float Accuracy(float weaponAccuracy,float characterAccuracy,float skill)
   =>Mathf.Clamp(weaponAccuracy+characterAccuracy+Mathf.Max(0,skill)*SkillAccuracyPerPoint,0,100);
  /// Shot cone in degrees (half-angle: shots scatter inside a disc of this radius).
  public static float Cone(float spread,float accuracy,bool aiming,bool moving)
   =>Mathf.Max(0,spread)*(1-Mathf.Clamp01(accuracy/100))*(aiming?AimSpreadScale:HipSpreadScale)*(moving?MovingSpreadScale:1);
  /// Chance that a shot with this cone lands on a target of the given half-width at this distance (1 inside the cone).
  public static float HitChance(float coneDegrees,float distance,float targetRadius)
  {
   if(coneDegrees<=0||distance<=0)return 1;
   float scatter=distance*Mathf.Tan(coneDegrees*Mathf.Deg2Rad);
   return scatter<=targetRadius?1:Mathf.Clamp01(targetRadius/scatter);
  }
  /// Flat armour: each point not covered by the weapon's armour penetration removes one point of damage, never
  /// below MinArmourFraction of the hit.
  public static float ArmourReduced(float damage,float armour,float penetration)
   =>Mathf.Max(damage*MinArmourFraction,damage-Mathf.Max(0,Mathf.Max(0,armour)-Mathf.Max(0,penetration)));
  /// The character skill a weapon definition trains: the catalog skill id contained in the weapon id
  /// (weapon_scrap_pistol → pistol, weapon_field_rifle → rifle). Null when none matches.
  public static string SkillFor(string weaponId)
  {
   if(string.IsNullOrEmpty(weaponId))return null;
   var id=weaponId.ToLowerInvariant();
   foreach(var skill in new[]{"pistol","rifle","shotgun","smg","heavyWeapons","energyWeapons"})if(id.Contains(skill.ToLowerInvariant()))return skill;
   return null;
  }
 }
}
