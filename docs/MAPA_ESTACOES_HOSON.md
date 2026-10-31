# Fluxo RIP 1.5 — Mapa de estações e interfaces Hoson

## Objetivo

Vincular um equipamento DTF/DTF UV cadastrado a uma estação Windows e à porta de rede onde ele está conectado. O inventário centralizado evita confusão quando placas Hoson chinesas, em máquinas diferentes, compartilham o mesmo IP padrão.

## Como funciona

1. A estação executa um agente que envia informações de adaptadores Ethernet via `POST /api/stations/heartbeat`.
2. O operador cadastra a impressora com ID exclusivo, tecnologia e IP confirmado.
3. Na aba **Estações**, o operador escolhe uma estação e uma interface da lista. O vínculo é persistido em `printer_station_links`.
4. O painel mostra máquina, estação, porta, IP, comunicação recente do agente e alterações de porta.
5. A criação, alteração e remoção ficam registradas nos eventos administrativos.

## Segurança operacional

- Nenhum socket TCP é aberto pelo módulo de associação em direção à impressora; não envia comandos Hoson, firmware, limpeza, calibração ou trabalhos RIP.
- Estado **Vínculo registrado** significa apenas que o operador associou cadastros. Não significa que a impressora está online, pronta, calibrada ou respondendo ao PrintExp.
- Descobertas por ARP ou ping são indícios, não prova de identidade de uma placa; uma máquina pode não responder a ping.
- A identificação do adaptador é feita pelo índice reportado pelo Windows. Se uma interface for renumerada ou removida, o sistema solicita revisão do vínculo.
- O agente deve estar na rede administrativa confiável. A Central HTTP Basic sem TLS só deve ser usada em LAN isolada, conforme guia `CENTRAL_E_ESTACOES.md`.
- Não mude IP do Windows, PrintExp ou placa Hoson automaticamente.

## IPs repetidos

A mesma combinação IP+interface física não pode ser atribuída a duas impressoras diferentes, para evitar ambiguidades. O mesmo IP pode aparecer em interfaces Ethernet ou estações distintas, situação comum em redes independentes de controladoras Hoson.

## API

- `GET /api/printer-links` — lista vínculos, equipamentos ainda sem associação e alertas de interface/agente.
- `PUT /api/printer-links/{printer_id}` — associa ou altera; corpo `{"station_id":"st-...","interface_id":9}`.
- `DELETE /api/printer-links/{printer_id}` — remove a associação sem afetar o equipamento físico.

As rotas administrativas seguem a autenticação da Central no modo multiestações. O agente de estação usa token próprio somente para heartbeat.

## Compatibilidade e dados

Compatível com a base SQLite existente. `Base.metadata.create_all()` cria a tabela de vínculos na inicialização; o campo legado `Printer.workstation` permanece para exibição histórica. Dados são persistidos sob `%LOCALAPPDATA%\FORGE` no Windows (pasta antiga mantida para não perder os pedidos).

## Testes

- `python -m unittest discover -s tests -p 'test_printer_links.py' -v`
- `python tests/smoke_http.py` (requer FastAPI/Uvicorn; não executa scan de rede)
- `python tests/ui_smoke_offline.py` (opcional, requer Playwright + navegador Chromium; dados simulados)
- `python -m unittest discover -s tests -v` (suite completa, requer dependências em `requirements-build.txt`)

## Próxima evolução

Avaliar um *diagnóstico passivo* por estação que registre informações verificáveis sobre o processo PrintExp sem executar comandos, quando houver documentação do fabricante e consentimento do operador. A coleta nunca deve inferir status de impressão apenas a partir do IP.
