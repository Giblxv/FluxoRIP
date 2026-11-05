# AutoRIP Studio v0.78 — igualdade de máscaras restringe limites ternários

## Resultado

Com base nos hashes de máscaras de diferenças previamente calculados sobre as amostras TESTER1.PRT (0%), TESTER1_1.PRT (50%) e TESTER1_0.PRT (100%), os grupos candidatos contíguos 1–10 possuem máscaras **0×50 e 0×100 idênticas** (SHA-256 iguais, para cada grupo). Para qualquer posição, se as duas máscaras são iguais, uma alteração 50×100 só pode ocorrer onde ambas indicam alteração; nessas posições, os três bytes são distintos. Portanto, a quantidade de posições com três valores distintos nesses dez grupos é exatamente a contagem 50×100: **18.369.527**.

Os grupos 0 e 11 não têm a mesma igualdade de máscaras, e seus limites agregados são [0, 81.352] e [1, 63.903], respectivamente. Assim, o intervalo global se estreita de [4, 18.514.782] na v0.77 para **[18.369.528, 18.514.782]** posições. Esse intervalo ainda não é uma contagem exata global.

A igualdade de hashes SHA-256 é tratada como igualdade das máscaras sob a hipótese usual de resistência a colisões. A geometria de 12 grupos contíguos permanece **hipotética**, não um mapeamento de canais físicos ou cabeças.

## Validação

- Cinco testes novos aprovados, incluindo contagens reais derivadas, incerteza das bordas e rejeição de evidências inconsistentes.
- Entradas: `real_mask_periodicity.json` derivado e os hashes de proveniência registrados. **Não houve nova leitura dos PRTs ou do ICC nesta execução**.
- Saída JSON gerada com `write_new_json`, que rejeita destinos existentes.
- Sem execução de programas proprietários, geração de PRT de produção, operação de impressoras ou publicação de dados PRT/ICC brutos.

## Pendências

Ler novamente os três PRTs originais com verificação SHA-256 para calcular a classificação ternária exata nas bordas; investigar separadamente 2 bits, ICC, DeviceN/Spot_1 e CMYKW, sem inferir equivalência a partir de periodicidade.