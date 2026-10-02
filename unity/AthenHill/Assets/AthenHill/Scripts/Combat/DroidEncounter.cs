using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Random=UnityEngine.Random;
namespace AthenHill
{
 /// A small territorial droid cluster. Move the spawn point children in the Scene view to reposition it;
 /// each spawn names the droid prefab to create there. Droids are created when the encounter activates: by the primer
 /// or a field order, or on its own once the player comes within Activate Within (outer Berms sites, 2 Oct 2026).
 /// Pack: when one droid turns on the player, the others within Pack Radius of it join the fight a moment later.
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
  [Tooltip("Activates by itself when the player comes within this distance (metres). 0 = only when told to (primer, field orders).")]
  [Min(0)]public float activateWithin;
  [Tooltip("Proximity activation waits until the player carries the scrap pistol.")]
  public bool requirePistol=true;
  [Tooltip("When one droid turns on the player, droids of this encounter within this radius of it join in. 0 = each fights alone.")]
  [Min(0)]public float packRadius=16;
  [Tooltip("Seconds before a called droid turns (random in this range), so a pack does not move as one.")]
  public Vector2 packDelay=new Vector2(.35f,1.1f);
  [Tooltip("Far-away clusters are parked (droids switched off, state kept) while the player is farther than this and none of them is fighting. 0 = never.")]
  [Min(0)]public float parkBeyond;
  public bool Parked {get;private set;}
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
    d.Killed+=OnKilled;d.Alerted+=CallPack;live.Add(d);
   }
  }
  void CallPack(FeralDroid caller)
  {
   if(packRadius<=0)return;
   foreach(var d in live)
   {
    if(!d||d==caller||!d.Health.Alive)continue;
    if((d.transform.position-caller.transform.position).sqrMagnitude<=packRadius*packRadius)d.JoinFight(Random.Range(packDelay.x,Mathf.Max(packDelay.x,packDelay.y)));
   }
  }
  /// Parking: the 500 m Berms keeps far clusters switched off (no thinking, skinning or draw calls) while the player is
  /// beyond Park Beyond and none of the droids is fighting; they come back as they were. 15 m hysteresis.
  void Park(bool far)
  {
   if(far==Parked)
   {
    // a cluster that re-formed while parked goes straight back off
    if(Parked)foreach(var d in live)if(d&&d.gameObject.activeSelf&&d.Health.Alive){d.gameObject.SetActive(false);parked.Add(d);}
    return;
   }
   if(far){foreach(var d in live)if(d&&d.Health.Alive&&d.Engaged)return;}
   else if((player.transform.position-transform.position).sqrMagnitude>(parkBeyond-15)*(parkBeyond-15))return;
   Parked=far;
   if(far){foreach(var d in live)if(d&&d.gameObject.activeSelf&&d.Health.Alive){d.gameObject.SetActive(false);parked.Add(d);}}
   else{foreach(var d in parked)if(d)d.gameObject.SetActive(true);parked.Clear();}
  }
  readonly HashSet<FeralDroid> parked=new HashSet<FeralDroid>();
  void OnKilled(FeralDroid d){if(Remaining==0){clearedAt=Time.time;WasCleared?.Invoke(this);}}
  void OnPlayerDowned(){foreach(var d in live)if(d)d.ResetToHome(false);}
  void Update()
  {
   if(!Spawned&&activateWithin>0&&player&&(!requirePistol||player.hasPistol)&&(player.transform.position-transform.position).sqrMagnitude<activateWithin*activateWithin)Activate();
   if(Spawned&&parkBeyond>0&&player)Park((player.transform.position-transform.position).sqrMagnitude>parkBeyond*parkBeyond);
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
