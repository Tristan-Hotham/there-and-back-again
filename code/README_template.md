# There and Back Again

{{n_journeys}} great journeys from about 600 BC to 1947, mapped out and back, and graded by the evidence that they happened: proven, probable, disputed or legend.

**Interactive version:** https://tristan-hotham.github.io/there-and-back-again/

This repository holds the interactive page, the journey, waypoint and passage data, and the code for the data study *There and Back Again: 2,500 years of great journeys, and how sure we are that they happened* by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- {{n_journeys}} journeys, {{n_stops}} named stops. By evidence: {{grade_counts.Proven}} proven, {{grade_counts.Probable}} probable, {{grade_counts.Disputed}} disputed, {{grade_counts.Legend}} legend.
- Of the {{pre1450.n}} journeys that began before 1450, {{pre1450.proven}} are proven; of the {{post1450.n}} that began later, {{post1450.proven}} are. All {{grade_counts.Legend}} legends begin before 1450.
- Conjectural stops: {{stop_conf_by_grade.Proven.share_conjectural|pct0}} on proven journeys, {{stop_conf_by_grade.Probable.share_conjectural|pct0}} on probable, {{stop_conf_by_grade.Disputed.share_conjectural|pct0}} on disputed and {{stop_conf_by_grade.Legend.share_conjectural|pct0}} on legends.
- Did they come back? {{return_counts.returned}} returned, {{return_counts.some}} partly, {{return_counts.never}} never, {{return_counts.unknown}} unknown.
- On {{n_passages}} dated passages, sailing ships made a median {{sail_median_kmd|f0}} km a day; da Gama took {{da_gama_out_back.out_days}} days from Malindi to Calicut and {{da_gama_out_back.back_days}} days back.
- Where the article states a distance, my drawn routes come to {{stated_vs_drawn_ratio_range.0|pct0}} to {{stated_vs_drawn_ratio_range.1|pct0}} of it ({{stated_vs_drawn_n}} journeys).

## Files

- `index.html`: the interactive page (D3 map with an Antarctic inset, timeline, charts, story cards).
- `header.png`: social card.
- `data/journeys.csv`: one row per journey: who, when, region, mode, grade and the reason for it, evidence types, whether they came back, drawn distances, share of the route between identifiable places, pace where dated, distance stated in the article, counts of stops by confidence, and the Wikipedia articles and sections used.
- `data/waypoints.csv`: every stop and drawn routing point in order, with date, leg (out or back), confidence (known, approximate, conjectural, or drawn), where the coordinates came from, and the Wikipedia article and section that names the stop.
- `data/passages.csv`: the {{n_passages}} passages with departure and arrival dates, their drawn distance and kilometres per day.
- `data/routes.geojson`: the drawn routes as lines (out and back legs).
- `data/results.json`: every number quoted on the page, in the paper, blog and collage.
- `code/`: Python scripts. Run in order: `build_data.py` (uses `journeys_spec.py` and `searoute.py`), `analyse.py`, `build_site.py`, `make_header.py`. `journeys_spec.py` is the hand-built specification of every journey, with the grade, the reason and the source of every stop.
- `release/`: the paper (`Hotham_There_and_Back_Again.pdf`, with its LaTeX source, template and figures in `release/paper/`), blog figures and post, and the Zenodo files. Run `release/make_figures.py`, then `release/paper/build_paper.py`, then `release/make_zenodo.py`.
- `reddit/`: the summary collage (`there_and_back_again.png`) and the script that draws it.

## Method in brief

For each journey I read the English Wikipedia article (and related articles) for the route, dates, evidence and debates, and listed the stops it names, in order, with the article and section. Coordinates come from the Wikipedia article of each place (via the MediaWiki API), from GeoNames where the article names a region or old site (a nearby town is used and noted), or from positions given in the article text. Sea legs are routed round land on a 0.5 degree ocean grid from Natural Earth and smoothed; land legs are great circles. Drawn routing points shape the line and are never shown as stops. Grades: Proven (archaeology, physical remains or several independent records), Probable (one good written source), Disputed (serious scholarly argument), Legend (myth, legend, oral tradition or speculation).

Caveats: the grades are judgements; the selection of journeys is mine and not a sample; the routes show the order of places, not tracks; Wikipedia is the only source for most facts, with a few checks noted in the data.

## Sources and licences

- English Wikipedia articles (text CC BY-SA 4.0), listed per journey in `data/journeys.csv` and per stop in `data/waypoints.csv`. Article coordinates via the MediaWiki API.
- GeoNames cities1000 (CC BY 4.0), https://www.geonames.org/
- Natural Earth 1:50m countries (public domain), https://www.naturalearthdata.com/
- Ioannidis, A. G. and others (2020) Native American gene flow into Polynesia predating Easter Island settlement. *Nature* 583, 572 to 577. https://pubmed.ncbi.nlm.nih.gov/32641827/ (cited for the Polynesian contact grade).
- Page libraries: D3 (ISC licence) from cdnjs.

Because the routes and text draw on Wikipedia, the data and the page text are released under CC BY-SA 4.0. Code is MIT (see `LICENSE`).

## How to rerun

Python 3 with numpy, shapely (2.x) and matplotlib. The inputs (Wikipedia wikitext and link coordinates, GeoNames cities1000, Natural Earth) are read from local paths set at the top of `code/build_data.py`, `code/searoute.py` and `code/analyse.py`. Then run the four scripts above from `code/`.

## Citation

Hotham, T. (2026) *There and Back Again: 2,500 years of great journeys, and how sure we are that they happened*. Zenodo. https://doi.org/10.5281/zenodo.23686756

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
