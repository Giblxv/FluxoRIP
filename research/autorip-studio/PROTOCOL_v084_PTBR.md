# AutoRIP Studio — protocolo prospectivo v0.84 (pré-registro)

**Escopo:** pesquisa somente leitura, sem impressão ou escrita de arquivos PRT. Data do pré-registro: 5 de novembro de 2026.

## Hipótese congelada antes de novas artes

O experimento histórico v0.82, baseado nos três PRTs TESTER1, encontrou uma concentração recorrente de alterações. Agora, antes de consultar qualquer resultado de novos arquivos, o analisador `prospective_periodicity.py` congela estes parâmetros:

| Item | Valor pré-definido | Origem |
|---|---:|---|
| Período candidato do payload | **17.472 bytes** | Estimativa descritiva v0.82 |
| Largura da janela | **1.456 bytes** | Estimativa descritiva v0.82 |
| Posição modular inicial | **5.821** | Primeira dentre **quatro posições empatadas** na v0.82 |
| Referência geométrica | `48 + 17.472 × stride` | Modelo candidato, não protocolo confirmado |
| Fração da janela no período | `1/12 = 8,3333%` | Referência uniforme **não probabilística** |

**Não se faz nova busca de fase ou período nos PRTs de teste.** A escolha histórica veio das mesmas três amostras utilizadas para formular a hipótese; uma divisão interna dessas três amostras não equivale a replicação independente.

## Os 12 arquivos necessários

Use primeiro o validador `controlled_capture.py` e o script `fill_capture_manifest.ps1` descritos em [PROTOCOL_v083_PTBR.md](PROTOCOL_v083_PTBR.md). São três **artes originais distintas** (`art_a`, `art_b`, `art_c`), cada uma exportada com branco declarado 0%, 50% e 100%, além de uma segunda exportação independente em 50% da mesma arte.

**Atenção:** mantenha as dimensões físicas, DPI, perfil ICC, resolução, passadas e demais condições do RIP constantes conforme o protocolo. O programa não inspeciona o estado real da interface do FlexiPRINT, portanto os hashes de arte e configuração atestam apenas os arquivos fornecidos pelo operador.

De preferência, teste novas artes com as dimensões e configurações necessárias para obter a mesma geometria candidata. Se o tamanho e a geometria mudarem, o módulo informa `not_evaluable`; isso **não** é evidência de que o protocolo não apresenta periodicidade.

## Como executar a etapa prospectiva

Em PowerShell, a partir de `research/autorip-studio`:

~~~powershell
py -3.11 prospective_periodicity.py --manifest "C:\AutoRIP-Piloto\plano-preenchido.json" --directory "C:\AutoRIP-Piloto\amostras" --output "C:\AutoRIP-Piloto\replicacao-v084.json"
~~~

O relatório JSON é criado **somente em arquivo novo**. O validador verifica todos os 12 hashes do plano antes da análise e confere novamente os digests durante a leitura comparativa dos arquivos compatíveis. O relatório mostra apenas **contagens agregadas**, sem os bytes dos PRTs.

## Interpretação pré-definida

- `descriptive_only_no_ink_inference`: repetição em 50% é binariamente estável e houve diferença de bytes entre níveis. A fração na janela fixa é descritiva: **não constitui prova de canal, tinta branca ou pixel**.
- `repeatability_confounded`: duas exportações declaradamente iguais em 50% produziram bytes diferentes. **Não** atribuir as demais diferenças exclusivamente à configuração de branco.
- `no_level_difference_observed`: 0% e 100% produziram arquivos idênticos nos bytes do payload, na geometria candidata. Não há evidência de mudança binária para aquela arte.
- `not_evaluable`: cabeçalhos diferentes ou geometria incompatível com o pré-registro. A hipótese ficou **sem teste válido** naquela arte.

O programa informa para cada par o total de bytes diferentes, a quantidade dentro da janela fixa, a quantidade fora dela e a proporção, quando houver diferenças. A referência uniforme de `8,3333%` é somente a **proporção geométrica da janela**, não um modelo nulo validado nem um valor-p. Distribuições naturais de imagens podem ser altamente não uniformes.

**Nenhuma condição isolada é promovida automaticamente a “hipótese comprovada”.** Para avaliar a generalização, precisamos examinar todos os três resultados, as exportações repetidas e os registros das variáveis controladas.

## Regras de segurança

- Não enviar PRT, ICC, dados de cabeçote, parâmetros de firmware ou arquivos proprietários ao GitHub.
- Não alterar arquivos de origem, executar a impressora ou gerar PRTs a partir deste módulo.
- O RIP de geração das amostras é o FlexiPRINT; PrintExp é o software controlador Hoson.
- A branch `main` permanece fora do experimento.
- Os testes CI usam somente artefatos sintéticos e não garantem compatibilidade de impressão.

## Status

Esta v0.84 implementa o **procedimento prospectivo antes da coleta**. Os 12 novos arquivos ainda **não foram fornecidos**. Os relatórios reais anteriores v0.80–v0.82 servem exclusivamente como origem histórica dos parâmetros congelados.
