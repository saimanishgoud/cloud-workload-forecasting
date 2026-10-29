# Cloud Workload Forecasting & Analysis — Final Report

## 1. Executive Summary

**Question.** How predictable is this cloud workload, how accurately can the next two hours be forecast, and what should an infrastructure team do with the forecast?

**Answer in brief.**

* **The workload is very stable in aggregate and only weakly predictable beyond ~30 minutes.** Aggregate CPU utilization (mean `avg_cpu` across 10,000 VMs) stayed between 9.11% and 9.91% over the 110 training observations (std 0.19 pp). Errors of a few tenths of a percentage point are therefore a large share of the signal.
* **Forecast submitted:** 10,000 active VMs and 9.19% aggregate CPU for each of the 24 holdout timestamps (a flat forecast).
* **Active VM count is constant by construction, not by workload behavior.** The challenge data keeps only VMs that have a complete 134-reading trace, and all 10,000 were created at t=0. Zero churn is therefore a property of the sampling, so the zero validation error for this target says nothing about real VM-count predictability.
* **Selected models:** persistence for VM count; 6-observation moving average (MA6) for CPU, chosen on rolling-origin validation using training data only.
* **MA6 beats the persistence baseline** by 32.8% (MAE) at a 30-minute horizon and by 17.6% at the full 2-hour horizon. The gain shrinks with horizon, and all models over-forecast by about 0.2 pp at 2 hours.
* **Main operational message:** the 9% average hides a heavy tail. The top 5% of VMs carry 30% of all CPU, and 1.3% of VM readings exceed 80%. Capacity decisions should key off tail indicators, not the fleet mean (Section 8).

**Honest caveat on model choice.** Selection used a 30-minute validation horizon, as pre-specified. When I later re-ran validation at the true 24-step horizon, a full-history mean beat MA6 (Section 6.2). Because only five overlapping folds exist, I treat this as a flagged limitation rather than a reason to change the submission.

---

## 2. Data Understanding and Preprocessing

**Data.** Curated subset of Azure Public Dataset V2: 10,000 VMs × 134 five-minute readings = 1,340,000 rows (`timestamp`, `vm_id`, `min_cpu`, `max_cpu`, `avg_cpu`), plus one metadata row per VM. File checksums were verified against `SHA256SUMS`.

**Quality checks** (`python -m cwfc.data_quality`):

| Check | Result |
|---|---|
| Missing values in CPU fields | 0 |
| Duplicate (timestamp, VM) records | 0 |
| CPU values outside [0, 100] | 0 |
| Unique timestamps | 134 (t = 0 to 39,900 s) |
| Interval between timestamps | 133 of 133 gaps are exactly 300 s |
| VMs created at t=0 | 10,000 of 10,000 |

**What this means.** There are no gaps to impute, so no imputation was done. Every VM is observed at every timestamp. This is a property of how the challenge set was built: only VMs with complete traces were eligible, and selection was stratified by VM category and core bucket. The data is therefore a stratified sample, not a random sample of the Azure fleet, and absolute utilization levels should not be generalized to the whole fleet.

**Target construction** (`python -m cwfc.build_targets`):

* `active_vm_count` = number of distinct `vm_id` values with a valid reading at the timestamp (each VM counted once).
* `aggregate_cpu_utilization` = unweighted mean of `avg_cpu` over all VMs at the timestamp, in percent (0–100). A core-weighted mean (using bucket sizes, ">24" taken as 24) would be about 9.3% on average, close to the unweighted 9.4%.

**Split.** The full 134-point target series is built first. The first 110 observations (t = 0–32,700 s, about 9 h 5 min) are the training window; the last 24 (t = 33,000–39,900 s) are the 2-hour holdout. Native 5-minute cadence is used throughout, so forecasts map one-to-one onto the holdout timestamps with no resampling.

**Leakage control.** Models use only lagged values of the target, which are available at the forecast origin. Holdout targets are never used for fitting, feature choice, or model selection. The final forecaster reads only the holdout *timestamps*.

---

## 3. Workload Analysis

All numbers in this section use the training window only.

### 3.1 Aggregate level and temporal behavior

| Property | Value |
|---|---|
| Range of aggregate CPU | 9.11% – 9.91% |
| Median / std | 9.38% / 0.19 pp |
| Linear trend | −0.013 pp per hour (negligible) |
| Peak | 9.91% at t = 16,500 s (~4.6 h) |
| Hourly means (h0 → h9) | 9.41, 9.41, 9.37, 9.36, 9.62, 9.71, 9.37, 9.30, 9.24, 9.14 |

The series rises to a mild plateau in hours 4–5, then drifts down. With only about 9 hours of history, no daily or weekly cycle can be identified; the 12-step seasonal-naive model (a 1-hour period) does worse than persistence, which supports the absence of a usable short seasonal pattern.

