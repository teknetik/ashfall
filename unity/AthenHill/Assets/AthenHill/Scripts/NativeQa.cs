using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 // Explicitly opt-in, development-player-only diagnostics. No command listener in releases.
 public class NativeQa:MonoBehaviour
 {
  string folder;GameSession session;AthenDebugBridge bridge;UIDocument document;CityAtmosphere atmosphere;
  ProfilerRecorder draws,tris,batches,setPass,mainThread,renderThread;
  readonly List<object> samples=new List<object>();bool profiling;float nextSnapshot;
#if UNITY_EDITOR || DEBUG
  float nextDevState;
#endif
  readonly FrameTiming[] timings=new FrameTiming[1];
#if UNITY_EDITOR || DEBUG
  readonly NativeVisualReview visualReview=new NativeVisualReview();
  readonly NativeAssetReview assetReview=new NativeAssetReview();
#endif
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void StartIfRequested()
  {
   if(!Debug.isDebugBuild)return;
   var args=Environment.GetCommandLineArgs();int index=Array.IndexOf(args,"--athen-qa");
   if(index<0||index+1>=args.Length)return;
   // Opt-in static capture jobs can render without desktop focus. Ordinary QA
   // and every release keep the normal focus policy; this does not inject input.
   if(Array.IndexOf(args,"--athen-qa-background")>=0)Application.runInBackground=true;
   var qa=new GameObject("Development QA").AddComponent<NativeQa>();qa.folder=Path.GetFullPath(args[index+1]);Directory.CreateDirectory(qa.folder);
  }
  void Start()
  {
   session=FindAnyObjectByType<GameSession>();bridge=FindAnyObjectByType<AthenDebugBridge>();document=FindAnyObjectByType<UIDocument>();atmosphere=FindAnyObjectByType<CityAtmosphere>();
   draws=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Draw Calls Count");tris=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Triangles Count");batches=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Batches Count");setPass=ProfilerRecorder.StartNew(ProfilerCategory.Render,"SetPass Calls Count");mainThread=ProfilerRecorder.StartNew(ProfilerCategory.Internal,"Main Thread");renderThread=ProfilerRecorder.StartNew(ProfilerCategory.Internal,"Render Thread");
   // Respect the player’s video settings during settings and performance QA.
   Write("environment.json",new{unity=Application.unityVersion,os=SystemInfo.operatingSystem,gpu=SystemInfo.graphicsDeviceName,api=SystemInfo.graphicsDeviceType.ToString(),driver=SystemInfo.graphicsDeviceVersion,cpu=SystemInfo.processorType,graphicsMemoryMB=SystemInfo.graphicsMemorySize>0?(int?)SystemInfo.graphicsMemorySize:null,systemMemoryMB=SystemInfo.systemMemorySize>0?(int?)SystemInfo.systemMemorySize:null,quality=QualitySettings.names[QualitySettings.GetQualityLevel()],width=Screen.width,height=Screen.height,vsync=QualitySettings.vSyncCount,targetFrameRate=Application.targetFrameRate,drawCounter=draws.Valid,triangleCounter=tris.Valid,mainThreadCounter=mainThread.Valid,renderThreadCounter=renderThread.Valid,actorCount=FindObjectsByType<ActorAnimation>().Length,runInBackground=Application.runInBackground,isBatchMode=Application.isBatchMode});
  }
  void Write(string name,object value){var path=Path.Combine(folder,name);File.WriteAllText(path+".tmp",JsonConvert.SerializeObject(value,Formatting.Indented));if(File.Exists(path))File.Replace(path+".tmp",path,null);else File.Move(path+".tmp",path);}
  void Update()
  {
#if UNITY_EDITOR || DEBUG
   if(visualReview.HudHidden&&session.State!=CityState.Dialogue)visualReview.SetHudHidden(document,session,false);
   assetReview.Tick();
#endif
   string path=Path.Combine(folder,"command.json");
   if(File.Exists(path))
   {
    string commandId=null;bool commandFailed=false;
    try
    {
     var j=JObject.Parse(File.ReadAllText(path));File.Delete(path);
     commandId=ReadCommandId(j);
     if(commandId==null){Write("ack.json",new{id=(string)null,success=false,error=new{code="bad_id",message="Command id must be 1–64 ASCII letters, digits, _ or -."}});return;}
     switch((string)j["action"])
     {
      case "memorySnapshot":Write("memory.json",MemorySnapshot());break;
      case "goto":bridge.Goto((string)j["landmark"]);break;
      case "view":
#if UNITY_EDITOR || DEBUG
       assetReview.Cancel();
#endif
       bridge.View((string)j["camera"]);break;
      case "reset":
#if UNITY_EDITOR || DEBUG
       assetReview.Cancel();
#endif
       bridge.ResetPlayer();break;
      case "cameraYaw":bridge.follow.yaw=(float)j["yaw"];break;
      case "cameraPitch":bridge.follow.pitch=(float)j["pitch"];break;
      case "cameraBoom":bridge.follow.boom=(float)j["boom"];break;
      case "capture":ScreenCapture.CaptureScreenshot(Path.Combine(folder,Path.GetFileName((string)j["name"])+".png"));break;
      case "profileStart":samples.Clear();profiling=true;break;
      case "profileStop":profiling=false;Write("profile.json",samples);break;
      case "uiSnapshot":UiSnapshot();break;
      case "settingsSnapshot":Write("settings.json",new{sound=session.Settings.Sound,video=session.Settings.Video,draft=session.Settings.Draft,previewing=session.Settings.Previewing,remaining=session.Settings.SecondsRemaining,renderScale=session.Settings.Pipeline.renderScale,msaa=session.Settings.Pipeline.msaaSampleCount,shadowDistance=session.Settings.Pipeline.shadowDistance,shadowResolution=session.Settings.Pipeline.mainLightShadowmapResolution,shadowCascades=session.Settings.Pipeline.shadowCascadeCount,cascade4Split=new[]{session.Settings.Pipeline.cascade4Split.x,session.Settings.Pipeline.cascade4Split.y,session.Settings.Pipeline.cascade4Split.z},textureLimit=QualitySettings.globalTextureMipmapLimit,vSync=QualitySettings.vSyncCount,frameLimit=Application.targetFrameRate,postProcessing=FindAnyObjectByType<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>().renderPostProcessing,track=FindAnyObjectByType<CityAudio>().CurrentTrack,transitions=FindAnyObjectByType<CityAudio>().MusicTransitions,timeScale=Time.timeScale});break;
      case "actorSnapshot":Write("actors.json",ActorDiagnostics.Snapshot());break;
      case "motionStart":ActorMotionTrace.Begin(session.player);break;
      case "motionStop":Write("motion.json",ActorMotionTrace.End());break;
#if UNITY_EDITOR || DEBUG
      case "reviewHud":visualReview.SetHudHidden(document,session,(bool)j["hidden"]);Write("visual-review-state.json",visualReview.Snapshot());break;
      case "reviewTree":visualReview.Tree(session,j);Write("visual-review-state.json",visualReview.Snapshot());break;
      case "reviewTreeShadow":visualReview.TreeShadow(j);Write("visual-review-state.json",visualReview.Snapshot());break;
      case "reviewReset":assetReview.Cancel();bridge.View("follow");visualReview.Restore();Write("visual-review-state.json",visualReview.Snapshot());break;
      case "reviewAssetPass":assetReview.Begin(bridge,j);Write("asset-review-state.json",assetReview.Snapshot());break;
      case "reviewAssetState":Write("asset-review-state.json",assetReview.Snapshot());break;
      case "timeSet":NativeTimeDiagnostics.Clock().SetHour((float)j["hour"]);break;
      case "timePause":NativeTimeDiagnostics.Clock().Paused=(bool)j["paused"];break;
      case "timeSpeed":NativeTimeDiagnostics.Clock().SetSpeed((float)j["speed"]);break;
      case "timeReset":NativeTimeDiagnostics.Clock().ResetToAuthoredDefault();break;
      case "timeState":Write("time-state.json",NativeTimeDiagnostics.Snapshot());break;
#endif
      case "resize":Screen.SetResolution((int)j["width"],(int)j["height"],FullScreenMode.Windowed);break;
      case "quit":Application.Quit();break;
      default:
#if UNITY_EDITOR || DEBUG
       if(((string)j["action"])?.StartsWith("dev.",StringComparison.Ordinal)==true)
       {
        var result=DevBridgeCommands.Execute(j,session,FindAnyObjectByType<BermsTutorial>(),FindAnyObjectByType<CityTimeOfDay>());
        if(!result.success){Write("ack.json",new{id=commandId,success=false,error=new{code=result.code,message=result.message}});commandFailed=true;WriteDevState();break;}
        WriteDevState();break;
       }
#endif
       throw new ArgumentException("Unknown QA operation");
     }
     if(!commandFailed)Write("ack.json",new{id=commandId,success=true});
    }
    catch(Exception e){if(File.Exists(path))File.Delete(path);Write("ack.json",new{id=commandId,success=false,error=new{code="command_error",message=e.Message}});Write("qa-error.json",new{id=commandId,error=e.ToString()});Debug.LogException(e);}
   }
   if(Time.unscaledTime>=nextSnapshot){nextSnapshot=Time.unscaledTime+.1f;Snapshot();}
#if UNITY_EDITOR || DEBUG
   if(Time.unscaledTime>=nextDevState){nextDevState=Time.unscaledTime+.5f;WriteDevState();}
#endif
  }
  static string ReadCommandId(JObject j)
  {
#if UNITY_EDITOR || DEBUG
   return DevBridgeCommands.ReadId(j);
#else
   var t=j?["id"];var id=t?.Type==JTokenType.String?(string)t:null;
   return !string.IsNullOrEmpty(id)&&id.Length<=64&&id.All(c=>c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-')?id:null;
#endif
  }
#if UNITY_EDITOR || DEBUG
  void WriteDevState(){Write("dev-state.json",DevBridgeCommands.State(session));}
#endif
  static object MemorySnapshot()
  {
   // Unity counters are separate from OS process RSS and driver VRAM residency.
   // A zero in this nonempty scene is reported as unavailable, not zero cost.
   long allocated=UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong();
   long reserved=UnityEngine.Profiling.Profiler.GetTotalReservedMemoryLong();
   ulong current=Texture.currentTextureMemory,desired=Texture.desiredTextureMemory,total=Texture.totalTextureMemory;
   return new{utc=DateTime.UtcNow.ToString("O"),frame=Time.frameCount,
    unityAllocatedBytes=allocated>0?(long?)allocated:null,unityReservedBytes=reserved>0?(long?)reserved:null,
    textureCurrentBytes=current>0?(ulong?)current:null,textureDesiredBytes=desired>0?(ulong?)desired:null,textureFullResolutionBytes=total>0?(ulong?)total:null,
    streamingMipmapsActive=QualitySettings.streamingMipmapsActive,
    scope="Unity allocator and texture counters only. Full-resolution texture memory is theoretical Texture2D/cubemap cost, not total GPU residency. Compare OS RSS and driver VRAM separately; null means unavailable."};
  }
  void LateUpdate()
  {
   FrameTimingManager.CaptureFrameTimings();
   if(!profiling)return;
   uint count=FrameTimingManager.GetLatestTimings(1,timings);
   samples.Add(new{dt=Time.unscaledDeltaTime,draws=draws.Valid?draws.LastValue:-1,tris=tris.Valid?tris.LastValue:-1,batches=batches.Valid?batches.LastValue:-1,setPass=setPass.Valid?setPass.LastValue:-1,mainMs=mainThread.Valid?mainThread.LastValue/1e6:-1,renderMs=renderThread.Valid?renderThread.LastValue/1e6:-1,cpuMs=count>0?timings[0].cpuFrameTime:-1,gpuMs=count>0?timings[0].gpuFrameTime:-1,state=session.State.ToString(),speed=session.player.Speed});
  }
  void Snapshot()
  {
   var p=session.player;var sound=FindAnyObjectByType<CityAudio>();var combat=FindAnyObjectByType<PlayerCombat>();var tutorial=FindAnyObjectByType<BermsTutorial>();
   var crafting=session.GetComponent<CraftingSession>();var model=crafting?crafting.Model:null;var orders=session.GetComponent<FieldOrders>();
   Write("crafting.json",new{knownRecipes=model?.KnownRecipes.ToArray(),gripSlot=model?.Loadout.Fitted("grip"),slots=model?.Loadout.FittedMods.ToDictionary(x=>x.Key,x=>x.Value),stats=combat?(object)combat.Stats:null,recoilBase=model?.BaseRecoil,recoilFinal=model?.RecoilStat,lastKickDegrees=combat?combat.LastKickDegrees:0,crafts=model?.Crafts,lootEvents=crafting?crafting.LootEvents:0,lastLoot=crafting?crafting.LastLoot:null,tutorialStep=orders?orders.LegacyGripStep:null,fieldOrder=orders&&orders.Ready?orders.Progress.Index:-1,orderStage=orders?orders.Stage.ToString():null,objective=orders?orders.Objective:null,fabricatorOpen=session.State==CityState.Fabricator});
   var mouse=UnityEngine.InputSystem.Mouse.current;
   if(mouse!=null&&document.rootVisualElement.panel!=null)
   {
    var screen=mouse.position.ReadValue();screen.y=Screen.height-screen.y;
    var panelPoint=RuntimePanelUtils.ScreenToPanel(document.rootVisualElement.panel,screen);
    var picked=document.rootVisualElement.panel.Pick(panelPoint);
    var slot=document.rootVisualElement.Q<Button>("slot1");
    Write("pointer.json",new{screenX=screen.x,screenY=screen.y,panelX=panelPoint.x,panelY=panelPoint.y,picked=picked?.name,pickedType=picked?.GetType().Name,overUi=session.input.PointerOverUi?.Invoke(),slotBounds=new[]{slot.worldBound.x,slot.worldBound.y,slot.worldBound.width,slot.worldBound.height}});
   }
   Write("snapshot.json",new{atmosphere=atmosphere?new{windTime=Shader.GetGlobalFloat("_AthenAtmosphereTime"),dustParticles=atmosphere.driftingDust?atmosphere.driftingDust.particleCount:0,dustPlaying=atmosphere.driftingDust&&atmosphere.driftingDust.isPlaying}:null,frame=Time.frameCount,width=Screen.width,height=Screen.height,session=new{state=session.State.ToString(),session.visitedHill,spoken=session.Spoken.ToArray(),session.boughtFlask,session.soldScrap,session.linked,session.muted,session.reducedMotion,session.notice,radio=session.RadioLine.Text,radioSpeaker=session.RadioLine.Speaker,radioQueued=session.RadioLine.Pending,session.selectedDestination,gridProgress=session.GridProgress,credits=session.Shop?.Credits,quantities=session.catalog.items.ToDictionary(i=>i.id,i=>session.Shop?.Quantity(i.id)),focused=(document.rootVisualElement.focusController.focusedElement as VisualElement)?.name},player=new{position=new[]{p.transform.position.x,p.transform.position.y,p.transform.position.z},grounded=p.Grounded,speed=p.Speed},footsteps=p.GetComponent<FootstepAudio>()?new{p.GetComponent<FootstepAudio>().StepCount,p.GetComponent<FootstepAudio>().LandCount,surface=p.GetComponent<FootstepAudio>().LastSurface.ToString(),clip=p.GetComponent<FootstepAudio>().LastClip,under=p.GetComponent<FootstepAudio>().Surface().ToString()}:null,guards=FindObjectsByType<ActorLookAt>(FindObjectsSortMode.None).Select(l=>new{name=l.actor?l.actor.name:l.name,l.Focused,clip=l.actor?l.actor.CurrentClip:null}).ToArray(),audio=sound?new{sound.StepCount,sound.ClickCount,sound.TradeCount,sound.UnavailableCount,sound.TravelOpenCount,sound.TravelLinkCount,paused=AudioListener.pause,volume=AudioListener.volume,sources=FindObjectsByType<AudioSource>().OrderBy(a=>a.name).Select(a=>new{name=a.name,clip=a.clip?a.clip.name:null,playing=a.isPlaying,time=a.clip?a.time:0,a.volume,a.spatialBlend,a.loop,group=a.outputAudioMixerGroup?a.outputAudioMixerGroup.name:null}).ToArray()}:null,camera=new{yaw=bridge.follow.yaw,pitch=bridge.follow.pitch,boom=bridge.follow.boom,distance=bridge.follow.Distance,firstPerson=bridge.follow.FirstPerson,playerHidden=bridge.follow.PlayerHidden,position=new[]{bridge.follow.transform.position.x,bridge.follow.transform.position.y,bridge.follow.transform.position.z},overlaps=Physics.OverlapSphere(bridge.follow.transform.position,.20f,bridge.follow.worldMask,QueryTriggerInteraction.Ignore).Select(x=>x.name).ToArray()},interaction=new{prompt=session.Prompt,npc=session.ActiveNpc?session.ActiveNpc.definition.displayName:null,node=session.State==CityState.Dialogue?session.dialogueNode:null,choices=session.State==CityState.Dialogue?session.Choices.Select(c=>c.label).ToArray():null,station=session.ActiveStation?session.ActiveStation.title:null,shop=session.State==CityState.Shop?session.ActiveShop.title:null,flags=session.Flags.ToArray()},combat=combat?new{combat.hasPistol,combat.Armed,combat.Aiming,combat.Nano,combat.ShotsFired,activeSlot=combat.ActiveSlot,weaponId=combat.Loadout?.WeaponId,hasRifle=combat.HasRifle,rifleShown=combat.heldRifle&&combat.heldRifle.activeInHierarchy,pistolShown=combat.heldPistol&&combat.heldPistol.activeInHierarchy,wornArmour=combat.GetComponent<PlayerArmourVisuals>()?combat.GetComponent<PlayerArmourVisuals>().Worn():new string[0],downs=combat.Downs,viewModelVisible=combat.viewModel&&combat.viewModel.Visible,viewModelAim=combat.viewModel?combat.viewModel.AimBlend:0,viewModelFlashes=combat.viewModel&&combat.viewModel.flash?combat.viewModel.flash.Flashes:0,thirdPersonFlashes=combat.thirdPersonFlash?combat.thirdPersonFlash.Flashes:0,aimPoseWeight=combat.GetComponent<PlayerWeaponPose>()?combat.GetComponent<PlayerWeaponPose>().Weight:0,health=combat.Health.Current,step=tutorial?tutorial.Step.ToString():null,targets=tutorial?tutorial.TargetsDown:0,objective=tutorial?tutorial.Objective:null,lockerEnabled=tutorial&&tutorial.locker&&tutorial.locker.enabled,enemies=FeralDroid.Active.Where(d=>d).Select(d=>new{d.displayName,state=d.State.ToString(),alive=d.Health.Alive,health=d.Health.Current,bolts=d.BoltsFired,position=new[]{d.transform.position.x,d.transform.position.y,d.transform.position.z}}).ToArray()}:null,fps=bridge.fps,draws=draws.Valid?draws.LastValue:-1,triangles=tris.Valid?tris.LastValue:-1});
  }
  void UiSnapshot()
  {
   var elements=new List<object>();
   void Visit(VisualElement e,bool ancestorsVisible)
   {
    bool visible=ancestorsVisible&&e.resolvedStyle.display!=DisplayStyle.None&&e.resolvedStyle.visibility==Visibility.Visible;
    var b=e.worldBound;
    if(!string.IsNullOrEmpty(e.name)||e is TextElement)elements.Add(new{name=e.name,type=e.GetType().Name,visible,enabled=e.enabledInHierarchy,e.focusable,e.tabIndex,e.delegatesFocus,text=(e as TextElement)?.text,value=(e as DropdownField)?.value,choices=(e as DropdownField)?.choices,bounds=new[]{b.x,b.y,b.width,b.height},fontSize=e.resolvedStyle.fontSize,classes=e.GetClasses().ToArray(),hasBackground=e.resolvedStyle.backgroundImage.texture!=null});
    foreach(var child in e.hierarchy.Children())Visit(child,visible);
   }
   Visit(document.rootVisualElement.panel.visualTree,true);
   Write("ui-layout.json",new{width=Screen.width,height=Screen.height,state=session.State.ToString(),focused=(document.rootVisualElement.focusController?.focusedElement as VisualElement)?.name,modalTabStops=UiNavigation.TabStops(document.rootVisualElement.Q("modal")).Select(e=>e.name).ToArray(),elements});
  }
  void OnDestroy(){
#if UNITY_EDITOR || DEBUG
   visualReview.Restore();
#endif
   draws.Dispose();tris.Dispose();batches.Dispose();setPass.Dispose();mainThread.Dispose();renderThread.Dispose();}
#if UNITY_EDITOR || DEBUG
    public static class NativeTimeDiagnostics
    {
        public static CityTimeOfDay Clock()
        {
            if (!Application.isEditor && !Debug.isDebugBuild) throw new InvalidOperationException("Time diagnostics require a development player.");
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>();
            if (!clock || !clock.isActiveAndEnabled) throw new InvalidOperationException("No active authored day/night controller.");
            return clock;
        }
        public static object Snapshot()
        {
            var clock = Clock(); var reflections = clock.reflections;
            var menu = UnityEngine.Object.FindAnyObjectByType<DeveloperTimeMenu>();
            var sunDirection = -clock.keyLight.transform.forward;
            return new
            {
                hour = clock.Hour, paused = clock.Paused, speed = clock.Speed, clock.PreviewWhilePaused, clock.ReducedMotionSpeedLimited,
                defaultHour = clock.profile.defaultHour, cycleMinutes = clock.profile.realMinutesPerCycle,
                lampStrength = clock.LampStrength, sunVisibility = clock.SunVisibility, menuOpen = menu && menu.IsOpen,
                sunIntensity = clock.keyLight.intensity, sunDirection = new[] { sunDirection.x, sunDirection.y, sunDirection.z },
                skyShader = RenderSettings.skybox ? RenderSettings.skybox.shader.name : "",
                skySunVisibility = RenderSettings.skybox && RenderSettings.skybox.HasProperty("_SunVisibility") ? RenderSettings.skybox.GetFloat("_SunVisibility") : -1,
                postExposure = clock.CurrentFrame.postExposure,
                ambient = new {
                    mode = RenderSettings.ambientMode.ToString(), intensity = RenderSettings.ambientIntensity,
                    sky = new[] { RenderSettings.ambientSkyColor.r, RenderSettings.ambientSkyColor.g, RenderSettings.ambientSkyColor.b },
                    equator = new[] { RenderSettings.ambientEquatorColor.r, RenderSettings.ambientEquatorColor.g, RenderSettings.ambientEquatorColor.b },
                    ground = new[] { RenderSettings.ambientGroundColor.r, RenderSettings.ambientGroundColor.g, RenderSettings.ambientGroundColor.b }
                },
                skyFill = clock.skyFill ? new {
                    clock.skyFill.enabled, clock.skyFill.intensity,
                    color = new[] { clock.skyFill.color.r, clock.skyFill.color.g, clock.skyFill.color.b },
                    shadows = clock.skyFill.shadows.ToString()
                } : null,
                realtimeReflectionsEnabled = QualitySettings.realtimeReflectionProbes,
                reflections = reflections ? new { pending = reflections.CapturePending, completed = reflections.CompletedCaptures, failed = reflections.FailedCaptures, status = reflections.Status,
                    lastCaptureLatencyMilliseconds = reflections.LastCaptureLatencyMilliseconds,
                    probes = reflections.probes.Where(p => p.probe).Select(p => new { p.probe.name, mode = p.probe.mode.ToString(), p.probe.intensity, p.probe.resolution,
                        texture = p.probe.texture ? p.probe.texture.name : "",
                        texturePresent = (bool)p.probe.texture,
                        textureWidth = p.probe.texture ? p.probe.texture.width : 0,
                        realtimeTextureCreated = p.probe.realtimeTexture && p.probe.realtimeTexture.IsCreated(),
                        slicing = p.probe.timeSlicingMode.ToString() }).ToArray() } : null,
                circuits = UnityEngine.Object.FindObjectsByType<CityLightCircuit>().Select(c => new { c.name, strength = c.CurrentStrength, activeLights = c.ActiveLights, shadowLights = c.ActiveShadowLights,
                    fixtures = c.practicalLights.Where(l => l).Select(l => new { l.name, l.enabled, l.intensity, l.range, shadows = l.shadows.ToString() }).ToArray() }).ToArray()
            };
        }
    }
#endif
 }
}
