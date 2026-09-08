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
        float distance, musicVolume;
        CityState previous;

        void Start()
        {
            if (!session) { enabled = false; return; }
            previous = session.State;
            session.Changed += Changed;
            session.SoundRequested += PlayCue;
            if (music) { musicVolume = music.volume; music.volume = 0; }
        }

        void OnDestroy()
        {
            if (!session) return;
            session.Changed -= Changed;
            session.SoundRequested -= PlayCue;
        }

        void Update()
        {
            if (music && !AudioListener.pause)
            {
                float level = session.State == CityState.Grid ? travelMusicLevel :
                    session.State == CityState.Dialogue || session.State == CityState.Shop ? dialogueMusicLevel : 1;
                music.volume = Mathf.MoveTowards(music.volume, musicVolume * level,
                    musicVolume * Time.unscaledDeltaTime / Mathf.Max(.1f, musicFadeSeconds));
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
