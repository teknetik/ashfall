using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// A Warden waystation out in the Berms (2 Oct 2026). Once the player has walked into it, a knocked-down player is
 /// dragged back to the nearest waystation found (or the gate post, if that is nearer) instead of always the gate.
 /// Found waystations are story flags ("waystation:ID"), so they are saved with the game.
 public class WardenWaystation:MonoBehaviour
 {
  public string id="berms_mid";
  public string displayName="Warden waystation";
  public GameSession session;
  public PlayerCombat player;
  [Tooltip("Where the player is set down (feet), facing its forward.")]
  public Transform respawnPoint;
  [Min(1)]public float discoverRadius=10;
  [Tooltip("Optional: lights that come up once the waystation is found.")]
  public Light[] foundLights=new Light[0];
  public static readonly List<WardenWaystation> All=new List<WardenWaystation>();
  public string Flag=>"waystation:"+id;
  public bool Found=>session&&session.HasFlag(Flag);
  bool shown;
  void OnEnable(){All.Add(this);}
  void OnDisable(){All.Remove(this);}
  void Update()
  {
   bool found=Found;
   if(found!=shown){shown=found;foreach(var l in foundLights)if(l)l.enabled=found;}
   if(found||!session||!player||session.State!=CityState.Play)return;
   if((player.transform.position-transform.position).sqrMagnitude<discoverRadius*discoverRadius)
   {
    session.SetFlag(Flag);
    session.Notify($"{displayName} · if you go down out here, the Wardens bring you back to this camp.","Outer Berms");
   }
  }
  /// The found waystation nearest to where the player went down, if it is nearer than the gate post.
  public static WardenWaystation NearestFound(Vector3 from,Vector3 post)
  {
   WardenWaystation best=null;float bestD=(post-from).sqrMagnitude;
   foreach(var w in All)
   {
    if(!w||!w.Found)continue;
    float d=(w.transform.position-from).sqrMagnitude;
    if(d<bestD){bestD=d;best=w;}
   }
   return best;
  }
 }
}
