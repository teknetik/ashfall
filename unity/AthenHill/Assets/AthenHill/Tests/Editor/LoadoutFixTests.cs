using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// 20 Nov 2026 playtest fixes (art/loadout_fix_20261120): the EYE implant slot, body-map leaders that end on the body
 /// part their slot names at every size, and hotbar strip reordering with its save.
 public class LoadoutFixTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CharacterCatalog Character()=>AssetDatabase.LoadAssetAtPath<CharacterCatalog>("Assets/AthenHill/Resources/CharacterCatalog.asset");
  static CraftingCatalog Crafting()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);

  // ------------------------------------------------------------------ eye slot
  [Test] public void ImplantsHaveAnEyeSlotAfterTheHeadAndNothingIsMovedIntoIt()
  {
   var c=Character();var ids=c.slots.Select(s=>s.id).ToList();
   Assert.That(ids.Count(i=>i=="implant_eye"),Is.EqualTo(1),"one eye slot (LoadoutFixPass20261120 install)");
   Assert.That(ids.IndexOf("implant_eye"),Is.EqualTo(ids.IndexOf("implant_head")+1));
   var eye=c.slots.First(s=>s.id=="implant_eye");Assert.That(eye.label,Is.EqualTo("Eye"));Assert.That(eye.section,Is.EqualTo("IMPLANTS"));
   Assert.That(c.equipment.Where(e=>e.slots.Contains("implant_eye")).Select(e=>e.itemId),Contains.Item("optic_suite_mk1"),"Warden Optic Suite Mk I fits the eye slot");
   Assert.That(c.Equipment("targeting_implant_mk1").slots,Is.EqualTo(new[]{"implant_head"}),"the neural targeting implant stays in the head");
  }

  [Test] public void ASaveFromBeforeTheEyeSlotLoadsWithTheEyeEmpty()
  {
   var pack=new ShopModel(City().items);var model=new CharacterModel(Character(),pack);
   var old=new CharacterState{version=2,level=2,equipped=new[]{new SlotEntry{slot="implant_head",itemId="targeting_implant_mk1"},new SlotEntry{slot="armour_chest",itemId="field_vest"}}};
   var skipped=model.Restore(old);
   Assert.That(skipped,Is.Empty);
   Assert.That(model.Equipped("implant_head"),Is.EqualTo("targeting_implant_mk1"));Assert.That(model.Equipped("armour_chest"),Is.EqualTo("field_vest"));
   Assert.That(model.Equipped("implant_eye"),Is.Null);
   const string json="{\"version\":4,\"savedUtc\":\"2026-11-19T12:00:00Z\",\"build\":\"qa\",\"credits\":10,\"character\":{\"version\":2,\"level\":1,\"equipped\":[{\"slot\":\"implant_head\",\"itemId\":\"targeting_implant_mk1\"}]},\"hotbar\":[{\"slot\":5,\"itemId\":\"medkit\"},{\"slot\":3,\"itemId\":\"nano_cell\"}]}";
   Assert.That(WardSaveFile.TryParse(json,out var data,out var error),error);
   Assert.That(data.version,Is.EqualTo(4));
   Assert.That(new CharacterModel(Character(),new ShopModel(City().items)).Restore(data.character),Is.Empty);
  }

  // ------------------------------------------------------------------ body map anchors
  // Body-part regions on the 1024 x 1536 figure (x0, y0, width, height), measured on a 25 px grid over ImplantBody.png.
  static readonly Dictionary<string,Rect[]> PartRegions=new Dictionary<string,Rect[]>
  {
   {"head",new[]{Rect.MinMaxRect(430,40,595,235)}},
   {"eye",new[]{Rect.MinMaxRect(465,110,505,150),Rect.MinMaxRect(520,110,562,150)}},
   {"arms",new[]{Rect.MinMaxRect(300,320,380,540),Rect.MinMaxRect(640,320,725,540)}},
   {"chest",new[]{Rect.MinMaxRect(470,300,555,470)}},
   {"wrist",new[]{Rect.MinMaxRect(205,700,265,760),Rect.MinMaxRect(760,700,820,760)}},
   {"waist",new[]{Rect.MinMaxRect(440,540,585,640)}},
   {"hand",new[]{Rect.MinMaxRect(150,730,265,880),Rect.MinMaxRect(760,730,880,880)}},
   {"hands",new[]{Rect.MinMaxRect(150,730,265,880),Rect.MinMaxRect(760,730,880,880)}},
   {"legs",new[]{Rect.MinMaxRect(370,760,460,1060),Rect.MinMaxRect(570,760,660,1060)}},
   {"feet",new[]{Rect.MinMaxRect(320,1340,470,1500),Rect.MinMaxRect(580,1340,720,1500)}},
   {"storage",new[]{Rect.MinMaxRect(560,270,700,360),Rect.MinMaxRect(330,270,465,360)}},
  };
  [Test] public void EveryBodyMapSlotHasAnAnchorOnTheFigure()
  {
   var tex=new Texture2D(2,2);
   Assert.That(tex.LoadImage(File.ReadAllBytes("Assets/AthenHill/Resources/UI/ImplantBody.png")));
   Assert.That(tex.width/(float)tex.height,Is.EqualTo(AnatomyLayout.ImageAspect).Within(.001f));
   try
   {
    foreach(bool implants in new[]{true,false})
     foreach(var a in AnatomyLayout.Anchors(implants))
     {
      string what=$"{(implants?"implant":"armour")} {a.part} anchor";
      // Brightness cannot tell the figure from its glow: the X-ray is translucent (cranium interior luma ~104, eye
      // socket ~75) and the glow beside the head reaches ~100. So the test checks what it means: the anchor lies in the
      // measured region of the body part it names (image pixels, measured on a 25 px grid, the same table as
      // unity/tools/capture_loadout_native.py)…
      var px=new Vector2(a.uv.x*tex.width,a.uv.y*tex.height);
      Assert.That(PartRegions.TryGetValue(a.part,out var regions),what+" has a measured region");
      Assert.That(regions.Any(r=>r.Contains(px)),what+$" at {px} lies on the {a.part}");
      // …and is not in the black background beyond the glow (background ~10–56 there; the dimmest anchor, the eye
      // socket, is ~75).
      float sum=0;int n=0;int cx=Mathf.RoundToInt(px.x),cy=Mathf.RoundToInt(tex.height-px.y);
      for(int y=-3;y<=3;y++)for(int x=-3;x<=3;x++){sum+=tex.GetPixel(cx+x,cy+y).grayscale;n++;}
      Assert.That(sum/n*255,Is.GreaterThan(60),what+" is not in the dark background");
      Assert.That(a.uv.x,Is.InRange(AnatomyLayout.FigureLeft,AnatomyLayout.FigureRight));
     }
   }
   finally{Object.DestroyImmediate(tex);}
   var c=Character();
   foreach(var s in c.slots.Where(s=>s.section=="IMPLANTS"||s.section=="ARMOUR"||s.section=="STORAGE"))
    Assert.That(AnatomyLayout.TryAnchor(s.section=="IMPLANTS",s.id,out _),"anchor for "+s.id);
   // Paired parts use the side of the figure their box is on.
   foreach(bool implants in new[]{true,false})
    foreach(var a in AnatomyLayout.Anchors(implants))
     if(Mathf.Abs(a.uv.x-.5f)>.02f)Assert.That(a.uv.x>.5f,Is.EqualTo(a.right),a.part+" anchor is on its box's side");
  }

  static List<(string id,AnatomyLayout.Anchor anchor)> Slots(bool implants)=>Character().slots
   .Where(s=>implants?s.section=="IMPLANTS":s.section=="ARMOUR"||s.section=="STORAGE").Select((s,i)=>(s.id,AnatomyLayout.AnchorFor(implants,s.id,i,99))).ToList();

  [Test] public void LeadersEndOnTheirAnchorsAndNeverCrossABoxAtAnySize()
  {
   foreach(bool implants in new[]{true,false})
    foreach(float width in new[]{560f,650f,760f,920f,1200f,1600f})
     foreach(float height in new[]{330f,420f,520f,700f,900f})
     {
      var slots=Slots(implants);var r=AnatomyLayout.Arrange(slots,width,height);string at=$"{(implants?"implants":"armour")} {width}x{height}";
      Assert.That(r.mapWidth+AnatomyLayout.MapMargin+AnatomyLayout.InspectorMinimum,Is.LessThanOrEqualTo(width+.01f),"the inspector keeps its width "+at);
      Assert.That(r.image.width/r.image.height,Is.EqualTo(AnatomyLayout.ImageAspect).Within(.001f),"the figure keeps its proportions "+at);
      Assert.That(r.image.height,Is.LessThanOrEqualTo(height+.01f));
      for(int i=0;i<slots.Count;i++)
      {
       var p=r.slots[i];var a=slots[i].anchor;
       Assert.That(Vector2.Distance(p.node,new Vector2(r.image.x+a.uv.x*r.image.width,r.image.y+a.uv.y*r.image.height)),Is.LessThan(.01f),"the dot is the anchor "+p.id+" "+at);
       Assert.That(p.box.yMin,Is.GreaterThanOrEqualTo(-.01f));Assert.That(p.box.yMax,Is.LessThanOrEqualTo(height+.01f),p.id+" box inside the map "+at);
       Assert.That(p.box.xMin,Is.GreaterThanOrEqualTo(-.01f));Assert.That(p.box.xMax,Is.LessThanOrEqualTo(r.mapWidth+.01f));
       Assert.That(p.leaderStart.x,Is.EqualTo(p.right?p.box.xMin:p.box.xMax).Within(.01f),"the leader leaves the box edge facing the figure");
       foreach(var q in r.slots)
       {
        Assert.That(q.box.Contains(p.node),Is.False,$"{p.id}'s dot is not under {q.id}'s box {at}");
        if(q==p)continue;
        Assert.That(AnatomyLayout.SegmentEntersRect(p.leaderStart,p.node,q.box),Is.False,$"{p.id}'s leader does not cross {q.id}'s box {at}");
        Assert.That(q.box.Overlaps(p.box),Is.False,$"{p.id} and {q.id} boxes do not overlap {at}");
        Assert.That(AnatomyLayout.SegmentsCross(p.leaderStart,p.node,q.leaderStart,q.node),Is.False,$"{p.id} and {q.id} leaders do not cross {at}");
       }
      }
     }
  }

  [Test] public void BodyMapBuildsOneDotPerSlotAndHidesTheBareSelectionLabel()
  {
   var go=new GameObject("anatomy ui test");go.SetActive(false);
   try
   {
    var session=go.AddComponent<GameSession>();session.catalog=City();
    var pack=new ShopModel(City().items);var model=new CharacterModel(Character(),pack);Set(session,"Shop",pack);Set(session,"Character",model);
    var root=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
    CharacterLoadoutPanel panel=null;panel=new CharacterLoadoutPanel(root,session,null,()=>null,()=>panel.Refresh());
    foreach(var section in new[]{"IMPLANTS","ARMOUR"})
    {
     typeof(CharacterLoadoutPanel).GetField("section",Any).SetValue(panel,section);panel.Refresh();
     var ids=Character().slots.Where(s=>s.section==section||section=="ARMOUR"&&s.section=="STORAGE").Select(s=>s.id).ToList();
     foreach(var id in ids){Assert.That(root.Q("equipment-"+id),Is.Not.Null,id);Assert.That(root.Q("anatomy-node-"+id),Is.Not.Null,id+" dot");}
     Assert.That(root.Query(className:"anatomy-node").ToList().Count,Is.EqualTo(ids.Count));
     Assert.That(root.Q("anatomy-leaders"),Is.Not.Null);
     Assert.That(root.Q("equipment-selection").style.display.value,Is.EqualTo(DisplayStyle.None),"no bare slot name under the body map");
    }
    typeof(CharacterLoadoutPanel).GetField("selectedSlot",Any).SetValue(panel,"implant_eye");
    typeof(CharacterLoadoutPanel).GetField("section",Any).SetValue(panel,"IMPLANTS");typeof(CharacterLoadoutPanel).GetField("signature",Any).SetValue(panel,null);panel.Refresh();
    var copy=string.Join("\n",root.Q("equipment-inspector").Query<Label>().ToList().Select(l=>l.text));
    Assert.That(copy,Does.Contain("EYE").And.Contain("fits the eye slot"),"the empty eye slot says what goes there");
    typeof(CharacterLoadoutPanel).GetField("section",Any).SetValue(panel,"SECONDARY");typeof(CharacterLoadoutPanel).GetField("signature",Any).SetValue(panel,null);panel.Refresh();
    Assert.That(root.Q<Label>("equipment-selection").text,Does.Contain(" · "),"the weapon page's selection line names the slot and its contents");
   }
   finally{Object.DestroyImmediate(go);}
  }

  // ------------------------------------------------------------------ hotbar reordering
  [Test] public void HotbarCellsMoveAndSwapButOneAndTwoStayFixed()
  {
   var bar=new HotbarModel(id=>id=="medkit"||id=="nano_cell"||id=="trauma_kit");
   Assert.That(bar.Swap(3,5),"a cell dragged onto an empty cell moves");
   Assert.That(bar.Item(3),Is.Null);Assert.That(bar.Item(5),Is.EqualTo("medkit"));
   Assert.That(bar.Swap(4,5),"onto a full cell swaps");Assert.That(bar.Item(5),Is.EqualTo("nano_cell"));Assert.That(bar.Item(4),Is.EqualTo("medkit"));
   Assert.That(bar.Swap(4,1),Is.False);Assert.That(bar.Swap(2,7),Is.False,"1 and 2 hold the weapons");
   var restored=new HotbarModel(id=>id=="medkit"||id=="nano_cell");restored.Restore(bar.Capture());
   Assert.That(restored.Item(4),Is.EqualTo("medkit"));Assert.That(restored.Item(5),Is.EqualTo("nano_cell"));Assert.That(restored.Item(3),Is.Null,"the order survives the save");
  }

  [Test] public void PackStripMovesClearsAndExplainsTheFixedWeaponCells()
  {
   var go=new GameObject("strip rig");go.SetActive(false);
   try
   {
    var session=go.AddComponent<GameSession>();session.catalog=City();var crafting=go.AddComponent<CraftingSession>();crafting.data=Crafting();
    var player=new GameObject("combat");player.transform.SetParent(go.transform);var combat=player.AddComponent<PlayerCombat>();combat.hasPistol=true;crafting.combat=combat;
    var pack=new ShopModel(City().items);var model=new CraftingModel(Crafting(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",CityState.Inventory);Set(crafting,"Model",model);Set(crafting,"Session",session);combat.BindLoadout(model.Loadout);
    var root=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
    var icons=new HashSet<string>(City().items.Where(i=>!string.IsNullOrEmpty(i.icon)).Select(i=>i.icon).Concat(new[]{"pack-icon","pistol-icon"}));
    var panel=new PackPanel(root,session,crafting,null,icons);panel.Opened();
    Assert.That(root.Q<Label>("pack-hotbar-help").text,Does.Contain("reorder").And.Contain("1 and 2 follow your weapons"));
    Assert.That(root.Q("packbar-slot1").ClassListContains("packbar-fixed")&&root.Q("packbar-slot2").ClassListContains("packbar-fixed"));
    Assert.That(root.Q("packbar-slot3").ClassListContains("packbar-fixed"),Is.False);
    Assert.That(panel.MoveHotbar(3,6));Assert.That(session.Quickbar.Item(6),Is.EqualTo("medkit"));Assert.That(session.Quickbar.Item(3),Is.Null);
    Assert.That(root.Q<Button>("packbar-slot6").ClassListContains("empty-slot"),Is.False,"the strip redraws");
    Assert.That(root.Q<Button>("packbar-slot3").ClassListContains("empty-slot"));
    Assert.That(panel.MoveHotbar(6,1),Is.False);Assert.That(session.notice,Does.Contain("1 and 2"));
    Assert.That(panel.ClearHotbar(6));Assert.That(session.Quickbar.Item(6),Is.Null);
    Assert.That(root.Query(className:"equipment-drag-ghost").ToList(),Is.Empty);
   }
   finally{Object.DestroyImmediate(go);}
  }
 }
}
