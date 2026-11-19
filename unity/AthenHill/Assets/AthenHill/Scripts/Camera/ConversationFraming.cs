using UnityEngine;
namespace AthenHill
{
    /// Over-the-shoulder conversation framing, kept free of scene state so it can be tested (19 Nov 2026).
    /// Conventions: Unity metres, +Y up; viewport coordinates 0..1 from the bottom-left; field of view is vertical.
    /// "side" is +1 when the camera sits over the player's right shoulder and -1 for the left.
    public static class ConversationFraming
    {
        [System.Serializable]
        public struct Shot
        {
            [Tooltip("Vertical field of view of the conversation lens (degrees).")]
            public float fieldOfView;
            [Tooltip("Metres behind the player's head, along the line to the NPC.")]
            public float back;
            [Tooltip("Metres above the player's head reference point.")]
            public float height;
            [Tooltip("Largest sideways offset from the player's head (metres).")]
            public float maxShoulder;
            [Tooltip("Where the NPC's head lands on screen for a right-shoulder shot (mirrored for the left). Thirds: x 0.667.")]
            public Vector2 npcViewport;
            [Tooltip("Where the player's head should land horizontally for a right-shoulder shot (mirrored for the left).")]
            public float playerViewportX;
            [Tooltip("The player-to-NPC distance is never treated as shorter than this (metres).")]
            public float minDepth;
            // Native QA 19 Nov 2026: back .7 -> 1.25 m, shoulder .65 -> .75 m, player at x .27: at 0.7 m the colonist's back and
            // helmet filled about half the frame width; at 1.25 m they take about a third.
            public static Shot Default => new Shot { fieldOfView = 40, back = 1.25f, height = .05f, maxShoulder = .75f, npcViewport = new Vector2(.667f, .64f), playerViewportX = .27f, minDepth = .8f };
        }

        public struct Pose
        {
            public Vector3 position;
            public Quaternion rotation;
            /// The sideways offset that was used (metres, always >= 0).
            public float shoulder;
        }

        /// The shoulder the camera should use: the side the gameplay camera is already on, so the move is short.
        public static float ChooseSide(Vector3 playerHead, Vector3 npcHead, Vector3 currentCamera)
        {
            var d = Flat(npcHead - playerHead, Vector3.forward);
            var right = Vector3.Cross(Vector3.up, d);
            return Vector3.Dot(currentCamera - playerHead, right) >= 0 ? 1 : -1;
        }

        /// Sideways offset that puts the player's head and the NPC's head the wanted angle apart on screen.
        /// From a camera "back" metres behind the player and "shoulder" metres to the side, the player's head and the NPC
        /// (depth metres further) are atan(s/back) - atan(s/(back+depth)) apart; that grows until s = sqrt(back*(back+depth)),
        /// so the search stops there (or at maxShoulder) and returns the closest achievable offset.
        public static float ShoulderOffset(float back, float depth, float npcNdcX, float playerNdcX, float tanHalfHorizontal, float maxShoulder)
        {
            back = Mathf.Max(.05f, back); depth = Mathf.Max(.05f, depth);
            float want = Mathf.Atan(npcNdcX * tanHalfHorizontal) - Mathf.Atan(playerNdcX * tanHalfHorizontal);
            if (want <= 0) return 0;
            float hi = Mathf.Min(Mathf.Max(0, maxShoulder), Mathf.Sqrt(back * (back + depth)));
            if (Separation(hi, back, depth) <= want) return hi;
            float lo = 0;
            for (int i = 0; i < 40; i++)
            {
                float mid = (lo + hi) * .5f;
                if (Separation(mid, back, depth) < want) lo = mid; else hi = mid;
            }
            return (lo + hi) * .5f;
        }
        public static float Separation(float shoulder, float back, float depth) => Mathf.Atan(shoulder / back) - Mathf.Atan(shoulder / (back + depth));

        /// A roll-free rotation that, for a camera at "from" with this vertical field of view and aspect, puts "target" exactly
        /// at the viewport point. Solved directly (pitch first, then yaw) rather than by aiming at the target and nudging,
        /// so the placement holds at any distance.
        public static Quaternion Aim(Vector3 from, Vector3 target, Vector2 viewport, float verticalFov, float aspect)
        {
            var w = target - from;
            if (w.sqrMagnitude < 1e-8f) return Quaternion.identity;
            w.Normalize();
            float tv = Mathf.Tan(Mathf.Clamp(verticalFov, 1, 179) * .5f * Mathf.Deg2Rad), th = tv * Mathf.Max(.01f, aspect);
            var t = new Vector3((viewport.x * 2 - 1) * th, (viewport.y * 2 - 1) * tv, 1).normalized;
            // Unity's pitch X turns local t to world height t.y*cosX - t.z*sinX = R*cos(X + phi).
            float r = Mathf.Sqrt(t.y * t.y + t.z * t.z), phi = Mathf.Atan2(t.z, t.y);
            float x = Mathf.Acos(Mathf.Clamp(w.y / Mathf.Max(1e-6f, r), -1, 1)) - phi;
            float vz = t.y * Mathf.Sin(x) + t.z * Mathf.Cos(x);
            float y = Mathf.Atan2(w.x, w.z) - Mathf.Atan2(t.x, vz);
            return Quaternion.Euler(x * Mathf.Rad2Deg, y * Mathf.Rad2Deg, 0);
        }

