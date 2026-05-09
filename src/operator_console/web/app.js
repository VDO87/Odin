const uiMode = {
  OPERATOR: "operator",
  TECHNICAL: "technical",
};

const routes = [
  "dashboard",
  "market",
  "risk",
  "decision",
  "execution",
  "portfolios",
  "market-data",
  "economic-calendar",
  "logs",
  "config",
  "commands",
  "integrations",
  "intelligence",
];

const routeTitles = {
  dashboard: "Dashboard",
  market: "Market",
  risk: "Risk",
  decision: "Decision",
  execution: "Execution",
  portfolios: "Portfolios",
  "market-data": "Market Data",
  "economic-calendar": "Economic Calendar",
  logs: "Logs",
  config: "Config",
  commands: "Commands",
  integrations: "Integrations",
  intelligence: "Intelligence",
};

const readOnlyCommands = new Set(["status", "health", "get-config", "validate-config", "external/status"]);
const criticalCommands = new Set(["pause", "resume", "stop"]);

let currentMode = uiMode.OPERATOR;
let currentRoute = "dashboard";
let pollTimer = null;
let pollMs = 2000;
let latestStatus = null;
let latestHealth = null;
let latestLogs = null;
let latestConfig = null;
let latestExternalStatus = null;
let latestExternalQuote = null;
let latestExternalQuoteGbp = null;
let latestExternalCalendar = null;
let latestExternalInject = null;
let latestIntelligence = null;
const marketGateHistory = [];
let lastCommandPayload = null;

const translations = {
  "ST-00": "Offline",
  "ST-10": "A arrancar",
  "ST-20": "Em espera",
  "ST-30": "Em monitorização",
  "ST-40": "Pronto",
  "ST-50": "Operação ativa",
  "ST-60": "Pausado",
  "ST-70": "Bloqueado por risco",
  "ST-80": "Bloqueado por falha",
  "ST-90": "Erro",
  "ST-100": "Em recuperação",
  "ST-120": "Manutenção",
  "MD-10": "Observação",
  "MD-20": "Demo",
  "MD-30": "Real",
  lite: "Leve",
  standard: "Standard",
  full: "Completo",
  blocked: "Bloqueado",
  starting: "A arrancar",
  monitoring: "Em monitorização",
  ready: "Pronto",
  active: "Ativo",
  ok: "OK",
  degraded: "Degradado",
  recovery_required: "Recuperação necessária",
  NOT_STARTED: "Sem heartbeat inicial",
  DELAYED: "Atrasado",
  TIMEOUT: "Timeout",
  UNAVAILABLE: "Indisponível",
  OK: "OK",
};

function byId(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const element = byId(id);
  if (!element) {
    return false;
  }
  element.textContent = value === null || value === undefined ? "" : String(value);
  return true;
}

function setHTML(id, html) {
  const element = byId(id);
  if (!element) {
    return false;
  }
  element.innerHTML = html;
  return true;
}

function setClass(id, className) {
  const element = byId(id);
  if (!element) {
    return false;
  }
  element.className = className;
  return true;
}

function setDisabled(id, disabled) {
  const element = byId(id);
  if (!element) {
    return false;
  }
  element.disabled = Boolean(disabled);
  return true;
}

function on(id, eventName, handler) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.addEventListener(eventName, handler);
}

function t(value) {
  if (value === null || value === undefined) {
    return "n/d";
  }
  const raw = String(value);
  return translations[raw] || raw;
}

function fmt(value) {
  return JSON.stringify(value, null, 2);
}

function fmtTs(value) {
  if (!value) {
    return "n/d";
  }
  const dt = new Date(String(value));
  if (Number.isNaN(dt.getTime())) {
    return String(value);
  }
  return dt.toISOString();
}

function quoteSourceMode(quote, statusPayload) {
  if (!quote || typeof quote !== "object") {
    return "n/d";
  }
  if (quote.from_cache) {
    return "CACHE";
  }
  const providers = Array.isArray(statusPayload?.providers) ? statusPayload.providers : [];
  const providerStatus = providers.find((provider) => provider.provider === quote.provider);
  if (providerStatus && providerStatus.source_type === "demo") {
    return "DEMO";
  }
  return "REAL";
}

function quoteQuality(quote) {
  if (!quote || typeof quote !== "object") {
    return "n/d";
  }
  if (quote.warning) {
    return `degradado (${quote.warning})`;
  }
  if (quote.from_cache) {
    return "cache";
  }
  if (quote.provider === "DemoProvider") {
    return "demo_sintetico";
  }
  return "real_provider";
}

async function fetchJson(url, options) {
  const response = await fetch(url, options || {});
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return {
      error: "invalid_json_response",
      reason_text: `unexpected content-type: ${contentType || "none"}`,
      status_code: response.status,
    };
  }
  return await response.json();
}

async function safeFetchJson(url, fallbackPayload) {
  try {
    const payload = await fetchJson(url);
    if (payload && !payload.error) {
      return payload;
    }
    return fallbackPayload;
  } catch (_error) {
    return fallbackPayload;
  }
}

function setMode(mode) {
  currentMode = mode;
  const operatorButton = byId("modeOperator");
  const technicalButton = byId("modeTechnical");
  if (operatorButton) {
    operatorButton.classList.toggle("active", mode === uiMode.OPERATOR);
  }
  if (technicalButton) {
    technicalButton.classList.toggle("active", mode === uiMode.TECHNICAL);
  }
  updatePageTechVisibility();
  renderCurrentRoute();
}

function updatePolling(ms) {
  pollMs = ms;
  if (pollTimer !== null) {
    clearInterval(pollTimer);
  }
  pollTimer = setInterval(refresh, pollMs);
}

function normalizeRoute(hash) {
  const candidate = String(hash || "").replace("#", "").trim().toLowerCase();
  if (routes.includes(candidate)) {
    return candidate;
  }
  return "dashboard";
}

function setActiveRoute(route) {
  currentRoute = route;
  setText("pageTitle", routeTitles[route] || "Dashboard");
  for (const section of document.querySelectorAll(".route-page")) {
    section.classList.add("hidden");
  }
  const target = byId(`page-${route}`);
  if (target) {
    target.classList.remove("hidden");
  }
  for (const link of document.querySelectorAll(".nav-link[data-route]")) {
    link.classList.toggle("active", link.dataset.route === route);
  }
  updatePageTechVisibility();
}

