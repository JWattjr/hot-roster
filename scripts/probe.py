import json
from chain import ROOT, client, transaction, read, save

proof = json.loads((ROOT / 'deploy/proof.json').read_text())
c = client()
if not proof.get('probeContract'):
    receipt = transaction(c, proof, 'probe-deploy', code=(ROOT / 'contracts/access_probe.py').read_text())
    proof['probeContract'] = receipt.get('recipient', receipt.get('to_address'))
    save(proof)
urls = [
    'https://www.billboard.com/charts/hot-100/2024-06-29/',
    'https://web.archive.org/cdx/search/cdx?url=www.billboard.com%2Fcharts%2Fhot-100%2F2024-06-29%2F&output=json&filter=statuscode%3A200&filter=mimetype%3Atext%2Fhtml&limit=1',
    'https://web.archive.org/web/20240701000000id_/https://www.billboard.com/charts/hot-100/2024-06-29/',
    'https://en.wikipedia.org/w/index.php?title=Short_n%27_Sweet_Tour&oldid=1230342438'
]
proof.setdefault('probes', {})
for i, url in enumerate(urls):
    transaction(c, proof, 'probe-source-' + str(i), proof['probeContract'], 'probe', [url])
    proof['probes'][url] = read(c, proof['probeContract'], 'result', [url])
    save(proof)
    print(url, proof['probes'][url], flush=True)
