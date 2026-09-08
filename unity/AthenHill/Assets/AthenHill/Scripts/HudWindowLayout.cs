using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

namespace AthenHill
{
 // Keep authored anchors/sizes in USS. User placement is a GPU translation over
 // that layout, so dragging never rebuilds a window or breaks its content bindings.
 public sealed class HudWindowLayout:IDisposable
 {
  readonly VisualElement root;
  readonly List<WindowDrag> windows=new List<WindowDrag>();
  readonly string prefix;
  WindowDrag active;
  public bool IsDragging=>active!=null;

  public HudWindowLayout(VisualElement root)
  {
   this.root=root;
   prefix="AthenHill.HudLayout.v1.";
   // Native checks can verify persistence without changing the player's layout.
   if(Debug.isDebugBuild&&Array.IndexOf(Environment.GetCommandLineArgs(),"--athen-qa")>=0)prefix+="QA.";
   root.RegisterCallback<GeometryChangedEvent>(RootResized);
  }

  public void Add(VisualElement window,string id,bool grip=false,bool worldAnchored=false)
  {
   if(string.IsNullOrEmpty(window.name))window.name=id;
   window.AddToClassList("movable-window");
   window.pickingMode=PickingMode.Position;
   if(grip)
   {
    var handle=new VisualElement{name=id+"-drag-handle",pickingMode=PickingMode.Position,tooltip="Drag to move · Ctrl-drag anywhere on this panel"};
    handle.AddToClassList("window-drag-grip");window.Add(handle);
   }
   var drag=new WindowDrag(this,window,prefix+id,worldAnchored);
   windows.Add(drag);window.AddManipulator(drag);
   window.schedule.Execute(drag.Reposition);
  }

  public void Reset()
  {
   CancelDrag();
   foreach(var window in windows)window.Reset();
   PlayerPrefs.Save();
  }
  public void CancelDrag(){active?.Finish(false);}
  void RootResized(GeometryChangedEvent evt){foreach(var window in windows)window.Reposition();}
  public void Dispose()
  {
   CancelDrag();root.UnregisterCallback<GeometryChangedEvent>(RootResized);
   foreach(var window in windows)window.Window.RemoveManipulator(window);
   windows.Clear();
  }

  [Serializable] class Placement { public float x,y; }

  sealed class WindowDrag:PointerManipulator
  {
   readonly HudWindowLayout owner;
   readonly string key;
   readonly bool worldAnchored;
   public readonly VisualElement Window;
   Placement placement;
   Vector2 offset,startOffset,startPointer;
   int pointerId=-1;
   bool moved;
   const float Edge=8;