**Key structural fact:** the 5-minute changes have lag-1 autocorrelation of −0.42. In other words the series behaves like a slowly moving level plus independent measurement noise. This explains why averaging the last few points beats copying the last value (Section 6).

### 3.2 VM-level distribution (the fleet mean hides a heavy tail)

| Statistic | Value |
|---|---|
| Median VM reading (`avg_cpu`) | 5.1% |
| Readings below 5% | 48.9% |
| 95th / 99th percentile reading | 37.3% / 87.4% |
| Readings above 50% / above 80% | 3.1% / 1.3% |
| Share of total CPU carried by the top 5% of VMs | 30.0% |
| VMs averaging above 50% over the window | 2.2% |
| VMs with at least one `max_cpu` ≥ 95% | 14.0% |

Half of all readings are nearly idle, while a small set of VMs run hot. A fleet average of 9% is fully consistent with a meaningful number of VMs being saturated.

### 3.3 Segments

| Segment | VMs | Mean CPU | Std over time |
|---|---:|---:|---:|
| **VM category** | | | |
| Interactive | 3,091 | 11.5% | 0.24 pp |
| Delay-insensitive | 6,180 | 8.3% | 0.22 pp |
| Unknown | 729 | 10.4% | 0.63 pp |
| **Core bucket** | | | |
| 2 cores | 7,534 | 9.8% | 0.24 pp |
| 4 cores | 1,908 | 7.9% | 0.19 pp |
| 8 cores | 486 | 9.7% | 0.42 pp |
| 24 cores | 62 | 11.4% | 0.41 pp |
| >24 cores | 10 | 6.6% | 2.00 pp |

Interactive VMs run about 3 pp hotter than delay-insensitive VMs. Interactive workloads are typically latency-sensitive, so they are the natural first target for headroom rules. Small segments (the 10 largest VMs) are far noisier, which is why aggregate forecasts are much steadier than segment forecasts would be.

### 3.4 What drives the aggregate

The aggregate moves with the bulk of VMs (correlation 0.92 with the mean of the other 95% of VMs) and less with the hot top 5% (correlation 0.71), although that group swings far more on its own (std 1.6 pp versus 0.16 pp). Aggregate stability therefore says little about individual hot VMs.

### 3.5 Peak and low-demand periods

Peak demand occurs around hours 4–5 (9.6–9.9%). The lowest values occur at the end of the training window (minimum 9.11% at t = 32,400 s). Differences between peak and low are about 0.8 pp, small in absolute terms.

---

## 4. Forecasting Approach

Candidate models (all at native 5-minute cadence, fitted on past data only):

| Model | Description |
|---|---|
| Persistence (baseline) | Last observed value |
| Seasonal naive (12) | Value one hour earlier, repeated |
| Moving average (3, 6, 12, 24) | Mean of the last *k* observations |
| Simple exponential smoothing (SES) | Exponentially weighted level (statsmodels, optimized) |
| Holt | Level + linear trend |
| Expanding mean | Mean of all history (diagnostic reference) |

The five models in the original pipeline are persistence, seasonal-naive, MA6, SES and Holt. MA3, MA12, MA24 and the expanding mean were added in the extended analysis (`python -m cwfc.extended_analysis`) to test sensitivity.

**Selection rule (pre-specified):** lowest rolling-origin MAE per target; RMSE and sMAPE as supporting metrics. For `active_vm_count` all models tie at zero error, so persistence (simplest) is used.

**Final fit:** the selected model is refit on all 110 training observations and projected 24 steps ahead. Output checks enforce column order, 24 rows, holdout timestamps in order, no duplicates, finite values, VM count ≥ 0 and CPU in [0, 100].

---

## 5. Validation Methodology

Rolling-origin (expanding-window) evaluation on the 110 training observations only, with no shuffling:

| Parameter | Primary (used for selection) | Horizon-matched (diagnostic) |
|---|---:|---:|
| Initial training window | 60 | 60 |
| Forecast horizon | 6 obs (30 min) | 24 obs (2 h) |
| Step between origins | 6 | 6 |
| Folds | 9 (last has 2 points) | 5 (overlapping) |
| Scored forecasts | 50 | 120 |

This design only ever scores forecasts on data that comes after the training window, which mirrors production use: refit as new data arrives, forecast ahead. The primary scheme was fixed before the final forecast was produced. The horizon-matched run was added because the final forecast is 2 hours, longer than the 30-minute selection horizon.

**Percentage metric.** sMAPE is used as a supporting metric. Its denominator is the mean of |actual| and |forecast|; here both are about 9, nowhere near zero, so near-zero instability does not occur.

---

## 6. Results

