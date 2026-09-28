using System;
using UnityEngine;
namespace AthenHill
{
 public enum FootSurface{Stone,Sand,Gravel,Concrete,Metal,Wood}

 [Serializable]
 public class FootstepSet
 {
  public FootSurface surface;
  public AudioClip[] walk=new AudioClip[0],run=new AudioClip[0],land=new AudioClip[0];
  [Tooltip("Per-surface trim on top of the footstep level.")]
  [Range(0,2)]public float volume=1;
 }

 [Serializable]
 public class FootSurfaceRule
 {
  [Tooltip("Lower-case text matched against the collider's object name and its parents' names.")]
  public string nameContains;
  public FootSurface surface;
 }

 /// Player footsteps: one sound per foot contact (foot-bone height crossing on the animated rig), chosen by the
 /// surface under the player, never repeating the previous variant, with small pitch/volume variation.
 /// Surfaces come from collider-name rules, then the Berms ground map (a grid baked from BermsGroundSplat:
 /// gravel road / sand / crust), then the default (city paving). Replaces CityAudio's distance cadence.
 public class FootstepAudio:MonoBehaviour
 {
  public GameSession session;
  public PlayerMotor motor;
  public FollowCamera follow;
  public PlayerCombat combat;
  [Tooltip("Near-field source at the player's feet (SFX group).")]
  public AudioSource source;
  public Transform leftFoot,rightFoot;
  public FootstepSet[] sets=new FootstepSet[0];
  public FootSurfaceRule[] colliderRules=new FootSurfaceRule[0];
  public FootSurface defaultSurface=FootSurface.Stone;
  public LayerMask groundMask=~(1<<8);
  [Header("Berms ground map (baked from BermsGroundSplat)")]
  [Tooltip("Lower-case name of the Berms ground collider object.")]
  public string bermsGroundName="berms ground";
  [Tooltip("x0, z0, 1/width, 1/depth, as the BermsGround shader's _SplatRect.")]
  public Vector4 bermsRect=new Vector4(-104,-54,1f/44,1f/102);
  [HideInInspector]public int bermsWidth,bermsHeight;
  [HideInInspector]public byte[] bermsSurfaces=new byte[0];
  [Header("Contact detection")]
  [Tooltip("Foot height above the player's feet (metres) that counts as planted.")]
  [Min(0)]public float contactHeight=.07f;
  [Tooltip("The foot must rise above this before the next contact counts.")]
  [Min(0)]public float liftHeight=.12f;
  [Tooltip("Minimum seconds between steps (guards against double triggers on shuffles).")]
  [Min(0)]public float minInterval=.18f;
  [Min(.01f)]public float moveThreshold=.25f;
  [Tooltip("Fallback cadence when the rig has no foot bones.")]
  [Min(.1f)]public float walkStepDistance=.95f,runStepDistance=1.45f;
  [Header("Mix")]
  [Range(0,1)]public float volume=.32f;
  [Range(0,1)]public float runVolume=.4f,landVolume=.55f;
  [Range(0,.2f)]public float pitchJitter=.05f;
  [Range(0,6)]public float volumeJitterDb=2;
  [Tooltip("First person and aiming hear their own steps less.")]
  [Range(0,1)]public float firstPersonScale=.7f,aimingScale=.75f;
  [Min(0)]public float landingAirTime=.28f;
  public int StepCount {get;private set;}
  public int LandCount {get;private set;}
  public FootSurface LastSurface {get;private set;}
  public string LastClip {get;private set;}
  readonly int[] lastIndex=new int[64];
  bool leftUp=true,rightUp=true,wasGrounded=true;
  float lastStep,airTime,distance;
  void Awake(){for(int i=0;i<lastIndex.Length;i++)lastIndex[i]=-1;}
  void LateUpdate()
  {
   if(!motor||!source)return;
   bool play=!session||session.State==CityState.Play;
   if(!motor.Grounded){airTime+=Time.deltaTime;wasGrounded=false;leftUp=rightUp=true;return;}
   if(!wasGrounded)
   {
    wasGrounded=true;
    if(play&&airTime>=landingAirTime){Play(Surface(),2,Mathf.Clamp01(airTime/.9f)*.4f+.6f);LandCount++;lastStep=Time.time;}
    airTime=0;
   }
   airTime=0;
   if(!play||motor.Speed<moveThreshold){distance=0;return;}
   bool running=motor.Speed>4.5f;
   if(!leftFoot||!rightFoot)
   {
    distance+=motor.Speed*Mathf.Min(Time.deltaTime,.1f);
    float stride=running?runStepDistance:walkStepDistance;
    if(distance>=stride){distance%=stride;Step(running);}
    return;
   }
   float floor=motor.RenderPosition.y;
   Contact(leftFoot.position.y-floor,ref leftUp,running);
   Contact(rightFoot.position.y-floor,ref rightUp,running);
  }
  void Contact(float height,ref bool up,bool running)
  {
   if(height>liftHeight){up=true;return;}
   if(!up||height>contactHeight)return;
   up=false;
   if(Time.time-lastStep<minInterval)return;
   Step(running);
  }
  void Step(bool running){lastStep=Time.time;StepCount++;Play(Surface(),running?1:0,1);}
  void Play(FootSurface surface,int gait,float scale)
  {
   var set=Find(surface);
   var clips=set==null?null:gait==0?set.walk:gait==1?set.run:set.land;
   if(clips==null||clips.Length==0)
   {
    // Fall back: land -> run, run <-> walk, then the default surface.
    if(set!=null&&gait==2)clips=set.run;
    if((clips==null||clips.Length==0)&&set!=null)clips=gait==0?set.run:set.walk;
    if((clips==null||clips.Length==0)&&surface!=defaultSurface){Play(defaultSurface,gait,scale);return;}
    if(clips==null||clips.Length==0)return;
   }
   int slot=((int)surface*3+gait)%lastIndex.Length;
   int index=UnityEngine.Random.Range(0,clips.Length);
   if(clips.Length>1&&index==lastIndex[slot])index=(index+1+UnityEngine.Random.Range(0,clips.Length-1))%clips.Length;
   lastIndex[slot]=index;
   var clip=clips[index];if(!clip)return;
   float level=(gait==0?volume:gait==1?runVolume:landVolume)*(set!=null?set.volume:1)*scale;
   if(follow&&follow.FirstPerson)level*=firstPersonScale;
   if(combat&&combat.Aiming)level*=aimingScale;
   level*=Mathf.Pow(10,UnityEngine.Random.Range(-volumeJitterDb,volumeJitterDb)/20);
   source.pitch=1+UnityEngine.Random.Range(-pitchJitter,pitchJitter);
   source.PlayOneShot(clip,level);
   LastSurface=surface;LastClip=clip.name;
  }
  FootstepSet Find(FootSurface s){foreach(var x in sets)if(x!=null&&x.surface==s)return x;return null;}
  /// The surface under the player's feet.
  public FootSurface Surface()
  {
   var origin=motor.transform.position+Vector3.up*.4f;
   if(!Physics.Raycast(origin,Vector3.down,out var hit,1.2f,groundMask,QueryTriggerInteraction.Ignore))return defaultSurface;
   return SurfaceAt(hit.collider.transform,hit.point);
  }
  public FootSurface SurfaceAt(Transform collider,Vector3 point)
  {
   for(var t=collider;t;t=t.parent)
   {
    string n=t.name.ToLowerInvariant();
    if(!string.IsNullOrEmpty(bermsGroundName)&&n.Contains(bermsGroundName))return BermsSurface(point);
    foreach(var r in colliderRules)if(r!=null&&!string.IsNullOrEmpty(r.nameContains)&&n.Contains(r.nameContains))return r.surface;
   }
   return defaultSurface;
  }
  public FootSurface BermsSurface(Vector3 point)
  {
   if(bermsWidth<=0||bermsSurfaces==null||bermsSurfaces.Length!=bermsWidth*bermsHeight)return FootSurface.Sand;
   float u=(point.x-bermsRect.x)*bermsRect.z,v=(point.z-bermsRect.y)*bermsRect.w;
   int x=Mathf.Clamp((int)(u*bermsWidth),0,bermsWidth-1),y=Mathf.Clamp((int)(v*bermsHeight),0,bermsHeight-1);
   return (FootSurface)bermsSurfaces[y*bermsWidth+x];
  }
 }
}
