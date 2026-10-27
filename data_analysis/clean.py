"""Cleaning and harmonisation.

The hard problem in this project is not missing data, it is *incoherent* data:
five sources that spell the same country and industry differently, and disagree
about who owns a company. This module produces one canonical vocabulary so the
analysis modules can mix sources without silently double counting.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from config import OWNERSHIP_LABELS

# --------------------------------------------------------------------------
# Country vocabulary
# --------------------------------------------------------------------------
# Countries outside the World Bank ISO3 set, plus spelling variants seen in
# the Forbes / CompaniesMarketCap / Wikipedia sources.
COUNTRY_ALIASES: dict[str, str] = {
    "czech republic": "CZE", "czechia": "CZE",
    "egypt": "EGY",
    "hong kong": "HKG", "hong kong sar": "HKG", "hong kong, china": "HKG",
    "south korea": "KOR", "korea, republic of": "KOR", "republic of korea": "KOR",
    "korea": "KOR",
    "taiwan": "TWN", "taiwan, china": "TWN", "chinese taipei": "TWN",
    "turkey": "TUR", "turkiye": "TUR", "türkiye": "TUR",
    "vietnam": "VNM", "viet nam": "VNM",
    "russia": "RUS", "russian federation": "RUS",
    "united states": "USA", "united states of america": "USA",
    "u.s.": "USA", "us": "USA", "usa": "USA",
    "united kingdom": "GBR", "uk": "GBR", "great britain": "GBR",
    "netherlands": "NLD", "the netherlands": "NLD", "holland": "NLD",
    "south africa": "ZAF",
    "united arab emirates": "ARE", "uae": "ARE",
    "saudi arabia": "SAU",
    "ivory coast": "CIV", "cote d'ivoire": "CIV", "côte d'ivoire": "CIV",
    "czechia " : "CZE",
    "lao pdr": "LAO", "laos": "LAO",
    "east timor": "TLS", "timor-leste": "TLS",
    "bosnia and herzegovina": "BIH", "bosnia": "BIH",
    "north macedonia": "MKD", "macedonia": "MKD",
    "swaziland": "SWZ", "eswatini": "SWZ",
    "cape verde": "CPV", "cabo verde": "CPV",
    "myanmar": "MMR", "burma": "MMR",
    "brunei darussalam": "BRN", "brunei": "BRN",
    "moldova, republic of": "MDA", "republic of moldova": "MDA",
    "venezuela, bolivarian republic of": "VEN",
    "iran, islamic republic of": "IRN", "iran": "IRN",
    "syrian arab republic": "SYR", "syria": "SYR",
    "micronesia, federated states of": "FSM",
    "kyrgyz republic": "KGZ", "kyrgyzstan": "KGZ",
    "slovak republic": "SVK", "slovakia": "SVK",
    "solomon islands": "SLB",
    "saint lucia": "LCA", "st. lucia": "LCA",
    "saint vincent and the grenadines": "VCT",
    "saint kitts and nevis": "KNA",
    "antigua and barbuda": "ATG",
    "trinidad and tobago": "TTO",
    "bahamas, the": "BHS", "the bahamas": "BHS",
    "gambia, the": "GMB", "the gambia": "GMB",
    "congo, democratic republic of the": "COD",
    "congo, republic of the": "COG", "republic of the congo": "COG",
    "cote divoire": "CIV",
    "saint martin": "MAF",
    "curacao": "CUW",
    "kosovo": "XKX",
    "palestine": "PSE", "palestinian territory": "PSE",
    "united kingdom of great britain and northern ireland": "GBR",
}

# Economies that exist as separate entries in the company sources but are not
# published as separate economies by the World Bank, so they are absent from
# ``country_meta.csv``. They still need a display name and a region.
EXTRA_COUNTRIES: dict[str, dict[str, str]] = {
    "TWN": {
        "name": "Taiwan",
        "region": "East Asia & Pacific",
        "forbes_region": "Asia-Pacific",
    },
}

# Forbes' six-region taxonomy, bridged onto World Bank regions so that
# countries missing from Forbes can still be placed.
# NOTE: Forbes labels the MENA bloc "Middle East & Central Asia" (not Africa).
# That vocabulary is kept verbatim so the numbers line up with Forbes.
WB_REGION_TO_FORBES = {
    "North America": "North America",
    "East Asia & Pacific": "Asia-Pacific",
    "South Asia": "Asia-Pacific",
    "Europe & Central Asia": "Europe",
    "Middle East, North Africa, Afghanistan & Pakistan": "Middle East & Central Asia",
    "Latin America & Caribbean": "Latin America",
    "Sub-Saharan Africa": "Africa",
}

# Reverse bridge: canonical region -> World Bank region, used when a Forbes
# region is needed for a country Forbes does not cover.
FORBES_TO_WB_REGION = {
    "North America": "North America",
    "Asia-Pacific": "East Asia & Pacific",
    "Europe": "Europe & Central Asia",
    "Middle East & Central Asia": "Middle East, North Africa, Afghanistan & Pakistan",
    "Latin America": "Latin America & Caribbean",
    "Africa": "Sub-Saharan Africa",
}

# Ownership vocabulary.
OWNERSHIP_MAP = {
    "state-owned": "state",
    "state owned": "state",
    "state-controlled": "state",
    "government-owned": "state",
    "public (outside forbes)": "public",
    "public": "public",
    "private (vc-backed)": "pe",
    "private (vc backed)": "pe",
    "private": "private",
    "mutual / cooperative": "mutual",
    "mutual": "mutual",
    "cooperative": "mutual",
    "dupe": "duplicate",
    "duplicate": "duplicate",
}

# --------------------------------------------------------------------------
# Sector vocabulary
# --------------------------------------------------------------------------
# Keyword rules map free-text industry labels (Wikipedia lists, Fortune,
# CompaniesMarketCap) onto the 13 Forbes sectors. First match wins, so the
# order encodes specificity.
SECTOR_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Financials", (
        "bank", "insurance", "financial", "asset management", "capital market",
        "investment", "credit", "securities", "brokerage", "leasing",
        "financ", "wealth", "asset", "reinsurance", "microfinance",
    )),
    ("Technology", (
        "software", "it service", "information technology", "semiconductor",
        "computer", "technology", "hardware", "electronic", "internet",
        "telecom", "data processing", "cloud", "cyber", "telecommunication",
    )),
    ("Healthcare", (
        "health care", "healthcare", "pharma", "biotech", "biotechnology",
        "medical", "drug", "hospital", "life science", "therapeutics",
        "health ", "wellness", "clinical",
    )),
    ("Energy & Utilities", (
        "oil", "gas", "energy", "utility", "utilities", "power", "electric",
        "coal", "petroleum", "refin", "renewable", "solar", "nuclear",
        "water supply", "mining", "oil & gas",
    )),
    ("Food & Agriculture", (
        "food", "agricultur", "beverage", "drink", "tobacco", "farm",
        "grain", "meat", "dairy", "crop", "brew", "fishery", "farming",
    )),
    ("Consumer & Retail", (
        "retail", "apparel", "clothing", "fashion", "department store",
        "supermarket", "convenience", "consumer", "specialty store",
        "e-commerce", "ecommerce", "sporting goods", "textile", "footwear",
        "jewelry", "toy", "household", "personal care",
    )),
    ("Materials & Chemicals", (
        "chemical", "material", "metals", "mining", "paper", "packaging",
        "steel", "aluminium", "aluminum", "cement", "glass", "rubber",
        "plastics", "resins", "agrochemical", "industrial gases",
    )),
    ("Construction & Real Estate", (
        "construct", "real estate", "realty", "property", "building",
        "engineering & construction", "infrastructure", "reit", "homebuilder",
        "civil engineering",
    )),
    ("Industrials & Defense", (
        "aerospace", "defense", "defence", "industrial", "machinery",
        "manufactur", "engineering", "shipbuild", "rail", "aircraft",
        "automotive", "auto ", "vehicle", "heavy machinery", "electrical equipment",
        "conglomerate industrial",
    )),
    ("Transport & Logistics", (
        "airline", "airways", "transport", "logistic", "freight", "shipping",
        "maritime", "port", "cargo", "courier", "postal", "railway", "trucking",
    )),
    ("Telecom & Media", (
        "media", "broadcast", "publishing", "entertainment", "telecom",
        "television", "radio", "newspaper", "magazine", "cable", "studio",
        "music", "film", "social media", "advertising", "games",
    )),
    ("Business Services", (
        "consulting", "professional service", "staffing", "human resource",
        "business service", "outsourcing", "advisory", "accounting",
        "marketing", "research", "cleaning", "security service",
        "waste management", "exhibition", "event", "recruitment",
    )),
]


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(text))
        if not unicodedata.combining(c)
    )


def norm_key(text) -> str:
    """Lowercase, de-accent, strip punctuation. Used for entity matching."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    s = strip_accents(str(text)).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def company_key(name: str) -> str:
    """Aggressive key for cross-source entity matching."""
    s = norm_key(name)
    for suffix in (" inc", " inc.", " corp", " corporation", " co", " company",
                   " ltd", " limited", " llc", " plc", " group", " holding",
                   " holdings", " sa", " s a", " nv", " n v", " ag", " ab",
                   " gmbh", " co ltd", " pvt", " private limited", " se", " a s"):
        s = re.sub(re.escape(suffix) + r"$", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


# --------------------------------------------------------------------------
# Country resolution
# --------------------------------------------------------------------------
def build_country_index(country_meta: pd.DataFrame,
                        forbes: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per country: iso3, name, world-bank region, forbes region.

    The Forbes region is taken from the Forbes 2000 where the country appears
    (majority vote) and back-filled from the World Bank region otherwise.
    """
    idx = country_meta.copy()
    idx["name"] = idx["name"].astype(str).str.strip()
    idx["region"] = idx["region"].astype(str).str.strip()
    idx["name_key"] = idx["name"].map(norm_key)
    idx["iso3"] = idx["iso3"].str.upper().str.strip()
    idx["forbes_region"] = idx["region"].map(WB_REGION_TO_FORBES)

    if forbes is not None and len(forbes):
        votes = (forbes.groupby("country")["region"]
                 .agg(lambda s: s.value_counts().idxmax()))
        name_to_iso = dict(zip(idx["name"], idx["iso3"]))
        for country, region in votes.items():
            iso = country_iso3(country, idx)
            if iso:
                idx.loc[idx["iso3"] == iso, "forbes_region"] = region

    # Aliases override.
    for alias, iso in COUNTRY_ALIASES.items():
        idx.loc[idx["name_key"] == alias, "iso3"] = iso

    # Merge duplicates created by aliases (e.g. Korea, Republic of -> KOR).
    idx = (idx.sort_values(["name_key"])
              .drop_duplicates("name_key", keep="first")
              .reset_index(drop=True))

    # Countries the World Bank does not publish as separate economies still
    # appear as separate entries in Forbes' list (Taiwan, and in our data
    # Hong Kong). Without a row here the ISO3 resolves but has no display
    # name, and a $2T country renders as "nan" in every country table.
    have = set(idx["iso3"])
    extra = []
    for iso, meta in EXTRA_COUNTRIES.items():
        if iso in have:
            continue
        extra.append({
            "iso3": iso,
            "name": meta["name"],
            "region": meta["region"],
            "name_key": norm_key(meta["name"]),
            "forbes_region": meta["forbes_region"],
        })
    if extra:
        idx = pd.concat([idx, pd.DataFrame(extra)], ignore_index=True)
        idx = idx.sort_values(["name_key"]).reset_index(drop=True)
    return idx


def country_iso3(name, idx: pd.DataFrame) -> str | None:
    """Resolve a country name to an ISO3 code."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return None
    key = norm_key(name)
    if not key:
        return None
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    hit = idx.loc[idx["name_key"] == key, "iso3"]
    if len(hit):
        return hit.iloc[0]
    # Try a prefix / containment match (e.g. "Bentonton, Ark." handled
    # elsewhere, but "Republic of Korea" style variants land here).
    cand = idx[idx["name_key"].str.contains(key, regex=False)]
    if len(cand) == 1:
        return cand.iloc[0]["iso3"]
    return None


def map_countries(names, idx: pd.DataFrame) -> pd.Series:
    lookup = dict(zip(idx["name_key"], idx["iso3"]))
    out = []
    for n in names:
        out.append(country_iso3(n, idx) if n is not None else None)
    return pd.Series(out, index=names.index if hasattr(names, "index") else None)


def region_of(iso3, idx: pd.DataFrame) -> str:
    if iso3 is None or (isinstance(iso3, float) and np.isnan(iso3)):
        return "Unknown"
    hit = idx.loc[idx["iso3"] == iso3, "forbes_region"]
    return hit.iloc[0] if len(hit) else "Unknown"


# --------------------------------------------------------------------------
# Ownership & sector
# --------------------------------------------------------------------------
def map_ownership(values) -> pd.Series:
    def one(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "unknown"
        s = norm_key(v)
        if s in OWNERSHIP_MAP:
            return OWNERSHIP_MAP[s]
        for k, val in OWNERSHIP_MAP.items():
            if k in s:
                return val
        return "unknown"
    return pd.Series([one(v) for v in values])


def map_sector(industry) -> str:
    """Map a free-text industry label onto the 13 Forbes sectors."""
    if industry is None or (isinstance(industry, float) and np.isnan(industry)):
        return "Unclassified"
    s = norm_key(industry)
    if not s:
        return "Unclassified"
    for sector, keys in SECTOR_RULES:
        for k in keys:
            if k in s:
                return sector
    return "Unclassified"


def ownership_label(key: str) -> str:
    return OWNERSHIP_LABELS.get(key, "Unknown")


# --------------------------------------------------------------------------
# Plausibility
# --------------------------------------------------------------------------
# Revenue/margin sanity bands used to flag impossible rows.
IMPLAUSIBLE = {
    "revenue_musd": (0.01, 1_000_000.0),      # $10K .. $1T
    "profit_margin_pct": (-500.0, 200.0),
    "roa_pct": (-200.0, 200.0),
    "market_value_to_revenue": (0.01, 100.0),
    "revenue_per_employee_usd": (1_000.0, 50_000_000.0),
    "asset_turnover": (0.001, 100.0),
}


def flag_implausible(df: pd.DataFrame, columns=None) -> pd.Series:
    """Boolean series: True where any checked value falls outside its band."""
    columns = columns or list(IMPLAUSIBLE)
    mask = pd.Series(False, index=df.index)
    for col in columns:
        if col not in df.columns:
            continue
        lo, hi = IMPLAUSIBLE[col]
        s = pd.to_numeric(df[col], errors="coerce")
        mask |= s.notna() & ((s < lo) | (s > hi))
    return mask


def dedupe(df: pd.DataFrame, keys: list[str], name_col: str = "company",
           keep: str = "first") -> pd.DataFrame:
    """Drop duplicate company rows within a frame."""
    cols = [c for c in keys if c in df.columns]
    if not cols:
        return df
    return df.drop_duplicates(subset=cols, keep=keep).reset_index(drop=True)


def weighted_mean(values, weights) -> float:
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    ok = ~np.isnan(v) & ~np.isnan(w) & (w > 0)
    if not ok.any():
        return float("nan")
    return float(np.average(v[ok], weights=w[ok]))


__all__ = [
    "COUNTRY_ALIASES", "OWNERSHIP_MAP", "SECTOR_RULES", "WB_REGION_TO_FORBES",
    "norm_key", "company_key", "strip_accents",
    "build_country_index", "country_iso3", "map_countries", "region_of",
    "map_ownership", "map_sector", "ownership_label",
    "flag_implausible", "dedupe", "weighted_mean", "IMPLAUSIBLE",
]