### 6.1 Primary validation (30-minute horizon)

Aggregate CPU, errors in percentage points:

| Model | MAE | RMSE | sMAPE | MAE gain vs persistence |
|---|---:|---:|---:|---:|
| MA3 *(extra)* | 0.1035 | 0.1391 | – | +33.6% |
| **MA6 (selected)** | **0.1049** | 0.1473 | **1.111%** | **+32.8%** |
| SES | 0.1101 | 0.1472 | 1.166% | +29.4% |
| Holt | 0.1170 | 0.1582 | 1.238% | +25.0% |
| MA12 *(extra)* | 0.1368 | 0.1765 | – | +12.3% |
| **Persistence (baseline)** | 0.1560 | 0.1903 | 1.649% | 0 |
| Seasonal naive (12) | 0.1859 | 0.2368 | 1.955% | −19.2% |

* MA6 vs persistence: MAE −32.8%, RMSE −22.6%.
* The MAE is about 1.1% of the CPU level.
* MA3 is marginally better than MA6 (0.1035 vs 0.1049), but the difference is well within noise for 50 scored points, so MA6 as originally selected stands.
* SES has a slightly lower RMSE than MA6 (0.14721 vs 0.14725), also a negligible difference.

`active_vm_count`: persistence, seasonal naive, moving average and SES all have exactly zero error; Holt's error is on the order of 10⁻¹² (floating-point noise). As explained in Section 1, this reflects the sampling design of the dataset.

### 6.2 Horizon-matched validation (2-hour horizon)

| Model | MAE | RMSE | Bias (pred − actual) | MAE gain vs persistence |
|---|---:|---:|---:|---:|
| Expanding mean *(diagnostic)* | 0.1728 | 0.2010 | +0.086 | +38.3% |
| MA3 | 0.2235 | 0.2799 | +0.206 | +20.2% |
| **MA6 (submitted)** | 0.2309 | 0.2865 | +0.221 | +17.6% |
| SES | 0.2346 | 0.2897 | +0.228 | +16.3% |
| Persistence | 0.2802 | 0.3322 | +0.277 | 0 |
| Holt | 0.2854 | 0.3591 | +0.280 | −1.9% |

Observations:

1. **Accuracy degrades with lead time.** MA6 MAE by lead: 0.12 (steps 1–6), 0.20 (7–12), 0.28 (13–18), 0.31 (19–24) pp. Persistence is worse at every lead.
2. **The advantage of MA6 over persistence shrinks** from 32.8% (30 min) to 17.6% (2 h). Part of this gain is variance reduction: smoothing removes the noise that persistence copies forward.
3. **A horizon-matched comparison would favor the full-history mean.** The expanding mean has 25% lower MAE than MA6 at 24 steps (0.173 vs 0.231). This is consistent with a series that fluctuates around a stable level: over two hours, the long-run mean is a better anchor than the last 30 minutes. It rests on five overlapping folds from one 9-hour trace, so I do not treat it as conclusive, and the submission keeps the pre-specified MA6.
4. **All models over-forecast.** The positive bias (+0.2 pp for MA6) arises because the series fell after its hour 4–5 plateau, so forecasts anchored on recent higher values were too high. For capacity planning this error direction is the conservative one.

---

## 7. Error and Failure Analysis

**Peak vs non-peak.** "High load" = actual ≥ 9.496% (75th percentile of the first 60 observations).

| Horizon | Period | Model | MAE | Bias | n |
|---|---|---|---:|---:|---:|
| 30 min | High load | MA6 | 0.104 | +0.080 | 14 |
| 30 min | High load | Persistence | 0.146 | +0.139 | 14 |
| 30 min | Other | MA6 | 0.105 | +0.075 | 36 |
| 2 h | High load | MA6 | 0.137 | +0.121 | 24 |
| 2 h | High load | Persistence | 0.178 | +0.174 | 24 |
| 2 h | Other | MA6 | 0.254 | +0.246 | 96 |

MA6 is not worse during peaks. Its largest 2-hour errors occur in the *lower*-demand periods that follow a peak, when it still anchors on the elevated recent level.

**Where it fails.** The five largest 30-minute errors are all over-forecasts, the worst being 0.51 pp at t = 22,800 s. The largest ones follow a drop in the utilization level (e.g., 9.67% forecast vs 9.15% actual at the worst point): the moving average lags a turning point by design.

**Structural failure modes.**

1. *Turning points:* any smoothing model lags level changes.
2. *Horizon:* skill over persistence decays with lead time.
3. *Tail blindness:* a model of the mean says nothing about individual hot VMs.
4. *Short history:* no daily or weekly cycle can be learned from 9 hours.
5. *No VM-count dynamics:* because count never changes, the model has never been tested on real churn.

