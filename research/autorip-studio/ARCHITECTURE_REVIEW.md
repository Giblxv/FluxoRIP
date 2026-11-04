# Revisão arquitetural — AutoRIP Studio (2026-11-04)

## Evidências examinadas
- `AGENTS.md`, `CODEX_HANDOFF.md`, `README.md`, `requirements.txt` e `app/watcher.py` da branch main.
- Listagem de módulos `app/` e `tests/` do FluxoRIP.
- Código experimental `prt_readonly.py` e testes sintéticos publicados nesta branch.

**Limite:** não é uma auditoria integral de cada módulo, nem comprovação de funcionamento em Windows, FlexiPRINT, PrintExp ou equipamento real.

## Decisão: arquitetura separada
1. **Motor AutoRIP (núcleo futuro):** validação de entrada, normalização de cor, ICC, rasterização, geração de máscaras branco/verniz, parâmetros de resolução, geometria, cache e logs determinísticos. Cada fase deve ter contrato e testes próprios. Nenhuma fase de geração de arquivo de impressão está habilitada nesta etapa.
2. **Laboratório PRT (atual):** leitura estática, hashes, comparação de faixas e hipóteses de layout. Sem dependências de drivers ou bibliotecas proprietárias.
3. **FluxoRIP (orquestrador):** Kanban, pedidos, estações, scanner, UI, fila administrativa, histórico e monitoramento de pastas. Esses módulos não devem entrar no núcleo RIP; mantê-los no produto de gestão evita regressões e mantém o foco.
4. **Adaptadores futuros:** formatos de entrada/saída e integrações opcionais, sempre desativados até homologação e com evidências de compatibilidade.

## O que não faz sentido dentro do núcleo RIP
- Scanner Ethernet e controle de Hoson: infraestrutura/segurança operacional, não transformação de imagem.
- Kanban, clientes, pedidos, central LAN, autenticação: orquestração empresarial.
- Motion graphics, web UI e geração de instalador: interface e distribuição.
- Ferramentas de IA de criação de arte: editor separado e opcional.
- Reproduzir a interface PrintExp: PrintExp controla impressora; não é o RIP usado na investigação.
- Presumir 12 faixas = 12 tintas, ou 2 bits/pixel sem evidência de amostras reais.

## Critérios para avançar
- Corpus PRT com SHA-256 verificado e proveniência de cada parâmetro.
- Amostras de branco 0%, 50%, 100% com diferenças atribuídas experimentalmente.
- Testes de comparação sob row-major e plane-major; preferir evidência espacial, não apenas cabeçalho.
- Perfis ICC: registrar origem, espaço de cor, quantidade de canais e permissões; não inventar perfil CMYKW.
- Só iniciar pipeline de renderização depois de especificação e testes determinísticos, sem saída para impressora.

## Estado dos testes
Seis testes sintéticos foram adicionados ao GitHub, **mas não executados nesta operação**. Nenhum resultado de aprovação deve ser inferido da presença do arquivo de teste. Suíte histórica de 655 testes também não foi executada.

## Regras de publicação
Branch isolada; sem merge automático na main; não subir PRTs proprietários, credenciais, perfis comerciais ou dados de clientes. Relatórios devem distinguir observação, hipótese e resultado de teste.
