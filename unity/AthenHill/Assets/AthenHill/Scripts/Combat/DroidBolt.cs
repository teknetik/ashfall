using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// A ranged droid's shot: a visible, dodgeable bolt (not a hitscan). It flies straight at Speed, hurts the player if
 /// it passes within Hit Radius of their body, and bursts on the first solid surface (optionally splashing the player
 /// within Splash Radius). Pooled per prefab; bolts hang in the air while a city modal is open, like the droids.
 public class DroidBolt:MonoBehaviour
 {
  [Min(.01f)]public float hitRadius=.32f;
  [Min(1)]public float maxDistance=80;
  [Tooltip("Splash (heavy lancer bolts): the player takes Splash Damage within this radius of the burst. 0 = none.")]
  [Min(0)]public float splashRadius,splashDamage;
  public LayerMask worldMask=~(1<<8);
  [Tooltip("Glowing core, scaled along the flight direction with speed.")]
  public Transform core;
  public TrailRenderer trail;
  [Tooltip("Burst played where the bolt ends (child; detached while it plays).")]
  public ParticleSystem impact;
  [Tooltip("Additive glow billboards that ride with the bolt (halo and hot core, 19 Nov 2026). No lights: the OpenGL player draws at most 32 per camera.")]
  public ParticleSystem[] glow=new ParticleSystem[0];
  [Tooltip("A short additive flash where the bolt ends (child; detached while it plays, like Impact).")]
  public ParticleSystem impactFlash;
  public AudioSource impactAudio;
  public AudioClip[] impactClips=new AudioClip[0];
  [Tooltip("Played as the bolt passes close to the player's head (near miss).")]
  public AudioClip[] flybyClips=new AudioClip[0];
  [Min(0)]public float flybyDistance=2.4f;
  [Tooltip("Fly-by and impact levels (19 Nov 2026; the old fixed values were 0.7 and 1).")]
  [Range(0,1)]public float flybyVolume=.7f,impactVolume=1;
  int lastFlyby=-1,lastImpact=-1;
  /// QA (19 Nov 2026 native check): fly-by and impact sounds played, across all bolts.
  public static int Flybys,Impacts;
  public FeralDroid Owner {get;private set;}
  public bool Flying {get;private set;}
  public DroidBolt Prefab {get;private set;}
  Vector3 velocity,origin;float damage,travelled;bool flybyDone;
  PlayerCombat target;GameSession session;
  readonly RaycastHit[] hits=new RaycastHit[8];
  static readonly Dictionary<DroidBolt,Stack<DroidBolt>> pools=new Dictionary<DroidBolt,Stack<DroidBolt>>();
  static Transform poolRoot;
  /// Prevents dead, inactive, staggered or EMP-stunned droids from launching stale bolts.
  public static bool CanOwnerFire(bool hasOwner,bool activeInHierarchy,bool alive,DroidState state)
   =>!hasOwner||activeInHierarchy&&alive&&state!=DroidState.Dead&&state!=DroidState.Stagger;
  /// Splash damage at distance from the burst centre (linear taper to 40 % at the edge, 0 outside).
  public static float SplashDamageAt(float distance,float splashRadius,float splashDamage)
  {
   if(splashRadius<=0||splashDamage<=0||float.IsNaN(distance)||distance<0||distance>=splashRadius)return 0;
   return splashDamage*(1-distance/splashRadius*.6f);
  }
  /// Takes a pooled bolt (or makes one) and fires it from origin along direction.
  public static DroidBolt Fire(DroidBolt prefab,FeralDroid owner,Vector3 from,Vector3 direction,float speed,float damage)
  {
   if(!prefab||direction.sqrMagnitude<1e-6f||speed<=0)return null;
   if(owner&&!CanOwnerFire(true,owner.gameObject.activeInHierarchy,owner.Health&&owner.Health.Alive,owner.State))return null;
   if(!pools.TryGetValue(prefab,out var pool))pools[prefab]=pool=new Stack<DroidBolt>();
   DroidBolt b=null;
   while(pool.Count>0&&!b)b=pool.Pop();
   if(!b)
   {
    if(!poolRoot){poolRoot=new GameObject("Droid bolts").transform;}
    b=Instantiate(prefab,poolRoot);b.name=prefab.name;b.Prefab=prefab;
   }
   b.Launch(owner,from,direction,speed,damage);
   return b;
  }
  void Launch(FeralDroid owner,Vector3 from,Vector3 direction,float speed,float dmg)
  {
   Owner=owner;target=owner?owner.Player:null;session=owner?owner.Session:null;
   origin=owner?owner.transform.position:from;
   transform.SetPositionAndRotation(from,Quaternion.LookRotation(direction));
   velocity=direction.normalized*speed;damage=dmg;travelled=0;flybyDone=false;Flying=true;
   gameObject.SetActive(true);
   if(core)core.gameObject.SetActive(true);
   if(trail){trail.Clear();trail.emitting=true;}
   if(impact){impact.transform.SetParent(transform,false);impact.transform.localPosition=Vector3.zero;}
   if(impactFlash){impactFlash.transform.SetParent(transform,false);impactFlash.transform.localPosition=Vector3.zero;}
   if(glow!=null)foreach(var g in glow)if(g){g.Clear(true);g.Play(true);}
  }
  void Update()
  {
   if(!Flying)return;
   if(session&&session.State!=CityState.Play)return;
   float dt=Time.deltaTime;var step=velocity*dt;float len=step.magnitude;
   if(len<1e-5f)return;
   var from=transform.position;var dir=step/len;
   // Check solid world geometry first so a bolt cannot clip through cover to hit a player standing just behind it.
   int n=Physics.SphereCastNonAlloc(from,.05f,dir,hits,len,worldMask,QueryTriggerInteraction.Ignore);
   float best=float.MaxValue;int bi=-1;
   for(int i=0;i<n;i++)
   {
    var c=hits[i].collider;
    if(c.GetComponentInParent<FeralDroid>()||c.GetComponentInParent<PlayerMotor>())continue;
    if(hits[i].distance<best){best=hits[i].distance;bi=i;}
   }
   var segmentEnd=bi>=0?hits[bi].point:from+step;
   // the player's body: a capsule from the feet to the head
   if(target&&target.Health&&target.Health.Alive)
   {
    var feet=target.transform.position;
    float d=SegmentToSegment(from,segmentEnd,feet+Vector3.up*.35f,feet+Vector3.up*1.55f,out var hitPoint);
    bool invulnerable=target.motor&&target.motor.DodgeInvulnerable;
    if(!invulnerable&&d<=hitRadius+.38f){HitPlayer(hitPoint);return;}
    if(!flybyDone&&flybyClips.Length>0&&d<flybyDistance)
    {
     flybyDone=true;var c=CombatAudio.Pick(flybyClips,ref lastFlyby);
     // the near miss is the player's cue to move: it always plays (only an identical clip on the same frame is dropped)
     if(c&&impactAudio&&VoiceLimiter.Droids.TryAcquire(Time.time,c.GetHashCode(),c.length,true)){impactAudio.PlayOneShot(c,flybyVolume);Flybys++;}
    }
   }
   if(bi>=0){transform.position=hits[bi].point;Burst(hits[bi].point,hits[bi].normal,false);return;}
   transform.position=from+step;travelled+=len;
   if(travelled>=maxDistance)Recycle();
  }
  void HitPlayer(Vector3 at)
  {
   target.Health.Damage(damage,origin);
   transform.position=at;Burst(at,-velocity.normalized,true);
  }
  void Burst(Vector3 at,Vector3 normal,bool directHit)
  {
   Flying=false;
   bool invulnerable=target&&target.motor&&target.motor.DodgeInvulnerable;
   if(!directHit&&!invulnerable&&splashRadius>0&&splashDamage>0&&target&&target.Health&&target.Health.Alive)
   {
    float d=Vector3.Distance(at,target.transform.position+Vector3.up*.9f);
    float splash=SplashDamageAt(d,splashRadius,splashDamage);
    if(splash>0&&!Physics.Linecast(at+normal*.1f,target.transform.position+Vector3.up*.9f,worldMask,QueryTriggerInteraction.Ignore))
     target.Health.Damage(splash,origin);
   }
   if(core)core.gameObject.SetActive(false);
   if(trail)trail.emitting=false;
   if(glow!=null)foreach(var g in glow)if(g)g.Clear(true);
   bool reduced=session&&session.reducedMotion;
   if(impactFlash)
   {
    impactFlash.transform.SetParent(null,true);impactFlash.transform.position=at+normal*.05f;
    impactFlash.Emit(1);
   }
   if(impact)
   {
    impact.transform.SetParent(null,true);impact.transform.position=at;
    impact.transform.rotation=normal.sqrMagnitude>1e-6f?Quaternion.LookRotation(normal):Quaternion.identity;
    impact.Emit(reduced?6:18);
   }
   if(impactAudio&&impactClips.Length>0)
   {
    impactAudio.transform.position=at;var c=CombatAudio.Pick(impactClips,ref lastImpact);
    if(c&&VoiceLimiter.Droids.TryAcquire(Time.time,c.GetHashCode(),c.length,false)){impactAudio.PlayOneShot(c,impactVolume);Impacts++;}
   }
   // long enough for the impact sound and sparks to finish before the bolt goes back to its pool
   Invoke(nameof(Recycle),Mathf.Max(.9f,trail?trail.time:0));
  }
  void Recycle()
  {
   CancelInvoke();Flying=false;
   if(impact&&impact.transform.parent!=transform){impact.transform.SetParent(transform,true);}
   if(impactFlash&&impactFlash.transform.parent!=transform){impactFlash.transform.SetParent(transform,true);}
   gameObject.SetActive(false);
   if(Prefab&&pools.TryGetValue(Prefab,out var pool))pool.Push(this);
  }
  /// Closest distance between segments p1-q1 and p2-q2; point on the second segment (the target) nearest the first.
  public static float SegmentToSegment(Vector3 p1,Vector3 q1,Vector3 p2,Vector3 q2,out Vector3 onSecond)
  {
   Vector3 d1=q1-p1,d2=q2-p2,r=p1-p2;
   float a=Vector3.Dot(d1,d1),e=Vector3.Dot(d2,d2),f=Vector3.Dot(d2,r);
   float s,t;
   if(a<=1e-8f&&e<=1e-8f){onSecond=p2;return r.magnitude;}
   if(a<=1e-8f){s=0;t=Mathf.Clamp01(f/e);}
   else
   {
    float c=Vector3.Dot(d1,r);
    if(e<=1e-8f){t=0;s=Mathf.Clamp01(-c/a);}
    else
    {
     float b=Vector3.Dot(d1,d2),den=a*e-b*b;
     s=den!=0?Mathf.Clamp01((b*f-c*e)/den):0;
     t=(b*s+f)/e;
     if(t<0){t=0;s=Mathf.Clamp01(-c/a);}else if(t>1){t=1;s=Mathf.Clamp01((b-c)/a);}
    }
   }
   onSecond=p2+d2*t;
   return Vector3.Distance(p1+d1*s,onSecond);
  }
  void OnDestroy(){if(Prefab&&pools.TryGetValue(Prefab,out var pool)&&pool.Count==0)pools.Remove(Prefab);}
 }
}
