"""Statistical toolkit: concentration, distributions, and inference.

Everything here is deliberately small and explicit rather than leaning on a
statistics package, because the quantities we need (Herfindahl indices over
revenue shares, Gini on a truncated firm list, Pareto tail fits) are not
one-liners in scipy.

All functions are pure: they take arrays/Series and return plain Python or
NumPy values, so the analysis modules stay declarative.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Concentration
# ---------------------------------------------------------------------------


def shares(values) -> np.ndarray:
    """Normalise a vector to shares that sum to 1 (ignoring negatives)."""
    v = pd.Series(values, dtype="float64").fillna(0.0)
    v = v.clip(lower=0.0)
    total = v.sum()
    if total <= 0:
        return np.zeros(len(v))
    return (v / total).to_numpy()


def herfindahl(values) -> float:
    """Herfindahl-Hirschman index on shares (0..1). Higher = more concentrated."""
    s = shares(values)
    if len(s) == 0:
        return float("nan")
    return float(np.sum(s ** 2))


def hhi_points(values) -> float:
    """HHI on the 0-10,000 scale used by antitrust practice."""
    return herfindahl(values) * 10_000.0


def gini(values) -> float:
    """Gini coefficient of a non-negative vector (0 = equal, ->1 = one owner)."""
    v = np.sort(pd.Series(values, dtype="float64").fillna(0.0).clip(lower=0.0).to_numpy())
    n = len(v)
    if n == 0 or v.sum() == 0:
        return float("nan")
    # Standard formula on the sorted vector.
    idx = np.arange(1, n + 1)
    return float((2 * (idx * v).sum()) / (n * v.sum()) - (n + 1) / n)


def top_k_share(values, k: int) -> float:
    """Share of the total held by the k largest entries."""
    v = pd.Series(values, dtype="float64").dropna().clip(lower=0.0)
    if len(v) == 0:
        return float("nan")
    k = max(1, min(int(k), len(v)))
    return float(v.nlargest(k).sum() / v.sum())


def firms_for_share(values, target: float = 0.5) -> int:
    """How many of the largest firms are needed to reach `target` of the total."""
    v = pd.Series(values, dtype="float64").dropna().clip(lower=0.0).sort_values(ascending=False)
    if len(v) == 0 or v.sum() == 0:
        return 0
    cum = v.cumsum() / v.sum()
    idx = np.searchsorted(cum.to_numpy(), target) + 1
    return int(min(idx, len(v)))


def lorenz_curve(values) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative share of the bottom x% of firms (sorted ascending)."""
    v = np.sort(pd.Series(values, dtype="float64").dropna().clip(lower=0.0).to_numpy())
    n = len(v)
    if n == 0 or v.sum() == 0:
        return np.array([0.0]), np.array([0.0])
    cum = np.cumsum(v) / v.sum()
    return np.linspace(0, 1, n + 1), np.concatenate([[0.0], cum])


def pareto_threshold_count(values, threshold: float) -> int:
    """How many firms exceed a given revenue threshold."""
    v = pd.Series(values, dtype="float64").dropna()
    return int((v >= threshold).sum())


# ---------------------------------------------------------------------------
# Distribution shape
# ---------------------------------------------------------------------------


def describe(series) -> dict:
    """Extended descriptive statistics for a numeric series."""
    s = pd.Series(series, dtype="float64").dropna()
    if len(s) == 0:
        return {}
    n = len(s)
    out = {
        "n": int(n),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "std": float(s.std(ddof=1)) if n > 1 else float("nan"),
        "min": float(s.min()),
        "p10": float(s.quantile(0.10)),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
        "p90": float(s.quantile(0.90)),
        "p99": float(s.quantile(0.99)),
        "max": float(s.max()),
        "sum": float(s.sum()),
        "skew": float(s.skew()) if n > 2 else float("nan"),
        "kurtosis": float(s.kurtosis()) if n > 3 else float("nan"),
        "cv": float(s.std(ddof=1) / s.mean()) if n > 1 and s.mean() else float("nan"),
    }
    out["mean_to_median"] = out["mean"] / out["median"] if out["median"] else float("nan")
    return out


