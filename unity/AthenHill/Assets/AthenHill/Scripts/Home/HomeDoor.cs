using UnityEngine;
namespace AthenHill
{
 /// The home's hinged steel door (5 Oct 2026). Locked until the lease (E on it says who holds the roll); afterwards it
 /// swings open as the player comes near and closes once they have gone. The leaf collider blocks the doorway only
 /// while the door is (nearly) shut.
 public class HomeDoor:MonoBehaviour
 {
  public GameSession session;
  [Tooltip("The door leaf, pivoting about its local Y at the hinge.")]
  public Transform leaf;
  [Tooltip("Leaf local yaw when shut and when open, in degrees.")]
  public float closedYaw,openYaw=-100;
  [Min(10)]public float degreesPerSecond=170;
  [Tooltip("The player is within this distance of the door (this transform) for it to open.")]
  [Min(.5f)]public float openDistance=2.4f;
  public Collider leafCollider;
  [Tooltip("E prompt on the locked door.")]
  public WorldInteractable lockedPrompt;
  [TextArea]public string lockedNotice="Locked. Linn on the hill keeps the housing roll for these homes.";
  public AudioSource audioSource;
  public AudioClip openClip,closeClip;
  public bool Locked {get;set;}=true;
  public float OpenFraction {get;private set;}
  Transform player;bool wantOpen;
  void Start()
  {
   if(!session)session=FindAnyObjectByType<GameSession>();
   player=session&&session.player?session.player.transform:null;
   if(lockedPrompt)lockedPrompt.Used+=Knock;
   Apply();
  }
  void OnDestroy(){if(lockedPrompt)lockedPrompt.Used-=Knock;}
  void Knock(){if(session&&Locked)session.Notify(lockedNotice,"Ward");}
  void Update()
  {
   bool near=player&&(player.position-transform.position).sqrMagnitude<openDistance*openDistance;
   bool open=!Locked&&near;
   if(open!=wantOpen)
   {
    wantOpen=open;
    var clip=open?openClip:closeClip;
    if(audioSource&&clip)audioSource.PlayOneShot(clip,.8f);
   }
   float span=Mathf.Max(1,Mathf.Abs(openYaw-closedYaw));
   OpenFraction=Mathf.MoveTowards(OpenFraction,open?1:0,degreesPerSecond/span*Time.deltaTime);
   if(lockedPrompt&&lockedPrompt.enabled!=Locked)lockedPrompt.enabled=Locked;
   Apply();
  }
  void Apply()
  {
   if(leaf)leaf.localRotation=Quaternion.Euler(0,Mathf.LerpAngle(closedYaw,openYaw,Mathf.SmoothStep(0,1,OpenFraction)),0);
   if(leafCollider)leafCollider.enabled=OpenFraction<.15f;
  }
 }
}
