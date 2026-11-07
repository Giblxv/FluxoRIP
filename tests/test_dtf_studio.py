"""DTF contracts with synthetic art only; never contacts a printer."""

import hashlib
import io
import json
import os
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageCms, ImageDraw

# A separate process is recommended for this suite; no production data is used.
_TEST_DATA = tempfile.TemporaryDirectory(prefix="fluxo-dtf-tests-")
os.environ.setdefault("FORGE_DATA_DIR", _TEST_DATA.name)
from app.db import SessionLocal, init_db
from app.dtf_studio import (
    EXPORT_DIR,
    DtfRun,
    RasterWorker,
    render_run,
    white_mask,
)
from app.main import app


class DtfStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        # Without lifespan: process jobs deterministically in the test thread.
        cls.client = TestClient(app)

    def upload(self, image, name="arte.png", **save_options):
        buffer = io.BytesIO()
        image.save(buffer, "PNG", **save_options)
        data = buffer.getvalue()
        response = self.client.post(
            "/api/art/upload", files={"file": (name, data, "image/png")}
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json(), data

    def synthetic(self):
        image = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 39, 49), fill=(230, 0, 100, 255))
        draw.rectangle((40, 10, 89, 49), fill=(0, 166, 214, 128))
        return self.upload(image)

    def request(self, asset_id, **kwargs):
        data = {
            "items": [{"asset_id": asset_id, "width_mm": 25.4, "copies": 1}],
            "film_width_mm": 50.8,
            "margin_mm": 0,
            "gap_mm": 0,
            "dpi": 150,
            "trim": False,
            "choke_mm": 0,
            "white_percent": 100,
            "mirror": True,
        }
        data.update(kwargs)
        return data

    def render(self, data):
        with SessionLocal() as db:
            row = DtfRun(
                id=str(uuid.uuid4()),
                name="Teste",
                status="PROCESSANDO",
                request_json=json.dumps(data),
            )
            db.add(row)
            db.commit()
            run_id = row.id
        render_run(run_id)
        with SessionLocal() as db:
            row = db.get(DtfRun, run_id)
            self.assertEqual(row.status, "CONCLUIDO", row.error)
            self.assertEqual(row.progress, 100)
        return run_id

    def test_studio_is_primary_and_management_remains_compatible(self):
        html = self.client.get("/").text
        self.assertIn("Studio DTF", html)
        self.assertNotIn('data-page="scanner"', html)
        self.assertNotIn('data-page="projects"', html)
        self.assertIn('data-page="scanner"', self.client.get("/gestao").text)
        self.assertEqual(self.client.get("/api/health").json()["version"], "2.0.0")

    def test_preflight_transparency_and_immutable_original(self):
        row, original = self.synthetic()
        info = self.client.get(f"/api/studio/assets/{row['id']}/preflight").json()
        self.assertTrue(info["has_transparency"])
        self.assertFalse(info["empty"])
        self.assertEqual(info["content_box"], [10, 10, 90, 50])
        self.assertEqual(
            self.client.get(f"/api/art/{row['id']}/original").content, original
        )
        thumb = self.client.get(f"/api/studio/assets/{row['id']}/thumbnail")
        self.assertEqual(thumb.status_code, 200)
        self.assertEqual(Image.open(io.BytesIO(thumb.content)).mode, "RGBA")

    def test_layout_preserves_ratio_trims_and_has_no_overlaps(self):
        a, _ = self.synthetic()
        data = self.request(
            a["id"],
            trim=True,
            margin_mm=2,
            gap_mm=1,
            items=[{"asset_id": a["id"], "width_mm": 20, "copies": 7}],
        )
        response = self.client.post("/api/studio/layout", json=data)
        self.assertEqual(response.status_code, 200, response.text)
        plan = response.json()
        self.assertEqual(plan["copies"], 7)
        self.assertEqual(plan["film_height_mm"], 47)
        for i, placement in enumerate(plan["placements"]):
            self.assertEqual(placement["content_box"], [10, 10, 90, 50])
            self.assertEqual(placement["height_mm"], 10)
            self.assertGreaterEqual(placement["x_mm"], 2)
            self.assertLessEqual(placement["x_mm"] + placement["width_mm"], 48.8 + 1e-6)
            for other in plan["placements"][i + 1 :]:
                self.assertTrue(
                    placement["x_mm"] + 20 <= other["x_mm"]
                    or other["x_mm"] + 20 <= placement["x_mm"]
                    or placement["y_mm"] + 10 <= other["y_mm"]
                    or other["y_mm"] + 10 <= placement["y_mm"]
                )

    def test_export_dimensions_alpha_white_mirror_dpi_and_hashes(self):
        row, _ = self.synthetic()
        run_id = self.render(self.request(row["id"]))
        response = self.client.get(f"/api/studio/runs/{run_id}/download")
        self.assertEqual(response.status_code, 200, response.text)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            rgb = Image.open(io.BytesIO(archive.read("cor_sRGB.png")))
            white = Image.open(io.BytesIO(archive.read("branco_W.tif")))
            self.assertEqual(rgb.size, (300, 90))
            self.assertEqual(white.size, rgb.size)
            self.assertEqual(rgb.mode, "RGBA")
            self.assertEqual(white.mode, "L")
            self.assertAlmostEqual(rgb.info["dpi"][0], 150, delta=0.1)
            self.assertAlmostEqual(white.info["dpi"][0], 150, delta=0.1)
            self.assertTrue(rgb.info.get("icc_profile"))
            # Source occupies the left half, then the entire sheet is mirrored.
            self.assertEqual(rgb.getpixel((30, 45))[3], 0)
            self.assertEqual(rgb.getpixel((270, 45))[3], 255)
            self.assertEqual(white.tobytes(), rgb.getchannel("A").tobytes())
            manifest = json.loads(archive.read("manifesto.json"))
            self.assertFalse(manifest["printer_ready"])
            self.assertFalse(manifest["halftoned"])
            self.assertEqual(manifest["orientation"], "espelhada")
            self.assertNotIn("cor_CMYK.tif", archive.namelist())
            for file in manifest["files"]:
                self.assertEqual(
                    file["sha256"],
                    hashlib.sha256(archive.read(file["name"])).hexdigest(),
                )
        self.assertFalse((EXPORT_DIR / f"{run_id}.partial").exists())

    def test_white_choke_coverage_and_zero_border(self):
        alpha = Image.new("L", (9, 9), 0)
        ImageDraw.Draw(alpha).rectangle((2, 2, 6, 6), fill=255)
        mask = white_mask(alpha, 254, 0.1, 50)  # one-pixel erosion
        self.assertEqual(mask.getbbox(), (3, 3, 6, 6))
        self.assertEqual(mask.getpixel((4, 4)), 128)
        opaque = white_mask(Image.new("L", (5, 5), 255), 254, 0.1, 100)
        self.assertEqual(opaque.getbbox(), (1, 1, 4, 4))
        self.assertIsNone(white_mask(alpha, 300, 0.1, 0).getbbox())

    def test_rejects_oversize_empty_overflow_and_nonfinite_values(self):
        row, _ = self.synthetic()
        empty, _ = self.upload(Image.new("RGBA", (10, 10), 0))
        cases = [
            self.request(row["id"], margin_mm=30),
            self.request(
                row["id"], items=[{"asset_id": row["id"], "width_mm": 100, "copies": 1}]
            ),
            self.request(empty["id"]),
            self.request(
                row["id"],
                items=[{"asset_id": row["id"], "width_mm": 40, "copies": 200}],
                dpi=600,
            ),
            self.request(
                row["id"],
                items=[
                    {"asset_id": row["id"], "width_mm": 10, "copies": 200},
                    {"asset_id": row["id"], "width_mm": 10, "copies": 1},
                ],
            ),
            self.request(row["id"], white_percent=101),
            self.request(row["id"], unexpected=True),
        ]
        for case in cases:
            with self.subTest(case=case):
                response = self.client.post("/api/studio/layout", json=case)
                self.assertEqual(response.status_code, 422, response.text)
        response = self.client.post(
            "/api/studio/layout",
            content=json.dumps(self.request(row["id"], gap_mm=float("nan"))),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_missing_or_non_cmyk_profile(self):
        bad = self.client.post(
            "/api/studio/profiles", files={"file": ("fake.icc", b"not an ICC")}
        )
        self.assertEqual(bad.status_code, 422)
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        self.assertEqual(
            self.client.post(
                "/api/studio/profiles", files={"file": ("srgb.icc", srgb)}
            ).status_code,
            422,
        )
        row, _ = self.synthetic()
        self.assertEqual(
            self.client.post(
                "/api/studio/layout", json=self.request(row["id"], profile_id="missing")
            ).status_code,
            404,
        )

    def test_cancel_does_not_publish_and_completed_cannot_cancel(self):
        row, _ = self.synthetic()
        response = self.client.post("/api/studio/runs", json=self.request(row["id"]))
        self.assertEqual(response.status_code, 201, response.text)
        run_id = response.json()["id"]
        self.assertEqual(
            self.client.post(f"/api/studio/runs/{run_id}/cancel").status_code, 200
        )
        render_run(run_id)
        self.assertFalse((EXPORT_DIR / f"{run_id}.zip").exists())
        self.assertEqual(
            self.client.get(f"/api/studio/runs/{run_id}/download").status_code, 409
        )
        complete = self.render(self.request(row["id"]))
        self.assertEqual(
            self.client.post(f"/api/studio/runs/{complete}/cancel").status_code, 409
        )

    @unittest.skipUnless(
        os.environ.get("FLUXO_TEST_CMYK_ICC"),
        "ICC CMYK externo não fornecido para esta validação opcional",
    )
    def test_cmyk_export_with_real_output_profile(self):
        profile = Path(os.environ["FLUXO_TEST_CMYK_ICC"]).read_bytes()
        response = self.client.post(
            "/api/studio/profiles", files={"file": ("perfil-teste.icc", profile)}
        )
        self.assertEqual(response.status_code, 201, response.text)
        profile_id = response.json()["id"]
        duplicate = self.client.post(
            "/api/studio/profiles", files={"file": ("mesmo-perfil.icc", profile)}
        )
        self.assertEqual(duplicate.json()["id"], profile_id)
        row, _ = self.synthetic()
        run_id = self.render(self.request(row["id"], profile_id=profile_id))
        with zipfile.ZipFile(EXPORT_DIR / f"{run_id}.zip") as archive:
            image = Image.open(io.BytesIO(archive.read("cor_CMYK.tif")))
            self.assertEqual(image.mode, "CMYK")
            self.assertEqual(image.size, (300, 90))
            self.assertEqual(image.getpixel((30, 45)), (0, 0, 0, 0))
            self.assertGreater(sum(image.getpixel((270, 45))), 0)
            self.assertEqual(image.info["icc_profile"], profile)
            self.assertAlmostEqual(image.info["dpi"][0], 150, delta=0.1)

    def test_worker_recovers_interrupted_job(self):
        with SessionLocal() as db:
            row = DtfRun(
                id=str(uuid.uuid4()),
                name="Interrupted",
                status="PROCESSANDO",
                request_json="{}",
            )
            db.add(row)
            db.commit()
            run_id = row.id
        worker = RasterWorker()
        worker.start()
        worker.stop()
        with SessionLocal() as db:
            row = db.get(DtfRun, run_id)
            self.assertEqual(row.status, "ERRO")
            self.assertIn("fechado", row.error)


if __name__ == "__main__":
    unittest.main()
