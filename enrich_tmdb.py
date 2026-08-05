#!/usr/bin/env python3
"""
Fase 3 — haal poster + beoordeling bij elk IMDB-id via TMDb.
Leest cc_imdb.json (de tt-nummers uit fase 2), bevraagt de TMDb /find-endpoint
per imdb_id en bewaart poster, stem-gemiddelde, jaar en tmdb-id.

Vereist een gratis TMDb API-key (v3). Zet die als omgevingsvariabele:
    export TMDB_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    python3 enrich_tmdb.py

Resumable + beleefd. Output: tmdb.json  { "tt0024216": {"p":"/xxx.jpg","r":7.9,"n":95000,"y":1933,"tm":244} }
"""
import json, os, sys, time, socket, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

CC   = "/Users/alan/Downloads/filmkeuring/cc_imdb.json"
OUT  = "/Users/alan/Downloads/filmkeuring/tmdb.json"
KEY  = os.environ.get("TMDB_KEY", "").strip()
API  = "https://api.themoviedb.org/3/find/{tt}?api_key={key}&external_source=imdb_id"
WORKERS = 8
DELAY   = 0.05

def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def tt_targets():
    cc = load(CC, {})
    return sorted({v["tt"] for v in cc.values() if v.get("tt")})

def fetch(tt):
    url = API.format(tt=tt, key=KEY)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                d = json.load(r)
            hits = (d.get("movie_results") or []) + (d.get("tv_results") or [])
            time.sleep(DELAY)
            if not hits:
                return tt, {"none": 1}
            m = hits[0]
            rec = {}
            if m.get("poster_path"): rec["p"] = m["poster_path"]
            if m.get("vote_average"): rec["r"] = round(m["vote_average"], 1)
            if m.get("vote_count"):   rec["n"] = m["vote_count"]
            rd = m.get("release_date") or m.get("first_air_date") or ""
            if rd[:4].isdigit():      rec["y"] = int(rd[:4])
            if m.get("id"):           rec["tm"] = m["id"]
            return tt, rec
        except urllib.error.HTTPError as e:
            if e.code == 429:  # rate limit
                time.sleep(2 * (attempt + 1)); continue
            return tt, {"err": e.code}
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout, OSError) as e:
            if attempt == 2:
                return tt, {"err": str(e)[:40]}
            time.sleep(1.5 * (attempt + 1))
    return tt, {"err": "fail"}

def main():
    if not KEY:
        sys.exit("Geen TMDB_KEY gevonden. Zet: export TMDB_KEY=...  (gratis via themoviedb.org)")
    done = load(OUT, {})
    tts = [t for t in tt_targets() if t not in done]
    print(f"{len(done)} al gedaan · {len(tts)} tt-id's te doen")
    t0 = time.time(); n = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for tt, rec in ex.map(fetch, tts):
            done[tt] = rec; n += 1
            if n % 200 == 0 or n == len(tts):
                with open(OUT, "w", encoding="utf-8") as f:
                    json.dump(done, f, ensure_ascii=False)
                pos = sum(1 for v in done.values() if v.get("p"))
                rate = n / max(time.time() - t0, .1)
                print(f"  {n}/{len(tts)}  posters={pos}  {rate:.1f}/s  ETA {(len(tts)-n)/max(rate,.1)/60:.0f}m")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False)
    pos = sum(1 for v in done.values() if v.get("p"))
    print(f"Klaar. {len(done)} films, {pos} met poster.")

if __name__ == "__main__":
    main()
