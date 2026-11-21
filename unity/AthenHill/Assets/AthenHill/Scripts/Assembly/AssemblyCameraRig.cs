using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;
namespace AthenHill
{
    /// The bench camera (DESIGN.md section 4). It takes the main camera over with a restore ledger, as photo mode
    /// does, because it needs the whole pose, the lens and its own depth of field for minutes at a time, and the
    /// follow camera must write nothing meanwhile (FollowCamera returns early while CinematicCamera.BenchActive). An
    /// overlay like the conversation camera would have to be recomposed over a pose that has no meaning at the bench.
    /// Shots are the cam_bench_* review cameras; the right button orbits a little about the point the shot looks at,
    /// and the wheel moves in on the active part.
    public sealed class AssemblyCameraRig
    {
        readonly AssemblyBench bench; readonly AssemblySettings settings;
        Camera lens; readonly RestoreLedger ledger = new RestoreLedger(); TransientVolume volume;
        Transform shot; Pose from; float fromFov, blend = 1, blendSeconds = .6f;
        float yaw, pitch, zoomTarget; Vector3 focus, focusSmooth, nudge; bool hasFocus;
        public bool Active { get; private set; }
        public string Shot { get; private set; } = "";
        public float Zoom { get; private set; }
        public float Yaw => yaw; public float Pitch => pitch;
        public bool Blending => blend < 1;
        public Camera Lens => lens;

        public AssemblyCameraRig(AssemblyBench bench, AssemblySettings settings) { this.bench = bench; this.settings = settings; }

        public Transform ShotTransform(string name)
        {
            if (!bench.cameraRoot) return null;
            return bench.cameraRoot.Find("cam_bench_" + name) ?? bench.cameraRoot.Find(name);
        }

        public void Enter(Camera camera, bool reducedMotion, string firstShot = "work")
        {
            if (Active || !camera) return;
            lens = camera; Active = true; CinematicCamera.BenchActive = true;
            var start = CameraState.Capture(lens);
            ledger.Add("camera", () => start.Apply(lens));
            ledger.Add("flag", () => CinematicCamera.BenchActive = false);
            // first-person arms render through overlay cameras stacked on this one; they must not hang over the bench
            var data = lens.GetUniversalAdditionalCameraData();
            if (data && data.renderType == CameraRenderType.Base && data.cameraStack != null && data.cameraStack.Count > 0)
            {
                var stack = data.cameraStack.ToList(); data.cameraStack.Clear();
                ledger.Add("overlay cameras", () => { if (!data) return; data.cameraStack.Clear(); foreach (var c in stack) if (c) data.cameraStack.Add(c); });
            }
            float near = lens.nearClipPlane; ledger.Add("near plane", () => { if (lens) lens.nearClipPlane = near; });
            lens.nearClipPlane = Mathf.Min(near, .03f);
            volume = new TransientVolume("Bench camera volume", 1000, TransientVolume.LayerFor(lens), false);
            ledger.Add("volume", () => { volume?.Dispose(); volume = null; });
            yaw = pitch = 0; Zoom = zoomTarget = 0; nudge = Vector3.zero; hasFocus = false;
            shot = null; Shot = "";
            from = new Pose(start.position, start.rotation); fromFov = start.fieldOfView;
            SetShot(firstShot, reducedMotion, settings ? settings.enterSeconds : .8f);
        }

        /// Gives the camera back. Unless it is a cut (Reduced Motion), the eye then travels from the bench to wherever the
        /// follow camera wants it over the same time the way in took.
        public void Exit(bool cut = false)
        {
            if (!Active) return;
            Active = false;
            var from = lens ? new Pose(lens.transform.position, lens.transform.rotation) : default; float fov = lens ? lens.fieldOfView : 60;
            ledger.RestoreAll();
            if (lens && !cut) AssemblyCameraBlendOut.Begin(lens, from, fov, settings ? settings.enterSeconds : .8f);
        }

        /// Moves to a named shot. False when the bench has no such shot (the camera stays where it is).
        public bool SetShot(string name, bool cut = false, float seconds = -1)
        {
            var t = ShotTransform(name);
            if (!t) return false;
            if (t == shot) return true;
            if (lens && shot) { from = new Pose(lens.transform.position, lens.transform.rotation); fromFov = lens.fieldOfView; }
            shot = t; Shot = name; yaw = pitch = 0;
            blendSeconds = Mathf.Max(.01f, seconds > 0 ? seconds : settings ? settings.shotSeconds : .6f);
            blend = cut ? 1 : 0;
            return true;
        }

