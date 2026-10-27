"""Curated ownership labels for the Fortune Global 500 companies that are not in
the Forbes Global 2000.

Fortune's own "Company type" field is unreliable for this purpose (it labels
State Grid as "Private"), so the classification below is manual and auditable.
Categories:
  State-owned            - majority government ownership
  Private                - family, founder, foundation or employee owned
  Mutual / Cooperative   - owned by members/policyholders
  Public (outside Forbes)- listed, but absent from the Forbes 2000
  DUPLICATE              - same company as a Forbes entry under another name
"""

from __future__ import annotations

import pandas as pd

LABELS: dict[str, tuple[str, str | None]] = {
    # --- duplicates: Fortune name -> Forbes name ---
    "saudi-aramco": ("DUPLICATE", "Saudi Arabian Oil Company (Saudi Aramco)"),
    "royal-bank-of-canada": ("DUPLICATE", "RBC"),
    "nippon-telegraph-telephone": ("DUPLICATE", "Nippon Telegraph & Tel"),
    "deutsche-post-dhl-group": ("DUPLICATE", "Deutsche Post"),
    "peoples-insurance-co-of-china": ("DUPLICATE", "PICC"),
    "ups": ("DUPLICATE", "United Parcel Service"),
    "toronto-dominion-bank": ("DUPLICATE", "TD Bank Group"),
    "dai-ichi-life-holdings": ("DUPLICATE", "Dai-ichi Life Insurance"),
    "tjx": ("DUPLICATE", "TJX Cos"),
    "acs": ("DUPLICATE", "ACS Actividades de Construccion y Servicios"),
    "bank-of-montreal": ("DUPLICATE", "BMO"),
    "fomento-economico-mexicano": ("DUPLICATE", "Femsa"),
    "honeywell-international": ("DUPLICATE", "Honeywell International"),
    "phoenix-group-holdings": ("DUPLICATE", "Phoenix Group Holdings"),
    # --- state-owned ---
    "state-grid": ("State-owned", None),
    "china-national-petroleum": ("State-owned", None),
    "sberbank": ("State-owned", None),
    "electricite-de-france": ("State-owned", None),
    "yankuang-group": ("State-owned", None),
    "gazprom": ("State-owned", None),
    "china-baowu-steel-group": ("State-owned", None),
    "powerchina": ("State-owned", None),
    "shenhua-group": ("State-owned", None),
    "china-post-group": ("State-owned", None),
    "cofco": ("State-owned", None),
    "u-s-postal-service": ("State-owned", None),
    "pemex": ("State-owned", None),
    "china-faw-group": ("State-owned", None),
    "pertamina": ("State-owned", None),
    "vtb-bank": ("State-owned", None),
    "uniper": ("State-owned", None),
    "china-poly-group": ("State-owned", None),
    "jinchuan-group": ("State-owned", None),
    "petronas": ("State-owned", None),
    "shaanxi-coal-chemical-industry": ("State-owned", None),
    "xiamen-itg-holding-group": ("State-owned", None),
    "state-power-investment": ("State-owned", None),
    "china-united-network-communications": ("State-owned", None),
    "china-huaneng-group": ("State-owned", None),
    "caixa-economica-federal": ("State-owned", None),
    "zhejiang-communications-investment-group": ("State-owned", None),
    "sncf-group": ("State-owned", None),
    "china-general-technology": ("State-owned", None),
    "china-huadian": ("State-owned", None),
    "russian-railways": ("State-owned", None),
    "sinomach": ("State-owned", None),
    "chery-automobile": ("State-owned", None),
    "guangzhou-industrial-investment-holdings": ("State-owned", None),
    "shaanxi-yanchang-petroleum-group": ("State-owned", None),
    "dz-bank": ("State-owned", None),
    "guangdong-guangxin-holdings": ("State-owned", None),
    "hangzhou-iron-and-steel-group": ("State-owned", None),
    "energie-baden-wurttemberg": ("State-owned", None),
    "la-poste": ("State-owned", None),
    "hangzhou-industrial-investment-group": ("State-owned", None),
    "shenzhen-investment-holdings": ("State-owned", None),
    "cdp-group": ("State-owned", None),
    "qnb-group": ("State-owned", None),
    "guangzhou-municipal-construction-group": ("State-owned", None),
    "shudao-investment-group": ("State-owned", None),
    "china-electronics": ("State-owned", None),
    "china-datang": ("State-owned", None),
    "hunan-iron-amp-steel-group": ("State-owned", None),
    "guangzhou-pharmaceutical-holdings": ("State-owned", None),
    "perusahaan-listrik-negara": ("State-owned", None),
    "cfe": ("State-owned", None),
    "landesbank-baden-wurttemberg": ("State-owned", None),
    "gazprombank": ("State-owned", None),
    "ansteel-group": ("State-owned", None),
    "guangxi-investment-group": ("State-owned", None),
    "dongfeng-motor": ("State-owned", None),  # 2026 edition addition
    # --- mutual / cooperative ---
    "state-farm-insurance-cos": ("Mutual / Cooperative", None),
    "nippon-life-insurance": ("Mutual / Cooperative", None),
    "new-york-life-insurance": ("Mutual / Cooperative", None),
    "nationwide": ("Mutual / Cooperative", None),
    "edeka-zentrale": ("Mutual / Cooperative", None),
    "credit-mutuel-group": ("Mutual / Cooperative", None),
    "usaa": ("Mutual / Cooperative", None),
    "tiaa": ("Mutual / Cooperative", None),
    "liberty-mutual-insurance-group": ("Mutual / Cooperative", None),
    "meiji-yasuda-life-insurance": ("Mutual / Cooperative", None),
    "massachusetts-mutual-life-insurance": ("Mutual / Cooperative", None),
    "northwestern-mutual": ("Mutual / Cooperative", None),
    "migros-group": ("Mutual / Cooperative", None),
    "chs": ("Mutual / Cooperative", None),
    "rabobank": ("Mutual / Cooperative", None),
    # --- listed but outside the Forbes 2000 ---
    "christian-dior": ("Public (outside Forbes)", None),
    "energy-transfer-equity": ("Public (outside Forbes)", None),
    "plains-gp-holdings": ("Public (outside Forbes)", None),
    # --- private ---
    "trafigura-group": ("Private", None),
    "huawei-investment-holding": ("Private", None),
    "robert-bosch": ("Private", None),
    "zhejiang-geely-holding-group": ("Private", None),
    "ep-group": ("Private", None),
    "zhejiang-hengyi-group": ("Private", None),
    "xiamen-xiangyu-group": ("Private", None),
    "x5-retail-group": ("Private", None),
    "louis-dreyfus": ("Private", None),
    "taikang-insurance-group": ("Private", None),
    "susun-construction-group": ("Private", None),
    "zf-friedrichshafen": ("Private", None),
    "mercadona": ("Private", None),
    "magnit": ("Private", None),
    "hailiang-group": ("Private", None),
    "shanghai-delong-steel-group": ("Private", None),
}


def main() -> None:
    df = pd.DataFrame(
        [{"slug": s, "ownership": o, "duplicate_of": d} for s, (o, d) in LABELS.items()]
    )
    df.to_csv("data/fortune_labels.csv", index=False, encoding="utf-8-sig")
    print(f"wrote data/fortune_labels.csv rows={len(df)}")
    print(df["ownership"].value_counts().to_string())


if __name__ == "__main__":
    main()
