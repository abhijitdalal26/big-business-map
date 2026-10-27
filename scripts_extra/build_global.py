import csv, re
ROOT = 'C:/Users/abhijit/Pictures/articles/forbes_500/'
WP = 'https://en.wikipedia.org/wiki/List_of_largest_private_non-governmental_companies_by_revenue'
# name, revenue US$bn, year label, country, ownership, sector
R = """Vitol|400|2023|Switzerland|private|Commodity trading
Suning Holdings Group|102.9|2019/20|China|private|Retail & conglomerate
Aldi|120.96|2023|Germany|family|Grocery retail
E.Leclerc|102.98|2023|France|co-op|Grocery retail
Amer International Group|88.9|2019|China|private|Commodities & metals trading
HNA Group|88.5|2018|China|private|Aviation & conglomerate
ByteDance|85.2|2022|China|private|Internet & media
Deloitte|67.2|2024|United Kingdom|private|Professional services
Ineos|65|2021|United Kingdom|private|Chemicals
CMA CGM|56|2021|France|family|Shipping & logistics
PwC|55.2|2024|United Kingdom|private|Professional services
Auchan Holding|54.7|2019|France|family|Grocery retail
EY|51.2|2024|United Kingdom|private|Professional services
Ingram Micro|47.2|2019|United States|private|IT distribution
SPAR|46.98|2022|Netherlands|private|Grocery retail
Cedar Holdings Group|41.3|2019|China|private|Trading & logistics
KPMG|38.4|2024|United Kingdom|private|Professional services
Tech Data|37|2019/20|United States|private|IT distribution
Mars|37|2019|United States|family|Food & confectionery
Les Mousquetaires|35.9|2019|France|co-op|Grocery retail
Yango Longking Group|35.9|2019|China|private|Real estate & conglomerate
Reyes Holdings|35|2019|United States|family|Beverage distribution
GuideWell|32.9|2024|United States|mutual|Health insurance
Wanda Group|31.7|2018|China|private|Real estate & entertainment
H-E-B|31.2|2018/19|United States|family|Grocery retail
Phoenix Pharma|30.5|2019/20|Germany|family|Pharma wholesale
Pilot Flying J|29.5|2019|United States|private|Fuel & travel centers
Asda|29.39|2024|United Kingdom|private|Grocery retail
Xinjiang Guanghui Industry Investment Group|28.7|2019|China|private|Energy & conglomerate
GS Caltex|28.5|2019|South Korea|private|Oil refining
Huaxia Life Insurance|28.49|2019|China|private|Insurance
EG Group|28.3|2023|United Kingdom|private|Fuel retail
C&S Wholesale Grocers|25.8|2018/19|United States|private|Grocery wholesale
Ferrero|22.4|2025|Italy|family|Confectionery
Bechtel|21.8|2019|United States|private|Engineering & construction
Boehringer Ingelheim|21.3|2019|Germany|family|Pharmaceuticals
Cox Enterprises|21.1|2019|United States|family|Media & automotive services
Greenergy|21.1|2019|United Kingdom|private|Biofuels & fuel distribution
Fidelity Investments|20.9|2019|United States|family|Asset management
Love's Travel Stops & Country Stores|20.6|2019|United States|family|Fuel & travel centers
Southern Glazer's Wine & Spirits|20|2019|United States|private|Beverage distribution
Systeme U|19.6|2019|France|co-op|Grocery retail
Wakefern Food Corporation|19.6|2022/23|United States|co-op|Grocery wholesale
Swire|18.4|2024|United Kingdom|family|Conglomerate
John Lewis Partnership|18.1|2024|United Kingdom|employee-owned|Retail
Meijer|18.1|2019/20|United States|family|Retail
Allied Universal|18.0|2020|United States|private|Security services
JM Family Enterprises|17.7|2019|United States|family|Automotive distribution
Octopus Group|17.2|2023|United Kingdom|private|Energy retail & investment
World Wide Technology|17.0|2022|United States|private|IT solutions
Subway|16.1|2019|United States|private|Restaurants (system sales)
Chanel|15.6|2021|France|family|Luxury goods
Gordon Food Service|15.5|2018/19|United States|family|Food distribution
Inspire Brands|14.6|2020|United States|private|Restaurants
Turner Construction|14.4|2020|United States|subsidiary|Construction
Land O'Lakes|13.95|2020|United States|co-op|Dairy & agriculture
Medline Industries|13.9|2019|United States|family|Medical supplies
Trader Joe's|13.7|2019|United States|subsidiary|Grocery retail
Allegis Group|13.6|2019|United States|private|Staffing
Guardian Life Insurance Company of America|13.56|2020|United States|mutual|Insurance
OpenAI|13.1|2025|United States|private|AI
American Family Insurance Group|13.07|2020|United States|mutual|Insurance
Wawa|13|2019|United States|private|Convenience retail
Kingston Technology|12.8|2019|United States|private|Memory products
RaceTrac|12.6|2019|United States|family|Fuel & convenience retail
Kiewit Corporation|12.46|2020|United States|employee-owned|Construction
Farmers Insurance Exchange|11.87|2020|United States|mutual|Insurance
ABC Supply|11.6|2019|United States|private|Building products distribution
Hearst Corporation|11.5|2019|United States|family|Media
Decathlon|11.4|2020|France|family|Sporting goods retail
Chick-fil-A|11.3|2019|United States|family|Restaurants
QuikTrip|11.2|2019/20|United States|private|Convenience retail
Wegmans|11.2|2021|United States|family|Grocery retail
Mutual of Omaha Insurance|11.1|2020|United States|mutual|Insurance
Republic National Distributing Company|11.0|2019|United States|private|Beverage distribution
Graybar|11.0|2023|United States|employee-owned|Electrical distribution
SHI International Corp|10.7|2019|United States|private|IT reseller
Menards|10.7|2019|United States|family|Home improvement retail
Bloomberg|10.5|2019|United States|private|Financial data & media
S. C. Johnson & Son|10.5|2019/20|United States|family|Consumer products
McKinsey|10.5|2019|United States|private|Consulting
Whiting-Turner Contracting Company|10.3|2019|United States|private|Construction
Jones Financial (Edward Jones)|10.17|2020|United States|private|Brokerage
Hy-Vee|10.1|2019|United States|employee-owned|Grocery retail
Calpine|10.1|2019|United States|private|Power generation
Pacific Life|10.06|2020|United States|mutual|Insurance
Schwarz Group|180.6|2023|Germany|family|Grocery retail (Lidl, Kaufland)
Robert Bosch|98.92|2023|Germany|private|Auto parts & industrial tech
Swire|18.4|2024|United Kingdom|family|Conglomerate
Auchan Holding|54.7|2019|France|family|Grocery retail
Heraeus|25.1|2019|Germany|family|Precious metals & technology
Coop Group|29.49|2019|Switzerland|co-op|Grocery retail
Mercadona|28|2019|Spain|private|Grocery retail
Louis Dreyfus Company|33.8|2019|France|family|Agri commodities
Groupe Casino|32.1|2021|France|listed-parent|Grocery retail
Achmea|27.6|2019|Netherlands|co-op|Insurance
Hailiang Group|27.2|2019|China|private|Copper & education
"""
SKIP_LISTED = {'Groupe Casino', 'Swire', 'Robert Bosch', 'Tech Data', 'HNA Group'}
# Additional state-owned unlisted, from separate Wikipedia pages
EXTRA = [
 ('Kuwait Petroleum Corporation', 97.9, 'FY2024/25', 'Kuwait', 'state', 'Oil & gas', 'Kuwait City', '', 'https://en.wikipedia.org/wiki/Kuwait_Petroleum_Corporation', 'medium'),
 ('Sonatrach', 77, '2023', 'Algeria', 'state', 'Oil & gas', 'Algiers', '', 'https://en.wikipedia.org/wiki/Sonatrach', 'medium'),
 ('QatarEnergy', 52, '2022', 'Qatar', 'state', 'Oil & gas', 'Doha', '', 'https://en.wikipedia.org/wiki/QatarEnergy', 'low'),
]
def k(s): return re.sub(r'[^a-z0-9]', '', s.lower())
have = {}
for fn, col in (('data/companies_master.csv', 'company'), ('data/fortune_g500_2025.csv', 'company'), ('data/private_us_2025.csv', 'company'), ('data/startups_2025.csv', 'company')):
    try:
        for r in csv.DictReader(open(ROOT + fn, encoding='utf-8-sig')):
            have[k(r[col])] = fn
    except Exception as e:
        print('skip', fn, e)
