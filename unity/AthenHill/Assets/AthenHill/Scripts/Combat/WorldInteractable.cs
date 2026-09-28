using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// A world object the player can use with E. GameSession prefers colonists and the city terminals first.
 public class WorldInteractable:MonoBehaviour
 {
  public string prompt="E · Use";
  [Min(.5f)]public float range=2.4f;
  public event Action Used;
  static readonly List<WorldInteractable> active=new List<WorldInteractable>();
  void OnEnable(){active.Add(this);}
  void OnDisable(){active.Remove(this);}
  public void Use()=>Used?.Invoke();
  public static WorldInteractable Nearest(Vector3 position)
  {
   WorldInteractable best=null;float bestDistance=float.MaxValue;
   foreach(var item in active)
   {
    float d=Vector3.Distance(item.transform.position,position);
    if(d<=item.range&&d<bestDistance){best=item;bestDistance=d;}
   }
   return best;
  }
 }
}
