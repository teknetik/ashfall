using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// A pooled, authored combat effect (prefab): child particle systems plus an optional flash light that decays and
 /// then flickers like a small fire. CombatFx places and replays it; nothing is instantiated per hit.
 public class FxBurst:MonoBehaviour
 {
  public ParticleSystem[] systems=new ParticleSystem[0];
  [Tooltip("Systems skipped under Reduced Motion (embers, debris).")]
  public ParticleSystem[] optional=new ParticleSystem[0];
  public Light flash;
  [Min(0)]public float flashIntensity=40,flashSeconds=.16f;
  [Tooltip("After the flash, the light settles to a flickering burn for this long (0 = none).")]
  [Min(0)]public float burnSeconds,burnIntensity=2.2f;
  [Min(.05f)]public float lifetime=8;
  float started=-99,scale=1,seed;
  /// Light budget (19 Nov 2026): at most MaxLights combat FX lights are on at once across every FxBurst, because the
  /// OpenGL player draws at most 32 lights per camera and the city already overflows that at night. A newer effect
  /// takes the slot of the oldest holder, which goes dark for the rest of its play. CombatFx sets the cap.
  public static int MaxLights=2;
  static readonly List<FxBurst> lit=new List<FxBurst>();
  public static int LightsLit {get{lit.RemoveAll(b=>!b);return lit.Count;}}
  bool evicted;
  public bool HoldsLight=>lit.Contains(this);
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]static void ResetBudget(){lit.Clear();MaxLights=2;}
  /// The light slot for this burst: true if it holds one (taking the oldest holder's slot when the budget is full).
  public bool AcquireLight()
  {
   if(lit.Contains(this))return true;
   if(evicted)return false;
   lit.RemoveAll(b=>!b);
   if(MaxLights<=0)return false;
   while(lit.Count>=MaxLights){var oldest=lit[0];lit.RemoveAt(0);oldest.evicted=true;if(oldest.flash)oldest.flash.enabled=false;}
   lit.Add(this);return true;
  }
  public void ReleaseLight(){lit.Remove(this);}
  void OnDisable(){ReleaseLight();if(flash)flash.enabled=false;}
  void OnDestroy(){ReleaseLight();}
  public bool Busy=>gameObject.activeSelf&&Time.time-started<lifetime;
  public void Play(Vector3 position,float size,bool reducedMotion)
  {
   transform.position=position;scale=Mathf.Max(.2f,size);transform.localScale=Vector3.one*scale;
   ReleaseLight();evicted=false;
   gameObject.SetActive(true);started=Time.time;seed=Random.value*50;
   foreach(var ps in systems)
   {
    if(!ps)continue;
    ps.Clear(true);
    if(reducedMotion&&System.Array.IndexOf(optional,ps)>=0)continue;
    ps.Play(true);
   }
   Update();
  }
  void Update()
  {
   float t=Time.time-started;
   if(flash)
   {
    float i=t<flashSeconds?flashIntensity*Mathf.Pow(1-t/flashSeconds,2):0;
    if(burnSeconds>0&&t<flashSeconds+burnSeconds)
    {
     float fade=1-Mathf.Clamp01((t-flashSeconds)/burnSeconds);
     i=Mathf.Max(i,burnIntensity*fade*(.65f+.35f*Mathf.PerlinNoise(seed,t*9)));
    }
    flash.intensity=i*scale;
    bool want=flash.intensity>.02f;
    if(want)want=AcquireLight();else ReleaseLight();
    flash.enabled=want;
   }
   if(t>lifetime)gameObject.SetActive(false);
  }
 }
}
