using System;
using UnityEngine;
namespace AthenHill
{
 /// How an open conversation is drawn (19 Nov 2026, interface package). Centred is the original 860 px window over the
 /// dark shade; LowerThird is the bottom panel with no shade, used only while the conversation camera frames the NPC.
 public enum DialogueLayout { None,Centred,LowerThird }
 /// Settings › Controls › Interface. Full is the HUD as it was before; Adaptive lets the quiet corner panels fade.
 public enum InterfaceMode { Full=0,Adaptive=1 }
 /// The HUD groups the presentation rules can fade. Identity, FieldNotes, Log and KeyHints follow the adaptive rules;
 /// Hotbar only gives way to the lower-third dialogue.
 public enum HudPanel { Identity,FieldNotes,Log,KeyHints,Hotbar,Compass }

 /// Pure rule for which dialogue layout applies. The conversation camera decides first person once per conversation,
 /// in its own LateUpdate after the dialogue opened, so for a short grace period the HUD predicts from the follow camera;
 /// from the frame the camera engages its own Framing flag is authoritative.
 public static class DialogueLayoutRule
 {
  /// Seconds the prediction is trusted before a camera that has not engaged counts as not framing.
  public const float Grace=.25f;
  /// <param name="cameraOn">ConversationCamera.Enabled, the component present, enabled and its framing switch on, and
  /// photo mode closed.</param>
  /// <param name="fixedView">A review camera owns the view (the conversation camera suspends itself).</param>
  /// <param name="firstPersonNow">The follow camera is in first person (the camera would add depth of field only).</param>
  /// <param name="engaged">The conversation camera has a weight above zero.</param>
  /// <param name="framing">The conversation camera is using its third-person shot (shoulder or eye-line fallback).</param>
  public static DialogueLayout Choose(bool dialogueOpen,bool cameraOn,bool fixedView,bool firstPersonNow,bool engaged,bool framing,float secondsOpen,float grace=Grace)
  {
   if(!dialogueOpen)return DialogueLayout.None;
   if(!cameraOn||fixedView)return DialogueLayout.Centred;
   if(engaged)return framing?DialogueLayout.LowerThird:DialogueLayout.Centred;
   return secondsOpen<=grace&&!firstPersonNow?DialogueLayout.LowerThird:DialogueLayout.Centred;
  }
  public static string Id(DialogueLayout layout)=>layout==DialogueLayout.LowerThird?"lowerThird":layout==DialogueLayout.Centred?"centred":"none";
  /// Second line of the lower-third name plate: "role · topic". Most opening nodes are titled with the colonist's own
  /// role ("Basic General"), so a topic that repeats the role is left out instead of printing it twice.
  public static string NamePlateSubtitle(string role,string topic)
  {
   role=(role??"").Trim();topic=(topic??"").Trim();
   if(role.Length==0)return topic;
   if(topic.Length==0||string.Equals(role,topic,System.StringComparison.OrdinalIgnoreCase))return role;
   return role+" · "+topic;
  }
 }

 /// One frame of what the HUD knows, for <see cref="AdaptiveHudModel.Step"/>.
 public struct HudFrame
 {
  public InterfaceMode mode;
  /// The lower-third dialogue is up: every HUD panel (identity, Field Notes, compass, log, key hints, hotbar) gives way to it
  /// in either mode (native QA, 19 Nov 2026: identity, Field Notes and the compass crowded the conversation shot).
  public bool lowerThird;
  /// Any window (dialogue, trade, pack, journal, pause, settings…) is open.
  public bool windowOpen;
  /// A weapon is drawn or the player was hurt recently.
  public bool combat;
  /// Left Alt is held (the pointer is freed for the HUD).
  public bool altHeld;
  /// An interaction prompt is offered (the key hints carry E · Interact).
  public bool prompt;
  public bool reducedMotion;
 }

 /// Adaptive HUD timing (pure). Each adaptive panel stays up for <see cref="quietSeconds"/> after it last had something
 /// to say (<see cref="Wake"/>), then fades out; windows, combat and Left Alt hold every panel up. Full mode keeps every
 /// panel at full opacity. Fades are linear opacity steps; Reduced Motion cuts. Times are unscaled seconds.
 [Serializable]
 public sealed class AdaptiveHudModel
 {
  public static readonly HudPanel[] Panels={HudPanel.Identity,HudPanel.FieldNotes,HudPanel.Log,HudPanel.KeyHints,HudPanel.Hotbar,HudPanel.Compass};
  [Tooltip("Seconds a panel stays up after its last change before it fades (Adaptive).")]
  [Min(0)]public float quietSeconds=6;
  [Min(0)]public float fadeInSeconds=.2f,fadeOutSeconds=.6f;
  /// Below this the panel is treated as hidden (no picking, no drawing).
  public const float HiddenBelow=.001f;
  readonly float[] lastWake=new float[Panels.Length];
  readonly float[] alpha=new float[Panels.Length];
  public AdaptiveHudModel(){for(int i=0;i<alpha.Length;i++){alpha[i]=1;lastWake[i]=float.NegativeInfinity;}}
  public float Alpha(HudPanel p)=>alpha[(int)p];
  public bool Hidden(HudPanel p)=>alpha[(int)p]<HiddenBelow;
  public float LastWake(HudPanel p)=>lastWake[(int)p];
  public static bool Adaptive(HudPanel p)=>p!=HudPanel.Hotbar&&p!=HudPanel.Compass;
  /// The panel has something new to show (a changed objective, a log line, a vitals change, a prompt).
  public void Wake(HudPanel p,float now){lastWake[(int)p]=now;}
  public void WakeAll(float now){foreach(var p in Panels)lastWake[(int)p]=now;}
  /// Where the panel is heading this frame (0 hidden, 1 shown).
  public float Target(HudPanel p,in HudFrame f,float now)
  {
   if(f.lowerThird)return 0;
   if(!Adaptive(p)||f.mode!=InterfaceMode.Adaptive)return 1;
   if(f.windowOpen||f.combat||f.altHeld)return 1;
   if(p==HudPanel.KeyHints&&f.prompt)return 1;
   return now-lastWake[(int)p]<quietSeconds?1:0;
  }
  /// Advances every panel's opacity toward its target. Returns true when any opacity changed.
  public bool Step(in HudFrame f,float now,float dt)
  {
   // Holding conditions count as activity, so a panel waits the full quiet time after a window closes or Alt is let go.
   if(f.mode==InterfaceMode.Adaptive&&(f.windowOpen||f.combat||f.altHeld))WakeAll(now);
   if(f.prompt)Wake(HudPanel.KeyHints,now);
   bool changed=false;
   foreach(var p in Panels)
   {
    int i=(int)p;float target=Target(p,f,now),a=alpha[i];
    float next=f.reducedMotion?target:Mathf.MoveTowards(a,target,Mathf.Max(0,dt)/Mathf.Max(1e-4f,target>a?fadeInSeconds:fadeOutSeconds));
    if(next!=a){alpha[i]=next;changed=true;}
   }
   return changed;
  }
  /// Comma-free ids for QA ("identity", "fieldNotes", "log", "keyHints", "hotbar", "compass").
  public static string Id(HudPanel p)=>p switch{HudPanel.Identity=>"identity",HudPanel.FieldNotes=>"fieldNotes",HudPanel.Log=>"log",HudPanel.KeyHints=>"keyHints",HudPanel.Compass=>"compass",_=>"hotbar"};
 }
}
