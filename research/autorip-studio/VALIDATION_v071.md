# AutoRIP Studio v0.71 — investigação de distribuição por layout

Experimento read-only nos três PRTs fornecidos pelo operador, sem execução de FlexiPRINT/PrintExp ou comandos para impressora. **Nenhum PRT, ICC, BMP ou dado proprietário bruto foi publicado.**

## Proveniência e geometria

- 0% TESTER1.PRT: `75ef4acb3b7c2dbbce28dc112187ca19b250f2728842eae0c5c7c38b41d8d8ec`
- 50% TESTER1_1.PRT: `7f5d2036cf9a107a4600f21b3e54a9238850d73861c4de22d8871f3497d68773`
- 100% TESTER1_0.PRT: `c143d3bac295c352ec63060ae20f0210c6dbf200e4f18fbee471e96d54c46136`

Assinatura candidata `0x5555`, cabeçalhos idênticos e geometria observada `48 + 1456 × 12 × 15176 = 265155120` bytes.

## Resultados

Comparações binárias (quantidades de bytes diferentes): 0%×50% = **18.519.938**; 50%×100% = **18.515.358**; 0%×100% = **18.520.514**.

Atribuição dos 18.520.514 bytes distintos da comparação 0%×100% a 12 agrupamentos **candidatos**:

- `row_major` (linha/faixa/stride): `[1540725,1544430,1543335,1543216,1545837,1539273,1545853,1540749,1544455,1545891,1540799,1545951]`.
- `plane_major` (faixa/linha/stride): `[81656,1836592,1838045,1838045,1836592,1838045,1838045,1836592,1838045,1838045,1836592,64220]`.
- `byte_interleaved` (offset relativo módulo 12): `[1542350,1542312,1542296,1542306,1555090,1542304,1542296,1542306,1542348,1542314,1542290,1542302]`.

A distribuição `plane_major` apresenta grupos centrais com mais alterações que as bordas, mas **não comprova** que o arquivo use esse layout. Nenhum grupo pode ser identificado como CMYKW ou Spot_1 apenas com estes dados.

## Testes

Foram aprovados **7 testes sintéticos novos** e a suíte integrada de **94 testes** após adicionar o módulo novo à base v0.70. Relatório local e JSON detalhado preservados fora do repositório público.

## Segurança e limites

O analisador é somente leitura, verifica SHA-256 em fluxo sequencial, igualdade de cabeçalhos, geometria candidata e metadados estáveis antes/depois da leitura. Isso não cria snapshot imutável nem comprova representação de pixels, 2-bit, física de impressão ou a ligação entre branco e Spot_1. Sem emissão de PRT de produção. Os arquivos de entrada nunca foram modificados.