   public WindowDrag(HudWindowLayout owner,VisualElement window,string key,bool worldAnchored)
   {
    this.owner=owner;Window=window;this.key=key;this.worldAnchored=worldAnchored;
    if(PlayerPrefs.HasKey(key))
    {
     try { placement=JsonUtility.FromJson<Placement>(PlayerPrefs.GetString(key)); }
     catch(ArgumentException) { placement=null; }
     if(placement!=null&&(!Finite(placement.x)||!Finite(placement.y)))placement=null;
    }
    // An off-camera nameplate may not receive geometry until much later.
    // Its saved displacement is relative to the NPC, independent of bounds.
    if(worldAnchored&&placement!=null)SetOffset(new Vector2(placement.x,placement.y));
   }
   static bool Finite(float n)=>!float.IsNaN(n)&&!float.IsInfinity(n);
   protected override void RegisterCallbacksOnTarget()
   {
    target.RegisterCallback<PointerDownEvent>(Down,TrickleDown.TrickleDown);
    target.RegisterCallback<PointerMoveEvent>(Move,TrickleDown.TrickleDown);
    target.RegisterCallback<PointerUpEvent>(Up,TrickleDown.TrickleDown);
    target.RegisterCallback<PointerCancelEvent>(Cancel);
    target.RegisterCallback<PointerCaptureOutEvent>(CaptureLost);
    target.RegisterCallback<GeometryChangedEvent>(Resized);
   }
   protected override void UnregisterCallbacksFromTarget()
   {
    target.UnregisterCallback<PointerDownEvent>(Down,TrickleDown.TrickleDown);
    target.UnregisterCallback<PointerMoveEvent>(Move,TrickleDown.TrickleDown);
    target.UnregisterCallback<PointerUpEvent>(Up,TrickleDown.TrickleDown);
    target.UnregisterCallback<PointerCancelEvent>(Cancel);
    target.UnregisterCallback<PointerCaptureOutEvent>(CaptureLost);
    target.UnregisterCallback<GeometryChangedEvent>(Resized);
   }
   void Down(PointerDownEvent evt)
   {
    if(evt.button!=0||!target.enabledInHierarchy||owner.active!=null)return;
    bool handle=false,control=target is Button;
    for(var element=evt.target as VisualElement;element!=null&&element!=target;element=element.parent)
    {
     handle|=element.ClassListContains("window-drag-grip");
     control|=element is Button||element is ScrollView||element is Scroller||element is Slider||element.ClassListContains("unity-base-field");
    }
    // Ordinary button/scroll input remains untouched. Ctrl-drag is the explicit
    // alternative when a narrow control leaves little exposed frame to grab.
    if(control&&!handle&&!evt.ctrlKey)return;
    owner.active=this;pointerId=evt.pointerId;moved=false;
    startPointer=(Vector2)evt.position;startOffset=offset;
    target.BringToFront();target.CapturePointer(pointerId);
    target.AddToClassList("window-dragging");
    evt.StopImmediatePropagation();
   }
   void Move(PointerMoveEvent evt)
   {
    if(owner.active!=this||evt.pointerId!=pointerId)return;
    var delta=(Vector2)evt.position-startPointer;
    if(delta.sqrMagnitude>=9)moved=true;
    if(moved)SetOffset(Clamp(startOffset+delta));
    evt.StopImmediatePropagation();
   }
   void Up(PointerUpEvent evt)
   {
    if(owner.active!=this||evt.pointerId!=pointerId||evt.button!=0)return;
    Finish(true);evt.StopImmediatePropagation();
   }
   void Cancel(PointerCancelEvent evt){if(owner.active==this)Finish(false);}
   void CaptureLost(PointerCaptureOutEvent evt){if(owner.active==this)Finish(true);}
   void Resized(GeometryChangedEvent evt){if(!worldAnchored)Reposition();}

   Vector2 BasePosition=>Window.worldBound.position-owner.root.worldBound.position-offset;
   Vector2 Travel=>new Vector2(Mathf.Max(0,owner.root.worldBound.width-Window.worldBound.width-Edge*2),Mathf.Max(0,owner.root.worldBound.height-Window.worldBound.height-Edge*2));
   Vector2 Clamp(Vector2 proposed)
   {
    var origin=BasePosition;var travel=Travel;var desired=origin+proposed;
    desired.x=Mathf.Clamp(desired.x,Edge,Edge+travel.x);
    desired.y=Mathf.Clamp(desired.y,Edge,Edge+travel.y);
    return desired-origin;
   }
   void SetOffset(Vector2 value)
   {
    offset=value;
    Window.style.translate=new Translate(new Length(offset.x),new Length(offset.y),0);
   }
   public void Reposition()
   {
    if(placement==null||owner.active==this||Window.resolvedStyle.display==DisplayStyle.None)return;
    var bounds=Window.worldBound;
    if(!Finite(bounds.width)||!Finite(bounds.height)||bounds.width<=0||bounds.height<=0)return;
    if(worldAnchored){SetOffset(new Vector2(placement.x,placement.y));return;}
    var travel=Travel;
    var position=new Vector2(Edge+Mathf.Clamp01(placement.x)*travel.x,Edge+Mathf.Clamp01(placement.y)*travel.y);
    SetOffset(position-BasePosition);
   }
   public void Finish(bool save)
   {
    if(owner.active!=this)return;
    owner.active=null;
    target.RemoveFromClassList("window-dragging");
    if(target.HasPointerCapture(pointerId))target.ReleasePointer(pointerId);
    pointerId=-1;
    if(!save){SetOffset(startOffset);Reposition();return;}
    if(!moved)return;
    var position=BasePosition+offset;var travel=Travel;
    placement=worldAnchored?new Placement{x=offset.x,y=offset.y}:new Placement{x=travel.x>0?(position.x-Edge)/travel.x:0,y=travel.y>0?(position.y-Edge)/travel.y:0};
    PlayerPrefs.SetString(key,JsonUtility.ToJson(placement));PlayerPrefs.Save();
   }
   public void Reset(){placement=null;PlayerPrefs.DeleteKey(key);SetOffset(Vector2.zero);}
  }
 }
}
