using UnityEngine;
#if UNITY_EDITOR || DEBUG
using System;
using System.Collections;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;
#endif

namespace AthenHill
{
    // All input, UI construction and commands compile out of a release player.
    [DefaultExecutionOrder(-200)]
    public sealed class DeveloperTimeMenu : MonoBehaviour
    {
        public CityTimeOfDay clock;
        public CityHud hud;
        public UnityEngine.UIElements.VisualTreeAsset layout;
#if UNITY_EDITOR || DEBUG
        public bool IsOpen { get; private set; }
        VisualElement overlay, panel, shade, tree;
        Label readout, status, reflectionStatus;
        Slider slider;
        FloatField hourField;
        Button play;
        Func<bool> previousPopup, previousPointer, popupGuard, pointerGuard;
        bool resumeOnClose, installed, hasStarted;
        int closeFrame = -10;
        float nextReadout;
        StyleEnum<DisplayStyle> oldShadeDisplay;

        IEnumerator Start()
        {
            if (!Application.isEditor && !Debug.isDebugBuild) { enabled = false; yield break; }
            hasStarted = true;
            // CityHud installs its own input predicates in Start; preserve them after that binding.
            yield return null;
            Install();
        }
        void OnEnable() { if (hasStarted) StartCoroutine(Reinstall()); }
        IEnumerator Reinstall() { yield return null; if (isActiveAndEnabled) Install(); }
        void Install()
        {
            if (installed || !clock || !hud || !layout || !hud.session || !hud.session.input) return;
            var document = hud.GetComponent<UIDocument>(); if (!document || document.rootVisualElement == null) return;
            tree = layout.CloneTree(); tree.pickingMode = PickingMode.Ignore;
            tree.style.position = Position.Absolute; tree.style.left = 0; tree.style.right = 0; tree.style.top = 0; tree.style.bottom = 0;
            overlay = tree.Q("developer-time-overlay"); document.rootVisualElement.Add(tree);
            panel = overlay.Q("developer-time-panel"); shade = document.rootVisualElement.Q("shade");
            readout = overlay.Q<Label>("developer-time-readout"); status = overlay.Q<Label>("developer-time-status");
            reflectionStatus = overlay.Q<Label>("developer-time-reflections");
            slider = overlay.Q<Slider>("developer-time-slider"); hourField = overlay.Q<FloatField>("developer-time-hour");
            play = overlay.Q<Button>("developer-time-play");
            Bind("close", CloseMenu); Bind("dawn", () => SelectTime(6.5f)); Bind("noon", () => SelectTime(clock.profile.defaultHour));
            Bind("dusk", () => SelectTime(17.5f)); Bind("night", () => SelectTime(0));
            Bind("play", () => { clock.Paused = !clock.Paused; Refresh(); });
            Bind("speed1", () => Speed(1)); Bind("speed10", () => Speed(10)); Bind("speed60", () => Speed(60));
            Bind("reset", () => { clock.ResetToAuthoredDefault(); Refresh(); });
            slider.RegisterValueChangedCallback(e => SelectTime(e.newValue));
            hourField.RegisterValueChangedCallback(e => { if (ClockMath.Finite(e.newValue)) SelectTime(e.newValue); else Refresh(); });
            var input = hud.session.input;
            previousPopup = input.MenuPopupOpen; previousPointer = input.PointerOverUi;
            popupGuard = () => IsOpen || Time.frameCount - closeFrame <= 1 || (previousPopup?.Invoke() ?? false);
            pointerGuard = () => IsOpen || (previousPointer?.Invoke() ?? false);
            input.MenuPopupOpen = popupGuard; input.PointerOverUi = pointerGuard; installed = true;
        }
        void Bind(string name, Action action) => overlay.Q<Button>("developer-time-" + name).clicked += action;
        void Speed(float value) { clock.SetSpeed(value); Refresh(); }
        void SelectTime(float value) { clock.Paused = true; clock.SetHour(value); Refresh(); }
        void Update()
        {
            if (!installed) return;
            var keyboard = Keyboard.current;
            if (keyboard != null && keyboard.f8Key.wasPressedThisFrame) { if (IsOpen) CloseMenu(); else OpenMenu(); }
            else if (IsOpen && keyboard != null && keyboard.escapeKey.wasPressedThisFrame) CloseMenu();
        }
        void LateUpdate()
        {
            if (!IsOpen) return;
            // Changed events from settings must not reintroduce the dimmed pause sheet over a lighting review.
            if (shade != null) shade.style.display = DisplayStyle.None;
            if (Time.unscaledTime >= nextReadout) { nextReadout = Time.unscaledTime + .1f; Refresh(); }
        }
        public void OpenMenu()
        {
            if (!installed || IsOpen || (hud.session.State != CityState.Play && hud.session.State != CityState.Paused)) return;
            resumeOnClose = hud.session.State == CityState.Play;
            hud.session.Open(CityState.Paused);
            if (shade != null) { oldShadeDisplay = shade.style.display; shade.style.display = DisplayStyle.None; }
            IsOpen = true; clock.PreviewWhilePaused = true; overlay.style.display = DisplayStyle.Flex;
            Refresh(); overlay.schedule.Execute(() => overlay.Q<Button>("developer-time-dawn").Focus());
        }
        public void CloseMenu()
        {
            if (!IsOpen) return;
            IsOpen = false; closeFrame = Time.frameCount; clock.PreviewWhilePaused = false;
            overlay.style.display = DisplayStyle.None;
            if (shade != null) shade.style.display = oldShadeDisplay;
            if (resumeOnClose && hud && hud.session && hud.session.State == CityState.Paused) hud.session.Close();
            else if (hud) hud.Refresh();
        }
        void Refresh()
        {
            if (overlay == null || !clock) return;
            int minute = Mathf.FloorToInt(clock.Hour * 60) % 1440;
            readout.text = $"{minute / 60:00}:{minute % 60:00}";
            slider.SetValueWithoutNotify(clock.Hour); hourField.SetValueWithoutNotify((float)Math.Round(clock.Hour, 2));
            play.text = clock.Paused ? "Resume clock" : "Pause clock";
            status.text = clock.ReducedMotionSpeedLimited ? "Reduced motion limits playback to 1×." : $"{clock.Speed:0.#}× speed · {clock.profile.realMinutesPerCycle:0.#} minutes per full cycle at 1×";
            reflectionStatus.text = clock.reflections ? clock.reflections.Status : "Reflection controller unavailable";
            foreach (int speed in new[] { 1, 10, 60 }) overlay.Q("developer-time-speed" + speed).EnableInClassList("selected", Mathf.Approximately(clock.Speed, speed));
            panel.EnableInClassList("small-window", Screen.width < 1500 || Screen.height < 900);
        }
        void OnDisable()
        {
            CloseMenu();
            if (installed && hud && hud.session && hud.session.input)
            {
                var input = hud.session.input;
                if (input.MenuPopupOpen == popupGuard) input.MenuPopupOpen = previousPopup;
                if (input.PointerOverUi == pointerGuard) input.PointerOverUi = previousPointer;
            }
            tree?.RemoveFromHierarchy(); tree = overlay = null; installed = false;
        }
#else
        public bool IsOpen => false;
        void OnEnable() { enabled = false; }
#endif
    }
}
