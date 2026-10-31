# FORGE v1.2 — Central e agentes Windows 10/11

## O que foi entregue

- Servidor central na LAN com senha aleatória individual (autenticação Basic protegida por PBKDF2); o modo local antigo continua disponível.
- Uma única base SQLite na **Central**; outros computadores acessam os mesmos pedidos pela URL no navegador.
- Nova aba **Estações** para mostrar o nome do PC, Windows, interfaces IPv4 e resultados de scans explicitamente autorizados no agente.
- Agente de estação que envia inventário de adaptadores a cada 120 segundos e **não recebe ordens remotas**.
- Descoberta de IPs da sub-rede Hoson em cada estação somente se `scan_on_start=true` for autorizado, uma vez no início do agente.

## 1. Computador CENTRAL (rede administrativa)

1. Faça backup de `%LOCALAPPDATA%\FORGE` e mantenha a mesma pasta no PC central.
2. Compile `FORGE.exe` pelo `GERAR_EXECUTAVEL.bat` em Windows 10 22H2 x64 ou Windows 11 x64.
3. Execute `CONFIGURAR_CENTRAL.bat` **uma única vez**. Guarde a senha longa mostrada na janela. A janela padrão Windows permite `Ctrl+C` para copiar o texto.
4. Execute `INICIAR_CENTRAL.bat` e informe o **IPv4 do PC central na rede administrativa** (por exemplo, `192.168.1.100`). **Não utilize** `192.168.127.x` da rede dedicada Hoson.
5. O navegador abre `http://IP-CENTRAL:8765`. Faça login com usuário `forge` e a senha gerada.
6. Nos outros computadores, acesse o mesmo endereço pelo navegador. Todos veem o banco central; não abra uma segunda Central no mesmo banco.
7. No Firewall do Windows, somente se necessário e com autorização do responsável pela rede, libere **entrada TCP 8765 apenas para a sub-rede administrativa confiável**, nunca para todas as redes. O FORGE não modifica o firewall automaticamente.

## 2. Estações de impressão (agente opcional)

1. Copie `FORGE.exe` e os arquivos `CONFIGURAR_ESTACAO.bat`, `.ps1`, `TESTAR_ESTACAO.bat`, `INICIAR_AGENTE.bat` para o PC da impressora.
2. Na Central, clique `MOSTRAR_CHAVE_AGENTE.bat`; copie a chave com cuidado e não publique nem envie por canais desprotegidos.
3. No PC da estação, execute `CONFIGURAR_ESTACAO.bat` e informe o IP administrativo da Central, nome da estação e chave.
4. Escolha **N** para scan inicial por padrão; **S** apenas se você autorizou procurar equipamentos nessa rede dedicada.
5. Execute `TESTAR_ESTACAO.bat`. Confirme que aparece no painel **Estações**.
6. Execute `INICIAR_AGENTE.bat` para manter a informação atualizada. O agente precisa permanecer em execução.
7. Verifique `%LOCALAPPDATA%\FORGE\forge.log` se ocorrer erro.

### Atenção sobre o scanner

O scanner acessado no navegador executa **no PC onde está rodando a Central**, não no navegador remoto. O agente envia seus próprios adaptadores e pode fazer uma varredura inicial autorizada em `192.168.127.0/24`. O scan não identifica com certeza fabricante, modelo, protocolo ou estado de impressão. Placas Hoson em PCs e interfaces diferentes podem repetir o mesmo IP, sem serem o mesmo dispositivo.

## Segurança / limites da versão

- **HTTP Basic não criptografa o tráfego**. Use somente em **LAN administrativa isolada e confiável**, preferencialmente HTTPS atrás de um proxy ou VPN antes de usar em redes compartilhadas; não exponha TCP 8765 à internet nem a uma Wi-Fi de convidados. As credenciais podem ser interceptadas em uma rede sem TLS.
- A senha de usuário é armazenada em hash PBKDF2, mas a chave dos agentes fica no arquivo protegido `%LOCALAPPDATA%\FORGE\central_auth.json` da Central e `estacao.json` dos agentes. Proteja backups e acesso ao perfil Windows.
- A chave é compartilhada entre agentes nesta primeira implementação; roubar uma chave permitiria enviar informações falsas de estação, mas não ler pedidos. Rotação: `FORGE.exe --redefinir-central` gera nova senha e invalida **todos** os agentes.
- O agente não modifica IP, firewall, rotas, firmware, PrintExp, tarefas do RIP ou valores elétricos das impressoras.
- Não há comandos remotos de impressão nem telemetria real Hoson. Estados de fila continuam manuais.
- O armazenamento de artes, pedidos e relatórios agora é centralizado somente quando você acessa o FORGE pela URL da Central. Um `FORGE.exe` aberto normalmente em outra estação continua sendo um aplicativo LOCAL independente.
- A v1.2 mantém SQLite para primeira implantação. Antes de uso multiusuário intensivo, cargas simultâneas e edição concorrente, planejar migração para PostgreSQL e autenticação individual por operador.
- Este pacote é código-fonte e compilador. A compilação EXE e validação com máquinas reais precisam ser feitas no Windows.
