using UnityEngine;

namespace AthenHill
{
    /// Two looping 2D wind layers driven by WeatherDirector: a wind bed that follows wind strength (gusts included) and
    /// a heavier sand-laden layer during a dust front. The sources are routed to the city's ambience mixer group by
    /// the installer and scaled by the Ambience volume setting; master volume, mute and pause act through the
    /// AudioListener as for every other source.
    public sealed class WeatherAudio : MonoBehaviour
    {
        public GameSession session;
        public AudioSource windBed, frontLayer;
        [Tooltip("Wind bed volume at full wind (before the Ambience setting).")]
        [Range(0, 1)] public float windBedVolume = .3f;
        [Tooltip("Dust-front layer volume at a front's peak (before the Ambience setting).")]
        [Range(0, 1)] public float frontVolume = .4f;
        [Tooltip("Wind strength (× authored) at which the bed is silent, and at which it is at full volume.")]
        public float silentStrength = .5f, fullStrength = 2.4f;
        [Tooltip("Pitch of the bed at silent and at full wind.")]
        public Vector2 bedPitch = new Vector2(.94f, 1.06f);
        [Tooltip("Seconds to follow a volume change (smooths gust swells and avoids zipper noise).")]
        [Min(.05f)] public float smoothing = .6f;
        float bed, front;

        public void Drive(float windStrength, float frontLevel, bool playing)
        {
            float ambience = session && session.Settings != null ? session.Settings.Sound.ambience : 1;
            float level = Mathf.Clamp01(Mathf.InverseLerp(silentStrength, fullStrength, windStrength));
            float bedTarget = playing ? windBedVolume * level * ambience : 0;
            float frontTarget = playing ? frontVolume * Mathf.Clamp01(frontLevel) * ambience : 0;
            // Unscaled: a fade to silence must still finish while the game is frozen (menus run at timeScale 0).
            float k = WeatherMix.EaseFactor(Time.unscaledDeltaTime, smoothing);
            bed = Mathf.Lerp(bed, bedTarget, k); front = Mathf.Lerp(front, frontTarget, k);
            Set(windBed, bed, Mathf.Lerp(bedPitch.x, bedPitch.y, level));
            Set(frontLayer, front, 1);
        }

        public void Silence() { bed = front = 0; Set(windBed, 0, 1); Set(frontLayer, 0, 1); }

        static void Set(AudioSource source, float volume, float pitch)
        {
            if (!source || !source.clip) return;
            source.volume = volume; source.pitch = pitch;
            if (volume > .0005f)
            {
                if (!source.isPlaying)
                {
                    source.loop = true;
                    // Different start points keep the two loops (and successive starts) from lining up.
                    source.time = Random.value * source.clip.length * .95f;
                    source.Play();
                }
            }
            else if (source.isPlaying) source.Stop();
        }

        public object State() => new
        {
            bedVolume = windBed ? windBed.volume : 0, bedPlaying = windBed && windBed.isPlaying, bedClip = windBed && windBed.clip ? windBed.clip.name : null,
            frontVolume = frontLayer ? frontLayer.volume : 0, frontPlaying = frontLayer && frontLayer.isPlaying, frontClip = frontLayer && frontLayer.clip ? frontLayer.clip.name : null,
            group = windBed && windBed.outputAudioMixerGroup ? windBed.outputAudioMixerGroup.name : null
        };
    }
}
