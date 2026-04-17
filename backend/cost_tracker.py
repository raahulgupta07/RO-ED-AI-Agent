#!/usr/bin/env python3
"""
Real-time cost tracker for API calls.
Each pipeline step records its token usage here.
The WebSocket reads accumulated costs per step.
"""

import threading

# Model pricing per million tokens (OpenRouter)
MODEL_PRICING = {
    "google/gemini-3.1-flash-lite-preview": {"input": 0.25, "output": 1.50},
    "google/gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "google/gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
    "google/gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "anthropic/claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "anthropic/claude-haiku-4-5": {"input": 0.80, "output": 4.00},
}

DEFAULT_PRICING = {"input": 0.50, "output": 3.00}

_lock = threading.Lock()
_costs = {}  # step_name -> {"input_tokens": N, "output_tokens": N, "cost": float}
_total_cost = 0.0


def reset():
    """Reset all costs for a new pipeline run."""
    global _costs, _total_cost
    with _lock:
        _costs = {}
        _total_cost = 0.0


def record(step_name: str, response_json: dict, model: str = ""):
    """Record cost from an OpenRouter API response."""
    global _total_cost
    usage = response_json.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    if not model:
        model = response_json.get("model", "")

    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    cost = (input_tokens * pricing["input"] / 1_000_000) + (output_tokens * pricing["output"] / 1_000_000)

    with _lock:
        if step_name not in _costs:
            _costs[step_name] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0}
        _costs[step_name]["input_tokens"] += input_tokens
        _costs[step_name]["output_tokens"] += output_tokens
        _costs[step_name]["cost"] += cost
        _costs[step_name]["calls"] += 1
        _total_cost += cost


def get_step_cost(step_name: str) -> dict:
    """Get cost info for a step."""
    with _lock:
        return _costs.get(step_name, {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0}).copy()


def get_total_cost() -> float:
    """Get total accumulated cost."""
    with _lock:
        return _total_cost


def get_all() -> dict:
    """Get all step costs."""
    with _lock:
        return {"steps": dict(_costs), "total": _total_cost}
