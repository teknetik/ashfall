using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
namespace AthenHill
{
    /// The photo panel's rows, in screen order.
    public enum PhotoRow { FieldOfView, Roll, DepthOfField, FocusDistance, Aperture, Exposure, TimeOfDay, Player, Hud, Capture, Exit }

    /// Photo-mode settings and their keyboard steps (19 Nov 2026). Pure data, so the panel and the tests share it.
    public sealed class PhotoControls
    {
        public const float MinFieldOfView = 15, MaxFieldOfView = 90, MaxRoll = 45, MinFocus = .3f, MaxFocus = 80, MinAperture = 1.4f, MaxAperture = 22, MaxExposure = 3;
        public static readonly PhotoRow[] Rows = (PhotoRow[])Enum.GetValues(typeof(PhotoRow));

        public float FieldOfView = 50, Roll, FocusDistance = 5, Aperture = 4, Exposure, Hour = 12;
        public bool DepthOfField, PlayerVisible = true, HudVisible;
        public int Selected;
        public PhotoRow SelectedRow => Rows[Mathf.Clamp(Selected, 0, Rows.Length - 1)];

        public void MoveSelection(int direction) { Selected = ((Selected + Math.Sign(direction)) % Rows.Length + Rows.Length) % Rows.Length; }

        /// One arrow step (coarse with Shift). Returns true when a value changed. Toggles flip either way.
        public bool Adjust(PhotoRow row, int direction, bool coarse)
        {
            int d = Math.Sign(direction);
            if (d == 0) return false;
            switch (row)
            {
                case PhotoRow.FieldOfView: return Set(ref FieldOfView, Mathf.Clamp(FieldOfView + d * (coarse ? 5 : 1), MinFieldOfView, MaxFieldOfView));
                case PhotoRow.Roll: return Set(ref Roll, Mathf.Clamp(Roll + d * (coarse ? 5 : 1), -MaxRoll, MaxRoll));
                // Focus and aperture step multiplicatively: the same press means as much at 1 m as at 40 m.
                case PhotoRow.FocusDistance: return Set(ref FocusDistance, Mathf.Clamp(FocusDistance * Mathf.Pow(coarse ? 1.25f : 1.05f, d), MinFocus, MaxFocus));
                case PhotoRow.Aperture: return Set(ref Aperture, Mathf.Clamp(Aperture * Mathf.Pow(2, d * (coarse ? .5f : 1f / 6)), MinAperture, MaxAperture));
                case PhotoRow.Exposure: return Set(ref Exposure, Mathf.Clamp(Mathf.Round((Exposure + d * (coarse ? .5f : .1f)) * 10) / 10, -MaxExposure, MaxExposure));
                case PhotoRow.TimeOfDay: return Set(ref Hour, Mathf.Repeat(Hour + d * (coarse ? 1 : .25f), 24));
                case PhotoRow.DepthOfField: DepthOfField = !DepthOfField; return true;
                case PhotoRow.Player: PlayerVisible = !PlayerVisible; return true;
                case PhotoRow.Hud: HudVisible = !HudVisible; return true;
                default: return false;
            }
        }
        static bool Set(ref float field, float value) { if (Mathf.Approximately(field, value)) return false; field = value; return true; }

        public static bool IsToggle(PhotoRow row) => row == PhotoRow.DepthOfField || row == PhotoRow.Player || row == PhotoRow.Hud;
        public static bool IsAction(PhotoRow row) => row == PhotoRow.Capture || row == PhotoRow.Exit;
        public static bool IsSlider(PhotoRow row) => !IsToggle(row) && !IsAction(row);

        public static string Label(PhotoRow row) => row switch
        {
            PhotoRow.FieldOfView => "Field of view",
            PhotoRow.Roll => "Roll",
            PhotoRow.DepthOfField => "Depth of field",
            PhotoRow.FocusDistance => "Focus distance",
            PhotoRow.Aperture => "Aperture",
            PhotoRow.Exposure => "Exposure",
            PhotoRow.TimeOfDay => "Time of day",
            PhotoRow.Player => "Colonist",
            PhotoRow.Hud => "Interface",
            PhotoRow.Capture => "Capture · F12 / click",
            _ => "Exit · P / Esc",
        };

