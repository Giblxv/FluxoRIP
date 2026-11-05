# AutoRIP Studio v0.72 — periodicidade em máscaras de diferenças de PRT reais

Execução pontual, somente leitura, sem comando de impressora, firmware ou execução de binário FlexiPRINT/PrintExp. A organização abaixo é **hipotética** e não é mapeamento CMYKW.

## Entradas verificadas por SHA-256

| Configuração informada pelo operador | Nome | SHA-256 |
|---|---|---|
| 0% | `TESTER1.PRT` | `75ef4acb3b7c2dbbce28dc112187ca19b250f2728842eae0c5c7c38b41d8d8ec` |
| 50% | `TESTER1_1.PRT` | `7f5d2036cf9a107a4600f21b3e54a9238850d73861c4de22d8871f3497d68773` |
| 100% | `TESTER1_0.PRT` | `c143d3bac295c352ec63060ae20f0210c6dbf200e4f18fbee471e96d54c46136` |

As três entradas contêm a assinatura candidata `0x5555`, cabeçalhos idênticos de 48 bytes e geometria candidata `48 + 1456 × 12 × 15176 = 265155120` bytes por arquivo. Essas interpretações ainda não definem o layout real de canal/pixel.

## Novo experimento

O código `mask_periodicity.py` trata as 12 divisões contíguas do payload como **planos candidatos**, sem concluir que sejam canais físicos. Em cada divisão, calcula a máscara de bytes diferentes (0 = mesmo byte, 1 = byte diferente), seu hash SHA-256 e sua quantidade de posições alteradas, para as comparações 0%×50%, 50%×100% e 0%×100%. Todos os três PRTs são lidos sequencialmente; nenhuma máscara ou byte proprietário é publicado no GitHub.

### Resultados nos arquivos reais

| Par | Bytes distintos | Mesma máscara periódica nos grupos 1–10? | Grupos candidatos com máscaras idênticas |
|---|---:|---|---|
| 0% × 50% | 18.519.938 | **Sim, período 3** | `[1,4,7,10]`, `[2,5,8]`, `[3,6,9]` |
| 50% × 100% | 18.515.358 | **Não** | nenhum par de grupos idênticos |
| 0% × 100% | 18.520.514 | **Sim, período 3** | `[1,4,7,10]`, `[2,5,8]`, `[3,6,9]` |

Adicionalmente, para os grupos candidatos 1–10, a máscara da comparação 0% × 50% é idêntica à da comparação 0% × 100%. Isso é compatível com as mesmas posições sendo ativadas em ambos os casos, mas com níveis codificados distintos. O comportamento da comparação 50% × 100% **quebra a periodicidade exata**, indicando que não se pode tratar o nível intermediário como uma transição binária universal.

Uma máscara igual não implica conteúdo de plano igual: a comparação indica somente igualdade das **posições** que mudaram. Este método não confirma `plane_major` contra `row_major`, não identifica pixels, não estabelece que cada grupo seja uma cor e não liga nenhuma faixa ao `Spot_1`, CMYKW ou ao branco físico. A repetição a cada três grupos pode refletir rasterização, repetição de imagem, alinhamento ou empacotamento, entre outras causas.

## Reprodutibilidade

- Foram aprovados **105 testes sintéticos** da suíte integrada (94 existentes + 11 novos): `python -m unittest discover -p 'test_*.py' -v` na pasta `integration`.
- O analisador também foi executado duas vezes sobre os **três PRTs reais**, com blocos de leitura de `2 MiB` e `37.117 bytes`. Os resultados JSON normalizados foram idênticos, incluindo hashes, máscaras e contagens.
- Dependência do novo analisador: Python 3.10+ e NumPy. O código não depende de driver ou RIP proprietário.
- Nenhum arquivo PRT, ICC ou BMP real integra este pacote ou a branch pública.

## Comando somente leitura

```bash
python mask_periodicity.py --white-0 /CAMINHO/TESTER1.PRT --white-50 /CAMINHO/TESTER1_1.PRT --white-100 /CAMINHO/TESTER1_0.PRT --output /CAMINHO_SEPARADO/periodicity.json
```

O destino JSON deve ser um caminho separado das entradas. Os arquivos de entrada são abertos apenas em modo de leitura binária; a execução realiza hash SHA-256 em fluxo e verifica alterações observáveis nos metadados dos arquivos. Isso **não equivale a bloqueio atômico/snapshot imutável**.

## Próxima etapa

Validar a periodicidade com **outros trabalhos PRT de conteúdo gráfico diferente** e experimentos de `Spot_1` isolado; somente então testar hipóteses de correspondência entre faixas de dados e separações reais. Não executar impressão nem gerar PRT para produção.
