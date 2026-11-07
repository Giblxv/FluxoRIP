# Integração PrintExp — leitura de arquivos

## Resultado

A aba **PrintExp** permite vincular uma instalação local ou uma cópia para análise e consultar seus arquivos de tarefas. O adaptador mantém `mode=observe_only`, `machine_status=NAO_VERIFICADO` e `can_submit=false`.

O caminho deve apontar para a raiz que contém `Project.ini` e `Data`, no computador que executa a API do Fluxo RIP. Não é um caminho do navegador remoto. A leitura é feita ao abrir a aba, vincular ou clicar em **Atualizar leitura**, sem varredura automática de discos. O vínculo é salvo em uma tabela adicional no banco do Fluxo; desvincular remove o caminho dessa configuração. Nenhuma tabela existente é alterada.

## Evidências analisadas em 7 de novembro de 2026

O operador disponibilizou uma cópia do PrintExp em uma pasta RIP no Drive. A análise foi estática; nenhum executável ou DLL desse pacote foi iniciado. Arquivos proprietários, parâmetros de máquina, dados de clientes e credenciais não fazem parte do repositório.

- `PrintExp_X64.exe`: PE32+ x64, data de compilação registrada em 10/01/2023. SHA-256 `4f8c874ee48edafaed444c20c7690333710ccd0a41d2959000a22406794dd0df`.
- Os recursos textuais do executável incluem `FileVersion 1.0.0.1` e `ProductVersion 5.7.0.35`. O primeiro item das notas de atualização refere-se ao pacote `PrintExp_X64_V5.7.6.5.122.BS_20230110.zip`. São referências diferentes; não se assume que uma delas representa firmware ou versão verificada na estação em funcionamento.
- O filtro de abertura de arquivos do executável referencia `.prn` e `.prt`. Isso não comprova suporte direto aos PNG/TIFF de pré-impressão gerados pelo Studio.
- `Project.ini` contém seleção de comunicação entre softwares e uma seção de plataforma ERP. Na cópia analisada, o módulo escolhido é RIIN e a plataforma ERP está desabilitada. Encontrar opções ou portas no arquivo não estabelece o protocolo, contrato de mensagens, autenticação ou procedimento seguro de envio. Nenhuma dessas opções é alterada.

| Arquivo analisado | Versão TSKF | Registros declarados e percorridos |
| --- | --- | --- |
| `fileTask.tf` | 24 | 35 |
| `printTask.tf` | 24 | 2 |
| `HistoryTask.tf` | 24 | 2.078 |
| `recordTask.tf` | 24 | 1.202 |

Os quatro arquivos chegaram exatamente ao fim após percorrer os registros; os hashes foram preservados após a leitura. Todos os caminhos de trabalhos encontrados nessa cópia referenciavam `.prt`. Esses números descrevem somente a cópia analisada; não confirmam uma fila ativa nem impressões concluídas.

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
