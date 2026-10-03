using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// 2 Oct 2026 next-level combat pass: range falloff, accuracy cone, skill accuracy, droid armour and the threat tier
 /// rule (grey/green/red) with the experience award.
 public class CombatBalanceTests
 {
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Craft()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static CharacterCatalog Characters()=>AssetDatabase.LoadAssetAtPath<CharacterCatalog>("Assets/AthenHill/Resources/CharacterCatalog.asset");
  static FeralDroid Prefab(string name)=>AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/"+name+".prefab").GetComponent<FeralDroid>();

  [Test] public void FalloffIsFullInsideTheEffectiveRangeAndTapersToTheFloor()
  {
   Assert.That(WeaponBallistics.Falloff(0,30),Is.EqualTo(1));
   Assert.That(WeaponBallistics.Falloff(18,30),Is.EqualTo(1),"60 % of the range is still full damage");
   Assert.That(WeaponBallistics.Falloff(24,30),Is.EqualTo(.675f).Within(1e-4),"half way through the taper");
   Assert.That(WeaponBallistics.Falloff(30,30),Is.EqualTo(WeaponBallistics.FalloffFloor));
   Assert.That(WeaponBallistics.Falloff(40,30),Is.EqualTo(WeaponBallistics.FalloffFloor),"beyond the range stat the floor holds (the shot cannot reach anyway)");
   Assert.That(WeaponBallistics.Falloff(5,0),Is.Zero);
   Assert.That(WeaponBallistics.EffectiveRange(95),Is.EqualTo(57).Within(1e-4));
  }

  [Test] public void ConeNarrowsWithAccuracyAndAimingAndWidensOnTheMove()
  {
   Assert.That(WeaponBallistics.Cone(4,0,false,false),Is.EqualTo(4));
   Assert.That(WeaponBallistics.Cone(4,50,false,false),Is.EqualTo(2));
   Assert.That(WeaponBallistics.Cone(4,50,true,false),Is.EqualTo(1));
   Assert.That(WeaponBallistics.Cone(4,50,false,true),Is.EqualTo(3.2f).Within(1e-4));
   Assert.That(WeaponBallistics.Cone(4,100,false,false),Is.Zero);
   Assert.That(WeaponBallistics.Cone(4,150,false,false),Is.Zero,"accuracy clamps at 100");
   Assert.That(WeaponBallistics.Cone(-3,0,false,false),Is.Zero);
  }

  [Test] public void AccuracyAddsCharacterStatAndAQuarterOfTheWeaponSkill()
  {
   Assert.That(WeaponBallistics.Accuracy(20,10,0),Is.EqualTo(30));
   Assert.That(WeaponBallistics.Accuracy(0,10,20),Is.EqualTo(15));
   Assert.That(WeaponBallistics.Accuracy(20,10,100),Is.EqualTo(55));
   Assert.That(WeaponBallistics.Accuracy(90,30,100),Is.EqualTo(100),"clamped");
   Assert.That(WeaponBallistics.Accuracy(0,0,-5),Is.Zero);
   Assert.That(WeaponBallistics.SkillFor("weapon_scrap_pistol"),Is.EqualTo("pistol"));
   Assert.That(WeaponBallistics.SkillFor("weapon_field_rifle"),Is.EqualTo("rifle"));
   Assert.That(WeaponBallistics.SkillFor("weapon_odd_thing"),Is.Null);
   Assert.That(WeaponBallistics.SkillFor(null),Is.Null);
  }

  [Test] public void HitChanceAndArmourMaths()
  {
   Assert.That(WeaponBallistics.HitChance(0,20,.35f),Is.EqualTo(1));
   Assert.That(WeaponBallistics.HitChance(1,10,.35f),Is.EqualTo(1),"10 m × tan 1° = 0.17 m scatter inside a 0.35 m target");
   float far=WeaponBallistics.HitChance(2,30,.35f);
   Assert.That(far,Is.EqualTo(.35f/(30*Mathf.Tan(2*Mathf.Deg2Rad))).Within(1e-4));Assert.That(far,Is.LessThan(.5f));
   Assert.That(WeaponBallistics.ArmourReduced(30,0,0),Is.EqualTo(30));
   Assert.That(WeaponBallistics.ArmourReduced(30,8,0),Is.EqualTo(22));
   Assert.That(WeaponBallistics.ArmourReduced(30,8,5),Is.EqualTo(27));
   Assert.That(WeaponBallistics.ArmourReduced(30,8,20),Is.EqualTo(30),"penetration never adds damage");
   Assert.That(WeaponBallistics.ArmourReduced(10,40,0),Is.EqualTo(2),"20 % floor");
  }

  [Test] public void CatalogWeaponsCarryTheNextLevelRangesAndLabels()
  {
   var data=Craft();
   var pistol=data.weapons.Single(w=>w.id=="weapon_scrap_pistol");var rifle=data.weapons.Single(w=>w.id=="weapon_field_rifle");
   Assert.That(pistol.stats.range,Is.EqualTo(30));Assert.That(pistol.stats.spread,Is.EqualTo(4));Assert.That(pistol.stats.accuracy,Is.Zero);
   Assert.That(rifle.stats.range,Is.EqualTo(95));Assert.That(rifle.stats.spread,Is.EqualTo(1.8f).Within(1e-4));Assert.That(rifle.stats.accuracy,Is.EqualTo(20));
   Assert.That(data.Stat("spread"),Is.Not.Null);Assert.That(data.Stat("spread").lowerIsBetter,Is.True);
   Assert.That(data.Stat("accuracy"),Is.Not.Null);Assert.That(data.Stat("accuracy").label,Is.EqualTo("Accuracy"));
   // the precision barrel still tightens the rifle, the pistol barrels reach and tighten the pistol
   var precision=WeaponLoadout.Compute(rifle,new[]{data.modifiers.Single(m=>m.itemId=="rifle_precision_barrel")});
   Assert.That(precision.range,Is.EqualTo(110));Assert.That(precision.spread,Is.EqualTo(1.35f).Within(1e-4));Assert.That(precision.accuracy,Is.EqualTo(28));
  }

  [Test] public void CharacterSkillsNarrowTheConeThroughTheSharedPipeline()
  {
   var pack=new ShopModel(City().items);var character=new CharacterModel(Characters(),pack);
   var model=new CraftingModel(Craft(),City().items,pack,()=>true);
   // the starting colonist: perception 10 → accuracy 10; skills carry attribute dependencies (pistol 20 + 10 = 30, rifle 10)
   Assert.That(character.Stat("accuracy"),Is.EqualTo(10).Within(1e-4));
   float pistolSkill=character.Stat("pistol"),rifleSkill=character.Stat("rifle");
   Assert.That(pistolSkill,Is.EqualTo(30).Within(1e-4));Assert.That(rifleSkill,Is.EqualTo(10).Within(1e-4));
   var pistol=model.GetLoadout("weapon_scrap_pistol").WithCharacter(character);
   var rifle=model.GetLoadout("weapon_field_rifle").WithCharacter(character);
   Assert.That(pistol.accuracy,Is.EqualTo(10+pistolSkill*WeaponBallistics.SkillAccuracyPerPoint).Within(1e-4),"0 + 10 perception + pistol skill × 0.25");
   Assert.That(pistol.accuracy,Is.EqualTo(17.5f).Within(1e-4));
   Assert.That(rifle.accuracy,Is.EqualTo(20+10+rifleSkill*WeaponBallistics.SkillAccuracyPerPoint).Within(1e-4),"20 + 10 perception + rifle skill × 0.25");
   Assert.That(WeaponBallistics.Cone(pistol.spread,pistol.accuracy,false,false),Is.EqualTo(3.3f).Within(1e-3));
   Assert.That(WeaponBallistics.Cone(pistol.spread,pistol.accuracy,true,false),Is.EqualTo(1.65f).Within(1e-3));
   Assert.That(WeaponBallistics.Cone(rifle.spread,rifle.accuracy,true,false),Is.EqualTo(.6075f).Within(1e-3));
   // training the rifle skill tightens the rifle, not the pistol
   Assert.That(character.GrantExperience(100,out var reason),reason);
   int trained=0;while(character.TryRaiseSkill("rifle",out _))trained++;
   Assert.That(trained,Is.GreaterThan(0));
   var rifle2=model.GetLoadout("weapon_field_rifle").WithCharacter(character);
   Assert.That(character.Stat("rifle"),Is.GreaterThan(rifleSkill));
   Assert.That(rifle2.accuracy,Is.EqualTo(30+character.Stat("rifle")*WeaponBallistics.SkillAccuracyPerPoint).Within(1e-3));
   Assert.That(model.GetLoadout("weapon_scrap_pistol").WithCharacter(character).accuracy,Is.EqualTo(pistol.accuracy).Within(1e-4));
  }

  [Test] public void TierThresholdsAndAwards()
  {
   Assert.That(DroidThreat.TierFor(0),Is.EqualTo(ThreatTier.Easy));
   Assert.That(DroidThreat.TierFor(DroidThreat.EasyBelow-1e-4f),Is.EqualTo(ThreatTier.Easy));
   Assert.That(DroidThreat.TierFor(DroidThreat.EasyBelow),Is.EqualTo(ThreatTier.Normal));
   Assert.That(DroidThreat.TierFor(DroidThreat.DangerFrom-1e-4f),Is.EqualTo(ThreatTier.Normal));
   Assert.That(DroidThreat.TierFor(DroidThreat.DangerFrom),Is.EqualTo(ThreatTier.Danger));
   Assert.That(DroidThreat.TierFor(float.PositiveInfinity),Is.EqualTo(ThreatTier.Danger));
   Assert.That(DroidThreat.AwardFor(12,ThreatTier.Easy),Is.Zero);
   Assert.That(DroidThreat.AwardFor(12,ThreatTier.Normal),Is.EqualTo(12));
   Assert.That(DroidThreat.AwardFor(12,ThreatTier.Danger),Is.EqualTo(21));
   Assert.That(DroidThreat.AwardFor(-5,ThreatTier.Normal),Is.Zero);
  }

  [Test] public void TierRuleIsRelativeToWeaponArmourAndLevel()
  {
   var droid=new DroidProfile{level=1,health=130,strikeDamage=18,windupSeconds=.55f,recoverSeconds=.85f};
   var pistol=new WeaponStats{damage=34,fireInterval=.28f,range=30,nanoMax=100,nanoPerShot=9,nanoRegen=30,spread=4,accuracy=17.5f};
   var player=new PlayerProfile{stats=pistol,health=100,level=1,nanoRegenDelay=.6f,mitigate=x=>x};
   var e=DroidThreat.Estimate(droid,player);
   Assert.That(e.engagementRange,Is.EqualTo(10));Assert.That(e.damagePerHit,Is.EqualTo(34));Assert.That(e.hitChance,Is.EqualTo(1));
   Assert.That(e.shotsToKill,Is.EqualTo(4));Assert.That(e.playerTimeToKill,Is.EqualTo(3*.28f+DroidThreat.AimOverheadSeconds).Within(1e-4));
   Assert.That(e.droidDamagePerSecond,Is.EqualTo(18/1.6f).Within(1e-4));Assert.That(e.droidTimeToDown,Is.EqualTo(100/(18/1.6f)).Within(1e-3));
   Assert.That(e.levelFactor,Is.EqualTo(1));Assert.That(e.tier,Is.EqualTo(ThreatTier.Normal),e.ToString());
   // the same droid against a levelled colonist with a stronger weapon and a plate carrier is Easy
   var rifle=new WeaponStats{damage=27,fireInterval=.18f,range=95,nanoMax=100,nanoPerShot=8,nanoRegen=30,spread=1.8f,accuracy=40,armourPenetration=8};
   var strong=new PlayerProfile{stats=rifle,health=104,level=3,nanoRegenDelay=.6f,mitigate=x=>x*.88f-24*.2f};
   var easy=DroidThreat.Estimate(droid,strong);
   Assert.That(easy.levelFactor,Is.EqualTo(Mathf.Pow(DroidThreat.LevelStep,-2)).Within(1e-4));
   Assert.That(easy.tier,Is.EqualTo(ThreatTier.Easy),easy.ToString());
   // a tougher, armoured, higher-level droid is Danger for the starter
   var elite=new DroidProfile{level=3,health=240,armour=8,strikeDamage=26,windupSeconds=.5f,recoverSeconds=.8f};
   var danger=DroidThreat.Estimate(elite,player);
   Assert.That(danger.damagePerHit,Is.EqualTo(26),"8 armour, no penetration");
   Assert.That(danger.tier,Is.EqualTo(ThreatTier.Danger),danger.ToString());
   // ranged droids are judged at their preferred range with the aiming cone and bolt hit fraction
   var gunner=new DroidProfile{level=2,health=150,ranged=true,preferredRange=17,boltDamage=8,burstCount=3,burstInterval=.2f,windupSeconds=.9f,volleyPauseMean=2};
   var g=DroidThreat.Estimate(gunner,player);
   Assert.That(g.engagementRange,Is.EqualTo(17));Assert.That(g.hitChance,Is.LessThan(1));
   Assert.That(g.droidDamagePerSecond,Is.EqualTo(3*8*DroidThreat.BoltHitFraction/(0.9f+.6f+2)).Within(1e-3));
   Assert.That(g.levelFactor,Is.EqualTo(DroidThreat.LevelStep).Within(1e-4));
   // a weapon that cannot hurt it: infinite time to kill, Danger
   var pea=new PlayerProfile{stats=new WeaponStats{damage=1,fireInterval=.3f,range=30,nanoMax=100,nanoPerShot=9,nanoRegen=30},health=100,level=1};
   Assert.That(DroidThreat.Estimate(new DroidProfile{level=1,health=100,armour=50,strikeDamage=10,windupSeconds=.5f,recoverSeconds=.5f},pea).tier,Is.EqualTo(ThreatTier.Danger));
  }

  [Test] public void SavedPrefabsAreNormalForTheStarterAndEasyForTheRifleColonist()
  {
   var pack=new ShopModel(City().items);var character=new CharacterModel(Characters(),pack);
   var model=new CraftingModel(Craft(),City().items,pack,()=>true);
   PlayerProfile Player(string weapon)=>new PlayerProfile{stats=model.GetLoadout(weapon).WithCharacter(character),health=character.Stat("health"),level=character.Level,nanoRegenDelay=.6f,mitigate=x=>PlayerCombat.ComputePhysicalDamage(character,x)};
   var names=new[]{"FeralWorkerDroid","FeralScrapDrone","FeralGunnerDroid","FeralLancerDrone"};
   var table=new System.Text.StringBuilder();
   var starter=Player("weapon_scrap_pistol");
   foreach(var n in names)
   {
    var d=Prefab(n);var e=DroidThreat.Estimate(DroidProfile.From(d,d.GetComponent<DroidThreat>()),starter);
    table.AppendLine($"L1 pistol vs {n}: {e}");
    Assert.That(e.tier,Is.EqualTo(ThreatTier.Normal),n+" for the starting colonist with the scrap pistol: "+e);
   }
   // level 3, rifle, plate carrier
   Assert.That(character.GrantExperience(200,out var reason),reason);Assert.That(character.Level,Is.EqualTo(3));
   if(character.Equipped("armour_chest")!=null)Assert.That(character.TryUnequip("armour_chest",out reason),reason);   // the starting field vest
   Assert.That(character.TryGrantEquipped("warden_plate_carrier","armour_chest",out reason),reason);
   Assert.That(character.Equipped("armour_chest"),Is.EqualTo("warden_plate_carrier"));
   var strong=Player("weapon_field_rifle");
   foreach(var n in names)
   {
    var d=Prefab(n);var e=DroidThreat.Estimate(DroidProfile.From(d,d.GetComponent<DroidThreat>()),strong);
    table.AppendLine($"L3 rifle+carrier vs {n}: {e}");
    Assert.That(e.tier,Is.EqualTo(ThreatTier.Easy),n+" for the level-3 rifle colonist in a plate carrier: "+e);
   }
   Debug.Log(table.ToString());
  }

  [Test] public void ExperienceLevelsTheCharacterAndKeepsTheRemainder()
  {
   var pack=new ShopModel(City().items);var character=new CharacterModel(Characters(),pack);
   int per=character.Data.experiencePerLevel,a0=character.AttributePoints,s0=character.SkillPoints;
   Assert.That(character.GrantExperience(per-1,out var r),r);Assert.That(character.Level,Is.EqualTo(1));Assert.That(character.Experience,Is.EqualTo(per-1));
   Assert.That(character.GrantExperience(DroidThreat.AwardFor(12,ThreatTier.Danger),out r),r);
   Assert.That(character.Level,Is.EqualTo(2));Assert.That(character.Experience,Is.EqualTo(20));
   Assert.That(character.AttributePoints,Is.EqualTo(a0+character.Data.attributePointsPerLevel));Assert.That(character.SkillPoints,Is.EqualTo(s0+character.Data.skillPointsPerLevel));
  }
 }
}