function applyRouteFromHash() {
  const route = normalizeRoute(window.location.hash);
  setActiveRoute(route);
  renderCurrentRoute();
}

function updatePageTechVisibility() {
  for (const section of document.querySelectorAll(".route-page")) {
    const visible = !section.classList.contains("hidden");
    const techBlocks = section.querySelectorAll(".page-tech");
    techBlocks.forEach((block) => {
      block.classList.toggle("hidden", !(visible && currentMode === uiMode.TECHNICAL));
    });
  }
}

function healthBucket(status) {
  if (status === "OK") {
    return "ok";
  }
  if (status === "DELAYED" || status === "NOT_STARTED") {
    return "degraded";
  }
  if (status === "TIMEOUT" || status === "UNAVAILABLE") {
    return "unavailable";
  }
  return "degraded";
}

function calculateHealthDistribution(liveness) {
  const summary = { ok: 0, degraded: 0, unavailable: 0, nodata: 0 };
  const modules = Object.keys(liveness || {});
  if (modules.length === 0) {
    summary.nodata = 1;
    return summary;
  }
  for (const moduleName of modules) {
    summary[healthBucket(String(liveness[moduleName]))] += 1;
  }
  return summary;
}

function renderHealthBars(liveness) {
  const summary = calculateHealthDistribution(liveness);
  const container = byId("healthBars");
  if (!container) {
    return summary;
  }

  const total = summary.ok + summary.degraded + summary.unavailable + summary.nodata;
  const rows = [
    { key: "ok", label: "OK", css: "bar-ok" },
    { key: "degraded", label: "Degraded", css: "bar-warn" },
    { key: "unavailable", label: "Unavailable", css: "bar-danger" },
    { key: "nodata", label: "Sem dados", css: "bar-nodata" },
  ];
  container.innerHTML = "";
  rows.forEach((row) => {
    const count = summary[row.key];
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    const element = document.createElement("div");
    element.className = "bar-row";
    element.innerHTML = `
      <span>${row.label}</span>
      <div class="bar-track"><div class="bar-fill ${row.css}" style="width:${pct}%"></div></div>
      <span>${count}</span>
    `;
    container.appendChild(element);
  });
  return summary;
}

function renderStateTimeline(globalState) {
  const timeline = byId("stateTimeline");
  if (!timeline) {
    return;
  }
  const ordered = ["ST-10", "ST-100", "ST-30", "ST-40", "ST-50"];
  const activeIndex = ordered.indexOf(globalState);
  timeline.innerHTML = "";
  ordered.forEach((stateCode, index) => {
    const step = document.createElement("div");
    step.className = "timeline-step";
    if (activeIndex >= 0 && index <= activeIndex) {
      step.classList.add("active");
    }
    step.textContent = t(stateCode);
    timeline.appendChild(step);
  });
}

function eventSeverity(event) {
  if (event.rejection_reason) {
    return "error";
  }
  if (criticalCommands.has(String(event.command || ""))) {
    return "warn";
  }
  return "info";
}

function summarizeSeverities(events) {
  const counts = { info: 0, warn: 0, error: 0, critical: 0 };
  events.forEach((event) => {
    const severity = eventSeverity(event);
    counts[severity] += 1;
  });
  return counts;
}

function renderSeverityCounters(events) {
  const container = byId("severityCounters");
  if (!container) {
    return;
  }
  const counts = summarizeSeverities(events);
  container.innerHTML = `
    <div class="severity-item severity-info"><span>Info</span><strong>${counts.info}</strong></div>
    <div class="severity-item severity-warn"><span>Warn</span><strong>${counts.warn}</strong></div>
    <div class="severity-item severity-error"><span>Error</span><strong>${counts.error}</strong></div>
    <div class="severity-item severity-critical"><span>Critical</span><strong>${counts.critical}</strong></div>
  `;
}

function filterUsefulEvents(events, technicalMode) {
  const source = Array.isArray(events) ? events : [];
  if (technicalMode) {
    return source.slice(-40).reverse();
  }
  return source
    .filter((event) => String(event.event_type || "").toLowerCase() !== "read_query")
    .filter((event) => !readOnlyCommands.has(String(event.command || "")))
    .filter((event, index, list) => {
      if (index === 0) {
        return true;
      }
      const previous = list[index - 1];
      return !(
        previous.command === event.command &&
        previous.accepted === event.accepted &&
        previous.rejection_reason === event.rejection_reason
      );
    })
    .slice(-20)
    .reverse();
}

function renderEventList(listId, events) {
  const list = byId(listId);
  if (!list) {
    return;
  }
  list.innerHTML = "";
  if (events.length === 0) {
    list.innerHTML = "<li>Sem eventos relevantes.</li>";
    return;
  }
  events.forEach((event) => {
    const li = document.createElement("li");
    const state = event.accepted ? "aceite" : "rejeitado";
    const reason = event.rejection_reason ? ` (${event.rejection_reason})` : "";
    li.textContent = `${event.completed_at_utc || "n/d"} | ${event.command} | ${state}${reason}`;
    list.appendChild(li);
  });
}

function renderModuleTable(liveness) {
  const body = byId("moduleHealthBody");
  if (!body) {
    return;
  }
  body.innerHTML = "";
  const modules = Object.keys(liveness || {}).sort();
  if (modules.length === 0) {
    body.innerHTML = "<tr><td colspan='4'>Sem módulos reportados.</td></tr>";
    return;
  }

  modules.forEach((moduleName) => {
    const status = String(liveness[moduleName]);
    let rowClass = "health-row-warn";
    let explanation = "Estado não mapeado.";
    let action = "Rever telemetria.";
    if (status === "OK") {
      rowClass = "health-row-ok";
      explanation = "Heartbeat normal.";
      action = "Sem ação.";
    } else if (status === "DELAYED") {
      explanation = "Heartbeat atrasado.";
      action = "Monitorizar estabilidade.";
    } else if (status === "NOT_STARTED") {
      explanation = "Sem heartbeat inicial.";
      action = "Confirmar arranque do módulo.";
    } else if (status === "TIMEOUT" || status === "UNAVAILABLE") {
      rowClass = "health-row-danger";
      explanation = status === "TIMEOUT" ? "Timeout de heartbeat." : "Módulo indisponível.";
      action = "Validar módulo e preparar recovery.";
    }
    if (["MARKET", "RISK", "EXEC"].includes(moduleName) && status !== "OK") {
      rowClass = "health-row-danger";
    }
    const row = document.createElement("tr");
    row.className = rowClass;
    row.innerHTML = `
      <td>${moduleName}</td>
      <td>${t(status)}</td>
      <td>${explanation}</td>
      <td>${action}</td>
    `;
    body.appendChild(row);
  });
}

