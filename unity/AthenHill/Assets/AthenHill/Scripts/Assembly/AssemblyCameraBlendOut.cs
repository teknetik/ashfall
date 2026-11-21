using UnityEngine;
namespace AthenHill
{
    /// The way back from the bench (DESIGN.md section 4: entering blends, so leaving does too). When the bench camera lets
    /// go, the follow camera has the view again at once and writes its pose every LateUpdate from its own state; this runs
    /// after it for a moment and carries the eye there from where the bench camera stood. It reads the pose the follow
    /// camera has just written, so it follows the player if they move off during the blend. Reduced Motion cuts instead
    /// (the rig does not start it). Photo mode, a conversation or the bench taking the camera again ends it.
    [DefaultExecutionOrder(900)]
    public sealed class AssemblyCameraBlendOut : MonoBehaviour
    {
        Camera lens; Pose from; float fromFov, toFov, seconds, t;
        public static bool Running { get; private set; }

        public static void Begin(Camera lens, Pose from, float fromFov, float seconds)
        {
            if (!lens || seconds <= 0 || !Application.isPlaying) return;
            var b = lens.GetComponent<AssemblyCameraBlendOut>(); if (!b) b = lens.gameObject.AddComponent<AssemblyCameraBlendOut>();
            b.hideFlags = HideFlags.DontSave; b.lens = lens; b.from = from; b.fromFov = fromFov; b.toFov = lens.fieldOfView; b.seconds = seconds; b.t = 0;
            Running = true;
        }
        void LateUpdate()
        {
            if (!lens || CinematicCamera.UnderControl) { Destroy(this); return; }
            t += Time.unscaledDeltaTime; float k = Mathf.Clamp01(t / seconds); k = k * k * (3 - 2 * k);
            var to = new Pose(lens.transform.position, lens.transform.rotation);
            lens.transform.SetPositionAndRotation(Vector3.Lerp(from.position, to.position, k), Quaternion.Slerp(from.rotation, to.rotation, k));
            lens.fieldOfView = Mathf.Lerp(fromFov, toFov, k);
            if (k >= 1) { lens.fieldOfView = toFov; Destroy(this); }
        }
        void OnDestroy() { Running = false; }
    }
}
