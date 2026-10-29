"""Explicit plugin discovery and loading via Python package entry points.

Never load plugins for listing: importing third-party Python is code execution.
"""
from __future__ import annotations
from importlib.metadata import entry_points

GROUP = "consensustree.providers"


def available_plugins() -> list[dict]:
    return [{"name": entry.name, "distribution": getattr(getattr(entry, "dist", None), "name", "unknown"),
             "module": entry.value}
            for entry in entry_points(group=GROUP)]


def load_client_plugin(name: str):
    matches = [entry for entry in entry_points(group=GROUP) if entry.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected one installed plugin named {name!r}; found {len(matches)}")
    # Explicit user selection is required before importing and running plugin code.
    provider = matches[0].load()
    client = provider() if callable(provider) else provider
    if not callable(getattr(client, "complete", None)):
        raise ValueError("Plugin must expose .complete(model_spec, system, user)")
    return client
