"""
prophet_module
--------------
Reusable module for batch forecasting with Prophet, with date-range controls
and portable saving to a top-level `forecasts/<forecast_name>/` folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple
import json
import pandas as pd
from pandas.tseries.frequencies import to_offset

try:
    from prophet import Prophet
except Exception as e:
    raise RuntimeError("Prophet is required. Install with: pip install prophet pandas") from e

# Where to save by default (sibling to this module)
BASE_FORECASTS_DIR = (Path(__file__).resolve().parent.parent / "forecasts").resolve()

# ------------------------- helpers -------------------------

def _parse_dt(x: Optional[object]) -> Optional[pd.Timestamp]:
    if x is None:
        return None
    dt = pd.to_datetime(x, errors="coerce")
    return None if pd.isna(dt) else dt

def _apply_date_range(df: pd.DataFrame, start: Optional[object], end: Optional[object], col: str = "ds") -> pd.DataFrame:
    s = _parse_dt(start)
    e = _parse_dt(end)
    out = df
    if s is not None:
        out = out[out[col] >= s]
    if e is not None:
        out = out[out[col] <= e]
    return out

def _align_next_step(ts: pd.Timestamp, freq: str) -> pd.Timestamp:
    return pd.date_range(start=ts, periods=2, freq=freq)[1]

def _ceil_to_freq(ts: pd.Timestamp, freq: str) -> pd.Timestamp:
    r = pd.date_range(start=ts, periods=2, freq=freq)
    return r[0] if r[0] == ts else r[1]

def _derive_periods(last_hist: pd.Timestamp, fcst_end: pd.Timestamp, freq: str) -> int:
    if fcst_end <= last_hist:
        return 0
    steps = pd.date_range(start=last_hist, end=fcst_end, freq=freq, inclusive="neither")
    return max(len(steps), 1)

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
    if df.empty:
        return df
    allowed = {"mean", "median", "max", "min"}
    if how not in allowed:
        raise ValueError(f"agg must be one of {allowed}")
    s = df[["ds", "y"]].dropna().set_index("ds")["y"].resample(freq)
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
    if "ds" not in df.columns or "y" not in df.columns:
        raise ValueError("Input DataFrame must have columns ['ds','y']")
    df = _apply_date_range(df, start=train_start, end=train_end, col="ds")
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
    If `fcst_end` is given, `periods` is derived from the last training timestamp.
    Returned forecast is clipped inclusively to [fcst_start, fcst_end] if provided.
    """
    if series.empty:
        raise ValueError("Series is empty after filtering/aggregation")
    series = series.sort_values("ds").reset_index(drop=True)
    last_hist = series["ds"].max()

    s = _parse_dt(fcst_start) if fcst_start is not None else None
    e = _parse_dt(fcst_end) if fcst_end is not None else None

    if s is None and e is not None:
        s = _align_next_step(last_hist, freq)
    if e is not None:
        e = _ceil_to_freq(e, freq)
    if e is not None:
        periods = _derive_periods(last_hist, e, freq)
    if periods is None:
        periods = 0

    m = Prophet(growth=growth)
    m.fit(series.rename(columns={"ds": "ds", "y": "y"}))
    future = m.make_future_dataframe(periods=int(periods), freq=freq, include_history=True)
    fcst = m.predict(future)

    if s is not None or e is not None:
        s_eff = s if s is not None else fcst["ds"].min()
        e_eff = e if e is not None else fcst["ds"].max()
        fcst = fcst.loc[fcst["ds"].between(s_eff, e_eff, inclusive="both")]

    return m, fcst

# ------------------------- Batch processing & saving -----------------------------

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
    periods: Optional[int] = 12,
    fcst_start: Optional[object] = None,
    fcst_end: Optional[object] = None,
    # saving
    write_to_disk: bool = False,
    forecast_name: str = "run1",
    base_output_dir: Path | str = BASE_FORECASTS_DIR,
) -> Dict[str, pd.DataFrame]:
    """
    Run forecasts for one or all parameters.

    Saves under: <base_output_dir>/<forecast_name>/ when write_to_disk=True
      - <param>.csv (ds,yhat,yhat_lower,yhat_upper)
      - _manifest.json (one per run)

    Returns dict {param: forecast_df} in all cases.
    """
    ts_dir = Path(timeseries_dir)
    outputs: Dict[str, pd.DataFrame] = {}

    base_dir = Path(base_output_dir)
    out_root = (base_dir / forecast_name).resolve()
    if write_to_disk:
        out_root.mkdir(parents=True, exist_ok=True)

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
            (out_root / f"{prm}.csv").write_text(result.to_csv(index=False), encoding="utf-8")

    if write_to_disk:
        manifest = {
            "timeseries_dir": str(ts_dir),
            "output_dir": str(out_root),
            "forecast_name": forecast_name,
            "params": [{"name": k, "forecast_file": str(out_root / f"{k}.csv")} for k in sorted(outputs.keys())],
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
