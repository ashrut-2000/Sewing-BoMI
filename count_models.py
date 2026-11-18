import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
from scipy.optimize import minimize
from scipy.special import gammaln, logsumexp
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests

NODES, WEIGHTS = np.polynomial.hermite.hermgauss(25)


def log_pmf(y, mu, theta):
    if theta is None:  # Poisson
        return y * np.log(mu) - mu - gammaln(y + 1)
    return (gammaln(y + theta) - gammaln(theta) - gammaln(y + 1)
            + theta * np.log(theta / (theta + mu)) + y * np.log(mu / (theta + mu)))


# GLMM with a random intercept per participant.
# The random intercept is integrated out with adaptive Gauss-Hermite quadrature.
def neg_loglik(params, X, y, pid, poisson):
    n, k = pid.max() + 1, X.shape[1]
    eta = X @ params[:k]
    sd = np.exp(params[k])
    theta = None if poisson else np.exp(params[k + 1])

    def log_joint(b):
        return (np.bincount(pid, log_pmf(y, np.exp(eta + b[pid]), theta), n)
                - 0.5 * (b / sd) ** 2 - np.log(sd * np.sqrt(2 * np.pi)))

    def info(b):
        mu = np.exp(eta + b[pid])
        w = mu if poisson else theta * mu * (y + theta) / (theta + mu) ** 2
        return np.bincount(pid, w, n) + 1 / sd ** 2

    b = np.zeros(n)
    for _ in range(100):
        mu = np.exp(eta + b[pid])
        resid = (y - mu) if poisson else theta * (y - mu) / (theta + mu)
        step = np.clip((np.bincount(pid, resid, n) - b / sd ** 2) / info(b), -5, 5)
        b += step
        if np.abs(step).max() < 1e-10:
            break

    scale = np.sqrt(2 / info(b))
    terms = [np.log(w) + x ** 2 + np.log(scale) + log_joint(b + scale * x) for x, w in zip(NODES, WEIGHTS)]
    return -logsumexp(terms, axis=0).sum()


def fit_glmm(X, y, pid, poisson):
    start = np.r_[np.linalg.lstsq(X, np.log(y + 0.5), rcond=None)[0], 0.0]
    if not poisson:
        start = np.r_[start, 1.0]
    res = minimize(neg_loglik, start, args=(X, y, pid, poisson), method="BFGS",
                   options=dict(gtol=1e-7, maxiter=10000))
    return res.x, -res.fun


def numerical_hessian(f, x, h=1e-4):
    n = len(x)
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            e_i, e_j = np.eye(n)[i] * h, np.eye(n)[j] * h
            H[i, j] = H[j, i] = (f(x + e_i + e_j) - f(x + e_i - e_j) - f(x - e_i + e_j) + f(x - e_i - e_j)) / (4 * h * h)
    return H


# Likelihood-ratio tests for Group, Trial and Group x Trial (each term dropped from the full model),
# and the BoMI-to-Pedal rate ratio averaged over trials
def analyze_counts(data, outcome, label):
    data = data.dropna(subset=[outcome]).reset_index(drop=True)
    y = data[outcome].to_numpy(float)
    pid = pd.factorize(data["pid"])[0]
    design = patsy.dmatrix("C(group, Sum) * C(trial, Sum)", data, return_type="dataframe")
    term_columns = list(design.design_info.term_slices.values())[1:]
    X = design.to_numpy()

    # Negative binomial; if its dispersion goes to the Poisson limit, the Poisson GLMM is used
    nb_params, nb_ll = fit_glmm(X, y, pid, poisson=False)
    pois_params, pois_ll = fit_glmm(X, y, pid, poisson=True)
    poisson = pois_ll >= nb_ll
    params, ll_full = (pois_params, pois_ll) if poisson else (nb_params, nb_ll)

    family = "Poisson (NB dispersion at its Poisson limit)" if poisson else f"negative binomial, theta = {np.exp(params[-1]):.3f}"
    print(f"\n{label}  ({pid.max() + 1} participants, {len(y)} trials; {family})")

    p_values = {}
    for cols, name in zip(term_columns, ["Group", "Trial", "Group x Trial"]):
        keep = np.ones(X.shape[1], bool)
        keep[cols] = False
        _, ll_reduced = fit_glmm(X[:, keep], y, pid, poisson)
        stat, df = 2 * (ll_full - ll_reduced), (~keep).sum()
        p_values[name] = chi2.sf(stat, df)
        print(f"  {name:14s} chi2({df}) = {stat:.2f}, p = {p_values[name]:.4f}")

    cov = np.linalg.inv(numerical_hessian(lambda v: neg_loglik(v, X, y, pid, poisson), params))
    g = term_columns[0].start
    est, se = 2 * params[g], 2 * np.sqrt(cov[g, g])
    print(f"  BoMI-to-Pedal rate ratio = {np.exp(est):.3f} (95% CI: {np.exp(est - 1.96 * se):.3f}-{np.exp(est + 1.96 * se):.3f})")
    return p_values


