# Estudo técnico do PrintExp (Hosonsoft) — FORGE v0.8

**Escopo:** softwares de controle PrintExp usados com placas Hoson em impressoras DTF e DTF UV de fabricantes diferentes, inclusive equipamentos chineses genéricos. Este documento foi feito a partir de manuais públicos e não constitui documentação de protocolo nem garantia de compatibilidade com firmware ou versão específica.

## Fontes e versões

- **Manual da Shenzhen Hosonsoft:** *PrintEXP Printer Control & Alignment Software Instruction*, referência HS/D-YF-A0-005, revisão 2018. Texto e imagens: https://device.report/m/554f2f7557b7334e0bd0247cbbbfc6b54218af84d5d7dbbde1841df9b9cdd8c_optim.pdf
- **Manual de instalação PrintExp Hoson LINKO:** https://www.dtflinko.com/pt-br/servicos-tecnicos/operacao-tecnica-de-reparo-de-impressora/guia-de-instalacao-do-software-printexp-hoson/
- **Comparação de telas e procedimentos de alinhamento:** https://www.inkdropprinterservices.com/post/printer-alignment-in-printexp

Essas referências retratam implementações específicas; a interface exata pode variar com a versão e com o OEM. **Nenhuma especificação de API de comando remoto confiável para a máquina do usuário foi localizada/validada**.

## Inventário funcional e situação do FORGE

| Grupo PrintExp | Funcionalidades documentadas | Na v0.8 | Protocolo validado? |
|---|---|---|---|
| Arquivos | Abrir arquivo processado, informações e preview | Prévia para revisão de arte vinculada; não decodifica PRN | Não |
| Trabalhos | Fila, histórico, iniciar, cancelar, mover para cima/baixo, propriedades | Fila e histórico **administrativos**; mover e registrar estados manuais | Não |
| Composição | Repetições X/Y, espaçamento horizontal/vertical, recorte da região, posição | Metadados persistidos por trabalho, sem produzir spool | Não |
| Impressão | Passadas, velocidade, direção, margem inicial | Perfis locais por impressora, sem aplicar à placa | Não |
| Acabamento de impressão | Barras de cor e feather | Valores de referência locais | Não |
| Cabeçotes | Inspeção de jatos, nivelamento, verticalidade, intervalos | Registro técnico com operador, data e resultado | Não |
| Calibração | Stepping, bidirecional, trapping, espaço cabeçote | Checklist e histórico manual | Não |
| Manutenção | Limpeza, flash, hidratação, teste de papel, carga de tinta | Checklist e histórico manual | Não |
| Eixos | Home/reset, avanço/retorno, movimento, microajustes | Documentação, **sem botões de atuação** | Não |
| Elétrico | Tensão/offset e temperatura de cabeça | Documentação, sem valores inventados ou comando | Não |
| Rede | Configuração de IP local e comunicação TCP | Cadastro de IP; sem socket para hardware | Não |
| Fábrica | Parâmetros de motor, placa, firmware, importar/exportar .bsf/.xtf | Documentação, sem leitura/escrita/flash | Não |
| Logs | Erros e avisos da máquina | Log do FORGE; não importa logs internos PrintExp | Não |

## Critérios para conectar a Hoson no futuro

1. Inventariar cada estação e sua versão exata de **PrintExp** e firmware da controladora, preferencialmente com capturas em Arquivo/Avançado/Versão.
2. Identificar se há uma integração oficialmente suportada (SDK/API, arquivo de status documentado, logs exportados ou interface de spool confiável). A presença de TCP e uma porta não autoriza a inferência do protocolo de controle.
3. Atenção: determinados manuais mencionam uma porta de recepção de dados de RIP, com exemplo de valor **9100**, e porta de comunicação da placa **5001** em uma implementação. Isso não comprova API de comandos, protocolo de telemetria nem que as mesmas portas sirvam em todas as placas. Não conectar nem transmitir dados a essas portas por tentativa.
4. Construir um **agente Windows separado por estação**, instalado junto do PrintExp, com logs e permissões mínimas; centralizar dados no servidor FORGE. Evitar conexão TCP paralela competindo com o PrintExp pelo mesmo endpoint.
5. Validar primeiro somente telemetria com uma única impressora ociosa. Diferenciar *status do agente*, *status da estação*, *status do spool* e *status físico da impressão*.
6. Guardar backups de parâmetros exportados pela ferramenta oficial, fora do executável e do repositório.
7. Somente liberar comandos reais depois de documentação do fabricante, testes supervisionados, proteção contra comandos duplicados, parada de emergência e confirmação do operador.
8. Não coletar nem codificar senhas de manutenção do PrintExp. Senhas são utilizadas apenas diretamente pelo operador autorizado no software original.

## Escopo intencional do módulo

O FORGE oferece um painel independente com visual operacional inspirado nas famílias de tela do PrintExp, em português, usando APIs próprias. Não incorpora o executável original, DLLs proprietárias, SDKs não fornecidos ou arquivos de configuração de fábrica. Não reproduz a lógica de controle de hardware sem documentação.

**Importante:** não afirmar que uma operação foi realmente executada na impressora quando ela foi apenas registrada no FORGE. Todo histórico de produção e manutenção nesta versão é informado por operadores.
