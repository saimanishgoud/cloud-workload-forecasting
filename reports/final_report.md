# Cloud Workload Forecasting & Analysis

## 1. Executive Summary

### Objective

The objective of this project is to analyze historical cloud virtual machine (VM) CPU utilization and forecast two workload indicators over a two-hour horizon:

* **Active VM count:** Number of distinct VMs with a valid CPU reading at each timestamp.
* **Aggregate CPU utilization:** Mean CPU utilization across the VMs with valid readings at each timestamp, expressed as a percentage.

The project uses a curated subset of the Microsoft Azure Public Dataset V2 VM trace. Observations are available at five-minute intervals. The provided training target series contains 110 observations, while the final forecast requires 24 predictions.

### Approach

The solution implements a reproducible Python forecasting workflow that includes data preparation, workload analysis, baseline forecasting, chronological model validation, model comparison, final prediction generation, and output validation.

Five forecasting approaches were evaluated:

1. Persistence
2. Seasonal Naive
3. Moving Average
4. Simple Exponential Smoothing (SES)
5. Holt's Exponential Smoothing

The models were compared using Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and symmetric Mean Absolute Percentage Error (sMAPE).

### Key Findings

The active VM count remained constant at 10,000 throughout the observed training window. Persistence and several other simple models achieved zero validation error for this target.

For aggregate CPU utilization, Moving Average with a six-observation window achieved the lowest validation MAE and sMAPE among the evaluated models.

| CPU validation metric |       Moving Average (6) |
| --------------------- | -----------------------: |
| MAE                   | 0.1049 percentage points |
| RMSE                  | 0.1473 percentage points |
| sMAPE                 |                   1.111% |

The final prediction file contains 24 chronological rows corresponding to the required forecast timestamps. The previously executed checks confirmed the expected columns, absence of missing values and duplicate timestamps, and compliance with the specified output constraints.

The forecast predicts an active VM count of 10,000 and aggregate CPU utilization of approximately 9.1909% at each of the 24 future timestamps.

**Important qualification:** The reported validation horizon is 30 minutes, whereas the final forecast horizon is two hours. The validation results therefore do not establish the accuracy of the complete two-hour forecast.

---

## 2. Data Understanding and Preprocessing

### 2.1 Dataset Overview

The project uses the curated Azure Public Dataset V2 VM trace supplied with the challenge.

The provided dataset includes:

* `vm_cpu_readings.csv.gz`: VM-level CPU readings.
* `vm_metadata.csv.gz`: VM metadata.
* `DATA_CARD.md`: Dataset documentation.
* `SHA256SUMS`: File checksum information.

The dataset subset contains 10,000 VMs, with 134 CPU observations per VM at five-minute intervals. This corresponds to approximately 1.34 million VM-level observations and an observation window of approximately 11.1 hours.

The forecasting workflow uses the challenge's training targets rather than treating individual VM readings as independent forecast targets.

### 2.2 Target Construction

Two aggregate targets are used.

**Active VM count**

At each timestamp, the active VM count is calculated as the number of distinct VMs with a valid CPU reading. Each VM must be counted at most once per timestamp.

**Aggregate CPU utilization**

At each timestamp, aggregate CPU utilization is calculated as the mean of the valid VM-level CPU readings. The resulting value is expressed on a 0–100 percentage scale.

This mean represents the average utilization across the observed VM population. It does not directly measure total CPU consumption, available compute capacity, or the utilization of the busiest individual VM.

### 2.3 Training and Forecast Windows

| Property                    | Value                                                                       |
| --------------------------- | --------------------------------------------------------------------------- |
| Training observations       | 110                                                                         |
| Observation interval        | 5 minutes                                                                   |
| Training-window duration    | Approximately 9 hours and 10 minutes between the first and last observation |
| Final forecast observations | 24                                                                          |
| Forecast horizon            | 2 hours                                                                     |
| Forecast interval           | 5 minutes                                                                   |

The final 24 timestamps are taken from the supplied holdout timestamp information.

The forecasting pipeline uses the historical training targets and required forecast timestamps. Holdout target values are not used to fit the models or select the forecasting approach.

### 2.4 Data Quality and Preprocessing

The data-quality report records 1,340,000 rows and five columns in the VM CPU readings dataset. The inspected fields—timestamp, vm_id, min_cpu, max_cpu, and avg_cpu—have zero missing values. No duplicate complete rows were recorded, and 10,000 unique VM IDs were identified. The displayed VM metadata fields also have zero missing values. These checks support the integrity of the inspected fields; they do not, by themselves, establish that every possible data-quality issue is absent.


---

## 3. Workload Analysis

### 3.1 Active VM Count

