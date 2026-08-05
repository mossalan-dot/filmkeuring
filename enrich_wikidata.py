#!/usr/bin/env python3
"""
Fase 3c — Wikidata-verrijking via SPARQL, gesleuteld op IMDb-id (P345).
Haalt per film: land van herkomst, genre(s), regisseur(s) en Nederlandse
Wikipedia-link. Batcht de tt-ids in blokken en aggregeert in Python.

Resumable (schrijft per blok) en beleefd (serieel, ~1 req/sec, nette UA).
Output: wikidata.json  { "tt0024216": {"c":["Verenigde Staten"],"d":["Merian C. Cooper",...],
                                       "g":["fantasyfilm",...],"w":"https://nl.wikipedia.org/wiki/..."} }
"""
import json, time, sys, urllib.request, urllib.parse, urllib.error, socket

CC    = "/Users/alan/Downloads/filmkeuring/cc_imdb.json"
OUT   = "/Users/alan/Downloads/filmkeuring/wikidata.json"
EP    = "https://query.wikidata.org/sparql"
UA    = "filmkeuring-archief/1.0 (https://filmkeuring.alanmoss.nl; mossalan@gmail.com)"
CHUNK = 140
PAUSE = 1.1

TEMPLATE = """SELECT ?imdb ?directorLabel ?genreLabel ?countryLabel ?article WHERE {{
  VALUES ?imdb {{ {values} }}
  ?film wdt:P345 ?imdb.
  OPTIONAL {{ ?film wdt:P57 ?director. }}
  OPTIONAL {{ ?film wdt:P136 ?genre. }}
  OPTIONAL {{ ?film wdt:P495 ?country. }}
  OPTIONAL {{ ?article schema:about ?film; schema:isPartOf <https://nl.wikipedia.org/>. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "nl,en". }}
}}"""

def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def query(tts):
    values = " ".join(f'"{t}"' for t in tts)
    q = TEMPLATE.format(values=values)
    url = EP + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                        "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code == 429 or 500 <= e.code < 600:   # rate-limit of tijdelijke serverfout
                time.sleep(5 * (attempt + 1)); continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout, OSError):
            time.sleep(3 * (attempt + 1))
    return []

def main():
    cc = load(CC, {})
    tts = sorted({v["tt"] for v in cc.values() if v.get("tt")})
    done = load(OUT, {})
    todo = [t for t in tts if t not in done]
    print(f"{len(done)} al gedaan · {len(todo)} tt-ids te doen ({len(tts)} totaal)")
    t0 = time.time()
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        rows = query(chunk)
        agg = {t: {"c": set(), "d": set(), "g": set(), "w": None} for t in chunk}
        for b in rows:
            g = lambda k: b.get(k, {}).get("value", "")
            tt = g("imdb")
            if tt not in agg:
                continue
            if g("countryLabel"):  agg[tt]["c"].add(g("countryLabel"))
            if g("directorLabel"): agg[tt]["d"].add(g("directorLabel"))
            if g("genreLabel"):    agg[tt]["g"].add(g("genreLabel"))
            if g("article"):       agg[tt]["w"] = urllib.parse.unquote(g("article"))
        for tt, a in agg.items():
            rec = {}
            if a["c"]: rec["c"] = sorted(a["c"])
            if a["d"]: rec["d"] = sorted(a["d"])
            if a["g"]: rec["g"] = sorted(a["g"])
            if a["w"]: rec["w"] = a["w"]
            done[tt] = rec
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(done, f, ensure_ascii=False)
        n = i + len(chunk)
        rate = n / max(time.time() - t0, .1)
        hit = sum(1 for v in done.values() if v.get("c") or v.get("d"))
        print(f"  {n}/{len(todo)}  wikidata-hits={hit}  ETA {(len(todo)-n)/max(rate,.1)/60:.0f}m")
        time.sleep(PAUSE)
    hit = sum(1 for v in done.values() if v.get("c") or v.get("d"))
    print(f"Klaar. {len(done)} tt-ids bevraagd, {hit} met Wikidata-gegevens.")

if __name__ == "__main__":
    main()
