# AutoRIP Studio — Validação v0.83 / coleta independente de PRT

**Data:** 5 de novembro de 2026. **Branch:** `research/autorizado-autorip-studio`.

## Implementação

- `controlled_capture.py`: ferramenta de linha de comando para gerar o modelo JSON de captura e verificar **12 amostras PRT** de **3 artes independentes**, cada uma com branco declarado 0%, 50%, 100%, mais uma exportação independente repetida a 50%.
- `test_controlled_capture.py`: 24 casos sintéticos, cobrindo segurança de nomes, integridade, arquivos trocados, hashes divergentes, aliases de inode, leitura limitada do manifesto, duplicação de condições, repetibilidade e prevenção de sobrescrita.
- `PROTOCOL_v083_PTBR.md`: protocolo para operação no Windows, documentação de parâmetros mantidos constantes e hashes SHA-256 obtidos de forma separada.
- `autorip-research-tests.yml`: CI atualizado para incluir a nova suíte no Windows e Ubuntu.

## CI e correção de teste

A primeira execução da nova suíte apresentou 1 falha em cada plataforma porque o teste de adulteração substituía o conteúdo por **outro tamanho**; o validador, corretamente, interrompia primeiro pela divergência de tamanho. O teste foi corrigido para modificar apenas **um byte**, preservando o tamanho, para alcançar especificamente a validação do SHA-256.

Execução verificada: [GitHub Actions 42085264242](https://github.com/Giblxv/FluxoRIP/actions/runs/42085264242), commit `81cd850533f4a75fb2b96cbed2c9c23ac22fae92`.

- **Windows:** 76/76 testes, 0 falhas, 0 ignorados (2,657 s de testes).
- **Ubuntu:** 76/76 testes, 0 falhas, 0 ignorados (1,323 s de testes).
- **Total:** 152 execuções aprovadas em duas plataformas.

## Etapas faltantes

As novas artes e os 12 PRTs ainda **não foram entregues ou gerados**. Logo, nesta versão somente o mecanismo de coleta, o protocolo e os testes sintéticos foram validados. Não foi feita nova inferência sobre codificação de pixels, canais de tinta ou geração de PRT funcional.

O validador confere bytes com hashes **fornecidos pelo operador**. Ele não atesta automaticamente se o perfil ICC, DPI, tamanho ou outros parâmetros do RIP realmente ficaram constantes; essas variáveis devem ser registradas externamente. A comparação dos resultados dos 12 arquivos contra o período candidato de 17.472 bytes é uma etapa **posterior** à coleta íntegra.

Nenhum PRT ou perfil ICC proprietário foi enviado ao repositório. Não houve acionamento de impressoras nem alteração na branch `main`.
