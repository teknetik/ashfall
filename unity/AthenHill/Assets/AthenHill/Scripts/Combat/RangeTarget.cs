using System;
using UnityEngine;
namespace AthenHill
{
 /// Warden practice plate: tips back when shot down and can be raised again.
 [RequireComponent(typeof(Health))]
 public class RangeTarget:MonoBehaviour
 {
  [Tooltip("Rotates backward about its base when knocked down.")]
  public Transform pivot;
  [Range(0,90)]public float fallAngle=78;
  [Min(.05f)]public float fallSeconds=.35f;
  public AudioSource clang;
  public ParticleSystem sparks;
  public Health Health {get;private set;}
  public bool Down=>!Health.Alive;
  public event Action<RangeTarget> KnockedDown;
  Quaternion upright;float fall;
  void Awake(){Health=GetComponent<Health>();if(!pivot)pivot=transform;upright=pivot.localRotation;Health.Damaged+=Hit;Health.Died+=Fall;}
  void OnDestroy(){if(Health){Health.Damaged-=Hit;Health.Died-=Fall;}}
  void Hit(float amount,Vector3 point){if(clang){clang.pitch=UnityEngine.Random.Range(.9f,1.1f);clang.Play();}if(sparks){sparks.transform.position=point;sparks.Emit(8);}}
  void Fall(){fall=0;KnockedDown?.Invoke(this);}
  public void Raise(){Health.Restore();fall=0;pivot.localRotation=upright;}
  void Update()
  {
   if(Health.Alive||fall>=1)return;
   fall=Mathf.Min(1,fall+Time.deltaTime/fallSeconds);
   float eased=1-(1-fall)*(1-fall);
   pivot.localRotation=upright*Quaternion.Euler(-fallAngle*eased,0,0);
  }
 }
}
