# Scanner de rede Hoson — FORGE v1.0

## Objetivo

Identificar interfaces Ethernet e **dispositivos observáveis** nas redes IPv4 ligadas às estações PrintExp, sem alterar parâmetros de impressoras ou do Windows.

## Referências técnicas

- Manual PrintExp Hoson: https://polus-print.ru/software/files/dtf-textile-printer/Component%20Manuals/PrintExp%20Printer%20Control%20%26%20Alignment%20Software%20Instruction.pdf
- Documentação `Get-NetIPConfiguration`: https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netipconfiguration
- Documentação `Get-NetNeighbor`: https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netneighbor

No manual Hoson há o exemplo de endereço **192.168.127.111 para o computador**, mas isso não determina o IP de todos os equipamentos. A faixa informada pelo usuário é `192.168.127.0/24`, e o exemplo `192.168.127.100` pode servir para um PC **somente se estiver livre** e for o correto para aquela estação. A máscara equivalente a `/24` é `255.255.255.0`.

**Para ligação dedicada PC-impressora, não configure um gateway padrão sem necessidade.** Um gateway indevido pode comprometer o acesso à internet/outros serviços. O FORGE não muda nenhuma configuração de rede.

## Modos da interface

**Porta selecionada**: selecione o adaptador Ethernet. O FORGE verifica se o adaptador está `Up` e se possui IPv4 na sub-rede /24 indicada. Testa até 254 IPs e consulta as entradas ARP desse adaptador.

**Todas as portas Hoson**: verifica os adaptadores conectados com endereço em `192.168.127.0/24`. Cada observação preserva nome e índice da interface. Adaptações que usam outras faixas devem ser examinadas selecionando a interface e digitando sua rede /24.

### Evidências mostradas

- `Respondeu ICMP`: um host respondeu ao ping.
- `Detectado via ARP`: o cache do Windows contém vizinho com MAC e estado de vizinhança recente.
- `Tipo: não identificado`: **não é prova de que o dispositivo seja uma Hoson**.
- IP, MAC e adaptador são informações de inventário, não dados de impressão.

O Windows pode manter dados ARP desatualizados e algumas controladoras não respondem ICMP. O scanner **não garante encontrar todos os dispositivos**. IP duplicado em duas placas ligadas à mesma sub-rede pode causar ambiguidade de roteamento; use estações dedicadas e confirme no PrintExp.

## Segurança do scanner

- Escopo restrito a redes IPv4 privadas `/24` diretamente ligadas à interface selecionada.
- Modo automático restrito às interfaces configuradas em `192.168.127.x`.
- No máximo 12 pings paralelos por interface, duração por tentativa controlada.
- No máximo duas interfaces verificadas simultaneamente.
- **Sem TCP na porta 9100**, sem comandos PrintExp, sem acesso a firmware, sem ajustes de rede, sem reinicialização e sem descoberta remota por broadcast.
- Rodar apenas em computadores e redes sob sua administração.

## Se a busca não encontrar impressoras

1. Confirme no Windows se o adaptador selecionado exibe estado `Up`.
2. Verifique se o cabo está na porta correta (algumas estações têm várias Ethernet).
3. Consulte no PrintExp o IP local e o IP do dispositivo configurados.
4. Verifique se o IPv4 do computador é, por exemplo, `192.168.127.100/24`, **somente se esse endereço estiver livre e for compatível com o PrintExp**.
5. Teste a outra entrada Ethernet, se existir.
6. Caso cada impressora use um PC diferente, rode o scanner no PC ligado àquela impressora; não é possível enxergar fisicamente uma rede Ethernet isolada a partir de outro computador.

## API incluída

- `GET /api/network/interfaces`: inventário de placas locais e IPv4.
- `POST /api/network/scan`: `{"interface_index": 12, "network": "192.168.127.0/24"}`.
- `POST /api/network/scan-all`: procura em todas as placas locais conectadas com IP na faixa Hoson de referência.

Os resultados podem ser exportados para CSV na interface e um dispositivo encontrado pode ter seu IP preenchido no cadastro manual. O sistema **não cadastra automaticamente dispositivos como impressoras confirmadas**.

## Limitações de validação

Os testes automatizados e a interface foram verificados com dados simulados. Esta sessão não tem acesso às placas reais Hoson nem a computadores Windows do usuário; a detecção física precisa ser validada no Windows 10 e Windows 11, nas estações ligadas às impressoras.
