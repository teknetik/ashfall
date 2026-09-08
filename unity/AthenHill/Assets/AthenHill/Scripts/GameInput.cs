using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill
{
 public class GameInput : MonoBehaviour
 {
  public InputActionAsset definition;
  InputActionAsset runtime;
  InputActionMap gameplay,ui;
  bool looking,jumpQueued;
  public System.Func<bool> PointerOverUi;
  public bool GameplayEnabled => gameplay!=null&&gameplay.enabled;
  public Vector2 Move => GameplayEnabled?gameplay["Move"].ReadValue<Vector2>():Vector2.zero;
  public bool Run => GameplayEnabled&&gameplay["Run"].IsPressed();
  public bool Orbit => GameplayEnabled&&looking;
  public Vector2 Look => Orbit&&!Pressed("Orbit")?gameplay["Look"].ReadValue<Vector2>():Vector2.zero;
  public float Zoom => GameplayEnabled&&!(PointerOverUi?.Invoke()??false)?gameplay["Zoom"].ReadValue<float>():0;
  public bool Pressed(string action) => GameplayEnabled&&gameplay.FindAction(action,false)?.WasPressedThisFrame()==true;
  public bool Cancel => ui!=null&&ui["Cancel"].WasPressedThisFrame();
  void OnEnable(){runtime=Instantiate(definition);gameplay=runtime.FindActionMap("Gameplay",true);ui=runtime.FindActionMap("UI",true);gameplay["Jump"].performed+=QueueJump;ui.Enable();gameplay.Enable();}
  void Update()
  {
   if(!GameplayEnabled||!gameplay["Orbit"].IsPressed())looking=false;
   else if(Pressed("Orbit"))looking=!(PointerOverUi?.Invoke()??false);
  }
  // Input runs at render cadence; retain a tap until exactly one physics tick consumes it.
  void QueueJump(InputAction.CallbackContext context){jumpQueued=true;}
  public bool ConsumeJump(){bool pressed=GameplayEnabled&&jumpQueued;jumpQueued=false;return pressed;}
  public void SetGameplay(bool enabled){looking=false;jumpQueued=false;if(enabled)gameplay.Enable();else gameplay.Disable();}
  void OnDisable(){looking=false;jumpQueued=false;if(runtime){runtime.Disable();Destroy(runtime);}}
 }
}
