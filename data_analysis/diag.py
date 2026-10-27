import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import context as ctxmod
import analysis
from analysis import capital, data_quality, industry, time_series

ctx = ctxmod.build(verbose=False)

for mod in (industry, time_series, data_quality):
    print("=" * 70)
    print("MODULE", mod.KEY)
    try:
        res = mod.run(ctx)
        print("  ok, metrics keys:", list(res["metrics"].keys()))
    except Exception:
        traceback.print_exc()

print("=" * 70)
print("CAPITAL: find DataFrame in metrics")
res = capital.run(ctx)


def find_dfs(obj, path=""):
    import pandas as pd
    if isinstance(obj, pd.DataFrame):
        print("   DataFrame at", path, obj.shape)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            find_dfs(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj[:50]):
            find_dfs(v, f"{path}[{i}]")


find_dfs(res["metrics"], "metrics")

print("=" * 70)
print("OPEN WEIGHTS values:", ctx.bundle.get("ai_companies")["open_weights"].value_counts().to_dict())
print("AI category values:", ctx.bundle.get("ai_companies")["category"].value_counts().head(12).to_dict())
print("=" * 70)
rec = ctx.reconciled
m = rec[rec["revenue_usd"].notna() & rec["profit_usd"].notna() & (rec["revenue_usd"] > 0)].copy()
m["mg"] = m["profit_usd"] / m["revenue_usd"]
print("margin describe:", m["mg"].describe().to_dict())
print("worst margins:")
print(m.nlargest(8, "mg")[["company", "source", "revenue_usd", "profit_usd", "mg"]].to_string())
print("n margin > 1:", (m["mg"] > 1).sum(), "of", len(m))
print("=" * 70)
print("countries named nan/none:")
print(ctx.reconciled["country"].value_counts().head(3))
print(ctx.reconciled["country"].astype(str).str.lower().isin(["nan", "none", ""]).sum())
