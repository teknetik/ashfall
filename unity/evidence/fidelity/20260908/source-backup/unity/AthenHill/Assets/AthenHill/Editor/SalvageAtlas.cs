using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 public static class SalvageAtlas
 {
  const string Folder=ImportSalvageAssets.Folder+"/Atlas";
  const int Size=4096,Border=8;
  static readonly string[] Names={"relay","hall","general","billboard","generator","crate","trash","scrap"};
  static readonly RectInt[] Slots={new(0,2048,2048,2048),new(2048,2048,2048,2048),new(0,0,2048,2048),new(2048,1024,1024,1024),new(3072,1024,1024,1024),new(2048,0,1024,1024),new(3072,512,1024,512),new(3072,0,1024,512)};
  public static void Build()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);Directory.CreateDirectory(Folder);AssetDatabase.Refresh();
   var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
   foreach(var map in new[]{"base_color","normal","metallic_smoothness"})Pack(map);
   var path=Folder+"/SalvageAtlas.mat";var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
   if(!mat){mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="SalvageAtlas",enableInstancing=true};AssetDatabase.CreateAsset(mat,path);}
   mat.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Folder+"/base_color.png"));mat.SetColor("_BaseColor",Color.white);mat.SetTexture("_BumpMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Folder+"/normal.png"));mat.SetFloat("_BumpScale",.55f);mat.EnableKeyword("_NORMALMAP");mat.SetTexture("_MetallicGlossMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Folder+"/metallic_smoothness.png"));mat.SetFloat("_Metallic",1);mat.SetFloat("_Smoothness",.5f);mat.EnableKeyword("_METALLICSPECGLOSSMAP");mat.SetFloat("_Cull",2);EditorUtility.SetDirty(mat);
   var newMeshes=new Dictionary<string,Mesh>();
   for(int i=0;i<Names.Length;i++)
   {
    var name=Names[i];var model=AssetDatabase.LoadAssetAtPath<GameObject>(ImportSalvageAssets.Folder+"/"+name+"/"+name+".fbx");var source=model.GetComponentInChildren<MeshFilter>().sharedMesh;
    var mesh=UnityEngine.Object.Instantiate(source);mesh.name=name+"_atlas";var uv=mesh.uv;var slot=Slots[i];
    for(int v=0;v<uv.Length;v++)uv[v]=new Vector2((slot.x+Border+Mathf.Clamp01(uv[v].x)*(slot.width-2*Border))/Size,(slot.y+Border+Mathf.Clamp01(uv[v].y)*(slot.height-2*Border))/Size);
    mesh.uv=uv;var meshPath=Folder+"/"+name+".asset";var old=AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);if(old){EditorUtility.CopySerialized(mesh,old);UnityEngine.Object.DestroyImmediate(mesh);mesh=old;}else AssetDatabase.CreateAsset(mesh,meshPath);newMeshes[name]=mesh;
    var prefabPath=ImportSalvageAssets.Prefabs+"/"+name+".prefab";var contents=PrefabUtility.LoadPrefabContents(prefabPath);
    foreach(var f in contents.GetComponentsInChildren<MeshFilter>()){f.sharedMesh=mesh;f.GetComponent<MeshRenderer>().sharedMaterial=mat;f.GetComponent<MeshRenderer>().shadowCastingMode=ShadowCastingMode.On;}
    PrefabUtility.SaveAsPrefabAsset(contents,prefabPath);PrefabUtility.UnloadPrefabContents(contents);
   }
   // Apply explicitly to the saved instances too: existing collider components retain
   // their imported physical mesh, while renderer UVs switch to the packed atlas.
   var root=GameObject.Find("Post-war salvage");
   foreach(Transform instance in root.transform)
   {
    string prefabPath=PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(instance.gameObject);string name=Path.GetFileNameWithoutExtension(prefabPath);if(!newMeshes.TryGetValue(name,out var mesh))continue;
    foreach(var f in instance.GetComponentsInChildren<MeshFilter>())if(f.transform.parent&&f.transform.IsChildOf(instance)&&f.GetComponent<Renderer>()&&f.name!="Reused sign frame"&&f.name!="Reused sign face"&&f.name!="Original shop name")
    {f.sharedMesh=mesh;f.GetComponent<MeshRenderer>().sharedMaterial=mat;f.GetComponent<MeshRenderer>().shadowCastingMode=ShadowCastingMode.On;}
   }
   chunks.smallMaterialTriangleLimit=5000;
   StaticRenderChunksEditor.Rebuild(chunks);AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();
   File.WriteAllText("../evidence/salvage/20260908/atlas.json",JsonConvert.SerializeObject(new{size=Size,padding=Border,slots=Names.Select((n,i)=>new{name=n,x=Slots[i].x,y=Slots[i].y,width=Slots[i].width,height=Slots[i].height}).ToArray(),sourceTexturesPreserved=true},Formatting.Indented));
   // Prefab reimports can settle after SaveAssets. Reload before the final chunk
   // fingerprint so build validation sees the same persisted source properties.
   RebuildAndBuild();
  }
  public static void RebuildAndBuild()
  {
   AssetDatabase.SaveAssets();AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   StaticRenderChunksEditor.Rebuild(UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>());
   GeometryReport();SalvageCityPass.Capture();LinuxBuild.Development();LinuxBuild.Release();
  }
  static void Pack(string map)
  {
   var pixels=new Color32[Size*Size];
   for(int i=0;i<Names.Length;i++)
   {
    var image=new Texture2D(2,2,TextureFormat.RGBA32,false,true);image.LoadImage(File.ReadAllBytes(ImportSalvageAssets.Folder+"/"+Names[i]+"/"+map+".png"));var src=image.GetPixels32();int w=image.width,h=image.height;var slot=Slots[i];
    for(int y=0;y<slot.height;y++)for(int x=0;x<slot.width;x++)
    {
     float u=Mathf.Clamp01((x-Border+.5f)/(slot.width-2*Border));float v=Mathf.Clamp01((y-Border+.5f)/(slot.height-2*Border));int sx=Mathf.Min(w-1,(int)(u*w)),sy=Mathf.Min(h-1,(int)(v*h));pixels[(slot.y+y)*Size+slot.x+x]=src[sy*w+sx];
    }
    UnityEngine.Object.DestroyImmediate(image);
   }
   var atlas=new Texture2D(Size,Size,TextureFormat.RGBA32,false,true);atlas.SetPixels32(pixels);atlas.Apply();var path=Folder+"/"+map+".png";File.WriteAllBytes(path,atlas.EncodeToPNG());UnityEngine.Object.DestroyImmediate(atlas);AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
   var importer=(TextureImporter)AssetImporter.GetAtPath(path);importer.textureType=map=="normal"?TextureImporterType.NormalMap:TextureImporterType.Default;importer.sRGBTexture=map=="base_color";importer.maxTextureSize=Size;importer.mipmapEnabled=true;importer.anisoLevel=4;importer.wrapMode=TextureWrapMode.Clamp;importer.textureCompression=TextureImporterCompression.CompressedHQ;importer.SaveAndReimport();
  }
  public static void GeometryReport()
  {
   var renderers=UnityEngine.Object.FindObjectsByType<Renderer>().Where(r=>r.enabled&&r.gameObject.activeInHierarchy).ToArray();var report=new List<object>();
   foreach(var camera in UnityEngine.Object.FindObjectsByType<Camera>().Where(c=>c.name.StartsWith("cam_")&&c.name!="cam_grid"))
   {
    var planes=GeometryUtility.CalculateFrustumPlanes(camera);var rs=renderers.Where(r=>GeometryUtility.TestPlanesAABB(planes,r.bounds)).Select(r=>new{r.name,triangles=Triangles(r)}).Where(r=>r.triangles>0).ToArray();report.Add(new{camera=camera.name,triangles=rs.Sum(r=>r.triangles),renderers=rs});
   }
   File.WriteAllText("../evidence/salvage/20260908/visible-geometry.json",JsonConvert.SerializeObject(report,Formatting.Indented));
  }
  static int Triangles(Renderer r)
  {if(r is SkinnedMeshRenderer skin)return skin.sharedMesh.triangles.Length/3;var f=r.GetComponent<MeshFilter>();return f&&f.sharedMesh?f.sharedMesh.triangles.Length/3:0;}
 }
}
