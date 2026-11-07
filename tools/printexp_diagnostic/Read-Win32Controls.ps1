# Read-only Win32 fallback for interfaces without UI Automation action patterns.
function Initialize-Win32WindowReader {
        if (-not ('FluxoRIP.ReadOnlyWindowsV3.Snapshot' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
namespace FluxoRIP.ReadOnlyWindowsV3 {
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
        public bool VisibleCaptureComplete;
        public int HiddenNodesOmitted;
        public int HelperWindowsOmitted;
    }
    public sealed class RootCandidate {
        public IntPtr Handle;
        public string ClassName;
        public bool Visible;
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
        public static bool IsHelper(string className) {
            return String.Equals(className, "tooltips_class32", StringComparison.OrdinalIgnoreCase)
                || String.Equals(className, "IME", StringComparison.OrdinalIgnoreCase)
                || String.Equals(className, "MSCTFIME UI", StringComparison.OrdinalIgnoreCase)
                || (className != null && className.StartsWith("VSyncHelper-", StringComparison.OrdinalIgnoreCase));
        }
        public static RootCandidate[] PrioritizeRoots(RootCandidate[] candidates) {
            var selected = new List<RootCandidate>();
            int visible = 0, hidden = 0;
            foreach (RootCandidate candidate in candidates) {
                if (!IsHelper(candidate.ClassName) && candidate.Visible && visible < 32) {
                    selected.Add(candidate); visible++;
                }
            }
            foreach (RootCandidate candidate in candidates) {
                if (!IsHelper(candidate.ClassName) && !candidate.Visible && hidden < 16) {
                    selected.Add(candidate); hidden++;
                }
            }
            return selected.ToArray();
        }
        public static Result Collect(int targetProcessId) {
            const int limit = 600;
            var handles = new List<IntPtr>();
            var ids = new Dictionary<IntPtr, int>();
            var roots = new HashSet<IntPtr>();
            bool truncated = false;
            bool visibleComplete = true;
            int hiddenOmitted = 0, helperOmitted = 0;
            Func<IntPtr, bool> add = delegate(IntPtr handle) {
                uint owner;
                GetWindowThreadProcessId(handle, out owner);
                if (owner != (uint)targetProcessId || ids.ContainsKey(handle)) return true;
                if (handles.Count >= limit) { truncated = true; return false; }
                handles.Add(handle);
                ids[handle] = handles.Count;
                return true;
            };
            var candidates = new List<RootCandidate>();
            int visited = 0;
            int topVisited = 0;
            EnumProc top = delegate(IntPtr handle, IntPtr context) {
                if (++topVisited > 8192) { truncated = true; visibleComplete = false; return false; }
                uint owner;
                GetWindowThreadProcessId(handle, out owner);
                if (owner != (uint)targetProcessId) return true;
                var className = new StringBuilder(128);
                if (GetClassNameW(handle, className, className.Capacity) == 0) return true;
                if (IsHelper(className.ToString())) { helperOmitted++; return true; }
                if (candidates.Count >= 512) { truncated = true; visibleComplete = false; return false; }
                candidates.Add(new RootCandidate { Handle=handle, ClassName=className.ToString(), Visible=IsWindowVisible(handle) });
                return true;
            };
            if (!EnumWindows(top, IntPtr.Zero) && !truncated) throw new InvalidOperationException("Window enumeration unavailable");
            RootCandidate[] selected = PrioritizeRoots(candidates.ToArray());
            if (selected.Length < candidates.Count) truncated = true;
            int visibleCount = 0;
            foreach (RootCandidate candidate in candidates) if (candidate.Visible) visibleCount++;
            if (visibleCount > 32) visibleComplete = false;
            // Discover and prioritize visible roots before applying output budgets.
            // Helper/tooltip windows cannot consume the root budget.
            foreach (RootCandidate candidate in selected) { roots.Add(candidate.Handle); add(candidate.Handle); }
            EnumProc child = delegate(IntPtr handle, IntPtr context) {
                if (++visited > 5000) { truncated = true; visibleComplete = false; return false; }
                uint owner;
                GetWindowThreadProcessId(handle, out owner);
                if (owner != (uint)targetProcessId) return true;
                if (!IsWindowVisible(handle)) { hiddenOmitted++; return true; }
                if (!add(handle)) { visibleComplete = false; return false; }
                return true;
            };
            foreach (RootCandidate root in selected) {
                EnumChildWindows(root.Handle, child, IntPtr.Zero);
                if (!visibleComplete && (handles.Count >= limit || visited > 5000)) break;
            }
            var nodes = new List<Node>();
            foreach (IntPtr handle in handles) {
                uint owner;
                GetWindowThreadProcessId(handle, out owner);
                if (owner != (uint)targetProcessId) { visibleComplete = false; continue; }
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
            return new Result { Nodes=nodes.ToArray(), Truncated=truncated,
                VisibleCaptureComplete=visibleComplete, HiddenNodesOmitted=hiddenOmitted,
                HelperWindowsOmitted=helperOmitted };
        }
    }
}
'@
        }
}

function Get-Win32WindowEvidence {
    param([int]$TargetProcessId)
    $result = [ordered]@{ state = 'unavailable'; nodes = @(); truncated = $false; visible_capture_complete = $false; hidden_nodes_omitted = 0; helper_windows_omitted = 0 }
    if ([Environment]::OSVersion.Platform -ne 'Win32NT') { return [pscustomobject]$result }
    try {
        Initialize-Win32WindowReader
        $snapshot = [FluxoRIP.ReadOnlyWindowsV3.Snapshot]::Collect($TargetProcessId)
        $result.nodes = @($snapshot.Nodes | ForEach-Object {
            [pscustomobject]@{
                node_id = $_.NodeId; parent_node_id = $_.ParentNodeId
                control_id = $_.ControlId; class_name = $_.ClassName
                top_level = $_.TopLevel; visible = $_.Visible; enabled = $_.Enabled
                style = $_.Style
            }
        })
        $result.truncated = $snapshot.Truncated
        $result.visible_capture_complete = $snapshot.VisibleCaptureComplete
        $result.hidden_nodes_omitted = $snapshot.HiddenNodesOmitted
        $result.helper_windows_omitted = $snapshot.HelperWindowsOmitted
        $result.state = 'observed'
    } catch { $result.state = 'unavailable' }
    return [pscustomobject]$result
}
