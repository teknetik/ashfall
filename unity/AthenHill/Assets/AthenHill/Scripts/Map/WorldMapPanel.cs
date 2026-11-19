using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// The world map window (M, 19 Nov 2026). It lives in the shared modal (like the journal) but replaces the modal's
 /// scroll view with its own sheet: a north-up viewport on the left (drag or arrows/WASD to pan, wheel or +/- to zoom,
 /// C centres on you, T on the tracked target, F shows the whole sheet) and a column on the right (where you are, the
 /// tracked mission, where you would wake if you went down, and a list of places that centres the sheet on one).
 /// The base is the installer's survey picture when there is one, else a schematic drawn here from WorldMapSchematic.
 /// Markers and labels are drawn over either. Built in code; its styles are Resources/WorldMap/WorldMap.uss.
 public sealed class WorldMapPanel
 {
  public const string StylePath="WorldMap/WorldMap";
  // DESIGN.md palette: cyan focus/lattice, bronze structure, warm white text, amber Berms sites, red vitality.
  static readonly Color Cyan=new Color32(0x58,0xd5,0xd7,255),Bronze=new Color32(0xa4,0x8a,0x62,255),Ivory=new Color32(0xee,0xe9,0xdc,255),
   Amber=new Color32(0xd3,0x9a,0x4a,255),Way=new Color32(0x5f,0xc7,0xc9,255),Red=new Color32(0xc6,0x5c,0x4f,255),Ink=new Color32(0x0a,0x0e,0x0d,255),
   Sheet=new Color32(0x10,0x17,0x17,255),Floor=new Color32(0x1c,0x23,0x20,255),Contour=new Color32(0x3b,0x47,0x40,255),Ridge=new Color32(0x58,0x55,0x46,255),
   Road=new Color32(0x2a,0x2e,0x27,255),CityFloor=new Color32(0x1a,0x24,0x23,255),Block=new Color32(0x2c,0x36,0x33,255),BlockEdge=new Color32(0x65,0x70,0x6a,255);
  readonly VisualElement root,modal,modalScroll,panel,viewport,surveyLayer,ink,marks,labels,placesList;
  readonly Label scaleText,whereText,trackedTitle,trackedText,respawnText,sourceText;
  readonly VisualElement scaleBar;
  readonly Button trackedButton;
  readonly GameSession session;
  readonly WorldMap map;
  readonly Dictionary<string,Label> placeLabels=new Dictionary<string,Label>();
  /// The place last chosen in the PLACES list: its label wins a declutter clash (native QA, 19 Nov 2026).
  string selectedPlace;
  readonly List<VisualElement> surveyImages=new List<VisualElement>();
  readonly Label wardLabel,bermsLabel;
  MapView view;bool viewSet,shown,dragging,surveyBuilt,surveyShown;int dragPointer=-1;Vector2 dragLast;
  float sideRefresh;string listSignature;
  public bool Shown=>shown;
  public MapView View=>view;
  public bool SurveyShown=>surveyShown;
  public VisualElement Viewport=>viewport;

  public WorldMapPanel(VisualElement root,GameSession session)
  {
   this.root=root;this.session=session;map=session?session.Map:null;
   var style=Resources.Load<StyleSheet>(StylePath);
   if(style)root.styleSheets.Add(style);else Debug.LogWarning("World map styles missing: Resources/"+StylePath+".uss");
   modal=root.Q("modal");modalScroll=root.Q("modal-scroll");
   panel=new VisualElement{name="map-panel"};panel.AddToClassList("map-panel");panel.style.display=DisplayStyle.None;
   if(modalScroll!=null&&modalScroll.parent!=null)modalScroll.parent.Insert(modalScroll.parent.IndexOf(modalScroll)+1,panel);else modal?.Add(panel);

   // ---- the sheet
   viewport=new VisualElement{name="map-viewport",focusable=true,tabIndex=0};viewport.AddToClassList("map-viewport");
   // the shared window layout drags the whole modal from any non-control element; the sheet pans instead
   viewport.AddToClassList(HudWindowLayout.NoDragClass);
   panel.Add(viewport);
   surveyLayer=Layer("map-survey");ink=Layer("map-ink");marks=Layer("map-marks");labels=Layer("map-labels");
   ink.generateVisualContent+=DrawBase;marks.generateVisualContent+=DrawMarks;
   wardLabel=RegionLabel("WARD");bermsLabel=RegionLabel("OUTER BERMS");
   var scale=new VisualElement{name="map-scale",pickingMode=PickingMode.Ignore};scale.AddToClassList("map-scale");viewport.Add(scale);
   scaleBar=new VisualElement{pickingMode=PickingMode.Ignore};scaleBar.AddToClassList("map-scale-bar");scale.Add(scaleBar);
   scaleText=new Label{pickingMode=PickingMode.Ignore};scaleText.AddToClassList("map-scale-text");scale.Add(scaleText);
   var north=new Label("N"){name="map-north",pickingMode=PickingMode.Ignore};north.AddToClassList("map-north");viewport.Add(north);
   sourceText=new Label{name="map-source",pickingMode=PickingMode.Ignore};sourceText.AddToClassList("map-source");viewport.Add(sourceText);

   viewport.RegisterCallback<PointerDownEvent>(OnPointerDown);
   viewport.RegisterCallback<PointerMoveEvent>(OnPointerMove);
   viewport.RegisterCallback<PointerUpEvent>(OnPointerUp);
   viewport.RegisterCallback<PointerCaptureOutEvent>(_=>{dragging=false;dragPointer=-1;});
   viewport.RegisterCallback<WheelEvent>(OnWheel);
   viewport.RegisterCallback<ClickEvent>(e=>{if(e.clickCount==2){Zoom((Vector2)e.localPosition,2);e.StopPropagation();}});
   // arrows and WASD pan the sheet (polled in Tick): withhold them from focus navigation while the sheet has focus
   viewport.RegisterCallback<NavigationMoveEvent>(e=>{if(UiNavigation.IsArrow(e.direction))UiNavigation.Consume(e,viewport);});
   viewport.RegisterCallback<GeometryChangedEvent>(_=>Resized());

   // ---- the column
   var side=new VisualElement{name="map-side"};side.AddToClassList("map-side");panel.Add(side);
   Heading(side,"YOU ARE");
   whereText=Text(side,"map-where","map-copy");
   var row=new VisualElement();row.AddToClassList("map-buttons");side.Add(row);
   var me=new Button(CentreOnPlayer){name="map-centre",text="Centre on me · C"};me.AddToClassList("map-button");row.Add(me);
   var all=new Button(ShowAll){name="map-whole",text="Whole sheet · F"};all.AddToClassList("map-button");row.Add(all);
   Heading(side,"TRACKED");
   trackedTitle=Text(side,"map-tracked-title","map-tracked-title");
   trackedText=Text(side,"map-tracked","map-copy");
   trackedButton=new Button(CentreOnTracked){name="map-centre-tracked",text="Show on the sheet · T"};trackedButton.AddToClassList("map-button");side.Add(trackedButton);
   Heading(side,"IF YOU GO DOWN");
   respawnText=Text(side,"map-respawn","map-copy");
   Heading(side,"PLACES");
   var scroll=new ScrollView(ScrollViewMode.Vertical){name="map-places-scroll"};scroll.AddToClassList("map-places-scroll");scroll.horizontalScrollerVisibility=ScrollerVisibility.Hidden;side.Add(scroll);
   UiNavigation.KeepFocusVisible(scroll);
   placesList=scroll.contentContainer;
   if(map)map.Panel=this;
  }
  VisualElement Layer(string name){var v=new VisualElement{name=name,pickingMode=PickingMode.Ignore};v.AddToClassList("map-layer");viewport.Add(v);return v;}
  Label RegionLabel(string text){var l=new Label(text){pickingMode=PickingMode.Ignore};l.AddToClassList("map-label");l.AddToClassList("region");labels.Add(l);return l;}
  static Label Text(VisualElement parent,string name,string cls){var l=new Label{name=name};l.AddToClassList(cls);parent.Add(l);return l;}
  static void Heading(VisualElement parent,string text){var l=new Label(text);l.AddToClassList("map-heading");parent.Add(l);}

  // ------------------------------------------------------------------ window
  /// Called from CityHud.Refresh: the sheet takes the modal's place while the map is open.
  public void Refresh()
  {
   bool open=session&&session.State==CityState.Map;
   if(open!=shown){shown=open;panel.style.display=open?DisplayStyle.Flex:DisplayStyle.None;modal?.EnableInClassList("map-modal",open);if(!open)dragging=false;}
   if(!open)return;
   if(modalScroll!=null)modalScroll.style.display=DisplayStyle.None;
   SetText("modal-title","World map");
   SetText("modal-subtitle",map&&map.InBerms?"Outer Berms · Warden survey sheet":"Ward · Warden survey sheet");
   SetText("modal-footer-right","Drag / arrows · Pan     Wheel / + − · Zoom     C · You     T · Tracked     M / Esc · Close");
   UpdateSide(true);
  }
  void SetText(string name,string text){var l=root.Q<Label>(name);if(l!=null)l.text=text;}
  /// The window opened (CityHud): focus the sheet and centre it on the player.
  public void Opened()
  {
   BuildSurvey();
   listSignature=null;
   viewSet=false;Resized();
   viewport.schedule.Execute(()=>viewport.Focus());
  }
  void Resized()
  {
   var size=viewport.contentRect.size;
   if(float.IsNaN(size.x)||size.x<=1||size.y<=1)return;
   bool first=view.scale<=0;
   view.size=size;
   if(!viewSet)
   {
    viewSet=true;
    float s=first?(map&&map.InBerms?1.3f:6f):view.scale;
    view.scale=Mathf.Clamp(s,MinScale,WorldMapMath.MaxScale);
    view.centre=PlayerXZ();
   }
   ApplyView();
  }
  float MinScale=>Mathf.Min(MapView.FitScale(SheetBounds,view.size.x>0?view.size:new Vector2(1200,800),12),2);
  Rect SheetBounds=>WorldMapMath.DefaultBounds;
  void ApplyView()
  {
   view=view.Clamp(SheetBounds);
   if(view.scale<=0)return;
   PlaceSurvey();ink.MarkDirtyRepaint();marks.MarkDirtyRepaint();PlaceLabels();UpdateScale();
  }
  Vector2 PlayerXZ(){var p=session&&session.player?session.player.transform.position:Vector3.zero;return new Vector2(p.x,p.z);}
  public void CentreOn(Vector2 world){view.centre=world;ApplyView();}
  public void CentreOnPlayer()=>CentreOn(PlayerXZ());
  public void CentreOnTracked(){var m=map?map.Tracked(out _):MapMarker.None;if(m.shown)CentreOn(m.position);}
  public void ShowAll(){view.scale=MinScale;view.centre=SheetBounds.center;ApplyView();}
  void Zoom(Vector2 at,float factor){view=view.ZoomAt(at,factor,MinScale,WorldMapMath.MaxScale);ApplyView();}

  // ------------------------------------------------------------------ input
  void OnPointerDown(PointerDownEvent e)
  {
   if(e.button!=0)return;
   viewport.Focus();dragging=true;dragPointer=e.pointerId;dragLast=e.localPosition;viewport.CapturePointer(e.pointerId);e.StopPropagation();
  }
  void OnPointerMove(PointerMoveEvent e)
  {
   if(!dragging||e.pointerId!=dragPointer)return;
   var p=(Vector2)e.localPosition;view=view.Pan(p-dragLast);dragLast=p;ApplyView();e.StopPropagation();
  }
  void OnPointerUp(PointerUpEvent e)
  {
   if(e.pointerId!=dragPointer)return;
   dragging=false;dragPointer=-1;if(viewport.HasPointerCapture(e.pointerId))viewport.ReleasePointer(e.pointerId);e.StopPropagation();
  }
  void OnWheel(WheelEvent e)
  {
   if(Mathf.Abs(e.delta.y)<.001f)return;
   Zoom(e.localMousePosition,e.delta.y<0?1.25f:.8f);e.StopPropagation();
  }
  /// Every frame while the map is open (WorldMap.Update): keys, the player arrow and the column.
  public void Tick(float dt)
  {
   if(!shown)return;
   var k=Keyboard.current;
   if(k!=null&&view.scale>0)
   {
    var focused=viewport.panel?.focusController?.focusedElement as VisualElement;
    bool sheet=focused==null||focused==viewport;
    if(sheet)
    {
     var d=Vector2.zero;
     if(k.leftArrowKey.isPressed||k.aKey.isPressed)d.x+=1;
     if(k.rightArrowKey.isPressed||k.dKey.isPressed)d.x-=1;
     if(k.upArrowKey.isPressed||k.wKey.isPressed)d.y+=1;
     if(k.downArrowKey.isPressed||k.sKey.isPressed)d.y-=1;
     if(d!=Vector2.zero){view=view.Pan(d.normalized*(k.shiftKey.isPressed?1400:560)*dt);ApplyView();}
    }
    bool zoomIn=k.equalsKey.isPressed||k.numpadPlusKey.isPressed,zoomOut=k.minusKey.isPressed||k.numpadMinusKey.isPressed;
    if(zoomIn!=zoomOut)Zoom(view.size*.5f,Mathf.Exp((zoomIn?1.6f:-1.6f)*dt));
    if(k.cKey.wasPressedThisFrame)CentreOnPlayer();
    if(k.tKey.wasPressedThisFrame)CentreOnTracked();
    if(k.fKey.wasPressedThisFrame)ShowAll();
   }
   marks.MarkDirtyRepaint();
   sideRefresh-=dt;if(sideRefresh<=0)UpdateSide(false);
  }

  // ------------------------------------------------------------------ survey pictures
  void BuildSurvey()
  {
   if(surveyBuilt)return;surveyBuilt=true;
   var survey=map?map.Survey:null;
   sourceText.text="SCHEMATIC";
   if(survey==null||survey.layers==null)return;
   foreach(var l in survey.layers.Where(survey.Usable).OrderBy(l=>l.order))
   {
    var img=new VisualElement{name="map-survey-"+l.id,pickingMode=PickingMode.Ignore,userData=l};img.AddToClassList("map-survey-layer");
    img.style.backgroundImage=new StyleBackground(l.texture);
    surveyLayer.Add(img);surveyImages.Add(img);
   }
   surveyShown=surveyImages.Count>0;
   sourceText.text=surveyShown?$"SURVEY · {survey.renderedUtc?.Split('T')[0]}":"SCHEMATIC";
  }
  void PlaceSurvey()
  {
   foreach(var img in surveyImages)
   {
    var r=view.WorldRectToPanel(((WorldMapSurvey.Layer)img.userData).worldRect);
    img.style.left=r.x;img.style.top=r.y;img.style.width=r.width;img.style.height=r.height;
   }
  }

  // ------------------------------------------------------------------ drawing
  Vector2 P(Vector2 world)=>view.WorldToPanel(world);
  /// The schematic base (only when there is no survey picture), the Warden trails and the walls' gates.
  void DrawBase(MeshGenerationContext ctx)
  {
   if(view.scale<=0)return;
   var g=ctx.painter2D;var size=view.size;
   // over a survey picture only the trails are drawn (the picture sits under this layer)
   if(!surveyShown){g.fillColor=Sheet;Box(g,new Rect(0,0,size.x,size.y));g.Fill();DrawSchematic(g);}
   // Warden trails (their cairns are in the Berms either way)
   g.strokeColor=new Color(Bronze.r,Bronze.g,Bronze.b,.75f);g.lineWidth=2;
   foreach(var t in WorldMapSchematic.Trails)for(int i=1;i<t.Length;i++)Dashed(g,P(t[i-1]),P(t[i]),7,6);
  }
  void DrawSchematic(Painter2D g)
  {
   float s=view.scale;
   // the bowl floor, with contour-like rings drawn inward from the mountain foot
   var bowl=WorldMapSchematic.Bowl;var centre=Centroid(bowl);
   g.fillColor=Floor;Poly(g,bowl,1,centre);g.Fill();
   g.strokeColor=Contour;g.lineWidth=1.2f;
   foreach(float k in new[]{.86f,.72f,.58f,.44f}){Poly(g,bowl,k,centre);g.Stroke();}
   // the mountain foot: a ridge line and hatching outward (downhill from the crest toward the floor reads inward)
   g.strokeColor=Ridge;g.lineWidth=2;Poly(g,bowl,1,centre);g.Stroke();
   g.lineWidth=1.2f;
   for(int i=0;i<bowl.Length;i++)
   {
    var a=bowl[i];var b=bowl[(i+1)%bowl.Length];float len=(b-a).magnitude;if(len<1)continue;
    var dir=(b-a)/len;var outward=new Vector2(dir.y,-dir.x);
    if(Vector2.Dot(outward,(a+b)*.5f-centre)<0)outward=-outward;
    for(float d=4;d<len;d+=9){var at=a+dir*d;g.BeginPath();g.MoveTo(P(at));g.LineTo(P(at+outward*(d%18<9?14:8)));g.Stroke();}
   }
   // the old Berms ground (the repainted road, the post and the range stand on it)
   g.fillColor=Road;Box(g,PanelRect(WorldMapSchematic.OldBerms));g.Fill();
   // the city: paving, the hill, buildings, the Tube conduit, walls and gates
   g.fillColor=CityFloor;Box(g,PanelRect(WorldMapMath.CityBounds));g.Fill();
   g.fillColor=new Color32(0x26,0x30,0x2b,255);g.strokeColor=Bronze;g.lineWidth=Mathf.Clamp(.4f*s,1,3);
   g.BeginPath();g.Arc(P(WorldMapSchematic.HillCentre),WorldMapSchematic.HillRadius*s,Angle.Degrees(0),Angle.Degrees(360),ArcDirection.Clockwise);g.ClosePath();g.Fill();g.Stroke();
   foreach(var b in WorldMapSchematic.Blocks)
   {
    var r=PanelRect(b.rect);
    g.fillColor=b.ruin?new Color(Block.r,Block.g,Block.b,.45f):Block;Box(g,r);g.Fill();
    g.strokeColor=BlockEdge;g.lineWidth=1;
    if(b.ruin){var c=new[]{new Vector2(r.xMin,r.yMin),new Vector2(r.xMax,r.yMin),new Vector2(r.xMax,r.yMax),new Vector2(r.xMin,r.yMax)};for(int i=0;i<4;i++)Dashed(g,c[i],c[(i+1)%4],4,3);}
    else{Box(g,r);g.Stroke();}
   }
   g.strokeColor=new Color(Cyan.r,Cyan.g,Cyan.b,.45f);g.lineWidth=Mathf.Clamp(.8f*s,1,4);
   foreach(var c in WorldMapSchematic.Conduit)Dashed(g,P(c.a),P(c.b),6,4);
   g.strokeColor=Bronze;g.lineWidth=Mathf.Clamp(1.4f*s,2,9);g.lineCap=LineCap.Butt;
   foreach(var w in WorldMapSchematic.Walls){g.BeginPath();g.MoveTo(P(w.a));g.LineTo(P(w.b));g.Stroke();}
   g.strokeColor=Ivory;g.lineWidth=Mathf.Clamp(.5f*s,1.5f,4);
   foreach(var w in WorldMapSchematic.Gates)Dashed(g,P(w.a),P(w.b),3,3);
  }
  /// Markers: places, the respawn ring, the tracked target, the last knock-down and the player arrow (every frame).
  void DrawMarks(MeshGenerationContext ctx)
  {
   if(view.scale<=0||!map)return;
   var g=ctx.painter2D;bool city=view.scale>=WorldMapMath.CityLabelScale;
   var respawn=map.RespawnStation;
   foreach(var p in map.Places)
   {
    if(!map.Shown(p))continue;
    var at=P(p.Position);if(!Inside(at,20))continue;
    switch(p.kind)
    {
     case MapPlaceKind.Site:Diamond(g,at,7,map.Cleared(p)?new Color(Amber.r,Amber.g,Amber.b,.45f):Amber);break;
     case MapPlaceKind.Waystation:Diamond(g,at,8,Way);break;
     case MapPlaceKind.Gate:Diamond(g,at,6,Ivory);break;
     case MapPlaceKind.BermsPlace:Diamond(g,at,5,Bronze);break;
     case MapPlaceKind.Home:Square(g,at,6,Bronze);break;
     default:if(city)Diamond(g,at,p.kind==MapPlaceKind.Landmark?6:4,p.kind==MapPlaceKind.Landmark?Ivory:Bronze);break;
    }
   }
   // the respawn: the nearest found waystation, else the gate post
   Vector3? wake=respawn?(Vector3?)respawn.transform.position:map.GatePost;
   if(wake.HasValue){var at=P(new Vector2(wake.Value.x,wake.Value.z));if(Inside(at,30))Ring(g,at,14,Way,2);}
   if(map.LastDowned.HasValue){var at=P(map.LastDowned.Value);if(Inside(at,10))Cross(g,at,7,Red);}
   var tracked=map.Tracked(out _);
   if(tracked.shown)
   {
    var at=P(tracked.position);
    if(Inside(at,-6))
    {
     if(tracked.area){g.fillColor=new Color(Cyan.r,Cyan.g,Cyan.b,.12f);g.BeginPath();g.Arc(at,Mathf.Max(16,tracked.radius*view.scale),Angle.Degrees(0),Angle.Degrees(360),ArcDirection.Clockwise);g.ClosePath();g.Fill();g.strokeColor=Cyan;g.lineWidth=2;Circle(g,at,Mathf.Max(16,tracked.radius*view.scale),true);}
     else{Ring(g,at,12,Cyan,2);Diamond(g,at,6,Cyan);}
    }
    else EdgeArrow(g,at,Cyan);
   }
   // the player: an arrow along the camera heading (the compass uses the same heading)
   var me=P(PlayerXZ());
   if(Inside(me,-4))
   {
    var fwd=WorldMapMath.HeadingToPanel(CameraHeading());var right=new Vector2(-fwd.y,fwd.x);
    g.fillColor=Ivory;g.strokeColor=Ink;g.lineWidth=2;g.lineJoin=LineJoin.Miter;
    g.BeginPath();g.MoveTo(me+fwd*13);g.LineTo(me-fwd*8+right*8);g.LineTo(me-fwd*4);g.LineTo(me-fwd*8-right*8);g.ClosePath();g.Fill();g.Stroke();
   }
   else EdgeArrow(g,me,Ivory);
  }
  float CameraHeading()
  {
   if(session&&session.follow)return session.follow.transform.eulerAngles.y;
   return session&&session.player&&session.player.visual?session.player.visual.eulerAngles.y:0;
  }
  bool Inside(Vector2 p,float margin)=>p.x>=-margin&&p.y>=-margin&&p.x<=view.size.x+margin&&p.y<=view.size.y+margin;
  Rect PanelRect(Rect world)=>view.WorldRectToPanel(world);
  static Vector2 Centroid(Vector2[] poly){var c=Vector2.zero;foreach(var p in poly)c+=p;return c/poly.Length;}
  void Poly(Painter2D g,Vector2[] poly,float k,Vector2 centre)
  {
   g.BeginPath();
   for(int i=0;i<poly.Length;i++){var p=P(centre+(poly[i]-centre)*k);if(i==0)g.MoveTo(p);else g.LineTo(p);}
   g.ClosePath();
  }
  static void Box(Painter2D g,Rect r){g.BeginPath();g.MoveTo(new Vector2(r.xMin,r.yMin));g.LineTo(new Vector2(r.xMax,r.yMin));g.LineTo(new Vector2(r.xMax,r.yMax));g.LineTo(new Vector2(r.xMin,r.yMax));g.ClosePath();}
  /// Dashes drawn as separate segments (no dash state is left on the painter).
  static void Dashed(Painter2D g,Vector2 a,Vector2 b,float dash,float gap)
  {
   float len=(b-a).magnitude;if(len<.5f)return;var dir=(b-a)/len;
   // at high zoom a trail runs thousands of pixels off the sheet: stretch the pattern rather than emit thousands of dashes
   float period=dash+gap;if(len/period>300){float k=len/period/300;dash*=k;period*=k;}
   g.BeginPath();
   for(float d=0;d<len;d+=period){g.MoveTo(a+dir*d);g.LineTo(a+dir*Mathf.Min(len,d+dash));}
   g.Stroke();
  }
  static void Diamond(Painter2D g,Vector2 at,float r,Color c)
  {
   g.fillColor=c;g.strokeColor=new Color(Ink.r,Ink.g,Ink.b,.8f);g.lineWidth=1.5f;g.lineJoin=LineJoin.Miter;
   g.BeginPath();g.MoveTo(at+new Vector2(0,-r));g.LineTo(at+new Vector2(r,0));g.LineTo(at+new Vector2(0,r));g.LineTo(at+new Vector2(-r,0));g.ClosePath();g.Fill();g.Stroke();
  }
  static void Square(Painter2D g,Vector2 at,float r,Color c)
  {
   g.fillColor=c;g.strokeColor=Ink;g.lineWidth=1.5f;
   Box(g,new Rect(at.x-r,at.y-r,r*2,r*2));g.Fill();g.Stroke();
  }
  static void Ring(Painter2D g,Vector2 at,float r,Color c,float width){g.strokeColor=c;g.lineWidth=width;Circle(g,at,r,false);}
  static void Circle(Painter2D g,Vector2 at,float r,bool dashed)
  {
   if(!dashed){g.BeginPath();g.Arc(at,r,Angle.Degrees(0),Angle.Degrees(360),ArcDirection.Clockwise);g.ClosePath();g.Stroke();return;}
   int n=Mathf.Clamp(Mathf.RoundToInt(r/3),12,72);
   g.BeginPath();
   for(int i=0;i<n;i+=2)
   {
    float a0=i*Mathf.PI*2/n,a1=(i+1)*Mathf.PI*2/n;
    g.MoveTo(at+new Vector2(Mathf.Cos(a0),Mathf.Sin(a0))*r);g.LineTo(at+new Vector2(Mathf.Cos(a1),Mathf.Sin(a1))*r);
   }
   g.Stroke();
  }
  static void Cross(Painter2D g,Vector2 at,float r,Color c)
  {
   g.strokeColor=c;g.lineWidth=3;g.lineCap=LineCap.Round;
   g.BeginPath();g.MoveTo(at+new Vector2(-r,-r));g.LineTo(at+new Vector2(r,r));g.MoveTo(at+new Vector2(r,-r));g.LineTo(at+new Vector2(-r,r));g.Stroke();
   g.lineCap=LineCap.Butt;
  }
  /// A small triangle on the sheet's edge pointing toward something off the sheet.
  void EdgeArrow(Painter2D g,Vector2 target,Color c)
  {
   var mid=view.size*.5f;var d=target-mid;if(d.sqrMagnitude<1)return;
   float t=Mathf.Min(Mathf.Abs((mid.x-16)/(Mathf.Abs(d.x)<.001f?.001f:d.x)),Mathf.Abs((mid.y-16)/(Mathf.Abs(d.y)<.001f?.001f:d.y)));
   var at=mid+d*Mathf.Min(1,t);var f=d.normalized;var r=new Vector2(-f.y,f.x);
   g.fillColor=c;g.strokeColor=Ink;g.lineWidth=1.5f;
   g.BeginPath();g.MoveTo(at+f*9);g.LineTo(at-f*6+r*7);g.LineTo(at-f*6-r*7);g.ClosePath();g.Fill();g.Stroke();
  }

  // ------------------------------------------------------------------ labels and scale
  void PlaceLabels()
  {
   if(!map)return;
   bool city=view.scale>=WorldMapMath.CityLabelScale;
   var seen=new HashSet<string>();
   var boxes=new List<WorldMapMath.LabelBox>();
   foreach(var p in map.Places)
   {
    bool cp=p.kind==MapPlaceKind.Shop||p.kind==MapPlaceKind.Service||p.kind==MapPlaceKind.Landmark||p.kind==MapPlaceKind.Home;
    var a=P(p.Position);
    if(!(map.Shown(p)&&(!cp||city||p.kind==MapPlaceKind.Home)&&Inside(a,-2)))continue;
    var size=WorldMapMath.LabelSize(p.name,p.kind==MapPlaceKind.Shop||p.kind==MapPlaceKind.Service?13:15);
    boxes.Add(new WorldMapMath.LabelBox{id=p.id,rect=new Rect(a.x+10,a.y-11,size.x,size.y),priority=WorldMapMath.LabelPriority(p.kind)});
   }
   var crowded=WorldMapMath.Declutter(boxes,selectedPlace);
   foreach(var p in map.Places)
   {
    seen.Add(p.id);
    if(!placeLabels.TryGetValue(p.id,out var l))
    {
     l=new Label(p.name){name="map-label-"+p.id,pickingMode=PickingMode.Ignore};l.AddToClassList("map-label");l.AddToClassList(p.kind.ToString().ToLowerInvariant());
     labels.Add(l);placeLabels[p.id]=l;
    }
    l.text=p.name;
    bool cityPlace=p.kind==MapPlaceKind.Shop||p.kind==MapPlaceKind.Service||p.kind==MapPlaceKind.Landmark||p.kind==MapPlaceKind.Home;
    var at=P(p.Position);
    bool show=map.Shown(p)&&(!cityPlace||city||p.kind==MapPlaceKind.Home)&&Inside(at,-2)&&!crowded.Contains(p.id);
    l.style.display=show?DisplayStyle.Flex:DisplayStyle.None;
    if(!show)continue;
    l.EnableInClassList("cleared",map.Cleared(p));
    l.style.left=at.x+10;l.style.top=at.y-11;
   }
   foreach(var pair in placeLabels)if(!seen.Contains(pair.Key))pair.Value.style.display=DisplayStyle.None;
   Region(wardLabel,new Vector2(0,0),!city);
   Region(bermsLabel,new Vector2(-330,10),view.scale<4);
  }
  void Region(Label l,Vector2 world,bool show)
  {
   var at=P(world);show&=Inside(at,-20);
   l.style.display=show?DisplayStyle.Flex:DisplayStyle.None;
   if(show){l.style.left=at.x;l.style.top=at.y;l.style.translate=new Translate(Length.Percent(-50),Length.Percent(-50));}
  }
  void UpdateScale()
  {
   float m=WorldMapMath.ScaleBarMetres(view.scale);
   scaleBar.style.width=m*view.scale;scaleText.text=WorldMapMath.MetresText(m);
  }

  // ------------------------------------------------------------------ column
  void UpdateSide(bool rebuildList)
  {
   sideRefresh=.25f;
   if(!map||!session)return;
   var p=session.player?session.player.transform.position:Vector3.zero;
   var nearest=map.Places.Where(x=>map.Shown(x)).OrderBy(x=>(x.Position-new Vector2(p.x,p.z)).sqrMagnitude).FirstOrDefault();
   string region=map.InBerms?"Outer Berms":"Ward";
   whereText.text=nearest!=null?$"{region} · {Mathf.RoundToInt((nearest.Position-new Vector2(p.x,p.z)).magnitude)} m from {nearest.name}":region;
   var marker=map.Tracked(out var mission);
   trackedTitle.text=mission!=null?mission.title.ToUpperInvariant():"NO MISSION TRACKED";
   if(mission==null)trackedText.text="Pick one in your journal (J).";
   else if(!marker.shown)trackedText.text=string.IsNullOrEmpty(mission.objective)?"No marker for this step.":mission.objective;
   else
   {
    float d=(marker.position-new Vector2(p.x,p.z)).magnitude;
    string label=string.IsNullOrEmpty(mission.targetLabel)?"Marker":mission.targetLabel;
    trackedText.text=marker.area?$"{label} · somewhere around here · about {Mathf.RoundToInt(d)} m":$"{label} · {Mathf.RoundToInt(d)} m";
   }
   trackedButton.SetEnabled(marker.shown);
   // Native QA (19 Nov 2026): no offer to show a target the tracked mission does not have on the sheet.
   trackedButton.style.display=marker.shown?DisplayStyle.Flex:DisplayStyle.None;
   var station=map.RespawnStation;
   respawnText.text=(station?$"The Wardens bring you back to the {station.displayName.ToLowerInvariant()} (cyan ring).":"The Wardens bring you back to the West Gate post (cyan ring).")+(map.LastDowned.HasValue?"\nThe red cross marks where you last went down.":"");
   string sig=string.Join(";",map.Places.Where(map.Shown).Select(x=>x.id));
   if(rebuildList&&listSignature==null||sig!=listSignature)
   {
    listSignature=sig;
    var focused=viewport.panel?.focusController?.focusedElement as VisualElement;bool inList=focused!=null&&placesList.Contains(focused);
    placesList.Clear();
    void Group(string heading,IEnumerable<MapPlace> items)
    {
     var list=items.ToList();if(list.Count==0)return;
     var h=new Label(heading);h.AddToClassList("map-heading");h.AddToClassList("map-group");placesList.Add(h);
     foreach(var x in list)
     {
      var place=x;
      var b=new Button(()=>{if(view.scale<WorldMapMath.CityLabelScale&&place.kind!=MapPlaceKind.Site&&place.kind!=MapPlaceKind.Waystation&&!place.id.StartsWith("berms:"))view.scale=WorldMapMath.CityLabelScale+1;selectedPlace=place.id;CentreOn(place.Position);}){name="map-place-"+place.id,text=place.name};
      b.AddToClassList("map-place");b.AddToClassList(place.kind.ToString().ToLowerInvariant());
      placesList.Add(b);
     }
    }
    var shown=map.Places.Where(map.Shown).ToList();
    Group("WARD",shown.Where(x=>x.id.StartsWith("city:")));
    Group("OUTER BERMS",shown.Where(x=>!x.id.StartsWith("city:")).OrderBy(x=>x.kind==MapPlaceKind.Site?1:0));
    if(inList)placesList.schedule.Execute(()=>placesList.Q<Button>()?.Focus());
   }
  }
 }
}
