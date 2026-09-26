#if UNITY_EDITOR
// STAGED ONLY. Order: reviewed source package -> DoorFrontLitPass Inspect/Apply -> this Inspect/Apply.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
 public static class MetalCoatingPass
 {
  static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
  static string Art => Path.Combine(Repo,"art/reference_street_20260910/metal-v4");
  static string ContractPath => Path.Combine(Art,"coating-contract.json");
  static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t,null);
  static string Sha(string p) {using(var h=SHA256.Create())using(var f=File.OpenRead(p))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
  static void Write(string p,object o) => File.WriteAllText(p,JsonConvert.SerializeObject(o,Formatting.Indented));
  static string Safe(string s) {if(string.IsNullOrEmpty(s)||s.Any(c=>!char.IsLetterOrDigit(c)&&c!='-'&&c!='_'))throw new ArgumentException("Explicit simple revision name required.");return s;}
  static IEnumerable<T> All<T>(Scene scene) where T:Component => scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<T>(true));
  static Vector2 V2(JToken a) => new Vector2((float)a[0],(float)a[1]);
  static Vector3 V3(JToken a) => new Vector3((float)a[0],(float)a[1],(float)a[2]);
  sealed class Target {public JObject row;public MeshRenderer renderer;public MeshFilter filter;public Material[] oldMaterials;public string path,group;}
  sealed class State {public Scene scene;public StaticRenderChunks chunks;public JObject contract,package,doorReceipt;public List<Target> targets;public Dictionary<string,Material> oldMaterials;public string packageSource,doorReceiptPath;}
  static string ComponentState(Component c,HashSet<MeshRenderer> targets)
  {
   var json=EditorJsonUtility.ToJson(c);
   if(c is MeshRenderer r&&targets.Contains(r)) {var o=JObject.Parse(json);if(!o.Remove("m_Materials"))throw new InvalidDataException("Renderer material serialization changed.");return o.ToString(Formatting.None);}
   return json;
  }
  static string Preserve(State s)
  {
   if(All<ActorAnimation>(s.scene).Count()!=9||All<AmbientWalker>(s.scene).Count()!=4||All<PlayerMotor>(s.scene).Count()!=1)throw new InvalidDataException("Require nine actors, four routes and one player.");
   var changed=new HashSet<MeshRenderer>(s.targets.Select(t=>t.renderer));var generated=s.chunks.generatedRoot;
   return JsonConvert.SerializeObject(new {
    gameplay=DistrictCityPass.GameplaySignature(),
    transforms=All<Transform>(s.scene).Where(t=>!generated||!t.IsChildOf(generated)).OrderBy(PathOf,StringComparer.Ordinal).Select(t=>new {path=PathOf(t),local=Enumerable.Range(0,16).Select(i=>Matrix4x4.TRS(t.localPosition,t.localRotation,t.localScale)[i]).ToArray(),t.gameObject.activeSelf,t.gameObject.layer,t.gameObject.tag}),
    components=All<Component>(s.scene).Where(c=>c&&!(c is Transform)&&c!=s.chunks&&(!generated||!c.transform.IsChildOf(generated))).OrderBy(c=>PathOf(c.transform)+"/"+c.GetType().FullName,StringComparer.Ordinal).Select(c=>new {path=PathOf(c.transform),type=c.GetType().FullName,json=ComponentState(c,changed)})
   });
  }
  static void SameHash(string path,string hash,string label) {if(!File.Exists(path)||Sha(path)!=hash)throw new InvalidDataException(label+": "+path);}
  static State Preflight(string packageRevision,string doorFrontRevision,bool freshChunks)
  {
   Safe(packageRevision);Safe(doorFrontRevision);var scene=SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||EditorApplication.isCompiling||EditorApplication.isUpdating||scene.isDirty||SceneManager.sceneCount!=1||scene.path!=ImportBaseline.ScenePath)throw new InvalidOperationException("Open the clean saved AthenHill scene in idle Edit mode.");
   var chunks=Object.FindAnyObjectByType<StaticRenderChunks>();
   if(!chunks||chunks.gameObject.scene!=scene||chunks.editingSources||chunks.sources==null||chunks.sourceVisibility==null||chunks.sources.Length!=chunks.sourceVisibility.Length)throw new InvalidDataException("Require the saved source renderer roster outside ShowSources mode.");
   if(freshChunks&&chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks))throw new InvalidDataException("Rebuild current source chunks before Apply.");
   var contract=JObject.Parse(File.ReadAllText(ContractPath));
   if((int)contract["schema"]!=1||contract["targets"].Count()!=111||contract["groups"].Count()!=4)throw new InvalidDataException("Exact 111-slot coating contract required.");
   string receiptPath=Path.Combine(Repo,"unity/evidence/reference-street/20260910/door-front-lit-"+doorFrontRevision+"/installed.json");var receipt=JObject.Parse(File.ReadAllText(receiptPath));
   if((string)receipt["contractSha256"]!=Sha(Path.Combine(Art,"front-lit-contract.json"))||receipt["targets"].Count()!=12)throw new InvalidDataException("Expected completed DoorFrontLitPass receipt with exact twelve receivers.");
   string source=Path.Combine(Art,packageRevision);var package=JObject.Parse(File.ReadAllText(Path.Combine(source,"coating-manifest.json")));
   if((int)package["schema"]!=1||(string)package["packageRevision"]!=packageRevision||(string)package["contractSha256"]!=Sha(ContractPath)||(int)package["sourceReadbackChecksPassed"]!=6)throw new InvalidDataException("Packager contract/readback changed.");
   string original=Path.Combine(Art,Safe((string)package["sourceRevision"]));SameHash(Path.Combine(original,"manifest.json"),(string)package["sourceManifestSha256"],"Authored source manifest changed");SameHash(Path.Combine(original,"color-readback-guard.json"),(string)package["sourceReadbackSha256"],"Source readback evidence changed");
   string recipeFile=(string)package["recipeFile"];if(Path.GetFileName(recipeFile)!=recipeFile||!recipeFile.EndsWith(".json",StringComparison.Ordinal))throw new InvalidDataException("Invalid source recipe path.");SameHash(Path.Combine(Art,recipeFile),(string)package["recipeSha256"],"Authored recipe changed");
   string frontSource=Path.Combine(Art,doorFrontRevision,"composite-manifest.json");SameHash(frontSource,Sha(Path.Combine(Path.GetDirectoryName(receiptPath),"composite-manifest.json")),"Composed source manifest differs from installed receipt");var composite=JObject.Parse(File.ReadAllText(frontSource));
   foreach(JObject family in composite["families"])foreach(JObject map in family["maps"])SameHash("Assets/AthenHill/Art/ReferenceStreet/20260910/DoorFrontLit/"+doorFrontRevision+"/"+(string)family["family"]+"/"+(string)map["file"],(string)map["sha256"],"Installed unique front map changed");
   if((string)composite["sourceRevision"]!=(string)package["sourceRevision"]||(string)composite["sourceManifestSha256"]!=(string)package["sourceManifestSha256"])throw new InvalidDataException("Door fronts and quiet coating must use the same authored source revision.");
   var familyNames=package["families"].Select(f=>(string)f["family"]).OrderBy(x=>x).ToArray();if(!familyNames.SequenceEqual(new[]{"CoatedSteel","ShutterSteel"}))throw new InvalidDataException("Exact two source families required.");
   foreach(JObject family in package["families"])
   {
    if((int)family["width"]!=4096||(int)family["height"]!=4096||(float)family["physicalTileMetres"]!=4)throw new InvalidDataException("Full authored 4096/4m source expected.");
    if(!family["maps"].Select(m=>(string)m["channel"]).OrderBy(x=>x).SequenceEqual(new[]{"BaseColor","MetalSmooth","Normal"}))throw new InvalidDataException("Three exact URP map channels required.");
    foreach(JObject map in family["maps"])
    {
     string file=(string)map["file"],channel=(string)map["channel"];
     if(file!=channel+".png"||(int)map["bitDepth"]!=16||(string)map["space"]!=(channel=="BaseColor"?"sRGB":"linear")||(channel=="MetalSmooth"&&(bool?)map["integerRoundtripExact"]!=true))throw new InvalidDataException("Map schema/packing mismatch.");
     SameHash(Path.Combine(source,(string)family["family"],file),(string)map["sha256"],"Packaged map changed");
    }
   }
   var mats=new Dictionary<string,Material>();
   foreach(JObject group in contract["groups"])
   {
    string name=(string)group["name"],path=(string)group["sourceMaterial"];SameHash(path,(string)group["sourceMaterialSha256"],"Old material changed");SameHash(path+".meta",(string)group["sourceMaterialMetaSha256"],"Old material metadata changed");var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
    if(!mat||mat.shader.name!="Universal Render Pipeline/Lit"||AssetDatabase.AssetPathToGUID(path)!=(string)group["sourceMaterialGuid"]||mat.GetTextureScale("_BaseMap")!=V2(group["baseScale"])||mat.GetTextureOffset("_BaseMap")!=V2(group["baseOffset"]))throw new InvalidDataException("Material/physical UV contract changed: "+name);
    mats.Add(name,mat);
   }
   var targets=new List<Target>();
   foreach(JObject row in contract["targets"])
   {
    string path=(string)row["path"],group=(string)row["group"];var found=chunks.sources.OfType<MeshRenderer>().Where(r=>r&&PathOf(r.transform)==path).ToArray();
    if(found.Length!=1)throw new InvalidDataException("Exact source path missing/ambiguous: "+path);var r=found[0];var filter=r.GetComponent<MeshFilter>();var mesh=filter?filter.sharedMesh:null;string front=(string)row["doorFrontFamily"];
    if(!mesh||!r.gameObject.activeInHierarchy||!chunks.sourceVisibility[Array.IndexOf(chunks.sources,r)]||(int)row["slot"]!=0||r.sharedMaterials.Length!=(front==null?1:2)||r.sharedMaterials[0]!=mats[group])throw new InvalidDataException("Eligible source/slot changed: "+path);
    SameHash((string)row["meshAsset"],(string)row["meshSha256"],"Preserved original mesh changed");SameHash((string)row["meshAsset"]+".meta",(string)row["meshMetaSha256"],"Original mesh metadata changed");
    if(front==null) {if(AssetDatabase.GetAssetPath(mesh)!=(string)row["meshAsset"]||mesh.subMeshCount!=1)throw new InvalidDataException("Original non-door mesh binding changed: "+path);}
    else
    {
     var rows=receipt["targets"].Cast<JObject>().Where(x=>(string)x["path"]==path).ToArray();if(rows.Length!=1)throw new InvalidDataException("Missing exact installed door receipt: "+path);var rr=rows[0];string derivative=(string)rr["derivative"],frontMat="Assets/AthenHill/Art/ReferenceStreet/20260910/DoorFrontLit/"+doorFrontRevision+"/"+front+"/Surface.mat";
     if((string)rr["source"]!=(string)row["meshAsset"]||AssetDatabase.GetAssetPath(mesh)!=derivative||!derivative.StartsWith("Assets/AthenHill/Art/ReferenceStreet/20260910/DoorFrontLit/"+doorFrontRevision+"/",StringComparison.Ordinal)||mesh.subMeshCount!=2||mesh.vertexCount!=(int)rr["vertices"]||mesh.GetIndexCount(1)!=6||AssetDatabase.GetAssetPath(r.sharedMaterials[1])!=frontMat||rr["materials"].Count()!=2||(string)rr["materials"][1]!=frontMat)throw new InvalidDataException("Installed door split/front binding changed: "+path);
     SameHash(derivative,(string)rr["derivativeSha256"],"Installed derivative changed/missing receipt hash");SameHash(derivative+".meta",(string)rr["derivativeMetaSha256"],"Installed derivative metadata changed");SameHash(frontMat,(string)rr["materialHashes"]?[frontMat],"Installed unique front material changed/missing hash");
    }
    if(group=="ShutterSteel")
    {
     var expected=row["registeredWorldPositions"];var vertices=mesh.vertices;if(vertices.Length!=expected.Count())throw new InvalidDataException("Shutter source vertex order/count changed.");
     for(int i=0;i<vertices.Length;i++)if((r.transform.TransformPoint(vertices[i])-V3(expected[i])).magnitude>(float)row["worldPositionToleranceMetres"])throw new InvalidDataException("Shutter lip-wear world registration changed: "+path);
    }
    targets.Add(new Target{row=row,renderer=r,filter=filter,oldMaterials=r.sharedMaterials,path=path,group=group});
   }
   if(targets.Select(t=>t.path).Distinct().Count()!=111||targets.Count(t=>t.oldMaterials.Length==2)!=12)throw new InvalidDataException("Exact target roster differs.");
   foreach(JObject group in contract["groups"])
   {
    string name=(string)group["name"];var expected=targets.Where(t=>t.group==name).Select(t=>t.path).OrderBy(x=>x).ToArray();
    var actual=chunks.sources.OfType<MeshRenderer>().Where(r=>r&&r.gameObject.activeInHierarchy&&chunks.sourceVisibility[Array.IndexOf(chunks.sources,r)]&&r.sharedMaterials.Length>0&&r.sharedMaterials[0]==mats[name]).Select(r=>PathOf(r.transform)).OrderBy(x=>x).ToArray();
    if(expected.Length!=(int)group["count"]||!expected.SequenceEqual(actual))throw new InvalidDataException("Current eligible material roster differs: "+name);
   }
   return new State{scene=scene,chunks=chunks,contract=contract,package=package,doorReceipt=receipt,targets=targets,oldMaterials=mats,packageSource=source,doorReceiptPath=receiptPath};
  }
  static Dictionary<string,string> OriginalAssets(State s)
  {
   var assets=new HashSet<string>();
   foreach(var t in s.targets) {assets.Add((string)t.row["meshAsset"]);assets.Add(AssetDatabase.GetAssetPath(t.filter.sharedMesh));foreach(var m in t.oldMaterials)foreach(var p in AssetDatabase.GetDependencies(AssetDatabase.GetAssetPath(m),false))if(File.Exists(p))assets.Add(p);foreach(var m in t.oldMaterials)assets.Add(AssetDatabase.GetAssetPath(m));}
   foreach(string p in assets.ToArray())if(File.Exists(p+".meta"))assets.Add(p+".meta");return assets.OrderBy(x=>x).ToDictionary(x=>x,Sha);
  }
  public static void Inspect(string packageRevision,string doorFrontRevision,string evidenceRevision)
  {
   Safe(evidenceRevision);var s=Preflight(packageRevision,doorFrontRevision,false);string folder=Path.Combine(Repo,"unity/evidence/reference-street/20260910/metal-coating-"+evidenceRevision);if(Directory.Exists(folder))throw new IOException("Use fresh evidence revision.");
   string preserved=Preserve(s);Directory.CreateDirectory(folder);Write(Path.Combine(folder,"preflight.json"),new {utc=DateTime.UtcNow,packageRevision,doorFrontRevision,sceneSha256=Sha(s.scene.path),contractSha256=Sha(ContractPath),groups=s.targets.GroupBy(t=>t.group).Select(g=>new{group=g.Key,slots=g.Count()}),slot0Count=s.targets.Count,preservedDoorFrontSlots=12,chunksFresh=s.chunks.sourceFingerprint==StaticRenderChunksEditor.Fingerprint(s.chunks),originalAssetHashes=OriginalAssets(s),noSceneOrAssetsMutation=!s.scene.isDirty,nativeAccepted=false});File.WriteAllText(Path.Combine(folder,"preserved-components.json"),preserved);
  }
  static Texture2D Import(string path,string channel)
  {
   AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);var i=(TextureImporter)AssetImporter.GetAtPath(path);i.GetSourceTextureWidthAndHeight(out int w,out int h);if(w!=4096||h!=4096)throw new InvalidDataException("Full 4K source dimensions changed.");
   i.textureType=channel=="Normal"?TextureImporterType.NormalMap:TextureImporterType.Default;i.sRGBTexture=channel=="BaseColor";i.convertToNormalmap=false;i.flipGreenChannel=false;i.alphaSource=TextureImporterAlphaSource.FromInput;i.alphaIsTransparency=false;i.npotScale=TextureImporterNPOTScale.None;i.maxTextureSize=4096;i.mipmapEnabled=true;i.streamingMipmaps=true;i.anisoLevel=8;i.wrapMode=TextureWrapMode.Repeat;i.filterMode=FilterMode.Trilinear;i.textureCompression=TextureImporterCompression.CompressedHQ;i.crunchedCompression=false;i.isReadable=false;i.ClearPlatformTextureSettings("Standalone");i.SaveAndReimport();var t=AssetDatabase.LoadAssetAtPath<Texture2D>(path);if(t.width!=w||t.height!=h)throw new InvalidDataException("Imported texture was reduced.");return t;
  }
  // Explicit revisions only: call after DoorFrontLitPass.Apply(matching doorFrontRevision).
  public static void Apply(string packageRevision,string doorFrontRevision)
  {
   var s=Preflight(packageRevision,doorFrontRevision,true);if(QualitySettings.globalTextureMipmapLimit!=0)throw new InvalidDataException("Full-resolution import verification requires mip limit0.");
   string folder="Assets/AthenHill/Art/ReferenceStreet/20260910/MetalCoating/"+packageRevision,evidence=Path.Combine(Repo,"unity/evidence/reference-street/20260910/metal-coating-"+packageRevision);if(Directory.Exists(folder)||Directory.Exists(evidence))throw new IOException("Use fresh asset/evidence revision.");
   string keep=Preserve(s);var originals=OriginalAssets(s);var meshes=s.targets.ToDictionary(t=>t.path,t=>t.filter.sharedMesh);
   Directory.CreateDirectory(evidence);Directory.CreateDirectory(folder);File.Copy(ContractPath,Path.Combine(evidence,"contract.json"),false);File.Copy(Path.Combine(s.packageSource,"coating-manifest.json"),Path.Combine(evidence,"coating-manifest.json"),false);File.Copy(s.doorReceiptPath,Path.Combine(evidence,"door-front-installed.json"),false);File.WriteAllText(Path.Combine(evidence,"preserved-before.json"),keep);Write(Path.Combine(evidence,"original-assets.json"),originals);EditorSceneManager.SaveScene(s.scene,Path.Combine(evidence,"before-scene.unity"),true);
   try
   {
    var maps=new Dictionary<string,Dictionary<string,Texture2D>>();foreach(JObject family in s.package["families"])
    {
     string name=(string)family["family"],dest=folder+"/"+name;Directory.CreateDirectory(dest);var familyMaps=new Dictionary<string,Texture2D>();foreach(JObject map in family["maps"]){string ch=(string)map["channel"],file=(string)map["file"];File.Copy(Path.Combine(s.packageSource,name,file),dest+"/"+file,false);familyMaps[ch]=Import(dest+"/"+file,ch);}maps.Add(name,familyMaps);
    }
    var materials=new Dictionary<string,Material>();foreach(JObject group in s.contract["groups"])
    {
     string name=(string)group["name"];var old=s.oldMaterials[name];var texture=maps[(string)group["sourceFamily"]];var mat=new Material(old){name=name+" v4 "+packageRevision};
     mat.SetTexture("_BaseMap",texture["BaseColor"]);mat.SetTexture("_MainTex",texture["BaseColor"]);mat.SetTexture("_BumpMap",texture["Normal"]);mat.SetTexture("_MetallicGlossMap",texture["MetalSmooth"]);mat.SetFloat("_BumpScale",1);mat.SetFloat("_Metallic",1);mat.SetFloat("_Smoothness",1);mat.SetFloat("_SmoothnessTextureChannel",0);
     BaseShaderGUI.SetMaterialKeywords(mat,UnityEditor.Rendering.Universal.ShaderGUI.LitGUI.SetMaterialKeywords,m=>{m.DisableKeyword("_DETAIL_MULX2");m.DisableKeyword("_DETAIL_SCALED");});
     foreach(string property in new[]{"_BaseMap","_MainTex"})if(mat.GetTextureScale(property)!=old.GetTextureScale(property)||mat.GetTextureOffset(property)!=old.GetTextureOffset(property))throw new InvalidDataException("Texture scale/offset was changed.");
     if(mat.GetColor("_BaseColor")!=old.GetColor("_BaseColor")||!mat.IsKeywordEnabled("_NORMALMAP")||!mat.IsKeywordEnabled("_METALLICSPECGLOSSMAP")||mat.IsKeywordEnabled("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A"))throw new InvalidDataException("Standard Lit material validation failed.");AssetDatabase.CreateAsset(mat,folder+"/"+name+".mat");materials.Add(name,mat);
    }
    s.chunks.ShowSources(true);foreach(var t in s.targets){var slots=(Material[])t.oldMaterials.Clone();slots[0]=materials[t.group];t.renderer.sharedMaterials=slots;EditorUtility.SetDirty(t.renderer);PrefabUtility.RecordPrefabInstancePropertyModifications(t.renderer);}
    AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(s.chunks);
    if(Preserve(s)!=keep)throw new InvalidDataException("Untouched component/root/collider or renderer setting changed; preserve failure evidence and restore backup before continuing.");
    foreach(var t in s.targets)if(t.filter.sharedMesh!=meshes[t.path]||t.renderer.sharedMaterials.Length!=t.oldMaterials.Length||t.renderer.sharedMaterials[0]!=materials[t.group]||!t.renderer.sharedMaterials.Skip(1).SequenceEqual(t.oldMaterials.Skip(1)))throw new InvalidDataException("Mesh binding or unique door-front slot changed.");
    foreach(var item in originals)SameHash(item.Key,item.Value,"Original source/importer asset changed");if(s.chunks.editingSources||s.chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(s.chunks))throw new InvalidDataException("Derived chunks are stale.");
    EditorSceneManager.SaveScene(s.scene);Write(Path.Combine(evidence,"installed.json"),new {utc=DateTime.UtcNow,packageRevision,doorFrontRevision,sceneSha256=Sha(s.scene.path),contractSha256=Sha(ContractPath),sourceFingerprint=s.chunks.sourceFingerprint,targets=s.targets.Select(t=>new {t.path,t.group,changedSlot=0,mesh=AssetDatabase.GetAssetPath(t.filter.sharedMesh),materials=t.renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath)}),newMaterials=materials.ToDictionary(k=>k.Key,k=>new {path=AssetDatabase.GetAssetPath(k.Value),sha256=Sha(AssetDatabase.GetAssetPath(k.Value)),scale=k.Value.GetTextureScale("_BaseMap")}),preservedMeshesAndOtherMaterialSlots=true,preservedOriginalAssetHashes=true,preservedSerializedComponents=true,sourcePacking="Full RGBA16 exact integer source packing; runtime HQ compression is separately inspected",nativeAccepted=false});
   }
   catch(Exception e){Write(Path.Combine(evidence,"failure.json"),new {utc=DateTime.UtcNow,error=e.ToString(),backup="before-scene.unity",status="Failed evidence retained; no automatic deletion or acceptance."});throw;}
  }
 }
}
#endif
