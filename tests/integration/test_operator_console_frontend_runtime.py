from __future__ import annotations

import json
import subprocess
from pathlib import Path


APP_JS_PATH = Path("src/operator_console/web/app.js")


def _run_frontend_harness(
    *,
    action_js: str,
    status_payload: dict | None = None,
    health_payload: dict | None = None,
    logs_payload: dict | None = None,
    config_payload: dict | None = None,
    external_status_payload: dict | None = None,
    external_quote_payload: dict | None = None,
    external_quote_gbp_payload: dict | None = None,
    external_calendar_payload: dict | None = None,
    missing_ids: list[str] | None = None,
) -> dict:
    status = status_payload or {
        "global_state": "ST-40",
        "mode": "MD-20",
        "profile": "lite",
        "kill_active": False,
        "active_block_count": 0,
        "market_runtime": {
            "last_gate_status": "open",
            "last_rejection_reason": None,
            "last_instrument_id": "EURUSD",
            "last_feed_id": "tick-feed",
            "instrument_scope": ["EURUSD"],
            "feed_scope": ["tick-feed"],
            "active_restrictions": [],
        },
        "risk_summary": {
            "risk_block_active": False,
            "dominant_block_reason": None,
            "active_block_count": 0,
        },
        "decision_last_result": {
            "decision_cycle_id": "dc-1",
            "reason_summary": "ok",
            "risk_decision": "allow",
        },
        "execution_summary": {
            "ledger_available": True,
            "last_execution": {
                "exec_state": "allowed",
                "intent_id": "intent-1",
                "request_id": "req-1",
                "reason_summary": "ok",
                "recorded_at_utc": "2026-01-01T00:00:00Z",
                "slippage_value": "0.1",
                "snapshot_payload": {"divergence_flag": False},
                "request_payload": {"tactic_id": "t1"},
                "context_payload": {"decision_score": 0.9, "rationale": "good"},
            },
            "recent_executions": [],
        },
    }
    health = health_payload or {
        "global_state": "ST-40",
        "liveness": {"MARKET": "OK", "RISK": "OK", "EXEC": "OK"},
        "startup_missing_heartbeat_modules": [],
        "startup_unavailable_modules": [],
    }
    logs = logs_payload or {
        "recent_events": [
            {
                "completed_at_utc": "2026-01-01T00:00:00Z",
                "command": "pause",
                "accepted": True,
                "rejection_reason": None,
            }
        ],
        "operator_recent_events": [
            {
                "completed_at_utc": "2026-01-01T00:00:00Z",
                "command": "pause",
                "accepted": True,
                "rejection_reason": None,
            }
        ],
        "technical_recent_events": [
            {
                "completed_at_utc": "2026-01-01T00:00:00Z",
                "command": "pause",
                "accepted": True,
                "rejection_reason": None,
            }
        ],
    }
    config = config_payload or {
        "response": {
            "active_config": {
                "core": {"startup_timeout_ms": 15000, "heartbeat_timeout_ms": 500},
                "runtime": {"state_dir": "runtime/state"},
            },
            "staged_patch": None,
        }
    }
    external_status = external_status_payload or {
        "providers": [
            {
                "provider": "DemoProvider",
                "healthy": True,
                "enabled": True,
                "configured": True,
                "source_type": "demo",
            },
            {
                "provider": "AlphaVantage",
                "healthy": False,
                "enabled": False,
                "configured": False,
                "source_type": "external",
            },
        ],
        "cache": {"entries": 1, "hits": 0, "misses": 0},
        "warnings": ["real_provider_disabled_by_profile_or_config"],
    }
    external_quote = external_quote_payload or {
        "quote": {
            "symbol": "EURUSD",
            "provider": "DemoProvider",
            "timestamp_utc": "2026-01-01T00:00:00+00:00",
            "last_price": 1.0819,
            "from_cache": False,
        },
        "cache": {"entries": 1, "hits": 0, "misses": 0},
        "warnings": [],
    }
    external_quote_gbp = external_quote_gbp_payload or {
        "quote": {
            "symbol": "GBPUSD",
            "provider": "DemoProvider",
            "timestamp_utc": "2026-01-01T00:00:01+00:00",
            "last_price": 1.2700,
            "from_cache": True,
        },
        "cache": {"entries": 2, "hits": 1, "misses": 1},
        "warnings": [],
    }
    external_calendar = external_calendar_payload or {
        "events": [
            {
                "title": "US CPI (Demo)",
                "country": "US",
                "impact": "high",
                "event_time_utc": "2026-01-01T06:00:00+00:00",
            }
        ],
        "next_event": {
            "title": "US CPI (Demo)",
            "event_time_utc": "2026-01-01T06:00:00+00:00",
        },
        "cache": {"entries": 1, "hits": 0, "misses": 0},
        "warnings": [],
    }
    missing = missing_ids or []

    script = f"""
const fs = require(\"fs\");
const vm = require(\"vm\");

const source = fs.readFileSync({json.dumps(str(APP_JS_PATH))}, \"utf8\");
const missingIds = new Set({json.dumps(missing)});

class ClassList {{
  constructor(element) {{
    this.element = element;
    this._set = new Set();
  }}
  _sync() {{
    this.element.className = Array.from(this._set).join(\" \");
  }}
  add(...names) {{
    names.forEach((name) => this._set.add(name));
    this._sync();
  }}
  remove(...names) {{
    names.forEach((name) => this._set.delete(name));
    this._sync();
  }}
  contains(name) {{
    return this._set.has(name);
  }}
  toggle(name, force) {{
    if (force === undefined) {{
      if (this._set.has(name)) {{
        this._set.delete(name);
      }} else {{
        this._set.add(name);
      }}
    }} else if (force) {{
      this._set.add(name);
    }} else {{
      this._set.delete(name);
    }}
    this._sync();
    return this._set.has(name);
  }}
}}

class Element {{
  constructor(id = \"\", tag = \"div\") {{
    this.id = id;
    this.tagName = tag.toUpperCase();
    this.innerHTML = \"\";
    this.textContent = \"\";
    this.className = \"\";
    this.dataset = {{}};
    this.style = {{}};
    this.disabled = false;
    this.value = \"\";
    this.children = [];
    this.listeners = {{}};
    this.classList = new ClassList(this);
    if (this.tagName === \"CANVAS\") {{
      this.width = 720;
      this.height = 170;
    }}
  }}
  appendChild(child) {{
    this.children.push(child);
    return child;
  }}
  querySelectorAll(selector) {{
    if (selector === \".page-tech\") {{
      return this.children.filter((child) => child.classList.contains(\"page-tech\"));
    }}
    return [];
  }}
  addEventListener(name, fn) {{
    if (!this.listeners[name]) {{
      this.listeners[name] = [];
    }}
    this.listeners[name].push(fn);
  }}
  getContext(kind) {{
    if (this.tagName !== \"CANVAS\" || kind !== \"2d\") {{
      return null;
    }}
    return {{
      clearRect() {{}},
      beginPath() {{}},
      moveTo() {{}},
      lineTo() {{}},
      stroke() {{}},
      set strokeStyle(value) {{}},
      set lineWidth(value) {{}},
    }};
  }}
}}

const ids = new Set();
const idPatterns = [
  /byId\\(\"([^\"]+)\"\\)/g,
  /document\\.getElementById\\(\"([^\"]+)\"\\)/g,
  /setText\\(\\s*\"([^\"]+)\"\\s*,/g,
  /setHTML\\(\\s*\"([^\"]+)\"\\s*,/g,
  /setClass\\(\\s*\"([^\"]+)\"\\s*,/g,
  /setDisabled\\(\\s*\"([^\"]+)\"\\s*,/g,
  /on\\(\\s*\"([^\"]+)\"\\s*,/g,
];
for (const pattern of idPatterns) {{
  for (const match of source.matchAll(pattern)) {{
    ids.add(match[1]);
  }}
}}

const elementsById = new Map();
const routePages = [];
const navLinks = [];
const commandButtons = [];

function register(id, tag = \"div\") {{
  if (!id || missingIds.has(id)) {{
    return null;
  }}
  if (elementsById.has(id)) {{
    return elementsById.get(id);
  }}
  const element = new Element(id, tag);
  elementsById.set(id, element);
  return element;
}}

const routes = [\"dashboard\", \"market\", \"risk\", \"decision\", \"execution\", \"portfolios\", \"market-data\", \"economic-calendar\", \"logs\", \"config\", \"commands\", \"integrations\", \"intelligence\"];
for (const route of routes) {{
  const page = register(`page-${{route}}`);
  if (page) {{
    page.classList.add(\"route-page\");
    if (route !== \"dashboard\") {{
      page.classList.add(\"hidden\");
    }}
    const tech = new Element(`tech-${{route}}`, \"div\");
    tech.classList.add(\"page-tech\");
    tech.classList.add(\"hidden\");
    page.appendChild(tech);
    routePages.push(page);
  }}

  const nav = new Element(\"\", \"a\");
  nav.classList.add(\"nav-link\");
  nav.dataset.route = route;
  navLinks.push(nav);
}}

for (const id of ids) {{
  let tag = \"div\";
  if (id === \"marketCanvas\") {{
    tag = \"canvas\";
  }} else if ([\"pollInterval\", \"logSeverity\", \"logModule\"].includes(id)) {{
    tag = \"select\";
  }}
  const element = register(id, tag);
  if (!element) {{
    continue;
  }}
  if (id === \"pollInterval\") {{
    element.value = \"2000\";
  }}
  if (id === \"logSeverity\" || id === \"logModule\") {{
    element.value = \"all\";
  }}
}}

const commandMap = {{
  pauseBtn: \"pause\",
  dashPauseBtn: \"pause\",
  resumeBtn: \"resume\",
  dashResumeBtn: \"resume\",
  stopBtn: \"stop\",
  dashStopBtn: \"stop\",
  cmdStatusBtn: \"status\",
  cmdValidateBtn: \"validate-config\",
}};
for (const [id, command] of Object.entries(commandMap)) {{
  const button = elementsById.get(id);
  if (button) {{
    button.dataset.command = command;
    commandButtons.push(button);
  }}
}}

const document = {{
  getElementById(id) {{
    return elementsById.get(id) || null;
  }},
  querySelectorAll(selector) {{
    if (selector === \".route-page\") {{
      return routePages;
    }}
    if (selector === \".nav-link[data-route]\") {{
      return navLinks;
    }}
    if (selector === \"button[data-command]\") {{
      return commandButtons;
    }}
    return [];
  }},
  createElement(tag) {{
    return new Element(\"\", tag);
  }},
}};

const windowListeners = {{}};
const window = {{
  location: {{ hash: \"#dashboard\" }},
  confirm() {{
    return true;
  }},
  addEventListener(name, fn) {{
    windowListeners[name] = fn;
  }},
  __ODIN_DISABLE_AUTO_INIT__: true,
}};

const fetchPayloads = {{
  \"/api/status\": {json.dumps(status)},
  \"/api/health\": {json.dumps(health)},
  \"/api/logs/recent\": {json.dumps(logs)},
  \"/api/config\": {json.dumps(config)},
  \"/api/external/status\": {json.dumps(external_status)},
  \"/api/external/quote?symbol=EURUSD\": {json.dumps(external_quote)},
  \"/api/external/quote?symbol=GBPUSD\": {json.dumps(external_quote_gbp)},
  \"/api/external/calendar\": {json.dumps(external_calendar)},
  \"/api/external/inject-demo-quote-to-market\": {{
    accepted: true,
    rejected: false,
    gate_status: \"accepted\",
    reason: null,
    runtime: {{
      last_gate_status: \"accepted\",
      last_instrument_id: \"EURUSD\",
      last_feed_id: \"primary\",
      applied_restrictions: []
    }},
    readiness_result: {{
      core_readiness: \"ready\",
      core_integrity: \"ok\",
      global_state: \"ST-40\"
    }}
  }},
  \"/api/logs/export\": {{}},
}};

const context = {{
  window,
  document,
  console,
  setInterval(fn, ms) {{
    context.__interval = fn;
    context.__intervalMs = ms;
    return 1;
  }},
  clearInterval() {{}},
  fetch: async (url) => {{
    return {{
      status: 200,
      headers: {{
        get(name) {{
          return \"application/json\";
        }},
      }},
      json: async () => fetchPayloads[url] || {{}},
    }};
  }},
  Date,
  Math,
  JSON,
  Array,
  Object,
  String,
  Number,
  Boolean,
  Promise,
}};
context.globalThis = context;

vm.createContext(context);
vm.runInContext(source, context, {{ timeout: 2000 }});

const hooks = window.__ODIN_TEST_HOOKS__;

(async () => {{
  {action_js}
}})().catch((error) => {{
  console.error(String(error && error.stack ? error.stack : error));
  process.exit(1);
}});
"""

    completed = subprocess.run(
        ["node", "-e", script],
        text=True,
        capture_output=True,
        check=True,
    )
    output = completed.stdout.strip().splitlines()
    assert output
    return json.loads(output[-1])


