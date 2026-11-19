# Combat audio, 19 November 2026

The field rifle gets its own layered shot, and the five newer droids (Scrap Reaper, Post Sentinel, Feral Gunner,
Feral Lancer, Depot Foreman) get their own alert, attack tell, attack and death sounds, plus new bolt fly-bys and
impacts. Clips, generator, code and installer are done; **nothing has been installed in Unity or heard yet** (Unity
was busy with a reimport and nobody could listen). Status: not yet accepted by Carl.

Builds on the combat feel pass (`../combat_feel/README.md`): its hit, critical and kill ticks (`Audio/UI/hit-*.wav`)
are untouched and still play on top of everything here.

## What changed

1. **Field rifle set.** Same three layers as the pistol, with their own character, cut for the rifle's fire interval
   of **0.18 s (333 rounds/min, `weapon_field_rifle` in `WardCrafting.asset`; the stat floor is 0.08 s)**:
   - mech, 6 variants: a harder steel bolt clack, high-passed at 400 Hz and cut at 0.15 s (the pistol's run to 0.48 s);
   - body, 8 variants: crack plus a heavier low end (+4 dB low shelf at 140 Hz), cut at 0.30 s;
   - tail, 6 variants: short desert slapback, high-passed at 180 Hz and forced to decay by 0.75 s (the pistol's ring
     to 1.6 s), so 5 overlapping tails at full rate stay clear instead of building into low-mid mud. While a burst
     is held, each tail plays at ×0.75 (`burstTailScale`);
   - empty ×2, draw ×2, holster ×2.
   Each layer's variants are fitted to within 0.6 dB of each other in loudness (they came back 5 dB apart).
2. **Per-weapon selection** (`PlayerCombat.weaponSounds`, `WeaponSoundSet` in `Scripts/Combat/CombatAudio.cs`). The
   set whose weapon id matches the bound loadout plays its layers, empty click and draw/holster foley. A weapon
   without a set (the scrap pistol) plays PlayerCombat's existing arrays exactly as before. `LastShotSoundSet` shows
   which set the last shot used (null = the pistol arrays).
3. **Droid identity** (`FeralDroid`, header "Sound identity"). New optional arrays `alertVariants`,
   `windupVariants`, `strikeVariants`, `slamVariants`, `fireVariants`, `hitVariants`, `deathVariants`,
   `stepVariants`. When an array is empty the droid plays its existing single clip, so the worker droid and the
   scrap drone are unchanged. Variants never repeat back to back.

   | Droid | Alert | Attack tell | Attack | Death | Other |
   | --- | --- | --- | --- | --- | --- |
   | Scrap Reaper | growl through a broken speaker, servos | blade arm raised, scrape and ring | blade chop ×2 | hydraulic groan, plate crash | heavy steps ×2 |
   | Post Sentinel | two-tone warble alarm, turret whirr | accelerating targeting beeps, lock click | sentry bolt cannon ×2 | motor whine-down, wheel grind, topple | rolling loop (below) |
   | Feral Gunner | radio static burst, gun-arm rack | stuttering capacitor whine, lock click | rivet cannon thunk ×2 | short pop, stutter, clatter | |
   | Feral Lancer | rotor rise, double chirp, arcing | deep hum rising steeply, fizzing arcs | arc cannon launch ×2 | rotors sputter, falling whine, crash | |
   | Depot Foreman | factory klaxon, hydraulic hiss | pneumatic pressure build | hydraulic fist slam | klaxon dying, venting, huge crash | ground slam (layered), Reaper steps |
   | Bolts (all three) | | | | | fly-by ×3; impact ×2 (gunner, sentinel) or heavy arc impact (lancer) |

4. **Sentinel rolling loop.** A procedural 4 s seamless loop (wheel rumble with a rotation bump, gravel grit, a faint
   drive-motor whine) on a new `Roll loop audio` child. `FeralDroid.RollAudio` sets volume and pitch from ground
   speed (`CombatAudio.RollMix`: 0.4 idle → 1 at the chase speed, pitch 0.75 → 1.2, × `rollVolume` 0.85), runs
   before the far-idle exit so an idle Sentinel still hums, stops the source beyond its Max Distance and fades it
   over about a second on death.
5. **Mix.**
   - **Mixer group: every source this pass touches goes to SFX.** Finding: the droid voices and bolt sources were
     on the **UI** group in the prefabs (Effects volume covers both, so nobody noticed). The worker and scrap drone
     stay on UI unless the optional `sfxall` step is run (Carl's call, below).
   - **Distance:** a custom rolloff (`CombatAudio.DesertRolloff`): inverse distance from Min Distance, faded to
     exactly silent at Max Distance (Unity's logarithmic mode holds its last level forever beyond Max). Doppler off
     (the fly-bys carry their own sweep).

     | Source | Min | Max | Level at 30 m | Level at 60 m |
     | --- | --- | --- | --- | --- |
     | Reaper voice | 3 m | 70 m | -21 dB | -35 dB |
     | Sentinel voice | 3 m | 90 m | -20 dB | -29 dB |
     | Sentinel roll loop | 12 m | 120 m | -8 dB | -15 dB |
     | Gunner voice | 2.5 m | 75 m | -22 dB | -34 dB |
     | Lancer voice | 2.5 m | 80 m | -22 dB | -32 dB |
     | Foreman voice | 4 m | 90 m | -18 dB | -27 dB |
     | Bolt fly-by / impact | 1.5 m | 50 m | -28 dB | silent |

     So a moving Sentinel carries about 60 m (its aggro radius is 36 m, and nothing reaches across the 500 m bowl).
   - **Voice limiting:** `VoiceLimiter.Droids` (static, shared by all droids and bolts). Alerts, attack tells,
     attacks, slams, bolt shots, deaths and fly-bys always play (the cues the player reacts to); footsteps, hit
     clangs and bolt impacts need a free slot under 10 droid one-shots at once. The same clip never restarts
     within 70 ms (two droids alerting on one frame only phase and double the level). The touched droids' voice
     priority is 96 and the roll loop 140, so tells outrank loops when the 32 real voices run out. `limitVoices`
     (default on) is per droid.
   - **Levels** (measured, nobody listened): see "Loudness" below.

## Loudness (EBU R128 through ffmpeg ebur128)

Short one-shots are below R128's 400 ms gate, so each file is measured as an "event": four repeats with 0.5 s gaps
(`event_lufs` in the manifest). Shots are measured as the game mixes them, with the runtime layer gains.

| Measure | Pistol (existing) | Field rifle (new) |
| --- | --- | --- |
| Runtime layer gains mech / body / tail | 0.548 / 0.694 / 0.365 | 0.512 / 0.699 / 0.354 |
| One shot, all three layers (mean of 6 random) | -19.9 LUFS | -18.4 LUFS (+1.5 dB) |
| Volley as fired (pistol 8 at 0.28 s, rifle 12 at 0.18 s) | -15.3 LUFS, TP -0.5 dBFS | -14.8 LUFS, TP -1.1 dBFS |
| Worst-case aligned peak of the loudest variants | -1.5 dBFS (generator rule) | -2.8 dBFS |

Droid sounds sit on the shared clip of the same role (event LUFS): alerts -15 to -16 (shared -15.7), tells -15.5 to
-16.5 (droid-windup -15.6, gunner-aim -16.1, lancer-charge -17.6), melee attacks -16.5 to -17 (shared strike -19.8:
the heavies hit harder), Foreman slam -16.9, bolt shots -17 to -18.5 (gunner-fire -18.6, lancer-fire -20.6), deaths
-14.5 to -15.5 (shared -15.2), Reaper steps -20 (shared -21.1), fly-bys -18.5 (shared -18.4), impacts -24 and
lancer -21 (**the shared impact is -30.7, so bolt impacts are 6-9 dB louder than before**: they now read as a hit
near you; turn `DroidBolt.impactVolume` down if they are too present). Roll loop -20 LUFS integrated before its
runtime volume (scrap drone rotor loop -22.4). Every file peaks at or under -3 dBFS. Per-file numbers:
`manifest.json` (here) and `unity/staging/elevenlabs-audio/combat-20261119/combat-20261119-manifest.json`.

## Files

New clips (44.1 kHz mono WAV): `Assets/AthenHill/Audio/ElevenLabs/Combat/Rifle/rifle-{mech,body,tail,empty,draw,holster}-NN.wav`
(26) and `Assets/AthenHill/Audio/ElevenLabs/Combat/Droids/*.wav` (35; `foreman-slam-b.wav` is the slam's boom
layer, not assigned). No existing clip was overwritten. Sources, exact requests and response ids:
`unity/staging/elevenlabs-audio/combat-20261119/` (including the two rejected takes, below).

Code: `Scripts/Combat/CombatAudio.cs` (new: `WeaponSoundSet`, `CombatAudio` selection/picking/rolloff/roll mix,
`VoiceLimiter`), `Scripts/Combat/PlayerCombat.cs` (`weaponSounds`, `ActiveSoundSet`, `LastShotSoundSet`, set playback;
`Pick` now delegates to `CombatAudio.Pick`, same behaviour), `Scripts/Combat/FeralDroid.cs` (variant arrays, `Say`
through the voice budget, roll loop), `Scripts/Combat/DroidBolt.cs` (no-repeat picks, `flybyVolume` 0.7 and
`impactVolume` 1 as before, budget). Installer `Editor/CombatAudioPass20261119.cs`, tests
`Tests/Editor/CombatAudioTests.cs`, generator `unity/tools/generate_combat_audio_20261119.py`.

## Install

Clips are already on disk. To regenerate without paying: `python3 unity/tools/generate_combat_audio_20261119.py`
(remasters cached takes; `--generate` only buys missing ones, with a 4,000-credit ledger guard). Then, with the
Editor closed, one Unity job, `-nographics`, in its memory-capped scope:

    Unity -batchmode -nographics -projectPath unity/AthenHill \
      -executeMethod AthenHill.Editor.CombatAudioPass20261119.RunBatch \
      --steps audio,weapon,droids,bolts,verify -logFile -

`verify` prints PASS/FAIL and exits 2 on FAIL. Every step is safe to re-run; original values are recorded once in
`record.json` here. It touches only: PlayerCombat.weaponSounds (scene), the five droid prefabs' new fields, their
voice source's group/distance/rolloff/priority, a `Roll loop audio` child on the Sentinel, and the three bolt prefabs'
clip arrays and source. It calls no other pass. Then run Edit Mode tests `CombatAudioTests` (plus `CharacterFeelTests`,
`CombatFeelTests`, `NextLevelEnemiesTests` for regressions).

## Listening test (native development build, real input, speakers or headphones at a fixed level)

1. **Pistol unchanged.** Draw the pistol (hotbar 2), fire single shots: same sound as the last build. QA:
   `LastShotSoundSet` null.
2. **Rifle single shots.** Hotbar 1, tap fire: a tighter, heavier shot than the pistol, slightly louder, a short dry
   slap after it; no click-only shots. `LastShotSoundSet` = `weapon_field_rifle`.
3. **Rifle burst.** Hold fire for a full charge (about 12 shots): no audible repeated sample, no "machine-gun"
   identical crack, the tail must not swell into a roar or a low rumble by the end of the burst; first person and
   aiming: mech closer, tail drier. Empty: a dull click and a dying whine, distinct from the pistol's.
4. **Draw / holster.** Rifle: sling and strap; pistol: leather holster as before.
5. **Sentinel.** Approach a Post Sentinel from 100 m: hear its motor/rolling before you can pick it out (from about
   60 m while it moves, 30-40 m standing); the roll rises with speed when it chases and drops when it stops; alarm
   warble on alert; accelerating beeps before each burst (time the dodge on them); death: wheel grind and topple,
   the roll fades in about a second. Walk away: silent beyond about 120 m.
6. **Reaper / Foreman.** Growl or klaxon on alert, the blade or fist tell clearly before each hit, a heavy chop or
   slam on the hit; the Foreman's ground slam has a clang and gravel on top of the boom (judge on laptop speakers too).
7. **Gunner / Lancer.** Static burst / chirp on alert; the charge must be audible over your own rifle fire (it is
   the dodge cue); launches sound different from the gunner's shots.
8. **Bolts.** Let bolts pass close: a bright zip, not a low whoosh; impacts on rock near you are clear but not
   louder than your own shot; lancer impacts heavier.
9. **Pack fight.** Pull the depot pack plus a gunner: nothing drops out that warns you (alerts, tells), steps and
   clangs thin out instead of piling up; no crackle or voice stealing of your own shots.
10. **Mixer.** Settings › Sound › Effects at 0 silences all of it; Master mute too.

## Rollback

    ... -executeMethod AthenHill.Editor.CombatAudioPass20261119.RunBatch --steps rollback

Removes the rifle set, empties (or, on the Foreman variant, reverts) the new droid fields, removes the roll loop child,
restores every voice and bolt source's group, distances, rolloff, doppler, priority and spatial blend and the bolt
clip arrays from `record.json`. The clips stay on disk, unused. Without the installer the code changes are inert:
empty arrays fall back to today's clips, no set means the pistol path. The voice budget is active either way (see
risks).

## ElevenLabs usage

Model `eleven_text_to_sound_v2`, explicit durations 0.5-2.5 s, 53 paid takes. Account character count before the
first request **34,791** (34,657 an hour earlier; another agent spends on the same account), after the last
**35,302**: **511 credits** for this pass, matching the sum of the response `character-cost` headers (budget
4,000). That includes two rejected takes (19 credits): `bolt-flyby-3` came back as a low whoosh (87 % of its energy
below 150 Hz) and was replaced by `bolt-flyby-4`; both Foreman slam takes were nearly pure sub (96-98 % below
150 Hz), so the slam is layered (second take's boom + the Foreman strike's clang above 300 Hz + procedural gravel).
The roll loop is fully procedural.

## Known risks and open questions

- **Not heard and not installed.** Prompts, levels and processing are judged by measurement only. The highest-risk
  calls: rifle body variants were levelled with up to 6 dB of soft limiting (some may sound squashed); the Reaper/
  Foreman alerts are growls/klaxons that could read as comic; the roll loop is synthetic.
- **The voice budget applies to every droid**, including the worker and scrap drone: in a pack fight their footsteps
  and hit clangs may now drop out, and two identical alerts on one frame play once. Set `limitVoices` off on a
  prefab to opt out.
- **Mixer group:** existing droid voices are on UI, not SFX. Running `--steps sfxall` moves the worker and scrap
  drone to SFX too (recorded, undone by rollback). Carl's call; not part of the default install.
- Bolt impacts are 6-9 dB louder than the old clip (above).
- At the 0.08 s stat floor (a fully modded fire rate) up to 10 tails overlap; the burst tail scale helps, but this was
  measured only at 0.18 s.
- `rollFullSpeed` is set from the Sentinel's chase speed (5 m/s); the roll loop pitch range (0.75-1.2) is a guess.

## Native QA fixes (19 Nov 2026)

- QA-only additions so a machine can tell which sounds played (nobody listened): `FeralDroid.VoicesPlayed`,
  `VoicesDropped`, `LastVoiceClip`, `RollPlaying`; static `DroidBolt.Flybys` / `Impacts`; reported in the snapshot under
  `combat.feel.droidAudio`, `boltFlybys`, `boltImpacts`. No change to what plays.
