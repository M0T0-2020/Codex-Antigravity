#!/usr/bin/env python3
"""Model mapping and resolution for Antigravity delegation.

Discovers models supported by `agy` CLI and maps logical tiers (research,
complex_research, flash, pro) to concrete model identifiers.
"""

import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

# Fallback default models if `agy models` is unreachable
FALLBACK_MODELS = [
    "gemini-3.8-flash-high",
    "gemini-3.7-flash-high",
    "gemini-3.1-pro-high",
    "claude-sonnet-4-6",
]

# Aliases mapping
DEFAULT_ALIASES = {
    "flash": "gemini-3.8-flash-high",
    "pro": "gemini-3.1-pro-high",
    "research": "gemini-3.8-flash-high",
    "complex_research": "gemini-3.1-pro-high",
}


def find_agy_binary(custom_path: Optional[str] = None) -> Optional[str]:
    """Find the path to the agy executable."""
    if custom_path and os.path.isabs(custom_path) and os.path.isfile(custom_path) and os.access(custom_path, os.X_OK):
        return custom_path

    if custom_path and custom_path != "agy":
        found = shutil.which(custom_path)
        if found:
            return found

    # Standard candidate locations
    candidates = [
        shutil.which("agy"),
        os.path.expanduser("~/.local/bin/agy"),
        "/usr/local/bin/agy",
        "/opt/homebrew/bin/agy",
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def get_available_models_detailed(agy_path: Optional[str] = None, timeout: int = 5) -> List[Dict[str, str]]:
    """Query available models with display names from `agy models`."""
    binary = find_agy_binary(agy_path)
    if not binary:
        return [{"id": m, "name": m} for m in FALLBACK_MODELS]

    try:
        res = subprocess.run(
            [binary, "models"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        if res.returncode == 0 and res.stdout:
            detailed = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if (
                    line
                    and not line.startswith("#")
                    and not line.startswith("Available")
                    and not line.startswith("Fetching")
                    and not line.startswith("ERROR")
                ):
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        model_id = parts[0].strip()
                        model_name = parts[1].strip()
                    else:
                        tokens = line.split(maxsplit=1)
                        model_id = tokens[0].strip()
                        model_name = tokens[1].strip() if len(tokens) > 1 else model_id

                    if model_id:
                        detailed.append({"id": model_id, "name": model_name})
            if detailed:
                return detailed
    except Exception:
        pass

    return [{"id": m, "name": m} for m in FALLBACK_MODELS]


def get_available_models(agy_path: Optional[str] = None, timeout: int = 5) -> List[str]:
    """Query available model IDs from `agy models`."""
    detailed = get_available_models_detailed(agy_path=agy_path, timeout=timeout)
    return [m["id"] for m in detailed]


def search_models(query: Optional[str] = None, agy_path: Optional[str] = None) -> List[Dict[str, str]]:
    """Search and filter available models by query substring."""
    all_models = get_available_models_detailed(agy_path)
    if not query:
        return all_models

    q = query.strip().lower()
    return [
        m for m in all_models
        if q in m["id"].lower() or q in m["name"].lower()
    ]


def resolve_model(
    model_name_or_alias: Optional[str],
    config_models: Optional[Dict[str, str]] = None,
    available_models: Optional[List[str]] = None,
) -> Optional[str]:
    """Resolve a logical model alias or tier into a model identifier.

    If None is provided, returns None so `agy` uses its default model.
    """
    if not model_name_or_alias:
        return None

    target = model_name_or_alias.strip()

    # Check config models first (e.g. config["models"]["research"])
    if config_models and target in config_models:
        target = config_models[target]

    # Check built-in aliases
    if target in DEFAULT_ALIASES:
        target = DEFAULT_ALIASES[target]

    # If available_models provided, verify or find best prefix match
    if available_models:
        if target in available_models:
            return target
        for m in available_models:
            if target.lower() in m.lower():
                return m

    return target


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Query or resolve Antigravity models.")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--search", type=str, help="Search models by keyword (e.g. flash, pro, claude)")
    parser.add_argument("--resolve", type=str, help="Resolve alias to model name")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    if args.list or args.search is not None:
        results = search_models(args.search)
        if args.json:
            import json
            print(json.dumps(results, indent=2))
        else:
            header = f"Matching models for '{args.search}':" if args.search else "Available models:"
            print(header)
            for m in results:
                print(f"  - {m['id']:<26} ({m['name']})")
    elif args.resolve:
        print(resolve_model(args.resolve, available_models=get_available_models()))
    else:
        parser.print_help()

