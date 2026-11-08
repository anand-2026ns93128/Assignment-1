"""Configuration loading (task T015; research R-09, Constitution X).

Precedence: explicit overrides (CLI) > environment variables > ``config/settings.toml``.
The API key is never read or stored here.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.toml"
MAX_TOKENS_LIMIT = 300  # Constitution X


class ConfigError(ValueError):
    """Invalid or inconsistent configuration."""


@dataclass(frozen=True)
class Pricing:
    input_per_mtok: float
    output_per_mtok: float
    long_context_threshold_tokens: int = 100_000
    long_input_per_mtok: float | None = None
    long_output_per_mtok: float | None = None

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimated USD cost; long-context rates apply when the prompt exceeds the threshold."""
        rate_in, rate_out = self.input_per_mtok, self.output_per_mtok
        if input_tokens > self.long_context_threshold_tokens:
            rate_in = self.long_input_per_mtok or rate_in
            rate_out = self.long_output_per_mtok or rate_out
        return (input_tokens * rate_in + output_tokens * rate_out) / 1_000_000

    def to_json(self) -> dict:
        return {
            "input_per_mtok": self.input_per_mtok,
            "output_per_mtok": self.output_per_mtok,
            "long_context_threshold_tokens": self.long_context_threshold_tokens,
            "long_input_per_mtok": self.long_input_per_mtok,
            "long_output_per_mtok": self.long_output_per_mtok,
        }


@dataclass(frozen=True)
class AgentConfig:
    model: str
    max_tokens: int
    temperature: float | None = None
    effort: str = "low"
    thinking: str = "disabled"
    timeout_seconds: float = 30
    pricing: Mapping[str, Pricing] = field(default_factory=dict)
    run_abort_usd: float = 0.50
    project_cap_usd: float = 5.00

    def __post_init__(self) -> None:
        if not isinstance(self.max_tokens, int) or not 1 <= self.max_tokens <= MAX_TOKENS_LIMIT:
            raise ConfigError(
                f"max_tokens must be an integer from 1 to {MAX_TOKENS_LIMIT}, "
                f"got {self.max_tokens}")
        if not self.model:
            raise ConfigError("model name must not be empty")

    def pricing_for(self, model: str | None = None) -> Pricing:
        name = model or self.model
        try:
            return self.pricing[name]
        except KeyError:
            raise ConfigError(f"no pricing configured for model {name!r}") from None

    def to_evidence(self) -> dict:
        """Settings recorded in every run's evidence. Never contains the API key."""
        return {
            "name": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,  # None = not sent (model default)
            "effort": self.effort,
            "thinking": self.thinking,
            "timeout_seconds": self.timeout_seconds,
        }


def _parse_float(name: str, value: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got {value!r}") from None


def _parse_int(name: str, value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ConfigError(f"{name} must be an integer, got {value!r}") from None


def load_config(
    path: Path | None = None,
    env: Mapping[str, str] | None = None,
    overrides: Mapping[str, object] | None = None,
) -> AgentConfig:
    """Load settings from the TOML file, then apply env vars, then explicit overrides."""
    env = os.environ if env is None else env
    data = tomllib.loads(Path(path or DEFAULT_CONFIG_PATH).read_text(encoding="utf-8"))
    model_section = data.get("model", {})
    budget = data.get("budget", {})

    model = model_section.get("name", "")
    max_tokens = model_section.get("max_tokens", MAX_TOKENS_LIMIT)
    temperature = model_section.get("temperature")

    if env.get("REMINDER_MODEL"):
        model = env["REMINDER_MODEL"]
    if env.get("REMINDER_MAX_TOKENS"):
        max_tokens = env["REMINDER_MAX_TOKENS"]
    if env.get("REMINDER_TEMPERATURE"):
        temperature = _parse_float("REMINDER_TEMPERATURE", env["REMINDER_TEMPERATURE"])

    for key, value in (overrides or {}).items():
        if value is None:
            continue
        if key == "model":
            model = str(value)
        elif key == "max_tokens":
            max_tokens = value
        elif key == "temperature":
            temperature = float(value)  # type: ignore[arg-type]
        else:
            raise ConfigError(f"unknown override {key!r}")

    pricing = {
        name: Pricing(**values) for name, values in (data.get("pricing") or {}).items()
    }
    return AgentConfig(
        model=model,
        max_tokens=_parse_int("max_tokens", max_tokens),
        temperature=temperature,
        effort=model_section.get("effort", "low"),
        thinking=model_section.get("thinking", "disabled"),
        timeout_seconds=model_section.get("timeout_seconds", 30),
        pricing=pricing,
        run_abort_usd=float(budget.get("run_abort_usd", 0.50)),
        project_cap_usd=float(budget.get("project_cap_usd", 5.00)),
    )
