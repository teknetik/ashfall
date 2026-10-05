using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// The journal window (J, 5 Oct 2026). MISSIONS: active and completed missions on the left; the selected one's giver,
 /// area, briefing, objective checklist, current instruction and reward on the right, with Track. WARD NOTES: the city
 /// notes that "City notes" used to show. Up/Down move through the missions, T tracks the selected one.
 public sealed class JournalPanel
 {
  readonly VisualElement panel,missionsPage,notesPage,list,steps;
  readonly Button tabMissions,tabNotes,track;
  readonly Label title,meta,status,summary,now,nowHeading,reward,rewardHeading,notesText,empty;
  readonly GameSession session;
  readonly QuestJournal journal;
  string selected,signature;bool notes;
  public string Selected=>selected;
  public bool NotesShown=>notes;
  public JournalPanel(VisualElement panel,GameSession session,QuestJournal journal)
  {
   this.panel=panel;this.session=session;this.journal=journal;
   var tabs=new VisualElement{name="journal-tabs"};tabs.AddToClassList("journal-tabs");panel.Add(tabs);
   tabMissions=new Button(()=>ShowNotes(false)){name="journal-tab-missions",text="MISSIONS"};tabMissions.AddToClassList("journal-tab");tabs.Add(tabMissions);
   tabNotes=new Button(()=>ShowNotes(true)){name="journal-tab-notes",text="WARD NOTES"};tabNotes.AddToClassList("journal-tab");tabs.Add(tabNotes);
   missionsPage=new VisualElement{name="journal-missions"};missionsPage.AddToClassList("journal-columns");panel.Add(missionsPage);
   list=new VisualElement{name="journal-list"};list.AddToClassList("journal-list");missionsPage.Add(list);
   var detail=new VisualElement{name="journal-detail"};detail.AddToClassList("journal-detail");missionsPage.Add(detail);
   title=Text(detail,"journal-title","journal-title");
   var metaRow=new VisualElement();metaRow.AddToClassList("journal-meta-row");detail.Add(metaRow);
   meta=Text(metaRow,"journal-meta","journal-meta");
   status=Text(metaRow,"journal-status","journal-status");
   Heading(detail,"BRIEFING");
   summary=Text(detail,"journal-summary","journal-summary");
   Heading(detail,"OBJECTIVES");
   steps=new VisualElement{name="journal-steps"};steps.AddToClassList("journal-steps");detail.Add(steps);
   nowHeading=Heading(detail,"NOW");
   now=Text(detail,"journal-now","journal-now");
   rewardHeading=Heading(detail,"REWARD");
   reward=Text(detail,"journal-reward","journal-reward");
   track=new Button(Track){name="journal-track",text="Track this mission · T"};track.AddToClassList("journal-track");detail.Add(track);
   empty=Text(detail,"journal-empty","journal-empty");empty.text="No missions yet. Linn is waiting on the hill.";
   notesPage=new VisualElement{name="journal-notes"};notesPage.AddToClassList("journal-notes");panel.Add(notesPage);
   notesText=Text(notesPage,"journal-notes-text","body-copy");
   panel.RegisterCallback<KeyDownEvent>(e=>{if(e.keyCode==KeyCode.T&&!notes){Track();e.StopPropagation();}},TrickleDown.TrickleDown);
  }
  static Label Text(VisualElement parent,string name,string cls){var l=new Label{name=name};l.AddToClassList(cls);parent.Add(l);return l;}
  static Label Heading(VisualElement parent,string text){var l=new Label(text);l.AddToClassList("small");l.AddToClassList("journal-heading");parent.Add(l);return l;}
  /// The journal opened: the tracked mission is selected and focused.
  public void Opened()
  {
   notes=false;signature=null;
   var tracked=journal?journal.Tracked:null;
   selected=tracked?.id??journal?.Missions.FirstOrDefault(m=>m.Active)?.id??journal?.Missions.FirstOrDefault()?.id;
   Refresh();
   panel.schedule.Execute(FocusSelected);
  }
  void FocusSelected(){var b=list.Q<Button>("journal-mission-"+selected);if(b!=null)b.Focus();else (notes?tabNotes:tabMissions).Focus();}
  public void ShowNotes(bool show){notes=show;Refresh();panel.schedule.Execute(()=>{if(notes)tabNotes.Focus();else FocusSelected();});}
  public void Select(string id){if(journal?.Find(id)==null)return;selected=id;Refresh();}
  public void Track(){if(journal!=null&&selected!=null&&journal.Track(selected))Refresh();}
  public void Refresh()
  {
   if(journal==null)return;
   tabMissions.EnableInClassList("active-tab",!notes);tabNotes.EnableInClassList("active-tab",notes);
   missionsPage.style.display=notes?DisplayStyle.None:DisplayStyle.Flex;notesPage.style.display=notes?DisplayStyle.Flex:DisplayStyle.None;
   notesText.text=session.catalog.notes;
   var missions=journal.Missions;
   if(selected==null||journal.Find(selected)==null)selected=missions.FirstOrDefault(m=>m.Active)?.id??missions.FirstOrDefault()?.id;
   string sig=string.Join(";",missions.Select(m=>m.id+":"+m.status+":"+m.title))+"|"+journal.TrackedId;
   if(sig!=signature)
   {
    signature=sig;var focused=panel.focusController?.focusedElement as VisualElement;bool listFocused=focused!=null&&list.Contains(focused);
    list.Clear();
    void Section(string heading,System.Collections.Generic.IEnumerable<Mission> items)
    {
     var group=items.ToList();if(group.Count==0)return;
     Heading(list,heading);
     foreach(var m in group)list.Add(Row(m));
    }
    Section("ACTIVE",missions.Where(m=>m.Active));
    Section("COMPLETED",missions.Where(m=>!m.Active));
    if(listFocused)panel.schedule.Execute(FocusSelected);
   }
   foreach(var b in list.Query<Button>(className:"journal-mission").ToList())b.EnableInClassList("selected",b.name=="journal-mission-"+selected);
   Detail(journal.Find(selected));
  }
  Button Row(Mission m)
  {
   string id=m.id;
   var b=new Button(()=>Select(id)){name="journal-mission-"+id};b.AddToClassList("journal-mission");
   b.EnableInClassList("complete",!m.Active);b.EnableInClassList("tracked",journal.TrackedId==id);
   var marker=new VisualElement{pickingMode=PickingMode.Ignore};marker.AddToClassList("journal-mission-marker");marker.AddToClassList("diamond");b.Add(marker);
   var copy=new VisualElement{pickingMode=PickingMode.Ignore};copy.AddToClassList("journal-mission-copy");b.Add(copy);
   var t=new Label(m.title){pickingMode=PickingMode.Ignore};t.AddToClassList("journal-mission-title");copy.Add(t);
   var a=new Label(journal.TrackedId==id?"TRACKED · "+m.giver:m.giver){pickingMode=PickingMode.Ignore};a.AddToClassList("journal-mission-area");copy.Add(a);
   b.RegisterCallback<FocusInEvent>(_=>{if(selected!=id){selected=id;foreach(var other in list.Query<Button>(className:"journal-mission").ToList())other.EnableInClassList("selected",other.name=="journal-mission-"+id);Detail(journal.Find(id));}});
   // double-click tracks
   b.RegisterCallback<ClickEvent>(e=>{if(e.clickCount==2){selected=id;Track();}});
   return b;
  }
  void Detail(Mission m)
  {
   bool any=m!=null;
   foreach(var e in new VisualElement[]{title,meta,status,summary,steps,track})e.style.display=any?DisplayStyle.Flex:DisplayStyle.None;
   empty.style.display=any?DisplayStyle.None:DisplayStyle.Flex;
   foreach(var h in panel.Query<Label>(className:"journal-heading").ToList())if(!list.Contains(h))h.style.display=any?DisplayStyle.Flex:DisplayStyle.None;
   if(!any)return;
   title.text=m.title;meta.text=$"{m.giver} · {m.area}";
   bool tracked=journal.TrackedId==m.id;
   status.text=!m.Active?"COMPLETE":tracked?"TRACKED":"ACTIVE";
   status.EnableInClassList("complete",!m.Active);status.EnableInClassList("tracked",tracked);
   summary.text=m.summary;
   steps.Clear();
   foreach(var s in m.steps)
   {
    var row=new VisualElement{pickingMode=PickingMode.Ignore};row.AddToClassList("journal-step");row.EnableInClassList("done",s.done);row.EnableInClassList("current",s.current);
    var mark=new VisualElement{pickingMode=PickingMode.Ignore};mark.AddToClassList("journal-step-mark");mark.AddToClassList("diamond");row.Add(mark);
    var l=new Label(s.text){pickingMode=PickingMode.Ignore};l.AddToClassList("journal-step-text");row.Add(l);
    steps.Add(row);
   }
   bool showNow=m.Active&&!string.IsNullOrEmpty(m.objective);
   now.text=showNow?m.objective+(m.target?$"\n{(m.targetLabel??"Marker")} · {Mathf.RoundToInt(Vector3.Distance(m.target.position,session.player.transform.position))} m · on your compass{(tracked?"":" once tracked")}":""):"";
   now.style.display=nowHeading.style.display=showNow?DisplayStyle.Flex:DisplayStyle.None;
   reward.text=m.reward??"";reward.style.display=rewardHeading.style.display=string.IsNullOrEmpty(m.reward)?DisplayStyle.None:DisplayStyle.Flex;
   track.style.display=m.Active?DisplayStyle.Flex:DisplayStyle.None;
   // an automatically tracked mission can be pinned (it then stays tracked until it is done)
   bool pinned=tracked&&journal.TrackedChosen;
   track.text=pinned?"Tracking this mission":tracked?"Keep tracking this mission · T":"Track this mission · T";
   track.SetEnabled(!pinned);
  }
 }
}
