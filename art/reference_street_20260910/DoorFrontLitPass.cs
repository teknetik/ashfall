#if UNITY_EDITOR
// Staged Editor-only: root operator explicitly copies/runs after source review.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
 public static class DoorFrontLitPass
 {
  static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
  static string Art => Path.Combine(Repo,"art/reference_street_20260910/metal-v4");
  static string ContractPath => Path.Combine(Art,"front-lit-contract.json");
  static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t,null);
  static string Sha(string p) { using(var h=SHA256.Create()) using(var f=File.OpenRead(p)) return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant(); }
  static void Write(string p,object o) => File.WriteAllText(p,JsonConvert.SerializeObject(o,Formatting.Indented));
  static string Safe(string s) { if(string.IsNullOrEmpty(s)||s.Any(c=>!char.IsLetterOrDigit(c)&&c!='-'&&c!='_')) throw new ArgumentException("Use a simple new revision name.");return s; }
  static IEnumerable<T> All<T>(Scene scene) where T:Component => scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<T>(true));
  static Vector3 V(JToken a) => new Vector3((float)a[0],(float)a[1],(float)a[2]);
  static string Preserve(Scene scene,StaticRenderChunks chunks,HashSet<Component> changed)
  {
   var actors=All<ActorAnimation>(scene).ToArray();var routes=All<AmbientWalker>(scene).ToArray();
   if(actors.Length!=9||routes.Length!=4||All<PlayerMotor>(scene).Count()!=1) throw new InvalidDataException("Expected nine actors, four routes and one player.");
   return JsonConvert.SerializeObject(new {
    gameplay=DistrictCityPass.GameplaySignature(),
    transforms=All<Transform>(scene).Where(t=>!chunks.generatedRoot||!t.IsChildOf(chunks.generatedRoot)).OrderBy(PathOf,StringComparer.Ordinal)
     .Select(t=>new {path=PathOf(t),local=Enumerable.Range(0,16).Select(i=>Matrix4x4.TRS(t.localPosition,t.localRotation,t.localScale)[i]).ToArray(),t.gameObject.activeSelf,t.gameObject.layer,t.gameObject.tag}),
    components=All<Component>(scene).Where(c=>c&&!(c is Transform)&&c!=chunks&&!changed.Contains(c)&&(!chunks.generatedRoot||!c.transform.IsChildOf(chunks.generatedRoot)))
     .OrderBy(c=>PathOf(c.transform)+"/"+c.GetType().FullName,StringComparer.Ordinal).Select(c=>new {path=PathOf(c.transform),type=c.GetType().FullName,json=EditorJsonUtility.ToJson(c)})
   });
  }
  sealed class Target
  {
   public JObject record;public MeshRenderer renderer;public MeshFilter filter;public Mesh source;public Material oldMaterial;public JObject door;
   public int[] frontIDs,duplicateIDs;public string path;
  }
  static (Scene,StaticRenderChunks,JObject,List<Target>) Preflight(bool requireFreshChunks=true)
  {
   var scene=SceneManager.GetActiveScene();
   if(EditorApplication.isPlayingOrWillChangePlaymode||EditorApplication.isCompiling||EditorApplication.isUpdating||scene.isDirty||SceneManager.sceneCount!=1||scene.path!=ImportBaseline.ScenePath)
    throw new InvalidOperationException("Open the clean saved AthenHill scene in idle Edit mode.");
   var chunks=Object.FindAnyObjectByType<StaticRenderChunks>();
   if(!chunks||chunks.gameObject.scene!=scene||chunks.editingSources||chunks.sources==null||chunks.sourceVisibility==null||chunks.sources.Length!=chunks.sourceVisibility.Length) throw new InvalidOperationException("Require the saved source-renderer roster outside ShowSources editing mode.");
   // Dry geometry inspection is independent of unrelated source changes. Apply
   // still requires a current rebuild before it performs its own source edits.
   if(requireFreshChunks&&chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks)) throw new InvalidOperationException("Rebuild the current source render chunks before Apply; the historical whole-scene hash is not an installation lock.");
   var contract=JObject.Parse(File.ReadAllText(ContractPath));
   if((int)contract["schema"]!=1||(int)contract["duplicateVertices"]!=48||(int)contract["frontTriangles"]!=24) throw new InvalidDataException("Front contract changed.");
   var result=new List<Target>();
   foreach(JObject row in contract["targets"])
   {
    string path=(string)row["path"];var matches=chunks.sources.OfType<MeshRenderer>().Where(r=>r&&PathOf(r.transform)==path).ToArray();
    if(matches.Length!=1) throw new InvalidDataException("Exact receiver path missing/ambiguous: "+path);
    var r=matches[0];var filter=r.GetComponent<MeshFilter>();var mesh=filter?filter.sharedMesh:null;string matPath=(string)row["sourceMaterial"];
    if(!mesh||AssetDatabase.GetAssetPath(mesh)!=(string)row["meshAsset"]||Sha((string)row["meshAsset"])!=(string)row["meshSha256"]||Sha((string)row["meshAsset"]+".meta")!=(string)row["meshMetaSha256"])
     throw new InvalidDataException("Original source mesh/hash changed: "+path);
    if(r.sharedMaterials.Length!=1||AssetDatabase.GetAssetPath(r.sharedMaterial)!=matPath||AssetDatabase.AssetPathToGUID(matPath)!=(string)row["sourceMaterialGuid"]||Sha(matPath)!=(string)row["sourceMaterialSha256"]||r.sharedMaterial.shader.name!="Universal Render Pipeline/Lit")
     throw new InvalidDataException("Original coated material binding changed: "+path);
    if(!r.gameObject.activeInHierarchy||!chunks.sourceVisibility[Array.IndexOf(chunks.sources,r)]||!mesh.isReadable||mesh.subMeshCount!=1||mesh.blendShapeCount!=0||mesh.bindposes.Length!=0)
     throw new InvalidDataException("Expected active readable static source: "+path);
    var p=mesh.vertices;var n=mesh.normals;var uv=mesh.uv;var tangent=mesh.tangents;var tr=mesh.triangles;
    if(p.Length!=(int)row["vertices"]||tr.Length!=(int)row["triangles"]*3||n.Length!=p.Length||uv.Length!=p.Length||tangent.Length!=p.Length||!tr.SequenceEqual(row["originalIndices"].Values<int>())) throw new InvalidDataException("Topology/attributes changed: "+path);
    var matrix=r.transform.localToWorldMatrix;var normalMatrix=matrix.inverse.transpose;
    if(matrix.determinant<=0) throw new InvalidDataException("Unexpected reflected source transform: "+path);
    for(int i=0;i<p.Length;i++)
    {
     if((matrix.MultiplyPoint3x4(p[i])-V(row["worldPositions"][i])).magnitude>(float)row["worldPositionToleranceMetres"]||(normalMatrix.MultiplyVector(n[i]).normalized-V(row["worldNormals"][i])).magnitude>0.001f)
      throw new InvalidDataException("Saved world geometry/normal changed: "+path+" vertex "+i);
     var u=row["originalUV0"][i];if(Mathf.Abs(uv[i].x-(float)u[0])>0.000002f||Mathf.Abs(uv[i].y-(float)u[1])>0.000002f) throw new InvalidDataException("Saved UV0 changed: "+path);
     var tv=new Vector3(tangent[i].x,tangent[i].y,tangent[i].z);
     if(!float.IsFinite(tv.sqrMagnitude)||Mathf.Abs(tv.magnitude-1)>.001f||Mathf.Abs(n[i].magnitude-1)>.001f||Mathf.Abs(Vector3.Dot(tv,n[i]))>.001f||Mathf.Abs(Mathf.Abs(tangent[i].w)-1)>.001f) throw new InvalidDataException("Invalid source tangent: "+path);
    }
    var actualFront=new List<int>();
    for(int i=0;i<tr.Length;i+=3)
    {
     var a=matrix.MultiplyPoint3x4(p[tr[i]]);var b=matrix.MultiplyPoint3x4(p[tr[i+1]]);var c=matrix.MultiplyPoint3x4(p[tr[i+2]]);
     var gn=Vector3.Cross(b-a,c-a).normalized;
     bool plane=new[]{a.x,b.x,c.x}.All(x=>Mathf.Abs(x-(float)row["frontWorldX"])<(float)row["frontPlaneToleranceMetres"]);
     bool facing=Vector3.Dot(gn,Vector3.left)>(float)row["frontNormalDotMinimum"]&&Enumerable.Range(0,3).All(k=>Vector3.Dot(normalMatrix.MultiplyVector(n[tr[i+k]]).normalized,Vector3.left)>(float)row["frontNormalDotMinimum"]);
     if(plane&&facing) actualFront.Add(i/3);
    }
    var fronts=row["frontTriangleIDs"].Values<int>().ToArray();var duplicates=row["duplicateVertexIDs"].Values<int>().ToArray();
    if(fronts.Length!=2||duplicates.Length!=4||!fronts.SequenceEqual(actualFront)) throw new InvalidDataException("Exact planar front eligibility changed: "+path);
    var frontVertices=fronts.SelectMany(i=>tr.Skip(i*3).Take(3)).Distinct().OrderBy(i=>i).ToArray();var remainder=tr.Where((_,i)=>!fronts.Contains(i/3)).ToArray();
    if(!frontVertices.SequenceEqual(duplicates)||!frontVertices.Intersect(remainder).OrderBy(i=>i).SequenceEqual(duplicates)) throw new InvalidDataException("Expected four shared boundary vertices: "+path);
    foreach(var attr in new[]{VertexAttribute.TexCoord0,VertexAttribute.Tangent}) if(mesh.GetVertexAttributeFormat(attr)!=VertexAttributeFormat.Float32||mesh.GetVertexAttributeDimension(attr)!=(attr==VertexAttribute.Tangent?4:2)) throw new InvalidDataException("Only inspected float32 UV0/tangent layout is supported.");
    result.Add(new Target {record=row,renderer=r,filter=filter,source=mesh,oldMaterial=r.sharedMaterial,door=contract["doors"].Cast<JObject>().Single(d=>(string)d["family"]==(string)row["family"]),frontIDs=fronts,duplicateIDs=duplicates,path=path});
   }
   if(result.Count!=12||result.Select(t=>t.path).Distinct().Count()!=12) throw new InvalidDataException("Expected twelve exact coated receivers.");
   // Wear positions depend on real handles and hinges as well as the coated leaf.
   // This is a live installation check, not a prerequisite for source-map auditions.
   var sceneRenderers=All<MeshRenderer>(scene).ToArray();
   foreach(JObject door in contract["doors"])
   {
    var handle=door["handle"];string path=(string)handle["sourcePath"];var candidates=sceneRenderers.Where(r=>PathOf(r.transform)==path).ToArray();
    if(candidates.Length!=1||!candidates[0].gameObject.activeInHierarchy||(candidates[0].bounds.min-V(handle["bounds"]["min"])).magnitude>.00003f||(candidates[0].bounds.max-V(handle["bounds"]["max"])).magnitude>.00003f) throw new InvalidDataException("Actual handle registration changed: "+path);
    foreach(JObject hinge in door["hinges"])
    {
     string hp=(string)hinge["sourcePath"];var hs=sceneRenderers.Where(r=>PathOf(r.transform)==hp).ToArray();
     if(hs.Length!=1||!hs[0].gameObject.activeInHierarchy||Mathf.Abs(hs[0].bounds.center.z-(float)hinge["z"])>.00003f||Mathf.Abs(hs[0].bounds.center.y-(float)hinge["y"])>.00003f) throw new InvalidDataException("Actual hinge registration changed: "+hp);
    }
   }
   return(scene,chunks,contract,result);
  }
  static void FloatBytes(byte[] buffer,int offset,float value) { var bytes=BitConverter.GetBytes(value);Array.Copy(bytes,0,buffer,offset,4); }
  static Mesh Split(Target t)
  {
   var source=t.source;int count=source.vertexCount;var oldTr=source.triangles;var remap=t.duplicateIDs.Select((id,i)=>(id,index:count+i)).ToDictionary(x=>x.id,x=>x.index);
   int[] back=oldTr.Where((_,i)=>!t.frontIDs.Contains(i/3)).ToArray(),front=t.frontIDs.SelectMany(i=>oldTr.Skip(i*3).Take(3)).Select(i=>remap[i]).ToArray();
   var oldBuffers=new List<byte[]>();using(var read=Mesh.AcquireReadOnlyMeshData(source)) for(int s=0;s<source.vertexBufferCount;s++) oldBuffers.Add(read[0].GetVertexData<byte>(s).ToArray());
   var write=Mesh.AllocateWritableMeshData(1);bool disposed=false;Mesh mesh=null;
   try
   {
    var data=write[0];data.SetVertexBufferParams(count+4,source.GetVertexAttributes());data.SetIndexBufferParams(oldTr.Length,source.indexFormat);
    int us=source.GetVertexAttributeStream(VertexAttribute.TexCoord0),ts=source.GetVertexAttributeStream(VertexAttribute.Tangent);int uo=source.GetVertexAttributeOffset(VertexAttribute.TexCoord0),to=source.GetVertexAttributeOffset(VertexAttribute.Tangent);
    var normals=source.normals;var vertices=source.vertices;var inverse=t.renderer.transform.worldToLocalMatrix;var world=t.renderer.transform.localToWorldMatrix;
    float z0=(float)t.door["worldZRange"][0],z1=(float)t.door["worldZRange"][1],y0=(float)t.door["worldYRange"][0],y1=(float)t.door["worldYRange"][1];
    var buffers=new List<byte[]>();
    for(int stream=0;stream<source.vertexBufferCount;stream++)
    {
     int stride=source.GetVertexBufferStride(stream);var bytes=new byte[(count+4)*stride];Array.Copy(oldBuffers[stream],bytes,oldBuffers[stream].Length);
     for(int j=0;j<4;j++)
     {
      int old=t.duplicateIDs[j],next=count+j;Array.Copy(oldBuffers[stream],old*stride,bytes,next*stride,stride);
      var p=world.MultiplyPoint3x4(vertices[old]);
      if(stream==us) {FloatBytes(bytes,next*stride+uo,(p.z-z0)/(z1-z0));FloatBytes(bytes,next*stride+uo+4,(p.y-y0)/(y1-y0));}
      if(stream==ts)
      {
       var n=normals[old];var u=inverse.MultiplyVector(Vector3.forward);u=(u-n*Vector3.Dot(n,u)).normalized;var v=inverse.MultiplyVector(Vector3.up);
       float handed=Vector3.Dot(Vector3.Cross(n,u),v)>=0?1:-1;
       if(Vector3.Dot(world.MultiplyVector(u).normalized,Vector3.forward)<.99999f) throw new InvalidDataException("New planar tangent points away from +worldZ.");
       FloatBytes(bytes,next*stride+to,u.x);FloatBytes(bytes,next*stride+to+4,u.y);FloatBytes(bytes,next*stride+to+8,u.z);FloatBytes(bytes,next*stride+to+12,handed);
      }
     }
     data.GetVertexData<byte>(stream).CopyFrom(bytes);buffers.Add(bytes);
    }
    var indices=back.Concat(front).ToArray();
    if(source.indexFormat==IndexFormat.UInt32)data.GetIndexData<uint>().CopyFrom(indices.Select(i=>(uint)i).ToArray());else data.GetIndexData<ushort>().CopyFrom(indices.Select(i=>checked((ushort)i)).ToArray());
    data.subMeshCount=2;data.SetSubMesh(0,new SubMeshDescriptor(0,back.Length){bounds=source.bounds,firstVertex=0,vertexCount=count+4},MeshUpdateFlags.DontRecalculateBounds);
    data.SetSubMesh(1,new SubMeshDescriptor(back.Length,front.Length){bounds=source.bounds,firstVertex=0,vertexCount=count+4},MeshUpdateFlags.DontRecalculateBounds);
    mesh=Object.Instantiate(source);mesh.name=source.name+" planar front v1";Mesh.ApplyAndDisposeWritableMeshData(write,mesh,MeshUpdateFlags.DontRecalculateBounds);disposed=true;mesh.bounds=source.bounds;
    using(var check=Mesh.AcquireReadOnlyMeshData(mesh)) for(int stream=0;stream<source.vertexBufferCount;stream++)
    {
     var actual=check[0].GetVertexData<byte>(stream).ToArray();if(!actual.SequenceEqual(buffers[stream])||!actual.Take(oldBuffers[stream].Length).SequenceEqual(oldBuffers[stream]))throw new InvalidDataException("Vertex-buffer preservation failed.");
     int stride=source.GetVertexBufferStride(stream);
     for(int j=0;j<4;j++)for(int b=0;b<stride;b++)
     {
      bool changed=(stream==us&&b>=uo&&b<uo+8)||(stream==ts&&b>=to&&b<to+16);
      if(!changed&&actual[(count+j)*stride+b]!=oldBuffers[stream][t.duplicateIDs[j]*stride+b]) throw new InvalidDataException("Untouched duplicate attribute changed.");
     }
    }
    if(!mesh.GetIndices(0).SequenceEqual(back)||!mesh.GetIndices(1).Select(i=>t.duplicateIDs[i-count]).SequenceEqual(t.frontIDs.SelectMany(i=>oldTr.Skip(i*3).Take(3))))throw new InvalidDataException("Triangle winding/connectivity changed.");
    return mesh;
   }
   catch {if(mesh)Object.DestroyImmediate(mesh);throw;}
   finally {if(!disposed)write.Dispose();}
  }
  public static void Inspect(string revision="preflight-v1")
  {
   Safe(revision);var (scene,chunks,contract,targets)=Preflight(false);string dir=Path.Combine(Repo,"unity/evidence/reference-street/20260910/door-front-lit-"+revision);
   if(Directory.Exists(dir))throw new IOException("Evidence folder already exists.");Directory.CreateDirectory(dir);var results=new List<object>();
   foreach(var t in targets) {var m=Split(t);results.Add(new {t.path,oldVertices=t.source.vertexCount,newVertices=m.vertexCount,oldTriangles=t.source.triangles.Length/3,newTriangles=m.triangles.Length/3,frontTriangles=m.GetIndexCount(1)/3,originalVertexBytesPreserved=true,duplicateNonUVTangentAttributesPreserved=true});Object.DestroyImmediate(m);}
   Write(Path.Combine(dir,"preflight.json"),new {utc=DateTime.UtcNow,scene=scene.path,sceneSha256=Sha(scene.path),contractSha256=Sha(ContractPath),results,chunksFresh=chunks.sourceFingerprint==StaticRenderChunksEditor.Fingerprint(chunks),staleChunksPermittedForReadOnlyInspection=true,sceneUnchanged=!scene.isDirty});
  }
  static Texture2D Import(string path,string channel,int width,int height)
  {
   AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);var i=(TextureImporter)AssetImporter.GetAtPath(path);i.GetSourceTextureWidthAndHeight(out int w,out int h);
   if(w!=width||h!=height)throw new InvalidDataException("Composed dimensions mismatch.");i.textureType=channel=="Normal"?TextureImporterType.NormalMap:TextureImporterType.Default;i.sRGBTexture=channel=="BaseColor";
   i.convertToNormalmap=false;i.flipGreenChannel=false;i.alphaSource=TextureImporterAlphaSource.FromInput;i.alphaIsTransparency=false;i.npotScale=TextureImporterNPOTScale.None;i.maxTextureSize=Mathf.NextPowerOfTwo(Mathf.Max(w,h));
   i.mipmapEnabled=true;i.streamingMipmaps=true;i.anisoLevel=8;i.wrapMode=TextureWrapMode.Clamp;i.filterMode=FilterMode.Trilinear;i.textureCompression=TextureImporterCompression.CompressedHQ;i.crunchedCompression=false;i.isReadable=false;i.ClearPlatformTextureSettings("Standalone");i.SaveAndReimport();
   var tex=AssetDatabase.LoadAssetAtPath<Texture2D>(path);if(tex.width!=w||tex.height!=h)throw new InvalidDataException("Full composed source dimensions not imported: "+path);return tex;
  }
  public static void Apply(string composedRevision="candidate-v1-litfront-v1")
  {
   Safe(composedRevision);var (scene,chunks,contract,targets)=Preflight();string folder="Assets/AthenHill/Art/ReferenceStreet/20260910/DoorFrontLit/"+composedRevision;
   string evidence=Path.Combine(Repo,"unity/evidence/reference-street/20260910/door-front-lit-"+composedRevision),source=Path.Combine(Art,composedRevision);
   if(Directory.Exists(folder)||Directory.Exists(evidence))throw new IOException("Use a fresh candidate/evidence revision.");
   if(QualitySettings.globalTextureMipmapLimit!=0)throw new InvalidDataException("Import validation requires full-resolution mip limit0.");
   var manifest=JObject.Parse(File.ReadAllText(Path.Combine(source,"composite-manifest.json")));
   if((string)manifest["contractSha256"]!=Sha(ContractPath)||(string)manifest["normalBasis"]!="U=+worldZ,V=+worldY,N=-worldX")throw new InvalidDataException("Compositor contract/basis changed.");
   if(manifest["families"].Count()!=4||!manifest["families"].Select(f=>(string)f["family"]).OrderBy(x=>x).SequenceEqual(contract["doors"].Select(d=>(string)d["family"]).OrderBy(x=>x)))throw new InvalidDataException("Exact four composed families required.");
   foreach(JObject row in manifest["families"])foreach(JObject map in row["maps"])
   {
    string name=(string)map["file"];if(Path.GetFileName(name)!=name||Sha(Path.Combine(source,(string)row["family"],name))!=(string)map["sha256"])throw new InvalidDataException("Composed map hash/path changed.");
   }
   var changed=new HashSet<Component>(targets.SelectMany(t=>new Component[]{t.renderer,t.filter}));string keep=Preserve(scene,chunks,changed);var derivatives=targets.Select(t=>Split(t)).ToArray();
   Directory.CreateDirectory(evidence);Directory.CreateDirectory(folder);File.Copy(ContractPath,Path.Combine(evidence,"contract.json"),false);File.Copy(Path.Combine(source,"composite-manifest.json"),Path.Combine(evidence,"composite-manifest.json"),false);
   File.WriteAllText(Path.Combine(evidence,"preserved-before.json"),keep);EditorSceneManager.SaveScene(scene,Path.Combine(evidence,"before-scene.unity"),true);
   try
   {
    var materials=new Dictionary<string,Material>();
    foreach(JObject family in manifest["families"])
    {
     string name=(string)family["family"];if(!contract["doors"].Any(d=>(string)d["family"]==name)||materials.ContainsKey(name))throw new InvalidDataException("Unexpected composed material family.");
     var old=targets.First(t=>(string)t.record["family"]==name).oldMaterial;string dest=folder+"/"+name;Directory.CreateDirectory(dest);var maps=new Dictionary<string,Texture2D>();
     foreach(JObject map in family["maps"]){string ch=(string)map["channel"],fn=(string)map["file"];if(!new[]{"BaseColor","Normal","MetalSmooth"}.Contains(ch)||maps.ContainsKey(ch))throw new InvalidDataException("Unexpected composed channel.");File.Copy(Path.Combine(source,name,fn),dest+"/"+fn,false);maps[ch]=Import(dest+"/"+fn,ch,(int)family["width"],(int)family["height"]);}
     if(maps.Count!=3)throw new InvalidDataException("Expected three URP map bindings.");
     var mat=new Material(old){name=name+" unique front v4"};mat.SetTexture("_BaseMap",maps["BaseColor"]);mat.SetTexture("_MainTex",maps["BaseColor"]);mat.SetColor("_BaseColor",Color.white);mat.SetColor("_Color",Color.white);mat.SetTextureScale("_BaseMap",Vector2.one);mat.SetTextureOffset("_BaseMap",Vector2.zero);mat.SetTextureScale("_MainTex",Vector2.one);mat.SetTextureOffset("_MainTex",Vector2.zero);
     mat.SetTexture("_BumpMap",maps["Normal"]);mat.SetFloat("_BumpScale",1);mat.SetTexture("_MetallicGlossMap",maps["MetalSmooth"]);mat.SetFloat("_Metallic",1);mat.SetFloat("_Smoothness",1);mat.SetFloat("_SmoothnessTextureChannel",0);
     foreach(string ch in new[]{"_DetailMask","_DetailAlbedoMap","_DetailNormalMap","_ParallaxMap","_OcclusionMap","_EmissionMap"})mat.SetTexture(ch,null);mat.SetColor("_EmissionColor",Color.black);
     BaseShaderGUI.SetMaterialKeywords(mat, UnityEditor.Rendering.Universal.ShaderGUI.LitGUI.SetMaterialKeywords, m => { m.DisableKeyword("_DETAIL_MULX2"); m.DisableKeyword("_DETAIL_SCALED"); });
     if(!mat.IsKeywordEnabled("_NORMALMAP")||!mat.IsKeywordEnabled("_METALLICSPECGLOSSMAP")||mat.IsKeywordEnabled("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A"))throw new InvalidDataException("URP material validation failed.");
     AssetDatabase.CreateAsset(mat,dest+"/Surface.mat");materials.Add(name,mat);
    }
    if(materials.Count!=4)throw new InvalidDataException("Expected four unique front materials.");
    chunks.ShowSources(true);
    for(int i=0;i<targets.Count;i++) {var t=targets[i];AssetDatabase.CreateAsset(derivatives[i],folder+"/"+i.ToString("D2")+"_"+t.source.name+".asset");t.filter.sharedMesh=derivatives[i];t.renderer.sharedMaterials=new[]{t.oldMaterial,materials[(string)t.record["family"]]};EditorUtility.SetDirty(t.filter);EditorUtility.SetDirty(t.renderer);PrefabUtility.RecordPrefabInstancePropertyModifications(t.filter);PrefabUtility.RecordPrefabInstancePropertyModifications(t.renderer);}
    // Source renderers outside the target temporarily change enabled state during ShowSources;
    // compare their complete state after explicit rebuild restores original visibility.
    AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);
    if(Preserve(scene,chunks,changed)!=keep)throw new InvalidDataException("An untouched component/root/collider changed; preserve failure evidence and restore backup before continuing.");
    foreach(var t in targets)if(Sha((string)t.record["meshAsset"])!=(string)t.record["meshSha256"]||Sha((string)t.record["sourceMaterial"])!=(string)t.record["sourceMaterialSha256"])throw new InvalidDataException("Original source asset changed.");
    if(chunks.editingSources||chunks.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(chunks))throw new InvalidDataException("Derived chunks are stale.");
    EditorSceneManager.SaveScene(scene);Write(Path.Combine(evidence,"installed.json"),new {utc=DateTime.UtcNow,sceneSha256=Sha(scene.path),contractSha256=Sha(ContractPath),sourceFingerprint=chunks.sourceFingerprint,targets=targets.Select(t=>new {t.path,source=t.record["meshAsset"],derivative=AssetDatabase.GetAssetPath(t.filter.sharedMesh),derivativeSha256=Sha(AssetDatabase.GetAssetPath(t.filter.sharedMesh)),derivativeMetaSha256=Sha(AssetDatabase.GetAssetPath(t.filter.sharedMesh)+".meta"),vertices=t.filter.sharedMesh.vertexCount,triangles=t.filter.sharedMesh.triangles.Length/3,materials=t.renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath),materialHashes=t.renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath).Distinct().ToDictionary(p=>p,Sha)}),preservedComponents=true,originalAssetHashesPreserved=true,nativeAccepted=false});
   }
   catch(Exception e){Write(Path.Combine(evidence,"failure.json"),new {utc=DateTime.UtcNow,error=e.ToString(),backup="before-scene.unity",status="Failed evidence retained; no automatic acceptance or deletion."});throw;}
  }
 }
}
#endif
