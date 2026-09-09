using UnityEngine;
namespace AthenHill
{
 public class AmbientWalker:MonoBehaviour
 {
  public Transform[] waypoints;
  [Min(0)]public float speed=1;
  [Range(0,1)]public float phase;
  [Min(0)]public float turnLookAhead=.18f;
  [Min(.01f)]public float turnSharpness=12;
  public ActorAnimation actor;
  float distance,total;float[] lengths;
  void Start(){lengths=new float[waypoints.Length];for(int i=0;i<lengths.Length;i++){lengths[i]=Vector3.Distance(waypoints[i].position,waypoints[(i+1)%lengths.Length].position);total+=lengths[i];}distance=phase*total;Place(true);}
  void Update(){if(total<=0)return;distance=(distance+speed*Time.deltaTime)%total;Place(false);actor.SetMotion(speed,false,false);}
  Vector3 Point(float at){float d=total>0?Mathf.Repeat(at,total):0;for(int i=0;i<lengths.Length;i++){if(d<=lengths[i])return Vector3.Lerp(waypoints[i].position,waypoints[(i+1)%waypoints.Length].position,d/Mathf.Max(.001f,lengths[i]));d-=lengths[i];}return transform.position;}
  void Place(bool immediate)
  {
   transform.position=Point(distance);
   // Anticipate the next authored segment; position, speed and route timing remain exact.
   var heading=Point(distance+Mathf.Max(.01f,speed*turnLookAhead))-transform.position;
   if(heading.sqrMagnitude<.000001f)return;
   var rotation=Quaternion.LookRotation(heading);
   transform.rotation=immediate?rotation:Quaternion.Slerp(transform.rotation,rotation,1-Mathf.Exp(-turnSharpness*Time.deltaTime));
  }
  void OnDrawGizmosSelected(){if(waypoints==null)return;Gizmos.color=Color.cyan;for(int i=0;i<waypoints.Length;i++)if(waypoints[i]&&waypoints[(i+1)%waypoints.Length])Gizmos.DrawLine(waypoints[i].position,waypoints[(i+1)%waypoints.Length].position);}
 }
}
