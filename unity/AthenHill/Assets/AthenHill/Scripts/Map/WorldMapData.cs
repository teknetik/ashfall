using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// World map state in a save (19 Nov 2026, additive to save v4): the places the player has found and where they last
 /// went down. Absent in older saves, which load with only what their progress implies (WorldMapDiscovery.Implied).
 [Serializable] public class MapState {public string[] discovered;public bool downed;public float downedX,downedZ;}

 public enum MapPlaceKind { Gate, Landmark, Shop, Service, Home, BermsPlace, Site, Waystation }

 /// One named place on the sheet. City places are always shown; Berms sites only once discovered.
 public sealed class MapPlace
 {
  public string id,name;
  public MapPlaceKind kind;
  public Vector2 position;
  /// Discovery radius in metres (sites); 0 = always known.
  public float radius;
  /// Optional live anchor: the place follows it (a colonist at a counter, the home, a site root).
  public Transform anchor;
  public Vector2 Position=>anchor?new Vector2(anchor.position.x,anchor.position.z):position;
  public bool Discoverable=>radius>0;
  public MapPlace(string id,string name,MapPlaceKind kind,float x,float z,float radius=0){this.id=id;this.name=name;this.kind=kind;position=new Vector2(x,z);this.radius=radius;}
 }

 /// Which places the player has found. Pure (no scene access) so the discovery and old-save rules are testable.
 public sealed class WorldMapDiscovery
 {
  public const string DepotId="site:machine_depot";
  public const string LatticePrefix="lattice:";
  public static string LatticeRelayId(string terminalId)=>string.IsNullOrEmpty(terminalId)?null:LatticePrefix+terminalId;
  public static IEnumerable<string> ImpliedTerminals(IEnumerable<string> unlockedTerminals)
  {
   if(unlockedTerminals!=null)foreach(var id in unlockedTerminals)if(!string.IsNullOrEmpty(id))yield return LatticeRelayId(id);
  }
  readonly HashSet<string> found=new HashSet<string>(StringComparer.Ordinal);
  public IReadOnlyCollection<string> Found=>found;
  public bool Has(string id)=>!string.IsNullOrEmpty(id)&&found.Contains(id);
  public bool Add(string id)=>!string.IsNullOrEmpty(id)&&found.Add(id);
  /// Marks every discoverable place within its radius of the player; returns the ones found just now.
  public List<MapPlace> Visit(Vector3 player,IEnumerable<MapPlace> places,Func<string,bool> allowed=null)
  {
   var now=new List<MapPlace>();
   if(places==null)return now;
   foreach(var p in places)
   {
    if(p==null||!p.Discoverable||found.Contains(p.id))continue;
    if(allowed!=null&&!allowed(p.id))continue;
    var at=p.Position;
    if(WorldMapMath.WithinRadius(player,new Vector3(at.x,0,at.y),p.radius)&&found.Add(p.id))now.Add(p);
   }
   return now;
  }
  /// Native QA fix (19 Nov 2026): a site the Warden's primer introduces is not discoverable before the primer reaches it
  /// (a new game walking out of the gate passed within 55 m of the depot and marked it). The machine depot opens at the
  /// Depot step, the moment the HUD's "MACHINE DEPOT" guidance appears; every other place keeps the radius rule.
  public static bool PrimerAllows(string id,BermsStep step)=>id!=DepotId||step>=BermsStep.Depot;
  /// What a save's progress already proves the player has seen: every waystation they checked in at (its story flag
  /// "waystation:ID" is also its map id) and, once the Warden's primer is done, the machine depot it ends at.
  public static IEnumerable<string> Implied(IEnumerable<string> flags,bool primerComplete)
  {
   if(flags!=null)foreach(var f in flags)if(!string.IsNullOrEmpty(f)&&f.StartsWith("waystation:",StringComparison.Ordinal))yield return f;
   if(primerComplete)yield return DepotId;
  }
  public MapState Capture(Vector2? downed)=>new MapState{discovered=found.OrderBy(x=>x,StringComparer.Ordinal).ToArray(),downed=downed.HasValue,downedX=downed?.x??0,downedZ=downed?.y??0};
  /// Replaces the found set with the save's (null in older saves) plus what progress implies.
  public void Restore(MapState state,IEnumerable<string> implied)
  {
   found.Clear();
   if(state?.discovered!=null)foreach(var id in state.discovered)Add(id);
   if(implied!=null)foreach(var id in implied)Add(id);
  }
  public static Vector2? Downed(MapState state)=>state!=null&&state.downed&&ClockMath.Finite(state.downedX)&&ClockMath.Finite(state.downedZ)?new Vector2(state.downedX,state.downedZ):(Vector2?)null;
 }

 /// The drawn sheet's data (19 Nov 2026), from the dated layout records rather than the scene, so the map draws
 /// without a texture or a scene scan. Units are Unity world metres, x east and z north. Sources:
 /// walls art/perimeter_walls_20261001/layout.json; shops art/wall_foot_drifts_20261001/faces.json (wall faces);
 /// hill, hall art/wall_foot_drifts_20261001/layout.json; water point and goods dock art/ward_life_20261003/layout.json;
 /// Ward buildings art/ward_buildings_20261003/layout.json; hydroponics art/hydroponics_20261001/layout.json;
 /// the Berms bowl, trails and sites art/berms_expanse_20261002 (footprint.json, sites.json);
 /// the gate post and range art/training_range_20261001/survey.json.
 public static class WorldMapSchematic
 {
  public struct Segment {public Vector2 a,b;public bool gap;public Segment(float ax,float az,float bx,float bz,bool gap=false){a=new Vector2(ax,az);b=new Vector2(bx,bz);this.gap=gap;}}
  public struct Block {public Rect rect;public bool ruin;public Block(float x0,float z0,float x1,float z1,bool ruin=false){rect=Rect.MinMaxRect(x0,z0,x1,z1);this.ruin=ruin;}}

  /// Curtain walls, the +X rampart and strip wall, and the Berms walls either side of the West Gate portal.
  public static readonly Segment[] Walls=
  {
   new Segment(-60,44.5f,60,44.5f),new Segment(-60,-44.5f,60,-44.5f),
   new Segment(48,-44.9f,48,-4.6f),new Segment(48,16.6f,48,44.9f),new Segment(59,-44,59,44),
   new Segment(-59,44,-59,4.6f),new Segment(-59,-2.5f,-59,-44),
  };
  /// Openings: the two barred arches in the +X rampart (the East Gate, where the player arrives) and the West Gate portal into the Berms.
  public static readonly Segment[] Gates={new Segment(48,-4.6f,48,5.2f,true),new Segment(48,6.8f,48,16.6f,true),new Segment(-59,-2.5f,-59,4.6f,true)};
  /// Building footprints (shops from their measured wall faces; others from their layout roots, approximate).
  public static readonly Block[] Blocks=
  {
   new Block(-25.1f,-21.9f,-14.5f,-14.1f),new Block(-25.1f,-12.9f,-14.5f,-5.1f),new Block(-25.1f,5.1f,-14.5f,12.9f),new Block(-25.1f,14.1f,-14.5f,21.9f),
   new Block(14.5f,-21.9f,25.1f,-14.1f),new Block(14.5f,-12.9f,25.1f,-5.1f),new Block(14.5f,5.1f,25.1f,12.9f),new Block(14.5f,14.1f,25.1f,21.9f),
   new Block(4.6f,13.6f,11.3f,18.2f),                       // Basic General booth
   new Block(-16.6f,-36.6f,-3.5f,-23.8f),                   // Vanguard Hall
   new Block(30,-34,42,-22),                                // Nanofab 2
   new Block(29,26,43,40,true),                             // Processing 11 (roofless)
   new Block(-41,-36,-29,-25),                              // Aquifer 3
   new Block(-40,26.5f,-28,30.5f),new Block(-40,34.5f,-28,38.5f), // hydroponics quonsets
   new Block(-11,39.4f,-7,42.2f),new Block(7,39.4f,11,42.2f),     // Node 07 west / east
   new Block(16.2f,-43,21.8f,-40.2f),new Block(25,-42.8f,30,-40),new Block(-20,40,-15,42.8f),new Block(-26.5f,39.8f,-21.5f,42.6f),new Block(-57.4f,-26.5f,-54.6f,-21.5f), // wall homes
   new Block(-57.5f,37,-53.4f,41.3f),new Block(-57.5f,-41.3f,-53.4f,-37),new Block(41.4f,37,45.5f,41.3f),new Block(41.4f,-41.3f,45.5f,-37), // watchtowers
  };
  /// The hill (plinth and tree ring) as a disc.
  public static readonly Vector2 HillCentre=new Vector2(.8f,-.2f);
  public const float HillRadius=9;
  /// The Quantum Tube conduit along the north wall.
  public static readonly Segment[] Conduit={new Segment(-44,42.2f,-11,42.2f),new Segment(11,42.2f,36,42.2f)};

  /// The foot of the western mountains (footprint.json "bowl", before the generator's noise warp).
  public static readonly Vector2[] Bowl=
  {
   new Vector2(-60,80),new Vector2(-110,92),new Vector2(-150,122),new Vector2(-205,165),new Vector2(-270,196),new Vector2(-335,214),new Vector2(-395,204),
   new Vector2(-440,222),new Vector2(-490,196),new Vector2(-525,150),new Vector2(-542,95),new Vector2(-566,40),new Vector2(-552,-15),new Vector2(-562,-70),
   new Vector2(-532,-118),new Vector2(-488,-160),new Vector2(-430,-200),new Vector2(-370,-214),new Vector2(-318,-234),new Vector2(-262,-212),new Vector2(-215,-180),
   new Vector2(-172,-150),new Vector2(-140,-118),new Vector2(-112,-96),new Vector2(-85,-86),new Vector2(-60,-84),
  };
  /// The original Berms ground beyond the West Gate: the repainted road, the Warden post and the range stand on it.
  public static readonly Rect OldBerms=Rect.MinMaxRect(-104,-60,-54,48);
  /// Warden trail routes (sites.json "routes"; the cairns stand on them).
  public static readonly Vector2[][] Trails=
  {
   new[]{new Vector2(-104,12),new Vector2(-126,30),new Vector2(-170,44),new Vector2(-222,50),new Vector2(-262,48)},
   new[]{new Vector2(-262,48),new Vector2(-300,30),new Vector2(-322,20)},
   new[]{new Vector2(-262,58),new Vector2(-280,100),new Vector2(-298,128)},
   new[]{new Vector2(-322,4),new Vector2(-351,-1),new Vector2(-380,-6),new Vector2(-410,-12),new Vector2(-440,-18),new Vector2(-478,-22)},
   new[]{new Vector2(-112,-62),new Vector2(-160,-70),new Vector2(-210,-82),new Vector2(-262,-98),new Vector2(-284,-104)},
  };

  /// City places, always on the sheet. Live anchors (colonists, the hill and Lattice points, the home) replace these
  /// positions at runtime where they exist.
  public static List<MapPlace> CityPlaces()=>new List<MapPlace>
  {
   new MapPlace("city:hill","Hill Tree",MapPlaceKind.Landmark,HillCentre.x,HillCentre.y),
   new MapPlace("city:lattice_jack","Lattice Jack",MapPlaceKind.Landmark,0,35.5f),
   new MapPlace("city:vanguard_hall","Vanguard Hall",MapPlaceKind.Landmark,-10,-30),
   new MapPlace("city:basic_general","Basic General",MapPlaceKind.Shop,8,16),
   new MapPlace("city:salvage","Salvage",MapPlaceKind.Shop,-19.8f,18),
   new MapPlace("city:tool_exchange","Tool Exchange",MapPlaceKind.Shop,-19.8f,9),
   new MapPlace("city:air_water","Air + Water",MapPlaceKind.Shop,-19.8f,-9),
   new MapPlace("city:relay_works","Relay Works",MapPlaceKind.Shop,-19.8f,-18),
   new MapPlace("city:thread_hide","Thread + Hide",MapPlaceKind.Shop,19.8f,18),
   new MapPlace("city:repairs","Repairs",MapPlaceKind.Shop,19.8f,9),
   new MapPlace("city:field_supply","Field Supply",MapPlaceKind.Shop,19.8f,-9),
   new MapPlace("city:finery","Finery",MapPlaceKind.Shop,19.8f,-18),
   new MapPlace("city:water_point","Water ration point",MapPlaceKind.Service,4,-33),
   new MapPlace("city:goods_dock","Node 07 goods dock",MapPlaceKind.Service,10,34),
   new MapPlace("city:nanofab","Nanofab 2",MapPlaceKind.Service,36,-28),
   new MapPlace("city:processing","Processing 11",MapPlaceKind.Service,36,33),
   new MapPlace("city:aquifer","Aquifer 3",MapPlaceKind.Service,-35,-30.5f),
   new MapPlace("city:hydroponics","Hydroponics",MapPlaceKind.Service,-34,32.5f),
   new MapPlace("city:barred_gates","East Gate",MapPlaceKind.Gate,51,6), // the +X spawn arches (id kept from the first map)
  };
  /// Berms places the Wardens show every newcomer (always on the sheet).
  public static List<MapPlace> BermsPlaces()=>new List<MapPlace>
  {
   new MapPlace("berms:west_gate","West Gate",MapPlaceKind.Gate,-58,1),
   new MapPlace("berms:warden_post","Warden post",MapPlaceKind.BermsPlace,-69,-3),
   new MapPlace("berms:range","Warden training range",MapPlaceKind.BermsPlace,-80,16),
  };
 }
}
