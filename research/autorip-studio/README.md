# AutoRIP Studio — pesquisa isolada

Este diretório contém a trilha de pesquisa **experimental e somente leitura** do AutoRIP Studio, separada do produto FluxoRIP. Esta ramificação não deve ser mesclada automaticamente na main.

## Escopo permitido
- Leitura estática de arquivos PRT, BSFX, XTFX e metadados do FlexiPRINT 22 F-PRINT Edition / PrintExp.
- Verificação de assinatura candidata `0x5555`, geometria candidata `48 + linhas × 12 × stride`, comparação por faixa, perfis CMYKW, SHA-256 e testes reproduzíveis.
- Arquivos de amostra originais sempre imutáveis; artefatos derivados em diretórios separados.
- Toda hipótese deve ser rotulada como tal até validação em amostras reais.

## Proibições
- Não executar binários proprietários ou instaladores de terceiros.
- Não alterar licenças, drivers, firmware ou configurações das máquinas.
- Não emitir comandos de impressora nem gerar PRT de produção.
- Não publicar amostras proprietárias, dados de clientes ou credenciais neste repositório público.

## Estado e proveniência
Relatórios históricos da conversa mencionam v0.59–v0.64 e testes sintéticos; **não foram importados nem revalidados nesta operação**. Antes de afirmar resultados, verificar bytes, hashes, logs e executar testes no ambiente corrente. Não confundir coerência de JSON anterior com nova leitura binária do PRT.

## Integração futura
O FluxoRIP é a camada de gestão; o AutoRIP Studio permanece uma pesquisa separada. Qualquer integração operacional exige homologação, revisão de segurança e testes supervisionados.

## Próximas ações
1. Recuperar e verificar fontes/artefatos anteriores por SHA-256.
2. Executar suíte sintética de regressão e publicar resultados reproduzíveis.
3. Analisar PRT real em modo somente leitura, sem publicar seus bytes.
4. Comparar amostras de branco 0%, 50%, 100% e investigar mapeamento CMYKW.
5. Abrir PR para revisão; não fazer merge automático.
