# Cloud Workload Forecasting

This project forecasts two things for a set of Azure virtual machines over a two-hour window: how many VMs are active, and what their average CPU utilization will be. It uses a 10,000-VM sample of the Microsoft Azure Public Dataset V2, sampled every five minutes.

The short version of what I found: the workload is very flat in aggregate, a simple moving average beats the "same as last time" baseline, and the fleet average hides a small group of busy VMs that matter more for capacity planning than the average does. The full write-up is in [`reports/final_report.md`](reports/final_report.md).

## Results at a glance

| | Active VM count | Aggregate CPU utilization |
|---|---|---|
| Model chosen | Persistence | 6-point moving average |
| Forecast for all 24 timestamps | 10,000 | 9.19% |
| Validation MAE (30-min horizon) | 0 | 0.105 pp |
| Persistence baseline MAE | 0 | 0.156 pp |

Two things worth knowing before you read the numbers:

* The VM count is constant at 10,000 because the challenge data only includes VMs with complete traces. It is a feature of how the dataset was built, so a zero error here doesn't say much about the model.
* Models were selected on a 30-minute validation horizon, but the final forecast covers two hours. The report checks the longer horizon too and is upfront about where the choice is shaky.

## Getting set up

You need Python 3.11 or newer.

```bash
git clone https://github.com/saimanishgoud/cloud-workload-forecasting.git
cd cloud-workload-forecasting

python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

python -m pip install -e ".[dev]"
```

### The data

The data isn't stored in this repository. Download the `data-v1` release and unpack it into `challenge_data/`:

```bash
curl -L -o data-v1.tar.gz \
  https://github.com/atomityhq/forecasting-challenge/releases/download/data-v1/data-v1.tar.gz
tar -xzf data-v1.tar.gz -C challenge_data
rm data-v1.tar.gz

cd challenge_data && sha256sum -c SHA256SUMS && cd ..
```

After that, `challenge_data/` should contain `vm_cpu_readings.csv.gz`, `vm_metadata.csv.gz`, `DATA_CARD.md` and `SHA256SUMS`, and the checksum check should print `OK` three times.

## Generating the predictions

From the repository root:

```bash
python -m cwfc.build_targets && \
python -m cwfc.run_model_comparison && \
python -m cwfc.final_forecast
```

This builds the two target series from the raw readings, compares the candidate models with rolling-origin validation, picks the best one for each target, and writes `predictions.csv`. It starts from nothing, so it works on a clean checkout and doesn't rely on anything already sitting in `reports/`. On a normal laptop it takes a minute or two, most of it spent loading the 1.3 million-row CPU file.

Run them in this order. `build_targets` is the only script that reads the raw data, and it creates the files the other two depend on, so running `final_forecast` first fails with a "file not found" error. If you hit that, start again from `build_targets`.

The output has exactly the columns `timestamp,active_vm_count,aggregate_cpu_utilization` and 24 rows, one for each five-minute timestamp in the final two hours.

## The rest of the analysis

The three commands above are all you need for the predictions. The remaining scripts produce the analysis behind the report and can be run in any order after `build_targets`:

```bash
python -m cwfc.data_quality               # missing values, duplicates, timestamp gaps
python -m cwfc.eda                        # exploratory charts
python -m cwfc.run_baseline_validation    # persistence and seasonal-naive on their own
python -m cwfc.export_workload_analysis   # Excel workbook and charts
python -m cwfc.extended_analysis          # 2-hour validation, peak errors, VM tail, segments
python -m pytest -q                       # unit tests
```

Everything is written to `reports/`.

## If something goes wrong

* `FileNotFoundError` mentioning `vm_cpu_readings.csv.gz`: the data isn't in `challenge_data/` yet. See "The data" above.
* `FileNotFoundError` mentioning a file in `reports/`: a step was skipped. Run `build_targets` first, then the others.
* `No module named cwfc`: activate your virtual environment and run the commands from the repository root.
* `No module named matplotlib` or `openpyxl`: reinstall with `python -m pip install -e ".[dev]"`.

## How it works

**Targets.** At every timestamp, `active_vm_count` is the number of distinct VMs with a valid reading, and `aggregate_cpu_utilization` is the average of `avg_cpu` across those VMs. The split is by position: the last 24 timestamps are the holdout, and everything before them (110 timestamps here) is training. The code works out the split from the data instead of hard-coding timestamps.

**Models.** Persistence, seasonal naive, moving average, simple exponential smoothing and Holt's trend method. All of them run at the native five-minute cadence, so there's no resampling step to explain.

**Validation.** Rolling-origin with an expanding window: start with 60 observations, forecast the next 6, move forward by 6, repeat. Nothing is shuffled, and every forecast is scored on data that comes after its training window. The best MAE per target wins.

**No leakage.** The only inputs are past values of the target. The final step reads the holdout *timestamps* to know what to label the predictions, but never the holdout values.

## What's in the repo

```text
challenge_data/   data release goes here (not committed)
reports/          generated tables, charts and the final report
src/cwfc/         the pipeline code
tests/            unit tests for metrics and validation splits
predictions.csv   the submission file
pyproject.toml    dependencies
```

## Limitations

* There are only about nine hours of history, so daily or weekly patterns can't be learned or tested.
* Validation uses a 30-minute horizon while the forecast spans two hours.
* The VM count never changes in this data, so churn forecasting is untested.
* The dataset is a stratified sample, not the whole Azure fleet, so the absolute CPU levels shouldn't be generalised.
* Average CPU says nothing about individual VMs. In this sample the top 5% of VMs account for about 30% of all CPU, so capacity decisions shouldn't be made from the fleet average alone. The report suggests tracking the share of VMs above 80% CPU instead.

## Data and licence

The data is a curated subset of the [Azure Public Dataset V2](https://github.com/Azure/AzurePublicDataset) and isn't redistributed here. See `SOURCES.md` and `challenge_data/DATA_CARD.md` for attribution. Code is released under the licence in `LICENSE`.
