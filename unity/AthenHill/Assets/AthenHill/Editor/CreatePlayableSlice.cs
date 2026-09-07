using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill.Editor
{
 public static class CreatePlayableSlice
 {
  [MenuItem("Athen Hill/U2/Add player controls")]
  public static void Create()
  {
   if(EditorApplication.isPlaying)throw new System.Exception("Exit Play first.");
   if(GameObject.Find("Player"))throw new System.Exception("Player exists; edit its Inspector settings.");
   var defs=ScriptableObject.CreateInstance<InputActionAsset>();var map=defs.AddActionMap("Gameplay");
   var move=map.AddAction("Move",InputActionType.Value);move.AddCompositeBinding("2DVector").With("Up","<Keyboard>/w").With("Down","<Keyboard>/s").With("Left","<Keyboard>/a").With("Right","<Keyboard>/d");move.AddCompositeBinding("2DVector").With("Up","<Keyboard>/upArrow").With("Down","<Keyboard>/downArrow").With("Left","<Keyboard>/leftArrow").With("Right","<Keyboard>/rightArrow");
   map.AddAction("Run",InputActionType.Button,"<Keyboard>/leftShift");map.AddAction("Orbit",InputActionType.Button,"<Mouse>/rightButton");map.AddAction("Look",InputActionType.Value,"<Mouse>/delta");map.AddAction("Interact",InputActionType.Button,"<Keyboard>/e");map.AddAction("Reset",InputActionType.Button,"<Keyboard>/r");
   for(int i=1;i<=6;i++)map.AddAction("Slot"+i,InputActionType.Button,"<Keyboard>/digit"+i);
   var ui=defs.AddActionMap("UI");ui.AddAction("Cancel",InputActionType.Button,"<Keyboard>/escape");
   string path="Assets/AthenHill/Data/Controls.inputactions";File.WriteAllText(path,defs.ToJson());AssetDatabase.ImportAsset(path);
   var input=new GameObject("Input").AddComponent<GameInput>();input.definition=AssetDatabase.LoadAssetAtPath<InputActionAsset>(path);
   var landmarks=new GameObject("Landmarks");
   string[] names={"west_gate","hill_tree","oa_hill","shop_row_e","shop_row_w","basic_general","vanguard_hall","lattice_jack","ring_gate","mission_slab","east_wreck"};
   Vector3[] p={new(-43,0,0),new(-4,1.5f,0),new(-4,1.5f,4),new(16,.5f,9),new(-16,.5f,9),new(-8,.5f,16),new(10,.5f,-25.5f),new(0,.5f,-36.5f),new(0,.5f,36),new(-8,.25f,-12.5f),new(51,0,0)};
   for(int i=0;i<names.Length;i++){var t=new GameObject(names[i]).transform;t.SetParent(landmarks.transform);t.position=ImportBaseline.Convert(p[i].x,p[i].y,p[i].z);}
   var root=new GameObject("Player");root.layer=8;root.transform.position=landmarks.transform.Find("west_gate").position+Vector3.up*.015f;
   var visual=GameObject.Find("PlayerCandidate");visual.transform.SetParent(root.transform);visual.transform.localPosition=Vector3.zero;visual.transform.localRotation=Quaternion.Euler(0,-90,0);
   foreach(var t in root.GetComponentsInChildren<Transform>(true))t.gameObject.layer=8;
   var cc=root.AddComponent<CharacterController>();cc.height=1.8f;cc.radius=.35f;cc.center=Vector3.up*.9f;cc.stepOffset=.3f;cc.slopeLimit=45;cc.skinWidth=.03f;cc.minMoveDistance=0;
   var camera=GameObject.Find("MainCamera").GetComponent<Camera>();var follow=camera.gameObject.AddComponent<FollowCamera>();follow.target=root.transform;follow.input=input;
   var player=root.AddComponent<PlayerMotor>();player.input=input;player.view=camera.transform;player.visual=visual.transform;player.actor=visual.GetComponent<ActorAnimation>();player.spawn=landmarks.transform.Find("west_gate");
   var debug=new GameObject("AthenDebugBridge").AddComponent<AthenDebugBridge>();debug.player=player;debug.follow=follow;debug.landmarks=landmarks.transform;
   Time.fixedDeltaTime=1f/60;PlayerSettings.runInBackground=true;EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());EditorSceneManager.SaveOpenScenes();
  }
 }
}
