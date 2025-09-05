"""
timeseries_builder
------------------
Utilities to convert semicolon-delimited environmental monitoring CSVs
into per-parameter time series suitable for Prophet.

Typical usage:

    from timeseries_builder import build_timeseries

    result = build_timeseries(
        datasets=["/path/one.csv", "/path/two.csv"],
        set_name="water_quality",
        out_root="timeseries"
    )
    print(result["out_dir"], result["counts"]["Azot"])

All functions are pure(ish) and can be reused in your own pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import numpy as np

# Canonical mapping for meta columns
META_COLUMNS_CANON = {
    "Post_ID": "post_id",
    "Post_Name": "post_name",
    "Post_Code": "post_code",
    "Riverbas_Name": "riverbas_name",
    "WaterLab_Name": "waterlab_name",
    "Latitude": "lat",
    "Longitude": "lon",
    "Controle_Date": "ds",  # Prophet-compatible timestamp column
}

NA_VALUES = ["NULL", "null", "", "NaN", "nan", "None", "none"]


# ----------------------------- Core IO ---------------------------------

def read_csv_semicolon(path: Path | str) -> pd.DataFrame:
    """Read a single semicolon-delimited CSV, keeping raw strings for later coercion."""
    df = pd.read_csv(
        path,
        sep=";",
        dtype=str,
        na_values=NA_VALUES,
        keep_default_na=True,
        engine="python",
    )
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
    return df


def load_all(datasets: Iterable[Path | str]) -> pd.DataFrame:
    """Load and concatenate multiple CSVs (row-wise)."""
    frames: List[pd.DataFrame] = []
    for p in datasets:
        p = Path(p)
        try:
            df = read_csv_semicolon(p)
            df = canonicalize_columns(df)
            frames.append(df)
        except Exception as e:
            # Soft-fail for a single file; caller can decide to raise if needed
            print(f"[WARN] Failed to read {p}: {e}")
    if not frames:
        raise ValueError("No datasets could be read.")
    return pd.concat(frames, ignore_index=True, sort=False)


# --------------------------- Transformations ---------------------------

def canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known meta columns to canonical snake_case."""
    rename_map = {src: dst for src, dst in META_COLUMNS_CANON.items() if src in df.columns}
    return df.rename(columns=rename_map)


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse 'ds' column to datetime if present."""
    if "ds" in df.columns:
        df = df.copy()
        df["ds"] = pd.to_datetime(df["ds"], errors="coerce", utc=False)
    return df


def numericize(series: pd.Series) -> pd.Series:
    """Coerce strings like '1,23' or ' 2.0 ' to numeric; invalid -> NaN."""
    s = series.astype(str).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def melt_parameters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wide table into long format with columns: ds, param, y, plus meta.
    Parameters are all non-meta columns.
    """
    known_meta = set(META_COLUMNS_CANON.values()) | set(META_COLUMNS_CANON.keys())
    id_vars = [c for c in df.columns if c in known_meta]
    value_vars = [c for c in df.columns if c not in id_vars]
    if "ds" not in id_vars and "Controle_Date" in df.columns:
        id_vars.append("Controle_Date")
    long = df.melt(id_vars=id_vars, var_name="param", value_name="y")
    long = canonicalize_columns(long)
    if "ds" not in long.columns and "Controle_Date" in long.columns:
        long = long.rename(columns={"Controle_Date": "ds"})
    return long


def clean_long_df(long: pd.DataFrame) -> pd.DataFrame:
    """Clean long-format frame: parse dates, numericize values, sort, and tidy IDs."""
    long = long.copy()  # avoid SettingWithCopyWarning

    long = parse_dates(long)
    long["y"] = numericize(long["y"])
    long = long.dropna(subset=["ds", "y"])

    if "lat" in long.columns:
        long["lat"] = numericize(long["lat"])
    if "lon" in long.columns:
        long["lon"] = numericize(long["lon"])

    if "post_id" in long.columns:
        long["post_id"] = long["post_id"].astype(str).str.strip()
    if "post_code" in long.columns:
        long["post_code"] = long["post_code"].astype(str).str.strip()

    long = long.sort_values(["param", "post_id", "ds"], kind="mergesort")
    return long


# ------------------------------ Output ---------------------------------

def safe_filename(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(name))
    while "__" in safe:
        safe = safe.replace("__", "_")
    safe = safe.strip("_")
    return safe or "param"


def write_per_param(long: pd.DataFrame, out_dir: Path) -> Dict[str, int]:
    """
    Write one CSV per parameter: timeseries/[set_name]/[PARAM].csv
    Returns a dict {param_name: row_count}.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: Dict[str, int] = {}
    keep_cols = ["ds", "y", "param", "post_id", "post_code", "post_name", "lat", "lon", "riverbas_name", "waterlab_name"]
    keep_cols = [c for c in keep_cols if c in long.columns]
    for param, chunk in long.groupby("param", sort=True):
        fn = out_dir / f"{safe_filename(param)}.csv"
        subset = chunk[keep_cols].copy().sort_values(["ds", "post_id"], kind="mergesort")
        subset.to_csv(fn, index=False)
        counts[str(param)] = int(len(subset))
    return counts


def build_catalog(out_dir: Path, counts: Dict[str, int]) -> dict:
    """Create a small JSON-serializable catalog structure (do not write)."""
    return {
        "timeseries_set": out_dir.name,
        "total_params": len(counts),
        "params": [{"name": k, "rows": int(v), "file": f"{safe_filename(k)}.csv"} for k, v in sorted(counts.items())],
    }


# ---------------------------- Public API --------------------------------

def to_long_dataframe(datasets: Iterable[Path | str]) -> pd.DataFrame:
    """
    Convenience: load all CSVs and return a cleaned long-format DataFrame
    with columns at least ['ds','param','y', ...].
    """
    wide = load_all(datasets)
    long = melt_parameters(wide)
    long = clean_long_df(long)
    return long


def build_timeseries(
    datasets: Iterable[Path | str],
    set_name: str,
    out_root: Path | str = "timeseries",
) -> dict:
    """
    Full pipeline: read, transform, and write per-parameter CSVs.
    Returns a dict with:
      - out_dir: Path to output folder
      - counts: dict of rows per parameter
      - catalog: the JSON-serializable catalog
    """
    out_dir = Path(out_root) / set_name.strip()
    long = to_long_dataframe(datasets)
    counts = write_per_param(long, out_dir)
    catalog = build_catalog(out_dir, counts)
    return {"out_dir": str(out_dir), "counts": counts, "catalog": catalog}