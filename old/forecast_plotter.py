"""
forecast_plotter
----------------
Generates three plots per parameter and writes a JSON file containing the
predictions and paths to the images. Everything is saved under:

  forecasts/<forecast_name>/

No CLI — import and call generate_plots(...).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict
import json
import pandas as pd
import matplotlib.pyplot as plt

from prophet_module import (
    batch_forecast,
    BASE_FORECASTS_DIR,  # use same base folder
)

# --------------------------- basic IO helpers ---------------------------

def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _read_param_csv(timeseries_dir: str | Path, param: str) -> pd.DataFrame:
    ts_dir = Path(timeseries_dir)
    candidate = ts_dir / f"{param}.csv"
    if not candidate.exists():
        matches = [p for p in ts_dir.glob("*.csv") if p.stem.lower() == param.lower()]
        if not matches:
            raise FileNotFoundError(f"Parameter file '{param}' not found in {ts_dir}")
        candidate = matches[0]
    df = pd.read_csv(candidate, parse_dates=["ds"])
    return df.sort_values("ds").reset_index(drop=True)

def _filter_station(df: pd.DataFrame, station_code: Optional[str], station_id: Optional[str]) -> pd.DataFrame:
    out = df
    if station_code is not None and "post_code" in out.columns:
        out = out[out["post_code"] == station_code]
    if station_id is not None and "post_id" in out.columns:
        out = out[out["post_id"].astype(str) == str(station_id)]
    return out

def _apply_range(df: pd.DataFrame, start: Optional[object], end: Optional[object], col: str = "ds") -> pd.DataFrame:
    s = None if start is None else pd.to_datetime(start, errors="coerce")
    e = None if end is None else pd.to_datetime(end, errors="coerce")
    out = df
    if s is not None:
        out = out[out[col] >= s]
    if e is not None:
        out = out[out[col] <= e]
    return out

def _aggregate_actuals(df: pd.DataFrame, freq: str, agg: str) -> pd.DataFrame:
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

def _suffix(param: str, station_code: Optional[str], station_id: Optional[str]) -> str:
    parts = [param]
    if station_code:
        parts.append(f"code={station_code}")
    if station_id:
        parts.append(f"id={station_id}")
    return "__".join(parts)

def _plot_with_xlim(df: pd.DataFrame, x: str, y: str, title: str, outfile: Path, xlim: tuple[pd.Timestamp, pd.Timestamp]) -> None:
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

def generate_plots(
    timeseries_dir: str | Path,
    param: str,
    # station filter
    station_code: Optional[str] = None,
    station_id: Optional[str] = None,
    # aggregation/model settings (match your forecasting)
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
    forecast_name: str = "run1",
    base_output_dir: Path | str = BASE_FORECASTS_DIR,
) -> Dict[str, str]:
    """
    Generates three PNGs and a JSON file with predictions + image paths, saved to:
      forecasts/<forecast_name>/

    Returns a dict with absolute paths to the generated files.
    """
    # Resolve forecast output folder
    base_dir = Path(base_output_dir)
    out_dir = (base_dir / forecast_name).resolve()
    _safe_mkdir(out_dir)

    # 1) Run forecast (returned DataFrame is already clipped to requested fcst window)
    fcst_map = batch_forecast(
        timeseries_dir=timeseries_dir,
        param=param,
        station_code=station_code,
        station_id=station_id,
        freq=freq,
        agg=agg,
        growth=growth,
        train_start=train_start,
        train_end=train_end,
        periods=periods,       # ignored if fcst_end is provided
        fcst_start=fcst_start,
        fcst_end=fcst_end,
        write_to_disk=False,   # plotting handles saving itself
        forecast_name=forecast_name,
        base_output_dir=base_dir,
    )
    if param not in fcst_map or fcst_map[param].empty:
        raise ValueError(f"No forecast produced for '{param}'. Check ranges/filters.")
    fcst_df = fcst_map[param].copy()  # ds, yhat, yhat_lower, yhat_upper

    # Normalize plotting window exactly to the forecast df range
    x_min, x_max = fcst_df["ds"].min(), fcst_df["ds"].max()

    # 2) Actuals aligned to same window and frequency
    raw = _read_param_csv(timeseries_dir, param)
    raw = _filter_station(raw, station_code=station_code, station_id=station_id)
    raw = _apply_range(raw, x_min, x_max, col="ds")
    actuals_df = _aggregate_actuals(raw, freq=freq, agg=agg)

    # 3) File names
    suffix = _suffix(param, station_code, station_id)
    fp_forecast = out_dir / f"{suffix}__forecast.png"
    fp_actuals = out_dir / f"{suffix}__actuals.png"
    fp_both = out_dir / f"{suffix}__actuals_vs_forecast.png"
    fp_json = out_dir / f"{suffix}__forecast.json"

    # 4) Plots (all limited to forecast x-range)
    xlim = (x_min, x_max)
    _plot_with_xlim(fcst_df.rename(columns={"yhat": "y"}), "ds", "y", f"Forecast: {param}", fp_forecast, xlim)
    _plot_with_xlim(actuals_df, "ds", "y", f"Actuals: {param}", fp_actuals, xlim)

    fig = plt.figure()
    ax = fig.gca()
    if not actuals_df.empty:
        ax.plot(actuals_df["ds"], actuals_df["y"], label="Actuals")
    ax.plot(fcst_df["ds"], fcst_df["yhat"], label="Forecast")
    ax.set_title(f"Actuals vs Forecast: {param}")
    ax.set_xlabel("ds")
    ax.set_ylabel("value")
    ax.grid(True)
    ax.legend()
    ax.set_xlim(*xlim)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(fp_both, dpi=150)
    plt.close(fig)

    # 5) Save JSON with predictions + image paths
    payload = {
        "param": param,
        "station_code": station_code,
        "station_id": station_id,
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
        "settings": {
            "freq": freq, "agg": agg, "growth": growth,
            "train_start": str(pd.to_datetime(train_start)) if train_start else None,
            "train_end": str(pd.to_datetime(train_end)) if train_end else None,
            "fcst_start": str(pd.to_datetime(fcst_start)) if fcst_start else None,
            "fcst_end": str(pd.to_datetime(fcst_end)) if fcst_end else None,
        },
    }
    fp_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "forecast_png": str(fp_forecast.resolve()),
        "actuals_png": str(fp_actuals.resolve()),
        "both_png": str(fp_both.resolve()),
        "json": str(fp_json.resolve()),
        "output_dir": str(out_dir),
    }
