using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Audio;

namespace AthenHill.Editor
{
    /// <summary>Update only saved audio components in the existing city scene.</summary>
    public static class ElevenLabsAudioPass
    {
        const string Folder = "Assets/AthenHill/Audio/ElevenLabs/";
        const string Evidence = "../evidence/audio/20260908/";

        static AudioClip Clip(string name)
        {
            string path = Folder + name + ".wav";
            var importer = AssetImporter.GetAtPath(path) as AudioImporter;
            if (!importer) throw new InvalidOperationException("Missing generated audio: " + path);
            bool music = name == "hill-at-dusk";
            bool loop = music || name == "desert-wind" || name == "market-murmur" || name.EndsWith("-hum");
            importer.forceToMono = name != "desert-wind" && !music;
            importer.loadInBackground = false;
            var settings = importer.defaultSampleSettings;
            settings.loadType = music ? AudioClipLoadType.Streaming : loop ? AudioClipLoadType.CompressedInMemory : AudioClipLoadType.DecompressOnLoad;
            settings.compressionFormat = loop ? AudioCompressionFormat.Vorbis : AudioCompressionFormat.PCM;
            settings.quality = .8f;
            settings.sampleRateSetting = AudioSampleRateSetting.PreserveSampleRate;
            importer.defaultSampleSettings = settings;
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<AudioClip>(path);
        }

        static AudioMixerGroup MusicGroup(AudioMixer mixer)
        {
            var existing = mixer.FindMatchingGroups("Music");
            if (existing.Length > 0) return existing.Single();
            // Unity keeps mixer authoring in its Editor controller API.
            var type = mixer.GetType();
            var master = type.GetProperty("masterGroup").GetValue(mixer);
            var groupType = master.GetType();
            var group = type.GetMethod("CreateNewGroup").Invoke(mixer, new object[] { "Music", true });
            var childProperty = groupType.GetProperty("children");
            var old = (Array)childProperty.GetValue(master);
            var children = Array.CreateInstance(groupType, old.Length + 1);
            Array.Copy(old, children, old.Length); children.SetValue(group, old.Length);
            childProperty.SetValue(master, children);
            var viewProperty = type.GetProperty("views");
            var views = (Array)viewProperty.GetValue(mixer);
            var viewType = viewProperty.PropertyType.GetElementType();
            var field = viewType.GetField("guids");
            var id = groupType.GetProperty("groupID").GetValue(group);
            for (int i = 0; i < views.Length; i++)
            {
                var view = views.GetValue(i); var ids = (Array)field.GetValue(view);
                var extended = Array.CreateInstance(ids.GetType().GetElementType(), ids.Length + 1);
                Array.Copy(ids, extended, ids.Length); extended.SetValue(id, ids.Length);
                field.SetValue(view, extended); views.SetValue(view, i);
            }
            viewProperty.SetValue(mixer, views);
            EditorUtility.SetDirty((UnityEngine.Object)master);
            EditorUtility.SetDirty(mixer);
            return (AudioMixerGroup)group;
        }

        [MenuItem("Athen Hill/Audio/Apply ElevenLabs soundscape")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play mode first.");
            if (UnityEngine.SceneManagement.SceneManager.GetActiveScene().path != ImportBaseline.ScenePath)
                EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var sound = UnityEngine.Object.FindAnyObjectByType<CityAudio>();
            if (!sound || !sound.session) throw new InvalidOperationException("Open the existing city with City Audio.");
            AssetDatabase.Refresh();
            var mixer = AssetDatabase.LoadAssetAtPath<AudioMixer>("Assets/AthenHill/Audio/City.mixer");
            var musicGroup = MusicGroup(mixer);

            AudioSource Source(AudioSource source, string name, string clip, string group, float volume,
                bool loop, Transform parent, float spatial = 0, float near = 2, float far = 16)
            {
                if (!source)
                {
                    var go = new GameObject(name); go.transform.SetParent(parent, false);
                    source = go.AddComponent<AudioSource>();
                }
                source.name = name; source.clip = Clip(clip);
                source.outputAudioMixerGroup = group == "Music" ? musicGroup : mixer.FindMatchingGroups(group).Single();
                source.volume = volume; source.loop = loop; source.playOnAwake = loop;
                source.spatialBlend = spatial; source.dopplerLevel = 0;
                source.rolloffMode = AudioRolloffMode.Linear; source.minDistance = near; source.maxDistance = far;
                source.priority = group == "Music" ? 160 : loop ? 180 : 100;
                EditorUtility.SetDirty(source);
                return source;
            }

            sound.ambience = Source(sound.ambience, "Desert wind", "desert-wind", "Ambience", .8f, true, sound.transform);
            sound.steps = Source(sound.steps, "Stone footsteps", "stone-step-01", "SFX", .55f, false, sound.session.player.transform);
            sound.footstepClips = new[] { sound.steps.clip, Clip("stone-step-02"), Clip("stone-step-03") };
            sound.confirmation = Source(sound.confirmation, "Terminal feedback", "terminal-click", "UI", .65f, false, sound.transform);
            sound.confirmation.ignoreListenerPause = true;
            sound.latticeHum = Source(sound.latticeHum, "Lattice hum", "lattice-hum", "Ambience", .7f, true, sound.session.latticePoint, 1, 3, 19);
            sound.ringHum = Source(sound.ringHum, "Ring hum", "ring-hum", "Ambience", .8f, true, sound.session.ringPoint, 1, 4, 22);
            sound.music = Source(sound.music, "Hill at Dusk - music", "hill-at-dusk", "Music", .65f, true, sound.transform);
            sound.market = Source(sound.market, "Market murmur", "market-murmur", "Ambience", .8f, true, sound.transform, 1, 4, 22);
            var vendor = sound.session.npcs.First(n => n.definition.id == "npc_mira");
            sound.market.transform.position = vendor.transform.position + Vector3.up;
            sound.travel = Source(sound.travel, "Lattice activation and link", "lattice-open", "SFX", .7f, false, sound.transform);
            sound.tradeConfirm = Clip("trade-confirm"); sound.unavailable = Clip("access-denied");
            sound.latticeOpen = sound.travel.clip; sound.latticeLink = Clip("lattice-link");
            EditorUtility.SetDirty(sound);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(sound.gameObject.scene); EditorSceneManager.SaveOpenScenes();
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "scene-audio.json", JsonConvert.SerializeObject(new {
                sources = UnityEngine.Object.FindObjectsByType<AudioSource>(FindObjectsSortMode.InstanceID).Select(s => new {
                    s.name, clip = s.clip ? s.clip.name : null, length = s.clip ? s.clip.length : 0,
                    group = s.outputAudioMixerGroup ? s.outputAudioMixerGroup.name : null,
                    s.volume, s.spatialBlend, s.loop, s.minDistance, s.maxDistance,
                    loadType = s.clip ? s.clip.loadType.ToString() : null
                }), footsteps = sound.footstepClips.Select(c => c.name),
                cues = new[] { sound.tradeConfirm.name, sound.unavailable.name, sound.latticeOpen.name, sound.latticeLink.name }
            }, Formatting.Indented));
        }

        public static void ApplyAndBuild()
        {
            Apply(); LinuxBuild.Development();
            File.Copy("Captures/linux-build.json", Evidence + "development-build.json", true);
            LinuxBuild.Release();
            File.Copy("Captures/linux-build.json", Evidence + "release-build.json", true);
        }
    }
}
