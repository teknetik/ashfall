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
 }
}
