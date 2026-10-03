using UnityEngine;
namespace AthenHill
{
 /// Finger grip for the MPFB player (2 Oct 2026): the body's clips animate only the 24 game bones, so the finger bones
 /// stay at their relaxed rest pose. While a weapon is drawn this curls the right hand round the grip (trigger finger
 /// a little open) and, with the rifle, the left hand round the handguard; it eases back to the relaxed hand when
 /// holstered. Runs after the animation each frame. Bones are wired by TutorialSetInstall; a rig without fingers has none.
 /// 3 Oct 2026 (player_face_20261003): solved grip poses per weapon and hand (fingers curled joint by joint until they
 /// touch the weapon, or the other hand, in the hold pose) replace the fixed curl where present; an empty array keeps
 /// the procedural curl below.
 [DisallowMultipleComponent]
 public class PlayerHandGrip:MonoBehaviour
 {
  public PlayerCombat combat;
  [Tooltip("Right-hand finger joints (index, middle, ring, pinky, thumb; 01-03 each).")]public Transform[] rightFingers=new Transform[0];
  public Transform[] leftFingers=new Transform[0];
  [Tooltip("Curl in degrees about each joint's local X for joints 01, 02, 03.")]public Vector3 fingerCurl=new Vector3(55,70,45);
  public Vector3 triggerCurl=new Vector3(22,28,18);
  public Vector3 thumbCurl=new Vector3(12,22,18);
  [Min(.01f)]public float blendSeconds=.15f;
  [Header("Solved grips (local rotations, same order as the finger arrays; empty = procedural curl)")]
  public Quaternion[] pistolRight=new Quaternion[0];
  public Quaternion[] pistolLeft=new Quaternion[0];
  public Quaternion[] rifleRight=new Quaternion[0];
  public Quaternion[] rifleLeft=new Quaternion[0];
  Quaternion[] rightRest,leftRest;
  float right,left;
  void Awake()
  {
   rightRest=Capture(rightFingers);leftRest=Capture(leftFingers);
  }
  static Quaternion[] Capture(Transform[] t)
  {
   var r=new Quaternion[t.Length];
   for(int i=0;i<t.Length;i++)r[i]=t[i]?t[i].localRotation:Quaternion.identity;
   return r;
  }
  void LateUpdate()
  {
   bool armed=combat&&combat.Armed;
   float k=1-Mathf.Exp(-Time.deltaTime/Mathf.Max(.01f,blendSeconds)*3);
   right=Mathf.Lerp(right,armed?1:0,k);
   left=Mathf.Lerp(left,armed?1:0,k);   // both holds are two-handed: the support hand wraps the rifle handguard or the pistol grip
   bool rifle=combat&&combat.RifleActive;
   Apply(rightFingers,rightRest,right,true,rifle?rifleRight:pistolRight);
   Apply(leftFingers,leftRest,left,false,rifle?rifleLeft:pistolLeft);
  }
  /// Editor review: pose the grip weights directly (no LateUpdate runs in batch captures).
  public void PreviewGrip(float rightWeight,float leftWeight)=>PreviewGrip(rightWeight,leftWeight,combat&&combat.RifleActive);
  public void PreviewGrip(float rightWeight,float leftWeight,bool rifle)
  {
   if(rightRest==null||rightRest.Length!=rightFingers.Length)Awake();
   Apply(rightFingers,rightRest,rightWeight,true,rifle?rifleRight:pistolRight);Apply(leftFingers,leftRest,leftWeight,false,rifle?rifleLeft:pistolLeft);
  }
  /// The relaxed rest rotations the grip blends from (captured on Awake).
  public Quaternion[] RestOf(bool rightHand){if(rightRest==null||rightRest.Length!=rightFingers.Length)Awake();return rightHand?rightRest:leftRest;}
  void Apply(Transform[] bones,Quaternion[] rest,float w,bool trigger,Quaternion[] solved)
  {
   if(bones==null||rest==null)return;
   bool useSolved=solved!=null&&solved.Length>0&&solved.Length==bones.Length;
   for(int i=0;i<bones.Length&&i<rest.Length;i++)
   {
    var b=bones[i];if(!b)continue;
    if(useSolved){b.localRotation=Quaternion.Slerp(rest[i],solved[i],w);continue;}
    string n=b.name;int joint=n.Contains("_01_")?0:n.Contains("_02_")?1:2;
    var c=n.StartsWith("thumb")?thumbCurl:(trigger&&n.StartsWith("index"))?triggerCurl:fingerCurl;
    b.localRotation=rest[i]*Quaternion.Euler(c[joint]*w,0,0);
   }
  }
 }
}
