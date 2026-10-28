# Cloud Workload Forecasting and Analysis

A Python time-series forecasting project that analyzes cloud virtual machine (VM) activity and CPU utilization, evaluates forecasting models, and generates predictions for a two-hour holdout period.

## Project Objectives

* Analyze VM-level CPU utilization and workload activity.
* Aggregate raw observations into timestamp-level forecasting targets.
* Evaluate forecasting approaches using chronological validation.
* Compare candidate models against baseline methods.
* Forecast active VM counts and aggregate CPU utilization.
* Generate a reproducible `predictions.csv` file.
* Provide workload insights to support capacity-planning decisions.

## Dataset

This project uses the curated Microsoft Azure Public Dataset V2 VM trace provided for the challenge.

Place the supplied release files in:

```text
challenge_data/
```

The forecasting pipeline derives two target metrics:

* **`active_vm_count`**: Number of distinct VMs with valid CPU readings at a given timestamp.
* **`aggregate_cpu_utilization`**: Mean CPU utilization across valid VM readings at a given timestamp, expressed as a percentage from 0 to 100.

The pipeline should derive its targets and timestamps from the supplied data rather than relying on fixed values specific to the public dataset.

## Forecasting Methodology

The project evaluates the following forecasting approaches:

* Persistence forecasting
* Seasonal-naive forecasting
* Moving-average forecasting
* Simple exponential smoothing
* Holt's trend method

Models are compared using chronological validation and metrics such as:

* **Mean Absolute Error (MAE)**
* **Root Mean Squared Error (RMSE)**
* **Symmetric Mean Absolute Percentage Error (sMAPE)**

The selected forecasting approach is evaluated against baseline methods to assess whether it improves predictive performance.

### Preventing Data Leakage

The final 24 target observations constitute the holdout period.

Holdout target values must not be used for model fitting, feature selection, hyperparameter tuning, or model selection. Model selection must be based exclusively on training and validation data available before the holdout.

## Installation

Python 3.11 or later is required.

Install the project and its development dependencies from the repository root:

```bash
python -m pip install -e ".[dev]"
```

## Reproducing Predictions

Run the forecasting pipeline from the repository root after installing dependencies and placing the supplied release data in `challenge_data/`.

The documented command must regenerate `predictions.csv` from the supplied release data without requiring manual edits to the output file.

> **Reproducibility requirement:** The final command must also work from a clean checkout. It must generate any required intermediate data and model-selection results automatically rather than depending on previously generated files in `reports/`.

The exact command should be documented here after the forecasting pipeline has been verified end to end.

## Required Output

The forecasting pipeline must generate:

```text
predictions.csv
```

The CSV must contain exactly these columns, in this order:

```csv
timestamp,active_vm_count,aggregate_cpu_utilization
```

### Output Requirements

* Exactly 24 data rows.
* One prediction for each final holdout timestamp.
* Timestamps matching the holdout timestamps exactly.
* Timestamps in chronological order.
* No duplicate timestamps.
* No missing predictions.
* All values finite and numeric.
* `active_vm_count >= 0`.
* `aggregate_cpu_utilization` within `[0, 100]`.
* No additional index column.

The output must be generated automatically by the forecasting pipeline.

## Testing

Run the automated test suite from the repository root:

```bash
python -m pytest -q
```

Tests should verify the forecasting utilities, validation logic, and relevant output requirements.

## Project Structure

```text
.
├── challenge_data/       # Supplied challenge data
├── reports/              # Analysis outputs, validation metrics, and final report
├── src/
│   └── cwfc/              # Data processing, forecasting, and evaluation modules
├── tests/                 # Automated tests
├── predictions.csv        # Required prediction output
├── pyproject.toml         # Project configuration and dependencies
└── README.md              # Project documentation
```

## Capacity Planning and Limitations

Forecasts of VM activity and aggregate CPU utilization can support workload monitoring and capacity-planning decisions.

However, the available workload history is short and may not capture longer-term trends, recurring patterns, or sudden workload changes. Forecasts should therefore be interpreted alongside uncertainty, infrastructure limits, service-level objectives, and operational headroom requirements.

CPU utilization alone is insufficient to determine the exact number of physical servers or the total infrastructure capacity required.

## Repository Hygiene

The repository should not contain:

* Credentials or secrets.
* Virtual environments.
* Generated caches.
* Notebook checkpoints.
* Large derived datasets.
* Copies of the upstream Azure release data.

The project should remain reproducible using the supplied challenge data and the documented execution command.
