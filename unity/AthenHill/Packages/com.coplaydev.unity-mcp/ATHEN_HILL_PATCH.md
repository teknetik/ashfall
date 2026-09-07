Based on CoplayDev/unity-mcp v10.2.0, git package revision 045e809812a8.

Local compatibility patch: Unity 6000.6.0f1 throws NotImplementedException from the reflected InstanceIDToObject method. The reverse wire-handle shim now searches loaded Unity objects, compares the plugin's existing forward handle and fails closed on ambiguity. It never fabricates a full EntityId from truncated bits. Editor-only lookup; no gameplay cost. Preserve the upstream licence.
