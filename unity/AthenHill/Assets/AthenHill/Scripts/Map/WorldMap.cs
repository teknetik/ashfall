using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// The world map's live state (19 Nov 2026): the places on the sheet (city places always; the Warden waystations once
 /// checked in at; Berms sites once the player has been within siteRadius of them), the tracked mission's marker, the
 /// respawn the player would get if they went down now, and their last knock-down. It owns no window: the M window
 /// (WorldMapPanel) reads it, and the save stores Capture(). Added to the GameSession object at runtime when the scene
 /// has none, like the journal, so no scene edit is needed.
 [RequireComponent(typeof(GameSession))]
 public class WorldMap:MonoBehaviour
 {
  [Tooltip("A Berms site counts as discovered once the player has stood within this many metres of its centre.")]
  [Min(5)]public float siteRadius=55;
  [Tooltip("Optional survey pictures; loaded from Resources/" + WorldMapSurvey.ResourcePath + " when unassigned.")]
  public WorldMapSurvey survey;
  GameSession session;PlayerCombat combat;BermsTutorial tutorial;
  readonly WorldMapDiscovery discovery=new WorldMapDiscovery();
  readonly List<MapPlace> places=new List<MapPlace>();
  readonly Dictionary<string,BermsCompassPoint> sitePoints=new Dictionary<string,BermsCompassPoint>();
  readonly Dictionary<string,WardenWaystation> stations=new Dictionary<string,WardenWaystation>();
  int pointCount=-1,stationCount=-1;bool surveyLoaded,bound;
  Vector3 lastPlayer;bool hasLast;
  public Vector2? LastDowned {get;private set;}
  /// The map window, when the HUD built one (it is ticked from here while open).
  public WorldMapPanel Panel {get;set;}
  /// A place was discovered or the knock-down spot moved (autosave hook).
  public event Action Changed;
  public IReadOnlyCollection<string> DiscoveredIds=>discovery.Found;
  public WorldMapSurvey Survey{get{if(!survey&&!surveyLoaded){surveyLoaded=true;survey=WorldMapSurvey.Load();}return survey;}}
  public GameSession Session=>session?session:session=GetComponent<GameSession>();
  public bool InBerms{get{if(!Session)return false;Bind();return combat?combat.InBerms:session.player&&session.player.transform.position.x<-59;}}

  void Awake(){session=GetComponent<GameSession>();}
  void Bind()
  {
   if(bound)return;bound=true;
   combat=session.player?session.player.GetComponent<PlayerCombat>():null;
   var orders=GetComponent<FieldOrders>();
   tutorial=orders&&orders.tutorial?orders.tutorial:FindAnyObjectByType<BermsTutorial>();
   if(combat)combat.Downed+=OnDowned;
  }
  void OnDestroy(){if(combat)combat.Downed-=OnDowned;}
  // PlayerCombat raises Downed after it has already moved the player to the respawn, so the spot is the position
  // recorded at the end of the previous frame.
  void OnDowned(){if(!hasLast)return;LastDowned=new Vector2(lastPlayer.x,lastPlayer.z);Changed?.Invoke();}

  void Update()
  {
   if(!Session)return;
   Bind();
   if(session.HasStarted&&session.State==CityState.Play&&session.player)
   {
    var p=session.player.transform.position;
    var all=Places;
    var step=tutorial?tutorial.Step:BermsStep.Complete;
    var found=discovery.Visit(p,all,id=>WorldMapDiscovery.PrimerAllows(id,step));
    foreach(var w in stations)if(w.Value&&w.Value.Found&&discovery.Add(w.Key))found.Add(all.FirstOrDefault(x=>x.id==w.Key));
    if(found.Count>0)
    {
     var named=found.Where(f=>f!=null&&f.kind!=MapPlaceKind.Waystation).Select(f=>f.name).ToList();
     // the waystation announces itself (WardenWaystation); a site gets one short line
     if(named.Count>0)session.Notify($"{string.Join(", ",named)} marked on your map · M","Map");
     Changed?.Invoke();
    }
   }
   if(session.State==CityState.Map)Panel?.Tick(Time.unscaledDeltaTime);
  }
  void LateUpdate(){if(Session&&session.player){lastPlayer=session.player.transform.position;hasLast=true;}}

  // ------------------------------------------------------------------ places
  /// Every place the sheet knows (shown or not). Rebuilt when sites or waystations enable/disable.
  public IReadOnlyList<MapPlace> Places
  {
   get
   {
    if(BermsCompassPoint.All.Count!=pointCount||WardenWaystation.All.Count!=stationCount||places.Count==0)Rebuild();
    return places;
   }
  }
  void Rebuild()
  {
   Bind();
   pointCount=BermsCompassPoint.All.Count;stationCount=WardenWaystation.All.Count;
   places.Clear();sitePoints.Clear();stations.Clear();
   var anchors=Survey?Survey.anchors:null;
   foreach(var p in WorldMapSchematic.CityPlaces())
   {
    var a=anchors?.FirstOrDefault(x=>x!=null&&x.id==p.id);
    if(a!=null)p.position=new Vector2(a.position.x,a.position.z);
    places.Add(p);
   }
   var hill=session.hillPoint?places.FirstOrDefault(p=>p.id=="city:hill"):null;
   if(hill!=null)hill.anchor=session.hillPoint;
   var jack=session.latticePoint?places.FirstOrDefault(p=>p.id=="city:lattice_jack"):null;
   if(jack!=null)jack.anchor=session.latticePoint;
   var home=session.Home;
   if(home)places.Add(new MapPlace("city:home","Home",MapPlaceKind.Home,0,0){anchor=home.lockerPoint?home.lockerPoint:home.transform});
   foreach(var p in WorldMapSchematic.BermsPlaces())places.Add(p);
   foreach(var c in BermsCompassPoint.All)
   {
    if(!c)continue;
    if(c.kind==BermsCompassPoint.Kind.Gate){var g=places.FirstOrDefault(p=>p.id=="berms:west_gate");if(g!=null){g.anchor=c.transform;if(!string.IsNullOrEmpty(c.displayName))g.name=c.displayName;}continue;}
    if(c.kind==BermsCompassPoint.Kind.Waystation)continue; // the WardenWaystation itself is listed below
    var id="site:"+WorldMapMath.Slug(c.displayName);
    if(sitePoints.ContainsKey(id))continue;
    sitePoints[id]=c;
    places.Add(new MapPlace(id,c.displayName,MapPlaceKind.Site,0,0,siteRadius){anchor=c.transform});
   }
   foreach(var w in WardenWaystation.All)
   {
    if(!w||stations.ContainsKey(w.Flag))continue;
    stations[w.Flag]=w;
    places.Add(new MapPlace(w.Flag,w.displayName,MapPlaceKind.Waystation,0,0){anchor=w.transform});
   }
   if(tutorial&&tutorial.depot&&!sitePoints.ContainsKey(WorldMapDiscovery.DepotId))
    places.Add(new MapPlace(WorldMapDiscovery.DepotId,"Machine depot",MapPlaceKind.Site,0,0,siteRadius){anchor=tutorial.depot.transform});
  }
  /// On the sheet now: city and gate places always (the home once leased); sites and waystations once found.
  public bool Shown(MapPlace p)
  {
   if(p==null)return false;
   switch(p.kind)
   {
    case MapPlaceKind.Home:return Session&&session.HasFlag(WardHome.LeasedFlag);
    case MapPlaceKind.Waystation:return discovery.Has(p.id)||stations.TryGetValue(p.id,out var w)&&w&&w.Found;
    case MapPlaceKind.Site:return discovery.Has(p.id);
    default:return true;
   }
  }
  /// The site's droid cluster is cleared (the compass dims it too).
  public bool Cleared(MapPlace p)=>p!=null&&sitePoints.TryGetValue(p.id,out var c)&&c&&c.Cleared;
  public bool Discovered(string id)=>discovery.Has(id);
  /// Marks a place discovered (development QA). False for an unknown id or one already found.
  public bool Discover(string id)
  {
   if(Places.All(p=>p.id!=id))return false;
   if(!discovery.Add(id))return false;
   Changed?.Invoke();return true;
  }

  // ------------------------------------------------------------------ markers
  /// Where the player would be set down if they went down now: the nearest found waystation, else the gate post.
  public WardenWaystation RespawnStation
  {
   get
   {
    Bind();if(!session||!session.player)return null;
    var post=combat&&combat.respawnPoint?combat.respawnPoint.position:session.player.transform.position;
    return WardenWaystation.NearestFound(session.player.transform.position,post);
   }
  }
  public Vector3? GatePost{get{Bind();return combat&&combat.respawnPoint?combat.respawnPoint.position:(Vector3?)null;}}
  /// The tracked mission's marker (the journal's tracked mission and target, as on the compass).
  public MapMarker Tracked(out Mission mission)
  {
   mission=Session&&session.Journal?session.Journal.Tracked:null;
   var t=mission?.target;
   if(!t)return MapMarker.None;
   bool machine=mission.droid||t.GetComponentInParent<FeralDroid>();
   var sites=machine?Places.Where(p=>p.kind==MapPlaceKind.Site).Select(p=>p.Position).ToList():null;
   return WorldMapMath.TrackedMarker(t.position,machine,sites);
  }

  // ------------------------------------------------------------------ save
  public MapState Capture()=>discovery.Capture(LastDowned);
  /// Save restore: the saved places, plus what the progress already implies (older saves have no map state).
  public void Restore(MapState state)
  {
   Bind();
   bool primer=tutorial&&tutorial.Step==BermsStep.Complete;
   discovery.Restore(state,WorldMapDiscovery.Implied(Session?Session.Flags:null,primer));
   LastDowned=WorldMapDiscovery.Downed(state);
  }
 }
}
