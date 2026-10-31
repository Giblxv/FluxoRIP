# FORGE v0.6 — ComfyUI removido

O módulo de geração de imagens por prompt do ComfyUI foi removido do FORGE.

**Eliminado:** `app/image_generation.py`, rotas `/api/generate*`,
`web/ai_generator.js`, painel "Gerar arte com IA", dependências e documentos
específicos do ComfyUI.

**Mantido:** Projetos, Fila de impressão, Histórico, Impressoras,
Arquivos e Editor de Arte (importar, cortar, redimensionar, DPI,
remover fundo simples, vetorizar com VTracer, remover fundo com rembg,
ampliar com Real-ESRGAN quando opcionais instalados).

## Atualizar a versão v0.5

1. Pare o FORGE antigo com Ctrl+C.
2. Faça cópias de segurança de `production.db` e `art_storage/`.
3. Extraia este ZIP em uma **nova pasta**, por exemplo `C:\FORGE_v06`.
4. Copie `production.db` e `art_storage/` da pasta antiga para essa nova pasta.
5. Execute `INSTALAR.bat` e depois `INICIAR.bat`.
6. Abra `http://127.0.0.1:8000` e use Ctrl+F5 se aparecer uma interface em cache.

## O que não é removido automaticamente

- ComfyUI instalado separadamente no Windows (fora do FORGE).
- Imagens que já foram criadas e salvas como revisões.
- Tabela antiga de histórico de geração dentro do SQLite, se já existia.

Nada disso é necessário para iniciar o FORGE. Não exclua `production.db`
para tentar desinstalar o ComfyUI: ali estão seus pedidos e histórico.
