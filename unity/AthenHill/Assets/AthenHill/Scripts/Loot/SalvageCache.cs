using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// A physical salvage drop at a wreck. It glows by the best rarity still inside: the emissive core carries the read
 /// (common subtle, uncommon clear but calm, rare the brightest, most saturated, with a gentle pulse); a small point
 /// light only pools about a metre around it. Collected with E. Whatever the pack cannot hold stays inside; an empty cache removes itself.
 /// Caches persist until collected: re-forming nests leave them alone. They expire after a generous lifetime of game
 /// time, and CraftingSession retires the oldest when too many are waiting.
 [RequireComponent(typeof(WorldInteractable))]
 public class SalvageCache:MonoBehaviour
 {
  [Header("Glow by best rarity inside")]
  public Light glowLight;
  [Tooltip("Renderers whose emission shows the rarity colour (the nanite core).")]
  public Renderer[] glowRenderers=new Renderer[0];
  public ParticleSystem motes;
  [Tooltip("Emission of the core (HDR): this carries the rarity read.")]
  [ColorUsage(false,true)]public Color commonGlow=new Color(.8f,.72f,.58f),uncommonGlow=new Color(.3f,1.35f,1.45f),rareGlow=new Color(5f,2f,.15f);
  [Tooltip("Point light intensity by rarity: a soft pool on the ground, never a flood.")]
  [Min(0)]public float commonLight=.15f,uncommonLight=.3f,rareLight=.55f;
  [Tooltip("Point light range (metres) by rarity.")]
  [Min(.1f)]public float commonLightRange=.8f,uncommonLightRange=.95f,rareLightRange=1.25f;
  [Tooltip("Rare caches breathe: ± this fraction of core and light brightness (off with reduced motion).")]
  [Range(0,1)]public float rarePulse=.25f;
  [Min(.05f)]public float rarePulseHz=.6f;
  [Header("Placement")]
  [Tooltip("Half size of the cache's footprint and height (metres): the spot must be flat under all four corners and free of other colliders.")]
  public Vector3 footprint=new Vector3(.26f,.2f,.25f);
  [Tooltip("How far from the wreck a clear spot may be.")]
  [Min(0)]public float searchRadius=1.5f;
  [Tooltip("Minimum distance between caches (metres).")]
  [Min(0)]public float minSeparation=.8f;
  [Tooltip("Largest height difference under the footprint (metres).")]
  [Min(0)]public float maxStep=.14f;
  [Tooltip("{0} = number of item stacks inside.")]
  public string promptFormat="E · Collect salvage ({0})";
  [Tooltip("Colliders ignored when snapping a new cache to the ground are those of droids and the player.")]
  public LayerMask groundMask=~(1<<8);
  [Tooltip("Seconds of game time an uncollected cache waits before it is gone (set by CraftingSession when spawned).")]
  [Min(30)]public float lifetimeSeconds=600;
  public float SpawnedAt {get;private set;}
  public SalvageContents Contents {get;private set;}
  public string Source {get;private set;}
  public ItemRarity Rarity {get;private set;}
  public static readonly List<SalvageCache> Active=new List<SalvageCache>();
  CraftingSession session;
  GameSession city;
  WorldInteractable interaction;
  MaterialPropertyBlock block;
  static readonly int EmissionId=Shader.PropertyToID("_EmissionColor");
  static readonly RaycastHit[] hits=new RaycastHit[12];
  void Awake(){interaction=GetComponent<WorldInteractable>();SpawnedAt=Time.time;}
  void Update()
  {
   if(Time.time-SpawnedAt>lifetimeSeconds){Despawn();return;}
   if(Rarity==ItemRarity.Rare&&rarePulse>0&&Contents!=null&&!(city&&city.reducedMotion))ApplyGlow(1+rarePulse*Mathf.Sin(Time.time*rarePulseHz*Mathf.PI*2));
  }
  /// Caches to retire so that at most keep remain: oldest first, and caches holding rare parts only after the rest.
  public static List<SalvageCache> Evictions(IEnumerable<SalvageCache> caches,int keep)
  {
   var live=caches.Where(c=>c).ToList();
   return EvictionOrder(live.Select(c=>(c.SpawnedAt,c.Rarity==ItemRarity.Rare)).ToList(),keep).Select(i=>live[i]).ToList();
  }
  /// Indices to retire so that at most keep remain (pure; see Evictions).
  public static List<int> EvictionOrder(IReadOnlyList<(float spawnedAt,bool rare)> caches,int keep)
  {
   int excess=caches.Count-System.Math.Max(0,keep);
   if(excess<=0)return new List<int>();
   return Enumerable.Range(0,caches.Count).OrderBy(i=>caches[i].rare?1:0).ThenBy(i=>caches[i].spawnedAt).ThenBy(i=>i).Take(excess).ToList();
  }
  void OnEnable(){if(!interaction)interaction=GetComponent<WorldInteractable>();interaction.Used+=Use;Active.Add(this);}
  void OnDisable(){if(interaction)interaction.Used-=Use;Active.Remove(this);}
  public void Fill(CraftingSession crafting,IEnumerable<ItemStack> items,string source)
  {
   session=crafting;Source=source;Contents=new SalvageContents(items);
   city=crafting?crafting.GetComponent<GameSession>():null;
   if(motes&&city&&city.reducedMotion){var e=motes.emission;e.enabled=false;}
   Refresh();
  }
  void Use()
  {
   if(!session||Contents==null)return;
   session.Collect(Contents,Source,transform.position);
   if(Contents.Empty)Despawn();else Refresh();
  }
  public Color GlowColor(ItemRarity rarity)=>rarity==ItemRarity.Rare?rareGlow:rarity==ItemRarity.Uncommon?uncommonGlow:commonGlow;
  public float LightIntensity(ItemRarity rarity)=>rarity==ItemRarity.Rare?rareLight:rarity==ItemRarity.Uncommon?uncommonLight:commonLight;
  public float LightRange(ItemRarity rarity)=>rarity==ItemRarity.Rare?rareLightRange:rarity==ItemRarity.Uncommon?uncommonLightRange:commonLightRange;
  /// Relative luminance of a rarity's core emission (for tests and tuning: rare > uncommon > common).
  public float CoreLuminance(ItemRarity rarity){var c=GlowColor(rarity);return .2126f*c.r+.7152f*c.g+.0722f*c.b;}
  void Refresh()
  {
   if(Contents==null)return;
   Rarity=session&&session.Session&&session.Session.Shop!=null?Contents.BestRarity(session.Session.Shop):ItemRarity.Common;
   var glow=GlowColor(Rarity);
   float peak=Mathf.Max(glow.r,Mathf.Max(glow.g,glow.b),.001f);
   if(glowLight){glowLight.color=new Color(glow.r/peak,glow.g/peak,glow.b/peak);glowLight.range=LightRange(Rarity);}
   if(motes){var main=motes.main;main.startColor=new Color(glow.r/peak,glow.g/peak,glow.b/peak,.8f);}
   ApplyGlow(1);
   interaction.prompt=string.Format(promptFormat,Contents.Stacks.Count);
  }
  void ApplyGlow(float scale)
  {
   var glow=GlowColor(Rarity)*scale;
   if(glowLight)glowLight.intensity=LightIntensity(Rarity)*scale;
   block??=new MaterialPropertyBlock();
   foreach(var r in glowRenderers){if(!r)continue;r.GetPropertyBlock(block);block.SetColor(EmissionId,glow);r.SetPropertyBlock(block);}
  }
  public void Despawn(){if(this&&gameObject){Active.Remove(this);Destroy(gameObject);}}
  /// A spot for a new cache near a wreck: flat under the whole footprint (centre and four corners within Max Step),
  /// no other collider inside the cache's box (platform edges, cradle bases, fences, the wreck itself), and at least
  /// Min Separation from the other caches. Tries the point itself, then rings out to Search Radius. Returns false
  /// (with the single-ray ground point) when nothing nearby qualifies.
  public bool FindSpot(Vector3 near,Quaternion rotation,IReadOnlyList<Vector3> others,out Vector3 spot)=>
   FindSpot(near,rotation,footprint,searchRadius,minSeparation,maxStep,groundMask,others,out spot);
  public static bool FindSpot(Vector3 near,Quaternion rotation,Vector3 halfSize,float searchRadius,float minSeparation,float maxStep,LayerMask mask,IReadOnlyList<Vector3> others,out Vector3 spot)
  {
   foreach(var c in Candidates(near,searchRadius))
   {
    if(!Footprint(c,rotation,halfSize,maxStep,mask,out var at))continue;
    bool crowded=false;
    if(others!=null)foreach(var o in others){var d=o-at;d.y=0;if(d.magnitude<minSeparation){crowded=true;break;}}
    if(crowded)continue;
    spot=at;return true;
   }
   spot=Ground(near,mask);return false;
  }
  static IEnumerable<Vector3> Candidates(Vector3 near,float radius)
  {
   yield return near;
   for(float r=.5f;r<=radius+.001f;r+=.5f)
    for(int i=0;i<8;i++){float a=i*Mathf.PI/4+(r*1.7f);yield return near+new Vector3(Mathf.Cos(a)*r,0,Mathf.Sin(a)*r);}
  }
  static readonly Collider[] overlaps=new Collider[16];
  /// Five downward rays (centre and footprint corners) must all land within maxStep of each other, and the cache's
  /// box resting on the highest of them must not overlap any collider but those of the player (droid wrecks count).
  public static bool Footprint(Vector3 at,Quaternion rotation,Vector3 halfSize,float maxStep,LayerMask mask,out Vector3 ground)
  {
   ground=at;float lo=float.MaxValue,hi=float.MinValue;
   for(int i=0;i<5;i++)
   {
    var offset=i==0?Vector3.zero:rotation*new Vector3((i&1)==0?-halfSize.x:halfSize.x,0,(i&2)==0?-halfSize.z:halfSize.z);
    if(!Surface(at+offset,mask,out float y))return false;
    lo=Mathf.Min(lo,y);hi=Mathf.Max(hi,y);
   }
   if(hi-lo>maxStep)return false;
   ground=new Vector3(at.x,hi,at.z);
   var centre=ground+Vector3.up*(halfSize.y+.06f);
   int n=Physics.OverlapBoxNonAlloc(centre,new Vector3(halfSize.x,halfSize.y,halfSize.z)*.95f,overlaps,rotation,mask,QueryTriggerInteraction.Ignore);
   for(int i=0;i<n;i++)if(!overlaps[i].GetComponentInParent<PlayerMotor>())return false;
   return true;
  }
  /// Highest surface under a point within 1.2 m above to 3 m below it, ignoring droids, the player and caches.
  static bool Surface(Vector3 at,LayerMask mask,out float y)
  {
   y=0;int n=Physics.RaycastNonAlloc(at+Vector3.up*1.2f,Vector3.down,hits,4.2f,mask,QueryTriggerInteraction.Ignore);
   float best=float.MinValue;
   for(int i=0;i<n;i++)
   {
    var c=hits[i].collider;
    if(c.GetComponentInParent<FeralDroid>()||c.GetComponentInParent<PlayerMotor>()||c.GetComponentInParent<SalvageCache>())continue;
    if(hits[i].normal.y<.8f)continue; // not a surface to rest on
    if(hits[i].point.y>best)best=hits[i].point.y;
   }
   if(best==float.MinValue)return false;
   y=best;return true;
  }
  /// Highest walkable surface under a point, ignoring droids and the player. Falls back to the point itself.
  public static Vector3 Ground(Vector3 at,LayerMask mask)
  {
   int n=Physics.RaycastNonAlloc(at+Vector3.up*2.5f,Vector3.down,hits,8,mask,QueryTriggerInteraction.Ignore);
   float best=float.MinValue;
   for(int i=0;i<n;i++)
   {
    var c=hits[i].collider;
    if(c.GetComponentInParent<FeralDroid>()||c.GetComponentInParent<PlayerMotor>()||c.GetComponentInParent<SalvageCache>())continue;
    if(hits[i].point.y>best)best=hits[i].point.y;
   }
   return best==float.MinValue?at:new Vector3(at.x,best,at.z);
  }
 }
}
