using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 [CustomEditor(typeof(StaticRenderChunks))]
 public class StaticRenderChunksEditor:UnityEditor.Editor
 {
  public override void OnInspectorGUI()
  {
   DrawDefaultInspector();var c=(StaticRenderChunks)target;
   EditorGUILayout.HelpBox("Show sources to edit individual city objects. Rebuild after moving, adding or changing them. Colliders remain separate. Generated meshes are disposable outputs.",MessageType.Info);
   if(GUILayout.Button("Show Sources for Editing")){Undo.RecordObject(c,"Edit city sources");c.ShowSources(true);EditorSceneManager.MarkSceneDirty(c.gameObject.scene);}
   if(GUILayout.Button("Rebuild Render Chunks"))Rebuild(c);
  }
  [MenuItem("Athen Hill/U4/Build editable render chunks")]
  public static void Create()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
   var c=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
   if(!c){c=new GameObject("City Render Chunks").AddComponent<StaticRenderChunks>();c.sourceRoots=new[]{GameObject.Find("AuthoredWorld").transform,GameObject.Find("Paving").transform,GameObject.Find("Paving Joints").transform};}
   Rebuild(c);
  }
  static IEnumerable<Renderer> AllSources(StaticRenderChunks c)=>c.sourceRoots.Where(t=>t).SelectMany(t=>t.GetComponentsInChildren<MeshRenderer>(true)).Where(r=>!r.name.StartsWith("COL_")).Distinct();
  public static string Fingerprint(StaticRenderChunks c)
  {
   var text=new StringBuilder(c.cellSize.ToString("R",System.Globalization.CultureInfo.InvariantCulture));
   var fileHashes=new Dictionary<string,string>();
   string FileHash(string path){if(!fileHashes.TryGetValue(path,out var hash)){using(var sha=SHA256.Create())hash=File.Exists(path)?Convert.ToBase64String(sha.ComputeHash(File.ReadAllBytes(path))):path;fileHashes[path]=hash;}return hash;}
   text.Append(c.cellDepth.ToString("R",System.Globalization.CultureInfo.InvariantCulture));
   foreach(var r in AllSources(c))
   {
    var m=r.GetComponent<MeshFilter>().sharedMesh;
    int sourceIndex=c.sources==null?-1:Array.IndexOf(c.sources,r);text.Append(c.editingSources||sourceIndex<0?r.enabled:c.sourceVisibility[sourceIndex]);
    text.Append(r.name).Append(r.gameObject.activeInHierarchy).Append((int)r.shadowCastingMode).Append(r.receiveShadows);
    var matrix=c.transform.worldToLocalMatrix*r.localToWorldMatrix;for(int i=0;i<16;i++)text.Append(matrix[i].ToString("R",System.Globalization.CultureInfo.InvariantCulture)).Append(',');
    text.Append(AssetDatabase.GetAssetPath(m)).Append(m.name).Append(m.vertexCount).Append(FileHash(AssetDatabase.GetAssetPath(m)));
    foreach(var mat in r.sharedMaterials){AssetDatabase.TryGetGUIDAndLocalFileIdentifier(mat,out string guid,out long id);text.Append(guid).Append(id);}
   }
   using(var sha=SHA256.Create())return Convert.ToBase64String(sha.ComputeHash(Encoding.UTF8.GetBytes(text.ToString())));
  }
  public static void Rebuild(StaticRenderChunks c)
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play before rebuilding.");
   c.ShowSources(true);
   var sources=AllSources(c).ToArray();var buckets=new Dictionary<(Material,int,int,ShadowCastingMode,bool),List<CombineInstance>>();
   foreach(var r in sources)
   {
    if(!r.enabled||!r.gameObject.activeInHierarchy)continue;
    var mesh=r.GetComponent<MeshFilter>().sharedMesh;var p=c.transform.InverseTransformPoint(r.bounds.center);
    for(int sub=0;sub<mesh.subMeshCount;sub++)
    {
     var key=(r.sharedMaterials[sub],Mathf.FloorToInt(p.x/c.cellSize),Mathf.FloorToInt((p.z+c.cellDepth*.5f)/c.cellDepth),r.shadowCastingMode,r.receiveShadows);
     if(!buckets.TryGetValue(key,out var list)){list=new List<CombineInstance>();buckets.Add(key,list);}
     list.Add(new CombineInstance{mesh=mesh,subMeshIndex=sub,transform=c.transform.worldToLocalMatrix*r.localToWorldMatrix});
    }
   }
   const string folder="Assets/AthenHill/Art/RenderChunks";Directory.CreateDirectory(folder);AssetDatabase.Refresh();
   // Only replace this component's generated outputs. Never touch imported meshes or source objects.
   if(c.generatedRoot){foreach(var f in c.generatedRoot.GetComponentsInChildren<MeshFilter>()){var path=AssetDatabase.GetAssetPath(f.sharedMesh);if(path.StartsWith(folder+"/"))AssetDatabase.DeleteAsset(path);}UnityEngine.Object.DestroyImmediate(c.generatedRoot.gameObject);}
   c.generatedRoot=new GameObject("Generated material chunks").transform;c.generatedRoot.SetParent(c.transform,false);
   int index=0;
   foreach(var pair in buckets)
   {
    var mesh=new Mesh{name=$"Chunk_{index++}_{pair.Key.Item1.name}_{pair.Key.Item2}_{pair.Key.Item3}",indexFormat=IndexFormat.UInt32};mesh.CombineMeshes(pair.Value.ToArray(),true,true);mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,folder+"/"+mesh.name+".asset");
    var go=new GameObject(mesh.name);go.transform.SetParent(c.generatedRoot,false);go.AddComponent<MeshFilter>().sharedMesh=mesh;var r=go.AddComponent<MeshRenderer>();r.sharedMaterial=pair.Key.Item1;r.shadowCastingMode=pair.Key.Item4;r.receiveShadows=pair.Key.Item5;
   }
   c.sources=sources;c.sourceVisibility=sources.Select(r=>r.enabled).ToArray();c.sourceFingerprint=Fingerprint(c);c.ShowSources(false);
   EditorUtility.SetDirty(c);AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(c.gameObject.scene);EditorSceneManager.SaveOpenScenes();Debug.Log($"Batched {sources.Length} editable renderers into {buckets.Count} material/spatial chunks.");
  }
 }
 public class VerifyRenderChunks:IPreprocessBuildWithReport
 {
  public int callbackOrder=>0;
  public void OnPreprocessBuild(BuildReport report)
  {
   foreach(var c in UnityEngine.Object.FindObjectsByType<StaticRenderChunks>())if(c.editingSources||c.sourceFingerprint!=StaticRenderChunksEditor.Fingerprint(c))throw new BuildFailedException("City sources changed. Select City Render Chunks and Rebuild Render Chunks before building.");
  }
 }
}
