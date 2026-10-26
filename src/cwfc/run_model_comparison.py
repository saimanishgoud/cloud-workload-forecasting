from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import (
    SimpleExpSmoothing,
    Holt,
)

from cwfc.baselines import (
    persistence_forecast,
    seasonal_naive_forecast,
)

from cwfc.metrics import mae, rmse, smape


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRAINING_FILE = PROJECT_ROOT / "reports" / "training_targets.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

TARGETS = [
    "active_vm_count",
    "aggregate_cpu_utilization",
]

INITIAL_TRAIN_SIZE = 60
VALIDATION_HORIZON = 6
STEP_SIZE = 6
SEASON_LENGTH = 12
MOVING_AVERAGE_WINDOW = 6


# --------------------------------------------------
# 2. Forecasting helpers
# --------------------------------------------------

def moving_average_forecast(train, template, target, window=6):
    """Forecast using the mean of the latest observations."""

    if window <= 0:
        raise ValueError("window must be positive")

    values = train[target].astype(float)

    if len(values) < window:
        raise ValueError("Not enough training observations")

    forecast_value = float(values.tail(window).mean())

    return pd.Series(
        forecast_value,
        index=template.index,
        dtype=float,
    )


def ses_forecast(train, template, target):
    """Fit Simple Exponential Smoothing on training data only."""

    values = train[target].astype(float)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        model = SimpleExpSmoothing(
            values,
            initialization_method="estimated",
        ).fit(optimized=True)

    predictions = model.forecast(len(template))

    return pd.Series(
        np.asarray(predictions, dtype=float),
        index=template.index,
    )


def holt_forecast(train, template, target):
    """Fit Holt's level-and-trend model on training data only."""

    values = train[target].astype(float)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        model = Holt(
            values,
            initialization_method="estimated",
        ).fit(optimized=True)

    predictions = model.forecast(len(template))

    return pd.Series(
        np.asarray(predictions, dtype=float),
        index=template.index,
    )


# --------------------------------------------------
# 3. Load and validate the training data
# --------------------------------------------------

def load_training_data():
    if not TRAINING_FILE.exists():
        raise FileNotFoundError(
            f"Training data not found: {TRAINING_FILE}"
        )

    frame = pd.read_csv(TRAINING_FILE)

    required_columns = ["timestamp", *TARGETS]

    missing_columns = [
        column
        for column in required_columns
        if column not in frame.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    frame = frame[required_columns].copy()

    for column in required_columns:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="raise",
        )

    if frame.isna().any().any():
        raise ValueError("Training data contains missing values")

    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("Training data contains non-finite values")

    if frame["timestamp"].duplicated().any():
        raise ValueError("Duplicate timestamps detected")

    if not frame["timestamp"].is_monotonic_increasing:
        raise ValueError("Timestamps must be sorted")

    if len(frame) <= INITIAL_TRAIN_SIZE:
        raise ValueError(
            "Not enough observations for the configured validation"
        )

    return frame.reset_index(drop=True)


# --------------------------------------------------
# 4. Rolling-origin validation
# --------------------------------------------------

def run_validation(frame):
    metric_rows = []
    prediction_rows = []

    model_names = [
        "persistence",
        "seasonal_naive_12",
        "moving_average_6",
        "ses",
        "holt",
    ]

    for target in TARGETS:

        for start in range(
            INITIAL_TRAIN_SIZE,
            len(frame),
            STEP_SIZE,
        ):

            end = min(
                start + VALIDATION_HORIZON,
                len(frame),
            )

            train = frame.iloc[:start].copy()
            validation = frame.iloc[start:end].copy()

            if validation.empty:
                continue

            if len(train) < SEASON_LENGTH:
                raise ValueError(
                    "Insufficient history for seasonal naive"
                )

            template = validation.copy()

            forecasts = {
                "persistence": persistence_forecast(
                    train, template, target
                ),

                "seasonal_naive_12": seasonal_naive_forecast(
                    train,
                    template,
                    target,
                    SEASON_LENGTH,
                ),

                "moving_average_6": moving_average_forecast(
                    train,
                    template,
                    target,
                    MOVING_AVERAGE_WINDOW,
                ),

                "ses": ses_forecast(
                    train, template, target
                ),

                "holt": holt_forecast(
                    train, template, target
                ),
            }

            actual = validation[target].to_numpy(dtype=float)

            for model_name in model_names:

                predicted = forecasts[model_name].to_numpy(
                    dtype=float
                )

                if not np.isfinite(predicted).all():
                    raise ValueError(
                        f"Non-finite forecast from {model_name}"
                    )

                # Count targets cannot be negative.
                # CPU utilization must remain between 0 and 100.
                if target == "active_vm_count":
                    predicted = np.maximum(predicted, 0)

                if target == "aggregate_cpu_utilization":
                    predicted = np.clip(predicted, 0, 100)

                for timestamp, actual_value, predicted_value in zip(
                    validation["timestamp"],
                    actual,
                    predicted,
                ):
                    prediction_rows.append({
                        "timestamp": timestamp,
                        "target": target,
                        "model": model_name,
                        "actual": actual_value,
                        "prediction": predicted_value,
                        "train_observations": len(train),
                    })

    predictions = pd.DataFrame(prediction_rows)

    # Metrics are calculated over identical validation timestamps.
    for (target, model_name), group in predictions.groupby(
        ["target", "model"]
    ):

        actual = group["actual"].to_numpy(dtype=float)
        predicted = group["prediction"].to_numpy(dtype=float)

        metric_rows.append({
            "target": target,
            "model": model_name,
            "MAE": mae(actual, predicted),
            "RMSE": rmse(actual, predicted),
            "sMAPE_percent": smape(actual, predicted),
            "validation_observations": len(group),
        })

    metrics = pd.DataFrame(metric_rows)

    return metrics, predictions


# --------------------------------------------------
# 5. Save results
# --------------------------------------------------

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    frame = load_training_data()

    print("Training observations:", len(frame))
    print("Training columns:", frame.columns.tolist())
    print(
        "Validation scheme:",
        f"initial training={INITIAL_TRAIN_SIZE},",
        f"horizon={VALIDATION_HORIZON},",
        f"step={STEP_SIZE}",
    )

    metrics, predictions = run_validation(frame)

    metrics_path = REPORTS_DIR / "model_comparison_metrics.csv"
    predictions_path = (
        REPORTS_DIR / "model_comparison_predictions.csv"
    )

    metrics.to_csv(metrics_path, index=False)
    predictions.to_csv(predictions_path, index=False)

    print("\nMODEL COMPARISON")
    print(
        metrics.sort_values(
            ["target", "MAE"]
        ).to_string(index=False)
    )

    print("\nSaved metrics:", metrics_path)
    print("Saved predictions:", predictions_path)


if __name__ == "__main__":
    main()