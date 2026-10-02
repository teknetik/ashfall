using System.Collections.Generic;
using System.Linq;
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
  GameObject weaponRoot;
  string weaponSignature;
  Bounds weaponBounds;
  readonly List<Mesh> previewMeshes=new List<Mesh>();
  readonly List<bool> savedEnabled=new List<bool>();
  public bool ShowingWeapon {get;private set;}
  sealed class StudioState{public Light light;public Vector3 position;public Quaternion rotation;public float intensity,range;}
  readonly List<StudioState> studioState=new List<StudioState>();
  void CaptureStudio()
  {
   if(studioState.Count>0)return;
   foreach(var light in studioLights)if(light)studioState.Add(new StudioState{light=light,position=light.transform.localPosition,rotation=light.transform.localRotation,intensity=light.intensity,range=light.range});
  }
  void RestoreStudio()
  {
   foreach(var state in studioState)if(state.light){state.light.transform.localPosition=state.position;state.light.transform.localRotation=state.rotation;state.light.intensity=state.intensity;state.light.range=state.range;}
   studioState.Clear();
  }
  void FrameWeaponStudio(float range,float radius)
  {
   float scale=Mathf.Max(.08f,radius/.95f);var subject=Vector3.forward*range;
   foreach(var state in studioState)if(state.light)
   {
    var p=(state.position-Vector3.forward*distance)*scale+subject;
    state.light.transform.localPosition=p;state.light.transform.localRotation=Quaternion.LookRotation(subject-p,Vector3.up);
    state.light.intensity=state.intensity*scale*scale;state.light.range=Mathf.Max(.5f,state.range*scale);
   }
  }

  /// A display-only mesh copy has no colliders, scripts, audio, animator or gameplay state.
  /// Its renderers are enabled only for the preview camera pass, so it cannot leak into the world camera.
  public bool SetWeapon(GameObject source,WeaponLoadout loadout)
  {
   string next=source?source.GetEntityId()+":"+(loadout==null?"":string.Join(";",loadout.Slots.Select(x=>loadout.Fitted(x)))):"missing";
   if(ShowingWeapon&&weaponSignature==next)return weaponRoot!=null&&renderers.Count>0;
   Restore();CaptureStudio();DestroyWeapon();ShowingWeapon=true;weaponSignature=next;Yaw=0;
   if(!source){renderers.Clear();return false;}
   var excluded=new HashSet<Renderer>(source.GetComponentsInChildren<MuzzleFlash>(true).Where(x=>x.card).Select(x=>x.card));
   weaponRoot=new GameObject("Inventory weapon display"){hideFlags=HideFlags.DontSave};weaponRoot.transform.position=new Vector3(0,-10000,0);
   void Copy(Transform from,Transform parent,bool first)
   {
    var node=new GameObject(from.name){hideFlags=HideFlags.DontSave};node.transform.SetParent(parent,false);
    node.transform.localPosition=first?Vector3.zero:from.localPosition;node.transform.localRotation=first?Quaternion.identity:from.localRotation;
    node.transform.localScale=first?from.lossyScale:from.localScale;
    bool on=first||from.gameObject.activeSelf;
    if(loadout?.Modifier(from.name)!=null)on=loadout.Slots.Any(x=>loadout.Fitted(x)==from.name);
    node.SetActive(on);node.layer=previewLayer;
    var filter=from.GetComponent<MeshFilter>();var meshRenderer=from.GetComponent<MeshRenderer>();
    if(filter&&filter.sharedMesh&&meshRenderer&&!excluded.Contains(meshRenderer)&&meshRenderer.shadowCastingMode!=ShadowCastingMode.ShadowsOnly)
    {
     node.AddComponent<MeshFilter>().sharedMesh=filter.sharedMesh;
     var output=node.AddComponent<MeshRenderer>();output.sharedMaterials=meshRenderer.sharedMaterials;output.shadowCastingMode=ShadowCastingMode.Off;output.receiveShadows=false;output.enabled=false;
    }
    var skin=from.GetComponent<SkinnedMeshRenderer>();
    if(skin&&skin.sharedMesh&&!excluded.Contains(skin)&&skin.shadowCastingMode!=ShadowCastingMode.ShadowsOnly)
    {
     var mesh=new Mesh{name="Inventory weapon mesh"};skin.BakeMesh(mesh);previewMeshes.Add(mesh);node.AddComponent<MeshFilter>().sharedMesh=mesh;
     var output=node.AddComponent<MeshRenderer>();output.sharedMaterials=skin.sharedMaterials;output.shadowCastingMode=ShadowCastingMode.Off;output.receiveShadows=false;output.enabled=false;
    }
    foreach(Transform child in from)Copy(child,node.transform,false);
   }
   Copy(source.transform,weaponRoot.transform,true);
   renderers.Clear();renderers.AddRange(weaponRoot.GetComponentsInChildren<Renderer>(false));
   if(renderers.Count==0){DestroyWeapon();return false;}
   weaponBounds=renderers[0].bounds;foreach(var r in renderers)weaponBounds.Encapsulate(r.bounds);
   float length=Mathf.Max(weaponBounds.size.x,weaponBounds.size.y,weaponBounds.size.z);
   float metres=loadout!=null&&loadout.WeaponId.Contains("pistol")?.34f:.9f;
   if(length>.0001f)weaponRoot.transform.localScale=Vector3.one*(metres/length);
   weaponBounds=renderers[0].bounds;foreach(var r in renderers)weaponBounds.Encapsulate(r.bounds);
   if(Active)Frame();return true;
  }
  public void ShowCharacter()
  {
   if(!ShowingWeapon)return;Restore();DestroyWeapon();RestoreStudio();ShowingWeapon=false;weaponSignature=null;Yaw=0;
   if(Active){CollectRenderers();Frame();}
  }
  void DestroyWeapon()
  {
   if(weaponRoot){weaponRoot.SetActive(false);ReleasePreviewObject(weaponRoot);weaponRoot=null;}
   foreach(var mesh in previewMeshes)if(mesh)ReleasePreviewObject(mesh);previewMeshes.Clear();
  }

  static void ReleasePreviewObject(Object value){if(Application.isPlaying)Destroy(value);else DestroyImmediate(value);}

  void Awake()
  {
   if(previewCamera)previewCamera.enabled=false;
   SetStudio(false);
   if(player)foreach(var r in player.GetComponentsInChildren<Renderer>(true))if(r)authored[r]=r.shadowCastingMode;
  }
  void OnEnable(){RenderPipelineManager.beginCameraRendering+=Begin;RenderPipelineManager.endCameraRendering+=End;}
  void OnDisable(){RenderPipelineManager.beginCameraRendering-=Begin;RenderPipelineManager.endCameraRendering-=End;Restore();SetActive(false);}
  void OnDestroy(){DestroyWeapon();RestoreStudio();if(Texture){Texture.Release();ReleasePreviewObject(Texture);Texture=null;}}

  /// Starts or stops the preview camera. The texture is created on first use and kept for the session.
  public void SetActive(bool active)
  {
   if(!active)Restore();
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
   if(ShowingWeapon)
   {
    if(!weaponRoot)return;
    var weaponFocus=weaponBounds.center;float radius=Mathf.Max(.05f,weaponBounds.extents.magnitude);
    float aspect=Texture?Texture.width/(float)Texture.height:1;
    float half=Mathf.Atan(Mathf.Tan(fieldOfView*Mathf.Deg2Rad*.5f)*Mathf.Min(1,aspect));
    float range=radius/Mathf.Sin(half)*1.13f;
    FrameWeaponStudio(range,radius);
    var direction=Quaternion.Euler(0,Yaw,0)*new Vector3(.9f,.22f,1).normalized;
    previewCamera.transform.SetPositionAndRotation(weaponFocus+direction*range,Quaternion.LookRotation(-direction,Vector3.up));
    previewCamera.nearClipPlane=.01f;previewCamera.farClipPlane=Mathf.Max(10,range*3);previewCamera.fieldOfView=fieldOfView;return;
   }
   previewCamera.nearClipPlane=.1f;previewCamera.farClipPlane=100;
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
   if(ShowingWeapon)
   {
    if(weaponRoot)renderers.AddRange(weaponRoot.GetComponentsInChildren<Renderer>(false));
    return;
   }
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
   savedLayers.Clear();savedShadows.Clear();savedEnabled.Clear();
   foreach(var r in renderers)
   {
    savedLayers.Add(r?r.gameObject.layer:0);savedShadows.Add(r?r.shadowCastingMode:ShadowCastingMode.On);savedEnabled.Add(r&&r.enabled);
    if(!r)continue;
    r.gameObject.layer=previewLayer;
    if(ShowingWeapon)r.enabled=true;
    // First person hides the colonist by leaving only its shadow; the preview shows it whole.
    if(r.shadowCastingMode==ShadowCastingMode.ShadowsOnly)r.shadowCastingMode=ShadowCastingMode.On;
   }
   savedMuted.Clear();
   foreach(var l in muteLights){savedMuted.Add(l&&l.enabled);if(l)l.enabled=false;}
   nearbyMuted.Clear();
   var at=ShowingWeapon?weaponBounds.center:player.transform.position+Vector3.up*.9f;
   foreach(var l in sceneLights)if(l&&l.enabled&&(l.transform.position-at).sqrMagnitude<(l.range+1.2f)*(l.range+1.2f)){l.enabled=false;nearbyMuted.Add(l);}
   SetStudio(true);
   swapped=true;
  }
  void End(ScriptableRenderContext context,Camera camera){if(camera==previewCamera)Restore();}
  void Restore()
  {
   if(!swapped)return;
   for(int i=0;i<renderers.Count&&i<savedLayers.Count;i++){var r=renderers[i];if(!r)continue;r.gameObject.layer=savedLayers[i];r.shadowCastingMode=savedShadows[i];if(ShowingWeapon&&i<savedEnabled.Count)r.enabled=savedEnabled[i];}
   for(int i=0;i<muteLights.Length&&i<savedMuted.Count;i++)if(muteLights[i])muteLights[i].enabled=savedMuted[i];
   foreach(var l in nearbyMuted)if(l)l.enabled=true;
   nearbyMuted.Clear();
   SetStudio(false);
   swapped=false;
  }
  void SetStudio(bool on){foreach(var l in studioLights)if(l)l.enabled=on;}
 }
}
