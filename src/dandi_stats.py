import os
import re
import pandas as pd
import numpy as np
from dandi.dandiapi import DandiAPIClient
from collections import defaultdict
from tqdm import tqdm

client = DandiAPIClient()
client.dandi_authenticate()
dandisets = list(client.get_dandisets(embargoed=True, empty=False))

species_replacement = {
    "House mouse": "Mouse",
    "Mus musculus - House mouse": "Mouse",
    "Scotinomys teguina - Alston's brown mouse": "Mouse",
    "Rattus norvegicus - Norway rat": "Rat",
    "Brown rat": "Rat",
    "Rat; norway rat; rats; brown rat": "Rat",
    "Homo sapiens - Human": "Human",
    "Drosophila melanogaster - Fruit fly": "Fruit fly",
    "Cricetulus griseus - Cricetulus aureus": "Hamster",
    "Procambarus clarkii - Red swamp crayfish": "Crayfish",
    "Caenorhabditis elegans": "C. elegans",
    "Oryctolagus cuniculus - Rabbits": "Rabbit",
    "Ooceraea biroi - Clonal raider ant": "Ant",
    "Macaca mulatta - Rhesus monkey": "Macaque",
    "Rhesus monkey": "Macaque",
    "Macaca fascicularis - Cynomolgus monkeys": "Macaque",
    "Danio rerio - Zebra fish": "Zebra fish",
    "Macaca nemestrina - Pig-tailed macaque": "Macaque",
    "Macaca nemestrina - Pigtail macaque": "Macaque",
    "Macaca nemestrina": "Macaque",
    "Rhesus macaque": "Macaque",
    "Callithrix jacchus - Common marmoset": "Marmoset",
    "Bos taurus - Cattle": "Cattle",
    "Sus scrofa domesticus - Domestic pig": "Pig"
}

neurodata_replacement = {
    "extracellularephys": ["LFP", "Units", "ElectricalSeries"],
    "opticalphysiology": ["PlaneSegmentation", "TwoPhotonSeries", "ImageSegmentation"],
    "intracellularephys": ["PatchClampSeries", "VoltageClampSeries", "CurrentClampSeries"],
    "behavior": ["BehavioralEpochs", "BehavioralEvents", "BehavioralTimeSeries", "Position"],
    "eyetracking": ["EyeTracking", "PupilTracking"],
    "optogenetics": ["OptogeneticSeries"],
    "fiberphotometry": ["FiberPhotometryResponseSeries", "FiberPhotometryTable", "fiber photometry", "fiber photometry approach"],
}

microscopy_suffixes = [
    "2PE", "BF", "CARS", "CONF", "DIC", "DF", "FLUO", "MPE", "NLO",
    "OCT", "PC", "PLI", "SEM", "SPIM", "SR", "TEM", "XPCT", "uCT",
]
microscopy_pattern = re.compile(
    rf"_({'|'.join(microscopy_suffixes)})\.(ome\.tif|ome\.btf|ome\.zarr|tif|png)$"
)

def has_microscopy(metadata, assets):
    standards = [s.get("name", "") for s in metadata["assetsSummary"].get("dataStandard") or []]
    if not any("BIDS" in s or "NGFF" in s for s in standards):
        return False

    return any(microscopy_pattern.search(asset.path) for asset in assets)

data = defaultdict(list)
asset_sizes = defaultdict(int)
failed = []
for dandiset in tqdm(dandisets):
    try:
        if not dandiset.draft_version.size:
            continue
        metadata = dandiset.get_raw_metadata()
        assets = list(dandiset.get_assets())
        access = dandiset.embargo_status.name

        data["created"].append(dandiset.created.date())
        data["size"].append(dandiset.draft_version.size)
        data["access"].append(access)

        species = metadata["assetsSummary"].get("species")
        data["species"].append(species[0]["name"] if species else np.nan)

        data["numberOfSubjects"].append(metadata["assetsSummary"].get("numberOfSubjects", np.nan))

        # Detect modalities by matching metadata values against neurodata_replacement
        modality_labels = list(metadata["assetsSummary"].get("variableMeasured") or [])
        modality_labels += metadata.get("keywords") or []
        for field in ("measurementTechnique", "approach"):
            for item in metadata["assetsSummary"].get(field) or []:
                modality_labels.append(item.get("name", ""))
        for item in metadata.get("about") or []:
            modality_labels.append(item.get("name", ""))
        modality_labels = {x.lower() for x in modality_labels}

        for modality, ndtypes in neurodata_replacement.items():
            data[modality].append(any(x.lower() in modality_labels for x in ndtypes))
        data["microscopy"].append(has_microscopy(metadata, assets))

        for asset in assets:
            asset_sizes[(asset.modified.strftime("%Y-%m"), access)] += asset.size
    except Exception as e:
        failed.append((dandiset.identifier, repr(e)))

if failed:
    print(f"Skipped {len(failed)} dandiset(s) due to errors:")
    for identifier, err in failed:
        print(f"  {identifier}: {err}")

df = pd.DataFrame(data)
df = df.sort_values(
    ["access", "created"],
    key=lambda col: col == "EMBARGOED" if col.name == "access" else col,
).reset_index(drop=True)
df["species"] = df["species"].replace(species_replacement)

# Number of Dandisets created (plot B) and bytes of assets created/updated (plot C) per month
df["period"] = pd.to_datetime(df["created"]).dt.to_period("M").astype(str)
number_added = df.groupby(["period", "access"]).size()
size_added = pd.Series(asset_sizes, dtype="int64")
size_added.index.names = ["period", "access"]
timeseries = (
    pd.DataFrame({"number_added": number_added, "size_added": size_added})
      .fillna(0)
      .astype("int64")
      .sort_index()
      .reset_index()
)
os.makedirs("data", exist_ok=True)
timeseries.to_csv("data/timeseries.csv", index=False)

# Create summaries for plots C-F
def histogram_by_access(values, edges):
    rows = []
    for access in ("OPEN", "EMBARGOED"):
        mask = (df["access"] == access) & values.notna()
        counts, _ = np.histogram(values[mask], bins=edges)
        for i, count in enumerate(counts):
            rows.append({
                "bin_left": round(edges[i], 2),
                "bin_right": round(edges[i + 1], 2),
                "access": access,
                "count": int(count),
            })
    return pd.DataFrame(rows)

size_edges = np.linspace(2, 16, 29)
log_size = np.log10(df["size"].where(df["size"] > 0))
histogram_by_access(log_size, size_edges).to_csv("data/sizes.csv", index=False)

subject_edges = np.linspace(0, 4, 31)
log_subjects = np.log10(df["numberOfSubjects"].where(df["numberOfSubjects"] > 0))
histogram_by_access(log_subjects, subject_edges).to_csv("data/subjects.csv", index=False)

(
    df.dropna(subset=["species"])
      .groupby(["species", "access"])
      .size()
      .reset_index(name="count")
      .to_csv("data/species.csv", index=False)
)

modality_cols = list(neurodata_replacement) + ["microscopy"]
(
    df[modality_cols + ["access"]]
      .melt(id_vars="access", var_name="modality", value_name="present")
      .query("present")
      .groupby(["modality", "access"])
      .size()
      .reset_index(name="count")
      .to_csv("data/modalities.csv", index=False)
)

