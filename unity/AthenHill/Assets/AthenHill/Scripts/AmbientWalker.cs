using UnityEngine;
namespace AthenHill
{
 public class AmbientWalker:MonoBehaviour
 {
  public Transform[] waypoints;
  [Min(0)]public float speed=1;
  [Range(0,1)]public float phase;
  public ActorAnimation actor;
  float distance,total;float[] lengths;
  void Start(){lengths=new float[waypoints.Length];for(int i=0;i<lengths.Length;i++){lengths[i]=Vector3.Distance(waypoints[i].position,waypoints[(i+1)%lengths.Length].position);total+=lengths[i];}distance=phase*total;Place();}
  void Update(){if(total<=0)return;distance=(distance+speed*Time.deltaTime)%total;Place();actor.SetMotion(speed,false,false);}
  void Place(){float d=distance;for(int i=0;i<lengths.Length;i++){if(d<=lengths[i]){var a=waypoints[i].position;var b=waypoints[(i+1)%lengths.Length].position;transform.position=Vector3.Lerp(a,b,d/Mathf.Max(.001f,lengths[i]));if((b-a).sqrMagnitude>0)transform.rotation=Quaternion.LookRotation(b-a);return;}d-=lengths[i];}}
  void OnDrawGizmosSelected(){if(waypoints==null)return;Gizmos.color=Color.cyan;for(int i=0;i<waypoints.Length;i++)if(waypoints[i]&&waypoints[(i+1)%waypoints.Length])Gizmos.DrawLine(waypoints[i].position,waypoints[(i+1)%waypoints.Length].position);}
 }
}
