# Read-only Win32 fallback for interfaces without UI Automation action patterns.
function Get-Win32WindowEvidence {
    param([int]$TargetProcessId)
    $result = [ordered]@{ state = 'unavailable'; nodes = @(); truncated = $false }
    if ([Environment]::OSVersion.Platform -ne 'Win32NT') { return [pscustomobject]$result }
    try {
        if (-not ('FluxoRIP.ReadOnlyWindowsV2.Snapshot' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
namespace FluxoRIP.ReadOnlyWindowsV2 {
    public sealed class Node {
        public int NodeId;
        public int? ParentNodeId;
        public int ControlId;
        public string ClassName;
        public bool TopLevel;
        public bool Visible;
        public bool Enabled;
        public uint Style;
    }
    public sealed class Result {
        public Node[] Nodes;
        public bool Truncated;
    }
    public static class Snapshot {
        private delegate bool EnumProc(IntPtr window, IntPtr context);
        [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc callback, IntPtr context);
        [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr parent, EnumProc callback, IntPtr context);
        [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
        [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetClassNameW(IntPtr window, StringBuilder text, int count);
        [DllImport("user32.dll")] private static extern int GetDlgCtrlID(IntPtr window);
        [DllImport("user32.dll")] private static extern IntPtr GetParent(IntPtr window);
        [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
        [DllImport("user32.dll")] private static extern bool IsWindowEnabled(IntPtr window);
        [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW")] private static extern IntPtr GetLong64(IntPtr window, int index);
        [DllImport("user32.dll", EntryPoint="GetWindowLongW")] private static extern int GetLong32(IntPtr window, int index);
        public static Result Collect(int targetProcessId) {
            const int limit = 600;
            var handles = new List<IntPtr>();
            var ids = new Dictionary<IntPtr, int>();
            var roots = new HashSet<IntPtr>();
            bool truncated = false;
            Func<IntPtr, bool> add = delegate(IntPtr handle) {
                uint owner;
                GetWindowThreadProcessId(handle, out owner);
                if (owner != (uint)targetProcessId || ids.ContainsKey(handle)) return true;
                if (handles.Count >= limit) { truncated = true; return false; }
                handles.Add(handle);
                ids[handle] = handles.Count;
                return true;
            };
            var hidden = new List<IntPtr>();
            int visited = 0;
            EnumProc top = delegate(IntPtr handle, IntPtr context) {
                uint owner;
                GetWindowThreadProcessId(handle, out owner);
                if (owner != (uint)targetProcessId) return true;
                if (roots.Count >= 32) { truncated = true; return false; }
                roots.Add(handle);
                return add(handle);
            };
            EnumWindows(top, IntPtr.Zero);
            // Seed all top-level windows before descendants, so a modal file dialog
            // cannot be lost behind hundreds of hidden controls in the main window.
            EnumProc child = delegate(IntPtr handle, IntPtr context) {
                if (++visited > 5000) { truncated = true; return false; }
                uint owner;
                GetWindowThreadProcessId(handle, out owner);
                if (owner != (uint)targetProcessId) return true;
                if (IsWindowVisible(handle)) return add(handle);
                if (hidden.Count < 2000) hidden.Add(handle);
                else truncated = true;
                return true;
            };
            foreach (IntPtr root in roots) {
                EnumChildWindows(root, child, IntPtr.Zero);
                if (handles.Count >= limit) { truncated = true; break; }
            }
            foreach (IntPtr handle in hidden) {
                if (!add(handle)) break;
            }
            var nodes = new List<Node>();
            foreach (IntPtr handle in handles) {
                var text = new StringBuilder(128);
                GetClassNameW(handle, text, text.Capacity);
                int parent;
                bool hasParent = ids.TryGetValue(GetParent(handle), out parent);
                long style = IntPtr.Size == 8 ? GetLong64(handle, -16).ToInt64() : (long)GetLong32(handle, -16);
                nodes.Add(new Node {
                    NodeId=ids[handle], ParentNodeId=hasParent ? (int?)parent : null,
                    ControlId=GetDlgCtrlID(handle), ClassName=text.ToString(),
                    TopLevel=roots.Contains(handle), Visible=IsWindowVisible(handle),
                    Enabled=IsWindowEnabled(handle), Style=unchecked((uint)style)
                });
            }
            return new Result { Nodes=nodes.ToArray(), Truncated=truncated || handles.Count >= limit };
        }
    }
}
'@
        }
        $snapshot = [FluxoRIP.ReadOnlyWindowsV2.Snapshot]::Collect($TargetProcessId)
        $result.nodes = @($snapshot.Nodes | ForEach-Object {
            [pscustomobject]@{
                node_id = $_.NodeId; parent_node_id = $_.ParentNodeId
                control_id = $_.ControlId; class_name = $_.ClassName
                top_level = $_.TopLevel; visible = $_.Visible; enabled = $_.Enabled
                style = $_.Style
            }
        })
        $result.truncated = $snapshot.Truncated
        $result.state = 'observed'
    } catch { $result.state = 'unavailable' }
    return [pscustomobject]$result
}
