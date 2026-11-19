using UnityEngine;
namespace AthenHill
{
    /// Who owns the main camera's pose right now (19 Nov 2026, showcase camera).
    /// Additive camera effects (combat shake, recoil sway, head bob) read <see cref="UnderControl"/> and stay off while it
    /// is true, so a conversation framing or a photo-mode shot is never shaken.
    public static class CinematicCamera
    {
        /// True while photo mode is open or a conversation camera is engaged (blending in, holding or blending out,
        /// including the depth-of-field-only first-person case).
        public static bool UnderControl => PhotoActive || ConversationEngaged;
        public static bool PhotoActive { get; internal set; }
        public static bool ConversationEngaged { get; internal set; }

        // Statics survive play-mode entry when domain reload is disabled.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { PhotoActive = false; ConversationEngaged = false; }
    }
}
