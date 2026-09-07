using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Editor
{
 public static class VerifyEditing
 {
  [MenuItem("Athen Hill/Diagnostics/Verify source edit round trip")]
  public static void Verify()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
   var c=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();c.ShowSources(true);
   var r=c.sources.First(x=>x&&x.enabled&&x.name.Contains("crate"));var position=r.transform.localPosition;bool enabled=r.enabled;var originalMesh=r.GetComponent<MeshFilter>().sharedMesh;int colliders=UnityEngine.Object.FindObjectsByType<Collider>().Length;string before=StaticRenderChunksEditor.Fingerprint(c);bool moved=false,hidden=false,restored=false;
   try
   {
    r.transform.localPosition+=Vector3.right*.25f;StaticRenderChunksEditor.Rebuild(c);moved=c.sourceFingerprint!=before&&r.GetComponent<MeshFilter>().sharedMesh==originalMesh;
    c.ShowSources(true);r.enabled=false;StaticRenderChunksEditor.Rebuild(c);c.ShowSources(true);hidden=!r.enabled;
    if(!moved||!hidden)throw new Exception("Source edit was lost while rebuilding chunks.");
   }
   finally
   {
    c.ShowSources(true);r.transform.localPosition=position;r.enabled=enabled;StaticRenderChunksEditor.Rebuild(c);restored=c.sourceFingerprint==before&&UnityEngine.Object.FindObjectsByType<Collider>().Length==colliders;
    Directory.CreateDirectory("Captures");File.WriteAllText("Captures/edit-roundtrip.json",JsonConvert.SerializeObject(new{source=r.name,moved,hidden,restored,colliders,prefabConnection=PrefabUtility.GetPrefabInstanceStatus(r.gameObject).ToString()},Formatting.Indented));
   }
   if(!restored)throw new Exception("Source edit test did not restore the original scene.");
  }
 }
}
