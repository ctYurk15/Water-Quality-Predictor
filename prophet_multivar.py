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
    *,
    # strategy knobs
    strategy: str = "prophet",           # 'prophet' | 'moving_average' | 'last' | 'linear'
    ma_window: int = 30,                 # for moving_average
    linear_window: int = 90,             # days used to fit linear trend
    prophet_cp_scale: float = 0.01,      # smooth trend for regressor
    prophet_disable_seasonality: bool = True,
) -> pd.DataFrame:
    """
    Return dense future for regressors on [fcst_start..fcst_end] with columns ['ds'] + regs.
    Ensures no NaNs (ffill/bfill).
    """
    future_index = pd.date_range(start=fcst_start, end=fcst_end, freq=freq)
    out = pd.DataFrame({"ds": future_index}).set_index("ds")

    for r in regs:
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
        hist = ser_r.sort_values("ds").set_index("ds")["y"]

        if strategy == "last":
            y_future = pd.Series(hist.iloc[-1], index=future_index)

        elif strategy == "moving_average":
            val = hist.rolling(ma_window, min_periods=1).mean().iloc[-1]
            y_future = pd.Series(val, index=future_index)

        elif strategy == "linear":
            # === FIX: stop using deprecated .last("ND"); use a timestamp mask instead ===
            if len(hist) > 3:
                cutoff = hist.index.max() - pd.Timedelta(days=int(linear_window))
                h = hist.loc[hist.index >= cutoff]
                if h.empty:  # fallback just in case
                    h = hist
            else:
                h = hist

            x = (h.index.view("int64") // 10**9).astype(float)  # seconds since epoch
            y = h.values.astype(float)
            x_mean, y_mean = x.mean(), y.mean()
            denom = ((x - x_mean) ** 2).sum()
            if denom == 0:
                slope = 0.0
                intercept = y_mean
            else:
                slope = ((x - x_mean) * (y - y_mean)).sum() / denom
                intercept = y_mean - slope * x_mean
            xf = (future_index.view("int64") // 10**9).astype(float)
            y_future = pd.Series(intercept + slope * xf, index=future_index)

        else:  # 'prophet' (ultra-smooth)
            pm = Prophet(
                growth="linear",
                changepoint_prior_scale=prophet_cp_scale,
                yearly_seasonality=not prophet_disable_seasonality,
                weekly_seasonality=not prophet_disable_seasonality,
                daily_seasonality=False,
            )
            pm.fit(ser_r.rename(columns={"ds": "ds", "y": "y"}))
            pfut = pd.DataFrame({"ds": future_index})
            pfc = pm.predict(pfut)[["ds", "yhat"]].set_index("ds")["yhat"]
            y_future = pfc.reindex(future_index)

        out[r] = y_future

    out = out.reindex(future_index).ffill().bfill()
    return out.reset_index().rename(columns={"index": "ds"})




# --------------------------- public API --------------------------------

def forecast_with_regressors(
    timeseries_dir: str | Path,
    target: str,
    regressors: List[str],
    # station filter
    station_code: Optional[str] = None,
    station_id: Optional[str] = None,
    # OUTPUT grid for predictions/images
    freq: str = "D",                    # <-- daily output points
    # MODEL grid for Prophet fit/forecast (can be smoother than output)
    model_freq: Optional[str] = None,   # e.g. "W"; if None -> same as freq
    # aggregation/model grid
    agg: str = "mean",
    growth: str = "linear",             # overridden to 'logistic' if bounds provided
    # optional bounds for TARGET
    target_min: Optional[float] = None,
    target_max: Optional[float] = None,
    # training window
    train_start: Optional[object] = None,
    train_end: Optional[object] = None,
    # forecast window (in absolute dates or periods on the MODEL grid)
    periods: Optional[int] = None,
    fcst_start: Optional[object] = None,
    fcst_end: Optional[object] = None,
    # saving
    forecast_name: str = "multirun1",
    base_output_dir: Path | str = BASE_FORECASTS_DIR,
    write_to_disk: bool = True,
    # accuracy
    accuracy_tolerance: float = 0.20,
    # stability & smoothing knobs
    regressor_prior_scale: float = 0.1,
    regressor_mode: Optional[str] = None,        # "additive" | "multiplicative" | None
    regressor_standardize: str | bool = "auto",
    smooth_regressors: bool = True,
    smooth_window: int = 7,
    changepoint_prior_scale: float = 0.05,
    seasonality_prior_scale: float = 5.0,
    # importance controls
    regressor_global_importance: float = 1.0,
    regressor_importance: Optional[Dict[str, float]] = None,
    # FUTURE regressor generation
    regressor_future_strategy: str = "moving_average",  # 'prophet' | 'moving_average' | 'last' | 'linear'
    regressor_future_ma_window: int = 30,
    regressor_future_linear_window: int = 90,
    regressor_future_prophet_cp_scale: float = 0.01,
    regressor_future_prophet_disable_seasonality: bool = True,
) -> pd.DataFrame:
    """
    Train on `model_freq` (e.g., 'W') and output predictions on `freq` (e.g., 'D').
    This stabilizes daily forecasts by modeling a smoother signal and then
    linearly interpolating to daily points for presentation.

    Writes CSV + data.json under forecasts/<forecast_name>/ with:
      - predictions on OUTPUT grid (freq)
      - accuracy computed on MODEL grid (more meaningful)
      - daily actuals for plotting
    """
    ts_dir = Path(timeseries_dir)
    out_dir = (Path(base_output_dir) / forecast_name).resolve()
    if write_to_disk:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Decide model grid
    mod_freq = model_freq or freq

    # ---- bounds / logistic config ----
    use_bounds = (target_min is not None) or (target_max is not None)
    if use_bounds:
        if (target_min is not None) and (target_max is not None) and float(target_min) >= float(target_max):
            raise ValueError("target_min must be < target_max when both are provided.")
        floor_val = float(target_min) if target_min is not None else 0.0
        cap_val = float(target_max) if target_max is not None else float("inf")
    else:
        floor_val = None
        cap_val = None

    # ---- 1) training matrix on MODEL grid ----
    target_train = _prepare_param_series(
        ts_dir, target, station_code, station_id, mod_freq, agg, train_start, train_end, rename_y_to="y"
    )
    if target_train.empty:
        raise ValueError("Target has no data after applying station/date filters.")

    reg_frames = []
    for r in regressors:
        ser_r = _prepare_param_series(
            ts_dir, r, station_code, station_id, mod_freq, agg, train_start, train_end, rename_y_to=r
        )
        if ser_r.empty:
            raise ValueError(f"Regressor '{r}' has no data after applying station/date filters.")
        reg_frames.append(ser_r)

    train_df = _merge_on_ds([target_train] + reg_frames)
    if train_df.empty or len(train_df) < 10:
        raise ValueError("Insufficient overlapping data between target and regressors after alignment.")

    # bounds for logistic
    if use_bounds:
        if cap_val != float("inf"):
            train_df["cap"] = cap_val
        train_df["floor"] = floor_val

    # optional smoothing (history)
    if smooth_regressors and smooth_window > 1:
        train_df = train_df.sort_values("ds")
        for r in regressors:
            train_df[r] = train_df[r].rolling(window=smooth_window, min_periods=1).mean()

    # ---- 2) forecast window on MODEL grid ----
    last_hist = train_df["ds"].max()
    s = _parse_dt(fcst_start) if fcst_start is not None else None
    e = _parse_dt(fcst_end) if fcst_end is not None else None
    if s is None and e is not None:
        s = _align_next_step(last_hist, mod_freq)
    if e is not None:
        e = _ceil_to_freq(e, mod_freq)
    if e is not None:
        periods = _derive_periods(last_hist, e, mod_freq)
    if periods is None:
        periods = 0

    # ---- 3) fit Prophet (regularized) on MODEL grid ----
    model_growth = "logistic" if use_bounds else growth
    m = Prophet(
        growth=model_growth,
        changepoint_prior_scale=changepoint_prior_scale,
        seasonality_prior_scale=seasonality_prior_scale,
    )

    reg_imp = regressor_importance or {}
    for r in regressors:
        eff_ps = regressor_prior_scale * regressor_global_importance * float(reg_imp.get(r, 1.0))
        if eff_ps <= 0:
            eff_ps = 1e-6
        m.add_regressor(r, prior_scale=eff_ps, standardize=regressor_standardize, mode=regressor_mode)

    m.fit(train_df.rename(columns={"ds": "ds", "y": "y"}))

    # ---- 4) build future on MODEL grid ----
    future = m.make_future_dataframe(periods=int(periods), freq=mod_freq, include_history=True)

    if use_bounds:
        if cap_val != float("inf"):
            future["cap"] = cap_val
        future["floor"] = floor_val

    # merge history features (exclude y/cap/floor)
    drop_cols = ["y"]
    if use_bounds:
        drop_cols += [c for c in ["cap", "floor"] if c in train_df.columns]
    future = future.merge(train_df.drop(columns=drop_cols), on="ds", how="left")

    # forecast FUTURE regressors on MODEL grid
    if periods and periods > 0:
        if s is None:
            s = _align_next_step(last_hist, mod_freq)
        if e is None:
            e = pd.date_range(start=s, periods=periods, freq=mod_freq)[-1]

        reg_future = _forecast_regressors_future(
            timeseries_dir=ts_dir, regs=regressors,
            station_code=station_code, station_id=station_id,
            freq=mod_freq, agg=agg,
            train_start=train_start, train_end=train_end,
            fcst_start=s, fcst_end=e,
            strategy=regressor_future_strategy,
            ma_window=regressor_future_ma_window,
            linear_window=regressor_future_linear_window,
            prophet_cp_scale=regressor_future_prophet_cp_scale,
            prophet_disable_seasonality=regressor_future_prophet_disable_seasonality,
        )
        future = future.merge(reg_future, on="ds", how="left", suffixes=("", "_fcst"))
        for r in regressors:
            if r in future.columns and f"{r}_fcst" in future.columns:
                future[r] = future[r].combine_first(future[f"{r}_fcst"])
        future = future.drop(columns=[c for c in future.columns if c.endswith("_fcst")])

    # ensure bounds present
    if use_bounds:
        if (cap_val != float("inf")) and ("cap" not in future.columns):
            future["cap"] = cap_val
        if "floor" not in future.columns:
            future["floor"] = floor_val

    # optional smoothing (future)
    if smooth_regressors and smooth_window > 1:
        future = future.sort_values("ds")
        for r in regressors:
            future[r] = future[r].rolling(window=smooth_window, min_periods=1).mean()

    # NaN guard
    nan_cols = [r for r in regressors if r not in future.columns or future[r].isna().any()]
    if nan_cols:
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

    # ---- 5) predict on MODEL grid + clip to requested MODEL window ----
    fcst = m.predict(future)
    if s is not None or e is not None:
        s_eff = s if s is not None else fcst["ds"].min()
        e_eff = e if e is not None else fcst["ds"].max()
        fcst = fcst.loc[fcst["ds"].between(s_eff, e_eff, inclusive="both")]

    result_model = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    if use_bounds:
        lo = floor_val if floor_val is not None else -float("inf")
        hi = cap_val if cap_val is not None else float("inf")
        for c in ["yhat", "yhat_lower", "yhat_upper"]:
            result_model[c] = result_model[c].clip(lower=lo, upper=hi)

    # ---- 6) UPSAMPLE to OUTPUT grid (if different) ----
    if mod_freq != freq:
        out_index = pd.date_range(start=result_model["ds"].min(), end=result_model["ds"].max(), freq=freq)
        res = result_model.set_index("ds").reindex(out_index)
        for c in ["yhat", "yhat_lower", "yhat_upper"]:
            res[c] = res[c].interpolate(method="time").ffill().bfill()
        result_out = res.reset_index().rename(columns={"index": "ds"})
    else:
        result_out = result_model.copy()

    # ---- 7) save csv + data.json (metrics on MODEL grid; daily actuals for plots) ----
    if write_to_disk:
        # CSV (on OUTPUT grid)
        tag = "with_" + "+".join(regressors) if regressors else "univariate"
        (out_dir / f"{target}__{tag}.csv").write_text(result_out.to_csv(index=False), encoding="utf-8")

        # actuals aligned to OUTPUT window (for plots)
        x_min, x_max = pd.to_datetime(result_out["ds"].min()), pd.to_datetime(result_out["ds"].max())
        raw_target = _read_param_csv(ts_dir, target)
        raw_target = _filter_station(raw_target, station_code=station_code, station_id=station_id)
        raw_target = _apply_date_range(raw_target, start=x_min, end=x_max, col="ds")
        actuals_daily = _build_daily_actuals(raw_target, start=x_min, end=x_max, agg=agg, fill="ffill_bfill", fill_limit=None)

        # accuracy on MODEL grid (meaningful, non-noisy)
        raw_for_model = _apply_date_range(_read_param_csv(ts_dir, target), start=result_model["ds"].min(), end=result_model["ds"].max(), col="ds")
        raw_for_model = _filter_station(raw_for_model, station_code=station_code, station_id=station_id)
        actuals_model = _aggregate(raw_for_model, freq=mod_freq, how=agg)
        acc_stats = _compute_accuracy_within_tolerance(
            pred=result_model[["ds", "yhat"]],
            actuals_on_grid=actuals_model[["ds", "y"]],
            tolerance=accuracy_tolerance,
        )

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
                "freq": freq,                 # OUTPUT grid
                "model_freq": mod_freq,       # MODEL grid
                "agg": agg, "growth": model_growth,
                "train_start": str(pd.to_datetime(train_start)) if train_start else None,
                "train_end": str(pd.to_datetime(train_end)) if train_end else None,
                "fcst_start": str(pd.to_datetime(result_out["ds"].min())),
                "fcst_end": str(pd.to_datetime(result_out["ds"].max())),
                "bounds": {"min": target_min, "max": target_max} if use_bounds else None,
                "accuracy_tolerance": accuracy_tolerance,
                "regressor_prior_scale": regressor_prior_scale,
                "regressor_standardize": regressor_standardize,
                "regressor_mode": regressor_mode,
                "smooth_regressors": smooth_regressors,
                "smooth_window": smooth_window,
                "changepoint_prior_scale": changepoint_prior_scale,
                "seasonality_prior_scale": seasonality_prior_scale,
                "regressor_global_importance": regressor_global_importance,
                "regressor_importance": regressor_importance or {},
                "regressor_future_strategy": regressor_future_strategy,
                "regressor_future_ma_window": regressor_future_ma_window,
                "regressor_future_linear_window": regressor_future_linear_window,
                "regressor_future_prophet_cp_scale": regressor_future_prophet_cp_scale,
                "regressor_future_prophet_disable_seasonality": regressor_future_prophet_disable_seasonality,
            },
            # save predictions on OUTPUT grid (daily if freq='D')
            "predictions": [
                {"ds": pd.to_datetime(r.ds).isoformat(),
                 "yhat": float(r.yhat),
                 "yhat_lower": float(r.yhat_lower),
                 "yhat_upper": float(r.yhat_upper)}
                for r in result_out.itertuples(index=False)
            ],
            # daily actuals for plotting
            "actuals_daily": [
                {"ds": pd.to_datetime(r.ds).isoformat(), "y": (None if pd.isna(r.y) else float(r.y))}
                for r in actuals_daily.itertuples(index=False)
            ],
            # accuracy on MODEL grid
            "metrics": {
                f"within_{int(accuracy_tolerance*100)}pct": acc_stats
            },
        })
        data_path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")

    # return OUTPUT-grid forecast
    return result_out




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

