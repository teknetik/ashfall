using System;
using System.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering;
namespace AthenHill.Editor
{
 public static class CheckpointRangePass
 {
  const string Art="Assets/AthenHill/Art/Checkpoint/";
  static GameObject Model(string file,Transform parent,string name)
  {
   var g=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Art+file));g.name=name;g.transform.SetParent(parent,false);g.transform.localPosition=Vector3.zero;g.transform.localRotation=Quaternion.identity;return g;
  }
  static void Letter(Transform p,string name,string text,Vector3 pos,float size)
  {
   var g=new GameObject(name);g.transform.SetParent(p,false);g.transform.localPosition=pos;var t=g.AddComponent<TextMesh>();t.text=text;t.characterSize=size;t.fontSize=80;t.anchor=TextAnchor.MiddleCenter;t.alignment=TextAlignment.Center;t.color=new Color(.94f,.88f,.66f);g.GetComponent<Renderer>().shadowCastingMode=ShadowCastingMode.Off;
  }
  [MenuItem("Athen Hill/Outer Berms/Replace pillow-foot range targets")]
  public static void Install()
  {
   if(GameObject.Find("Range reset control"))throw new Exception("Range pass already installed; edit saved targets.");
   const string path="Assets/AthenHill/Prefabs/OuterBerms/RangeTarget.prefab";
   var p=PrefabUtility.LoadPrefabContents(path);
   try{
    var t=p.GetComponent<RangeTarget>();
    foreach(var r in t.pivot.GetComponentsInChildren<Renderer>())if(!r.transform.IsChildOf(t.pivot.Find("Steel target plate")))r.gameObject.SetActive(false);
    t.pivot.localPosition=new Vector3(0,.47f,0);
    if(!t.pivot.Find("Steel target plate"))Model("SteelTargetPlate.glb",t.pivot,"Steel target plate");
    var box=t.pivot.GetComponent<BoxCollider>();box.center=new Vector3(0,.52f,0);box.size=new Vector3(.56f,1.05f,.10f);
    if(!p.transform.Find("Steel target stand"))Model("SteelTargetStand.glb",p.transform,"Steel target stand");p.GetComponent<Health>().aimOffset=new Vector3(0,1.03f,0);
    PrefabUtility.SaveAsPrefabAsset(p,path);
   }finally{PrefabUtility.UnloadPrefabContents(p);}
   var tutorial=UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();int i=0;
   var shader=Shader.Find("Universal Render Pipeline/Lit");if(!shader)throw new Exception("Missing URP Lit shader");
   foreach(var target in tutorial.targets)
   {
    var pivot=target.pivot;var mat=new Material(shader){name="Painted target "+(++i)};
    mat.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Art+"Target"+i+".png"));mat.SetFloat("_Surface",1);mat.SetFloat("_Blend",0);mat.SetFloat("_SrcBlend",(int)BlendMode.SrcAlpha);mat.SetFloat("_DstBlend",(int)BlendMode.OneMinusSrcAlpha);mat.SetFloat("_ZWrite",0);mat.SetFloat("_Cull",0);mat.SetFloat("_Smoothness",.15f);mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");mat.renderQueue=3000;var existing=AssetDatabase.LoadAssetAtPath<Material>(Art+"PaintedTarget"+i+".mat");if(existing){UnityEngine.Object.DestroyImmediate(mat);mat=existing;}else AssetDatabase.CreateAsset(mat,Art+"PaintedTarget"+i+".mat");
    var decal=GameObject.CreatePrimitive(PrimitiveType.Quad);decal.name="Painted bullseye "+i;decal.transform.SetParent(pivot,false);decal.transform.localPosition=new Vector3(0,.48f,.041f);decal.transform.localScale=Vector3.one*.38f;UnityEngine.Object.DestroyImmediate(decal.GetComponent<Collider>());decal.GetComponent<Renderer>().sharedMaterial=mat;decal.GetComponent<Renderer>().shadowCastingMode=ShadowCastingMode.Off;
    Letter(target.transform,"Target number","PLATE 0"+i,new Vector3(0,.27f,.187f),.018f);
    target.transform.Find("Target number").localEulerAngles=new Vector3(0,180,0);
   }
   var root=GameObject.Find("West Gate checkpoint").transform;
   var reset=new GameObject("Range reset control");reset.transform.SetParent(root,false);reset.transform.position=new Vector3(-68.2f,-1.55f,8.0f);
   var ui=reset.AddComponent<WorldInteractable>();ui.prompt="E · Reset the three range plates";ui.range=1.8f;
   var logic=reset.AddComponent<RangeResetStation>();logic.tutorial=tutorial;logic.session=tutorial.session;
   var panel=GameObject.CreatePrimitive(PrimitiveType.Cube);panel.name="Range control pedestal";panel.transform.SetParent(reset.transform,false);panel.transform.localPosition=new Vector3(0,.53f,0);panel.transform.localScale=new Vector3(.6f,1.06f,.34f);panel.GetComponent<Renderer>().sharedMaterial=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/BuildingMaterials/WardConcrete/WardConcrete.mat");
   Letter(reset.transform,"Range reset lettering","WARDEN RANGE\nE · RESET PLATES",new Vector3(0,.82f,-.18f),.025f);
   var sign=new GameObject("Warden training range sign");sign.transform.SetParent(root,false);sign.transform.position=new Vector3(-69,-.5f,9.6f);sign.transform.rotation=Quaternion.Euler(0,-35,0);
   Letter(sign.transform,"Training range lettering","TRAINING RANGE\n3 NUMBERED STEEL PLATES",Vector3.zero,.045f);
   var signPanel=GameObject.CreatePrimitive(PrimitiveType.Cube);signPanel.name="Range sign backing";signPanel.transform.SetParent(sign.transform,false);signPanel.transform.localPosition=new Vector3(0,0,.03f);signPanel.transform.localScale=new Vector3(2.0f,.66f,.06f);signPanel.GetComponent<Renderer>().sharedMaterial=panel.GetComponent<Renderer>().sharedMaterial;
   var marks=GameObject.Find("Landmarks").transform;Marker(marks,"checkpoint_firingline",new Vector3(-66,-1.55f,7.5f));Marker(marks,"checkpoint_road",new Vector3(-76,-1.3f,-6));Marker(marks,"checkpoint_range_reset",new Vector3(-68.2f,-1.55f,6.6f));
   Camera(root,"cam_checkpoint_range",new Vector3(-66,.4f,7.5f),new Vector3(-79,.25f,15.5f),60);
   i=0;foreach(var t in tutorial.targets)Camera(root,"cam_checkpoint_plate"+(++i),new Vector3(-66,.2f,7.5f),t.transform.position+t.GetComponent<Health>().aimOffset,50);
   Camera(root,"cam_checkpoint_target_close",tutorial.targets[0].transform.position+tutorial.targets[0].transform.forward*2.8f+Vector3.up*1.55f,tutorial.targets[0].transform.position+Vector3.up*.8f,58);
   tutorial.lineTargets="Those are training targets: three numbered steel plates on hinged stands. Hold right mouse to aim, then left click to fire; F fires from the hip. Knock down all three. The range control raises them for practice after the primer.";
   EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());EditorSceneManager.SaveOpenScenes();AssetDatabase.SaveAssets();
  }
  static void Marker(Transform p,string n,Vector3 v){var g=new GameObject(n);g.transform.SetParent(p,true);g.transform.position=v;}
  static void Camera(Transform p,string n,Vector3 v,Vector3 target,float fov){var g=new GameObject(n,typeof(Camera));g.transform.SetParent(p,true);g.transform.position=v;g.transform.LookAt(target);var c=g.GetComponent<Camera>();c.enabled=false;c.fieldOfView=fov;c.farClipPlane=650;}
 }
}
