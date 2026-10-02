using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill
{
 /// A walk-in interior (the Salvage shop, 1 Oct 2026). The city has no baked light probes, so every renderer takes the
 /// sky's trilight ambient and a closed room would be as bright as the street. This gives the interior's renderers a
 /// custom ambient probe: the sky ambient scaled down and warmed, plus sky light entering through the open bay. Actors
 /// (the player, first-person arms) blend to the same probe as they walk in. The interior's lamps are indoor lights:
 /// on by day and night, switched off when the viewer is far away so they do not take the city's light budget (URP on
 /// the Linux OpenGL player draws 32 lights per camera) from across town.
 [DisallowMultipleComponent]
 public class InteriorLighting:MonoBehaviour
 {
  [Tooltip("Room volume in this object's local space (for the shop root: facade centre at paving level, +Z to the avenue).")]
  public Bounds localBounds=new Bounds(new Vector3(0,2.5f,-3.45f),new Vector3(6.76f,3.95f,6.06f));
  [Tooltip("Local direction the outside light comes in from (towards the opening).")]
  public Vector3 openingDirection=Vector3.forward;
  [Tooltip("Static interior renderers (shell and props). Found from Interior Roots when empty at start.")]
  public List<Renderer> renderers=new List<Renderer>();
  [Tooltip("Every renderer under these objects is lit as interior (the shell's Interior* meshes are added by name).")]
  public Transform[] interiorRoots=new Transform[0];
  public Light[] lamps=new Light[0];
  [Tooltip("Rendering layer the interior lamps light (bit 7, \"Light Layer 7\"). Interior renderers carry it as well as Default, so the lamps never shine through the walls onto the street; the player carries it while inside.")]
  public uint interiorLayer=1u<<7;
  [Header("Ambient")]
  [Range(0,1)]public float ambientScale=.3f;
  public Color ambientTint=new Color(1f,.88f,.74f);
  [Tooltip("Sky light through the opening, as a directional term (fraction of the horizon ambient).")]
  [Range(0,2)]public float openingLight=.55f;
  [Tooltip("Actors blend to the interior probe over this distance past the opening plane.")]
  [Min(.1f)]public float blendMetres=1.4f;
  [Min(.05f)]public float refreshSeconds=.25f;
  [Header("Visibility")]
  [Tooltip("The room is drawn only while the camera is inside it or in front of its opening (walls hide it from everywhere else; the city has no occlusion culling).")]
  public bool cullWhenUnseen=true;
  [Tooltip("Metres in front of the room's inner face that the outer facade stands (the opening's depth).")]
  [Min(0)]public float facadeDepth=.42f;
  [Tooltip("The opening's outline in local space (four corners in order round the rectangle). From outside, a prop is drawn only when its bounds can be seen through it.")]
  public Vector3[] openingCorners=new Vector3[0];
  public bool RoomVisible {get;private set;}=true;
  /// Props (and the colonist) drawn this frame; the room's own shell is never portal-culled.
  public int PropsDrawn {get;private set;}
  readonly List<Renderer> shell=new List<Renderer>(),props=new List<Renderer>();
  readonly Dictionary<Renderer,bool> drawn=new Dictionary<Renderer,bool>();
  readonly Plane[] portal=new Plane[5];
  bool shAmbient=true,portalCulling=true;
  [Header("Lamps")]
  [Tooltip("Lamps are on while the camera is within this distance of the room and the room is in view.")]
  [Min(1)]public float lampsOnWithin=34;
  public Transform viewer;
  readonly List<Renderer> actors=new List<Renderer>();
  readonly Dictionary<Renderer,LightProbeUsage> actorUsage=new Dictionary<Renderer,LightProbeUsage>();
  readonly Dictionary<Renderer,uint> actorLayers=new Dictionary<Renderer,uint>();
  MaterialPropertyBlock block;
  SphericalHarmonicsL2[] one=new SphericalHarmonicsL2[1];
  Transform player;float nextRefresh;bool lampsOn=true;float[] lampIntensity;
  public SphericalHarmonicsL2 InteriorProbe {get;private set;}
  public float PlayerInside {get;private set;}

  void Start()
  {
   block=new MaterialPropertyBlock();
   foreach(var root in interiorRoots)if(root)foreach(var r in root.GetComponentsInChildren<Renderer>(true))if(!renderers.Contains(r))renderers.Add(r);
   foreach(var r in GetComponentsInChildren<Renderer>(true))if(r.name.Contains("_Interior")&&!renderers.Contains(r))renderers.Add(r);
   foreach(var r in renderers)if(r){r.lightProbeUsage=LightProbeUsage.CustomProvided;r.renderingLayerMask|=interiorLayer;(r.name.Contains("_Interior")?shell:props).Add(r);}
   foreach(var l in lamps)if(l)l.renderingLayerMask=(int)interiorLayer;
   var motor=FindAnyObjectByType<PlayerMotor>();
   if(motor)
   {
    player=motor.transform;
    foreach(var r in motor.GetComponentsInChildren<Renderer>(true))actors.Add(r);
   }
   var arms=FindAnyObjectByType<FirstPersonViewModel>(FindObjectsInactive.Include);
   if(arms)foreach(var r in arms.GetComponentsInChildren<Renderer>(true))if(!actors.Contains(r))actors.Add(r);
   foreach(var r in actors)if(r){actorUsage[r]=r.lightProbeUsage;actorLayers[r]=r.renderingLayerMask;}
   lampIntensity=new float[lamps.Length];for(int i=0;i<lamps.Length;i++)if(lamps[i])lampIntensity[i]=lamps[i].intensity;
#if UNITY_EDITOR || DEBUG
   // Cost attribution in development builds (A/B in one build): ATHEN_INTERIOR_OFF=lamps|room|probe|all
   var off=System.Environment.GetEnvironmentVariable("ATHEN_INTERIOR_OFF")??"";
   if(off=="lamps"||off=="all"){foreach(var l in lamps)if(l)l.gameObject.SetActive(false);lamps=new Light[0];}
   if(off=="room"||off=="all"){foreach(var r in renderers)if(r)r.forceRenderingOff=true;renderers.Clear();shell.Clear();props.Clear();}
   if(off=="probe"||off=="all")foreach(var p in GetComponentsInChildren<ReflectionProbe>(true))p.enabled=false;
   if(off=="sh"){shAmbient=false;foreach(var r in renderers)if(r)r.lightProbeUsage=LightProbeUsage.BlendProbes;}
   if(off=="portal")portalCulling=false;
   if(off!="")Debug.Log("InteriorLighting: ATHEN_INTERIOR_OFF="+off);
#endif
   Refresh();
  }
  void OnDisable()
  {
   foreach(var pair in actorUsage)if(pair.Key){pair.Key.lightProbeUsage=pair.Value;pair.Key.renderingLayerMask=actorLayers[pair.Key];Clear(pair.Key);}
  }
  void LateUpdate()
  {
   if(!viewer){var cam=Camera.main;if(cam)viewer=cam.transform;}
   UpdateVisibility();
   UpdateLamps();
   if(Time.unscaledTime>=nextRefresh){nextRefresh=Time.unscaledTime+refreshSeconds;Refresh();}
   UpdateActors();
  }
  /// How far inside the room a world point is: 0 outside or at the opening plane, 1 a blend distance in.
  public float Inside(Vector3 world)
  {
   var p=transform.InverseTransformPoint(world);var b=localBounds;
   if(p.x<b.min.x||p.x>b.max.x||p.y<b.min.y-.6f||p.y>b.max.y||p.z<b.min.z-.2f)return 0;
   // the room's open side is +Z (the bay); depth past that plane drives the blend
   return Mathf.Clamp01((b.max.z+.35f-p.z)/blendMetres);
  }
  static SphericalHarmonicsL2 Sky(bool fromColours=false)
  {
   var sh=RenderSettings.ambientProbe;
   // Fallback when the engine has not filled the probe from the trilight colours.
   if(fromColours||sh[0,0]+sh[1,0]+sh[2,0]<1e-4f)
   {
    sh=new SphericalHarmonicsL2();
    sh.AddAmbientLight(RenderSettings.ambientEquatorColor*RenderSettings.ambientIntensity);
    sh.AddDirectionalLight(Vector3.up,(RenderSettings.ambientSkyColor-RenderSettings.ambientEquatorColor)*.5f,RenderSettings.ambientIntensity);
   }
   return sh;
  }
  /// Editor previews (no Play mode): the interior probe from the current trilight colours on the room's renderers.
  public void ApplyInEditor()
  {
   block=new MaterialPropertyBlock();
   var list=new List<Renderer>(renderers.Where(r=>r));
   foreach(var root in interiorRoots)if(root)foreach(var r in root.GetComponentsInChildren<Renderer>(true))if(!list.Contains(r))list.Add(r);
   foreach(var r in list)r.lightProbeUsage=LightProbeUsage.CustomProvided;
   Refresh(true,list);
  }
  void Refresh()=>Refresh(false,renderers);
  void Refresh(bool fromColours,List<Renderer> targets)
  {
   var sky=Sky(fromColours);
   var sh=sky*ambientScale;
   for(int c=0;c<3;c++)for(int k=0;k<9;k++)sh[c,k]*=ambientTint[c];
   var horizon=RenderSettings.ambientEquatorColor*RenderSettings.ambientIntensity;
   sh.AddDirectionalLight(transform.TransformDirection(openingDirection.normalized),horizon*openingLight,1);
   InteriorProbe=sh;
   one[0]=sh;
   if(shAmbient)foreach(var r in targets)if(r){r.GetPropertyBlock(block);block.CopySHCoefficientArraysFrom(one);r.SetPropertyBlock(block);}
  }
  void UpdateActors()
  {
   float w=player?Inside(player.position+Vector3.up*.9f):0;PlayerInside=w;
   if(w<=.001f){foreach(var pair in actorUsage)if(pair.Key&&pair.Key.lightProbeUsage!=pair.Value){pair.Key.lightProbeUsage=pair.Value;pair.Key.renderingLayerMask=actorLayers[pair.Key];Clear(pair.Key);}return;}
   var sky=Sky();var mix=sky*(1-w)+InteriorProbe*w;one[0]=mix;
   foreach(var r in actors)
   {
    if(!r)continue;
    r.lightProbeUsage=LightProbeUsage.CustomProvided;r.renderingLayerMask=actorLayers[r]|interiorLayer;
    r.GetPropertyBlock(block);block.CopySHCoefficientArraysFrom(one);r.SetPropertyBlock(block);
   }
  }
  void Clear(Renderer r){r.GetPropertyBlock(block);block.Clear();r.SetPropertyBlock(block);}
  /// Cheap portal test: inside the room, or anywhere in front of the facade (from there the opening can be in view).
  public bool SeenFrom(Vector3 world)
  {
   var c=transform.InverseTransformPoint(world);var b=localBounds;b.Expand(1f);
   if(b.Contains(c))return true;
   var n=openingDirection.normalized;
   float face=Vector3.Dot(localBounds.center,n)+Mathf.Abs(Vector3.Dot(localBounds.extents,new Vector3(Mathf.Abs(n.x),Mathf.Abs(n.y),Mathf.Abs(n.z))));
   return Vector3.Dot(c,n)>face+facadeDepth*.5f;
  }
  void UpdateVisibility()
  {
   bool seen=!cullWhenUnseen||!viewer||SeenFrom(viewer.position);
   if(seen!=RoomVisible){RoomVisible=seen;foreach(var r in shell)if(r)r.forceRenderingOff=!seen;}
   // props: everything inside the room; from outside only what the opening reveals; nothing when the room is unseen
   bool inside=viewer&&Inside(viewer.position)>0;
   bool portalTest=seen&&!inside&&portalCulling&&cullWhenUnseen&&viewer&&openingCorners.Length==4&&BuildPortal(viewer.position);
   int n=0;
   foreach(var r in props)
   {
    if(!r)continue;
    bool show=seen&&(!portalTest||GeometryUtility.TestPlanesAABB(portal,r.bounds));
    if(!drawn.TryGetValue(r,out var was)||was!=show){drawn[r]=show;r.forceRenderingOff=!show;}
    if(show)n++;
   }
   PropsDrawn=n;
  }
  /// Planes from the eye through the opening's four edges (normals into the view), and the opening plane itself.
  bool BuildPortal(Vector3 eye)
  {
   var w=new Vector3[4];var mid=Vector3.zero;
   for(int i=0;i<4;i++){w[i]=transform.TransformPoint(openingCorners[i]);mid+=w[i]/4;}
   var inward=-transform.TransformDirection(openingDirection.normalized);
   var probe=mid+inward*1.5f;
   for(int i=0;i<4;i++)
   {
    var a=w[i];var b=w[(i+1)%4];
    var nrm=Vector3.Cross(a-eye,b-eye);if(nrm.sqrMagnitude<1e-8f)return false;
    var pl=new Plane(nrm.normalized,eye);if(pl.GetDistanceToPoint(probe)<0)pl.Flip();
    portal[i]=pl;
   }
   portal[4]=new Plane(inward,mid);
   return true;
  }
  void UpdateLamps()
  {
   if(lamps==null||lamps.Length==0||!viewer)return;
   float d=Vector3.Distance(viewer.position,transform.TransformPoint(localBounds.center));
   bool on=RoomVisible&&(lampsOn?d<lampsOnWithin+2:d<lampsOnWithin);
   if(on==lampsOn)return;
   lampsOn=on;
   foreach(var l in lamps)if(l)l.enabled=on;
  }
  void OnDrawGizmosSelected(){Gizmos.matrix=transform.localToWorldMatrix;Gizmos.color=new Color(1f,.8f,.4f,.6f);Gizmos.DrawWireCube(localBounds.center,localBounds.size);}
 }
}
