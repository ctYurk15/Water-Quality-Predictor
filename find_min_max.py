import pandas as pd
import argparse
from pathlib import Path

def find_min_max(csv_path: str):
    """
    Reads a time series CSV file (with columns 'ds' and 'y') 
    and prints the min/max of the 'y' column.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Read the CSV (semicolon or comma separator)
    try:
        df = pd.read_csv(path, sep=',')
    except Exception:
        df = pd.read_csv(path)

    # Try to find target column
    if "y" not in df.columns:
        raise ValueError(f"Column 'y' not found in {path.name}. "
                         f"Columns: {list(df.columns)}")

    # Convert to numeric and drop NaNs
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df = df.dropna(subset=["y"])

    # Calculate min and max
    y_min, y_max = df["y"].min(), df["y"].max()

    print(f"File: {path.name}")
    print(f"Min: {y_min:.6f}")
    print(f"Max: {y_max:.6f}")
    return y_min, y_max


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find min/max values in time series CSV")
    parser.add_argument("csv_path", help="Path to the CSV file (e.g., timeseries/set1/Azot.csv)")
    args = parser.parse_args()

    find_min_max(args.csv_path)