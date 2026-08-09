#!/usr/bin/env python3
"""
Filmkeuringsrapporten 1928-1960 (NA index NT00402) -> compacte data.json
Fase 1: alleen de kale index (Cinema Context + NA-links). tt-ids/posters komen
later via enrich_cc.py (fase 2) en enrich_tmdb.py (fase 3).
"""
import csv, json, re, os, urllib.parse, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "NT00402_FILMKEURINGSRAPPORTEN.csv")

# oordeel -> korte code
OORDEEL = {
    "alle leeftijden": "A",
    "14 jaar": "14",
    "18 jaar": "18",
    "niet toegelaten": "X",
    "": "?",
}
# landcode-tag achter fabrieksnaam, bv "Ufa (D)"
LAND = {
    "A": "Verenigde Staten", "D": "Duitsland", "N": "Nederland",
    "E": "Engeland", "F": "Frankrijk", "I": "Italië", "R": "Rusland/USSR",
    "O": "Oostenrijk", "Z": "Zweden", "B": "België", "H": "Hongarije",
    "T": "Tsjechoslowakije", "S": "Spanje", "P": "Polen", "DK": "Denemarken",
}
TAG_RE = re.compile(r"\s*\(([A-Z]{1,2})\)\s*$")
METER_RE = re.compile(r"([\d.]+)")

QUOTES_RE = re.compile(r'"{2,}')
def clean(s):
    """Archiefdata gebruikt verdubbelde aanhalingstekens rond (deel)titels."""
    s = (s or "").strip()
    s = QUOTES_RE.sub('"', s)          # """" -> "
    s = s.strip().strip('"').strip()   # omringende quotes weg, subtitel-quotes blijven
    return s

# lidwoord dat archivarisch achteraan is gezet ("Bruiden van Dracula, De" -> "De Bruiden van Dracula")
ARTICLES = {"de","het","een","'t","'n","the","a","an","le","la","les","l'","un","une","des",
            "der","die","das","ein","eine","il","lo","el","los","las","una","gli","os","as"}
# BEWUST NIET: "i" — dubbelzinnig (Italiaans lidwoord vs deel/roman "I", bv "Olympische Spiele 1936, I")
ART_RE = re.compile(r"^(.*?),\s*([A-Za-z'’]{1,4})$")
def _invert(seg):
    seg = seg.strip()
    m = ART_RE.match(seg)
    if m and m.group(2).lower() in ARTICLES:
        art, rest = m.group(2), m.group(1).strip()
        return art + rest if art.lower() in ("l'", "l’") else art + " " + rest
    return seg
def normalize_title(raw):
    """('Bruiden van Dracula, De; Brides of Dracula') -> ('De Bruiden van Dracula', ['Brides of Dracula'])"""
    parts = [_invert(p) for p in clean(raw).split(";") if p.strip()]
    if not parts:
        return clean(raw), []
    return parts[0], parts[1:]

def meters(s):
    m = METER_RE.search(s or "")
    if not m:
        return None
    try:
        return int(round(float(m.group(1).replace(".", ""))))  # "1.234 meter" -> 1234
    except ValueError:
        return None

def cc_id(url):
    u = urllib.parse.unquote(url or "").strip()
    if not u:
        return None
    tail = u.rstrip("/").rsplit("/", 1)[-1]
    return tail if tail.startswith("F") else None

def studio_base(name):
    """('Ufa (D)') -> ('Ufa', 'D')"""
    name = (name or "").strip()
    if not name:
        return None, None
    m = TAG_RE.search(name)
    if m:
        return TAG_RE.sub("", name).strip(), m.group(1)
    return name, None

films = []
by_year = defaultdict(lambda: Counter())
oordeel_tot = Counter()
cat_by_year = defaultdict(lambda: Counter())
studio_count = Counter()
studio_land = {}
banned = coupures = herk = 0