        /// The unobstructed over-the-shoulder pose.
        public static Pose Solve(Vector3 playerHead, Vector3 npcHead, float side, Shot shot, float aspect)
        {
            var flat = npcHead - playerHead; flat.y = 0;
            float depth = Mathf.Max(flat.magnitude, shot.minDepth);
            var d = Flat(flat, Vector3.forward);
            var right = Vector3.Cross(Vector3.up, d);
            side = side < 0 ? -1 : 1;
            float th = Mathf.Tan(Mathf.Clamp(shot.fieldOfView, 1, 179) * .5f * Mathf.Deg2Rad) * Mathf.Max(.01f, aspect);
            float shoulder = ShoulderOffset(shot.back, depth, shot.npcViewport.x * 2 - 1, shot.playerViewportX * 2 - 1, th, shot.maxShoulder);
            var position = playerHead + Vector3.up * shot.height - d * shot.back + right * (side * shoulder);
            var viewport = new Vector2(side > 0 ? shot.npcViewport.x : 1 - shot.npcViewport.x, shot.npcViewport.y);
            return new Pose { position = position, rotation = Aim(position, npcHead, viewport, shot.fieldOfView, aspect), shoulder = shoulder };
        }

        /// Pulls a camera in along the pivot-to-desired line when a sweep hit something hitDistance metres from the pivot
        /// (negative: nothing was hit). Returns the safe position and its distance from the pivot.
        /// Yaw (degrees, Unity's Y rotation) that turns someone at `from` to face `to` on the ground plane; null when they stand
        /// on the same spot.
        public static float? FaceYaw(Vector3 from, Vector3 to)
        {
            float dx = to.x - from.x, dz = to.z - from.z;
            if (dx * dx + dz * dz < .0025f) return null;
            return Mathf.Atan2(dx, dz) * Mathf.Rad2Deg;
        }

        /// The shoulder shot is too tight when the lens was pulled in closer than minClearance to the player's head, or to
        /// less than minFraction of its full distance (the player's head and shoulder then fill the frame and hide the NPC).
        /// Standing closer than this to the NPC (ground plane), the NPC is behind the player's own head and shoulder from any
        /// shoulder position, so the eye line is used (native QA: the player at Mira's counter).
        public static bool TooClose(Vector3 playerHead, Vector3 npcHead, float minSeparation)
        { float dx = npcHead.x - playerHead.x, dz = npcHead.z - playerHead.z; return dx * dx + dz * dz < minSeparation * minSeparation; }

        public static bool TooTight(float clear, float full, float minClearance, float minFraction)
            => clear < minClearance || full > 1e-4f && clear < full * minFraction;

        public static Vector3 PullIn(Vector3 pivot, Vector3 desired, float hitDistance, float margin, out float distance)
        {
            var offset = desired - pivot; float length = offset.magnitude;
            if (length < 1e-5f) { distance = 0; return pivot; }
            distance = hitDistance < 0 ? length : Mathf.Clamp(hitDistance - Mathf.Max(0, margin), 0, length);
            return pivot + offset * (distance / length);
        }

        /// One step of the blend weight (linear in time; the caller eases it). A cut jumps straight to the end.
        public static float StepWeight(float weight, bool on, float deltaTime, float seconds, bool cut)
        {
            if (cut) return on ? 1 : 0;
            return Mathf.MoveTowards(weight, on ? 1 : 0, Mathf.Max(0, deltaTime) / Mathf.Max(.01f, seconds));
        }
        public static float Ease(float weight) { weight = Mathf.Clamp01(weight); return weight * weight * (3 - 2 * weight); }

        /// Focal length (mm) of a full-frame lens (24 mm frame height) with this vertical field of view, so a narrower photo
        /// lens also gives a shallower depth of field. URP's Bokeh pass uses the number as given and clamps the blur radius.
        public static float FocalLength(float verticalFov) => Mathf.Clamp(12f / Mathf.Tan(Mathf.Clamp(verticalFov, 1, 179) * .5f * Mathf.Deg2Rad), 1, 300);

        static Vector3 Flat(Vector3 v, Vector3 fallback) { v.y = 0; return v.sqrMagnitude > 1e-8f ? v.normalized : fallback; }
    }
}