def test_dashboard_renders_without_module_health_body() -> None:
    result = _run_frontend_harness(
        missing_ids=["moduleHealthBody"],
        action_js="""
await hooks.refresh();
window.location.hash = "#dashboard";
hooks.applyRouteFromHash();
console.log(JSON.stringify({
  state: document.getElementById("generalState").textContent,
  health: document.getElementById("generalHealth").textContent
}));
""",
    )
    assert result["state"] == "Pronto"
    assert result["health"] == "OK"


def test_hash_route_switch_market_and_config_does_not_fail() -> None:
    result = _run_frontend_harness(
        action_js="""
await hooks.refresh();
window.location.hash = "#market";
hooks.applyRouteFromHash();
const activeMarket = hooks._state().currentRoute;
const marketVisible = !document.getElementById("page-market").classList.contains("hidden");
const activeNavMarket = document
  .querySelectorAll(".nav-link[data-route]")
  .filter((link) => link.classList.contains("active"))
  .map((link) => link.dataset.route);

window.location.hash = "#config";
hooks.applyRouteFromHash();
const activeConfig = hooks._state().currentRoute;
const configVisible = !document.getElementById("page-config").classList.contains("hidden");
const activeNavConfig = document
  .querySelectorAll(".nav-link[data-route]")
  .filter((link) => link.classList.contains("active"))
  .map((link) => link.dataset.route);

console.log(JSON.stringify({
  activeMarket,
  marketVisible,
  activeNavMarket,
  activeConfig,
  configVisible,
  activeNavConfig
}));
""",
    )
    assert result["activeMarket"] == "market"
    assert result["marketVisible"] is True
    assert result["activeNavMarket"] == ["market"]
    assert result["activeConfig"] == "config"
    assert result["configVisible"] is True
    assert result["activeNavConfig"] == ["config"]


