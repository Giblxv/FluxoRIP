# AutoRIP Studio v0.76 — limites algébricos dos padrões ternários

## Objetivo e proveniência

Verificar se as três contagens agregadas de bytes diferentes (v0.71) permitem deduzir quantas posições dos PRTs têm três valores distintos (0%, 50%, 100%). **Não foi feita nova leitura dos PRTs nem do ICC nesta execução**; somente as contagens publicadas anteriormente foram reutilizadas. Nenhuma informação privada de pixel, perfil ICC ou PRT foi publicada.

A geometria **hipotética** v0.71: 48 bytes de cabeçalho, 12 grupos, 1456 linhas, stride 15176; carga útil de 265.155.072 bytes por amostra. Contagens de diferença anteriores: 0%×50% = 18.519.938; 50%×100% = 18.515.358; 0%×100% = 18.520.514.

## Resultado matemático

As contagens são compatíveis com múltiplas decomposições em cinco classes de igualdade. O número de posições com **três valores distintos** pode variar de **0 a 18.514.782**, em passos de 2, sem contrariar as três contagens agregadas. Assim, não é possível concluir a frequência real da classe `all_distinct` apenas pelas distâncias par a par. É necessário executar `ternary_transition.py` sobre as amostras verificadas para medi-la.

Exemplo extremo com 0 posições all-distinct: 237.377.167 all-equal; 9.257.967 (0=50); 9.257.391 (0=100); 9.262.547 (50=100). Outro extremo com 18.514.782 all-distinct: 246.634.558 all-equal; 576 (0=50); 0 (0=100); 5.156 (50=100). Ambos produzem as mesmas três distâncias agregadas. São decomposições matemáticas, não medições reais.

## Implementação

`pairwise_bounds.py` valida inteiros, capacidade e desigualdades de triângulo, calcula o intervalo exato e mostra dois exemplos extremos. É somente leitura e usa apenas a biblioteca padrão. `test_pairwise_bounds.py` executa 10 testes, incluindo enumeração exaustiva das possibilidades para duas posições com alfabeto de três valores.

Foram executados **20 testes** no total: 10 novos e 10 do módulo `ternary_transition.py` v0.75, usando a dependência `safe_json_output.py` recuperada do pacote v0.73. Todos passaram em Linux/Python. **Não é uma validação da suíte completa do projeto nem da plataforma Windows.**

## Próximos passos e limites

- Executar o analisador ternário com as três amostras reais verificadas por SHA-256 e confrontar os resultados com os limites algébricos.
- Avaliar a classe all-distinct por cada um dos 12 grupos candidatos, sem assumir que sejam canais físicos.
- Nenhuma conclusão sobre 2 bits, DeviceN/Spot_1, CMYKW, perfil ICC, fluxo FlexiPRINT ou capacidade de gerar PRT de produção decorre destes limites.
- Não executar binários proprietários, alterar licenças, enviar trabalhos ou controlar impressoras.
