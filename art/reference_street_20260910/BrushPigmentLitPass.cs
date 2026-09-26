#if UNITY_EDITOR
// Staged only. Copy into Editor and explicitly invoke after live source review.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace AthenHill.Editor
{
 public static class BrushPigmentLitPass
 {
  static string Repo=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
  static string Art=>Path.Combine(Repo,"art/reference_street_20260910/brush-pigment-lit-v1");
  static string ContractPath=>Path.Combine(Art,"installer-contract.json");
  const string Folder="Assets/AthenHill/Art/ReferenceStreet/20260910/BrushPigmentLitV1";
  static string PathOf(Transform t)=>AnimationUtility.CalculateTransformPath(t,null);
  static string Sha(string p){using(var h=SHA256.Create())using(var f=File.OpenRead(p))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
  static void Write(string p,object x)=>File.WriteAllText(p,JsonConvert.SerializeObject(x,Formatting.Indented));
  static IEnumerable<T> All<T>(Scene s)where T:Component=>s.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<T>(true));
  static Vector3 V(JToken a)=>new Vector3((float)a[0],(float)a[1],(float)a[2]);
  sealed class Target {public JObject row,part;public MeshRenderer renderer;public MeshFilter filter;public Mesh mesh;public Material old;}
  static void Files(JObject c)
  {
   if(Sha(Path.Combine(Repo,(string)c["sourceMeshExport"]))!=(string)c["sourceMeshSha256"]||Sha(Path.Combine(Repo,(string)c["sourceContract"]))!=(string)c["sourceContractSha256"])throw new InvalidDataException("Brush source geometry/contract changed.");
   foreach(JObject map in c["sourceMapRecords"])if(Sha(Path.Combine(Repo,(string)map["file"]))!=(string)map["sha256"])throw new InvalidDataException("Original pigment map changed.");
   if(c["packedMaps"].Count()!=2)throw new InvalidDataException("Expected color/alpha and metal/smoothness maps.");
   foreach(JObject map in c["packedMaps"])
   {
    string file=(string)map["file"];if(!new[]{"BaseRGBA.png","MetalSmooth.png"}.Contains(file)||Sha(Path.Combine(Art,file))!=(string)map["sha256"])throw new InvalidDataException("Packed channel source changed.");
   }
   var old=c["oldMaterial"];string mat=(string)old["asset"];
   if(Sha(mat)!=(string)old["sha256"]||Sha(mat+".meta")!=(string)old["metaSha256"])throw new InvalidDataException("Retained brush material changed.");
   foreach(JObject row in c["targets"])
   {
    string p=(string)row["meshAsset"];if(Sha(p)!=(string)row["meshSha256"]||Sha(p+".meta")!=(string)row["meshMetaSha256"]||AssetDatabase.AssetPathToGUID(p)!=(string)row["meshGuid"])throw new InvalidDataException("Retained brush mesh/hash changed.");
   }
  }
  static (Scene,StaticRenderChunks,JObject,List<Target>) Preflight()
  {
   var scene=SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||EditorApplication.isCompiling||EditorApplication.isUpdating||scene.isDirty||SceneManager.sceneCount!=1||scene.path!=ImportBaseline.ScenePath)throw new InvalidOperationException("Open the clean saved AthenHill scene in idle Edit mode.");
   var chunks=Object.FindAnyObjectByType<StaticRenderChunks>();
   if(!chunks||chunks.gameObject.scene!=scene||chunks.editingSources||chunks.sources==null||chunks.sourceVisibility==null||chunks.sources.Length!=chunks.sourceVisibility.Length||chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks))throw new InvalidOperationException("Require current saved source render chunks outside ShowSources editing mode.");
   var c=JObject.Parse(File.ReadAllText(ContractPath));
   if((int)c["schema"]!=1||(string)c["revision"]!="brush-pigment-lit-v1"||(float)c["cutoff"]!=.45f||!c["baseMapScale"].Values<float>().SequenceEqual(new[]{2f,2f})||!c["baseMapOffset"].Values<float>().SequenceEqual(new[]{0f,0f}))throw new InvalidDataException("Unreviewed pigment contract or metric UV scale.");
   Files(c);var parts=JArray.Parse(File.ReadAllText(Path.Combine(Repo,(string)c["sourceMeshExport"])));var result=new List<Target>();
   if(c["targets"].Count()!=2||parts.Count!=2||!parts.Select(p=>(string)p["text"]).SequenceEqual(new[]{"THE FACTORIES","NEVER SLEEP."}))throw new InvalidDataException("Exact two source phrases required.");
   foreach(JObject row in c["targets"])
   {
    string path=(string)row["path"];var matches=chunks.sources.OfType<MeshRenderer>().Where(r=>r&&PathOf(r.transform)==path).ToArray();if(matches.Length!=1)throw new InvalidDataException("Missing/ambiguous brush receiver: "+path);
    var r=matches[0];var f=r.GetComponent<MeshFilter>();var m=f?f.sharedMesh:null;var part=(JObject)parts.Single(p=>(string)p["sourcePath"]==path);
    if(!m||AssetDatabase.GetAssetPath(m)!=(string)row["meshAsset"]||r.sharedMaterials.Length!=1||AssetDatabase.GetAssetPath(r.sharedMaterial)!=(string)c["oldMaterial"]["asset"]||r.sharedMaterial.shader.name!="Universal Render Pipeline/Lit"||!r.gameObject.activeInHierarchy||!chunks.sourceVisibility[Array.IndexOf(chunks.sources,r)]||r.shadowCastingMode!=ShadowCastingMode.Off||r.GetComponent<Collider>())throw new InvalidDataException("Existing brush mesh/material/visibility/collision assignment changed: "+path);
    if(!m.isReadable||m.subMeshCount!=1||m.vertexCount!=(int)row["vertices"]||m.triangles.Length!=(int)row["triangles"]*3||m.blendShapeCount!=0||m.bindposes.Length!=0||!m.triangles.SequenceEqual(part["indices"].Values<int>()))throw new InvalidDataException("Exact brush topology changed: "+path);
    var p=m.vertices;var n=m.normals;var uv=m.uv;if(n.Length!=p.Length||uv.Length!=p.Length)throw new InvalidDataException("Missing original brush attributes.");
    var matrix=r.transform.localToWorldMatrix;var nm=matrix.inverse.transpose;
    for(int i=0;i<p.Length;i++)
    {
     if((matrix.MultiplyPoint3x4(p[i])-V(part["positions"][i])).magnitude>(float)row["worldPositionToleranceMetres"]||(nm.MultiplyVector(n[i]).normalized-V(part["normals"][i])).magnitude>.001f||Mathf.Abs(uv[i].x-(float)part["uv"][i][0])>.000002f||Mathf.Abs(uv[i].y-(float)part["uv"][i][1])>.000002f)throw new InvalidDataException("Brush world positions/normals/UV0 changed at vertex "+i+": "+path);
    }
    result.Add(new Target{row=row,part=part,renderer=r,filter=f,mesh=m,old=r.sharedMaterial});
   }
   if(result.Select(t=>t.renderer).Distinct().Count()!=2)throw new InvalidDataException("Duplicate receiver.");return(scene,chunks,c,result);
  }
  static string ComponentState(Component c,HashSet<MeshRenderer> changed)
  {
   string json=EditorJsonUtility.ToJson(c);if(!(c is MeshRenderer r)||!changed.Contains(r))return json;
   var token=JObject.Parse(json);token.Remove("m_Materials");return token.ToString(Formatting.None);
  }
  static string Preserve(Scene s,StaticRenderChunks chunks,List<Target> targets)
  {
   var changed=new HashSet<MeshRenderer>(targets.Select(t=>t.renderer));
   if(All<ActorAnimation>(s).Count()!=9||All<AmbientWalker>(s).Count()!=4||All<PlayerMotor>(s).Count()!=1)throw new InvalidDataException("Expected nine actors/four routes/one player.");
   return JsonConvert.SerializeObject(new{gameplay=DistrictCityPass.GameplaySignature(),
    transforms=All<Transform>(s).Where(t=>!chunks.generatedRoot||!t.IsChildOf(chunks.generatedRoot)).OrderBy(PathOf,StringComparer.Ordinal).Select(t=>new{path=PathOf(t),local=Enumerable.Range(0,16).Select(i=>Matrix4x4.TRS(t.localPosition,t.localRotation,t.localScale)[i]).ToArray(),t.gameObject.activeSelf,t.gameObject.layer,t.gameObject.tag}),
    components=All<Component>(s).Where(x=>x&&!(x is Transform)&&x!=chunks&&(!chunks.generatedRoot||!x.transform.IsChildOf(chunks.generatedRoot))).OrderBy(x=>PathOf(x.transform)+"/"+x.GetType().FullName,StringComparer.Ordinal).Select(x=>new{path=PathOf(x.transform),type=x.GetType().FullName,json=ComponentState(x,changed)})});
  }
  static Texture2D Import(string path,bool color,float cutoff)
  {
   AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);var i=(TextureImporter)AssetImporter.GetAtPath(path);i.GetSourceTextureWidthAndHeight(out int w,out int h);if(w!=4096||h!=4096)throw new InvalidDataException("4K source required.");
   i.textureType=TextureImporterType.Default;i.sRGBTexture=color;i.alphaSource=TextureImporterAlphaSource.FromInput;i.alphaIsTransparency=false;i.npotScale=TextureImporterNPOTScale.None;i.maxTextureSize=4096;i.mipmapEnabled=true;i.streamingMipmaps=true;i.mipMapsPreserveCoverage=color;i.alphaTestReferenceValue=cutoff;i.anisoLevel=8;i.wrapMode=TextureWrapMode.Repeat;i.filterMode=FilterMode.Trilinear;i.textureCompression=TextureImporterCompression.CompressedHQ;i.crunchedCompression=false;i.isReadable=false;i.ClearPlatformTextureSettings("Standalone");i.SaveAndReimport();
   var t=AssetDatabase.LoadAssetAtPath<Texture2D>(path);if(t.width!=4096||t.height!=4096)throw new InvalidDataException("Full-size pigment texture not imported.");return t;
  }
  public static void Apply()
  {
   var(scene,chunks,c,targets)=Preflight();string evidence=Path.Combine(Repo,"unity/evidence/reference-street/20260910/brush-pigment-lit-v1");
   if(Directory.Exists(Folder)||Directory.Exists(evidence))throw new IOException("Preserve an existing candidate; this installer runs once.");
   if(QualitySettings.globalTextureMipmapLimit!=0)throw new InvalidDataException("Full-resolution import inspection requires mip limit zero.");
   string keep=Preserve(scene,chunks,targets);Directory.CreateDirectory(evidence);Directory.CreateDirectory(Folder);Write(Path.Combine(evidence,"contract.json"),c);File.WriteAllText(Path.Combine(evidence,"preserved-before.json"),keep);EditorSceneManager.SaveScene(scene,Path.Combine(evidence,"before-scene.unity"),true);
   try
   {
    foreach(string file in new[]{"BaseRGBA.png","MetalSmooth.png"})File.Copy(Path.Combine(Art,file),Folder+"/"+file,false);
    var color=Import(Folder+"/BaseRGBA.png",true,.45f);var packed=Import(Folder+"/MetalSmooth.png",false,.45f);
    var shader=Shader.Find("Universal Render Pipeline/Lit");if(!shader)throw new InvalidDataException("Installed URP Lit shader unavailable.");
    var mat=new Material(shader){name="Factory faded brush pigment v1",enableInstancing=true};
    mat.SetFloat("_WorkflowMode",1);mat.SetFloat("_Surface",0);mat.SetFloat("_AlphaClip",1);mat.SetFloat("_Cutoff",.45f);mat.SetFloat("_Cull",0);mat.SetFloat("_ZWrite",1);
    mat.SetTexture("_BaseMap",color);mat.SetTexture("_MainTex",color);mat.SetColor("_BaseColor",Color.white);mat.SetColor("_Color",Color.white);mat.SetTextureScale("_BaseMap",new Vector2(2,2));mat.SetTextureOffset("_BaseMap",Vector2.zero);mat.SetTextureScale("_MainTex",new Vector2(2,2));mat.SetTextureOffset("_MainTex",Vector2.zero);
    mat.SetTexture("_MetallicGlossMap",packed);mat.SetFloat("_Metallic",0);mat.SetFloat("_Smoothness",1);mat.SetFloat("_SmoothnessTextureChannel",0);mat.SetTexture("_BumpMap",null);mat.SetTexture("_ParallaxMap",null);mat.SetTexture("_DetailNormalMap",null);mat.SetTexture("_DetailAlbedoMap",null);mat.SetTexture("_EmissionMap",null);mat.SetColor("_EmissionColor",Color.black);
    BaseShaderGUI.SetMaterialKeywords(mat,UnityEditor.Rendering.Universal.ShaderGUI.LitGUI.SetMaterialKeywords,m=>{m.DisableKeyword("_DETAIL_MULX2");m.DisableKeyword("_DETAIL_SCALED");});
    if(!mat.IsKeywordEnabled("_ALPHATEST_ON")||!mat.IsKeywordEnabled("_METALLICSPECGLOSSMAP")||mat.IsKeywordEnabled("_NORMALMAP")||mat.IsKeywordEnabled("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A")||mat.IsKeywordEnabled("_SURFACE_TYPE_TRANSPARENT")||mat.GetFloat("_ZWrite")!=1)throw new InvalidDataException("URP alpha/metal/smoothness keyword contract failed.");
    AssetDatabase.CreateAsset(mat,Folder+"/FactoryBrushPigment.mat");chunks.ShowSources(true);
    foreach(var t in targets){t.renderer.sharedMaterial=mat;EditorUtility.SetDirty(t.renderer);PrefabUtility.RecordPrefabInstancePropertyModifications(t.renderer);}
    AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);
    if(Preserve(scene,chunks,targets)!=keep)throw new InvalidDataException("An untouched component, geometry, transform, visibility or gameplay property changed; restore the recorded backup before continuing.");
    Files(c);foreach(var t in targets)if(t.filter.sharedMesh!=t.mesh||t.renderer.shadowCastingMode!=ShadowCastingMode.Off||t.renderer.sharedMaterials.Length!=1||t.renderer.sharedMaterial!=mat)throw new InvalidDataException("Letter geometry/shadow/material preservation failed.");
    if(chunks.editingSources||chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks))throw new InvalidDataException("Derived chunks stale after source material replacement.");
    EditorSceneManager.SaveScene(scene);Write(Path.Combine(evidence,"installed.json"),new{utc=DateTime.UtcNow,sceneSha256=Sha(scene.path),contractSha256=Sha(ContractPath),sourceFingerprint=chunks.sourceFingerprint,material=AssetDatabase.GetAssetPath(mat),materialSha256=Sha(AssetDatabase.GetAssetPath(mat)),alphaToMask=mat.GetFloat("_AlphaToMask"),mat.renderQueue,maps=new[]{color,packed}.Select(t=>new{path=AssetDatabase.GetAssetPath(t),t.width,t.height,format=t.format.ToString(),sha256=Sha(AssetDatabase.GetAssetPath(t)),metaSha256=Sha(AssetDatabase.GetAssetPath(t)+".meta")}),targets=targets.Select(t=>new{path=(string)t.row["path"],phrase=(string)t.part["text"],mesh=AssetDatabase.GetAssetPath(t.mesh),vertices=t.mesh.vertexCount,triangles=t.mesh.triangles.Length/3}),geometryUVPhrasePlacementCollidersRoutesPreserved=true,sourceAssetsAndImportersPreserved=true,paintHasNoAddedNormalOrDepth=true,retainedLetterOffsetM=.008999,nativeAccepted=false});
   }
   catch(Exception error){Write(Path.Combine(evidence,"failure.json"),new{utc=DateTime.UtcNow,error=error.ToString(),backup="before-scene.unity",status="Failed evidence and candidate assets retained; no automatic acceptance."});throw;}
  }
 }
}
#endif
