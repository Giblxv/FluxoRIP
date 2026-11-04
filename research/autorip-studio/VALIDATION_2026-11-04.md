# AutoRIP Studio — registro de validação e prioridades

Data: 2026-11-04

## Execução local confirmada
Foi reexecutada a suíte de testes do conjunto de arquivos **v0.64**, que já existia no ambiente local de trabalho, com:

```bash
cd /mnt/data/autoprip064-work
python -m unittest discover -p 'test_*.py' -v
```

Resultado: **33 testes; 0 falhas; OK**. Os módulos incluídos nessa suíte foram `layout_hypotheses.py`, `spatial_layout.py`, `slot_evidence.py` e `prt_diff.py` e seus respectivos testes. Os dados testados são sintéticos.

**Distinção obrigatória:** essa execução não valida automaticamente o `prt_readonly.py` publicado nesta branch, que ainda exige execução separada de seus seis testes. Não houve nova leitura de arquivos PRT reais, teste em Windows, geração de saída para impressora ou integração com Hoson.

## Próximas prioridades, por ordem
1. **Unificar os leitores:** confrontar o `prt_readonly.py` da branch com o leitor v0.64, preservar as validações mais rigorosas, corrigir divergências e executar testes de regressão.
2. **Corpus de evidências:** obter arquivos PRT de forma autorizada e registrar hash, origem, versão do FlexiPRINT, configurações e dimensão; manter bytes proprietários fora do GitHub público.
3. **Experimento de branco:** comparar 0%, 50% e 100% por diferença binária e por hipótese de layout; não inferir diretamente canal físico a partir de uma faixa.
4. **Contratos do pipeline RIP:** entrada PNG/TIFF, validação de dimensões/DPI, ICC e perfis de cor, máscaras de branco, rasterização e empacotamento de saída; cada fase testável isoladamente.
5. **Integração FluxoRIP:** somente interface administrativa para receber jobs e exibir estados verificáveis; nenhum controle físico sem homologação.

## Escopo negativo
Não migrar para o núcleo RIP módulos de Kanban, central LAN, scanner, controle de impressoras, editor criativo, motion ou instalador. Esses módulos pertencem à aplicação de gestão/distribuição e permanecem intocados.

## Estado de segurança
Somente análise estática. Não executar softwares proprietários, alterar firmware/licenças, enviar comandos às impressoras ou publicar amostras comerciais.
