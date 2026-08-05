#!/usr/bin/env python3
"""
Fase 3b — IMDb-ratings via de officiële IMDb-datasets (gratis, bulk).
Downloadt title.ratings.tsv.gz en joint op de tt-nummers uit cc_imdb.json.

Output: imdb_ratings.json  { "tt0024216": {"ar": 7.9, "nv": 95000} }
    ar = averageRating (0-10), nv = numVotes
"""
import json, gzip, io, urllib.request

CC   = "/Users/alan/Downloads/filmkeuring/cc_imdb.json"
OUT  = "/Users/alan/Downloads/filmkeuring/imdb_ratings.json"
URL  = "https://datasets.imdbws.com/title.ratings.tsv.gz"
UA   = "filmkeuring-archief/1.0 (mossalan@gmail.com)"

def main():
    with open(CC, encoding="utf-8") as f:
        cc = json.load(f)
    want = {v["tt"] for v in cc.values() if v.get("tt")}
    print(f"{len(want)} tt-ids om ratings voor te zoeken")

    print("download title.ratings.tsv.gz …")
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    print(f"  {len(raw)/1e6:.1f} MB, uitpakken…")

    out = {}
    with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8") as fh:
        next(fh)  # header: tconst  averageRating  numVotes
        for line in fh:
            tt, avg, nv = line.rstrip("\n").split("\t")
            if tt in want:
                out[tt] = {"ar": float(avg), "nv": int(nv)}

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    cov = 100 * len(out) / max(len(want), 1)
    print(f"Klaar. {len(out)} van {len(want)} tt-ids hebben een IMDb-rating ({cov:.0f}%).")

if __name__ == "__main__":
    main()