cols = ['company', 'country', 'ownership', 'sector', 'hq_city', 'revenue_musd', 'revenue_year', 'employees', 'source', 'url', 'confidence']
out = []; seen = set(); dups = []
def stale(y):
    m = re.findall(r'\d{4}', y)
    return int(m[0]) <= 2021 if m else True
for line in R.strip().split('\n'):
    n, rev, y, cty, own, sec = line.split('|')
    if n in SKIP_LISTED or k(n) in seen: continue
    seen.add(k(n))
    hit = [fn for kk, fn in have.items() if kk == k(n) or (len(kk) > 6 and (kk in k(n) or k(n) in kk)) and k(n)[:6] == kk[:6]]
    if hit:
        dups.append((n, hit[0])); continue
    out.append([n, cty, own, sec, '', round(float(rev) * 1000), y, '',
                'Wikipedia: List of largest private non-governmental companies by revenue (figures from company reports/press as cited there)', WP,
                'low' if stale(y) else 'medium'])
for e in EXTRA:
    n, rev, y, cty, own, sec, city, emp, url, conf = e
    if k(n) in have: dups.append((n, 'have')); continue
    out.append([n, cty, own, sec, city, round(rev * 1000), y, emp, 'Wikipedia company page infobox', url, conf])
with open(ROOT + 'data/extra/private_global.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(cols); w.writerows(out)
print(len(out), 'dups skipped', len(dups)); print(dups)
