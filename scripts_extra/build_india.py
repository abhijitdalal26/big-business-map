import json, csv
ROOT = r'C:/Users/abhijit/Pictures/articles/forbes_500/'
big = json.load(open(ROOT + 'data/extra/raw_bs/big.json'))
S = 'state'; M = 'subsidiary'; F = 'family'; P = 'private'; C = 'co-op'
D = 'Power distribution'; G = 'Power generation'; T = 'Power transmission'
A = {  # rank:(ownership,sector,city)
1:(M,'Oil & gas refining','Mumbai'),2:(S,T,'Mumbai'),3:(M,'Consumer electronics','Gurugram'),4:(S,D,'Lucknow'),
5:(M,'Oil & gas refining','Bathinda'),6:(S,'Power utility','Chennai'),7:(S,'Power trading','Vadodara'),8:(M,'E-commerce','Bengaluru'),
9:(M,'IT services','Bengaluru'),10:(M,'Steel','Hazira'),11:(M,'Automobiles','Bidadi'),12:(S,D,'Jabalpur'),
13:(P,'Airlines','Gurugram'),14:(M,'Consumer electronics','Noida'),15:(S,'Alcoholic beverages retail','Bengaluru'),16:(F,'Infrastructure & EPC','Hyderabad'),
17:(C,'Fertilizers','New Delhi'),18:(M,'IT services','Chennai'),19:(M,'Automobiles','Hansalpur'),20:(S,D,'Patiala'),
21:(M,'Automobiles','Anantapur'),22:(M,'Precious metals refining','Mumbai'),23:(M,'Electronics manufacturing','Chennai'),24:(S,D,'Hyderabad'),
25:(S,D,'Kolkata'),26:(M,'IT services','Bengaluru'),27:(M,'IT services & hardware','Bengaluru'),28:(M,'Retail & digital commerce','Mumbai'),
29:(M,'Consumer electronics','Noida'),30:(M,'Telecom equipment','Gurugram'),31:(M,'IT services','Mumbai'),32:(S,'Oil & gas','Gandhinagar'),
33:(S,D,'Meerut'),34:(M,'Telecom equipment','Chennai'),35:(M,'Two-wheelers','Manesar'),36:(F,'Jewellery retail','Chennai'),
37:(S,D,'Jaipur'),38:(S,D,'Bengaluru'),39:(M,'E-commerce','Bengaluru'),40:(S,'Power & irrigation','Kolkata'),
41:(S,D,'Hisar'),42:(S,D,'Tirupati'),43:(M,'Alcoholic beverages','Gurugram'),44:(S,D,'Rajkot'),
45:(S,'Mining','Bhubaneswar'),46:(S,'Food procurement & distribution','New Delhi'),47:(S,D,'Raipur'),48:(M,'IT hardware distribution','Bengaluru'),
49:(P,'Lottery & gaming','Coimbatore'),50:(M,'Commercial vehicles','Indore'),51:(S,'Steel','Visakhapatnam'),52:(S,D,'Lucknow'),
53:(S,D,'Jodhpur'),54:(S,D,'Surat'),55:(M,'Business services / GCC','Mumbai'),56:(M,'Consumer electronics','Noida'),
57:(S,'Telecom','New Delhi'),58:(S,'Nuclear power','Mumbai'),59:(M,'Oil & gas trading','Bengaluru'),60:(M,'Automobiles','Mumbai'),
61:(M,'Automobiles','Pune'),62:(M,'IT services & software','Bengaluru'),63:(S,D,'Ajmer'),64:(S,D,'Indore'),
65:(F,'Pharmaceuticals','Ahmedabad'),66:(S,G,'Jaipur'),67:(F,'Diversified','Mumbai'),68:(S,D,'Visakhapatnam'),
69:(M,'IT services & software','Hyderabad'),70:(M,'Media & broadcasting','Mumbai'),71:(S,D,'Himmatnagar'),72:(M,'Construction equipment','Ballabgarh'),
73:(S,D,'Warangal'),74:(M,'Electronics retail (Croma)','Mumbai'),75:(M,'E-commerce','Bengaluru'),76:(M,'Engineering & construction','Mumbai'),
77:(S,D,'Patna'),78:(F,'Consumer goods & engineering','Bengaluru'),79:(M,'Automobiles','Greater Noida'),80:(S,D,'Panchkula'),
81:(F,'Biscuits & confectionery','Mumbai'),82:(F,'Conglomerate (appliances, engineering, real estate)','Mumbai'),83:(M,'Beverages bottling','Gurugram'),84:(M,'Auto components','Chennai'),
85:(F,'Diversified','Chennai'),86:(M,'Electronics manufacturing','Bengaluru'),87:(F,'Jewellery retail','Thrissur'),88:(M,'Tractors & farm equipment','Pune'),
89:(S,G,'Hyderabad'),90:(S,G,'Vijayawada'),91:(P,'Airlines','Gurugram'),92:(F,'Diversified','Chennai'),
93:(M,'Electronics manufacturing','Chennai'),94:(M,'Consulting & IT services','Mumbai'),95:(M,'Electrical equipment','Gurugram'),96:(P,'Supply chain / quick commerce','Mumbai'),
97:(P,'Petrochemicals','Kolkata'),98:(M,'Software R&D','Hyderabad'),99:(F,'Biscuits','Mumbai'),102:(C,'Fertilizers','New Delhi'),
103:(F,'Pharmaceuticals','Hyderabad'),104:(S,G,'Vadodara'),105:(S,T,'Bhubaneswar'),106:(M,'Packaged foods','Mumbai'),
107:(M,'Business services / GCC','Hyderabad'),108:(M,'Consumer electronics','Gurugram'),109:(P,'Telecom towers','Gurugram'),110:(M,'Automobiles','Chennai'),
111:(M,'Commercial vehicles','Chennai'),112:(M,'E-commerce logistics','Bengaluru'),113:(M,'Semiconductor R&D','Bengaluru'),114:(S,'Airports','New Delhi'),
115:(M,'Telecom towers','Gurugram'),116:(M,'Automobiles','Pune'),117:(M,'Construction equipment','Chennai'),118:(M,'Software','Bengaluru'),
119:(P,'Steel','Mumbai'),120:(M,'Rail transport equipment','Bengaluru'),121:(M,'Electronics manufacturing','Chennai'),122:(M,'Business services','Gurugram'),
123:(S,G,'Kolkata'),124:(P,'Manufacturing / B2B platform','Bengaluru'),125:(F,'Vaccines & pharma','Pune'),126:(M,'Steel','Mumbai'),
127:(M,'IT services','Hyderabad'),128:(S,G,'Jabalpur'),129:(S,D,'Hubli'),130:(S,G,'Bengaluru'),
131:(M,'Polyester / textiles','Gurugram'),132:(P,'Power generation','Hyderabad'),133:(M,'Business services / GCC','Pune'),134:(F,'Diamonds','Surat'),
135:(S,'Renewable energy','New Delhi'),136:(M,'Building materials','Chennai'),137:(S,D,'Guwahati'),138:(P,'Steel','Kolkata'),
139:(P,'Commodity trading','Surat'),141:(F,'Tractors','Hoshiarpur'),142:(F,'Detergents & consumer goods','Ahmedabad'),
143:(P,'Quick commerce / retail',''),144:(F,'Garments','Chennai'),145:(M,'Two-wheelers','Faridabad'),146:(M,'Consumer electronics','Gurugram'),
147:(F,'Poultry & agribusiness','Pune'),149:(F,'Mining',''),150:(M,'Automobiles','Gurugram'),151:(F,'Diamonds / jewellery',''),
152:(M,'Trading','Gurugram'),153:(P,'Diamonds / jewellery',''),154:(M,'Chemicals','Mumbai'),155:(F,'FMCG / ayurveda','Haridwar'),
156:(M,'Business services / GCC','Chennai'),157:(S,D,'Vadodara'),158:(P,'Edible oils','Mumbai'),159:(P,'Jewellery',''),
160:(M,'Business services / GCC','Hyderabad'),161:(M,'Consumer goods','Mumbai'),163:(F,'Poultry','Coimbatore'),164:(M,'Engineering services','Pune'),
165:(F,'Software','Chennai'),166:(M,'Software','Hyderabad'),167:(F,'Pharmaceuticals','Mumbai'),168:(M,'Business services / GCC','Bengaluru'),
169:(M,'Real estate & infrastructure','Ahmedabad'),170:(P,'Steel products','Mumbai'),171:(S,'Alcoholic beverages retail','Vijayawada'),172:(M,'Business services / GCC','Chennai'),
173:(M,'Consumer goods','Gurugram'),174:(S,'Power utility','Dehradun'),175:(M,'Two-wheelers','Gurugram'),176:(P,'Chemicals',''),
177:(M,'Tractors','Chennai'),178:(M,'Business services / GCC','Hyderabad'),179:(S,G,'Panchkula'),180:(M,'Pharmaceuticals','Mumbai'),
181:(F,'Mining / earthmoving','Chennai'),
}
DROP = {140, 162}  # Hexaware (listed 2025), WNS (entity ambiguous)
FX = {'2024': 83.0, '2023': 80.4}  # approx average INR/USD for the fiscal year
yrs41 = ['2024','2023','2024','2024','2024','2023','2023','2024','2024','2024','2024','2023','2024','2023','2024','2024','2024','2023','2024','2023','2023','2024','2023','2023','2024','2024','2024','2024','2023','2024','2024','2023','2024','2024','2023','2023','2023','2023','2024','2024','2023']
URL = 'https://bsmedia.business-standard.com/_media/bs/data/general-file-upload/2025-03/unlisted-companies-tables-2025.pdf'
fix = {'Accenture Solutions': 'Accenture Solutions India', 'U P Power Corp': 'Uttar Pradesh Power Corporation',
       'Foxconn Hon Hai Techn': 'Foxconn Hon Hai Technology India Mega Development'}
