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


# --------------------------------------------------
# 1. Paths and configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORTS_DIR = PROJECT_ROOT / "reports"

TRAINING_FILE = REPORTS_DIR / "training_targets.csv"
METRICS_FILE = REPORTS_DIR / "model_comparison_metrics.csv"
HOLDOUT_FILE = REPORTS_DIR / "holdout_timestamps.csv"

OUTPUT_FILE = PROJECT_ROOT / "predictions.csv"

TARGETS = [
    "active_vm_count",
    "aggregate_cpu_utilization",
]

SEASON_LENGTH = 12
MOVING_AVERAGE_WINDOW = 6


# --------------------------------------------------
# 2. Moving Average
# --------------------------------------------------

def moving_average_forecast(train, template, target, window=6):
    if window <= 0:
        raise ValueError("window must be positive")

    values = train[target].astype(float)

    if len(values) < window:
        raise ValueError("Insufficient training history")

    forecast_value = float(values.tail(window).mean())

    return pd.Series(
        forecast_value,
        index=template.index,
        dtype=float,
    )


# --------------------------------------------------
# 3. Simple Exponential Smoothing
# --------------------------------------------------

def ses_forecast(train, template, target):
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


# --------------------------------------------------
# 4. Holt's Exponential Smoothing
# --------------------------------------------------

def holt_forecast(train, template, target):
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
# 5. Load training data
# --------------------------------------------------

def load_training_data():
    if not TRAINING_FILE.exists():
        raise FileNotFoundError(
            f"Missing training file: {TRAINING_FILE}"
        )

    frame = pd.read_csv(TRAINING_FILE)

    required = ["timestamp", *TARGETS]

    missing = set(required) - set(frame.columns)

    if missing:
        raise ValueError(
            f"Missing training columns: {sorted(missing)}"
        )

    frame = frame[required].copy()

    for column in required:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="raise",
        )

    if frame.isna().any().any():
        raise ValueError("Training data contains missing values")

    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("Training data contains non-finite values")

    if frame["timestamp"].duplicated().any():
        raise ValueError("Duplicate training timestamps")

    if not frame["timestamp"].is_monotonic_increasing:
        raise ValueError("Training timestamps are not sorted")

    return frame.reset_index(drop=True)


# --------------------------------------------------
# 6. Load holdout timestamps only
# --------------------------------------------------

def load_holdout_timestamps():
    if HOLDOUT_FILE.exists():
        holdout = pd.read_csv(HOLDOUT_FILE)

        if "timestamp" not in holdout.columns:
            raise ValueError(
                "holdout_timestamps.csv must contain timestamp"
            )

        timestamps = pd.to_numeric(
            holdout["timestamp"],
            errors="raise",
        )
    else:
        # Fallback: read only timestamp values from the
        # aggregate target file. Do not load target columns.
        aggregate_file = REPORTS_DIR / "aggregate_targets.csv"

        if not aggregate_file.exists():
            raise FileNotFoundError(
                "Neither holdout_timestamps.csv nor "
                "aggregate_targets.csv exists"
            )

        timestamps = pd.read_csv(
            aggregate_file,
            usecols=["timestamp"],
        )["timestamp"]

        timestamps = pd.to_numeric(
            timestamps,
            errors="raise",
        ).tail(24)

    timestamps = timestamps.reset_index(drop=True)

    if len(timestamps) != 24:
        raise ValueError(
            f"Expected 24 holdout timestamps; found {len(timestamps)}"
        )

    if timestamps.duplicated().any():
        raise ValueError("Duplicate holdout timestamps")

    if not timestamps.is_monotonic_increasing:
        raise ValueError("Holdout timestamps are not sorted")

    if not np.isfinite(timestamps.to_numpy(dtype=float)).all():
        raise ValueError("Holdout timestamps contain invalid values")

    return timestamps


# --------------------------------------------------
# 7. Select model using validation metrics
# --------------------------------------------------

