# Future package development decisions

## Status

These are agreed requirements for a future package. They are **not implemented
in the current manuscript prototype**, and this document does not change the
current analysis or its saved validation results.

## 1. Transport to the consuming compartment

A pathway root must be transportable from the environment to the compartment
where its first consuming reaction occurs. The package must not require every
root to reach the cytosol.

Accepted examples include:

```text
environment -> periplasm
environment -> cytosol
environment -> periplasm -> cytosol
```

For each root, the output should report the first consuming reaction, its
compartment, and the directionally valid transport chain reaching that
compartment.

## 2. Complete supply accounting for multi-root pathways

For a pathway such as:

```text
A + B + C -> target
```

every required root must have a valid source. A root may be supplied by the
environment or by a donor that can form it intracellularly, transport it
outward, and export it.

### 2A. One donor-supplied focal precursor

When testing `A` as the focal cross-fed precursor:

- `A` is withheld from the environment and must be supplied by a donor.
- `B` and `C` may be supplied by the environment.
- `B` and `C` must still reach the compartments where their first consuming
  reactions occur.

```text
donor 1 -> A
environment -> B + C
A + B + C -> recipient -> target
```

### 2B. Multiple donor-supplied roots

If `B` or `C` is not environmentally available, the missing roots may be
supplied by the same donor or by different donors.

```text
donor 1 -> A
donor 2 -> B
donor 1 or donor 3 -> C
A + B + C -> recipient -> target
```

The complete pathway is retained only when every required root has at least one
valid supply source. The result may therefore be a community-supported route,
not only a pairwise donor-recipient edge.

Common gut metabolites such as carbon dioxide and ethanol must not be removed
solely because many organisms can produce them. Their source should instead be
reported as environmental, single-donor, or multi-donor supported.

## 3. Collapse strain-level results to species-level relationships

The package must preserve the complete strain-level audit but provide a second,
non-redundant species-level result. Strain rows should be grouped using the
directional key:

```text
target + donor species + precursor/root + recipient species
```

For every collapsed relationship, retain:

- all supporting donor GEM and strain identifiers;
- all supporting recipient GEM and strain identifiers;
- the number of supporting donor GEMs;
- the number of supporting recipient GEMs;
- the number of supported donor-recipient GEM combinations;
- the total number of available GEMs for each species; and
- links back to every strain-level reaction and pathway record.

Collapsing must remove presentational redundancy without discarding
strain-specific disagreement. A species-level edge is a summary of model-panel
support, not evidence that every strain of the species has the pathway.

## 4. Strain-frequency criterion for broadly supported pathways

The package should calculate within-species GEM-support frequencies separately
for the donor and recipient roles:

```text
donor frequency = supporting donor GEMs / all available donor GEMs for the donor species
recipient frequency = supporting recipient GEMs / all available recipient GEMs for the recipient species
```

A candidate broadly supported species-level edge should require both frequencies
to be at least 0.30 (30%):

```text
donor frequency >= 0.30 AND recipient frequency >= 0.30
```

The output should also report the joint supported-pair frequency:

```text
supported donor-recipient GEM pairs / all possible donor-recipient GEM pairs
```

This is a GEM-panel frequency, not a population prevalence estimate. The raw
numerator and denominator must always be shown. Species represented by very few
GEMs, especially one model, should receive a low-coverage flag and must not be
called universal merely because 1/1 models pass. The 30% threshold should be a
configurable package parameter, with 0.30 as the agreed default.

## 5. GEM file-encoding QC and safe normalization

The package must inspect the actual byte encoding before parsing XML/SBML. It
should distinguish at least UTF-8, UTF-8 with a byte-order mark, Latin-1, and
common Windows-1252 cases, and report the detected encoding and any invalid byte
location.

The source GEM must never be silently overwritten. When normalization is
requested, create a new UTF-8 copy, preserve the original file, record SHA-256
checksums for both files, and rerun XML and SBML validation on the normalized
copy. Encoding repair must be reported separately from biological or SBML
quality findings.

