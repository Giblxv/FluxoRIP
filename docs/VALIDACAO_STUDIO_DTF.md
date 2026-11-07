# Validação do Studio DTF 2.0

Data: 7 de novembro de 2026. Base: `research/autorizado-autorip-studio`, commit `d90cca7`. Ambiente local de validação: Linux, Python 3.12.14, Node 24 e Chromium. Banco e imagens sintéticos em diretórios temporários; nenhuma conexão a impressora.

## Implementação verificada

A tela inicial agora é o Studio DTF. A navegação se concentra em preparar filme, biblioteca, rasterizações, perfis ICC e pasta automática. A gestão antiga foi deslocada para `/gestao`; tabelas e APIs existentes foram preservadas. Nenhuma amostra de cliente, ICC de produção ou pacote raster foi adicionado ao Git.

O pipeline executa composição física, preservação de proporções, corte do alfa, interpolação Lanczos, espelhamento do filme inteiro, máscara branca com erosão e cobertura, conversão ICC opcional e exportação ZIP. Os rasters têm DPI e o PNG incorpora sRGB. A saída CMYK usa o perfil informado, com cobertura modulada pelo alfa. Máscaras W são imagens em cinza, não canais spot de dispositivo.

A fila registra progresso em etapas realmente concluídas. O cancelamento usa atualizações condicionais para não sobrescrever uma conclusão concorrente. Arquivos incompletos usam `.partial` e só são publicados após finalização; trabalhos interrompidos são identificados na próxima abertura. O monitor de pasta é desativado por padrão e exige configuração explícita.

## Prévias

[Interface desktop](previews/studio-desktop.png) · [Interface mobile](previews/studio-mobile.png). São capturas do programa funcionando com artes sintéticas.

## Resultados locais

| Verificação | Resultado |
| --- | --- |
| `python -m unittest discover -s tests -v`, com ICC de teste local | **50 testes aprovados** |
| Exportação CMYK real | Testada com `/usr/share/color/icc/ghostscript/default_cmyk.icc`; apenas perfil genérico para testar a transformação, não para recomendar cores de produção |
| Os mesmos testes sem ICC externo | O teste opcional de exportação CMYK é ignorado; os demais não dependem de perfis externos |
| `python tests/smoke_http.py` | API HTTP real aprovada; regressão das associações administrativas preservada |
| Dez scripts `web/test_*.mjs` | Aprovados; navegação, foco, movimento reduzido, contraste e ciclo de vida dos efeitos |
| `python tests/ui_studio.py` com Chromium instalado | Fluxo real aprovado, sem mocks de API e sem erros JS |
| Sintaxe Python e JavaScript; `git diff --check` | Aprovadas |
| CI em Ubuntu e Windows Server 2022 | Testes Python, smoke HTTP e dez regressões JS aprovados |
| Prévia EXE Windows x64 | Compilada por PyInstaller no GitHub Actions, com autoteste HTTP local aprovado e SHA-256 no artefato |

O teste de navegador importa duas artes, ajusta larguras e cópias, verifica a prévia, restaura o rascunho após recarregar, exporta e abre o ZIP, confere transparência, trata geometria inválida, processa uma imagem em pasta automática e comprova que a entrada permanece intacta. Também abre as cinco telas em 390 px de largura sem transbordamento horizontal e verifica movimento reduzido/contraste forçado. As capturas usam artes sintéticas.

As miniaturas e metadados têm caches limitados; o cálculo repetido de composição não mantém imagens de resolução completa na memória. Requisições de conferência são agrupadas na interface, e respostas antigas não substituem uma prévia mais recente.

## Pesquisa anterior, separada do produto

A descoberta completa de testes em `research/autorip-studio` executou 230 testes e encontrou dois erros de preparação de classes: `test_mask_equality_bounds` e `test_plane_bounds_audit` exigem `real_mask_periodicity.json`, que não existe no checkout público. Não foram fabricadas evidências para fazer esses testes passarem. O código dessa pesquisa não foi modificado. A suíte sintética selecionada pelo workflow existente foi executada separadamente: **103 testes aprovados**.

Dois testes antigos de motion tinham simulações de DOM desatualizadas: faltavam `querySelectorAll` e a resolução dos seletores dos elementos pressionados. Os harnesses foram corrigidos para representar o DOM usado por `motion.js`; o comportamento do script de animação foi mantido.

## Pendências e limites

- A compilação EXE e o autoteste foram feitos em Windows Server 2022 no GitHub Actions. Execução em Windows 10/11, janela WebView2 e teste físico de impressão continuam pendentes.
- Não há PRT homologado, retícula de dispositivo, canal spot W integrado, protocolo Hoson ou envio à máquina.
- Composição por prateleiras, sem rotação e sem garantia de solução ótima; limite de 40 MP e 30.000 px por lado na saída. Sem tiles/paginação automática do rolo.
- Um único worker/processo de servidor; não iniciar múltiplos Uvicorn workers.
- A prova de branco na interface representa o alfa. O TIFF exportado contém a cobertura e o recuo realmente calculados.
- A pasta automática considera estabilidade observada, não consegue provar que um programa externo concluiu a escrita. Use extensão temporária seguida de renomeação para cópias longas.
- O modo Central mantém as condições de rede do projeto anterior; uso externo continua exigindo a infraestrutura TLS/VPN já descrita na documentação.

## Reproduzir

Consulte os comandos em `README.md`, `requirements-test.txt` e `.github/workflows/dtf-studio-checks.yml`. O workflow novo valida backend em Linux/Windows e o fluxo de navegador em Linux. A primeira execução de CI também revelou uma resposta atrasada que recriava o formulário da pasta automática durante o preenchimento. O Studio agora aguarda a configuração inicial e preserva campos editados; o teste de navegador inclui uma leitura atrasada para prevenir essa regressão.
