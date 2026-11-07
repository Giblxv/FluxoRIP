// Disposable test application. Contains no printer code or proprietary software.
using System;
using System.IO;
using System.Windows.Forms;

public static class PrintDialogFixture {
    [STAThread]
    public static void Main(string[] args) {
        string folder = args[0];
        string kind = args.Length > 1 ? args[1] : "open";
        Application.EnableVisualStyles();
        using (var owner = new Form()) {
            owner.Text = "Synthetic dialog owner";
            owner.Show();
            if (kind == "save") {
                using (var dialog = new SaveFileDialog()) {
                    dialog.InitialDirectory = folder;
                    dialog.Filter = "Synthetic files|*.prt;*.prn";
                    dialog.FileName = "";
                    dialog.ShowDialog(owner);
                }
            } else {
                using (var dialog = new OpenFileDialog()) {
                    dialog.InitialDirectory = folder;
                    dialog.Filter = "Synthetic files|*.prt;*.prn";
                    dialog.FileName = kind == "nonempty" ? "operator-draft.prt" : "";
                    dialog.Multiselect = false;
                    dialog.CheckFileExists = true;
                    dialog.FileOk += delegate(object sender, System.ComponentModel.CancelEventArgs eventArgs) {
                        File.WriteAllText(Path.Combine(folder, "confirmation-was-triggered.txt"), "unexpected");
                        eventArgs.Cancel = true;
                    };
                    dialog.ShowDialog(owner);
                }
            }
        }
    }
}
