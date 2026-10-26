# Day 3: Model Training and Validation

## 1. Dataset

- Training observations: 110
- Observation interval: 5 minutes
- Initial training window: 60 observations
- Validation horizon: 6 observations
- Validation step: 6 observations

## 2. Models Evaluated

- Persistence
- Seasonal Naive
- Moving Average
- Simple Exponential Smoothing
- Holt's Exponential Smoothing

## 3. Evaluation Metrics

Models were compared using MAE, RMSE, and sMAPE.
Lower values indicate better predictive performance.

## 4. Active VM Count

The active VM count remained constant throughout the
observed training data.

Persistence and Seasonal Naive both achieved zero error
on the previous validation results.

This does not establish that the count remains constant
throughout the holdout period.

## 5. CPU Utilization

The previous validation results showed that Persistence
outperformed Seasonal Naive.

The additional models were evaluated using the same
chronological validation scheme.

Best model by CPU MAE: [fill in from actual results]

CPU MAE: [actual value]

CPU RMSE: [actual value]

CPU sMAPE: [actual value]

## 6. Model Selection

Selected model: [fill in after comparison]

Reason for selection: [explain using actual metrics]

## 7. Limitations

The training series contains only 110 observations.
The final forecast horizon is two hours, while the
initial validation horizon is 30 minutes.

Model performance over a two-hour forecast horizon
must be considered separately before final submission.