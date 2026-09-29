using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Editor
{
 /// Narrow, one-time installation. Refuses to overwrite saved crafting content.
 public static class CraftingSliceInstaller
 {
  const string DataPath="Assets/AthenHill/Data/Crafting/WardCrafting.asset";
  static LootEntry Drop(string id,int count,float chance=1)=>new LootEntry{itemId=id,minQuantity=count,maxQuantity=count,chance=chance};
  public static void Install()
  {
   if(AssetDatabase.LoadAssetAtPath<CraftingCatalog>(DataPath))throw new Exception("WardCrafting.asset exists; inspect and edit it, do not rerun installer.");
   var scene=EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   var session=UnityEngine.Object.FindAnyObjectByType<GameSession>();
   var tutorial=UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();
   if(!session||!tutorial||session.GetComponent<CraftingSession>()||GameObject.Find("Field fabricator"))throw new Exception("Crafting slice already installed or scene references missing.");
   var data=ScriptableObject.CreateInstance<CraftingCatalog>();
   data.weapons=new[]{new CraftWeapon{id="weapon_scrap_pistol",name="Scrap Pistol",stats=WeaponStats.ScrapPistol,slots=new[]{"grip"}}};
   data.modifiers=new[]{new CraftModifier{id="mod_grip_stabilised",itemId="grip_stabilised_pistol",slot="grip",weaponIds=new[]{"weapon_scrap_pistol"},effects=new[]{new CraftEffect{stat="recoil",op="add",value=-7}}}};
   data.stations=new[]{new CraftStation{id="station_field_fabricator",name="Warden Field Fabricator"}};
   data.recipes=new[]{new CraftRecipe{id="recipe_grip_stabilised_pistol",name="Stabilised Pistol Grip",stationId="station_field_fabricator",requiresWeaponId="weapon_scrap_pistol",inputs=new[]{new CraftIngredient{kind="tag",id="component:servo",quantity=1},new CraftIngredient{kind="item",id="scrap_alloy",quantity=2},new CraftIngredient{kind="tag",id="nanite:tier1",quantity=5}},outputItemId="grip_stabilised_pistol",outputQuantity=1,unlocks=new[]{new CraftUnlock{type="acquireItem",id="droid_servo_damaged"},new CraftUnlock{type="tutorialStep",id="Fabricate"}}}};
   data.lootTables=new[]{new LootTable{id="loot_feral_scrap_drone",entries=new[]{Drop("scrap_alloy",1),Drop("nanite_residue",2),Drop("copper_filament",1,.6f),Drop("micro_capacitor",1,.25f)}},new LootTable{id="loot_feral_worker_droid",entries=new[]{Drop("droid_servo_damaged",1),Drop("scrap_alloy",1),Drop("nanite_residue",1),Drop("copper_filament",1,.65f)}}};
   Directory.CreateDirectory(Path.GetDirectoryName(DataPath));
   AssetDatabase.CreateAsset(data,DataPath);
   BindPrefab("FeralScrapDrone","loot_feral_scrap_drone");BindPrefab("FeralWorkerDroid","loot_feral_worker_droid");
   // These are the saved scene's measured world-space points. Check future outpost changes before moving it.
   var position=new Vector3(-75f,-1.54f,.6f);
   foreach(var item in UnityEngine.Object.FindObjectsByType<WorldInteractable>(FindObjectsSortMode.None))
    if(Vector3.Distance(item.transform.position,position)<4.8f)throw new Exception("Fabricator too close to "+item.name);
   foreach(var npc in session.npcs)if(npc&&Vector3.Distance(npc.transform.position,position)<2.4f)throw new Exception("Fabricator too close to "+npc.name);
   var crafting=session.gameObject.AddComponent<CraftingSession>();crafting.data=data;crafting.combat=tutorial.combat;
   var outpost=GameObject.Find("Outpost");if(!outpost)throw new Exception("Outpost hierarchy missing.");
   var station=new GameObject("Field fabricator");station.transform.SetParent(outpost.transform,true);station.transform.position=position;
   var visual=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/WestGate/PH_ToolCart.prefab");
   if(visual){var instance=(GameObject)PrefabUtility.InstantiatePrefab(visual,scene);instance.name="Field fabricator tool cart";instance.transform.SetParent(station.transform,false);instance.transform.localPosition=Vector3.zero;}
   var prompt=station.AddComponent<WorldInteractable>();prompt.prompt="E · Use field fabricator";prompt.range=2.4f;
   var marker=station.AddComponent<CraftingStationMarker>();marker.stationId="station_field_fabricator";marker.session=session;
   crafting.fabricator=station.transform;
   var landmarks=GameObject.Find("Landmarks");if(landmarks){var landmark=new GameObject("checkpoint_fabricator");landmark.transform.SetParent(landmarks.transform);landmark.transform.position=position+new Vector3(0,0,-1.5f);}
   tutorial.lineComplete="Clean work. Bring that servo to the field fabricator at my post; a steadier grip will tame that pistol. The rest of the salvage sells at Basic General.";
   EditorUtility.SetDirty(tutorial);EditorUtility.SetDirty(session);EditorSceneManager.MarkSceneDirty(scene);
   EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
   Debug.Log("CRAFT_INSTALL saved station at "+position+" and asset "+DataPath);
  }
  static void BindPrefab(string name,string table)
  {
   string path="Assets/AthenHill/Prefabs/OuterBerms/"+name+".prefab";
   var root=PrefabUtility.LoadPrefabContents(path);
   try
   {
    if(root.GetComponent<LootSource>())throw new Exception("LootSource already on "+path);
    root.AddComponent<LootSource>().lootTableId=table;
    PrefabUtility.SaveAsPrefabAsset(root,path);
   }
   finally{PrefabUtility.UnloadPrefabContents(root);}
  }
 }
}
