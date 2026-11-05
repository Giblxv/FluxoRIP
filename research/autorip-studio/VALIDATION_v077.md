# AutoRIP Studio v0.77 — auditoria dos limites ternários por faixa

**Escopo:** somente leitura de um JSON derivado de análise anterior. Nesta rodada **não** foram abertos os três PRTs originais, o perfil ICC nem aplicativos proprietários. Não há identificação de canais físicos, `Spot_1`, CMYKW ou formato de 2 bits.

## Descoberta verificável

A v0.76, utilizando apenas as contagens globais, estabelecia o limite inferior de **0** posições com três valores distintos (0%, 50%, 100%) e limite superior de **18.514.782**. A v0.77 usa adicionalmente as contagens por cada uma das 12 faixas candidatas publicadas no derivado `real_mask_periodicity.json` da v0.72.

O número de posições com os três bytes distintos deve ser **ímpar** nas faixas candidatas **2, 8, 10 e 11** (índices começando em zero). Em cada uma dessas faixas, portanto, há no mínimo uma posição com três valores diferentes. Somando os limites individuais, o limite inferior fica **4**, enquanto o superior permanece **18.514.782**. Isso é uma inferência matemática das contagens por faixa, **não** uma nova medição dos arquivos proprietários.

A divisão em faixas contíguas é uma hipótese de organização do arquivo. O argumento de paridade é válido para as partições de posições usadas no JSON derivado, sem estabelecer que representem canais de tinta. As máscaras de diferenças não provam a representação 2-bit.

## Proveniência e limites

Os hashes SHA-256 dos três PRTs são comparados aos valores **registrados anteriormente** (0%, 50%, 100%). Eles não foram recalculados a partir dos originais nesta execução. O analisador rejeita JSON com contagens incompatíveis, total divergente, assinatura de esquema incorreta ou hashes diferentes dos esperados.

## Testes executados

- **10 testes** do novo auditor: aprovados.
- **30 testes** combinados do novo auditor, analisador ternário e limites globais: aprovados.
- **110 testes** da suíte integrada de referência v0.72/v0.73 extraída dos pacotes anteriores: aprovados.
- Os números **não** devem ser somados como testes exclusivos; as suítes se sobrepõem.

## Próxima etapa

Executar `ternary_transition.py` diretamente sobre as três amostras originais depois de confirmar novamente os SHA-256. Comparar as cinco classes reais por faixa com estes limites, antes de inferir canais físicos ou criar qualquer RIP de produção.

Arquivos de saída são criados exclusivamente por `safe_json_output.write_new_json()` e não sobrescrevem arquivos existentes. A branch `main` não deve ser modificada.
