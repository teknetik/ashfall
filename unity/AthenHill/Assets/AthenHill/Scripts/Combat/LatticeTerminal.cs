using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Pure rules and target resolution for Field Lattice Terminals (22 Nov 2026).
 /// Kept scene-independent so key-gating, permanent unlock, combat lock and two-way travel are unit-testable.
 public static class LatticeTerminalLogic
 {
  public const string DefaultKeyId="berms_relay_key";
  public const string DefaultWaystationId="berms_mid";
  public const string DefaultDisplayName="Waystation Lattice Relay";
  public const string WaystationGridLabel="Outer Berms · Waystation Relay";
  public const string TerminalDestinationPrefix="terminal:";
  public const string WardJackDestinationId="ward_lattice_jack";
  public const string CombatBlockedMessage="Cannot link while under fire — break contact first.";

  public enum InteractionOutcome { CombatBlocked, MissingKey, Unlocked, Online }

  public readonly struct TravelTarget
  {
   public readonly string id;
   public readonly string name;
   public readonly string description;
   public readonly bool isFastTravel;
   public readonly string terminalId;
   public TravelTarget(string id,string name,string description,bool isFastTravel,string terminalId=null)
   {
    this.id=id;this.name=name;this.description=description;this.isFastTravel=isFastTravel;this.terminalId=terminalId;
   }
  }

  /// True while any active, living feral droid is actively engaged in combat.
  public static bool AnyDroidEngaged(IEnumerable<FeralDroid> droids)
  {
   if(droids==null)return false;
   foreach(var d in droids)
   {
    if(d&&d.gameObject.activeInHierarchy&&d.State!=DroidState.Dead&&d.Engaged)return true;
   }
   return false;
  }

  public static bool AnyDroidEngaged()=>AnyDroidEngaged(FeralDroid.Active);

  public static bool CanUseTerminal(bool anyDroidEngaged,out string blockedReason)
  {
   if(anyDroidEngaged){blockedReason=CombatBlockedMessage;return false;}
   blockedReason=null;return true;
  }

  public static InteractionOutcome EvaluateInteraction(bool isUnlocked,bool hasKey,bool anyDroidEngaged,out string message)
  {
   if(anyDroidEngaged){message=CombatBlockedMessage;return InteractionOutcome.CombatBlocked;}
   if(!isUnlocked)
   {
    if(!hasKey){message="Lattice Terminal offline. Requires Warden Relay Key.";return InteractionOutcome.MissingKey;}
    message="Warden Relay Key accepted. Lattice Terminal is now permanently online.";
    return InteractionOutcome.Unlocked;
   }
   message=null;
   return InteractionOutcome.Online;
  }

  public static string PromptText(bool isUnlocked,bool hasKey,bool travelArmed,string displayName=null)
  {
   if(!isUnlocked)
    return hasKey?"E · Bring Lattice Terminal Online (Warden Relay Key)":"E · Lattice Terminal (Requires Warden Relay Key)";
   if(travelArmed)return "E · Fast Travel to Ward (Lattice Jack)";
   string label=string.IsNullOrEmpty(displayName)?"Lattice Terminal":displayName;
   return $"E · {label} (Save & Fast Travel)";
  }

  public static string DestinationId(string terminalId)=>string.IsNullOrEmpty(terminalId)?null:TerminalDestinationPrefix+terminalId;

  public static string ParseTerminalDestinationId(string destinationId)
  {
   if(string.IsNullOrEmpty(destinationId)||!destinationId.StartsWith(TerminalDestinationPrefix,StringComparison.Ordinal))return null;
   string tid=destinationId.Substring(TerminalDestinationPrefix.Length);
   return string.IsNullOrEmpty(tid)?null:tid;
  }

  public static string GridLabelForTerminal(string terminalId,string displayName=null)
  {
   if(terminalId==DefaultWaystationId)return WaystationGridLabel;
   string name=string.IsNullOrEmpty(displayName)?terminalId:displayName;
   return $"Outer Berms · {name}";
  }

  /// Resolves the destination list shown at Ward's Lattice Jack (CityState.Grid):
  /// existing catalog sector nodes plus one fast-travel target per unlocked Outer Berms terminal.
  public static List<TravelTarget> ResolveWardJackDestinations(IEnumerable<TravelNode> catalogDestinations,IEnumerable<string> unlockedTerminals,IEnumerable<LatticeTerminal> sceneTerminals=null)
  {
   var list=new List<TravelTarget>();
   if(catalogDestinations!=null)
   {
    foreach(var n in catalogDestinations)
    {
     if(n==null||string.IsNullOrEmpty(n.id))continue;
     list.Add(new TravelTarget(n.id,n.name,n.description,false,null));
    }
   }
   if(unlockedTerminals!=null)
   {
    var byId=new Dictionary<string,LatticeTerminal>(StringComparer.Ordinal);
    if(sceneTerminals!=null)foreach(var t in sceneTerminals)if(t&&!string.IsNullOrEmpty(t.terminalId)&&!byId.ContainsKey(t.terminalId))byId[t.terminalId]=t;
    foreach(var tid in unlockedTerminals.Where(x=>!string.IsNullOrEmpty(x)).Distinct(StringComparer.Ordinal).OrderBy(x=>x,StringComparer.Ordinal))
    {
     byId.TryGetValue(tid,out var term);
     string label=GridLabelForTerminal(tid,term?term.displayName:null);
     list.Add(new TravelTarget(DestinationId(tid),label,"Field Lattice Terminal · fast travel to the Outer Berms.",true,tid));
    }
   }
   return list;
  }

  public static TravelTarget ResolveTerminalReturnTarget()
   =>new TravelTarget(WardJackDestinationId,"Ward · Lattice Jack","Return to Ward's north court beside the Lattice Jack.",true,null);

  /// Pure wake-point resolution for Continue: wakes at lastTerminalId only if it is in the unlocked set.
  public static string ResolveWakeTerminalId(string lastTerminalId,IEnumerable<string> unlockedTerminals)
  {
   if(string.IsNullOrEmpty(lastTerminalId)||unlockedTerminals==null)return null;
   foreach(var id in unlockedTerminals)if(string.Equals(id,lastTerminalId,StringComparison.Ordinal))return lastTerminalId;
   return null;
  }
 }

 /// Key-gated Field Lattice Terminal in the Outer Berms (22 Nov 2026).
 /// Starts offline until activated with the Warden Relay Key (`berms_relay_key`). Once unlocked, stays permanently
 /// online via save data (`WardSaveData.unlockedTerminals`), offers Manual Save (recording `lastTerminalId` as the
 /// Continue wake point) and two-way Fast Travel with Ward's Lattice Jack, and refuses both while any droid is Engaged.
 [RequireComponent(typeof(WorldInteractable))]
 public class LatticeTerminal:MonoBehaviour
 {
  public string terminalId=LatticeTerminalLogic.DefaultWaystationId;
  public string displayName=LatticeTerminalLogic.DefaultDisplayName;
  public string requiredKeyId=LatticeTerminalLogic.DefaultKeyId;
  public GameSession session;
  [Tooltip("Optional: WardenWaystation colocated with this terminal. Auto-resolved from self or parent when unassigned.")]
  public WardenWaystation waystation;
  [Tooltip("Where the player wakes on Continue or arrives from Ward's Lattice Jack. Falls back to waystation.respawnPoint, then this transform.")]
  public Transform wakePoint;
  [Tooltip("Optional: lights that illuminate when the terminal is brought online.")]
  public Light[] statusLights=new Light[0];
  [Tooltip("Optional: emissive screen renderers that shift from locked amber to online cyan.")]
  public Renderer[] statusRenderers=new Renderer[0];
  public Color lockedColor=new Color(.83f,.60f,.29f,1f);
  public Color onlineColor=new Color(.35f,.84f,.84f,1f);
  public bool consumeKeyOnUnlock=false;

  public const float TravelArmSeconds=6f;
  public static readonly List<LatticeTerminal> All=new List<LatticeTerminal>();
  static readonly int EmissionId=Shader.PropertyToID("_EmissionColor");
  static readonly int BaseColorId=Shader.PropertyToID("_BaseColor");

  WorldInteractable interaction;
  MaterialPropertyBlock propBlock;
  bool visualsApplied,lastOnline;
  float travelArmUntil=-1f;

  public string MapId=>WorldMapDiscovery.LatticeRelayId(terminalId);
  public Transform WakePoint=>wakePoint?wakePoint:(waystation&&waystation.respawnPoint?waystation.respawnPoint:transform);
  public bool Unlocked=>session&&session.IsTerminalUnlocked(terminalId);
  public bool HasKey=>session&&session.Shop!=null&&!string.IsNullOrEmpty(requiredKeyId)&&session.Shop.Quantity(requiredKeyId)>0;
  public bool TravelArmed=>travelArmUntil>Time.unscaledTime;

  public static LatticeTerminal FindById(string id)
  {
   if(string.IsNullOrEmpty(id))return null;
   foreach(var t in All)if(t&&string.Equals(t.terminalId,id,StringComparison.Ordinal))return t;
   return null;
  }

  void OnEnable()
  {
   if(!All.Contains(this))All.Add(this);
   if(!interaction)interaction=GetComponent<WorldInteractable>();
   if(interaction)interaction.Used+=OnUsed;
   if(!waystation)waystation=GetComponent<WardenWaystation>()??GetComponentInParent<WardenWaystation>();
   if(!session&&waystation&&waystation.session)session=waystation.session;
   if(!session)session=FindAnyObjectByType<GameSession>();
   SyncVisuals(true);
   UpdatePrompt();
  }

  void OnDisable()
  {
   All.Remove(this);
   if(interaction)interaction.Used-=OnUsed;
   travelArmUntil=-1f;
  }

  void Update()
  {
   SyncVisuals(false);
   UpdatePrompt();
  }

  void OnUsed()=>Interact();

  void UpdatePrompt()
  {
   if(interaction)interaction.prompt=LatticeTerminalLogic.PromptText(Unlocked,HasKey,TravelArmed,displayName);
  }

  void SyncVisuals(bool force)
  {
   bool online=Unlocked;
   if(!force&&visualsApplied&&online==lastOnline)return;
   visualsApplied=true;lastOnline=online;
   Color c=online?onlineColor:lockedColor;
   if(statusLights!=null)
   {
    foreach(var l in statusLights)
    {
     if(!l)continue;
     l.color=c;
     l.enabled=online;
    }
   }
   if(statusRenderers!=null&&statusRenderers.Length>0)
   {
    if(propBlock==null)propBlock=new MaterialPropertyBlock();
    foreach(var r in statusRenderers)
    {
     if(!r)continue;
     r.GetPropertyBlock(propBlock);
     propBlock.SetColor(EmissionId,c*(online?1.8f:.45f));
     propBlock.SetColor(BaseColorId,c);
     r.SetPropertyBlock(propBlock);
    }
   }
  }

  /// Main E-key interaction: blocks during combat, unlocks with Warden Relay Key, or saves & arms fast travel to Ward.
  public LatticeTerminalLogic.InteractionOutcome Interact()
  {
   var outcome=LatticeTerminalLogic.EvaluateInteraction(Unlocked,HasKey,LatticeTerminalLogic.AnyDroidEngaged(),out var message);
   switch(outcome)
   {
    case LatticeTerminalLogic.InteractionOutcome.CombatBlocked:
     travelArmUntil=-1f;
     session?.Notify(message,displayName);
     session?.Cue(CitySoundCue.Unavailable);
     return outcome;

    case LatticeTerminalLogic.InteractionOutcome.MissingKey:
     session?.Notify(message,displayName);
     session?.Cue(CitySoundCue.Unavailable);
     if(session&&!session.HasFlag("terminal_hint:"+terminalId))
     {
      session.SetFlag("terminal_hint:"+terminalId);
      session.Radio("That relay terminal's locked out. The patrol who held this post lost their Warden Relay Key in the inner Berms — recover it and you can bring the link back up.","Warden Ossa");
     }
     return outcome;

    case LatticeTerminalLogic.InteractionOutcome.Unlocked:
     TryUnlock();
     return outcome;

    case LatticeTerminalLogic.InteractionOutcome.Online:
     if(TravelArmed)
     {
      travelArmUntil=-1f;
      FastTravelToWard();
     }
     else
     {
      if(ManualSave())
      {
       travelArmUntil=Time.unscaledTime+TravelArmSeconds;
       session?.Notify($"Progress saved at {displayName}. Press E again within {TravelArmSeconds:0} s to fast-travel to Ward's Lattice Jack.",displayName);
      }
     }
     UpdatePrompt();
     return outcome;
   }
   return outcome;
  }

  /// Brings the terminal permanently online using the Warden Relay Key.
  public bool TryUnlock()
  {
   if(!session||string.IsNullOrEmpty(terminalId))return false;
   if(!LatticeTerminalLogic.CanUseTerminal(LatticeTerminalLogic.AnyDroidEngaged(),out var blocked))
   {
    session.Notify(blocked,displayName);
    session.Cue(CitySoundCue.Unavailable);
    return false;
   }
   if(Unlocked)return true;
   if(!HasKey)
   {
    session.Notify("Lattice Terminal offline. Requires Warden Relay Key.",displayName);
    session.Cue(CitySoundCue.Unavailable);
    return false;
   }
   if(consumeKeyOnUnlock&&session.Shop!=null)
    session.Shop.TryApply(new[]{new KeyValuePair<string,int>(requiredKeyId,-1)},0,out _);

   session.UnlockTerminal(terminalId);
   session.SetLastTerminal(terminalId);
   if(waystation&&!waystation.Found)session.SetFlag(waystation.Flag);
   SyncVisuals(true);
   UpdatePrompt();

   var save=session.GetComponent<WardSaveGame>();
   if(save&&save.Ready)save.SaveNow("terminal");
   session.Cue(CitySoundCue.LatticeLink);
   session.Notify($"{displayName} online. Manual save and Lattice fast travel to Ward are now active.",displayName);
   session.Radio("Link confirmed on my board. You can save at that relay or jump straight back to Ward's Lattice Jack — as long as nothing's shooting at you.","Warden Ossa");
   return true;
  }

  /// Saves progress at this terminal and sets it as the Continue wake point.
  public bool ManualSave()
  {
   if(!session||!Unlocked)return false;
   if(!LatticeTerminalLogic.CanUseTerminal(LatticeTerminalLogic.AnyDroidEngaged(),out var blocked))
   {
    session.Notify(blocked,displayName);
    session.Cue(CitySoundCue.Unavailable);
    return false;
   }
   session.SetLastTerminal(terminalId);
   var save=session.GetComponent<WardSaveGame>();
   bool saved=!save||!save.Ready||save.SaveNow("terminal");
   session.Cue(saved?CitySoundCue.LatticeOpen:CitySoundCue.Unavailable);
   if(!saved)session.Notify("Could not save progress right now.",displayName);
   return saved;
  }

  /// Fast-travels from this unlocked terminal back to Ward's Lattice Jack.
  public bool FastTravelToWard()
  {
   if(!session||!Unlocked)return false;
   if(!LatticeTerminalLogic.CanUseTerminal(LatticeTerminalLogic.AnyDroidEngaged(),out var blocked))
   {
    session.Notify(blocked,displayName);
    session.Cue(CitySoundCue.Unavailable);
    return false;
   }
   session.SetLastTerminal(terminalId);
   var save=session.GetComponent<WardSaveGame>();
   if(save&&save.Ready)save.SaveNow("terminal");
   return session.FastTravelToWard(this);
  }
 }
}
