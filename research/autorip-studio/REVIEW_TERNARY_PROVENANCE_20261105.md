# AutoRIP Studio — auditoria de integridade da análise ternária (2026-11-05)

## Escopo e evidências

Revisão estática dos módulos publicados na branch experimental: `ternary_transition.py`, `mask_equality_bounds.py`, `plane_bounds_audit.py` e `safe_json_output.py`. **Nesta rodada não foram reabertos os três PRTs nem o ICC, e não foram executados testes Python.** Não atribuir novas contagens aos originais.

## Constatação técnica: ausência de verificação de identidade esperada no scanner ternário

`ternary_transition.analyze()` calcula SHA-256 dos três arquivos e inclui os valores no JSON de saída, mas **não exige** que coincidam com os três SHA-256 de referência antes de aceitar as contagens. A checagem de cabeçalho, geometria, inodes distintos e tamanho igual não prova que os três arquivos sejam as amostras 0%, 50%, 100% da campanha original. É possível produzir um relatório internamente coerente com arquivos distintos porém trocados ou pertencentes a outro experimento. Esse é um risco de **atribuição/proveniência**, não evidência de corrupção dos dados atuais.

O auditor `plane_bounds_audit.audit()` já contém uma política de proveniência que pode ser reutilizada: 
- white_0: `75ef4acb3b7c2dbbce28dc112187ca19b250f2728842eae0c5c7c38b41d8d8ec`
- white_50: `7f5d2036cf9a107a4600f21b3e54a9238850d73861c4de22d8871f3497d68773`
- white_100: `c143d3bac295c352ec63060ae20f0210c6dbf200e4f18fbee471e96d54c46136`

Esses valores são **registros de referência do repositório**, não hashes recalculados nesta execução.

## Correção proposta para implementação após testes

Adicionar ao scanner ternário um parâmetro explícito de hashes esperados por rótulo, validado ao fim da leitura e **antes** de exportar qualquer resultado. No fluxo da campanha original, usar os três hashes conhecidos como requisito; para ensaios sintéticos, permitir um manifesto de teste independente e explícito. Não substituir a verificação por simples igualdade de tamanho/cabeçalho. Rejeitar erro de hash, permutação de rótulos e qualquer mudança de arquivo durante o processamento.

Testes de regressão mínimos: (1) três amostras sintéticas corretas com hashes conhecidos; (2) um byte alterado em qualquer entrada; (3) troca dos rótulos 50% e 100%; (4) três arquivos com cabeçalho e geometria idênticos, mas hashes inesperados; (5) ausência de arquivo de saída quando a verificação falha; (6) reprodutibilidade entre tamanhos de blocos distintos. A implementação deve continuar estritamente somente leitura para PRTs e sem geração de dados de impressão.

## Interpretação matemática que permanece válida

A igualdade das máscaras binárias `0_vs_50` e `0_vs_100` em um grupo implica que o número de posições com **três bytes distintos** nesse grupo é exatamente o número de diferenças `50_vs_100`. Não implica identidade de canais, pixels, cobertura de branco, codificação de 2 bits ou equivalência entre `Spot_1` e CMYKW. O limite reportado na v0.78 ([18.369.528, 18.514.782] posições) é **condicional à autenticidade e consistência da evidência derivada**.

## Limitações

Auditoria estática sem execução de testes nesta rodada. Nenhuma alteração em `main`, nenhum merge, nenhuma publicação de PRT/ICC, nenhuma operação de impressora. **A correção proposta não foi integrada ao código porque ainda não foi testada.**
