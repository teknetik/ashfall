using UnityEngine;

namespace AthenHill
{
    public enum CitySoundCue { Trade, Unavailable, LatticeOpen, LatticeLink }

    public class CityAudio : MonoBehaviour
    {
        public GameSession session;
        public AudioSource ambience, steps, confirmation, latticeHum, ringHum;
        public AudioSource music, market, travel;
        [Tooltip("Surface-aware foot-contact footsteps. When set and enabled it replaces the distance cadence below.")]
        public FootstepAudio footsteps;
        public AudioClip[] footstepClips;
        public AudioClip[] musicPlaylist;
        public string CurrentTrack => activeMusic && activeMusic.clip ? activeMusic.clip.name : "Music unavailable";
        public int MusicTransitions { get; private set; }
        public AudioClip tradeConfirm, unavailable, latticeOpen, latticeLink;
        [Min(.1f)] public float walkStepDistance = .95f, runStepDistance = 1.45f;
        [Min(.1f)] public float musicFadeSeconds = 3;
        [Min(.05f)] public float duckAttackSeconds = .45f, duckReleaseSeconds = 1.6f;
        [Range(0, 1)] public float dialogueMusicLevel = .65f, travelMusicLevel = .4f;
        public int StepCount => footsteps && footsteps.isActiveAndEnabled ? footsteps.StepCount : distanceSteps;
        int distanceSteps;
        public int ClickCount { get; private set; }
        public int TradeCount { get; private set; }
        public int UnavailableCount { get; private set; }
        public int TravelOpenCount { get; private set; }
        public int TravelLinkCount { get; private set; }
        float distance, musicVolume, duck = 1, fadeIn, crossfade;
        int trackIndex;
        bool transitioning;
        AudioSource activeMusic, incomingMusic;
        AudioSource[] levelSources;
        float[] baseLevels;
        GameSettings settings;
        CityState previous;

        void Start()
        {
            if (!session) { enabled = false; return; }
            previous = session.State;
            session.Changed += Changed;
            session.SoundRequested += PlayCue;
            settings = session.Settings;
            levelSources = new[] { ambience, market, latticeHum, ringHum, steps, confirmation, travel };
            baseLevels = new float[levelSources.Length];
            for (int i = 0; i < levelSources.Length; i++) if (levelSources[i]) baseLevels[i] = levelSources[i].volume;
            if (settings) settings.Changed += ApplyLevels;
            ApplyLevels();
            if (music)
            {
                musicVolume = music.volume; music.volume = 0; music.Stop(); music.loop = false;
                if (musicPlaylist != null && musicPlaylist.Length > 0)
                {
                    int first = CityAudioMix.NextPlayableTrack(musicPlaylist, -1);
                    if (first >= 0) { trackIndex = first; music.clip = musicPlaylist[first]; }
                }
                activeMusic = music;
                incomingMusic = new GameObject("City music crossfade").AddComponent<AudioSource>();
                incomingMusic.transform.SetParent(transform, false);
                incomingMusic.outputAudioMixerGroup = music.outputAudioMixerGroup;
                incomingMusic.playOnAwake = false; incomingMusic.loop = false;
                incomingMusic.spatialBlend = 0; incomingMusic.priority = music.priority;
                if (music.clip) music.Play();
            }
        }

        void OnDestroy()
        {
            if (!session) return;
            session.Changed -= Changed;
            session.SoundRequested -= PlayCue;
            if (settings) settings.Changed -= ApplyLevels;
        }

        void ApplyLevels()
        {
            float amb = settings ? settings.Sound.ambience : 1f;
            float sfx = settings ? settings.Sound.effects : 1f;
            for (int i = 0; i < levelSources.Length; i++)
                if (levelSources[i]) levelSources[i].volume = baseLevels[i] * (i < 4 ? amb : sfx);
            ApplyMusicLevels();
        }

        void ApplyMusicLevels()
        {
            if (!activeMusic) return;
            float musicSetting = settings ? settings.Sound.music : 1f;
            float level = musicVolume * musicSetting * duck * fadeIn;
            if (transitioning)
            {
                CityAudioMix.EqualPowerCrossfade(crossfade, out float outGain, out float inGain);
                activeMusic.volume = level * outGain;
                if (incomingMusic) incomingMusic.volume = level * inGain;
            }
            else
            {
                activeMusic.volume = level;
                if (incomingMusic) incomingMusic.volume = 0;
            }
        }

        public void NextMusic()
        {
            if (!activeMusic || !incomingMusic || transitioning || musicPlaylist == null || musicPlaylist.Length == 0) return;
            int next = CityAudioMix.NextPlayableTrack(musicPlaylist, trackIndex);
            if (next < 0) return;
            trackIndex = next; incomingMusic.clip = musicPlaylist[next]; incomingMusic.volume = 0;
            incomingMusic.Play(); crossfade = 0; transitioning = true; MusicTransitions++;
        }

        public void PreviewEffect() => OneShot(confirmation, confirmation ? confirmation.clip : null);

