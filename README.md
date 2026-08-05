# De Filmkeuring 1928–1960

Doorzoekbaar dashboard en filmdatabase van de keuringsrapporten van de **Centrale
Commissie voor de Filmkeuring**. Van 1928 tot 1960 moest elke film die in Nederland
vertoond werd langs deze commissie; van elke keuring werd een rapport opgemaakt.

**Live:** https://filmkeuring.alanmoss.nl

- **Dashboard** — tijdlijn van de oordelen per jaar (met de bezettingsdip 1940–’45),
  de meest voorkomende productiemaatschappijen met land van herkomst, en de verdeling
  van het eindoordeel.
- **Het kabinet van de verboden film** — galerij van alle 796 geheel geweigerde films.
- **Explorer** — doorzoek alle 48.499 rapporten op titel, studio of aanvrager; filter
  op leeftijdsoordeel, geknipte films, herkeuringen en fictie.

Elke film linkt door naar [Cinema Context](https://www.cinemacontext.nl), naar het
originele keuringsdossier bij het Nationaal Archief, en — waar bekend — naar IMDb met
poster en beoordeling.

## Bron

Nationaal Archief, index **NT00402** (toegang 2.04.60, *Commissie voor de Filmkeuring*),
zoekhulp: https://www.nationaalarchief.nl/onderzoeken/zoekhulpen/filmkeuringsrapporten-1928-1960.
De ruwe export staat in `NT00402_FILMKEURINGSRAPPORTEN.csv` (48.499 records, CC0).

## Pijplijn

```bash
python3 parse.py          # CSV → stats.json (dashboard) + films.json (explorer)

python3 enrich_cc.py       # ~20.900 Cinema Context-pagina's → IMDb-id's (cc_imdb.json)
export TMDB_KEY=...         # gratis v3-sleutel via themoviedb.org
python3 enrich_tmdb.py      # IMDb-id's → poster + beoordeling (tmdb.json)
python3 parse.py           # opnieuw: verrijking wordt nu meegebouwd
```

Het dashboard en de explorer zijn statische HTML die `stats.json` en `films.json`
client-side inladen. Lokaal draaien:

```bash
python3 -m http.server 8899
```

## Licentie

Broncode: MIT. De onderliggende gegevens zijn afkomstig van het Nationaal Archief (CC0).
Posters en beoordelingen via [TMDb](https://www.themoviedb.org) (niet door TMDb bekrachtigd).
