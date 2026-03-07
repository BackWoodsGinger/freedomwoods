"""
Manufacturing/quality analytics: descriptive stats, SPC, capability, hypothesis tests.
"""
import math
import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def descriptive_stats(series):
    """Single variable: mean, stdev, min, max, quartiles, N, etc."""
    s = pd.Series(series).dropna()
    if s.empty or not np.issubdtype(s.dtype, np.number):
        return None
    q = s.quantile([0, 0.25, 0.5, 0.75, 1.0])
    n = len(s)
    return {
        "N": n,
        "N_missing": series.size - n,
        "Mean": float(s.mean()),
        "StDev": float(s.std(ddof=1)) if n > 1 else 0.0,
        "Variance": float(s.var(ddof=1)) if n > 1 else 0.0,
        "Min": float(s.min()),
        "Q1": float(q.iloc[1]),
        "Median": float(q.iloc[2]),
        "Q3": float(q.iloc[3]),
        "Max": float(s.max()),
        "Range": float(s.max() - s.min()),
        "IQR": float(q.iloc[3] - q.iloc[1]),
        "SE_Mean": float(s.sem()) if n > 0 else 0.0,
        "Skewness": float(s.skew()) if n > 2 else None,
        "Kurtosis": float(s.kurtosis()) if n > 3 else None,
    }


def descriptive_stats_table(df, columns=None):
    """Descriptive statistics for multiple numeric columns."""
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
    if not cols:
        return {}
    return {col: descriptive_stats(df[col]) for col in cols if descriptive_stats(df[col])}


# ---------------------------------------------------------------------------
# Control charts (SPC)
# ---------------------------------------------------------------------------

def _control_constants(n):
    """Constants for X-bar R/S charts (n = subgroup size)."""
    # A2, D3, D4 for R chart; A3, B3, B4 for S chart
    constants = {
        2: (1.880, 0, 3.267, 2.659, 0, 3.267),
        3: (1.023, 0, 2.574, 1.954, 0, 2.568),
        4: (0.729, 0, 2.282, 1.628, 0, 2.266),
        5: (0.577, 0, 2.114, 1.427, 0, 2.089),
        6: (0.483, 0, 2.004, 1.287, 0.030, 1.970),
        7: (0.419, 0.076, 1.924, 1.182, 0.118, 1.882),
        8: (0.373, 0.136, 1.864, 1.099, 0.185, 1.815),
        9: (0.337, 0.184, 1.816, 1.032, 0.239, 1.761),
        10: (0.308, 0.223, 1.777, 0.975, 0.284, 1.716),
    }
    return constants.get(n, (3 / math.sqrt(n), max(0, 1 - 3 / (1.128 * math.sqrt(n))), 1 + 3 / (1.128 * math.sqrt(n)), 3 / (0.921 * math.sqrt(n)), 0, 2))  # approx


def xbar_r_chart(data, subgroup_size=5):
    """
    X-bar and R chart. data: list/array of values in order; subgroup_size: n.
    Returns center lines, UCL, LCL for X-bar and R.
    """
    data = np.asarray(data, dtype=float)
    n = int(subgroup_size)
    if n < 2 or len(data) % n != 0:
        return None
    subgroups = data.reshape(-1, n)
    xbars = subgroups.mean(axis=1)
    ranges = subgroups.max(axis=1) - subgroups.min(axis=1)
    xbar_center = float(xbars.mean())
    r_center = float(ranges.mean())
    A2, D3, D4, *_ = _control_constants(n)
    return {
        "chart": "X-bar R",
        "subgroup_size": n,
        "Xbar": {
            "center": xbar_center,
            "UCL": xbar_center + A2 * r_center,
            "LCL": xbar_center - A2 * r_center,
            "values": xbars.tolist(),
        },
        "R": {
            "center": r_center,
            "UCL": D4 * r_center,
            "LCL": D3 * r_center,
            "values": ranges.tolist(),
        },
    }


