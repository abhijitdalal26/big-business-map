"""Statistical models: regressions, clustering and dimensionality reduction.

These are the pieces that turn descriptive tables into claims. A margin table
tells you *what*; a regression tells you *why*, with an effect size and a
standard error attached.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# OLS
# ---------------------------------------------------------------------------


def ols(df: pd.DataFrame, y: str, x_cols: list[str],
        categorical: list[str] | None = None,
        weights: str | None = None,
        cluster: str | None = None) -> dict:
    """Ordinary least squares with optional categorical controls.

    ``cluster`` groups standard errors (e.g. by country) so that a single
    country with 600 companies does not masquerade as 600 independent
    observations.
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    categorical = categorical or []
    cols = [y] + x_cols + categorical
    data = df[cols].copy()
    for c in x_cols + categorical:
        data[c] = pd.to_numeric(data[c], errors="coerce") if c == y else data[c]
    data = data.dropna(subset=[y] + [c for c in x_cols])
    if len(data) < len(x_cols) + 3:
        return {"ok": False, "reason": "insufficient data", "n": int(len(data))}

    terms = " + ".join(x_cols + [f"C({c})" for c in categorical])
    formula = f"Q('{y}') ~ {terms}"
    try:
        if weights:
            model = smf.wls(formula, data, weights=data[weights])
        else:
            model = smf.ols(formula, data)
        if cluster and cluster in df.columns:
            groups = df.loc[data.index, cluster]
            res = model.fit(cov_type="cluster", cov_kwds={"groups": groups})
        else:
            res = model.fit()
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "reason": str(exc), "n": int(len(data))}

    tidy = pd.DataFrame({
        "term": res.params.index,
        "coef": res.params.values,
        "std_err": res.bse.values,
        "t": res.tvalues.values,
        "p": res.pvalues.values,
    })
    tidy["ci_low"] = tidy["coef"] - 1.96 * tidy["std_err"]
    tidy["ci_high"] = tidy["coef"] + 1.96 * tidy["std_err"]

    return {
        "ok": True,
        "n": int(res.nobs),
        "r2": float(res.rsquared),
        "adj_r2": float(res.rsquared_adj),
        "f_stat": float(res.fvalue) if hasattr(res, "fvalue") else float("nan"),
        "f_p": float(res.f_pvalue) if hasattr(res, "f_pvalue") else float("nan"),
        "params": tidy,
        "result": res,
        "formula": formula,
    }


def log_log_elasticity(df: pd.DataFrame, y: str, x: str,
                       controls: list[str] | None = None,
                       categorical: list[str] | None = None) -> dict:
    """Elasticity from a log-log regression: how does y scale with x?

    Uses simple OLS on logs with an intercept so that the slope is the
    elasticity directly (no correction needed, since we include a constant).
    """
    d = df[[y, x] + (controls or [])].copy()
    d = d[(d[y] > 0) & (d[x] > 0)]
    d = d.dropna()
    if len(d) < 20:
        return {"ok": False, "reason": "insufficient data", "n": int(len(d))}

    import statsmodels.api as sm

    X = np.column_stack([np.ones(len(d)), np.log(d[x].to_numpy(dtype=float))])
    if controls:
        for c in controls:
            X = np.column_stack([X, np.log(d[c].to_numpy(dtype=float))])
    yv = np.log(d[y].to_numpy(dtype=float))
    try:
        res = sm.OLS(yv, X).fit()
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "reason": str(exc), "n": int(len(d))}
    names = ["const", f"log({x})"] + [f"log({c})" for c in (controls or [])]
    return {
        "ok": True,
        "n": int(len(d)),
        "elasticity": float(res.params[1]),
        "std_err": float(res.bse[1]),
        "p": float(res.pvalues[1]),
        "ci_low": float(res.conf_int()[1, 0]),
        "ci_high": float(res.conf_int()[1, 1]),
        "r2": float(res.rsquared),
        "params": dict(zip(names, res.params.tolist())),
    }


