# The earth business atlas — notes for the article

Four layers, four sources, one picture: what business exists on earth, how big it
is, and where the visible numbers stop.

## Layer 0 — the frame

| | |
|---|---|
| World GDP (2024) | **$111.7 trillion** |
| Workers on earth | **3.70 billion** (population 8.14B) |
| Listed companies on earth | **47,980** |
| Global 2000 companies | 2,000 (4.2% of listed companies) |

Source: World Bank Open Data.

## Layer 1 — the public giants (Forbes Global 2000, 2025)

- Revenue **$52.9T**, profit **$4.9T**, assets **$242T**, market value **$91.3T**.
- Employees **92.6M** — about 2.5% of all workers.
- The 2,000 companies' revenue equals **47% of world GDP** — a scale statement, not
  an accounting one (revenue double counts along supply chains; GDP is value added).

**By sector (share of the $52.9T):**

| Sector | Revenue | Share | Companies |
|---|---|---|---|
| Financials | $12.43T | 23% | 578 |
| Consumer & Retail | $9.08T | 17% | 218 |
| Energy & Utilities | $6.81T | 13% | 188 |
| Technology | $4.69T | 9% | 184 |
| Healthcare | $3.18T | 6% | 106 |
| Food & Agriculture | $3.00T | 6% | 111 |
| Construction & Real Estate | $2.75T | 5% | 111 |
| Materials & Chemicals | $2.43T | 5% | 131 |
| Industrials & Defense | $2.30T | 4% | 108 |
| Business Services | $2.27T | 4% | 110 |
| Telecom & Media | $1.87T | 4% | 63 |
| Transport & Logistics | $1.81T | 3% | 84 |
| Conglomerates | $0.27T | 1% | 8 |

**Concentration:** top 10 = 8.5% of revenue; top 100 = 35%; top 500 = 71%; top 1,000 = 88%.

## Layer 2 — the whole economy (World Bank, 2024)

| | GDP share | Employment share |
|---|---|---|
| Agriculture | 4.1% | 26.1% |
| Industry | 25.4% | 23.6% |
| Services | 63.3% | 50.3% |

The gap is the story: **agriculture is 4% of output but 26% of workers** (~965M people),
while services produce 63% of output with half the workers.

## Layer 3 — the invisible giants (Fortune Global 500 names absent from Forbes)

90 companies, **$6.36T revenue**, not in the public list:

| Ownership | Companies | Revenue |
|---|---|---|
| State-owned | 56 | $4.08T |
| Private | 16 | $1.17T |
| Mutual / cooperative | 15 | $0.89T |
| Listed but outside Forbes | 3 | $0.22T |

Largest: **State Grid $555B**, China National Petroleum $402B, Trafigura $240B,
Sberbank $135B, State Farm $132B, EDF $128B, Huawei $123B, Shandong Energy $117B,
Gazprom $115B, China Baowu $103B.

State Grid alone would rank **third-largest company on earth by revenue** — it is
absent because it is wholly state-owned and unlisted.

## Layer 4 — the future (Cloud 100 / Next Billion-Dollar Startups, 2025)

- Cloud 100: **$1.24T** combined valuation, median **$5.1B**; OpenAI $300B, Anthropic $183B.
- 125 companies total including the 25 Next Billion-Dollar Startups.

## What the numbers add up to

- Visible public layer: **$52.9T** revenue (2,000 companies).
- Invisible large layer: **$6.4T** (90 companies).
- Private venture layer: **$1.2T** valuation (100 companies, not revenue).
- Together: **~$59T of company revenue** against **$111.7T of world GDP**.

## Country gap (top 10 economies)

| Country | GDP share | Global 2000 revenue share |
|---|---|---|
| United States | 26.5% | 36.9% |
| China | 16.9% | 14.8% |
| Germany | 4.2% | 4.3% |
| Japan | 3.8% | 8.0% |
| India | 3.4% | 2.5% |
| United Kingdom | 3.3% | 4.0% |
| France | 2.9% | 3.8% |
| Italy | 2.2% | 1.1% |
| Canada | 2.1% | 2.5% |
| Russia | 2.0% | **0.0%** |

Russia is the anomaly: 2% of world GDP, **zero companies** in the 2025 list
(no Russian company appears at all — a sanctions/delisting effect, not a data bug).

## Caveats to keep in the piece

1. Revenue is not value added. Never say "these companies are 47% of the economy";
   say "their combined revenue equals 47% of world GDP."
2. Forbes and Fortune use different fiscal years and definitions; the two layers
   are never summed inside a single chart.
3. Fortune's "Company type" field mislabels state firms as "Private" — our
   ownership column is manual and documented in `scripts/label_fortune.py`.
4. Market values are May 2025 snapshots.
5. Mutual insurers (State Farm, TIAA) are "private" in the everyday sense but
   policyholder-owned; they are a distinct category, not family firms.
