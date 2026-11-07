/* Fluxo RIP Studio DTF. No build step, no simulated printer telemetry. */
(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const number = (value, digits = 1) =>
    Number(value).toLocaleString("pt-BR", { maximumFractionDigits: digits });
  const defaults = {
    name: "Composição DTF",
    film_width_mm: 600,
    max_page_length_mm: 1000,
    margin_mm: 10,
    gap_mm: 5,
    dpi: 300,
    mirror: true,
    trim: true,
    white_percent: 100,
    choke_mm: 0.15,
    profile_id: null,
  };
  const state = {
    page: "studio",
    assets: [],
    assetTotal: 0,
    libraryItems: [],
    libraryTotal: 0,
    libraryOffset: 0,
    libraryBusy: false,
    libraryError: "",
    previewPage: 0,
    proofRun: null,
    proofPage: 1,
    initialized: false,
    initializing: false,
    profiles: [],
    runs: [],
    runsEtag: null,
    items: [],
    settings: { ...defaults },
    layout: null,
    layoutError: "",
    importing: false,
    errors: [],
    preview: "color",
    hotfolder: null,
    automationLoadError: "",
    automationDirty: false,
    search: "",
    online: false,
    generating: false,
    layoutBusy: false,
  };
  const draftKey = "fluxorip.studio.draft.v2";
  let inspectionSequence = 0;
  let automationSequence = 0,
    librarySequence = 0,
    libraryTimer;
  let layoutSequence = 0,
    layoutTimer,
    toastTimer,
    pollBusy = false;
  try {
    const saved = JSON.parse(localStorage.getItem(draftKey) || "null");
    if (saved && Array.isArray(saved.items)) {
      state.settings = {
        ...defaults,
        ...Object.fromEntries(
          Object.entries(saved.settings || {}).filter(
            ([key]) => key in defaults,
          ),
        ),
      };
      state.items = saved.items
        .filter((i) => i && typeof i.asset_id === "string")
        .slice(0, 50);
    }
  } catch (_) {
    /* Private browsing or old drafts. */
  }
  function saveDraft() {
    try {
      localStorage.setItem(
        draftKey,
        JSON.stringify({ settings: state.settings, items: state.items }),
      );
    } catch (_) {
      /* Optional persistence. */
    }
  }
  function toast(message) {
    $("#toast").textContent = message;
    $("#toast").classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("#toast").classList.remove("show"), 4500);
  }
  async function api(url, options = {}) {
    const { conditional = false, ...fetchOptions } = options;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: fetchOptions.signal || controller.signal,
      });
      if (conditional && response.status === 304) return null;
      if (conditional) state.runsEtag = response.headers.get("ETag");
      if (!response.ok) {
        let detail;
        try {
          detail = (await response.json()).detail;
        } catch (_) {
          /* non-JSON errors */
        }
        const error = new Error(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? "Confira os valores: " + detail.map((e) => e.msg).join("; ")
              : `Não foi possível concluir (${response.status}).`,
        );
        error.status = response.status;
        throw error;
      }
      return await response.json();
    } catch (error) {
      if (error.name === "AbortError")
        throw new Error("O servidor demorou para responder. Tente novamente.");
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }
  const post = (url, data) =>
    api(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  const payload = () => ({
    ...state.settings,
    items: state.items.map((i) => ({
      asset_id: i.asset_id,
      width_mm: Number(i.width_mm),
      copies: Number(i.copies),
      rotation: i.rotation || 0,
    })),
  });
  const asset = (id) => state.assets.find((a) => a.id === id);
  const thumb = (id, rotation = 0) =>
    `/api/studio/assets/${encodeURIComponent(id)}/thumbnail?rotation=${rotation}`;
  function setOnline(online) {
    state.online = online;
    $("#connection-banner").hidden = online;
    $("#import-button").disabled = state.importing || !online;
    $("#connection-dot").classList.toggle("offline", !online);
    $("#connection-text").textContent = online
      ? "Studio conectado"
      : "Servidor indisponível";
    updateGenerate();
  }
  function updateBadges() {
    $("#library-count").textContent = state.assetTotal;
    $("#run-count").textContent = state.runs.filter((r) =>
      ["AGUARDANDO", "PROCESSANDO"].includes(r.status),
    ).length;
  }
  const titles = {
    studio: [
      "PREPARAR FILME",
      "Seu próximo filme<br>começa aqui<span>.</span>",
      "Importe suas artes. O Fluxo cuida da composição.",
    ],
    library: [
      "BIBLIOTECA DE ARTES",
      "Suas artes, prontas<br>para o próximo fluxo<span>.</span>",
      "Originais preservados. Cada ajuste cria uma nova revisão.",
    ],
    runs: [
      "RASTERIZAÇÕES",
      "Do pixel ao filme<span>.</span>",
      "Acompanhe o processamento e baixe seus pacotes de pré-impressão.",
    ],
    automation: [
      "PASTA AUTOMÁTICA",
      "Um fluxo que<br>segue sozinho<span>.</span>",
      "Ative uma pasta de entrada para importar, compor e rasterizar novas imagens.",
    ],
    profiles: [
      "PERFIS DE COR",
      "A cor certa começa<br>com o perfil certo<span>.</span>",
      "Adicione o ICC de saída da sua combinação de impressora, tinta e filme.",
    ],
  };
  function navigate(page, recordHistory = true) {
    if (!(page in titles)) return;
    if (recordHistory && location.hash !== `#${page}`)
      history.pushState({ page }, "", `#${page}`);
    if ($("#asset-dialog").open) $("#asset-dialog").close();
    state.page = page;
    state.automationDirty = false;
    render();
    if (page === "automation") loadAutomation().catch((e) => toast(e.message));
    if (page === "library") loadLibrary(state.libraryOffset);
    window.forgeMotionOnRender?.(page);
    $("#view").focus({ preventScroll: true });
  }
  function render() {
    const [breadcrumb, title, description] = titles[state.page];
    $("#breadcrumb").textContent = breadcrumb;
    $("#title").innerHTML = title;
    $("#page-description").textContent = description;
    document.querySelectorAll(".nav-item").forEach((button) => {
      const active = button.dataset.page === state.page;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    $("#import-button").disabled = state.importing || !state.online;
    $("#import-button").innerHTML =
      state.page === "profiles"
        ? "<span>＋</span> Importar ICC"
        : "<span>＋</span> Importar artes";
    $("#page-content").innerHTML =
      `${state.importing ? '<div class="upload-progress" role="status" id="upload-progress">Importando artes…</div>' : ""}${state.errors.length ? `<div class="import-errors" role="alert">${state.errors.map(esc).join("<br>")}<br><button class="button small subtle" data-action="dismiss-errors">Fechar avisos</button></div>` : ""}${state.page === "studio" ? studioMarkup() : state.page === "library" ? libraryMarkup() : state.page === "runs" ? '<div id="runs-list"></div>' : state.page === "automation" ? automationMarkup() : profilesMarkup()}`;
    if (state.page === "studio") {
      paintLayout();
      updateGenerate();
    }
    if (state.page === "runs") renderRuns();
    updateBadges();
  }
  function field(key, label, unit, extra = "") {
    return `<label class="field"><span>${label}</span><div class="input-unit"><input type="number" data-setting="${key}" value="${esc(state.settings[key])}" ${extra} />${unit ? `<b>${unit}</b>` : ""}</div></label>`;
  }
  function studioMarkup() {
    return `<div class="studio-grid"><div class="composition-column">
      <div class="summary-strip"><div class="summary-item"><small>ARTES NO FILME</small><strong id="metric-copies">${state.items.reduce((sum, i) => sum + Number(i.copies || 0), 0)} <span>cópias</span></strong></div><div class="summary-item"><small>COMPRIMENTO</small><strong id="metric-length">— <span>cm de filme</span></strong></div><div class="summary-item"><small>APROVEITAMENTO</small><strong id="metric-usage">— <span>da área</span></strong></div></div>
      <section class="panel"><div class="panel-top"><h2><span class="step-number">01</span> Artes da composição</h2><button class="button subtle small" data-action="open-library">Abrir biblioteca →</button></div>
      <button class="drop-zone" id="drop-zone" data-action="import" ${state.importing ? "disabled" : ""}><span class="upload-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/></svg></span><span><strong>Arraste suas artes até aqui</strong><small>ou clique para escolher · PNG, JPG, WEBP, BMP, TIFF<br>Até 30 MB por arquivo · transparência preservada</small></span><span class="drop-plus" aria-hidden="true">＋</span></button>
      ${
        state.items.length
          ? `<div class="selection-header"><span>${state.items.length} ARTE${state.items.length > 1 ? "S" : ""} SELECIONADA${state.items.length > 1 ? "S" : ""}</span><button class="button small subtle" data-action="clear">Limpar composição</button></div><div class="selection-list">${state.items
              .map((item, index) => {
                const a = asset(item.asset_id);
                if (!a) return "";
                return `<div class="selected-art" role="group" aria-label="${esc(a.original_name)}"><button class="icon-button" data-inspect="${esc(a.id)}" aria-label="Conferir ${esc(a.original_name)}"><img class="art-thumb checker" src="${thumb(a.id)}" alt="" /></button><div class="art-copy"><strong title="${esc(a.original_name)}">${esc(a.original_name)}</strong><small>${a.width} × ${a.height} px · ${item.rotation || 0}° <button class="rotate-art" data-rotate="${index}" aria-label="Girar ${esc(a.original_name)} 90 graus">↻ Girar</button></small></div><div class="mini-field art-width"><label for="width-${index}">LARGURA · mm</label><input id="width-${index}" type="number" data-item="${index}" data-key="width_mm" value="${esc(item.width_mm)}" min="1" max="2000" step="0.1" /></div><div class="mini-field art-copies"><label for="copies-${index}">CÓPIAS</label><input id="copies-${index}" type="number" data-item="${index}" data-key="copies" value="${esc(item.copies)}" min="1" max="200" step="1" /></div><button class="icon-button" data-remove="${index}" aria-label="Remover ${esc(a.original_name)}">×</button></div>`;
              })
              .join("")}</div>`
          : '<div class="empty-selection">Seu filme está em branco. Adicione a primeira arte<br>para começar a composição automática.</div>'
      }${state.items.length ? '<div class="selection-hint">Largura antes da rotação. A altura acompanha a proporção da arte.</div>' : ""}</section>
      <section class="panel canvas-panel"><div class="panel-top"><h2><span class="step-number">02</span> Composição do filme</h2><small id="layout-status">PRÉVIA DE POSICIONAMENTO</small></div><div class="canvas-toolbar"><strong id="film-caption">Filme DTF · ${number(state.settings.film_width_mm / 10)} cm</strong><div class="preview-mode" aria-label="Visualização"><button class="${state.preview === "color" ? "active" : ""}" data-preview="color" aria-pressed="${state.preview === "color"}">Cor</button><button class="${state.preview === "white" ? "active" : ""}" data-preview="white" aria-pressed="${state.preview === "white"}">Alfa</button></div></div><div class="page-navigator" id="page-navigator" hidden></div><div class="film-stage"><div class="film-width-line" id="film-width-label">${number(state.settings.film_width_mm)} mm</div><div class="film-paper empty" id="film-paper"><div class="film-empty"><span class="film-symbol">▧</span>A prévia aparece aqui.<br>Artes organizadas automaticamente no filme.</div></div></div><div class="canvas-footer"><span id="mirror-status">${state.settings.mirror ? "↔ Espelhamento ativado" : "↔ Orientação normal"}</span><span id="resolution-status"><b>${state.settings.dpi} DPI</b> · proporções preservadas</span></div></section>
      <div id="layout-feedback" aria-live="polite"></div><div class="help-note"><span aria-hidden="true">ⓘ</span><div>A prévia mostra posição, orientação e alfa. Após rasterizar, use Conferir separações para ver provas da cor e do branco final, com cobertura e recuo aplicados.<br>O pacote deve ser importado no RIP compatível com sua impressora. PRT e envio à Hoson ainda não estão disponíveis.</div></div>
      </div><aside class="panel settings-panel" aria-label="Configuração da composição"><div class="panel-top"><h2><span class="step-number">03</span> Preparação DTF</h2></div><div class="settings-body">
      <label class="field"><span>Nome da composição</span><input data-setting="name" maxlength="120" value="${esc(state.settings.name)}" /></label>
      <label class="field"><span>Largura do filme</span><select data-setting="film_width_mm">${[280, 300, 330, 580, 600, 800, 1200].map((v) => `<option value="${v}" ${Number(state.settings.film_width_mm) === v ? "selected" : ""}>${number(v / 10)} cm · ${v} mm</option>`).join("")}</select></label>
      <div class="field-grid">${field("margin_mm", "Margens", "mm", 'min="0" max="100" step="0.5"')}${field("gap_mm", "Entre artes", "mm", 'min="0" max="100" step="0.5"')}</div>
${field("max_page_length_mm", "Comprimento máximo por página", "mm", 'min="50" max="3000" step="10"')}<div class="setting-note pagination-note">Filmes longos são divididos automaticamente entre artes. Cada página respeita o limite de memória na resolução escolhida.</div>
      <label class="field"><span>Resolução de saída</span><select data-setting="dpi">${[150, 300, 600].map((v) => `<option value="${v}" ${Number(state.settings.dpi) === v ? "selected" : ""}>${v} DPI${v === 300 ? " · recomendado" : ""}</option>`).join("")}</select><small>DPI de rasterização. Não define as passadas da impressora.</small></label>
      <div class="setting-divider"><h3><i class="white-dot"></i> BASE BRANCA · W</h3><label class="field"><span>Cobertura do branco</span><div class="range-row"><input type="range" min="0" max="100" step="1" data-setting="white_percent" value="${esc(state.settings.white_percent)}" /><output id="white-value">${state.settings.white_percent}%</output></div></label>${field("choke_mm", "Recuo da borda", "mm", 'min="0" max="1" step="0.05"')}<div class="setting-note">O recuo contrai o branco para reduzir halos nas bordas. O resultado depende da resolução e deve ser conferido no RIP.</div></div>
      <label class="field"><span>Perfil de saída CMYK</span><select data-setting="profile_id"><option value="">sRGB + branco · sem ICC CMYK</option>${state.profiles.map((p) => `<option value="${esc(p.id)}" ${state.settings.profile_id === p.id ? "selected" : ""}>${esc(p.name)}</option>`).join("")}</select><small>Para saída CMYK, <button class="text-link" data-action="profiles">importe seu perfil ICC</button>.</small></label>
      <div class="check-field"><input type="checkbox" id="mirror" data-setting="mirror" ${state.settings.mirror ? "checked" : ""} /><label for="mirror">Espelhar para transferência</label></div><div class="check-field"><input type="checkbox" id="trim" data-setting="trim" ${state.settings.trim ? "checked" : ""} /><label for="trim">Aparar bordas transparentes</label></div>
      </div><div class="generate-area"><button class="button cyan" id="generate-button" data-action="generate" disabled><span>≋</span> Gerar pacote DTF <span>→</span></button><small>PNG de cor + TIFF branco + manifesto${state.settings.profile_id ? " + TIFF CMYK" : ""}</small></div></aside></div>`;
  }
  function mergeAssets(items) {
    const map = new Map(state.assets.map((a) => [a.id, a]));
    items.forEach((a) => map.set(a.id, a));
    state.assets = Array.from(map.values());
  }
  async function ensureAssets(ids) {
    const missing = [...new Set(ids)].filter((id) => !asset(id));
    const results = await Promise.all(
      missing.map(async (id) => {
        try {
          return await api(`/api/studio/assets/${encodeURIComponent(id)}`);
        } catch (error) {
          if (error.status === 404) return null;
          throw error;
        }
      }),
    );
    mergeAssets(results.filter(Boolean));
  }
  function libraryMarkup() {
    return `<div class="search-toolbar"><input type="search" id="library-search" placeholder="Buscar em todas as artes…" aria-label="Buscar artes" value="${esc(state.search)}" /><span id="library-total">${state.libraryTotal} resultados</span></div><div id="library-results">${libraryCards()}</div>`;
  }
  function libraryCards() {
    if (state.libraryBusy)
      return '<div class="initial-loading" role="status">Buscando na biblioteca…</div>';
    if (state.libraryError)
      return `<div class="layout-error" role="alert">${esc(state.libraryError)} <button class="button small" data-action="retry-library">Tentar novamente</button></div>`;
    const filtered = state.libraryItems;
    const totalPages = Math.max(1, Math.ceil(state.libraryTotal / 32));
    const navigation = `<div class="library-navigation"><span>${state.libraryTotal ? state.libraryOffset + 1 : 0}–${Math.min(state.libraryOffset + 32, state.libraryTotal)} de ${state.libraryTotal}</span><div><button class="button small" data-library-offset="${Math.max(0, state.libraryOffset - 32)}" ${state.libraryOffset === 0 ? "disabled" : ""}>← Anterior</button><span>Página ${Math.floor(state.libraryOffset / 32) + 1} de ${totalPages}</span><button class="button small" data-library-offset="${state.libraryOffset + 32}" ${state.libraryOffset + 32 >= state.libraryTotal ? "disabled" : ""}>Próxima →</button></div></div>`;
    if (!filtered.length)
      return `<div class="empty-page"><div class="empty-icon">◇</div><h2>${state.search ? "Nenhuma arte encontrada." : "Um lugar para suas próximas criações."}</h2><p>${state.search ? "Tente outro nome na busca." : "Importe suas artes para DTF. Seus arquivos originais ficam preservados."}</p>${state.search ? "" : '<button class="button primary" data-action="import">＋ Importar artes</button>'}</div>`;
    return `<div class="library-grid">${filtered.map((a) => `<article class="library-card"><button class="library-preview checker" data-inspect="${esc(a.id)}" aria-label="Conferir ${esc(a.original_name)}"><img src="${thumb(a.id)}" alt="${esc(a.original_name)}" loading="lazy" /></button><div class="library-details"><strong title="${esc(a.original_name)}">${esc(a.original_name)}</strong><small>${a.width} × ${a.height} px · ${a.dpi_x} DPI</small><small>${a.operation === "importada" ? "Original importado" : "Revisão · " + esc(a.operation)}</small><div class="library-actions"><button class="button small" data-add="${esc(a.id)}">＋ Compor</button><button class="button small subtle" data-inspect="${esc(a.id)}">Conferir →</button></div></div></article>`).join("")}</div>${navigation}`;
  }
  async function loadLibrary(offset = 0) {
    const sequence = ++librarySequence;
    state.libraryBusy = true;
    state.libraryError = "";
    state.libraryOffset = offset;
    const paint = () => {
      if (state.page === "library" && $("#library-results")) {
        $("#library-results").innerHTML = libraryCards();
        $("#library-total").textContent = `${state.libraryTotal} resultados`;
      }
    };
    paint();
    try {
      const result = await api(
        `/api/studio/library?q=${encodeURIComponent(state.search)}&offset=${offset}&limit=32`,
      );
      if (sequence !== librarySequence) return;
      state.libraryItems = result.items;
      state.libraryTotal = result.total;
      if (!state.search.trim()) state.assetTotal = result.total;
      mergeAssets(result.items);
      updateBadges();
    } catch (error) {
      if (sequence === librarySequence) state.libraryError = error.message;
    } finally {
      if (sequence === librarySequence) {
        state.libraryBusy = false;
        paint();
      }
    }
  }
  function automationMarkup() {
    if (!state.hotfolder)
      return state.automationLoadError
        ? `<div class="layout-error" role="alert">${esc(state.automationLoadError)} <button class="button small" data-action="retry-automation">Tentar novamente</button></div>`
        : '<div class="initial-loading" role="status">Carregando configuração da pasta automática…</div>';
    const config = state.hotfolder?.settings || {};
    const receipts = state.hotfolder?.receipts || [];
    return `<div class="guide-panel"><strong>Uma imagem nova. Um pacote DTF.</strong><br>O Fluxo observa apenas a pasta escolhida neste computador servidor, espera o arquivo estabilizar e gera uma composição por imagem. Os originais permanecem na pasta de entrada. Use os parâmetros atuais da tela Preparar filme para configurar a automação.</div><section class="panel automation-panel"><div class="panel-top"><h2><span class="step-number">AUTO</span> Entrada de imagens</h2><span class="status-tag ${config.enabled ? "CONCLUIDO" : ""}">${config.enabled ? "ATIVADA" : "DESATIVADA"}</span></div><form id="hotfolder-form" class="settings-body"><label class="field"><span>Caminho completo da pasta de entrada</span><input id="hotfolder-path" value="${esc(config.folder || "")}" placeholder="C:&#92;Artes&#92;Entrada DTF" required autocomplete="off" /><small>A pasta precisa existir no computador que executa o Fluxo RIP. Sem subpastas.</small></label><label class="field"><span>Largura de cada arte no filme · mm</span><input id="hotfolder-width" type="number" value="${esc(config.art_width_mm || 100)}" min="1" max="2000" step="0.1" required /></label><div class="setting-note">Ao ativar, também serão processadas imagens já presentes nesta pasta. Um arquivo estável é importado uma vez; alterações de tamanho ou data criam uma nova entrada. Cada imagem gera um pacote separado, sem envio à impressora.</div><div class="automation-actions"><button class="button cyan" type="submit" ${!state.online ? "disabled" : ""}>Usar parâmetros atuais e ativar</button><button class="button" type="button" data-action="disable-hotfolder" ${!config.enabled ? "disabled" : ""}>Desativar</button></div>${config.enabled ? `<div class="setting-note">Configuração salva: filme ${number(config.film_width_mm / 10)} cm · ${config.dpi} DPI · ${config.mirror ? "espelhado" : "normal"} · branco ${config.white_percent}% · recuo ${number(config.choke_mm, 2)} mm. Novas alterações no Studio só afetam esta pasta depois de ativar novamente.</div>` : ""}</form></section><div id="automation-error" aria-live="polite">${automationErrorMarkup()}</div><div class="automation-receipts">${
      receipts.length
        ? `<h2>Arquivos observados</h2>${receipts
            .slice(0, 30)
            .map(
              (r) =>
                `<div class="receipt"><span>${esc(r.filename)}${r.error ? `<small>${esc(r.error)}</small>` : ""}</span><span class="status-tag ${r.status === "ERRO" ? "ERRO" : "CONCLUIDO"}">${{ ERRO: "REVISAR", CONCLUIDO: "PACOTE PRONTO", AGUARDANDO: "NA FILA", PROCESSANDO: "RASTERIZANDO", CANCELADO: "CANCELADO" }[r.status] || "IMPORTADO"}</span></div>`,
            )
            .join("")}`
        : ""
    }</div>`;
  }
  function automationErrorMarkup() {
    const message = state.automationLoadError || state.hotfolder?.last_error;
    return message
      ? `<div class="layout-error" role="alert">${esc(message)}</div>`
      : "";
  }
  async function loadAutomation(force = false) {
    const sequence = ++automationSequence;
    state.automationLoadError = "";
    try {
      const latest = await api("/api/studio/hotfolder");
      if (sequence !== automationSequence) return;
      state.hotfolder = latest;
      if (state.page === "automation" && (force || !state.automationDirty)) {
        state.automationDirty = false;
        render();
      }
    } catch (error) {
      if (sequence === automationSequence) {
        state.automationLoadError = error.message;
        if (state.page === "automation") {
          if (!state.hotfolder) render();
          else if ($("#automation-error"))
            $("#automation-error").innerHTML = automationErrorMarkup();
        }
      }
      throw error;
    }
  }
  function profilesMarkup() {
    return `<div class="guide-panel"><strong>Perfis ligados à sua produção.</strong><br>Um ICC CMYK descreve a resposta de cor da combinação de impressora, tinta, filme e processo. Use o perfil fornecido ou medido para sua operação. Sem ICC CMYK, o Fluxo exporta a cor em sRGB com transparência e a máscara branca independente.</div><div class="profile-grid"><article class="profile-card"><div class="profile-icon">◉</div><h3>sRGB + branco</h3><p>Saída padrão, com transparência. A conversão final de cor fica a cargo do RIP de impressão.</p><span class="status-tag CONCLUIDO">DISPONÍVEL</span></article>${state.profiles.map((p) => `<article class="profile-card"><div class="profile-icon">◉</div><h3>${esc(p.name)}</h3><p>ICC de saída CMYK · validado pelo LittleCMS.<br>O perfil não substitui a calibração física.</p><code>SHA-256<br>${esc(p.sha256)}</code></article>`).join("")}<article class="profile-card"><div class="profile-icon" style="color:var(--cyan)">＋</div><h3>Seu perfil CMYK</h3><p>Importe um arquivo .icc ou .icm de até 4 MB.</p><button class="button small" data-action="import-icc">Importar perfil ICC</button></article></div>`;
  }
  function renderRuns() {
    const target = $("#runs-list");
    if (!target) return;
    target.innerHTML = state.runs.length
      ? state.runs
          .map(
            (r) =>
              `<article class="job-card"><div class="job-heading"><div><h3>${esc(r.name)}</h3><small>${new Date(r.created_at + (/[Z+]/.test(r.created_at) ? "" : "Z")).toLocaleString("pt-BR")} · ${esc(r.id.slice(0, 8))} · ${r.request.dpi} DPI · ${r.request.mirror ? "espelhado" : "normal"}</small></div><span class="status-tag ${r.status}">${{ AGUARDANDO: "NA FILA", PROCESSANDO: "RASTERIZANDO", CONCLUIDO: "PACOTE PRONTO", CANCELADO: "CANCELADO", ERRO: "ERRO" }[r.status] || esc(r.status)}</span></div><div class="progress-track" role="progressbar" aria-label="Rasterização de ${esc(r.name)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${r.progress}"><div class="progress-bar" style="width:${r.progress}%"></div></div><div class="job-meta"><span>${esc(r.phase)} · ${r.progress}%${r.result ? ` · ${number(r.result.film_width_mm / 10)} × ${number(r.result.film_height_mm / 10)} cm · ${r.result.page_count || 1} página(s)` : ""}</span><div class="job-actions">${r.download_url ? `<button class="button small" data-proof="${r.id}">Conferir separações</button><a class="button small cyan" href="${r.download_url}" download>↓ Baixar pacote ZIP</a>` : ""}${["AGUARDANDO", "PROCESSANDO"].includes(r.status) ? `<button class="button small danger" data-cancel="${r.id}">Cancelar</button>` : `<button class="button small" data-reuse="${r.id}">Usar composição</button>`}</div></div>${r.error ? `<div class="job-error" role="alert">${esc(r.error)}</div>` : ""}</article>`,
          )
          .join("")
      : '<div class="empty-page"><div class="empty-icon">≋</div><h2>O próximo fluxo começa com uma arte.</h2><p>Suas rasterizações e pacotes exportados aparecerão aqui. O progresso acompanha as etapas reais do processamento.</p><button class="button primary" data-action="prepare">Preparar meu primeiro filme →</button></div>';
  }
  function updateGenerate() {
    const button = $("#generate-button");
    if (button) {
      button.disabled =
        !state.online ||
        !state.layout ||
        state.layoutBusy ||
        state.importing ||
        state.generating ||
        !!state.layoutError;
      button.textContent = state.generating
        ? "Adicionando à fila…"
        : state.layoutBusy
          ? "Conferindo composição…"
          : "≋  Gerar pacote DTF  →";
    }
  }
  function paintLayout() {
    if (state.page !== "studio") return;
    const fullPlan = state.layout;
    state.previewPage = Math.min(
      state.previewPage,
      (fullPlan?.page_count || 1) - 1,
    );
    const plan = fullPlan?.pages?.[state.previewPage] || fullPlan;
    $("#metric-copies").innerHTML =
      `${state.items.reduce((n, i) => n + Number(i.copies || 0), 0)} <span>cópias</span>`;
    $("#metric-length").innerHTML =
      `${fullPlan ? number(fullPlan.film_height_mm / 10) : "—"} <span>cm de filme</span>`;
    $("#metric-usage").innerHTML =
      `${fullPlan ? number(fullPlan.utilization_percent) + "%" : "—"} <span>da área</span>`;
    $("#film-caption").textContent =
      `Filme DTF · ${number(state.settings.film_width_mm / 10)} cm`;
    $("#film-width-label").textContent =
      `${number(state.settings.film_width_mm)} mm`;
    $("#mirror-status").textContent = state.settings.mirror
      ? "↔ Espelhamento ativado"
      : "↔ Orientação normal";
    $("#resolution-status").innerHTML =
      `<b>${state.settings.dpi} DPI</b> · proporções preservadas`;
    $("#layout-status").textContent = state.layoutBusy
      ? "CONFERINDO…"
      : "PRÉVIA DE POSICIONAMENTO";
    const navigation = $("#page-navigator");
    navigation.hidden = !fullPlan || fullPlan.page_count <= 1;
    navigation.innerHTML = fullPlan
      ? `<button class="button small" aria-label="Página anterior do filme" data-film-page="${state.previewPage - 1}" ${state.previewPage === 0 ? "disabled" : ""}>←</button><span>Página ${state.previewPage + 1} de ${fullPlan.page_count} · ${number(plan.film_height_mm / 10)} cm</span><button class="button small" aria-label="Próxima página do filme" data-film-page="${state.previewPage + 1}" ${state.previewPage + 1 >= fullPlan.page_count ? "disabled" : ""}>→</button>`
      : "";
    const paper = $("#film-paper");
    paper.className = `film-paper${plan ? "" : " empty"}${state.settings.mirror ? " mirrored" : ""}${state.preview === "white" ? " white-preview" : ""}`;
    paper.style.aspectRatio = plan
      ? `${plan.film_width_mm} / ${plan.film_height_mm}`
      : "";
    paper.style.minHeight = plan ? "0" : "";
    paper.innerHTML = plan
      ? `<div class="film-margins" style="left:${(100 * state.settings.margin_mm) / plan.film_width_mm}%;right:${(100 * state.settings.margin_mm) / plan.film_width_mm}%;top:${(100 * state.settings.margin_mm) / plan.film_height_mm}%;bottom:${(100 * state.settings.margin_mm) / plan.film_height_mm}%"></div>${plan.placements
          .map((p) => {
            const x = state.settings.mirror
              ? plan.film_width_mm - p.x_mm - p.width_mm
              : p.x_mm;
            // Preview crops the alpha bounds using an SVG viewport; originals remain untouched.
            const a = asset(p.asset_id),
              [x0, y0, x1, y1] = p.preview_box || p.content_box;
            return `<svg class="film-item" role="img" aria-label="${esc(p.name)}" viewBox="${x0} ${y0} ${x1 - x0} ${y1 - y0}" style="left:${(100 * x) / plan.film_width_mm}%;top:${(100 * p.y_mm) / plan.film_height_mm}%;width:${(100 * p.width_mm) / plan.film_width_mm}%;height:${(100 * p.height_mm) / plan.film_height_mm}%" preserveAspectRatio="none"><image href="${thumb(p.asset_id, p.rotation || 0)}" width="${p.preview_width_px || a?.width || x1}" height="${p.preview_height_px || a?.height || y1}" preserveAspectRatio="none" /></svg>`;
          })
          .join("")}`
      : `<div class="film-empty"><span class="film-symbol">▧</span>${state.layoutError ? "Ajuste a composição para continuar." : "A prévia aparece aqui.<br>Artes organizadas automaticamente no filme."}</div>`;
    $("#layout-feedback").innerHTML = state.layoutError
      ? `<div class="layout-error" role="alert">${esc(state.layoutError)}</div>`
      : fullPlan?.warnings.length
        ? `<details class="warnings"><summary>${fullPlan.warnings.length} ${fullPlan.warnings.length === 1 ? "ponto para conferir" : "pontos para conferir"} antes da impressão</summary><ul>${fullPlan.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></details>`
        : "";
    updateGenerate();
  }
  function scheduleLayout() {
    saveDraft();
    state.layoutBusy = !!state.items.length;
    state.layout = null;
    state.layoutError = "";
    const sequence = ++layoutSequence;
    clearTimeout(layoutTimer);
    paintLayout();
    if (!state.items.length) {
      state.layoutBusy = false;
      paintLayout();
      return;
    }
    layoutTimer = setTimeout(async () => {
      try {
        const plan = await post("/api/studio/layout", payload());
        if (sequence !== layoutSequence) return;
        state.layout = plan;
        state.layoutError = "";
      } catch (e) {
        if (sequence !== layoutSequence) return;
        state.layout = null;
        state.layoutError = e.message;
      } finally {
        if (sequence === layoutSequence) {
          state.layoutBusy = false;
          paintLayout();
        }
      }
    }, 250);
  }
  function addAsset(id, showStudio = true) {
    if (!asset(id)) return;
    const existing = state.items.find((i) => i.asset_id === id);
    if (existing) existing.copies = Math.min(200, Number(existing.copies) + 1);
    else if (state.items.length >= 50) {
      toast("Até 50 artes diferentes por composição.");
      return;
    } else
      state.items.push({
        asset_id: id,
        width_mm: Math.min(
          100,
          state.settings.film_width_mm - 2 * state.settings.margin_mm,
        ),
        copies: 1,
      });
    if (showStudio) navigate("studio");
    else render();
    scheduleLayout();
  }
  async function importFiles(files) {
    if (state.importing || !files.length) return;
    const addToComposition = state.page === "studio";
    state.importing = true;
    state.errors = [];
    render();
    updateGenerate();
    const results = [];
    const batch = Array.from(files).slice(0, 50);
    if (files.length > 50)
      state.errors.push("Importação limitada aos primeiros 50 arquivos.");
    for (let index = 0; index < batch.length; index++) {
      const file = batch[index];
      if ($("#upload-progress"))
        $("#upload-progress").textContent =
          `Importando ${index + 1} de ${batch.length}: ${file.name}`;
      if (file.size > 30 * 1024 * 1024) {
        state.errors.push(`${file.name}: arquivo acima de 30 MB.`);
        continue;
      }
      const form = new FormData();
      form.append("file", file);
      try {
        results.push(
          await api("/api/art/upload", { method: "POST", body: form }),
        );
      } catch (e) {
        state.errors.push(`${file.name}: ${e.message}`);
      }
    }
    state.assets.unshift(...results);
    state.assetTotal += results.length;
    if (addToComposition) {
      for (const a of results)
        if (state.items.length < 50)
          state.items.push({
            asset_id: a.id,
            width_mm: Math.max(
              1,
              Math.min(
                100,
                state.settings.film_width_mm - 2 * state.settings.margin_mm,
              ),
            ),
            copies: 1,
          });
    }
    state.importing = false;
    $("#file-input").value = "";
    render();
    scheduleLayout();
    if (state.page === "library") loadLibrary(0);
    if (results.length)
      toast(
        `${results.length} ${results.length === 1 ? "arte importada" : "artes importadas"}. Originais preservados.`,
      );
  }
  async function inspect(id) {
    const sequence = ++inspectionSequence;
    const a = asset(id);
    if (!a) return;
    const dialog = $("#asset-dialog");
    state.proofRun = null;
    $("#asset-dialog-content").innerHTML =
      `<div class="dialog-header"><h2 id="asset-dialog-title">${esc(a.original_name)}</h2><button class="icon-button" data-action="close-dialog" aria-label="Fechar">×</button></div><div class="dialog-preview checker"><img src="${thumb(id)}" alt="${esc(a.original_name)}" /></div><div class="dialog-stats"><span>${a.width} × ${a.height} px</span><span>${a.dpi_x} DPI de origem</span><span>Proporção preservada na composição</span></div><div id="preflight-result">Conferindo transparência e perfil…</div><div class="dialog-controls"><button class="button small" data-add="${esc(id)}">＋ Adicionar à composição</button><a class="button small subtle" href="/api/art/${encodeURIComponent(id)}/original" download>↓ Original recebido</a></div><div class="setting-divider"><h3>Remover fundo chapado</h3><div class="setting-note">Remove áreas conectadas aos cantos com cor semelhante. Confira o resultado; uma nova revisão será criada.</div><div class="dialog-controls"><label class="field"><span>Tolerância de cor (0–255)</span><input id="background-tolerance" type="number" min="0" max="255" value="28" /></label><button class="button small" data-background="${esc(id)}">Criar revisão sem fundo</button></div></div>`;
    dialog.showModal();
    try {
      const info = await api(
        `/api/studio/assets/${encodeURIComponent(id)}/preflight`,
      );
      const node = $("#preflight-result");
      if (!node || sequence !== inspectionSequence) return;
      node.innerHTML = `<div class="setting-note">${info.empty ? "Arte totalmente transparente: não pode ser rasterizada." : info.has_transparency ? "✓ Transparência detectada." : "A arte tem fundo opaco."}${info.warnings.length ? "<br>" + info.warnings.map(esc).join("<br>") : ""}</div>`;
    } catch (e) {
      if ($("#preflight-result") && sequence === inspectionSequence)
        $("#preflight-result").textContent = e.message;
    }
  }
  function openProof(id) {
    const run = state.runs.find((r) => r.id === id);
    if (!run?.download_url) return;
    state.proofRun = id;
    state.proofPage = 1;
    paintProof();
    if (!$("#asset-dialog").open) $("#asset-dialog").showModal();
  }
  function paintProof() {
    const run = state.runs.find((r) => r.id === state.proofRun);
    if (!run) return;
    const count = run.result?.page_count || 1,
      page = state.proofPage;
    const metadata = run.result?.pages?.[page - 1] || run.result;
    const url = (channel) =>
      `/api/studio/runs/${run.id}/proof?page=${page}&channel=${channel}`;
    const download = (channel) =>
      `/api/studio/runs/${run.id}/separation?page=${page}&channel=${channel}`;
    $("#asset-dialog-content").innerHTML =
      `<div class="dialog-header"><h2 id="asset-dialog-title">Conferir separações · ${esc(run.name)}</h2><button class="icon-button" data-action="close-dialog" aria-label="Fechar">×</button></div><div class="proof-pagination"><button class="button small" data-proof-page="${page - 1}" ${page === 1 ? "disabled" : ""}>← Anterior</button><span>Página ${page} de ${count}</span><button class="button small" data-proof-page="${page + 1}" ${page === count ? "disabled" : ""}>Próxima →</button></div><div class="proof-grid"><section><h3>Cor · sRGB com alfa</h3><div class="proof-image checker"><img src="${url("color")}" alt="Prova da cor exportada" /></div><a class="button small" href="${download("color")}" download>↓ Cor em resolução completa</a></section><section><h3>Branco · cobertura e recuo aplicados</h3><div class="proof-image white-proof"><img src="${url("white")}" alt="Prova da base branca exportada" /></div><a class="button small" href="${download("white")}" download>↓ Máscara W em TIFF</a></section></div><div class="setting-note">Provas reduzidas dos rasters finais. ${metadata?.width_px || "—"} × ${metadata?.height_px || "—"} px · ${run.request.dpi} DPI · ${run.request.mirror ? "espelhado" : "orientação normal"}. Branco: preto = sem tinta, branco = cobertura máxima. Estas provas não simulam a resposta de cor da impressão física.</div>${run.request.profile_id ? `<a class="button small" href="${download("cmyk")}" download>↓ TIFF CMYK com ICC</a>` : ""}`;
  }
  async function generate() {
    if (
      state.generating ||
      !state.layout ||
      state.layoutBusy ||
      state.layoutError ||
      !state.online
    )
      return;
    state.generating = true;
    updateGenerate();
    try {
      const run = await post("/api/studio/runs", payload());
      state.runs.unshift(run);
      navigate("runs");
      toast("Composição adicionada à fila de rasterização.");
    } catch (e) {
      toast(e.message);
    } finally {
      state.generating = false;
      updateGenerate();
    }
  }
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button || button.disabled) return;
    try {
      if (button.dataset.page) navigate(button.dataset.page);
      if (button.id === "import-button")
        (state.page === "profiles"
          ? $("#icc-input")
          : $("#file-input")
        ).click();
      if (button.dataset.add) {
        if ($("#asset-dialog").open) $("#asset-dialog").close();
        addAsset(button.dataset.add);
      }
      if (button.dataset.inspect) await inspect(button.dataset.inspect);
      if (button.dataset.proof) openProof(button.dataset.proof);
      if (button.dataset.proofPage) {
        state.proofPage = Number(button.dataset.proofPage);
        paintProof();
      }
      if (button.dataset.libraryOffset !== undefined)
        loadLibrary(Number(button.dataset.libraryOffset));
      if (button.dataset.filmPage !== undefined) {
        state.previewPage = Number(button.dataset.filmPage);
        paintLayout();
      }
      if (button.dataset.rotate !== undefined) {
        const item = state.items[Number(button.dataset.rotate)];
        item.rotation = ((item.rotation || 0) + 90) % 360;
        render();
        scheduleLayout();
      }
      if (button.dataset.remove !== undefined) {
        state.items.splice(Number(button.dataset.remove), 1);
        render();
        scheduleLayout();
      }
      if (button.dataset.preview) {
        state.preview = button.dataset.preview;
        document.querySelectorAll("[data-preview]").forEach((b) => {
          b.classList.toggle("active", b.dataset.preview === state.preview);
          b.setAttribute(
            "aria-pressed",
            String(b.dataset.preview === state.preview),
          );
        });
        paintLayout();
      }
      if (button.dataset.cancel) {
        button.disabled = true;
        await post(`/api/studio/runs/${button.dataset.cancel}/cancel`, {});
        await poll();
      }
      if (button.dataset.reuse) {
        const run = state.runs.find((r) => r.id === button.dataset.reuse);
        state.settings = { ...defaults, ...run.request };
        delete state.settings.items;
        state.items = run.request.items.map((i) => ({ ...i }));
        navigate("studio");
        scheduleLayout();
      }
      if (button.dataset.background) {
        const tolerance = Number($("#background-tolerance").value);
        if (!Number.isInteger(tolerance) || tolerance < 0 || tolerance > 255)
          throw new Error("Informe tolerância de 0 a 255.");
        button.disabled = true;
        button.textContent = "Criando revisão…";
        const revision = await post(
          `/api/art/${button.dataset.background}/process`,
          { action: "background_simple", tolerance },
        );
        state.assets.unshift(revision);
        state.assetTotal += 1;
        $("#asset-dialog").close();
        addAsset(revision.id);
        toast("Nova revisão criada. A arte anterior foi preservada.");
      }
      const action = button.dataset.action;
      if (action === "reconnect") await initializeData();
      if (action === "retry-automation") await loadAutomation(true);
      if (action === "retry-library") loadLibrary(state.libraryOffset);
      if (action === "import") $("#file-input").click();
      if (action === "import-icc") $("#icc-input").click();
      if (action === "open-library") navigate("library");
      if (action === "prepare") navigate("studio");
      if (action === "profiles") navigate("profiles");
      if (action === "clear") {
        state.items = [];
        render();
        scheduleLayout();
      }
      if (action === "disable-hotfolder") {
        await api("/api/studio/hotfolder", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...state.hotfolder.settings, enabled: false }),
        });
        await loadAutomation(true);
        toast(
          "Pasta automática desativada. Os trabalhos já enfileirados continuam disponíveis.",
        );
      }
      if (action === "generate") await generate();
      if (action === "close-dialog") $("#asset-dialog").close();
      if (action === "dismiss-errors") {
        state.errors = [];
        render();
      }
    } catch (e) {
      button.disabled = false;
      toast(e.message);
    }
  });
  document.addEventListener("submit", async (event) => {
    if (event.target.id !== "hotfolder-form") return;
    event.preventDefault();
    const button = event.target.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      const settings = { ...state.settings };
      delete settings.name;
      await api("/api/studio/hotfolder", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...settings,
          enabled: true,
          folder: $("#hotfolder-path").value,
          art_width_mm: Number($("#hotfolder-width").value),
        }),
      });
      await loadAutomation(true);
      toast("Pasta automática ativada. Aguardando arquivos estáveis.");
    } catch (e) {
      toast(e.message);
      button.disabled = false;
    }
  });
  function updateInput(event) {
    const target = event.target;
    if (target.closest("#hotfolder-form")) state.automationDirty = true;
    if (target.id === "library-search") {
      state.search = target.value;
      state.libraryBusy = true;
      $("#library-results").innerHTML = libraryCards();
      clearTimeout(libraryTimer);
      librarySequence++;
      libraryTimer = setTimeout(() => loadLibrary(0), 250);
      return;
    }
    if (target.dataset.setting) {
      const key = target.dataset.setting;
      state.settings[key] =
        target.type === "checkbox"
          ? target.checked
          : key === "name"
            ? target.value
            : key === "profile_id"
              ? target.value || null
              : Number(target.value);
      if (key === "white_percent" && $("#white-value"))
        $("#white-value").value = `${target.value}%`;
      if (key === "name") {
        saveDraft();
        return;
      }
      scheduleLayout();
    }
    if (target.dataset.item !== undefined) {
      const item = state.items[Number(target.dataset.item)];
      if (!item) return;
      item[target.dataset.key] =
        target.value === "" ? null : Number(target.value);
      scheduleLayout();
    }
  }
  document.addEventListener("input", updateInput);
  // input events cover native selects and checkboxes in Chromium/WebView2.
  $("#file-input").addEventListener("change", (event) =>
    importFiles(event.target.files),
  );
  $("#icc-input").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    $("#import-button").disabled = true;
    try {
      const profile = await api("/api/studio/profiles", {
        method: "POST",
        body: form,
      });
      if (!state.profiles.some((p) => p.id === profile.id))
        state.profiles.push(profile);
      state.settings.profile_id = profile.id;
      saveDraft();
      render();
      scheduleLayout();
      toast("ICC CMYK validado e selecionado.");
    } catch (e) {
      toast(e.message);
    } finally {
      $("#icc-input").value = "";
      $("#import-button").disabled = false;
    }
  });
  document.addEventListener("dragover", (event) => {
    if (event.dataTransfer.types.includes("Files")) {
      event.preventDefault();
      $("#drop-zone")?.classList.add("dragover");
    }
  });
  document.addEventListener("dragleave", (event) => {
    if (!event.relatedTarget) $("#drop-zone")?.classList.remove("dragover");
  });
  document.addEventListener("drop", (event) => {
    if (!event.dataTransfer.files.length) return;
    event.preventDefault();
    $("#drop-zone")?.classList.remove("dragover");
    if (!$("#asset-dialog").open && state.page !== "profiles")
      importFiles(event.dataTransfer.files);
  });
  document.addEventListener(
    "error",
    (event) => {
      if (event.target.matches?.(".proof-image img"))
        event.target.parentElement.innerHTML =
          '<p class="setting-note">Não foi possível abrir a prova. Confira se o pacote está disponível ou gere a composição novamente.</p>';
    },
    true,
  );
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "o") {
      event.preventDefault();
      if (!$("#asset-dialog").open) $("#file-input").click();
    }
  });
  async function poll() {
    if (pollBusy) return;
    pollBusy = true;
    try {
      const runs = await api("/api/studio/runs", {
        conditional: true,
        cache: "no-store",
        headers: state.runsEtag ? { "If-None-Match": state.runsEtag } : {},
      });
      const changed =
        runs !== null && JSON.stringify(runs) !== JSON.stringify(state.runs);
      if (runs !== null) state.runs = runs;
      setOnline(true);
      updateBadges();
      if (changed && state.page === "runs") renderRuns();
      if (!state.initialized && !state.initializing) {
        await initializeData();
        return;
      }
      if (changed && state.page === "library" && !state.libraryBusy)
        loadLibrary(state.libraryOffset);
      if (state.page === "automation") {
        const latest = await api("/api/studio/hotfolder");
        state.hotfolder = latest;
        state.automationLoadError = "";
        if ($("#automation-error"))
          $("#automation-error").innerHTML = automationErrorMarkup();
        const container = $(".automation-receipts");
        if (!container && !state.automationDirty) render();
        if (container) {
          const scratch = document.createElement("div");
          scratch.innerHTML = automationMarkup();
          container.innerHTML = scratch.querySelector(
            ".automation-receipts",
          ).innerHTML;
        }
      }
    } catch (_) {
      setOnline(false);
    } finally {
      pollBusy = false;
    }
  }
  function tick() {
    $("#clock").textContent = new Date().toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  async function initializeData() {
    if (state.initializing) return;
    state.initializing = true;
    try {
      const [library, profiles, runs] = await Promise.all([
        api("/api/studio/library?limit=32"),
        api("/api/studio/profiles"),
        api("/api/studio/runs"),
      ]);
      mergeAssets(library.items);
      state.libraryItems = library.items;
      state.libraryTotal = library.total;
      state.assetTotal = library.total;
      state.profiles = profiles;
      state.runs = runs;
      await ensureAssets(state.items.map((i) => i.asset_id));
      const lost = state.items.filter((i) => !asset(i.asset_id)).length;
      state.items = state.items.filter((i) => asset(i.asset_id));
      if (lost)
        state.errors.push(
          "Algumas artes do rascunho não estão disponíveis neste servidor. Adicione-as novamente.",
        );
      if (
        state.settings.profile_id &&
        !profiles.some((p) => p.id === state.settings.profile_id)
      )
        state.settings.profile_id = null;
      state.initialized = true;
      setOnline(true);
      render();
      scheduleLayout();
      if (state.page === "library" && state.search) loadLibrary(0);
      if (state.page === "automation")
        loadAutomation().catch((e) => toast(e.message));
    } catch (error) {
      setOnline(false);
    } finally {
      state.initializing = false;
    }
  }
  function init() {
    render();
    tick();
    initializeData();
  }
  setInterval(() => {
    tick();
    if (!document.hidden) poll();
  }, 2000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) poll();
  });
  $("#asset-dialog").addEventListener("close", () => {
    inspectionSequence++;
  });
  const pageFromHash = () =>
    location.hash.slice(1) in titles ? location.hash.slice(1) : "studio";
  const syncLocation = () => {
    const page = pageFromHash();
    if (page !== state.page) navigate(page, false);
  };
  window.addEventListener("popstate", syncLocation);
  window.addEventListener("hashchange", syncLocation);
  state.page = pageFromHash();
  init();
})();
