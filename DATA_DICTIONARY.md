# Data Dictionary

All participants were novices with no prior sewing experience. `group` is the control interface: `BoMI` (trunk-controlled body-machine interface) or `Pedal` (conventional foot pedal).

## combined_training_data.xlsx (sheet "Training")

One row per participant per training trial (24 participants × 10 trials = 240 rows). Blank cells: participant P21 (Pedal), whose voltage log was corrupted, has no values for the columns marked *voltage log*.

| Column | Description | Units / values |
|---|---|---|
| `participant id` | Participant identifier | P01–P24 |
| `group` | Control interface | BoMI, Pedal |
| `trial` | Training trial number | 1–10 |
| `time` | Completion time, stopwatch, first to final stitch | seconds |
| `ln_time` | Natural log of `time` | — |
| `error` | Needle perforations falling entirely outside the template boundary lines | count |
| `P.F lift error` | Excess presser-foot lifts beyond the eight required lifts (*voltage log*) | count |
| `needle lift error` | Unintended needle lifts; the template requires none (*voltage log*) | count |
| `needle %` | Time in the presser-foot-and-needle-lift state (*voltage log*) | % of trial time |
| `P.F lift %` | Time in the presser-foot-lift state (*voltage log*) | % of trial time |
| `dead zone %` | Time in the dead zone, presser foot down and needle stationary (*voltage log*) | % of trial time |
| `minimum speed %` | Time in the minimum-speed zone (*voltage log*) | % of trial time |
| `ramp %` | Time in the proportional-speed zone (*voltage log*) | % of trial time |
| `other %` | Time in the maximum-speed zone; 0 in all trials (*voltage log*) | % of trial time |
| `percent time sewing` | Time with the needle moving (minimum-speed + proportional-speed + maximum-speed zones) (*voltage log*) | % of trial time |
| `mean active speed (rpm)` | Mean sewing speed while the needle was moving, converted from voltage using the machine's voltage–speed characterization (*voltage log*) | RPM |
| `ln_speed` | Natural log of `mean active speed (rpm)` | — |

The six time-distribution columns (`needle %` through `other %`) sum to 100% for each trial.

## Transfer.csv

One row per participant per transfer trial (24 participants × 3 trials = 72 rows).

| Column | Description | Units / values |
|---|---|---|
| `participant_id` | Participant identifier | P01–P24 |
| `group` | Control interface | BoMI, Pedal |
| `trial` | Transfer trial number | 1–3 |
| `time_s` | Completion time, stopwatch, first to final stitch | seconds |
| `errors` | Needle perforations falling entirely outside the template boundary lines | count |
| `ln_time` | Natural log of `time_s` | — |

## NASATLX.csv

One row per participant (24 rows), collected after all trials were completed.

| Column | Description | Units / values |
|---|---|---|
| `participant_id` | Participant identifier | P01–P24 |
| `group` | Control interface | BoMI, Pedal |
| `mental_demand` | NASA-TLX mental demand | 0–100, steps of 5 |
| `physical_demand` | NASA-TLX physical demand | 0–100, steps of 5 |
| `temporal_demand` | NASA-TLX temporal demand | 0–100, steps of 5 |
| `performance` | NASA-TLX performance | 0–100, steps of 5 |
| `effort` | NASA-TLX effort | 0–100, steps of 5 |
| `frustration` | NASA-TLX frustration | 0–100, steps of 5 |

Lower NASA-TLX values indicate lower perceived workload.