function renderMarketCanvas() {
  const canvas = byId("marketCanvas");
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#2b3531";
  ctx.lineWidth = 1;
  for (let i = 1; i < 5; i += 1) {
    const y = (height / 5) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  ctx.strokeStyle = "#14b8a6";
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i <= 45; i += 1) {
    const x = (width / 45) * i;
    const y = height * 0.52 + Math.sin(i / 4) * 14;
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();
}

function buildDiagnosis(status, health, events) {
  const panel = byId("diagnostic");
  const headline = byId("diagnosisHeadline");
  const issuesList = byId("diagnosisIssues");
  const actionsList = byId("diagnosisActions");
  if (!panel || !headline || !issuesList || !actionsList) {
    return;
  }

  const issues = [];
  const actions = [];
  const liveness = health.liveness || {};
  const missing = health.startup_missing_heartbeat_modules || [];
  const unavailable = health.startup_unavailable_modules || [];
  const nonOk = Object.entries(liveness)
    .filter((entry) => entry[1] !== "OK")
    .map((entry) => `${entry[0]}=${t(entry[1])}`);

  if (status.kill_active) {
    issues.push("Kill switch ativo.");
    actions.push("Investigar causa do kill antes de retoma.");
  }
  if ((status.active_block_count || 0) > 0) {
    issues.push(`Existem ${status.active_block_count} bloqueios ativos.`);
    actions.push("Remover bloqueios apenas após diagnóstico.");
  }
  if (missing.length > 0) {
    issues.push(`Módulos sem heartbeat inicial: ${missing.join(", ")}.`);
    actions.push("Confirmar arranque dos módulos críticos.");
  }
  if (unavailable.length > 0) {
    issues.push(`Módulos indisponíveis: ${unavailable.join(", ")}.`);
    actions.push("Restaurar módulos indisponíveis.");
  }
  if (nonOk.length > 0) {
    issues.push(`Liveness degradada: ${nonOk.join(" | ")}.`);
    actions.push("Validar heartbeat e conectividade.");
  }
  if (events.some((event) => event.rejection_reason)) {
    issues.push("Há comandos recentes rejeitados.");
    actions.push("Rever reason_code dos comandos rejeitados.");
  }

  const readyToOperate =
    ["ST-40", "ST-50"].includes(status.global_state) &&
    !status.kill_active &&
    (status.active_block_count || 0) === 0 &&
    nonOk.length === 0;

  panel.classList.remove("ok", "warn", "danger");
  if (readyToOperate) {
    panel.classList.add("ok");
    headline.textContent = "Odin pronto para operar.";
    if (actions.length === 0) {
      actions.push("Manter monitorização contínua.");
    }
  } else {
    panel.classList.add(issues.length > 2 ? "danger" : "warn");
    headline.textContent = "Odin não está pronto para operar.";
    if (issues.length === 0) {
      issues.push(`Estado atual: ${t(status.global_state)}.`);
      actions.push("Aguardar convergência para estado pronto.");
    }
  }

  issuesList.innerHTML = "";
  actionsList.innerHTML = "";
  issues.forEach((issue) => {
    const li = document.createElement("li");
    li.textContent = issue;
    issuesList.appendChild(li);
  });
  actions.forEach((action) => {
    const li = document.createElement("li");
    li.textContent = action;
    actionsList.appendChild(li);
  });
}

function buildHealthLabel(status, healthSummary) {
  if (healthSummary.unavailable > 0 || status.kill_active || status.active_block_count > 0) {
    return "Bloqueado";
  }
  if (healthSummary.degraded > 0) {
    return "Degradado";
  }
  if (healthSummary.ok > 0) {
    return "OK";
  }
  return "Sem dados";
}

function renderExternalDataCards() {
  const quotePayload = latestExternalQuote || {};
  const calendarPayload = latestExternalCalendar || {};
  const statusPayload = latestExternalStatus || {};

  const quote = quotePayload.quote || {};
  const nextEvent = calendarPayload.next_event || {};
  const providers = Array.isArray(statusPayload.providers) ? statusPayload.providers : [];
  const healthyCount = providers.filter((provider) => provider.healthy).length;
  const totalCount = providers.length;
  const cache = statusPayload.cache || quotePayload.cache || {};
  const warnings = Array.isArray(statusPayload.warnings) ? statusPayload.warnings : [];
  const activeProvider = quote.provider || "n/d";
  const sourceMode = quoteSourceMode(quote, statusPayload);
  const quality = quoteQuality(quote);
  const market = latestStatus?.market_runtime || {};
  const feedsMarket = (
    market.last_instrument_id === quote.symbol &&
    market.last_feed_id === "primary" &&
    market.last_gate_status !== "idle"
  )
    ? `Sim (${market.last_gate_status})`
    : "Não";

  const quoteText = quote.last_price !== undefined && quote.last_price !== null
    ? `${quote.last_price}${quote.from_cache ? " (cache)" : ""}`
    : "n/d";
  setText("externalEurUsdPrice", quoteText);

  const eventText = nextEvent.title
    ? `${nextEvent.title} @ ${nextEvent.event_time_utc || "n/d"}`
    : "Sem eventos";
  setText("externalNextMacroEvent", eventText);
  setText("externalActiveProvider", activeProvider);
  setText("externalSourceMode", sourceMode);
  setText("externalLastUpdate", fmtTs(quote.timestamp_utc));
  setText("externalDataQuality", quality);

  setText("externalProviderHealth", `${healthyCount}/${totalCount} healthy`);
  setText(
    "externalCacheState",
    `entries=${cache.entries ?? "n/d"} | hits=${cache.hits ?? "n/d"} | misses=${cache.misses ?? "n/d"}`,
  );
  setText("externalFeedsMarket", feedsMarket);
  setText(
    "externalProviderWarning",
    warnings.length > 0 ? warnings.join(" | ") : "Providers reais configurados",
  );
}

function renderDashboard(view) {
  const status = view.status;
  const health = view.health;
  const events = view.events;
  const healthSummary = renderHealthBars(health.liveness || {});

  renderStateTimeline(status.global_state);
  renderSeverityCounters(events);
  renderModuleTable(health.liveness || {});

  setText("generalState", t(status.global_state));
  setText("generalMode", t(status.mode));
  setText("generalProfile", t(status.profile));
  setText("generalKill", status.kill_active ? "Ativo" : "Inativo");
  setText("generalBlocks", String(status.active_block_count || 0));
  setText("generalHealth", buildHealthLabel(status, healthSummary));

  const marketRuntime = status.market_runtime || {};
  setText(
    "miniMarket",
    `${marketRuntime.last_gate_status || "idle"}${marketRuntime.last_rejection_reason ? ` (${marketRuntime.last_rejection_reason})` : ""}`,
  );

  const riskSummary = status.risk_summary || {};
  setText("miniRisk", riskSummary.risk_block_active ? "Bloqueado" : "Sem bloqueio");

  const decisionSummary = status.decision_last_result || {};
  setText(
    "miniDecision",
    decisionSummary.operational_output
      ? `${decisionSummary.operational_output}${decisionSummary.reason_summary ? ` (${decisionSummary.reason_summary})` : ""}`
      : (decisionSummary.reason_summary || "Sem decisão recente"),
  );

  const execSummary = status.execution_summary || {};
  setText("miniExecution", execSummary.ledger_available ? "Ledger disponível" : "Sem ledger");

  const criticalEvents = events
    .filter((event) => event.rejection_reason || criticalCommands.has(String(event.command || "")))
    .slice(0, 10);
  renderEventList("dashboardCriticalEvents", criticalEvents);
  buildDiagnosis(status, health, events);
  renderExternalDataCards();
}

function renderMarket(view) {
  const status = view.status;
  const market = status.market_runtime || {};
  const gate = String(market.last_gate_status || "idle");
  const readiness = status.readiness || "n/d";
  setText(
    "marketSummary",
    gate === "idle"
      ? "Sem dados de mercado ainda."
      : `Gate atual: ${gate}${market.last_rejection_reason ? ` (${market.last_rejection_reason})` : ""}.`,
  );
  setText("marketInstrument", market.last_instrument_id || (market.instrument_scope || []).join(", ") || "n/d");
  setText("marketFeed", market.last_feed_id || (market.feed_scope || []).join(", ") || "n/d");
  setText("marketGate", gate);
  setText(
    "marketRestrictions",
    (market.applied_restrictions || market.active_restrictions || []).join(", ") || "nenhuma",
  );
  setText("marketLastGateStatus", gate);
  setText("marketLastRejection", market.last_rejection_reason || "n/d");
  setText("marketReadinessResult", readiness);

  const historyLine = `${new Date().toISOString()} | gate=${gate}${market.last_rejection_reason ? ` | reason=${market.last_rejection_reason}` : ""}`;
  if (marketGateHistory.length === 0 || marketGateHistory[marketGateHistory.length - 1] !== historyLine) {
    marketGateHistory.push(historyLine);
    if (marketGateHistory.length > 30) {
      marketGateHistory.shift();
    }
  }
  const list = byId("marketGateHistory");
  if (list) {
    list.innerHTML = "";
    marketGateHistory
      .slice()
      .reverse()
      .forEach((entry) => {
        const li = document.createElement("li");
        li.textContent = entry;
        list.appendChild(li);
      });
  }

  renderMarketCanvas();
}

function renderRisk(view) {
  const status = view.status;
  const risk = status.risk_summary || {};
  setText("riskState", risk.risk_block_active ? "Bloqueado" : "Sem bloqueio");
  setText("riskKillState", status.kill_active ? "Kill ativo" : "Kill inativo");
  setText("riskCount", String(risk.active_block_count || 0));
  setText("riskReason", risk.dominant_block_reason || "n/d");
  setText("riskCooldown", "n/d");
  setText("riskLimits", "n/d");

  const fill = byId("riskGaugeFill");
  if (!fill) {
    return;
  }
  const count = Number(risk.active_block_count || 0);
  const pct = Math.min(100, count * 20 + (risk.risk_block_active ? 35 : 0));
  fill.style.width = `${pct}%`;
  if (pct < 35) {
    fill.style.background = "var(--ok)";
  } else if (pct < 70) {
    fill.style.background = "var(--warn)";
  } else {
    fill.style.background = "var(--danger)";
  }
}

function renderDecision(view) {
  const status = view.status;
  const decision = status.decision_last_result || {};
  const executionSummary = status.execution_summary || {};
  const execution = executionSummary.last_execution || {};
  setText("decisionResult", decision.operational_output || decision.reason_summary || "Sem decisão recente");
  setText("decisionCycle", decision.decision_cycle_id || "n/d");
  setText("decisionTactic", decision.tactic_id || execution.request_payload?.tactic_id || "n/d");
  setText("decisionScore", decision.score ?? "n/d");
  setText("decisionRationale", decision.reason_summary || execution.reason_summary || "n/d");
  setText("decisionIntent", decision.intent_id || execution.intent_id ? "Emitida" : "Não emitida");
  setText("decisionExecutedDemo", decision.executed_in_demo ? "Sim" : "Não");
  setText("decisionBlockedReason", decision.reason_summary || execution.reason_summary || "n/d");
}

function renderExecution(view) {
  const status = view.status;
  const executionSummary = status.execution_summary || {};
  const latest = executionSummary.last_execution || {};

  setText("mt5ExecutionFocus", "FOCO INICIAL: FOREX + AUTO_DEMO");
  setText("xtbExecutionFocus", "ASSISTIDO: ETFs/Ações/FIRE via Telegram + confirmação humana");
  setText("manualExecutionFocus", "MANUAL_CONFIRMATION via CommandGateway");

  setText("execLedger", executionSummary.ledger_available ? "Disponível" : "Sem ledger");
  setText("execState", latest.exec_state || "n/d");
  setText("execSlippage", latest.slippage_value ?? "n/d");
  setText("execDivergence", latest.snapshot_payload?.divergence_flag ?? "n/d");
  setText("execIntentId", latest.intent_id || "n/d");
  setText("execRequestId", latest.request_id || "n/d");
  setText("execReason", latest.reason_summary || "n/d");

  const rows = byId("executionRows");
  if (!rows) {
    return;
  }
  rows.innerHTML = "";
  const recent = executionSummary.recent_executions || (latest.intent_id ? [latest] : []);
  if (recent.length === 0) {
    rows.innerHTML = "<tr><td colspan='5'>Sem execuções recentes.</td></tr>";
    return;
  }
  recent.forEach((entry) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${entry.recorded_at_utc || "n/d"}</td>
      <td>${entry.exec_state || "n/d"}</td>
      <td>${entry.intent_id || "n/d"}</td>
      <td>${entry.request_id || "n/d"}</td>
      <td>${entry.reason_summary || "n/d"}</td>
    `;
    rows.appendChild(tr);
  });
}

function renderPortfolios() {
  setText("portfolioForex", "SHORT_TERM_TRADING | FOREX | venue preferencial MT5 (demo)");
  setText("portfolioEtf", "MEDIUM_TERM_3_5Y | ETF | XTB assisted (advisory)");
  setText("portfolioStock", "MEDIUM_TERM_3_5Y | STOCK | XTB assisted (advisory)");
  setText("portfolioFire", "FIRE_LONG_TERM | ETF/STOCK | confirmação humana");
  setText("portfolio3to5y", "MEDIUM_TERM_3_5Y | advisory + confirmação humana");
}

function renderMarketData() {
  const statusPayload = latestExternalStatus || {};
  const quotePayload = latestExternalQuote || {};
  const quotePayloadGbp = latestExternalQuoteGbp || {};
  const calendarPayload = latestExternalCalendar || {};
  const providers = Array.isArray(statusPayload.providers) ? statusPayload.providers : [];
  const cache = statusPayload.cache || quotePayload.cache || {};
  const warnings = Array.isArray(statusPayload.warnings) ? statusPayload.warnings : [];
  const quote = quotePayload.quote || {};
  const quoteGbp = quotePayloadGbp.quote || {};
  const nextEvent = calendarPayload.next_event || {};
  const events = Array.isArray(calendarPayload.events) ? calendarPayload.events : [];
  const healthyCount = providers.filter((provider) => provider.healthy).length;
  const realProviders = providers.filter((provider) => provider.source_type === "external");
  const realEnabled = realProviders.filter((provider) => provider.enabled);
  const realConfigured = realEnabled.filter((provider) => provider.configured);
  const market = latestStatus?.market_runtime || {};
  const feedsMarket = (
    market.last_instrument_id === quote.symbol &&
    market.last_feed_id === "primary" &&
    market.last_gate_status !== "idle"
  )
    ? `Sim (${market.last_gate_status})`
    : "Não";

  setText("marketDataProviderHealth", `${healthyCount}/${providers.length} healthy`);
  setText(
    "marketDataCacheState",
    `entries=${cache.entries ?? "n/d"} | hits=${cache.hits ?? "n/d"} | misses=${cache.misses ?? "n/d"}`,
  );
  setText(
    "marketDataRealStatus",
    realEnabled.length === 0
      ? "desativado (modo/profile)"
      : `${realConfigured.length}/${realEnabled.length} configurado`,
  );
  setText(
    "marketDataApiKeysWarning",
    warnings.length > 0 ? warnings.join(" | ") : "ok",
  );
  setText("marketDataEurUsd", quote.last_price ?? "n/d");
  setText("marketDataGbpUsd", quoteGbp.last_price ?? "n/d");
  setText("marketDataQuoteSource", `${quote.provider || "n/d"} | ${quoteSourceMode(quote, statusPayload)}`);
  setText("marketDataQuoteUpdated", fmtTs(quote.timestamp_utc));
  setText("marketDataQuoteQuality", quoteQuality(quote));
  setText("marketDataFeedToMarket", feedsMarket);
  setText(
    "marketDataCalendarNext",
    nextEvent?.title ? `${nextEvent.title} @ ${nextEvent.event_time_utc || "n/d"}` : "Sem eventos",
  );

  const providerList = byId("marketDataProviderList");
  if (providerList) {
    providerList.innerHTML = "";
    if (providers.length === 0) {
      providerList.innerHTML = "<li>Sem providers reportados.</li>";
    } else {
      providers.forEach((provider) => {
        const li = document.createElement("li");
        li.textContent = `${provider.provider} | type=${provider.source_type} | enabled=${provider.enabled} | configured=${provider.configured} | healthy=${provider.healthy}`;
        providerList.appendChild(li);
      });
    }
  }

  const calendarList = byId("marketDataCalendarList");
  if (calendarList) {
    calendarList.innerHTML = "";
    if (events.length === 0) {
      calendarList.innerHTML = "<li>Sem eventos.</li>";
    } else {
      events.slice(0, 10).forEach((event) => {
        const li = document.createElement("li");
        li.textContent = `${event.event_time_utc || "n/d"} | ${event.country || "n/d"} | ${event.title || "n/d"} | impact=${event.impact || "n/d"}`;
        calendarList.appendChild(li);
      });
    }
  }
}

function renderEconomicCalendar() {
  const statusPayload = latestExternalStatus || {};
  const calendarPayload = latestExternalCalendar || {};
  const providers = Array.isArray(statusPayload.providers) ? statusPayload.providers : [];
  const events = Array.isArray(calendarPayload.events) ? calendarPayload.events : [];
  const nextEvent = calendarPayload.next_event || {};
  const calendarProvider = providers.find((provider) => provider.provider === "TradingEconomics");

  setText(
    "economicCalendarNext",
    nextEvent?.title ? `${nextEvent.title} @ ${nextEvent.event_time_utc || "n/d"}` : "Sem eventos",
  );
  if (calendarProvider) {
    setText(
      "economicCalendarProviderStatus",
      `TradingEconomics enabled=${calendarProvider.enabled} configured=${calendarProvider.configured} healthy=${calendarProvider.healthy}`,
    );
  } else {
    setText("economicCalendarProviderStatus", "TradingEconomics indisponível, fallback demo");
  }

  const list = byId("economicCalendarList");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  if (events.length === 0) {
    list.innerHTML = "<li>Sem eventos.</li>";
    return;
  }
  events.slice(0, 20).forEach((event) => {
    const li = document.createElement("li");
    li.textContent = `${event.event_time_utc || "n/d"} | ${event.country || "n/d"} | ${event.title || "n/d"} | impact=${event.impact || "n/d"}`;
    list.appendChild(li);
  });
}

function renderLogs(view) {
  const events = view.events;
  const severityElement = byId("logSeverity");
  const moduleElement = byId("logModule");
  const selectedSeverity = severityElement ? severityElement.value : "all";
  const selectedModule = moduleElement ? moduleElement.value : "all";

  const rows = byId("logRows");
  if (!rows) {
    return;
  }
  rows.innerHTML = "";
  const filtered = events.filter((event) => {
    const severity = eventSeverity(event);
    const module = "OPERATOR_CONSOLE";
    if (selectedSeverity !== "all" && severity !== selectedSeverity) {
      return false;
    }
    if (selectedModule !== "all" && module !== selectedModule) {
      return false;
    }
    return true;
  });
  if (filtered.length === 0) {
    rows.innerHTML = "<tr><td colspan='5'>Sem eventos para os filtros atuais.</td></tr>";
    return;
  }
  filtered.forEach((event) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${event.completed_at_utc || "n/d"}</td>
      <td>${eventSeverity(event)}</td>
      <td>OPERATOR_CONSOLE</td>
      <td>${event.command || "n/d"}</td>
      <td>${event.accepted ? "accepted" : `rejected (${event.rejection_reason || "n/d"})`}</td>
    `;
    rows.appendChild(tr);
  });
}

