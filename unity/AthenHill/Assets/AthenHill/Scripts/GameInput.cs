using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill
{
 public class GameInput : MonoBehaviour
 {
  public InputActionAsset definition;
  InputActionAsset runtime;
  InputActionMap gameplay,ui;
  public bool GameplayEnabled => gameplay!=null&&gameplay.enabled;
  public Vector2 Move => GameplayEnabled?gameplay["Move"].ReadValue<Vector2>():Vector2.zero;
  public bool Run => GameplayEnabled&&gameplay["Run"].IsPressed();
  public bool Orbit => GameplayEnabled&&gameplay["Orbit"].IsPressed();
  public Vector2 Look => Orbit?gameplay["Look"].ReadValue<Vector2>():Vector2.zero;
  public bool Pressed(string action) => GameplayEnabled&&gameplay.FindAction(action,false)?.WasPressedThisFrame()==true;
  public bool Cancel => ui!=null&&ui["Cancel"].WasPressedThisFrame();
  void OnEnable(){runtime=Instantiate(definition);gameplay=runtime.FindActionMap("Gameplay",true);ui=runtime.FindActionMap("UI",true);ui.Enable();gameplay.Enable();}
  public void SetGameplay(bool enabled){if(enabled)gameplay.Enable();else gameplay.Disable();}
  void OnDisable(){if(runtime){runtime.Disable();Destroy(runtime);}}
 }
}
