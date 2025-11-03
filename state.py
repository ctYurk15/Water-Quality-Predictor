from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

WORKSPACE = Path.cwd() / "workspace"
STATE_FILE = WORKSPACE / "state.json"

DEFAULT_STATE = {
    "timeseries": [],   # [{name, files}]
    "models": [],       # [{name, meta}]
    "forecasts": []     # [{name, model, parameter, train_from, train_to, prob, created_at}]
}

def ensure_workspace() -> None:
    WORKSPACE.mkdir(exist_ok=True)

def load_state() -> Dict[str, Any]:
    ensure_workspace()
    if not STATE_FILE.exists():
        return DEFAULT_STATE.copy()
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # обережне злиття з дефолтом
        out = DEFAULT_STATE.copy()
        out.update({k: v for k, v in data.items() if k in DEFAULT_STATE})
        return out
    except Exception:
        # якщо файл пошкоджений — стартуємо з порожнього
        return DEFAULT_STATE.copy()

def save_state(state: Dict[str, Any]) -> None:
    ensure_workspace()
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