The active VM count remained at 10,000 throughout the 110-observation training series.

This indicates that the aggregated training target does not show changes in the number of VMs with valid readings during the observed period.

Persistence and Seasonal Naive both achieved zero validation error for active VM count. Moving Average and Simple Exponential Smoothing also achieved zero validation error. Holt's Exponential Smoothing produced only a negligible floating-point error of approximately 2.1 × 10⁻¹².

These results support using a simple persistence forecast for this target. However, a constant historical count does not guarantee that the active VM population will remain unchanged in the future.

### 3.2 Aggregate CPU Utilization

CPU utilization is the more informative forecasting target in this dataset because its values vary over time, while the observed active VM count remains constant.

The initial and final values previously inspected in the training target file were approximately 9.39% and 9.16%, respectively. These observations suggest a modest decline across the observed window, but two endpoints alone are insufficient to establish the complete trend or identify recurring patterns.

The model comparison results show that Moving Average (6) performed best on validation MAE and sMAPE. Simple Exponential Smoothing achieved a marginally lower RMSE.

A moving-average forecast smooths short-term variation by averaging recent observations. This makes it a reasonable candidate for a relatively stable series, although it may respond slowly to sudden changes in workload demand.

### 3.3 Operational Interpretation

The forecasted aggregate CPU utilization is approximately 9.19%. This is a low average relative to the full 0–100 utilization scale.

However, aggregate CPU utilization should not be interpreted as evidence that every VM has sufficient capacity. A low population average can coexist with high utilization on a subset of VMs.

The available aggregate series also does not, by itself, establish the timing or magnitude of workload spikes, individual VM saturation, or host-level bottlenecks.

Consequently, capacity decisions should incorporate VM-level and host-level telemetry where available.

---

## 4. Forecasting Approach

### 4.1 Baseline and Candidate Models

Five forecasting approaches were evaluated.

| Model                        | Description                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| Persistence                  | Uses the most recent observed value as the forecast.                                         |
| Seasonal Naive (12)          | Uses a value from 12 observations earlier, corresponding to one hour at five-minute cadence. |
| Moving Average (6)           | Uses a six-observation window, corresponding to 30 minutes of history.                       |
| Simple Exponential Smoothing | Produces forecasts using exponentially weighted historical observations.                     |
| Holt's Exponential Smoothing | Extends exponential smoothing to model a trend component.                                    |

Persistence provides a simple benchmark against which more complex forecasting methods can be evaluated.

The candidate models were compared using the same chronological validation framework.

### 4.2 Model Selection Criteria

MAE was used as the primary selection metric. RMSE and sMAPE were used as supporting metrics.

* **MAE** measures the average absolute difference between predictions and actual values.
* **RMSE** penalizes larger errors more strongly because the errors are squared before averaging and taking the square root.
* **sMAPE** expresses forecast error as a symmetric percentage-based measure.

For CPU utilization, MAE and RMSE are expressed in percentage points because the target is measured on a 0–100 percentage scale.

The selected models were:

* **Active VM count:** Persistence.
* **Aggregate CPU utilization:** Moving Average (6).

Persistence is appropriate for the observed constant active VM count. Moving Average (6) was selected for CPU utilization because it had the lowest validation MAE and sMAPE among the evaluated candidates.

### 4.3 Final Forecast Generation

After model selection, the forecasting pipeline refits the selected models using the complete available training window and generates predictions for the 24 required timestamps.

The pipeline includes checks for:

* Required training columns.
* Valid and chronologically ordered observations.
* Correct prediction timestamps.
* The required number of forecast rows.
* Missing and non-finite predictions.
* Nonnegative active VM counts.
* CPU utilization within the 0–100 range.

The final output is written to `predictions.csv` without an index column.

---

## 5. Validation Methodology

### 5.1 Time-Aware Validation

The model comparison uses chronological rolling-origin validation rather than a random train-test split.

The initial training window contains 60 observations. Each validation fold forecasts up to six observations, and the origin advances by six observations for the next fold.

| Validation parameter                   |           Value |
| -------------------------------------- | --------------: |
| Available training observations        |             110 |
| Initial training window                | 60 observations |
| Validation horizon                     |  6 observations |
| Validation horizon in time             |      30 minutes |
| Step size                              |  6 observations |
| Total validation observations reported |              50 |

This design preserves temporal ordering and evaluates models on observations that occur after their respective training windows.

It is more representative of forecasting future workloads than a random split, which could allow observations from later periods to influence model evaluation.

The reported total of 50 validation observations includes the final partial fold. With the current configuration, the first eight folds contain six observations each, while the final fold contains two observations.

### 5.2 Limitations of the Validation Design

