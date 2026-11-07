# Alternativas de integração sem SDK

## Caminhos distintos

Para uma operação que salva PRT/PRN no RIP e abre esse arquivo manualmente no PrintExp, não existe necessariamente uma transmissão entre os dois programas para capturar. As possibilidades devem ser verificadas separadamente:

| Caminho | Evidência necessária | Limite |
| --- | --- | --- |
| Entrada no Production Manager por hot folder | Fila e preset escolhidos pelo operador | Automatiza entrada no RIP; não comprova importação no PrintExp |
| Abertura por associação PRT/PRN do Windows | Registro da associação e teste com a versão instalada | Uma associação existente pode usar outro programa; não é autorização para executá-la |
| Automação da interface do PrintExp | Controles acessíveis, comportamento de importar e política de início da fila | Depende da versão, foco e estado da janela; não implementada nesta investigação |
| Receptor de rede do PrintExp | Processo e socket observados, contrato do transporte e testes controlados | Um socket escutando não define o protocolo nem confirma que é seguro enviar dados |
| API/SDK do fornecedor | Contrato compatível com software, placa e firmware | Continua sendo uma possibilidade, sem ser o único caminho de investigação |

Os caminhos podem coexistir. A geração do raster de dispositivo e o transporte ao PrintExp são problemas diferentes. Descobrir como entregar um PRT não torna um PNG/TIFF automaticamente compatível nem valida a geração de PRT de produção.

## Fontes públicas

- [SAi — Setup Properties](https://support.thinksai.com/hc/en-us/articles/4405332556564-Setup-Properties): documenta hot folder e as políticas **Hold**, **Auto Start** e **Schedule** do Production Manager. Em uma investigação inicial, **Hold** permite observar a entrada sem solicitar início automático. A configuração deve ser conferida na estação antes de depositar arquivos.
- [SAi — Creating Multiple Queues](https://support.thinksai.com/hc/en-us/articles/4405353674772-Creating-Multiple-Queues): documenta filas com presets e pastas diferentes.
- [Hosonsoft — RIIN User's Manual](https://www.hosonsoft.com/uploads/Driver/Help/help-Eng.pdf): distingue saída em arquivo PRN e envio TCP/IP ao software de impressão. É um manual de operação do RIIN, não o contrato do protocolo nem uma comprovação para outra versão de PrintExp.
- [Wonder — documentação de produto WDMS250](https://www.wonderjet.net/uploads/soft/20230516/1684232937.pdf): apresenta um fluxo ERP/PrintExp por arquivos para outra família de equipamentos. Isso não estabelece compatibilidade com DTF, nem disponibiliza por si só o formato das mensagens ou habilita essa função em outras instalações.

## Diagnóstico da estação

O pacote em [`tools/printexp_diagnostic`](../tools/printexp_diagnostic/LEIAME.md) lê processos, associações de PRT/PRN, metadados de acessibilidade e sockets TCP já existentes de processos selecionados. Não escaneia endereços ou portas e não transmite pacotes, abre trabalhos ou interage com controles.

O JSON omite IPs, caminhos, usuários, nomes de trabalhos e textos da interface. Os resultados pertencem à estação e não devem ser incluídos no Git. Processos genéricos como `App.exe` só são considerados quando o caminho identifica a instalação SAi/Flexi; acesso negado pode produzir um relatório parcial.

A versão 2 inclui metadados Win32 para janelas que não expõem padrões de ação UI Automation. Enumera janelas do processo selecionado, classes, IDs de controles, hierarquia, estilos e estados de visibilidade/habilitação; não lê títulos ou conteúdos. Janelas de nível superior e controles visíveis são priorizados antes dos ocultos, com limites de enumeração. Não há `SendMessage`, `PostMessage`, acionamento de padrões ou cliques. Esses identificadores ajudam a investigar seletores e não provam que uma ação de importação é compatível.

Testes automatizados usam processos e conexões sintéticos, mais uma coleta de leitura no Windows Server sem PrintExp ou impressora. A ferramenta não confirma compatibilidade com a máquina real. A leitura de acessibilidade pode não estar disponível em janelas personalizadas; existe a opção `-SkipAccessibility`.

## O que esta investigação não habilita

Não são executadas DLLs proprietárias nem gerados comandos pela interpretação de nomes de funções ou portas. Não há escrita em arquivos de tarefas, alteração de parâmetros de máquina, envio de jobs ou automação de botões. Qualquer caminho ativo exige evidência de comportamento e teste supervisionado antes de ser incorporado ao aplicativo.