# NB GLM for Transfer Trial 1 (theta estimated by maximum likelihood)
def nb_glm_trial1(data):
    X = sm.add_constant((data["group"] == "BoMI").astype(float))
    alpha = sm.NegativeBinomial(data["errors"], X).fit(disp=0).params["alpha"]
    fit = sm.GLM(data["errors"], X, family=sm.families.NegativeBinomial(alpha=alpha)).fit()
    b, se = fit.params["group"], fit.bse["group"]
    return np.exp(b), np.exp(b - 1.96 * se), np.exp(b + 1.96 * se), fit.pvalues["group"]


def describe(y, label):
    y = y.dropna()
    print(f"{label}: mean = {y.mean():.2f}, variance = {y.var():.2f}, zeros = {100 * (y == 0).mean():.1f}%")


# ---------------- Training ----------------
train = pd.read_excel("combined_training_data.xlsx", sheet_name="Training")
train = train.rename(columns={"participant id": "pid", "P.F lift error": "pf_err", "needle lift error": "nl_err"})

describe(train["error"], "Training errors")
describe(train["pf_err"], "Presser-foot lift errors")

p_train = {}
for outcome, label in [("error", "Training errors"), ("pf_err", "Presser-foot lift errors"), ("nl_err", "Needle-lift errors")]:
    p_train[label] = analyze_counts(train, outcome, label)

# ---------------- Transfer ----------------
transfer = pd.read_csv("Transfer.csv").rename(columns={"participant_id": "pid"})
trial1 = transfer[transfer["trial"] == 1].reset_index(drop=True)

print()
describe(trial1["errors"], "Transfer Trial 1 errors")
rr, lo, hi, p_trial1 = nb_glm_trial1(trial1)
print(f"Transfer Trial 1 NB GLM: rate ratio = {rr:.3f} (95% CI: {lo:.3f}-{hi:.3f}), p = {p_trial1:.4f}")

loo = pd.DataFrame([nb_glm_trial1(trial1.drop(i)) for i in trial1.index],
                   index=trial1["pid"], columns=["RR", "lower", "upper", "p"])
worst = loo["p"].idxmax()
print(f"Leave-one-participant-out: RR {loo.RR.min():.3f}-{loo.RR.max():.3f}, p {loo.p.min():.4f}-{loo.p.max():.4f}; "
      f"least favorable without {worst}: RR = {loo.RR[worst]:.3f} (95% CI: {loo.lower[worst]:.3f}-{loo.upper[worst]:.3f}), p = {loo.p[worst]:.4f}")

p_transfer = analyze_counts(transfer, "errors", "Transfer errors, Trials 1-3")

# ---------------- Holm correction ----------------
# p values of the LMM effects (from JASP), needed to complete each family
lmm_training = {"Sewing time: Group": 0.3566214, "Sewing time: Trial": 0.01056185, "Sewing time: Group x Trial": 0.000197383,
                "Speed: Group": 0.6276760, "Speed: Trial": 3.7e-32, "Speed: Group x Trial": 0.007624713}
lmm_transfer = {"Trial 1 time: Group": 0.5170565,
                "Time: Group": 0.6948627, "Time: Trial": 0.0602060, "Time: Group x Trial": 0.0046061}

families = {
    "training (15 tests)": {**{f"{o}: {t}": p for o, d in p_train.items() for t, p in d.items()}, **lmm_training},
    "transfer (8 tests)": {"Trial 1 errors: Group": p_trial1,
                           **{f"Errors: {t}": p for t, p in p_transfer.items()}, **lmm_transfer},
}
for name, tests in families.items():
    adjusted = multipletests(list(tests.values()), method="holm")[1]
    print(f"\nHolm-adjusted p values, {name}:")
    for (test, raw), adj in zip(tests.items(), adjusted):
        print(f"  {test:45s} p = {raw:.4f}   Holm p = {adj:.4f}")
