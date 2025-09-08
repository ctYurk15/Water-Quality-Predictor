"""
prophet_module
--------------
Reusable module for batch forecasting with Prophet, now with date-range controls.

New args:
  - train_start, train_end: limit the history used to train Prophet
  - fcst_start, fcst_end:   limit the forecast window; periods auto-derived from fcst_end

Date strings are parsed with pandas.to_datetime (e.g., "2007-01-01").
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import json
import pandas as pd

try:
    from prophet import Prophet
except Exception as e:
    raise RuntimeError("Prophet is required. Install with: pip install prophet pandas") from e


# ------------------------- Helpers -------------------------

def _parse_dt(x: Optional[object]) -> Optional[pd.Timestamp]:
    if x is None:
        return None
    dt = pd.to_datetime(x, errors="coerce")
    return None if pd.isna(dt) else dt


def _apply_date_range(df: pd.DataFrame, start: Optional[object], end: Optional[object], col: str = "ds") -> pd.DataFrame:
    """Filter df so start <= df[col] <= end (inclusive)."""
    s = _parse_dt(start)
    e = _parse_dt(end)
    out = df
    if s is not None:
        out = out[out[col] >= s]
    if e is not None:
        out = out[out[col] <= e]
    return out


def _steps_between(last_hist: pd.Timestamp, end: pd.Timestamp, freq: str) -> int:
    """
    Count how many forward steps of `freq` are needed from last_hist to reach `end`.
    Examples:
      last_hist=2007-01-31, end=2007-04-30, freq='M' -> 3 steps (Feb, Mar, Apr)
    """
    if end <= last_hist:
        return 0
    rng = pd.date_range(start=last_hist, end=end, freq=freq, inclusive="neither")
    return len(rng)


# ------------------------- IO / filtering -------------------------

def _read_param_csv(timeseries_dir: Path | str, param: str) -> pd.DataFrame:
    ts_dir = Path(timeseries_dir)
    candidate = ts_dir / f"{param}.csv"
    if not candidate.exists():
        matches = [p for p in ts_dir.glob("*.csv") if p.stem.lower() == param.lower()]
        if not matches:
            raise FileNotFoundError(f"Parameter file '{param}' not found in {ts_dir}")
        candidate = matches[0]
    df = pd.read_csv(candidate, parse_dates=["ds"])
    return df.sort_values("ds")


def _filter_station(df: pd.DataFrame, station_code: Optional[str], station_id: Optional[str]) -> pd.DataFrame:
    out = df
    if station_code is not None and "post_code" in out.columns:
        out = out[out["post_code"] == station_code]
    if station_id is not None and "post_id" in out.columns:
        out = out[out["post_id"].astype(str) == str(station_id)]
    return out


def _aggregate(df: pd.DataFrame, freq: str, how: str) -> pd.DataFrame:
    """Resample to a regular frequency with aggregation (mean/median/max/min)."""
    if df.empty:
        return df
    allowed = {"mean", "median", "max", "min"}
    if how not in allowed:
        raise ValueError(f"agg must be one of {allowed}")

    s = (
        df[["ds", "y"]].dropna().set_index("ds")["y"]  # <- Series resampler avoids rename bug
        .resample(freq)
    )
    agg_map = {
        "mean": s.mean(),
        "median": s.median(),
        "max": s.max(),
        "min": s.min(),
    }
    out = agg_map[how].to_frame(name="y").reset_index()
    return out.dropna()


def _prepare_series(
    df: pd.DataFrame,
    freq: str,
    agg: str,
    train_start: Optional[object],
    train_end: Optional[object],
) -> pd.DataFrame:
    """Prepare a single series for Prophet: filter by training range, resample, return (ds,y)."""
    if "ds" not in df.columns or "y" not in df.columns:
        raise ValueError("Input DataFrame must have columns ['ds','y']")
    # 1) apply training date window BEFORE aggregation
    df = _apply_date_range(df, start=train_start, end=train_end, col="ds")
    # 2) aggregate to regular frequency
    ser = _aggregate(df, freq=freq, how=agg)
    if ser.empty:
        return ser
    return ser[["ds", "y"]].dropna().sort_values("ds").reset_index(drop=True)


# ------------------------------- Prophet --------------------------------

def forecast_one(
    series: pd.DataFrame,
    periods: Optional[int] = 12,
    freq: str = "MS",
    growth: str = "linear",
    fcst_start: Optional[object] = None,
    fcst_end: Optional[object] = None,
) -> Tuple[Prophet, pd.DataFrame]:
    """
    Train Prophet on `series` (ds,y) and produce forecast.

    If `fcst_end` is provided, `periods` is auto-computed from the last history ds to fcst_end.
    `fcst_start`/`fcst_end` are applied to the *returned* forecast (filtering rows).
    """
    if series.empty:
        raise ValueError("Series is empty after filtering/aggregation")
    series = series.sort_values("ds")
    last_hist = series["ds"].max()

    # Auto-derive periods if fcst_end given
    if fcst_end is not None:
        end_dt = _parse_dt(fcst_end)
        if end_dt is None:
            raise ValueError("fcst_end could not be parsed into a datetime")
        steps = _steps_between(last_hist, end_dt, freq=freq)
        periods = max(steps, 0)

    if periods is None:
        periods = 0  # no future steps, only history predictions

    m = Prophet(growth=growth)
    m.fit(series.rename(columns={"ds": "ds", "y": "y"}))
    future = m.make_future_dataframe(periods=int(periods), freq=freq, include_history=True)
    fcst = m.predict(future)

    # Filter returned forecast to requested fcst window (if any)
    fcst = _apply_date_range(fcst, start=fcst_start, end=fcst_end, col="ds")
    return m, fcst


# ------------------------- Batch processing -----------------------------

def _iter_params(timeseries_dir: Path | str):
    ts_dir = Path(timeseries_dir)
    for p in sorted(ts_dir.glob("*.csv")):
        if p.name.startswith("_"):
            continue
        yield p.stem


def batch_forecast(
    timeseries_dir: str | Path,
    param: Optional[str] = None,
    station_code: Optional[str] = None,
    station_id: Optional[str] = None,
    # aggregation / model
    freq: str = "MS",
    agg: str = "mean",
    growth: str = "linear",
    # training window
    train_start: Optional[object] = None,
    train_end: Optional[object] = None,
    # forecast window
    periods: Optional[int] = 12,           # used if fcst_end is None
    fcst_start: Optional[object] = None,
    fcst_end: Optional[object] = None,
    # output
    write_to_disk: bool = False,
    outdir_name: str = "_forecasts",
) -> Dict[str, pd.DataFrame]:
    """
    Run forecasts for one or all parameters.

    Training window:
      - train_start/train_end limit the *history* used to fit the model.

    Forecast window:
      - If fcst_end is provided, periods is auto-computed from the last training point to fcst_end.
      - fcst_start/fcst_end filter the *returned* forecast rows.
      - If both are None, returns full history+future horizon (periods).

    Returns dict {param: forecast_df}. If write_to_disk=True, also writes CSV and a manifest.
    """
    ts_dir = Path(timeseries_dir)
    outputs: Dict[str, pd.DataFrame] = {}

    out_root = ts_dir / outdir_name
    if write_to_disk:
        out_root.mkdir(parents=True, exist_ok=True)

    def _out_name(prm: str) -> str:
        suffix = []
        if station_code:
            suffix.append(f"code={station_code}")
        if station_id:
            suffix.append(f"id={station_id}")
        if train_start or train_end:
            suffix.append(f"train={str(_parse_dt(train_start))[:10]}..{str(_parse_dt(train_end))[:10]}")
        if fcst_start or fcst_end:
            suffix.append(f"fcst={str(_parse_dt(fcst_start))[:10]}..{str(_parse_dt(fcst_end))[:10]}")
        return f"{prm}" + (("__" + "_".join(suffix)) if suffix else "") + ".csv"

    params = [param] if param else list(_iter_params(ts_dir))

    for prm in params:
        df = _read_param_csv(ts_dir, prm)
        df = _filter_station(df, station_code=station_code, station_id=station_id)
        ser = _prepare_series(df, freq=freq, agg=agg, train_start=train_start, train_end=train_end)
        if ser.empty:
            continue

        _, fcst = forecast_one(
            ser,
            periods=periods,
            freq=freq,
            growth=growth,
            fcst_start=fcst_start,
            fcst_end=fcst_end,
        )
        result = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        outputs[prm] = result

        if write_to_disk:
            (out_root / _out_name(prm)).write_text(result.to_csv(index=False), encoding="utf-8")

    if write_to_disk:
        manifest = {
            "timeseries_dir": str(ts_dir),
            "outdir": str(out_root),
            "params": [{"name": k, "forecast_file": str(out_root / _out_name(k))} for k in sorted(outputs.keys())],
            "settings": {
                "freq": freq, "agg": agg, "growth": growth,
                "train_start": str(_parse_dt(train_start)) if train_start else None,
                "train_end": str(_parse_dt(train_end)) if train_end else None,
                "periods": periods,
                "fcst_start": str(_parse_dt(fcst_start)) if fcst_start else None,
                "fcst_end": str(_parse_dt(fcst_end)) if fcst_end else None,
                "station_code": station_code, "station_id": station_id,
            },
        }
        (out_root / "_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return outputs