def xbar_s_chart(data, subgroup_size=5):
    """X-bar and S chart (use S instead of R for subgroup size > 10 or preference)."""
    data = np.asarray(data, dtype=float)
    n = int(subgroup_size)
    if n < 2 or len(data) % n != 0:
        return None
    subgroups = data.reshape(-1, n)
    xbars = subgroups.mean(axis=1)
    stds = subgroups.std(axis=1, ddof=1)
    xbar_center = float(xbars.mean())
    s_center = float(stds.mean())
    A2, D3, D4, A3, B3, B4 = _control_constants(n)
    return {
        "chart": "X-bar S",
        "subgroup_size": n,
        "Xbar": {
            "center": xbar_center,
            "UCL": xbar_center + A3 * s_center,
            "LCL": xbar_center - A3 * s_center,
            "values": xbars.tolist(),
        },
        "S": {
            "center": s_center,
            "UCL": B4 * s_center,
            "LCL": B3 * s_center,
            "values": stds.tolist(),
        },
    }


def i_mr_chart(data):
    """Individual (I) and Moving Range (MR) chart for individual measurements."""
    data = np.asarray(data, dtype=float)
    if len(data) < 2:
        return None
    mr = np.abs(np.diff(data))
    mr_center = float(mr.mean())
    x_center = float(np.mean(data))
    # E2 ≈ 2.66 for n=2 moving range
    return {
        "chart": "I-MR",
        "I": {
            "center": x_center,
            "UCL": x_center + 2.66 * mr_center,
            "LCL": x_center - 2.66 * mr_center,
            "values": data.tolist(),
        },
        "MR": {
            "center": mr_center,
            "UCL": 3.267 * mr_center,
            "LCL": 0,
            "values": [float(mr[0])] + mr.tolist(),  # align length with I
        },
    }


def p_chart(series, n_per_sample):
    """P-chart for proportion defective. series: 0/1 or counts; n_per_sample: sample size (constant)."""
    p = np.asarray(series, dtype=float)
    n = int(n_per_sample)
    pbar = p.mean()
    ucl = pbar + 3 * math.sqrt(pbar * (1 - pbar) / n)
    lcl = pbar - 3 * math.sqrt(pbar * (1 - pbar) / n)
    return {
        "chart": "P",
        "center": float(pbar),
        "UCL": float(min(1, ucl)),
        "LCL": float(max(0, lcl)),
        "values": p.tolist(),
    }


def c_chart(series):
    """C-chart for count of defects per unit (constant area/volume)."""
    c = np.asarray(series, dtype=float)
    cbar = c.mean()
    ucl = cbar + 3 * math.sqrt(cbar)
    lcl = cbar - 3 * math.sqrt(cbar)
    return {
        "chart": "C",
        "center": float(cbar),
        "UCL": float(max(0, ucl)),
        "LCL": float(max(0, lcl)),
        "values": c.tolist(),
    }


# ---------------------------------------------------------------------------
# Process capability
# ---------------------------------------------------------------------------

def capability_indices(series, usl, lsl):
    """
    Cp, Cpk, Pp, Ppk. usl/lsl: upper/lower spec limits (None if one-sided).
    Uses overall stdev for Pp/Ppk and within (or pooled) for Cp/Cpk; here we use
    same stdev for both (sample) so Cp≈Pp, Cpk≈Ppk unless we have subgroups.
    """
    s = pd.Series(series).dropna()
    if s.empty or not np.issubdtype(s.dtype, np.number):
        return None
    mean = float(s.mean())
    std = float(s.std(ddof=1)) if len(s) > 1 else 0.0
    n = len(s)

    if usl is None and lsl is None:
        return None
    if usl is not None and lsl is not None and float(lsl) >= float(usl):
        return None

    usl = float(usl) if usl is not None else None
    lsl = float(lsl) if lsl is not None else None

    # Cp/Cpk (often use within-subgroup sigma; here use sample sigma as proxy)
    if std <= 0:
        cp = cpk = pp = ppk = None
    else:
        if usl is not None and lsl is not None:
            cp = (usl - lsl) / (6 * std)
            cpk = min((usl - mean) / (3 * std), (mean - lsl) / (3 * std))
        elif usl is not None:
            cp = None
            cpk = (usl - mean) / (3 * std)
        else:
            cp = None
            cpk = (mean - lsl) / (3 * std)
        pp = (usl - lsl) / (6 * std) if (usl and lsl) else None
        ppk = min((usl - mean) / (3 * std), (mean - lsl) / (3 * std)) if (usl and lsl) else cpk

    return {
        "N": n,
        "Mean": mean,
        "StDev": std,
        "USL": usl,
        "LSL": lsl,
        "Cp": round(cp, 4) if cp is not None else None,
        "Cpk": round(cpk, 4) if cpk is not None else None,
        "Pp": round(pp, 4) if pp is not None else None,
        "Ppk": round(ppk, 4) if ppk is not None else None,
    }


