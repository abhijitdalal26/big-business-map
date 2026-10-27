# The world's stock markets — writer's notes (markets.html)

Dates: company/exchange figures = CompaniesMarketCap, **Oct 2026**. Country totals/history = World Bank/WFE, **end-2024**. Rebuild: `python site/build/markets.py`.

## Quotable facts
1. The World Bank counts **47,980** listed domestic companies in 2024, worth **$115.1T**, or **129% of world GDP**.
2. That count has stayed between ~40,000 and ~52,000 since 2000 (39,890 in 2000, 52,292 in 2021). Value went from $31.1T (2003) to $115.1T (2024).
3. The 9,780 companies we track on 60 exchanges sum to **~$148.5T**. That is about a fifth of all listings by count but nearly all of the value.
4. **Nasdaq ($46.1T) + NYSE ($34.2T)** hold over half of all tracked value. Tokyo, the #3, is $7.8T.
5. Nasdaq's top 10 are 63% of its value; NYSE's top 10 are 21%.
6. **15 companies are worth $1T+** ($36.2T combined). 12 are American; the others are TSMC, Saudi Aramco and Samsung.
7. NVIDIA ($5.2T) is worth more than all NSE-tracked companies combined ($3.8T), and more than every country's 2024 GDP except the US and China.
8. Top 50: 37 are American and 19 are technology companies. There is no Indian company in it.
9. **The top 1% of tracked listings hold 43% of the value**; the top 10 companies hold 20%, the top 10% hold 79%, and the bottom half holds 2%.
10. 6,244 tracked companies are worth over $1B, 2,006 over $10B, 232 over $100B and 15 over $1T. The median tracked company is worth ~$1.8B.
11. **India: $5.13T market cap, 136% of GDP** (WB 2024), up from 76% in 2019. India has **4.5% of world market value vs 3.4% of world GDP**.
12. China's market is only 63% of its GDP. India's market has been deeper than China's (as % of GDP) every year since 2008.
13. US: 212% of GDP, about 54% of world market value with 26% of world GDP.
14. NSE is #9 among exchanges by value ($3.84T) and #4 by number of tracked companies (564). India is #8 by country (tracked).
15. Reliance ($171B) is India's largest company and about #112 in the world. 4 Indian companies are over $100B, against 116 in the US.
16. Valuation (Forbes 2000): technology has a median 4.2× sales / 26× profit, financials 1.5× / 10×, real estate 0.6× sales.
17. By country, India has the highest median P/E among large markets (~21×, Forbes 2000), vs the US ~19×, Japan ~13×, China ~12× and Korea ~6×.
18. US listed companies roughly halved, from 8,090 (1996) to 4,010 (2024), because of M&A, buyouts and companies staying private longer.

## Story angles
- "Wide vs deep": India and Japan have many listings; Taiwan and Saudi have a few giants (TSMC is 54% of Taiwan's tracked value).
- Will India get a $1T company? Reliance would need ~6× growth.
- Is the market an AI bet? Chipmakers are in or near the $1T club.
- India premium: high P/E plus steady domestic SIP inflows. Is it growth or froth?
- The shrinking US listed universe vs the boom in private capital.
- The Buffett indicator: the world is at 129%, near its 2020 peak.

## Caveats
- **Tracked ≠ total.** Exchange company counts are coverage (e.g. BSE shows 5, but BSE lists 5,000+). Never call $148T "world market cap".
- Two dates (Oct 2026 vs end-2024). Don't mix them without saying so.
- **WB series break in 2019**: India 6,988 → 1,955 and China 3,584 → 12,730 look like reporting changes. They inflate the world 2019–21 count.
- ADRs are attributed to home exchanges (TSMC → Taipei; also Arm/Linde → London, a judgement call).
- Market cap/GDP compares a stock with a flow. It is inflated by foreign listings (Hong Kong ~1,100%, Switzerland, Bermuda).
- Sector labels: Forbes match 54% of value, manual 22%, keyword 17%, unclassified 7%.
- SpaceX shows as Nasdaq-listed at $1.9T in the Oct 2026 snapshot. Verify before quoting.
- P/S is only comparable within a sector. P/E excludes loss-makers.
