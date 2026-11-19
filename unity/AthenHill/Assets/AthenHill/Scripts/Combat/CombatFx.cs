using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// Scene-level combat presentation: watches every feral droid's Health and plays pooled, authored effects —
 /// a death burst (flash, sparks, debris, fireball, smoke plume, embers, a short burn) and a hit flash — plus a small
 /// camera kick for nearby kills. Gameplay never depends on it; Reduced Motion drops the kick and optional particles.
 /// 19 Nov 2026 (combat feel): a brighter critical flash (no light) where a critical or weak-point shot lands, and a
 /// CameraImpulse shake for nearby wrecks in place of the old pitch kick when one is bound.
 public class CombatFx:MonoBehaviour
 {
  public GameSession session;
  public FollowCamera follow;
  public PlayerCombat player;
  public FxBurst deathBurst,hitFlash;
  [Tooltip("Played at the strike point of a critical or weak-point hit, on top of the hit flash. Optional.")]
  public FxBurst criticalFlash;
  [Min(1)]public int deathPool=3,hitPool=6,criticalPool=3;
  [Tooltip("When bound, nearby wrecks shake the camera (trauma × wreck size, falling off to Kick Range) instead of kicking its pitch.")]
  public CameraImpulse impulse;
  [Range(0,1)]public float deathTrauma=.45f;
  public int CriticalFlashes {get;private set;}
  [Tooltip("Most combat FX lights (hit flashes, death bursts) on at once across all effects; the newest takes the oldest's slot. 0 = no FX lights.")]
  [Min(0)]public int maxFxLights=2;
  void Awake(){FxBurst.MaxLights=maxFxLights;}
  void OnValidate(){if(Application.isPlaying)FxBurst.MaxLights=maxFxLights;}
  [Tooltip("Camera kick (degrees) for a kill at point-blank range, fading to zero at Kick Range.")]
  [Range(0,3)]public float deathKickDegrees=.9f;
  [Min(1)]public float kickRange=14;
  [Tooltip("Ground search below a wreck for the burn and smoke origin.")]
  public LayerMask groundMask=1;
  readonly List<FxBurst> deaths=new List<FxBurst>(),hits=new List<FxBurst>(),criticals=new List<FxBurst>();
  readonly HashSet<Health> watched=new HashSet<Health>();
  int nextDeath,nextHit,nextCritical;bool listening;
  bool Reduced=>session&&session.reducedMotion;
  void Start()
  {
   Fill(deathBurst,deathPool,deaths);Fill(hitFlash,hitPool,hits);Fill(criticalFlash,criticalPool,criticals);
   if(!player)player=FindAnyObjectByType<PlayerCombat>();
   if(!impulse)impulse=FindAnyObjectByType<CameraImpulse>();
   if(player){player.HitLanded+=OnPlayerHit;listening=true;}
  }
  void OnDestroy(){if(listening&&player)player.HitLanded-=OnPlayerHit;}
  void OnPlayerHit(CombatHit hit)
  {
   if(!hit.critical)return;
   var fx=Next(criticals,ref nextCritical);
   if(fx){fx.Play(hit.point,1,Reduced);CriticalFlashes++;}
  }
  void Fill(FxBurst prefab,int count,List<FxBurst> pool)
  {
   if(!prefab)return;
   for(int i=0;i<count;i++){var fx=Instantiate(prefab,transform);fx.name=prefab.name+" "+i;fx.gameObject.SetActive(false);pool.Add(fx);}
  }
  void LateUpdate()
  {
   var targets=Health.Targets;
   for(int i=0;i<targets.Count;i++)
   {
    var h=targets[i];
    if(!h||watched.Contains(h))continue;
    var droid=h.GetComponent<FeralDroid>();if(!droid)continue;
    watched.Add(h);var health=h;
    h.Died+=()=>OnDied(health,droid);
    h.Damaged+=(amount,point)=>OnHit(point);
   }
  }
  FxBurst Next(List<FxBurst> pool,ref int cursor)
  {
   if(pool.Count==0)return null;
   for(int i=0;i<pool.Count;i++){var fx=pool[(cursor+i)%pool.Count];if(!fx.Busy){cursor=(cursor+i+1)%pool.Count;return fx;}}
   var oldest=pool[cursor];cursor=(cursor+1)%pool.Count;return oldest;
  }
  void OnDied(Health health,FeralDroid droid)
  {
   if(!health)return;
   var centre=health.AimPoint;
   var ground=Physics.Raycast(centre+Vector3.up*.2f,Vector3.down,out var hit,6,groundMask,QueryTriggerInteraction.Ignore)?hit.point:droid.transform.position;
   // Bigger machines make bigger wrecks: scale by hit points relative to a worker (100).
   float size=Mathf.Clamp(Mathf.Sqrt(health.max/100f),.7f,1.8f);
   var fx=Next(deaths,ref nextDeath);
   if(fx)fx.Play(Vector3.Lerp(ground,centre,.35f),size,Reduced);
   if(impulse&&player)impulse.AddAt(centre,deathTrauma*size,kickRange);
   else if(follow&&player&&!Reduced&&deathKickDegrees>0)
   {
    float d=Vector3.Distance(player.transform.position,centre);
    if(d<kickRange)follow.ApplyShotKick(deathKickDegrees*size*(1-d/kickRange),.65f,.4f);
   }
  }
  void OnHit(Vector3 point)
  {
   var fx=Next(hits,ref nextHit);
   if(fx)fx.Play(point,1,Reduced);
  }
 }
}
