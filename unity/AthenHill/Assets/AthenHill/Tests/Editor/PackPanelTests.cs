using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// Field pack after the user's Ark reference (30 Sep 2026): pack grid with tabs, filters and search | colonist loadout
 /// and stats | colonist view. Built from the real UXML and catalogs; the colonist view isolates the player per pass.
 public class PackPanelTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static VisualElement Hud()=>AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
  static HashSet<string> Icons()=>new HashSet<string>(City().items.Where(i=>!string.IsNullOrEmpty(i.icon)).Select(i=>i.icon).Concat(new[]{"pack-icon","pistol-icon"}));
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public ShopModel pack;public CraftingModel model;
   public Rig(bool pistol=true)
   {
    go=new GameObject("pack rig");go.SetActive(false);
    session=go.AddComponent<GameSession>();session.catalog=City();crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    var player=new GameObject("combat");player.transform.SetParent(go.transform);combat=player.AddComponent<PlayerCombat>();combat.hasPistol=pistol;crafting.combat=combat;
    pack=new ShopModel(City().items);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",CityState.Inventory);
    Set(crafting,"Model",model);Set(crafting,"Session",session);combat.BindLoadout(model.Loadout);
   }
   public void Grant(string id,int n){Assert.That(pack.Grant(id,n,0,out var message),message);}
   public void Dispose(){Object.DestroyImmediate(go);Time.timeScale=1;}
  }
  static List<string> Tiles(VisualElement root)=>root.Query<Button>(className:"inventory-tile").ToList().Select(b=>b.name).ToList();

  [Test] public void CategoriesAndSearchOnlyUseCatalogTagsAndNames()
  {
   var items=City().items;var shop=new ShopModel(items);
   foreach(var id in new[]{"scrap_alloy","grip_stabilised_pistol","alloy_plate","water_flask"})shop.Grant(id,1,0,out _);
   string[] Ids(string category,string search)=>InventoryView.Items(items,shop,InventoryView.FindCategory(category),search).Select(x=>x.id).ToArray();
   Assert.That(Ids("mods",""),Is.EqualTo(new[]{"grip_stabilised_pistol"}));
   Assert.That(Ids("refined",null),Is.EqualTo(new[]{"alloy_plate"}));
   Assert.That(Ids("supplies",""),Does.Contain("water_flask").And.Not.Contain("scrap_alloy"));
   Assert.That(Ids("all","ALLOY"),Is.EqualTo(new[]{"scrap_alloy","alloy_plate"}),"search ignores case and keeps catalog order");
   Assert.That(Ids("salvage","  alloy "),Is.EqualTo(new[]{"scrap_alloy"}),"search trims");
   Assert.That(InventoryView.FindCategory("nonsense").id,Is.EqualTo("all"));
   foreach(var c in InventoryView.Categories.Where(c=>c.tag!=null))Assert.That(items.Any(i=>i.HasTag(c.tag)),c.tag+" is a real catalog tag");
  }

  [Test] public void PackLayoutHasThreeColumnsAndDetailsTakeTheViewsPlace()
  {
   var root=Hud();
   var content=root.Q("inventory-content");
   Assert.That(content.Children().Select(c=>c.name),Is.EqualTo(new[]{"pack-col","you-col","preview-col","inventory-details"}));
   foreach(var name in new[]{"pack-tab-items","pack-tab-schematics","details-close"})Assert.That(root.Q<Button>(name),Is.Not.Null,name);
   Assert.That(root.Q<TextField>("pack-search"),Is.Not.Null);
   foreach(var name in new[]{"pack-filters","inventory-grid","inventory-overview","loadout-left","loadout-right","colonist-facts","you-stats","preview-view","you-progress-fill"})Assert.That(root.Q(name),Is.Not.Null,name);
   Assert.That(root.Q("pack-col").Contains(root.Q("inventory-scroll")));
   var uss=System.IO.File.ReadAllText("Assets/AthenHill/UI/CityHUD.uss");
   Assert.That(uss,Does.Contain("#modal.pack-modal"));
   Assert.That(AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/AthenHill/UI/Art/preview-grid.png"),Is.Not.Null);
  }

  [Test] public void GridFiltersSearchesAndCompletesItsRows()
  {
   using var rig=new Rig();
   foreach(var (id,n) in new[]{("scrap_alloy",4),("droid_servo_damaged",2),("grip_stabilised_pistol",1),("alloy_plate",3),("lattice_shard",1)})rig.Grant(id,n);
   var root=Hud();var panel=new PackPanel(root,rig.session,rig.crafting,null,Icons());
   panel.Opened();
   var carried=InventoryView.Items(City().items,rig.pack).Select(i=>"inv-"+i.id).ToList();
   Assert.That(Tiles(root),Is.EqualTo(carried),"one cell per carried item, catalog order");
   int cells=root.Query(className:"pack-cell").ToList().Count+carried.Count;
   Assert.That(cells,Is.GreaterThanOrEqualTo(PackPanel.MinimumCells));Assert.That(cells%panel.Columns(),Is.Zero,"empty cells complete the last row");
   Assert.That(root.Query<Button>(className:"pack-chip").ToList().Count,Is.EqualTo(InventoryView.Categories.Length));
   var shard=root.Q<Button>("inv-lattice_shard");
   Assert.That(shard.ClassListContains("tile-rare"));Assert.That(shard.Q<Label>(className:"inventory-tile-qty").text,Is.EqualTo("×1"));
   Assert.That(shard.Q<Label>(className:"inventory-tile-name").text,Is.EqualTo("Quantum Lattice Shard"));
   panel.SetFilter("mods");
   Assert.That(Tiles(root),Is.EqualTo(new[]{"inv-grip_stabilised_pistol"}));
   Assert.That(root.Q<Label>("pack-filter-name").text,Is.EqualTo("MODS"));
   Assert.That(root.Q<Button>("pack-filter-mods").ClassListContains("active-chip"));
   panel.SetFilter("all");panel.SetSearch("alloy");
   Assert.That(Tiles(root),Is.EqualTo(new[]{"inv-scrap_alloy","inv-alloy_plate"}));
   Assert.That(root.Q<Label>("pack-summary").text,Does.StartWith("2 of "));
   panel.SetSearch("no such thing");
   Assert.That(Tiles(root),Is.Empty);
   Assert.That(root.Q("inventory-empty").style.display.value,Is.EqualTo(DisplayStyle.Flex));
   Assert.That(root.Q<Label>("inventory-empty-title").text,Is.EqualTo("Nothing here matches."));
   panel.SetSearch("");
   Assert.That(Tiles(root),Is.EqualTo(carried));
   // The selected-item strip shows catalog facts only.
   Assert.That(panel.SelectedKey,Is.EqualTo(carried[0]));
   Assert.That(root.Q<Label>("inventory-overview-name").text,Is.EqualTo(City().items.First(i=>"inv-"+i.id==carried[0]).name));
   Assert.That(root.Q<Label>("inventory-overview-quantity").text,Does.Not.Contain("WEIGHT"));
  }

  [Test] public void SchematicsTabListsKnownRecipesWithTheirParts()
  {
   using var rig=new Rig();
   var root=Hud();var panel=new PackPanel(root,rig.session,rig.crafting,null,Icons());
   panel.Opened();
   panel.SetTab(PackPanel.Tab.Schematics);
   Assert.That(Tiles(root),Is.EqualTo(new[]{"sch-recipe_field_rifle","sch-recipe_rifle_precision_barrel"}));
   Assert.That(rig.model.Unlock("recipe_alloy_plate"));Assert.That(rig.model.Unlock("recipe_grip_stabilised_pistol"));
   panel.Refresh();
   Assert.That(Tiles(root),Is.EqualTo(new[]{"sch-recipe_alloy_plate","sch-recipe_grip_stabilised_pistol","sch-recipe_field_rifle","sch-recipe_rifle_precision_barrel"}));
   Assert.That(root.Q<Button>("sch-recipe_alloy_plate").ClassListContains("short"),"no parts carried");
   Assert.That(root.Q<Label>("inventory-overview-description").text,Does.StartWith("Parts: ").And.Contain("workbench at Salvage"));
   Assert.That(root.Query<Button>(className:"pack-chip").ToList().Select(b=>b.text),Is.EqualTo(new[]{"ALL","COMPONENTS","MARK I","MARK II","WEAPONS","WEAPON MODS"}));
   panel.SetFilter("MarkI");
   Assert.That(Tiles(root),Is.EqualTo(new[]{"sch-recipe_grip_stabilised_pistol"}));
   panel.SetTab(PackPanel.Tab.Items);
   Assert.That(root.Query<Button>(className:"pack-chip").ToList().Count,Is.EqualTo(InventoryView.Categories.Length));
  }

  [Test] public void LoadoutShowsTheSidearmFittedModsAndPistolStats()
  {
   using var rig=new Rig();
   var root=Hud();var panel=new PackPanel(root,rig.session,rig.crafting,null,Icons());
   panel.Opened();
   var slots=new[]{"sidearm"}.Concat(rig.model.Loadout.Slots).ToList();
   foreach(var slot in slots)Assert.That(root.Q("pack-slot-"+slot),Is.Not.Null,slot);
   Assert.That(root.Q("loadout-left").childCount+root.Q("loadout-right").childCount,Is.EqualTo(slots.Count));
   Assert.That(root.Q("pack-slot-sidearm").ClassListContains("empty"),Is.False,"the pistol is carried");
   Assert.That(root.Q("pack-slot-grip").ClassListContains("empty"));
   var statCells=root.Q("you-pistol-stats").Children().ToList();
   Assert.That(statCells.Count,Is.EqualTo(Data().statLabels.Length));
   var recoil=root.Q("you-stat-recoil");
   Assert.That(recoil.Q<Label>(className:"you-stat-delta").text,Is.EqualTo("base"));
   rig.Grant("grip_stabilised_pistol",1);
   Assert.That(rig.model.TryFit("grip_stabilised_pistol",out var reason),reason);
   panel.Refresh();
   Assert.That(root.Q("pack-slot-grip").ClassListContains("empty"),Is.False);
   var label=Data().statLabels.First(s=>s.stat=="recoil");
   Assert.That(recoil.Q<Label>(className:"you-stat-value").text,Is.EqualTo(CraftingText.FormatStat(label,rig.model.Loadout.Stats.recoil)));
   Assert.That(recoil.Q<Label>(className:"you-stat-delta").ClassListContains("better"),"less recoil is better");
   Assert.That(root.Q<Label>("colonist-mods").text,Is.EqualTo($"1 / {rig.model.Loadout.Slots.Count}"));
   Assert.That(root.Q<Label>("you-progress-label").text,Is.EqualTo("CITY VISIT"));
  }

  [Test] public void WithoutAPistolTheLoadoutSaysSo()
  {
   using var rig=new Rig(false);
   var root=Hud();var panel=new PackPanel(root,rig.session,rig.crafting,null,Icons());
   panel.Opened();
   Assert.That(root.Q("pack-slot-sidearm").ClassListContains("empty"));
   Assert.That(root.Q("you-pistol-stats").style.display.value,Is.EqualTo(DisplayStyle.None));
   Assert.That(root.Q<Label>(className:"you-stat-note").style.display.value,Is.EqualTo(DisplayStyle.Flex));
  }

  [Test] public void DetailsReplaceTheColonistView()
  {
   using var rig=new Rig();rig.Grant("lattice_shard",1);
   var root=Hud();var panel=new PackPanel(root,rig.session,rig.crafting,null,Icons());
   panel.Opened();
   Assert.That(root.Q("preview-col").style.display.value,Is.EqualTo(DisplayStyle.Flex));
   Assert.That(root.Q("preview-fallback").style.display.value,Is.EqualTo(DisplayStyle.Flex),"no preview rig: the insignia stands in");
   rig.session.OpenItemDetails("lattice_shard");panel.Refresh();
   Assert.That(root.Q("inventory-details").style.display.value,Is.EqualTo(DisplayStyle.Flex));
   Assert.That(root.Q("preview-col").style.display.value,Is.EqualTo(DisplayStyle.None));
   Assert.That(root.Q<Label>("details-title").ClassListContains("rarity-rare"));
   Assert.That(root.Q<Label>("details-prices").text,Is.EqualTo("Rare part · neither Mira nor Brann will trade it"));
   rig.session.CloseItemDetails();panel.Refresh();
   Assert.That(root.Q("inventory-details").style.display.value,Is.EqualTo(DisplayStyle.None));
   Assert.That(root.Q("preview-col").style.display.value,Is.EqualTo(DisplayStyle.Flex));
  }

  [Test] public void ColonistViewIsolatesThePlayerOnlyForItsOwnPass()
  {
   var go=new GameObject("preview rig");RenderTexture texture=null;
   try
   {
    var player=new GameObject("player");player.transform.SetParent(go.transform);var motor=player.AddComponent<PlayerMotor>();
    var body=GameObject.CreatePrimitive(PrimitiveType.Capsule);body.transform.SetParent(player.transform);var bodyRenderer=body.GetComponent<Renderer>();
    var arms=GameObject.CreatePrimitive(PrimitiveType.Cube);arms.transform.SetParent(player.transform);arms.layer=9;
    var proxy=GameObject.CreatePrimitive(PrimitiveType.Cylinder);proxy.transform.SetParent(player.transform);proxy.GetComponent<Renderer>().shadowCastingMode=ShadowCastingMode.ShadowsOnly;
    var sparks=new GameObject("sparks");sparks.transform.SetParent(player.transform);sparks.AddComponent<ParticleSystem>();
    var sun=new GameObject("sun").AddComponent<Light>();sun.transform.SetParent(go.transform);sun.type=LightType.Directional;
    var lamp=new GameObject("lamp").AddComponent<Light>();lamp.transform.SetParent(go.transform);lamp.type=LightType.Point;lamp.range=4;lamp.transform.position=new Vector3(2,2,0);
    var farLamp=new GameObject("far lamp").AddComponent<Light>();farLamp.transform.SetParent(go.transform);farLamp.type=LightType.Point;farLamp.range=4;farLamp.transform.position=new Vector3(40,2,0);
    var camGo=new GameObject("preview camera");camGo.transform.SetParent(go.transform);var cam=camGo.AddComponent<Camera>();
    var key=new GameObject("key").AddComponent<Light>();key.transform.SetParent(camGo.transform);key.enabled=false;
    var preview=go.AddComponent<CharacterPreview>();
    preview.player=motor;preview.previewCamera=cam;preview.studioLights=new[]{key};preview.muteLights=new[]{sun};preview.resolution=new Vector2Int(64,96);
    preview.SetActive(true);
    bodyRenderer.shadowCastingMode=ShadowCastingMode.ShadowsOnly; // first person hides the colonist after the view opened
    Assert.That(cam.enabled);Assert.That(cam.cullingMask,Is.EqualTo(1<<preview.previewLayer));Assert.That(preview.Texture,Is.Not.Null);
    Assert.That(Vector3.Distance(cam.transform.position,player.transform.position),Is.GreaterThan(preview.distance-.01f));
    var begin=typeof(CharacterPreview).GetMethod("Begin",Any);var end=typeof(CharacterPreview).GetMethod("End",Any);
    var other=new GameObject("world camera");other.transform.SetParent(go.transform);var world=other.AddComponent<Camera>();
    begin.Invoke(preview,new object[]{default(ScriptableRenderContext),world});
    Assert.That(body.layer,Is.EqualTo(0),"other cameras never see the swap");Assert.That(sun.enabled);Assert.That(key.enabled,Is.False);
    begin.Invoke(preview,new object[]{default(ScriptableRenderContext),cam});
    Assert.That(body.layer,Is.EqualTo(preview.previewLayer));Assert.That(arms.layer,Is.EqualTo(9),"first-person arms stay out");
    Assert.That(bodyRenderer.shadowCastingMode,Is.EqualTo(ShadowCastingMode.On),"a first-person-hidden colonist shows whole");
    Assert.That(sun.enabled,Is.False);Assert.That(key.enabled);
    Assert.That(proxy.layer,Is.EqualTo(0),"shadow-only proxies stay out");Assert.That(sparks.layer,Is.EqualTo(0),"effects stay out");
    Assert.That(lamp.enabled,Is.False,"a lamp reaching the colonist is muted for the pass");Assert.That(farLamp.enabled,"distant lamps are untouched");
    end.Invoke(preview,new object[]{default(ScriptableRenderContext),cam});
    Assert.That(body.layer,Is.EqualTo(0));Assert.That(bodyRenderer.shadowCastingMode,Is.EqualTo(ShadowCastingMode.ShadowsOnly));
    Assert.That(sun.enabled);Assert.That(key.enabled,Is.False);Assert.That(lamp.enabled);
    preview.Drag(100);Assert.That(preview.Yaw,Is.EqualTo(100*preview.dragDegreesPerPixel).Within(.001f));
    preview.Drag(1000);Assert.That(preview.Yaw,Is.InRange(-180f,180f));
    preview.SetActive(false);Assert.That(cam.enabled,Is.False);
    texture=preview.Texture;
   }
   finally{Object.DestroyImmediate(go);if(texture){texture.Release();Object.DestroyImmediate(texture);}}
  }
 }
}
