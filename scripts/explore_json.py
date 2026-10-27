import json
from pathlib import Path

p = Path("data/raw/global2000_2025_api.json")
data = json.loads(p.read_text(encoding="utf-8"))

print("top-level type:", type(data).__name__)
if isinstance(data, dict):
    print("top-level keys:", list(data.keys())[:20])
    for k, v in data.items():
        print(f"  {k}: {type(v).__name__}", (len(v) if hasattr(v, "__len__") else ""))

# find the list of companies
def find_list(obj, path=""):
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        print(f"\nlist at {path!r}: {len(obj)} items")
        print("first item keys:", list(obj[0].keys())[:40])
        return obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            r = find_list(v, f"{path}.{k}")
            if r:
                return r
    return None

lst = find_list(data)
if lst:
    print("\n--- sample record ---")
    print(json.dumps(lst[0], indent=2, ensure_ascii=False)[:3000])
