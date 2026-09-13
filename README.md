# Target-guided potential cross-feeding workflow

This Python pipeline identifies genome-scale metabolic model (GEM)-supported
potential microbial cross-feeding relationships that may contribute to the
production of user-selected, host-relevant metabolites. Given a selected set
of microbial GEMs and target metabolites, it traces potential
donor -> precursor -> recipient -> target-metabolite relationships and reports
the resulting potential edges in an Excel workbook.

The pipeline was developed to connect predicted microbe-microbe metabolic
interactions with host-microbiome research in human health and disease.

## Inputs and output

The user supplies:

- a selected set of microbial GEMs in SBML/XML format; and
- a table of microbial metabolites selected for their relevance to the host
  question.

The primary user-facing output is an Excel workbook containing potential
cross-feeding edges and the model-level evidence used to retain or exclude
them. The pipeline does not perform taxon selection, ASV-to-16S mapping,
literature screening, species-level frequency calculation or network
visualization. These steps, when required, are separate study-specific
analyses.

## Six-stage workflow

1. **Resolve target ID:** match each user-selected target to metabolite
   identifiers in the supplied GEMs.
2. **Confirm target exchange:** require an exchange reaction that permits the
   target to leave the model.
3. **Trace outward target transport:** require transport from the cytosol to
   the extracellular compartment, including the periplasm for models that use
   one.
4. **Find target-withheld paths and precursor roots:** withhold the target and
   oxygen, search for alternative intracellular target-production paths and
   identify their extracellular precursor roots.
5. **Confirm precursor import:** require the recipient to import a nominated
   precursor from the environment and transport it to the compartment where
   the production path consumes it.
6. **Confirm donor supply:** require a different-species donor to produce the
   precursor, transport it outward and permit its exchange export.

The search uses MeneTools 3.4.0 for qualitative metabolic reachability. It is
not a flux, yield or abundance calculation.

For the complete scientific definitions, see
[docs/METHOD.md](docs/METHOD.md).

## Installation

Python 3.11 is recommended. Download or clone this repository, open a terminal
in the repository folder and use either Conda or a standard Python virtual
environment.

### Conda

```bash
conda env create -f environment.yml
conda activate crossfeeding-workflow
```

### Python virtual environment

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

All resource paths are resolved relative to this repository or are provided
when the command is run. No user-specific Mac or Windows path is required.

## Quick tutorial: Case 01

Case 01 asks whether changing the donor changes an L-lactate-supported
butyrate edge while the recipient and target remain fixed:

```text
Expected positive:
Bifidobacterium adolescentis L2-32
    -> L-lactate
Eubacterium hallii L2-7
    -> butyrate

Expected negative:
Paraprevotella xylaniphila YIT 11841
    -X-> L-lactate
Eubacterium hallii L2-7
    -> butyrate
```

The positive relationship is supported by Belenguer et al. (2006), who tested
the exact positive strains in coculture. The negative expectation is supported
by the fermentation products reported for the exact YIT 11841 strain by
Morotomi et al. (2009).

