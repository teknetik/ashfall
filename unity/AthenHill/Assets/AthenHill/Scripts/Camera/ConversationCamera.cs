using UnityEngine;
using UnityEngine.Rendering.Universal;
namespace AthenHill
{
    /// Conversation camera (19 Nov 2026, showcase camera). While a dialogue is open, FollowCamera hands its gameplay pose
    /// to <see cref="Compose"/>, which eases it to an over-the-shoulder framing (the NPC's head on a thirds line, the
    /// player's shoulder in the foreground) and adds a mild depth of field through a transient volume. It never changes
    /// FollowCamera's yaw, pitch, boom or zoom, so when the weight returns to zero the gameplay pose is exactly what it
    /// was. In first person (including the container home's confined view) only the depth of field is applied.
    /// Reduced Motion cuts instead of easing. Off with <see cref="framingEnabled"/> or the static <see cref="Enabled"/>.
    [DisallowMultipleComponent]
    public class ConversationCamera : MonoBehaviour
    {
        /// Game-wide switch (a Settings toggle can drive this). Both this and the serialized flag must be on.
        public static bool Enabled { get; set; } = true;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { Enabled = true; }

        [Tooltip("Serialized switch for this camera; the static ConversationCamera.Enabled must also be on.")]
        public bool framingEnabled = true;
        public GameSession session;
        public FollowCamera follow;
        [Header("Framing")]
        public ConversationFraming.Shot shot = ConversationFraming.Shot.Default;
        [Tooltip("Height of the player's head reference above the feet (metres).")]
        [Min(.5f)] public float playerHeadHeight = 1.58f;
        [Tooltip("Height used for the NPC's head when no head bone is found (metres above the root).")]
        [Min(.5f)] public float npcHeadFallback = 1.6f;
        [Tooltip("Seconds for the NPC head target to settle (smooths the talk animation's head sway out of the framing).")]
        [Min(0)] public float headSmoothing = .25f;
        [Header("Safety")]
        [Tooltip("Radius swept from the player's head to the lens.")]
        [Min(.01f)] public float sweepRadius = .18f;
        [Min(0)] public float wallMargin = .05f;
        [Tooltip("Closer than this to the player's head after pulling in, the shot falls back to the player's eye line.")]
        [Min(0)] public float minClearance = .35f;
        [Tooltip("Pulled in to less than this share of the full shoulder distance, the player's own head and shoulder fill the frame and hide the NPC, so the shot falls back to the eye line (native QA, 19 Nov 2026: Mira across her counter, Torr by the slab).")]
        [Range(0, 1)] public float minShotFraction = .75f;
        [Tooltip("Closer than this to the NPC (metres, ground plane) the shot uses the eye line: the NPC would stand behind the player's own head.")]
        [Min(0)] public float minSeparation = 1.2f;
        [Tooltip("On the eye-line fallback the lens stays at least this far from the NPC's head (metres, ground plane), pulled back from the player's eye.")]
        [Min(0)] public float eyeLineDistance = 1.3f;
        [Tooltip("The lens never comes closer than this to the NPC's head (metres).")]
        [Min(0)] public float npcClearance = .5f;
        [Header("Blend")]
        [Min(.01f)] public float blendSeconds = .6f;
        [Header("Depth of field")]
        public bool depthOfField = true;
        public DepthOfFieldMode depthOfFieldMode = DepthOfFieldMode.Bokeh;
        [Range(1, 32)] public float aperture = 5.6f;
        [Range(1, 300)] public float focalLength = 50;
        [Tooltip("Above the scene's grade volume (priority 20) and below photo mode.")]
        public float volumePriority = 1000;

        public float Weight => weight;
        public bool Engaged => weight > 0;
        /// The third-person over-the-shoulder pose is in use (false in first person and when blended out).
        public bool Framing => weight > 0 && !firstPerson;
        /// The shoulder shot was blocked and the camera sits on the player's eye line instead.
        public bool EyeLine => weight > 0 && !firstPerson && eyeFallback;
        public NpcAgent Subject => subject;
        public float Side => side;
        public bool HidesPlayer => weight > .5f && !firstPerson && eyeFallback;
        public float FocusDistance { get; private set; }
        /// Share of the full shoulder distance left after the obstruction sweep (1 = nothing in the way; QA).
        public float ShotFraction { get; private set; } = 1;

