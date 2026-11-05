# AutoRIP Studio v0.75 — transições ternárias entre 0%, 50% e 100%

Data: 2026-11-05 (America/Sao_Paulo). Escopo: pesquisa **somente leitura** e testes sintéticos.

## Novo método

`ternary_transition.py` classifica cada offset de byte das três entradas em cinco classes mutuamente exclusivas:

- `all_equal`: A=B=C;
- `zero_equals_fifty`: A=B≠C;
- `zero_equals_hundred`: A=C≠B;
- `fifty_equals_hundred`: B=C≠A;
- `all_distinct`: A≠B, A≠C e B≠C.

A saída inclui totais por uma das 12 faixas **candidatas** de organização contígua, totais globais, SHA-256 de cada entrada e contagens de diferenças par-a-par reconstruídas algebricamente. A ferramenta não produz imagem, PRT, dados de pixels, amostras brutas ou saída para impressora. A escrita JSON usa `safe_json_output.write_new_json` (criação exclusiva, sem sobrescrever destino existente).

## Evidência disponível da análise real anterior

Os resultados derivados da v0.72 indicam as contagens de bytes diferentes:

| Comparação | Bytes diferentes |
| --- | ---: |
| 0% × 50% | 18.519.938 |
| 50% × 100% | 18.515.358 |
| 0% × 100% | 18.520.514 |

Esses totais são referências históricas para validação cruzada em uma futura leitura real com o novo método. **Não foram recalculados nesta rodada**: os PRTs proprietários não estavam disponíveis no ambiente local. Os cinco totais de classes reais, portanto, permanecem desconhecidos.

## Testes

Dez testes novos passaram com fixtures sintéticas: classificação de cinco classes, consistência de contagens de pares, invariância ao tamanho de bloco, integridade SHA-256 e imutabilidade, incompatibilidade de cabeçalho/geometria, rejeição de alias hardlink, symlink, chunk inválido, ausência de rótulo e assinatura inválida. A suíte completa do repositório e o Windows **não** foram testados nesta rodada.

## Interpretação e limites

As três comparações par-a-par **não determinam unicamente** os cinco totais de igualdade: é preciso comparar os três valores no mesmo offset. A análise ternária poderá diferenciar transições 0→50→100 que mudam de valor sem alterar a máscara de diferenças 0→100. Nenhuma igualdade de byte identifica fisicamente Spot_1, CMYKW, 2-bit, canal branco ou o perfil ICC. O layout em 12 faixas permanece hipótese. `stat` + SHA-256 detectam mudanças observáveis, não fornecem snapshot transacional contra alteração concorrente adversarial.

## Próximos passos

1. Quando os três PRTs forem disponibilizados nesta execução, confirmar seus SHA-256 antes de calcular as classes reais.
2. Conferir se os totais par-a-par reconstruídos coincidem exatamente com os três números da v0.72; rejeitar divergências.
3. Verificar distribuição das cinco classes em cada faixa e periodicidade candidata, sem extrapolar para canais físicos.
4. Inspecionar separadamente metadados do ICC, sem publicar o arquivo proprietário.

Sem execução de software proprietário, sem alteração de impressoras, sem merge e sem publicação de PRT/ICC.