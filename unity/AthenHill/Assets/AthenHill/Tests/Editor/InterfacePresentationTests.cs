using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// Interface package (19 Nov 2026): which dialogue layout applies, the adaptive HUD's rules and timers, the interface
 /// settings round trip and the Settings rows, and the UXML names the HUD binds.
 public class InterfacePresentationTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  string prefix;bool cameraWas;
  readonly List<GameObject> objects=new List<GameObject>();
  [SetUp]public void SetUp(){prefix="AthenHill.Tests.Interface."+Guid.NewGuid().ToString("N")+".";cameraWas=ConversationCamera.Enabled;}
  [TearDown]public void TearDown()
  {
   foreach(var o in objects)UnityEngine.Object.DestroyImmediate(o);objects.Clear();
   PlayerPrefs.DeleteKey(prefix+"Interface");PlayerPrefs.Save();
   ConversationCamera.Enabled=cameraWas;
  }

  // ---- Dialogue layout
  static DialogueLayout Choose(bool open=true,bool cameraOn=true,bool fixedView=false,bool firstPerson=false,bool engaged=false,bool framing=false,float seconds=0)
   =>DialogueLayoutRule.Choose(open,cameraOn,fixedView,firstPerson,engaged,framing,seconds);

  [Test]public void NoDialogueMeansNoLayout()=>Assert.That(Choose(open:false,engaged:true,framing:true),Is.EqualTo(DialogueLayout.None));
  [Test]public void CameraOffOrReviewCameraKeepsTheCentredWindow()
  {
   Assert.That(Choose(cameraOn:false,engaged:true,framing:true),Is.EqualTo(DialogueLayout.Centred));
   Assert.That(Choose(fixedView:true,engaged:true,framing:true),Is.EqualTo(DialogueLayout.Centred));
  }
  [Test]public void EngagedCameraDecides()
  {
   Assert.That(Choose(engaged:true,framing:true,seconds:5),Is.EqualTo(DialogueLayout.LowerThird),"shoulder or eye-line shot");
   Assert.That(Choose(engaged:true,framing:false),Is.EqualTo(DialogueLayout.Centred),"first person: depth of field only");
   // Once engaged, the follow camera's current zoom no longer matters: the camera fixed first person at the start.
   Assert.That(Choose(engaged:true,framing:true,firstPerson:true),Is.EqualTo(DialogueLayout.LowerThird));
  }
  [Test]public void BeforeTheCameraEngagesThePredictionHoldsOnlyForTheGrace()
  {
   Assert.That(Choose(seconds:0),Is.EqualTo(DialogueLayout.LowerThird),"third person, first frame");
   Assert.That(Choose(seconds:DialogueLayoutRule.Grace),Is.EqualTo(DialogueLayout.LowerThird));
   Assert.That(Choose(firstPerson:true,seconds:0),Is.EqualTo(DialogueLayout.Centred),"first person never frames");
   Assert.That(Choose(seconds:DialogueLayoutRule.Grace+.01f),Is.EqualTo(DialogueLayout.Centred),"camera never engaged: not framing");
  }
  [Test]public void NamePlateDoesNotRepeatTheRole()
  {
   Assert.That(DialogueLayoutRule.NamePlateSubtitle("Basic General","Basic General"),Is.EqualTo("Basic General"),"opening node titled with the role");
   Assert.That(DialogueLayoutRule.NamePlateSubtitle("Salvage dealer","Salvage"),Is.EqualTo("Salvage dealer · Salvage"));
   Assert.That(DialogueLayoutRule.NamePlateSubtitle("Local fixer","local fixer "),Is.EqualTo("Local fixer"));
   Assert.That(DialogueLayoutRule.NamePlateSubtitle("West Gate watch","The arms locker"),Is.EqualTo("West Gate watch · The arms locker"));
   Assert.That(DialogueLayoutRule.NamePlateSubtitle("","Housing roll"),Is.EqualTo("Housing roll"));
   Assert.That(DialogueLayoutRule.NamePlateSubtitle("Hill regular",null),Is.EqualTo("Hill regular"));
  }
  [Test]public void LayoutIdsForQa()
  {
   Assert.That(DialogueLayoutRule.Id(DialogueLayout.LowerThird),Is.EqualTo("lowerThird"));
   Assert.That(DialogueLayoutRule.Id(DialogueLayout.Centred),Is.EqualTo("centred"));
   Assert.That(DialogueLayoutRule.Id(DialogueLayout.None),Is.EqualTo("none"));
  }

  // ---- Adaptive HUD
  static HudFrame Frame(InterfaceMode mode=InterfaceMode.Adaptive,bool lowerThird=false,bool window=false,bool combat=false,bool alt=false,bool prompt=false,bool vitalsActive=false,bool reduced=false)
   =>new HudFrame{mode=mode,lowerThird=lowerThird,windowOpen=window,combat=combat,altHeld=alt,prompt=prompt,vitalsActive=vitalsActive,reducedMotion=reduced};
  static AdaptiveHudModel Model(){var m=new AdaptiveHudModel{quietSeconds=5,fadeInSeconds=.2f,fadeOutSeconds=.5f};m.WakeAll(0);return m;}
  /// Steps the model from t0 to t1 in 50 ms frames; returns the time reached.
  static float Run(AdaptiveHudModel m,HudFrame f,float t0,float t1){float t=t0;while(t<t1-1e-5f){t=Mathf.Min(t1,t+.05f);m.Step(f,t,.05f);}return t;}

  [Test]public void FullModeKeepsEveryPanelUp()
  {
   var m=Model();Run(m,Frame(InterfaceMode.Full),0,30);
   foreach(var p in AdaptiveHudModel.Panels)Assert.That(m.Alpha(p),Is.EqualTo(1),p.ToString());
  }
  [Test]public void LowerThirdHidesLogHintsAndHotbarInEitherModeAndRestoresThem()
  {
   foreach(var mode in new[]{InterfaceMode.Full,InterfaceMode.Adaptive})
   {
    var m=Model();float t=Run(m,Frame(mode,lowerThird:true,window:true),0,1);
    // native QA 19 Nov 2026: identity, Field Notes and the compass give way too
    foreach(var p in AdaptiveHudModel.Panels)Assert.That(m.Hidden(p),p+" "+mode);
    Run(m,Frame(mode),t,t+.5f);
    Assert.That(m.Alpha(HudPanel.Hotbar),Is.EqualTo(1),"the hotbar is back after the conversation");
    if(mode==InterfaceMode.Full)foreach(var p in AdaptiveHudModel.Panels)Assert.That(m.Alpha(p),Is.EqualTo(1),p.ToString());
   }
  }
  [Test]public void QuietPanelsFadeAfterTheQuietTimeAndTheHotbarStays()
  {
   var m=Model();Run(m,Frame(),0,4.9f);
   foreach(var p in AdaptiveHudModel.Panels)Assert.That(m.Alpha(p),Is.EqualTo(1),"still within the quiet time: "+p);
   Run(m,Frame(),4.9f,5.25f);
   Assert.That(m.Alpha(HudPanel.Log),Is.GreaterThan(0).And.LessThan(1),"part way through the fade");
   Run(m,Frame(),5.25f,6);
   foreach(var p in new[]{HudPanel.Identity,HudPanel.FieldNotes,HudPanel.Log,HudPanel.KeyHints})Assert.That(m.Hidden(p),p.ToString());
   Assert.That(m.Alpha(HudPanel.Hotbar),Is.EqualTo(1));
  }
  [Test]public void AWakeBringsBackOnlyThatPanelForTheQuietTime()
  {
   var m=Model();float t=Run(m,Frame(),0,8);
   m.Wake(HudPanel.Log,t);t=Run(m,Frame(),t,t+.2f);
   Assert.That(m.Alpha(HudPanel.Log),Is.EqualTo(1).Within(1e-4f),"fades in over 0.2 s");
   Assert.That(m.Hidden(HudPanel.Identity));
   t=Run(m,Frame(),t,t+4.5f);Assert.That(m.Alpha(HudPanel.Log),Is.EqualTo(1));
   Run(m,Frame(),t,t+1.5f);Assert.That(m.Hidden(HudPanel.Log));
  }
  [Test]public void WindowsCombatAndAltHoldEveryPanelAndRestartTheQuietTime()
  {
   foreach(var hold in new[]{Frame(window:true),Frame(combat:true),Frame(alt:true)})
   {
    var m=Model();float t=Run(m,Frame(),0,8);
    t=Run(m,hold,t,t+20);
    foreach(var p in AdaptiveHudModel.Panels)Assert.That(m.Alpha(p),Is.EqualTo(1),p.ToString());
    t=Run(m,Frame(),t,t+4.5f);
    Assert.That(m.Alpha(HudPanel.Identity),Is.EqualTo(1),"the quiet time counts from the end of the hold");
    Run(m,Frame(),t,t+1.5f);Assert.That(m.Hidden(HudPanel.Identity));
   }
  }
  [Test]public void APromptHoldsTheKeyHintsOnly()
  {
   var m=Model();float t=Run(m,Frame(),0,8);
   Run(m,Frame(prompt:true),t,t+10);
   Assert.That(m.Alpha(HudPanel.KeyHints),Is.EqualTo(1));Assert.That(m.Hidden(HudPanel.FieldNotes));
  }
  [Test]public void VitalsActiveHoldsIdentityOnlyAndRestartsQuietTime()
  {
   var m=Model();float t=Run(m,Frame(),0,8);
   t=Run(m,Frame(vitalsActive:true),t,t+4);
   Assert.That(m.Alpha(HudPanel.Identity),Is.EqualTo(1),"low vitality / overclock / overcharge keeps Identity up");
   Assert.That(m.Hidden(HudPanel.FieldNotes));Assert.That(m.Hidden(HudPanel.Log));
   t=Run(m,Frame(),t,t+4.5f);
   Assert.That(m.Alpha(HudPanel.Identity),Is.EqualTo(1),"quiet timer starts after vitals settle");
   Run(m,Frame(),t,t+1.5f);
   Assert.That(m.Hidden(HudPanel.Identity));
   // Lower-third dialogue still takes precedence over vitalsActive.
   Run(m,Frame(lowerThird:true,vitalsActive:true),t+2,t+3);
   Assert.That(m.Hidden(HudPanel.Identity));
  }
  [Test]public void IsDisplayedInRejectsDetachedAndHiddenAncestors()
  {
   var parent=new VisualElement();var child=new Button();parent.Add(child);
   Assert.That(CityHud.IsDisplayedIn(child),Is.False,"detached elements have no panel");
   Assert.That(CityHud.IsDisplayedIn(null),Is.False);
  }
  [Test]public void ReducedMotionCutsInsteadOfFading()
  {
   var m=Model();m.Step(Frame(reduced:true),5.01f,.016f);
   Assert.That(m.Hidden(HudPanel.Identity),"cut out on the first frame past the quiet time");
   m.Wake(HudPanel.Identity,6);m.Step(Frame(reduced:true),6,.016f);
   Assert.That(m.Alpha(HudPanel.Identity),Is.EqualTo(1),"cut back in");
  }
  [Test]public void PanelIdsForQa()=>Assert.That(AdaptiveHudModel.Panels.Select(AdaptiveHudModel.Id),Is.EqualTo(new[]{"identity","fieldNotes","log","keyHints","hotbar","compass"}));

  // ---- Settings
  GameSettings Settings()
  {
   var go=new GameObject("interface settings test");go.SetActive(false);objects.Add(go);
   var s=go.AddComponent<GameSettings>();
   typeof(GameSettings).GetField("prefix",Any).SetValue(s,prefix);
   return s;
  }
  static InterfaceOptions ReadInterface(GameSettings s)=>(InterfaceOptions)typeof(GameSettings).GetMethod("Read",Any).MakeGenericMethod(typeof(InterfaceOptions)).Invoke(s,new object[]{"Interface",new InterfaceOptions()});

  [Test]public void InterfaceDefaultsAreTodaysBehaviour()
  {
   var o=new InterfaceOptions();
   Assert.That(o.conversationCamera,Is.True);Assert.That(o.Mode,Is.EqualTo(InterfaceMode.Adaptive));
   var old=JsonUtility.FromJson<InterfaceOptions>("{}");
   Assert.That(old.conversationCamera,Is.True,"a save without the field keeps the camera on");Assert.That(old.Mode,Is.EqualTo(InterfaceMode.Adaptive));
   Assert.That(JsonUtility.FromJson<InterfaceOptions>("{\"mode\":7}").Mode,Is.EqualTo(InterfaceMode.Adaptive),"an unknown mode reads as Adaptive");
  }
  [Test]public void InterfaceSettingsRoundTripAndDriveTheConversationCamera()
  {
   var s=Settings();int changed=0;s.Changed+=()=>changed++;
   s.Interface.conversationCamera=false;s.Interface.mode=(int)InterfaceMode.Full;s.SaveInterface();
   Assert.That(changed,Is.EqualTo(1));
   Assert.That(ConversationCamera.Enabled,Is.False);
   var read=ReadInterface(Settings());
   Assert.That(read.conversationCamera,Is.False);Assert.That(read.Mode,Is.EqualTo(InterfaceMode.Full));
   s.ResetInterface();
   Assert.That(ConversationCamera.Enabled,Is.True);
   read=ReadInterface(Settings());
   Assert.That(read.conversationCamera,Is.True);Assert.That(read.Mode,Is.EqualTo(InterfaceMode.Adaptive));
  }
  [Test]public void SettingsPanelShowsTheNewRowsWithTheirValues()
  {
   var s=Settings();
   typeof(GameSettings).GetProperty("Sound",Any).SetValue(s,new SoundOptions());
   typeof(GameSettings).GetProperty("Video",Any).SetValue(s,new VideoOptions());
   typeof(GameSettings).GetProperty("Draft",Any).SetValue(s,new VideoOptions());
   var go=new GameObject("interface session test");go.SetActive(false);objects.Add(go);
   var session=go.AddComponent<GameSession>();
   s.Interface.mode=(int)InterfaceMode.Adaptive;s.Interface.conversationCamera=false;
   var root=new VisualElement();var panel=new SettingsPanel(root,s,session);
   try
   {
    var camera=root.Q<Toggle>("conversation-camera");var mode=root.Q<DropdownField>("interface-mode");var captions=root.Q<Toggle>("bark-captions");
    Assert.That(camera,Is.Not.Null);Assert.That(mode,Is.Not.Null);Assert.That(captions,Is.Not.Null);
    Assert.That(camera.value,Is.False);Assert.That(mode.choices,Is.EqualTo(new[]{"Full","Adaptive"}));Assert.That(mode.value,Is.EqualTo("Adaptive"));
    Assert.That(captions.value,Is.EqualTo(BarkDirector.CaptionsEnabled));
    Assert.That(root.Q("controls-page").Contains(camera)&&root.Q("controls-page").Contains(mode),"camera and interface sit on the Controls tab");
    Assert.That(root.Q("sound-page").Contains(captions),"captions sit with Reduced motion under Accessibility");
    Assert.That(root.Q<Toggle>("hit-markers"),Is.Not.Null,"the combat feedback rows are kept");
   }
   finally{panel.Dispose();}
  }

  // ---- UXML and window hold
  [Test]public void UxmlKeepsTheNamesTheHudBinds()
  {
   var root=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
   foreach(var n in new[]{"shade","modal","identity","objective-box","top-actions","chat","key-hints","quickbar","dialogue-panel","dialogue-line","dialogue-responses","radio","notice"})Assert.That(root.Q(n),Is.Not.Null,n);
   foreach(var n in new[]{"objective-title","objective","progress","credits","dialogue-text","modal-title","modal-subtitle"})Assert.That(root.Q<Label>(n),Is.Not.Null,n);
   for(int i=0;i<GameSession.MaxChoices;i++)Assert.That(root.Q("dialogue-responses").Q<Button>("choice"+i),Is.Not.Null,"choice"+i);
   Assert.That(root.Q("dialogue-line").Contains(root.Q("dialogue-text")));
  }
  [Test]public void HeldWindowSitsAtItsAuthoredPlaceUntilReleased()
  {
   var root=new VisualElement();var window=new VisualElement();root.Add(window);
   string id="interface-test-"+Guid.NewGuid().ToString("N");
   var layout=new HudWindowLayout(root);
   try
   {
    layout.Add(window,id);
    window.style.translate=new Translate(new Length(40),new Length(-30),0);
    layout.Hold(window,true);
    Assert.That(layout.Held(window));
    Assert.That(window.style.translate.value.x.value,Is.EqualTo(0));Assert.That(window.style.translate.value.y.value,Is.EqualTo(0));
    layout.Hold(window,false);
    Assert.That(layout.Held(window),Is.False);
   }
   finally{layout.Dispose();PlayerPrefs.DeleteKey("AthenHill.HudLayout.v1."+id);}
  }
 }
}
