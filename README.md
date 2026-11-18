# Body-Machine Interface for Sewing-Machine Control: Data and Analysis

Data, analysis and controller files for:

> A. Aryal, R. Ranganathan, and R. Mukherjee, "Design and Evaluation of a Body-Machine Interface as an Alternative Control Paradigm for Pedal-based Sewing Machines."

Twenty-four novice participants (12 BoMI, 12 Pedal) completed 10 training trials of the Blum's test, 3 trials of a transfer task, and the NASA-TLX. Participant IDs (P01–P24) are the only identifiers; no personal information is included. Column definitions are in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Files

| File | Contents |
|---|---|
| `combined_training_data.xlsx` | Training data, one row per participant per trial (240 rows) |
| `Transfer.csv` | Transfer data, one row per participant per trial (72 rows) |
| `NASATLX.csv` | NASA-TLX ratings, one row per participant (24 rows) |
| `LMM_training_time.jasp` | Linear mixed model, training completion time (log scale) |
| `LMM_percent_time_sewing.jasp` | Linear mixed model, percentage of time sewing |
| `LMM_mean_speed.jasp` | Linear mixed model, mean active sewing speed (log scale) |
| `count_models.py` | Mixed models for training errors, presser-foot lift errors and needle-lift errors; transfer error models; Holm correction |
| `transfer_analysis.py` | All transfer analyses (Trial 1 and Trials 1–3) with Holm correction |
| `nasa_tlx.py` | NASA-TLX Mann–Whitney U tests, Holm correction and Welch 95% CIs |
| `controller.ino` | Arduino UNO R4 Minima firmware: receives voltage commands over serial (115200 baud) and outputs the control voltage to the sewing-machine control board (12-bit DAC, clipped to 1.10–4.40 V, 0.3 s watchdog) |

## How to reproduce the results

**JASP files:** open in JASP. Each file contains its data and the fitted model.

**Python scripts:** install the packages, then run each script from the folder that contains the data files.

```bash
pip install numpy pandas scipy statsmodels patsy openpyxl
python count_models.py
python transfer_analysis.py
python nasa_tlx.py
```

Tested with Python 3.13, numpy 2.5, pandas 3.0, scipy 1.18, statsmodels 0.15, patsy 1.0 and openpyxl 3.1.

**Controller:** open `controller.ino` in the Arduino IDE and upload it to an Arduino UNO R4 Minima.