def _compute_accuracy_within_tolerance(
    pred: pd.DataFrame,
    actuals_on_grid: pd.DataFrame,
    tolerance: float = 0.20
) -> dict:
    """
    Compute accuracy: share of points where |y - yhat| / |y| <= tolerance.
    - pred: DataFrame with ['ds','yhat']
    - actuals_on_grid: DataFrame with ['ds','y'] (aligned to same freq)
    - tolerance: error bound, e.g. 0.20 for 20%
    """
    if pred.empty or actuals_on_grid.empty:
        return {
            "metric": f"within_{int(tolerance*100)}pct",
            "accuracy": None,
            "n_total": int(len(pred)),
            "n_eval": 0,
            "n_within": 0,
        }

    df = pred[["ds", "yhat"]].merge(actuals_on_grid[["ds", "y"]], on="ds", how="inner")
    df = df.dropna(subset=["y"])
    df = df[df["y"].abs() > 0]

    n_total = int(len(pred))
    n_eval = int(len(df))
    if n_eval == 0:
        return {
            "metric": f"within_{int(tolerance*100)}pct",
            "accuracy": None,
            "n_total": n_total,
            "n_eval": 0,
            "n_within": 0,
        }

    ape = (df["yhat"] - df["y"]).abs() / df["y"].abs()
    within = (ape <= tolerance)
    n_within = int(within.sum())
    acc = float(n_within / n_eval)

    return {
        "metric": f"within_{int(tolerance*100)}pct",
        "accuracy": acc,
        "n_total": n_total,
        "n_eval": n_eval,
        "n_within": n_within,
    }
