using UnityEditor;
using UnityEngine;
using MCPForUnity.Editor.Services;

// Connection bootstrap only. Scene creation and verification are performed through MCP.
[InitializeOnLoad]
public static class ConnectLocalMcp
{
    static int retries;
    static double nextAttempt;
    static void Retry(){if(EditorApplication.timeSinceStartup<nextAttempt)return;EditorApplication.update-=Retry;Connect();}
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
        bool connected=await MCPServiceLocator.Bridge.StartAsync();
        Debug.Log("Athen Hill MCP connection: " + connected);
        if(!connected&&++retries<12){nextAttempt=EditorApplication.timeSinceStartup+5;EditorApplication.update-=Retry;EditorApplication.update+=Retry;}
    }
}