        void Update()
        {
            if (activeMusic && !AudioListener.pause)
            {
                float level = CityAudioMix.TargetMusicDuck(session.State, dialogueMusicLevel, travelMusicLevel);
                float dt = Time.unscaledDeltaTime;
                duck = CityAudioMix.StepDuck(duck, level, dt, duckAttackSeconds, duckReleaseSeconds);
                float delta = dt / Mathf.Max(.1f, musicFadeSeconds);
                fadeIn = Mathf.MoveTowards(fadeIn, 1, delta);
                if (!transitioning && activeMusic.clip)
                {
                    float fadeWindow = Mathf.Min(musicFadeSeconds, activeMusic.clip.length * .45f);
                    if (!activeMusic.isPlaying || (activeMusic.time > 0 && activeMusic.clip.length - activeMusic.time <= fadeWindow)) NextMusic();
                }
                if (transitioning)
                {
                    crossfade = Mathf.MoveTowards(crossfade, 1, delta);
                    if (crossfade >= 1)
                    {
                        activeMusic.Stop(); var old = activeMusic; activeMusic = incomingMusic; incomingMusic = old;
                        transitioning = false;
                    }
                }
                ApplyMusicLevels();
            }
            if (footsteps && footsteps.isActiveAndEnabled) return;
            if (session.State != CityState.Play || !session.player || !session.player.Grounded || session.player.Speed < .12f)
            { distance = 0; return; }
            distance += session.player.Speed * Mathf.Min(Time.deltaTime, .1f);
            float stride = session.player.Speed > 4.5f ? runStepDistance : walkStepDistance;
            if (distance < stride) return;
            distance %= stride;
            if (!steps) return;
            var clip = footstepClips != null && footstepClips.Length > 0 ? footstepClips[distanceSteps % footstepClips.Length] : steps.clip;
            if (!clip) return;
            steps.pitch = ++distanceSteps % 2 == 0 ? 1.03f : .97f;
            steps.PlayOneShot(clip);
        }

        void Changed()
        {
            if (previous == session.State) return;
            // Travel activation has its own cue. Log/progress refreshes make no sound.
            if (previous != CityState.Boot && session.State != CityState.Grid)
                OneShot(confirmation, confirmation ? confirmation.clip : null);
            if (previous == CityState.Grid && travel) travel.Stop();
            previous = session.State;
        }

        void OneShot(AudioSource source, AudioClip clip)
        {
            if (!source || !clip) return;
            source.PlayOneShot(clip);
            ClickCount++;
        }

        void PlayCue(CitySoundCue cue)
        {
            switch (cue)
            {
                case CitySoundCue.Trade: OneShot(confirmation, tradeConfirm); TradeCount++; break;
                case CitySoundCue.Unavailable: OneShot(confirmation, unavailable); UnavailableCount++; break;
                case CitySoundCue.LatticeOpen: OneShot(travel, latticeOpen); TravelOpenCount++; break;
                case CitySoundCue.LatticeLink: OneShot(travel, latticeLink); TravelLinkCount++; break;
            }
        }
    }

    /// Pure music ducking and equal-power crossfade math for CityAudio (tested in WorldAtmospherePolishTests).
    public static class CityAudioMix
    {
        public static float TargetMusicDuck(CityState state, float dialogueLevel, float travelLevel)
        {
            switch (state)
            {
                case CityState.Grid:
                    return Mathf.Clamp01(travelLevel);
                case CityState.Dialogue:
                case CityState.Shop:
                case CityState.Stash:
                case CityState.Rest:
                case CityState.Fabricator:
                case CityState.Map:
                case CityState.Journal:
                case CityState.Inventory:
                case CityState.Paused:
                case CityState.Settings:
                    return Mathf.Clamp01(dialogueLevel);
                default:
                    return 1f;
            }
        }

        public static float StepDuck(float current, float target, float deltaTime, float attackSeconds, float releaseSeconds)
        {
            target = Mathf.Clamp01(target);
            if (!ClockMath.Finite(current)) current = target;
            if (!ClockMath.Finite(deltaTime) || deltaTime <= 0) return current;
            float duration = target < current ? Mathf.Max(.05f, attackSeconds) : Mathf.Max(.05f, releaseSeconds);
            float k = 1f - Mathf.Exp(-3f * deltaTime / duration);
            float next = Mathf.Lerp(current, target, k);
            return Mathf.Abs(next - target) < .001f ? target : next;
        }

        public static void EqualPowerCrossfade(float t, out float outGain, out float inGain)
        {
            t = Mathf.Clamp01(t);
            float angle = t * Mathf.PI * .5f;
            outGain = Mathf.Cos(angle);
            inGain = Mathf.Sin(angle);
        }

        public static int NextPlayableTrack(AudioClip[] playlist, int currentIndex)
        {
            if (playlist == null || playlist.Length == 0) return -1;
            int n = playlist.Length;
            int start = ((currentIndex + 1) % n + n) % n;
            for (int i = 0; i < n; i++)
            {
                int idx = (start + i) % n;
                if (playlist[idx]) return idx;
            }
            return -1;
        }
    }
}
