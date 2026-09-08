using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 public static class DistrictAtlas
 {
  const string Folder=ImportDistrictAssets.Folder+"/Atlas";
  public static void Apply()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
   var path=Folder+"/DistrictAtlas.mat";var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
   if(!mat){mat=new Material(AssetDatabase.LoadAssetAtPath<Material>(ImportSalvageAssets.Folder+"/Atlas/SalvageAtlas.mat")){name="DistrictAtlas"};AssetDatabase.CreateAsset(mat,path);}
   foreach(var channel in new[]{"base_color","normal","metallic_smoothness"})
   {
    var file=Folder+"/"+channel+".png";if(!File.Exists(file))throw new Exception("Run prepare_district_atlas.py first.");
    var i=(TextureImporter)AssetImporter.GetAtPath(file);i.textureType=channel=="normal"?TextureImporterType.NormalMap:TextureImporterType.Default;i.sRGBTexture=channel=="base_color";i.maxTextureSize=8192;i.npotScale=TextureImporterNPOTScale.None;i.mipmapEnabled=true;i.anisoLevel=4;i.wrapMode=TextureWrapMode.Clamp;i.textureCompression=TextureImporterCompression.CompressedHQ;i.SaveAndReimport();
    mat.SetTexture(channel=="base_color"?"_BaseMap":channel=="normal"?"_BumpMap":"_MetallicGlossMap",AssetDatabase.LoadAssetAtPath<Texture2D>(file));
   }
   EditorUtility.SetDirty(mat);var oldMeshes=new Dictionary<string,Mesh>();var newMeshes=new Dictionary<string,Mesh>();
   foreach(var name in ImportSalvageAssets.Names)
   {
    var source=AssetDatabase.LoadAssetAtPath<Mesh>(ImportSalvageAssets.Folder+"/Atlas/"+name+".asset");
    var mesh=Copy(source,"salvage_"+name,v=>new Vector2(v.x*4096f/6144f,v.y));oldMeshes[name]=mesh;Prefab(ImportSalvageAssets.Prefabs+"/"+name+".prefab",mesh,mat);
   }
   for(int n=0;n<ImportDistrictAssets.Names.Length;n++)
   {
    var name=ImportDistrictAssets.Names[n];var model=AssetDatabase.LoadAssetAtPath<GameObject>(ImportDistrictAssets.Folder+"/"+name+"/"+name+".fbx");var source=model.GetComponentInChildren<MeshFilter>().sharedMesh;
    float x=4096+n%2*1024,y=(3-n/2)*1024;
    var mesh=Copy(source,name,v=>new Vector2((x+8+Mathf.Clamp01(v.x)*1008)/6144f,(y+8+Mathf.Clamp01(v.y)*1008)/4096f));newMeshes[name]=mesh;Prefab(ImportDistrictAssets.Prefabs+"/"+name+".prefab",mesh,mat);
   }
   Instances(GameObject.Find("Post-war salvage").transform,oldMeshes,mat);Instances(GameObject.Find(DistrictCityPass.RootName).transform,newMeshes,mat);
   StaticRenderChunksEditor.Rebuild(chunks);AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();
   AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);EditorSceneManager.OpenScene(ImportBaseline.ScenePath);StaticRenderChunksEditor.Rebuild(UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>());
   DistrictCityPass.GeometryReport();DistrictCityPass.Capture();
  }
  static Mesh Copy(Mesh source,string name,Func<Vector2,Vector2> map)
  {
   var mesh=UnityEngine.Object.Instantiate(source);mesh.name=name;mesh.uv=mesh.uv.Select(map).ToArray();var path=Folder+"/"+name+".asset";var old=AssetDatabase.LoadAssetAtPath<Mesh>(path);
   if(old){EditorUtility.CopySerialized(mesh,old);UnityEngine.Object.DestroyImmediate(mesh);return old;}AssetDatabase.CreateAsset(mesh,path);return mesh;
  }
  static void Prefab(string path,Mesh mesh,Material mat)
  {
   var root=PrefabUtility.LoadPrefabContents(path);foreach(var f in root.GetComponentsInChildren<MeshFilter>()){f.sharedMesh=mesh;f.GetComponent<MeshRenderer>().sharedMaterial=mat;}
   PrefabUtility.SaveAsPrefabAsset(root,path);PrefabUtility.UnloadPrefabContents(root);
  }
  static void Instances(Transform root,Dictionary<string,Mesh> meshes,Material mat)
  {
   foreach(Transform instance in root)
   {
    string name=Path.GetFileNameWithoutExtension(PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(instance.gameObject));if(!meshes.TryGetValue(name,out var mesh))continue;
    foreach(var f in instance.GetComponentsInChildren<MeshFilter>(true))
    {
     if(f.name=="Reused sign frame"||f.name=="Reused sign face"||f.name=="Original shop name")continue;
     f.sharedMesh=mesh;var r=f.GetComponent<MeshRenderer>();r.sharedMaterial=mat;PrefabUtility.RecordPrefabInstancePropertyModifications(f);PrefabUtility.RecordPrefabInstancePropertyModifications(r);
    }
   }
  }
 }
}
