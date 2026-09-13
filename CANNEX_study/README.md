# CANNEX study reproducibility bundle

This directory preserves the exact inputs and complete saved outputs for the
two pain/gut-brain metabolite screens reported in the manuscript. The files are
reproducibility records; they do not change or direct the core Python pipeline.

## Contents

| Analysis | Locked GEM panel | Saved output | Recorded runtime |
|---|---:|---|---:|
| Core-6 | 29 AGORA2 v2.01 models | 2,793 retained model-level potential edges | Not retained in the original run record |
| Core-15 | 37 AGORA2 v2.01 models | 6,688 retained model-level potential edges | 4,093.80 seconds (68.23 minutes) |

Each analysis directory contains five files:

- `models.zip`: unmodified AGORA2 SBML files plus the matching model manifest;
- `model_manifest.tsv`: directly readable copy of the manifest, including one
  SHA-256 identity per model;
- `targets.tsv`: the seven literature-selected targets fixed before screening;
- `results.xlsx`: primary user-facing saved pipeline output; and
- `results.json.gz`: losslessly compressed machine-readable companion retained
  only for reproducibility and automated checking. After decompression, this
  is byte-identical to the original saved JSON.

The manifests are preserved exactly as used in the analyses. Their historical
`redistributed` field therefore still says that redistribution had not yet been
assessed when the run was locked. The current release attribution and
redistribution record is `THIRD_PARTY_DATA_NOTICE.md`.

The validation inputs and outputs remain under `validation/`. Their locked
summary is `validation/validation_summary.csv`, and their formal case registry
is `validation/VALIDATION_INDEX.tsv`.

## Re-running one analysis

1. Create the pinned environment from the repository root using
   `environment.yml`.
2. Extract `models.zip` into an empty `models` directory inside the selected
   analysis directory. Do not rename or edit the XML files.
3. From the repository root, verify the input before starting the long run:

```bash
python find_crossfeeding.py \
  --gem-dir CANNEX_study/core6/models \
  --targets CANNEX_study/core6/targets.tsv \
  --check-only
```

4. Run the analysis only when output generation is intended:

```bash
python find_crossfeeding.py \
  --gem-dir CANNEX_study/core6/models \
  --targets CANNEX_study/core6/targets.tsv \
  --output CANNEX_study/core6/rerun_results.xlsx
```

Replace `core6` with `core15` for the second panel. The rerun creates a new
Excel workbook and adjacent JSON file; it does not overwrite the locked files
unless the locked filename is explicitly supplied.

## Recorded analysis environment

- Python 3.11
- MeneTools 3.4.0
- clyngor-with-clingo 5.8.0.post1
- openpyxl 3.1.5
- scipy 1.17.1
- AGORA2 HighFiber diet
- Anaerobic target-withheld condition
- Deterministic scientific stages with `PYTHONHASHSEED=0`

The pipeline files used for the Core-15 run match the files currently included
in this release. Their identities are listed in `PIPELINE_SHA256SUMS`.
Distributed-file hashes are listed in `SHA256SUMS`; hashes of the original
JSON files after decompression are listed in `ORIGINAL_JSON_SHA256SUMS`.
From inside this directory, verify the distributed files with
`shasum -a 256 -c SHA256SUMS` on macOS/Linux or the equivalent SHA-256 checker
on Windows.

These outputs represent qualitative GEM-supported potential cross-species
precursor-supply edges. They do not demonstrate secretion quantity, physical
transfer, community flux, recipient growth benefit, in vivo cross-feeding, or
causality for pain.
