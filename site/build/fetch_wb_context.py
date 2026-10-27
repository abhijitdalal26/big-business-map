"""Download World Bank indicators for the context page into site/build/raw_context/wb_<indicator>.json"""
import json, os, requests, time
OUT = os.path.join(os.path.dirname(__file__), 'raw_context')
IND = ['IC.BUS.NDNS.ZS','IC.BUS.NREG','CM.MKT.LCAP.CD','CM.MKT.LDOM.NO','NY.GDP.MKTP.CD',
       'SL.EMP.SELF.ZS','SL.EMP.VULN.ZS','BX.KLT.DINV.CD.WD','NE.TRD.GNFS.ZS','SL.ISV.IFRM.ZS','BX.KLT.DINV.WD.GD.ZS']
for ind in IND:
    url = f'https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000&date=1975:2026'
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=90); r.raise_for_status(); js = r.json(); break
        except Exception as e:
            print('retry', ind, e); time.sleep(3)
    else:
        continue
    json.dump(js, open(os.path.join(OUT, f'wb_{ind}.json'), 'w'))
    print(ind, js[0].get('total'), js[0].get('lastupdated'))
# country metadata (region / income / aggregate flag)
r = requests.get('https://api.worldbank.org/v2/country?format=json&per_page=400', timeout=60)
json.dump(r.json(), open(os.path.join(OUT, 'wb_countries.json'), 'w'))
print('countries ok')
