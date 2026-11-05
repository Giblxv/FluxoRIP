# AutoRIP Studio v0.69 — validação reprodutível

Rodada: 2026-11-04. Execução local: Python 3.13.5 em Linux; nenhum teste Windows ou com hardware.

## Cinco prioridades trabalhadas

1. Segurança ICC: inventário usa os.walk com followlinks=False, pula links de diretórios, não abre arquivos linkados, rejeita raiz symlink e impõe limite de perfis. Risco residual: TOCTOU em árvore mutável por terceiros.
2. Repositório: 20 arquivos Python (9 módulos, 11 arquivos de teste) foram sincronizados para esta branch experimental; a correspondência com as fontes locais testadas foi conferida pelos hashes de blob do Git para cada arquivo. Main não foi alterada.
3. PRT: leitura de assinatura candidata 0x5555, cabeçalho de 48 bytes, geometria candidata rows*slots*stride e SHA-256. Exemplo relatado anteriormente: 48 + 960*12*5125 = 59040048 bytes, conferido apenas aritmeticamente. Comparador calcula diferenças por slot sob row-major e plane-major. Não há amostras PRT reais disponíveis nesta rodada.
4. DeviceN/CMYKW: duas configurações textuais reais da pasta Google Drive FlexPRINT/Spot Colors (2), 202 bytes cada, possuem SHA-256 igual: 17f726edb32b5f1348f4f30cc16afeae7405d9ce46d5687ffd4494849df83512. Declararam 4 nomes CMYK e Spot_1 a Spot_8. Não prova ordem de bytes, branco ou mapeamento físico. Nenhum ICC real foi validado.
5. Testes: 75 testes sintéticos aprovados localmente, zero falhas. O log local correspondente tem SHA-256 44decacb244a3620dc0da6b2d4482acfa476223320f0312cdd22d68ba3730b19. Reproduzir com python -m unittest discover -p 'test_*.py' -v.

## Evidências e restrições

- O patch ZIP local de v0.69 possui SHA-256 20a10be81a200b3b61b88a5852441c4b6d3c5a38e9186a86cd2a4894350951d5. As fontes e testes individuais também estão nesta branch.
- O PRT histórico não foi reaberto; o SHA-256 histórico dele não foi confirmado nesta rodada.
- Os arquivos de Drive foram lidos como texto estático, sem execução, alteração ou publicação de conteúdo bruto.
- Não houve execução de software proprietário, manipulação de licenças, comunicação com impressoras ou geração de PRTs de produção.
- A compatibilidade com FlexiPRINT 22 / PrintExp e o mapeamento CMYKW permanecem em investigação.

## Próximas evidências necessárias

- Três PRTs reais da mesma arte com branco 0%, 50% e 100% (trilha SHA-256 e metadados).
- Perfis ICC reais da impressora e seus parâmetros de origem.
- Execução de testes em Windows 10/11 e avaliação de riscos TOCTOU com diretórios de terceiros.
