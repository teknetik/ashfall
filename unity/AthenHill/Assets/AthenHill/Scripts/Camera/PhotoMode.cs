using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.UIElements;
namespace AthenHill
{
    /// Photo mode (19 Nov 2026, showcase camera). P in play freezes the game (time scale 0; everything here runs on
    /// unscaled time), detaches a free camera with a distance limit and collision, and opens a keyboard-operable panel:
    /// field of view, roll, depth of field (focus, aperture), exposure compensation, time of day, colonist and interface
    /// visibility. Capture writes a 1x PNG of the screen and a supersampled copy to ~/Pictures/Ashfall/.
    /// P or Esc closes it and every change is undone in reverse (camera, lens, time scale, time of day, volumes, overlay
    /// cameras, colonist renderers, interface, input and cursor). It never saves the game or touches quest state, and it
    /// only opens from plain play (no dialogue, window or review camera).
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(1000)]
    public class PhotoMode : MonoBehaviour
    {
        /// Photo mode is open (GameSession skips its own input while this is true).
        public static bool Active { get; private set; }
        public static PhotoMode Current { get; private set; }
        public static string LastCapturePath { get; private set; }
        public static string LastSupersampledPath { get; private set; }
        public static string LastError { get; private set; }
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { Active = false; Current = null; LastCapturePath = LastSupersampledPath = LastError = null; }

        public GameSession session;
        public FollowCamera follow;
        [Tooltip("Found in the scene when empty.")] public CityTimeOfDay clock;
        [Tooltip("The HUD whose document hosts the photo panel. Found in the scene when empty.")] public CityHud hud;
        [Tooltip("UI/PhotoMode.uxml. Without it the panel is built from code with PhotoMode.uss (panelStyle).")]
        public VisualTreeAsset panelTemplate;
        public StyleSheet panelStyle;
        [Header("Free camera")]
        [Min(.1f)] public float moveSpeed = 3;
        [Min(1)] public float fastMultiplier = 4;
        [Range(.01f, 1)] public float slowMultiplier = .25f;
        [Tooltip("The camera stays within this many metres of the colonist's head.")]
        [Min(1)] public float maxDistance = 15;
        [Tooltip("Collision radius of the free camera against the world mask (FollowCamera.worldMask).")]
        [Min(.05f)] public float collisionRadius = .2f;
        [Tooltip("Degrees of field of view per wheel notch.")]
        [Min(.1f)] public float zoomStep = 2;
        [Header("Defaults")]
        [Range(1.4f, 22)] public float defaultAperture = 4;
        [Tooltip("The interface starts hidden; the Interface row shows it again.")]
        public bool hideInterfaceOnOpen = true;
        public DepthOfFieldMode depthOfFieldMode = DepthOfFieldMode.Bokeh;
        [Header("Capture")]
        [Tooltip("Size multiplier of the supersampled copy (1 = no copy).")]
        [Range(1, 4)] public int supersample = 2;
        public string folderName = "Ashfall";
        [Tooltip("Above the conversation camera's volume.")]
        public float volumePriority = 1001;

        public bool IsOpen => open;
        public bool Capturing => capturing;
        public bool PanelShown => panelShown;
        public PhotoControls Controls => controls;
        public string Status { get; private set; } = "";

        bool open, capturing, panelShown, userHidPanel;
        int openedFrame = -10, closedFrame = -10;
        Camera lens;
        GameInput input;
        readonly RestoreLedger ledger = new RestoreLedger();
        PhotoControls controls = new PhotoControls();
        TransientVolume volume;
        float yaw, pitch, appliedHour = -1;
        CameraState start;
        Renderer[] playerRenderers = new Renderer[0];
        bool[] playerEnabled = new bool[0];
        readonly List<(VisualElement element, StyleEnum<DisplayStyle> display)> hiddenInterface = new List<(VisualElement, StyleEnum<DisplayStyle>)>();
        readonly List<(Task<string> task, bool supersampled)> saves = new List<(Task<string>, bool)>();
        // Panel
        VisualElement panelRoot, panel, rowsHost;
        Label statusLabel;
        readonly List<RowView> rows = new List<RowView>();
        sealed class RowView { public PhotoRow row; public VisualElement element; public Slider slider; public Label value; public Button button; }

        void Awake()
        {
            lens = GetComponent<Camera>();
            if (!follow) follow = GetComponent<FollowCamera>();
            if (!session) session = FindAnyObjectByType<GameSession>();
        }
        void Start()
        {
            input = session ? session.input : follow ? follow.input : null;
            if (!clock) clock = FindAnyObjectByType<CityTimeOfDay>();
            if (!hud) hud = FindAnyObjectByType<CityHud>();
        }

        bool CanOpen => isActiveAndEnabled && !open && lens && input && follow && follow.target && session && session.HasStarted
            && session.State == CityState.Play && input.GameplayEnabled && !follow.FixedView && !(input.MenuPopupOpen?.Invoke() ?? false);

        void Update()
        {
            PollSaves();
            if (!open)
            {
                if (input && input.Pressed("PhotoMode") && Time.frameCount - closedFrame > 1) Open();
                return;
            }
            // Something else took over (a developer menu, a scripted state change): give everything back.
            if (!session || session.State != CityState.Play || !input || !input.PhotoEnabled) { Close(); return; }
            if (capturing) return;
            if (Time.frameCount - openedFrame > 1 && input.PhotoPressed("Exit")) { Close(); return; }
            bool coarse = input.PhotoHeld("Fast");
            if (input.PhotoPressed("PanelUp")) controls.MoveSelection(-1);
            if (input.PhotoPressed("PanelDown")) controls.MoveSelection(1);
            if (input.PhotoPressed("PanelLeft")) controls.Adjust(controls.SelectedRow, -1, coarse);
            if (input.PhotoPressed("PanelRight")) controls.Adjust(controls.SelectedRow, 1, coarse);
            if (input.PhotoPressed("PanelSubmit")) Activate(controls.SelectedRow);
            if (input.PhotoPressed("TogglePanel")) { userHidPanel = !userHidPanel; SetPanelShown(!userHidPanel); }
            if (input.PhotoPressed("ResetView")) ResetView();
            // The capture click only counts while the cursor is locked; with Left Alt held the mouse works the panel.
            if (input.PhotoPressed("Capture") && (!(input.PhotoDevice("Capture") is Mouse) || input.Looking)) Capture();
            float wheel = input.PhotoZoom;
            if (Mathf.Abs(wheel) > .01f) controls.FieldOfView = Mathf.Clamp(controls.FieldOfView - Mathf.Sign(wheel) * zoomStep, PhotoControls.MinFieldOfView, PhotoControls.MaxFieldOfView);
        }

        void LateUpdate()
        {
            if (!open) return;
            Fly();
            Apply();
            RefreshPanel();
        }

        // ------------------------------------------------------------------ open / close
        /// Opens photo mode from plain play. False when it is not available (dialogue, window, review camera, menu).
        public bool Open()
        {
            if (!CanOpen) return false;
            open = true; Active = true; Current = this; CinematicCamera.PhotoActive = true;
            openedFrame = Time.frameCount; capturing = false; userHidPanel = false; Status = ""; LastError = null;
            ledger.RestoreAll();
            var conversation = GetComponent<ConversationCamera>(); if (conversation) conversation.Suspend();

            float timeScale = Time.timeScale;
            ledger.Add("time scale", () => { if (session && session.State == CityState.Play) Time.timeScale = timeScale; });
            Time.timeScale = 0;

            ledger.Add("input", () => { if (input) input.SetPhoto(false, session && session.State == CityState.Play); });
            input.SetPhoto(true);

            start = CameraState.Capture(lens);
            var restoreCamera = start;
            ledger.Add("camera", () => restoreCamera.Apply(lens));

            // First-person arms render through overlay cameras stacked on this one; they must not hang in front of a free camera.
            var data = lens.GetUniversalAdditionalCameraData();
            if (data && data.renderType == CameraRenderType.Base && data.cameraStack != null && data.cameraStack.Count > 0)
            {
                var stack = data.cameraStack.ToList();
                data.cameraStack.Clear();
                ledger.Add("overlay cameras", () => { if (!data) return; data.cameraStack.Clear(); foreach (var c in stack) if (c) data.cameraStack.Add(c); });
            }

            // Native QA fix (19 Nov 2026): opened from first person (the container home, or wheeled in) the free camera starts
            // inside the colonist's head, so showing the colonist filled the frame with the inside of the face. Start hidden there;
            // the Colonist row still shows it once the camera has moved away.
            bool startedInside = follow.FirstPerson || follow.PlayerHidden;
            follow.ShowPlayerForPhoto();
            playerRenderers = follow.target.GetComponentsInChildren<Renderer>(true);
            playerEnabled = playerRenderers.Select(r => r && r.enabled).ToArray();
            var renderers = playerRenderers; var enabledFlags = playerEnabled;
            ledger.Add("colonist", () => { for (int i = 0; i < renderers.Length; i++) if (renderers[i]) renderers[i].enabled = enabledFlags[i]; });

            if (!clock) clock = FindAnyObjectByType<CityTimeOfDay>();
            bool hasClock = clock && clock.isActiveAndEnabled;
            if (hasClock)
            {
                var c = clock; float hour = c.Hour;
                ledger.Add("time of day", () => { if (c && Mathf.Abs(Mathf.DeltaAngle(c.Hour * 15, hour * 15)) > .001f) c.SetHour(hour); });
            }

            volume = new TransientVolume("Photo mode volume", volumePriority, TransientVolume.LayerFor(lens), true);
            ledger.Add("volume", () => { if (volume != null) volume.Dispose(); volume = null; });

            ledger.Add("interface", () => ShowInterface());
            EnsurePanel();
            ledger.Add("panel", () => SetPanelShown(false));

            var euler = lens.transform.eulerAngles;
            yaw = euler.y; pitch = Mathf.Clamp(PhotoFlight.WrapPitch(euler.x), -89, 89);
            controls = new PhotoControls
            {
                FieldOfView = Mathf.Clamp(lens.fieldOfView, PhotoControls.MinFieldOfView, PhotoControls.MaxFieldOfView),
                Hour = hasClock ? clock.Hour : 12, FocusDistance = DefaultFocus(), Aperture = defaultAperture,
                HudVisible = !hideInterfaceOnOpen, PlayerVisible = !startedInside, DepthOfField = false,
            };
            appliedHour = controls.Hour;
            SetPanelShown(true);
            Apply();
            RefreshPanel();
            return true;
        }

        /// Closes photo mode and restores everything it changed.
        public void Close()
        {
            if (!open) return;
            StopAllCoroutines();
            open = false; capturing = false; Active = false; CinematicCamera.PhotoActive = false;
            ledger.RestoreAll((name, e) => Debug.LogException(new Exception("Photo mode could not restore " + name, e)));
            closedFrame = Time.frameCount;
            if (hud) hud.Refresh();
        }

        void OnDisable() { Close(); }
        void OnDestroy() { if (Current == this) Current = null; }

        float DefaultFocus()
        {
            // Third person: the colonist is the subject. First person: whatever the view centre rests on.
            var head = follow.target.position + Vector3.up * 1.5f;
            if (follow.Distance > .5f) return Mathf.Clamp(Vector3.Distance(lens.transform.position, head), PhotoControls.MinFocus, PhotoControls.MaxFocus);
            if (Physics.Raycast(lens.transform.position, lens.transform.forward, out var hit, PhotoControls.MaxFocus, follow.worldMask, QueryTriggerInteraction.Ignore))
                return Mathf.Clamp(hit.distance, PhotoControls.MinFocus, PhotoControls.MaxFocus);
            return 10;
        }

        void ResetView()
        {
            start.Apply(lens);
            var euler = start.rotation.eulerAngles; yaw = euler.y; pitch = Mathf.Clamp(PhotoFlight.WrapPitch(euler.x), -89, 89);
            controls.Roll = 0; controls.FieldOfView = Mathf.Clamp(start.fieldOfView, PhotoControls.MinFieldOfView, PhotoControls.MaxFieldOfView);
        }

        void Activate(PhotoRow row)
        {
            if (row == PhotoRow.Capture) Capture();
            else if (row == PhotoRow.Exit) Close();
            else if (PhotoControls.IsToggle(row)) controls.Adjust(row, 1, false);
        }

        // ------------------------------------------------------------------ camera
        void Fly()
        {
            float dt = Mathf.Min(Time.unscaledDeltaTime, .1f);
            var settings = session ? session.Settings : null;
            var look = input.PhotoLook;
            if (look != Vector2.zero)
            {
                float scale = follow.sensitivity * (settings ? settings.Controls.Sensitivity : 1);
                yaw += look.x * scale;
                pitch = Mathf.Clamp(pitch - look.y * scale * (settings && settings.Controls.invertY ? -1 : 1), -89, 89);
            }
            float vertical = (input.PhotoHeld("Rise") ? 1 : 0) - (input.PhotoHeld("Fall") ? 1 : 0);
            float speed = PhotoFlight.Speed(moveSpeed, input.PhotoHeld("Fast"), input.PhotoHeld("Slow"), fastMultiplier, slowMultiplier);
            var position = lens.transform.position;
            var step = PhotoFlight.Displacement(Quaternion.Euler(pitch, yaw, 0), input.PhotoMove, vertical, speed, dt);
            if (step.sqrMagnitude > 1e-10f)
            {
                var anchor = follow.target.position + Vector3.up * 1.5f;
                position = Sweep(position, PhotoFlight.ClampToAnchor(anchor, position + step, maxDistance));
            }
            lens.transform.SetPositionAndRotation(position, Quaternion.Euler(pitch, yaw, controls.Roll));
        }

        /// Moves as far as the world allows, then slides once along what it hit, so the camera can never pass through a
        /// wall, the ground or a roof and leave the world.
        Vector3 Sweep(Vector3 from, Vector3 to)
        {
            var mask = follow.worldMask;
            for (int pass = 0; pass < 2; pass++)
            {
                var d = to - from; float length = d.magnitude;
                if (length < 1e-5f) return from;
                if (!Physics.SphereCast(from, collisionRadius, d / length, out var hit, length, mask, QueryTriggerInteraction.Ignore)) return to;
                var reached = from + d / length * Mathf.Max(0, hit.distance - .02f);
                var rest = Vector3.ProjectOnPlane(to - reached, hit.normal);
                from = reached; to = reached + rest;
            }
            return from;
        }

        void Apply()
        {
            lens.fieldOfView = controls.FieldOfView;
            if (volume != null)
            {
                volume.SetDepthOfField(controls.DepthOfField, depthOfFieldMode, controls.FocusDistance, controls.Aperture, ConversationFraming.FocalLength(controls.FieldOfView));
                volume.SetExposure(TransientVolume.SceneExposure(volume.Volume), controls.Exposure);
            }
            if (clock && clock.isActiveAndEnabled && Mathf.Abs(controls.Hour - appliedHour) > 1e-4f) { clock.SetHour(controls.Hour); appliedHour = controls.Hour; }
            for (int i = 0; i < playerRenderers.Length; i++) if (playerRenderers[i]) playerRenderers[i].enabled = playerEnabled[i] && controls.PlayerVisible;
            if (controls.HudVisible && !capturing) ShowInterface(); else HideInterface();
        }

        // ------------------------------------------------------------------ interface
        /// Hides every UI document's top-level elements except the photo panel. Re-applied every frame, because the HUD
        /// sets its own top-level display on refresh.
        void HideInterface()
        {
            if (hiddenInterface.Count == 0)
                foreach (var doc in FindObjectsByType<UIDocument>(FindObjectsSortMode.None))
                {
                    var root = doc ? doc.rootVisualElement : null;
                    if (root == null) continue;
                    foreach (var child in root.hierarchy.Children())
                        if (child != panelRoot) hiddenInterface.Add((child, child.style.display));
                }
            foreach (var entry in hiddenInterface) entry.element.style.display = DisplayStyle.None;
        }
        void ShowInterface()
        {
            if (hiddenInterface.Count == 0) return;
            foreach (var entry in hiddenInterface) entry.element.style.display = entry.display;
            hiddenInterface.Clear();
            if (hud) hud.Refresh();
        }

        void SetPanelShown(bool shown)
        {
            panelShown = shown && panelRoot != null;
            if (panelRoot != null) panelRoot.style.display = panelShown ? DisplayStyle.Flex : DisplayStyle.None;
        }

        void EnsurePanel()
        {
            if (panelRoot != null && panelRoot.panel != null) return;
            if (!hud) hud = FindAnyObjectByType<CityHud>();
            var doc = hud ? hud.GetComponent<UIDocument>() : FindAnyObjectByType<UIDocument>();
            if (!doc || doc.rootVisualElement == null) return;
            // Hosted inside the HUD's own document so the scene keeps a single UIDocument for QA and focus handling.
            if (panelTemplate) panelRoot = panelTemplate.Instantiate();
            else
            {
                panelRoot = new VisualElement();
                if (panelStyle) panelRoot.styleSheets.Add(panelStyle);
                var p = new VisualElement { name = "photo-panel" }; p.AddToClassList("panel"); panelRoot.Add(p);
                var header = new VisualElement(); header.AddToClassList("photo-header"); p.Add(header);
                var title = new Label("PHOTO MODE"); title.AddToClassList("photo-title"); header.Add(title);
                var paused = new Label("GAME PAUSED"); paused.AddToClassList("photo-paused"); header.Add(paused);
                p.Add(new VisualElement { name = "photo-rows" });
                p.Add(new Label { name = "photo-status" });
                p.Add(new Label { name = "photo-hints" });
            }
            panelRoot.name = "photo-mode";
            panelRoot.AddToClassList("photo-mode");
            panelRoot.pickingMode = PickingMode.Ignore;
            panelRoot.style.position = Position.Absolute; panelRoot.style.left = 0; panelRoot.style.top = 0; panelRoot.style.right = 0; panelRoot.style.bottom = 0;
            panel = panelRoot.Q("photo-panel");
            rowsHost = panelRoot.Q("photo-rows");
            statusLabel = panelRoot.Q<Label>("photo-status");
            statusLabel?.AddToClassList("photo-status");
            var hints = panelRoot.Q<Label>("photo-hints");
            if (hints != null)
            {
                hints.AddToClassList("photo-hints");
                if (string.IsNullOrEmpty(hints.text)) hints.text = "WASD move · Space/E rise · C/Q fall · Shift fast · Ctrl slow · Mouse look · Wheel zoom\n↑↓ choose · ←→ adjust (Shift ×5) · Enter toggle · R reset view · H hide panel · Hold Alt for the cursor";
            }
            BuildRows();
            doc.rootVisualElement.Add(panelRoot);
            SetPanelShown(false);
        }

        void BuildRows()
        {
            rows.Clear();
            if (rowsHost == null) return;
            rowsHost.Clear();
            for (int i = 0; i < PhotoControls.Rows.Length; i++)
            {
                var row = PhotoControls.Rows[i]; int index = i;
                var view = new RowView { row = row, element = new VisualElement { name = "photo-row-" + row } };
                view.element.AddToClassList("photo-row");
                view.element.RegisterCallback<PointerDownEvent>(_ => controls.Selected = index, TrickleDown.TrickleDown);
                if (PhotoControls.IsAction(row))
                {
                    view.button = new Button(() => Activate(row)) { text = PhotoControls.Label(row), focusable = false };
                    view.button.AddToClassList("photo-row-action");
                    view.element.Add(view.button);
                }
                else
                {
                    var label = new Label(PhotoControls.Label(row)) { pickingMode = PickingMode.Ignore };
                    label.AddToClassList("photo-row-label"); view.element.Add(label);
                    if (PhotoControls.IsSlider(row))
                    {
                        PhotoControls.SliderRange(row, out float min, out float max);
                        view.slider = new Slider(min, max) { focusable = false };
                        view.slider.AddToClassList("photo-row-slider");
                        view.slider.RegisterValueChangedCallback(e => { controls.Selected = index; controls.SetFromSlider(row, e.newValue); });
                        view.element.Add(view.slider);
                    }
                    else
                    {
                        view.button = new Button(() => { controls.Selected = index; controls.Adjust(row, 1, false); }) { focusable = false };
                        view.button.AddToClassList("photo-row-toggle"); view.element.Add(view.button);
                    }
                    view.value = new Label { pickingMode = PickingMode.Ignore };
                    view.value.AddToClassList("photo-row-value"); view.element.Add(view.value);
                }
                rowsHost.Add(view.element); rows.Add(view);
            }
        }

        void RefreshPanel()
        {
            if (!panelShown) return;
            bool hasClock = clock && clock.isActiveAndEnabled;
            for (int i = 0; i < rows.Count; i++)
            {
                var v = rows[i];
                v.element.EnableInClassList("photo-row--selected", i == controls.Selected);
                bool usable = (v.row != PhotoRow.FocusDistance && v.row != PhotoRow.Aperture || controls.DepthOfField) && (v.row != PhotoRow.TimeOfDay || hasClock);
                v.element.EnableInClassList("photo-row--dim", !usable);
                if (v.slider != null) v.slider.SetValueWithoutNotify(controls.SliderValue(v.row));
                if (v.value != null) v.value.text = v.row == PhotoRow.TimeOfDay && !hasClock ? "n/a" : controls.Value(v.row);
                if (v.button != null && PhotoControls.IsToggle(v.row)) v.button.text = controls.Value(v.row);
            }
            if (statusLabel != null && statusLabel.text != Status) statusLabel.text = Status;
        }

        // ------------------------------------------------------------------ capture
        /// Saves the current view (1x from the screen, then the supersampled copy). False while a capture is running.
        public bool Capture()
        {
            if (!open || capturing) return false;
            StartCoroutine(CaptureRoutine());
            return true;
        }

        IEnumerator CaptureRoutine()
        {
            capturing = true; Status = "Capturing…"; LastError = null;
            bool panelWas = panelShown;
            SetPanelShown(false); HideInterface();
            // One full frame without the panel and interface, then grab the finished back buffer.
            yield return null;
            yield return new WaitForEndOfFrame();
            string stem = null; Exception error = null;
            Texture2D shot = null;
            try
            {
                shot = ScreenCapture.CaptureScreenshotAsTexture();
                stem = PhotoFiles.Stem(PhotoFiles.DefaultFolder(folderName), DateTime.Now, supersample, File.Exists);
                QueueSave(stem + ".png", shot, false);
            }
            catch (Exception e) { error = e; }
            finally { if (shot) Destroy(shot); }
            SetPanelShown(panelWas && !userHidPanel);
            capturing = false;
            if (error == null && supersample > 1)
            {
                capturing = true;
                yield return null;
                try { RenderSupersampled(PhotoFiles.SupersampledPath(stem, supersample)); }
                catch (Exception e) { error = e; }
                capturing = false;
            }
            if (error != null) { LastError = error.Message; Status = "Capture failed: " + error.Message; Debug.LogException(error); }
        }

        void RenderSupersampled(string path)
        {
            int max = SystemInfo.maxTextureSize;
            int w = Mathf.Min(Screen.width * supersample, max), h = Mathf.Min(Screen.height * supersample, max);
            var rt = new RenderTexture(new RenderTextureDescriptor(w, h, GraphicsFormat.R8G8B8A8_SRGB, 24) { msaaSamples = 1 }) { name = "Photo mode supersampled" };
            var active = RenderTexture.active;
            Texture2D pixels = null;
            try
            {
                rt.Create();
                var request = new RenderPipeline.StandardRequest { destination = rt };
                if (!RenderPipeline.SupportsRenderRequest(lens, request)) throw new InvalidOperationException("The render pipeline cannot render the supersampled copy.");
                RenderPipeline.SubmitRenderRequest(lens, request);
                RenderTexture.active = rt;
                pixels = new Texture2D(w, h, TextureFormat.RGB24, false, false);
                pixels.ReadPixels(new Rect(0, 0, w, h), 0, 0, false);
                QueueSave(path, pixels, true);
            }
            finally
            {
                RenderTexture.active = active;
                if (pixels) Destroy(pixels);
                rt.Release(); Destroy(rt);
            }
        }

        /// PNG encoding and the file write run off the main thread; the texture's bytes are copied first.
        void QueueSave(string path, Texture2D texture, bool supersampled)
        {
            var bytes = texture.GetRawTextureData();
            var format = texture.graphicsFormat; uint w = (uint)texture.width, h = (uint)texture.height;
            int alpha = texture.format == TextureFormat.ARGB32 ? 0 : texture.format == TextureFormat.RGBA32 || texture.format == TextureFormat.BGRA32 ? 3 : -1;
            saves.Add((Task.Run(() =>
            {
                if (alpha >= 0) PhotoFiles.ForceOpaque(bytes, alpha);
                var png = ImageConversion.EncodeArrayToPNG(bytes, format, w, h);
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.WriteAllBytes(path, png);
                return path;
            }), supersampled));
        }

        void PollSaves()
        {
            for (int i = saves.Count - 1; i >= 0; i--)
            {
                var (task, supersampled) = saves[i];
                if (!task.IsCompleted) continue;
                saves.RemoveAt(i);
                if (task.Status == TaskStatus.RanToCompletion)
                {
                    if (supersampled) { LastSupersampledPath = task.Result; Status = "Saved " + LastCapturePath + "\nand " + Path.GetFileName(task.Result); }
                    else { LastCapturePath = task.Result; Status = "Saved " + task.Result; }
                    Debug.Log("Photo mode saved " + task.Result);
                }
                else
                {
                    var e = task.Exception?.GetBaseException();
                    LastError = e != null ? e.Message : "unknown error"; Status = "Capture failed: " + LastError;
                    if (e != null) Debug.LogException(e);
                }
            }
        }
    }
}
