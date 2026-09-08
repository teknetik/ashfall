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
 public static class ImportSalvageAssets
 {
  public const string Folder="Assets/AthenHill/Art/Imported/Meshy/Salvage";
  public const string Prefabs="Assets/AthenHill/Prefabs/Salvage";
  public static readonly string[] Names={"relay","general","hall","billboard","crate","generator","trash","scrap"};
  static readonly Vector3[] Sizes={new(7.6f,9.75f,8.8f),new(5.5f,3.35f,3.5f),new(12,16.5f,10.5f),new(3.5f,5,.7f),new(1.3f,1.37f,1.3f),new(1.6f,1.1f,.95f),new(1.4f,.38f,1),new(1.8f,1.25f,1.1f)};
  public static Bounds BoundsOf(GameObject root)
  {
   var rs=root.GetComponentsInChildren<Renderer>(true);if(rs.Length==0)throw new Exception("No mesh in "+root.name);
   var b=rs[0].bounds;foreach(var r in rs.Skip(1))b.Encapsulate(r.bounds);return b;
  }
  public static void Prepare()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play before importing.");
   ShaderUtil.allowAsyncCompilation=false;
   Directory.CreateDirectory(Prefabs);AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
   var reports=new List<object>();
   for(int i=0;i<Names.Length;i++)
   {
    var name=Names[i];var path=Folder+"/"+name+"/"+name+".fbx";if(!File.Exists(path))continue;
    var importer=(ModelImporter)AssetImporter.GetAtPath(path);importer.animationType=ModelImporterAnimationType.None;importer.importAnimation=false;importer.importCameras=false;importer.importLights=false;importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.importNormals=ModelImporterNormals.Import;importer.importTangents=ModelImporterTangents.CalculateMikk;importer.isReadable=true;importer.meshCompression=ModelImporterMeshCompression.Off;importer.SaveAndReimport();
    var model=AssetDatabase.LoadAssetAtPath<GameObject>(path);var root=new GameObject(name);var visual=(GameObject)PrefabUtility.InstantiatePrefab(model);visual.transform.SetParent(root.transform,false);visual.name="Meshy visual";
    var source=BoundsOf(root);visual.transform.localScale=Vector3.Scale(visual.transform.localScale,new Vector3(Sizes[i].x/source.size.x,Sizes[i].y/source.size.y,Sizes[i].z/source.size.z));
    var b=BoundsOf(root);visual.transform.localPosition-=new Vector3(b.center.x,b.min.y,b.center.z);
    var material=MaterialFor(name);
    foreach(var r in root.GetComponentsInChildren<MeshRenderer>())
    {r.sharedMaterials=Enumerable.Repeat(material,r.sharedMaterials.Length).ToArray();r.renderingLayerMask=3;r.shadowCastingMode=name=="trash"?ShadowCastingMode.Off:ShadowCastingMode.On;r.receiveShadows=true;r.motionVectorGenerationMode=MotionVectorGenerationMode.ForceNoMotion;}
    var triangles=root.GetComponentsInChildren<MeshFilter>().Sum(f=>f.sharedMesh.triangles.Length/3);
    reports.Add(new{name,sourceSize=V(source.size),size=V(BoundsOf(root).size),triangles,tangents=root.GetComponentsInChildren<MeshFilter>().Select(f=>f.sharedMesh.tangents.Length).ToArray()});
    PrefabUtility.SaveAsPrefabAsset(root,Prefabs+"/"+name+".prefab");UnityEngine.Object.DestroyImmediate(root);
   }
   AssetDatabase.SaveAssets();Directory.CreateDirectory("../evidence/salvage/20260908/import");File.WriteAllText("../evidence/salvage/20260908/import/models.json",JsonConvert.SerializeObject(reports,Formatting.Indented));
   Preview();
  }
  static float[] V(Vector3 p)=>new[]{p.x,p.y,p.z};
  static Texture2D Texture(string name,string file,bool srgb,bool normal=false,bool readable=false)
  {
   var path=Folder+"/"+name+"/"+file+".png";AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
   var i=(TextureImporter)AssetImporter.GetAtPath(path);i.textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;i.sRGBTexture=srgb;i.maxTextureSize=2048;i.mipmapEnabled=true;i.anisoLevel=4;i.isReadable=readable;i.textureCompression=readable?TextureImporterCompression.Uncompressed:TextureImporterCompression.CompressedHQ;i.SaveAndReimport();return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
  }
  static Material MaterialFor(string name)
  {
   var albedo=Texture(name,"base_color",true);var normal=Texture(name,"normal",false,true);var metal=Texture(name,"metallic",false,false,true);var rough=Texture(name,"roughness",false,false,true);
   var m=metal.GetPixels32();var r=rough.GetPixels32();if(m.Length!=r.Length)throw new Exception("PBR atlas sizes differ for "+name);
   for(int i=0;i<m.Length;i++)m[i]=new Color32(m[i].r,0,0,(byte)(255-r[i].r));
   var packed=new Texture2D(metal.width,metal.height,TextureFormat.RGBA32,false,true);packed.SetPixels32(m);packed.Apply();File.WriteAllBytes(Folder+"/"+name+"/metallic_smoothness.png",packed.EncodeToPNG());UnityEngine.Object.DestroyImmediate(packed);
   var path=Folder+"/"+name+"/"+name+".mat";var mat=AssetDatabase.LoadAssetAtPath<Material>(path);if(!mat){mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="Salvage_"+name,enableInstancing=true};AssetDatabase.CreateAsset(mat,path);}
   mat.SetTexture("_BaseMap",albedo);mat.SetColor("_BaseColor",Color.white);mat.SetTexture("_BumpMap",normal);mat.SetFloat("_BumpScale",.55f);mat.EnableKeyword("_NORMALMAP");mat.SetTexture("_MetallicGlossMap",Texture(name,"metallic_smoothness",false));mat.SetFloat("_Metallic",1);mat.SetFloat("_Smoothness",.5f);mat.EnableKeyword("_METALLICSPECGLOSSMAP");mat.SetFloat("_Cull",2);EditorUtility.SetDirty(mat);return mat;
  }
  public static void Preview()
  {
   ShaderUtil.allowAsyncCompilation=false;
   EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.55f,.55f,.55f);
   var sun=new GameObject("Preview key").AddComponent<Light>();sun.type=LightType.Directional;sun.intensity=2;sun.transform.rotation=Quaternion.Euler(45,-35,0);
   var fill=new GameObject("Preview fill").AddComponent<Light>();fill.type=LightType.Directional;fill.intensity=.7f;fill.transform.rotation=Quaternion.Euler(30,145,0);
   foreach(var name in Names)
   {
    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Prefabs+"/"+name+".prefab");if(!prefab)continue;
    var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);var b=BoundsOf(go);float d=Mathf.Max(b.size.x,b.size.y,b.size.z)*1.6f;
    for(int side=0;side<2;side++)
    {
     var c=ImportBaseline.Camera("preview",b.center+new Vector3(d*.65f,d*.25f,(side==0?1:-1)*d),b.center,42);c.clearFlags=CameraClearFlags.SolidColor;c.backgroundColor=new Color(.36f,.36f,.34f);PortDiagnostics.Capture("preview");PortDiagnostics.Capture("preview");File.Copy("Captures/Fixed/preview.png","../evidence/salvage/20260908/import/"+name+(side==0?"-plusz":"-minusz")+".png",true);UnityEngine.Object.DestroyImmediate(c.gameObject);
    }
    UnityEngine.Object.DestroyImmediate(go);
   }
  }
 }
}
