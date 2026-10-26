
from pathlib import Path

import numpy as np
import pandas as pd

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "challenge_data"
REPORT_DIR = PROJECT_ROOT / "reports"

CPU_FILE = DATA_DIR / "vm_cpu_readings.csv.gz"

TARGET_FILE = REPORT_DIR / "aggregate_targets.csv"
TRAIN_FILE = REPORT_DIR / "training_targets.csv"
HOLDOUT_FILE = REPORT_DIR / "holdout_timestamps.csv"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not CPU_FILE.exists():
        raise FileNotFoundError(
            f"CPU dataset not found: {CPU_FILE}"
        )

    print("Loading CPU readings...")
    cpu = pd.read_csv(CPU_FILE)

    required_columns = {
        "timestamp",
        "vm_id",
        "avg_cpu",
    }

    missing_columns = required_columns - set(cpu.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    print(f"Original rows: {len(cpu):,}")

    # Convert target columns to numeric values.
    cpu["timestamp"] = pd.to_numeric(
        cpu["timestamp"],
        errors="coerce",
    )

    cpu["avg_cpu"] = pd.to_numeric(
        cpu["avg_cpu"],
        errors="coerce",
    )

    # Report invalid data before excluding records.
    invalid_timestamp = cpu["timestamp"].isna()
    missing_vm_id = cpu["vm_id"].isna()
    missing_avg_cpu = cpu["avg_cpu"].isna()

    cpu_out_of_range = (
        cpu["avg_cpu"].notna()
        & ~cpu["avg_cpu"].between(0, 100)
    )

    print("\nData-quality checks:")
    print(
        "Missing/invalid timestamps:",
        f"{invalid_timestamp.sum():,}",
    )
    print(
        "Missing VM IDs:",
        f"{missing_vm_id.sum():,}",
    )
    print(
        "Missing/invalid average CPU readings:",
        f"{missing_avg_cpu.sum():,}",
    )
    print(
        "CPU readings outside 0-100:",
        f"{cpu_out_of_range.sum():,}",
    )

    # Exclude records without a valid timestamp or VM ID.
    # These records cannot identify a VM at a particular time.
    identified = cpu.loc[
        ~invalid_timestamp & ~missing_vm_id
    ].copy()

    # A valid CPU reading requires a numeric value in [0, 100].
    valid_cpu = identified.loc[
        identified["avg_cpu"].between(0, 100)
    ].copy()

    # Identify repeated timestamp-VM combinations.
    duplicate_key_mask = valid_cpu.duplicated(
        subset=["timestamp", "vm_id"],
        keep=False,
    )

    duplicate_keys = valid_cpu.loc[
        duplicate_key_mask,
        ["timestamp", "vm_id"],
    ].drop_duplicates()

    print(
        "\nDistinct timestamp-VM combinations with repeated "
        f"valid CPU records: {len(duplicate_keys):,}"
    )

    # Do not silently discard repeated records.
    # If the same VM has multiple valid readings at one timestamp,
    # average those readings first so each VM contributes once.
    vm_level = (
        valid_cpu.groupby(
            ["timestamp", "vm_id"],
            as_index=False,
        )
        .agg(avg_cpu=("avg_cpu", "mean"))
    )

    # Build the required aggregate targets.
    targets = (
        vm_level.groupby("timestamp")
        .agg(
            active_vm_count=("vm_id", "nunique"),
            aggregate_cpu_utilization=("avg_cpu", "mean"),
        )
        .reset_index()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    if targets.empty:
        raise ValueError(
            "No valid observations remain after data-quality checks."
        )

    # Validate the target series.
    if targets["timestamp"].duplicated().any():
        raise ValueError("Duplicate timestamps remain in target series.")

    if (targets["active_vm_count"] < 0).any():
        raise ValueError("Negative active VM count detected.")

    if not targets["aggregate_cpu_utilization"].between(
        0, 100
    ).all():
        raise ValueError(
            "Aggregate CPU utilization is outside the 0-100 range."
        )

    if not np.isfinite(
        targets[
            ["active_vm_count", "aggregate_cpu_utilization"]
        ].to_numpy(dtype=float)
    ).all():
        raise ValueError("Non-finite target values detected.")

    # Save the complete target series.
    targets.to_csv(TARGET_FILE, index=False)

    print("\nTarget construction completed.")
    print(f"Valid target timestamps: {len(targets):,}")
    print(f"Active VM count range: "
          f"{targets['active_vm_count'].min()} - "
          f"{targets['active_vm_count'].max()}")
    print(f"Aggregate CPU minimum: "
          f"{targets['aggregate_cpu_utilization'].min():.4f}")
    print(f"Aggregate CPU maximum: "
          f"{targets['aggregate_cpu_utilization'].max():.4f}")

    print("\nFirst five target rows:")
    print(targets.head().to_string(index=False))

    print("\nLast five target rows:")
    print(targets.tail().to_string(index=False))

    # Split chronologically using the assignment's 24-point holdout.
    # The first n-24 observations are the training window.
    # Do not use the holdout target values for model development.
    if len(targets) <= 24:
        raise ValueError(
            "The dataset must contain more than 24 target timestamps "
            "to create a non-empty training window."
        )

    split_index = len(targets) - 24

    training = targets.iloc[:split_index].copy()

    holdout_timestamps = targets.iloc[
        split_index:
    ][["timestamp"]].copy()

    training.to_csv(TRAIN_FILE, index=False)
    holdout_timestamps.to_csv(HOLDOUT_FILE, index=False)

    print(f"\nTraining observations: {len(training)}")
    print(f"Holdout timestamps: {len(holdout_timestamps)}")
    print(f"Training file: {TRAIN_FILE}")
    print(f"Holdout timestamp file: {HOLDOUT_FILE}")
    print(f"Complete targets file: {TARGET_FILE}")


if __name__ == "__main__":
    main()