def test_dom_helpers_ignore_missing_ids() -> None:
    result = _run_frontend_harness(
        action_js="""
const r1 = hooks.setText("missing-text", "abc");
const r2 = hooks.setHTML("missing-html", "<p>x</p>");
const r3 = hooks.setClass("missing-class", "x");
console.log(JSON.stringify({ r1, r2, r3 }));
""",
    )
    assert result == {"r1": False, "r2": False, "r3": False}


def test_dashboard_critical_cards_are_filled_in_operator_mode() -> None:
    result = _run_frontend_harness(
        action_js="""
await hooks.refresh();
window.location.hash = "#dashboard";
hooks.applyRouteFromHash();
console.log(JSON.stringify({
  state: document.getElementById("generalState").textContent,
  mode: document.getElementById("generalMode").textContent,
  profile: document.getElementById("generalProfile").textContent,
  kill: document.getElementById("generalKill").textContent,
  blocks: document.getElementById("generalBlocks").textContent,
  health: document.getElementById("generalHealth").textContent
}));
""",
    )
    assert result == {
        "state": "Pronto",
        "mode": "Demo",
        "profile": "Leve",
        "kill": "Inativo",
        "blocks": "0",
        "health": "OK",
    }


def test_technical_payload_is_rendered_only_for_active_route() -> None:
    result = _run_frontend_harness(
        action_js="""
await hooks.refresh();
hooks.setMode("technical");
window.location.hash = "#dashboard";
hooks.applyRouteFromHash();

const dashTech = document.getElementById("techDashboard").textContent;
const marketTechBefore = document.getElementById("techMarket").textContent;

window.location.hash = "#market";
hooks.applyRouteFromHash();
const marketTechAfter = document.getElementById("techMarket").textContent;

console.log(JSON.stringify({
  dashHasJson: dashTech.includes("global_state"),
  marketBeforeEmpty: marketTechBefore === "",
  marketAfterHasJson: marketTechAfter.includes("last_gate_status")
}));
""",
    )
    assert result["dashHasJson"] is True
    assert result["marketBeforeEmpty"] is True
    assert result["marketAfterHasJson"] is True


