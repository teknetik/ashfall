using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// A small territorial droid cluster. Move the spawn point children in the Scene view to reposition it;
 /// each spawn names the droid prefab to create there. Droids are created when the encounter activates.
 public class DroidEncounter:MonoBehaviour
 {
  [Serializable]public class Spawn{public FeralDroid prefab;public Transform point;}
  public string displayName="Droid cluster";
  public Spawn[] spawns=new Spawn[0];
  public PlayerCombat player;
  public GameSession session;
  [Tooltip("After being cleared, the cluster re-forms this many seconds later once the player is away. 0 = never.")]
  [Min(0)]public float respawnSeconds;
  [Tooltip("\"Away\" means farther than this from the encounter (metres). Keep nearby work spots such as the field fabricator inside it.")]
  [Min(0)]public float respawnClearance=35;
  [Tooltip("The player must also have stayed away this many seconds in a row, so a cluster never re-forms just as they turn their back.")]
  [Min(0)]public float awaySeconds;
  public bool Spawned {get;private set;}
  public int Total=>spawns.Length;
  public int Remaining=>live.Count(d=>d&&d.Health.Alive);
  public bool Cleared=>Spawned&&Remaining==0;
  public IReadOnlyList<FeralDroid> Droids=>live;
  /// The droid of the first spawn (the Depot Foreman in its encounter; escorts follow it).
  public FeralDroid Leader=>live.Count>0?live[0]:null;
  public event Action<DroidEncounter> WasCleared;
  readonly List<FeralDroid> live=new List<FeralDroid>();
  float clearedAt,awayFor;
  void Start(){if(player)player.Downed+=OnPlayerDowned;}
  void OnDestroy(){if(player)player.Downed-=OnPlayerDowned;}
  public void Activate()
  {
   if(Spawned)return;
   Spawned=true;
   foreach(var s in spawns)
   {
    if(!s.prefab||!s.point)continue;
    var d=Instantiate(s.prefab,s.point.position,s.point.rotation,transform);
    d.name=s.prefab.name;d.Bind(player,session,s.point.position);
    var loot=d.GetComponent<LootSource>();if(loot&&session)loot.Bind(session.GetComponent<CraftingSession>());
    d.Killed+=OnKilled;live.Add(d);
   }
  }
  void OnKilled(FeralDroid d){if(Remaining==0){clearedAt=Time.time;WasCleared?.Invoke(this);}}
  void OnPlayerDowned(){foreach(var d in live)if(d)d.ResetToHome(false);}
  void Update()
  {
   if(respawnSeconds<=0||!Cleared||!player){awayFor=0;return;}
   bool away=Vector3.Distance(player.transform.position,transform.position)>=respawnClearance;
   awayFor=away?awayFor+Time.deltaTime:0;
   if(!ShouldReform(respawnSeconds,Time.time-clearedAt,away,awayFor,awaySeconds))return;
   awayFor=0;
   foreach(var d in live)if(d)d.ResetToHome(true);
  }
  /// Re-form rule: cleared long enough ago, and the player is away and has stayed away long enough.
  public static bool ShouldReform(float respawnSeconds,float sinceCleared,bool away,float awayFor,float awaySeconds)=>respawnSeconds>0&&sinceCleared>=respawnSeconds&&away&&awayFor>=awaySeconds;
 }
}
