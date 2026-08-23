#!/usr/bin/env python3
"""Haalt de 'bekende' filmtitel (IMDb primaryTitle + originalTitle) op voor elk
tt-nummer in onze set, door title.basics.tsv.gz van IMDb te streamen en te
filteren. Schrijft imdb_titles.json = {tt: {"pt": primaryTitle, "ot": originalTitle}}.

primaryTitle = de titel waaronder de film het bekendst is (meestal Engels/origineel);
die gebruiken we in de site als hoofdtitel, met de archivarische NL-titel als
'ook bekend als'.
"""
import json, gzip, io, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
CC = HERE + "/cc_imdb.json"
OUT = HERE + "/imdb_titles.json"


def wanted_tts():
    cc = json.load(open(CC, encoding="utf-8"))
    return {v["tt"] for v in cc.values() if v.get("tt")}


def main():
    tts = wanted_tts()
    print(f"{len(tts)} tt-nummers gezocht")
    req = urllib.request.Request(BASICS_URL, headers={"User-Agent": "Mozilla/5.0"})
    print("stream title.basics.tsv.gz (~200 MB) …")
    resp = urllib.request.urlopen(req, timeout=180)
    gz = gzip.GzipFile(fileobj=resp)
    txt = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
    header = txt.readline()  # tconst titleType primaryTitle originalTitle isAdult startYear endYear runtimeMinutes genres
    out = {}
    n = 0
    for line in txt:
        n += 1
        if n % 1_000_000 == 0:
            print(f"  {n:,} regels, {len(out)} gevonden")
        # snelle prefilter: tconst staat vooraan
        tab = line.find("\t")
        if tab < 0:
            continue
        tconst = line[:tab]
        if tconst not in tts:
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        pt, ot = parts[2], parts[3]
        rec = {}
        if pt and pt != "\\N":
            rec["pt"] = pt
        if ot and ot != "\\N" and ot != pt:
            rec["ot"] = ot
        if rec:
            out[tconst] = rec
        if len(out) == len(tts):
            break
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"klaar: {len(out)} titels -> {OUT}")


if __name__ == "__main__":
    main()
