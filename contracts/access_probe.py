# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
from genlayer import *

class AccessProbe(gl.Contract):
    results: TreeMap[str, str]
    def __init__(self):
        pass

    @gl.public.write
    def probe(self, url: str) -> None:
        def fetch():
            try:
                response = gl.nondet.web.get(url)
                body = response.body.decode('utf8', errors='replace')
                return {'status': response.status, 'length': len(body), 'chart_rows': body.count('o-chart-results-list-row-container'), 'oldid': 'oldid' in body, 'sample': body[:160]}
            except Exception:
                return {'status': 0, 'length': 0, 'chart_rows': 0, 'oldid': False, 'sample': 'Validator fetch failed'}
        def agree(result):
            own = fetch()
            return isinstance(result, gl.vm.Return) and own['status'] == result.calldata['status'] and (own['chart_rows'] == 100) == (result.calldata['chart_rows'] == 100) and (own['length'] > 500) == (result.calldata['length'] > 500)
        self.results[url] = json.dumps(gl.vm.run_nondet_unsafe(fetch, agree))

    @gl.public.view
    def result(self, url: str) -> str:
        return self.results.get(url, '{}')
