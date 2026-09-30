# DANDI Stats

Summary plots for the [DANDI Archive](https://dandiarchive.org), published at [stats.dandiarchive.org](https://stats.dandiarchive.org).

## Repository layout

| Path | Description |
| --- | --- |
| [`src/dandi_stats.py`](src/dandi_stats.py) | Fetches metadata for all non-empty Dandisets and aggregates it into summary CSVs in `data/` |
| [`src/index.html`](src/index.html) | Static page that loads the CSVs and renders the plots |
| [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml) | Runs the Python script daily, commits CSVs, deploys the site to GitHub Pages |
| [`data/`](data/) | Generated summary CSVs, each split by access status (`OPEN` / `EMBARGOED`) |
| [`data/timeseries.csv`](data/timeseries.csv) | Number of Dandisets and bytes added per month |
| [`data/sizes.csv`](data/sizes.csv) | Histogram of the Dandiset sizes |
| [`data/subjects.csv`](data/subjects.csv) | Histogram of the number of subjects per Dandiset |
| [`data/species.csv`](data/species.csv) | Dandiset counts by species |
| [`data/modalities.csv`](data/modalities.csv) | Dandiset counts by data modality |

