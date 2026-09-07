using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UIElements;
namespace AthenHill.Editor
{
 public static class CreateCityLoop
 {
  [MenuItem("Athen Hill/U3/Add editable city loop")]
  public static void Create()
  {
   if(EditorApplication.isPlaying)throw new System.Exception("Exit Play first.");
   if(GameObject.Find("CitySession"))throw new System.Exception("City loop exists; edit its assets and scene objects.");
   var source=JObject.Parse(File.ReadAllText("Assets/AthenHill/Data/source-content.json"));
   var catalog=ScriptableObject.CreateInstance<CityCatalog>();JsonUtility.FromJsonOverwrite(source["catalog"].ToString(),catalog);catalog.credits=AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/AthenHill/Art/THIRD_PARTY_LICENSES.txt");AssetDatabase.CreateAsset(catalog,"Assets/AthenHill/Data/CityCatalog.asset");
   var npcs=new System.Collections.Generic.List<NpcAgent>();var group=new GameObject("Colonists");
   var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/NpcImportAudition.prefab");
   foreach(var n in source["npcs"])
   {
    var definition=ScriptableObject.CreateInstance<NpcDefinition>();JsonUtility.FromJsonOverwrite(n.ToString(),definition);definition.role=definition.nodes[0].title;AssetDatabase.CreateAsset(definition,"Assets/AthenHill/Data/"+definition.id+".asset");
    var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.name=definition.id;go.transform.SetParent(group.transform);var p=n["position"];go.transform.position=ImportBaseline.Convert((float)p[0],(float)p[1],(float)p[2]);go.transform.rotation=Quaternion.Euler(0,-(float)n["yaw"]*Mathf.Rad2Deg,0);
    var agent=go.AddComponent<NpcAgent>();agent.definition=definition;agent.actor=go.GetComponent<ActorAnimation>();
    Tint(go,(string)n["tint"]);npcs.Add(agent);
   }
   var audition=GameObject.Find("NpcImportAudition");if(audition)Object.DestroyImmediate(audition);
   foreach(var w in source["walkers"])
   {
    var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.name=(string)w["id"];go.transform.SetParent(group.transform);var walker=go.AddComponent<AmbientWalker>();walker.speed=(float)w["speed"];walker.phase=(float)w["phase"];walker.actor=go.GetComponent<ActorAnimation>();
    var route=new GameObject(go.name+" route");var points=new System.Collections.Generic.List<Transform>();int i=0;
    foreach(var p in w["waypoints"]){var t=new GameObject("Waypoint "+(++i)).transform;t.SetParent(route.transform);t.position=ImportBaseline.Convert((float)p[0],(float)p[1],(float)p[2]);points.Add(t);}walker.waypoints=points.ToArray();go.transform.position=points[0].position;Tint(go,(string)w["tint"]);
   }
   var session=new GameObject("CitySession").AddComponent<GameSession>();session.catalog=catalog;session.npcs=npcs.ToArray();session.input=Object.FindAnyObjectByType<GameInput>();session.player=Object.FindAnyObjectByType<PlayerMotor>();session.follow=Object.FindAnyObjectByType<FollowCamera>();
   AddMarkers();
   var panel=ScriptableObject.CreateInstance<PanelSettings>();panel.scaleMode=PanelScaleMode.ScaleWithScreenSize;panel.referenceResolution=new Vector2Int(1920,1080);panel.screenMatchMode=PanelScreenMatchMode.MatchWidthOrHeight;panel.match=.5f;AssetDatabase.CreateAsset(panel,"Assets/AthenHill/UI/CityPanel.asset");
   var ui=new GameObject("City HUD");var doc=ui.AddComponent<UIDocument>();doc.panelSettings=panel;doc.visualTreeAsset=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml");var hud=ui.AddComponent<CityHud>();hud.session=session;hud.worldCamera=session.follow.GetComponent<Camera>();
   var events=new GameObject("UI Event System");events.AddComponent<EventSystem>();events.AddComponent<InputSystemUIInputModule>().AssignDefaultActions();
   AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());EditorSceneManager.SaveOpenScenes();
  }
  [MenuItem("Athen Hill/U3/Add interaction markers")]
  public static void AddMarkers()
  {
   if(EditorApplication.isPlaying)throw new System.Exception("Exit Play first.");
   var s=Object.FindAnyObjectByType<GameSession>();
   if(!s.hillPoint)s.hillPoint=Marker("Hill visit area",Vector3.zero);
   if(!s.latticePoint)s.latticePoint=Marker("Lattice interaction",new Vector3(0,.5f,-39));
   if(!s.ringPoint)s.ringPoint=Marker("Ring interaction",new Vector3(0,.5f,36.1f));
   EditorSceneManager.MarkSceneDirty(s.gameObject.scene);EditorSceneManager.SaveOpenScenes();
  }
  static Transform Marker(string name,Vector3 position){var t=new GameObject(name).transform;t.position=position;return t;}
  static void Tint(GameObject go,string html)
  {
   if(!ColorUtility.TryParseHtmlString(html,out var color))return;
   foreach(var r in go.GetComponentsInChildren<Renderer>())if(r.sharedMaterial.name=="MAT_cloth")
   {
    var mat=new Material(r.sharedMaterial);mat.name=go.name+" jacket";
    if(mat.HasProperty("baseColorFactor"))mat.SetColor("baseColorFactor",color);
    AssetDatabase.CreateAsset(mat,"Assets/AthenHill/Materials/"+go.name+".mat");r.sharedMaterial=mat;
   }
  }
 }
}