def zipf_exponent(ranks, values) -> dict:
    """Fit log(value) = a - b*log(rank) and return the Zipf exponent b.

    A pure Zipf law has b = 1. b > 1 means the distribution is *steeper* than
    Zipf (super-concentrated at the top); b < 1 means flatter.
    """
    r = pd.Series(ranks, dtype="float64").reset_index(drop=True)
    v = pd.Series(values, dtype="float64").reset_index(drop=True)
    if len(r) != len(v):
        n = min(len(r), len(v))
        r, v = r.iloc[:n], v.iloc[:n]
    # Align on the joint frame so NaNs are dropped from BOTH series at once.
    joint = pd.DataFrame({"r": r, "v": v}).dropna()
    r, v = joint["r"].to_numpy(), joint["v"].to_numpy()
    mask = (r > 0) & (v > 0)
    r, v = r[mask], v[mask]
    if len(r) < 10:
        return {"exponent": float("nan"), "intercept": float("nan"),
                "r2": float("nan"), "n": int(len(r))}
    x = np.log(r)
    y = np.log(v)
    b, a = np.polyfit(x, y, 1)
    yhat = a + b * x
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "exponent": float(-b),
        "intercept": float(a),
        "r2": float(1 - ss_res / ss_tot) if ss_tot else float("nan"),
        "n": int(len(r)),
    }


def pareto_alpha(values, threshold: float) -> float:
    """Maximum-likelihood Pareto shape parameter for the tail above `threshold`.

    Returns alpha (the "Zipf exponent" of the tail).  For a Pareto tail
    P(X > x) = (x_min / x)^alpha, alpha ~ 1 means a thin tail.
    """
    v = pd.Series(values, dtype="float64").dropna()
    v = v[v > threshold]
    n = len(v)
    if n < 30:
        return float("nan")
    return float(n / np.sum(np.log(v / threshold)))


def tail_share_estimate(values, threshold: float, alpha: float) -> float:
    """Estimate total revenue held by firms above `threshold` from a Pareto fit.

    Uses the rank-size form: if the distribution of sizes above the
    threshold follows N(x) = C * x^(-alpha), then the total is the integral
    of the density.  A simpler and more robust estimator: the Hill estimator
    on the top tail gives the number of firms above the threshold implied by
    the observed exceedance count.
    """
    v = pd.Series(values, dtype="float64").dropna()
    v = v[v > threshold]
    n = len(v)
    if n < 10 or not np.isfinite(alpha) or alpha <= 0:
        return float("nan")
    # Total = n * threshold / (alpha - 1) for a Pareto with xmin = threshold.
    if alpha <= 1.01:
        return float("nan")
    return float(n * threshold / (alpha - 1.0))


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

_RNG = np.random.default_rng(20251017)


def bootstrap_ci(values, stat, n_boot: int = 2000, alpha: float = 0.05,
                 seed: int | None = None) -> tuple[float, float]:
    """Percentile bootstrap CI for any statistic of a sample."""
    rng = np.random.default_rng(seed) if seed is not None else _RNG
    s = pd.Series(values, dtype="float64").dropna().to_numpy()
    if len(s) < 5:
        return (float("nan"), float("nan"))
    stats = []
    for _ in range(n_boot):
        sample = rng.choice(s, size=len(s), replace=True)
        try:
            stats.append(float(stat(sample)))
        except Exception:
            continue
    if not stats:
        return (float("nan"), float("nan"))
    arr = np.array(stats)
    lo, hi = np.percentile(arr, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(lo), float(hi))


