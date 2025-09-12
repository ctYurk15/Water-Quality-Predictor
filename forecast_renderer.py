"""
forecast_renderer
-----------------
Read forecasts/<forecast_name>/data.json and render three PNGs for a selected item:
  1) forecast-only
  2) actuals-only (prefers daily actuals if available)
  3) actuals + forecast overlay (with optional uncertainty band)

No model fitting. No raw timeseries required. Everything is taken from data.json.

Usage:
    from forecast_renderer import render_from_json
    paths = render_from_json("set1", target="Azot")     # multivariate example
    # or
    paths = render_from_json("set1", param="Azot")      # univariate example
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict
import json
import pandas as pd
import matplotlib.pyplot as plt


# --------------------------- plotting helpers ---------------------------

def _plot_line(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    outfile: Path,
    xlim: tuple[pd.Timestamp, pd.Timestamp],
) -> None:
    """Single line plot (no seaborn, no explicit colors)."""
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


def _series_title(item: dict) -> str:
    if item.get("kind") == "multivariate":
        regs = item.get("regressors") or []
        return f"{item.get('target')} (with {', '.join(regs)})" if regs else f"{item.get('target')} (univariate)"
    return item.get("param", "series")


def _file_suffix(item: dict) -> str:
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


# ------------------------------ public API ------------------------------

def render_from_json(
    forecast_name: str,
    *,
    param: Optional[str] = None,      # for univariate items
    target: Optional[str] = None,     # for multivariate items
    base_output_dir: Optional[str | Path] = None,
) -> Dict[str, str]:
    """
    Render 3 PNGs for a selected item from forecasts/<forecast_name>/data.json.

    Selection priority:
      1) If target is provided → first multivariate item with that target
      2) Else if param is provided → first univariate item with that param
      3) Else → the first item in data.json

    Returns:
      {
        "kind": "univariate" | "multivariate",
        "forecast_png": ".../forecast.png",
        "actuals_png": ".../actuals.png",
        "both_png": ".../actuals_vs_forecast.png",
        "run_dir": ".../forecasts/<forecast_name>"
      }
    """
    # Resolve run directory and read data.json
    if base_output_dir is None:
        base_output_dir = Path(__file__).resolve().parent / "forecasts"
    run_dir = Path(base_output_dir) / forecast_name
    data_path = run_dir / "data.json"
    if not data_path.exists():
        raise FileNotFoundError(f"data.json not found at: {data_path}")

    blob = json.loads(data_path.read_text(encoding="utf-8"))
    items = blob.get("items", [])
    if not items:
        raise ValueError("data.json contains no items")

    # Choose item
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

    # Build DataFrames from JSON
    pred = pd.DataFrame(chosen.get("predictions", []))
    if pred.empty:
        raise ValueError("Chosen item has no predictions in data.json")
    pred["ds"] = pd.to_datetime(pred["ds"])

    # Prefer daily actuals if available
    act_daily = pd.DataFrame(chosen.get("actuals_daily", []))
    if not act_daily.empty:
        act_daily["ds"] = pd.to_datetime(act_daily["ds"])
        act_plot = act_daily.dropna(subset=["y"]).copy()
    else:
        act = pd.DataFrame(chosen.get("actuals", []))
        act_plot = act.copy()
        if not act_plot.empty:
            act_plot["ds"] = pd.to_datetime(act_plot["ds"])

    # X-range from predictions
    x_min, x_max = pred["ds"].min(), pred["ds"].max()
    xlim = (x_min, x_max)

    # Output filenames
    suffix = _file_suffix(chosen)
    fp_forecast = run_dir / f"{suffix}__forecast.png"
    fp_actuals = run_dir / f"{suffix}__actuals.png"
    fp_both = run_dir / f"{suffix}__actuals_vs_forecast.png"

    # Plots
    _plot_line(pred.rename(columns={"yhat": "y"}), "ds", "y", f"Forecast: {_series_title(chosen)}", fp_forecast, xlim)
    _plot_line(act_plot, "ds", "y", f"Actuals: {_series_title(chosen)}", fp_actuals, xlim)

    fig = plt.figure()
    ax = fig.gca()
    if not act_plot.empty:
        ax.plot(act_plot["ds"], act_plot["y"], label="Actuals")
    ax.plot(pred["ds"], pred["yhat"], label="Forecast")
    # Optional uncertainty band if present
    if {"yhat_lower", "yhat_upper"}.issubset(pred.columns):
        try:
            ax.fill_between(pred["ds"], pred["yhat_lower"], pred["yhat_upper"], alpha=0.2, label="Uncertainty")
        except Exception:
            pass
    ax.set_title(f"Actuals vs Forecast: {_series_title(chosen)}")
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
