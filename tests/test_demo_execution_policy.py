from pathlib import Path


ROOT = Path(".")
POLICY_FILES = (
    ROOT / "AGENTS.md",
    ROOT / "docs/ARCHITECTURE_LOCK.md",
    ROOT / "docs/CODEX_POLICY.md",
    ROOT / "docs/architecture/adr/ADR-005-mt5-adapter-strategy.md",
)


def test_demo_exception_is_bound_to_one_adapter_and_human_canary() -> None:
    for path in POLICY_FILES:
        text = path.read_text(encoding="utf-8")
        assert "src/odin/adapters/mt5/demo_execution_adapter.py" in text
        assert "CANARY" in text


def test_policies_preserve_real_and_unknown_hard_blocks() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in POLICY_FILES)
    assert "real_trading=false" in combined
    assert "REAL" in combined
    assert "UNKNOWN" in combined
    assert "HARD_BLOCK" in combined


def test_global_runtime_still_defaults_to_no_order_send() -> None:
    state_contract = (ROOT / "src/odin/contracts/state.py").read_text(encoding="utf-8")
    assert "mt5_transport_allowed=False" in state_contract


def test_upstream_financial_authority_remains_forbidden() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for authority in ("Hermes", "n8n", "LLM", "Strategy", "Risk"):
        assert authority in agents
