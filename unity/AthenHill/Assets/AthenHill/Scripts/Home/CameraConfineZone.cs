using UnityEngine;
namespace AthenHill
{
 /// A tight interior (5 Oct 2026: the 2.35 m wide container home): while the player's chest is inside this box the
 /// follow camera holds first person, and gives the player's own zoom back at the door (FollowCamera.Confined).
 public class CameraConfineZone:MonoBehaviour
 {
  public FollowCamera follow;
  [Tooltip("Box in this transform's local space.")]
  public Vector3 center=new Vector3(0,1.2f,0),size=new Vector3(5.8f,2.3f,2.2f);
  [Min(0)]public float chestHeight=1.1f;
  Transform player;bool inside;
  public bool Inside=>inside;
  void Start()
  {
   if(!follow)follow=FindAnyObjectByType<FollowCamera>();
   player=follow?follow.target:null;
  }
  void LateUpdate()
  {
   if(!player||!follow)return;
   var local=transform.InverseTransformPoint(player.position+Vector3.up*chestHeight)-center;
   bool now=Mathf.Abs(local.x)<=size.x*.5f&&Mathf.Abs(local.y)<=size.y*.5f&&Mathf.Abs(local.z)<=size.z*.5f&&!follow.FixedView;
   if(now!=inside){inside=now;follow.Confined=now;}
  }
  void OnDisable(){if(inside&&follow)follow.Confined=false;inside=false;}
  void OnDrawGizmosSelected(){Gizmos.matrix=transform.localToWorldMatrix;Gizmos.color=new Color(.35f,.85f,.85f,.6f);Gizmos.DrawWireCube(center,size);}
 }
}
