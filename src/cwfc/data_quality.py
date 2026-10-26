
from pathlib import Path

import pandas as pd

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "challenge_data"
REPORT_DIR = PROJECT_ROOT / "reports"

CPU_FILE = DATA_DIR / "vm_cpu_readings.csv.gz"
METADATA_FILE = DATA_DIR / "vm_metadata.csv.gz"


def inspect_dataset(df, dataset_name):
    """Generate basic data-quality checks for a DataFrame."""

    print(f"\n{'=' * 60}")
    print(f"DATASET: {dataset_name}")
    print(f"{'=' * 60}")

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Duplicate complete rows: {df.duplicated().sum():,}")

    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nData types:")
    print(df.dtypes.to_string())

    print("\nMissing values:")
    print(df.isna().sum().to_string())

    print("\nUnique VM IDs:")
    if "vm_id" in df.columns:
        print(f"{df['vm_id'].nunique(dropna=True):,}")

    records = []

    for column in df.columns:
        records.append({
            "dataset": dataset_name,
            "check": "column",
            "item": column,
            "value": str(df[column].dtype),
        })

        records.append({
            "dataset": dataset_name,
            "check": "missing_values",
            "item": column,
            "value": int(df[column].isna().sum()),
        })

    records.extend([
        {
            "dataset": dataset_name,
            "check": "total_rows",
            "item": "all",
            "value": len(df),
        },
        {
            "dataset": dataset_name,
            "check": "total_columns",
            "item": "all",
            "value": len(df.columns),
        },
        {
            "dataset": dataset_name,
            "check": "duplicate_complete_rows",
            "item": "all",
            "value": int(df.duplicated().sum()),
        },
    ])

    if "vm_id" in df.columns:
        records.append({
            "dataset": dataset_name,
            "check": "unique_vm_ids",
            "item": "vm_id",
            "value": int(df["vm_id"].nunique(dropna=True)),
        })

    return records


def inspect_cpu_values(cpu_df):
    """Inspect CPU value ranges and timestamp irregularities."""

    print(f"\n{'=' * 60}")
    print("CPU VALUE CHECKS")
    print(f"{'=' * 60}")

    cpu_columns = ["min_cpu", "avg_cpu", "max_cpu"]

    for column in cpu_columns:
        if column not in cpu_df.columns:
            print(f"\nWARNING: Missing expected column: {column}")
            continue

        values = pd.to_numeric(cpu_df[column], errors="coerce")

        print(f"\n{column}:")
        print(f"  Invalid/non-numeric values: {values.isna().sum():,}")
        print(f"  Minimum: {values.min()}")
        print(f"  Maximum: {values.max()}")
        print(f"  Values below 0: {(values < 0).sum():,}")
        print(f"  Values above 100: {(values > 100).sum():,}")

    if {"timestamp", "vm_id"}.issubset(cpu_df.columns):
        duplicate_keys = cpu_df.duplicated(
            subset=["timestamp", "vm_id"],
            keep=False,
        )

        print("\nRepeated timestamp + VM ID records:")
        print(f"  Rows involved: {duplicate_keys.sum():,}")
        print(
            "  Distinct repeated keys:",
            cpu_df.loc[
                duplicate_keys, ["timestamp", "vm_id"]
            ].drop_duplicates().shape[0],
        )

    if "timestamp" in cpu_df.columns:
        timestamps = pd.to_numeric(
            cpu_df["timestamp"],
            errors="coerce",
        )

        unique_timestamps = sorted(timestamps.dropna().unique())

        print("\nTimestamp checks:")
        print(f"  Invalid/missing timestamps: {timestamps.isna().sum():,}")
        print(f"  Unique timestamps: {len(unique_timestamps):,}")

        if unique_timestamps:
            print(f"  First timestamp: {unique_timestamps[0]}")
            print(f"  Last timestamp: {unique_timestamps[-1]}")

        if len(unique_timestamps) > 1:
            differences = pd.Series(unique_timestamps).diff().dropna()

            print(
                "  Most common timestamp intervals (seconds):"
            )
            print(differences.value_counts().head(10).to_string())

            timestamp_report = pd.DataFrame({
                "timestamp": unique_timestamps,
            })

            timestamp_report["interval_from_previous_seconds"] = (
                timestamp_report["timestamp"].diff()
            )

            timestamp_report.to_csv(
                REPORT_DIR / "cpu_timestamp_summary.csv",
                index=False,
            )

            print(
                "\nSaved timestamp summary to "
                "reports/cpu_timestamp_summary.csv"
            )


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    for file_path in [CPU_FILE, METADATA_FILE]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {file_path}"
            )

    print("Loading CPU readings...")
    cpu_df = pd.read_csv(CPU_FILE)

    print("Loading VM metadata...")
    metadata_df = pd.read_csv(METADATA_FILE)

    all_records = []

    all_records.extend(
        inspect_dataset(cpu_df, "vm_cpu_readings")
    )

    all_records.extend(
        inspect_dataset(metadata_df, "vm_metadata")
    )

    inspect_cpu_values(cpu_df)

    report = pd.DataFrame(all_records)

    output_file = REPORT_DIR / "data_quality_report.csv"
    report.to_csv(output_file, index=False)

    print(f"\n{'=' * 60}")
    print("DATA QUALITY ANALYSIS COMPLETED")
    print(f"{'=' * 60}")
    print(f"Report saved to: {output_file}")
    print(f"Timestamp summary: {REPORT_DIR / 'cpu_timestamp_summary.csv'}")


if __name__ == "__main__":
    main()