with open(SRC, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        title, alt_titles = normalize_title(row["ond_tekst_filmtitel"])
        d = row["ond_datum_keuring"].strip()
        year = d[:4] if len(d) >= 4 and d[:4].isdigit() else None
        o = OORDEEL.get(row["ond_tekst_oordeel"].strip(), "?")
        cat = row["ond_tekst_categorie"].strip().lower()
        c = 1 if cat == "fictie" else (0 if cat == "nonfictie" else None)
        coup = row["ond_tekst_coupures"].strip()
        has_coup = bool(coup) and coup.lower() != "geen"
        cid = cc_id(row["vwz_url_cinemacontext"])
        sbase, sland = studio_base(row["org_naam_fabriek"])
        ho = row["ond_tekst_herkeuring_oordeel"].strip()
        ho_code = OORDEEL.get(ho, None) if ho else None

        rec = {"t": title}
        if alt_titles:
            rec["alt"] = alt_titles
        aanvr_c = clean(row["org_naam_aanvrager"])
        fabr_c = clean(row["org_naam_fabriek"])
        if aanvr_c:
            rec["a"] = aanvr_c
        if fabr_c:
            rec["f"] = fabr_c
        mm = meters(row["ond_tekst_lengte_meters"])
        if mm:
            rec["m"] = mm
        if row["ond_tekst_smalfilm"].strip().lower() == "ja":
            rec["s"] = 1
        if c is not None:
            rec["c"] = c
        if d:
            rec["d"] = d
        rec["o"] = o
        if has_coup:
            rec["k"] = coup
        if ho_code:
            rec["ho"] = ho_code
            if row["ond_datum_herkeuring"].strip():
                rec["hd"] = row["ond_datum_herkeuring"].strip()
        if cid:
            rec["ci"] = cid
        if row["ond_UUID"].strip():
            rec["id"] = row["ond_UUID"].strip()
        films.append(rec)

        # aggregaten
        oordeel_tot[o] += 1
        if year:
            by_year[year][o] += 1
            by_year[year]["_"] += 1
            if c == 1:
                cat_by_year[year]["fic"] += 1
            elif c == 0:
                cat_by_year[year]["non"] += 1
        if o == "X":
            banned += 1
        if has_coup:
            coupures += 1
        if ho_code:
            herk += 1
        if sbase:
            studio_count[sbase] += 1
            if sland and sbase not in studio_land:
                studio_land[sbase] = sland

years = sorted(by_year)
timeline = [{
    "y": int(y),
    "A": by_year[y]["A"], "f14": by_year[y]["14"], "f18": by_year[y]["18"],
    "X": by_year[y]["X"], "q": by_year[y]["?"], "tot": by_year[y]["_"],
    "fic": cat_by_year[y]["fic"], "non": cat_by_year[y]["non"],
} for y in years]

top_studios = [{
    "n": n, "c": cnt, "l": LAND.get(studio_land.get(n), studio_land.get(n)),
} for n, cnt in studio_count.most_common(30)]

stats = {
    "total": len(films),
    "oordeel": dict(oordeel_tot),
    "banned": banned,
    "coupures": coupures,
    "herkeuringen": herk,
    "years": [int(y) for y in years],
    "timeline": timeline,
    "topStudios": top_studios,
    "landLegend": LAND,
}

# --- verrijking samenvoegen (fase 2/3), indien aanwezig ---
def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

D = HERE + "/"
cc = _load(D + "cc_imdb.json")        # {Fid:{tt}}
tm = _load(D + "tmdb.json")           # {tt:{p,r,n,y,tm}}
ir = _load(D + "imdb_ratings.json")   # {tt:{ar,nv}}
wd = _load(D + "wikidata.json")       # {tt:{c,g,d,w}}
ac = _load(D + "actors_cast.json")    # {tt:[{id,n}]}
n_tt = n_poster = n_rating = 0
if cc:
    ci2tt = {k: v["tt"] for k, v in cc.items() if v.get("tt")}
    for rec in films:
        tt = ci2tt.get(rec.get("ci"))
        if not tt:
            continue
        rec["tt"] = tt
        n_tt += 1
        md = tm.get(tt) if tm else None
        if md:
            if md.get("p"): rec["p"] = md["p"]; n_poster += 1
            if md.get("r"): rec["r"] = md["r"]
            if md.get("n"): rec["rn"] = md["n"]
        rt = ir.get(tt) if ir else None
        if rt:
            rec["ir"] = rt["ar"]; rec["iv"] = rt["nv"]; n_rating += 1
        wr = wd.get(tt) if wd else None
        if wr:
            if wr.get("c"): rec["co"] = wr["c"]
            if wr.get("g"): rec["ge"] = wr["g"]
            if wr.get("d"): rec["di"] = wr["d"]
            if wr.get("w"): rec["w"] = wr["w"]
        cst = ac.get(tt) if ac else None
        if cst:
            rec["cast"] = [a["n"] for a in cst[:3]]
    print(f"verrijkt: {n_tt} records met tt-id, {n_poster} poster, {n_rating} IMDb-rating")

# --- Verboden-galerij: compacte lijst van alle 'niet toegelaten'-films ---
banned_list = []
for rec in films:
    if rec.get("o") != "X":
        continue
    b = {"t": rec["t"], "y": (rec.get("d") or "")[:4]}
    for k in ("f", "ci", "id", "tt", "p", "r"):
        if rec.get(k):
            b[k] = rec[k]
    banned_list.append(b)
banned_list.sort(key=lambda b: (b["y"], b["t"]))
stats["bannedList"] = banned_list

# --- LOD-analyses: bouw film-niveau (per uniek tt) uit de records ---
ORD = {"A": 0, "14": 1, "18": 2, "X": 3}
by_tt = {}
for rec in films:
    tt = rec.get("tt")
    if not tt:
        continue
    e = by_tt.get(tt)
    if e is None:
        e = by_tt[tt] = {"ir": rec.get("ir"), "iv": rec.get("iv"),
                         "ostr": ORD.get(rec["o"], 0), "banned": False, "cut": False,
                         "year": None, "co": rec.get("co"), "ge": rec.get("ge"),
                         "di": rec.get("di")}
    e["ostr"] = max(e["ostr"], ORD.get(rec["o"], 0))
    if rec["o"] == "X": e["banned"] = True
    if rec.get("k"):    e["cut"] = True
    yr = (rec.get("d") or "")[:4]
    if yr.isdigit():
        y = int(yr)
        e["year"] = y if e["year"] is None else min(e["year"], y)
STRO = {0: "A", 1: "14", 2: "18", 3: "X"}

# 1) Censuur × waardering: IMDb-rating per (strengste) oordeel + geknipt vs niet
rating_by_oordeel = {}
for code in ("A", "14", "18", "X"):
    vals = [e["ir"] for e in by_tt.values() if e["ir"] and STRO[e["ostr"]] == code]
    if vals:
        hist = [0] * 10
        for v in vals:
            hist[min(int(v), 9)] += 1
        rating_by_oordeel[code] = {"n": len(vals), "mean": round(sum(vals) / len(vals), 2), "hist": hist}
cut_vals = [e["ir"] for e in by_tt.values() if e["ir"] and e["cut"]]
unc_vals = [e["ir"] for e in by_tt.values() if e["ir"] and not e["cut"]]
rating_cut = {
    "cut": {"n": len(cut_vals), "mean": round(sum(cut_vals) / len(cut_vals), 2) if cut_vals else None},
    "uncut": {"n": len(unc_vals), "mean": round(sum(unc_vals) / len(unc_vals), 2) if unc_vals else None},
}
stats["ratingByOordeel"] = rating_by_oordeel
stats["ratingCut"] = rating_cut

# 2) Herkomst over tijd: primair land per film, per eerste-keuringsjaar
country_count = Counter()
for e in by_tt.values():
    if e["co"]:
        country_count[e["co"][0]] += 1
top_countries = [c for c, _ in country_count.most_common(7)]
cby = defaultdict(lambda: Counter())
for e in by_tt.values():
    if not e["co"] or e["year"] is None:
        continue
    c = e["co"][0]
    cby[e["year"]][c if c in top_countries else "Overig"] += 1
country_by_year = [dict({"y": y}, **{c: cby[y].get(c, 0) for c in top_countries + ["Overig"]})
                   for y in sorted(cby)]
stats["topCountries"] = top_countries
stats["countryByYear"] = country_by_year

# 2b) Productieland per decennium (ISO3) voor de choropleth-kaart
NL2ISO = {
    "Verenigde Staten":"USA","Duitsland":"DEU","Duitse Rijk":"DEU","nazi-Duitsland":"DEU",
    "Weimarrepubliek":"DEU","Duitse Democratische Republiek":"DEU","Bondsrepubliek Duitsland":"DEU",
    "Duitse Keizerrijk":"DEU","Frankrijk":"FRA","Verenigd Koninkrijk":"GBR","Italië":"ITA",
    "Koninkrijk Italië":"ITA","Oostenrijk":"AUT","Sovjet-Unie":"RUS",
    "Georgische Socialistische Sovjetrepubliek":"RUS","Denemarken":"DNK","Zweden":"SWE",
    "Nederland":"NLD","Mexico":"MEX","Tsjecho-Slowakije":"CZE","Protectoraat Bohemen en Moravië":"CZE",
    "Eerste Tsjecho-Slowaakse Republiek":"CZE","Polen":"POL","België":"BEL","Australië":"AUS",
    "Spanje":"ESP","Hongarije":"HUN","Zwitserland":"CHE","Japan":"JPN","Argentinië":"ARG",
    "Noorwegen":"NOR","Brits-Indië":"IND","India":"IND","Brazilië":"BRA","Griekenland":"GRC",
    "Finland":"FIN","Ierland":"IRL","Joegoslavië":"SRB","Socialistische Federale Republiek Joegoslavië":"SRB",
    "Nederlands-Indië":"IDN","Zuid-Afrika":"ZAF","Canada":"CAN","Estland":"EST",
    "Mandaatgebied Palestina":"ISR","Israël":"ISR","Filipijnen":"PHL","Roemenië":"ROU",
    "Albanië":"ALB","Volksrepubliek China":"CHN",
}
ISONAME = {"USA":"Verenigde Staten","DEU":"Duitsland","FRA":"Frankrijk","GBR":"Verenigd Koninkrijk",
    "ITA":"Italië","AUT":"Oostenrijk","RUS":"Sovjet-Unie / Rusland","DNK":"Denemarken","SWE":"Zweden",
    "NLD":"Nederland","MEX":"Mexico","CZE":"Tsjecho-Slowakije","POL":"Polen","BEL":"België","AUS":"Australië",
    "ESP":"Spanje","HUN":"Hongarije","CHE":"Zwitserland","JPN":"Japan","ARG":"Argentinië","NOR":"Noorwegen",
    "IND":"India","BRA":"Brazilië","GRC":"Griekenland","FIN":"Finland","IRL":"Ierland","SRB":"Joegoslavië",
    "IDN":"Nederlands-Indië","ZAF":"Zuid-Afrika","CAN":"Canada","EST":"Estland","ISR":"Palestina / Israël",
    "PHL":"Filipijnen","ROU":"Roemenië","ALB":"Albanië","CHN":"China"}
cmap = {}
for e in by_tt.values():
    if not e["co"] or e["year"] is None:
        continue
    iso = NL2ISO.get(e["co"][0])
    if not iso:
        continue
    dec = (e["year"] // 10) * 10
    c = cmap.setdefault(iso, {"n": ISONAME.get(iso, iso), "tot": 0, "dec": {}})
    c["tot"] += 1
    c["dec"][dec] = c["dec"].get(dec, 0) + 1
stats["countryMap"] = cmap

# 3) Regisseurs: films + geknipt/verboden
dir_stat = defaultdict(lambda: {"films": 0, "banned": 0, "cut": 0})
for e in by_tt.values():
    for d in (e["di"] or []):
        s = dir_stat[d]; s["films"] += 1
        if e["banned"]:  s["banned"] += 1   # verboden
        elif e["cut"]:   s["cut"] += 1      # geknipt (niet verboden) -> geen dubbeltelling
dirs = [{"n": d, **s} for d, s in dir_stat.items()]
for d in dirs:
    d["cens"] = d["banned"] + d["cut"]
    d["pct"] = round(100 * d["cens"] / d["films"]) if d["films"] else 0
stats["topDirectors"] = sorted(dirs, key=lambda x: -x["films"])[:18]
stats["censoredDirectors"] = sorted([d for d in dirs if d["cens"] >= 2], key=lambda x: -x["cens"])[:15]

# 4) Genre × oordeel
genre_o = defaultdict(lambda: Counter())
for e in by_tt.values():
    for g in (e["ge"] or []):
        genre_o[g][STRO[e["ostr"]]] += 1
        genre_o[g]["tot"] += 1
        if e["banned"]:  genre_o[g]["ban"] += 1
        elif e["cut"]:   genre_o[g]["cut"] += 1
genres_sorted = sorted(genre_o.items(), key=lambda kv: -kv[1]["tot"])[:12]
stats["genreOordeel"] = [{"g": g, "A": c["A"], "f14": c["14"], "f18": c["18"], "X": c["X"], "tot": c["tot"],
                          "cut": c["cut"], "ban": c["ban"]} for g, c in genres_sorted]

# 5) Acteurs: aanwezigheid, publieksbereik (IMDb-stemmen), censuur
if ac:
    astat = {}
    for tt, cast in ac.items():
        e = by_tt.get(tt)
        if e is None:
            continue
        reach = e["iv"] or 0
        cens = 1 if (e["banned"] or e["cut"]) else 0
        for a in cast:
            s = astat.setdefault(a["id"], {"n": a["n"], "id": a["id"], "films": 0, "reach": 0, "banned": 0, "cut": 0})
            s["films"] += 1; s["reach"] += reach
            if e["banned"]:  s["banned"] += 1
            elif e["cut"]:   s["cut"] += 1
    alist = list(astat.values())
    for a in alist:
        a["cens"] = a["banned"] + a["cut"]
        a["pct"] = round(100 * a["cens"] / a["films"]) if a["films"] else 0
    stats["topActors"] = sorted(alist, key=lambda x: -x["films"])[:24]
    # sterren in censuur: gerangschikt op aandeel van het (getoonde) oeuvre dat geknipt/verboden was
    stats["starsCensored"] = sorted([a for a in alist if a["films"] >= 12 and a["cens"] >= 4],
                                    key=lambda x: (-x["pct"], -x["cens"]))[:16]

# 6) Censuur door de tijd + filmlengte + smalfilm (per keuringsjaar, record-niveau)
cens_year = defaultdict(lambda: {"cut": 0, "banned": 0, "tot": 0})
len_year = defaultdict(list)
smal_year = defaultdict(lambda: {"smal": 0, "tot": 0})
for rec in films:
    yr = (rec.get("d") or "")[:4]
    if not yr.isdigit():
        continue
    y = int(yr)
    cens_year[y]["tot"] += 1
    if rec["o"] == "X":
        cens_year[y]["banned"] += 1
    if rec.get("k"):
        cens_year[y]["cut"] += 1
    smal_year[y]["tot"] += 1
    if rec.get("s"):
        smal_year[y]["smal"] += 1
    if rec.get("c") == 1 and rec.get("m") and 100 <= rec["m"] <= 6000:
        len_year[y].append(rec["m"])

def _median(xs):
    xs = sorted(xs); n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)

stats["censTimeline"] = [dict({"y": y}, **cens_year[y]) for y in sorted(cens_year)]
stats["lengthByYear"] = [{"y": y, "med": round(_median(len_year[y])), "n": len(len_year[y])}
                         for y in sorted(len_year) if len_year[y]]
stats["smalByYear"] = [{"y": y, "smal": smal_year[y]["smal"], "tot": smal_year[y]["tot"]}
                       for y in sorted(smal_year)]
stats["studioCoverage"] = {"withFabriek": sum(1 for r in films if r.get("f")),
                           "total": len(films), "distinct": len(studio_count)}

stats["coverage"] = {"tt": n_tt, "rating": n_rating, "poster": n_poster,
                     "country": sum(1 for e in by_tt.values() if e["co"]),
                     "director": sum(1 for e in by_tt.values() if e["di"]),
                     "cast": len(ac) if ac else 0, "films_tt": len(by_tt)}

meta = {"bron": "Nationaal Archief NT00402 / 2.04.60",
        "titel": "Filmkeuringsrapporten 1928-1960",
        "enriched": bool(cc), "posters": bool(tm)}

STATS_OUT = os.path.join(HERE, "stats.json")
FILMS_OUT = os.path.join(HERE, "films.json")
with open(STATS_OUT, "w", encoding="utf-8") as f:
    json.dump({"meta": meta, "stats": stats}, f, ensure_ascii=False, separators=(",", ":"))
with open(FILMS_OUT, "w", encoding="utf-8") as f:
    json.dump({"meta": meta, "films": films}, f, ensure_ascii=False, separators=(",", ":"))

print(f"{len(films)} films -> stats.json ({os.path.getsize(STATS_OUT)/1e3:.0f} KB) + films.json ({os.path.getsize(FILMS_OUT)/1e6:.1f} MB)")
print(f"verboden={banned}  geknipt={coupures}  herkeuringen={herk}")
print("top studio's:", ", ".join(f'{s["n"]}({s["c"]})' for s in top_studios[:8]))
