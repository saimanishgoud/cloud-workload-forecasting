from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cwfc.baselines import (
    persistence_forecast,
    seasonal_naive_forecast,
)
from cwfc.metrics import mae, rmse, smape


REPORT_DIR = PROJECT_ROOT / "reports"
TRAIN_FILE = REPORT_DIR / "training_targets.csv"

TARGETS = [
    "active_vm_count",
    "aggregate_cpu_utilization",
]

INITIAL_TRAIN_SIZE = 60
HORIZON = 6
STEP = 6
SEASON_LENGTH = 12


def load_data():
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(
            f"Training file not found: {TRAIN_FILE}"
        )

    data = pd.read_csv(TRAIN_FILE)

    required = ["timestamp", *TARGETS]
    missing = set(required) - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    for column in required:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        )

    if data[required].isna().any().any():
        raise ValueError(
            "Training data contains missing or invalid values."
        )

    if data["timestamp"].duplicated().any():
        raise ValueError("Duplicate timestamps found.")

    data = data.sort_values("timestamp").reset_index(drop=True)

    if len(data) <= INITIAL_TRAIN_SIZE:
        raise ValueError(
            "Not enough observations for the chosen validation setup."
        )

    intervals = data["timestamp"].diff().dropna()

    if not intervals.eq(300).all():
        raise ValueError(
            "Expected observations every 300 seconds. "
            "Inspect timestamp irregularities before proceeding."
        )

    return data


def run_validation(data, target):
    records = []

    for start in range(
        INITIAL_TRAIN_SIZE,
        len(data),
        STEP,
    ):
        end = min(start + HORIZON, len(data))

        history = data[target].iloc[:start]
        actual = data[target].iloc[start:end]

        # A template is used to preserve the existing baseline API.
        template = data.iloc[start:end]

        forecasts = {
            "persistence": persistence_forecast(
                data.iloc[:start],
                template,
                target,
            )
        }

        # Seasonal naive requires at least 12 history observations.
        if len(history) >= SEASON_LENGTH:
            forecasts["seasonal_naive_12"] = (
                seasonal_naive_forecast(
                    data.iloc[:start],
                    template,
                    target,
                    season_length=SEASON_LENGTH,
                )
            )

        for model_name, predicted in forecasts.items():
            for position, prediction in enumerate(predicted):
                records.append(
                    {
                        "target": target,
                        "model": model_name,
                        "timestamp": data.iloc[
                            start + position
                        ]["timestamp"],
                        "actual": float(actual.iloc[position]),
                        "predicted": float(prediction),
                    }
                )

    predictions = pd.DataFrame(records)

    # Each model is evaluated over the same validation timestamps.
    results = []

    for model_name, group in predictions.groupby("model"):
        results.append(
            {
                "target": target,
                "model": model_name,
                "MAE": mae(
                    group["actual"],
                    group["predicted"],
                ),
                "RMSE": rmse(
                    group["actual"],
                    group["predicted"],
                ),
                "sMAPE_percent": smape(
                    group["actual"],
                    group["predicted"],
                ),
                "validation_observations": len(group),
            }
        )

    return predictions, pd.DataFrame(results)


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    data = load_data()

    print(f"Training observations: {len(data)}")
    print(f"Initial training size: {INITIAL_TRAIN_SIZE}")
    print(f"Forecast horizon: {HORIZON} observations")
    print(f"Step size: {STEP} observations")
    print(f"Season length: {SEASON_LENGTH} observations")

    all_predictions = []
    all_metrics = []

    for target in TARGETS:
        print(f"\nEvaluating: {target}")

        predictions, metrics = run_validation(data, target)

        all_predictions.append(predictions)
        all_metrics.append(metrics)

        print(
            metrics.sort_values("MAE").to_string(index=False)
        )

    prediction_frame = pd.concat(
        all_predictions,
        ignore_index=True,
    )

    metric_frame = pd.concat(
        all_metrics,
        ignore_index=True,
    )

    prediction_frame.to_csv(
        REPORT_DIR / "baseline_validation_predictions.csv",
        index=False,
    )

    metric_frame.to_csv(
        REPORT_DIR / "baseline_validation_metrics.csv",
        index=False,
    )

    print("\nBaseline validation completed.")
    print(
        "Metrics: reports/baseline_validation_metrics.csv"
    )
    print(
        "Predictions: reports/baseline_validation_predictions.csv"
    )


if __name__ == "__main__":
    main()