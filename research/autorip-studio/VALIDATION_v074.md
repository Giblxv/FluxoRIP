# AutoRIP Studio v0.74 — segurança da CLI de periodicidade

## Problema reproduzido
A versão v0.73 corrigiu a exportação em `layout_concentration.py`, mas `mask_periodicity.py` ainda chamava `Path.write_text()` diretamente, podendo sobrescrever um destino preexistente ou hardlink para uma entrada PRT.

## Correção
`mask_periodicity.py` agora usa `write_new_json()` com criação exclusiva (`O_CREAT|O_EXCL`), não sobrescrevendo arquivos existentes. Foram criados quatro testes CLI com fixtures sintéticas: criação e segunda execução, hardlink, symlink, arquivo preexistente. Em todos os casos as três entradas permaneceram inalteradas.

## Validação
Nove testes passaram (5 do módulo de exportação + 4 de integração CLI) em Linux com Python. Não é uma execução da suíte completa de 110 testes, nem uma validação Windows. Não foram reabertos PRTs ou ICC proprietários nesta rodada. A análise de 12 faixas, a codificação 2-bit e o mapeamento físico de Spot_1/CMYKW permanecem hipóteses.

## Limites
A garantia de não sobrescrita vale para o arquivo final, mas a criação de diretórios pais ainda é permitida. Não garante proteção contra um adversário com controle concorrente do diretório de saída. O operador deve escolher diretório de resultados confiável. Nenhuma impressão, execução de binários proprietários ou merge em main foi realizada.
