using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill
{
 /// Gameplay input and the cursor (5 Oct 2026: mouse look is always on in play). While gameplay input is enabled the
 /// cursor is locked and hidden and the pointer delta turns the camera; any open UI (gameplay disabled) frees it, and
 /// holding Free Cursor (Left Alt) frees it during play for the HUD's buttons and movable windows.
 public class GameInput : MonoBehaviour
 {
  public InputActionAsset definition;
  InputActionAsset runtime;
  InputActionMap gameplay,ui;
  bool jumpQueued,locked;
  int settleFrames;
  public System.Func<bool> PointerOverUi;
  public System.Func<bool> MenuPopupOpen;
  public bool GameplayEnabled => gameplay!=null&&gameplay.enabled;
  public Vector2 Move => GameplayEnabled?gameplay["Move"].ReadValue<Vector2>():Vector2.zero;
  public bool Run => GameplayEnabled&&gameplay["Run"].IsPressed();
  /// Free Cursor (Left Alt) is held in play: the cursor is shown and the camera holds still.
  public bool CursorFreed => GameplayEnabled&&gameplay.FindAction("FreeCursor",false)?.IsPressed()==true;
  /// The mouse turns the camera: play, the cursor locked, the window focused.
  public bool Looking => GameplayEnabled&&locked&&!CursorFreed;
  /// Pointer delta for the camera (zero while the cursor is free and for two frames after it locks, when the
  /// recentring shows up as one large jump).
  public Vector2 Look => Looking&&settleFrames==0?gameplay["Look"].ReadValue<Vector2>():Vector2.zero;
  /// Wheel zoom; with a free cursor the wheel scrolls a HUD list under the pointer instead.
  public float Zoom => GameplayEnabled&&(Looking||!(PointerOverUi?.Invoke()??false))?gameplay["Zoom"].ReadValue<float>():0;
  public bool Held(string action) => GameplayEnabled&&gameplay.FindAction(action,false)?.IsPressed()==true;
  public bool Pressed(string action) => GameplayEnabled&&gameplay.FindAction(action,false)?.WasPressedThisFrame()==true;
  /// Fire (left mouse or F) never counts while Free Cursor is held, so clicking the HUD never shoots.
  public bool FirePressed => !CursorFreed&&Pressed("Fire");
  public bool FireHeld => !CursorFreed&&Held("Fire");
  public bool Cancel => ui!=null&&ui["Cancel"].WasPressedThisFrame()&&!(MenuPopupOpen?.Invoke()??false);
  void OnEnable(){runtime=Instantiate(definition);gameplay=runtime.FindActionMap("Gameplay",true);ui=runtime.FindActionMap("UI",true);gameplay["Jump"].performed+=QueueJump;ui.Enable();gameplay.Enable();}
  void Update()
  {
   if(settleFrames>0)settleFrames--;
   // A window that lost focus already shows the cursor; take it back only once the player is in the window again.
   bool want=GameplayEnabled&&!CursorFreed&&Application.isFocused;
   if(want!=locked||want&&Cursor.lockState!=CursorLockMode.Locked)SetLocked(want);
  }
  void SetLocked(bool value)
  {
   if(value&&!locked)settleFrames=2;
   locked=value;
   Cursor.lockState=value?CursorLockMode.Locked:CursorLockMode.None;
   Cursor.visible=!value;
  }
  // Input runs at render cadence; retain a tap until exactly one physics tick consumes it.
  void QueueJump(InputAction.CallbackContext context){jumpQueued=true;}
  public bool ConsumeJump(){bool pressed=GameplayEnabled&&jumpQueued;jumpQueued=false;return pressed;}
  public void SetGameplay(bool enabled){jumpQueued=false;if(enabled)gameplay.Enable();else gameplay.Disable();if(!enabled&&locked)SetLocked(false);}
  void OnDisable(){jumpQueued=false;if(locked)SetLocked(false);if(runtime){runtime.Disable();Destroy(runtime);}}
 }
}
