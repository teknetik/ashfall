using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Editor
{
 public static class CraftingSurvey
 {
  public static void RepairImportedMarket()
  {
   const string path="Assets/AthenHill/Art/KaraveenMarket/KaraveenMarket.glb";
   AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);
   Debug.Log("CRAFT_REIMPORT "+path+" "+(AssetDatabase.LoadAssetAtPath<GameObject>(path)!=null));
  }
  public static void Run()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   var tutorial=Object.FindAnyObjectByType<BermsTutorial>();
   Debug.Log("CRAFT_SURVEY locker="+tutorial.locker.transform.position+" Ossa="+tutorial.briefingWarden.position);
   foreach(var item in Object.FindObjectsByType<WorldInteractable>(FindObjectsSortMode.None))Debug.Log("CRAFT_SURVEY interaction="+item.name+" "+item.transform.position);
   foreach(var go in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None))if(go.name=="Outpost"||go.name=="Landmarks")Debug.Log("CRAFT_SURVEY parent="+go.name+" "+go.position);
  }
 }
}