function renderConfig(view) {
  const config = view.config;
  const status = view.status;
  const response = config.response || {};
  const active = response.active_config || {};
  const staged = response.staged_patch;
  const core = active.core || {};
  const runtime = active.runtime || {};
  setText(
    "configSummary",
    `profile=${status?.profile || "n/d"} | startup_timeout_ms=${core.startup_timeout_ms || "n/d"} | heartbeat_timeout_ms=${core.heartbeat_timeout_ms || "n/d"} | state_dir=${runtime.state_dir || "n/d"}`,
  );
  setText("stagedConfigSummary", staged ? fmt(staged) : "Sem staged config ativa.");
}

function updateCommandButtons(status) {
  const blockedStates = new Set(["ST-00", "ST-10", "ST-80", "ST-90", "ST-100"]);
  const blocked = blockedStates.has(status.global_state);
  setDisabled("pauseBtn", blocked || status.global_state === "ST-60");
  setDisabled("dashPauseBtn", blocked || status.global_state === "ST-60");
  setDisabled("resumeBtn", blocked || status.global_state !== "ST-60");
  setDisabled("dashResumeBtn", blocked || status.global_state !== "ST-60");
  setDisabled("stopBtn", blocked);
  setDisabled("dashStopBtn", blocked);
}

function renderCommands(view) {
  updateCommandButtons(view.status);
}

