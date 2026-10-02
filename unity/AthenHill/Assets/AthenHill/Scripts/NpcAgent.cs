using UnityEngine;
namespace AthenHill
{
 public class NpcAgent : MonoBehaviour
 {
  public NpcDefinition definition;
  public ActorAnimation actor;
  [Tooltip("Counts toward the original four-colonist city visit objective.")]
  public bool countsForCityVisit=true;
  [Tooltip("Workbench this colonist keeps: a dialogue choice with action \"fabricator\" opens it (Brann at Salvage).")]
 public CraftingStationMarker workbench;
 public bool talking;
 [Range(0,1)]public float voiceGain=.8f;
 AudioSource voiceSource;
 public void Speak(DialogueNode node,GameSettings settings,AudioSource effectsBus)
 {
  StopSpeaking();
  if(node==null||!node.voice)return;
  if(!voiceSource)
  {
   var emitter=new GameObject("Dialogue voice");
   emitter.transform.SetParent(transform,false);
   emitter.transform.localPosition=new Vector3(0,1.55f,0);
   voiceSource=emitter.AddComponent<AudioSource>();
   voiceSource.playOnAwake=false;
   voiceSource.spatialBlend=.7f;
   voiceSource.minDistance=1.5f;
   voiceSource.maxDistance=14f;
   voiceSource.rolloffMode=AudioRolloffMode.Linear;
   voiceSource.priority=80;
  }
  if(effectsBus)voiceSource.outputAudioMixerGroup=effectsBus.outputAudioMixerGroup;
  SetVoiceLevel(settings?settings.Sound.effects:1);
  voiceSource.clip=node.voice;
  voiceSource.Play();
 }
 public void SetVoiceLevel(float effectsLevel){if(voiceSource)voiceSource.volume=voiceGain*Mathf.Clamp01(effectsLevel);}
 public void StopSpeaking(){if(voiceSource){voiceSource.Stop();voiceSource.clip=null;}}
 void Update(){if(actor)actor.SetMotion(0,false,talking);}
 }
}