        public string Value(PhotoRow row) => row switch
        {
            PhotoRow.FieldOfView => $"{FieldOfView:0}°",
            PhotoRow.Roll => $"{Roll:+0;-0;0}°",
            PhotoRow.DepthOfField => DepthOfField ? "On" : "Off",
            PhotoRow.FocusDistance => FocusDistance < 10 ? $"{FocusDistance:0.0} m" : $"{FocusDistance:0} m",
            PhotoRow.Aperture => $"f/{Aperture:0.0}",
            PhotoRow.Exposure => $"{Exposure:+0.0;-0.0;0.0} EV",
            PhotoRow.TimeOfDay => $"{Mathf.FloorToInt(Hour):00}:{Mathf.FloorToInt(Mathf.Repeat(Hour, 1) * 60 + .001f):00}",
            PhotoRow.Player => PlayerVisible ? "Shown" : "Hidden",
            PhotoRow.Hud => HudVisible ? "Shown" : "Hidden",
            _ => "",
        };

        /// Slider positions. Focus and aperture use a log scale so the slider moves evenly in stops and doublings.
        public static void SliderRange(PhotoRow row, out float min, out float max)
        {
            switch (row)
            {
                case PhotoRow.FieldOfView: min = MinFieldOfView; max = MaxFieldOfView; return;
                case PhotoRow.Roll: min = -MaxRoll; max = MaxRoll; return;
                case PhotoRow.FocusDistance: min = Mathf.Log(MinFocus); max = Mathf.Log(MaxFocus); return;
                case PhotoRow.Aperture: min = Mathf.Log(MinAperture); max = Mathf.Log(MaxAperture); return;
                case PhotoRow.Exposure: min = -MaxExposure; max = MaxExposure; return;
                case PhotoRow.TimeOfDay: min = 0; max = 24; return;
                default: min = 0; max = 1; return;
            }
        }
        public float SliderValue(PhotoRow row) => row switch
        {
            PhotoRow.FieldOfView => FieldOfView,
            PhotoRow.Roll => Roll,
            PhotoRow.FocusDistance => Mathf.Log(FocusDistance),
            PhotoRow.Aperture => Mathf.Log(Aperture),
            PhotoRow.Exposure => Exposure,
            PhotoRow.TimeOfDay => Hour,
            _ => 0,
        };
        public void SetFromSlider(PhotoRow row, float v)
        {
            switch (row)
            {
                case PhotoRow.FieldOfView: FieldOfView = Mathf.Clamp(v, MinFieldOfView, MaxFieldOfView); break;
                case PhotoRow.Roll: Roll = Mathf.Clamp(v, -MaxRoll, MaxRoll); break;
                case PhotoRow.FocusDistance: FocusDistance = Mathf.Clamp(Mathf.Exp(v), MinFocus, MaxFocus); break;
                case PhotoRow.Aperture: Aperture = Mathf.Clamp(Mathf.Exp(v), MinAperture, MaxAperture); break;
                case PhotoRow.Exposure: Exposure = Mathf.Clamp(Mathf.Round(v * 10) / 10, -MaxExposure, MaxExposure); break;
                case PhotoRow.TimeOfDay: Hour = Mathf.Repeat(Mathf.Clamp(v, 0, 24), 24); break;
            }
        }
    }

    /// Free-camera movement maths (unscaled time; the game is frozen).
    public static class PhotoFlight
    {
        public static float Speed(float baseSpeed, bool fast, bool slow, float fastMultiplier = 4, float slowMultiplier = .25f)
            => Mathf.Max(0, baseSpeed) * (fast ? fastMultiplier : 1) * (slow ? slowMultiplier : 1);