function renderIntegrations() {
  setText("integrationMt5", "Adapter preferencial inicial para Forex/demo");
  setText("integrationXtb", "Workflow assistido (real execution não ativo)");
  setText("integrationTelegram", "Bridge only: sem execução direta");
  setText("integrationOpenai", "Advisory only");
  setText("integrationProviders", "External providers via ExternalDataService");
}

function renderIntelligence() {
  setText("intelligenceAdvisoryWarning", "Advisory only: não altera estado operacional.");
  const advisory = latestIntelligence || {};
  setText("intelligenceProvider", advisory.provider || "AnythingLLM");
  setText("intelligenceAccepted", advisory.accepted === true ? "accepted" : advisory.accepted === false ? "rejected" : "n/d");
  setText("intelligenceReasonCode", advisory.reason_code || "n/d");
  setText("intelligenceQueryScope", advisory.query_scope || "n/d");
  setText("intelligenceAnswer", advisory.answer || advisory.reason_code || "Sem resposta ainda.");
  setText("intelligenceContext", Array.isArray(advisory.used_context) ? advisory.used_context.join(", ") || "n/d" : "n/d");

  const sources = Array.isArray(advisory.sources) ? advisory.sources : [];
  const list = byId("intelligenceSources");
  if (list) {
    list.innerHTML = "";
    if (sources.length === 0) {
      list.innerHTML = "<li>Sem fontes reportadas.</li>";
    } else {
      sources.forEach((source) => {
        const li = document.createElement("li");
        const ref = source.ref ? ` (${source.ref})` : "";
        li.textContent = `${source.kind || "source"}: ${source.summary || "n/d"}${ref}`;
        list.appendChild(li);
      });
    }
  }
}

