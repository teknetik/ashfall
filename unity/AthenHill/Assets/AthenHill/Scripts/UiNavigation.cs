using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// Keyboard navigation rules shared by the city windows. UI Toolkit already turns arrows/WASD into
 /// NavigationMoveEvents (via the Input System UI module), so lists and grids handle those events and never KeyDown
 /// as well: one key press is one step. Handled moves are withheld from the FocusController's own navigation.
 public static class UiNavigation
 {
  /// Columns of a wrapped grid, read from its laid-out cells (cells sharing the first cell's row). 1 when unknown.
  public static int Columns(IReadOnlyList<Rect> cells)
  {
   if(cells==null||cells.Count==0)return 1;
   float y=cells[0].y;if(float.IsNaN(y))return 1;
   int n=0;foreach(var r in cells){if(Mathf.Abs(r.y-y)<1)n++;else break;}
   return Mathf.Max(1,n);
  }
  /// One step in a reading-order grid. Left/Right move to the previous/next cell (continuing across rows); Up/Down move a
  /// whole row and stop at the edges (Down onto a shorter last row lands on its last cell). Returns index when blocked.
  public static int GridStep(int index,int count,int columns,NavigationMoveEvent.Direction direction)
  {
   if(count<=0)return -1;
   index=Mathf.Clamp(index,0,count-1);columns=Mathf.Max(1,columns);
   switch(direction)
   {
    case NavigationMoveEvent.Direction.Left:return Mathf.Max(0,index-1);
    case NavigationMoveEvent.Direction.Right:return Mathf.Min(count-1,index+1);
    case NavigationMoveEvent.Direction.Up:return index-columns>=0?index-columns:index;
    case NavigationMoveEvent.Direction.Down:
     if(index+columns<count)return index+columns;
     // Moving down from a row above a shorter last row lands on that row's last cell.
     return index/columns<(count-1)/columns?count-1:index;
    default:return index;
   }
  }
  /// Step in a vertical list; stops at both ends.
  public static int ListStep(int index,int count,int delta)=>count<=0?-1:Mathf.Clamp(index+delta,0,count-1);
  public static bool IsArrow(NavigationMoveEvent.Direction d)=>d==NavigationMoveEvent.Direction.Up||d==NavigationMoveEvent.Direction.Down||d==NavigationMoveEvent.Direction.Left||d==NavigationMoveEvent.Direction.Right;
  /// The event was handled here: no other handler, and no FocusController navigation, acts on it.
  public static void Consume(EventBase e,VisualElement anyInPanel)
  {
   anyInPanel?.panel?.focusController?.IgnoreEvent(e);
   e.StopPropagation();
  }
  /// Next index when Tab (forward) or Shift+Tab cycles through count stops from index (-1 = none focused yet).
  public static int Cycle(int index,int count,bool forward)
  {
   if(count<=0)return -1;
   if(index<0||index>=count)return forward?0:count-1;
   return forward?(index+1)%count:(index-1+count)%count;
  }
  /// Tab stops inside scope in tree order: focusable, enabled, displayed controls with a non-negative tab index —
  /// never scrollbars or the insides of a field that delegates its focus.
  public static List<VisualElement> TabStops(VisualElement scope)
  {
   var stops=new List<VisualElement>();
   if(scope==null)return stops;
   scope.Query<VisualElement>().ForEach(v=>{if(v!=scope&&IsTabStop(v,scope))stops.Add(v);});
   return stops;
  }
  static bool IsTabStop(VisualElement v,VisualElement scope)
  {
   if(!v.focusable||v.tabIndex<0||!v.enabledInHierarchy||v is ScrollView||v is Scroller)return false;
   for(var e=v;e!=null&&e!=scope.parent;e=e.parent)
   {
    if(!e.visible||e.resolvedStyle.display==DisplayStyle.None)return false;
    if(e!=v&&(e is Scroller||e.focusable&&e.delegatesFocus))return false;
   }
   return true;
  }
  /// Whenever keyboard focus enters the scroll view's content, scroll the focused element into view (after layout).
  public static void KeepFocusVisible(ScrollView scroll)
  {
   if(scroll==null)return;
   scroll.RegisterCallback<FocusInEvent>(e=>
   {
    if(e.target is VisualElement target&&target!=scroll&&scroll.contentContainer.Contains(target))
     scroll.schedule.Execute(()=>{if(target.panel!=null&&scroll.contentContainer.Contains(target))scroll.ScrollTo(target);});
   });
  }
 }
}
