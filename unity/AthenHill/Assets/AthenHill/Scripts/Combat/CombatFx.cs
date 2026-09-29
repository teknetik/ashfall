using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// Scene-level combat presentation: watches every feral droid's Health and plays pooled, authored effects —
 /// a death burst (flash, sparks, debris, fireball, smoke plume, embers, a short burn) and a hit flash — plus a small
 /// camera kick for nearby kills. Gameplay never depends on it; Reduced Motion drops the kick and optional particles.
 public class CombatFx:MonoBehaviour
 {
  public GameSession session;
  public FollowCamera follow;
  public PlayerCombat player;
  public FxBurst deathBurst,hitFlash;
  [Min(1)]public int deathPool=3,hitPool=6;
  [Tooltip("Camera kick (degrees) for a kill at point-blank range, fading to zero at Kick Range.")]
  [Range(0,3)]public float deathKickDegrees=.9f;
  [Min(1)]public float kickRange=14;
  [Tooltip("Ground search below a wreck for the burn and smoke origin.")]
  public LayerMask groundMask=1;
  readonly List<FxBurst> deaths=new List<FxBurst>(),hits=new List<FxBurst>();
  readonly HashSet<Health> watched=new HashSet<Health>();
  int nextDeath,nextHit;
  bool Reduced=>session&&session.reducedMotion;
  void Start()
  {
   Fill(deathBurst,deathPool,deaths);Fill(hitFlash,hitPool,hits);
   if(!player)player=FindAnyObjectByType<PlayerCombat>();
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
   if(follow&&player&&!Reduced&&deathKickDegrees>0)
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
