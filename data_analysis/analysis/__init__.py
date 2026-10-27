"""Analysis modules for the Companies-on-Earth project.

Each module exposes the same shape:

    KEY: str
    run(ctx) -> {"key": str, "metrics": dict, "tables": dict[str, DataFrame]}
    insights(metrics) -> list[str]

``metrics`` must be JSON-safe (plain dicts / lists / numbers / strings) because
it is serialised straight into the dashboard payload.  ``tables`` may hold
pandas DataFrames and is converted to records by the dashboard builder.
"""

from __future__ import annotations

from . import (
    capital,
    companies,
    data_quality,
    geography,
    industry,
    ownership,
    private_capital,
    scale,
    time_series,
)

# Execution order — the order the tabs appear in the report.
MODULES = [
    scale,
    geography,
    industry,
    ownership,
    capital,
    private_capital,
    time_series,
    data_quality,
    companies,
]

__all__ = [
    "MODULES",
    "capital",
    "companies",
    "data_quality",
    "geography",
    "industry",
    "ownership",
    "private_capital",
    "scale",
    "time_series",
]
