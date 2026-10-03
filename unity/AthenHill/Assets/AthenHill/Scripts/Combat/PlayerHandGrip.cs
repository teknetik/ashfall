using UnityEngine;
namespace AthenHill
{
 /// Finger grip for the MPFB player (2 Oct 2026): the body's clips animate only the 24 game bones, so the finger bones
 /// stay at their relaxed rest pose. While a weapon is drawn this curls the right hand round the grip (trigger finger
 /// a little open) and, with the rifle, the left hand round the handguard; it eases back to the relaxed hand when
 /// holstered. Runs after the animation each frame. Bones are wired by TutorialSetInstall; a rig without fingers has none.
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
   Apply(rightFingers,rightRest,right,true);
   Apply(leftFingers,leftRest,left,false);
  }
  /// Editor review: pose the grip weights directly (no LateUpdate runs in batch captures).
  public void PreviewGrip(float rightWeight,float leftWeight)
  {
   if(rightRest==null||rightRest.Length!=rightFingers.Length)Awake();
   Apply(rightFingers,rightRest,rightWeight,true);Apply(leftFingers,leftRest,leftWeight,false);
  }
  void Apply(Transform[] bones,Quaternion[] rest,float w,bool trigger)
  {
   if(bones==null||rest==null)return;
   for(int i=0;i<bones.Length&&i<rest.Length;i++)
   {
    var b=bones[i];if(!b)continue;
    string n=b.name;int joint=n.Contains("_01_")?0:n.Contains("_02_")?1:2;
    var c=n.StartsWith("thumb")?thumbCurl:(trigger&&n.StartsWith("index"))?triggerCurl:fingerCurl;
    b.localRotation=rest[i]*Quaternion.Euler(c[joint]*w,0,0);
   }
  }
 }
}
