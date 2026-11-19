using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// One weapon's layered shot and foley (19 Nov 2026 combat audio pass, art/showcase_20261119/combat_audio). PlayerCombat
 /// plays the set whose Weapon Id matches the bound loadout; a weapon without a usable set keeps PlayerCombat's own
 /// layer arrays (the scrap pistol's), so nothing changes for it.
 [Serializable] public class WeaponSoundSet
 {
  [Tooltip("Crafting weapon definition id (WardCrafting.asset), e.g. weapon_field_rifle.")]
  public string weaponId;
  public AudioClip[] mech=new AudioClip[0],body=new AudioClip[0],tail=new AudioClip[0];
  public AudioClip[] empty=new AudioClip[0],draw=new AudioClip[0],holster=new AudioClip[0];
  [Range(0,1.5f)]public float mechGain=.55f,bodyGain=.69f,tailGain=.37f;
  [Tooltip("Random pitch range per shot (both layers move together, the tail separately on a tail source).")]
  public Vector2 pitch=new Vector2(.97f,1.03f);
  [Tooltip("Tail gain while a burst is held (a shot within 1.5 fire intervals of the last): overlapping tails would otherwise build into a low-mid wash.")]
  [Range(0,1)]public float burstTailScale=1;
  /// The body layer is what makes it a shot; without it the set is ignored.
  public bool Usable=>body!=null&&Array.Exists(body,c=>c);
 }
 public static class CombatAudio
 {
  /// The set for this weapon id, or null (use the legacy arrays). Empty ids never match.
  public static WeaponSoundSet SelectSet(WeaponSoundSet[] sets,string weaponId)
  {
   if(sets==null||string.IsNullOrEmpty(weaponId))return null;
   foreach(var s in sets)if(s!=null&&s.weaponId==weaponId&&s.Usable)return s;
   return null;
  }
  /// Index in [0,count) from two uniform randoms, never equal to last when count > 1: a different variant is always
  /// one of the others with equal chance.
  public static int PickIndex(int count,int last,float r1,float r2)
  {
   if(count<=0)return -1;
   int i=Mathf.Min(count-1,(int)(Mathf.Clamp01(r1)*count));
   if(count>1&&i==last)i=(i+1+Mathf.Min(count-2,(int)(Mathf.Clamp01(r2)*(count-1))))%count;
   return i;
  }
  public static AudioClip Pick(AudioClip[] clips,ref int last)
  {
   if(clips==null||clips.Length==0)return null;
   int i=PickIndex(clips.Length,last,UnityEngine.Random.value,UnityEngine.Random.value);
   last=i;return clips[i];
  }
  /// A variant from the override array when it holds any clip, else the shared clip (the droid's single field).
  public static AudioClip Choose(AudioClip[] overrides,AudioClip shared,ref int last)
  {
   if(overrides!=null&&Array.Exists(overrides,c=>c))
   {
    for(int tries=0;tries<4;tries++){var c=Pick(overrides,ref last);if(c)return c;}
    foreach(var c in overrides)if(c)return c;
   }
   return shared;
  }
  /// Rolloff for an open desert: inverse distance from Min Distance (as Unity's logarithmic mode) times a fade that
  /// reaches silence exactly at Max Distance, so a sound carries a long way but never across the whole bowl (Unity's
  /// own logarithmic curve holds its last level beyond Max Distance). x is distance / Max Distance.
  public static AnimationCurve DesertRolloff(float minDistance,float maxDistance,int keys=12)
  {
   maxDistance=Mathf.Max(maxDistance,minDistance+.01f);minDistance=Mathf.Max(.01f,minDistance);
   float near=minDistance/maxDistance;keys=Mathf.Max(4,keys);
   var list=new List<Keyframe>{new Keyframe(0,1,0,0)};
   for(int k=0;k<keys;k++)
   {
    float x=Mathf.Lerp(near,1,Mathf.Pow(k/(float)(keys-1),2));   // denser near the source, where the curve bends
    // exact slopes of near*(1/x - x^2) (smoothed tangents overshoot above 1 just past Min Distance); flat inside it
    float slope=-near*(1/(x*x)+2*x);
    list.Add(new Keyframe(x,RolloffGain(x,near),k==0?0:slope,slope));
   }
   return new AnimationCurve(list.ToArray());
  }
  public static float RolloffGain(float x,float near)=>x<=near?1:Mathf.Clamp01(near/x*(1-Mathf.Pow(Mathf.Clamp01(x),3)));
  /// Sentinel rolling loop: (volume, pitch) for a ground speed. Standing still it idles at Idle Volume (the drive motor),
  /// rolling at Full Speed it reaches full volume and the top of the pitch range.
  public static Vector2 RollMix(float speed,float fullSpeed,float idleVolume,Vector2 pitch)
  {
   float t=Mathf.Clamp01(speed/Mathf.Max(.01f,fullSpeed));
   return new Vector2(Mathf.Lerp(Mathf.Clamp01(idleVolume),1,Mathf.Sqrt(t)),Mathf.Lerp(pitch.x,pitch.y,t));
  }
 }
 /// Caps how many droid and bolt one-shots sound at once so a pack fight does not stack dozens of sources on the 32
 /// real voices (ProjectSettings/AudioManager). Essential cues (alerts, attack tells, attacks, deaths: the sounds the
 /// player reacts to) always play, but the same clip is not restarted within Same Clip Window (two droids alerting on
 /// one frame only phase and double the level). Other sounds (footsteps, hit clangs, impacts) also need a free slot
 /// under Max Voices, counting every sound still playing.
 public sealed class VoiceLimiter
 {
  public int maxVoices;public float sameClipWindow;
  readonly List<(int key,float start,float end)> playing=new List<(int,float,float)>();
  public static readonly VoiceLimiter Droids=new VoiceLimiter(10,.07f);
  public VoiceLimiter(int maxVoices,float sameClipWindow){this.maxVoices=maxVoices;this.sameClipWindow=sameClipWindow;}
  public int Playing(float now){Expire(now);return playing.Count;}
  void Expire(float now){for(int i=playing.Count-1;i>=0;i--)if(playing[i].end<=now||playing[i].start>now)playing.RemoveAt(i);}
  public bool TryAcquire(float now,int key,float length,bool essential)
  {
   Expire(now);
   foreach(var p in playing)if(p.key==key&&now-p.start<sameClipWindow)return false;
   if(!essential&&playing.Count>=maxVoices)return false;
   playing.Add((key,now,now+Mathf.Max(.02f,length)));
   return true;
  }
  public void Clear()=>playing.Clear();
 }
}
