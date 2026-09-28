using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace AthenHill.Editor
{
 public static class CheckpointSignPass
 {
  public static void Apply()
  {
   var shader=Shader.Find("Athen Hill/Checkpoint Lettering");if(!shader)throw new System.Exception("Missing checkpoint lettering shader");
   const string path="Assets/AthenHill/Art/Checkpoint/Lettering.mat";
   var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
   var source=GameObject.Find("Arms locker lettering").GetComponent<Renderer>().sharedMaterial;
   if(!mat){mat=new Material(source){name="Checkpoint lettering"};mat.shader=shader;AssetDatabase.CreateAsset(mat,path);}
   // Keep the cabinet name within its own panel rather than extending past both sides.
   GameObject.Find("Arms locker lettering").GetComponent<TextMesh>().characterSize=.018f;
   GameObject.Find("Pistol issue lettering").GetComponent<TextMesh>().characterSize=.012f;
   foreach(var t in GameObject.Find("West Gate checkpoint").GetComponentsInChildren<TextMesh>(true)){t.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");t.GetComponent<Renderer>().sharedMaterial=mat;}
   var tutorial=Object.FindAnyObjectByType<BermsTutorial>();foreach(var plate in tutorial.targets)foreach(var t in plate.GetComponentsInChildren<TextMesh>(true)){t.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");t.GetComponent<Renderer>().sharedMaterial=mat;}
   EditorUtility.SetDirty(mat);EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());EditorSceneManager.SaveOpenScenes();AssetDatabase.SaveAssets();
  }
 }
}
