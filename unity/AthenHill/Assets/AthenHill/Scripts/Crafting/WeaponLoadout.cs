using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Supported weapon numbers. Field names are the stat IDs that CraftEffect.stat refers to.
 [Serializable] public struct WeaponStats
 {
  [Min(0)]public float damage,fireInterval,range,recoil,nanoMax,nanoPerShot,nanoRegen,aimAssist;
  [Min(0)]public float accuracy,spread,criticalChance,criticalMultiplier,projectileVelocity,reloadTime,heatGeneration,cooling,durability,armourPenetration;
  // Handling (20 Nov 2026, Steady Hands bench): what the hands and eyes get, read by PlayerCombat, FollowCamera and the
  // view models. sway = idle aim sway amplitude in degrees (visual only, never moves the shot); sideKick = random sideways
  // camera step per shot in degrees; recovery = seconds the kick takes to settle (0 = PlayerCombat's default; slow
  // recovery overshoots once); scatterGrowth = extra shot cone per rapid shot, as a fraction of the cone (decays between shots).
  [Min(0)]public float sway,sideKick,recovery,scatterGrowth;
  public static readonly string[] Ids={"damage","fireInterval","range","recoil","nanoMax","nanoPerShot","nanoRegen","aimAssist","accuracy","spread","criticalChance","criticalMultiplier","projectileVelocity","reloadTime","heatGeneration","cooling","durability","armourPenetration","sway","sideKick","recovery","scatterGrowth"};
  public const int Count=22;
  public static int IndexOf(string id)=>id==null?-1:Array.IndexOf(Ids,id);
  public float this[int i]
  {
   get=>i switch{0=>damage,1=>fireInterval,2=>range,3=>recoil,4=>nanoMax,5=>nanoPerShot,6=>nanoRegen,7=>aimAssist,8=>accuracy,9=>spread,10=>criticalChance,11=>criticalMultiplier,12=>projectileVelocity,13=>reloadTime,14=>heatGeneration,15=>cooling,16=>durability,17=>armourPenetration,18=>sway,19=>sideKick,20=>recovery,21=>scatterGrowth,_=>throw new ArgumentOutOfRangeException(nameof(i))};
   set{switch(i){case 0:damage=value;break;case 1:fireInterval=value;break;case 2:range=value;break;case 3:recoil=value;break;case 4:nanoMax=value;break;case 5:nanoPerShot=value;break;case 6:nanoRegen=value;break;case 7:aimAssist=value;break;case 8:accuracy=value;break;case 9:spread=value;break;case 10:criticalChance=value;break;case 11:criticalMultiplier=value;break;case 12:projectileVelocity=value;break;case 13:reloadTime=value;break;case 14:heatGeneration=value;break;case 15:cooling=value;break;case 16:durability=value;break;case 17:armourPenetration=value;break;case 18:sway=value;break;case 19:sideKick=value;break;case 20:recovery=value;break;case 21:scatterGrowth=value;break;default:throw new ArgumentOutOfRangeException(nameof(i));}}
  }
  public float this[string id]=>this[IndexOf(id)];
  // Initial values for new catalog entries only; the saved WardCrafting asset is authoritative.
  // 2 Oct 2026 next-level pass: range 30 m (full damage to 18 m, WeaponBallistics), 4° spread.
  public static WeaponStats ScrapPistol=>new WeaponStats{damage=34,fireInterval=.28f,range=30,recoil=38,nanoMax=100,nanoPerShot=9,nanoRegen=30,aimAssist=3.5f,spread=4};
  public static WeaponStats DefaultMin=>new WeaponStats{damage=1,fireInterval=.08f,range=10,recoil=0,nanoMax=20,nanoPerShot=1,nanoRegen=1,aimAssist=0};
  public static WeaponStats DefaultMax=>new WeaponStats{damage=400,fireInterval=2,range=200,recoil=100,nanoMax=400,nanoPerShot=60,nanoRegen=200,aimAssist=12,accuracy=100,spread=180,criticalChance=100,criticalMultiplier=10,projectileVelocity=10000,reloadTime=60,heatGeneration=1000,cooling=1000,durability=100000,armourPenetration=100,sway=20,sideKick=20,recovery=5,scatterGrowth=5};
  public bool Approximately(WeaponStats other){for(int i=0;i<Count;i++)if(Math.Abs(this[i]-other[i])>.0005f)return false;return true;}
  public override string ToString(){var self=this;return string.Join(", ",Ids.Select((id,i)=>id+"="+self[i]));}
 }

 /// The fitted mods of one weapon and the effective stats they produce. Pure C#: no Unity lifecycle, no per-frame work.
 /// Effective stat = clamp(round3((base + Σadd) × (1 + Σpercent / 100)), min, max).
 public sealed class WeaponLoadout
 {
  readonly CraftWeapon weapon;
  readonly string[] slots;
  readonly Dictionary<string,CraftModifier> byItem=new Dictionary<string,CraftModifier>();
  readonly Dictionary<string,string> fitted=new Dictionary<string,string>();
  /// Crafted quality per fitted slot (20 Nov 2026); a slot not listed is Standard.
  readonly Dictionary<string,CraftQuality> quality=new Dictionary<string,CraftQuality>();
  public string WeaponId=>weapon.id;
  public string WeaponName=>weapon.name;
  public string ItemId=>weapon.itemId;
  public WeaponStats Base=>weapon.stats;
  public WeaponStats Stats {get;private set;}
  public WeaponStats WithCharacter(CharacterModel character)
  {
   var result=WeaponStatPipeline.ApplyCharacter(Stats,character,weapon.id);
   for(int i=0;i<WeaponStats.Count;i++)
   {
    float hi=weapon.maxStats[i];
    if(i>=8&&weapon.minStats[i]==0&&hi==0)hi=WeaponStats.DefaultMax[i];
    result[i]=Mathf.Clamp(result[i],weapon.minStats[i],Mathf.Max(weapon.minStats[i],hi));
   }
   return result;
  }
  public IReadOnlyList<string> Slots=>Array.AsReadOnly(slots);
  /// Raised after any fit or removal, once the cached stats are current.
  public event Action Changed;
  public WeaponLoadout(CraftWeapon weapon,IEnumerable<CraftModifier> modifiers,IEnumerable<string> recipeSlots=null)
  {
   this.weapon=weapon??throw new ArgumentNullException(nameof(weapon));
   slots=(recipeSlots??weapon.slots??Array.Empty<string>()).Where(x=>!string.IsNullOrEmpty(x)).Distinct().ToArray();
   if(modifiers!=null)foreach(var m in modifiers)if(m!=null&&!string.IsNullOrEmpty(m.itemId)&&!byItem.ContainsKey(m.itemId))byItem.Add(m.itemId,m);
   Stats=Compute(weapon,Enumerable.Empty<CraftModifier>());
   ResetCondition();
  }
  // ---- Condition (20 Nov 2026, Phase 3). The weapon's Durability stat is its full condition; weapons with 0 do not wear.
  /// True when this weapon has a condition (its base Durability stat is above 0).
  public bool HasCondition=>weapon.stats.durability>0;
  /// Current condition, 0 = jammed.
  public float Durability {get;private set;}
  /// Highest condition field repairs can bring it back to; each field repair lowers it, a bench overhaul restores it.
  public float MaxDurability {get;private set;}
  /// Field repairs made since the last overhaul.
  public int Repairs {get;private set;}
  public float WearPerShot=>Mathf.Max(0,weapon.wearPerShot);
  public bool Jammed=>HasCondition&&Durability<=0;
  /// Raised when condition changes by a whole point or on any repair, overhaul or restore (not on every shot).
  public event Action ConditionChanged;
  /// New or overhauled: full condition at the full cap, no repairs.
  internal void ResetCondition()
  {
   MaxDurability=Mathf.Max(0,weapon.stats.durability);Durability=MaxDurability;Repairs=0;
   ConditionChanged?.Invoke();
  }
  /// Save restore. Values are clamped (cap to the weapon's own, condition to the cap).
  internal void SetCondition(float durability,float max,int repairs)
  {
   float full=Mathf.Max(0,weapon.stats.durability);
   MaxDurability=Mathf.Clamp(float.IsNaN(max)?full:max,0,full);
   Durability=Mathf.Clamp(float.IsNaN(durability)?MaxDurability:durability,0,MaxDurability);
   Repairs=Math.Max(0,repairs);
   ConditionChanged?.Invoke();
  }
  /// One shot's wear. Returns the condition after it.
  public float Wear(float amount)
  {
   if(!HasCondition||amount<=0)return Durability;
   float before=Durability;Durability=Mathf.Max(0,Durability-amount);
   if(Mathf.Ceil(before)!=Mathf.Ceil(Durability))ConditionChanged?.Invoke();
   return Durability;
  }
  /// A field repair: lowers the cap by capLoss, then restores up to amount (never above the new cap).
  internal void ApplyRepair(float amount,float capLoss)
  {
   MaxDurability=Mathf.Max(0,MaxDurability-Mathf.Max(0,capLoss));
   Durability=Mathf.Min(MaxDurability,Durability+Mathf.Max(0,amount));
   Repairs++;ConditionChanged?.Invoke();
  }
  public string Fitted(string slot)=>slot!=null&&fitted.TryGetValue(slot,out var id)?id:null;
  /// Crafted quality of the mod in this slot (Standard when empty, timed or from an older save).
  public CraftQuality Quality(string slot)=>slot!=null&&fitted.ContainsKey(slot)&&quality.TryGetValue(slot,out var q)?q:CraftQuality.Standard;
  IEnumerable<KeyValuePair<CraftModifier,CraftQuality>> Effective=>fitted.Select(x=>new KeyValuePair<CraftModifier,CraftQuality>(Modifier(x.Value),Quality(x.Key)));
  public IEnumerable<KeyValuePair<string,string>> FittedMods=>fitted;
  public CraftModifier Modifier(string itemId)=>itemId!=null&&byItem.TryGetValue(itemId,out var m)?m:null;
  public bool HasSlot(string slot)=>slot!=null&&Array.IndexOf(slots,slot)>=0;
  /// A mod fits when it names this weapon and one of its slots.
  public bool Accepts(CraftModifier mod)=>mod!=null&&mod.weaponIds!=null&&Array.IndexOf(mod.weaponIds,weapon.id)>=0&&HasSlot(mod.slot);
  /// Only CraftingModel writes slots, after its pack transaction has committed.
  internal void Set(string slot,string itemId,CraftQuality q=CraftQuality.Standard)
  {
   if(string.IsNullOrEmpty(itemId)){fitted.Remove(slot);quality.Remove(slot);}
   else{fitted[slot]=itemId;if(q==CraftQuality.Standard)quality.Remove(slot);else quality[slot]=q;}
   Stats=Compute(weapon,Effective);
   Changed?.Invoke();
  }
  /// Restores all slots at once (save load). Unknown or unfit items are dropped and reported.
  internal List<string> Replace(IEnumerable<KeyValuePair<string,string>> slots)=>Replace(slots,null);
  /// qualities: slot to quality for the restored slots (null or missing = Standard).
  internal List<string> Replace(IEnumerable<KeyValuePair<string,string>> slots,IDictionary<string,CraftQuality> qualities)
  {
   var rejected=new List<string>();fitted.Clear();quality.Clear();
   if(slots!=null)foreach(var pair in slots)
   {
    var mod=Modifier(pair.Value);
    if(mod==null||!Accepts(mod)||mod.slot!=pair.Key||fitted.ContainsKey(pair.Key)){if(pair.Value!=null)rejected.Add(pair.Value);continue;}
    fitted[pair.Key]=pair.Value;
    if(qualities!=null&&qualities.TryGetValue(pair.Key,out var q)&&q!=CraftQuality.Standard)quality[pair.Key]=q;
   }
   Stats=Compute(weapon,Effective);
   Changed?.Invoke();
   return rejected;
  }
  /// Stats if the slot held this item instead (null = the slot emptied). Does not change the loadout.
  public WeaponStats Preview(string slot,string itemId,CraftQuality q=CraftQuality.Standard)
  {
   var mods=fitted.Where(x=>x.Key!=slot).Select(x=>new KeyValuePair<CraftModifier,CraftQuality>(Modifier(x.Value),Quality(x.Key))).ToList();
   if(!HasSlot(slot))return Stats;
   if(!string.IsNullOrEmpty(itemId))
   {
    var mod=Modifier(itemId);
    if(!Accepts(mod)||mod.slot!=slot)return Stats;
    mods.Add(new KeyValuePair<CraftModifier,CraftQuality>(mod,q));
   }
   return Compute(weapon,mods);
  }
  public static WeaponStats Compute(CraftWeapon weapon,IEnumerable<CraftModifier> mods)
   =>Compute(weapon,(mods??Enumerable.Empty<CraftModifier>()).Select(m=>new KeyValuePair<CraftModifier,CraftQuality>(m,CraftQuality.Standard)));
  /// Quality scale for effects without explicit per-quality values (Rough, Standard, Fine).
  public static readonly float[] DefaultQualityScale={.75f,1f,1.25f};
  /// One effect's value at a crafted quality: CraftEffect.byQuality when it holds three values, otherwise value times the
  /// modifier's qualityScale (three values) or DefaultQualityScale. Standard is always the effect's own value.
  public static float EffectValue(CraftModifier mod,CraftEffect effect,CraftQuality q)
  {
   if(effect==null)return 0;
   int i=Mathf.Clamp((int)q,0,2);
   if(q==CraftQuality.Standard&&(effect.byQuality==null||effect.byQuality.Length!=3))return effect.value;
   if(effect.byQuality!=null&&effect.byQuality.Length==3)return effect.byQuality[i];
   var scale=mod?.qualityScale!=null&&mod.qualityScale.Length==3?mod.qualityScale:DefaultQualityScale;
   return effect.value*scale[i];
  }
  public static WeaponStats Compute(CraftWeapon weapon,IEnumerable<KeyValuePair<CraftModifier,CraftQuality>> mods)
  {
   var add=new float[WeaponStats.Count];var percent=new float[WeaponStats.Count];
   foreach(var pair in mods??Enumerable.Empty<KeyValuePair<CraftModifier,CraftQuality>>())
   {
    var mod=pair.Key;
    if(mod?.effects==null)continue;
    foreach(var effect in mod.effects)
    {
     int i=WeaponStats.IndexOf(effect?.stat);if(i<0)continue;
     float value=EffectValue(mod,effect,pair.Value);
     if(float.IsNaN(value)||float.IsInfinity(value))continue;
     if(effect.op=="add")add[i]+=value;else if(effect.op=="percent")percent[i]+=value;
    }
   }
   var result=new WeaponStats();
   for(int i=0;i<WeaponStats.Count;i++)
   {
    double value=Math.Round((weapon.stats[i]+(double)add[i])*(1+percent[i]/100.0),3,MidpointRounding.AwayFromZero);
    float lo=weapon.minStats[i],hi=weapon.maxStats[i];
    // Older serialized weapons predate these fields and have zero bounds for them.
    if(i>=8&&lo==0&&hi==0)hi=WeaponStats.DefaultMax[i];
    result[i]=(float)Math.Max(lo,Math.Min(hi>=lo?hi:lo,value));
   }
   return result;
  }
 }
 public enum ShotOutcome { Fire, Misfire, Jammed }
 /// Pure condition rules (ConditionRules in the catalog): spread, misfire, jam, field repair and broken state.
 public static class WeaponCondition
 {
  /// Shot cone multiplier: 1 above SpreadBelow, rising linearly to SpreadMaxScale at 0.
  public static float SpreadScale(ConditionRules r,float durability)
  {
   if(r==null||r.spreadBelow<=0||durability>=r.spreadBelow)return 1;
   float t=1-Mathf.Clamp01(durability/r.spreadBelow);
   return Mathf.Lerp(1,Mathf.Max(1,r.spreadMaxScale),t);
  }
  /// Misfire chance per trigger pull: 0 at MisfireBelow, MisfireMaxChance as condition nears 0 (0 itself is a jam, not a misfire).
  public static float MisfireChance(ConditionRules r,float durability)
  {
   if(r==null||r.misfireBelow<=0||durability>=r.misfireBelow||durability<=0)return 0;
   return Mathf.Lerp(0,Mathf.Clamp01(r.misfireMaxChance),1-Mathf.Clamp01(durability/r.misfireBelow));
  }
  /// What a trigger pull does: roll is a uniform 0..1 sample.
  public static ShotOutcome BeforeShot(WeaponLoadout loadout,ConditionRules r,float roll)
  {
   if(loadout==null||!loadout.HasCondition)return ShotOutcome.Fire;
   if(loadout.Durability<=0)return ShotOutcome.Jammed;
   return roll<MisfireChance(r,loadout.Durability)?ShotOutcome.Misfire:ShotOutcome.Fire;
  }
  /// Broken for field repair: the cap fell under BrokenBelow, or every repair entry was used.
  public static bool IsBroken(WeaponLoadout loadout,ConditionRules r)
   =>loadout!=null&&loadout.HasCondition&&r!=null&&(loadout.MaxDurability<r.brokenBelow||loadout.Repairs>=(r.repairAmounts?.Length??0));
  /// Condition the next field repair would restore (0 when none remain).
  public static float NextRepairAmount(WeaponLoadout loadout,ConditionRules r)
   =>loadout!=null&&r?.repairAmounts!=null&&loadout.Repairs>=0&&loadout.Repairs<r.repairAmounts.Length?Mathf.Max(0,r.repairAmounts[loadout.Repairs]):0;
  /// "Condition 76 / 92" with a state word: jammed, worn, broken.
  public static string Label(WeaponLoadout loadout,ConditionRules r)
  {
   if(loadout==null||!loadout.HasCondition)return "";
   string text=$"Condition {Mathf.Ceil(loadout.Durability):0} / {Mathf.Floor(loadout.MaxDurability):0}";
   if(loadout.Jammed)text+=" · jammed";
   else if(r!=null&&loadout.Durability<r.misfireBelow)text+=" · misfires";
   else if(r!=null&&loadout.Durability<r.spreadBelow)text+=" · worn";
   if(IsBroken(loadout,r))text+=" · needs a bench overhaul";
   return text;
  }
 }
 /// The same character contribution is used by combat and inspection panels after socket effects.
 /// Accuracy (2 Oct 2026): weapon base + the character's accuracy derived stat + the weapon's skill (pistol, rifle, …
 /// by WeaponBallistics.SkillFor) × WeaponBallistics.SkillAccuracyPerPoint, clamped to 0..100.
 public static class WeaponStatPipeline
 {
  public static WeaponStats ApplyCharacter(WeaponStats modified,CharacterModel character)=>ApplyCharacter(modified,character,null);
  public static WeaponStats ApplyCharacter(WeaponStats modified,CharacterModel character,string weaponId)
  {
   if(character==null)return modified;
   bool Has(string id)=>character.Data.derivedStats.Any(x=>x.id==id);
   if(Has("rangedDamage"))modified.damage*=Mathf.Max(0,character.Stat("rangedDamage"));
   if(Has("recoilControl"))modified.recoil*=1-Mathf.Clamp01(character.Stat("recoilControl"));
   float characterAccuracy=Has("accuracy")?character.Stat("accuracy"):0;
   var skill=WeaponBallistics.SkillFor(weaponId);
   float skillValue=skill!=null&&character.Data.skills!=null&&character.Data.skills.Any(x=>x!=null&&x.id==skill)?character.Stat(skill):0;
   modified.accuracy=WeaponBallistics.Accuracy(modified.accuracy,characterAccuracy,skillValue);
   if(Has("criticalChance"))modified.criticalChance=Mathf.Clamp(modified.criticalChance+character.Stat("criticalChance")*100,0,100);
   return modified;
  }
 }
}