        /// The point the close view follows and the lens focuses on.
        public void Focus(Vector3 world) { if (!hasFocus) focusSmooth = world; focus = world; hasFocus = true; }
        public void Nudge(Vector3 direction, float metres) { nudge += direction.normalized * metres; }
        public void ZoomTo(float value) { zoomTarget = Mathf.Clamp01(value); }

        public void Tick(float dt, in AssemblyInputFrame f, bool wheelZooms, bool reducedMotion)
        {
            if (!Active || !lens || !shot) return;
            var s = settings;
            // look around: right button drag, or Left Shift with the arrows
            if (f.lookHeld) { yaw += f.delta.x * s.orbitPerPixel; pitch -= f.delta.y * s.orbitPerPixel; }
            // the drag takes hold of the bench (it follows the hand); the keys move the eye (Right goes round to the right, Up goes higher)
            if (f.lookKey) { yaw -= f.navigate.x * s.orbitPerSecond * dt; pitch += f.navigate.y * s.orbitPerSecond * dt; }
            yaw = Mathf.Clamp(yaw, -s.orbitYaw, s.orbitYaw); pitch = Mathf.Clamp(pitch, -s.orbitPitch, s.orbitPitch);
            if (wheelZooms && f.scroll != 0) zoomTarget = Mathf.Clamp01(zoomTarget + f.scroll * s.zoomPerNotch);
            if (f.zoom != 0) zoomTarget = Mathf.Clamp01(zoomTarget + f.zoom * s.zoomPerSecond * dt);
            Zoom = reducedMotion ? zoomTarget : Mathf.Lerp(Zoom, zoomTarget, 1 - Mathf.Exp(-s.zoomFollow * dt));
            focusSmooth = reducedMotion || !hasFocus ? focus : Vector3.Lerp(focusSmooth, focus, 1 - Mathf.Exp(-6 * dt));

            // the shot, orbited about the point it looks at on the work surface
            var up = bench.Up; var basePos = shot.position; var forward = shot.forward;
            var plane = new Plane(up, bench.SurfacePoint);
            Vector3 pivot = plane.Raycast(new Ray(basePos, forward), out float hit) && hit < 2 ? basePos + forward * hit : basePos + forward * 1.2f;
            var arm = basePos - pivot;
            var right = Vector3.Cross(up, -arm).normalized; if (right.sqrMagnitude < 1e-6f) right = shot.right;
            arm = Quaternion.AngleAxis(yaw, up) * (Quaternion.AngleAxis(pitch, right) * arm);
            var position = pivot + arm; var look = pivot;
            if (hasFocus && Zoom > .001f)
            {
                var toFocus = focusSmooth - position; float d = toFocus.magnitude;
                var close = d > s.closeDistance ? focusSmooth - toFocus / d * s.closeDistance : position;
                position = Vector3.Lerp(position, close, Zoom); look = Vector3.Lerp(pivot, focusSmooth, Zoom);
            }
            var rotation = Quaternion.LookRotation((look - position).normalized, up);
            var shotLens = shot.GetComponent<Camera>(); float fov = shotLens ? shotLens.fieldOfView : 55;

            if (blend < 1)
            {
                blend = reducedMotion ? 1 : Mathf.Min(1, blend + dt / blendSeconds);
                float k = blend * blend * (3 - 2 * blend);
                position = Vector3.Lerp(from.position, position, k); rotation = Quaternion.Slerp(from.rotation, rotation, k); fov = Mathf.Lerp(fromFov, fov, k);
            }
            nudge = reducedMotion ? Vector3.zero : Vector3.Lerp(nudge, Vector3.zero, 1 - Mathf.Exp(-14 * dt));
            lens.transform.SetPositionAndRotation(position + nudge, rotation);
            lens.fieldOfView = fov;
            if (volume != null)
            {
                bool dof = s.depthOfField && !reducedMotion && blend >= 1;
                float distance = Vector3.Distance(position, hasFocus ? focusSmooth : look);
                volume.SetDepthOfField(dof, DepthOfFieldMode.Bokeh, distance, Mathf.Lerp(s.aperture * 1.8f, s.aperture, Zoom), ConversationFraming.FocalLength(fov));
            }
        }
    }
}
