# Como levar o histórico original do ChatGPT ao Codex

O Codex usa uma visualização e histórico separados do ChatGPT. Este pacote traz um **resumo técnico**, não uma exportação literal de todas as mensagens.

## Para começar a desenvolver imediatamente
1. Extraia este ZIP no Windows.
2. Abra o aplicativo ChatGPT para desktop e escolha **Codex** no menu superior, ou use Codex na IDE/terminal.
3. Abra a pasta local **FluxoRIP**, que contém o código e `AGENTS.md`.
4. Cole o conteúdo de `PROMPT_PARA_CODEX.txt` na nova conversa.
5. Peça ao Codex para consultar `CODEX_HANDOFF.md`, `HISTORICO_CONVERSA.md` e `docs/` antes de editar arquivos.

## Para levar também a conversa original, palavra por palavra
1. No ChatGPT: **Configurações → Controles de dados → Exportar dados**.
2. Após receber o ZIP de exportação, localize a conversa relevante em `chat.html` ou `conversations.json`.
3. Salve SOMENTE a conversa pertinente como texto/Markdown. Evite transferir o arquivo completo de exportação, pois ele pode conter outras conversas e dados pessoais.
4. Revise e remova credenciais, senhas e informações sensíveis antes de colocar a transcrição num repositório ou enviá-la a ferramentas de programação.
5. Disponibilize o texto da conversa na pasta local, por exemplo `CONTEXTO_CHATGPT_PRIVADO.md`, **sem fazer commit** do arquivo. Solicite ao Codex que leia esse arquivo.

Como alternativa à exportação completa, use a opção **Compartilhar** no ChatGPT para obter um link da conversa, quando disponível. Confirme o conteúdo visível antes de compartilhar. Um link por si só não importa automaticamente todo o histórico para uma sessão do Codex.

Fonte oficial: https://help.openai.com/pt-br/articles/7260999-exporting-your-chatgpt-history-and-data
