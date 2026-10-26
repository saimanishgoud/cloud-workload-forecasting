# Day 4: Final Forecasting Pipeline

## 1. Objective

The objective is to generate 24 future predictions for active VM count and aggregate CPU utilization using the 110 observations in the historical training window.

Each observation represents five minutes, so the forecast covers two hours. The predictions are written to `predictions.csv` in chronological order.

## 2. Model Selection

Models were compared using chronological rolling-origin validation. MAE was the primary selection metric, with RMSE and sMAPE used as supporting metrics.

**Selected model for active VM count:** Persistence.

**Selected model for aggregate CPU utilization:** Moving Average (6).

Persistence was selected for active VM count because the target remained constant at 10,000 throughout the observed training window, and persistence achieved zero validation error.

Moving Average (6) was selected for CPU utilization because it achieved the lowest MAE and sMAPE among the evaluated models.

The CPU validation metrics were:

| Metric | Moving Average (6) |
| ------ | -----------------: |
| MAE    |             0.1049 |
| RMSE   |             0.1473 |
| sMAPE  |             1.111% |

These results were obtained using 50 validation observations and a six-step validation horizon. They should be interpreted as short-horizon validation results, not as a direct measurement of two-hour forecast accuracy.

## 3. Final Forecasting Pipeline

The forecasting pipeline uses the available historical training targets and the required forecast timestamps to generate predictions.

The pipeline is designed to:

1. Load and validate the historical training data.
2. Read the required holdout timestamps without using holdout target values for fitting or model selection.
3. Select forecasting models using the recorded validation metrics.
4. Generate predictions for the 24 required timestamps.
5. Apply output constraints and write the predictions to `predictions.csv`.

The output file contains one forecast for each required timestamp.

## 4. Output Validation

The previously executed output checks returned the following results:

| Validation check                               | Result |
| ---------------------------------------------- | ------ |
| Required columns                               | Passed |
| Prediction rows                                | 24     |
| Holdout timestamp count                        | 24     |
| Prediction timestamps match holdout timestamps | Yes    |
| Duplicate timestamps                           | 0      |
| Missing values                                 | 0      |
| Active VM count nonnegative                    | Passed |
| CPU utilization within [0, 100]                | Passed |

The checks confirm that the previously examined prediction file satisfies these output constraints. They do not establish forecast accuracy.

## 5. Forecast Behavior

The generated CPU forecasts are constant at approximately **9.1909%** across the 24 forecast timestamps. The predicted active VM count remains at 10,000.

The constant active VM forecast is consistent with the unchanged count in the observed training window.

The CPU forecast behavior should be interpreted in the context of the selected forecasting implementation and the available historical observations. A constant forecast does not imply that actual future CPU utilization will remain constant.

## 6. Limitations

The historical training window contains 110 observations at five-minute intervals. This is a limited amount of history for identifying longer-term trends or recurring workload patterns.

The current validation horizon is six observations, equivalent to 30 minutes, while the final forecast horizon is 24 observations, equivalent to two hours. Consequently, the validation metrics may not fully reflect the errors that occur over the final forecast horizon.

The active VM count was constant throughout the observed training window. The current data therefore provides limited evidence about model performance when the active VM population changes.

The CPU predictions are point forecasts and do not provide a prediction interval or explicit estimate of uncertainty.

## 7. Capacity Planning Implications

The predicted aggregate CPU utilization is approximately 9.19% over the two-hour forecast period. This suggests low average CPU demand in the observed workload population, but aggregate utilization alone is insufficient to determine whether individual VMs or hosts have adequate capacity.

An infrastructure team should:

* Use the forecast as one input to short-term capacity planning rather than as a guarantee of future demand.
* Monitor actual utilization against forecasts and investigate material deviations.
* Consider individual VM and host-level utilization alongside the aggregate average.
* Evaluate a safety margin using historical forecast errors and the consequences of under-provisioning.
* Avoid unnecessary over-provisioning, which can increase infrastructure costs, while maintaining sufficient headroom to handle demand spikes.

Any operational utilization threshold or safety margin should be treated as a policy assumption until it is supported by workload-specific evidence.

## 8. Conclusion

The solution implements a reproducible forecasting workflow for active VM count and aggregate CPU utilization, compares several simple time-series models, and produces the required 24-row prediction file.

The initial validation results favor Moving Average (6) for CPU utilization and simple persistence for active VM count. However, longer-horizon validation is recommended before using these forecasts for operational decisions.
