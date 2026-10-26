"""Local server for the Labwise pilot UI and scholarly-search prototype.

Run with ``python3 server.py``.  The search endpoint deliberately talks only to
the fixed Crossref API host; it is a discovery aid, not proof that a student's
claim is supported by a paper.
"""
import html
import json
import os
import re
import ssl
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen
import pilot_backend

try:
    import certifi
except ImportError:  # The system trust store still works on many Python builds.
    certifi = None

ROOT = Path(__file__).resolve().parent
USER_AGENT = "LabwisePilot/0.1 (citation verification prototype)"
MAX_QUERY_LENGTH = 300
MAX_RESULTS = 10
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where() if certifi else None)
NCBI_LOCK = Lock()
NCBI_LAST_REQUEST = 0.0


def fetch_remote(url, xml=False, ncbi=False):
    global NCBI_LAST_REQUEST
    if ncbi:
        with NCBI_LOCK:
            interval = 0.11 if os.environ.get('NCBI_API_KEY') else 0.35
            time.sleep(max(0, interval - (time.monotonic() - NCBI_LAST_REQUEST)))
            NCBI_LAST_REQUEST = time.monotonic()
    request = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(request, timeout=12, context=TLS_CONTEXT) as response:
        content = response.read(4_000_001)
    if len(content) > 4_000_000:
        raise ValueError('Upstream response too large')
    return ET.fromstring(content) if xml else json.loads(content)


