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
| `python -m unittest discover -s tests -v`, com ICC de teste local | **63 testes aprovados** |
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
- Composição por prateleiras, com rotação manual em passos de 90° e sem garantia de solução ótima. Paginação automática entre artes: até 40 MP e 30.000 px por lado por página, 50 páginas/200 MP no total. Uma arte não é dividida entre páginas. Sem tiles de uma imagem única.
- Um único worker/processo de servidor; não iniciar múltiplos Uvicorn workers.
- Na composição, a visualização Alfa representa a transparência. A conferência de separações usa provas reduzidas dos rasters finais, com cobertura e recuo do branco aplicados. Não é uma simulação de cor física.
- A pasta automática considera estabilidade observada, não consegue provar que um programa externo concluiu a escrita. Use extensão temporária seguida de renomeação para cópias longas.
- O modo Central mantém as condições de rede do projeto anterior; uso externo continua exigindo a infraestrutura TLS/VPN já descrita na documentação.

## Reproduzir

Consulte os comandos em `README.md`, `requirements-test.txt` e `.github/workflows/dtf-studio-checks.yml`. O workflow novo valida backend em Linux/Windows e o fluxo de navegador em Linux. A primeira execução de CI da entrega inicial também revelou uma resposta atrasada que recriava o formulário da pasta automática durante o preenchimento. O Studio agora aguarda a configuração inicial e preserva campos editados; o teste de navegador inclui uma leitura atrasada para prevenir essa regressão.

## Rodada de refinamento adicional

- Filmes longos são divididos em páginas inteiras, com navegação na composição e no diálogo de separações. O manifesto v2 mantém a posição de todas as cópias e identifica os arquivos de cada página; pacotes antigos de uma página continuam disponíveis.
- Rotação, medidas físicas, alfa e espelhamento foram verificados em pixels assimétricos conhecidos, incluindo cobertura de branco de 50%. Provas e downloads individuais foram comparados aos bytes dos rasters exportados.
- A biblioteca busca em todo o banco, com paginação, normalização de acentos e tratamento literal de `%`/`_`. O teste cria mais de 500 revisões sintéticas e encontra uma arte fora do lote inicial. O rascunho recupera referências fora da primeira página.
- A fila usa respostas compactas e ETag/HTTP 304 quando o estado não muda, evitando retransmitir posições de todas as artes em cada atualização.
- Importação pesada roda fora do ciclo HTTP; um teste mantém uma importação aguardando e comprova que `/api/health` responde durante o processamento. Entradas animadas ou TIFFs com várias páginas são rejeitados, preservando a necessidade de tratar todas as páginas.
- A pasta automática mostra os 30 registros mais recentes e o estado atual do trabalho; falhas de acesso à pasta aparecem e desaparecem sem recriar o formulário em edição.
- Cancelamento entre páginas remove o ZIP parcial. A migração por cópia preserva também `dtf_profiles` e `dtf_exports`, mantendo os originais. Nenhuma coluna/tabela existente foi alterada por esta rodada.
- O teste de navegador cobre busca paginada, resposta de inspeção atrasada, indisponibilidade temporária da pasta, recuperação de conexão, rotação, exportação multipágina, provas finais, navegação voltar/avançar e largura mobile.
- O autoteste raster opcional do EXE usa dados temporários e verifica três páginas, máscara branca e TIFF no aplicativo empacotado. A compilação aguarda os testes de backend e navegador.

As fontes Archivo e Public Sans são empacotadas localmente com licenças OFL. O teste de navegador bloqueia HTTPS externo e verifica que o Studio não tenta carregar recursos externos; as fontes e a interface continuam disponíveis na rede local.

O histórico de rasterizações também é paginado e pesquisável por nome ou ID. Os testes criam 105 trabalhos sintéticos e recuperam registros fora dos primeiros 100; o contador de trabalhos ativos é global, independente do filtro/página. ETags incluem os parâmetros de consulta para evitar respostas vazias incorretamente reutilizadas entre páginas.
