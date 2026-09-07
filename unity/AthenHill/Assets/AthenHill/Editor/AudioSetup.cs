using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Audio;
namespace AthenHill.Editor
{
 public static class AudioSetup
 {
  [MenuItem("Athen Hill/U4/Add editable audio")]
  public static void Create()
  {
   if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
   if(UnityEngine.Object.FindAnyObjectByType<CityAudio>())throw new Exception("Audio exists; edit its mixer and AudioSources.");
   const string path="Assets/AthenHill/Audio/City.mixer";
   if(File.Exists(path))throw new Exception("Mixer already exists; refusing to overwrite it.");
   var type=TypeCache.GetTypesDerivedFrom<AudioMixer>().Single(t=>t.FullName=="UnityEditor.Audio.AudioMixerController");
   var mixer=(AudioMixer)type.GetMethod("CreateMixerControllerAtPath",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{path});
   var master=type.GetProperty("masterGroup").GetValue(mixer);
   var groupType=master.GetType();var children=Array.CreateInstance(groupType,3);
   var names=new[]{"Ambience","SFX","UI"};
   for(int i=0;i<3;i++){var g=type.GetMethod("CreateNewGroup").Invoke(mixer,new object[]{names[i],true});children.SetValue(g,i);}
   groupType.GetProperty("children").SetValue(master,children);
   var viewProperty=type.GetProperty("views");var viewType=viewProperty.PropertyType.GetElementType();var view=Activator.CreateInstance(viewType);viewType.GetField("name").SetValue(view,"All groups");
   var guidProperty=groupType.GetProperty("groupID");var guids=Array.CreateInstance(guidProperty.PropertyType,4);guids.SetValue(guidProperty.GetValue(master),0);for(int i=0;i<3;i++)guids.SetValue(guidProperty.GetValue(children.GetValue(i)),i+1);viewType.GetField("guids").SetValue(view,guids);var views=Array.CreateInstance(viewType,1);views.SetValue(view,0);viewProperty.SetValue(mixer,views);
   EditorUtility.SetDirty((UnityEngine.Object)master);EditorUtility.SetDirty(mixer);AssetDatabase.SaveAssets();
   var audio=new GameObject("City Audio").AddComponent<CityAudio>();audio.session=UnityEngine.Object.FindAnyObjectByType<GameSession>();
   AudioSource Source(string name,string file,string group,float volume,bool loop,Transform parent,float spatial=0)
   {
    var go=new GameObject(name);go.transform.SetParent(parent,false);var source=go.AddComponent<AudioSource>();source.clip=AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/AthenHill/Audio/"+file+"-mix.mp3");source.outputAudioMixerGroup=mixer.FindMatchingGroups(group).Single();source.volume=volume;source.loop=loop;source.playOnAwake=loop;source.spatialBlend=spatial;source.rolloffMode=AudioRolloffMode.Linear;source.minDistance=2;source.maxDistance=14;return source;
   }
   audio.ambience=Source("Desert bed","desert-bed","Ambience",.39f,true,audio.transform);
   audio.steps=Source("Stone footsteps","stone-step","SFX",.32f,false,audio.session.player.transform);
   audio.confirmation=Source("Terminal confirmation","terminal-click","UI",.31f,false,audio.transform);audio.confirmation.ignoreListenerPause=true;
   audio.latticeHum=Source("Lattice hum","transport-hum","Ambience",.31f,true,audio.session.latticePoint,1);
   audio.ringHum=Source("Ring hum","transport-hum","Ambience",.24f,true,audio.session.ringPoint,1);
   AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(audio.gameObject.scene);EditorSceneManager.SaveOpenScenes();
  }
 }
}