## 6. Input adapters for multiple GEM sources

The package should support AGORA/AGORA2, APOLLO, CarveMe, gapseq, and custom
SBML GEMs through a common internal model representation. Source-specific
adapters should normalize or map:

- cytosol, extracellular and periplasm compartment conventions;
- exchange, demand, sink and transport-reaction conventions;
- reaction direction and FBC bound representations;
- metabolite identifiers and annotations across VMH, BiGG, ModelSEED,
  MetaNetX, KEGG and custom namespaces;
- species, strain and model metadata; and
- model-specific missing or non-standard fields.

Each adapter should have small fixed test models and expected QC, transport,
production and export results. Unknown custom formats should fail with an
actionable report rather than being silently interpreted as an AGORA model.

The exact APOLLO format and identifier conventions should be verified when
implementation begins.

## 7. Recommended package result tiers

The package should retain rather than silently delete lower-confidence results:

1. complete strain-level audit;
2. collapsed species-level relationships;
3. Case 2A complete routes: one donor-supplied focal root and all other roots
   supplied by the environment;
4. Case 2B community-supported routes: all non-environmental roots assigned to
   one or more donors; and
5. broadly supported routes meeting the configurable within-species frequency
   criterion.

These functions are reserved for the future package paper. The current
manuscript prototype and its saved CANNEX analyses must remain unchanged.

## Future output requirement

For every retained pathway, report at least:

- pathway identifier;
- root metabolite;
- first consuming reaction and compartment;
- required transport chain;
- source type: environment or donor;
- supplying donor model or models, when applicable; and
- whether all pathway roots have a complete supply assignment.

## 8. Stoichiometric classification of pathway roots

The future package must use the stoichiometric coefficients encoded in the GEM
when deciding whether an extracellular metabolite is required by a pathway.
Coefficients are reaction ratios, not measured in-vivo production amounts. A
missing displayed coefficient is interpreted as `1` only when that convention
is valid for the input SBML representation; non-standard or unsupported
stoichiometry must be reported by GEM QC rather than silently guessed.

For candidate root `A`, define its pathway balance under a stoichiometrically
feasible non-negative reaction weighting as:

```text
net balance of A = total A produced - total A consumed
```

The sign, not merely whether the value differs from zero, determines the
interpretation:

```text
net balance < 0  -> net-required root; external supply is required
net balance = 0  -> recycled/initiating root; no net external requirement
net balance > 0  -> the pathway is a net producer of A; A is not a required root
```

The output should preserve both `net-required` and `recycled/initiating`
dependencies rather than treating them as the same biological claim. For a
strict cross-feeding precursor, the package should require a positive external
uptake requirement, equivalent to a negative pathway balance for that
metabolite. A robust implementation may minimize the required uptake of `A`,
or withhold `A` and test whether positive target production remains feasible.

This is a structural stoichiometric requirement. It must not be reported as an
in-vivo uptake amount, secretion rate, or measured flux.

## 9. Positive-net confirmation for donor precursors

The donor stage must not pass a donor solely because one selected reaction
forms the precursor. After MeneTools identifies a target-withheld donor
reaction set, the package must apply a stoichiometric feasibility check to the
complete set and require:

```text
net precursor production > numerical tolerance
```

The donor decision should therefore be:

```text
positive net intracellular precursor production
AND directionally valid outward transport
AND export-capable exchange
```

If net precursor production is zero or negative, the model must not be retained
as a donor for that pathway, even if an individual reaction forms the
precursor. The feasibility calculation demonstrates that some non-negative
reaction weighting can leave a positive net amount; it does not predict the
realized biological flux or secretion quantity.

Audit context for the fixed CANNEX Batch 1 results: all 288 retained unique
donor-precursor audits passed this positive-net post-hoc check, and none of the
500 retained recipient pathways showed the audited net-consumed-root omission.
These checks support the saved Batch 1 results but do not replace the future
package safeguards above.
