# HISTORICO_CONVERSA.md — Linha do tempo de requisitos e mudanças

**Objetivo:** transferir ao Codex o conteúdo útil do histórico de trabalho do Fluxo RIP. Este arquivo é um relato cronológico, NÃO um dump literal das mensagens do ChatGPT.

## Fase 1 — definição do projeto
1. Usuário pediu especialização em RIP/PrintExp e em quadros de produção como Notion/Trello. Decidiu construir simultaneamente gestão gráfica e integração com PrintExp.
2. Informou: Windows 11; DTF e DTF UV; PrintExp; sistema próprio (não Trello/Notion) e automação máxima. Arquitetura proposta: React (visão inicial), backend FastAPI/Python, SQLite, monitor de pastas, integração Hoson de forma incremental. A implementação concreta evoluiu para UI HTML/JS em `web/`.
3. Confirmou >5 impressoras, Ethernet, controladoras Hoson, fabricantes chineses genéricos como Funsun; versão do PrintExp e software RIP específico desconhecidos; sem screenshots disponíveis. Decisão: adaptador passivo até validação do protocolo.

## Fase 2 — MVP e UI operacional
4. v0.1/v0.2: API para impressoras, pedidos, estados, eventos, watcher de arquivos; configuração por `config.json`, riscos de estado de impressão manual/documentado.
5. Relatou `No module named uvicorn`; orientação para usar `.venv` correta, instalar requirements e acessar `/docs`.
6. Relatou falha ao compilar PyYAML; instrução de evitar extras Uvicorn não essenciais. Relatou 404 em `/docs%2A%2A`, corrigido link literal `/docs`.
7. Pediu aparência inspirada no PrintExp e abas **Projetos**, **Fila de impressão**, **Histórico de impressão**. v0.3: console técnico, tabelas, itens e controle administrativo.

## Fase 3 — Editor de Arte e IA descartada
8. Pediu estudo de repositórios GitHub que permitissem crop, resize sem perda aparente, tamanho/DPI, vetorização e fundo simples. v0.4: Pillow, VTracer, rembg, Real-ESRGAN opcionais; art_storage e revisões. Observação: DPI é metadado e interpolação/IA não recuperam dados originais perfeitamente.
9. Pediu geração de arte grátis por prompt; v0.5 testou módulo ComfyUI local. Usuário não conseguiu instalar ComfyUI; solicitou remoção explícita. v0.6 retirou ComfyUI e manteve editor.
10. Pediu **executável único**; v0.7 adaptou launcher PyInstaller/pywebview, dados persistentes fora do exe em `%LOCALAPPDATA%\FORGE`. Compilação final precisa Windows.

## Fase 4 — PrintExp e microanimações
11. Pediu seção Impressões com funções inspiradas no PrintExp. Informou acesso autorizado a telas avançadas; NÃO armazenar a credencial em arquivos. v0.8 incluiu Trabalhos, Configurações, Calibração, Manutenção, Avançado e Logs, composição/perfis/registros manuais, sem comando físico.
12. Pediu motion em tudo selecionável. v0.9 adicionou microinterações, MOTION ON/OFF, CSS transitions e `prefers-reduced-motion`.
13. Enviou screenshot evidenciando **duplicação da navegação** dentro de Impressões. v0.9.1 tornou segunda linha contextual, com ações específicas por seção.

## Fase 5 — rede Hoson, compatibilidade e multiestações
14. Informou sub-rede `192.168.127.X`, configuração PC de exemplo 192.168.127.100/24 e impressoras frequentemente .10/.1 (não universal). Pediu scanner de IPs em cada entrada/saída Ethernet para listar impressoras. v1.0 adicionou scanner ICMP/ARP por NIC, separação resultados por interface e `/24` máximo, cadastro manual.
15. Pediu suporte Windows 10 + 11. v1.1 adicionou diagnóstico Windows, fallback navegador e compilação Windows via GitHub Actions.
16. Autorizou continuar. v1.2 adicionou Central multiestações, agente e aba Estações; HTTP Basic apenas para LAN isolada (melhoria TLS pendente).
17. Compartilhou traceback de importação de testes: `starlette.testclient` exigia `httpx2`. v1.2.1 atualizou dependências de build, botão de correção e scripts.
18. Pediu instalação simplificada. v1.3 criou assistente primeira abertura Uso local/Central/Estação e `INSTALAR_E_ABRIR.bat`.

## Fase 6 — identidade Fluxo RIP
19. Enviou `Fluxo RIP – Identidade visual.html` e `Fluxo RIP – Motion graphics.html` e pediu integração completa com troca de nome.
20. v1.4 renomeou marca para **Fluxo RIP**; `FluxoRIP.exe`; logotipo CMY, cores, fontes, animações, assets SVG/ICO e guias. Mantém dados em `%LOCALAPPDATA%\FORGE` por compatibilidade. Historicamente foram reportados 31 testes aprovados e prévia Chromium, mas build real e hardware não comprovados nesta sessão de transferência.

## Pedido atual
Usuário quer "passar toda essa conversa pro Codex". Os arquivos `CODEX_HANDOFF.md`, `AGENTS.md`, este histórico e o código-fonte v1.4 foram agrupados para que o Codex entenda decisões e comece pelo estado atual. Para importar o transcript integral, usar a interface ChatGPT/Codex se oferecer a opção de adicionar chat existente.
