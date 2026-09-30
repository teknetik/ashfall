using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
namespace AthenHill
{
 /// Field-pack colonist view. A camera renders only the player colonist into a texture the pack shows: for that
 /// camera's pass alone the colonist's renderers join the preview layer, the studio lights switch on, and the scene
 /// lights listed in Mute Lights plus any lamp whose range reaches the colonist switch off, so the colonist reads the
 /// same at any hour and anywhere in the city. Runs only while Active.
 [DisallowMultipleComponent]
 public class CharacterPreview:MonoBehaviour
 {
  public PlayerMotor player;
  [Tooltip("Renders the colonist into Texture. Kept disabled while the pack is closed.")]
  public Camera previewCamera;
  [Tooltip("Studio lights, children of the preview camera. Lit only during the preview pass.")]
  public Light[] studioLights=new Light[0];
  [Tooltip("Scene lights (the sun and sky fill) switched off during the preview pass.")]
  public Light[] muteLights=new Light[0];
  [Tooltip("Layer the colonist joins during the preview pass. The preview camera renders only this layer.")]
  [Range(0,31)]public int previewLayer=10;
  [Tooltip("Renderers on these layers stay out of the preview (first-person arms).")]
  public LayerMask excludeLayers=1<<9;
  [Tooltip("Also switch off, for the preview pass only, every other lamp whose range reaches the colonist.")]
  public bool muteNearbyLights=true;
  [Tooltip("Texture size; its aspect matches the pack's colonist panel.")]
  public Vector2Int resolution=new Vector2Int(640,1040);
  [Range(1,8)]public int msaa=4;
  [Header("Framing")]
  [Range(10,60)]public float fieldOfView=24;
  [Min(.5f)]public float distance=5f;
  [Tooltip("Height of the camera above the colonist's feet (m).")]
  public float cameraHeight=1.15f;
  [Tooltip("Height of the point the camera looks at (m).")]
  public float focusHeight=.92f;
  [Tooltip("Degrees per reference pixel when the player drags the view.")]
  [Min(0)]public float dragDegreesPerPixel=.45f;
  /// Orbit around the colonist in degrees; 0 faces them.
  public float Yaw {get;set;}
  public RenderTexture Texture {get;private set;}
  public bool Active {get;private set;}
  readonly List<Renderer> renderers=new List<Renderer>();
  readonly List<int> savedLayers=new List<int>();
  readonly List<ShadowCastingMode> savedShadows=new List<ShadowCastingMode>();
  readonly List<bool> savedMuted=new List<bool>();
  readonly List<Light> sceneLights=new List<Light>(),nearbyMuted=new List<Light>();
  // Shadow modes as authored (read before first person can hide the colonist): shadow-only proxies stay out.
  readonly Dictionary<Renderer,ShadowCastingMode> authored=new Dictionary<Renderer,ShadowCastingMode>();
  bool swapped;

  void Awake()
  {
   if(previewCamera)previewCamera.enabled=false;
   SetStudio(false);
   if(player)foreach(var r in player.GetComponentsInChildren<Renderer>(true))if(r)authored[r]=r.shadowCastingMode;
  }
  void OnEnable(){RenderPipelineManager.beginCameraRendering+=Begin;RenderPipelineManager.endCameraRendering+=End;}
  void OnDisable(){RenderPipelineManager.beginCameraRendering-=Begin;RenderPipelineManager.endCameraRendering-=End;Restore();SetActive(false);}
  void OnDestroy(){if(Texture){Texture.Release();Destroy(Texture);Texture=null;}}

  /// Starts or stops the preview camera. The texture is created on first use and kept for the session.
  public void SetActive(bool active)
  {
   if(active&&(!previewCamera||!player))active=false;
   if(active==Active&&(!previewCamera||previewCamera.enabled==active))return;
   Active=active;
   if(!previewCamera)return;
   if(active&&!Texture)
   {
    Texture=new RenderTexture(Mathf.Max(64,resolution.x),Mathf.Max(64,resolution.y),24,RenderTextureFormat.ARGB32){name="Colonist preview",antiAliasing=Mathf.ClosestPowerOfTwo(Mathf.Clamp(msaa,1,8))};
    Texture.Create();
   }
   if(active)
   {
    previewCamera.targetTexture=Texture;previewCamera.cullingMask=1<<previewLayer;
    previewCamera.clearFlags=CameraClearFlags.SolidColor;previewCamera.backgroundColor=new Color(0,0,0,0);
    previewCamera.allowHDR=false;previewCamera.fieldOfView=fieldOfView;previewCamera.aspect=Texture.width/(float)Texture.height;
    var data=previewCamera.GetUniversalAdditionalCameraData();
    if(data){data.renderPostProcessing=false;data.antialiasing=AntialiasingMode.None;data.requiresColorTexture=false;data.requiresDepthTexture=false;data.volumeLayerMask=0;data.renderShadows=true;}
    CollectRenderers();Frame();
   }
   previewCamera.enabled=active;
  }
  public void Drag(float referencePixels){Yaw=Mathf.Repeat(Yaw+referencePixels*dragDegreesPerPixel+180,360)-180;}

