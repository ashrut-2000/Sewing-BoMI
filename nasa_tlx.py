import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

data = pd.read_csv("NASATLX.csv")
subscales = ["mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration"]

rows = []
for s in subscales:
    bomi = data.loc[data["group"] == "BoMI", s]
    pedal = data.loc[data["group"] == "Pedal", s]

    # Mann-Whitney U test (normal approximation with continuity correction)
    u, p = stats.mannwhitneyu(bomi, pedal, alternative="two-sided", method="asymptotic")

    # BoMI - Pedal mean difference with Welch 95% CI
    welch = stats.ttest_ind(bomi, pedal, equal_var=False)
    ci = welch.confidence_interval(0.95)

    rows.append({"subscale": s,
                 "BoMI mean": bomi.mean(), "Pedal mean": pedal.mean(),
                 "U": u, "p": p,
                 "mean diff": bomi.mean() - pedal.mean(), "CI low": ci.low, "CI high": ci.high})

results = pd.DataFrame(rows)
results["Holm p"] = multipletests(results["p"], method="holm")[1]

pd.set_option("display.width", 200)
print(results.round({"BoMI mean": 2, "Pedal mean": 2, "U": 1, "p": 4, "Holm p": 4,
                     "mean diff": 2, "CI low": 2, "CI high": 2}).to_string(index=False))
