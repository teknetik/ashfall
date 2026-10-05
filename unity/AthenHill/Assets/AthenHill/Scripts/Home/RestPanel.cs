using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// The bunk (5 Oct 2026): sleep until morning or evening, or rest a while. Any of them restores vitality and the weapon
 /// charge, saves, and makes Continue start at the bunk (GameSession.Rest).
 public sealed class RestPanel
 {
  public const float Morning=6.5f,Evening=18.5f;
  readonly VisualElement panel;
  readonly Label text;
  readonly Button morning;
  readonly GameSession session;
  public RestPanel(VisualElement panel,GameSession session)
  {
   this.panel=panel;this.session=session;
   text=new Label{name="rest-text"};text.AddToClassList("body-copy");panel.Add(text);
   var actions=new VisualElement{name="rest-actions"};actions.AddToClassList("rest-actions");panel.Add(actions);
   Button Choice(string name,string label,System.Action a){var b=new Button(a){name=name,text=label};b.AddToClassList("rest-choice");actions.Add(b);return b;}
   morning=Choice("rest-morning","Sleep until morning · 06:30",()=>session.Rest(Morning));
   Choice("rest-evening","Rest until evening · 18:30",()=>session.Rest(Evening));
   Choice("rest-short","Rest a while",()=>session.Rest(-1));
  }
  public void Opened()
  {
   var clock=Object.FindAnyObjectByType<CityTimeOfDay>();
   string time=clock?$"{Mathf.FloorToInt(clock.Hour):00}:{Mathf.FloorToInt(clock.Hour%1*60):00}":"";
   var combat=session.player?session.player.GetComponent<PlayerCombat>():null;
   string health=combat?$" Vitality {Mathf.CeilToInt(combat.Health.Current)} / {Mathf.RoundToInt(combat.Health.max)}.":"";
   text.text=$"A thin mattress on a welded frame, a blanket that still smells of caravan dust.{(time.Length>0?" It is "+time+".":"")}{health}\n\nResting restores your vitality and nano charge and saves your progress. From now on, Continue wakes you here.";
   panel.schedule.Execute(()=>morning.Focus());
  }
 }
}
