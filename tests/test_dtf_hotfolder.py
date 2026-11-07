"""Explicitly selected local hot folders; synthetic images only."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

_TEST_DATA = tempfile.TemporaryDirectory(prefix="fluxo-hotfolder-tests-")
os.environ.setdefault("FORGE_DATA_DIR", _TEST_DATA.name)
from app.db import SessionLocal, init_db
from app.dtf_hotfolder import HotFolderMonitor, HotFolderReceipt
from app.dtf_studio import EXPORT_DIR, DtfRun
from app.main import app


class HotFolderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="dtf-incoming-")
        self.addCleanup(self.folder.cleanup)
        self.addCleanup(
            lambda: self.client.put("/api/studio/hotfolder", json={"enabled": False})
        )
        self.config = {
            "enabled": True,
            "folder": self.folder.name,
            "art_width_mm": 20,
            "film_width_mm": 60,
            "dpi": 150,
        }

    def test_opt_in_and_stability_deduplication(self):
        image = Path(self.folder.name) / "sintetica.png"
        Image.new("RGBA", (64, 32), (0, 166, 214, 255)).save(image)
        monitor = HotFolderMonitor()
        self.client.put("/api/studio/hotfolder", json={"enabled": False})
        monitor.scan()
        self.assertFalse(monitor.observed)
        self.assertEqual(
            self.client.put("/api/studio/hotfolder", json=self.config).status_code, 200
        )
        with patch("app.dtf_hotfolder.time.monotonic", return_value=100):
            monitor.scan()
        with SessionLocal() as db:
            before = len(db.scalars(select(HotFolderReceipt)).all())
        with patch("app.dtf_hotfolder.time.monotonic", return_value=103):
            monitor.scan()
        with SessionLocal() as db:
            self.assertEqual(len(db.scalars(select(HotFolderReceipt)).all()), before)
        original = image.read_bytes()
        with patch("app.dtf_hotfolder.time.monotonic", return_value=107):
            monitor.scan()
            monitor.scan()
        self.assertEqual(image.read_bytes(), original)
        with SessionLocal() as db:
            rows = db.scalars(select(HotFolderReceipt)).all()
            self.assertEqual(len(rows), before + 1)
            receipt = next(
                r for r in rows if r.filename == "sintetica.png" and r.run_id
            )
            self.assertEqual(db.get(DtfRun, receipt.run_id).status, "AGUARDANDO")
            # Leave no pending jobs for other tests' worker lifecycles.
            run = db.get(DtfRun, receipt.run_id)
            run.status = "CANCELADO"
            db.commit()

    def test_rejects_missing_relative_output_folder_and_invalid_geometry(self):
        for folder in (
            "relative/path",
            str(Path(self.folder.name) / "missing"),
            str(EXPORT_DIR),
        ):
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            response = self.client.put(
                "/api/studio/hotfolder", json={**self.config, "folder": folder}
            )
            self.assertEqual(response.status_code, 422, response.text)
        for extra in ({"art_width_mm": 5000}, {"dpi": 123}, {"margin_mm": 80}):
            response = self.client.put(
                "/api/studio/hotfolder", json={**self.config, **extra}
            )
            self.assertEqual(response.status_code, 422, response.text)

    def test_bad_image_recorded_once_without_modifying_source(self):
        file = Path(self.folder.name) / "corrompida.png"
        file.write_bytes(b"not-an-image")
        self.client.put("/api/studio/hotfolder", json=self.config)
        monitor = HotFolderMonitor()
        with patch("app.dtf_hotfolder.time.monotonic", return_value=10):
            monitor.scan()
        with patch("app.dtf_hotfolder.time.monotonic", return_value=20):
            monitor.scan()
            monitor.scan()
        with SessionLocal() as db:
            rows = db.scalars(
                select(HotFolderReceipt).where(
                    HotFolderReceipt.filename == "corrompida.png"
                )
            ).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].status, "ERRO")
        self.assertEqual(file.read_bytes(), b"not-an-image")

    def test_local_browser_write_requires_same_origin(self):
        response = self.client.put(
            "/api/studio/hotfolder",
            json=self.config,
            headers={"Origin": "https://unrelated.example"},
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.put(
            "/api/studio/hotfolder",
            json=self.config,
            headers={"Origin": "http://testserver"},
        )
        self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