        float weight, side = 1;
        bool firstPerson, eyeFallback;
        NpcAgent subject;
        Transform head;
        Vector3 smoothedHead, headVelocity;
        TransientVolume volume;
        Camera lens;

        void Awake()
        {
            lens = GetComponent<Camera>();
            if (!follow) follow = GetComponent<FollowCamera>();
            if (!session) session = FindAnyObjectByType<GameSession>();
        }

        bool Wanted => Enabled && framingEnabled && session && session.State == CityState.Dialogue && session.ActiveNpc && !CinematicCamera.PhotoActive;

        /// Called by FollowCamera every LateUpdate with the gameplay pose it is about to write. Returns the eased weight.
        public float Compose(Vector3 playerFeet, bool firstPersonView, ref Vector3 position, ref Quaternion rotation, ref float fieldOfView)
        {
            bool wanted = Wanted;
            if (wanted && subject != session.ActiveNpc) Begin(session.ActiveNpc, playerFeet, position, firstPersonView);
            bool cut = session && session.reducedMotion;
            // Native QA (19 Nov 2026): the colonist turns to face the NPC while the dialogue is open (an over-the-shoulder
            // shot must show the back of the player's head), through PlayerMotor's facing; released on close. First person: nothing.
            var motor = session ? session.player : null;
            if (motor)
            {
                motor.TalkYaw = wanted && subject && !firstPerson ? ConversationFraming.FaceYaw(playerFeet, subject.transform.position) : null;
                motor.TalkYawSnap = cut;
            }
            weight = ConversationFraming.StepWeight(weight, wanted, Time.unscaledDeltaTime, blendSeconds, cut);
            if (weight <= 0 || !subject) { Suspend(); return 0; }
            CinematicCamera.ConversationEngaged = true;
            var headNow = HeadPosition();
            smoothedHead = cut || headSmoothing <= 0 ? headNow : Vector3.SmoothDamp(smoothedHead, headNow, ref headVelocity, headSmoothing, Mathf.Infinity, Time.unscaledDeltaTime);
            float e = ConversationFraming.Ease(weight);
            if (!firstPerson)
            {
                var pivot = playerFeet + Vector3.up * playerHeadHeight;
                var shotPose = ShoulderPose(pivot, smoothedHead, out eyeFallback);
                var blended = Vector3.Lerp(position, shotPose.position, e);
                // Both ends are clear; the straight path between them may cut a corner, so it is swept again.
                position = Sweep(pivot, blended, out _);
                rotation = Quaternion.Slerp(rotation, shotPose.rotation, e);
                fieldOfView = Mathf.Lerp(fieldOfView, shot.fieldOfView, e);
            }
            FocusDistance = Vector3.Distance(position, smoothedHead);
            UpdateVolume(e);
            return e;
        }

        /// Drops the framing at once (photo mode, fixed review cameras, a missing subject).
        public void Suspend()
        {
            weight = 0; subject = null; head = null; eyeFallback = false;
            if (session && session.player) session.player.TalkYaw = null;
            CinematicCamera.ConversationEngaged = false;
            if (volume != null) { volume.Dispose(); volume = null; }
        }

        void Begin(NpcAgent npc, Vector3 playerFeet, Vector3 cameraPosition, bool firstPersonView)
        {
            subject = npc; head = FindHead(npc); headVelocity = Vector3.zero;
            smoothedHead = HeadPosition();
            // Decided once per conversation: switching first person or shoulder mid-dialogue would read as a cut.
            firstPerson = firstPersonView;
            var pivot = playerFeet + Vector3.up * playerHeadHeight;
            side = ConversationFraming.ChooseSide(pivot, smoothedHead, cameraPosition);
            // Prefer the other shoulder when the chosen one is walled in and the other is not.
            if (!firstPerson)
            {
                Clearance(pivot, smoothedHead, side, out float near);
                Clearance(pivot, smoothedHead, -side, out float far);
                if (near < .7f && far > near + .1f) side = -side;
            }
        }

