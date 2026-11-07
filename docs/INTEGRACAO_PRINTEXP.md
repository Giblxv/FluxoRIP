# Integração PrintExp — leitura de arquivos

## Resultado

A aba **PrintExp** permite vincular uma instalação local ou uma cópia para análise e consultar seus arquivos de tarefas. O adaptador mantém `mode=observe_only`, `machine_status=NAO_VERIFICADO` e `can_submit=false`.

O caminho deve apontar para a raiz que contém `Project.ini` e `Data`, no computador que executa a API do Fluxo RIP. Não é um caminho do navegador remoto. A leitura é feita ao abrir a aba, vincular ou clicar em **Atualizar leitura**, sem varredura automática de discos. O vínculo é salvo em uma tabela adicional no banco do Fluxo; desvincular remove o caminho dessa configuração. Nenhuma tabela existente é alterada.

## Escopo da análise

O operador disponibilizou uma cópia para análise estática; nenhum executável ou DLL desse pacote foi iniciado. Os testes de compatibilidade verificaram os arquivos de tarefas sem modificá-los. Detalhes de versão, inventário, contagens operacionais, parâmetros e arquivos fornecidos ficam fora desta documentação pública. Os testes reproduzíveis do repositório usam somente dados sintéticos.

Ler uma cópia não confirma a versão em execução, a configuração atual da estação, uma fila ativa ou impressões concluídas. A existência de opções de comunicação também não estabelece o contrato de mensagens ou um procedimento seguro de envio.

## Contrato implementado

O leitor aceita a assinatura `TSKF`, a versão 24 e a quantidade de registros. Percorre registros prefixados por tamanho e verifica os quatro primeiros campos de texto, também prefixados por tamanho, após um identificador opaco. Usa somente o terceiro campo para obter o nome base do arquivo. O restante do registro permanece opaco: nenhum código de estado, DPI, canal, tinta ou progresso físico é interpretado.

Os nomes são lidos como UTF-8 ou Windows-1252, conforme os nomes em português da instalação analisada. Outros conjuntos de caracteres e versões precisam de amostras próprias. As opções INI são decodificadas separadamente, incluindo os comentários chineses do pacote.

O adaptador limita cada arquivo de tarefas a 16 MiB, 10.000 registros e campos de até 4.096 bytes. Exibe até 30 nomes na ordem do arquivo, sem supor ordem cronológica. Não abre arquivos ou miniaturas referenciados pelas tarefas. Rejeita links, arquivos fora da raiz, tamanhos inválidos, versões desconhecidas, dados truncados, bytes extras e alterações detectadas durante a leitura. Uma falha não impede a consulta dos outros arquivos.

A API retorna apenas nomes base, contagens, hashes, datas e opções INI explicitamente permitidas (`COMM_MODULE` e `ENABLE` da plataforma). Não retorna parâmetros de cabeça, endereço da placa, senhas ou o conteúdo integral das configurações. Respostas usam `Cache-Control: no-store` e herdam a autenticação e proteção de origem do aplicativo.

## Validação

- Seis testes automatizados com registros sintéticos: leitura sem alteração dos arquivos, ausência de comandos, formatos inválidos, limites, links, leitura concorrente, atualização, desvinculação, proteção de origem e exclusão de dados privados.
- Os quatro arquivos reais foram lidos pelo mesmo parser, preservando hashes; os dados permanecem fora do Git.
- Chromium com API real e arquivos sintéticos: vínculo, persistência após recarregar, nomes escapados como texto, erro isolado por arquivo, atualização preservando edição do caminho e desvinculação.
- A integração não foi testada com PrintExp aberto, em uma impressora física ou em Windows 10/11 do operador. A leitura de uma cópia não valida concorrência real ou comunicação com o equipamento.

## Próxima etapa para envio automático

É necessário obter o contrato documentado da interface ERP/RIIN ou outro mecanismo oficial de importação, confirmar a versão e a estação de destino e validar um trabalho de teste supervisionado fora de produção. O pacote analisado não forneceu esse contrato nos arquivos examinados. DLLs, nomes de funções e números de porta isolados não substituem essa documentação.

O Fluxo continua exportando pré-impressão sRGB/CMYK e branco separado. A geração de PRT de produção e a comunicação ativa com PrintExp/Hoson não estão implementadas nesta entrega. As hipóteses de formato em `research/autorip-studio` não são promovidas a código de produção por esta integração.
