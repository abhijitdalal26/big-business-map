# Sectors — quotable facts (Forbes Global 2000, 2025 list, FY2024 financials)

Source for everything below: data/global2000_2025.csv (recomputed in site/build/sectors.py) and World Bank WDI (data/world_macro.csv). The page is site/sectors.html.

## Headline facts
1. **Financials take 23.5% of Global 2000 revenue, 34.1% of profit and only 20.6% of market value.** That works out to $1.66T profit on $12.4T revenue.
2. **Technology takes 8.9% of revenue, 16.7% of profit and 26.8% of market value ($24.5T).** The −10.1 pp gap between its profit share and its market-value share is the largest of any sector.
3. **The market pays 30× profit for tech and 11.3× for financials** (aggregate P/E). On that basis a dollar of tech profit is "worth" about 2.7 dollars of bank profit.
4. **Banking alone (327 firms) books 12.4% of revenue and 21.9% of profit.** It is the biggest single industry on both counts.
5. **The whole list trades at 1.73× sales and 18.7× profit.** Semiconductors trade at 8.05× sales and Software at 6.7×. Food Markets (grocers) and Trading Companies trade at about 0.5×.
6. **The median Global 2000 firm keeps 10.1 cents of each revenue dollar as net profit.** Financials have the highest sector median (15.7%) and Construction & Real Estate the lowest (4.3%). 128 of the 2,000 firms made a loss.
7. **Grocers work on a 2.2% margin but turn their assets over 1.59× a year. Software earns 22.4% on 0.45× turnover.** Their ROA is 3.5% and 10.1%. ROA = margin × asset turnover, and this is an exact identity.
8. **Banks earn a 16.2% margin but turn their assets over only 0.052×, so their ROA is 0.85%.** They make their money through leverage.
9. **Telecom & Media has the most loss-makers (22% of firms).** Materials & Chemicals is next (14.5%), and Financials has the fewest (1.9%).
10. **Concentration (HHI on revenue inside the Global 2000):** Media scores 1,252, with Comcast, Disney and Charter holding 54% of the industry's revenue. Health-care equipment & services scores 1,137, with the US drug wholesalers McKesson, Cencora and Cardinal holding 55%. Banking is the most fragmented big industry: HHI 134, top 3 = 11%. HHI for the whole list is just 21.
11. **Retail & Wholesale:** Walmart, Amazon and CVS hold 40% of the revenue of 80 listed retail giants.
12. **Consumer & Retail employs 25.5% of the 92.6M Global 2000 workers on 17.2% of revenue.** Energy & Utilities employs 4.9% of the workers on 12.9% of revenue.
13. **Aerospace & Defense has the highest aggregate P/E of any industry with 5+ firms (44.8×).** Two things push it up: the re-armament premium and Boeing's losses, which shrink the profit side of the ratio.
14. **Agriculture is 4.1% of world GDP but 26.1% of world employment (2024), about 964M people. Its share of Global 2000 revenue is about 0%:** no Forbes industry is farming. The closest firms are grain and oilseed traders (ADM, Bunge, Wilmar, Olam) and fertiliser makers (Nutrien).
15. **Agriculture's share of world jobs fell from 39% in 2000 to 26% in 2024.**
16. **Industry is 25% of world GDP (manufacturing 15%) but 48% of Global 2000 revenue.** Services are 63% of GDP but 52% of revenue. Scale industries (oil, cars, chips, steel) produce giants; most services are fragmented into small firms.
17. **India has 70 Global 2000 firms with $1.3T revenue (2.5% of the list).** Financials make up 33% of that revenue and Energy & Utilities 30%, which is +9.9 pp and +17.2 pp over the global mix. Technology is just 6% and Healthcare under 1%.
18. **Country DNA:** China is +13.8 pp overweight Construction (China State Construction, China Railway). Germany is +19.2 pp overweight Consumer & Retail, where Forbes files the carmakers. The US is overweight Healthcare (+5.2 pp) and Technology (+4.1 pp).
19. **Technology by country:** the US holds 54% of Global 2000 tech revenue, Taiwan 12%, China 10% and India 2% (TCS, Infosys, HCLTech).

## Story angles
- "Where profit is made is not where value is priced": banks and oil are under-priced compared with their profits, and tech is over-priced.
- "The 2-cent business": grocers and commodity traders move trillions on margins of about 2%.
- "Clubs of three": drug wholesaling, cable/media, smartphones and chips. India parallels: telecom, cement, aviation.
- "The economy Forbes can't see": about a billion farm workers, plus informal firms, appear in no ranking.
- "India Inc. is a bank with an oil refinery attached."

## Caveats
- Bank "revenue" is gross (interest + fees). That inflates Financials' revenue share.
- Forbes classifications can be odd. UnitedHealth is filed under Insurance; Elevance and Centene under Pharma & Biotech; Fannie Mae and Freddie Mac under Business Services; BASF under Capital Goods. Check the company before quoting an industry fact.
- Market value is a spring-2025 snapshot. Profits are single-year net income, including one-offs.
- HHI and top-3 shares are measured within the Global 2000 only. They are not market shares.
- Comparing the World Bank and Forbes means comparing value added (GDP) with gross revenue. Use it for direction only. The agriculture/industry/services bucket mapping is ours.
- Unlisted SOEs (State Grid) and private firms (Cargill, Mars) are absent from these figures.
- These numbers are recomputed from company rows, so they can differ by 0.1–0.2 pp from data_analysis/output tables.
- The India farm-employment figure (about 43–46% of workers) comes from outside this dataset (World Bank/PLFS). Verify it before quoting.
