using UnityEngine;
namespace AthenHill
{
    /// Showcase-camera state and commands for the development QA bridge (NativeQa snapshot key "showcase").
    public static class ShowcaseQa
    {
        public static object State()
        {
            var conversation = Object.FindAnyObjectByType<ConversationCamera>();
            var photo = PhotoMode.Current ? PhotoMode.Current : Object.FindAnyObjectByType<PhotoMode>();
            var c = photo ? photo.Controls : null;
            return new
            {
                cinematic = CinematicCamera.UnderControl,
                timeScale = Time.timeScale,
                conversation = new
                {
                    installed = (bool)conversation,
                    enabled = ConversationCamera.Enabled && conversation && conversation.framingEnabled,
                    active = conversation && conversation.Engaged,
                    weight = conversation ? conversation.Weight : 0,
                    framing = conversation && conversation.Framing,
                    eyeLine = conversation && conversation.EyeLine,
                    side = conversation ? conversation.Side : 0,
                    subject = conversation && conversation.Subject && conversation.Subject.definition ? conversation.Subject.definition.displayName : null,
                    focusDistance = conversation ? conversation.FocusDistance : 0,
                    shotFraction = conversation ? conversation.ShotFraction : 1,
                },
                photo = new
                {
                    installed = (bool)photo,
                    active = PhotoMode.Active,
                    capturing = photo && photo.Capturing,
                    panelShown = photo && photo.PanelShown,
                    status = photo ? photo.Status : null,
                    selected = c != null ? c.SelectedRow.ToString() : null,
                    fieldOfView = c?.FieldOfView, roll = c?.Roll, depthOfField = c?.DepthOfField, focusDistance = c?.FocusDistance,
                    aperture = c?.Aperture, exposure = c?.Exposure, hour = c?.Hour, playerVisible = c?.PlayerVisible, hudVisible = c?.HudVisible,
                    lastCapture = PhotoMode.LastCapturePath,
                    lastSupersampled = PhotoMode.LastSupersampledPath,
                    lastError = PhotoMode.LastError,
                },
            };
        }

        /// photoMode {open}: opens or closes photo mode (opening fails outside plain play, like the key).
        public static void SetPhotoMode(bool open)
        {
            var photo = Object.FindAnyObjectByType<PhotoMode>();
            if (!photo) throw new System.InvalidOperationException("Photo mode is not installed in this scene.");
            if (open) { if (!photo.IsOpen && !photo.Open()) throw new System.InvalidOperationException("Photo mode is only available in plain play."); }
            else photo.Close();
        }

        public static void Capture()
        {
            var photo = PhotoMode.Current;
            if (!PhotoMode.Active || !photo) throw new System.InvalidOperationException("Photo mode is not open.");
            if (!photo.Capture()) throw new System.InvalidOperationException("A capture is already running.");
        }
    }
}
