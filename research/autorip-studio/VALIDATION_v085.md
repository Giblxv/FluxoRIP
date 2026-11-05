# AutoRIP Studio — validação v0.85: interpretação conservadora e identidade de amostras

**Data:** 05/11/2026. **Branch experimental:** `research/autorizado-autorip-studio`. Sem mudanças na `main`.

## 1. Revisão dos critérios de classificação da v0.84

A revisão do código revelou dois casos que poderiam induzir interpretação incorreta:

- **Extremos iguais não implicam ausência de mudança:** se os dados dos arquivos declarados 0% e 100% forem idênticos, mas o arquivo declarado 50% for diferente, o novo estado `endpoints_equal_intermediate_differs` registra explicitamente esse padrão. O estado `no_level_difference_observed` agora exige **zero diferenças nos três pares**: 0×50, 50×100 e 0×100.
- **Rerip diferente com geometria inadequada:** uma alteração no cabeçalho ou na geometria pode impedir a comparação modular (`not_evaluable`). Mesmo assim, os campos `white_50_reexport_byte_identical` e `repeatability_confounded` são sempre incluídos no resultado individual de cada arte, após a verificação do conjunto de 12 amostras por SHA-256. Uma exportação 50% diferente permanece **expressamente registrada**.

As classes continuam **descritivas**, não medem porcentagem física de tinta, passagem de cabeçote ou equivalência de impressão. Um resultado `not_evaluable` continua sendo inconclusivo sobre a hipótese periódica; o campo de repetibilidade é uma observação independente dessa classificação.

## 2. Validação reforçada do plano de coleta

`controlled_capture.py` agora exige identificadores com tipos exatos: arte e nível como strings, repetição como inteiro (por exemplo, `true` não é aceito como `1` no JSON). Cada arquivo PRT deve usar o nome canônico definido pelo próprio modelo:

`art_a_white_0_r1.PRT`, `art_a_white_50_r1.PRT`, `art_a_white_50_r2.PRT`, `art_a_white_100_r1.PRT` — e o mesmo padrão para `art_b` e `art_c`.

A correspondência entre o nome do PRT e a condição declarada é checada **antes da comparação**. Isso ajuda a detectar trocas acidentais de amostras, mas não prova que o operador selecionou efetivamente o nível de branco pretendido no FlexiPRINT.

## 3. Testes acrescentados

- 6 testes sintéticos para extremos idênticos/intermediário diferente, alterações do cabeçalho do rerip, geometria incompatível com rerip diferente e consistência dos sinais de repetibilidade.
- 4 testes sintéticos para tipos incorretos de repetição, troca dos nomes das amostras no manifesto e tolerância de maiúsculas/minúsculas no nome canônico.
- Os testes são adicionados à suíte já executada pelo GitHub Actions, tanto no Windows quanto no Ubuntu.

## 4. Limitações

Ainda **não existem novas 12 amostras independentes** disponíveis nesta fase. Nenhum resultado da hipótese prospectiva foi considerado comprovado com dados reais adicionais. As amostras TESTER1 históricas permanecem como base de definição do período 17.472, janela 1.456 e fase 5.821 — esta última **não é única** entre as alternativas empatadas.

As verificações são somente leitura; não existe geração de PRT para impressão, execução do RIP comercial, envio ao PrintExp ou controle de impressora Hoson. Os arquivos proprietários originais e a branch `main` permanecem intocados.

## 5. Próxima atividade

Gerar três artes independentes e 12 PRTs controlados conforme `PROTOCOL_v083_PTBR.md`, registrar hashes externos usando `fill_capture_manifest.ps1` e verificar o conjunto por `controlled_capture.py` antes de executar `prospective_periodicity.py`. Reportar separadamente a estabilidade de rerip, problemas de geometria e concentrações na janela congelada.