def search_pubmed(query, limit):
    base = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
    common = {'db': 'pubmed', 'tool': 'labwise'}
    if os.environ.get('NCBI_API_KEY'):
        common['api_key'] = os.environ['NCBI_API_KEY']
    if os.environ.get('LABWISE_CONTACT_EMAIL'):
        common['email'] = os.environ['LABWISE_CONTACT_EMAIL']
    found = fetch_remote(base + 'esearch.fcgi?' + urlencode({**common, 'term': query, 'retmax': limit, 'retmode': 'json'}), ncbi=True)
    ids = found['esearchresult']['idlist']
    if not ids:
        return []
    root = fetch_remote(base + 'efetch.fcgi?' + urlencode({**common, 'id': ','.join(ids), 'retmode': 'xml'}), xml=True, ncbi=True)
    works = []
    for article in root.findall('.//PubmedArticle'):
        text = lambda path: ''.join(article.find(path).itertext()).strip() if article.find(path) is not None else None
        pmid = text('.//MedlineCitation/PMID')
        doi = next((node.text for node in article.findall('.//ArticleId') if node.get('IdType') == 'doi'), None)
        pmcid = next((node.text for node in article.findall('.//ArticleId') if node.get('IdType') == 'pmc'), None)
        works.append({'title': text('.//ArticleTitle'), 'authors': [' '.join(filter(None, [a.findtext('ForeName'), a.findtext('LastName'), a.findtext('CollectiveName')])) for a in article.findall('.//Author')], 'year': text('.//PubDate/Year'), 'doi': doi, 'pmid': pmid, 'pmcid': pmcid, 'container_title': text('.//Journal/Title'), 'abstract': '\n'.join(''.join(n.itertext()) for n in article.findall('.//AbstractText')) or None, 'url': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/', 'source': 'PubMed'})
    return works


def search_europe_pmc(query, limit):
    data = fetch_remote('https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urlencode({'query': query, 'format': 'json', 'resultType': 'core', 'pageSize': limit}))
    return [{'title': item.get('title'), 'authors': [a.get('fullName', '') for a in item.get('authorList', {}).get('author', [])], 'year': item.get('pubYear'), 'doi': item.get('doi'), 'pmid': item.get('pmid'), 'pmcid': item.get('pmcid'), 'container_title': item.get('journalInfo', {}).get('journal', {}).get('title'), 'abstract': _plain_text(item.get('abstractText')), 'url': 'https://europepmc.org/article/' + quote(item.get('source', 'MED'), safe='') + '/' + quote(item['id'], safe=''), 'source': 'Europe PMC', 'open_access': item.get('isOpenAccess') == 'Y'} for item in data.get('resultList', {}).get('result', [])]


def merge_works(groups):
    merged = []
    for works in groups:
        for work in works:
            existing = next((w for w in merged if any(work.get(key) and w.get(key) and str(work[key]).lower() == str(w[key]).lower() for key in ('doi', 'pmid', 'pmcid'))), None)
            if existing:
                existing['sources'].append(work['source'])
                for key, value in work.items():
                    if not existing.get(key) and value:
                        existing[key] = value
            else:
                merged.append({**work, 'sources': [work['source']]})
    return merged


def search_crossref(query, limit):
    doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', query, flags=re.IGNORECASE)
    exact = DOI_PATTERN.fullmatch(doi)
    url = 'https://api.crossref.org/works/' + quote(doi, safe='') if exact else 'https://api.crossref.org/works?' + urlencode({'query.bibliographic': query, 'rows': limit})
    message = fetch_remote(url)['message']
    return [_normalise_work(message)] if exact else [_normalise_work(item) for item in message.get('items', [])]


def _plain_text(value):
    """Remove the small amount of JATS/HTML commonly returned in abstracts."""
    if not value:
        return None
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _year(item):
    parts = (item.get("published-print") or item.get("published-online") or item.get("issued") or {}).get("date-parts", [])
    return parts[0][0] if parts and parts[0] else None


def _normalise_work(item):
    authors = []
    for author in item.get("author", [])[:8]:
        name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
        if name:
            authors.append(name)
    title = item.get("title") or []
    container = item.get("container-title") or []
    return {
        "title": title[0] if title else "Untitled work",
        "authors": authors,
        "year": _year(item),
        "doi": item.get("DOI"),
        "container_title": container[0] if container else None,
        "publisher": item.get("publisher"),
        "type": item.get("type"),
        "url": item.get("URL"),
        "abstract": _plain_text(item.get("abstract")),
        "source": "Crossref",
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if not self._local_request():
            return self._json(403, {'error': 'Local access only.'})
        if parsed.path.startswith('/api/pilot/'):
            return self._pilot('GET', parsed.path)
        # Serve explicit public assets only. Never expose SQLite, keys or samples.
        public = {'/word-reader.html','/word-reader.js','/word-reader.css','/visual-inventory.js', '/original-reader.html', '/original-reader.mjs', '/teacher-live.js', '/teacher-live.css', '/document-viewer.js', '/document-viewer.css', '/turnitin-bridge.js', '/turnitin-bridge.css', '/', '/index.html', '/pilot.html', '/pilot.css', '/pilot-export.css', '/pilot.js', '/assignment-editor.js', '/teacher-shell.js', '/teacher-settings.css', '/teacher-modules.js', '/teacher-modules.css', '/workspace-resize.js', '/workspace-resize.css',
                  '/review-links.js', '/citation-verification.js', '/pilot-citations.js',
                  '/lab_report_rubric.default.json', '/custom_rubric.template.json',
                  '/examples/pilot-rubric.json'}
        if parsed.path == "/api/scholarly/search":
            return self._search_all(parse_qs(parsed.query))
        if parsed.path.startswith('/vendor/pdfjs/'):
            asset = (ROOT / parsed.path.lstrip('/')).resolve()
            vendor_root = (ROOT / 'vendor' / 'pdfjs').resolve()
            if asset.is_relative_to(vendor_root) and asset.is_file():
                return super().do_GET()
        if parsed.path not in public:
            return self._json(404, {'error': 'Not found.'})
        super().do_GET()

    def _local_request(self):
        host = self.headers.get('Host', '').split(':')[0]
        origin = self.headers.get('Origin')
        return host in ('127.0.0.1', 'localhost') and (not origin or origin == 'http://' + self.headers.get('Host'))

    def do_HEAD(self):
        self.send_error(405)

    def do_POST(self):
        if not self._local_request():
            return self._json(403, {'error': 'Local access only.'})
        return self._pilot('POST', urlparse(self.path).path)

    def _pilot(self, method, path):
        try:
            body = {}
            if method == 'POST':
                size = int(self.headers.get('Content-Length', '0'))
                if size <= 0 or size > 15 * 1024 * 1024:
                    raise ValueError('请求为空或超过 15 MB。')
                if not self.headers.get('Content-Type', '').startswith('application/json'):
                    raise ValueError('请使用 JSON 请求。')
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError('请求应为 JSON 对象。')
            return self._json(200, pilot_backend.dispatch(method, path, body, TLS_CONTEXT))
        except LookupError as e:
            return self._json(404, {'error': str(e)})
        except (ValueError, TypeError, AttributeError) as e:
            return self._json(400, {'error': str(e)})
        except Exception:
            return self._json(500, {'error': '本地服务处理失败，请检查日志并重试。'})

    def _search_all(self, params):
        query = (params.get('q') or [''])[0].strip()
        if not query or len(query) > MAX_QUERY_LENGTH:
            return self._json(400, {'error': 'Query must contain 1–300 characters.'})
        try:
            limit = min(MAX_RESULTS, max(1, int((params.get('limit') or [5])[0])))
        except ValueError:
            return self._json(400, {'error': 'limit must be an integer.'})
        providers = {'Crossref': search_crossref, 'PubMed': search_pubmed, 'Europe PMC': search_europe_pmc}
        groups, states = [], []
        with ThreadPoolExecutor(max_workers=3) as executor:
            pending = [(name, executor.submit(search, query, limit)) for name, search in providers.items()]
            for name, future in pending:
                try:
                    works = future.result()
                    groups.append(works)
                    states.append({'provider': name, 'status': 'ok', 'count': len(works)})
                except Exception:
                    states.append({'provider': name, 'status': 'unavailable'})
        success = any(s['status'] == 'ok' for s in states)
        return self._json(200 if success else 502, {'query': query, 'providers': states, 'results': merge_works(groups), 'error': None if success else 'All scholarly providers are unavailable.'})

    def _search_crossref(self, params):
        query = (params.get("q") or [""])[0].strip()
        if not query or len(query) > MAX_QUERY_LENGTH:
            return self._json(400, {"error": "Query must contain 1–300 characters."})
        try:
            limit = min(MAX_RESULTS, max(1, int((params.get("limit") or [5])[0])))
        except ValueError:
            return self._json(400, {"error": "limit must be an integer."})

        # The upstream host and path are fixed to avoid turning this endpoint
        # into an arbitrary URL fetcher.
        normalised_doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", query, flags=re.IGNORECASE)
        exact_doi = DOI_PATTERN.fullmatch(normalised_doi)
        if exact_doi:
            upstream = "https://api.crossref.org/works/" + quote(normalised_doi, safe="")
        else:
            upstream_params = {
                "query.bibliographic": query,
                "rows": limit,
                "select": "DOI,title,author,published-print,published-online,issued,container-title,publisher,type,URL,abstract",
            }
            if os.environ.get("LABWISE_CONTACT_EMAIL"):
                upstream_params["mailto"] = os.environ["LABWISE_CONTACT_EMAIL"]
            upstream = "https://api.crossref.org/works?" + urlencode(upstream_params)
        request = Request(upstream, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=8, context=TLS_CONTEXT) as response:
                payload = json.load(response)
            message = payload["message"]
            works = [_normalise_work(message)] if exact_doi else [_normalise_work(item) for item in message.get("items", [])]
            return self._json(200, {
                "query": query,
                "provider": "Crossref",
                "disclaimer": "Metadata matches are discovery evidence only; verify the source text before confirming claim support.",
                "results": works,
            })
        except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            return self._json(502, {"error": "Scholarly search is temporarily unavailable.", "detail": type(exc).__name__})


if __name__ == "__main__":
    pilot_backend.init()
    import auto_analysis
    address = (os.environ.get('LABWISE_HOST', '127.0.0.1'), int(os.environ.get("LABWISE_PORT", "8000")))
    print(f"Labwise local preview: http://{address[0]}:{address[1]}")
    httpd = ThreadingHTTPServer(address, Handler)
    auto_analysis.start(TLS_CONTEXT)
    httpd.serve_forever()
