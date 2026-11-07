# Ensaio de preparação de caminho no PrintExp

Este protótipo verifica uma alternativa de integração pela janela padrão de abertura de arquivos do Windows. Ele pode preencher somente o campo de nome de arquivo que já está aberto no PrintExp. A confirmação de abertura e a impressão continuam manuais. O ensaio termina com a conferência do campo preenchido e o cancelamento manual da janela.

É um pacote separado do diagnóstico de leitura e do Studio. Não está habilitado como automação de produção. Sua estrutura foi testada com janelas sintéticas no Windows Server; o comportamento na instalação real deve ser verificado pelo operador, com a impressão anterior já terminada.

## Como fazer o ensaio

1. Aguarde o trabalho atual terminar normalmente. Use uma única instância do PrintExp.
2. Extraia todos os arquivos deste ZIP para uma pasta nova. Não execute diretamente dentro do compactador.
3. No PrintExp, abra manualmente **OpenFiles / Abrir arquivo**. Deixe o campo de nome do arquivo vazio e a janela aberta.
4. Execute `PREPARAR_CAMINHO.cmd`.
5. Na janela do **Fluxo RIP**, selecione um PRT/PRN local que você já tenha gerado no seu RIP. Isso escolhe apenas o caminho para o ensaio.
6. Confira o caminho apresentado e confirme que deseja preencher somente o campo do PrintExp.
7. Confira visualmente se o campo do PrintExp recebeu o caminho correto. **Para encerrar este ensaio, clique manualmente em Cancelar no PrintExp. Não confirme a abertura e não inicie uma impressão.**
8. Será criada uma subpasta nova `FluxoRIP-Preparacao-...` junto dos scripts, com `resultado.json`. Envie esse JSON no chat.

`VERIFICAR_JANELA.cmd` faz somente a inspeção da janela, sem selecionar ou preencher caminho. É a opção para conferir a identificação antes do ensaio.

## Verificações e limites

- Procura uma única instância de processo cujo nome corresponda a PrintExp. Não inicia nem reinicia o programa.
- Exige uma única janela padrão de abertura, visível e habilitada, ligada a uma janela do mesmo processo que esteja desabilitada pelo diálogo modal.
- Confere a hierarquia do campo de arquivo, os controles padrão e o papel dos botões **Open/Abrir** e **Cancel/Cancelar**. Janelas Salvar, estruturas diferentes e outros idiomas ficam sem suporte neste ensaio.
- Exige campo vazio; não sobrescreve um texto já digitado. Revalida a janela depois da seleção e confirmação no assistente.
- Aceita um arquivo local existente, não vazio, `.prt` ou `.prn`, com caminho de até 259 caracteres. Caminhos de rede, links/junções, dispositivos e fluxos alternativos ficam fora deste primeiro ensaio.
- Uma confirmação permite no máximo uma tentativa de escrita no campo de texto. Não há repetição automática, cliques ou teclas de confirmação. O token de inspeção expira em cinco minutos.
- Verifica a leitura de volta e a permanência da janela aberta. Se o texto não puder ser conferido, o resultado registra ausência de confirmação; revise o campo manualmente.
- O helper não lê nem altera o conteúdo do PRT/PRN, não valida o raster, não envia arquivos ao receptor de rede e não faz comunicação com a controladora.

O JSON não inclui caminho, nome do trabalho, textos da interface, IPs, tokens ou handles. Registra apenas os resultados das verificações e do preenchimento. Os campos `helper_confirmed_file=false`, `helper_requested_print=false` e `machine_status=NAO_VERIFICADO` distinguem esse ensaio de uma confirmação de impressão.

Os `.cmd` usam uma política de execução apenas para o processo PowerShell iniciado; não alteram a política permanente do Windows. Não há solicitação automática de elevação. Diferenças de permissão entre os programas podem impedir o ensaio e devem resultar em recusa, sem contornar proteções do Windows.

## Fontes da API Windows

- [Microsoft — WM_SETTEXT](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settext): alteração do conteúdo de um controle de texto.
- [Microsoft — SendMessageTimeoutW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw): chamada com limite de espera e tratamento de encerramento da janela.
- [Microsoft — Open and Save As dialog boxes](https://learn.microsoft.com/en-us/windows/win32/dlgbox/open-and-save-as-dialog-boxes): distinção entre preencher o nome e confirmar uma seleção.

Este caminho não resolve a geração de PRT de produção nem comprova importação ou impressão física. A etapa atual verifica somente a preparação assistida do campo de arquivo.
