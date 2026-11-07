"""Opt-in raster smoke for disposable build-test data, including frozen Pillow.

Only called with --autoteste and FORGE_DTF_RASTER_SMOKE=1. It creates synthetic
art/jobs in FORGE_DATA_DIR; CI explicitly supplies a temporary data directory.
"""

import io
import json
import time
import uuid
import zipfile
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw


def run_smoke(base):
    image = Image.new("RGBA", (150, 90), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, 60, 60), fill=(255, 0, 100, 255))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    boundary = "fluxo-" + uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="autoteste_sintetico.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
        + buffer.getvalue()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    upload = Request(
        base + "/api/art/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urlopen(upload, timeout=10) as response:
        asset_id = json.load(response)["id"]
    payload = {
        "name": "Autoteste DTF sintético",
        "items": [{"asset_id": asset_id, "width_mm": 40, "copies": 3, "rotation": 90}],
        "film_width_mm": 50.8,
        "max_page_length_mm": 50,
        "margin_mm": 2,
        "gap_mm": 5,
        "dpi": 150,
        "trim": False,
        "mirror": True,
        "white_percent": 50,
        "choke_mm": 0.15,
    }
    request = Request(
        base + "/api/studio/runs",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        run_id = json.load(response)["id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with urlopen(base + "/api/studio/runs", timeout=5) as response:
            run = next(item for item in json.load(response) if item["id"] == run_id)
        if run["status"] in ("ERRO", "CANCELADO"):
            raise RuntimeError(
                "Autoteste de rasterização falhou: " + str(run.get("error"))
            )
        if run["status"] == "CONCLUIDO":
            break
        time.sleep(0.1)
    else:
        raise TimeoutError("Autoteste DTF excedeu 30 segundos.")
    with urlopen(base + run["download_url"], timeout=10) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as package:
            manifest = json.loads(package.read("manifesto.json"))
            assert manifest["layout"]["page_count"] == 3, manifest["layout"][
                "page_count"
            ]
            assert manifest["printer_ready"] is False
            for index in range(1, 4):
                assert f"filme_{index:03d}/cor_sRGB.png" in package.namelist()
    with urlopen(
        f"{base}/api/studio/runs/{run_id}/proof?page=2&channel=white", timeout=10
    ) as response:
        with Image.open(io.BytesIO(response.read())) as proof:
            assert proof.mode == "L" and proof.getextrema()[1] == 128
    with urlopen(
        f"{base}/api/studio/runs/{run_id}/separation?page=2&channel=white", timeout=10
    ) as response:
        with Image.open(io.BytesIO(response.read())) as white:
            assert white.format == "TIFF" and white.mode == "L"