function publishCommandResult(text) {
  setText("commandResult", text);
  setText("commandResultDashboard", text);
}

function formatCommandResult(result) {
  const reason = result.reason_code || result.rejection_reason || "n/d";
  const ts = result.completed_at_utc || new Date().toISOString();
  if (result.accepted) {
    return `accepted | command=${result.command} | reason_code=n/a | timestamp=${ts}`;
  }
  if (reason === "runtime_not_active") {
    return `rejected | command=${result.command} | reason_code=runtime_not_active | timestamp=${ts} | runtime offline`;
  }
  return `rejected | command=${result.command} | reason_code=${reason} | timestamp=${ts}`;
}

function renderTechnicalForRoute(route, view) {
  if (currentMode !== uiMode.TECHNICAL) {
    return;
  }
  if (route === "dashboard") {
    setText(
      "techDashboard",
      fmt({
        status: view.status,
        health: view.health,
        events: view.events,
        external: {
          status: latestExternalStatus,
          quote_eurusd: latestExternalQuote,
          quote_gbpusd: latestExternalQuoteGbp,
          calendar: latestExternalCalendar,
          last_inject: latestExternalInject,
        },
      }),
    );
  } else if (route === "market") {
    setText("techMarket", fmt(view.status.market_runtime || {}));
  } else if (route === "risk") {
    setText("techRisk", fmt(view.status.risk_summary || {}));
  } else if (route === "decision") {
    setText("techDecision", fmt(view.status.decision_last_result || {}));
  } else if (route === "execution") {
    setText("techExecution", fmt(view.status.execution_summary || {}));
  } else if (route === "portfolios") {
    setText(
      "techPortfolios",
      fmt({
        buckets: {
          forex_trading: "SHORT_TERM_TRADING",
          etf: "MEDIUM_TERM_3_5Y",
          stock: "MEDIUM_TERM_3_5Y",
          fire_reforma: "FIRE_LONG_TERM",
          horizon_3_5y: "MEDIUM_TERM_3_5Y",
        },
        policy: {
          xtb_real_execution_active: false,
          telegram_direct_execution_allowed: false,
          medium_long_term_requires_human_confirmation: true,
        },
      }),
    );
  } else if (route === "market-data") {
    setText(
      "techMarketData",
      fmt({
        status: latestExternalStatus,
        quote_eurusd: latestExternalQuote,
        quote_gbpusd: latestExternalQuoteGbp,
        calendar: latestExternalCalendar,
        last_inject: latestExternalInject,
      }),
    );
  } else if (route === "economic-calendar") {
    setText("techEconomicCalendar", fmt(latestExternalCalendar || {}));
  } else if (route === "logs") {
    setText("techLogs", fmt(view.logs));
  } else if (route === "config") {
    setText("techConfig", fmt(view.config));
  } else if (route === "commands") {
    setText("techCommands", fmt(lastCommandPayload));
  } else if (route === "integrations") {
    setText("techIntegrations", fmt({ status: "development_placeholder" }));
  } else if (route === "intelligence") {
    setText("techIntelligence", fmt(latestIntelligence || { status: "no_advisory_response" }));
  }
}

