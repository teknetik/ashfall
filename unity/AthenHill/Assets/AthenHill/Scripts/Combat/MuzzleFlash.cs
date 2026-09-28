using UnityEngine;
namespace AthenHill
{
 /// A short muzzle flash: an additive star card (random roll and size each shot) and an optional light.
 [DisallowMultipleComponent]
 public class MuzzleFlash:MonoBehaviour
 {
  public Renderer card;
  public Light flashLight;
  [Min(.01f)]public float seconds=.045f;
  public Vector2 sizeRange=new Vector2(.09f,.13f);
  [Tooltip("Card length along the barrel relative to its width.")]
  [Min(1)]public float stretch=1.6f;
  public int Flashes {get;private set;}
  float off=-1;
  void Awake(){Hide();}
  public void Fire()
  {
   Flashes++;off=Time.time+seconds;
   if(card)
   {
    float s=Random.Range(sizeRange.x,sizeRange.y);
    card.transform.localRotation=Quaternion.Euler(0,0,Random.Range(0,360f));
    card.transform.localScale=new Vector3(s,s,s*stretch);
    card.enabled=true;
   }
   if(flashLight){flashLight.intensity=flashLight.intensity>0?flashLight.intensity:2;flashLight.enabled=true;}
  }
  void LateUpdate(){if(off>=0&&Time.time>off)Hide();}
  void Hide(){off=-1;if(card)card.enabled=false;if(flashLight)flashLight.enabled=false;}
  void OnDisable(){Hide();}
 }
}
