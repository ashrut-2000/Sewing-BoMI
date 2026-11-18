import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from scipy.optimize import minimize
from scipy.special import gammaln, logsumexp
from statsmodels.stats.multitest import multipletests

NODES, WEIGHTS = np.polynomial.hermite.hermgauss(25)

data = pd.read_csv("Transfer.csv").rename(columns={"participant_id": "pid", "time_s": "time"})
data["ln_time"] = np.log(data["time"])
trial1 = data[data["trial"] == 1].reset_index(drop=True)


# ---------------- Descriptives ----------------
print("Trial 1, mean ± SD (median, range):")
for g, d in trial1.groupby("group"):
    print(f"  {g:5s} time = {d.time.mean():.2f} ± {d.time.std():.2f} s   "
          f"errors = {d.errors.mean():.2f} ± {d.errors.std():.2f} (median {d.errors.median():g}, range {d.errors.min()}-{d.errors.max()})")
y = trial1["errors"]
print(f"  Trial 1 errors overall: mean = {y.mean():.2f}, variance = {y.var():.2f}, zeros = {100 * (y == 0).mean():.1f}%")

print("\nMeans across transfer trials:")
print(data.pivot_table(index="trial", columns="group", values=["errors", "time"]).round(2).to_string())


# ---------------- Trial 1: completion time (linear model on ln time) ----------------
raw = smf.ols("time ~ group", trial1).fit()
log = smf.ols("ln_time ~ C(group, Treatment('Pedal'))", trial1).fit()
term = "C(group, Treatment('Pedal'))[T.BoMI]"
lo, hi = log.conf_int().loc[term]
print(f"\nTrial 1 time: residual skewness raw = {stats.skew(raw.resid, bias=False):.2f}, log = {stats.skew(log.resid, bias=False):.2f}")
print(f"Trial 1 time: BoMI-to-Pedal ratio = {np.exp(log.params[term]):.3f} "
      f"(95% CI: {np.exp(lo):.3f}-{np.exp(hi):.3f}), p = {log.pvalues[term]:.4f}")
p_tests = {"Trial 1 time: Group": log.pvalues[term]}


# ---------------- Trial 1: errors (negative-binomial GLM) ----------------
def nb_glm_trial1(d):
    X = sm.add_constant((d["group"] == "BoMI").astype(float))
    alpha = sm.NegativeBinomial(d["errors"], X).fit(disp=0).params["alpha"]
    fit = sm.GLM(d["errors"], X, family=sm.families.NegativeBinomial(alpha=alpha)).fit()
    b, se = fit.params["group"], fit.bse["group"]
    return np.exp(b), np.exp(b - 1.96 * se), np.exp(b + 1.96 * se), fit.pvalues["group"]


rr, lo, hi, p = nb_glm_trial1(trial1)
print(f"Trial 1 errors: BoMI-to-Pedal rate ratio = {rr:.3f} (95% CI: {lo:.3f}-{hi:.3f}), p = {p:.4f}")
p_tests["Trial 1 errors: Group"] = p

loo = pd.DataFrame([nb_glm_trial1(trial1.drop(i)) for i in trial1.index],
                   index=trial1["pid"], columns=["RR", "lower", "upper", "p"])
worst = loo["p"].idxmax()
print(f"Leave-one-participant-out: RR {loo.RR.min():.3f}-{loo.RR.max():.3f}, p {loo.p.min():.4f}-{loo.p.max():.4f}; "
      f"least favorable without {worst}: RR = {loo.RR[worst]:.3f} (95% CI: {loo.lower[worst]:.3f}-{loo.upper[worst]:.3f}), p = {loo.p[worst]:.4f}")


