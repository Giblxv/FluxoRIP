// Generic Windows file-dialog path preparation. No job confirmation API exists here.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace FluxoRIP.PrepareOnlyV1 {
    public sealed class Inspection {
        public string State;
        public int CandidateCount;
        public bool InputEmpty;
        public bool CanPrepare;
        public string Token;
    }
    public sealed class Preparation {
        public string State;
        public bool WriteAttempted;
        public bool WriteAccepted;
        public bool PathVerified;
        public bool DialogStillOpen;
    }
    public static class FileDialogGuard {
        private const uint ReadMessage = 0x000D;
        private const uint WriteMessage = 0x000C;
        private const uint TimeoutFlags = 0x0023;
        private delegate bool EnumProc(IntPtr window, IntPtr context);
        [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc callback, IntPtr context);
        [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr root, EnumProc callback, IntPtr context);
        [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
        [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetClassNameW(IntPtr window, StringBuilder text, int count);
        [DllImport("user32.dll")] private static extern IntPtr GetDlgItem(IntPtr root, int controlId);
        [DllImport("user32.dll")] private static extern IntPtr GetParent(IntPtr window);
        [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
        [DllImport("user32.dll")] private static extern bool IsWindowEnabled(IntPtr window);
        [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW")] private static extern IntPtr GetStyle64(IntPtr window, int index);
        [DllImport("user32.dll", EntryPoint="GetWindowLongW")] private static extern int GetStyle32(IntPtr window, int index);
        [DllImport("user32.dll", EntryPoint="SendMessageTimeoutW", CharSet=CharSet.Unicode)]
        private static extern IntPtr ReadText(IntPtr window, uint message, UIntPtr count, [Out] StringBuilder text, uint flags, uint timeout, out UIntPtr result);
        [DllImport("user32.dll", EntryPoint="SendMessageTimeoutW", CharSet=CharSet.Unicode)]
        private static extern IntPtr WriteText(IntPtr window, uint message, UIntPtr unused, string text, uint flags, uint timeout, out UIntPtr result);

        private sealed class Candidate {
            public int ProcessId;
            public IntPtr Root, Owner, Edit;
            public long Created;
        }
        private static readonly Dictionary<string, Candidate> Tokens = new Dictionary<string, Candidate>();
        private static readonly object Gate = new object();

        public static string NormalizeRole(string label) {
            return (label ?? "").Replace("&", "").Trim().ToLowerInvariant();
        }
        public static bool IsOpenRole(string label) {
            string role = NormalizeRole(label);
            return role == "open" || role == "abrir";
        }
        public static bool IsCancelRole(string label) {
            string role = NormalizeRole(label);
            return role == "cancel" || role == "cancelar";
        }
        public static bool IsSafePathSyntax(string path) {
            if (String.IsNullOrEmpty(path) || path.Length > 259 || path.Length < 4) return false;
            if (!Char.IsLetter(path[0]) || path[1] != ':' || path[2] != '\\') return false;
            if (path.IndexOf(':', 2) >= 0) return false;
            foreach (char value in path) {
                if (value < 32 || "\"<>|?*".IndexOf(value) >= 0) return false;
            }
            string leaf = path.Substring(path.LastIndexOf('\\') + 1);
            string baseName = leaf.Split('.')[0].TrimEnd(' ', '.').ToUpperInvariant();
            if (baseName == "CON" || baseName == "PRN" || baseName == "AUX" || baseName == "NUL") return false;
            if (baseName.Length == 4 && (baseName.StartsWith("COM") || baseName.StartsWith("LPT")) && baseName[3] >= '1' && baseName[3] <= '9') return false;
            string extension = Path.GetExtension(path);
            return String.Equals(extension, ".prt", StringComparison.OrdinalIgnoreCase)
                || String.Equals(extension, ".prn", StringComparison.OrdinalIgnoreCase);
        }
        public static string ValidateLocalFile(string path) {
            if (!IsSafePathSyntax(path)) return "path_invalid";
            if (Environment.OSVersion.Platform != PlatformID.Win32NT) return "windows_required";
            try {
                string full = Path.GetFullPath(path);
                if (!String.Equals(full, path, StringComparison.OrdinalIgnoreCase)) return "path_not_normalized";
                var drive = new DriveInfo(Path.GetPathRoot(full));
                if (drive.DriveType != DriveType.Fixed && drive.DriveType != DriveType.Removable) return "not_local_drive";
                if (!File.Exists(full)) return "file_missing";
                if ((File.GetAttributes(full) & (FileAttributes.Directory | FileAttributes.ReparsePoint)) != 0) return "file_not_regular";
                for (DirectoryInfo parent = new FileInfo(full).Directory; parent != null; parent = parent.Parent) {
                    if ((parent.Attributes & FileAttributes.ReparsePoint) != 0) return "parent_is_link";
                }
                if (new FileInfo(full).Length == 0) return "file_empty";
                return "valid";
            } catch { return "file_unavailable"; }
        }
        private static bool Belongs(IntPtr window, int expected) {
            if (window == IntPtr.Zero) return false;
            uint owner;
            GetWindowThreadProcessId(window, out owner);
            return owner == (uint)expected;
        }
        private static string ClassOf(IntPtr window) {
            var text = new StringBuilder(128);
            GetClassNameW(window, text, text.Capacity);
            return text.ToString();
        }
        private static bool TryRead(IntPtr window, int capacity, out string value) {
            var text = new StringBuilder(capacity);
            UIntPtr length;
            bool ok = ReadText(window, ReadMessage, (UIntPtr)(uint)capacity, text, TimeoutFlags, 500, out length) != IntPtr.Zero;
            value = ok ? text.ToString() : "";
            return ok && length.ToUInt64() < (ulong)(capacity - 1);
        }
        private static Candidate Qualify(IntPtr root, int processId) {
            if (!Belongs(root, processId) || !IsWindowVisible(root) || !IsWindowEnabled(root) || ClassOf(root) != "#32770") return null;
            IntPtr owner = GetParent(root);
            if (!Belongs(owner, processId) || !IsWindowVisible(owner) || IsWindowEnabled(owner)) return null;
            IntPtr outer = GetDlgItem(root, 1148);
            IntPtr combo = GetDlgItem(outer, 1148);
            IntPtr edit = GetDlgItem(combo, 1148);
            if (ClassOf(outer) != "ComboBoxEx32" || ClassOf(combo) != "ComboBox" || ClassOf(edit) != "Edit") return null;
            if (!Belongs(edit, processId) || !IsWindowVisible(edit) || !IsWindowEnabled(edit)) return null;
            long editStyle = IntPtr.Size == 8 ? GetStyle64(edit, -16).ToInt64() : (long)GetStyle32(edit, -16);
            if ((editStyle & 0x0824) != 0) return null; // No read-only, password or multiline field.
            IntPtr positive = GetDlgItem(root, 1), negative = GetDlgItem(root, 2);
            if (ClassOf(positive) != "Button" || ClassOf(negative) != "Button") return null;
            if (!IsWindowVisible(positive) || !IsWindowVisible(negative) || !IsWindowEnabled(positive) || !IsWindowEnabled(negative)) return null;
            bool shellView = false;
            int visited = 0;
            EnumChildWindows(root, delegate(IntPtr child, IntPtr context) {
                if (++visited > 600) return false;
                if (Belongs(child, processId) && ClassOf(child) == "SHELLDLL_DefView") shellView = true;
                return true;
            }, IntPtr.Zero);
            if (!shellView || visited > 600) return null;
            string positiveRole, negativeRole;
            if (!TryRead(positive, 128, out positiveRole) || !TryRead(negative, 128, out negativeRole)) return null;
            if (!IsOpenRole(positiveRole) || !IsCancelRole(negativeRole)) return null;
            return new Candidate { Root=root, Owner=owner, Edit=edit, ProcessId=processId, Created=Stopwatch.GetTimestamp() };
        }
        private static List<Candidate> Find(int processId) {
            var candidates = new List<Candidate>();
            int visited = 0;
            bool limited = false;
            bool ok = EnumWindows(delegate(IntPtr window, IntPtr context) {
                if (++visited > 8192) { limited = true; return false; }
                if (!Belongs(window, processId)) return true;
                Candidate candidate = Qualify(window, processId);
                if (candidate != null) candidates.Add(candidate);
                return true;
            }, IntPtr.Zero);
            if (!ok || limited) throw new InvalidOperationException("window_enumeration_incomplete");
            return candidates;
        }
        public static Inspection Inspect(int processId) {
            var result = new Inspection { State="unavailable" };
            if (Environment.OSVersion.Platform != PlatformID.Win32NT) { result.State="windows_required"; return result; }
            try {
                List<Candidate> candidates = Find(processId);
                result.CandidateCount = candidates.Count;
                if (candidates.Count != 1) { result.State=candidates.Count == 0 ? "no_supported_open_dialog" : "ambiguous_dialog"; return result; }
                string input;
                if (!TryRead(candidates[0].Edit, 512, out input)) { result.State="input_unreadable"; return result; }
                result.InputEmpty = input.Length == 0;
                if (!result.InputEmpty) { result.State="input_not_empty"; return result; }
                result.CanPrepare = true;
                result.State = "ready_for_manual_preparation";
                result.Token = Guid.NewGuid().ToString("N");
                lock (Gate) {
                    Tokens.Clear();
                    Tokens[result.Token] = candidates[0];
                }
                return result;
            } catch { result.State="inspection_unavailable"; return result; }
        }
        public static Preparation Prepare(string token, string path) {
            var result = new Preparation { State="token_invalid" };
            Candidate expected;
            lock (Gate) {
                if (token == null || !Tokens.TryGetValue(token, out expected)) return result;
                Tokens.Remove(token); // A user confirmation permits at most one write attempt.
            }
            if ((Stopwatch.GetTimestamp() - expected.Created) / (double)Stopwatch.Frequency > 300) { result.State="inspection_expired"; return result; }
            result.State = ValidateLocalFile(path);
            if (result.State != "valid") return result;
            try {
                List<Candidate> current = Find(expected.ProcessId);
                if (current.Count != 1 || current[0].Root != expected.Root || current[0].Edit != expected.Edit || current[0].Owner != expected.Owner) {
                    result.State="dialog_changed"; return result;
                }
                string input;
                if (!TryRead(expected.Edit, 512, out input)) { result.State="input_unreadable"; return result; }
                if (input.Length != 0) { result.State="input_not_empty"; return result; }
                Candidate lastCheck = Qualify(expected.Root, expected.ProcessId);
                if (lastCheck == null || lastCheck.Edit != expected.Edit) { result.State="dialog_changed"; return result; }
                UIntPtr accepted;
                result.WriteAttempted = true;
                result.WriteAccepted = WriteText(expected.Edit, WriteMessage, UIntPtr.Zero, path, TimeoutFlags, 1000, out accepted) != IntPtr.Zero && accepted.ToUInt64() == 1;
                string readback;
                result.PathVerified = result.WriteAccepted && TryRead(expected.Edit, 512, out readback) && String.Equals(readback, path, StringComparison.Ordinal);
                result.DialogStillOpen = Qualify(expected.Root, expected.ProcessId) != null;
                result.State = result.PathVerified && result.DialogStillOpen ? "path_prepared_confirmation_manual" : "preparation_not_confirmed";
            } catch { result.State="preparation_unavailable"; }
            return result;
        }
    }
}
