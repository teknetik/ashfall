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
 /// Set by BarkDirector while a bark plays: the talk clip runs, and ActorLookAt holds eye contact for it.
 [System.NonSerialized]public bool barking;
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
 [Tooltip("Turn the body to face the player while a dialogue with this colonist is open, and back afterwards (native QA, 19 Nov 2026: spoken to from behind, the NPC kept its back to the conversation camera).")]
 public bool faceSpeaker=true;
 [Min(.1f)]public float faceTurnRate=6;
 Transform body;Quaternion homeLocal;bool homeKnown;GameSession session;
 void Update()
 {
  if(actor)actor.SetMotion(0,false,talking||barking);
  if(!faceSpeaker)return;
  if(!body){var look=GetComponentInChildren<ActorLookAt>();body=look?look.transform:actor?actor.transform:null;if(!body)return;}
  if(!homeKnown){homeLocal=body.localRotation;homeKnown=true;}
  if(!session)session=FindAnyObjectByType<GameSession>();
  var target=homeLocal;
  if(talking&&session&&session.player)
  {
   var yaw=ConversationFraming.FaceYaw(body.position,session.player.transform.position);
   if(yaw.HasValue)
   {
    // Turn about world up by the difference between the authored facing and the player, keeping any other part of
    // the visual's rotation (import axes) as it was.
    var parent=body.parent?body.parent.rotation:Quaternion.identity;
    var homeWorld=parent*homeLocal;var f=homeWorld*Vector3.forward;
    float delta=Mathf.DeltaAngle(Mathf.Atan2(f.x,f.z)*Mathf.Rad2Deg,yaw.Value);
    target=Quaternion.Inverse(parent)*(Quaternion.Euler(0,delta,0)*homeWorld);
   }
  }
  if(Quaternion.Angle(body.localRotation,target)<.05f)return;
  body.localRotation=session&&session.reducedMotion?target:Quaternion.Slerp(body.localRotation,target,1-Mathf.Exp(-faceTurnRate*Time.deltaTime));
 }
 }
}
