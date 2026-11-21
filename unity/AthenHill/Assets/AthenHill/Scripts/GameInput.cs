using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill
{
 /// Gameplay input and the cursor (5 Oct 2026: mouse look is always on in play). While gameplay input is enabled the
 /// cursor is locked and hidden and the pointer delta turns the camera; any open UI (gameplay disabled) frees it, and
 /// holding Free Cursor (Left Alt) frees it during play for the HUD's buttons and movable windows.
 /// Photo mode (19 Nov 2026) has its own action map: while it is enabled gameplay is off, the cursor stays locked for
 /// the free camera (Left Alt frees it for the panel) and the UI Cancel action is withheld so Esc never pauses.
 public class GameInput : MonoBehaviour
 {
  public InputActionAsset definition;
  InputActionAsset runtime;
  InputActionMap gameplay,ui,photo,bench;
  bool jumpQueued,dodgeQueued,locked;
  int settleFrames,photoClosedFrame=-10;
  public System.Func<bool> PointerOverUi;
  public System.Func<bool> MenuPopupOpen;
  public bool GameplayEnabled => gameplay!=null&&gameplay.enabled;
  public bool PhotoEnabled => photo!=null&&photo.enabled;
  /// The Bench map (Steady Hands bench, 20 Nov 2026): on while the assembly session works. The cursor is free and visible
  /// at the bench, because neither gameplay nor photo input is enabled.
  public bool BenchEnabled => bench!=null&&bench.enabled;
  public InputAction BenchAction(string action) => BenchEnabled?bench.FindAction(action,false):null;
  public void SetBench(bool enabled){if(bench==null)return;if(enabled){gameplay.Disable();photo?.Disable();bench.Enable();}else bench.Disable();}
  public Vector2 Move => GameplayEnabled?gameplay["Move"].ReadValue<Vector2>():Vector2.zero;
  public bool Run => GameplayEnabled&&gameplay["Run"].IsPressed();
  /// Free Cursor (Left Alt) is held in play or photo mode: the cursor is shown and the camera holds still.
  public bool CursorFreed => GameplayEnabled&&gameplay.FindAction("FreeCursor",false)?.IsPressed()==true||PhotoEnabled&&photo.FindAction("FreeCursor",false)?.IsPressed()==true;
  /// The mouse turns the camera: play (or photo mode), the cursor locked, the window focused.
  public bool Looking => (GameplayEnabled||PhotoEnabled)&&locked&&!CursorFreed;
  /// Pointer delta for the camera (zero while the cursor is free and for two frames after it locks, when the
  /// recentring shows up as one large jump).
  public Vector2 Look => Looking&&settleFrames==0&&GameplayEnabled?gameplay["Look"].ReadValue<Vector2>():Vector2.zero;
  /// Wheel zoom; with a free cursor the wheel scrolls a HUD list under the pointer instead.
  public float Zoom => GameplayEnabled&&(Looking||!(PointerOverUi?.Invoke()??false))?gameplay["Zoom"].ReadValue<float>():0;
  public bool Held(string action) => GameplayEnabled&&gameplay.FindAction(action,false)?.IsPressed()==true;
  public bool Pressed(string action) => GameplayEnabled&&gameplay.FindAction(action,false)?.WasPressedThisFrame()==true;
  /// Fire (left mouse or F) never counts while Free Cursor is held, so clicking the HUD never shoots.
  public bool FirePressed => !CursorFreed&&Pressed("Fire");
  public bool FireHeld => !CursorFreed&&Held("Fire");
  /// Esc on the frame photo mode closed belongs to photo mode, not to the pause menu.
  public bool Cancel => ui!=null&&ui["Cancel"].WasPressedThisFrame()&&!PhotoEnabled&&Time.frameCount-photoClosedFrame>1&&!(MenuPopupOpen?.Invoke()??false);
  /// World map key (M, 19 Nov 2026). It lives in the always-on UI map so the same key closes the map window, where
  /// gameplay input is off.
  public bool MapPressed => ui!=null&&!PhotoEnabled&&ui.FindAction("Map",false)?.WasPressedThisFrame()==true&&!(MenuPopupOpen?.Invoke()??false);
  // ---- Photo mode map (PhotoMode drives it; nothing else reads it).
  public bool PhotoHeld(string action) => PhotoEnabled&&photo.FindAction(action,false)?.IsPressed()==true;
  public bool PhotoPressed(string action) => PhotoEnabled&&photo.FindAction(action,false)?.WasPressedThisFrame()==true;
  public Vector2 PhotoMove => PhotoEnabled?photo["Move"].ReadValue<Vector2>():Vector2.zero;
  public Vector2 PhotoLook => PhotoEnabled&&Looking&&settleFrames==0?photo["Look"].ReadValue<Vector2>():Vector2.zero;
  public float PhotoZoom => PhotoEnabled&&Looking?photo["Zoom"].ReadValue<float>():0;
  /// The device that triggered a photo action this frame (the capture click is only honoured with the cursor locked).
  public InputDevice PhotoDevice(string action) => PhotoEnabled?photo.FindAction(action,false)?.activeControl?.device:null;
  /// Swaps gameplay for the photo map (true) or back (false); gameplay is restored only when asked, because the session
  /// may have left Play meanwhile.
  public void SetPhoto(bool enabled,bool gameplayAfter=true)
  {
   if(photo==null)return;
   jumpQueued=false;dodgeQueued=false;
   if(enabled){gameplay.Disable();photo.Enable();}
   else{photo.Disable();photoClosedFrame=Time.frameCount;if(gameplayAfter)gameplay.Enable();else if(locked)SetLocked(false);}
  }
  void OnEnable(){runtime=Instantiate(definition);gameplay=runtime.FindActionMap("Gameplay",true);ui=runtime.FindActionMap("UI",true);photo=runtime.FindActionMap("Photo",false);bench=runtime.FindActionMap("Bench",false);bench?.Disable();gameplay["Jump"].performed+=QueueJump;var dodge=gameplay.FindAction("Dodge",false);if(dodge!=null)dodge.performed+=QueueDodge;ui.Enable();gameplay.Enable();}
  void Update()
  {
   if(settleFrames>0)settleFrames--;
   // A window that lost focus already shows the cursor; take it back only once the player is in the window again.
   bool want=(GameplayEnabled||PhotoEnabled)&&!CursorFreed&&Application.isFocused;
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
  void QueueDodge(InputAction.CallbackContext context){dodgeQueued=true;}
  public bool ConsumeJump(){bool pressed=GameplayEnabled&&jumpQueued;jumpQueued=false;return pressed;}
  public bool ConsumeDodge(){bool pressed=GameplayEnabled&&dodgeQueued;dodgeQueued=false;return pressed;}
  public void SetGameplay(bool enabled){jumpQueued=false;dodgeQueued=false;if(enabled){photo?.Disable();bench?.Disable();gameplay.Enable();}else gameplay.Disable();if(!enabled&&locked&&!PhotoEnabled)SetLocked(false);}
  void OnDisable(){jumpQueued=false;dodgeQueued=false;if(locked)SetLocked(false);if(runtime){runtime.Disable();Destroy(runtime);}}
 }
}
