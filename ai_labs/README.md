# AI labs — closed, open-weight and national

Separate dataset (fifth): who builds foundation models, how open they are, and how
much their open work actually travels.

## What's in it

**99 labs** in a curated registry, plus hard evidence from Hugging Face on open-weight reach.

| Category | Count | Examples |
|---|---|---|
| Frontier, closed | 19 | OpenAI, Anthropic, xAI, Baidu |
| Frontier, open-weight | 8 | DeepSeek, Qwen, Mistral, Moonshot, Zhipu |
| Open-weight specialists | 11 | 01.AI, StepFun, Nous, Upstage |
| Research institutes / national | 24 | Ai2, EleutherAI, BAAI, Shanghai AI Lab, TII, AI Singapore |
| Enterprise / application | 15 | Cohere, AI21, Databricks, Perplexity |
| Generative media | 8 | Midjourney, Runway, Stability, Black Forest Labs |
| Hardware / infrastructure / data | 14 | NVIDIA, Groq, Cerebras, Scale AI |

**By country:** US 37 · China 17 · Japan 6 · South Korea 5 · Germany 4 · UK 3 ·
France 3 · Canada 3 · Taiwan 3 · India 3 · Russia 3.

**By openness:** 48 ship open weights, 18 partial, 33 closed.

## The interesting finding

**China's frontier labs are overwhelmingly open-weight** — DeepSeek, Qwen, Kimi
(Moonshot), GLM (Zhipu), MiniMax, StepFun, Baichuan all publish weights. The US
frontier is mostly closed with open-weight exceptions (Llama, Gemma, Nemotron,
Granite, OLMo).

On Hugging Face, the most-downloaded model per lab puts **BAAI (58M), Google (42M),
Qwen (29M)** at the top — China's open models reach more developers than any single
US frontier lab's open releases.

## The wide map: 173 model-builders across 15 modalities

`data/ai_companies.csv` is the superset — not just LLM labs:

| Modality | Companies |
|---|---|
| LLM | 58 |
| Chips | 10 |
| Video | 10 |
| Robotics | 10 |
| Autonomy | 10 |
| Biology / drug discovery | 9 |
| Code | 8 |
| Infrastructure | 7 |
| Image | 7 |
| Enterprise AI | 5 |
| Audio / voice | 4 |
| Agents | 4 |
| Data labelling | 4 |
| 3D / world models | 4 |
| Search | 2 |

Across all 173: **45 ship open weights, 24 partial, 104 closed**. Outside LLMs,
almost nothing is open — robotics, autonomy, video and biology are effectively
closed-weight industries.

## What each company row carries

`data/ai_companies.csv` is enriched per company:

| Column | Coverage | Source |
|---|---|---|
| `description` — what they're building | **136 of 173 (79%)** | Wikipedia intro, CC BY-SA |
| `wiki_url` | 136 | citation link |
| `valuation_busd_cb` + `valuation_date` | 54 | CB Insights unicorn board |
| `investors` | 49 | CB Insights |
| `total_funding_usd` | **0 — deliberately blank** | no free reliable source |
| `modality`, `category`, `country`, `founded`, `status`, `parent`, `open_weights`, `ticker` | 173 | curated |

The 37 without a description are niche institutes and young startups (LLM-jp,
BharatGen, TAIDE, Pika, Cartesia...) where Wikipedia has no page yet.

## Files

| Path | What it is |
|---|---|
| `data/ai_companies.csv` | **173 companies across 15 modalities**: category, country, founded, status, parent, open-weight policy, HF org, ticker, CB valuation |
| `data/ai_labs.csv` | 99 labs: country, founded, category, parent, open-weight policy, flagship models, licence, HF stats, CB valuation |
| `data/hf_stats.csv` | per-org: top model, downloads, licence, model count |
| `charts/ai01_labs_by_country.png` | labs by country, split by openness |
| `charts/ai02_open_reach.png` | most-downloaded model per lab |
| `charts/ai03_modalities.png` | companies by modality and openness |
| `charts/ai04_valuations.png` | largest private AI companies |

## Caveats

1. **This is a curated list, not a census.** There are hundreds of small labs; I kept
   99 that matter for a global overview. Absence is not insignificance.
2. **"Open weights" ≠ open source.** Most release weights but not training data or
   full code; licences range from Apache-2.0 to restrictive community licences.
3. **Categories are judgement calls.** "Frontier" vs "open-weight specialist" is a
   spectrum, and labs move.
4. **Founding years and flagship model names** are as of October 2026 and change fast.
5. **Funding totals are not included — the column exists but is empty.** No free source publishes reliable
   total-raised figures for private AI companies; inventing them would be worse than
   leaving them blank. `valuation_busd_cb` covers the 54 that sit on the CB unicorn
   board; the rest are blank on purpose. A Crunchbase or FMP key would fill this.
6. **Valuations come from CB Insights** (`valuation_busd_cb`), not from filings — private
   marks, and unmatched labs are blank on purpose.
6. **Hugging Face downloads measure usage, not quality** — BAAI's top model is an
   embedding model, not an LLM.

## Rebuild

```powershell
$py = "C:\Users\abhijit\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py ai_labs/scripts/build_labs.py
& $py ai_labs/scripts/make_charts.py
```
