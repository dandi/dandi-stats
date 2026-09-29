# DANDI Stats

Summary plots for the [DANDI Archive](https://dandiarchive.org), published at [stats.dandiarchive.org](https://stats.dandiarchive.org).

## Repository layout

| Path | Description |
| --- | --- |
| [`src/dandi_stats.py`](src/dandi_stats.py) | Fetches metadata for all non-empty Dandisets and aggregates it into summary CSVs in `data/` |
| [`src/index.html`](src/index.html) | Static page that loads the CSVs and renders the plots |
| [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml) | Runs the Python script daily, commits CSVs, deploys the site to GitHub Pages |
| [`data/`](data/) | Generated summary CSVs, each split by access status (`OPEN` / `EMBARGOED`) |
| [`data/summary_timeseries.csv`](data/summary_timeseries.csv) | Number of Dandisets and bytes added per month |
| [`data/summary_sizes.csv`](data/summary_sizes.csv) | Histogram of the Dandiset sizes |
| [`data/summary_subjects.csv`](data/summary_subjects.csv) | Histogram of the number of subjects per Dandiset |
| [`data/summary_species.csv`](data/summary_species.csv) | Dandiset counts by species |
| [`data/summary_modalities.csv`](data/summary_modalities.csv) | Dandiset counts by data modality |

