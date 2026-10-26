# Day 3: Model Training and Validation

## 1. Dataset

* Training observations: 110
* Observation interval: 5 minutes
* Initial training window: 60 observations
* Validation horizon: 6 observations (30 minutes)
* Validation step: 6 observations

## 2. Models Evaluated

The following forecasting models were evaluated:

* Persistence
* Seasonal Naive (12)
* Moving Average (6)
* Simple Exponential Smoothing (SES)
* Holt's Exponential Smoothing

## 3. Evaluation Metrics

Models were compared using Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and symmetric Mean Absolute Percentage Error (sMAPE).

Lower values indicate better predictive performance. MAE measures average absolute error, RMSE penalizes larger errors more heavily, and sMAPE expresses error as a normalized percentage.

## 4. Active VM Count

The active VM count remained constant throughout the observed training data, at 10,000 VMs.

Persistence, Seasonal Naive, Moving Average, and SES achieved zero validation error. Holt's model also produced negligible numerical error, approximately \(2.1 \times 10^{-12}\) MAE.

These results reflect the constant target in the observed training window. They do not establish that the active VM count remains constant throughout the holdout period.

## 5. CPU Utilization

The models were evaluated on 50 validation observations using chronological rolling-origin validation.

| Model               |        MAE |       RMSE |      sMAPE |
| ------------------- | ---------: | ---------: | ---------: |
| Moving Average (6)  | **0.1049** |     0.1473 | **1.111%** |
| SES                 |     0.1101 | **0.1472** |     1.166% |
| Holt                |     0.1170 |     0.1582 |     1.238% |
| Persistence         |     0.1560 |     0.1903 |     1.649% |
| Seasonal Naive (12) |     0.1859 |     0.2368 |     1.955% |

The Moving Average model achieved the lowest MAE and sMAPE. SES achieved a marginally lower RMSE. The differences between these two models are small.

The CPU MAE values are expressed in percentage points because CPU utilization is measured on a scale from 0 to 100.

## 6. Model Selection

**Selected model: Moving Average (6)**

Moving Average (6) was selected because it achieved the lowest MAE and sMAPE among the evaluated models. It also outperformed the persistence baseline on both MAE and RMSE.

Compared with persistence, Moving Average reduced MAE by approximately 32.8% and RMSE by approximately 22.6% on the existing validation results.

These improvements apply to the current validation scheme and should not be interpreted as proof of superior performance over the full two-hour forecast horizon.

## 7. Limitations

The training series contains only 110 observations, representing approximately 9 hours and 10 minutes of observations between the first and last timestamps.

The current validation horizon is six observations, equivalent to 30 minutes, whereas the final forecast horizon is 24 observations, equivalent to two hours.

Consequently, the validation results may not fully represent the error characteristics of the final forecast. The model comparison should ideally be repeated using complete 24-step rolling-origin validation before final model selection.

The active VM count is constant throughout the observed training period, limiting the ability to evaluate how the models would perform if VM activity changed.
