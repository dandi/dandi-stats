import os
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
}

data = defaultdict(list)
failed = []
for dandiset in tqdm(dandisets):
    try:
        if not dandiset.draft_version.size:
            continue
        metadata = dandiset.get_raw_metadata()

        data["created"].append(dandiset.created.date())
        data["size"].append(dandiset.draft_version.size)
        data["access"].append(dandiset.embargo_status.name)

        species = metadata["assetsSummary"].get("species")
        data["species"].append(species[0]["name"] if species else np.nan)

        data["numberOfSubjects"].append(metadata["assetsSummary"].get("numberOfSubjects", np.nan))

        variables_measured = metadata["assetsSummary"].get("variableMeasured") or []
        for modality, ndtypes in neurodata_replacement.items():
            data[modality].append(any(x in ndtypes for x in variables_measured))
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

# Number of Dandisets created and size added per month for plots A and B
df["period"] = pd.to_datetime(df["created"]).dt.to_period("M").astype(str)
grouped = df.groupby(["period", "access"])
timeseries = pd.DataFrame({
    "number_added": grouped.size(),
    "size_added": grouped["size"].sum(),
}).reset_index()
os.makedirs("data", exist_ok=True)
timeseries.to_csv("data/summary_timeseries.csv", index=False)

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
histogram_by_access(log_size, size_edges).to_csv("data/summary_sizes.csv", index=False)

subject_edges = np.linspace(0, 4, 31)
log_subjects = np.log10(df["numberOfSubjects"].where(df["numberOfSubjects"] > 0))
histogram_by_access(log_subjects, subject_edges).to_csv("data/summary_subjects.csv", index=False)

(
    df.dropna(subset=["species"])
      .groupby(["species", "access"])
      .size()
      .reset_index(name="count")
      .to_csv("data/summary_species.csv", index=False)
)

modality_cols = list(neurodata_replacement)
(
    df[modality_cols + ["access"]]
      .melt(id_vars="access", var_name="modality", value_name="present")
      .query("present")
      .groupby(["modality", "access"])
      .size()
      .reset_index(name="count")
      .to_csv("data/summary_modalities.csv", index=False)
)

