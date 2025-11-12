"""
forecast_renderer
-----------------
Read forecasts/<forecast_name>/data.json and render three PNGs for a selected item:
  1) Forecast (forecast-only)
  2) Actuals (actuals-only; prefers daily actuals if available)
  3) Actuals vs Forecast (overlay)

Titles are minimal:
  - line 1: "Forecast" | "Actuals" | "Actuals vs Forecast"
  - line 2 (optional): "(with reg1, reg2, ...)" for multivariate items

No model fitting. Everything is read from data.json.

Usage:
    from forecast_renderer import render_from_json
    paths = render_from_json("set1", target="Azot")
    # or
    paths = render_from_json("set1", param="Azot")
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# --------------------------- plotting helpers ---------------------------

def _apply_monthly_ticks(ax) -> None:
    """Format x-axis with monthly major ticks and YYYY-MM labels."""
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))


def _subtitle_for_item(item: dict) -> str:
    """Second line under the main title: regressors list if multivariate, else empty."""
    if item.get("kind") == "multivariate":
        regs = [str(r) for r in (item.get("regressors") or []) if r]
        if regs:
            return f"(with {', '.join(regs)})"
    return ""


def _plot_line(
    df: pd.DataFrame,
    x: str,
    y: str,
    title_main: str,
    title_sub: str,
    outfile: Path,
    xlim: tuple[pd.Timestamp, pd.Timestamp],
    color: '#0000FF'
) -> None:
    """Single line plot with monthly ticks; optional second-line subtitle."""
    fig = plt.figure()
    ax = fig.gca()
    if not df.empty:
        line = ax.plot(df[x], df[y], label=title_main, color=color)

    # Titles: first line minimal; second line (if any) with regressors
    ax.set_title(title_main + (f"\n{title_sub}" if title_sub else ""))
    ax.set_xlabel("ds")
    ax.set_ylabel("value")
    ax.grid(True)
    ax.set_xlim(*xlim)

    _apply_monthly_ticks(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(outfile, dpi=150)
    plt.close(fig)


def _series_title(item: dict) -> str:
    # Not used in titles anymore; kept if you want to repurpose.
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


def _pick_accuracy_metric(metrics: dict) -> tuple[str, dict]:
    """(Kept for return info; NOT displayed in titles anymore.)"""
    if not isinstance(metrics, dict) or not metrics:
        return "", {}
    candidates = []
    for k, v in metrics.items():
        m = re.fullmatch(r"within_(\d+)pct", str(k))
        if m and isinstance(v, dict):
            tol_pct = int(m.group(1))
            candidates.append((tol_pct, k, v))
    if not candidates:
        for k, v in metrics.items():
            if isinstance(v, dict):
                return k, v
        return "", {}
    candidates.sort(key=lambda t: t[0])
    _, key, payload = candidates[-1]
    return key, payload


# ------------------------------ public API ------------------------------

def render_from_json(
    forecast_name: str,
    *,
    param: Optional[str] = None,      # for univariate items
    target: Optional[str] = None,     # for multivariate items
    base_output_dir: Optional[str | Path] = None,
    real_data_color: '#0000FF',
    forecast_color: '#FF0000'
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
        "metric_key": "within_20pct" | "" ,
        "forecast_png": ".../forecast.png",
        "actuals_png": ".../actuals.png",
        "both_png": ".../actuals_vs_forecast.png",
        "run_dir": ".../forecasts/<forecast_name>"
      }
    """
    # Resolve run directory and read data.json
    if base_output_dir is None:
        base_output_dir = Path(__file__).resolve().parent.parent / "forecasts"
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
    fp_forecast = run_dir / f"forecast.png"
    fp_actuals = run_dir / f"actuals.png"
    fp_both = run_dir / f"actuals_vs_forecast.png"

    # Accuracy metric (kept only for return payload; not shown in titles)
    metric_key, _ = _pick_accuracy_metric(chosen.get("metrics", {}))

    # Titles (minimal + optional regressors on second line)
    subtitle = _subtitle_for_item(chosen)

    # Plots
    _plot_line(
        pred.rename(columns={"yhat": "y"}),
        "ds", "y",
        "Forecast", subtitle,
        fp_forecast, 
        xlim,
        forecast_color
    )
    _plot_line(
        act_plot,
        "ds", "y",
        "Actuals", '',
        fp_actuals, 
        xlim,
        real_data_color
    )

    # ---- accuracy (from JSON) ----
    metric_key, metric_payload = _pick_accuracy_metric(chosen.get("metrics", {}))
    acc_line = ""
    if metric_payload and (metric_payload.get("accuracy") is not None):
        try:
            m = re.fullmatch(r"within_(\d+)pct", metric_key or "")
            tol = m.group(1) if m else "?"
            acc_pct = round(100.0 * float(metric_payload["accuracy"]), 1)
            n_eval = int(metric_payload.get("n_eval", 0))
            n_total = int(metric_payload.get("n_total", 0))
            acc_line = f"Acc@{tol}%: {acc_pct}% (n={n_eval}/{n_total})"
        except Exception:
            acc_line = ""

    # ---- overlay plot ----
    fig = plt.figure()
    ax = fig.gca()
    if not act_plot.empty:
        ax.plot(act_plot["ds"], act_plot["y"], label="Actuals", color=real_data_color)
    ax.plot(pred["ds"], pred["yhat"], label="Forecast", color=forecast_color)
    if {"yhat_lower", "yhat_upper"}.issubset(pred.columns):
        try:
            ax.fill_between(pred["ds"], pred["yhat_lower"], pred["yhat_upper"], alpha=0.2, label="Uncertainty")
        except Exception:
            pass

    # title lines: 1) main, 2) regressors (if any), 3) accuracy (if any)
    subtitle = _subtitle_for_item(chosen)
    title_lines = ["Actuals vs Forecast"]
    if subtitle:
        title_lines.append(subtitle)
    if acc_line:
        title_lines.append(acc_line)
    ax.set_title("\n".join(title_lines))

    ax.set_xlabel("ds")
    ax.set_ylabel("value")
    ax.grid(True)
    ax.legend()
    ax.set_xlim(*xlim)
    _apply_monthly_ticks(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(fp_both, dpi=150)
    plt.close(fig)

    return {
        "kind": chosen.get("kind", "univariate"),
        "metric_key": metric_key,
        "forecast_png": str(fp_forecast.resolve()),
        "actuals_png": str(fp_actuals.resolve()),
        "both_png": str(fp_both.resolve()),
        "run_dir": str(run_dir.resolve()),
    }
