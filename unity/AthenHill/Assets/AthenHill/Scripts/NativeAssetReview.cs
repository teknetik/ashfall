#if UNITY_EDITOR || DEBUG
using System;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace AthenHill
{
    // Explicit opt-in development capture only. Moves the diagnostic camera,
    // never the player, assets, materials, settings, colliders or saved scene.
    internal sealed class NativeAssetReview
    {
        AthenDebugBridge bridge;
        Vector3 start, end, target;
        float started, duration;
        int sampledFrames, overlappingFrames;
        string sourceCamera;
        bool active;

        static Vector3 ReadVector(JToken token)
        {
            var array = token as JArray;
            if (array == null || array.Count != 3) throw new ArgumentException("Expected a three-value vector");
            var v = new Vector3((float)array[0], (float)array[1], (float)array[2]);
            if (!float.IsFinite(v.x) || !float.IsFinite(v.y) || !float.IsFinite(v.z)) throw new ArgumentException("Finite coordinates required");
            return v;
        }

        public void Begin(AthenDebugBridge owner, JObject request)
        {
            string camera = (string)request["camera"];
            if (string.IsNullOrEmpty(camera) || !(camera.StartsWith("cam_ground_", StringComparison.Ordinal) ||
                camera.StartsWith("cam_canopy_", StringComparison.Ordinal))) throw new ArgumentException("Use a saved ground or canopy review camera");
            var offset = ReadVector(request["offset"]);
            var lookTarget = ReadVector(request["target"]);
            float seconds = (float)request["seconds"];
            if (!float.IsFinite(seconds) || seconds < 3 || seconds > 30 || offset.magnitude > 4)
                throw new ArgumentOutOfRangeException("Use a 3–30 second pass with at most four metres of camera travel");
            var saved = GameObject.Find(camera);
            if (!saved || !saved.GetComponent<Camera>() || Vector3.Distance(saved.transform.position, lookTarget) < .3f ||
                Vector3.Distance(saved.transform.position, lookTarget) > 20 || Vector3.Distance(saved.transform.position + offset, lookTarget) < .3f)
                throw new ArgumentException("Saved camera and a nearby noncoincident target required");
            float closest = offset.sqrMagnitude > .000001f ? Mathf.Clamp01(Vector3.Dot(lookTarget - saved.transform.position, offset) / offset.sqrMagnitude) : 0;
            if (Vector3.Distance(saved.transform.position + offset * closest, lookTarget) < .3f)
                throw new ArgumentException("The camera path must not cross its look target");
            Cancel();
            bridge = owner; sourceCamera = camera; duration = seconds;
            start = saved.transform.position; end = start + offset; target = lookTarget;
            bridge.View(camera); started = Time.unscaledTime; sampledFrames = overlappingFrames = 0; active = true;
            Tick();
        }

        public void Tick()
        {
            if (!active || !bridge) return;
            float t = Mathf.Clamp01((Time.unscaledTime - started) / duration);
            Vector3 position = Vector3.Lerp(start, end, Mathf.SmoothStep(0, 1, t));
            bridge.follow.transform.SetPositionAndRotation(position, Quaternion.LookRotation(target - position));
            sampledFrames++;
            if (Physics.CheckSphere(position, .08f, bridge.follow.worldMask, QueryTriggerInteraction.Ignore)) overlappingFrames++;
            if (t >= 1) active = false;
        }

        public object Snapshot() => new { purpose = "Continuous diagnostic asset-camera pass; not real player traversal or performance qualification",
            sourceCamera, active, durationSeconds = duration, sampledFrames, overlappingFrames,
            start = new[] { start.x, start.y, start.z }, end = new[] { end.x, end.y, end.z }, target = new[] { target.x, target.y, target.z } };

        public void Cancel() { active = false; }
    }
}
#endif