def select_models():
    if not METRICS_FILE.exists():
        raise FileNotFoundError(
            "Missing model comparison metrics. "
            "Complete Day 3 model comparison first."
        )

    metrics = pd.read_csv(METRICS_FILE)

    required = {"target", "model", "MAE", "RMSE", "sMAPE_percent"}

    if not required.issubset(metrics.columns):
        raise ValueError(
            "Model comparison metrics are missing required columns"
        )

    selected = {}

    # Prefer simpler models when MAE is tied.
    preference = {
        "persistence": 0,
        "seasonal_naive_12": 1,
        "moving_average_6": 2,
        "ses": 3,
        "holt": 4,
    }

    for target in TARGETS:
        candidates = metrics.loc[
            metrics["target"] == target
        ].copy()

        candidates = candidates.replace(
            [np.inf, -np.inf],
            np.nan,
        ).dropna(subset=["MAE", "RMSE", "sMAPE_percent"])

        if candidates.empty:
            raise ValueError(
                f"No valid model metrics found for {target}"
            )

        candidates["_preference"] = (
            candidates["model"].map(preference).fillna(999)
        )

        candidates = candidates.sort_values(
            ["MAE", "_preference", "RMSE"]
        )

        selected[target] = candidates.iloc[0]["model"]

    return selected


# --------------------------------------------------
# 8. Forecast using the selected model
# --------------------------------------------------

def forecast_with_model(model_name, train, template, target):
    if model_name == "persistence":
        return persistence_forecast(
            train, template, target
        )

    if model_name == "seasonal_naive_12":
        return seasonal_naive_forecast(
            train,
            template,
            target,
            SEASON_LENGTH,
        )

    if model_name == "moving_average_6":
        return moving_average_forecast(
            train,
            template,
            target,
            MOVING_AVERAGE_WINDOW,
        )

    if model_name == "ses":
        return ses_forecast(
            train, template, target
        )

    if model_name == "holt":
        return holt_forecast(
            train, template, target
        )

    raise ValueError(
        f"Unsupported selected model: {model_name}"
    )


# --------------------------------------------------
# 9. Generate final predictions
# --------------------------------------------------

def main():
    train = load_training_data()
    holdout_timestamps = load_holdout_timestamps()

    selected_models = select_models()

    # The forecasting template contains timestamps only.
    template = pd.DataFrame({
        "timestamp": holdout_timestamps
    })

    output = template.copy()

    print("Training observations:", len(train))
    print("Forecast horizon:", len(template))

    for target in TARGETS:
        model_name = selected_models[target]

        predictions = forecast_with_model(
            model_name,
            train,
            template,
            target,
        )

        values = np.asarray(
            predictions,
            dtype=float,
        )

        if not np.isfinite(values).all():
            raise ValueError(
                f"{target} forecast contains invalid values"
            )

        if target == "active_vm_count":
            values = np.maximum(values, 0)

        elif target == "aggregate_cpu_utilization":
            values = np.clip(values, 0, 100)

        output[target] = values

        print(f"Selected model for {target}: {model_name}")

    # Active VM count is a count, so round to whole VMs.
    output["active_vm_count"] = (
        output["active_vm_count"]
        .round()
        .astype("int64")
    )

    output = output[
        [
            "timestamp",
            "active_vm_count",
            "aggregate_cpu_utilization",
        ]
    ]

    # Final contract checks.
    if len(output) != 24:
        raise ValueError("Output must contain exactly 24 rows")

    if output["timestamp"].duplicated().any():
        raise ValueError("Duplicate output timestamps")

    if not output["timestamp"].is_monotonic_increasing:
        raise ValueError("Output timestamps are not sorted")

    if (output["active_vm_count"] < 0).any():
        raise ValueError("Negative active VM count")

    cpu = output["aggregate_cpu_utilization"]

    if ((cpu < 0) | (cpu > 100)).any():
        raise ValueError("CPU prediction outside [0, 100]")

    if not np.isfinite(
        output.select_dtypes(include="number").to_numpy()
    ).all():
        raise ValueError("Output contains non-finite values")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(OUTPUT_FILE, index=False)

    print("\nFinal predictions saved to:", OUTPUT_FILE)
    print("\nFirst five predictions:")
    print(output.head().to_string(index=False))

    print("\nAll 24 predictions:")
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()