The final forecast horizon is 24 observations, equivalent to two hours. The validation horizon is only six observations, equivalent to 30 minutes.

As a result, the reported metrics primarily characterize short-horizon forecasting performance. They do not fully measure the errors that may accumulate over a two-hour forecast.

A stronger final evaluation would use complete 24-step rolling-origin validation folds, provided the training series supports a meaningful comparison. The results should then be compared with the corresponding baseline forecasts.

The small number of observations also limits the range of workload patterns available for evaluating generalization.

---

## 6. Results Versus Baseline

### 6.1 Active VM Count Results

| Model                        |                  MAE |                 RMSE |                sMAPE |
| ---------------------------- | -------------------: | -------------------: | -------------------: |
| Moving Average (6)           |               0.0000 |               0.0000 |               0.000% |
| Persistence                  |               0.0000 |               0.0000 |               0.000% |
| Seasonal Naive (12)          |               0.0000 |               0.0000 |               0.000% |
| Simple Exponential Smoothing |               0.0000 |               0.0000 |               0.000% |
| Holt's Exponential Smoothing | Approximately 0.0000 | Approximately 0.0000 | Approximately 0.000% |

The tiny errors recorded for Holt's model are numerical floating-point differences rather than meaningful changes in predicted VM count.

Because the active VM count remains constant throughout the observed series, a simple persistence forecast is sufficient based on the available validation evidence. There is no demonstrated advantage in using a more complex model for this target.

### 6.2 CPU Utilization Results

The following table presents the recorded chronological validation metrics for aggregate CPU utilization.

| Model                        |    MAE |   RMSE |  sMAPE |
| ---------------------------- | -----: | -----: | -----: |
| Moving Average (6)           | 0.1049 | 0.1473 | 1.111% |
| Simple Exponential Smoothing | 0.1101 | 0.1472 | 1.166% |
| Holt's Exponential Smoothing | 0.1170 | 0.1582 | 1.238% |
| Persistence                  | 0.1560 | 0.1903 | 1.649% |
| Seasonal Naive (12)          | 0.1859 | 0.2368 | 1.955% |

Moving Average (6) achieved the lowest MAE and sMAPE. Simple Exponential Smoothing achieved a marginally lower RMSE, indicating that it had a slightly lower root mean squared error over the recorded validation observations.

Moving Average (6) was selected because MAE was the primary selection metric and its sMAPE was also the lowest.

### 6.3 Improvement Over Persistence

Relative to the persistence baseline, Moving Average (6) achieved approximately:

* **32.8% lower MAE**
* **22.6% lower RMSE**

These improvements are calculated from the recorded validation metrics:

$$
\text{MAE improvement}
=
\frac{0.1559702 - 0.1048601}{0.1559702}
\times 100
\approx 32.8\%
$$

$$
\text{RMSE improvement}
=
\frac{0.1903433 - 0.1472531}{0.1903433}
\times 100
\approx 22.6\%
$$

These improvements apply to the reported short-horizon validation results. They should not be interpreted as established improvements over the full two-hour forecast horizon.

### 6.4 Interpreting sMAPE

sMAPE provides a percentage-based comparison of forecast errors. It is useful alongside MAE and RMSE, but it should not be interpreted in isolation.

Percentage-based metrics can behave poorly when actual and predicted values are near zero. In this dataset, the inspected CPU utilization values are around 9%, rather than near zero, but the metric should still be interpreted alongside absolute errors.

---

## 7. Error Analysis and Failure Considerations

### 7.1 Observed Validation Errors

Moving Average (6) produced a CPU MAE of approximately 0.1049 percentage points and RMSE of approximately 0.1473 percentage points over the recorded validation observations.

The difference between MAE and RMSE indicates that larger errors contribute more to RMSE than to the average absolute error, as expected. The available aggregate metrics do not, however, identify the exact timestamps or causes of those larger errors.

The active VM count models achieved effectively zero error because the target remained constant during the observed training and validation periods.

### 7.2 Potential Forecast Failure Modes

Several limitations could affect future performance:

1. **Workload changes:** CPU utilization may increase or decrease more sharply than observed in the training window.
2. **VM population changes:** New VM activity, shutdowns, or missing telemetry may change the active VM count.
3. **Longer forecast horizon:** A model that performs well over 30 minutes may not perform as well over two hours.
4. **Short historical window:** The series may not contain enough history to identify recurring daily or weekly patterns.
5. **Aggregation effects:** Mean CPU utilization can hide individual VMs that are heavily utilized.
6. **Model responsiveness:** A moving average can lag sudden changes because it smooths recent observations.

### 7.3 Recommended Error Analysis