        ConversationFraming.Pose ShoulderPose(Vector3 pivot, Vector3 npcHead, out bool fallback)
        {
            float aspect = lens ? lens.aspect : 16f / 9;
            var pose = ConversationFraming.Solve(pivot, npcHead, side, shot, aspect);
            float full = Vector3.Distance(pivot, pose.position);
            pose.position = Sweep(pivot, pose.position, out float clear);
            ShotFraction = full > 1e-4f ? clear / full : 1;
            fallback = ConversationFraming.TooTight(clear, full, minClearance, minShotFraction) || ConversationFraming.TooClose(pivot, npcHead, minSeparation) || Vector3.Distance(pose.position, npcHead) < npcClearance;
            if (!fallback) { pose.rotation = ConversationFraming.Aim(pose.position, npcHead, new Vector2(side > 0 ? shot.npcViewport.x : 1 - shot.npcViewport.x, shot.npcViewport.y), shot.fieldOfView, aspect); return pose; }
            // Too tight for a shoulder shot: look from the player's eye line, NPC centred (FollowCamera hides the body).
            var eye = pivot + Vector3.up * .07f;
            // Native QA (19 Nov 2026): standing right at the NPC (Mira across her counter) the eye line was a few decimetres from
            // her face. Step the lens back along the line from the NPC to at least eyeLineDistance, swept against the world.
            var away = eye - npcHead; away.y = 0;
            float gap = away.magnitude;
            if (gap < eyeLineDistance && gap > 1e-3f) eye = Sweep(pivot, eye + away / gap * (eyeLineDistance - gap), out _);
            return new ConversationFraming.Pose { position = eye, rotation = ConversationFraming.Aim(eye, npcHead, new Vector2(.5f, .55f), shot.fieldOfView, aspect) };
        }

        /// How far the lens can go from the pivot toward the shoulder pose of one side before something is in the way
        /// (as a fraction of the full distance).
        void Clearance(Vector3 pivot, Vector3 npcHead, float s, out float fraction)
        {
            var pose = ConversationFraming.Solve(pivot, npcHead, s, shot, lens ? lens.aspect : 16f / 9);
            float full = Vector3.Distance(pivot, pose.position);
            Sweep(pivot, pose.position, out float clear);
            fraction = full > 1e-4f ? clear / full : 1;
        }

        Vector3 Sweep(Vector3 pivot, Vector3 desired, out float distance)
        {
            var offset = desired - pivot; float length = offset.magnitude;
            float hit = -1;
            if (length > 1e-4f && follow && Physics.SphereCast(pivot, sweepRadius, offset / length, out var h, length, follow.worldMask, QueryTriggerInteraction.Ignore)) hit = h.distance;
            return ConversationFraming.PullIn(pivot, desired, hit, wallMargin, out distance);
        }

        void UpdateVolume(float e)
        {
            if (!depthOfField) { if (volume != null) { volume.Dispose(); volume = null; } return; }
            if (volume == null || !volume.Alive) volume = new TransientVolume("Conversation depth of field", volumePriority, TransientVolume.LayerFor(lens), false);
            // Blend through the aperture (f/32 is nearly sharp) with the focus already on the NPC, so the subject never
            // drifts out of focus while the camera eases in.
            volume.SetDepthOfField(true, depthOfFieldMode, FocusDistance, Mathf.Lerp(32, aperture, e), focalLength);
        }

        Vector3 HeadPosition() => head ? head.position : subject ? subject.transform.position + Vector3.up * npcHeadFallback : smoothedHead;

        static Transform FindHead(NpcAgent npc)
        {
            if (!npc) return null;
            var look = npc.GetComponentInChildren<ActorLookAt>();
            if (look && look.head) return look.head;
            foreach (var t in npc.GetComponentsInChildren<Transform>()) if (t.name == "Head" || t.name == "head") return t;
            return null;
        }

        void OnDisable() { Suspend(); }
    }
}
