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
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

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
        if parsed.path == "/api/scholarly/search":
            return self._search_crossref(parse_qs(parsed.query))
        super().do_GET()

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
    address = ("127.0.0.1", int(os.environ.get("LABWISE_PORT", "8000")))
    print(f"Labwise local preview: http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, Handler).serve_forever()
