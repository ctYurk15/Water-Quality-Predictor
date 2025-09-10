"""
forecast_plotter_multivar
-------------------------
Render 3 PNGs for a multivariate Prophet forecast (target + extra regressors)
and save a JSON bundle with predictions and image paths.

Outputs go to: forecasts/<forecast_name>/

Depends on:
  - prophet_multivar.py (forecast_with_regressors)
  - prophet_module.py  (helpers + BASE_FORECASTS_DIR)

No CLI — import and call generate_multivar_plots(...).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List
import json
import pandas as pd
import matplotlib.pyplot as plt

from prophet_module import (
    BASE_FORECASTS_DIR,
    _read_param_csv,
    _filter_station,
)
from prophet_multivar import forecast_with_regressors


# --------------------------- helpers ---------------------------

def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _apply_range(df: pd.DataFrame, start: Optional[pd.Timestamp], end: Optional[pd.Timestamp], col: str = "ds") -> pd.DataFrame:
    out = df
    if start is not None:
        out = out[out[col] >= pd.to_datetime(start)]
    if end is not None:
        out = out[out[col] <= pd.to_datetime(end)]
    return out


def _aggregate_actuals(df: pd.DataFrame, freq: str, agg: str) -> pd.DataFrame:
    """Resample actual observations to match forecast frequency."""
    if df.empty:
        return df
    allowed = {"mean", "median", "max", "min"}
    if agg not in allowed:
        raise ValueError(f"agg must be one of {allowed}")
    s = df[["ds", "y"]].dropna().set_index("ds")["y"].resample(freq)
    out = {
        "mean": s.mean(),
        "median": s.median(),
        "max": s.max(),
        "min": s.min(),
    }[agg].to_frame("y").reset_index()
    return out.dropna()


def _suffix(target: str, regressors: List[str], station_code: Optional[str], station_id: Optional[str]) -> str:
    parts = [target, "with_" + "+".join(regressors) if regressors else "univariate"]
    if station_code:
        parts.append(f"code={station_code}")
    if station_id:
        parts.append(f"id={station_id}")
    return "__".join(parts)


def _plot_line(df: pd.DataFrame, x: str, y: str, title: str, outfile: Path, xlim: tuple[pd.Timestamp, pd.Timestamp]) -> None:
    """Single line plot. No seaborn, no explicit colors."""
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


# --------------------------- public API ---------------------------

def generate_multivar_plots(
    timeseries_dir: str | Path,
    target: str,
    regressors: List[str],
    # station filter
    station_code: Optional[str] = None,
    station_id: Optional[str] = None,
    # aggregation/model (must match your training)
    freq: str = "MS",
    agg: str = "mean",
    growth: str = "linear",
    # training window
    train_start: Optional[object] = None,
    train_end: Optional[object] = None,
    # forecast window
    periods: Optional[int] = 12,
    fcst_start: Optional[object] = None,
    fcst_end: Optional[object] = None,
    # saving
    forecast_name: str = "multirun1",
    base_output_dir: Path | str = BASE_FORECASTS_DIR,
    write_json: bool = True,
) -> Dict[str, str]:
    """
    Runs a multivariate forecast and generates:
      - <forecast_name>/<target>__with_<r1+...>__forecast.png
      - <forecast_name>/<target>__with_<r1+...>__actuals.png
      - <forecast_name>/<target>__with_<r1+...>__actuals_vs_forecast.png
      - <forecast_name>/<target>__with_<r1+...>.json   (predictions + image paths)

    Returns a dict with absolute file paths.
    """
    # 1) Compute or recompute the multivariate forecast (saved CSVs are handled by the forecaster if write_to_disk=True)
    fcst_df = forecast_with_regressors(
        timeseries_dir=timeseries_dir,
        target=target,
        regressors=regressors,
        station_code=station_code,
        station_id=station_id,
        freq=freq,
        agg=agg,
        growth=growth,
        train_start=train_start,
        train_end=train_end,
        periods=periods,
        fcst_start=fcst_start,
        fcst_end=fcst_end,
        forecast_name=forecast_name,
        base_output_dir=base_output_dir,
        write_to_disk=True,  # still save CSV + manifest for traceability
    )

    # 2) Resolve output folder (same place as forecaster)
    base_dir = Path(base_output_dir)
    out_dir = (base_dir / forecast_name).resolve()
    _safe_mkdir(out_dir)

    # 3) Plotting window from forecast df
    x_min, x_max = pd.to_datetime(fcst_df["ds"].min()), pd.to_datetime(fcst_df["ds"].max())
    xlim = (x_min, x_max)

    # 4) Actuals for the TARGET aligned to same freq and window
    raw_target = _read_param_csv(timeseries_dir, target)
    raw_target = _filter_station(raw_target, station_code=station_code, station_id=station_id)
    raw_target = _apply_range(raw_target, x_min, x_max, col="ds")
    actuals_df = _aggregate_actuals(raw_target, freq=freq, agg=agg)

    # 5) File names
    suffix = _suffix(target, regressors, station_code, station_id)
    fp_forecast = out_dir / f"{suffix}__forecast.png"
    fp_actuals = out_dir / f"{suffix}__actuals.png"
    fp_both = out_dir / f"{suffix}__actuals_vs_forecast.png"
    fp_json = out_dir / f"{suffix}.json"

    # 6) Render plots
    _plot_line(fcst_df.rename(columns={"yhat": "y"}), "ds", "y", f"Forecast: {target}", fp_forecast, xlim)
    _plot_line(actuals_df, "ds", "y", f"Actuals: {target}", fp_actuals, xlim)

    fig = plt.figure()
    ax = fig.gca()
    if not actuals_df.empty:
        ax.plot(actuals_df["ds"], actuals_df["y"], label="Actuals")
    ax.plot(fcst_df["ds"], fcst_df["yhat"], label="Forecast")
    # Optional: show uncertainty band without explicit colors
    try:
        ax.fill_between(fcst_df["ds"], fcst_df["yhat_lower"], fcst_df["yhat_upper"], alpha=0.2, label="Uncertainty")
    except Exception:
        pass
    ax.set_title(f"Actuals vs Forecast: {target} (with {', '.join(regressors)})")
    ax.set_xlabel("ds")
    ax.set_ylabel("value")
    ax.grid(True)
    ax.legend()
    ax.set_xlim(*xlim)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(fp_both, dpi=150)
    plt.close(fig)

    # 7) JSON bundle with predictions + image paths
    if write_json:
        payload = {
            "target": target,
            "regressors": regressors,
            "forecast_name": forecast_name,
            "output_dir": str(out_dir),
            "images": {
                "forecast_png": str(fp_forecast.resolve()),
                "actuals_png": str(fp_actuals.resolve()),
                "both_png": str(fp_both.resolve()),
            },
            "predictions": [
                {
                    "ds": pd.to_datetime(r.ds).isoformat(),
                    "yhat": float(r.yhat),
                    "yhat_lower": float(r.yhat_lower),
                    "yhat_upper": float(r.yhat_upper),
                }
                for r in fcst_df.itertuples(index=False)
            ],
        }
        fp_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "forecast_png": str(fp_forecast.resolve()),
        "actuals_png": str(fp_actuals.resolve()),
        "both_png": str(fp_both.resolve()),
        "json": str(fp_json.resolve()),
        "output_dir": str(out_dir),
    }
