# Atualização para o FORGE 0.8

1. Pare o FORGE antes da atualização e faça uma cópia de `%LOCALAPPDATA%\FORGE\production.db` e da pasta `art_storage` para outro local seguro.
2. Use `GERAR_EXECUTAVEL.bat` no Windows 10 ou 11 com Python 3.12 x64 instalado. Ele prepara o ambiente de compilação e gera `dist\FORGE.exe`. A compilação requer internet para baixar dependências.
3. Substitua apenas o executável e mantenha intacta a pasta `%LOCALAPPDATA%\FORGE`.
4. Na primeira execução, o SQLAlchemy cria três tabelas adicionais (`forge_print_profiles`, `forge_print_layouts`, `forge_technical_records`) sem excluir pedidos, filas ou artes existentes.
5. Abra **Impressões**, escolha a máquina, selecione **Configurações** para cadastrar o perfil de referência e **Trabalhos** para registrar composições.
6. Se o arquivo `.exe` não iniciar, use `FORGE.exe --autoteste` no PowerShell e consulte `%LOCALAPPDATA%\FORGE\forge.log`.

**Não é uma instalação nova do PrintExp.** O controlador original permanece instalado nas estações e o FORGE não transmite comandos à placa.

## Autorização e segurança

O programa serve somente em `127.0.0.1` (loopback) e não deve ser exposto diretamente à internet. Antes de conectar computadores em rede, implemente uma API central autenticada, controle de permissões e auditoria por usuário. A senha de acesso ao menu avançado do PrintExp não deve ser embutida em um aplicativo distribuível.