function buildViewModel() {
  const sourceEvents =
    currentMode === uiMode.TECHNICAL
      ? latestLogs?.technical_recent_events || latestLogs?.recent_events || []
      : latestLogs?.operator_recent_events || latestLogs?.recent_events || [];
  const usefulEvents = filterUsefulEvents(sourceEvents, currentMode === uiMode.TECHNICAL);
  return {
    status: latestStatus,
    health: latestHealth,
    logs: latestLogs,
    config: latestConfig,
    events: usefulEvents,
  };
}

function renderCurrentRoute() {
  if (!latestStatus || !latestHealth || !latestLogs || !latestConfig) {
    return;
  }
  const view = buildViewModel();

  if (currentRoute === "dashboard") {
    renderDashboard(view);
  } else if (currentRoute === "market") {
    renderMarket(view);
  } else if (currentRoute === "risk") {
    renderRisk(view);
  } else if (currentRoute === "decision") {
    renderDecision(view);
  } else if (currentRoute === "execution") {
    renderExecution(view);
  } else if (currentRoute === "portfolios") {
    renderPortfolios(view);
  } else if (currentRoute === "market-data") {
    renderMarketData(view);
  } else if (currentRoute === "economic-calendar") {
    renderEconomicCalendar(view);
  } else if (currentRoute === "logs") {
    renderLogs(view);
  } else if (currentRoute === "config") {
    renderConfig(view);
  } else if (currentRoute === "commands") {
    renderCommands(view);
  } else if (currentRoute === "integrations") {
    renderIntegrations(view);
  } else if (currentRoute === "intelligence") {
    renderIntelligence(view);
  }

  renderTechnicalForRoute(currentRoute, view);
}

async function refresh() {
  try {
    const [status, health, logs, config] = await Promise.all([
      fetchJson("/api/status"),
      fetchJson("/api/health"),
      fetchJson("/api/logs/recent"),
      fetchJson("/api/config"),
    ]);
    if (status.error || health.error || logs.error || config.error) {
      publishCommandResult(
        `Erro de endpoint: ${status.reason_text || health.reason_text || logs.reason_text || config.reason_text || "falha"}`,
      );
      setText("diagnosisHeadline", "Falha ao ler dados da consola.");
      return;
    }

    latestStatus = status;
    latestHealth = health;
    latestLogs = logs;
    latestConfig = config;
    [
      latestExternalStatus,
      latestExternalQuote,
      latestExternalQuoteGbp,
      latestExternalCalendar,
    ] = await Promise.all([
      safeFetchJson("/api/external/status", {
        providers: [],
        cache: {},
        warnings: ["external_status_unavailable"],
      }),
      safeFetchJson("/api/external/quote?symbol=EURUSD", {
        quote: {},
        cache: {},
        warnings: ["external_quote_unavailable"],
      }),
      safeFetchJson("/api/external/quote?symbol=GBPUSD", {
        quote: {},
        cache: {},
        warnings: ["external_quote_unavailable"],
      }),
      safeFetchJson("/api/external/calendar", {
        events: [],
        next_event: null,
        cache: {},
        warnings: ["external_calendar_unavailable"],
      }),
    ]);

    renderCurrentRoute();
  } catch (error) {
    publishCommandResult(`Erro ao atualizar: ${String(error)}`);
  }
}

