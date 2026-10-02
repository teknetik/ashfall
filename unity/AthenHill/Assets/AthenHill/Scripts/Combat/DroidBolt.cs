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
  public AudioSource impactAudio;
  public AudioClip[] impactClips=new AudioClip[0];
  [Tooltip("Played as the bolt passes close to the player's head (near miss).")]
  public AudioClip[] flybyClips=new AudioClip[0];
  [Min(0)]public float flybyDistance=2.4f;
  public FeralDroid Owner {get;private set;}
  public bool Flying {get;private set;}
  public DroidBolt Prefab {get;private set;}
  Vector3 velocity,origin;float damage,travelled;bool flybyDone;
  PlayerCombat target;GameSession session;
  readonly RaycastHit[] hits=new RaycastHit[8];
  static readonly Dictionary<DroidBolt,Stack<DroidBolt>> pools=new Dictionary<DroidBolt,Stack<DroidBolt>>();
  static Transform poolRoot;
  /// Takes a pooled bolt (or makes one) and fires it from origin along direction.
  public static DroidBolt Fire(DroidBolt prefab,FeralDroid owner,Vector3 from,Vector3 direction,float speed,float damage)
  {
   if(!prefab)return null;
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
  }
  void Update()
  {
   if(!Flying)return;
   if(session&&session.State!=CityState.Play)return;
   float dt=Time.deltaTime;var step=velocity*dt;float len=step.magnitude;
   if(len<1e-5f)return;
   var from=transform.position;var dir=step/len;
   // the player's body: a capsule from the feet to the head
   if(target&&target.Health.Alive)
   {
    var feet=target.transform.position;
    float d=SegmentToSegment(from,from+step,feet+Vector3.up*.35f,feet+Vector3.up*1.55f,out var hitPoint);
    if(d<=hitRadius+.38f){HitPlayer(hitPoint);return;}
    if(!flybyDone&&flybyClips.Length>0&&d<flybyDistance)
    {
     flybyDone=true;var c=flybyClips[Random.Range(0,flybyClips.Length)];
     if(c&&impactAudio)impactAudio.PlayOneShot(c,.7f);
    }
   }
   int n=Physics.SphereCastNonAlloc(from,.05f,dir,hits,len,worldMask,QueryTriggerInteraction.Ignore);
   float best=float.MaxValue;int bi=-1;
   for(int i=0;i<n;i++)
   {
    var c=hits[i].collider;
    if(c.GetComponentInParent<FeralDroid>()||c.GetComponentInParent<PlayerMotor>())continue;
    if(hits[i].distance<best){best=hits[i].distance;bi=i;}
   }
   if(bi>=0){transform.position=hits[bi].point;Burst(hits[bi].point,hits[bi].normal);return;}
   transform.position=from+step;travelled+=len;
   if(travelled>=maxDistance)Recycle();
  }
  void HitPlayer(Vector3 at)
  {
   target.Health.Damage(damage,origin);
   transform.position=at;Burst(at,-velocity.normalized);
  }
  void Burst(Vector3 at,Vector3 normal)
  {
   Flying=false;
   if(splashRadius>0&&splashDamage>0&&target&&target.Health.Alive)
   {
    float d=Vector3.Distance(at,target.transform.position+Vector3.up*.9f);
    if(d<splashRadius&&!Physics.Linecast(at+normal*.1f,target.transform.position+Vector3.up*.9f,worldMask,QueryTriggerInteraction.Ignore))
     target.Health.Damage(splashDamage*(1-d/splashRadius*.6f),origin);
   }
   if(core)core.gameObject.SetActive(false);
   if(trail)trail.emitting=false;
   bool reduced=session&&session.reducedMotion;
   if(impact)
   {
    impact.transform.SetParent(null,true);impact.transform.position=at;impact.transform.rotation=Quaternion.LookRotation(normal);
    impact.Emit(reduced?6:18);
   }
   if(impactAudio&&impactClips.Length>0){impactAudio.transform.position=at;var c=impactClips[Random.Range(0,impactClips.Length)];if(c)impactAudio.PlayOneShot(c);}
   // long enough for the impact sound and sparks to finish before the bolt goes back to its pool
   Invoke(nameof(Recycle),Mathf.Max(.9f,trail?trail.time:0));
  }
  void Recycle()
  {
   CancelInvoke();Flying=false;
   if(impact&&impact.transform.parent!=transform){impact.transform.SetParent(transform,true);}
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
