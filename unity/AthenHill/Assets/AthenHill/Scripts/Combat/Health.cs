using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// Hit points shared by the player, feral droids and range targets. Tuning is serialized.
 public class Health:MonoBehaviour
 {
  [Min(1)]public float max=100;
  [Tooltip("Points restored per second once no damage has been taken for Regen Delay seconds.")]
  [Min(0)]public float regenPerSecond,regenDelay=5;
  [Tooltip("Hostile or practice targets the scrap pistol's aim assist may select.")]
  public bool aimTarget=true;
  [Tooltip("Aim assist and HUD bars use this point, relative to the transform.")]
  public Vector3 aimOffset=new Vector3(0,1,0);
  public float Current {get;private set;}
  public bool Alive=>Current>0;
  public float Fraction=>Current/max;
  public float LastDamageTime {get;private set;}=-99;
  public Vector3 AimPoint=>transform.TransformPoint(aimOffset);
  public event Action<float,Vector3> Damaged;
  public event Action Died;
  public static readonly List<Health> Targets=new List<Health>();
  void Awake(){Current=max;}
  void OnEnable(){if(aimTarget)Targets.Add(this);}
  void OnDisable(){Targets.Remove(this);}
  void Update(){if(Alive&&regenPerSecond>0&&Current<max&&Time.time-LastDamageTime>regenDelay)Current=Mathf.Min(max,Current+regenPerSecond*Time.deltaTime);}
  public bool Damage(float amount,Vector3 point)
  {
   if(!Alive||amount<=0)return false;
   Current=Mathf.Max(0,Current-amount);LastDamageTime=Time.time;
   Damaged?.Invoke(amount,point);
   if(Current<=0)Died?.Invoke();
   return true;
  }
  public void Heal(float amount){if(Alive&&amount>0)Current=Mathf.Min(max,Current+amount);}
  public void Restore(){Current=max;LastDamageTime=-99;}
 }
}
