using UnityEngine;
namespace AthenHill
{
    /// Every number that decides how the bench feels, in one asset (Data/Assembly/AssemblySettings.asset) so it can be
    /// tuned from play without code. The table in art/steady_hands_bench_20261120/bench/README.md says what each does.
    public class AssemblySettings : ScriptableObject
    {
        [Header("Carry: the object follows the hand on a critically damped spring")]
        [Tooltip("Spring frequency (rad/s) by mass class. Higher follows the hand more tightly; heavy things lag.")]
        public float springTiny = 34, springLight = 26, springMedium = 17, springHeavy = 10;
        [Tooltip("Height above the work surface a carried object rides at, metres.")] public float carryLift = .085f;
        [Tooltip("Degrees of lean per m/s of hand speed, and the most it leans.")] public float tiltPerSpeed = 10, tiltMax = 14;
        [Tooltip("Degrees a held part turns per wheel notch, and per second with Q / E.")] public float yawPerNotch = 15, yawPerSecond = 150;
        [Tooltip("How fast the part settles onto its new angle (1/s).")] public float yawFollow = 16;
        [Tooltip("A press shorter than this and nearly still is a tap: the object stays in the hand. Longer is a drag.")] public float tapSeconds = .22f;
        public float tapPixels = 9;
        [Tooltip("Speed of the keyboard focus carry, m/s.")] public float keyboardCarrySpeed = .45f;

        [Header("Seat: the pull-in")]
        [Tooltip("Seconds from clear to seated once the part is close and aligned (DESIGN: 60 to 90 ms).")] public float pullInSeconds = .075f;
        [Tooltip("Seconds to reach the clear pose before the pull-in.")] public float approachSeconds = .09f;
        [Tooltip("Camera nudge along the insertion axis on a seat, millimetres (none under Reduced Motion).")] public float cameraNudgeMm = 2.5f;
        [Tooltip("Seconds of rim flash on the seam.")] public float rimFlashSeconds = .22f;
        [Tooltip("Hand speed (m/s) above which a seat counts as fumbled, where the action has such a fault.")] public float fumbleSpeed = .9f;
        [Tooltip("Tolerance multiplier for the keyboard form (the focus ring brings the part to the place).")] public float keyboardTolerance = 1;
        [Tooltip("Shudder of a blocked part: millimetres and seconds.")] public float shudderMm = 1.6f, shudderSeconds = .28f;

        [Header("Turn")]
        [Tooltip("Turns per wheel notch, and per second held on the keyboard (before the action's gain).")] public float turnsPerNotch = .125f, keyTurnsPerSecond = 1.15f;
        [Tooltip("The mouse circle only counts beyond this distance from the pivot, millimetres.")] public float circleMinRadiusMm = 7;
        [Tooltip("Stop turns: seconds the part must rest inside the band to count as snug.")] public float stopSettleSeconds = .3f;
        [Tooltip("Loop pitch at no resistance and at full resistance.")] public float pitchLoose = .86f, pitchTight = 1.28f;
        [Tooltip("Turns per second that cam the bit out of a stiff screw (gain under 0.6).")] public float camOutSpeed = 4.5f;
        [Tooltip("Tool vibration at full resistance, millimetres.")] public float buzzMm = .5f;

        [Header("Window")]
        [Tooltip("Strike: seconds for the tool to rise fully while held.")] public float strikeRaiseSeconds = .85f;
        [Tooltip("Strike: how far the tool lifts at full height, metres.")] public float strikeLift = .11f;
        [Tooltip("Hold: how far past the window counts as over, as a fraction of the 0-1 value.")] public float overMargin = .06f;

        [Header("Point")]
        [Tooltip("Tolerance when the mark gives none, millimetres; beyond three times this a click is ignored.")] public float pointTolMm = 6;
        [Tooltip("Aim: degrees of wander become this many times the handling numbers.")] public float aimSwayScale = 1;
        [Tooltip("Aim: seconds per figure of eight.")] public float aimSwayPeriod = 2.6f;
        [Tooltip("Aim: how far in front of the eye the pistol is held at the card, metres.")] public float aimReach = .42f;
        [Tooltip("Aim: how far right of the middle the grip sits, as a share of the half width of the picture at that distance.")] public float aimSide = .32f;
        [Tooltip("Aim: how low in the picture the grip sits, as a share of the half height (0.64 puts the pistol in the lower third).")] public float aimLow = .42f;
        [Tooltip("Aim: seconds for the pistol to come up to the card and to go back to the hand.")] public float aimRaiseSeconds = .25f;

        [Header("Flick")]
        [Tooltip("Hand speed (m/s) a reversal must reach, reversals needed, and the seconds they must fall within.")] public float flickSpeed = .45f;
        public int flickReversals = 4; public float flickWindow = 1.5f;
        [Tooltip("Keyboard form: seconds to hold.")] public float flickHoldSeconds = .7f;

        [Header("Path and Wipe")]
        [Tooltip("Distance from the line that still counts, millimetres.")] public float pathTolMm = 9;
        [Tooltip("Keyboard pace along a line, m/s.")] public float pathKeyPace = .05f;
        [Tooltip("Brush radius, millimetres, and the share of the zone that counts as clean.")] public float wipeRadiusMm = 14, wipeDone = .9f;
        [Tooltip("Share of a zone at which a wipe finishes by itself; below it the wipe ends when the player lets go, and what was missed shows later.")] public float wipeFull = .97f;
        [Tooltip("A step done below this mean precision counts as done badly where a later step checks it (the spin test, the tester, the damper).")] public float poorPrecision = .8f;
        [Tooltip("Sustain (the press): how fast the value falls when the lever is let go, as a share of the pump rate, and seconds out of the band that leave a void.")] public float sustainDrift = .55f, sustainVoidSeconds = 2;

        [Header("Hints (DESIGN section 8): seconds with no progress")]
        public float hintGlint = 10; public float hintVoice = 25, hintGhost = 45, ghostSeconds = 2;

        [Header("Camera")]
        [Tooltip("Blend from the player's view on entering, and between stage shots, seconds.")] public float enterSeconds = .8f, shotSeconds = .6f;
        [Tooltip("Orbit limits with the right button, degrees, and degrees per pixel / per second on the keyboard.")] public float orbitYaw = 25, orbitPitch = 12, orbitPerPixel = .14f, orbitPerSecond = 45;
        [Tooltip("Zoom per wheel notch (0 whole bench, 1 close on the work), per second on Z / C, and how fast it settles.")] public float zoomPerNotch = .14f, zoomPerSecond = .9f, zoomFollow = 9;
        [Tooltip("Distance from the active part at full zoom, metres.")] public float closeDistance = .34f;
        [Tooltip("Depth of field aperture (off under Reduced Motion).")] public float aperture = 4.5f;
        public bool depthOfField = true;

        [Header("Leaving")]
        [Tooltip("Seconds Backspace (or the on-screen control) must be held to abandon the job.")] public float abandonHoldSeconds = 2;

        [Header("Sound")]
        [Tooltip("One-shots playing at once, and seconds within which the same event is not started twice.")] public int maxVoices = 8; public float sameEventWindow = .04f;
        [Tooltip("Seconds of quiet between two strokes of a one-shot sound that is held (a file stroke, a bite of the shears).")] public float strokeGap = .1f;
        [Tooltip("Bus gain of every bench sound. 0.74 keeps the audio package's worst pile-up under full scale.")] [Range(0, 1)] public float volume = .74f;

        public float Spring(string mass) => mass == "tiny" ? springTiny : mass == "medium" ? springMedium : mass == "heavy" ? springHeavy : springLight;
    }
}
