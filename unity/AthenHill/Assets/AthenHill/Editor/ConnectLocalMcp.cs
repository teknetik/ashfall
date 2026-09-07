using UnityEditor;
using UnityEngine;
using MCPForUnity.Editor.Services;

// Connection bootstrap only. Scene creation and verification are performed through MCP.
[InitializeOnLoad]
public static class ConnectLocalMcp
{
    static ConnectLocalMcp() { EditorApplication.delayCall += Connect; }

    [MenuItem("Athen Hill/Connect local MCP")]
    public static async void Connect()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating)
        {
            EditorApplication.delayCall += Connect;
            return;
        }
        if (MCPServiceLocator.Bridge.IsRunning) return;
        EditorPrefs.SetBool("MCPForUnity.UseHttpTransport", true);
        EditorPrefs.SetString("MCPForUnity.HttpTransportScope", "local");
        EditorPrefs.SetString("MCPForUnity.HttpUrl", "http://127.0.0.1:18081");
        EditorConfigurationCache.Instance.Refresh();
        Debug.Log("Athen Hill MCP connection: " + await MCPServiceLocator.Bridge.StartAsync());
    }
}
