"""
forecast_renderer
-----------------
Read forecasts/<forecast_name>/data.json and render three PNGs per selected item:
  1) forecast-only
  2) actuals-only
  3) actuals + forecast overlay

No re-fitting and no access to raw timeseries — everything comes from data.json.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict
import json
import pandas as pd
import matplotlib.pyplot as plt

def _plot_line(df: pd.DataFrame, x: str, y: str, title: str, outfile: Path, xlim: tuple[pd.Timestamp, pd.Timestamp]) -> None:
    fig = plt.figure()
    ax = fig.gca()
    if not df.empty:
        ax.plot(df[x], df[y])
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(True)
    ax.set_xlim(*xlim)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    plt.close(fig)

def _title_of(item: dict) -> str:
    if item.get("kind") == "multivariate":
        regs = item.get("regressors") or []
        return f"{item.get('target')} (with {', '.join(regs)})" if regs else f"{item.get('target')} (univariate)"
    # univariate fallback
    return item.get("param", "series")

def _suffix_of(item: dict) -> str:
    base = item.get("target") if item.get("kind") == "multivariate" else item.get("param")
    if item.get("kind") == "multivariate":
        regs = item.get("regressors") or []
        base = f"{base}__with_{'+'.join(regs)}" if regs else f"{base}__univariate"
    parts = [base]
    if item.get("station_code"):
        parts.append(f"code={item['station_code']}")
    if item.get("station_id"):
        parts.append(f"id={item['station_id']}")
    return "__".join(parts)

def render_from_json(
    forecast_name: str,
    *,
    # choose which item to render:
    param: Optional[str] = None,      # for univariate items
    target: Optional[str] = None,     # for multivariate items
    base_output_dir: Path | str = None,
) -> Dict[str, str]:
    """
    Render 3 PNGs for the selected item in forecasts/<forecast_name>/data.json.
    Selection priority:
      - if target provided, pick the first multivariate item with that target
      - else if param provided, pick the first univariate item with that param
      - else pick the first item
    Returns dict with paths to the images and the used item kind.
    """
    # resolve run directory
    if base_output_dir is None:
        base_output_dir = Path(__file__).resolve().parent / "forecasts"
    run_dir = Path(base_output_dir) / forecast_name
    data_path = run_dir / "data.json"
    blob = json.loads(data_path.read_text(encoding="utf-8"))

    items = blob.get("items", [])
    if not items:
        raise ValueError("data.json contains no items")

    # choose item
    chosen = None
    if target:
        for it in items:
            if it.get("kind") == "multivariate" and it.get("target") == target:
                chosen = it
                break
    if chosen is None and param:
        for it in items:
            if it.get("kind") == "univariate" and it.get("param") == param:
                chosen = it
                break
    if chosen is None:
        chosen = items[0]

    # build dataframes from JSON
    pred = pd.DataFrame(chosen.get("predictions", []))
    if not pred.empty:
        pred["ds"] = pd.to_datetime(pred["ds"])

    act = pd.DataFrame(chosen.get("actuals", []))
    if not act.empty:
        act["ds"] = pd.to_datetime(act["ds"])

    if pred.empty:
        raise ValueError("Chosen item has no predictions in data.json")

    # x-range from predictions
    x_min, x_max = pred["ds"].min(), pred["ds"].max()
    xlim = (x_min, x_max)

    # file names
    suffix = _suffix_of(chosen)
    fp_forecast = run_dir / f"{suffix}__forecast.png"
    fp_actuals = run_dir / f"{suffix}__actuals.png"
    fp_both = run_dir / f"{suffix}__actuals_vs_forecast.png"

    # plots
    _plot_line(pred.rename(columns={"yhat": "y"}), "ds", "y", f"Forecast: {_title_of(chosen)}", fp_forecast, xlim)
    _plot_line(act, "ds", "y", f"Actuals: {_title_of(chosen)}", fp_actuals, xlim)

    fig = plt.figure()
    ax = fig.gca()
    if not act.empty:
        ax.plot(act["ds"], act["y"], label="Actuals")
    ax.plot(pred["ds"], pred["yhat"], label="Forecast")
    # optional: uncertainty band (if present)
    if "yhat_lower" in pred.columns and "yhat_upper" in pred.columns:
        try:
            ax.fill_between(pred["ds"], pred["yhat_lower"], pred["yhat_upper"], alpha=0.2, label="Uncertainty")
        except Exception:
            pass
    ax.set_title(f"Actuals vs Forecast: {_title_of(chosen)}")
    ax.set_xlabel("ds")
    ax.set_ylabel("value")
    ax.grid(True)
    ax.legend()
    ax.set_xlim(*xlim)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(fp_both, dpi=150)
    plt.close(fig)

    return {
        "kind": chosen.get("kind", "univariate"),
        "forecast_png": str(fp_forecast.resolve()),
        "actuals_png": str(fp_actuals.resolve()),
        "both_png": str(fp_both.resolve()),
        "run_dir": str(run_dir.resolve()),
    }
