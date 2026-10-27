"""AI labs: closed-source frontier labs, open-weight labs, national institutes.

Two inputs:
  1. a curated lab registry (below) — country, founding year, category, models
  2. Hugging Face API — objective evidence of open-weight shipping per org
     (top model by downloads, license, model count)

Outputs: ai_labs/data/ai_labs.csv, ai_labs/data/hf_stats.csv
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)

# lab, hf_org, country, founded, category, parent, open_weights, flagship, notable_open, license
LABS = [
    # ---- frontier closed ----
    ("OpenAI", "openai", "United States", 2015, "frontier_closed", None, "partial",
     "GPT-5.x, o-series, Sora", "gpt-oss-120b", "Apache-2.0"),
    ("Anthropic", None, "United States", 2021, "frontier_closed", None, "no",
     "Claude 4.x", None, None),
    ("Google DeepMind", "google", "United Kingdom", 2010, "frontier_closed", "Alphabet", "partial",
     "Gemini 3, Veo, AlphaFold", "Gemma 4", "Gemma license"),
    ("Meta Superintelligence Labs / FAIR", "meta-llama", "United States", 2013, "frontier_open",
     "Meta", "yes", "Llama 4.x", "Llama 4", "Llama license"),
    ("xAI", None, "United States", 2023, "frontier_closed", None, "partial",
     "Grok 4", "grok-1", "Apache-2.0"),
    ("Microsoft AI / MAI", None, "United States", 2023, "frontier_closed", "Microsoft", "no",
     "MAI-1, Copilot", None, None),
    ("Amazon AGI / Nova", None, "United States", 2023, "frontier_closed", "Amazon", "no",
     "Nova 2", None, None),
    ("Apple Intelligence", None, "United States", 2024, "frontier_closed", "Apple", "no",
     "Apple Intelligence, Ferret", None, None),
    ("Mistral AI", "mistralai", "France", 2023, "frontier_open", None, "partial",
     "Mistral Large, Le Chat", "Mistral 7B", "Apache-2.0"),
    ("Cohere", "CohereLabs", "Canada", 2019, "enterprise", None, "partial",
     "Command A", "Command R", "CC-BY-NC"),
    ("AI21 Labs", "ai21labs", "Israel", 2017, "enterprise", None, "partial",
     "Jamba", "Jamba", "Apache-2.0"),
    ("Perplexity", None, "United States", 2022, "application", None, "no",
     "Sonar", None, None),
    ("Character.AI", None, "United States", 2021, "application", "Google (licence)", "no",
     "Character models", None, None),
    ("Inflection AI", None, "United States", 2022, "application", "Microsoft (talent)", "no",
     "Pi", None, None),
    ("Adept", None, "United States", 2022, "application", "Amazon (acquired)", "no",
     "ACT-1", None, None),
    ("Runway", None, "United States", 2018, "generative_media", None, "no",
     "Gen-4", None, None),
    ("Midjourney", None, "United States", 2021, "generative_media", None, "no",
     "Midjourney v7", None, None),
    ("Stability AI", "stabilityai", "United Kingdom", 2019, "generative_media", None, "yes",
     "Stable Diffusion 3.5", "SDXL", "Stability Community"),
    ("Black Forest Labs", "black-forest-labs", "Germany", 2024, "generative_media", None, "yes",
     "FLUX.2", "FLUX.1", "Apache-2.0"),
    ("Luma AI", None, "United States", 2021, "generative_media", None, "no",
     "Ray3", None, None),
    ("ElevenLabs", None, "United States", 2022, "generative_media", None, "no",
     "Eleven v3 (voice)", None, None),
    ("Suno", None, "United States", 2022, "generative_media", None, "no",
     "v5 (music)", None, None),
    ("Synthesia", None, "United Kingdom", 2017, "generative_media", None, "no",
     "Avatar video", None, None),
    ("Reka AI", "RekaAI", "United States", 2022, "frontier_closed", None, "partial",
     "Reka Core", "Reka Flash", "Apache-2.0"),
    ("Nous Research", "NousResearch", "United States", 2023, "open_weight", None, "yes",
     "Hermes", "Hermes 4", "Llama/Apache"),
    ("Together AI", "togethercomputer", "United States", 2022, "infrastructure", None, "yes",
     "hosting open models", "RedPajama", "Apache-2.0"),
    ("Databricks (Mosaic)", "databricks", "United States", 2023, "enterprise", "Databricks", "yes",
     "DBRX", "DBRX", "Databricks Open"),
    ("NVIDIA", "nvidia", "United States", 1993, "hardware_lab", None, "yes",
     "Nemotron", "Nemotron-4", "NVIDIA Open"),
    ("IBM Research", "ibm-granite", "United States", 1945, "enterprise", "IBM", "yes",
     "Granite 4", "Granite", "Apache-2.0"),
    ("Salesforce AI Research", "Salesforce", "United States", 2016, "enterprise", "Salesforce", "yes",
     "xLAM, BLIP", "xLAM", "Apache-2.0"),
    ("Allen Institute for AI (Ai2)", "allenai", "United States", 2014, "institute", None, "yes",
     "OLMo 3, Molmo", "OLMo", "Apache-2.0"),
    ("EleutherAI", "EleutherAI", "United States", 2020, "institute", None, "yes",
     "Pythia, GPT-NeoX", "Pythia", "Apache-2.0"),
    ("BigScience", "bigscience", "International", 2021, "institute", None, "yes",
     "BLOOM", "BLOOM-176B", "RAIL"),
    ("LMSYS", "lmsys", "United States", 2023, "institute", None, "yes",
     "Vicuna, Chatbot Arena", "Vicuna", "Apache-2.0"),
    ("Hugging Face", "HuggingFaceTB", "United States", 2016, "infrastructure", None, "yes",
     "SmolLM", "SmolLM3", "Apache-2.0"),
    ("LAION", "laion", "Germany", 2019, "institute", None, "yes",
     "datasets (LAION-5B)", "LAION-5B", "CC-BY"),
    ("Modular", None, "United States", 2022, "infrastructure", None, "no",
     "Mojo, MAX", None, None),
    ("Groq", None, "United States", 2016, "hardware_lab", None, "no",
     "LPU inference", None, None),
    ("Cerebras", None, "United States", 2016, "hardware_lab", None, "yes",
     "CS-3, inference", None, None),
    ("SambaNova", None, "United States", 2017, "hardware_lab", None, "yes",
     "SN40L", None, None),
    ("Google Research", "google-research", "United States", 2011, "institute", "Alphabet", "yes",
     "BERT, T5", "T5", "Apache-2.0"),
    # ---- China ----
    ("DeepSeek", "deepseek-ai", "China", 2023, "frontier_open", None, "yes",
     "DeepSeek V4, R2", "DeepSeek-V3", "MIT"),
    ("Alibaba Qwen", "Qwen", "China", 2023, "frontier_open", "Alibaba", "yes",
     "Qwen3.5", "Qwen3", "Apache-2.0"),
    ("Moonshot AI", "moonshotai", "China", 2023, "frontier_open", None, "yes",
     "Kimi K2", "Kimi K2", "Modified MIT"),
    ("Zhipu AI (Z.ai)", "zai-org", "China", 2019, "frontier_open", None, "yes",
     "GLM-5", "GLM-4.5", "MIT"),
    ("MiniMax", "MiniMaxAI", "China", 2021, "frontier_open", None, "yes",
     "MiniMax-M2", "MiniMax-M2", "MIT"),
    ("01.AI", "01-ai", "China", 2023, "open_weight", None, "yes",
     "Yi", "Yi-34B", "Apache-2.0"),
    ("StepFun", "stepfun-ai", "China", 2023, "open_weight", None, "yes",
     "Step-3", "Step-3", "Apache-2.0"),
    ("Baichuan", "baichuan-inc", "China", 2023, "open_weight", None, "yes",
     "Baichuan-M2", "Baichuan 2", "Apache-2.0"),
    ("Baidu", None, "China", 2000, "frontier_closed", None, "no",
     "ERNIE 5", None, None),
    ("ByteDance Seed", "ByteDance-Seed", "China", 2023, "frontier_closed", "ByteDance", "partial",
     "Doubao, Seed", "Seed-OSS", "Apache-2.0"),
    ("Tencent Hunyuan", "Tencent-Hunyuan", "China", 2023, "frontier_open", "Tencent", "yes",
     "Hunyuan-Large", "Hunyuan 7B", "Tencent license"),
    ("Huawei", None, "China", 1987, "frontier_closed", None, "no",
     "Pangu 5", None, None),
    ("SenseTime", None, "China", 2014, "application", None, "partial",
     "SenseNova", None, None),
    ("iFlytek", None, "China", 1999, "application", None, "no",
     "Spark", None, None),
    ("Shanghai AI Lab", "internlm", "China", 2020, "institute", None, "yes",
     "InternLM, InternVL", "InternLM2.5", "Apache-2.0"),
    ("BAAI", "BAAI", "China", 2018, "institute", None, "yes",
     "BGE, Emu", "BGE-M3", "MIT"),
    ("Xiaomi", "XiaomiMiMo", "China", 2024, "open_weight", "Xiaomi", "yes",
     "MiMo", "MiMo-7B", "Apache-2.0"),
    # ---- Korea / Japan / Asia ----
    ("Naver", None, "South Korea", 1999, "frontier_closed", None, "no",
     "HyperCLOVA X", None, None),
    ("Kakao", None, "South Korea", 2010, "frontier_closed", None, "no",
     "KoGPT", None, None),
    ("Upstage", "upstage", "South Korea", 2020, "open_weight", None, "yes",
     "Solar Pro", "Solar", "Apache-2.0"),
    ("LG AI Research", "LGAI-EXAONE", "South Korea", 2020, "open_weight", "LG", "yes",
     "EXAONE 4", "EXAONE", "EXAONE license"),
    ("SK Telecom", None, "South Korea", 1984, "frontier_closed", None, "no",
     "A.X", None, None),
    ("Sakana AI", None, "Japan", 2023, "institute", None, "partial",
     "evolutionary merging", None, None),
    ("Preferred Networks", None, "Japan", 2014, "application", None, "yes",
     "PLaMo", "PLaMo", "Apache-2.0"),
    ("Rinna", "rinna", "Japan", 2014, "open_weight", None, "yes",
     "Rinna", "rinna/japanese-gpt2", "MIT"),
    ("LLM-jp", "llm-jp", "Japan", 2023, "institute", None, "yes",
     "LLM-jp", "llm-jp-3", "Apache-2.0"),
    ("Fujitsu", None, "Japan", 1935, "enterprise", None, "partial",
     "Fugaku-LLM", None, None),
    ("SoftBank", None, "Japan", 1981, "frontier_closed", None, "no",
     "investment / OpenAI alliance", None, None),
    ("TSMC", None, "Taiwan", 1987, "hardware_lab", None, "no",
     "AI accelerators", None, None),
    ("MediaTek", None, "Taiwan", 1997, "hardware_lab", None, "no",
     "edge AI chips", None, None),
    ("TAIDE", "taide", "Taiwan", 2023, "institute", None, "yes",
     "TAIDE", "TAIDE-LX", "Apache-2.0"),
    ("AI Singapore", "aisingapore", "Singapore", 2017, "institute", None, "yes",
     "SEA-LION", "SEA-LION", "Apache-2.0"),
    ("G42 / TII", "tiiuae", "United Arab Emirates", 2021, "institute", "G42", "yes",
     "Falcon 3", "Falcon", "TII license"),
    ("MBZUAI", "MBZUAI", "United Arab Emirates", 2019, "institute", None, "yes",
     "K2, Jais", "K2", "Apache-2.0"),
    ("Sarvam AI", "sarvamai", "India", 2023, "open_weight", None, "yes",
     "Sarvam-M", "Sarvam-M", "Apache-2.0"),
    ("Krutrim", None, "India", 2023, "frontier_closed", "Ola", "no",
     "Krutrim-2", None, None),
    ("BharatGen", None, "India", 2024, "institute", None, "partial",
     "BharatGen", None, None),
    ("VinAI", None, "Vietnam", 2019, "institute", "Vingroup", "partial",
     "ViGPT", None, None),
    # ---- Europe ----
    ("Aleph Alpha", "Aleph-Alpha", "Germany", 2019, "frontier_closed", None, "partial",
     "Pharia", "Pharia-1", "Apache-2.0"),
    ("DeepL", None, "Germany", 2017, "application", None, "no",
     "translation models", None, None),
    ("Kyutai", "kyutai", "France", 2023, "institute", None, "yes",
     "Moshi", "Moshi", "Apache-2.0"),
    ("LightOn", "LightOnIO", "France", 2016, "open_weight", None, "yes",
     "Paradigm", "Paradigm", "Apache-2.0"),
    ("Mila", None, "Canada", 1993, "institute", None, "partial",
     "research", None, None),
    ("Vector Institute", None, "Canada", 2017, "institute", None, "partial",
     "research", None, None),
    ("AI Sweden", None, "Sweden", 2019, "institute", None, "yes",
     "GPT-SW3", "GPT-SW3", "Apache-2.0"),
    ("TurkuNLP", "TurkuNLP", "Finland", 2019, "institute", None, "yes",
     "Poro", "Poro", "Apache-2.0"),
    ("Silo AI", None, "Finland", 2017, "application", "AMD (acquired)", "partial",
     "Poro, enterprise", None, None),
    ("SpeakLeash", None, "Poland", 2022, "institute", None, "yes",
     "Bielik", "Bielik", "Apache-2.0"),
    ("Swiss AI Initiative", "swiss-ai", "Switzerland", 2023, "institute", None, "yes",
     "Apertus", "Apertus", "Apache-2.0"),
    ("GPT-NL", None, "Netherlands", 2024, "institute", None, "yes",
     "GPT-NL", None, None),
    ("Yandex", None, "Russia", 1997, "frontier_closed", None, "partial",
     "YaLM", None, None),
    ("Sber", None, "Russia", 1991, "frontier_closed", None, "no",
     "GigaChat", None, None),
    ("T-Bank (T-Technologies)", None, "Russia", 2006, "open_weight", None, "yes",
     "T-lite", "T-lite", "Apache-2.0"),
    # ---- tools / hosting (no frontier model) ----
    ("Ollama", None, "United States", 2023, "infrastructure", None, "no",
     "local model runner", None, None),
    ("vLLM", None, "United States", 2023, "infrastructure", None, "no",
     "inference engine", None, None),
    ("Replicate", None, "United States", 2019, "infrastructure", None, "no",
     "hosting", None, None),
    ("Scale AI", None, "United States", 2016, "data", None, "no",
     "data labelling", None, None),
    ("Surge AI", None, "United States", 2020, "data", None, "no",
     "data labelling", None, None),
]


def hf_stats(org: str) -> dict:
    out = {"hf_org": org, "hf_models": None, "hf_top_model": None,
           "hf_top_downloads": None, "hf_license": None}
    for attempt in range(3):
        try:
            r = requests.get("https://huggingface.co/api/models",
                             params={"author": org, "sort": "downloads",
                                     "direction": -1, "limit": 100},
                             headers={"User-Agent": "earth-atlas-research/1.0"},
                             timeout=30)
            if r.status_code != 200:
                return out
            models = r.json()
            out["hf_models"] = len(models)
            if models:
                top = models[0]
                out["hf_top_model"] = top.get("modelId")
                out["hf_top_downloads"] = top.get("downloads")
                tags = top.get("tags") or []
                lic = [t.split(":", 1)[1] for t in tags if t.startswith("license:")]
                out["hf_license"] = lic[0] if lic else None
            return out
        except Exception:  # noqa: BLE001
            time.sleep(1.5)
    return out


def main() -> None:
    df = pd.DataFrame(LABS, columns=["lab", "hf_org", "country", "founded", "category",
                                     "parent", "open_weights", "flagship_models",
                                     "notable_open_model", "license"])

    stats = []
    for org in df["hf_org"].dropna().unique():
        print("  hf:", org)
        stats.append(hf_stats(org))
        time.sleep(0.1)
    sdf = pd.DataFrame(stats)
    sdf.to_csv(DATA / "hf_stats.csv", index=False, encoding="utf-8-sig")

    out = df.merge(sdf, on="hf_org", how="left")

    uni_path = BASE.parent / "startups" / "data" / "startups_global.csv"
    out["valuation_busd_cb"] = None
    if uni_path.exists():
        uni = pd.read_csv(uni_path)[["company", "valuation_busd"]]
        umap = {str(c).lower(): v for c, v in zip(uni["company"], uni["valuation_busd"])}
        out["valuation_busd_cb"] = out["lab"].str.lower().map(umap)
    out.to_csv(DATA / "ai_labs.csv", index=False, encoding="utf-8-sig")

    print(f"\nlabs: {len(out)}")
    print(out["category"].value_counts().to_string())
    print("\nby country:")
    print(out["country"].value_counts().head(12).to_string())
    print("\nopen weights:", out["open_weights"].value_counts().to_string())


if __name__ == "__main__":
    main()
