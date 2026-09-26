#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using Object=UnityEngine.Object;
namespace AthenHill.Editor {
public static class StoneThresholdDetailPass {
 const string Folder="Assets/AthenHill/Art/ReferenceStreet/20260910/Thresholds";
 static string Repo=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
 static string Source=>Path.Combine(Repo,"art/reference_street_20260910");
 static string Evidence=>Path.Combine(Repo,"unity/evidence/reference-street/20260910/threshold-install");
 static string PathOf(Transform t)=>AnimationUtility.CalculateTransformPath(t,null);
 static string Physics()=>JsonConvert.SerializeObject(Object.FindObjectsByType<Collider>(FindObjectsInactive.Include,FindObjectsSortMode.None).Where(c=>c.gameObject.scene.IsValid()).OrderBy(c=>PathOf(c.transform)).Select(c=>new{path=PathOf(c.transform),active=c.gameObject.activeInHierarchy,transform=Enumerable.Range(0,16).Select(i=>c.transform.localToWorldMatrix[i]).ToArray(),component=EditorJsonUtility.ToJson(c)}));
 static string Actors()=>JsonConvert.SerializeObject(Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include,FindObjectsSortMode.None).Where(c=>c.gameObject.scene.IsValid() && new[]{"PlayerMotor","ActorAnimation","AmbientWalker","GameSession","NpcDefinition"}.Contains(c.GetType().Name)).OrderBy(c=>PathOf(c.transform)+c.GetType().Name).Select(c=>new{path=PathOf(c.transform),type=c.GetType().Name,data=EditorJsonUtility.ToJson(c),position=Enumerable.Range(0,16).Select(i=>c.transform.localToWorldMatrix[i]).ToArray()}));
 static Texture2D Map(string path,bool color,bool normal=false){
  AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);var i=(TextureImporter)AssetImporter.GetAtPath(path);
  i.textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;i.sRGBTexture=color;i.mipmapEnabled=true;i.streamingMipmaps=true;i.maxTextureSize=4096;i.anisoLevel=8;i.textureCompression=TextureImporterCompression.CompressedHQ;i.npotScale=TextureImporterNPOTScale.None;i.SaveAndReimport();return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
 }
 public static void Apply(){
  var scene=EditorSceneManager.GetActiveScene();if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=ImportBaseline.ScenePath||scene.isDirty)throw new InvalidOperationException("Open the saved scene in Edit mode");
  if(Directory.Exists(Folder)||Directory.Exists(Evidence))throw new InvalidOperationException("Preserve prior threshold revision");
  var chunks=Object.FindAnyObjectByType<StaticRenderChunks>();var root=GameObject.Find("Reference street thresholds and detail");if(!root||!chunks.sourceRoots.Contains(root.transform))throw new InvalidOperationException("Registered source root missing");
  var prior=JArray.Parse(File.ReadAllText(Path.Combine(Repo,"art/reference_street_20260909/threshold-replacements-v2.json")));
  var expected=prior.Select((p,i)=>new{path=(string)p["sourcePath"],mesh="Assets/AthenHill/Art/ReferenceStreet/20260909/Meshes/threshold_replacements_v2_"+i.ToString("D3")+"_"+(string)p["name"]+".asset"}).ToDictionary(p=>p.path,p=>p.mesh);
  foreach(var pair in expected){var t=GameObject.Find(pair.Key);if(!t||AssetDatabase.GetAssetPath(t.GetComponent<MeshFilter>().sharedMesh)!=pair.Value)throw new InvalidDataException("Threshold source changed: "+pair.Key);}
  var retired=JArray.Parse(File.ReadAllText(Path.Combine(Repo,"art/reference_street_20260909/threshold-additions-v2.json"))).Select(p=>root.transform.Find((string)p["name"])).ToArray();
  if(retired.Length!=36||retired.Any(t=>!t||t.GetComponentsInChildren<Collider>(true).Length>0))throw new InvalidDataException("Previous grit roster changed");
  string physics=Physics(),actors=Actors();Directory.CreateDirectory(Evidence);EditorSceneManager.SaveScene(scene,Path.Combine(Evidence,"before-scene.unity"),true);Directory.CreateDirectory(Folder);
  var texDir=Folder+"/Photos";Directory.CreateDirectory(texDir);string photo=Path.Combine(Repo,"refs/quality_20260909/basic-general/materials/sandstone_cracks");
  File.Copy(Path.Combine(photo,"sandstone_cracks_diff_4k.jpg"),texDir+"/BaseColor.jpg");File.Copy(Path.Combine(photo,"sandstone_cracks_nor_gl_4k.jpg"),texDir+"/Normal.jpg");
  var rough=new Texture2D(2,2,TextureFormat.RGBA32,false,true);rough.LoadImage(File.ReadAllBytes(Path.Combine(photo,"sandstone_cracks_rough_4k.jpg")));var px=rough.GetPixels32();for(int j=0;j<px.Length;j++)px[j]=new Color32(0,0,0,(byte)(255-px[j].r));rough.SetPixels32(px);rough.Apply();File.WriteAllBytes(texDir+"/MetalSmooth.png",rough.EncodeToPNG());Object.DestroyImmediate(rough);
  AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);var color=Map(texDir+"/BaseColor.jpg",true);var normal=Map(texDir+"/Normal.jpg",false,true);var packed=Map(texDir+"/MetalSmooth.png",false);
  var materials=new Dictionary<string,Material>();foreach(var key in new[]{"ThresholdStone","ThresholdMortar","ThresholdGrit"}){
   var m=new Material(Shader.Find("Universal Render Pipeline/Lit")){name=key+" 20260910",enableInstancing=true};m.SetTexture("_BaseMap",color);m.SetTexture("_BumpMap",normal);m.SetTexture("_MetallicGlossMap",packed);m.SetFloat("_BumpScale",.65f);m.SetFloat("_Metallic",0);m.SetFloat("_Smoothness",1);m.EnableKeyword("_NORMALMAP");m.EnableKeyword("_METALLICSPECGLOSSMAP");m.SetColor("_BaseColor",key=="ThresholdMortar"?new Color(.48f,.44f,.37f):key=="ThresholdGrit"?new Color(.80f,.78f,.71f):new Color(.87f,.87f,.82f));AssetDatabase.CreateAsset(m,Folder+"/"+key+".mat");materials[key]=m;
  }
  chunks.ShowSources(true);var parent=new GameObject("Stone threshold revision 20260910");parent.transform.SetParent(root.transform,false);
  var result=HeroStreetDetailPass.ImportParts(Path.Combine(Source,"stone-threshold-meshes-v1.json"),Folder+"/Meshes",parent.transform,materials,expected);
  foreach(var t in retired){var r=t.GetComponent<Renderer>();r.enabled=false;EditorUtility.SetDirty(r);PrefabUtility.RecordPrefabInstancePropertyModifications(r);}
  if(Physics()!=physics||Actors()!=actors)throw new InvalidOperationException("Collision or actor data changed; inspect without saving");
  AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);EditorSceneManager.SaveScene(scene);
  File.WriteAllText(Path.Combine(Evidence,"installation.json"),JsonConvert.SerializeObject(new{utc=DateTime.UtcNow,result,retiredGrit=retired.Select(PathOf).ToArray(),physicsPreserved=Physics()==physics,actorsPreserved=Actors()==actors,chunksFresh=chunks.sourceFingerprint==StaticRenderChunksEditor.Fingerprint(chunks),pending="Native surface and traversal review"},Formatting.Indented));
 }
}}
#endif