Before relying on the forecast for operational decisions, the following analyses should be completed using the validation predictions:

* Plot actual and predicted CPU utilization for each validation fold.
* Calculate the largest absolute forecast errors.
* Compare errors during relatively high- and low-utilization periods.
* Inspect whether forecast errors increase with the forecast lead time.
* Compare the selected model with persistence over complete 24-step validation horizons.
* Investigate periods where the active VM count changes, if such periods are available.

The exact peak-period errors and timestamp-specific failure causes have not been established by the aggregate metrics presented in this report.

---

## 8. Capacity Planning Recommendation

### 8.1 Forecast-Based Interpretation

The final forecast predicts aggregate CPU utilization of approximately 9.1909% across the two-hour horizon, with the active VM count remaining at 10,000.

This provides a short-term indication of average utilization under the selected forecasting approach. It should not be treated as a guarantee that future utilization will remain at this level.

The current forecast is most useful as an additional signal for workload monitoring and planning, rather than as the sole input to automated scaling or resource removal.

### 8.2 Over-Provisioning and Under-Provisioning

**Over-provisioning** occurs when more compute capacity is allocated than the workload requires. It can increase infrastructure expenditure and leave resources underutilized.

**Under-provisioning** occurs when available capacity is insufficient for demand. It can lead to high utilization, increased latency, degraded performance, failed workloads, or service interruptions.

Capacity planning must balance these costs. A low aggregate utilization forecast may suggest an opportunity to investigate resource efficiency, but it is not sufficient evidence to remove capacity without examining individual VM and host utilization.

### 8.3 Recommended Operational Actions

1. Monitor actual CPU utilization against the forecast at each five-minute interval.
2. Evaluate per-VM and host-level utilization before scaling resources.
3. Use historical forecast errors to estimate an appropriate safety margin.
4. Assess the impact of under-provisioning on workload performance and service objectives.
5. Prefer incremental, reversible capacity changes where operationally appropriate.
6. Re-evaluate the model when workload patterns or VM population characteristics change.

### 8.4 Safety Margin Assumptions

This report does not prescribe a fixed utilization threshold or safety margin because the available results do not establish an appropriate operational threshold for this workload.

Any threshold should be treated as an explicit policy assumption and justified using forecast errors, workload criticality, service-level objectives, and the consequences of capacity shortages.

A production deployment should consider prediction intervals or other uncertainty estimates, rather than relying exclusively on point forecasts.

---

## 9. Limitations and Future Work

### Limitations

The solution has several limitations:

* Only 110 aggregate training observations are available.
* The training series covers approximately 9 hours and 10 minutes between the first and last observations.
* The initial validation horizon is 30 minutes, shorter than the final two-hour forecast.
* The active VM count remains constant throughout the observed training series, limiting the evidence for predicting VM population changes.
* Aggregate mean CPU utilization can conceal localized utilization peaks.
* The current forecasts do not quantify uncertainty.
* The reported metrics do not provide a complete timestamp-level analysis of peak errors.

### Future Work

The following improvements would strengthen the forecasting solution:

1. **Longer-horizon validation:** Evaluate models using complete 24-step rolling-origin folds.
2. **Expanded error analysis:** Inspect forecast errors by timestamp, forecast lead time, and workload level.
3. **Uncertainty estimation:** Add prediction intervals to communicate the range of plausible future utilization.
4. **Additional features:** Where available and justified, investigate time-of-day effects, VM metadata, workload categories, and lagged CPU values.
5. **Dynamic VM count forecasting:** Evaluate models on periods where active VM counts actually change.
6. **Operational monitoring:** Compare forecasts with incoming telemetry and establish a process for detecting sustained forecast deviations.
7. **Reproducibility:** Maintain documented installation instructions, deterministic preprocessing, automated validation, and a repeatable forecasting command.

Any additional model should be retained only if it demonstrates a meaningful improvement under an appropriate chronological validation scheme.

---

## 10. Conclusion

This project implements a reproducible workflow for analyzing cloud workload targets and forecasting active VM count and aggregate CPU utilization.

The recorded validation results support persistence for active VM count and Moving Average (6) for CPU utilization. The selected CPU model improved validation MAE by approximately 32.8% relative to persistence under the current short-horizon evaluation.

The final prediction file contains the required 24 timestamps and satisfies the previously checked structural and value constraints.

However, the two-hour forecast horizon exceeds the current 30-minute validation horizon. Longer-horizon validation and timestamp-level error analysis are therefore important before using these predictions to make capacity allocation decisions.

The main conclusion is that simple time-series methods provide a reasonable starting point for this dataset, but operational deployment requires stronger evidence about longer-horizon accuracy, workload variability, and forecast uncertainty.
