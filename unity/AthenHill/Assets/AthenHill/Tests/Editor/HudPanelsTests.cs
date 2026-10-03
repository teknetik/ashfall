using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// Gameplay v2 M3: the fabricator window and Basic General salvage list build from the real UXML and catalogs.
 public class HudPanelsTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static VisualElement Hud()=>AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public ShopModel pack;public CraftingModel model;
   public Rig(CityState state)
   {
    go=new GameObject("hud rig");go.SetActive(false);
    session=go.AddComponent<GameSession>();session.catalog=City();crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    var player=new GameObject("combat");player.transform.SetParent(go.transform);combat=player.AddComponent<PlayerCombat>();combat.hasPistol=true;crafting.combat=combat;
    pack=new ShopModel(City().items);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",state);Set(session,"ActiveStationId","station_field_fabricator");
    Set(crafting,"Model",model);Set(crafting,"Session",session);combat.BindLoadout(model.Loadout);
   }
   public void Dispose(){Object.DestroyImmediate(go);Time.timeScale=1;}
  }

  [Test] public void UxmlKeepsEveryNamedControlTheCodeBinds()
  {
   using var rig=new Rig(CityState.Shop);
   var root=Hud();new MerchantPanel(root,rig.session,rig.crafting).Refresh();
   foreach(var name in new[]{"fab-recipe-list","fabricator-ingredients","fab-slots","fab-stats"})Assert.That(root.Q(name),Is.Not.Null,name);
   foreach(var name in new[]{"fabricator-recipe","fab-description","fab-reason","fabricator-stat","merchant-empty"})Assert.That(root.Q<Label>(name),Is.Not.Null,name);
   foreach(var name in new[]{"fabricator-craft","fabricator-fit","fabricator-remove","merchant-tab-buy","merchant-tab-sell","merchant-trade","merchant-sell-all","close"})Assert.That(root.Q<Button>(name),Is.Not.Null,name);
   Assert.That(root.Q("merchant-scroll"),Is.Not.Null);
  }

  [Test] public void FabricatorListsGroupsLocksStatsAndReasons()
  {
   using var rig=new Rig(CityState.Fabricator);
   var root=Hud();var panel=new FabricatorPanel(root,rig.session,rig.crafting);
   panel.Opened();
   var buttons=root.Query<Button>(className:"fab-recipe").ToList();
   Assert.That(buttons.Count,Is.EqualTo(Data().recipes.Length));
   Assert.That(root.Query<Label>(className:"fab-group").ToList().Select(l=>l.text),Is.EqualTo(new[]{"REFINED COMPONENTS","MARK I PISTOL MODS","MARK II PISTOL MODS","WEAPONS","WEAPON MODS","ARMOUR"}));
   Assert.That(buttons.Where(b=>!b.name.EndsWith("recipe_field_rifle")&&!b.name.EndsWith("recipe_rifle_precision_barrel")).All(b=>b.ClassListContains("locked")),"the field-order recipes are still discovered in play");
   panel.Select("recipe_grip_stabilised_pistol");
   Assert.That(root.Query(className:"fab-slot").ToList().Count,Is.EqualTo(3));
   Assert.That(root.Query(className:"fab-stat-row").ToList().Count,Is.EqualTo(1+Data().statLabels.Length));
   // Know the grip, carry part of it: have/need rows and a worded reason, Fabricate disabled.
   rig.model.Acquire("droid_servo_damaged");
   Assert.That(rig.pack.TryApply(new[]{new KeyValuePair<string,int>("droid_servo_damaged",1),new KeyValuePair<string,int>("scrap_alloy",2),new KeyValuePair<string,int>("nanite_residue",2)},0,out _));
   panel.Select("recipe_grip_stabilised_pistol");panel.Refresh();
   var counts=root.Query<Label>(className:"fab-input-count").ToList();
   Assert.That(counts.Select(c=>c.text),Is.EqualTo(new[]{"1 / 1","2 / 2","2 / 5"}));
   Assert.That(counts[2].ClassListContains("have-short"));Assert.That(counts[0].ClassListContains("have-ok"));
   Assert.That(root.Q<Button>("fabricator-craft").enabledSelf,Is.False);
   Assert.That(root.Q<Label>("fab-reason").text,Is.EqualTo("Missing parts: 3 × Any tier-one nanites."));
   // Preview column shows the grip's recoil change before it is fitted.
   var recoilRow=root.Query(className:"fab-stat-row").ToList().First(r=>r.Q<Label>(className:"fab-stat-name")?.text=="Recoil");
   var cells=recoilRow.Query<Label>(className:"fab-stat-cell").ToList();
   Assert.That(cells.Select(c=>c.text),Is.EqualTo(new[]{"38","31","−7"}));Assert.That(cells[2].ClassListContains("better"));
   // Complete the parts, fabricate through the panel's button, then fit.
   Assert.That(rig.pack.TryApply(new[]{new KeyValuePair<string,int>("nanite_residue",3)},0,out _));panel.Refresh();
   var craft=root.Q<Button>("fabricator-craft");Assert.That(craft.enabledSelf);
   typeof(FabricatorPanel).GetMethod("Craft",Any).Invoke(panel,null);// the Fabricate button's click handler
   Assert.That(rig.pack.Quantity("grip_stabilised_pistol"),Is.EqualTo(1),"Fabricate button crafted one grip");
   panel.Refresh();Assert.That(root.Q<Button>("fabricator-fit").enabledSelf);
   Assert.That(rig.crafting.Fit("grip_stabilised_pistol",out _));panel.Refresh();
   Assert.That(root.Q<Button>("fabricator-remove").enabledSelf);Assert.That(root.Q<Button>("fabricator-fit").enabledSelf,Is.False);
   Assert.That(root.Q("fab-slot-grip").Q<Label>(className:"fab-slot-mod").text,Is.EqualTo("Stabilised Pistol Grip"));
   Assert.That(cells[0].text,Is.EqualTo("31"));Assert.That(cells[1].text,Is.EqualTo("—"),"no preview once fitted");
  }

  [Test] public void SalvageListRowsSellAndDisappearWhenEmpty()
  {
   using var rig=new Rig(CityState.Shop);
   var root=Hud();var panel=new MerchantPanel(root,rig.session,rig.crafting);
   panel.Refresh();panel.SetMode(true);
   Assert.That(root.Q("merchant-item-scrap_alloy"),Is.Null);
   Assert.That(rig.pack.TryApply(new[]{new KeyValuePair<string,int>("scrap_alloy",3),new KeyValuePair<string,int>("lattice_shard",1)},0,out _));
   panel.Refresh();panel.Select("scrap_alloy");
   Assert.That(root.Q("merchant-item-scrap_alloy"),Is.Not.Null);
   Assert.That(root.Q("merchant-item-lattice_shard"),Is.Null,"rare quest salvage cannot be sold");
   Assert.That(root.Q<Button>("merchant-sell-all").text,Is.EqualTo("Sell 3 · 3 cr"));
   typeof(MerchantPanel).GetMethod("Trade",Any).Invoke(panel,null);
   Assert.That(rig.pack.Quantity("scrap_alloy"),Is.EqualTo(2));
   Assert.That(root.Q<Button>("merchant-sell-all").text,Is.EqualTo("Sell 2 · 2 cr"));
   typeof(MerchantPanel).GetMethod("SellStack",Any).Invoke(panel,null);
   Assert.That(root.Q("merchant-item-scrap_alloy"),Is.Null);Assert.That(rig.pack.Quantity("scrap_alloy"),Is.Zero);
   Assert.That(rig.pack.Credits,Is.EqualTo(28));
   Assert.That(rig.pack.Quantity("lattice_shard"),Is.EqualTo(1));
  }
 }
}