async function injectDemoQuoteToMarket() {
  const payload = {
    requested_by: "trader-console-ui",
    role: "operator",
    authorization_context: { ticket: "trader-console-ui" },
  };
  const result = await fetchJson("/api/external/inject-demo-quote-to-market", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (result.error) {
    setText(
      "marketDataInjectResult",
      `Falha inject-demo-quote-to-market: ${result.reason_text || result.error}`,
    );
  } else {
    latestExternalInject = result;
    setText(
      "marketDataInjectResult",
      `Inject ${result.accepted ? "accepted" : "rejected"} | gate=${result.gate_status || "n/d"} | reason=${result.reason || "n/d"}`,
    );
  }
  await refresh();
}

async function runDecisionCycle() {
  const result = await fetchJson("/api/test/run-decision-cycle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requested_by: "trader-console-ui",
      role: "operator",
      mode: "test",
    }),
  });
  if (result.error) {
    setText("decisionRunResult", `Falha run-decision-cycle: ${result.reason_text || result.error}`);
  } else {
    const decision = result.decision_summary || result.decision || {};
    setText(
      "decisionRunResult",
      `cycle=${decision.decision_cycle_id || "n/d"} | output=${decision.operational_output || decision.decision_output || "n/d"} | accepted=${result.accepted ? "true" : "false"} | reason=${decision.reason_summary || "n/d"} | ledger=${decision.execution_ledger_ref || "n/d"}`,
    );
  }
  await refresh();
}

async function askIntelligence() {
  const questionInput = byId("intelligenceQuestion");
  const question = String((questionInput && questionInput.value) || "").trim();
  if (!question) {
    setText("intelligenceAnswer", "Pergunta obrigatória.");
    return;
  }
  const result = await fetchJson("/api/intelligence/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      requested_by: "trader-console-ui",
      role: "operator",
    }),
  });
  if (result.error) {
    latestIntelligence = {
      accepted: false,
      provider: "AnythingLLM",
      reason_code: result.reason_text || result.error,
      answer: null,
      sources: [],
      used_context: [],
      query_scope: null,
    };
  } else {
    latestIntelligence = result;
  }
  renderCurrentRoute();
}

async function postCommand(command) {
  const needsConfirm = criticalCommands.has(command);
  const confirmed = needsConfirm ? window.confirm(`Confirmar comando crítico ${command}?`) : true;
  const payload = {
    confirmation: confirmed,
    requested_by: "trader-console-ui",
    role: "operator",
    authorization_context: { ticket: "trader-console-ui" },
  };
  const endpoint = command === "status" || command === "validate-config" ? "/api/config" : `/api/commands/${command}`;

  let result;
  if (command === "status") {
    result = await fetchJson("/api/status");
    if (result.error) {
      publishCommandResult(`Erro no comando status: ${result.reason_text || result.error}.`);
    } else {
      lastCommandPayload = {
        accepted: true,
        command: "status",
        reason_code: null,
        completed_at_utc: new Date().toISOString(),
      };
      publishCommandResult(
        `accepted | command=status | reason_code=n/a | timestamp=${new Date().toISOString()}`,
      );
    }
  } else if (command === "validate-config") {
    result = await fetchJson("/api/config");
    if (result.error) {
      publishCommandResult(
        `Erro no comando validate-config: ${result.reason_text || result.error}.`,
      );
    } else {
      lastCommandPayload = {
        accepted: true,
        command: "validate-config",
        reason_code: null,
        completed_at_utc: new Date().toISOString(),
      };
      publishCommandResult(
        `accepted | command=validate-config | reason_code=n/a | timestamp=${new Date().toISOString()}`,
      );
    }
  } else {
    result = await fetchJson(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (result.error) {
      publishCommandResult(`Erro no comando ${command}: ${result.reason_text || result.error}.`);
    } else {
      publishCommandResult(formatCommandResult(result));
      lastCommandPayload = result;
    }
  }
  await refresh();
}

async function exportLogs() {
  const result = await fetchJson("/api/logs/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requested_by: "trader-console-ui",
      role: "operator",
      payload: { export_path: "runtime/logs/trader-console-export.json" },
      authorization_context: { ticket: "trader-console-ui" },
    }),
  });
  if (result.error) {
    publishCommandResult(`Erro na exportação: ${result.reason_text || result.error}.`);
  } else {
    publishCommandResult(formatCommandResult(result));
    lastCommandPayload = result;
  }
}

for (const button of document.querySelectorAll("button[data-command]")) {
  button.addEventListener("click", async () => {
    await postCommand(button.dataset.command);
  });
}

on("exportLogs", "click", exportLogs);
on("validateConfigBtn", "click", async () => {
  await postCommand("validate-config");
});
on("marketDataInjectBtn", "click", injectDemoQuoteToMarket);
on("runDecisionCycleBtn", "click", runDecisionCycle);
on("intelligenceAskBtn", "click", askIntelligence);

on("logSeverity", "change", () => {
  renderCurrentRoute();
});
on("logModule", "change", () => {
  renderCurrentRoute();
});

on("modeOperator", "click", () => setMode(uiMode.OPERATOR));
on("modeTechnical", "click", () => setMode(uiMode.TECHNICAL));
on("pollInterval", "change", () => {
  const pollIntervalSelect = byId("pollInterval");
  const value = Number((pollIntervalSelect && pollIntervalSelect.value) || "2000");
  updatePolling(Number.isFinite(value) && value > 0 ? value : 2000);
});
window.addEventListener("hashchange", applyRouteFromHash);

function initApp() {
  setMode(uiMode.OPERATOR);
  updatePolling(pollMs);
  applyRouteFromHash();
  refresh();
}

if (typeof window !== "undefined") {
  window.__ODIN_TEST_HOOKS__ = {
    setText,
    setHTML,
    setClass,
    normalizeRoute,
    setActiveRoute,
    applyRouteFromHash,
    renderDashboard,
    renderMarket,
    renderRisk,
    renderDecision,
    renderExecution,
    renderPortfolios,
    renderMarketData,
    renderEconomicCalendar,
    renderLogs,
    renderConfig,
    renderCommands,
    renderIntegrations,
    renderIntelligence,
    renderCurrentRoute,
    refresh,
    injectDemoQuoteToMarket,
    runDecisionCycle,
    setMode,
    t,
    _state: () => ({
      currentMode,
      currentRoute,
      latestStatus,
      latestHealth,
      latestLogs,
      latestConfig,
      latestExternalStatus,
      latestExternalQuote,
      latestExternalQuoteGbp,
      latestExternalCalendar,
      latestExternalInject,
      latestIntelligence,
      lastCommandPayload,
    }),
  };

  if (!window.__ODIN_DISABLE_AUTO_INIT__) {
    initApp();
  }
} else {
  initApp();
}
