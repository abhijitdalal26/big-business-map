"""Every notable company training AI models, by modality.

Supersedes the 99-lab registry with a ~200-company map across:
LLM, video, image, audio/music, 3D/world models, robotics, autonomy, biology,
code, search/agents, infrastructure, chips, data, and national/big-tech in-house.

Where  : ai_labs/data/ai_companies.csv
Journs : CB Insights valuation (private marks) joined by name where available.
Funding is deliberately left blank where not verifiable — no invented numbers.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

# (company, modality, category, country, founded, status, parent, open_weights, hf_org, ticker)
C = [
    # ---------- frontier LLMs, closed ----------
    ("OpenAI", "LLM / multimodal", "frontier_closed", "United States", 2015, "private", None, "partial", "openai", None),
    ("Anthropic", "LLM", "frontier_closed", "United States", 2021, "private", None, "no", None, None),
    ("xAI", "LLM", "frontier_closed", "United States", 2023, "private", None, "partial", None, None),
    ("Google DeepMind", "LLM / multimodal", "frontier_closed", "United Kingdom", 2010, "subsidiary", "Alphabet", "partial", "google", "GOOGL"),
    ("Microsoft AI", "LLM", "frontier_closed", "United States", 2023, "subsidiary", "Microsoft", "no", None, "MSFT"),
    ("Amazon AGI", "LLM", "frontier_closed", "United States", 2023, "subsidiary", "Amazon", "no", None, "AMZN"),
    ("Apple Intelligence", "LLM / on-device", "frontier_closed", "United States", 2024, "subsidiary", "Apple", "no", None, "AAPL"),
    ("Meta Superintelligence Labs", "LLM / multimodal", "frontier_open", "United States", 2013, "subsidiary", "Meta", "yes", "meta-llama", "META"),
    ("Baidu", "LLM", "frontier_closed", "China", 2000, "public", None, "no", None, "BIDU"),
    ("Huawei", "LLM / chips", "frontier_closed", "China", 1987, "private", None, "no", None, None),
    ("ByteDance Seed", "LLM / video", "frontier_closed", "China", 2023, "subsidiary", "ByteDance", "partial", "ByteDance-Seed", None),
    ("Tencent Hunyuan", "LLM / video", "frontier_open", "China", 2023, "subsidiary", "Tencent", "yes", "Tencent-Hunyuan", "TCEHY"),
    ("Samsung Research", "LLM / on-device", "frontier_closed", "South Korea", 2012, "subsidiary", "Samsung", "no", None, "SSNLF"),
    ("Naver", "LLM", "frontier_closed", "South Korea", 1999, "public", None, "no", None, "035420.KS"),
    ("Kakao", "LLM", "frontier_closed", "South Korea", 2010, "public", None, "no", None, "035720.KS"),
    ("SK Telecom", "LLM", "frontier_closed", "South Korea", 1984, "public", None, "no", None, "017670.KS"),
    ("Yandex", "LLM", "frontier_closed", "Russia", 1997, "public", None, "partial", None, "YDEX.ME"),
    ("Sber", "LLM", "frontier_closed", "Russia", 1991, "public", None, "no", None, "SBER.ME"),
    ("Cohere", "LLM / enterprise", "enterprise", "Canada", 2019, "private", None, "partial", "CohereLabs", None),
    ("AI21 Labs", "LLM", "enterprise", "Israel", 2017, "private", None, "partial", "ai21labs", None),
    ("Reka AI", "LLM / multimodal", "frontier_closed", "United States", 2022, "private", None, "partial", "RekaAI", None),
    ("Aleph Alpha", "LLM / sovereign", "frontier_closed", "Germany", 2019, "private", None, "partial", "Aleph-Alpha", None),
    ("Perplexity", "search / agents", "application", "United States", 2022, "private", None, "no", None, None),
    ("Character.AI", "LLM / consumer", "application", "United States", 2021, "private", "Google licence", "no", None, None),
    ("Inflection AI", "LLM / consumer", "application", "United States", 2022, "private", "Microsoft talent", "no", None, None),
    # ---------- frontier LLMs, open ----------
    ("Mistral AI", "LLM", "frontier_open", "France", 2023, "private", None, "partial", "mistralai", None),
    ("DeepSeek", "LLM / reasoning", "frontier_open", "China", 2023, "private", None, "yes", "deepseek-ai", None),
    ("Alibaba Qwen", "LLM / multimodal", "frontier_open", "China", 2023, "subsidiary", "Alibaba", "yes", "Qwen", "BABA"),
    ("Moonshot AI", "LLM", "frontier_open", "China", 2023, "private", None, "yes", "moonshotai", None),
    ("Zhipu AI (Z.ai)", "LLM", "frontier_open", "China", 2019, "private", None, "yes", "zai-org", None),
    ("MiniMax", "LLM / video", "frontier_open", "China", 2021, "private", None, "yes", "MiniMaxAI", None),
    ("01.AI", "LLM", "open_weight", "China", 2023, "private", None, "yes", "01-ai", None),
    ("StepFun", "LLM / multimodal", "open_weight", "China", 2023, "private", None, "yes", "stepfun-ai", None),
    ("Baichuan", "LLM", "open_weight", "China", 2023, "private", None, "yes", "baichuan-inc", None),
    ("Xiaomi", "LLM / devices", "open_weight", "China", 2024, "subsidiary", "Xiaomi", "yes", "XiaomiMiMo", "1810.HK"),
    ("Upstage", "LLM", "open_weight", "South Korea", 2020, "private", None, "yes", "upstage", None),
    ("LG AI Research", "LLM", "open_weight", "South Korea", 2020, "subsidiary", "LG", "yes", "LGAI-EXAONE", None),
    ("Sarvam AI", "LLM / Indic", "open_weight", "India", 2023, "private", None, "yes", "sarvamai", None),
    ("Krutrim", "LLM", "frontier_closed", "India", 2023, "private", "Ola", "no", None, None),
    ("Nous Research", "LLM", "open_weight", "United States", 2023, "private", None, "yes", "NousResearch", None),
    ("T-Bank (T-Technologies)", "LLM", "open_weight", "Russia", 2006, "public", None, "yes", None, "T.ME"),
    # ---------- research institutes ----------
    ("Allen Institute for AI (Ai2)", "LLM", "institute", "United States", 2014, "nonprofit", None, "yes", "allenai", None),
    ("EleutherAI", "LLM", "institute", "United States", 2020, "nonprofit", None, "yes", "EleutherAI", None),
    ("BigScience", "LLM", "institute", "International", 2021, "nonprofit", None, "yes", "bigscience", None),
    ("BAAI", "embeddings / LLM", "institute", "China", 2018, "nonprofit", None, "yes", "BAAI", None),
    ("Shanghai AI Lab", "LLM / vision", "institute", "China", 2020, "nonprofit", None, "yes", "internlm", None),
    ("LLM-jp", "LLM", "institute", "Japan", 2023, "nonprofit", None, "yes", "llm-jp", None),
    ("TAIDE", "LLM", "institute", "Taiwan", 2023, "nonprofit", None, "yes", "taide", None),
    ("AI Singapore", "LLM (SEA)", "institute", "Singapore", 2017, "nonprofit", None, "yes", "aisingapore", None),
    ("TII (Falcon)", "LLM", "institute", "United Arab Emirates", 2021, "nonprofit", "G42", "yes", "tiiuae", None),
    ("MBZUAI", "LLM", "institute", "United Arab Emirates", 2019, "nonprofit", None, "yes", "MBZUAI", None),
    ("BharatGen", "LLM", "institute", "India", 2024, "nonprofit", None, "partial", None, None),
    ("AI Sweden", "LLM", "institute", "Sweden", 2019, "nonprofit", None, "yes", None, None),
    ("TurkuNLP", "LLM", "institute", "Finland", 2019, "nonprofit", None, "yes", "TurkuNLP", None),
    ("SpeakLeash", "LLM", "institute", "Poland", 2022, "nonprofit", None, "yes", None, None),
    ("Swiss AI Initiative", "LLM", "institute", "Switzerland", 2023, "nonprofit", None, "yes", "swiss-ai", None),
    ("GPT-NL", "LLM", "institute", "Netherlands", 2024, "nonprofit", None, "yes", None, None),
    ("Kyutai", "speech / LLM", "institute", "France", 2023, "nonprofit", None, "yes", "kyutai", None),
    ("Mila", "research", "institute", "Canada", 1993, "nonprofit", None, "partial", None, None),
    ("Vector Institute", "research", "institute", "Canada", 2017, "nonprofit", None, "partial", None, None),
    ("Rinna", "LLM", "open_weight", "Japan", 2014, "private", None, "yes", "rinna", None),
    ("Sakana AI", "LLM", "institute", "Japan", 2023, "private", None, "partial", None, None),
    ("Preferred Networks", "LLM", "application", "Japan", 2014, "private", None, "yes", None, None),
    ("Hugging Face", "infrastructure", "infrastructure", "United States", 2016, "private", None, "yes", "HuggingFaceTB", None),
    # ---------- video / generative media ----------
    ("Runway", "video", "generative_media", "United States", 2018, "private", None, "no", None, None),
    ("Pika", "video", "generative_media", "United States", 2023, "private", None, "no", None, None),
    ("Luma AI", "video / 3D", "generative_media", "United States", 2021, "private", None, "no", None, None),
    ("Kuaishou (Kling)", "video", "generative_media", "China", 2011, "public", None, "partial", None, "1024.HK"),
    ("Genmo", "video", "generative_media", "United States", 2023, "private", None, "yes", None, None),
    ("Haiper", "video", "generative_media", "United Kingdom", 2022, "private", None, "no", None, None),
    ("Moonvalley", "video", "generative_media", "Canada", 2023, "private", None, "no", None, None),
    ("HeyGen", "video / avatars", "generative_media", "United States", 2020, "private", None, "no", None, None),
    ("Synthesia", "video / avatars", "generative_media", "United Kingdom", 2017, "private", None, "no", None, None),
    ("Captions", "video", "generative_media", "United States", 2020, "private", None, "no", None, None),
    ("Midjourney", "image", "generative_media", "United States", 2021, "private", None, "no", None, None),
    ("Stability AI", "image / audio", "generative_media", "United Kingdom", 2019, "private", None, "yes", "stabilityai", None),
    ("Black Forest Labs", "image", "generative_media", "Germany", 2024, "private", None, "yes", "black-forest-labs", None),
    ("Ideogram", "image", "generative_media", "Canada", 2022, "private", None, "no", None, None),
    ("Recraft", "image", "generative_media", "United States", 2022, "private", None, "no", None, None),
    ("Leonardo AI", "image", "generative_media", "Australia", 2022, "private", "Canva", "no", None, None),
    ("Adobe Firefly", "image / video", "generative_media", "United States", 2023, "subsidiary", "Adobe", "no", None, "ADBE"),
    ("ElevenLabs", "audio / voice", "generative_media", "United States", 2022, "private", None, "no", None, None),
    ("Cartesia", "audio / voice", "generative_media", "United States", 2023, "private", None, "partial", None, None),
    ("Hume AI", "audio / emotion", "generative_media", "United States", 2021, "private", None, "no", None, None),
    ("Sesame", "audio / voice", "generative_media", "United States", 2024, "private", None, "no", None, None),
    ("Suno", "music", "generative_media", "United States", 2022, "private", None, "no", None, None),
    ("Udio", "music", "generative_media", "United States", 2023, "private", None, "no", None, None),
    ("World Labs", "3D / world models", "generative_media", "United States", 2024, "private", None, "no", None, None),
    ("Decart", "world models", "generative_media", "Israel", 2023, "private", None, "no", None, None),
    ("Odyssey", "world models", "generative_media", "United States", 2023, "private", None, "no", None, None),
    ("Meshy", "3D", "generative_media", "United States", 2022, "private", None, "no", None, None),
    # ---------- robotics / embodied ----------
    ("Physical Intelligence", "robotics", "robotics", "United States", 2024, "private", None, "no", None, None),
    ("Figure AI", "robotics", "robotics", "United States", 2022, "private", None, "no", None, None),
    ("Skild AI", "robotics", "robotics", "United States", 2023, "private", None, "no", None, None),
    ("1X Technologies", "robotics", "robotics", "Norway", 2014, "private", None, "no", None, None),
    ("Agility Robotics", "robotics", "robotics", "United States", 2015, "private", None, "no", None, None),
    ("Covariant", "robotics", "robotics", "United States", 2017, "private", "Amazon (talent)", "no", None, None),
    ("Boston Dynamics", "robotics", "robotics", "United States", 1992, "subsidiary", "Hyundai", "no", None, None),
    ("Apptronik", "robotics", "robotics", "United States", 2016, "private", None, "no", None, None),
    ("Sanctuary AI", "robotics", "robotics", "Canada", 2018, "private", None, "no", None, None),
    ("Dexterity", "robotics", "robotics", "United States", 2017, "private", None, "no", None, None),
    # ---------- autonomy ----------
    ("Waymo", "autonomous driving", "autonomy", "United States", 2009, "subsidiary", "Alphabet", "no", None, None),
    ("Tesla (FSD / Optimus)", "autonomy / robotics", "autonomy", "United States", 2003, "public", None, "no", None, "TSLA"),
    ("Mobileye", "autonomy", "autonomy", "Israel", 1999, "public", "Intel", "no", None, "MBLY"),
    ("Wayve", "autonomy", "autonomy", "United Kingdom", 2017, "private", None, "no", None, None),
    ("Aurora", "autonomy", "autonomy", "United States", 2017, "public", None, "no", None, "AUR"),
    ("Nuro", "autonomy", "autonomy", "United States", 2016, "private", None, "no", None, None),
    ("Zoox", "autonomy", "autonomy", "United States", 2014, "subsidiary", "Amazon", "no", None, None),
    ("Waabi", "autonomy", "autonomy", "Canada", 2021, "private", None, "no", None, None),
    ("Kodiak Robotics", "autonomy", "autonomy", "United States", 2018, "private", None, "no", None, None),
    ("Gatik", "autonomy", "autonomy", "Canada", 2017, "private", None, "no", None, None),
    ("Motional", "autonomy", "autonomy", "United States", 2020, "private", "Hyundai/Aptiv", "no", None, None),
    # ---------- biology ----------
    ("Isomorphic Labs", "biology / drug discovery", "biology", "United Kingdom", 2021, "subsidiary", "Alphabet", "no", None, None),
    ("Recursion", "biology", "biology", "United States", 2013, "public", None, "no", None, "RXRX"),
    ("Insitro", "biology", "biology", "United States", 2018, "private", None, "no", None, None),
    ("Generate Biomedicines", "biology", "biology", "United States", 2018, "private", None, "no", None, None),
    ("EvolutionaryScale", "biology / protein", "biology", "United States", 2023, "private", None, "partial", None, None),
    ("Chai Discovery", "biology", "biology", "United States", 2024, "private", None, "no", None, None),
    ("Xaira Therapeutics", "biology", "biology", "United States", 2024, "private", None, "no", None, None),
    ("Latent Labs", "biology", "biology", "United Kingdom", 2024, "private", None, "no", None, None),
    ("Schrödinger", "biology / simulation", "biology", "United States", 1990, "public", None, "no", None, "SDGR"),
    ("Tempus AI", "health / data", "biology", "United States", 2015, "public", None, "no", None, "TEM"),
    # ---------- code / agents ----------
    ("Cognition", "code", "application", "United States", 2023, "private", None, "no", None, None),
    ("Anysphere (Cursor)", "code", "application", "United States", 2022, "private", None, "no", None, None),
    ("Windsurf (Codeium)", "code", "application", "United States", 2021, "private", None, "no", None, None),
    ("Replit", "code", "application", "United States", 2016, "private", None, "no", None, None),
    ("Poolside", "code", "application", "United States", 2023, "private", None, "partial", None, None),
    ("Magic", "code", "application", "United States", 2022, "private", None, "no", None, None),
    ("Augment Code", "code", "application", "United States", 2022, "private", None, "no", None, None),
    ("GitHub Copilot", "code", "application", "United States", 2021, "subsidiary", "Microsoft", "no", None, "MSFT"),
    ("Glean", "search / enterprise", "application", "United States", 2019, "private", None, "no", None, None),
    ("Sierra", "agents", "application", "United States", 2023, "private", None, "no", None, None),
    ("Decagon", "agents", "application", "United States", 2023, "private", None, "no", None, None),
    ("Imbue", "agents / LLM", "application", "United States", 2021, "private", None, "partial", None, None),
    ("Adept", "agents", "application", "United States", 2022, "private", "Amazon (acquired)", "no", None, None),
    # ---------- infrastructure / chips / data ----------
    ("Together AI", "infrastructure", "infrastructure", "United States", 2022, "private", None, "yes", "togethercomputer", None),
    ("Fireworks AI", "infrastructure", "infrastructure", "United States", 2022, "private", None, "no", None, None),
    ("Modal", "infrastructure", "infrastructure", "United States", 2021, "private", None, "no", None, None),
    ("Baseten", "infrastructure", "infrastructure", "United States", 2019, "private", None, "no", None, None),
    ("Replicate", "infrastructure", "infrastructure", "United States", 2019, "private", None, "no", None, None),
    ("Anyscale", "infrastructure", "infrastructure", "United States", 2019, "private", None, "no", None, None),
    ("NVIDIA", "chips / models", "chips", "United States", 1993, "public", None, "yes", "nvidia", "NVDA"),
    ("AMD", "chips", "chips", "United States", 1969, "public", None, "partial", None, "AMD"),
    ("Intel", "chips", "chips", "United States", 1968, "public", None, "no", None, "INTC"),
    ("Qualcomm", "chips / on-device", "chips", "United States", 1985, "public", None, "no", None, "QCOM"),
    ("Arm", "chips (IP)", "chips", "United Kingdom", 1990, "public", None, "no", None, "ARM"),
    ("TSMC", "chips (foundry)", "chips", "Taiwan", 1987, "public", None, "no", None, "TSM"),
    ("SK Hynix", "memory", "chips", "South Korea", 1983, "public", None, "no", None, "000660.KS"),
    ("Micron", "memory", "chips", "United States", 1978, "public", None, "no", None, "MU"),
    ("ASML", "lithography", "chips", "Netherlands", 1984, "public", None, "no", None, "ASML"),
    ("Groq", "inference chips", "hardware_lab", "United States", 2016, "private", None, "no", None, None),
    ("Cerebras", "chips / inference", "hardware_lab", "United States", 2016, "private", None, "yes", None, None),
    ("SambaNova", "chips / inference", "hardware_lab", "United States", 2017, "private", None, "yes", None, None),
    ("Graphcore", "chips", "hardware_lab", "United Kingdom", 2016, "subsidiary", "SoftBank", "no", None, None),
    ("Tenstorrent", "chips", "hardware_lab", "Canada", 2016, "private", None, "partial", None, None),
    ("Etched", "chips", "hardware_lab", "United States", 2022, "private", None, "no", None, None),
    ("d-Matrix", "chips", "hardware_lab", "United States", 2019, "private", None, "no", None, None),
    ("Scale AI", "data labelling", "data", "United States", 2016, "private", None, "no", None, None),
    ("Surge AI", "data labelling", "data", "United States", 2020, "private", None, "no", None, None),
    ("Mercor", "data / hiring", "data", "United States", 2023, "private", None, "no", None, None),
    ("Labelbox", "data labelling", "data", "United States", 2018, "private", None, "no", None, None),
    ("Turing", "data / services", "data", "United States", 2018, "private", None, "no", None, None),
    ("Appen", "data labelling", "data", "Australia", 1996, "public", None, "no", None, "APX.AX"),
    ("Databricks (Mosaic)", "enterprise / models", "enterprise", "United States", 2023, "private", "Databricks", "yes", "databricks", None),
    ("IBM Research", "enterprise / models", "enterprise", "United States", 1945, "public", "IBM", "yes", "ibm-granite", "IBM"),
    ("Salesforce AI Research", "enterprise / models", "enterprise", "United States", 2016, "public", "Salesforce", "yes", "Salesforce", "CRM"),
    ("Palantir", "enterprise AI", "application", "United States", 2003, "public", None, "no", None, "PLTR"),
    ("C3.ai", "enterprise AI", "application", "United States", 2009, "public", None, "no", None, "AI"),
    ("DataRobot", "enterprise AI", "application", "United States", 2012, "private", None, "no", None, None),
    ("H2O.ai", "enterprise AI", "application", "United States", 2011, "private", None, "partial", "h2oai", None),
    ("DeepL", "translation", "application", "Germany", 2017, "private", None, "no", None, None),
    ("Silo AI", "enterprise AI", "application", "Finland", 2017, "subsidiary", "AMD", "partial", None, None),
    ("VinAI", "LLM / automotive", "institute", "Vietnam", 2019, "subsidiary", "Vingroup", "partial", None, None),
]


def main() -> None:
    df = pd.DataFrame(C, columns=["company", "modality", "category", "country", "founded",
                                  "status", "parent", "open_weights", "hf_org", "ticker"])
    df = df.drop_duplicates("company").reset_index(drop=True)

    uni_path = BASE.parent / "startups" / "data" / "startups_global.csv"
    df["valuation_busd_cb"] = None
    if uni_path.exists():
        uni = pd.read_csv(uni_path)[["company", "valuation_busd"]]
        umap = {str(c).lower(): v for c, v in zip(uni["company"], uni["valuation_busd"])}
        df["valuation_busd_cb"] = df["company"].str.lower().map(umap)

    df.to_csv(DATA / "ai_companies.csv", index=False, encoding="utf-8-sig")
    print(f"companies: {len(df)}")
    print("\nby modality:")
    print(df["modality"].str.split(" / ").str[0].value_counts().head(15).to_string())
    print("\nby category:")
    print(df["category"].value_counts().to_string())
    print("\nby country (top 10):")
    print(df["country"].value_counts().head(10).to_string())
    print("\nopen weights:", df["open_weights"].value_counts().to_string())
    print(f"with CB valuation: {df.valuation_busd_cb.notna().sum()}")


if __name__ == "__main__":
    main()