# ---------------------------------------------------------------------------
# Hypothesis tests
# ---------------------------------------------------------------------------

def one_sample_t(series, mu0):
    """One-sample t-test: H0 mean = mu0."""
    s = pd.Series(series).dropna()
    if s.empty or len(s) < 2 or not np.issubdtype(s.dtype, np.number):
        return None
    t_stat, p_val = stats.ttest_1samp(s, float(mu0))
    return {
        "test": "One-Sample T",
        "mu0": float(mu0),
        "N": len(s),
        "Mean": float(s.mean()),
        "StDev": float(s.std(ddof=1)),
        "SE_Mean": float(s.sem()),
        "T": float(t_stat),
        "P": float(p_val),
    }


def two_sample_t(series1, series2, equal_var=True):
    """Two-sample t-test (independent); H0: means equal."""
    a = np.asarray(series1, dtype=float)
    b = np.asarray(series2, dtype=float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return None
    t_stat, p_val = stats.ttest_ind(a, b, equal_var=equal_var)
    return {
        "test": "Two-Sample T",
        "N1": len(a),
        "N2": len(b),
        "Mean1": float(np.mean(a)),
        "Mean2": float(np.mean(b)),
        "StDev1": float(np.std(a, ddof=1)),
        "StDev2": float(np.std(b, ddof=1)),
        "T": float(t_stat),
        "P": float(p_val),
    }


def paired_t(series1, series2):
    """Paired t-test; H0: mean(diff) = 0."""
    a = np.asarray(series1, dtype=float)
    b = np.asarray(series2, dtype=float)
    if len(a) != len(b) or len(a) < 2:
        return None
    t_stat, p_val = stats.ttest_rel(a, b)
    diff = a - b
    return {
        "test": "Paired T",
        "N": len(a),
        "Mean_diff": float(np.mean(diff)),
        "StDev_diff": float(np.std(diff, ddof=1)),
        "T": float(t_stat),
        "P": float(p_val),
    }


def one_way_anova(groups_dict):
    """One-way ANOVA. groups_dict: { 'group_name': [values], ... }."""
    groups = [np.asarray(v, dtype=float)[~np.isnan(np.asarray(v, dtype=float))] for v in groups_dict.values()]
    names = list(groups_dict.keys())
    if any(len(g) < 2 for g in groups) or len(groups) < 2:
        return None
    f_stat, p_val = stats.f_oneway(*groups)
    return {
        "test": "One-Way ANOVA",
        "groups": names,
        "F": float(f_stat),
        "P": float(p_val),
    }


def chi_square_test(observed_2d):
    """
    Chi-square test of independence. observed_2d: 2D list/array (contingency table).
    """
    obs = np.asarray(observed_2d)
    if obs.size < 4 or obs.min() < 0:
        return None
    chi2, p, dof, expected = stats.chi2_contingency(obs)
    return {
        "test": "Chi-Square",
        "Chi2": float(chi2),
        "DF": int(dof),
        "P": float(p),
    }


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

def simple_linear_regression(x, y):
    """Simple linear regression: y = b0 + b1*x. Returns coefficients, R-sq, SE, ANOVA."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return None
    slope, intercept, r, p, se = stats.linregress(x, y)
    yhat = intercept + slope * x
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_sq = 1 - ss_res / ss_tot if ss_tot != 0 else 0
    n, k = len(x), 2
    adj_r_sq = 1 - (1 - r_sq) * (n - 1) / (n - k) if n > k else r_sq
    return {
        "model": "Y = b0 + b1*X",
        "Intercept": float(intercept),
        "Slope": float(slope),
        "R_sq": round(r_sq, 4),
        "Adj_R_sq": round(adj_r_sq, 4),
        "P_value": float(p),
        "N": n,
    }


def run_all_descriptive(df, columns=None):
    """Convenience: run descriptive stats on numeric columns."""
    return descriptive_stats_table(df, columns=columns)


def run_capability(df, column, usl=None, lsl=None):
    """Convenience: capability for one column."""
    return capability_indices(df[column], usl=usl, lsl=lsl)
