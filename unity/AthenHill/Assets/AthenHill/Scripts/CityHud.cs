using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 [RequireComponent(typeof(UIDocument))]
 public class CityHud:MonoBehaviour
 {
  public GameSession session;
  public Camera worldCamera;
  [Range(0,4)]public float tunnelSpeed=2;
  VisualElement root;
  readonly Dictionary<NpcAgent,Label> tags=new Dictionary<NpcAgent,Label>();
  CityState previous=CityState.Boot;
  void Start()
  {
   root=GetComponent<UIDocument>().rootVisualElement;
   Bind("close",session.Close);Bind("resume",session.Close);Bind("reset",session.ResetPlayer);
   Bind("inventory-button",()=>session.Open(CityState.Inventory));Bind("notes-button",()=>session.Open(CityState.Notes));Bind("pause-button",()=>session.Open(CityState.Paused));Bind("credits-button",()=>session.Open(CityState.Credits));Bind("interaction",session.Interact);
   Bind("quit",()=>Application.Quit());Show("quit",!Application.isEditor);
   Bind("mute",session.ToggleMute);Bind("reduced-motion",session.ToggleReducedMotion);
   for(int i=0;i<2;i++){int index=i;Bind("choice"+i,()=>session.Choose(index));}
   for(int i=0;i<3;i++){int index=i;Bind("buy"+i,()=>session.Trade(session.catalog.items[index].id,true));Bind("sell"+i,()=>session.Trade(session.catalog.items[index].id,false));Bind("node"+i,()=>session.SelectDestination(index));}
   for(int i=1;i<=6;i++){int slot=i;Bind("slot"+i,()=>session.Hotbar(slot));}
   foreach(var npc in session.npcs){var label=new Label(npc.definition.displayName+"\n"+npc.definition.role);label.AddToClassList("nametag");label.pickingMode=PickingMode.Ignore;root.Q("nametags").Add(label);tags.Add(npc,label);}
   session.Changed+=Refresh;Refresh();
  }
  void OnDestroy(){if(session)session.Changed-=Refresh;}
  void Bind(string name,Action action){root.Q<Button>(name).clicked+=action;}
  void Show(string name,bool show){root.Q(name).style.display=show?DisplayStyle.Flex:DisplayStyle.None;}
  void Text(string name,string value){root.Q<Label>(name).text=value;}
  public void Refresh()
  {
   if(root==null||session.Shop==null)return;
   bool modal=session.State!=CityState.Play;
   root.Q("top-actions").SetEnabled(!modal);root.Q("hotbar").SetEnabled(!modal);
   Show("shade",modal);Show("notice",!modal&&!string.IsNullOrEmpty(session.notice));Text("notice",session.notice);Text("modal-notice",session.notice);
   Text("objective",session.Objective);Text("progress",$"Conversations {session.Spoken.Count}/4 · Flask {(session.boughtFlask?"✓":"–")} · Scrap {(session.soldScrap?"✓":"–")} · Link {(session.linked?"✓":"–")}");
   root.Q<Button>("inventory-button").text=$"Inventory · {session.Shop.Credits} cr";
   Text("log",string.Join("\n",session.Log.TakeLast(4)));
   Show("dialogue-panel",session.State==CityState.Dialogue);Show("shop-panel",session.State==CityState.Shop);Show("grid-panel",session.State==CityState.Grid);Show("pause-panel",session.State==CityState.Paused);Show("text-panel",session.State==CityState.Inventory||session.State==CityState.Notes||session.State==CityState.Credits);
   Text("modal-title",session.State.ToString());Text("modal-subtitle","");
   if(session.State==CityState.Dialogue){Text("modal-title",session.ActiveNpc.definition.displayName);Text("modal-subtitle",session.Dialogue.title);Text("dialogue-text",session.Dialogue.text);for(int i=0;i<2;i++)root.Q<Button>("choice"+i).text=session.Dialogue.choices[i].label;}
   if(session.State==CityState.Shop)
   {
    Text("modal-title","Basic General");Text("modal-subtitle","Mira · Supplies and salvage");Text("shop-credit",$"Available balance: {session.Shop.Credits} credits");
    for(int i=0;i<3;i++){var item=session.catalog.items[i];Text("item"+i,$"{item.name} · {session.Shop.Quantity(item.id)} carried\n{item.description}");var b=root.Q<Button>("buy"+i);b.text=$"Buy · {item.buyPrice} cr";b.SetEnabled(session.Shop.Credits>=item.buyPrice);var s=root.Q<Button>("sell"+i);s.text=$"Sell · {item.sellPrice} cr";s.SetEnabled(session.Shop.Quantity(item.id)>0);}
   }
   if(session.State==CityState.Grid)
   {
    Text("modal-title","Sector lattice");Text("modal-subtitle","Lattice Jack · Athen Hill uplink");Text("grid-status",session.GridProgress<1?"Opening the connection…":"Select a destination to establish a link.");root.Q<ProgressBar>("grid-progress").value=session.GridProgress*100;
    Show("grid-nodes",session.GridProgress>=1);for(int i=0;i<3;i++){var n=session.catalog.destinations[i];root.Q<Button>("node"+i).text=n.name+"\n"+n.description;}
    Text("grid-selection",session.selectedDestination==""?"This city slice ends at the uplink.":"Link established. Your position in Athen Hill is unchanged.");
   }
   if(session.State==CityState.Paused){Text("modal-title","City paused");Text("modal-subtitle","Take your time. The hill will be here.");root.Q<Button>("mute").text=session.muted?"Unmute audio":"Mute audio";root.Q<Button>("reduced-motion").text="Reduced motion: "+(session.reducedMotion?"On":"Off");}
   if(session.State==CityState.Inventory){Text("modal-title","Field pack");Text("panel-text",$"{session.Shop.Credits} credits\n\n"+string.Join("\n\n",session.catalog.items.Select(i=>$"{i.name} · {session.Shop.Quantity(i.id)}\n{i.description}")));}
   if(session.State==CityState.Notes){Text("modal-title","City notes");Text("panel-text",session.Objective+"\n\n"+session.catalog.notes);}
   if(session.State==CityState.Credits){Text("modal-title","Credits and licences");Text("panel-text",session.catalog.credits?session.catalog.credits.text:"Credits unavailable.");}
   if(previous!=session.State){previous=session.State;if(modal)root.schedule.Execute(()=>root.Q<Button>(session.State==CityState.Dialogue?"choice0":"close").Focus());else root.focusController?.focusedElement?.Blur();}
  }
  void LateUpdate()
  {
   if(root==null||root.panel==null)return;
   bool tunnel=session.State==CityState.Grid&&session.GridProgress<1&&!session.reducedMotion;
   Show("tunnel",tunnel);
   if(tunnel)for(int i=0;i<4;i++){var ring=root.Q("tunnel-ring"+i);float phase=Mathf.Repeat(session.GridProgress*tunnelSpeed+i*.25f,1);float size=20+phase*480;ring.style.width=Length.Percent(size);ring.style.height=Length.Percent(size);ring.style.left=Length.Percent(50-size/2);ring.style.top=Length.Percent(50-size/2);ring.style.opacity=1-phase;}
   string prompt=session.Prompt;Show("interaction",!string.IsNullOrEmpty(prompt));root.Q<Button>("interaction").text=prompt;
   foreach(var pair in tags)
   {
    var world=pair.Key.transform.position+Vector3.up*2.15f;var p=worldCamera.WorldToViewportPoint(world);
    bool visible=session.State==CityState.Play&&p.z>0&&p.x>0&&p.x<1&&p.y>0&&p.y<1&&Vector3.Distance(world,session.player.transform.position)<34;
    pair.Value.style.display=visible?DisplayStyle.Flex:DisplayStyle.None;
    if(visible){var point=RuntimePanelUtils.CameraTransformWorldToPanel(root.panel,world,worldCamera);pair.Value.style.left=point.x-90;pair.Value.style.top=point.y-30;}
   }
  }
 }
}
