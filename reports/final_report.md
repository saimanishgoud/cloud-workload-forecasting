Cloud Workload Forecasting and Analysis

1. Executive Summary

This project builds a time-series workflow to forecast active VM count and aggregate CPU utilization from VM-level CPU telemetry. It prepares five-minute aggregate targets, compares simple forecasting baselines using chronological validation, and writes a 24-step forecast to predictions.csv.

The recorded short-horizon validation supports Persistence for active VM count and Moving Average (6) for CPU utilization. Moving Average (6) reduced CPU validation MAE by approximately 32.8% and RMSE by approximately 22.6% relative to Persistence in the primary 30-minute validation setup.

These results require caution: the final forecast spans two hours, while the primary model comparison evaluates six steps (30 minutes). The available history is short, and active VM count does not vary in the observed training series.

2. Data and Targets

The supplied Azure VM trace is expected under challenge_data/:

vm_cpu_readings.csv.gz

vm_metadata.csv.gz

DATA_CARD.md

SHA256SUMS

The target-building step creates five-minute observations with active_vm_count and aggregate_cpu_utilization. The observed training target contains 110 observations, covering approximately 9 hours and 10 minutes between the first and last timestamps.

The recorded data-quality output reports 1,340,000 CPU-reading rows, five columns, 10,000 unique VM IDs, no missing values in the inspected CPU-reading fields, and no duplicate complete rows. These checks describe the fields and tests performed; they do not prove that every possible data-quality issue is absent.

3. Workload Analysis

Active VM count

The active VM count is 10,000 throughout the observed training target. This explains why simple forecasts achieve effectively zero validation error. Because the series does not vary, the current data does not meaningfully test prediction of VM creation, shutdown, or churn.

Aggregate CPU utilization

CPU utilization varies over the observed period and is the more informative forecasting target. Previously inspected values were approximately 9.39% near the start and 9.16% near the end. Those endpoints alone do not establish a stable long-term trend or seasonality.

A fleet-wide average can conceal heavily utilized individual VMs. The aggregate forecast should be treated as a monitoring reference, not as a standalone reason to remove capacity or consolidate workloads.

4. Forecasting Method

The main model-comparison workflow evaluates:

Persistence — repeats the latest observed value.

Seasonal Naive (12) — repeats the value from 12 observations earlier (one hour at five-minute intervals).

Moving Average (6) — averages the latest six observations (a 30-minute trailing window).

Simple Exponential Smoothing (SES) — smooths historical observations with exponentially decreasing weights.

Holt's Exponential Smoothing — models a level and trend component.

Validation preserves time order and uses rolling-origin splits. The primary forecast horizon is six observations (30 minutes); MAE is the primary selection metric, with RMSE and sMAPE also reported.

Scope note: An Expanding Mean / Full-History Mean result was discussed in supplementary analysis, but the repository search did not identify a reproducible implementation of that two-hour comparison in the src/cwfc Python modules. Its supplementary metrics are therefore not presented as results reproducible from the main pipeline and are excluded from the model-selection conclusion here.

5. Validation Results

Active VM count

Model

MAE

RMSE

sMAPE

Persistence

0.0000

0.0000

0.000%

Seasonal Naive (12)

0.0000

0.0000

0.000%

Moving Average (6)

0.0000

0.0000

0.000%

Simple Exponential Smoothing

0.0000

0.0000

0.000%

Holt's Exponential Smoothing

Approximately 0.0000

Approximately 0.0000

Approximately 0.000%

The near-zero errors result from the constant observed target. Persistence is a simple choice based on this evidence.

Aggregate CPU utilization

Model

MAE

RMSE

sMAPE

Moving Average (6)

0.1049

0.1473

1.111%

Simple Exponential Smoothing

0.1101

0.1472

1.166%

Holt's Exponential Smoothing

0.1170

0.1582

1.238%

Persistence

0.1560

0.1903

1.649%

Seasonal Naive (12)

0.1859

0.2368

1.955%

MAE and RMSE are expressed in CPU-utilization percentage points. Moving Average (6) achieved the lowest MAE and sMAPE. SES had a marginally lower RMSE, so no model is best under every metric. Moving Average (6) was selected because MAE is the primary selection metric.

Improvement over Persistence

From the recorded primary validation metrics:

MAE decreased from 0.1559702 to 0.1048601: approximately 32.8% lower.

RMSE decreased from 0.1903433 to 0.1472531: approximately 22.6% lower.

These improvements apply to the primary short-horizon validation. They do not establish superior accuracy across the full two-hour horizon.

6. Final Forecast Output

predictions.csv must contain exactly 24 chronological forecast rows at five-minute intervals, with exactly these columns:

timestamp,active_vm_count,aggregate_cpu_utilization

The recorded output uses an active VM count of 10,000 and a Moving Average (6) CPU forecast of approximately 9.1909% across the horizon.

The forecast workflow must use training targets and the required forecast timestamps; holdout target values must not be used to fit models or select the forecasting method. Any post-hoc holdout diagnostic must be labelled as such and must not be used for model selection.

7. Operational Interpretation

The forecast suggests aggregate CPU utilization near 9.2% for the specified horizon. It does not prove that every VM has spare capacity. A low fleet-wide mean can coexist with high CPU utilization on a subset of VMs.

Treat the forecast as an additional monitoring baseline.

Compare future observations with forecasts and investigate sustained deviations.

Inspect per-VM and host-level utilization before capacity decisions.

Do not remove capacity based only on the aggregate mean.

Re-evaluate the model when workload characteristics or VM population change.

The primary validation results do not establish a fixed scaling threshold or safety margin.

8. Limitations and Future Work

Limitations

Only 110 aggregate training observations are available.

Primary validation covers 30 minutes, shorter than the final two-hour forecast.

Active VM count is constant in the observed training period, so VM churn forecasting is untested.

Aggregate CPU utilization can conceal individual VM saturation.

Point forecasts do not quantify predictive uncertainty.

The short history does not establish daily or weekly seasonality.

The supplementary two-hour Expanding Mean result is not currently reproducible from the identified main pipeline scripts.

Future work

Implement and test reproducible 24-step rolling-origin validation.

Add timestamp-level error plots and analyze errors by forecast lead time.

Estimate prediction intervals when more history is available.

Evaluate on traces with meaningful VM population changes.

Forecast high-percentile CPU utilization alongside the aggregate mean.

Automate checks for output schema, timestamp cadence, finite values, and valid ranges.

9. Conclusion

The project provides a straightforward forecasting pipeline for active VM count and aggregate CPU utilization. In the recorded 30-minute chronological validation, Persistence is adequate for the constant active-VM target, while Moving Average (6) provides the lowest CPU MAE among the five methods in the main comparison.

The CPU error reduction relative to Persistence is supported by the recorded short-horizon metrics. However, the final forecast horizon is longer than the primary validation horizon, so these results alone are insufficient for operational capacity decisions. Reproducible two-hour validation, per-VM monitoring, and uncertainty estimates would strengthen the solution.
