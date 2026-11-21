using UnityEngine;
namespace AthenHill
{
 public class AmbientWalker:MonoBehaviour
 {
  /// A pause at one of the route's waypoints (residents pass, 20 Nov 2026): the walker stands there for a while, turned to
  /// a facing, playing its idle clip (or its talk clip) as a working motion, then walks on. Walkers without stops are
  /// unchanged: their update is the original constant-speed loop.
  [System.Serializable]
  public class WorkStop
  {
   [Tooltip("Index into Waypoints where the walker stops.")]
   public int waypoint;
   [Min(0)]public float seconds=20;
   [Tooltip("World yaw (degrees) the walker turns to while stopped.")]
   public float facingYaw;
   [Tooltip("Play the actor's Talk clip instead of its Idle clip while stopped (a second working motion).")]
   public bool talkClip;
   [Tooltip("What the stop is, for QA and the Inspector (\"tally desk\", \"produce stall\").")]
   public string label;
  }
  public Transform[] waypoints;
  [Min(0)]public float speed=1;
  [Range(0,1)]public float phase;
  [Min(0)]public float turnLookAhead=.18f;
  [Min(.01f)]public float turnSharpness=12;
  public ActorAnimation actor;
  [Tooltip("Optional work stops. Empty = walk the loop without stopping (every walker before 20 Nov 2026).")]
  public WorkStop[] stops=new WorkStop[0];
  [Tooltip("Metres before and after a stop over which the walker eases between Slow Factor and full speed (walk playback follows, so feet do not slide).")]
  [Min(0)]public float easeDistance=.9f;
  [Range(.1f,1)]public float slowFactor=.45f;
  [Tooltip("Phase 4 Living Ward (21 Nov 2026): react to dust fronts (hurry between stops, shelter longer) and night (slower evening pace).")]
  public bool reactToWeatherAndTime=true;
  /// Standing at a work stop (BarkDirector lets a working walker make idle remarks).
  public bool AtWork{get;private set;}
  public WorkStop CurrentStop{get;private set;}
  public float StopSecondsLeft{get;private set;}
  public bool SeekingShelter{get;private set;}
  float distance,total;float[] lengths;float[] cumulative;int lastWaypoint=-1;
  CityTimeOfDay clock;
  /// Pure Living Ward pacing rule: dust fronts make walkers hurry between stops and linger at shelter;
  /// night softens walking speed and extends work-stop pauses. Calm daylight returns exact 1.0x authored pacing.
  public static void AmbientPacing(float windStrength,float visibility,float sunVisibility,out float speedScale,out float stopScale,out bool seekingShelter)
  {
   // A dust front is read from visibility only: gusts in clear weather (wind strength with gust swell above 1.8) are not a front.
   bool front=visibility<.75f;
   bool night=sunVisibility<.15f;
   seekingShelter=front;
   if(front){speedScale=Mathf.Lerp(1.25f,1.4f,Mathf.Clamp01((.75f-visibility)/.45f));stopScale=1.5f;}
   else if(night){speedScale=.82f;stopScale=1.35f;}
   else{speedScale=1f;stopScale=1f;}
  }
  void Start(){clock=FindAnyObjectByType<CityTimeOfDay>();lengths=new float[waypoints.Length];cumulative=new float[waypoints.Length];for(int i=0;i<lengths.Length;i++){cumulative[i]=total;lengths[i]=Vector3.Distance(waypoints[i].position,waypoints[(i+1)%lengths.Length].position);total+=lengths[i];}distance=phase*total;Place(true);}
  bool HasStops=>stops!=null&&stops.Length>0;
  void Update()
  {
   if(total<=0)return;
   speedScale=1f;stopScale=1f;bool shelter=false;
   if(reactToWeatherAndTime)
   {
    float sun=clock?clock.SunVisibility:1f;
    AmbientPacing(WeatherConditions.WindStrength,WeatherConditions.Visibility,sun,out speedScale,out stopScale,out shelter);
   }
   SeekingShelter=shelter;
   if(!HasStops){float v=speed*speedScale;distance=(distance+v*Time.deltaTime)%total;Place(false);if(actor)actor.SetMotion(v,false,false);return;}
   UpdateWithStops(Time.deltaTime);
  }
  /// Pacing from the last Update (1 = authored); fields so UpdateWithStops keeps its one-argument signature (tests step it).
  float speedScale=1f,stopScale=1f;
  void UpdateWithStops(float dt)
  {
   if(AtWork)
   {
    StopSecondsLeft-=dt;
    transform.position=Point(distance);
    var face=Quaternion.Euler(0,CurrentStop.facingYaw,0);
    transform.rotation=Quaternion.Slerp(transform.rotation,face,1-Mathf.Exp(-turnSharpness*.5f*dt));
    if(actor)actor.SetMotion(0,false,CurrentStop.talkClip&&!SeekingShelter);
    if(StopSecondsLeft>0)return;
    AtWork=false;CurrentStop=null;
   }
   // ease into and out of stops: the walk clip's playback follows the speed, so the planted foot stays put
   float ahead=float.MaxValue,behind=float.MaxValue;WorkStop next=null;
   if(lastWaypoint>=0&&Mathf.Repeat(distance-cumulative[lastWaypoint],total)>.001f)lastWaypoint=-1;
   foreach(var s in stops)
   {
    if(s==null||s.waypoint<0||s.waypoint>=cumulative.Length)continue;
    float a=Mathf.Repeat(cumulative[s.waypoint]-distance,total),b=Mathf.Repeat(distance-cumulative[s.waypoint],total);
    // a stop at the same place as the one just finished (a zero-length segment) follows it in waypoint order
    bool due=a>0||a<.0001f&&s.waypoint>lastWaypoint;
    if(due&&a<ahead){ahead=a;next=s;}
    if(b<behind)behind=b;
   }
   float ease=easeDistance>0?Mathf.Clamp01(Mathf.Min(ahead,behind)/easeDistance):1;
   float v=speed*speedScale*Mathf.Lerp(slowFactor,1,ease*ease*(3-2*ease));
   float step=v*dt;
   if(next!=null&&ahead<=step)
   {
    distance=cumulative[next.waypoint];AtWork=true;CurrentStop=next;StopSecondsLeft=next.seconds*stopScale;lastWaypoint=next.waypoint;
    transform.position=Point(distance);
    if(actor)actor.SetMotion(0,false,next.talkClip&&!SeekingShelter);
    return;
   }
   distance=(distance+step)%total;Place(false);if(actor)actor.SetMotion(v,false,false);
  }
  Vector3 Point(float at){float d=total>0?Mathf.Repeat(at,total):0;for(int i=0;i<lengths.Length;i++){if(d<=lengths[i])return Vector3.Lerp(waypoints[i].position,waypoints[(i+1)%waypoints.Length].position,d/Mathf.Max(.001f,lengths[i]));d-=lengths[i];}return transform.position;}
  void Place(bool immediate)
  {
   transform.position=Point(distance);
   // Anticipate the next authored segment; position, speed and route timing remain exact.
   var heading=Point(distance+Mathf.Max(.01f,speed*turnLookAhead))-transform.position;
   if(heading.sqrMagnitude<.000001f)return;
   var rotation=Quaternion.LookRotation(heading);
   transform.rotation=immediate?rotation:Quaternion.Slerp(transform.rotation,rotation,1-Mathf.Exp(-turnSharpness*Time.deltaTime));
  }
  void OnDrawGizmosSelected()
  {
   if(waypoints==null)return;Gizmos.color=Color.cyan;for(int i=0;i<waypoints.Length;i++)if(waypoints[i]&&waypoints[(i+1)%waypoints.Length])Gizmos.DrawLine(waypoints[i].position,waypoints[(i+1)%waypoints.Length].position);
   if(stops==null)return;Gizmos.color=new Color(1,.6f,.1f);
   foreach(var s in stops)if(s!=null&&s.waypoint>=0&&s.waypoint<waypoints.Length&&waypoints[s.waypoint]){var p=waypoints[s.waypoint].position;Gizmos.DrawWireSphere(p,.25f);Gizmos.DrawLine(p+Vector3.up*.1f,p+Vector3.up*.1f+Quaternion.Euler(0,s.facingYaw,0)*Vector3.forward*.6f);}
  }
 }
}