def proportion_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (better near 0/1)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def kmeans_archetypes(df: pd.DataFrame, feature_cols: list[str], k: int = 4,
                      label: str = "archetype", seed: int = 42,
                      scale: bool = True) -> dict:
    """Cluster firms on a financial fingerprint to find corporate archetypes.

    Features are log-transformed (so that "a bank and a retailer" are not
    separated merely by size) and then z-scored.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    d = df[feature_cols].apply(pd.to_numeric, errors="coerce")
    d = d.replace([np.inf, -np.inf], np.nan)
    # log1p the money columns, which are heavy-tailed
    for c in feature_cols:
        d[c] = np.log1p(d[c].clip(lower=0))
    d = d.dropna()
    if len(d) < k * 10:
        return {"ok": False, "reason": "insufficient data", "n": int(len(d))}

    X = d.to_numpy(dtype=float)
    if scale:
        X = StandardScaler().fit_transform(X)

    km = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(X)
    labels = km.labels_

    profile_rows = []
    for c in range(k):
        idx = labels == c
        row = {"cluster": c, "n": int(idx.sum())}
        for col in feature_cols:
            row[col] = float(d.loc[idx, col].median()) if idx.any() else float("nan")
        profile_rows.append(row)
    profile = pd.DataFrame(profile_rows).sort_values("n", ascending=False).reset_index(drop=True)

    return {
        "ok": True,
        "n": int(len(d)),
        "features": feature_cols,
        "labels": pd.Series(labels, index=d.index, name=label),
        "profile": profile,
        "centroids": km.cluster_centers_,
        "inertia": float(km.inertia_),
    }


# ---------------------------------------------------------------------------
# PCA
# ---------------------------------------------------------------------------


def pca_components(df: pd.DataFrame, feature_cols: list[str], n: int = 3,
                   scale: bool = True) -> dict:
    """Principal component analysis over the financial fingerprint.

    Answers "how many independent dimensions does corporate identity
    actually have?" and which variables load on each axis.
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    d = df[feature_cols].apply(pd.to_numeric, errors="coerce")
    d = d.replace([np.inf, -np.inf], np.nan)
    for c in feature_cols:
        d[c] = np.log1p(d[c].clip(lower=0))
    d = d.dropna()
    if len(d) < 20:
        return {"ok": False, "reason": "insufficient data", "n": int(len(d))}

    X = d.to_numpy(dtype=float)
    if scale:
        X = StandardScaler().fit_transform(X)

    p = PCA(n_components=min(n, X.shape[1]))
    scores = p.fit_transform(X)

    loadings = pd.DataFrame(
        p.components_.T,
        index=feature_cols,
        columns=[f"PC{i + 1}" for i in range(scores.shape[1])],
    )
    return {
        "ok": True,
        "n": int(len(d)),
        "explained_variance_ratio": [float(v) for v in p.explained_variance_ratio_],
        "loadings": loadings,
        "scores": pd.DataFrame(
            scores,
            index=d.index,
            columns=[f"PC{i + 1}" for i in range(scores.shape[1])],
        ),
    }


# ---------------------------------------------------------------------------
# Growth
# ---------------------------------------------------------------------------


def cagr(start: float, end: float, years: float) -> float:
    """Compound annual growth rate; NaN if inputs make it undefined."""
    if start is None or end is None or years <= 0:
        return float("nan")
    if start <= 0 or end <= 0:
        return float("nan")
    return float((end / start) ** (1.0 / years) - 1.0)


def rank_mobility(df: pd.DataFrame, id_col: str, rank_col: str,
                  year_col: str) -> pd.DataFrame:
    """Change in rank between the first and last year observed per company."""
    d = df.copy()
    d = d.sort_values([id_col, year_col])
    first = d.groupby(id_col).first()
    last = d.groupby(id_col).last()
    out = pd.DataFrame({
        "rank_first": first[rank_col],
        "rank_last": last[rank_col],
        "year_first": first[year_col],
        "year_last": last[year_col],
    })
    out["rank_change"] = out["rank_first"] - out["rank_last"]
    out["years"] = out["year_last"] - out["year_first"]
    out = out[out["years"] > 0]
    # Annualise: positive = climbed the table.
    out["ranks_per_year"] = out["rank_change"] / out["years"]
    return out.sort_values("ranks_per_year", ascending=False).reset_index()


def cohort_aggregate(df: pd.DataFrame, id_col: str, value_col: str,
                     year_col: str, cohort: list[str] | None = None) -> pd.DataFrame:
    """Aggregate a metric over a fixed set of companies (a constant cohort).

    Summing the raw total of a list that changes composition year to year
    confounds growth with membership churn. Holding the cohort fixed is the
    only way to see real growth.
    """
    d = df.copy()
    if cohort is not None:
        d = d[d[id_col].isin(set(cohort))]
    agg = d.groupby(year_col).agg(
        total=(value_col, "sum"),
        n=(value_col, "count"),
    ).reset_index()
    return agg
