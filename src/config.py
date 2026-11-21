"""Load config.yaml once and share it. Every module reads settings from here."""

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def load_config(path: str | Path = ROOT / "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def feature_names() -> list[str]:
    """Feature columns in the shared features.parquet contract, in a fixed order."""
    return list(load_config()["features"].keys())
