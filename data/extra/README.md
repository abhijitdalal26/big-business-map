# data/extra - big companies outside the Forbes Global 2000

Built 2026-10-27. Nothing outside data/extra/ was modified. Build scripts: scripts_extra/build_india.py, scripts_extra/build_global.py.

## Files
- india_unlisted.csv (185 rows): company, ownership, sector, hq_city, revenue_musd, revenue_year, employees, source, url, confidence
- private_global.csv (57 rows): same plus country
- raw_bs/: downloaded Business Standard PDF and its text/parsed extracts (untrusted raw data)

## Sources
India:
- Business Standard BS1000 "Unlisted Companies" table, 2025 edition (total revenue, year ended Mar 2023 or Mar 2024). About 176 rows with revenue >= Rs 8,500 cr. https://bsmedia.business-standard.com/_media/bs/data/general-file-upload/2025-03/unlisted-companies-tables-2025.pdf
- Hurun India / JM Financial Unlisted Gems 2026 as reported by Adda247 (Tata Electronics, Malabar, OfBusiness, Tata Passenger EV, SBI General, Haldiram).
- Wikipedia infoboxes: Reliance Retail (FY25), GCMMF/Amul (FY25), Tata Sons (standalone).
Global:
- Wikipedia "List of largest private non-governmental companies by revenue" (revenue years 2018-2025).
- Wikipedia infoboxes: Kuwait Petroleum Corp, Sonatrach, QatarEnergy.

## Method
- Revenue in Rs crore converted at approximate average INR/USD for the fiscal year (FY24 83.0, FY23 80.4, FY25 84.6, 81.7 where the year is unresolved). Rounded to whole US$ millions.
- Sector, ownership and hq_city are my classifications from general knowledge, not from the sources; hq_city is blank where unsure. Ownership "subsidiary" means an Indian unit of a foreign or other parent.
- Global rows were de-duplicated by normalised name against data/companies_master.csv, data/fortune_g500_2025.csv, data/private_us_2025.csv and data/startups_2025.csv (36 dropped, e.g. Mars, Bechtel, Heraeus, Mercadona, OpenAI). State firms already in the Fortune 2025 file were excluded.
- Dropped: Hexaware (listed 2025), WNS (entity unclear), HNA Group (defunct), Groupe Casino and Swire (listed parents), Tech Data (absorbed into listed TD Synnex), Robert Bosch (already present as Bosch Group).

## Caveats
- Employees are blank for nearly all rows (not in sources); never estimated.
- BS table: years past rank 41 could not be reliably aligned from the PDF layout, so revenue_year reads "FY2023 or FY2024 (unresolved)". Some power DISCOM figures are FY2023.
- Overlap: many Indian rows are subsidiaries whose revenue is also inside a foreign parent's consolidated figure (Samsung, Toyota, Microsoft, Apple etc.). Flipkart India, Flipkart Internet and Instakart are one group (separate legal entities). Reliance Retail, Tata Digital and Tata Sons overlap with other Tata/Reliance rows. Do not sum across rows.
- Several state DISCOMs/generators are tiny-by-world-standard utilities but pass the US$1B bar; filter by ownership if undesired.
- Amul figure is group-wide (Rs 90,000 cr) while GCMMF alone is smaller. Reliance Retail Wikipedia figure (Rs 3.31 lakh cr) differs from Hurun (~Rs 2.7 lakh cr). Nayara FY25 (about Rs 1.49-1.50 lakh cr) is newer than the FY24 figure used.
- Global list is dominated by stale revenues (2018-2020 = confidence low). Jio Platforms excluded because it appears to be mid-IPO (Oct 2026). Tata Sons is standalone only (confidence low).
- Gaps: not covered are Indian unlisted firms beyond BS1000 (e.g. Reliance Jio, Tata group unlisted arms, Hero MotoCorp promoters, Hurun list of 100), Fortune India 500 2026 itself (paywalled/unreachable), and most Asian/European privates and state-owned unlisted firms (ADNOC, NIOC, PDVSA, Tata, Samsung C&T affiliates, Japanese/Korean chaebol private arms, Mondragon, etc.). Confidence is "medium" for single secondary-source figures and "low" for stale (<=2021), unclear-year or standalone figures.
