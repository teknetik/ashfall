using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    public static class SettingsAudioPass
    {
        [MenuItem("Athen Hill/Audio/Apply supplied city music")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Exit Play mode first.");
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            AssetDatabase.Refresh();
            var audio = UnityEngine.Object.FindAnyObjectByType<CityAudio>();
            if (!audio || !audio.music) throw new InvalidOperationException("The saved city audio is missing.");
            audio.musicPlaylist = new[] { "Dust of the Giants", "Dust of Alshain" }.Select(name =>
            {
                string path = "Assets/AthenHill/Audio/Music/" + name + ".mp3";
                var importer = AssetImporter.GetAtPath(path) as AudioImporter;
                if (!importer) throw new InvalidOperationException("Missing supplied track: " + path);
                importer.forceToMono = false;
                var sample = importer.defaultSampleSettings;
                sample.loadType = AudioClipLoadType.Streaming;
                sample.compressionFormat = AudioCompressionFormat.Vorbis;
                sample.quality = .85f; sample.preloadAudioData = false;
                importer.defaultSampleSettings = sample; importer.SaveAndReimport();
                return AssetDatabase.LoadAssetAtPath<AudioClip>(path);
            }).ToArray();
            audio.music.Stop(); audio.music.name = "City soundtrack";
            audio.music.clip = audio.musicPlaylist[0]; audio.music.loop = false; audio.music.playOnAwake = false;
            if (!audio.session.GetComponent<GameSettings>()) audio.session.gameObject.AddComponent<GameSettings>();
            EditorUtility.SetDirty(audio); EditorUtility.SetDirty(audio.music);
            EditorSceneManager.MarkSceneDirty(audio.gameObject.scene);
            EditorSceneManager.SaveOpenScenes(); AssetDatabase.SaveAssets();
        }
        public static void ApplyAndBuild()
        {
            Apply();
            Directory.CreateDirectory("../evidence/settings/20260908");
            LinuxBuild.Development();
            File.Copy("Captures/linux-build.json", "../evidence/settings/20260908/development-build.json", true);
            LinuxBuild.Release();
            File.Copy("Captures/linux-build.json", "../evidence/settings/20260908/release-build.json", true);
        }
    }
}
