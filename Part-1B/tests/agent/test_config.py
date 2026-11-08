"""Tests for configuration, src/reminder_agent/config.py (T011).

Covers Constitution X, research R-09 and FR-040.
"""

from __future__ import annotations

import pytest

from reminder_agent.config import ConfigError, load_config


def test_defaults_from_settings_file():
    """Constitution X, FR-040: default model, max_tokens 300, temperature left unset."""
    cfg = load_config(env={})
    assert cfg.model == "claude-haiku-5-5"
    assert cfg.max_tokens == 300
    assert cfg.temperature is None
    assert cfg.effort == "low" and cfg.thinking == "disabled"
    assert cfg.run_abort_usd == 0.50 and cfg.project_cap_usd == 5.00


@pytest.mark.parametrize("source", ["env", "override", "file"])
def test_max_tokens_above_300_rejected(source, tmp_path):
    """Constitution X: max_tokens may never exceed 300, from any source."""
    with pytest.raises(ConfigError):
        if source == "env":
            load_config(env={"REMINDER_MAX_TOKENS": "301"})
        elif source == "override":
            load_config(env={}, overrides={"max_tokens": 1000})
        else:
            path = tmp_path / "s.toml"
            path.write_text('[model]\nname = "m"\nmax_tokens = 301\n', encoding="utf-8")
            load_config(path=path, env={})


def test_precedence_cli_over_env_over_file():
    """R-09: CLI overrides beat environment variables, which beat the file."""
    env = {"REMINDER_MODEL": "env-model", "REMINDER_MAX_TOKENS": "200",
           "REMINDER_TEMPERATURE": "0.5"}
    cfg = load_config(env=env)
    assert (cfg.model, cfg.max_tokens, cfg.temperature) == ("env-model", 200, 0.5)
    cfg = load_config(env=env, overrides={"model": "cli-model", "max_tokens": 100,
                                          "temperature": None})
    assert (cfg.model, cfg.max_tokens, cfg.temperature) == ("cli-model", 100, 0.5)


def test_pricing_lookup():
    """FR-040, Constitution X: pricing comes from the config; unknown models are an error."""
    cfg = load_config(env={})
    price = cfg.pricing_for()
    assert price.input_per_mtok == 0.10 and price.output_per_mtok == 0.50
    assert price.cost(100_000, 1_000_000) == pytest.approx(0.01 + 0.50)   # standard rates
    assert price.cost(200_000, 0) == pytest.approx(0.10)   # long-context input rate
    with pytest.raises(ConfigError):
        load_config(env={"REMINDER_MODEL": "unknown-model"}).pricing_for()


def test_to_evidence_has_no_key_and_null_temperature(monkeypatch):
    """FR-040, Constitution IX: evidence config records temperature null and never the key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-" + "ant-test-123456")
    evidence = load_config(env={}).to_evidence()
    assert evidence["temperature"] is None
    assert "ant-test" not in repr(evidence)
    assert evidence["max_tokens"] == 300
