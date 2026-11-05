# AutoRIP Studio — Validação de pesquisa v0.84

**Data:** 5 de novembro de 2026  
**Branch:** `research/autorizado-autorip-studio` (nenhuma alteração na `main`)

## Escopo entregue

1. `prospective_periodicity.py`: análise somente leitura para um **conjunto novo e independente de 12 PRTs**, com hashes verificados pelo `controlled_capture.py`.
2. `test_prospective_periodicity.py`: **17 testes sintéticos** que verificam a invariância de parâmetros, teste negativo com janela deslocada, repetibilidade da exportação, geometria incompatível, cabeçalhos divergentes, integridade SHA-256, preservação da origem, tamanhos de bloco e não sobrescrita de resultados.
3. `PROTOCOL_v084_PTBR.md`: protocolo de replicação prospectiva, definindo antecipadamente entradas e critérios de interpretação.

## Hipótese congelada

| Parâmetro | Valor | Motivo |
|---|---:|---|
| Período candidato | 17.472 bytes | Investigação histórica v0.82 |
| Janela de alterações | 1.456 bytes | Investigação histórica v0.82 |
| Posição inicial fixa | 5.821 | Uma entre **quatro fases empatadas** |
| Fração geométrica da janela | 1/12 (8,3333%) | Referência descritiva, **não p-valor** |

Em nenhum momento o módulo reotimiza período ou fase com base nas artes novas. Se a geometria não for comparável com a hipótese pré-registrada, informa `not_evaluable`, sem extrapolar.

## Verificação cruzada em CI

Execução verificada: [GitHub Actions 42090965420](https://github.com/Giblxv/FluxoRIP/actions/runs/42090965420), commit `7f668c55ce37c779213d5a35c5793dc8c529f401`.

| Plataforma | Testes Python | Falhas | Smoke PowerShell |
|---|---:|---:|---|
| Windows | **93/93** | 0 | **Aprovado** |
| Ubuntu | **93/93** | 0 | Não aplicável |

**Total: 186 execuções de testes Python aprovadas**, além do smoke test Windows. Todos executados em artefatos sintéticos, sem PRTs proprietários no repositório.

## Saída esperada quando novas amostras estiverem disponíveis

O relatório por arte traz:
- Confirmação de 12 arquivos verificados por hash do manifesto do operador;
- Contagem de bytes diferentes nas comparações 0×50, 50×100, 0×100 e 50%×50% (exportação repetida);
- Contagens dentro e fora da **mesma janela fixa**;
- Indicação clara de `repeatability_confounded`, `no_level_difference_observed`, `not_evaluable` ou `descriptive_only_no_ink_inference`.

Não é emitido qualquer mapa de canais de tinta, arquivo de impressão, máscara proprietária, bytes PRT ou perfil ICC.

## Limitação central

As **12 amostras novas ainda não foram coletadas/fornecidas**. Portanto, esta versão verifica o procedimento e sua implementação, **não comprova a hipótese de periodicidade em artes independentes**. A concentração em uma janela não revela por si só formato de pixel, camada Spot, dose de tinta branca, mapeamento ICC ou compatibilidade com Hoson.

O RIP das amostras é o **FlexiPRINT MiniTX F-PRINT Edition**. O **PrintExp** é o controlador, não o RIP.

## Próximo passo

Depois de gerar as três artes e 12 exportações com parâmetros controlados, preencher `plano-preenchido.json` (script `fill_capture_manifest.ps1`), executar o validador `controlled_capture.py` e, finalmente, rodar:

~~~powershell
py -3.11 prospective_periodicity.py --manifest "C:\AutoRIP-Piloto\plano-preenchido.json" --directory "C:\AutoRIP-Piloto\amostras" --output "C:\AutoRIP-Piloto\replicacao-v084.json"
~~~

O arquivo de destino precisa ser novo. Nenhum PRT é modificado, nenhuma impressora é acionada e nenhum código da branch `main` é alterado.
