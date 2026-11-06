# Fluxo RIP — Refinamento CMYK / Motion cartunesco

Implementação experimental na branch `research/autorizado-autorip-studio`. Os arquivos estão vinculados à **interface real** em `web/index.html`, não a um mockup.

## Direção criativa

Motion design elástico, com antecipação, squash-and-stretch discreto, transições com acomodação e trilhas gráficas em **CMYK**. Referência apenas à energia e aos princípios gerais da animação cartunesca clássica; **nenhum personagem, logo, desenho ou asset protegido de terceiros foi reutilizado**.

A identidade original do Fluxo RIP foi preservada:
- Ciano: `#00A6D6`
- Magenta: `#E5007D`
- Amarelo: `#FFD500`
- Preto: `#14171A`

## Arquivos incorporados

- `web/cmyk-cartoon.css`: faixa CMYK no cabeçalho, indicador de aba com três tintas e animação de entrada, pop elástico de ícones, botões de ação com squash e brilho, entrada escalonada dos cards, aparência refinada das tarefas, avisos e foco.
- `web/cmyk-navigation.js`: navegação da barra de abas usando **setas, Home e End**, com foco itinerante e ativação pelo **mesmo clique usado pelo app**. Não implementa outro roteador nem interfere em API.
- `web/test_cmyk_navigation.mjs`: teste sintético de DOM com Node.js para transição de abas, wrap-around, controles desabilitados e preferência de movimento reduzido.
- `web/index.html`: adição dos recursos reais ao aplicativo via `/static/`.

## Acessibilidade e segurança operacional

- `prefers-reduced-motion: reduce` e o controle `MOTION ON/OFF` continuam respeitados. A cor/seleção permanece visível sem movimento.
- O foco do teclado utiliza contorno amarelo de alto contraste.
- Efeitos são estritamente decorativos; não animam um indicador de impressão real, não simulam telemetria nem enviam comandos Hoson.
- Nenhuma mudança no banco, configurações de impressão, firmware ou periféricos.
- Este passo **não comprova visualmente WebView2, Windows 10 ou desempenho em máquinas reais**. Testes com navegador/Windows real são próximos objetivos.

## Verificação

O workflow `.github/workflows/autorip-research-tests.yml` executa testes do módulo de pesquisa, verificação do JavaScript e smoke de navegação em ambiente sintético nas plataformas Windows e Ubuntu. O conjunto de testes não acessa impressoras reais.

## Próximas decisões de UX

1. Avaliar visualmente navegação, legibilidade, contraste e ritmo do movimento em desktop e janelas pequenas.
2. Integrar feedback mais expressivo para **eventos administrativos**, sem afirmar execução na controladora.
3. Medir custo de animações em WebView2 e diminuir efeitos para dispositivos sem aceleração gráfica.
4. Validar a interface em Windows 10/11 com dados simulados e sem impressão automática.

A pesquisa PRT permanece separada. As 12 novas amostras de laboratório continuam pendentes.