  void LateUpdate(){if(Active)Frame();}
  /// Keeps the camera in front of the colonist (plus the player's orbit), framed head to toe.
  void Frame()
  {
   if(!previewCamera||!player)return;
   var body=player.visual?player.visual:player.transform;
   var forward=Vector3.ProjectOnPlane(body.forward,Vector3.up);
   if(forward.sqrMagnitude<1e-4f)forward=Vector3.forward;
   forward=Quaternion.Euler(0,Yaw,0)*forward.normalized;
   var feet=player.transform.position;
   var focus=feet+Vector3.up*focusHeight;
   previewCamera.transform.SetPositionAndRotation(feet+forward*distance+Vector3.up*cameraHeight,Quaternion.LookRotation(focus-(feet+forward*distance+Vector3.up*cameraHeight),Vector3.up));
   previewCamera.fieldOfView=fieldOfView;
  }
  /// The colonist's own meshes (body, held pistol and mods): not effects, first-person arms or shadow-only proxies.
  void CollectRenderers()
  {
   renderers.Clear();sceneLights.Clear();
   if(!player)return;
   var body=player.visual?player.visual:player.transform;
   foreach(var r in body.GetComponentsInChildren<Renderer>(true))
   {
    if(!r||(excludeLayers.value&(1<<r.gameObject.layer))!=0||r is ParticleSystemRenderer||r is LineRenderer||r is TrailRenderer)continue;
    if(!authored.TryGetValue(r,out var mode))authored[r]=mode=r.shadowCastingMode;
    if(mode!=ShadowCastingMode.ShadowsOnly)renderers.Add(r);
   }
   if(muteNearbyLights)foreach(var l in FindObjectsByType<Light>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))
    if(l&&l.type!=LightType.Directional&&System.Array.IndexOf(studioLights,l)<0&&System.Array.IndexOf(muteLights,l)<0)sceneLights.Add(l);
  }
  void Begin(ScriptableRenderContext context,Camera camera)
  {
   if(camera!=previewCamera||!Active||swapped)return;
   savedLayers.Clear();savedShadows.Clear();
   foreach(var r in renderers)
   {
    savedLayers.Add(r?r.gameObject.layer:0);savedShadows.Add(r?r.shadowCastingMode:ShadowCastingMode.On);
    if(!r)continue;
    r.gameObject.layer=previewLayer;
    // First person hides the colonist by leaving only its shadow; the preview shows it whole.
    if(r.shadowCastingMode==ShadowCastingMode.ShadowsOnly)r.shadowCastingMode=ShadowCastingMode.On;
   }
   savedMuted.Clear();
   foreach(var l in muteLights){savedMuted.Add(l&&l.enabled);if(l)l.enabled=false;}
   nearbyMuted.Clear();
   var at=player.transform.position+Vector3.up*.9f;
   foreach(var l in sceneLights)if(l&&l.enabled&&(l.transform.position-at).sqrMagnitude<(l.range+1.2f)*(l.range+1.2f)){l.enabled=false;nearbyMuted.Add(l);}
   SetStudio(true);
   swapped=true;
  }
  void End(ScriptableRenderContext context,Camera camera){if(camera==previewCamera)Restore();}
  void Restore()
  {
   if(!swapped)return;
   for(int i=0;i<renderers.Count&&i<savedLayers.Count;i++){var r=renderers[i];if(!r)continue;r.gameObject.layer=savedLayers[i];r.shadowCastingMode=savedShadows[i];}
   for(int i=0;i<muteLights.Length&&i<savedMuted.Count;i++)if(muteLights[i])muteLights[i].enabled=savedMuted[i];
   foreach(var l in nearbyMuted)if(l)l.enabled=true;
   nearbyMuted.Clear();
   SetStudio(false);
   swapped=false;
  }
  void SetStudio(bool on){foreach(var l in studioLights)if(l)l.enabled=on;}
 }
}
