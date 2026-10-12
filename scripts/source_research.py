"""Collect external fixtures, exact CDX captures and permanent Wikipedia revisions."""
import json
import sys
import requests
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent.parent
headers = {'User-Agent':'Mozilla/5.0 HotRoster/1.0'}
def fetch(url):
    r = requests.get(url,headers=headers,timeout=90)
    print(r.status_code,len(r.content),url,flush=True)
    r.raise_for_status()
    return r

if sys.argv[1:] == ['archive']:
    url = 'https://www.billboard.com/charts/hot-100/2024-06-29/'
    captures = fetch('https://web.archive.org/cdx/search/cdx?url='+url+'&output=json&filter=statuscode:200&filter=mimetype:text/html&fl=timestamp,original&from=20240629&limit=-1').json()
    print(captures)
    if len(captures)>1:
        ts,origin=captures[1]
        result = fetch('https://web.archive.org/web/'+ts+'id_/'+origin)
        (ROOT / 'tests/fixtures/archived-billboard-2024-06-29.html').write_bytes(result.content)
        print('rows:',result.text.count('o-chart-results-list-row-container'))
else:
    dates=[(datetime(2024,5,25)+timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(6)]
    for date in dates:
        file=ROOT / ('tests/fixtures/billboard-'+date+'.html')
        if not file.exists():
            file.write_bytes(fetch('https://www.billboard.com/charts/hot-100/'+date+'/').content)
    wiki = 'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=Short_n%27_Sweet_Tour&rvprop=ids%7Ctimestamp&rvlimit=1&rvstart=2024-06-23T00%3A00%3A00Z&format=json'
    result = fetch(wiki).json()
    (ROOT / 'deploy/evidence-research.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
