# FORGE 1.1 — Compatibilidade Windows 10 e 11

## Configuração recomendada

| Requisito | Windows 10 | Windows 11 |
| --- | --- | --- |
| SO | 22H2 x64 recomendado | x64 |
| Python no computador de uso | Não é necessário (EXE compilado) | Não é necessário |
| Python para compilar | 3.12 x64 | 3.12 x64 |
| Interface nativa | WebView2 Runtime | WebView2 Runtime |
| Sem WebView2 | Modo navegador | Modo navegador |
| Scanner Hoson | Windows PowerShell + módulos NetTCPIP/NetAdapter | Idem |
| Dados | `%LOCALAPPDATA%\FORGE` | `%LOCALAPPDATA%\FORGE` |

## Uso

1. Faça backup de `%LOCALAPPDATA%\FORGE` se estiver atualizando.
2. Em Windows 10 ou 11 x64 com Python 3.12 instalado, execute `GERAR_EXECUTAVEL.bat` para construir. O arquivo final será `dist\FORGE.exe`.
3. Copie o **único EXE** para o computador de destino e execute-o. Nenhuma instalação de Python é necessária no destino.
4. Instale o WebView2 Runtime da Microsoft caso queira a janela integrada. Sem esse runtime, o FORGE tenta abrir pelo navegador. Para forçar: `FORGE.exe --navegador`.
5. Para diagnosticar sem varrer IPs nem alterar a rede, execute `FORGE.exe --diagnostico` e veja `%LOCALAPPDATA%\FORGE\diagnostico_windows.json`.
6. Teste primeiro numa máquina ociosa e em rede dedicada antes de distribuir para as estações de impressão.

## Observações e limites

- Executável único não significa instalação de todos os componentes opcionais de terceiros. Real-ESRGAN e rembg são externos/opcionais.
- O scanner de rede detecta dispositivos via ICMP e cache ARP e **não garante identificação de impressoras Hoson**. Ele não altera IP, gateway, firewall ou roteamento, nem envia comandos de impressão.
- Em estações com múltiplas portas na mesma faixa 192.168.127.x, o Windows pode rotear pacotes por uma interface diferente. Confira os resultados e não considere a mera resposta como identificação inequívoca da porta física.
- A compilação em Windows 11 não é garantia de execução em todas as versões do Windows 10. Para maior cobertura, compile no Windows 10 22H2 64 bits e valide no Windows 11, além de verificar o EXE gerado via GitHub Actions.
- O Windows 10 Home/Pro saiu do suporte padrão em 14/10/2025. Para máquinas industriais que precisam permanecer nesse sistema, mantenha atualização/ESU quando aplicável e uma rede isolada.
- Se o scanner não listar placas, verifique com PowerShell local: `Get-NetAdapter` e `Get-NetIPAddress -AddressFamily IPv4`. Sem esses comandos ou sem permissão, a descoberta será indisponível, mas os módulos de gestão continuam úteis.

## Diagnóstico e suporte

O comando `--diagnostico` inclui versão do SO e disponibilidade dos componentes e **não coleta endereços IP, MAC, senhas ou dados de pedidos**. O log do programa continua em `%LOCALAPPDATA%\FORGE\forge.log`.

## Fontes

- Python 3.12 no Windows: https://docs.python.org/3.12/using/windows.html
- WebView2 Runtime: https://developer.microsoft.com/en-us/microsoft-edge/webview2/
- pywebview no Windows: https://pywebview.idepy.com/en/guide/installation
- Microsoft, Windows 10 EOL: https://support.microsoft.com/pt-br/windows/deployment/updates-lifecycle/windows-10-support-has-ended-on-october-14-2025
