"""Physical layouts and final rasters; all inputs are synthetic and local."""

import io
import json
import os
import tempfile
import threading
import unittest
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import delete

_TEST_DATA = tempfile.TemporaryDirectory(prefix="fluxo-refinements-")
os.environ.setdefault("FORGE_DATA_DIR", _TEST_DATA.name)

from app.art_editor import ArtRevision, import_art_bytes
from app.db import SessionLocal, init_db
from app.dtf_studio import EXPORT_DIR, DtfRun, render_run
from app.main import app


class DtfRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def upload(self, image, name="refinamento.png"):
        out = io.BytesIO()
        image.save(out, "PNG")
        response = self.client.post(
            "/api/art/upload", files={"file": (name, out.getvalue(), "image/png")}
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def source(self):
        im = Image.new("RGBA", (150, 90), 0)
        draw = ImageDraw.Draw(im)
        draw.rectangle((2, 3, 38, 19), fill=(255, 0, 0, 255))
        draw.rectangle((80, 20, 147, 87), fill=(0, 166, 214, 128))
        return self.upload(im)

    def request(self, asset_id, **overrides):
        result = {
            "items": [{"asset_id": asset_id, "width_mm": 25.4, "copies": 1}],
            "film_width_mm": 50.8,
            "dpi": 150,
            "mirror": False,
            "margin_mm": 0,
            "gap_mm": 0,
            "trim": False,
            "choke_mm": 0,
            "white_percent": 100,
        }
        result.update(overrides)
        return result

    def render(self, data):
        with SessionLocal() as db:
            row = DtfRun(
                id=str(uuid.uuid4()),
                name="Refinamento",
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
        return run_id

    def test_rotation_physical_bounds_and_thumbnail(self):
        row = self.source()
        data = self.request(
            row["id"],
            items=[
                {"asset_id": row["id"], "width_mm": 25.4, "copies": 1, "rotation": 90}
            ],
        )
        response = self.client.post("/api/studio/layout", json=data)
        self.assertEqual(response.status_code, 200, response.text)
        p = response.json()["placements"][0]
        self.assertAlmostEqual(p["width_mm"], 15.24)
        self.assertAlmostEqual(p["height_mm"], 25.4)
        self.assertEqual(p["preview_box"], [0, 0, 90, 150])
        thumb = self.client.get(f"/api/studio/assets/{row['id']}/thumbnail?rotation=90")
        self.assertEqual(
            thumb.status_code, 200, thumb.text if thumb.status_code != 200 else ""
        )
        im = Image.open(io.BytesIO(thumb.content))
        self.assertEqual(im.size, (90, 150))
        self.assertEqual(im.getpixel((79, 10)), (255, 0, 0, 255))
        self.assertEqual(
            self.client.get(
                f"/api/studio/assets/{row['id']}/thumbnail?rotation=13"
            ).status_code,
            422,
        )

    def test_rotation_mirror_and_final_white_proof_match_export(self):
        row = self.source()
        data = self.request(
            row["id"],
            mirror=True,
            choke_mm=0.15,
            white_percent=50,
            items=[
                {"asset_id": row["id"], "width_mm": 25.4, "copies": 1, "rotation": 90}
            ],
        )
        run_id = self.render(data)
        with zipfile.ZipFile(EXPORT_DIR / f"{run_id}.zip") as package:
            color = Image.open(io.BytesIO(package.read("cor_sRGB.png")))
            white = Image.open(io.BytesIO(package.read("branco_W.tif")))
            self.assertEqual(color.size, (300, 150))
            self.assertEqual(color.getpixel((220, 10)), (255, 0, 0, 255))
            self.assertEqual(white.getpixel((220, 10)), 128)
            self.assertEqual(color.getpixel((250, 100))[3], 128)
            self.assertEqual(white.getpixel((250, 100)), 64)
            self.assertEqual(white.getpixel((30, 50)), 0)
            proof = self.client.get(f"/api/studio/runs/{run_id}/proof?channel=white")
            self.assertEqual(
                proof.status_code, 200, proof.text if proof.status_code != 200 else ""
            )
            self.assertEqual(
                Image.open(io.BytesIO(proof.content)).tobytes(), white.tobytes()
            )
            download = self.client.get(
                f"/api/studio/runs/{run_id}/separation?channel=white"
            )
            self.assertEqual(download.content, package.read("branco_W.tif"))
            self.assertEqual(
                self.client.get(
                    f"/api/studio/runs/{run_id}/separation?channel=cmyk"
                ).status_code,
                404,
            )

    def test_multi_page_export_never_splits_art_and_keeps_all_copies(self):
        row = self.source()
        data = self.request(
            row["id"],
            max_page_length_mm=50,
            margin_mm=2,
            gap_mm=5,
            items=[{"asset_id": row["id"], "width_mm": 40, "copies": 4}],
        )
        plan = self.client.post("/api/studio/layout", json=data).json()
        self.assertEqual(plan["page_count"], 4)
        self.assertEqual(plan["copies"], 4)
        self.assertAlmostEqual(plan["film_height_mm"], 112)
        for page in plan["pages"]:
            self.assertEqual(page["copies"], 1)
            self.assertLessEqual(page["height_px"] * page["width_px"], 40_000_000)
            p = page["placements"][0]
            self.assertEqual((p["x_mm"], p["y_mm"]), (2, 2))
            self.assertEqual(p["page_number"], page["number"])
        run_id = self.render(data)
        with zipfile.ZipFile(EXPORT_DIR / f"{run_id}.zip") as package:
            manifest = json.loads(package.read("manifesto.json"))
            self.assertEqual(len(manifest["pages"]), 4)
            for number in range(1, 5):
                prefix = f"filme_{number:03d}/"
                self.assertIn(prefix + "cor_sRGB.png", package.namelist())
                self.assertIn(prefix + "branco_W.tif", package.namelist())
                color = self.client.get(
                    f"/api/studio/runs/{run_id}/separation?page={number}&channel=color"
                )
                self.assertEqual(color.content, package.read(prefix + "cor_sRGB.png"))
            self.assertEqual(
                self.client.get(f"/api/studio/runs/{run_id}/proof?page=5").status_code,
                404,
            )
            self.assertEqual(
                self.client.get(
                    f"/api/studio/runs/{run_id}/separation?page=5"
                ).status_code,
                404,
            )

    def test_per_page_and_total_memory_limits(self):
        row = self.source()
        data = self.request(
            row["id"], items=[{"asset_id": row["id"], "width_mm": 10, "copies": 9}]
        )
        with patch("app.dtf_studio.MAX_SHEET_PIXELS", 20000):
            response = self.client.post("/api/studio/layout", json=data)
            self.assertEqual(response.status_code, 200, response.text)
            plan = response.json()
            self.assertGreater(plan["page_count"], 1)
            for page in plan["pages"]:
                self.assertLessEqual(page["width_px"] * page["height_px"], 20000)
            with patch("app.dtf_studio.MAX_RUN_PIXELS", 20000):
                response = self.client.post("/api/studio/layout", json=data)
                self.assertEqual(response.status_code, 422)
        invalid = self.request(
            row["id"],
            items=[{"asset_id": row["id"], "width_mm": 40, "copies": 200}],
            max_page_length_mm=50,
            gap_mm=3,
        )
        self.assertEqual(
            self.client.post("/api/studio/layout", json=invalid).status_code, 422
        )

    def test_library_search_beyond_500_rows_with_unicode_and_literal_wildcards(self):
        row = self.source()
        prefix = uuid.uuid4().hex[:10]
        with SessionLocal() as db:
            original = db.get(ArtRevision, row["id"])
            entries = []
            for index in range(510):
                entries.append(
                    ArtRevision(
                        id=f"{prefix}-{index}",
                        root_id=original.root_id,
                        original_name=f"{prefix} lote {index}.png",
                        operation="importada",
                        file_format="PNG",
                        width=150,
                        height=90,
                        dpi_x=300,
                        dpi_y=300,
                        saved_path=original.saved_path,
                        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                    )
                )
            entries[-1].original_name = f"{prefix} Árvore São 100%_DTF.png"
            db.add_all(entries)
            db.commit()
        try:
            response = self.client.get(
                "/api/studio/library", params={"q": prefix, "offset": 500, "limit": 10}
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["total"], 510)
            self.assertEqual(len(response.json()["items"]), 10)
            self.assertFalse(response.json()["has_more"])
            found = self.client.get(
                "/api/studio/library", params={"q": f"{prefix} arvore sao"}
            )
            self.assertEqual(found.json()["total"], 1)
            self.assertEqual(
                self.client.get("/api/studio/library", params={"q": "100%_DTF"}).json()[
                    "total"
                ],
                1,
            )
            self.assertEqual(
                self.client.get(f"/api/studio/assets/{prefix}-509").status_code, 200
            )
        finally:
            with SessionLocal() as db:
                db.execute(delete(ArtRevision).where(ArtRevision.id.startswith(prefix)))
                db.commit()

    def test_previous_single_page_packages_still_have_proofs(self):
        row = self.source()
        run_id = self.render(self.request(row["id"]))
        path = EXPORT_DIR / f"{run_id}.zip"
        with zipfile.ZipFile(path) as package:
            kept = {
                name: package.read(name)
                for name in package.namelist()
                if not name.startswith("previas/")
            }
        with zipfile.ZipFile(path, "w") as package:
            for name, data in kept.items():
                package.writestr(name, data)
        self.assertEqual(
            self.client.get(
                f"/api/studio/runs/{run_id}/proof?channel=white"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/api/studio/runs/{run_id}/proof?page=2").status_code, 404
        )

    def test_cancel_between_pages_removes_incomplete_package(self):
        from app.dtf_studio import checkpoint

        row = self.source()
        data = self.request(
            row["id"],
            max_page_length_mm=50,
            margin_mm=2,
            gap_mm=5,
            items=[{"asset_id": row["id"], "width_mm": 40, "copies": 4}],
        )
        with SessionLocal() as db:
            run = DtfRun(
                id=str(uuid.uuid4()),
                name="Cancelar páginas",
                status="PROCESSANDO",
                request_json=json.dumps(data),
            )
            db.add(run)
            db.commit()
            run_id = run.id

        def cancel_second(identifier, progress, phase):
            if phase.startswith("Página 2/"):
                with SessionLocal() as db:
                    run = db.get(DtfRun, identifier)
                    run.status = "CANCELADO"
                    db.commit()
            return checkpoint(identifier, progress, phase)

        with patch("app.dtf_studio.checkpoint", side_effect=cancel_second):
            render_run(run_id)
        self.assertFalse((EXPORT_DIR / f"{run_id}.zip").exists())
        self.assertFalse((EXPORT_DIR / f"{run_id}.partial").exists())
        self.assertEqual(
            self.client.get(f"/api/studio/runs/{run_id}/proof").status_code, 409
        )

    def test_runs_use_compact_results_and_conditional_polling(self):
        row = self.source()
        run_id = self.render(self.request(row["id"]))
        response = self.client.get("/api/studio/runs")
        result = next(run for run in response.json() if run["id"] == run_id)["result"]
        self.assertNotIn("placements", result)
        self.assertNotIn("placements", result["pages"][0])
        self.assertIn("width_px", result["pages"][0])
        etag = response.headers["ETag"]
        unchanged = self.client.get("/api/studio/runs", headers={"If-None-Match": etag})
        self.assertEqual(unchanged.status_code, 304)
        self.assertFalse(unchanged.content)
        with SessionLocal() as db:
            pending = DtfRun(
                id=str(uuid.uuid4()),
                name="Fila nova",
                request_json=json.dumps(self.request(row["id"])),
            )
            db.add(pending)
            db.commit()
            pending_id = pending.id
        changed = self.client.get("/api/studio/runs", headers={"If-None-Match": etag})
        self.assertEqual(changed.status_code, 200)
        self.assertNotEqual(changed.headers["ETag"], etag)
        self.client.post(f"/api/studio/runs/{pending_id}/cancel")

    def test_history_pagination_finds_runs_older_than_first_hundred(self):
        prefix = uuid.uuid4().hex
        with SessionLocal() as db:
            for index in range(105):
                db.add(
                    DtfRun(
                        id=str(uuid.uuid4()),
                        name=f"{prefix} Histórico São {index:03d}",
                        status="CONCLUIDO",
                        request_json='{"items":[]}',
                    )
                )
            db.commit()
        try:
            response = self.client.get(
                "/api/studio/runs", params={"q": prefix, "offset": 100, "limit": 20}
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers["X-Total-Count"], "105")
            self.assertEqual(len(response.json()), 5)
            normalized = self.client.get(
                "/api/studio/runs", params={"q": f"{prefix} historico sao 000"}
            )
            self.assertEqual(normalized.headers["X-Total-Count"], "1")
            self.assertEqual(
                normalized.json()[0]["name"], f"{prefix} Histórico São 000"
            )
            by_id = self.client.get(
                "/api/studio/runs", params={"q": normalized.json()[0]["id"][:12]}
            )
            self.assertEqual(by_id.json()[0]["id"], normalized.json()[0]["id"])
        finally:
            with SessionLocal() as db:
                db.execute(delete(DtfRun).where(DtfRun.name.startswith(prefix)))
                db.commit()

    def test_history_etags_are_specific_to_query_and_page(self):
        q = uuid.uuid4().hex
        first = self.client.get(
            "/api/studio/runs", params={"q": q, "offset": 0, "limit": 20}
        )
        tag = first.headers["ETag"]
        same = self.client.get(
            "/api/studio/runs",
            params={"q": q, "offset": 0, "limit": 20},
            headers={"If-None-Match": tag},
        )
        self.assertEqual(same.status_code, 304)
        different = self.client.get(
            "/api/studio/runs",
            params={"q": q, "offset": 20, "limit": 20},
            headers={"If-None-Match": tag},
        )
        self.assertEqual(different.status_code, 200)
        self.assertEqual(different.json(), [])
        self.assertNotEqual(different.headers["ETag"], tag)
        self.assertIn("X-Active-Count", different.headers)

    def test_multi_frame_input_is_not_silently_reduced_to_first_page(self):
        buffer = io.BytesIO()
        first = Image.new("RGB", (16, 16), "red")
        second = Image.new("RGB", (16, 16), "blue")
        first.save(buffer, "TIFF", save_all=True, append_images=[second])
        response = self.client.post(
            "/api/art/upload",
            files={"file": ("duas_paginas.tif", buffer.getvalue(), "image/tiff")},
        )
        self.assertEqual(response.status_code, 415, response.text)
        self.assertIn("várias páginas", response.json()["detail"])

    def test_upload_processing_does_not_block_health(self):
        image = io.BytesIO()
        Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(image, "PNG")
        entered = threading.Event()
        release = threading.Event()

        def delayed(*args, **kwargs):
            entered.set()
            release.wait(5)
            return import_art_bytes(*args, **kwargs)

        with TestClient(app) as client, ThreadPoolExecutor(max_workers=2) as pool:
            with patch("app.art_editor.import_art_bytes", side_effect=delayed):
                upload = pool.submit(
                    lambda: client.post(
                        "/api/art/upload",
                        files={"file": ("lenta.png", image.getvalue(), "image/png")},
                    )
                )
                try:
                    self.assertTrue(entered.wait(2))
                    health = pool.submit(lambda: client.get("/api/health"))
                    self.assertEqual(health.result(timeout=1).status_code, 200)
                finally:
                    release.set()
                self.assertEqual(upload.result(timeout=5).status_code, 201)


if __name__ == "__main__":
    unittest.main()
