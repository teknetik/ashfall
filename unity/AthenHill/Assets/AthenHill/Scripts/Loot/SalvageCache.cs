using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// A physical salvage drop at a wreck. It glows by the best rarity still inside (light, emissive beacon and motes)
 /// and is collected with E. Whatever the pack cannot hold stays inside; an empty cache removes itself.
 [RequireComponent(typeof(WorldInteractable))]
 public class SalvageCache:MonoBehaviour
 {
  [Header("Glow by best rarity inside")]
  public Light glowLight;
  [Tooltip("Renderers whose emission shows the rarity colour (the beacon).")]
  public Renderer[] glowRenderers=new Renderer[0];
  public ParticleSystem motes;
  [ColorUsage(false,true)]public Color commonGlow=new Color(1.5f,1.35f,1.1f),uncommonGlow=new Color(.45f,1.9f,1.95f),rareGlow=new Color(2.6f,1.45f,.3f);
  [Min(0)]public float lightIntensity=1.2f;
  [Tooltip("{0} = number of item stacks inside.")]
  public string promptFormat="E · Collect salvage ({0})";
  [Tooltip("Colliders ignored when snapping a new cache to the ground are those of droids and the player.")]
  public LayerMask groundMask=~(1<<8);
  public SalvageContents Contents {get;private set;}
  public string Source {get;private set;}
  public ItemRarity Rarity {get;private set;}
  public static readonly List<SalvageCache> Active=new List<SalvageCache>();
  CraftingSession session;
  WorldInteractable interaction;
  MaterialPropertyBlock block;
  static readonly int EmissionId=Shader.PropertyToID("_EmissionColor");
  static readonly RaycastHit[] hits=new RaycastHit[12];
  void Awake(){interaction=GetComponent<WorldInteractable>();}
  void OnEnable(){if(!interaction)interaction=GetComponent<WorldInteractable>();interaction.Used+=Use;Active.Add(this);}
  void OnDisable(){if(interaction)interaction.Used-=Use;Active.Remove(this);}
  public void Fill(CraftingSession crafting,IEnumerable<ItemStack> items,string source)
  {
   session=crafting;Source=source;Contents=new SalvageContents(items);
   var city=crafting?crafting.GetComponent<GameSession>():null;
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
  void Refresh()
  {
   if(Contents==null)return;
   Rarity=session&&session.Session&&session.Session.Shop!=null?Contents.BestRarity(session.Session.Shop):ItemRarity.Common;
   var glow=GlowColor(Rarity);
   float peak=Mathf.Max(glow.r,Mathf.Max(glow.g,glow.b),.001f);
   if(glowLight){glowLight.color=new Color(glow.r/peak,glow.g/peak,glow.b/peak);glowLight.intensity=lightIntensity;}
   if(motes){var main=motes.main;main.startColor=new Color(glow.r/peak,glow.g/peak,glow.b/peak,.8f);}
   block??=new MaterialPropertyBlock();
   foreach(var r in glowRenderers){if(!r)continue;r.GetPropertyBlock(block);block.SetColor(EmissionId,glow);r.SetPropertyBlock(block);}
   interaction.prompt=string.Format(promptFormat,Contents.Stacks.Count);
  }
  public void Despawn(){if(this&&gameObject)Destroy(gameObject);}
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
