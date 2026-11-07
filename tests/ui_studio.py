"""Real Chromium workflow, isolated SQLite and synthetic artwork; no printers.

python tests/ui_studio.py
Optional: FLUXO_BROWSER_EXECUTABLE=/usr/bin/chromium
          FLUXO_UI_SCREENSHOTS=/absolute/path/to/screenshots
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def synthetic_art(path, title, color):
    im = Image.new("RGBA", (900, 1100))
    draw = ImageDraw.Draw(im)

    def font(size):
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except OSError:
            return ImageFont.load_default(size=size)

    draw.rounded_rectangle((90, 65, 810, 1010), radius=180, fill="#14171A")
    draw.arc((160, 110, 740, 690), 190, 350, fill=color, width=25)
    draw.arc((195, 145, 705, 655), 195, 345, fill="#FFD500", width=14)
    draw.ellipse((325, 230, 575, 480), fill=color)
    draw.ellipse((375, 245, 550, 420), fill="#FFD500")
    draw.line((230, 575, 675, 575), fill="white", width=10)
    draw.text((450, 620), title, anchor="mt", font=font(97), fill="white")
    draw.text((450, 750), "PRINT LAB", anchor="mt", font=font(40), fill=color)
    draw.text(
        (450, 878), "EST. 2026  /  BRASIL", anchor="mt", font=font(22), fill="white"
    )
    im.save(path, dpi=(300, 300))


def main():
    shots = Path(os.environ.get("FLUXO_UI_SCREENSHOTS", ROOT / "work" / "ui-studio"))
    shots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fluxorip-browser-") as temp:
        data = Path(temp)
        incoming = data / "incoming"
        incoming.mkdir()
        for title, color in [("FLUXO", "#00A6D6"), ("STUDIO", "#E5007D")]:
            synthetic_art(data / f"{title}.png", title, color)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {
            **os.environ,
            "FORGE_DATA_DIR": str(data / "runtime"),
            "FORGE_CENTRAL_MODE": "0",
        }
        with (data / "server.log").open("w+") as log:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            base = f"http://127.0.0.1:{port}"
            try:
                for _ in range(100):
                    try:
                        with urlopen(base + "/api/health", timeout=1):
                            break
                    except Exception:
                        if proc.poll() is not None:
                            log.seek(0)
                            raise RuntimeError(log.read())
                        time.sleep(0.1)
                else:
                    raise RuntimeError("API não iniciou")
                with sync_playwright() as p:
                    executable = os.environ.get("FLUXO_BROWSER_EXECUTABLE")
                    browser = p.chromium.launch(
                        **({"executable_path": executable} if executable else {})
                    )
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1100}, accept_downloads=True
                    )
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda exc: errors.append(str(exc)))
                    page.goto(base)
                    expect(page.locator("#connection-text")).to_have_text(
                        "Studio conectado"
                    )
                    expect(page.locator("#generate-button")).to_be_disabled()
                    page.locator("#file-input").set_input_files(
                        [str(data / "FLUXO.png"), str(data / "STUDIO.png")]
                    )
                    expect(page.locator(".selected-art")).to_have_count(2)
                    page.locator("[data-setting=dpi]").select_option("150")
                    page.locator("#copies-0").fill("2")
                    page.locator("#width-0").fill("140")
                    page.locator("#width-1").fill("180")
                    expect(page.locator("#generate-button")).to_be_enabled()
                    expect(page.locator(".film-item")).to_have_count(3)
                    assert not page.evaluate(
                        "document.documentElement.scrollWidth > innerWidth"
                    )
                    page.locator("#toast").evaluate(
                        '(el) => el.classList.remove("show")'
                    )
                    page.locator("#title").click()
                    page.screenshot(
                        path=str(shots / "studio-desktop.png"), full_page=True
                    )
                    # Keyboard/motion preference persists without breaking the draft.
                    page.locator("#motion-toggle").click()
                    expect(page.locator("html")).to_have_class("motion-off")
                    page.reload()
                    expect(page.locator("#copies-0")).to_have_value("2")
                    expect(page.locator("#generate-button")).to_be_enabled()
                    page.locator("#generate-button").click()
                    expect(page.locator(".status-tag.CONCLUIDO")).to_have_count(
                        1, timeout=30000
                    )
                    with page.expect_download() as download:
                        page.get_by_role("link", name="Baixar pacote ZIP").click()
                    with zipfile.ZipFile(download.value.path()) as package:
                        assert {
                            "cor_sRGB.png",
                            "branco_W.tif",
                            "manifesto.json",
                        } <= set(package.namelist())
                        manifest = json.loads(package.read("manifesto.json"))
                        assert manifest["layout"]["copies"] == 3
                        assert manifest["request"]["dpi"] == 150
                        assert manifest["printer_ready"] is False
                    page.screenshot(
                        path=str(shots / "rasterizacao-desktop.png"), full_page=True
                    )
                    page.locator("[data-page=library]").click()
                    expect(page.locator(".library-card")).to_have_count(2)
                    page.locator("#library-search").fill("FLUXO")
                    expect(page.locator(".library-card")).to_have_count(1)
                    page.locator(".library-preview").click()
                    expect(page.locator("#asset-dialog")).to_be_visible()
                    expect(page.locator("#preflight-result")).to_contain_text(
                        "Transparência detectada"
                    )
                    page.keyboard.press("Escape")
                    expect(page.locator("#asset-dialog")).not_to_be_visible()
                    page.locator("[data-page=studio]").click()
                    page.locator("#width-0").fill("2000")
                    expect(page.locator(".layout-error")).to_contain_text("excede")
                    expect(page.locator("#generate-button")).to_be_disabled()
                    page.locator("#width-0").fill("140")
                    expect(page.locator("#generate-button")).to_be_enabled()
                    # Real hot-folder ingestion, untouched source, no fake API responses.
                    held_requests = []

                    def hold_settings(route):
                        if route.request.method == "GET":
                            held_requests.append(route)
                        else:
                            route.continue_()

                    page.route("**/api/studio/hotfolder", hold_settings)
                    page.locator("[data-page=automation]").click()
                    # A delayed initial read cannot replace fields during typing.
                    expect(page.locator("#hotfolder-form")).to_have_count(0)
                    page.wait_for_timeout(100)
                    assert held_requests, "Config request was not intercepted"
                    for route in held_requests:
                        route.continue_()
                    page.unroute("**/api/studio/hotfolder", hold_settings)
                    page.locator("#hotfolder-path").fill(str(incoming))
                    page.locator("#hotfolder-width").fill("60")
                    page.get_by_role(
                        "button", name="Usar parâmetros atuais e ativar"
                    ).click()
                    expect(page.locator(".automation-panel .status-tag")).to_have_text(
                        "ATIVADA"
                    )
                    synthetic_art(incoming / "automatico.png", "AUTO", "#00A6D6")
                    original = (incoming / "automatico.png").read_bytes()
                    expect(page.locator(".receipt")).to_have_count(1, timeout=20000)
                    assert (incoming / "automatico.png").read_bytes() == original
                    page.get_by_role("button", name="Desativar", exact=True).click()
                    expect(page.locator(".automation-panel .status-tag")).to_have_text(
                        "DESATIVADA"
                    )
                    for page_id in (
                        "studio",
                        "library",
                        "runs",
                        "profiles",
                        "automation",
                    ):
                        page.set_viewport_size({"width": 390, "height": 844})
                        page.locator(f"[data-page={page_id}]").click()
                        assert not page.evaluate(
                            "document.documentElement.scrollWidth > innerWidth"
                        ), page_id
                        if page_id == "studio":
                            page.locator("#toast").evaluate(
                                '(el) => el.classList.remove("show")'
                            )
                            page.screenshot(
                                path=str(shots / "studio-mobile.png"), full_page=True
                            )
                    page.emulate_media(reduced_motion="reduce")
                    expect(page.locator("html")).to_have_class("motion-off")
                    expect(page.locator("#motion-toggle")).to_be_disabled()
                    page.emulate_media(forced_colors="active")
                    assert not errors, errors
                    context.close()
                    browser.close()
                print(
                    "PASS: importação, composição, exportação ZIP, rascunho, preflight, pasta automática, 5 telas mobile, movimento reduzido; sem erros JS."
                )
                print("Screenshots:", shots)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


if __name__ == "__main__":
    main()
