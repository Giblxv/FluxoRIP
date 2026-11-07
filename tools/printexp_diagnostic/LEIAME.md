# Diagnóstico local do PrintExp e FlexiPRINT · versão 3

Esta ferramenta consulta informações do Windows para investigar uma integração com a instalação em execução. Não precisa do IP da impressora nem de Python.

1. Extraia todos os arquivos do ZIP para uma pasta no computador usado na impressão.
2. Aguarde a impressão atual terminar normalmente e deixe PrintExp e FlexiPRINT / Production Manager abertos. Esta coleta deve ocorrer com a operação ociosa; não é necessário interromper um trabalho.
3. No PrintExp, use a opção com que você costuma escolher um PRT/PRN (**OpenFiles / Abrir arquivo**). Mantenha a janela de seleção aberta, sem confirmar a abertura de nenhum arquivo nem iniciar impressão.
4. Abra `EXECUTAR_DIAGNOSTICO.cmd`, mantendo essa janela de seleção do PrintExp aberta.
5. Escolha uma pasta para salvar o resultado. Será criada uma subpasta nova `FluxoRIP-Diagnostico-...` com `diagnostico.json`.
6. Revise o JSON e envie o arquivo no chat ou coloque essa subpasta na pasta **RIP** do seu Drive. Informe no chat quando estiver disponível.

O diagnóstico lê versões dos processos correspondentes, tipos de controles de acessibilidade, identificadores e estilos de controles Win32, associações de abertura de PRT/PRN e conexões TCP que esses processos já possuem. Não abre conexões, transmite comandos, inicia o PrintExp, clica em controles, abre trabalhos, altera o registro ou lê artes e parâmetros de máquina.

O relatório omite endereços IP, nome do computador, usuário, caminhos de instalação, argumentos de processos, títulos de janelas, textos dos controles e nomes de trabalhos. Endereços são classificados como `loopback`, `any` ou `non_loopback`; portas existentes e IDs temporários de processos permanecem no JSON para correlação. Na leitura Win32, handles de janela são substituídos por números locais do relatório; aparecem classe, ID de controle, hierarquia, estilo, visibilidade e habilitação. Não é captura de pacotes.

O arquivo `.cmd` permite a execução deste script somente no processo PowerShell iniciado; não altera a política permanente do Windows. Não solicita elevação de administrador. Se alguma informação não puder ser lida, o relatório registra a ausência; não tente liberar portas ou mudar configurações de rede.

Se a leitura de acessibilidade não responder, feche a janela do diagnóstico e execute no PowerShell, dentro da pasta extraída:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Diagnosticar-PrintExp.ps1 -SkipAccessibility
```

O resultado verifica quais caminhos podem ser investigados. Uma associação de arquivo ou um socket existente não confirma que importar trabalhos é seguro, que a impressora está pronta ou que um protocolo é compatível.

## Execução técnica

```powershell
.\Diagnosticar-PrintExp.ps1 -OutputDirectory C:\Diagnosticos -NonInteractive -SkipAccessibility
```

Compatibilidade alvo: Windows 10 22H2 / Windows 11, Windows PowerShell 5.1. Os testes automatizados usam Windows Server 2022; isso não substitui a validação na estação do operador.

O formato do JSON é `schema_version=3`. Caso a enumeração nativa esteja indisponível, a seção `native_windows` registra essa condição. Para omiti-la explicitamente, utilize `-SkipNativeWindows`.

Esta versão prioriza todas as janelas visíveis encontradas antes de aplicar o limite de saída. Ignora janelas auxiliares de dicas/IME e omite descendentes ocultos. Isso evita perder um diálogo visível por excesso de controles ocultos. O relatório registra `helper_windows_omitted`, `hidden_nodes_omitted` e `visible_capture_complete`. Um valor `false` nesse último campo impede concluir que uma janela ou controle esteja ausente.
