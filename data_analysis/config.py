"""Central configuration: paths, palette, and the dataset registry.

Every other module imports from here so that paths resolve identically no
matter what the current working directory is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
PKG = Path(__file__).resolve().parent

OUT = PKG / "output"
OUT_CHARTS = OUT / "charts"
OUT_DATA = OUT / "data"
OUT_RAW = OUT / "raw"

DATA = ROOT / "data"
LISTED = ROOT / "listed_universe" / "data"
STOCK = ROOT / "stock_market" / "data"
STARTUPS = ROOT / "startups" / "data"
AI_LABS = ROOT / "ai_labs" / "data"

TEMPLATES = PKG / "templates"

for _d in (OUT, OUT_CHARTS, OUT_DATA, OUT_RAW):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# House palette (matches the existing scripts/ chart style)
# --------------------------------------------------------------------------
INK = "#0B2545"
BAR = "#1B6CA8"
ACCENT = "#E07A4F"
MUTED = "#9AA5B1"
BG = "#FFFFFF"
GRID = "#E6EAF0"

# Extended ramps for categorical work (ordered, colour-blind safe)
PALETTE = [
    "#0B2545", "#1B6CA8", "#4E9BD1", "#9CC7E4", "#E07A4F",
    "#F2B79B", "#2E8B74", "#7FC3AC", "#8A6FB0", "#C3B0DA",
    "#B8860B", "#E8C87A", "#5A6673", "#9AA5B1", "#D6DCE5",
]

FONT = "Segoe UI"
DPI = 200

# --------------------------------------------------------------------------
# Dataset registry
# --------------------------------------------------------------------------
# trust: "authoritative" | "reported" | "estimate" | "mark"
# kind:  "financials"   -> revenue/profit-bearing, safe to add up
#        "valuation"    -> market cap / valuation, not additive with revenue
#        "reference"    -> macro / lookup / metadata


@dataclass(frozen=True)
class Dataset:
    key: str
    path: Path
    label: str
    trust: str
    kind: str
    publisher: str
    url: str
    notes: str = ""
    optional: bool = False


REGISTRY: list[Dataset] = [
    Dataset(
        "forbes2000", DATA / "global2000_2025.csv",
        "Forbes Global 2000 2025", "reported", "financials",
        "Forbes", "https://www.forbes.com/lists/global2000/",
        "2,000 largest firms by revenue. Revenue is a Forbes estimate in USD.",
    ),
    Dataset(
        "forbes2000_hist", DATA / "global2000_2025_history.csv",
        "Forbes Global 2000 10-year history", "reported", "financials",
        "Forbes", "https://www.forbes.com/lists/global2000/",
        "Long-format revenue/profit history, approx. 10 years.",
    ),
    Dataset(
        "fortune500", DATA / "fortune_g500_2025.csv",
        "Fortune Global 500 2025", "reported", "financials",
        "Fortune", "https://fortune.com/ranking/global500/",
        "US-centric list; 500 firms ranked by revenue, USD millions.",
    ),
    Dataset(
        "fortune_labels", DATA / "fortune_labels.csv",
        "Fortune ownership labels (manual)", "reported", "reference",
        "manual correction", "",
        "Corrects Fortune's company_type field, which mislabels state-owned firms as Private.",
    ),
    Dataset(
        "master", DATA / "companies_master.csv",
        "Companies master (Forbes + Fortune)", "reported", "financials",
        "derived", "",
        "Union of Forbes 2000 and Fortune 500 with manual ownership labels.",
    ),
    Dataset(
        "industry_taxonomy", DATA / "industry_taxonomy.csv",
        "Industry taxonomy (13 sectors / 30 industries)", "reported", "reference",
        "derived", "", "Sector rollup of the Forbes 2000.",
    ),
    Dataset(
        "country_meta", DATA / "country_meta.csv",
        "Country metadata (ISO3, region)", "reference", "reference",
        "derived", "", "217 countries, 6 regions.",
    ),
    Dataset(
        "country_gdp", DATA / "country_gdp_2024.csv",
        "Country GDP 2024", "authoritative", "reference",
        "World Bank", "https://data.worldbank.org/",
        "Nominal GDP in current USD, 204 countries.",
    ),
    Dataset(
        "world_macro", DATA / "world_macro.csv",
        "World macro series", "authoritative", "reference",
        "World Bank", "https://data.worldbank.org/",
        "World aggregates: GDP, employment by sector, labour force, population.",
    ),
    Dataset(
        "private_us", DATA / "private_us_2025.csv",
        "Forbes America's Top Private Companies", "reported", "financials",
        "Forbes", "https://www.forbes.com/largest-private-companies/",
        "US only. Revenue reported by Forbes.",
    ),
    Dataset(
        "forbes_startups", DATA / "startups_2025.csv",
        "Forbes Cloud 100 + Next Billion", "mark", "valuation",
        "Forbes", "https://www.forbes.com/lists/",
        "Private valuations. Cloud 100 + Next Billion Dollar Startups.",
    ),
    Dataset(
        "listed", LISTED / "listed_universe.csv",
        "Listed company universe", "authoritative/estimate", "financials",
        "SEC XBRL + CompaniesMarketCap", "",
        "12,512 listed firms. SEC revenue is audited; CMC revenue is an estimate.",
    ),
    Dataset(
        "profiles", LISTED / "company_profiles.csv",
        "Company profiles + descriptions", "mixed", "reference",
        "Forbes + Wikipedia", "",
        "20,663 profiles. Descriptions: Forbes (editorial) + Wikipedia (CC BY-SA).",
    ),
    Dataset(
        "exchanges", STOCK / "exchanges.csv",
        "Global stock exchanges", "reported", "valuation",
        "CompaniesMarketCap", "",
        "60 exchanges. Market cap totals are coverage-limited, not world totals.",
    ),
    Dataset(
        "exchange_top", STOCK / "exchange_top_companies.csv",
        "Top companies per exchange", "reported", "valuation",
        "CompaniesMarketCap", "", "Top ~10 firms per exchange.",
    ),
    Dataset(
        "exchange_all", STOCK / "exchange_companies.csv",
        "Companies per exchange", "reported", "valuation",
        "CompaniesMarketCap", "", "9,780 firm-exchange rows. ADRs mapped to home exchange.",
    ),
    Dataset(
        "exchange_lookup", STOCK / "exchanges_lookup.csv",
        "Ticker suffix to exchange map", "reference", "reference",
        "derived", "", "Maps ticker suffixes to exchanges.",
    ),
    Dataset(
        "unicorns", STARTUPS / "unicorns_cbinsights.csv",
        "Unicorn company list (CB Insights)", "mark", "valuation",
        "CB Insights", "https://www.cbinsights.com/",
        "1,442 private companies with $1B+ valuations. Paper marks, not prices.",
    ),
    Dataset(
        "startups_global", STARTUPS / "startups_global.csv",
        "Startups global (CB Insights + Forbes)", "mark", "valuation",
        "CB Insights / Forbes", "", "1,479 rows, merged and de-duplicated.",
    ),
    Dataset(
        "ai_companies", AI_LABS / "ai_companies.csv",
        "AI model builders", "mixed", "reference",
        "compiled", "", "173 companies across 15 modalities.",
    ),
    Dataset(
        "ai_labs", AI_LABS / "ai_labs.csv",
        "AI labs", "mixed", "reference",
        "compiled", "", "99 labs. Open/closed weight status, HF org, valuation.",
    ),
    Dataset(
        "hf_stats", AI_LABS / "hf_stats.csv",
        "Hugging Face org stats", "reported", "reference",
        "Hugging Face", "https://huggingface.co/",
        "Model counts and top-model downloads per org.",
    ),
]

REGISTRY_BY_KEY = {d.key: d for d in REGISTRY}

# Files produced by the scrapers in this package.
SCRAPED = {
    "wiki_countries": OUT_RAW / "wiki_country_companies.csv",
    "fortune_profiles": OUT_RAW / "fortune_profiles.csv",
    "worldbank_extra": OUT_RAW / "worldbank_extra.csv",
    "world_geo": OUT_RAW / "world_countries.geojson",
}

# --------------------------------------------------------------------------
# Analysis constants
# --------------------------------------------------------------------------
TOP_N_DEFAULT = 100
USD_PER_MUSD = 1_000_000.0

# Revenue basis ladder used when reconciling sources into one universe.
# Lower index = stronger evidence. The first basis present wins.
REVENUE_BASIS_PRIORITY = [
    "sec_filing",       # audited XBRL
    "forbes",          # Forbes editorial estimate
    "fortune",         # Fortune reported
    "wikipedia",       # Wikipedia country list (often Forbes-sourced)
    "estimate",        # third-party estimate
]

OWNERSHIP_LABELS = {
    "public": "Publicly listed",
    "listed": "Publicly listed",
    "state": "State-owned / state-controlled",
    "private": "Private (founder / family)",
    "mutual": "Mutual / cooperative",
    "cooperative": "Mutual / cooperative",
    "subsidiary": "Subsidiary of a parent",
    "pe": "Private equity / venture-backed",
    "unknown": "Unknown",
}

REGION_ORDER = ["North America", "Asia-Pacific", "Europe",
                "Middle East & Central Asia", "Latin America", "Africa"]
