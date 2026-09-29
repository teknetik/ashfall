using UnityEngine;
namespace AthenHill
{
 /// A searchable scrap heap in the Outer Berms. E starts a short search; moving away or opening any menu cancels it.
 /// A completed search rolls the node's loot table into the pack (anything that does not fit is left in a cache
 /// beside the heap). The heap is then picked clean until its respawn timer runs out.
 [RequireComponent(typeof(WorldInteractable))]
 public class SalvageNode:MonoBehaviour
 {
  public CraftingSession crafting;
  public string displayName="Scrap heap";
  public string lootTableId="loot_scrap_heap";
  [Min(.1f)]public float searchSeconds=1.2f;
  [Tooltip("Seconds of play (menus pause it) before a picked-clean heap can be searched again.")]
  [Min(1)]public float respawnSeconds=270;
  [Tooltip("Moving farther than this from where the search began cancels it.")]
  [Min(.05f)]public float cancelDistance=.6f;
  public string readyPrompt="E · Search the scrap heap";
  public string searchingPrompt="Searching the heap… hold still";
  [Tooltip("{0} = minutes:seconds until it can be searched again.")]
  public string depletedPrompt="Picked clean · more scrap in {0}";
  [Header("Presentation (shown while searchable)")]
  public Light readyLight;
  public ParticleSystem readyMotes;
  /// The heap being searched right now (the HUD shows its progress), or null.
  public static SalvageNode Searching {get;private set;}
  public SalvageSearch Search {get;private set;}
  public float Progress=>Search!=null?Search.Progress(Time.time):0;
  WorldInteractable interaction;
  GameSession session;
  int shownSeconds=-1;
  void Awake(){interaction=GetComponent<WorldInteractable>();Search=new SalvageSearch(searchSeconds,respawnSeconds,cancelDistance);}
  void Start()
  {
   if(!crafting)crafting=FindAnyObjectByType<CraftingSession>();
   session=crafting?crafting.GetComponent<GameSession>():FindAnyObjectByType<GameSession>();
   Present();
  }
  void OnEnable(){if(!interaction)interaction=GetComponent<WorldInteractable>();interaction.Used+=Use;}
  void OnDisable(){if(interaction)interaction.Used-=Use;if(Searching==this)Searching=null;}
  Vector3 Player=>session&&session.player?session.player.transform.position:transform.position;
  void Use()
  {
   if(!crafting||crafting.Model==null||!session)return;
   if(Search.State==SalvageNodeState.Depleted){session.Notify($"This {displayName.ToLowerInvariant()} is picked clean. More scrap settles in about {Clock(Search.RespawnRemaining(Time.time))}.","Field Pack");return;}
   if(Searching&&Searching!=this)return;
   if(Search.Begin(Time.time,Player)){Searching=this;Present();}
  }
  void Update()
  {
   if(Search==null)return;
   switch(Search.Tick(Time.time,Player,session&&session.State==CityState.Play))
   {
    case SalvageTick.Cancelled:
     if(Searching==this)Searching=null;
     if(session)session.Notify("Search interrupted. Stay close to the heap until it finishes.","Field Pack");
     Present();break;
    case SalvageTick.Completed:
     if(Searching==this)Searching=null;
     crafting.SearchHeap(lootTableId,transform.position,transform.parent,displayName);
     Present();break;
    case SalvageTick.Respawned:Present();break;
   }
   if(Search.State==SalvageNodeState.Depleted)
   {
    int seconds=Mathf.CeilToInt(Search.RespawnRemaining(Time.time));
    if(seconds!=shownSeconds){shownSeconds=seconds;interaction.prompt=string.Format(depletedPrompt,Clock(seconds));}
   }
  }
  void Present()
  {
   bool ready=Search.State==SalvageNodeState.Ready;
   if(readyLight)readyLight.enabled=ready;
   if(readyMotes){if(ready&&!(session&&session.reducedMotion)){if(!readyMotes.isPlaying)readyMotes.Play();}else readyMotes.Stop();}
   shownSeconds=-1;
   interaction.prompt=Search.State==SalvageNodeState.Searching?searchingPrompt:ready?readyPrompt:string.Format(depletedPrompt,Clock(Search.RespawnRemaining(Time.time)));
  }
  static string Clock(float seconds){int s=Mathf.Max(0,Mathf.CeilToInt(seconds));return $"{s/60}:{s%60:00}";}
 }
}
