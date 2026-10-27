"""A two-level taxonomy that covers the whole economy, and a canonical mapping
for the free-text industry labels Forbes uses (they have 39 variants)."""

from __future__ import annotations

import sys

import pandas as pd
from pathlib import Path

# Forbes industry label -> (sector, canonical industry)
SECTOR_MAP: dict[str, tuple[str, str]] = {
    # Financials
    "Banking": ("Financials", "Banking"),
    "Banking and Financial Services": ("Financials", "Banking"),
    "Insurance": ("Financials", "Insurance"),
    "Diversified Financials": ("Financials", "Diversified Financials"),
    # Energy & utilities
    "Oil & Gas Operations": ("Energy & Utilities", "Oil & Gas"),
    "Utilities": ("Energy & Utilities", "Utilities"),
    # Technology
    "IT Software & Services": ("Technology", "Software & IT Services"),
    "Technology Hardware & Equipment": ("Technology", "Hardware & Equipment"),
    "Semiconductors": ("Technology", "Semiconductors"),
    "Semiconductor": ("Technology", "Semiconductors"),
    "Semiconductors, Electronics, Electrical Engineering": ("Technology", "Semiconductors"),
    # Telecom & media
    "Telecommunications Services": ("Telecom & Media", "Telecom Services"),
    "Telecommunications Services, Cable Supplier": ("Telecom & Media", "Telecom Services"),
    "Media": ("Telecom & Media", "Media"),
    # Healthcare
    "Drugs & Biotechnology": ("Healthcare", "Pharma & Biotech"),
    "Health Care Equipment & Services": ("Healthcare", "Health Care Equipment & Services"),
    # Industrials
    "Aerospace & Defense": ("Industrials & Defense", "Aerospace & Defense"),
    "Capital Goods": ("Industrials & Defense", "Capital Goods"),
    "Engineering, Manufacturing": ("Industrials & Defense", "Engineering & Manufacturing"),
    # Construction
    "Construction": ("Construction & Real Estate", "Construction"),
    "Construction, Chemicals, Raw Materials": ("Construction & Real Estate", "Construction"),
    # Materials
    "Materials": ("Materials & Chemicals", "Materials"),
    "Chemicals": ("Materials & Chemicals", "Chemicals"),
    # Food
    "Food, Drink & Tobacco": ("Food & Agriculture", "Food, Drink & Tobacco"),
    "Food Markets": ("Food & Agriculture", "Food Markets"),
    # Consumer
    "Retailing": ("Consumer & Retail", "Retail & Wholesale"),
    "Retail and Wholesale": ("Consumer & Retail", "Retail & Wholesale"),
    "Consumer Durables": ("Consumer & Retail", "Consumer Durables"),
    "Automotive": ("Consumer & Retail", "Automotive"),
    "Automotive (Automotive and Suppliers)": ("Consumer & Retail", "Automotive"),
    "Household & Personal Products": ("Consumer & Retail", "Household & Personal Products"),
    "Hotels, Restaurants & Leisure": ("Consumer & Retail", "Hotels & Leisure"),
    # Transport
    "Transportation": ("Transport & Logistics", "Transportation"),
    "Transportation and Logistics": ("Transport & Logistics", "Transportation"),
    "Airlines": ("Transport & Logistics", "Airlines"),
    # Business services
    "Business Services & Supplies": ("Business Services", "Business Services"),
    "Trading Companies": ("Business Services", "Trading Companies"),
    # Conglomerates
    "Conglomerate": ("Conglomerates", "Conglomerate"),
    "Conglomerates": ("Conglomerates", "Conglomerate"),
    "Multicompany": ("Conglomerates", "Conglomerate"),
    "Ancsa Native Corporations": ("Conglomerates", "Conglomerate"),
    # Labels that only appear on the private-companies list
    "Food & Drink": ("Food & Agriculture", "Food, Drink & Tobacco"),
    "Food, Soft Beverages, Alcohol & Tobacco": ("Food & Agriculture", "Food, Drink & Tobacco"),
    "Services": ("Business Services", "Business Services"),
    "Business Management Consultants": ("Business Services", "Business Services"),
    "Manufacturing": ("Industrials & Defense", "Engineering & Manufacturing"),
    "Convenience Stores & Gas Stations": ("Consumer & Retail", "Retail & Wholesale"),
    "Restaurants": ("Consumer & Retail", "Hotels & Leisure"),
    "Clothing, Shoes, Sports Equipment": ("Consumer & Retail", "Household & Personal Products"),
    "Healthcare & Social Services": ("Healthcare", "Health Care Equipment & Services"),
}


def annotate(df: pd.DataFrame, industry_col: str = "industry") -> pd.DataFrame:
    out = df.copy()
    mapped = out[industry_col].map(lambda x: SECTOR_MAP.get(str(x).strip(), None))
    out["sector"] = [m[0] if m else "Unclassified" for m in mapped]
    out["industry_canon"] = [m[1] if m else "Unclassified" for m in mapped]
    return out


def main() -> None:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026  # python scripts/taxonomy.py [year]
    src = f"data/global2000_{year}.csv"
    df = pd.read_csv(src)
    df = annotate(df)
    unmatched = df[df.sector == "Unclassified"]["industry"].unique()
    print("unmapped labels:", list(unmatched))
    df.to_csv(src, index=False, encoding="utf-8-sig")

    tax = (df.groupby(["sector", "industry_canon"], as_index=False)
             .agg(companies=("company", "count"),
                  revenue_musd=("revenue_musd", "sum"),
                  profits_musd=("profits_musd", "sum"))
             .sort_values("revenue_musd", ascending=False))
    tax.to_csv("data/industry_taxonomy.csv" if year == 2025 else f"data/industry_taxonomy_{year}.csv", index=False, encoding="utf-8-sig")
    print(tax.to_string(index=False))
    print("sectors:", df.sector.nunique(), "industries:", df.industry_canon.nunique())


if __name__ == "__main__":
    main()
