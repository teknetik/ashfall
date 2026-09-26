using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using System.IO;

[InitializeOnLoad]
public class InfoSetupPip : EditorWindow
{
    static bool showdialogwindow = true;
    static InfoSetupPip dialogwindow;
    static string prefkey;

    static InfoSetupPip()
    {
        EditorApplication.update += Update;
    }
    static void Update()
    {
        var datapath = Application.dataPath;
        var strval = datapath.Split("/"[0]);
        prefkey = strval[strval.Length - 2];

        showdialogwindow = (!EditorPrefs.HasKey(prefkey));
        if (showdialogwindow)
        {
            dialogwindow = GetWindow<InfoSetupPip>(true);
            dialogwindow.minSize = new Vector2(350, 380);
        }
        EditorApplication.update -= Update;
    }

    public void OnGUI()
    {
        var rect = GUILayoutUtility.GetRect(position.width - 10, 100, GUI.skin.box);

        Texture2D ilranchlogo = AssetDatabase.LoadAssetAtPath<Texture2D>(
            Path.GetDirectoryName(AssetDatabase.GetAssetPath(MonoScript.FromScriptableObject(this))) + "/LogoDialog.png");
        if (ilranchlogo != null)
        {
            GUI.DrawTexture(rect, ilranchlogo, ScaleMode.ScaleToFit);
        }

        GUI.backgroundColor = Color.white;
        EditorGUILayout.HelpBox("Pipelines setup for Beginners:", MessageType.Info, true);
        GUI.backgroundColor = Color.clear;
        EditorGUILayout.HelpBox("This package contains HDRP and LWRP (Universal) assets.", MessageType.None);
        GUI.backgroundColor = Color.white;
        EditorGUILayout.HelpBox("In order to enable prefabs you should enable HDRP or LWRP pipeline.", MessageType.None);
        GUI.backgroundColor = Color.clear;
        EditorGUILayout.HelpBox("Step by step:", MessageType.None);
        GUI.backgroundColor = Color.white;
        EditorGUILayout.HelpBox("1. Open package manager:", MessageType.None);

        GUI.backgroundColor = Color.green;
        if (GUILayout.Button("Open Package Manager"))
        {
            EditorApplication.ExecuteMenuItem("Window/Package Manager");
        }

        GUI.backgroundColor = Color.white;
        EditorGUILayout.HelpBox("2. Install HDRP or LWRP (Universal) pipeline.", MessageType.None);
        EditorGUILayout.HelpBox("3. Open project settings:", MessageType.None);

        GUI.backgroundColor = Color.green;
        if (GUILayout.Button("Open Project Settings"))
        {
            EditorApplication.ExecuteMenuItem("Edit/Project Settings...");
        }

        GUI.backgroundColor = Color.white;
        EditorGUILayout.HelpBox("4. Assign HDRP or LWRP asset from 'PipAsset' folder into", MessageType.None);
        EditorGUILayout.HelpBox("Graphics > Scriptable Render Pipeline Settings.", MessageType.None);
        EditorGUILayout.HelpBox("Done. Prefabs ready to use.", MessageType.None);

        GUILayout.FlexibleSpace();
        GUI.backgroundColor = Color.cyan;
        if (GUILayout.Button("Close Prompt"))
        {
            EditorPrefs.SetBool(prefkey, true);
            Close();
        }
    }
}