def bootstrap_diff_ci(a, b, stat, n_boot: int = 2000, alpha: float = 0.05,
                      seed: int | None = None) -> tuple[float, float]:
    """Percentile bootstrap CI for stat(a) - stat(b), resampling independently."""
    rng = np.random.default_rng(seed) if seed is not None else _RNG
    x = pd.Series(a, dtype="float64").dropna().to_numpy()
    y = pd.Series(b, dtype="float64").dropna().to_numpy()
    if len(x) < 5 or len(y) < 5:
        return (float("nan"), float("nan"))
    diffs = []
    for _ in range(n_boot):
        sa = rng.choice(x, size=len(x), replace=True)
        sb = rng.choice(y, size=len(y), replace=True)
        try:
            diffs.append(float(stat(sa) - stat(sb)))
        except Exception:
            continue
    if not diffs:
        return (float("nan"), float("nan"))
    arr = np.array(diffs)
    lo, hi = np.percentile(arr, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(lo), float(hi))


def welch_t(a, b) -> dict:
    """Welch's unequal-variance t-test (does not assume equal variance)."""
    from scipy import stats as sps

    x = pd.Series(a, dtype="float64").dropna().to_numpy()
    y = pd.Series(b, dtype="float64").dropna().to_numpy()
    if len(x) < 3 or len(y) < 3:
        return {"t": float("nan"), "p": float("nan"), "df": float("nan"),
                "mean_diff": float("nan")}
    t, p = sps.ttest_ind(x, y, equal_var=False)
    return {"t": float(t), "p": float(p),
            "df": float(len(x) + len(y) - 2),
            "mean_diff": float(x.mean() - y.mean())}


def mann_whitney(a, b) -> dict:
    """Mann-Whitney U: distribution-free alternative to the t-test."""
    from scipy import stats as sps

    x = pd.Series(a, dtype="float64").dropna().to_numpy()
    y = pd.Series(b, dtype="float64").dropna().to_numpy()
    if len(x) < 3 or len(y) < 3:
        return {"u": float("nan"), "p": float("nan")}
    u, p = sps.mannwhitneyu(x, y, alternative="two-sided")
    return {"u": float(u), "p": float(p)}


def correlation(a, b, method: str = "spearman") -> dict:
    """Correlation with a p-value."""
    from scipy import stats as sps

    x = pd.Series(a, dtype="float64")
    y = pd.Series(b, dtype="float64")
    pair = pd.concat([x, y], axis=1).dropna()
    if len(pair) < 4:
        return {"r": float("nan"), "p": float("nan"), "n": 0}
    if method == "spearman":
        r, p = sps.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
    else:
        r, p = sps.pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
    return {"r": float(r), "p": float(p), "n": int(len(pair))}


def pct_difference(a, b) -> float:
    """Symmetric percentage difference: |a-b| / ((a+b)/2) * 100."""
    a, b = float(a), float(b)
    mid = (a + b) / 2
    if mid == 0:
        return float("nan")
    return abs(a - b) / abs(mid) * 100.0


def median_absolute_pct_diff(a, b) -> float:
    """Median symmetric % difference between two aligned numeric series."""
    x = pd.Series(a, dtype="float64")
    y = pd.Series(b, dtype="float64")
    pair = pd.concat([x, y], axis=1).dropna()
    if len(pair) == 0:
        return float("nan")
    mid = (pair.iloc[:, 0] + pair.iloc[:, 1]) / 2
    diff = (pair.iloc[:, 0] - pair.iloc[:, 1]).abs()
    ok = mid != 0
    if not ok.any():
        return float("nan")
    return float((diff[ok] / mid[ok] * 100).median())


def zscore(s: pd.Series) -> pd.Series:
    s = pd.Series(s, dtype="float64")
    sd = s.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return s * 0.0
    return (s - s.mean()) / sd


def fmt_p(p) -> str:
    """Format a p-value the way a journal would."""
    if p is None or not np.isfinite(p):
        return "n/a"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def fmt_ci(lo, hi, fmt: str = "{:.3f}") -> str:
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "n/a"
    return f"[{fmt.format(lo)}, {fmt.format(hi)}]"


def safe_div(a, b):
    """Division that returns NaN instead of raising or warning."""
    try:
        if b == 0 or b is None or (isinstance(b, float) and math.isnan(b)):
            return float("nan")
        return a / b
    except (TypeError, ZeroDivisionError):
        return float("nan")
