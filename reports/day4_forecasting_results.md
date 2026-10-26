# Day 4: Final Forecasting Pipeline

## 1. Objective

Generate 24 future predictions for active VM count and
aggregate CPU utilization using historical training data.

## 2. Model Selection

Models were compared using chronological validation.

Selected model for active VM count:
[Insert actual model]

Selected model for CPU utilization:
[Insert actual model]

Selection criteria:
MAE was the primary metric, with RMSE and sMAPE used
as supporting metrics.

## 3. Final Forecasting Pipeline

The selected models were refitted using the complete
available training window.

The pipeline reads the required forecast timestamps
and generates predictions without using holdout target
values.

## 4. Output Validation

- Required columns: [verified result]
- Prediction rows: [verified result]
- Missing values: [verified result]
- Duplicate timestamps: [verified result]
- Active VM count constraints: [verified result]
- CPU utilization constraints: [verified result]

## 5. Forecast Behavior

Describe whether the CPU predictions are constant,
increasing, decreasing, or fluctuating.

Explain the observed behavior using the selected
model and the historical training data.

## 6. Limitations

The historical training window contains only 110
observations at five-minute intervals.

The two-hour forecast extends beyond the initial
30-minute validation horizon. Longer-horizon
validation is therefore important.

The active VM count was constant in the observed
training window, but future counts are not guaranteed
to remain constant.

## 7. Capacity Planning Implications

Discuss historical CPU levels, forecast limitations,
the cost of over-provisioning, and the risk of
under-provisioning.

Any proposed utilization threshold or safety margin
must be stated as an assumption and justified.