def test_dashboard_renders_external_data_cards() -> None:
    result = _run_frontend_harness(
        action_js="""
await hooks.refresh();
window.location.hash = "#dashboard";
hooks.applyRouteFromHash();
console.log(JSON.stringify({
  eurusd: document.getElementById("externalEurUsdPrice").textContent,
  macro: document.getElementById("externalNextMacroEvent").textContent,
  provider: document.getElementById("externalActiveProvider").textContent,
  sourceMode: document.getElementById("externalSourceMode").textContent,
  quality: document.getElementById("externalDataQuality").textContent,
  providerHealth: document.getElementById("externalProviderHealth").textContent,
  cacheState: document.getElementById("externalCacheState").textContent,
  feedsMarket: document.getElementById("externalFeedsMarket").textContent,
  warning: document.getElementById("externalProviderWarning").textContent
}));
""",
    )
    assert "1.0819" in result["eurusd"]
    assert "US CPI (Demo)" in result["macro"]
    assert result["provider"] == "DemoProvider"
    assert result["sourceMode"] == "DEMO"
    assert "demo" in result["quality"].lower()
    assert "healthy" in result["providerHealth"]
    assert "entries=" in result["cacheState"]
    assert result["feedsMarket"] == "Não"
    assert "real_provider_disabled_by_profile_or_config" in result["warning"]


