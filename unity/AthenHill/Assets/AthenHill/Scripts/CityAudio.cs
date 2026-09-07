using UnityEngine;
namespace AthenHill
{
 public class CityAudio:MonoBehaviour
 {
  public GameSession session;
  public AudioSource ambience,steps,confirmation,latticeHum,ringHum;
  [Min(.1f)]public float walkStepDistance=.95f,runStepDistance=1.45f;
  public int StepCount {get;private set;}
  public int ClickCount {get;private set;}
  float distance,lastClick=-1;CityState previous;int logCount;
  void Start(){previous=session.State;session.Changed+=Changed;}
  void OnDestroy(){if(session)session.Changed-=Changed;}
  void Update()
  {
   if(session.State!=CityState.Play||!session.player.Grounded||session.player.Speed<.12f){distance=0;return;}
   distance+=session.player.Speed*Mathf.Min(Time.deltaTime,.1f);
   float stride=session.player.Speed>4.5f?runStepDistance:walkStepDistance;
   if(distance>=stride){distance%=stride;steps.pitch=++StepCount%2==0?1.03f:.97f;steps.PlayOneShot(steps.clip);}
  }
  void Changed()
  {
   bool changed=previous!=session.State||logCount!=session.LogRevision;
   previous=session.State;logCount=session.LogRevision;
   if(changed&&Time.unscaledTime-lastClick>.08f){lastClick=Time.unscaledTime;confirmation.PlayOneShot(confirmation.clip);ClickCount++;}
  }
 }
}
