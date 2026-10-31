# Integrações e dependências do FORGE v0.7

A versão desktop não usa API do GitHub durante o funcionamento. Os projetos abaixo são dependências locais; o GitHub Actions compila o programa para Windows.

| Ferramenta | Repo | Empacotada no EXE | Observação |
|---|---|---|---|
| Pillow | https://github.com/python-pillow/Pillow | Sim | Crop, resize, DPI, fundo simples |
| VTracer | https://github.com/visioncortex/vtracer | Sim, na compilação | SVG, sem modelos externos |
| PyInstaller | https://github.com/pyinstaller/pyinstaller | Compilador, não runtime | Gera EXE |
| pywebview | https://github.com/r0x0r/pywebview | Sim | Janela WebView2 depende de runtime Windows |
| rembg | https://github.com/danielgatis/rembg | **Não** | Exige biblioteca/modelos externos |
| Real-ESRGAN NCNN | https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan | **Não** | Executável e pesos externos |
| ComfyUI | https://github.com/comfyanonymous/ComfyUI | **Removido** | Não usado |

A fila de impressão ainda é administrativa e **não** conversa com a controladora Hoson.
