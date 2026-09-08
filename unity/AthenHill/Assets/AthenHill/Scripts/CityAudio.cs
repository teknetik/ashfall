using UnityEngine;

namespace AthenHill
{
    public enum CitySoundCue { Trade, Unavailable, LatticeOpen, LatticeLink }

    public class CityAudio : MonoBehaviour
    {
        public GameSession session;
        public AudioSource ambience, steps, confirmation, latticeHum, ringHum;
        public AudioSource music, market, travel;
        public AudioClip[] footstepClips;
        public AudioClip[] musicPlaylist;
        public string CurrentTrack => activeMusic && activeMusic.clip ? activeMusic.clip.name : "Music unavailable";
        public int MusicTransitions { get; private set; }
        public AudioClip tradeConfirm, unavailable, latticeOpen, latticeLink;
        [Min(.1f)] public float walkStepDistance = .95f, runStepDistance = 1.45f;
        [Min(.1f)] public float musicFadeSeconds = 3;
        [Range(0, 1)] public float dialogueMusicLevel = .65f, travelMusicLevel = .4f;
        public int StepCount { get; private set; }
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
            settings.Changed += ApplyLevels;
            ApplyLevels();
            if (music)
            {
                musicVolume = music.volume; music.volume = 0; music.Stop(); music.loop = false;
                if (musicPlaylist != null && musicPlaylist.Length > 0) music.clip = musicPlaylist[0];
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
            for (int i = 0; i < levelSources.Length; i++)
                if (levelSources[i]) levelSources[i].volume = baseLevels[i] * (i < 4 ? settings.Sound.ambience : settings.Sound.effects);
            ApplyMusicLevels();
        }

        void ApplyMusicLevels()
        {
            if (!activeMusic) return;
            float level = musicVolume * settings.Sound.music * duck * fadeIn;
            activeMusic.volume = level * (transitioning ? 1 - crossfade : 1);
            incomingMusic.volume = level * (transitioning ? crossfade : 0);
        }

        public void NextMusic()
        {
            if (!activeMusic || transitioning || musicPlaylist == null || musicPlaylist.Length == 0) return;
            int next = (trackIndex + 1) % musicPlaylist.Length;
            if (!musicPlaylist[next]) return;
            trackIndex = next; incomingMusic.clip = musicPlaylist[next]; incomingMusic.volume = 0;
            incomingMusic.Play(); crossfade = 0; transitioning = true; MusicTransitions++;
        }

        public void PreviewEffect() => OneShot(confirmation, confirmation ? confirmation.clip : null);

        void Update()
        {
            if (activeMusic && !AudioListener.pause)
            {
                float level = session.State == CityState.Grid ? travelMusicLevel :
                    session.State == CityState.Dialogue || session.State == CityState.Shop ? dialogueMusicLevel : 1;
                float delta = Time.unscaledDeltaTime / Mathf.Max(.1f, musicFadeSeconds);
                duck = Mathf.MoveTowards(duck, level, delta); fadeIn = Mathf.MoveTowards(fadeIn, 1, delta);
                if (!transitioning && activeMusic.clip && (!activeMusic.isPlaying || activeMusic.clip.length - activeMusic.time <= musicFadeSeconds)) NextMusic();
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
            if (session.State != CityState.Play || !session.player.Grounded || session.player.Speed < .12f)
            { distance = 0; return; }
            distance += session.player.Speed * Mathf.Min(Time.deltaTime, .1f);
            float stride = session.player.Speed > 4.5f ? runStepDistance : walkStepDistance;
            if (distance < stride) return;
            distance %= stride;
            if (!steps) return;
            var clip = footstepClips != null && footstepClips.Length > 0 ? footstepClips[StepCount % footstepClips.Length] : steps.clip;
            if (!clip) return;
            steps.pitch = ++StepCount % 2 == 0 ? 1.03f : .97f;
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
}
