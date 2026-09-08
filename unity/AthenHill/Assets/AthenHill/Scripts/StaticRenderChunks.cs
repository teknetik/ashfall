using UnityEngine;
namespace AthenHill
{
 // Generated meshes are saved assets, never assembled at runtime. Source objects stay editable.
 public class StaticRenderChunks:MonoBehaviour
 {
  public Transform[] sourceRoots;
  [Min(8)]public float cellSize=64;
  [Min(8)]public float cellDepth=128;
  [Tooltip("Combine small material families across cells. Larger meshes retain spatial culling; zero disables this optimization.")]
  [Min(0)]public int smallMaterialTriangleLimit;
  [HideInInspector]public Transform generatedRoot;
  [HideInInspector]public Renderer[] sources;
  [HideInInspector]public bool[] sourceVisibility;
  [HideInInspector]public string sourceFingerprint;
  [HideInInspector]public bool editingSources;
  public void ShowSources(bool show)
  {
   if(editingSources==show)return;
   editingSources=show;
   if(sources!=null)for(int i=0;i<sources.Length;i++)if(sources[i])sources[i].enabled=show&&sourceVisibility[i];
   if(generatedRoot)generatedRoot.gameObject.SetActive(!show);
  }
 }
}