        /// Planar input moves along the view (forward follows the pitch, like a drone); rise and fall are world vertical.
        public static Vector3 Displacement(Quaternion view, Vector2 move, float vertical, float speed, float deltaTime)
        {
            var d = view * new Vector3(move.x, 0, move.y) + Vector3.up * vertical;
            return Vector3.ClampMagnitude(d, 1) * speed * Mathf.Max(0, deltaTime);
        }

        /// Keeps the camera within maxDistance of the anchor (the player's head).
        public static Vector3 ClampToAnchor(Vector3 anchor, Vector3 desired, float maxDistance)
        {
            var offset = desired - anchor;
            return offset.magnitude <= maxDistance ? desired : anchor + offset.normalized * Mathf.Max(0, maxDistance);
        }

        public static float WrapPitch(float eulerX) { eulerX = Mathf.Repeat(eulerX + 180, 360) - 180; return eulerX; }
    }

    /// Photo file names: ~/Pictures/Ashfall/Ashfall_yyyyMMdd_HHmmss.png and the supersampled _2x.png beside it.
    public static class PhotoFiles
    {
        public static string DefaultFolder(string folderName = "Ashfall")
        {
            string home = Environment.GetEnvironmentVariable("HOME");
            if (string.IsNullOrEmpty(home)) home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return Path.Combine(home, "Pictures", folderName);
        }

        /// A stem that collides with neither the 1x nor the supersampled file of an earlier shot in the same second.
        public static string Stem(string folder, DateTime when, int supersample, Func<string, bool> exists)
        {
            string baseName = "Ashfall_" + when.ToString("yyyyMMdd_HHmmss", System.Globalization.CultureInfo.InvariantCulture);
            for (int n = 1; n < 1000; n++)
            {
                string stem = Path.Combine(folder, n == 1 ? baseName : baseName + "-" + n);
                if (!exists(stem + ".png") && (supersample <= 1 || !exists(SupersampledPath(stem, supersample)))) return stem;
            }
            return Path.Combine(folder, baseName + "-" + Guid.NewGuid().ToString("N").Substring(0, 8));
        }
        public static string SupersampledPath(string stem, int supersample) => stem + "_" + supersample + "x.png";

        /// 8-bit four-channel data from a screen grab can carry a meaningless alpha; a photo must be opaque.
        /// alphaOffset is the alpha byte within each pixel (3 for RGBA/BGRA, 0 for ARGB).
        public static void ForceOpaque(byte[] pixels, int alphaOffset = 3)
        {
            for (int i = Mathf.Clamp(alphaOffset, 0, 3); i < pixels.Length; i += 4) pixels[i] = 255;
        }
    }

    /// The parts of a camera photo mode changes, captured on entry and put back on exit.
    public struct CameraState
    {
        public Vector3 position;
        public Quaternion rotation;
        public float fieldOfView;
        public static CameraState Capture(Camera camera) => new CameraState { position = camera.transform.position, rotation = camera.transform.rotation, fieldOfView = camera.fieldOfView };
        public void Apply(Camera camera) { if (!camera) return; camera.transform.SetPositionAndRotation(position, rotation); camera.fieldOfView = fieldOfView; }
    }

    /// Undo steps recorded while entering photo mode and replayed in reverse on exit, exactly once each.
    public sealed class RestoreLedger
    {
        readonly List<(string name, Action undo)> steps = new List<(string, Action)>();
        public int Count => steps.Count;
        public void Add(string name, Action undo) { if (undo != null) steps.Add((name, undo)); }
        /// Runs every step in reverse order; one failing step is logged and does not stop the rest.
        public int RestoreAll(Action<string, Exception> onError = null)
        {
            int ran = 0;
            for (int i = steps.Count - 1; i >= 0; i--)
            {
                var (name, undo) = steps[i];
                try { undo(); ran++; }
                catch (Exception e) { if (onError != null) onError(name, e); else Debug.LogException(e); }
            }
            steps.Clear();
            return ran;
        }
    }
}
