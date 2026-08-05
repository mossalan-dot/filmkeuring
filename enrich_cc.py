#!/usr/bin/env python3
"""
Fase 2 — oogst IMDB-id's (tt-nummers) van Cinema Context.
Leest de unieke fictie-CC-id's uit films.json, haalt elke pagina
cinemacontext.nl/id/<Fxxxx> op en extraheert het tt-nummer + jaar/land/regie.

Resumable: schrijft cc_imdb.json na elke batch. Onderbreken mag; herstart pikt op.
Beleefd: begrensde concurrency + kleine vertraging + retries.

Gebruik:
    python3 enrich_cc.py            # alle nog-niet-opgehaalde fictie-id's
    python3 enrich_cc.py --sample 20
"""
import json, re, time, sys, socket, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

FILMS = "/Users/alan/Downloads/filmkeuring/films.json"
OUT   = "/Users/alan/Downloads/filmkeuring/cc_imdb.json"
BASE  = "https://www.cinemacontext.nl/id/"
WORKERS = 5          # gelijktijdige verzoeken (beleefd tegen een klein archief)
DELAY   = 0.15       # sec pauze per verzoek, per worker
UA = "Mozilla/5.0 (filmkeuring-archief; educatief; contact mossalan@gmail.com)"

TT_RE   = re.compile(r"imdb\.com/title/(tt\d+)")
YEAR_RE = re.compile(r"\((\d{4})\)")

def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def target_ids():
    films = load(FILMS, {"films": []})["films"]
    ids = []
    seen = set()
    for f in films:
        if f.get("c") == 1 and f.get("ci") and f["ci"] not in seen:
            seen.add(f["ci"]); ids.append(f["ci"])
    return ids

def fetch(cid):
    url = BASE + cid
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                html = r.read().decode("utf-8", "replace")
            tt = TT_RE.search(html)
            rec = {"tt": tt.group(1) if tt else None}
            time.sleep(DELAY)
            return cid, rec
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout, OSError) as e:
            if attempt == 2:
                return cid, {"err": str(e)[:60]}
            time.sleep(1.5 * (attempt + 1))
    return cid, {"err": "fail"}

def main():
    sample = None
    if "--sample" in sys.argv:
        sample = int(sys.argv[sys.argv.index("--sample") + 1])
    done = load(OUT, {})
    ids = [i for i in target_ids() if i not in done]
    if sample:
        ids = ids[:sample]
    print(f"{len(done)} al gedaan · {len(ids)} te doen"
          + (f" (sample {sample})" if sample else ""))
    t0 = time.time(); n = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for cid, rec in ex.map(fetch, ids):
            done[cid] = rec; n += 1
            if n % 100 == 0 or n == len(ids):
                with open(OUT, "w", encoding="utf-8") as f:
                    json.dump(done, f, ensure_ascii=False)
                hit = sum(1 for v in done.values() if v.get("tt"))
                rate = n / max(time.time() - t0, .1)
                eta = (len(ids) - n) / max(rate, .1)
                print(f"  {n}/{len(ids)}  tt-hits={hit}  {rate:.1f}/s  ETA {eta/60:.0f}m")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False)
    hit = sum(1 for v in done.values() if v.get("tt"))
    print(f"Klaar. {len(done)} pagina's, {hit} met IMDB-id ({100*hit/max(len(done),1):.0f}%).")

if __name__ == "__main__":
    main()