def test_market_data_page_renders_provider_cache_and_calendar() -> None:
    result = _run_frontend_harness(
        action_js="""
await hooks.refresh();
window.location.hash = "#market-data";
hooks.applyRouteFromHash();
console.log(JSON.stringify({
  providerHealth: document.getElementById("marketDataProviderHealth").textContent,
  cacheState: document.getElementById("marketDataCacheState").textContent,
  nextEvent: document.getElementById("marketDataCalendarNext").textContent,
  providerListCount: document.getElementById("marketDataProviderList").children.length,
  calendarCount: document.getElementById("marketDataCalendarList").children.length
}));
""",
    )
    assert "healthy" in result["providerHealth"]
    assert "entries=" in result["cacheState"]
    assert "US CPI (Demo)" in result["nextEvent"]
    assert result["providerListCount"] >= 1
    assert result["calendarCount"] >= 1


def test_market_data_inject_demo_quote_updates_result_and_market_runtime() -> None:
    result = _run_frontend_harness(
        action_js="""
await hooks.refresh();
window.location.hash = "#market-data";
hooks.applyRouteFromHash();
await hooks.injectDemoQuoteToMarket();
window.location.hash = "#market";
hooks.applyRouteFromHash();
console.log(JSON.stringify({
  injectResult: document.getElementById("marketDataInjectResult").textContent,
  marketGate: document.getElementById("marketLastGateStatus").textContent,
  marketInstrument: document.getElementById("marketInstrument").textContent,
  marketFeed: document.getElementById("marketFeed").textContent
}));
""",
    )
    assert "Inject accepted" in result["injectResult"]
    assert result["marketGate"] in {"open", "accepted"}
    assert result["marketInstrument"] == "EURUSD"
    assert result["marketFeed"] in {"tick-feed", "primary"}