cols = ['company','ownership','sector','hq_city','revenue_musd','revenue_year','employees','source','url','confidence']
out = []
for r, n, v in big:
    if r in DROP: continue
    o, s, c = A[r]
    if r <= 41:
        y = yrs41[r-1]; fx = FX[y]; yl = 'FY%s (Mar %s)' % (y, y)
    else:
        fx = 81.7; yl = 'FY2023 or FY2024 (year ended Mar 2023/24; unresolved)'
    n = fix.get(n, n)
    out.append([n, o, s, c, round(v*1e7/fx/1e6), yl, '',
                'Business Standard BS1000 Unlisted Companies 2025 (total revenue Rs %s crore; converted at avg INR/USD %s)' % (format(v, ','), fx), URL, 'medium'])
AD = 'https://currentaffairs.adda247.com/top-10-highest-revenue-unlisted-indian-companies-in-2026/'
def add(n, o, s, c, cr, y, fx, emp, src, url, conf):
    out.append([n, o, s, c, round(cr*1e7/fx/1e6), y, emp, src, url, conf])
add('Reliance Retail Ventures', M, 'Retail', 'Mumbai', 330870, 'FY2025', 84.6, 207552, 'Wikipedia Reliance Retail infobox (Rs 330,870 cr FY25; employees 2024); Hurun Unlisted Gems cites ~Rs 2.7 lakh cr (different basis)', 'https://en.wikipedia.org/wiki/Reliance_Retail', 'medium')
add('Amul (GCMMF group)', C, 'Dairy', 'Anand', 90000, 'FY2025', 84.6, 1000, 'Wikipedia GCMMF infobox (Rs 90,000 cr group revenue FY25; 1,000 officers/employees; 3.6m milk producers)', 'https://en.wikipedia.org/wiki/Gujarat_Cooperative_Milk_Marketing_Federation', 'medium')
add('Malabar Gold and Diamonds', F, 'Jewellery retail', 'Kozhikode', 66872, 'FY2025', 84.6, '', 'Hurun India Unlisted Gems 2026 via Adda247', AD, 'medium')
add('Tata Electronics', M, 'Electronics / semiconductors manufacturing', 'Mumbai', 66601, 'FY2025', 84.6, '', 'Hurun India Unlisted Gems 2026 via Adda247', AD, 'medium')
add('OfBusiness', P, 'B2B commerce & financing', 'Gurugram', 22499, 'FY2025', 84.6, '', 'Hurun India Unlisted Gems 2026 via Adda247', AD, 'medium')
add('Tata Passenger Electric Mobility', M, 'Electric vehicles', 'Mumbai', 15247, 'FY2025', 84.6, '', 'Hurun India Unlisted Gems 2026 via Adda247', AD, 'medium')
add('SBI General Insurance', M, 'General insurance', 'Mumbai', 14140, 'FY2025', 84.6, '', 'Hurun India Unlisted Gems 2026 via Adda247', AD, 'medium')
add('Haldiram Snacks Food', F, 'Snacks & packaged foods', 'Noida', 14000, 'not stated', 84.6, '', 'Adda247 top-10 unlisted (year not stated)', AD, 'low')
add('Tata Sons (standalone)', P, 'Holding company', 'Mumbai', 38835, 'FY2025', 84.6, '', 'Wikipedia Tata Sons infobox (standalone revenue only, not group consolidated)', 'https://en.wikipedia.org/wiki/Tata_Sons', 'low')
with open(ROOT + 'data/extra/india_unlisted.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(cols); w.writerows(out)
print(len(out))
