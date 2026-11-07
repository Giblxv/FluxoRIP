"""Explicitly selected local hot folders; synthetic images only."""

import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete, select

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

    def test_recent_receipts_remain_visible_and_show_current_job_status(self):
        prefix = uuid.uuid4().hex
        with SessionLocal() as db:
            run = DtfRun(
                id=str(uuid.uuid4()),
                name="Status da automação",
                status="PROCESSANDO",
                request_json="{}",
            )
            db.add(run)
            db.flush()
            run_id = run.id
            for index in range(120):
                db.add(
                    HotFolderReceipt(
                        fingerprint=uuid.uuid4().hex,
                        filename=f"{prefix}-{index:03d}",
                        status="ENFILEIRADO",
                        run_id=run_id,
                    )
                )
            db.commit()
        try:
            response = self.client.get("/api/studio/hotfolder")
            self.assertEqual(response.status_code, 200, response.text)
            receipts = response.json()["receipts"]
            self.assertEqual(len(receipts), 30)
            self.assertEqual(receipts[0]["filename"], f"{prefix}-119")
            self.assertEqual(receipts[-1]["filename"], f"{prefix}-090")
            self.assertTrue(all(r["status"] == "PROCESSANDO" for r in receipts))
            self.client.post(f"/api/studio/runs/{run_id}/cancel")
            self.assertEqual(
                self.client.get("/api/studio/hotfolder").json()["receipts"][0][
                    "status"
                ],
                "CANCELADO",
            )
        finally:
            with SessionLocal() as db:
                db.execute(
                    delete(HotFolderReceipt).where(
                        HotFolderReceipt.filename.startswith(prefix)
                    )
                )
                db.execute(delete(DtfRun).where(DtfRun.id == run_id))
                db.commit()

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
