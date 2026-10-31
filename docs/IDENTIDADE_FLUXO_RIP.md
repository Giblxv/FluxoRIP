# Guia de aplicação — Fluxo RIP

Fonte: documentos HTML fornecidos pelo usuário, preservados em `referencias_identidade/`.

- Nome exibido: **fluxo rip** (arquivo executável `FluxoRIP.exe`).
- Símbolo: três gotas de tinta sobrepostas, ciano `#00A6D6`, magenta `#E5007D` e amarelo `#FFD500`; linhas do raster branco dentro da gota, sempre sobre base branca. SVG é vetorial.
- Cores de suporte: preto `#14171A`, branco `#FFFFFF`, papel `#EEF1F2`; dark UI: `#101316`, superfície `#181C20`.
- Tipografia: títulos Archivo ExtraBold / largura expandida; textos Public Sans. Se a fonte Google não carregar, há fallback local (sem distribuição de fontes).
- Motion: splash de abertura 1,7 s (só uma vez por sessão), camadas CMY em sequência e linhas raster desenhadas; microinterações já existentes permanecem. `prefers-reduced-motion` e controle MOTION ON/OFF desativam o efeito.
- Nenhuma animação representa progresso real do RIP. Não há comunicação direta com controladoras neste release.
- Ícones: `web/assets/fluxo-rip-mark.svg`, `web/assets/fluxo-rip-icon.png`, `FluxoRIP.ico`.
- Alterações de interface: cabeçalho, logo, ações principais, métricas, cores de seleção, console Impressões, splash e rodapé.
- Backward compatibility: pasta de dados `%LOCALAPPDATA%\FORGE` e identificadores internos `FORGE_*` permanecem para não perder dados/autenticação e evitar migrações arriscadas.
- Versão mono: prevista no documento-fonte, não usada como ícone do Windows.
- Regras: não girar/esticar/recolorir símbolo; respeitar o fundo branco; o amarelo não é usado em texto sobre fundo claro.
