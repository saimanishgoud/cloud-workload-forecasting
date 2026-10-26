from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports"
CHART_DIR = REPORT_DIR / "charts"

TARGET_FILE = REPORT_DIR / "aggregate_targets.csv"
TRAIN_FILE = REPORT_DIR / "training_targets.csv"


def load_targets():
    if not TARGET_FILE.exists():
        raise FileNotFoundError(
            f"Target file not found: {TARGET_FILE}\n"
            "Run build_targets.py first."
        )

    targets = pd.read_csv(TARGET_FILE)

    required_columns = [
        "timestamp",
        "active_vm_count",
        "aggregate_cpu_utilization",
    ]

    missing_columns = set(required_columns) - set(targets.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    targets = targets[required_columns].copy()

    for column in required_columns:
        targets[column] = pd.to_numeric(
            targets[column], errors="coerce"
        )

    if targets.isna().any().any():
        raise ValueError("Target data contains missing or invalid values.")

    if targets["timestamp"].duplicated().any():
        raise ValueError("Duplicate timestamps found.")

    targets = targets.sort_values("timestamp").reset_index(drop=True)

    return targets


def analyze_workload(targets):
    print("\n" + "=" * 60)
    print("1. DATASET OVERVIEW")
    print("=" * 60)

    print(f"Number of timestamps: {len(targets)}")
    print(f"First timestamp: {targets['timestamp'].iloc[0]}")
    print(f"Last timestamp:  {targets['timestamp'].iloc[-1]}")

    intervals = targets["timestamp"].diff().dropna()

    print("\nTimestamp intervals in seconds:")
    print(intervals.value_counts().sort_index().to_string())

    print("\n" + "=" * 60)
    print("2. ACTIVE VM COUNT")
    print("=" * 60)

    vm = targets["active_vm_count"]

    print(f"Mean:   {vm.mean():.2f}")
    print(f"Median: {vm.median():.2f}")
    print(f"Minimum: {vm.min():.0f}")
    print(f"Maximum: {vm.max():.0f}")
    print(f"Standard deviation: {vm.std():.2f}")

    print("\nTimestamps with the highest active VM counts:")
    print(
        targets.nlargest(5, "active_vm_count")
        .to_string(index=False)
    )

    print("\n" + "=" * 60)
    print("3. AGGREGATE CPU UTILIZATION")
    print("=" * 60)

    cpu = targets["aggregate_cpu_utilization"]

    print(f"Mean:   {cpu.mean():.2f}%")
    print(f"Median: {cpu.median():.2f}%")
    print(f"Minimum: {cpu.min():.2f}%")
    print(f"Maximum: {cpu.max():.2f}%")
    print(f"Standard deviation: {cpu.std():.2f}%")

    print("\nTimestamps with the highest aggregate CPU utilization:")
    print(
        targets.nlargest(5, "aggregate_cpu_utilization")
        .to_string(index=False)
    )

    print("\n" + "=" * 60)
    print("4. CHANGE BETWEEN OBSERVATIONS")
    print("=" * 60)

    changes = targets.copy()

    changes["vm_count_change"] = (
        changes["active_vm_count"].diff()
    )

    changes["cpu_change"] = (
        changes["aggregate_cpu_utilization"].diff()
    )

    print("Largest increase in active VM count:")
    print(changes.nlargest(3, "vm_count_change")[
        ["timestamp", "vm_count_change"]
    ].to_string(index=False))

    print("\nLargest decrease in active VM count:")
    print(changes.nsmallest(3, "vm_count_change")[
        ["timestamp", "vm_count_change"]
    ].to_string(index=False))

    print("\nLargest increase in aggregate CPU utilization:")
    print(changes.nlargest(3, "cpu_change")[
        ["timestamp", "cpu_change"]
    ].to_string(index=False))

    print("\nLargest decrease in aggregate CPU utilization:")
    print(changes.nsmallest(3, "cpu_change")[
        ["timestamp", "cpu_change"]
    ].to_string(index=False))


def create_eda_charts(targets):
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    # Chart 1: Active VM count over time
    plt.figure(figsize=(12, 5))
    plt.plot(
        targets["timestamp"],
        targets["active_vm_count"],
        marker="o",
        markersize=3,
    )
    plt.title("Active VM Count Over Time")
    plt.xlabel("Timestamp (seconds relative to source trace)")
    plt.ylabel("Active VM Count")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(CHART_DIR / "eda_active_vm_count.png", dpi=150)
    plt.close()

    # Chart 2: Aggregate CPU utilization over time
    plt.figure(figsize=(12, 5))
    plt.plot(
        targets["timestamp"],
        targets["aggregate_cpu_utilization"],
        marker="o",
        markersize=3,
    )
    plt.title("Aggregate CPU Utilization Over Time")
    plt.xlabel("Timestamp (seconds relative to source trace)")
    plt.ylabel("Mean CPU Utilization (%)")
    plt.ylim(0, 100)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "eda_aggregate_cpu_utilization.png",
        dpi=150,
    )
    plt.close()

    # Chart 3: Distribution of aggregate CPU utilization
    plt.figure(figsize=(9, 5))
    plt.hist(
        targets["aggregate_cpu_utilization"],
        bins=15,
        edgecolor="black",
    )
    plt.title("Distribution of Aggregate CPU Utilization")
    plt.xlabel("Mean CPU Utilization (%)")
    plt.ylabel("Number of Timestamps")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "eda_cpu_distribution.png",
        dpi=150,
    )
    plt.close()

    # Chart 4: Changes in active VM count
    plt.figure(figsize=(12, 5))
    plt.plot(
        targets["timestamp"],
        targets["active_vm_count"].diff(),
        marker="o",
        markersize=3,
    )
    plt.axhline(0, linewidth=1)
    plt.title("Change in Active VM Count Between Observations")
    plt.xlabel("Timestamp (seconds relative to source trace)")
    plt.ylabel("Change in VM Count")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(
        CHART_DIR / "eda_vm_count_changes.png",
        dpi=150,
    )
    plt.close()

    print(f"\nCharts saved to: {CHART_DIR}")


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    targets = load_targets()

    # Use the training window for exploratory analysis.
    # Do not use holdout target values for model selection.
    if TRAIN_FILE.exists():
        training = pd.read_csv(TRAIN_FILE)

        required = [
            "timestamp",
            "active_vm_count",
            "aggregate_cpu_utilization",
        ]

        if set(required).issubset(training.columns):
            targets = training[required].copy()

            for column in required:
                targets[column] = pd.to_numeric(
                    targets[column], errors="coerce"
                )

            if targets.isna().any().any():
                raise ValueError(
                    "Training targets contain missing or invalid values."
                )

            targets = targets.sort_values(
                "timestamp"
            ).reset_index(drop=True)

    analyze_workload(targets)
    create_eda_charts(targets)

    print("\nEDA completed successfully.")


if __name__ == "__main__":
    main()