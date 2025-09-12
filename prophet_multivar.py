"""
prophet_multivar
----------------
Forecast a target parameter with Prophet using other parameters as extra regressors.

Example:
    from prophet_multivar import forecast_with_regressors

    fcst = forecast_with_regressors(
        timeseries_dir="timeseries/water_quality",
        target="Azot",
        regressors=["Amoniy", "Atrazin"],
        station_code=None,          # or "...", optional
        station_id=None,            # or "26853", optional
        freq="MS", agg="mean",
        train_start="2007-01-01", train_end="2010-12-31",
        fcst_start="2011-01-01", fcst_end="2012-12-31",
        forecast_name="set1"
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import json
import pandas as pd

from prophet import Prophet

# Reuse helpers/semantics from your existing univariate module
from prophet_module import (
    BASE_FORECASTS_DIR,
    _parse_dt,                 # datetime parser
    _read_param_csv,
    _filter_station,
    _aggregate,                # (ds,y) aggregation to freq with agg
    _apply_date_range,
    _align_next_step,
    _ceil_to_freq,
    _derive_periods,
    forecast_one,              # core Prophet fit/predict on (ds,y)
)

# -------------------------- internal helpers --------------------------

def _prepare_param_series(
    timeseries_dir: Path | str,
    param: str,
    station_code: Optional[str],
    station_id: Optional[str],
    freq: str,
    agg: str,
    train_start: Optional[object],
    train_end: Optional[object],
    rename_y_to: str,
) -> pd.DataFrame:
    """
    Load one parameter, filter station, apply train window, aggregate to (ds, y),
    then rename y -> rename_y_to.
    """
    df = _read_param_csv(timeseries_dir, param)
    df = _filter_station(df, station_code=station_code, station_id=station_id)
    df = _apply_date_range(df, start=train_start, end=train_end, col="ds")
    ser = _aggregate(df, freq=freq, how=agg)
    if ser.empty:
        return ser
    ser = ser[["ds", "y"]].dropna().sort_values("ds").reset_index(drop=True)
    return ser.rename(columns={"y": rename_y_to})


def _merge_on_ds(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """Left-join sequentially on 'ds' to keep common timestamps only (inner behavior)."""
    if not frames:
        return pd.DataFrame(columns=["ds"])
    out = frames[0]
    for f in frames[1:]:
        out = out.merge(f, on="ds", how="inner")
    # Ensure sorted and no duplicates
    return out.dropna().sort_values("ds").reset_index(drop=True)


def _forecast_regressors_future(
    timeseries_dir: Path | str,
    regs: List[str],
    station_code: Optional[str],
    station_id: Optional[str],
    freq: str,
    agg: str,
    train_start: Optional[object],
    train_end: Optional[object],
    fcst_start: pd.Timestamp,
    fcst_end: pd.Timestamp,
) -> pd.DataFrame:
    """
    Build a dense future dataframe on the exact [fcst_start..fcst_end] grid:
      columns = ['ds'] + regs
    Each regressor is forecast univariately; we take its yhat on that grid.
    Ensures no NaNs remain (ffill/bfill within the future window), else raises.
    """
    future_index = pd.date_range(start=fcst_start, end=fcst_end, freq=freq)
    reg_future = pd.DataFrame({"ds": future_index})

    for r in regs:
        # Training series for regressor r (aligned like the target)
        ser_r = _prepare_param_series(
            timeseries_dir=timeseries_dir,
            param=r,
            station_code=station_code,
            station_id=station_id,
            freq=freq,
            agg=agg,
            train_start=train_start,
            train_end=train_end,
            rename_y_to="y",
        )
        if ser_r.empty:
            raise ValueError(f"Regressor '{r}' has no data in the training window after filtering.")

        # Forecast regressor r exactly on [fcst_start..fcst_end]
        _, fcst_r = forecast_one(
            series=ser_r,
            periods=None,
            freq=freq,
            growth="linear",
            fcst_start=fcst_start,
            fcst_end=fcst_end,
        )
        yhat = fcst_r[["ds", "yhat"]].rename(columns={"yhat": r})
        reg_future = reg_future.merge(yhat, on="ds", how="left")

    # Reindex to ensure one row per future step and fill any internal gaps
    reg_future = reg_future.sort_values("ds").set_index("ds").reindex(future_index)
    reg_future = reg_future.ffill().bfill()

    # Final check: all regressors must be non-null
    missing_cols = [c for c in reg_future.columns if reg_future[c].isna().any()]
    if missing_cols:
        raise ValueError(f"Regressor(s) {missing_cols} missing after fill for some future steps.")

    return reg_future.reset_index().rename(columns={"index": "ds"})


# --------------------------- public API --------------------------------

def forecast_with_regressors(
    timeseries_dir: str | Path,
    target: str,
    regressors: List[str],
    # station filter
    station_code: Optional[str] = None,
    station_id: Optional[str] = None,
    # aggregation/model
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
    write_to_disk: bool = True,
) -> pd.DataFrame:
    """
    Multivariate Prophet with extra regressors:
      - Build training matrix on a common (ds) grid for [target + regressors]
      - Auto-forecast each regressor for future window and inject into target's future
      - Guarantee no NaNs in regressor columns before predict()

    Returns the target forecast DataFrame (ds, yhat, yhat_lower, yhat_upper) and,
    if write_to_disk=True, saves CSV and appends this run to forecasts/<forecast_name>/data.json.
    """
    ts_dir = Path(timeseries_dir)
    base_dir = Path(base_output_dir)
    out_dir = (base_dir / forecast_name).resolve()
    if write_to_disk:
        out_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 1) Build training matrix ----------
    target_train = _prepare_param_series(
        timeseries_dir=ts_dir,
        param=target,
        station_code=station_code,
        station_id=station_id,
        freq=freq,
        agg=agg,
        train_start=train_start,
        train_end=train_end,
        rename_y_to="y",
    )
    if target_train.empty:
        raise ValueError("Target has no data after applying station/date filters.")

    reg_frames = []
    for r in regressors:
        ser_r = _prepare_param_series(
            timeseries_dir=ts_dir,
            param=r,
            station_code=station_code,
            station_id=station_id,
            freq=freq,
            agg=agg,
            train_start=train_start,
            train_end=train_end,
            rename_y_to=r,
        )
        if ser_r.empty:
            raise ValueError(f"Regressor '{r}' has no data after applying station/date filters.")
        reg_frames.append(ser_r)

    train_df = _merge_on_ds([target_train] + reg_frames)
    if train_df.empty or len(train_df) < 10:
        raise ValueError("Insufficient overlapping data between target and regressors after alignment.")

    # ---------- 2) Decide forecast window ----------
    last_hist = train_df["ds"].max()
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

    # ---------- 3) Fit Prophet with regressors ----------
    m = Prophet(growth=growth)
    for r in regressors:
        m.add_regressor(r)

    m.fit(train_df.rename(columns={"ds": "ds", "y": "y"}))

    # Build future ds (history + periods)
    future = m.make_future_dataframe(periods=int(periods), freq=freq, include_history=True)

    # Merge historical regressor values into future (for history rows)
    future = future.merge(train_df.drop(columns=["y"]), on="ds", how="left")

    # For future rows, forecast regressors and fill
    if periods and periods > 0:
        if s is None:  # first future step after history
            s = _align_next_step(last_hist, freq)
        if e is None:  # derive end if only periods provided
            e = pd.date_range(start=s, periods=periods, freq=freq)[-1]

        reg_future = _forecast_regressors_future(
            timeseries_dir=ts_dir,
            regs=regressors,
            station_code=station_code,
            station_id=station_id,
            freq=freq,
            agg=agg,
            train_start=train_start,
            train_end=train_end,
            fcst_start=s,
            fcst_end=e,
        )

        # Merge future regressor values; prefer existing history values
        future = future.merge(reg_future, on="ds", how="left", suffixes=("", "_fcst"))
        for r in regressors:
            if r in future.columns and f"{r}_fcst" in future.columns:
                future[r] = future[r].combine_first(future[f"{r}_fcst"])
        future = future.drop(columns=[c for c in future.columns if c.endswith("_fcst")])

    # FINAL GUARD: Prophet forbids NaNs in extra regressors
    nan_cols = [r for r in regressors if r not in future.columns or future[r].isna().any()]
    if nan_cols:
        # Best-effort fill within full frame; if still NaN, raise with context
        for r in nan_cols:
            if r in future.columns:
                future[r] = future[r].ffill().bfill()
        nan_cols = [r for r in regressors if r not in future.columns or future[r].isna().any()]
        if nan_cols:
            bad = future[["ds"] + [r for r in regressors if r in future.columns]]
            bad = bad[bad.isna().any(axis=1)]
            raise ValueError(
                "Found NaN in regressors {} at rows:\n{}\n"
                "Consider widening training windows or adjusting frequency/aggregation.".format(
                    nan_cols, bad.to_string(index=False) if not bad.empty else "<no rows captured>"
                )
            )

    # ---------- 4) Predict and clip to requested forecast window ----------
    fcst = m.predict(future)
    if s is not None or e is not None:
        s_eff = s if s is not None else fcst["ds"].min()
        e_eff = e if e is not None else fcst["ds"].max()
        fcst = fcst.loc[fcst["ds"].between(s_eff, e_eff, inclusive="both")]

    result = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

    # ---------- 5) Save CSV and append to forecasts/<forecast_name>/data.json ----------
    if write_to_disk:
        out_dir.mkdir(parents=True, exist_ok=True)

        tag = "with_" + "+".join(regressors) if regressors else "univariate"
        fn_csv = out_dir / f"{target}__{tag}.csv"
        fn_csv.write_text(result.to_csv(index=False), encoding="utf-8")

        # build aligned ACTUALS for the target on the forecast range
        x_min, x_max = pd.to_datetime(result["ds"].min()), pd.to_datetime(result["ds"].max())
        raw_target = _read_param_csv(ts_dir, target)
        raw_target = _filter_station(raw_target, station_code=station_code, station_id=station_id)
        raw_target = _apply_date_range(raw_target, start=x_min, end=x_max, col="ds")
        actuals = _aggregate(raw_target, freq=freq, how=agg)  # (ds, y)
        actuals_daily = _build_daily_actuals(raw_target, start=x_min, end=x_max, agg=agg, fill="ffill_bfill", fill_limit=None)

        # append into data.json
        data_path = out_dir / "data.json"
        try:
            blob = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {"items": []}
            if not isinstance(blob, dict) or "items" not in blob:
                blob = {"items": []}
        except Exception:
            blob = {"items": []}

        blob["items"].append({
            "kind": "multivariate",
            "target": target,
            "regressors": regressors,
            "forecast_name": forecast_name,
            "timeseries_dir": str(ts_dir),
            "station_code": station_code,
            "station_id": station_id,
            "settings": {
                "freq": freq, "agg": agg, "growth": growth,
                "train_start": str(pd.to_datetime(train_start)) if train_start else None,
                "train_end": str(pd.to_datetime(train_end)) if train_end else None,
                "fcst_start": str(pd.to_datetime(result["ds"].min())),
                "fcst_end": str(pd.to_datetime(result["ds"].max())),
            },
            "predictions": [
                {
                    "ds": pd.to_datetime(r.ds).isoformat(),
                    "yhat": float(r.yhat),
                    "yhat_lower": float(r.yhat_lower),
                    "yhat_upper": float(r.yhat_upper),
                } for r in result.itertuples(index=False)
            ],
            "actuals": [
                {"ds": pd.to_datetime(r.ds).isoformat(), "y": float(r.y)}
                for r in actuals.itertuples(index=False)
            ],
            "actuals_daily": [
                {"ds": pd.to_datetime(r.ds).isoformat(), "y": (None if pd.isna(r.y) else float(r.y))}
                for r in actuals_daily.itertuples(index=False)
            ],
        })
        data_path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")

    return result

# Append to data.json
def _append_run_item_json(out_dir: Path, item: dict) -> Path:
    data_path = out_dir / "data.json"
    if data_path.exists():
        try:
            blob = json.loads(data_path.read_text(encoding="utf-8"))
            if not isinstance(blob, dict) or "items" not in blob:
                blob = {"items": []}
        except Exception:
            blob = {"items": []}
    else:
        blob = {"items": []}
    blob["items"].append(item)
    data_path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    return data_path

def _build_daily_actuals(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    agg: str = "mean",
    fill: str = "ffill_bfill",   # "none" | "ffill" | "ffill_bfill"
    fill_limit: int | None = None
) -> pd.DataFrame:
    """
    Make a continuous daily series on [start..end] from raw (ds,y) rows:
      - resample to 'D' with agg (mean/median/max/min)
      - optionally fill gaps to keep a smooth daily line on plots
    Returns DataFrame with ['ds','y'] daily.
    """
    if df.empty:
        return pd.DataFrame(columns=["ds", "y"])
    allowed = {"mean", "median", "max", "min"}
    if agg not in allowed:
        raise ValueError(f"agg must be one of {allowed}")

    s = df[["ds", "y"]].dropna().set_index("ds")["y"].resample("D")
    daily = {
        "mean": s.mean(),
        "median": s.median(),
        "max": s.max(),
        "min": s.min(),
    }[agg].to_frame("y")

    # reindex to full daily grid
    idx = pd.date_range(start=start, end=end, freq="D")
    daily = daily.reindex(idx)

    if fill == "ffill":
        daily["y"] = daily["y"].ffill(limit=fill_limit)
    elif fill == "ffill_bfill":
        daily["y"] = daily["y"].ffill(limit=fill_limit).bfill(limit=fill_limit)

    return daily.reset_index().rename(columns={"index": "ds"})