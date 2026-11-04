# AutoRIP Studio v0.68 — validação local

Data: 2026-11-04

Foi desenvolvido localmente um inventário de perfis ICC/ICM somente leitura (`icc_manifest.py`) e cinco testes (`test_icc_manifest.py`). A suíte local de v0.68 executou **51 testes sem falhas** (`python -m unittest discover -p 'test_*.py' -v`).

O inventário identifica perfis por SHA-256, agrupa hashes duplicados, registra erros individualmente, limita contagem e marca symlinks de arquivos como não processados. Os testes usam perfis sintéticos; **não há evidência de validação de perfis reais, CMYKW, PRT reais ou integração física**. Código v0.68 permanece no pacote local, não sincronizado nesta branch.

Próximas prioridades: revisar symlinks de diretório, comparar PRT reais 0/50/100% com proveniência, e integrar os módulos testados à branch isolada. Sem execução de binários proprietários ou controle de impressoras.