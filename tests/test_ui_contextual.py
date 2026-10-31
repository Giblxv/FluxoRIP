"""Regression checks for the Impressões contextual action bar."""
from pathlib import Path
import unittest

WEB = Path(__file__).resolve().parents[1] / "web"

class ContextToolbarTests(unittest.TestCase):
    def test_contextual_toolbar_replaces_duplicate_menu(self):
        js = (WEB / "prints.js").read_text(encoding="utf-8")
        self.assertIn("function pcContextToolbar()", js)
        self.assertIn("${pcContextToolbar()}", js)
        self.assertNotIn('class="pc-tool" data-pc-tab=', js)
        for action in ("nozzles", "bidirectional", "stepping", "cleaning", "flash",
                       "feeding", "refresh-logs", "export-logs", "save-profile"):
            self.assertIn(f"['{action}'", js)
        self.assertIn('data-pc-action="${id}"', js)

    def test_version_and_styles(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        css = (WEB / "styles.css").read_text(encoding="utf-8")
        self.assertIn("FLUXO RIP v1.5", html)
        self.assertIn('prints.js?v=10', html)
        self.assertIn('.pc-context-toolbar', css)