**Uncertainty.** MA6's 2-hour residuals (prediction − actual) have 5th/50th/95th percentiles of −0.04/+0.22/+0.53 pp. A 90% band calibrated on the early folds covered only 75% of the later folds, so empirical bands from this little history under-cover. I therefore recommend a wider band of **±0.6 pp (about 2 × the 2-hour RMSE of 0.29)** around the forecast, and I flag it as a judgment-based policy parameter.

**Post-hoc holdout check** *(reported after the fact; not used for fitting or selection; alternatives other than the baseline were deliberately not evaluated on the holdout to avoid test-set selection)*:

| Model | Forecast | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| MA6 (submitted) | 9.191 | 0.134 | 0.171 | −0.078 |
| Persistence (baseline) | 9.165 | 0.147 | 0.185 | −0.104 |

The actual holdout CPU ranged from 8.98% to 9.64% (mean 9.27%), and all 24 values fall inside the ±0.6 pp band. The submitted forecast beat persistence by about 9% on MAE. This is better than the validation-based expectation at 2 hours (0.23 MAE) but the holdout is one 2-hour window, so it is a single data point. Active VM count was predicted exactly (10,000).

---

## 8. Capacity-Planning Recommendation

**Principle: size and alert on the tail, use the forecast for drift detection.**

The forecast says average CPU will stay near 9.2%. On its own that would suggest large unused capacity. The VM-level data says otherwise: the top 5% of VMs carry 30% of CPU, 14% of VMs touched ≥95% peak CPU in the 9-hour window, and every timestamp has 1.1–1.5% of VMs above 80%. Consolidating on the mean would hit those VMs.

**Proposed policy** (all thresholds are assumptions to be tuned to the team's service-level objectives):

1. **Do not remove or consolidate capacity based on the fleet average.** Use the forecast as a monitoring baseline.
2. **Drift trigger (aggregate).** Flag for review if actual aggregate CPU exceeds the forecast by more than **0.6 pp for 3 consecutive 5-minute intervals** (15 minutes). In the training window such a gap would essentially never occur, so this detects a genuine regime shift rather than ordinary noise.
3. **Tail trigger (the important one).** Normal range for the share of VMs above 80% CPU is 1.1–1.5%. Investigate hot VMs when the share exceeds **2%** for 3 consecutive intervals (≈1.4 × the observed maximum). Also track the per-timestamp 99th percentile (normally 82–91%).
4. **Segment rule.** Interactive VMs (11.5% mean CPU, latency-sensitive) get headroom and alerting first. Delay-insensitive VMs (8.3%) can tolerate queuing and are the first candidates for batching or consolidation, subject to rule 3.
5. **Prefer small, reversible steps.** Scale out in increments and re-forecast every 5 minutes.
6. **VM count.** Treat "10,000" as an assumption; in production, VM churn must be forecast separately.

**Trade-off.** Under-provisioning risks latency, throttling and failures, with immediate user impact. Over-provisioning wastes spend and is easy to reverse. At a 9% average utilization the cost asymmetry favors keeping headroom for the tail. The forecast's over-forecasting bias (+0.2 pp at 2 hours) errs toward more capacity, the safer direction.

---

## 9. Limitations and Future Work

**Limitations**

* Only 9 hours of training history, so there is no seasonality evidence and only five (overlapping) 2-hour folds.
* Model selection used a 30-minute horizon; the 2-hour check favors a different model (full-history mean).
* VM count is constant by dataset construction, so churn forecasting is untested.
* The sample is a stratified subset of the fleet, not the whole fleet.
* The ±0.6 pp band and all trigger thresholds are policy assumptions, not statistically calibrated.
* The holdout check is a single 2-hour window.

**Future work**

1. Select models using 24-step folds (or horizon-weighted loss) and re-run with a longer history.
2. Add quantile/conformal intervals once more history exists.
3. Forecast tail indicators directly (share of VMs >80%, p99), since the operational policy depends on them.
4. Forecast by segment (interactive vs delay-insensitive) with hierarchical reconciliation.
5. Evaluate on traces with real VM creation and deletion.
6. Add time-of-day and day-of-week features once multi-day data is available.

---

## 10. Reproducibility

```bash
python -m pip install -e ".[dev]"        # pyproject.toml must list matplotlib and openpyxl
python -m cwfc.build_targets
python -m cwfc.data_quality
python -m cwfc.eda
python -m cwfc.run_baseline_validation
python -m cwfc.run_model_comparison
python -m cwfc.final_forecast            # writes predictions.csv
python -m cwfc.export_workload_analysis
python -m cwfc.extended_analysis         # numbers in Sections 3, 6.2, 7 and 8
python -m pytest -q
```

Verified on a clean clone: the pipeline regenerates `predictions.csv` identically to the committed file.
