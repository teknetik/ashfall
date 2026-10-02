using System;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 public class CharacterLoadoutPanelTests
 {
  const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  GameObject go;CityCatalog city;CharacterCatalog data;GameSession session;ShopModel pack;CharacterModel character;VisualElement root;CharacterLoadoutPanel panel;
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,BindingFlags.Instance|BindingFlags.Public).SetValue(target,value);
  void Call(string method,params object[] arguments)=>typeof(CharacterLoadoutPanel).GetMethod(method,Private).Invoke(panel,arguments);
  [SetUp] public void Setup()
  {
   go=new GameObject("character ui test");go.SetActive(false);session=go.AddComponent<GameSession>();
   city=ScriptableObject.CreateInstance<CityCatalog>();city.items=new[]{new ItemSpec{id="test_weapon",name="Test weapon",maxStack=10,weightKg=1},new ItemSpec{id="test_armour",name="Test armour",maxStack=10,weightKg=1}};
   data=ScriptableObject.CreateInstance<CharacterCatalog>();
   data.attributes=new[]{new CharacterAttribute{id="strength",label="Strength",initial=10}};
   data.derivedStats=new[]{new CharacterDerivedStat{id="carryCapacity",label="Carry capacity",initial=100},new CharacterDerivedStat{id="storageCapacity",label="Storage",initial=100}};
   data.slots=new[]{new CharacterSlot{id="secondary",label="Secondary",section="SECONDARY"},new CharacterSlot{id="armour_chest",label="Chest",section="ARMOUR"}};
   data.equipment=new[]{new CharacterEquipment{itemId="test_weapon",slots=new[]{"secondary"}},new CharacterEquipment{itemId="test_armour",slots=new[]{"armour_chest"}}};
   pack=new ShopModel(city.items);character=new CharacterModel(data,pack);session.catalog=city;Set(session,"Shop",pack);Set(session,"Character",character);
   root=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
   panel=new CharacterLoadoutPanel(root,session,null,()=>"test_weapon",()=>panel.Refresh());panel.Refresh();
  }
  [TearDown] public void Cleanup(){UnityEngine.Object.DestroyImmediate(go);UnityEngine.Object.DestroyImmediate(city);UnityEngine.Object.DestroyImmediate(data);Time.timeScale=1;}
  [Test] public void ShowsFiveSectionsRealCapacityAndExpandableStats()
  {
   foreach(var name in new[]{"primary","secondary","stats","implants","armour"})Assert.That(root.Q<Button>("character-tab-"+name),Is.Not.Null);
   Assert.That(root.Q<Label>("character-capacity").text,Does.Contain("/ 100 kg"));
   Assert.That(root.Q<Button>("equipment-secondary"),Is.Not.Null);
   typeof(CharacterLoadoutPanel).GetField("section",Private).SetValue(panel,"STATS");panel.Refresh();
   Assert.That(root.Q<Button>("raise-strength"),Is.Not.Null);
   Assert.That(root.Q<Foldout>("breakdown-carryCapacity"),Is.Not.Null);
  }
  [Test] public void RejectedDropPreservesInventoryAndReportsReason()
  {
   Assert.That(pack.Grant("test_weapon",1,0,out _),Is.True);
   Call("Place","test_weapon",null,null,null,"armour_chest",null,null);
   Assert.That(pack.Quantity("test_weapon"),Is.EqualTo(1));Assert.That(character.Equipped("armour_chest"),Is.Null);
   Assert.That(root.Q<Label>("equipment-result").text,Is.Not.Empty);
   Assert.That(root.Q("equipment-result").ClassListContains("rejected"),Is.True);
  }
  [Test] public void DropAndKeyboardRemovalUseTheSameAuthoritativeEquipment()
  {
   Assert.That(pack.Grant("test_weapon",1,0,out _),Is.True);
   Call("Place","test_weapon",null,null,null,"secondary",null,null);
   Assert.That(character.Equipped("secondary"),Is.EqualTo("test_weapon"));Assert.That(pack.Quantity("test_weapon"),Is.Zero);
   Assert.That(root.Q<Button>("equipment-secondary").tooltip,Does.Contain("Test weapon"));
   typeof(CharacterLoadoutPanel).GetField("selectedSlot",Private).SetValue(panel,"secondary");Call("RemoveSelected");
   Assert.That(character.Equipped("secondary"),Is.Null);Assert.That(pack.Quantity("test_weapon"),Is.EqualTo(1));
  }
  [Test] public void CarriedModificationDetailsExplainCompatibilityEffectsAndRequirements()
  {
   data.modifications=new[]{new CharacterModification{itemId="test_module",slots=new[]{"armour_chest"},socketTypes=new[]{"armour_plate"},
    modifiers=new[]{new CharacterModifier{stat="strength",flat=2,percent=.08f}},
    requirements=new[]{new CharacterRequirement{stat="strength",minimum=12}},operatingRequirements=new[]{new CharacterRequirement{stat="strength",minimum=15}}}};
   var text=panel.DescribeItem("test_module");
   Assert.That(text,Does.Contain("Fits: Chest").And.Contain("Socket type: Armour plate"));
   Assert.That(text,Does.Contain("Strength +2 +8%"),"fractional modifiers display as percentages");
   Assert.That(text,Does.Contain("Requires: Strength 10/12").And.Contain("To operate: Strength 10/15"));
   Assert.That(character.Equipped("armour_chest"),Is.Null,"inspection does not install the module");
  }

  [Test] public void ImplantBodyIsTwoDimensionalAndEachHostExposesThreeClickableAugmentations()
  {
   city.items=new[]{new ItemSpec{id="implant",name="Neural interface",maxStack=1,weightKg=.2f},new ItemSpec{id="augment",name="Cognition mesh",maxStack=2,weightKg=.05f}};
   data.slots=new[]{new CharacterSlot{id="implant_head",label="Neural",section="IMPLANTS"}};
   data.equipment=new[]{new CharacterEquipment{itemId="implant",slots=new[]{"implant_head"}}};
   data.modifications=new[]{new CharacterModification{itemId="augment",slots=new[]{"implant_head"},socketTypes=new[]{"implant"}}};
   pack=new ShopModel(city.items);character=new CharacterModel(data,pack);Set(session,"Shop",pack);Set(session,"Character",character);
   Assert.That(character.TryGrantEquipped("implant","implant_head",out _),Is.True);Assert.That(pack.Grant("augment",1,0,out _),Is.True);
   typeof(CharacterLoadoutPanel).GetField("section",Private).SetValue(panel,"IMPLANTS");panel.Refresh();
   Assert.That(panel.WantsPreview,Is.False,"implants never start the 3D character camera");
   Assert.That(root.Q<Image>("anatomy-image"),Is.Not.Null);Assert.That(root.Q("implant-body-map"),Is.Not.Null);
   Assert.That(root.Query<Button>(className:"modification-socket").ToList().Count,Is.EqualTo(3));
   Assert.That(root.Q("augmentation-details"),Is.Null);
   Call("ChooseModification",1);
   Assert.That(root.Q("augmentation-details"),Is.Not.Null);Assert.That(root.Q<Button>("install-augmentation-augment"),Is.Not.Null);
   Assert.That(root.Q("modification-socket-1").ClassListContains("selected"),Is.True);
   Assert.That(character.TryUnequip("implant_head",out _),Is.True);panel.Refresh();
   Assert.That(root.Q("augmentation-details"),Is.Null,"removing a host clears its nested socket selection safely");
  }

 }
}
