#!/usr/bin/env python3
"""
Fase 3d — cast per film via de officiële IMDb-datasets (gestreamd, niets groots
op schijf). Filtert title.principals op onze tt-nummers en resolvet namen via
name.basics. Alleen acteurs/actrices, top-billed volgorde.

Output: actors_cast.json  { "tt0024216": [ {"id":"nm0000...","n":"Fay Wray"}, ... ] }
"""
import json, gzip, io, time, urllib.request

CC        = "/Users/alan/Downloads/filmkeuring/cc_imdb.json"
OUT       = "/Users/alan/Downloads/filmkeuring/actors_cast.json"
PRINC_URL = "https://datasets.imdbws.com/title.principals.tsv.gz"
NAME_URL  = "https://datasets.imdbws.com/name.basics.tsv.gz"
UA        = "filmkeuring-archief/1.0 (mossalan@gmail.com)"
TOP_N     = 6   # max top-billed acteurs per film

def stream_lines(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=120)
            gz = gzip.GzipFile(fileobj=resp)
            txt = io.TextIOWrapper(gz, encoding="utf-8", newline="")
            next(txt)  # header
            for line in txt:
                yield line
            return
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  stream-fout ({str(e)[:50]}), opnieuw…")
            time.sleep(5)

def main():
    with open(CC, encoding="utf-8") as f:
        cc = json.load(f)
    want = {v["tt"] for v in cc.values() if v.get("tt")}
    print(f"{len(want)} films om cast voor te zoeken")

    # 1) title.principals streamen en filteren
    print("stream title.principals.tsv.gz (778 MB) …")
    per_film = {}   # tt -> list[(ordering, nconst)]
    n = 0; t0 = time.time()
    for line in stream_lines(PRINC_URL):
        n += 1
        if n % 5_000_000 == 0:
            print(f"  {n//1_000_000}M regels · {int(time.time()-t0)}s · films gevonden {len(per_film)}")
        p = line.rstrip("\n").split("\t")
        # tconst ordering nconst category job characters
        if p[0] not in want:
            continue
        if p[3] not in ("actor", "actress"):
            continue
        per_film.setdefault(p[0], []).append((int(p[1]), p[2]))
    print(f"  klaar: {len(per_film)} films met cast, {n:,} regels doorlopen")

    # top-billed per film, en verzamel benodigde nconsts
    need = set()
    for tt, lst in per_film.items():
        lst.sort()
        per_film[tt] = [nc for _, nc in lst[:TOP_N]]
        need.update(per_film[tt])
    print(f"  {len(need)} unieke acteurs om namen voor te resolven")

    # 2) name.basics streamen voor de namen
    print("stream name.basics.tsv.gz (308 MB) …")
    names = {}; n = 0; t0 = time.time()
    for line in stream_lines(NAME_URL):
        n += 1
        if n % 3_000_000 == 0:
            print(f"  {n//1_000_000}M regels · {int(time.time()-t0)}s · namen {len(names)}/{len(need)}")
        p = line.rstrip("\n").split("\t")
        # nconst primaryName birthYear deathYear primaryProfession knownForTitles
        if p[0] in need:
            names[p[0]] = p[1]
            if len(names) == len(need):
                break

    out = {}
    for tt, ncs in per_film.items():
        cast = [{"id": nc, "n": names.get(nc, "?")} for nc in ncs]
        out[tt] = cast
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Klaar. cast voor {len(out)} films → actors_cast.json")

if __name__ == "__main__":
    main()
