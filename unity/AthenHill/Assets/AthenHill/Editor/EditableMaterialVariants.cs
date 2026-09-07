using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 public static class EditableMaterialVariants
 {
  [MenuItem("Athen Hill/Editing/Make editable material variants")]
  public static void Create()
  {
   if(EditorApplication.isPlaying)throw new System.Exception("Exit Play before editing assets.");
   var replacements=new Dictionary<Material,Material>();
   foreach(var file in new[]{"world.glb","player-candidate.glb","npcs.glb"})
   {
    string folder="Assets/AthenHill/Materials/"+(file=="world.glb"?"World":"Actors");Directory.CreateDirectory(folder);AssetDatabase.Refresh();
    foreach(var original in AssetDatabase.LoadAllAssetsAtPath(ImportBaseline.Art+file).OfType<Material>())
    {
     if(original.name=="MAT_leaf")continue; // Already has its cutout adaptation.
     string path=folder+"/"+original.name+".mat";var editable=AssetDatabase.LoadAssetAtPath<Material>(path);
     if(!editable){editable=new Material(original){name=original.name};AssetDatabase.CreateAsset(editable,path);}replacements.Add(original,editable);
    }
   }
   void Replace(GameObject go)
   {
    foreach(var renderer in go.GetComponentsInChildren<Renderer>(true))
    {
     var materials=renderer.sharedMaterials;bool changed=false;
     for(int i=0;i<materials.Length;i++)if(replacements.TryGetValue(materials[i],out var editable)){materials[i]=editable;changed=true;}
     if(changed)renderer.sharedMaterials=materials;
    }
   }
   Replace(GameObject.Find("AuthoredWorld"));
   foreach(var path in new[]{"Assets/AthenHill/Prefabs/PlayerCandidate.prefab","Assets/AthenHill/Prefabs/NpcImportAudition.prefab"})
   {
    var root=PrefabUtility.LoadPrefabContents(path);
    try{Replace(root);PrefabUtility.SaveAsPrefabAsset(root,path);}finally{PrefabUtility.UnloadPrefabContents(root);}
   }
   // Preserve source shadow exclusions for the distant vista, plus the browser ground.
   var names=JObject.Parse(File.ReadAllText(ImportBaseline.Art+"world.glb.json"))["nodes"].Where(n=>(bool?)n["extras"]?["castShadow"]==false).Select(n=>(string)n["name"]).ToHashSet();
   foreach(var r in GameObject.Find("AuthoredWorld").GetComponentsInChildren<Renderer>(true))if(names.Contains(r.name))r.shadowCastingMode=ShadowCastingMode.Off;
   GameObject.Find("Paving").GetComponent<Renderer>().shadowCastingMode=ShadowCastingMode.Off;
   AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(Object.FindAnyObjectByType<StaticRenderChunks>());
  }
 }
}
