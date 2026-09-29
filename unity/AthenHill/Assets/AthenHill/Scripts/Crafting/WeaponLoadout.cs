using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Scrap-pistol numbers. Field names are the stat IDs that CraftEffect.stat refers to.
 [Serializable] public struct WeaponStats
 {
  [Min(0)]public float damage,fireInterval,range,recoil,nanoMax,nanoPerShot,nanoRegen,aimAssist;
  public static readonly string[] Ids={"damage","fireInterval","range","recoil","nanoMax","nanoPerShot","nanoRegen","aimAssist"};
  public const int Count=8;
  public static int IndexOf(string id)=>id==null?-1:Array.IndexOf(Ids,id);
  public float this[int i]
  {
   get=>i switch{0=>damage,1=>fireInterval,2=>range,3=>recoil,4=>nanoMax,5=>nanoPerShot,6=>nanoRegen,7=>aimAssist,_=>throw new ArgumentOutOfRangeException(nameof(i))};
   set{switch(i){case 0:damage=value;break;case 1:fireInterval=value;break;case 2:range=value;break;case 3:recoil=value;break;case 4:nanoMax=value;break;case 5:nanoPerShot=value;break;case 6:nanoRegen=value;break;case 7:aimAssist=value;break;default:throw new ArgumentOutOfRangeException(nameof(i));}}
  }
  public float this[string id]=>this[IndexOf(id)];
  // Initial values for new catalog entries only; the saved WardCrafting asset is authoritative.
  public static WeaponStats ScrapPistol=>new WeaponStats{damage=34,fireInterval=.28f,range=70,recoil=38,nanoMax=100,nanoPerShot=9,nanoRegen=30,aimAssist=3.5f};
  public static WeaponStats DefaultMin=>new WeaponStats{damage=1,fireInterval=.08f,range=10,recoil=0,nanoMax=20,nanoPerShot=1,nanoRegen=1,aimAssist=0};
  public static WeaponStats DefaultMax=>new WeaponStats{damage=400,fireInterval=2,range=200,recoil=100,nanoMax=400,nanoPerShot=60,nanoRegen=200,aimAssist=12};
  public bool Approximately(WeaponStats other){for(int i=0;i<Count;i++)if(Math.Abs(this[i]-other[i])>.0005f)return false;return true;}
  public override string ToString(){var self=this;return string.Join(", ",Ids.Select((id,i)=>id+"="+self[i]));}
 }

 /// The fitted mods of one weapon and the effective stats they produce. Pure C#: no Unity lifecycle, no per-frame work.
 /// Effective stat = clamp(round3((base + Σadd) × (1 + Σpercent / 100)), min, max).
 public sealed class WeaponLoadout
 {
  readonly CraftWeapon weapon;
  readonly Dictionary<string,CraftModifier> byItem=new Dictionary<string,CraftModifier>();
  readonly Dictionary<string,string> fitted=new Dictionary<string,string>();
  public string WeaponId=>weapon.id;
  public string WeaponName=>weapon.name;
  public WeaponStats Base=>weapon.stats;
  public WeaponStats Stats {get;private set;}
  public IReadOnlyList<string> Slots=>weapon.slots??Array.Empty<string>();
  /// Raised after any fit or removal, once the cached stats are current.
  public event Action Changed;
  public WeaponLoadout(CraftWeapon weapon,IEnumerable<CraftModifier> modifiers)
  {
   this.weapon=weapon??throw new ArgumentNullException(nameof(weapon));
   if(modifiers!=null)foreach(var m in modifiers)if(m!=null&&!string.IsNullOrEmpty(m.itemId)&&!byItem.ContainsKey(m.itemId))byItem.Add(m.itemId,m);
   Stats=Compute(weapon,Enumerable.Empty<CraftModifier>());
  }
  public string Fitted(string slot)=>slot!=null&&fitted.TryGetValue(slot,out var id)?id:null;
  public IEnumerable<KeyValuePair<string,string>> FittedMods=>fitted;
  public CraftModifier Modifier(string itemId)=>itemId!=null&&byItem.TryGetValue(itemId,out var m)?m:null;
  public bool HasSlot(string slot)=>weapon.slots!=null&&Array.IndexOf(weapon.slots,slot)>=0;
  /// A mod fits when it names this weapon and one of its slots.
  public bool Accepts(CraftModifier mod)=>mod!=null&&mod.weaponIds!=null&&Array.IndexOf(mod.weaponIds,weapon.id)>=0&&HasSlot(mod.slot);
  /// Only CraftingModel writes slots, after its pack transaction has committed.
  internal void Set(string slot,string itemId)
  {
   if(string.IsNullOrEmpty(itemId))fitted.Remove(slot);else fitted[slot]=itemId;
   Stats=Compute(weapon,fitted.Values.Select(Modifier));
   Changed?.Invoke();
  }
  /// Restores all slots at once (save load). Unknown or unfit items are dropped and reported.
  internal List<string> Replace(IEnumerable<KeyValuePair<string,string>> slots)
  {
   var rejected=new List<string>();fitted.Clear();
   if(slots!=null)foreach(var pair in slots)
   {
    var mod=Modifier(pair.Value);
    if(mod==null||!Accepts(mod)||mod.slot!=pair.Key||fitted.ContainsKey(pair.Key)){if(pair.Value!=null)rejected.Add(pair.Value);continue;}
    fitted[pair.Key]=pair.Value;
   }
   Stats=Compute(weapon,fitted.Values.Select(Modifier));
   Changed?.Invoke();
   return rejected;
  }
  /// Stats if the slot held this item instead (null = the slot emptied). Does not change the loadout.
  public WeaponStats Preview(string slot,string itemId)
  {
   var mods=fitted.Where(x=>x.Key!=slot).Select(x=>Modifier(x.Value)).ToList();
   if(!string.IsNullOrEmpty(itemId))mods.Add(Modifier(itemId));
   return Compute(weapon,mods);
  }
  public static WeaponStats Compute(CraftWeapon weapon,IEnumerable<CraftModifier> mods)
  {
   var add=new float[WeaponStats.Count];var percent=new float[WeaponStats.Count];
   foreach(var mod in mods)
   {
    if(mod?.effects==null)continue;
    foreach(var effect in mod.effects)
    {
     int i=WeaponStats.IndexOf(effect?.stat);if(i<0)continue;
     if(effect.op=="add")add[i]+=effect.value;else if(effect.op=="percent")percent[i]+=effect.value;
    }
   }
   var result=new WeaponStats();
   for(int i=0;i<WeaponStats.Count;i++)
   {
    double value=Math.Round((weapon.stats[i]+(double)add[i])*(1+percent[i]/100.0),3,MidpointRounding.AwayFromZero);
    float lo=weapon.minStats[i],hi=weapon.maxStats[i];
    result[i]=(float)Math.Max(lo,Math.Min(hi>=lo?hi:lo,value));
   }
   return result;
  }
 }
}
