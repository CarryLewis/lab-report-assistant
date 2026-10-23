"""Live retrieval audit. Sends only reference identifiers, never report text."""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import search_crossref, search_pubmed, search_europe_pmc, merge_works


def run():
    records = []
    providers = {'Crossref': search_crossref, 'PubMed': search_pubmed, 'Europe PMC': search_europe_pmc}
    for path in sorted(Path('corpus/historical/samples').glob('*.md')):
        dois = sorted(set(re.findall(r'https://doi.org/(10\.\d{4,9}/[^\s]+)', path.read_text())))
        for raw in dois:
            doi = raw.rstrip('.,;)')
            groups, states = [], []
            with ThreadPoolExecutor(max_workers=3) as pool:
                jobs = [(name, pool.submit(fn, doi, 3)) for name, fn in providers.items()]
                for name, job in jobs:
                    try:
                        works = job.result()
                        exact = [w for w in works if (w.get('doi') or '').lower() == doi.lower()]
                        groups.append(exact)
                        states.append({'provider': name, 'returned': len(works), 'exact_matches': len(exact)})
                    except Exception as error:
                        states.append({'provider': name, 'error': type(error).__name__})
            record = {'sample': str(path), 'doi': doi, 'providers': states, 'matches': merge_works(groups)}
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
    return records


if __name__ == '__main__':
    run()