# ---------------- Trials 1-3: completion time (LMM on ln time) ----------------
# With complete, balanced data, the random-intercept LMM F tests equal the split-plot ANOVA F tests
def split_plot_anova(d, y):
    grand = d[y].mean()
    group_m = d.groupby("group")[y].transform("mean")
    trial_m = d.groupby("trial")[y].transform("mean")
    cell_m = d.groupby(["group", "trial"])[y].transform("mean")
    subj_m = d.groupby("pid")[y].transform("mean")
    n_subj, n_group, n_trial = d.pid.nunique(), d.group.nunique(), d.trial.nunique()

    ss = {"Group": ((group_m - grand) ** 2).sum(),
          "Trial": ((trial_m - grand) ** 2).sum(),
          "Group x Trial": ((cell_m - group_m - trial_m + grand) ** 2).sum()}
    ss_subj, df_subj = ((subj_m - group_m) ** 2).sum(), n_subj - n_group
    ss_err, df_err = ((d[y] - cell_m - subj_m + group_m) ** 2).sum(), (n_subj - n_group) * (n_trial - 1)
    df = {"Group": n_group - 1, "Trial": n_trial - 1, "Group x Trial": (n_group - 1) * (n_trial - 1)}

    p_values = {}
    for name in ss:
        df2, ms_err = (df_subj, ss_subj / df_subj) if name == "Group" else (df_err, ss_err / df_err)
        F = (ss[name] / df[name]) / ms_err
        p_values[name] = stats.f.sf(F, df[name], df2)
        print(f"  {name:14s} F({df[name]},{df2}) = {F:.2f}, p = {p_values[name]:.4f}")
    return p_values


print("\nTrials 1-3, completion time (log-time LMM):")
for name, p in split_plot_anova(data, "ln_time").items():
    p_tests[f"Time: {name}"] = p


# ---------------- Trials 1-3: errors (negative-binomial GLMM) ----------------
def log_pmf(y, mu, theta):
    return (gammaln(y + theta) - gammaln(theta) - gammaln(y + 1)
            + theta * np.log(theta / (theta + mu)) + y * np.log(mu / (theta + mu)))


# Random intercept per participant, integrated out with adaptive Gauss-Hermite quadrature
def neg_loglik(params, X, y, pid):
    n, k = pid.max() + 1, X.shape[1]
    eta = X @ params[:k]
    sd, theta = np.exp(params[k]), np.exp(params[k + 1])

    def log_joint(b):
        return (np.bincount(pid, log_pmf(y, np.exp(eta + b[pid]), theta), n)
                - 0.5 * (b / sd) ** 2 - np.log(sd * np.sqrt(2 * np.pi)))

    def info(b):
        mu = np.exp(eta + b[pid])
        return np.bincount(pid, theta * mu * (y + theta) / (theta + mu) ** 2, n) + 1 / sd ** 2

    b = np.zeros(n)
    for _ in range(100):
        mu = np.exp(eta + b[pid])
        step = np.clip((np.bincount(pid, theta * (y - mu) / (theta + mu), n) - b / sd ** 2) / info(b), -5, 5)
        b += step
        if np.abs(step).max() < 1e-10:
            break

    scale = np.sqrt(2 / info(b))
    terms = [np.log(w) + x ** 2 + np.log(scale) + log_joint(b + scale * x) for x, w in zip(NODES, WEIGHTS)]
    return -logsumexp(terms, axis=0).sum()


def fit_nb_glmm(X, y, pid):
    start = np.r_[np.linalg.lstsq(X, np.log(y + 0.5), rcond=None)[0], 0.0, 1.0]
    res = minimize(neg_loglik, start, args=(X, y, pid), method="BFGS", options=dict(gtol=1e-7, maxiter=10000))
    return -res.fun


print("\nTrials 1-3, errors (negative-binomial GLMM):")
y = data["errors"].to_numpy(float)
pid = pd.factorize(data["pid"])[0]
design = patsy.dmatrix("C(group, Sum) * C(trial, Sum)", data, return_type="dataframe")
X = design.to_numpy()
ll_full = fit_nb_glmm(X, y, pid)
for cols, name in zip(list(design.design_info.term_slices.values())[1:], ["Group", "Trial", "Group x Trial"]):
    keep = np.ones(X.shape[1], bool)
    keep[cols] = False
    stat, df = 2 * (ll_full - fit_nb_glmm(X[:, keep], y, pid)), (~keep).sum()
    p_tests[f"Errors: {name}"] = stats.chi2.sf(stat, df)
    print(f"  {name:14s} chi2({df}) = {stat:.2f}, p = {p_tests[f'Errors: {name}']:.4f}")


# ---------------- Holm correction across the 8 transfer tests ----------------
adjusted = multipletests(list(p_tests.values()), method="holm")[1]
print("\nHolm-adjusted p values (8 transfer tests):")
for (test, raw_p), adj in zip(p_tests.items(), adjusted):
    print(f"  {test:25s} p = {raw_p:.4f}   Holm p = {adj:.4f}")