- Belenguer A, et al. *Applied and Environmental Microbiology*. 2006.
  [doi:10.1128/AEM.72.5.3593-3599.2006](https://doi.org/10.1128/AEM.72.5.3593-3599.2006)
- Morotomi M, et al. *International Journal of Systematic and Evolutionary
  Microbiology*. 2009.
  [doi:10.1099/ijs.0.008169-0](https://doi.org/10.1099/ijs.0.008169-0)

First check the installation, model files, manifest and target table without
running the analysis:

```bash
python find_crossfeeding.py \
  --gem-dir validation/cases/01_two_donors_control/models \
  --targets validation/cases/01_two_donors_control/config/targets.tsv \
  --check-only
```

Then generate a new Excel workbook under `outputs/`. This protects the locked
validation result distributed with the repository.

```bash
python find_crossfeeding.py \
  --gem-dir validation/cases/01_two_donors_control/models \
  --targets validation/cases/01_two_donors_control/config/targets.tsv \
  --output outputs/case01_example.xlsx
```

### Case 01 result

Open `outputs/case01_example.xlsx`. The unbiased search retains seven
potential edges overall. Within the prespecified L-lactate comparison, the
expected positive *B. adolescentis* L2-32 donor edge is retained, whereas the
*P. xylaniphila* YIT 11841 donor edge is excluded because donor L-lactate
production was not retained.

**Interpretation:** The pipeline distinguished a literature-supported positive
donor from a biologically defined negative donor while holding the recipient,
precursor and target constant. The retained record represents GEM-supported
structural potential, not proof of metabolite transfer in vivo.

## Preparing your own input data

Users begin with an already selected and quality-checked set of GEMs. Taxon
selection, sequencing analysis, ASV-to-reference matching, GEM reconstruction
and biological literature selection are the user's responsibility and are
outside the scope of this pipeline.

### 1. Place the selected GEMs together

Place only the intended SBML/XML models in one folder, for example:

```text
my_models/
├── organism_01.xml
├── organism_02.xml
└── organism_03.xml
```

### 2. Generate and review the model manifest

```bash
python create_model_manifest.py --gem-dir my_models
```

This creates `my_models/model_manifest.tsv`. It checks XML readability,
required cytosolic and extracellular compartments, records an optional
periplasm, extracts model metadata and calculates a SHA-256 checksum for each
file. Review the inferred species and strain information before analysis.

### 3. Prepare the target table

Copy `config/clinical_targets.tsv` and edit the copy. Required columns are:

- `target_name`
- `base_id`
- `host_relevance`
- `metabolite_class`
- `microbial_evidence`
- `selection_rationale`
- `reference`

Targets must be selected before running the pipeline. A target identifier that
cannot be found in the supplied GEMs is reported as unresolved rather than
silently discarded.

### 4. Check the inputs

```bash
python find_crossfeeding.py \
  --gem-dir my_models \
  --targets my_targets.tsv \
  --check-only
```

### 5. Run the pipeline

```bash
python find_crossfeeding.py \
  --gem-dir my_models \
  --targets my_targets.tsv \
  --output outputs/crossfeeding_results.xlsx
```

## Understanding the Excel workbook

Start with the following worksheets:

- **Run Summary:** analysis settings and result counts.
- **Strain Key:** model files, model identifiers, species and strains.
- **Results:** tested donor-precursor-recipient-target relationships and their
  final keep or exclude decision.
- **Candidate Pathways:** recipient reaction sets and their extracellular
  precursor roots.
- **Donor Audits** and **Donor Evidence:** donor production, outward transport
  and exchange-export decisions with supporting reactions.
- **Consumer Audits** and **Consumer Evidence:** recipient target-production,
  transport and precursor-import checks with supporting reactions.

For biological interpretation, begin with the retained records in **Results**
and use the evidence worksheets to examine why a relationship was retained or
excluded.

Single- versus multi-root classification across strains, literature-supported
filtering and network visualization are post-hoc analyses. They are not
reported as outputs of the core pipeline.

## Additional tutorials: Cases 02-08

The remaining examples cover a matched recipient control, exact-strain
positive relationships and cases that expose incomplete GEM representation.
Each tutorial contains its supporting paper, run command, Excel result and a
short interpretation.

| Case | Relationship tested | Result status | Tutorial |
|---|---|---|---|
| 02 | One donor and two recipients; L-lactate to butyrate | Positive retained; negative excluded | [Open](validation/README.md#case-02-one-donor-and-two-recipients) |
| 03 | Succinate-supported propionate production | Expected edge retained | [Open](validation/README.md#case-03-succinate-to-propionate) |
| 04 | Acetate-supported butyrate production | Expected edge retained | [Open](validation/README.md#case-04-acetate-to-butyrate) |
| 05 | L-lactate-supported hydrogen-sulfide production | Expected edge retained | [Open](validation/README.md#case-05-l-lactate-to-hydrogen-sulfide) |
| 06 | Ornithine/arginine-linked putrescine production | Partial pathway match | [Open](validation/README.md#case-06-putrescine-pathway) |
| 07 | Indole-3-lactate to indole-3-propionate | Expected edge absent from donor GEM | [Open](validation/README.md#case-07-indole-3-lactate-to-indole-3-propionate) |
| 08 | Cholate to deoxycholate | Recipient route found; donor supply absent | [Open](validation/README.md#case-08-cholate-to-deoxycholate) |

## Scope and interpretation

A retained edge means that the supplied GEMs encode a qualitative,
directionally compatible donor-precursor-recipient-target route under the
configured environment. It does not establish secretion quantity, community
flux, physical transfer, recipient growth benefit, realized in vivo
cross-feeding or a causal host effect.

MeneTools selects cardinality-minimal reaction sets under each search state.
These are not necessarily the shortest biochemical route, the highest-yield
route or the biologically preferred route. Alternative pathways depend on the
reactions and annotations represented in the supplied GEMs.

## Developer and release verification

These commands are for verifying the software release; users do not need them
for routine analysis.

```bash
python -m unittest discover -s tests -v
python validate_expected_cases.py
```

The first command runs the automated unit and regression checks. The second
checks the seven prespecified comparisons stored in Cases 01-05.

## Repository contents

- `find_crossfeeding.py`: main pipeline entry point.
- `create_model_manifest.py`: GEM manifest and checksum generator.
- `src/`: six pipeline stages and Excel writer.
- `config/`: default target, diet and regression configuration.
- `validation/`: eight literature-grounded tutorials and locked result files.
- `CANNEX_study/`: exact Core-6 and Core-15 model panels, targets, results and
  checksums used for CANNEX manuscript reproducibility.
- `tests/`: automated release checks.
- `windows/`: Windows setup and compatibility-test helpers.
- `visualization/`: exact R reproduction of the manuscript validation panels
  and Core-6/Core-15 GABA and butyrate networks; separate from the core Python
  pipeline.

## Citation and licence

The software is distributed under the BSD 3-Clause licence. Author and
software citation information is provided in `CITATION.cff`. The associated
manuscript citation and permanent archive DOI will be added when available.

AGORA2 models remain third-party data. Their provenance and applicable terms
are described in
[CANNEX_study/THIRD_PARTY_DATA_NOTICE.md](CANNEX_study/THIRD_PARTY_DATA_NOTICE.md).
